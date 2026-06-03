import json
import os
import asyncio
import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from api.routers import analytics, insights, pos, debug
from api.websocket import ws_router, init_websocket, cleanup_websocket
from api.kafka_consumer import consume_kafka

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_camera_config(config_path: str) -> dict:
    """Load camera configuration from JSON file."""
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
    except Exception as exc:
        logger.warning(f"Failed to load camera config from {config_path}: {exc}")
    return {"stores": []}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    config_path = os.getenv("CAMERA_CONFIG_PATH", "/app/config/cameras.json")

    app.state.redis = aioredis.from_url(f"redis://{redis_host}:{redis_port}", decode_responses=True)
    app.state.sync_redis = None  # Will be set by the debug router if needed

    # Load camera config and store in app state
    app.state.camera_config = load_camera_config(config_path)
    app.state.store_ids = [s.get("store_id") for s in app.state.camera_config.get("stores", [])]
    if not app.state.store_ids:
        app.state.store_ids = ["store_1"]
        logger.info("No stores found in config, defaulting to store_1")

    # Initialize store/camera metrics from config
    for store in app.state.camera_config.get("stores", []):
        store_id = store.get("store_id", "store_1")
        for cam in store.get("cameras", []):
            camera_id = cam.get("camera_id", "unknown")
            # Pre-initialize Redis keys for each store/camera
            await app.state.redis.set(f"store:{store_id}:camera:{camera_id}:current_occupancy", 0)
            await app.state.redis.set(f"store:{store_id}:camera:{camera_id}:peak_occupancy", 0)
            await app.state.redis.set(f"store:{store_id}:camera:{camera_id}:fps", 0)
            await app.state.redis.set(f"store:{store_id}:camera:{camera_id}:anomaly_count", 0)
            logger.info(f"Initialized metrics for {store_id}/{camera_id}")

    # Start Kafka consumer
    task = asyncio.create_task(consume_kafka(app))

    # Initialize WebSocket
    init_websocket(app)
    logger.info("Application startup complete")

    yield

    # Shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await cleanup_websocket(app)
    await app.state.redis.close()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Store Intelligence API",
    description="Multi-store, multi-camera analytics API for retail store intelligence",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Routers
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(pos.router, prefix="/api/v1")
app.include_router(debug.router, prefix="/api/v1")

# WebSocket router (mounted without prefix since it has its own path)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}
