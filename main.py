import json
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field

from api.routers import analytics, insights, pos, debug
from api.kafka_consumer import consume_kafka
from api.websocket import ws_router, init_websocket, cleanup_websocket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Pydantic models with store_id/camera_id/zone_id ──────────────────────

class Detection(BaseModel):
    track_id: int
    bbox: list[float]
    confidence: float
    centroid: list[float]
    zone: Optional[str] = None


class DetectionEvent(BaseModel):
    frame_id: int
    timestamp: float
    store_id: str = Field("store_1", description="Store identifier")
    camera_id: str = Field(..., description="Camera identifier")
    zone_id: Optional[str] = Field(None, description="Zone identifier")
    fps: float
    detections: list[Detection]


class FootfallEvent(BaseModel):
    event_type: str  # "entry" or "exit"
    track_id: int
    timestamp: float
    store_id: str = Field("store_1", description="Store identifier")
    camera_id: str = Field(..., description="Camera identifier")
    zone_id: Optional[str] = Field(None, description="Zone identifier")
    is_reentry: bool = False
    is_staff: bool = False


class AnomalyEvent(BaseModel):
    anomaly_type: str  # "dwell", "crowd", "loitering"
    store_id: str = Field("store_1", description="Store identifier")
    camera_id: str = Field(..., description="Camera identifier")
    zone_id: Optional[str] = Field(None, description="Zone identifier")
    timestamp: float
    severity: str  # "low", "medium", "high"
    metadata: dict = {}


# ── Config loader ────────────────────────────────────────────────────────

def load_camera_config(config_path: str) -> dict:
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
    except Exception as exc:
        logger.warning(f"Failed to load camera config from {config_path}: {exc}")
    return {"stores": []}


# ── Lifespan ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    config_path = os.getenv("CAMERA_CONFIG_PATH", "/app/config/cameras.json")

    app.state.redis = aioredis.from_url(f"redis://{redis_host}:{redis_port}", decode_responses=True)

    app.state.camera_config = load_camera_config(config_path)
    app.state.store_ids = [s.get("store_id") for s in app.state.camera_config.get("stores", [])]
    if not app.state.store_ids:
        app.state.store_ids = ["store_1"]
        logger.info("No stores found in config, defaulting to store_1")

    for store in app.state.camera_config.get("stores", []):
        store_id = store.get("store_id", "store_1")
        for cam in store.get("cameras", []):
            camera_id = cam.get("camera_id", "unknown")
            await app.state.redis.set(f"store:{store_id}:camera:{camera_id}:current_occupancy", 0)
            await app.state.redis.set(f"store:{store_id}:camera:{camera_id}:peak_occupancy", 0)
            await app.state.redis.set(f"store:{store_id}:camera:{camera_id}:fps", 0)
            await app.state.redis.set(f"store:{store_id}:camera:{camera_id}:anomaly_count", 0)
            logger.info(f"Initialized metrics for {store_id}/{camera_id}")

    task = asyncio.create_task(consume_kafka(app))
    init_websocket(app)
    logger.info("Application startup complete")

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await cleanup_websocket(app)
    await app.state.redis.close()
    logger.info("Application shutdown complete")


# ── FastAPI app ──────────────────────────────────────────────────────────

app = FastAPI(
    title="Store Intelligence API",
    description="Multi-store, multi-camera analytics API for retail store intelligence",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

app.include_router(analytics.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(pos.router, prefix="/api/v1")
app.include_router(debug.router, prefix="/api/v1")
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}


@app.get("/api/v1/stores", tags=["Stores"])
async def list_stores():
    """List all configured stores."""
    return {"stores": app.state.store_ids}


@app.get("/api/v1/stores/{store_id}/cameras", tags=["Stores"])
async def list_cameras(store_id: str):
    """List all cameras for a given store."""
    for store in app.state.camera_config.get("stores", []):
        if store.get("store_id") == store_id:
            cameras = [cam.get("camera_id") for cam in store.get("cameras", [])]
            return {"store_id": store_id, "cameras": cameras}
    return {"store_id": store_id, "cameras": []}
