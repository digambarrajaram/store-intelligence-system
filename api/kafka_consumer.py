import json
from aiokafka import AIOKafkaConsumer

async def consume_kafka(app):

    consumer = AIOKafkaConsumer(
        "cv.detections",
        bootstrap_servers="kafka:9092",
        group_id="analytics-group",
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8"))
    )

    await consumer.start()

    print("Kafka Consumer Started")

    try:
        async for msg in consumer:

            event = msg.value

            detections = event.get("detections", [])

            occupancy = len(detections)

            redis = app.state.redis

            # Running total
            await redis.incrby(
                "total_entries",
                occupancy
            )

            # Current frame occupancy
            await redis.set(
                "current_occupancy",
                occupancy
            )

            # Peak occupancy
            current_peak = int(
                await redis.get("peak_occupancy") or 0
            )

            if occupancy > current_peak:
                await redis.set(
                    "peak_occupancy",
                    occupancy
                )

            # FPS
            await redis.set(
                "camera_fps",
                event.get("fps", 0)
            )

            # Timestamp
            await redis.set(
                "metrics:last_updated",
                event.get("timestamp")
            )

            # Simple anomaly
            if occupancy > 5:

                anomaly_count = int(
                    await redis.get("anomaly_count") or 0
                )

                await redis.set(
                    "anomaly_count",
                    anomaly_count + 1
                )

    except Exception as e:
        print(f"Kafka Consumer Error: {e}")

    finally:
        await consumer.stop()