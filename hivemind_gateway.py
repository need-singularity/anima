#!/usr/bin/env python3
"""hivemind_gateway.py - WS proxy for Hivemind cluster.

Proxies user WS connections to Anima nodes with round-robin routing.
Serves web/index.html and exposes hivemind status in init messages.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import List

ANIMA_DIR = Path(__file__).parent
HEALTHCHECK_INTERVAL = 5.0

try:
    from websockets.asyncio.server import serve as _ws_serve
    from websockets.http11 import Response as _ws_Response
    from websockets.datastructures import Headers as _ws_Headers
    import websockets
except ImportError:
    _ws_serve = None


class HivemindGateway:
    """WS proxy that routes users to Anima nodes."""

    def __init__(self, gateway_port: int = 8765, node_ports: List[int] = None,
                 node_host: str = "localhost"):
        self.gateway_port = gateway_port
        self.node_ports = node_ports or []
        self.node_host = node_host
        self._rr_index = 0
        self._node_ws = {}
        self._node_healthy = {p: False for p in self.node_ports}
        self._node_states = {}
        self._user_clients = set()

    def _next_node(self) -> int:
        if not self.node_ports:
            return None
        port = self.node_ports[self._rr_index % len(self.node_ports)]
        self._rr_index += 1
        return port

    def hivemind_status(self) -> dict:
        total_phi = sum(
            s.get("consciousness", {}).get("phi", 0)
            for s in self._node_states.values()
        )
        n_healthy = sum(1 for h in self._node_healthy.values() if h)
        return {
            "nodes": len(self.node_ports),
            "healthy": n_healthy,
            "total_phi": total_phi,
            "sync_r": 0.0,
            "active": False,
        }

    def _http_handler(self, connection, request):
        if request.headers.get("Upgrade", "").lower() == "websocket":
            return None
        if request.path in ("/", "/index.html"):
            html = ANIMA_DIR / "web" / "index.html"
            if html.exists():
                body = html.read_bytes()
                return _ws_Response(200, "OK", _ws_Headers([
                    ("Content-Type", "text/html; charset=utf-8"),
                    ("Content-Length", str(len(body))),
                ]), body)
        return _ws_Response(404, "Not Found", _ws_Headers(), b"404")

    async def _ws_handler(self, websocket):
        self._user_clients.add(websocket)
        node_port = self._next_node()
        node_url = f"ws://{self.node_host}:{node_port}"
        try:
            async with websockets.connect(node_url) as node_ws:
                init_raw = await asyncio.wait_for(node_ws.recv(), timeout=10)
                init_msg = json.loads(init_raw)
                init_msg["hivemind"] = self.hivemind_status()
                await websocket.send(json.dumps(init_msg, ensure_ascii=False))

                async def user_to_node():
                    async for msg in websocket:
                        await node_ws.send(msg)

                async def node_to_user():
                    async for msg in node_ws:
                        await websocket.send(msg)

                await asyncio.gather(user_to_node(), node_to_user())
        except Exception:
            pass
        finally:
            self._user_clients.discard(websocket)

    async def _healthcheck_loop(self):
        while True:
            for port in self.node_ports:
                url = f"ws://{self.node_host}:{port}"
                try:
                    async with websockets.connect(url) as ws:
                        init = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                        self._node_healthy[port] = True
                        self._node_states[port] = init
                except Exception:
                    self._node_healthy[port] = False
            await asyncio.sleep(HEALTHCHECK_INTERVAL)

    async def run(self):
        asyncio.create_task(self._healthcheck_loop())
        async with _ws_serve(self._ws_handler, "0.0.0.0", self.gateway_port,
                             process_request=self._http_handler,
                             ping_interval=20, ping_timeout=60):
            print(f"[gateway] http://localhost:{self.gateway_port} -> nodes {self.node_ports}")
            while True:
                await asyncio.sleep(1)


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--nodes", type=str, required=True, help="Comma-separated node ports")
    p.add_argument("--host", type=str, default="localhost")
    args = p.parse_args()
    node_ports = [int(x) for x in args.nodes.split(",")]
    gw = HivemindGateway(gateway_port=args.port, node_ports=node_ports, node_host=args.host)
    asyncio.run(gw.run())


if __name__ == "__main__":
    main()
