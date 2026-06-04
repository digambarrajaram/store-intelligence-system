# 🛒 Store Intelligence System
### Purplle Tech Challenge 2026 Submission

An AI-powered retail analytics platform that processes CCTV video streams to deliver real-time footfall analytics, anomaly detection, and business insights.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![YOLOv8](https://img.shields.io/badge/YOLOv8-8.0+-red.svg)
![Kafka](https://img.shields.io/badge/Kafka-3.+-orange.svg)
![Redis](https://img.shields.io/badge/Redis-7.0+-blue.svg)
![React](https://img.shields.io/badge/React-18.2+-blue.svg)
![Docker](https://img.shields.io/badge/Docker-24.0+-blue.svg)

## Quick Start
```bash
git clone https://github.com/digambarrajaram/Store-Intelligence-System-AI-Powered-Retail-Analytics-Platform.git
cd Store-Intelligence-System-AI-Powered-Retail-Analytics-Platform
cp .env.example .env
docker compose up -d
curl http://localhost:8000/health
```
Expected response: `{"status":"healthy","env":"development","timestamp":"...","services":{"redis":"ok","kafka":"ok"},"version":"0.1.0"}`

## Architecture
```ascii
┌─────────────────┐    ┌──────────────────┐    ┌────────────────────┐
│   CCTV Cameras  │───▶│   Video Worker   │───▶│   Kafka Topics     │
│  (RTSP/Webcam)  │    │  (YOLOv8+ByteTrack)│ │  (cv.detections)   │
└─────────────────┘    └──────────────────┘    └─────────┬──────────┘
                                                        ▼
                                               ┌──────────────────┐
                                               │ Anomaly Detector │
                                               │  (Isolation Forest)│
                                               └─────────┬──────────┘
                                                         ▼
                                              ┌──────────────────┐
                                              │   Redis Cache    │
                                              │  (KPIs, Alerts)  │
                                              └────────┬─────────┘
                                                       ▼
                                      ┌─────────────────────────────┐
                                      │        FastAPI API            │
                                      │  /health, /metrics, /funnel,  │
                                      │  /anomalies, /pos/ingest,    │
                                      │  /insights/*, /ws/alerts     │
                                      └─────────────┬────────────────┘
                                                    ▼
                                      ┌─────────────────────────────┐
                                      │     React Dashboard (WS)     │
                                      │  Live charts, heatmaps,      │
                                      │  anomaly alerts, POS data    │
                                      └─────────────────────────────┘
```

## API Reference
| Method | Endpoint                 | Description                                                | Response                                  |
|--------|--------------------------|------------------------------------------------------------|-------------------------------------------|
| GET    | `/health`                | Health check of API and dependencies                       | `{status, env, timestamp, services, version}` |
| GET    | `/api/v1/store-metrics`   | Store KPIs (entries, exits, occupancy, dwell time, etc.)   | JSON with period metrics                  |
| GET    | `/api/v1/funnel`         | Conversion funnel (entered store → browsed → checkout → purchased) | JSON with funnel steps and conversion rate |
| GET    | `/api/v1/anomalies`      | Recent anomalies (dwell, crowd, loitering) with filtering  | Array of anomaly objects                  |
| POST   | `/api/v1/pos/ingest`     | Ingest POS data (CSV or JSON) to compute daily aggregates  | `{status, date, transactions_processed, aggregates_cached}` |
| GET    | `/api/v1/insights/correlation` | Correlation between vision footfall and POS data (conversion rate, revenue per visitor) | JSON with metrics and insight text |
| GET    | `/api/v1/insights/salesperson` | Ranked leaderboard of salespeople by total GMV           | Array of salesperson objects (order_count, total_gmv, avg_basket) |
| WS     | `/ws/alerts`             | Real-time WebSocket stream of anomaly events               | JSON anomaly messages (`{type, data, connected_clients, server_time}`) |

## Configuration
| Environment Variable       | Default                     | Description                                                |
|----------------------------|-----------------------------|------------------------------------------------------------|
| `API_PORT`                 | `8000`                      | Port for the FastAPI server                                |
| `DASHBOARD_PORT`           | `3000`                      | Port for the React dashboard                               |
| `GRAFANA_PORT`             | `3001`                      | Port for Grafana (if used)                                 |
| `KAFKA_PORT`               | `9092`                      | Port for Kafka broker                                      |
| `ZOOKEEPER_PORT`           | `2181`                      | Port for Zookeeper (if used)                               |
| `REDIS_PORT`               | `6379`                      | Port for Redis server                                      |
| `PROMETHEUS_PORT`          | `9090`                      | Port for Prometheus metrics                                |
| `KAFKA_BOOTSTRAP_SERVERS`  | `kafka:9092`                | Kafka broker addresses (used by workers and API)           |
| `REDIS_HOST`               | `redis`                     | Redis hostname                                             |
| `MIN_CONFIDENCE`           | `0.4`                       | Minimum confidence for YOLOv8 detections                   |
| `FRAME_SKIP`               | `3`                         | Number of frames to skip between detections                |
| `VIDEO_SOURCE`             | `0`                         | Video source (camera index, file path, or RTSP URL)        |
| `CAMERA_ID`                | `camera_0`                  | Identifier for the camera/video source                     |
| `DWELL_THRESHOLD_SECONDS`  | `300`                       | Seconds to trigger a dwell anomaly                         |
| `CROWD_THRESHOLD`          | `8`                         | Person count threshold to trigger a crowd anomaly          |
| `ANOMALY_DWELL_THRESHOLD_SEC`| `30`                      | (API) Threshold for dwell anomalies in seconds             |
| `ANOMALY_CROWD_THRESHOLD`  | `10`                        | (API) Threshold for crowd anomalies                        |

## Running Tests
```bash
# Install test dependencies (if not already installed)
pip install -r requirements.txt
pip install pytest pytest-asyncio

# Run all tests
pytest
```
Expected output:  
```
================================================= test session starts =================================================
collected X items

tests/test_*.py ........                                                                                                                    [100%]

================================================== X passed in YY.Ys ==================================================
```

## Project Structure
```
store-intelligence-system/
├── api/                          # FastAPI backend service
│   ├── __init__.py
│   ├── main.py                   # App entry point with /health endpoint
│   ├── metrics.py                # Prometheus metrics definitions
│   ├── websocket.py              # WebSocket connection manager and /ws/alerts
│   ├── kafka_consumer.py         # Kafka consumer for detection events
│   ├── routers/                  # API route modules
│   │   ├── analytics.py          # /metrics, /funnel
│   │   ├── insights.py           # /insights/correlation, /insights/salesperson
│   │   ├── pos.py                # /pos/ingest
│   │   └── debug.py              # Debug endpoints (if any)
│   ├── middleware/               # Custom middleware (logging)
│   ├── Dockerfile                # Container definition for API
│   └── requirements.txt          # Python dependencies
├── worker/                       # Video processing service (YOLOv8+ByteTrack → Kafka)
│   ├── __init__.py
│   ├── worker.py                 # Main processing loop
│   ├── metrics.py                # Prometheus metrics for worker
│   ├── seed_salesperson.py       # Seeds salesperson data
│   ├── Dockerfile
│   └── requirements.txt
├── detection/                    # Anomaly detection module
│   ├── __init__.py
│   └── anomaly_detector.py       # Isolation Forest-based anomaly detection
├── events/                       # Event publishing & schema definitions
│   ├── __init__.py
│   ├── publisher.py              # Event publisher to Kafka/Redis
│   └── schema.py                 # Event schema definitions
├── services/                     # Business logic services
│   ├── __init__.py
│   ├── alert_engine.py           # Alert generation and management
│   ├── conversion_engine.py      # Conversion funnel computation
│   ├── event_store.py            # Event storage and retrieval
│   ├── transaction_importer.py   # POS data import and processing
│   ├── video_processor.py        # Video frame processing pipeline
│   └── zone_manager.py           # Zone-based detection management
├── config/                       # Store and camera configuration
│   ├── cameras.json              # Camera definitions
│   ├── zones.json                # Zone definitions
│   ├── store_layout.json         # Store layout configuration
│   ├── store_1_camera_1_layout.json
│   ├── store_1_camera_2_layout.json
│   ├── store_1_camera_3_layout.json
│   ├── store_1_camera_4_layout.json
│   ├── store_2_camera_1_layout.json
│   ├── store_2_camera_2_layout.json
│   ├── store_2_camera_3_layout.json
│   └── store_2_camera_4_layout.json
├── dashboard/                    # React frontend (Vite + TypeScript)
│   ├── src/
│   │   ├── main.tsx              # App entry point
│   │   ├── App.tsx               # Root component
│   │   ├── index.css             # Global styles
│   │   ├── components/           # UI components
│   │   │   ├── AnomalyFeed.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   ├── FunnelChart.tsx
│   │   │   ├── KPICards.tsx
│   │   │   ├── OccupancyChart.tsx
│   │   │   └── SalespersonLeaderboard.tsx
│   │   ├── hooks/                # Custom React hooks
│   │   │   ├── usePolling.ts
│   │   │   └── useWebSocket.ts
│   │   └── types/
│   │       └── api.ts            # TypeScript type definitions
│   ├── Dockerfile
│   ├── nginx.conf                # Nginx configuration for production
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── tailwind.config.js
│   └── postcss.config.js
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── conftest.py               # Shared test fixtures
│   ├── unit/                     # Unit tests
│   │   ├── __init__.py
│   │   ├── test_alert_engine.py
│   │   ├── test_anomaly_detector.py
│   │   ├── test_conversion_engine.py
│   │   ├── test_event_store.py
│   │   ├── test_reentry_tracker.py
│   │   ├── test_staff_filter.py
│   │   ├── test_video_processor.py
│   │   ├── test_zone_detector.py
│   │   └── test_zone_manager_service.py
│   └── integration/              # Integration tests
│       ├── __init__.py
│       ├── test_api_funnel.py
│       ├── test_api_metrics.py
│       └── test_websocket_alerts.py
├── grafana/                      # Grafana dashboards & provisioning
│   ├── dashboards/
│   │   └── store.json            # Pre-built store analytics dashboard
│   └── provisioning/
│       ├── dashboards/
│       └── datasources/
├── prometheus/                   # Prometheus monitoring config
│   └── prometheus.yml
├── docker-compose.yml            # Orchestrates all services (api, 8 workers, kafka, redis, dashboard, prometheus, grafana)
├── Dockerfile                    # Builds worker service images (YOLOv8 video processing)
├── Dockerfile.api                # Builds the FastAPI service image
├── entrypoint.sh                 # API container entrypoint (waits for Redis, seeds data, starts uvicorn)
├── main.py                       # FastAPI application entry point (routes, lifespan, health check)
├── .env.example                  # Template environment variables
├── .gitignore
├── requirements.txt              # Python dependencies for worker Docker image
├── CHOICES.md                    # Technical decisions documentation
├── DESIGN.md                     # Design documentation
└── README.md                     # This file
```

## Demo (10-Minute Verification)
1. **Start the stack**:  
   `docker compose up -d` (wait 30 seconds for services to initialize)
2. **Verify health**:  
   `curl http://localhost:8000/health` → should return `"status":"healthy"`
3. **Check metrics**:  
   `curl http://localhost:8000/api/v1/store-metrics` → returns JSON with KPIs (all zeros initially)
4. **Simulate a detection**:  
   ```bash
   curl -X POST http://localhost:8000/api/v1/ingest/detection \
     -H "Content-Type: application/json" \
     -d '{"frame_id":1,"timestamp":1717171717,"camera_id":"cam_0","fps":30,"detections":[{"bbox":[100,100,200,200],"confidence":0.9,"class_id":0,"track_id":1}]}'
   ```
   Returns `{"queued":true,"topic":"cv.detections"}`
5. **View anomaly stream**:  
   Open `ws://localhost:8000/ws/alerts` in a WebSocket client (or use browser dev tools) to see live anomaly events.
6. **Ingest POS data**:  
   ```bash
   curl -X POST http://localhost:8000/api/v1/pos/ingest \
     -F 'file=@path/to/sample_pos.csv' \
     -H "Content-Type: multipart/form-data"
   ```
   Returns `{"status":"success",...}` (use any CSV with required columns)
7. **View insights**:  
   `curl http://localhost:8000/api/v1/insights/correlation?date=2026-05-31` → returns correlation insights (if POS data ingested for today)
8. **Check dashboard**:  
   Visit `http://localhost:3000` to see live charts and anomaly feed (requires simulated data for meaningful visualization).

All endpoints should respond within 2 seconds. Stop the stack with `docker compose down`.
