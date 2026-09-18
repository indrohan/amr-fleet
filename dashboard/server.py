"""
server.py — Async WebSocket server + HTTP static file server.

Architecture
────────────
  ┌─────────────────────────────────────────┐
  │           asyncio event loop            │
  │                                         │
  │  SimulationEngine ──► state_queue       │
  │                            │            │
  │                    BroadcastServer      │
  │                    (ws://localhost:8765)│
  │                            │            │
  │                     Browser clients     │
  │                                         │
  │  aiohttp HTTP server (localhost:8080)   │
  │  serves dashboard/static/index.html     │
  └─────────────────────────────────────────┘

The state_queue is an asyncio.Queue shared between the simulation
engine and the broadcast server.  The engine puts JSON snapshots;
the server drains the queue and fans them out to all connected
WebSocket clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Set

import websockets
import websockets.exceptions
from aiohttp import web

from core.config import WS_HOST, WS_PORT, HTTP_HOST, HTTP_PORT

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


# ── Broadcast server ───────────────────────────────────────────────────────────

class BroadcastServer:
    """
    Manages WebSocket connections and fans out state snapshots to all
    connected browser clients.

    Always stores the last snapshot that included a full warehouse layout
    so newly-connecting browsers get the map immediately.
    """

    def __init__(self, state_queue: asyncio.Queue) -> None:
        self.state_queue = state_queue
        self._clients: Set[websockets.WebSocketServerProtocol] = set()
        self._latest_snapshot: str = ""       # most recent frame
        self._full_snapshot: str   = ""       # last frame with full warehouse

    async def handler(self,
                      ws: websockets.WebSocketServerProtocol) -> None:
        self._clients.add(ws)
        logger.info("Dashboard client connected. Total: %d", len(self._clients))

        # Send the full-warehouse snapshot first so the client can draw the map
        init = self._full_snapshot or self._latest_snapshot
        if init:
            try:
                await ws.send(init)
            except websockets.exceptions.ConnectionClosed:
                pass

        try:
            async for _ in ws:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(ws)
            logger.info("Dashboard client disconnected. Total: %d",
                        len(self._clients))

    async def broadcaster(self) -> None:
        """Drains the state queue and broadcasts to all connected clients."""
        while True:
            snapshot: dict = await self.state_queue.get()
            raw = json.dumps(snapshot, default=str)
            self._latest_snapshot = raw

            # Keep a copy with the full warehouse layout for new clients
            if isinstance(snapshot.get("warehouse"), dict) and \
               "grid" in snapshot["warehouse"]:
                self._full_snapshot = raw

            dead: Set[websockets.WebSocketServerProtocol] = set()
            for client in list(self._clients):
                try:
                    await client.send(raw)
                except (websockets.exceptions.ConnectionClosed, Exception):
                    dead.add(client)
            self._clients -= dead


# ── HTTP server ───────────────────────────────────────────────────────────────

async def _build_http_app() -> web.Application:
    app = web.Application()

    async def index(_req: web.Request) -> web.Response:
        html_path = STATIC_DIR / "index.html"
        return web.FileResponse(html_path)

    app.router.add_get("/", index)
    app.router.add_static("/static", STATIC_DIR)
    return app


# ── Launcher ──────────────────────────────────────────────────────────────────

async def start_servers(state_queue: asyncio.Queue,
                        simulation_coro) -> None:
    """
    Start WebSocket server, HTTP server, and the simulation coroutine
    concurrently on the same event loop.

    Parameters
    ----------
    state_queue : asyncio.Queue
        Shared queue between simulation and broadcaster.
    simulation_coro : coroutine
        The SimulationEngine.run_async() coroutine.
    """
    broadcast_server = BroadcastServer(state_queue)

    # WebSocket server
    ws_server = await websockets.serve(
        broadcast_server.handler,
        WS_HOST, WS_PORT,
        ping_interval=20,
        ping_timeout=10,
    )
    logger.info("WebSocket server listening on ws://%s:%d", WS_HOST, WS_PORT)

    # HTTP server
    http_app = await _build_http_app()
    runner   = web.AppRunner(http_app)
    await runner.setup()
    site = web.TCPSite(runner, HTTP_HOST, HTTP_PORT)
    await site.start()
    logger.info("Dashboard available at http://%s:%d", HTTP_HOST, HTTP_PORT)

    print(f"\n  ✅  Fleet Dashboard → http://{HTTP_HOST}:{HTTP_PORT}")
    print(f"  ✅  WebSocket feed  → ws://{WS_HOST}:{WS_PORT}\n")

    # Run all three tasks concurrently
    await asyncio.gather(
        broadcast_server.broadcaster(),
        simulation_coro,
    )

    # Cleanup
    ws_server.close()
    await ws_server.wait_closed()
    await runner.cleanup()
