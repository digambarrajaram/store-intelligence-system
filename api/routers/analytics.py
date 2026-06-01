import json
import time
from aiokafka import AIOKafkaConsumer

async def consume_kafka(app):

    consumer = AIOKafkaConsumer(
        "cv.detections",
        bootstrap_servers="kafka:9092",
        group_id="analytics-group",
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(
            m.decode("utf-8")
        )
    )

    await consumer.start()

    print("Kafka Consumer Started")

    redis = app.state.redis

    try:

        while True:

            msg = await consumer.getone()

            event = msg.value

            detections = event.get(
                "detections",
                []
            )

            now = time.time()

            for det in detections:

                track_id = str(
                    det["track_id"]
                )

                exists = await redis.sismember(
                    "active_tracks",
                    track_id
                )

                if not exists:

                    await redis.sadd(
                        "active_tracks",
                        track_id
                    )

                    await redis.zadd(
                        "entries",
                        {
                            track_id: now
                        }
                    )

            occupancy = await redis.scard(
                "active_tracks"
            )

            current_peak = int(
                await redis.get(
                    "peak_occupancy"
                ) or 0
            )

            if occupancy > current_peak:

                await redis.set(
                    "peak_occupancy",
                    occupancy
                )

            await redis.set(
                "camera_fps",
                event.get("fps", 0)
            )

            await redis.set(
                "metrics:last_updated",
                now
            )

    except Exception as e:

        print(
            f"Kafka Consumer Error: {e}"
        )

    finally:

        await consumer.stop()