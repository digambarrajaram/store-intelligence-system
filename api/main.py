import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
import redis.asyncio as aioredis

# Import routers
from routers.analytics import router as analytics_router
from routers.debug import router as debug_router
from routers.insights import router as insights_router
from routers.pos import router as pos_router
from websocket import router as ws_router, ws_router as websocket_ws_router, init_websocket, cleanup_websocket

# Create FastAPI app
app = FastAPI(title="Store Intelligence API", version="0.1.0")

# CORS middleware (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus instrumentation
Instrumentator().instrument(app).expose(app)

# Redis connection setup
@app.on_event("startup")
async def startup_event():
    # Initialize Redis connection
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    redis_db = int(os.getenv('REDIS_DB', 0))
    
    redis_client = aioredis.from_url(
        f"redis://{redis_host}:{redis_port}/{redis_db}",
        encoding="utf-8",
        decode_responses=True
    )
    app.state.redis = redis_client
    
    # Initialize WebSocket components
    init_websocket(app)

@app.on_event("shutdown")
async def shutdown_event():
    # Cleanup WebSocket components
    await cleanup_websocket(app)
    # Close Redis connection
    if hasattr(app.state, 'redis'):
        await app.state.redis.close()

# Include routers
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(insights_router, prefix="/api/v1")
app.include_router(pos_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")  # HTTP routes from websocket.py
app.include_router(websocket_ws_router)  # WebSocket routes (no prefix)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Store Intelligence API is running"}