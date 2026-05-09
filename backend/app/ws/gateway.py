"""
gateway.py
==========
WebSocket gateway singleton — routes job progress events to connected React
clients, keyed by campaign_id.

Import ``gateway`` (the module-level singleton) to broadcast events.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Set

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


class WebSocketGateway:
    """Routes job-progress events to connected React clients by campaign_id."""

    def __init__(self) -> None:
        # campaign_id → set of connected WebSocket instances
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, campaign_id: str, websocket: WebSocket) -> None:
        """Accept the WebSocket and register it under *campaign_id*."""
        await websocket.accept()
        if campaign_id not in self.connections:
            self.connections[campaign_id] = set()
        self.connections[campaign_id].add(websocket)
        logger.debug(
            "WebSocketGateway: client connected for campaign_id=%s (total=%d)",
            campaign_id,
            len(self.connections[campaign_id]),
        )

    async def disconnect(self, campaign_id: str, websocket: WebSocket) -> None:
        """Remove *websocket* from the set for *campaign_id*."""
        bucket = self.connections.get(campaign_id)
        if bucket:
            bucket.discard(websocket)
            if not bucket:
                del self.connections[campaign_id]
        logger.debug(
            "WebSocketGateway: client disconnected for campaign_id=%s", campaign_id
        )

    async def broadcast(self, campaign_id: str, message: dict) -> None:
        """
        Send a JSON-encoded *message* to all connections for *campaign_id*.

        Dead connections are silently pruned.
        """
        bucket = self.connections.get(campaign_id)
        if not bucket:
            return

        payload = json.dumps(message)
        dead: list[WebSocket] = []

        for ws in list(bucket):
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
                else:
                    dead.append(ws)
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "WebSocketGateway.broadcast: send failed for campaign_id=%s (%s)",
                    campaign_id,
                    exc,
                )
                dead.append(ws)

        for ws in dead:
            bucket.discard(ws)
        if not bucket:
            self.connections.pop(campaign_id, None)

    async def send_progress(
        self, campaign_id: str, event_type: str, data: dict
    ) -> None:
        """
        Convenience wrapper. Broadcasts a structured progress event.

        Parameters
        ----------
        campaign_id:
            Target campaign scope.
        event_type:
            Event type string, e.g. ``"image_processed"``, ``"sync_progress"``.
        data:
            Payload dict merged under ``"data"`` key.
        """
        await self.broadcast(campaign_id, {"type": event_type, "data": data})


# ── Module-level singleton ────────────────────────────────────────────────────

gateway = WebSocketGateway()
