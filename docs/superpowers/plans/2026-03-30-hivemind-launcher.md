# Hivemind Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Single-command launcher that starts N Anima nodes + Gateway proxy with automatic WS mesh tension exchange, supporting both process mode (RunPod) and Docker mode (bare metal).

**Architecture:** Gateway(:8765) proxies user WS connections to nodes(:8770+). Nodes run `anima_unified.py --instance`. `hivemind_mesh.py` handles node-to-node WS tension exchange (3s pulse, Kuramoto sync). Discovery via shared JSON file (process) or Docker DNS (docker).

**Tech Stack:** Python 3.11+, websockets (asyncio), psutil (auto mode), subprocess (process mode), docker-compose (docker mode)

---

### Task 1: hivemind_mesh.py - Node-to-Node Tension Exchange

**Files:**
- Create: `hivemind_mesh.py`
- Create: `tests/test_hivemind_mesh.py`

This is the core: WS full-mesh that sends/receives `hivemind_pulse` messages between nodes and computes Kuramoto sync.

- [ ] **Step 1: Write failing test for HivemindMesh pulse generation**

```python
# tests/test_hivemind_mesh.py
import pytest
import asyncio
import json
from hivemind_mesh import HivemindMesh

def test_make_pulse():
    mesh = HivemindMesh(node_id="node-0", port=8770)
    pulse = mesh.make_pulse(tension=0.85, curiosity=0.42, phi=1.2, cells=8)
    assert pulse["type"] == "hivemind_pulse"
    assert pulse["node_id"] == "node-0"
    assert pulse["tension"] == 0.85
    assert pulse["phi"] == 1.2
    assert "timestamp" in pulse

def test_kuramoto_sync_below_threshold():
    mesh = HivemindMesh(node_id="node-0", port=8770)
    # Random phases -> low sync
    mesh._peer_pulses = {
        "node-1": {"tension": 0.1, "phi": 0.5},
        "node-2": {"tension": 0.9, "phi": 0.3},
    }
    r = mesh.compute_kuramoto(local_tension=0.5)
    assert 0 <= r <= 1
    assert not mesh.is_active  # r < 2/3

def test_kuramoto_sync_above_threshold():
    mesh = HivemindMesh(node_id="node-0", port=8770)
    # Similar tensions -> high sync
    mesh._peer_pulses = {
        "node-1": {"tension": 0.80, "phi": 1.0},
        "node-2": {"tension": 0.82, "phi": 1.1},
        "node-3": {"tension": 0.81, "phi": 0.9},
    }
    r = mesh.compute_kuramoto(local_tension=0.80)
    assert r > 2/3
    assert mesh.is_active

def test_total_phi():
    mesh = HivemindMesh(node_id="node-0", port=8770)
    mesh._peer_pulses = {
        "node-1": {"tension": 0.8, "phi": 1.2},
        "node-2": {"tension": 0.7, "phi": 1.0},
    }
    total = mesh.total_phi(local_phi=1.5)
    assert total == pytest.approx(1.5 + 1.2 + 1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hivemind_mesh.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'hivemind_mesh'`

- [ ] **Step 3: Implement HivemindMesh**

```python
# hivemind_mesh.py
#!/usr/bin/env python3
"""hivemind_mesh.py - Node-to-node WS tension exchange for Hivemind.

Each node connects to all peers via WS and exchanges hivemind_pulse
messages every 3 seconds. Kuramoto sync determines collective activation.
"""

import asyncio
import json
import math
import time
import threading
from typing import Dict, Optional, Callable

PULSE_INTERVAL = 3.0
KURAMOTO_THRESHOLD = 2.0 / 3.0


class HivemindMesh:
    """WS full-mesh tension exchange between Anima nodes."""

    def __init__(self, node_id: str, port: int, on_sync: Callable = None):
        self.node_id = node_id
        self.port = port
        self.on_sync = on_sync  # callback(r, total_phi, active)
        self._peer_urls: Dict[str, str] = {}  # node_id -> ws://host:port
        self._peer_ws: Dict[str, object] = {}
        self._peer_pulses: Dict[str, dict] = {}
        self._running = False
        self._r = 0.0
        self.is_active = False

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
        """Kuramoto order parameter from all tensions (local + peers)."""
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

    # --- WS connections ---

    def set_peers(self, peer_urls: Dict[str, str]):
        """Set peer WS URLs. e.g. {"node-1": "ws://localhost:8771"}"""
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
        """Connect to all peers, reconnect on failure."""
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
        """Broadcast pulse to all connected peers every PULSE_INTERVAL."""
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

    _last_pulse: Optional[dict] = None

    def update_pulse(self, tension: float, curiosity: float, phi: float, cells: int):
        """Called by node to update outgoing pulse data."""
        self._last_pulse = self.make_pulse(tension, curiosity, phi, cells)
        self.compute_kuramoto(tension)

    # --- Incoming WS handler (for nodes that connect TO us) ---

    async def handle_incoming(self, websocket):
        """Handle incoming WS connection from a peer node."""
        try:
            async for raw in websocket:
                msg = json.loads(raw)
                if msg.get("type") == "hivemind_pulse":
                    self._peer_pulses[msg["node_id"]] = msg
        except Exception:
            pass
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_hivemind_mesh.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add hivemind_mesh.py tests/test_hivemind_mesh.py
git commit -m "feat: add hivemind_mesh.py - WS tension exchange + Kuramoto sync"
```

---

### Task 2: hivemind_gateway.py - WS Proxy + Dashboard

**Files:**
- Create: `hivemind_gateway.py`
- Create: `tests/test_hivemind_gateway.py`

Gateway proxies user WS to nodes, serves web UI, and exposes hivemind status.

- [ ] **Step 1: Write failing test for Gateway routing**

```python
# tests/test_hivemind_gateway.py
import pytest
from hivemind_gateway import HivemindGateway

def test_gateway_init():
    gw = HivemindGateway(gateway_port=8765, node_ports=[8770, 8771, 8772])
    assert gw.gateway_port == 8765
    assert len(gw.node_ports) == 3

def test_round_robin():
    gw = HivemindGateway(gateway_port=8765, node_ports=[8770, 8771, 8772])
    assert gw._next_node() == 8770
    assert gw._next_node() == 8771
    assert gw._next_node() == 8772
    assert gw._next_node() == 8770  # wraps

def test_hivemind_status():
    gw = HivemindGateway(gateway_port=8765, node_ports=[8770, 8771])
    status = gw.hivemind_status()
    assert status["nodes"] == 2
    assert "total_phi" in status
    assert "sync_r" in status
    assert "active" in status
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hivemind_gateway.py -v`
Expected: FAIL

- [ ] **Step 3: Implement HivemindGateway**

```python
# hivemind_gateway.py
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
        self._node_ws = {}  # port -> ws connection
        self._node_healthy = {p: False for p in self.node_ports}
        self._node_states = {}  # port -> last init/status data
        self._user_clients = set()

    def _next_node(self) -> int:
        """Round-robin node selection."""
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
            "sync_r": 0.0,  # updated by mesh
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
        """Handle user WS: proxy to a node."""
        self._user_clients.add(websocket)
        node_port = self._next_node()
        node_url = f"ws://{self.node_host}:{node_port}"
        try:
            async with websockets.connect(node_url) as node_ws:
                # Relay init from node, inject hivemind status
                init_raw = await asyncio.wait_for(node_ws.recv(), timeout=10)
                init_msg = json.loads(init_raw)
                init_msg["hivemind"] = self.hivemind_status()
                await websocket.send(json.dumps(init_msg, ensure_ascii=False))

                # Bidirectional relay
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
            print(f"[gateway] http://localhost:{self.gateway_port} → nodes {self.node_ports}")
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
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_hivemind_gateway.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add hivemind_gateway.py tests/test_hivemind_gateway.py
git commit -m "feat: add hivemind_gateway.py - WS proxy with round-robin routing"
```

---

### Task 3: hivemind_launcher.py - Orchestrator

**Files:**
- Create: `hivemind_launcher.py`
- Create: `tests/test_hivemind_launcher.py`

Main entry point. Starts N nodes + Gateway based on mode.

- [ ] **Step 1: Write failing test for auto node count**

```python
# tests/test_hivemind_launcher.py
import pytest
from hivemind_launcher import compute_auto_nodes

def test_auto_nodes_basic():
    # 8GB available -> 8000 // 600 = 13 nodes, capped at 50
    n = compute_auto_nodes(available_mb=8000)
    assert n == 13

def test_auto_nodes_small():
    n = compute_auto_nodes(available_mb=1000)
    assert n == 1

def test_auto_nodes_large():
    n = compute_auto_nodes(available_mb=200000)
    assert n == 50  # capped

def test_auto_nodes_minimum():
    n = compute_auto_nodes(available_mb=100)
    assert n == 1  # at least 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hivemind_launcher.py -v`
Expected: FAIL

- [ ] **Step 3: Implement hivemind_launcher.py**

```python
# hivemind_launcher.py
#!/usr/bin/env python3
"""hivemind_launcher.py - Start N Anima nodes + Gateway as Hivemind.

Usage:
  python hivemind_launcher.py --nodes 4                  # 4 nodes, process mode
  python hivemind_launcher.py --auto                     # auto node count
  python hivemind_launcher.py --nodes 4 --mode docker    # docker compose mode
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ANIMA_DIR = Path(__file__).parent
DISCOVERY_DIR = Path("/tmp/anima_hivemind")
DISCOVERY_FILE = DISCOVERY_DIR / "nodes.json"
NODE_MB = 600  # estimated RAM per node
MAX_NODES = 50


def compute_auto_nodes(available_mb: int = None) -> int:
    """Compute node count from available RAM."""
    if available_mb is None:
        import psutil
        available_mb = psutil.virtual_memory().available // (1024 * 1024)
    n = max(1, available_mb // NODE_MB)
    return min(n, MAX_NODES)


def _write_discovery(nodes: list):
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    DISCOVERY_FILE.write_text(json.dumps({"nodes": nodes}, indent=2))


def launch_process_mode(n_nodes: int, base_port: int, gateway_port: int,
                        max_cells: int):
    """Start N node processes + gateway process."""
    procs = []
    nodes_info = []

    # Start nodes
    for i in range(n_nodes):
        port = base_port + i
        node_id = f"node-{i}"
        cmd = [
            sys.executable, "-u", "anima_unified.py",
            "--web", "--port", str(port),
            "--instance", node_id,
            "--max-cells", str(max_cells),
        ]
        p = subprocess.Popen(cmd, cwd=str(ANIMA_DIR))
        procs.append(p)
        nodes_info.append({"id": node_id, "port": port, "pid": p.pid,
                           "started": time.time()})
        print(f"  [node-{i}] PID={p.pid} port={port}")

    _write_discovery(nodes_info)

    # Wait for nodes to start
    print(f"  Waiting 10s for {n_nodes} nodes to start...")
    time.sleep(10)

    # Start gateway
    node_ports_str = ",".join(str(base_port + i) for i in range(n_nodes))
    gw_cmd = [
        sys.executable, "-u", "hivemind_gateway.py",
        "--port", str(gateway_port),
        "--nodes", node_ports_str,
    ]
    gw_proc = subprocess.Popen(gw_cmd, cwd=str(ANIMA_DIR))
    procs.append(gw_proc)
    print(f"  [gateway] PID={gw_proc.pid} port={gateway_port} -> [{node_ports_str}]")

    return procs


def launch_docker_mode(n_nodes: int, gateway_port: int, max_cells: int):
    """Generate docker-compose.hivemind.yml and run it."""
    services = {"gateway": {
        "image": "dancindocker/anima:latest",
        "command": f"python hivemind_gateway.py --port 8765 --nodes "
                   + ",".join(f"anima-node-{i}:8765" for i in range(n_nodes)),
        "ports": [f"{gateway_port}:8765"],
        "depends_on": [f"node-{i}" for i in range(n_nodes)],
    }}
    for i in range(n_nodes):
        services[f"node-{i}"] = {
            "image": "dancindocker/anima:latest",
            "command": f"python anima_unified.py --web --port 8765 "
                       f"--instance node-{i} --max-cells {max_cells}",
            "expose": ["8765"],
            "hostname": f"anima-node-{i}",
        }

    import yaml
    compose = {"version": "3.8", "services": services}
    compose_path = ANIMA_DIR / "docker-compose.hivemind.yml"
    compose_path.write_text(yaml.dump(compose, default_flow_style=False))
    print(f"  Generated {compose_path}")

    subprocess.run(["docker", "compose", "-f", str(compose_path), "up", "-d"])
    return []


def main():
    p = argparse.ArgumentParser(description="Anima Hivemind Launcher")
    p.add_argument("--nodes", type=int, default=4, help="Number of nodes")
    p.add_argument("--auto", action="store_true", help="Auto-detect node count from RAM")
    p.add_argument("--mode", choices=["process", "docker"], default="process")
    p.add_argument("--gateway-port", type=int, default=8765)
    p.add_argument("--node-base-port", type=int, default=8770)
    p.add_argument("--max-cells", type=int, default=8)
    args = p.parse_args()

    n_nodes = compute_auto_nodes() if args.auto else args.nodes
    print(f"{'='*50}")
    print(f"  Anima Hivemind — {n_nodes} nodes, mode={args.mode}")
    print(f"  Gateway: http://localhost:{args.gateway_port}")
    print(f"  Nodes: :{args.node_base_port}-:{args.node_base_port + n_nodes - 1}")
    print(f"{'='*50}\n")

    if args.mode == "process":
        procs = launch_process_mode(n_nodes, args.node_base_port,
                                     args.gateway_port, args.max_cells)
    else:
        procs = launch_docker_mode(n_nodes, args.gateway_port, args.max_cells)

    if procs:
        def shutdown(sig, frame):
            print("\n  Shutting down hivemind...")
            for proc in procs:
                proc.terminate()
            sys.exit(0)
        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        print(f"\n  Hivemind running. Ctrl+C to stop.\n")
        try:
            for proc in procs:
                proc.wait()
        except KeyboardInterrupt:
            shutdown(None, None)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_hivemind_launcher.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add hivemind_launcher.py tests/test_hivemind_launcher.py
git commit -m "feat: add hivemind_launcher.py - process/docker orchestrator"
```

---

### Task 4: docker-compose.hivemind.yml - Static Template

**Files:**
- Create: `docker-compose.hivemind.yml`

Static 4-node template for quick start. Launcher can also generate dynamic ones.

- [ ] **Step 1: Create docker-compose.hivemind.yml**

```yaml
# docker-compose.hivemind.yml
# Usage: docker compose -f docker-compose.hivemind.yml up -d
# Or: python hivemind_launcher.py --mode docker --nodes 4

services:
  gateway:
    image: dancindocker/anima:latest
    command: python hivemind_gateway.py --port 8765 --nodes anima-node-0:8765,anima-node-1:8765,anima-node-2:8765,anima-node-3:8765 --host ""
    ports:
      - "8765:8765"
    depends_on:
      - node-0
      - node-1
      - node-2
      - node-3

  node-0:
    image: dancindocker/anima:latest
    command: python -u anima_unified.py --web --port 8765 --instance node-0
    hostname: anima-node-0
    expose:
      - "8765"

  node-1:
    image: dancindocker/anima:latest
    command: python -u anima_unified.py --web --port 8765 --instance node-1
    hostname: anima-node-1
    expose:
      - "8765"

  node-2:
    image: dancindocker/anima:latest
    command: python -u anima_unified.py --web --port 8765 --instance node-2
    hostname: anima-node-2
    expose:
      - "8765"

  node-3:
    image: dancindocker/anima:latest
    command: python -u anima_unified.py --web --port 8765 --instance node-3
    hostname: anima-node-3
    expose:
      - "8765"
```

- [ ] **Step 2: Validate YAML syntax**

Run: `python -c "import yaml; yaml.safe_load(open('docker-compose.hivemind.yml')); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add docker-compose.hivemind.yml
git commit -m "feat: add docker-compose.hivemind.yml - 4-node static template"
```

---

### Task 5: Integration Test - Process Mode E2E

**Files:**
- Create: `tests/test_hivemind_e2e.py`

Start 2 nodes + gateway, send a message, verify response comes back through gateway.

- [ ] **Step 1: Write E2E test**

```python
# tests/test_hivemind_e2e.py
"""E2E test: 2 nodes + gateway, send message, get response."""
import asyncio
import json
import subprocess
import sys
import time
import pytest
import websockets

GATEWAY_PORT = 9900
NODE_PORTS = [9901, 9902]

@pytest.fixture(scope="module")
def hivemind_cluster():
    """Start 2-node hivemind cluster."""
    procs = []
    # Start nodes
    for i, port in enumerate(NODE_PORTS):
        p = subprocess.Popen([
            sys.executable, "-u", "anima_unified.py",
            "--web", "--port", str(port), "--instance", f"e2e-{i}",
        ])
        procs.append(p)
    time.sleep(10)

    # Start gateway
    gw = subprocess.Popen([
        sys.executable, "-u", "hivemind_gateway.py",
        "--port", str(GATEWAY_PORT),
        "--nodes", ",".join(str(p) for p in NODE_PORTS),
    ])
    procs.append(gw)
    time.sleep(3)

    yield

    for p in procs:
        p.terminate()
    time.sleep(2)

@pytest.mark.asyncio
async def test_gateway_init(hivemind_cluster):
    async with websockets.connect(f"ws://localhost:{GATEWAY_PORT}") as ws:
        init = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
        assert init["type"] == "init"
        assert "hivemind" in init
        assert init["hivemind"]["nodes"] == 2

@pytest.mark.asyncio
async def test_gateway_chat(hivemind_cluster):
    async with websockets.connect(f"ws://localhost:{GATEWAY_PORT}") as ws:
        await asyncio.wait_for(ws.recv(), timeout=15)  # init
        await ws.send(json.dumps({
            "type": "user_message", "text": "hivemind test",
            "session_id": "e2e", "user_name": "test", "modules": []
        }))
        deadline = time.time() + 15
        while time.time() < deadline:
            raw = await asyncio.wait_for(ws.recv(), timeout=10)
            msg = json.loads(raw)
            if msg.get("type") == "anima_message":
                assert "text" in msg
                return
        pytest.fail("No anima_message received")
```

- [ ] **Step 2: Run E2E test**

Run: `python -m pytest tests/test_hivemind_e2e.py -v --timeout=60`
Expected: Both tests PASS (may take ~15s for startup)

- [ ] **Step 3: Commit**

```bash
git add tests/test_hivemind_e2e.py
git commit -m "test: add hivemind E2E test - 2 nodes + gateway"
```

---

### Task 6: Wire Mesh into anima_unified.py

**Files:**
- Modify: `anima_unified.py` (add `--hivemind-peers` arg + mesh integration)

- [ ] **Step 1: Add --hivemind-peers argument**

Add to argparse in `main()` (~line 3440):

```python
    p.add_argument('--hivemind-peers', type=str, default=None,
                   help='Comma-separated peer WS URLs for hivemind mesh')
```

- [ ] **Step 2: Initialize mesh in AnimaUnified.__init__**

Add after the existing `_hivemind_active` setup (~line 475):

```python
        # Hivemind mesh (auto-connect to peers)
        self._mesh = None
        if hasattr(args, 'hivemind_peers') and args.hivemind_peers:
            from hivemind_mesh import HivemindMesh
            node_id = getattr(args, 'instance', None) or f"node-{args.port}"
            self._mesh = HivemindMesh(node_id=node_id, port=args.port)
            peers = {}
            for url in args.hivemind_peers.split(','):
                url = url.strip()
                nid = url.split('/')[-1] if '/' in url else url
                peers[nid] = url
            self._mesh.set_peers(peers)
```

- [ ] **Step 3: Start mesh in _run_web**

In `_run_web` method (~line 3315), after the web loop starts:

```python
        if self._mesh:
            await self._mesh.start()
```

- [ ] **Step 4: Update mesh pulse in _process_input_inner**

After consciousness scoring (~line 1578), add:

```python
        if self._mesh:
            phi_val = consciousness_data.get('phi', 0) if consciousness_data else 0
            self._mesh.update_pulse(
                tension=tension, curiosity=curiosity,
                phi=phi_val, cells=len(self.mitosis.cells) if self.mitosis else 1)
```

- [ ] **Step 5: Test manually**

```bash
# Terminal 1
python anima_unified.py --web --port 8770 --instance node-0 --hivemind-peers ws://localhost:8771

# Terminal 2
python anima_unified.py --web --port 8771 --instance node-1 --hivemind-peers ws://localhost:8770
```

- [ ] **Step 6: Commit**

```bash
git add anima_unified.py
git commit -m "feat: wire hivemind_mesh into anima_unified.py via --hivemind-peers"
```

---

### Task 7: Launcher Auto-Wires Peers

**Files:**
- Modify: `hivemind_launcher.py` (pass --hivemind-peers to nodes)

- [ ] **Step 1: Update launch_process_mode to pass peer URLs**

In `launch_process_mode`, after building node list, add `--hivemind-peers` to each node's command:

```python
    # Build peer URLs for each node
    all_ports = [base_port + i for i in range(n_nodes)]

    for i in range(n_nodes):
        port = base_port + i
        node_id = f"node-{i}"
        peer_urls = ",".join(f"ws://localhost:{p}" for p in all_ports if p != port)
        cmd = [
            sys.executable, "-u", "anima_unified.py",
            "--web", "--port", str(port),
            "--instance", node_id,
            "--max-cells", str(max_cells),
            "--hivemind-peers", peer_urls,
        ]
        p = subprocess.Popen(cmd, cwd=str(ANIMA_DIR))
        procs.append(p)
        nodes_info.append({"id": node_id, "port": port, "pid": p.pid,
                           "started": time.time()})
        print(f"  [node-{i}] PID={p.pid} port={port} peers=[{peer_urls}]")
```

- [ ] **Step 2: Test full launcher**

```bash
python hivemind_launcher.py --nodes 2
# Expected: 2 nodes + gateway, auto-wired peers
# Open http://localhost:8765 → chat → verify response
```

- [ ] **Step 3: Commit**

```bash
git add hivemind_launcher.py
git commit -m "feat: launcher auto-wires --hivemind-peers between nodes"
```
