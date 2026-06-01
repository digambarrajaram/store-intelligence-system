from fastapi import APIRouter, Depends, Query
from redis import Redis
import datetime
import time
import os

router = APIRouter()


def get_redis():
    return Redis(
        host=os.getenv("REDIS_HOST", "redis"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True
    )


@router.get("/metrics")
async def get_metrics(
    window_minutes: int = Query(60, ge=1, le=1440),
    redis: Redis = Depends(get_redis)
):

    now = time.time()
    start = now - (window_minutes * 60)

    total_entries = redis.zcount("entries", start, now)
    total_exits = redis.zcount("exits", start, now)

    current_occupancy = max(
        0,
        total_entries - total_exits
    )

    exited_track_ids = redis.zrangebyscore(
        "exits",
        start,
        now
    )

    total_dwell_time_seconds = 0
    valid_exits = 0

    for track_id in exited_track_ids:

        dwell_time = redis.hget(
            "dwell_times",
            track_id
        )

        if dwell_time is not None:
            try:
                total_dwell_time_seconds += float(
                    dwell_time
                )
                valid_exits += 1
            except ValueError:
                pass

    avg_dwell_minutes = (
        (total_dwell_time_seconds / 60)
        / valid_exits
        if valid_exits > 0
        else 0
    )

    peak_occupancy = int(
        redis.get("peak_occupancy") or 0
    )

    staff_count = int(
        redis.get("staff_count") or 0
    )

    anomaly_count = int(
        redis.get("anomaly_count") or 0
    )

    camera_fps = float(
        redis.get("camera_fps") or 0
    )

    period_start = datetime.datetime.fromtimestamp(
        start,
        tz=datetime.timezone.utc
    )

    period_end = datetime.datetime.fromtimestamp(
        now,
        tz=datetime.timezone.utc
    )

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "total_entries": total_entries,
        "total_exits": total_exits,
        "current_occupancy": current_occupancy,
        "peak_occupancy": peak_occupancy,
        "avg_dwell_minutes": round(
            avg_dwell_minutes,
            2
        ),
        "staff_count": staff_count,
        "anomaly_count": anomaly_count,
        "camera_fps": round(
            camera_fps,
            2
        )
    }


@router.get("/funnel")
async def get_funnel(
    redis: Redis = Depends(get_redis)
):

    entered_store = redis.smembers(
        "funnel:entered_store"
    )

    browsed_gt_2min = redis.smembers(
        "funnel:browsed_gt_2min"
    )

    reached_checkout_zone = redis.smembers(
        "funnel:reached_checkout_zone"
    )

    converted = redis.smembers(
        "funnel:converted"
    )

    entered_store_count = len(
        entered_store
    )

    browsed_gt_2min_count = len(
        browsed_gt_2min
    )

    reached_checkout_zone_count = len(
        reached_checkout_zone
    )

    converted_count = len(
        converted
    )

    conversion_rate_pct = (
        converted_count
        / entered_store_count
        * 100
        if entered_store_count > 0
        else 0
    )

    return {
        "entered_store": entered_store_count,
        "browsed_gt_2min": browsed_gt_2min_count,
        "reached_checkout_zone": reached_checkout_zone_count,
        "converted": converted_count,
        "conversion_rate_pct": round(
            conversion_rate_pct,
            2
        )
    }