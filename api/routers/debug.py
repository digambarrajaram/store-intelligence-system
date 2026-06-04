from fastapi import APIRouter, Request, HTTPException, Query
import datetime
import time
import json
import os
from typing import Optional

router = APIRouter()

@router.post("/simulate", tags=["Debug"])
async def simulate(
    request: Request,
    entries: int,
    exits: int,
    anomalies: int,
    dwell_seconds: int,
    store_id: str = Query("store_1"),
    camera_id: str = Query("camera_0"),
):
    redis = request.app.state.redis
    now = time.time()
    start_time = now - 600

    for i in range(entries):
        ts = start_time + (i / max(entries, 1)) * 600
        await redis.zadd(f'store:{store_id}:camera:{camera_id}:entries', {f'entry:{int(now)}:{i}': ts})
        # Also add to store-wide
        await redis.zadd(f'store:{store_id}:entries', {f'{camera_id}:entry:{int(now)}:{i}': ts})

    for i in range(exits):
        ts = start_time + (i / max(exits, 1)) * 600
        await redis.zadd(f'store:{store_id}:camera:{camera_id}:exits', {f'exit:{int(now)}:{i}': ts})
        await redis.zadd(f'store:{store_id}:exits', {f'{camera_id}:exit:{int(now)}:{i}': ts})
        dwell_vari = dwell_seconds * (0.5 + 0.5 * (i / max(exits, 1)))
        await redis.hset(f'store:{store_id}:camera:{camera_id}:dwell_times', f'exit:{int(now)}:{i}', dwell_vari)

    await redis.incrby(f'store:{store_id}:camera:{camera_id}:anomaly_count', anomalies)
    current_occupancy = max(0, entries - exits)
    existing_peak = int(await redis.get(f'store:{store_id}:camera:{camera_id}:peak_occupancy') or 0)
    await redis.set(f'store:{store_id}:camera:{camera_id}:peak_occupancy', max(existing_peak, current_occupancy))
    await redis.set(f'store:{store_id}:camera:{camera_id}:fps', 25.0)
    await redis.set(f'store:{store_id}:camera:{camera_id}:current_occupancy', current_occupancy)
    await redis.set('cv:heatmap:10x10', json.dumps([[1]*10 for _ in range(10)]))
    await redis.sadd(f'store:{store_id}:camera:{camera_id}:active_tracks', *[f'track_{i}' for i in range(max(entries, exits) + 10)])
    await redis.incrby('cv:pipeline:frames_processed', 1000)
    await redis.set('cv:pipeline:last_frame_id', int(now))
    await redis.set('cv:pipeline:unique_tracks_seen', max(entries, exits) + 50)
    await redis.incrby('cv:pipeline:events_published', entries + exits + anomalies)
    await redis.set('cv:pipeline:worker_last_heartbeat', datetime.datetime.now(datetime.timezone.utc).isoformat())
    await redis.set('cv:metrics:last_updated', datetime.datetime.now(datetime.timezone.utc).isoformat())

    return {
        "status": "simulation_complete",
        "store_id": store_id,
        "camera_id": camera_id,
        "entries_added": entries,
        "exits_added": exits,
        "anomalies_added": anomalies,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }


@router.get("/pipeline/status", tags=["Debug"])
async def pipeline_status(
    request: Request,
    store_id: str = Query("store_1"),
    camera_id: str = Query("camera_0"),
):
    redis = request.app.state.redis
    return {
        "store_id": store_id,
        "camera_id": camera_id,
        "frames_processed": int(await redis.get('cv:pipeline:frames_processed') or 0),
        "last_frame_id": int(await redis.get('cv:pipeline:last_frame_id') or 0),
        "unique_tracks_seen": int(await redis.get('cv:pipeline:unique_tracks_seen') or 0),
        "events_published": int(await redis.get('cv:pipeline:events_published') or 0),
        "worker_last_heartbeat": await redis.get('cv:pipeline:worker_last_heartbeat')
    }


@router.get("/health/integrity", tags=["Debug"])
async def health_integrity(
    request: Request,
    store_id: str = Query("store_1"),
    camera_id: str = Query("camera_0"),
):
    redis = request.app.state.redis
    metrics_last_updated = await redis.get('cv:metrics:last_updated')
    worker_last_heartbeat = await redis.get('cv:pipeline:worker_last_heartbeat')
    redis_keys_count = len(await redis.keys('*'))
    kafka_messages_produced = int(await redis.get('cv:pipeline:events_published') or 0)

    status = "no_data"
    if metrics_last_updated:
        try:
            last_updated = datetime.datetime.fromisoformat(metrics_last_updated.replace('Z', '+00:00'))
            now = datetime.datetime.now(datetime.timezone.utc)
            status = "healthy" if (now - last_updated).total_seconds() < 300 else "stale"
        except Exception:
            status = "stale"

    return {
        "store_id": store_id,
        "camera_id": camera_id,
        "metrics_last_updated": metrics_last_updated,
        "worker_last_heartbeat": worker_last_heartbeat,
        "redis_keys_count": redis_keys_count,
        "kafka_messages_produced": kafka_messages_produced,
        "status": status
    }
