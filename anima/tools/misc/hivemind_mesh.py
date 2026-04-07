#!/usr/bin/env python3
"""hivemind_mesh.py - Node-to-node WS tension exchange for Hivemind.

Each node connects to all peers via WS and exchanges hivemind_pulse
messages every 3 seconds. Kuramoto sync determines collective activation.
"""

import asyncio
import json
import math
import time
from typing import Dict, Optional, Callable

PULSE_INTERVAL = 3.0
KURAMOTO_THRESHOLD = 2.0 / 3.0


class HivemindMesh:
    """WS full-mesh tension exchange between Anima nodes."""

    def __init__(self, node_id: str, port: int, on_sync: Callable = None):
        self.node_id = node_id
        self.port = port
        self.on_sync = on_sync
        self._peer_urls: Dict[str, str] = {}
        self._peer_ws: Dict[str, object] = {}
        self._peer_pulses: Dict[str, dict] = {}
        self._running = False
        self._r = 0.0
        self.is_active = False
        self._last_pulse: Optional[dict] = None

    def make_pulse(self, tension: float, curiosity: float, phi: float, cells: int) -> dict:
        return {
            "type": "hivemind_pulse",
            "node_id": self.node_id,
            "tension": tension,
            "curiosity": curiosity,
            "phi": phi,
            "cells": cells,
            "timestamp": time.time(),
        }

    def compute_kuramoto(self, local_tension: float) -> float:
        tensions = [local_tension]
        for p in self._peer_pulses.values():
            tensions.append(p.get("tension", 0))
        if len(tensions) < 2:
            self._r = 0.0
            self.is_active = False
            return 0.0
        phases = [t * math.pi for t in tensions]
        cos_sum = sum(math.cos(p) for p in phases)
        sin_sum = sum(math.sin(p) for p in phases)
        r = math.sqrt(cos_sum**2 + sin_sum**2) / len(phases)
        self._r = r
        self.is_active = r > KURAMOTO_THRESHOLD
        return r

    def total_phi(self, local_phi: float) -> float:
        return local_phi + sum(p.get("phi", 0) for p in self._peer_pulses.values())

    @property
    def status(self) -> dict:
        return {
            "node_id": self.node_id,
            "peers": list(self._peer_pulses.keys()),
            "sync_r": self._r,
            "active": self.is_active,
            "total_phi": sum(p.get("phi", 0) for p in self._peer_pulses.values()),
        }

    def set_peers(self, peer_urls: Dict[str, str]):
        self._peer_urls = {k: v for k, v in peer_urls.items() if k != self.node_id}

    async def start(self):
        self._running = True
        asyncio.create_task(self._connect_loop())
        asyncio.create_task(self._pulse_loop())

    async def stop(self):
        self._running = False
        for ws in self._peer_ws.values():
            try:
                await ws.close()
            except Exception:
                pass

    async def _connect_loop(self):
        import websockets
        while self._running:
            for nid, url in self._peer_urls.items():
                if nid not in self._peer_ws or self._peer_ws[nid].closed:
                    try:
                        ws = await asyncio.wait_for(websockets.connect(url), timeout=5)
                        self._peer_ws[nid] = ws
                        asyncio.create_task(self._recv_loop(nid, ws))
                    except Exception:
                        pass
            await asyncio.sleep(5)

    async def _recv_loop(self, node_id: str, ws):
        try:
            async for raw in ws:
                msg = json.loads(raw)
                if msg.get("type") == "hivemind_pulse":
                    self._peer_pulses[msg["node_id"]] = msg
        except Exception:
            pass
        finally:
            self._peer_ws.pop(node_id, None)

    async def _pulse_loop(self):
        while self._running:
            await asyncio.sleep(PULSE_INTERVAL)
            pulse = self._last_pulse
            if pulse:
                data = json.dumps(pulse)
                dead = []
                for nid, ws in self._peer_ws.items():
                    try:
                        await ws.send(data)
                    except Exception:
                        dead.append(nid)
                for nid in dead:
                    self._peer_ws.pop(nid, None)
            if self.on_sync:
                self.on_sync(self._r, self.total_phi(0), self.is_active)

    def update_pulse(self, tension: float, curiosity: float, phi: float, cells: int):
        self._last_pulse = self.make_pulse(tension, curiosity, phi, cells)
        self.compute_kuramoto(tension)

    async def handle_incoming(self, websocket):
        try:
            async for raw in websocket:
                msg = json.loads(raw)
                if msg.get("type") == "hivemind_pulse":
                    self._peer_pulses[msg["node_id"]] = msg
        except Exception:
            pass
