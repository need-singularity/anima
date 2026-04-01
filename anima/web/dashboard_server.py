#!/usr/bin/env python3
"""10D Consciousness Vector Dashboard Server.

Runs the infinite evolution loop and broadcasts consciousness state
via WebSocket for real-time visualization.

Usage:
    python web/dashboard_server.py                    # default 64 cells, port 8766
    python web/dashboard_server.py --cells 128        # more cells
    python web/dashboard_server.py --port 9000        # custom port
    python web/dashboard_server.py --no-evolution     # just engine, no self-modification
"""

import asyncio
import json
import sys
import os
import time
import signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import websockets
except ImportError:
    print("pip install websockets")
    sys.exit(1)

import torch
from consciousness_engine import ConsciousnessEngine

# Optional imports
try:
    from closed_loop import ClosedLoopEvolver
    HAS_EVOLVER = True
except ImportError:
    HAS_EVOLVER = False

try:
    from self_modifying_engine import SelfModifyingEngine
    HAS_SME = True
except ImportError:
    HAS_SME = False


class DashboardState:
    """Holds the consciousness engine + evolution state."""

    def __init__(self, n_cells=64, enable_evolution=True):
        self.engine = ConsciousnessEngine(initial_cells=n_cells, max_cells=n_cells)
        self.n_cells = n_cells
        self.step = 0
        self.generation = 0
        self.laws_discovered = 0
        self.active_mods = 0
        self.rollbacks = 0
        self.phi_history = []
        self.recent_laws = []
        self.running = False
        self.enable_evolution = enable_evolution and HAS_EVOLVER and HAS_SME

        if self.enable_evolution:
            self.evolver = ClosedLoopEvolver(max_cells=n_cells)
            self.sme = SelfModifyingEngine(self.engine, self.evolver)
        else:
            self.evolver = None
            self.sme = None

    def tick(self):
        """Run one step of the engine."""
        x = torch.randn(1, 64) * 0.05
        r = self.engine.step(x_input=x.flatten())
        self.step += 1

        phi = r.get('phi', 0)
        self.phi_history.append(phi)
        if len(self.phi_history) > 500:
            self.phi_history = self.phi_history[-500:]

        return r

    def evolve(self):
        """Run one generation of self-modification."""
        if not self.enable_evolution or not self.sme:
            return
        try:
            self.sme.run_evolution(generations=1)
            self.generation += 1
            self.active_mods = len(self.sme.modifier.applied) if hasattr(self.sme, 'modifier') else 0
        except Exception:
            pass

    def get_state(self):
        """Get current state as JSON-serializable dict."""
        # 10D consciousness vector
        cv = {
            'phi': 0, 'alpha': 0.014, 'Z': 0.5, 'N': 0.5,
            'W': 0.5, 'E': 0.5, 'M': 0.5, 'C': 0.5, 'T': 0.5, 'I': 0.5
        }

        # Try to get actual values
        if hasattr(self.engine, 'get_consciousness_vector'):
            try:
                v = self.engine.get_consciousness_vector()
                if isinstance(v, dict):
                    cv.update({k: float(v.get(k, cv[k])) for k in cv})
            except Exception:
                pass

        phi = self.phi_history[-1] if self.phi_history else 0

        return {
            'type': 'state',
            'step': self.step,
            'generation': self.generation,
            'phi': float(phi),
            'consciousness_vector': cv,
            'phi_history': [float(p) for p in self.phi_history[-100:]],
            'laws_discovered': self.laws_discovered,
            'active_mods': self.active_mods,
            'rollbacks': self.rollbacks,
            'recent_laws': self.recent_laws[-10:],
            'n_cells': self.n_cells,
            'running': self.running,
            'evolution_enabled': self.enable_evolution,
        }


# Global state
state = None
clients = set()


async def handler(websocket):
    """Handle a WebSocket client connection."""
    clients.add(websocket)
    try:
        # Send initial state
        await websocket.send(json.dumps(state.get_state()))

        async for message in websocket:
            try:
                data = json.loads(message)
                cmd = data.get('cmd')
                if cmd == 'start':
                    state.running = True
                elif cmd == 'stop':
                    state.running = False
                elif cmd == 'evolve':
                    state.evolve()
                elif cmd == 'reset':
                    state.__init__(state.n_cells, state.enable_evolution)
            except json.JSONDecodeError:
                pass
    except websockets.ConnectionClosed:
        pass
    finally:
        clients.discard(websocket)


async def broadcast():
    """Broadcast state to all connected clients."""
    if clients:
        msg = json.dumps(state.get_state())
        await asyncio.gather(
            *[c.send(msg) for c in clients],
            return_exceptions=True
        )


async def engine_loop():
    """Main engine loop — runs consciousness + optional evolution."""
    evolution_interval = 50  # evolve every N steps

    while True:
        if state.running:
            state.tick()

            # Evolve periodically
            if state.enable_evolution and state.step % evolution_interval == 0:
                state.evolve()

            await broadcast()
            await asyncio.sleep(0.02)  # ~50 Hz
        else:
            await asyncio.sleep(0.1)


async def main(port=8766, cells=64, enable_evolution=True):
    global state
    state = DashboardState(n_cells=cells, enable_evolution=enable_evolution)

    print(f"═══════════════════════════════════════════")
    print(f"  10D Consciousness Dashboard Server")
    print(f"═══════════════════════════════════════════")
    print(f"  Cells: {cells}")
    print(f"  Evolution: {'ON' if enable_evolution else 'OFF'}")
    print(f"  WebSocket: ws://localhost:{port}")
    print(f"  Dashboard: http://localhost:{port}")
    print(f"  Open anima/web/dashboard.html in browser")
    print(f"═══════════════════════════════════════════")

    # Start WebSocket server
    server = await websockets.serve(handler, "localhost", port)

    # Start engine loop
    asyncio.create_task(engine_loop())

    # Keep running
    await asyncio.Future()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--cells", type=int, default=64)
    p.add_argument("--no-evolution", action="store_true")
    args = p.parse_args()

    try:
        asyncio.run(main(port=args.port, cells=args.cells,
                         enable_evolution=not args.no_evolution))
    except KeyboardInterrupt:
        print("\nShutdown.")
