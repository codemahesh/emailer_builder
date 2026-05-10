"""
routers/ws.py
=============
WebSocket endpoint — /ws/{campaign_id}

Clients connect once per campaign and receive real-time JSON progress events
from the image processing pipeline. The connection is kept alive with
ping/pong over text frames.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.gateway import gateway

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/{campaign_id}")
async def websocket_endpoint(campaign_id: str, websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time campaign progress events.

    Clients:
    - Connect to ``ws://host/ws/{campaign_id}``
    - Send ``"ping"`` text frames to keep the connection alive
    - Receive JSON frames: ``{"type": "image_processed", "data": {...}}``
    """
    await gateway.connect(campaign_id, websocket)
    try:
        while True:
            # Block until the client sends a frame (ping/pong keepalive)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.debug("websocket_endpoint: client disconnected campaign_id=%s", campaign_id)
        await gateway.disconnect(campaign_id, websocket)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "websocket_endpoint: unexpected error campaign_id=%s (%s)", campaign_id, exc
        )
        await gateway.disconnect(campaign_id, websocket)
