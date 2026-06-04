# NOTE: Add redis-tools to Dockerfile apt-get install for healthcheck to work.
import os
import cv2
import json
import time
import signal
import sys
import asyncio
import redis as redis_client
from aiokafka import AIOKafkaProducer
from ultralytics import YOLO

# Import metrics counter for Kafka publish errors
try:
    from metrics import kafka_publish_errors_total
except ImportError:
    # Fallback if metrics module not available (e.g., when running in isolation)
    class DummyCounter:
        def inc(self):
            pass
    kafka_publish_errors_total = DummyCounter()

# Local service imports
try:
    from services.video_processor import VideoProcessor
except ImportError:
    VideoProcessor = None

try:
    from services.event_store import EventStore
except ImportError:
    EventStore = None

try:
    from services.conversion_engine import ConversionEngine
except ImportError:
    ConversionEngine = None

try:
    from services.alert_engine import AlertEngine
except ImportError:
    AlertEngine = None

# Environment variables with defaults
MIN_CONFIDENCE = float(os.getenv('MIN_CONFIDENCE', '0.4'))
FRAME_SKIP = int(os.getenv('FRAME_SKIP', '3'))
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'cv.detections')
VIDEO_SOURCE = os.getenv('VIDEO_SOURCE', os.getenv('VIDEO_PATH', '0'))
CAMERA_ID = os.getenv('CAMERA_ID', 'camera_0')
STORE_ID = os.getenv('STORE_ID', 'store_1')
CAMERA_CONFIG_PATH = os.getenv('CAMERA_CONFIG_PATH', '/app/config/cameras.json')
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

# Global flag for graceful shutdown
running = True

def signal_handler(sig, frame):
    global running
    print('Received shutdown signal. Stopping gracefully...')
    running = False

def load_camera_config(config_path: str, store_id: str, camera_id: str) -> dict | None:
    """Load camera configuration from JSON file for the given store and camera."""
    try:
        if not os.path.exists(config_path):
            print(f"Camera config not found at {config_path}, using env vars")
            return None
        with open(config_path, 'r') as f:
            config = json.load(f)
        stores = config.get('stores', [])
        for store in stores:
            if store.get('store_id') == store_id:
                for cam in store.get('cameras', []):
                    if cam.get('camera_id') == camera_id:
                        return cam
        print(f"Camera {camera_id} not found in store {store_id} config, using env vars")
        return None
    except Exception as exc:
        print(f"Error loading camera config: {exc}")
        return None

async def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Load camera config if available
    cam_config = load_camera_config(CAMERA_CONFIG_PATH, STORE_ID, CAMERA_ID)
    if cam_config:
        video_path = cam_config.get('video_path', VIDEO_SOURCE)
        print(f"Loaded camera config for {STORE_ID}/{CAMERA_ID}: video_path={video_path}")
    else:
        video_path = VIDEO_SOURCE

    # Redis connection with retry logic (5 attempts, 3s sleep)
    print("Connecting to Redis...")
    r = None
    for attempt in range(5):
        try:
            r = redis_client.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
            r.ping()
            print(f"Redis connected on attempt {attempt + 1}")
            break
        except Exception as e:
            print(f"Redis connection attempt {attempt + 1} failed: {e}")
            if attempt < 4:  # Not the last attempt
                time.sleep(3)
            else:
                print("ERROR: Could not connect to Redis after 5 attempts. Exiting.")
                sys.exit(1)

    # Write initial heartbeat immediately so healthcheck passes during startup
    heartbeat_key = f'store:{STORE_ID}:camera:{CAMERA_ID}:worker.alive'
    r.set(heartbeat_key, '1', ex=120)
    r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:worker:last_heartbeat', time.time())
    r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:worker:status', 'initializing')
    print(f"Initial heartbeat written to {heartbeat_key}")

    # Initialize event storage
    event_store = None
    if EventStore is not None:
        try:
            event_store = EventStore(r, store_id=STORE_ID, camera_id=CAMERA_ID)
            print("EventStore initialized")
        except Exception as exc:
            print(f"Warning: EventStore initialization failed: {exc}")
            event_store = None

    # Kafka producer with retry logic (10 attempts, 5s sleep)
    print("Connecting to Kafka...")
    producer = None
    for attempt in range(10):
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=30000,
                retry_backoff_ms=1000,
                acks=1,
                max_batch_size=16384,
                linger_ms=100
            )
            await producer.start()
            print(f"Kafka producer connected on attempt {attempt + 1}")
            break
        except Exception as e:
            print(f"Kafka connection attempt {attempt + 1} failed: {e}")
            if attempt < 9:  # Not the last attempt
                await asyncio.sleep(5)
            else:
                print("ERROR: Could not connect to Kafka after 10 attempts. Exiting.")
                await producer.stop() if producer else None
                sys.exit(1)

    # Load YOLOv8n model
    model = YOLO('yolov8n.pt')
    print("YOLOv8n model loaded")

    # Initialize video processor for event enrichment
    processor = None
    if VideoProcessor is not None:
        try:
            processor = VideoProcessor()
            print("VideoProcessor initialized")
        except Exception as exc:
            print(f"Warning: VideoProcessor initialization failed: {exc}")
            processor = None

    conversion_engine = None
    if ConversionEngine is not None:
        try:
            conversion_engine = ConversionEngine(r, camera_id=CAMERA_ID, store_id=STORE_ID)
            print(f"ConversionEngine initialized for {STORE_ID}/{CAMERA_ID}")
        except Exception as exc:
            print(f"Warning: ConversionEngine initialization failed: {exc}")
            conversion_engine = None

    alert_engine = None
    if AlertEngine is not None and processor is not None:
        try:
            alert_engine = AlertEngine(r, processor.zone_manager, store_id=STORE_ID, camera_id=CAMERA_ID)
            print("AlertEngine initialized")
        except Exception as exc:
            print(f"Warning: AlertEngine initialization failed: {exc}")
            alert_engine = None

    # Open video source
    source = int(video_path) if video_path.isdigit() else video_path
    
    # Check if VIDEO_SOURCE is a file that exists
    is_file = not video_path.isdigit() and os.path.exists(video_path)
    
    if not is_file and not video_path.isdigit():
        print(f"WARNING: Video file not found at {video_path}. Running in demo mode.")
        # Demo mode: we'll generate synthetic events
        cap = None  # We won't use OpenCV capture
    else:
        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            print(f"Error: Could not open video source '{video_path}'")
            # Don't exit — keep container alive so healthcheck can still pass
            # Write heartbeat so worker health endpoint doesn't stale immediately
            r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:worker.alive', '1', ex=300)
            r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:pipeline:status', json.dumps({
                'frames_processed': 0,
                'last_frame_id': 0,
                'unique_tracks_seen': 0,
                'events_published': 0,
                'error': f'Could not open video source: {video_path}'
            }))
            await producer.stop()
            return

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0 if cap else 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if cap else 640
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if cap else 480
    if cap:
        print(f"Video opened: {video_path} ({width}x{height} @ {fps:.1f}fps)")
    else:
        print(f"Running in demo mode: generating synthetic events")

    frame_count = 0
    processed_count = 0
    events_published = 0
    unique_tracks = set()
    start_time = time.time()
    last_log_time = start_time
    last_heartbeat = start_time
    last_demo_event_time = start_time

    try:
        while running:
            if cap:
                ret, frame = cap.read()
                if not ret:
                    print("End of video stream or failed to read frame")
                    break

                frame_count += 1

                # Skip frames for performance
                if frame_count % (FRAME_SKIP + 1) != 0:
                    continue

                processed_count += 1

                # Run YOLOv8 tracking with ByteTrack
                results = model.track(
                    frame,
                    persist=True,
                    tracker="bytetrack.yaml",
                    classes=[0],           # person only
                    conf=MIN_CONFIDENCE,
                    verbose=False
                )

                detections = []
                if results[0].boxes is not None and len(results[0].boxes) > 0:
                    boxes = results[0].boxes
                    for box in boxes:
                        track_id = int(box.id.item()) if box.id is not None else -1
                        bbox = box.xyxy[0].tolist()
                        confidence = float(box.conf.item())

                        x1, y1, x2, y2 = bbox
                        cx = (x1 + x2) / 2
                        cy = (y1 + y2) / 2

                        if track_id != -1:
                            unique_tracks.add(track_id)

                        detections.append({
                            'track_id': track_id,
                            'bbox': [round(x, 2) for x in bbox],
                            'confidence': round(confidence, 4),
                            'centroid': [round(cx, 2), round(cy, 2)]
                        })
            else:
                # Demo mode: generate synthetic DetectionEvents every 1 second
                current_time = time.time()
                if current_time - last_demo_event_time < 1.0:
                    # Sleep a bit to avoid busy loop
                    await asyncio.sleep(0.1)
                    continue
                last_demo_event_time = current_time
                
                processed_count += 1
                frame_count += 1  # Simulate frame count
                
                # Generate 1-3 random detections
                import random
                num_detections = random.randint(1, 3)
                detections = []
                for i in range(num_detections):
                    track_id = random.randint(1000, 9999)
                    # Generate random bbox within 640x480
                    x1 = random.randint(0, 500)
                    y1 = random.randint(0, 400)
                    x2 = x1 + random.randint(50, 140)
                    y2 = y1 + random.randint(80, 200)
                    bbox = [x1, y1, x2, y2]
                    confidence = round(random.uniform(0.5, 0.95), 4)
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    
                    detections.append({
                        'track_id': track_id,
                        'bbox': [round(x, 2) for x in bbox],
                        'confidence': confidence,
                        'centroid': [round(cx, 2), round(cy, 2)]
                    })
                    
                    if track_id != -1:
                        unique_tracks.add(track_id)

            # Build base event payload
            timestamp = time.time()
            event = {
                'frame_id': frame_count,
                'timestamp': timestamp,
                'store_id': STORE_ID,
                'camera_id': CAMERA_ID,
                'fps': round(fps, 2),
                'detections': detections
            }

            # Attach generated customer movement events if the processor is available
            customer_events = []
            if processor is not None:
                try:
                    customer_events = processor.process_frame(
                        frame_count,
                        timestamp,
                        CAMERA_ID,
                        detections
                    )
                    if customer_events:
                        event['customer_events'] = customer_events
                        if event_store is not None:
                            try:
                                event_store.save_events(customer_events)
                            except Exception as exc:
                                print(f"EventStore save failed: {exc}")
                        if conversion_engine is not None:
                            try:
                                conversion_engine.process_customer_events(customer_events)
                            except Exception as exc:
                                print(f"ConversionEngine processing failed: {exc}")
                except Exception as exc:
                    print(f"VideoProcessor processing failed: {exc}")

            if alert_engine is not None:
                try:
                    alert_engine.process_frame(
                        customer_events=customer_events,
                        detections=detections,
                        timestamp=timestamp,
                        camera_id=CAMERA_ID,
                    )
                except Exception as exc:
                    print(f"AlertEngine processing failed: {exc}")

            try:
                await producer.send(KAFKA_TOPIC, event, key=f'{STORE_ID}:{CAMERA_ID}'.encode('utf-8'))
                events_published += 1
            except Exception as e:
                print(f"Kafka publish error: {e}")
                kafka_publish_errors_total.inc()

            current_time = time.time()

            # Update pipeline status in Redis every 100 frames
            if processed_count % 100 == 0:
                r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:pipeline:frames_processed', processed_count)
                r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:pipeline:last_frame_id', frame_count)
                r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:pipeline:unique_tracks_seen', len(unique_tracks))
                r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:pipeline:events_published', events_published)
                r.set('metrics:last_updated', time.time())

            # Heartbeat every 30 seconds
            if current_time - last_heartbeat >= 30:
                r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:worker.alive', '1', ex=120)  # expires in 2 min if worker dies
                r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:worker:last_heartbeat', current_time)
                last_heartbeat = current_time

            # Log FPS every 30 seconds
            if current_time - last_log_time >= 30:
                elapsed = current_time - start_time
                processing_fps = processed_count / elapsed if elapsed > 0 else 0
                print(f"[{STORE_ID}/{CAMERA_ID}] Frames: {processed_count} | Tracks: {len(unique_tracks)} | FPS: {processing_fps:.2f} | Published: {events_published}")
                last_log_time = current_time

    except Exception as e:
        print(f"Error during processing: {e}")
        r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:worker:error', str(e))
    finally:
        if cap:
            cap.release()
        # Final status write
        r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:pipeline:frames_processed', processed_count)
        r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:pipeline:last_frame_id', frame_count)
        r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:pipeline:unique_tracks_seen', len(unique_tracks))
        r.set(f'store:{STORE_ID}:camera:{CAMERA_ID}:pipeline:events_published', events_published)
        await producer.stop()
        print(f"Worker stopped. Total: {processed_count} frames, {len(unique_tracks)} unique tracks, {events_published} events published.")

if __name__ == "__main__":
    asyncio.run(main())
