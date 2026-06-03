import json
import asyncio
from datetime import datetime
from typing import Set
from redis import asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.websockets import WebSocketState

router = APIRouter()
ws_router = APIRouter()  # Separate router for WebSocket without prefix

# Allowed origins for WebSocket connections
ALLOWED_ORIGINS = {
    "http://65.0.204.95:3000",
    "https://65.0.204.95:3000",
    "http://localhost:3000",
    "https://localhost:3000",
    "http://localhost:5173",
    "https://localhost:5173",
    "http://localhost:8000",
    "https://localhost:8000",
}

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.redis = None  # Will be set externally via init

    async def connect(self, websocket: WebSocket):
        # Accept first, then validate origin.
        # Calling close() before accept() causes Starlette to send HTTP 403.
        await websocket.accept()
        # Validate origin - allow empty (non-browser clients, proxies stripping header)
        # and known origins
        origin = websocket.headers.get("origin", "")
        if origin:
            # Only reject if origin is present but not allowed
            origin_allowed = any(
                origin == allowed or origin.startswith(allowed.rstrip("/") + "/")
                for allowed in ALLOWED_ORIGINS
            )
            if not origin_allowed:
                print(f"WebSocket connection rejected: origin={origin}")
                await websocket.close(code=1008)
                return
        self.active_connections.add(websocket)
        # Send catch-up messages
        await self.send_catchup(websocket)
        # Send initial connected clients count
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": None,
            "connected_clients": len(self.active_connections),
            "server_time": datetime.utcnow().isoformat()
        }))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def send_catchup(self, websocket: WebSocket):
        """Send last 5 anomalies from Redis list"""
        if not self.redis:
            return
        try:
            # Get last 5 anomalies (newest first)
            anomalies = await self.redis.lrange("recent_anomalies", 0, 4)
            # Reverse to send oldest first
            anomalies = list(reversed(anomalies))
            for anomaly_json in anomalies:
                anomaly = json.loads(anomaly_json)
                await websocket.send_text(json.dumps({
                    "type": "catchup",
                    "data": anomaly,
                    "connected_clients": len(self.active_connections),
                    "server_time": datetime.utcnow().isoformat()
                }))
        except Exception as e:
            print(f"Error sending catchup: {e}")

    async def broadcast_anomaly(self, anomaly: dict):
        """Broadcast anomaly to all connected clients"""
        if not self.active_connections:
            return
        message = json.dumps({
            "type": "anomaly",
            "data": anomaly,
            "connected_clients": len(self.active_connections),
            "server_time": datetime.utcnow().isoformat()
        })
        # Send to all connections, remove disconnected ones
        disconnected = set()
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(message)
                else:
                    disconnected.add(connection)
            except Exception:
                disconnected.add(connection)
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_reconnecting(self):
        """Broadcast reconnecting status to all clients"""
        if not self.active_connections:
            return
        message = json.dumps({
            "type": "reconnecting",
            "data": None,
            "connected_clients": len(self.active_connections),
            "server_time": datetime.utcnow().isoformat()
        })
        disconnected = set()
        for connection in self.active_connections:
            try:
                if connection.client_state == WebSocketState.CONNECTED:
                    await connection.send_text(message)
                else:
                    disconnected.add(connection)
            except Exception:
                disconnected.add(connection)
        for conn in disconnected:
            self.disconnect(conn)

    async def start_ping_task(self):
        """Send ping every 30s and disconnect if no pong within 10s"""
        while True:
            await asyncio.sleep(30)
            if not self.active_connections:
                continue
            # Send ping to all connections
            disconnected = set()
            ping_message = json.dumps({
                "type": "ping",
                "data": None,
                "connected_clients": len(self.active_connections),
                "server_time": datetime.utcnow().isoformat()
            })
            for connection in self.active_connections:
                try:
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.send_text(ping_message)
                    else:
                        disconnected.add(connection)
                except Exception:
                    disconnected.add(connection)
            # Wait for pong responses (we'll rely on WebSocket's built-in ping/pong)
            # Actually, we'll use WebSocket's native ping/pong mechanism
            # Send a WebSocket ping frame and wait for pong
            for connection in self.active_connections:
                try:
                    if connection.client_state == WebSocketState.CONNECTED:
                        await connection.ping()
                    else:
                        disconnected.add(connection)
                except Exception:
                    disconnected.add(connection)
            # Give 10 seconds to respond to ping
            await asyncio.sleep(10)
            # Check again and disconnect non-responsive
            for connection in list(self.active_connections):
                try:
                    # Try to send a small message to check if connection is alive
                    await connection.send_text(json.dumps({
                        "type": "ping_check",
                        "data": None,
                        "connected_clients": len(self.active_connections),
                        "server_time": datetime.utcnow().isoformat()
                    }))
                except Exception:
                    disconnected.add(connection)
            for conn in disconnected:
                self.disconnect(conn)

# Global connection manager
manager = ConnectionManager()

@ws_router.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    client_host = websocket.client.host if websocket.client else "unknown"
    print(f"WebSocket client connected: {client_host}")
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, wait for any messages from client (though we don't expect any)
            data = await websocket.receive_text()
            # Echo back any received messages (optional)
            # await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"WebSocket client disconnected: {client_host}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@router.post("/test-alert")
async def test_alert():
    """Publish a dummy anomaly to the Redis channel for testing"""
    if not manager.redis:
        raise HTTPException(status_code=500, detail="Redis connection not available")
    # Create a dummy anomaly event
    anomaly = {
        "anomaly_id": f"test-{datetime.utcnow().isoformat()}",
        "anomaly_type": "test",
        "camera_id": "test-camera",
        "timestamp": datetime.utcnow().timestamp(),
        "severity": "low",
        "metadata": {"test": True}
    }
    try:
        await manager.redis.publish("anomaly_alerts", json.dumps(anomaly))
        return {"status": "sent", "anomaly": anomaly}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to publish to Redis: {e}")

async def pubsub_listener(redis_conn: aioredis.Redis):
    """Listen to Redis pub/sub channel and broadcast anomalies"""
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe("anomaly_alerts")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    # Store for catch-up
                    await store_anomaly_for_catchup(redis_conn, data)
                    # Broadcast to WebSocket clients
                    await manager.broadcast_anomaly(data)
                except json.JSONDecodeError:
                    print(f"Invalid JSON received: {message['data']}")
                except Exception as e:
                    print(f"Error processing anomaly: {e}")
                    # Notify clients of reconnecting
                    await manager.broadcast_reconnecting()
    except Exception as e:
        print(f"Pub/sub listener error: {e}")
        await manager.broadcast_reconnecting()
    finally:
        await pubsub.unsubscribe("anomaly_alerts")
        await pubsub.close()

async def store_anomaly_for_catchup(redis_conn: aioredis.Redis, anomaly: dict):
    """Store anomaly in Redis list for catch-up (keep last 5)"""
    anomaly_json = json.dumps(anomaly)
    await redis_conn.lpush("recent_anomalies", anomaly_json)
    await redis_conn.ltrim("recent_anomalies", 0, 4)  # Keep only first 5 elements

def init_websocket(app):
    """Initialize WebSocket components - call from main.py lifespan"""
    # Set Redis connection for manager (assuming app.state.redis is set by main.py)
    manager.redis = app.state.redis
    # Start background tasks
    app.state.pubsub_task = asyncio.create_task(pubsub_listener(manager.redis))
    app.state.ping_task = asyncio.create_task(manager.start_ping_task())

async def cleanup_websocket(app):
    """Cleanup WebSocket components - call from main.py lifespan"""
    # Cancel background tasks
    if hasattr(app.state, 'pubsub_task'):
        app.state.pubsub_task.cancel()
        try:
            await app.state.pubsub_task
        except asyncio.CancelledError:
            pass
    if hasattr(app.state, 'ping_task'):
        app.state.ping_task.cancel()
        try:
            await app.state.ping_task
        except asyncio.CancelledError:
            pass