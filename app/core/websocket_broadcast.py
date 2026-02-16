"""
WebSocket real-time broadcast module.

Streams signals, events, and metrics to connected clients in real-time.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional, Set
from fastapi import WebSocket, WebSocketDisconnect

from app.core.monitoring import get_system_metrics

logger = logging.getLogger(__name__)

# Connected WebSocket clients
_clients: Set[WebSocket] = set()
_broadcast_task: Optional[asyncio.Task] = None
_running = False


async def start_websocket_broadcaster() -> None:
    """Start the WebSocket broadcast task."""
    global _broadcast_task, _running
    _running = True
    _broadcast_task = asyncio.create_task(_broadcast_loop())
    logger.info("WebSocket broadcaster started")


async def stop_websocket_broadcaster() -> None:
    """Stop the WebSocket broadcast task."""
    global _broadcast_task, _running
    _running = False
    if _broadcast_task:
        _broadcast_task.cancel()
        try:
            await _broadcast_task
        except asyncio.CancelledError:
            pass
        _broadcast_task = None
    logger.info("WebSocket broadcaster stopped")


async def _broadcast_loop() -> None:
    """Main broadcast loop - sends periodic status updates to all clients."""
    while _running:
        try:
            # Send periodic status update every 10 seconds
            await asyncio.sleep(10)
            await broadcast_status()
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Broadcast loop error")
            await asyncio.sleep(1)


async def broadcast_signal(signal: dict) -> None:
    """Broadcast a signal to all connected clients."""
    if not _clients:
        return
    
    message = {
        "type": "signal",
        "data": signal,
    }
    
    await _broadcast(message)


async def broadcast_status() -> None:
    """Broadcast system status to all connected clients."""
    if not _clients:
        return
    
    metrics = get_system_metrics()
    message = {
        "type": "status",
        "data": {
            "metrics": metrics,
            "connected_clients": len(_clients),
        },
    }
    
    await _broadcast(message)


async def _broadcast(message: dict) -> None:
    """Send a message to all connected clients."""
    disconnected = set()
    
    for client in _clients:
        try:
            await client.send_json(message)
        except Exception:
            logger.debug("Client disconnected during broadcast")
            disconnected.add(client)
    
    # Remove disconnected clients
    for client in disconnected:
        _clients.discard(client)


async def handle_websocket_connection(websocket: WebSocket) -> None:
    """Handle a new WebSocket connection."""
    await websocket.accept()
    _clients.add(websocket)
    logger.info(f"WebSocket client connected. Total clients: {len(_clients)}")
    
    # Send initial connection message
    await websocket.send_json({
        "type": "connected",
        "data": {
            "message": "Connected to SignalEngine real-time feed",
            "version": "3.0.0",
        },
    })
    
    try:
        # Keep connection alive and listen for client messages
        while True:
            try:
                # Wait for client messages (ping/pong, etc.)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Echo or handle client messages if needed
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({"type": "keepalive"})
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception:
        logger.exception("WebSocket connection error")
    finally:
        _clients.discard(websocket)
        logger.info(f"WebSocket client removed. Remaining clients: {len(_clients)}")
