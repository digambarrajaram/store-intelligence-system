import json
import time

from aiokafka import AIOKafkaConsumer


async def consume_kafka(app):

    print("ENTERED consume_kafka()")

    consumer = AIOKafkaConsumer(
        "cv.detections",
        bootstrap_servers="kafka:9092",
        group_id="analytics-group",
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(
            m.decode("utf-8")
        )
    )

    print("Starting Kafka Consumer")

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

            current_tracks = set()

            for det in detections:

                track_id = str(
                    det["track_id"]
                )

                current_tracks.add(track_id)

                exists = await redis.zscore(
                    "entries",
                    track_id
                )

                if exists is None:

                    await redis.zadd(
                        "entries",
                        {
                            track_id: now
                        }
                    )

            stored_tracks = await redis.smembers(
                "active_tracks"
            )

            stored_tracks = set(
                stored_tracks
            )

            exited_tracks = (
                stored_tracks
                - current_tracks
            )

            for track_id in exited_tracks:

                already_exited = await redis.zscore(
                    "exits",
                    track_id
                )

                if already_exited is None:

                    await redis.zadd(
                        "exits",
                        {
                            track_id: now
                        }
                    )

                    entry_time = await redis.zscore(
                        "entries",
                        track_id
                    )

                    if entry_time:

                        dwell_time = (
                            now
                            - float(
                                entry_time
                            )
                        )

                        await redis.hset(
                            "dwell_times",
                            track_id,
                            dwell_time
                        )

            await redis.delete(
                "active_tracks"
            )

            if current_tracks:

                await redis.sadd(
                    "active_tracks",
                    *list(current_tracks)
                )

            occupancy = len(
                current_tracks
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
                event.get(
                    "fps",
                    0
                )
            )

            await redis.set(
                "metrics:last_updated",
                now
            )

            if occupancy > 5:

                anomaly_count = int(
                    await redis.get(
                        "anomaly_count"
                    ) or 0
                )

                await redis.set(
                    "anomaly_count",
                    anomaly_count + 1
                )

    except Exception as e:

        print(
            f"Kafka Consumer Error: {e}"
        )

    finally:

        await consumer.stop()