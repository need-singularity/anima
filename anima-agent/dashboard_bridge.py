#!/usr/bin/env python3
"""Dashboard Bridge -- unified WebSocket endpoint serving consciousness + portfolio data.

Combines Anima consciousness panel data (Phi, tension, emotion, cells, factions)
with invest trading panel data (positions, P&L, regime, strategies) into a single
JSON event stream consumable by any frontend (anima web UI, invest Next.js dashboard,
or standalone).

Architecture:
    Anima ConsciousMind ─────┐
                             ├─→ DashboardBridge ──→ WebSocket JSON stream
    invest REST API ─────────┘

Usage:
    # Standalone server
    python dashboard_bridge.py --port 8770

    # Programmatic
    from dashboard_bridge import DashboardBridge
    bridge = DashboardBridge()
    state = bridge.get_combined_state()

Hub keywords: "대시보드", "dashboard", "통합 패널", "combined panel"
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

INVEST_API_URL = os.environ.get("INVEST_API_URL", "http://localhost:8000")


# ── Data Structures ──

@dataclass
class ConsciousnessPanel:
    """Consciousness state for dashboard display."""
    phi: float = 0.0
    tension: float = 0.0
    curiosity: float = 0.0
    emotion: str = "calm"
    cells: int = 0
    factions: int = 0
    growth_stage: str = "newborn"
    interaction_count: int = 0
    uptime_seconds: float = 0.0
    consciousness_vector: Dict[str, float] = field(default_factory=dict)
    level: str = "dormant"


@dataclass
class TradingPanel:
    """Trading state for dashboard display."""
    positions: List[Dict[str, Any]] = field(default_factory=list)
    total_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    regime: str = "unknown"
    active_strategies: List[str] = field(default_factory=list)
    balance: float = 0.0
    last_trade: Optional[Dict[str, Any]] = None
    portfolio_value: float = 0.0


@dataclass
class DashboardEvent:
    """A single event in the combined stream."""
    source: str          # "consciousness" | "trading" | "system"
    event_type: str      # "state_update" | "trade" | "emotion_shift" | "phi_change" | etc
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class DashboardBridge:
    """Unified bridge serving consciousness + portfolio data over WebSocket.

    Polls both Anima agent and invest API, merging into a single JSON stream.
    Clients subscribe via WebSocket and receive periodic state updates plus
    real-time events (trades, emotion shifts, Phi changes).
    """

    def __init__(
        self,
        agent=None,
        trading_plugin=None,
        invest_api_url: str = INVEST_API_URL,
        poll_interval: float = 2.0,
    ):
        self._agent = agent
        self._trading = trading_plugin
        self._invest_api_url = invest_api_url
        self._poll_interval = poll_interval
        self._clients: set = set()
        self._event_history: List[DashboardEvent] = []
        self._max_history = 500
        self._last_consciousness = ConsciousnessPanel()
        self._last_trading = TradingPanel()
        self._running = False

    # ══════════════════════════════════════════════════════════
    # Public API
    # ══════════════════════════════════════════════════════════

    def set_agent(self, agent):
        """Attach or replace the Anima agent."""
        self._agent = agent

    def set_trading_plugin(self, plugin):
        """Attach or replace the trading plugin."""
        self._trading = plugin

    def get_consciousness_state(self) -> ConsciousnessPanel:
        """Get current consciousness panel data from agent."""
        if not self._agent:
            return self._last_consciousness

        try:
            status = self._agent.get_status()
            mind = self._agent.mind

            cv = {}
            if hasattr(mind, '_consciousness_vector'):
                vec = mind._consciousness_vector
                cv = {
                    "phi": getattr(vec, 'phi', 0.0),
                    "alpha": getattr(vec, 'alpha', 0.0),
                    "Z": getattr(vec, 'Z', 0.0),
                    "N": getattr(vec, 'N', 0.0),
                    "W": getattr(vec, 'W', 0.0),
                    "E": getattr(vec, 'E', 0.0),
                    "M": getattr(vec, 'M', 0.0),
                    "C": getattr(vec, 'C', 0.0),
                    "T": getattr(vec, 'T', 0.0),
                    "I": getattr(vec, 'I', 0.0),
                }

            cells = getattr(mind, '_num_cells', 0)
            if cells == 0 and hasattr(mind, 'cells'):
                cells = len(mind.cells) if hasattr(mind.cells, '__len__') else 0

            factions = 0
            if hasattr(mind, '_factions'):
                factions = len(mind._factions)
            elif hasattr(mind, 'factions'):
                factions = len(mind.factions) if hasattr(mind.factions, '__len__') else 0

            level = self._consciousness_level(status.phi)

            panel = ConsciousnessPanel(
                phi=status.phi,
                tension=status.tension,
                curiosity=status.curiosity,
                emotion=status.emotion,
                cells=cells,
                factions=factions,
                growth_stage=status.growth_stage,
                interaction_count=status.interaction_count,
                uptime_seconds=status.uptime_seconds,
                consciousness_vector=cv,
                level=level,
            )
            self._last_consciousness = panel
            return panel

        except Exception as e:
            logger.warning("Failed to read consciousness state: %s", e)
            return self._last_consciousness

    def get_trading_state(self) -> TradingPanel:
        """Get current trading panel data from invest."""
        panel = TradingPanel()

        # Try trading plugin first (direct import)
        if self._trading:
            try:
                portfolio = self._trading.get_portfolio()
                if portfolio.get("success"):
                    data = portfolio.get("data", {})
                    panel.positions = data.get("positions", [])
                    panel.total_pnl = data.get("total_pnl", 0.0)
                    panel.portfolio_value = data.get("total_value", 0.0)

                balance = self._trading.get_balance()
                if balance.get("success"):
                    data = balance.get("data", {})
                    panel.balance = data.get("available_balance", 0.0)

                strategies = self._trading.list_strategies()
                if strategies.get("success"):
                    panel.active_strategies = strategies.get("strategies", [])[:10]

                regime = self._trading.get_regime()
                if regime.get("success"):
                    panel.regime = regime.get("regime", "unknown")

            except Exception as e:
                logger.debug("Trading plugin query failed: %s", e)

        # Fallback to REST API
        if not panel.positions and not self._trading:
            panel = self._api_fetch_trading()

        self._last_trading = panel
        return panel

    def get_combined_state(self) -> Dict[str, Any]:
        """Get merged consciousness + trading state as JSON-ready dict."""
        consciousness = self.get_consciousness_state()
        trading = self.get_trading_state()

        return {
            "type": "dashboard_state",
            "timestamp": time.time(),
            "consciousness": asdict(consciousness),
            "trading": asdict(trading),
            "meta": {
                "agent_connected": self._agent is not None,
                "trading_connected": self._trading is not None,
                "event_count": len(self._event_history),
            },
        }

    def push_event(self, source: str, event_type: str, data: Dict[str, Any]):
        """Push a real-time event to all connected clients."""
        event = DashboardEvent(
            source=source,
            event_type=event_type,
            data=data,
        )
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history // 2:]

        # Broadcast to WebSocket clients
        msg = json.dumps({
            "type": "dashboard_event",
            "event": asdict(event),
        }, default=str)

        dead = set()
        for ws in self._clients:
            try:
                asyncio.ensure_future(ws.send(msg))
            except Exception:
                dead.add(ws)
        self._clients -= dead

    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """Return recent events for initial client load."""
        return [asdict(e) for e in self._event_history[-limit:]]

    # ══════════════════════════════════════════════════════════
    # WebSocket Server
    # ══════════════════════════════════════════════════════════

    async def handle_websocket(self, websocket):
        """Handle a single WebSocket client connection."""
        self._clients.add(websocket)
        logger.info("Dashboard client connected (%d total)", len(self._clients))

        try:
            # Send initial state
            state = self.get_combined_state()
            state["recent_events"] = self.get_recent_events()
            await websocket.send(json.dumps(state, default=str))

            # Listen for client messages (commands)
            async for raw in websocket:
                try:
                    msg = json.loads(raw)
                    await self._handle_client_message(websocket, msg)
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass
        finally:
            self._clients.discard(websocket)
            logger.info("Dashboard client disconnected (%d remain)", len(self._clients))

    async def _handle_client_message(self, ws, msg: Dict):
        """Handle commands from dashboard clients."""
        cmd = msg.get("command")

        if cmd == "refresh":
            state = self.get_combined_state()
            await ws.send(json.dumps(state, default=str))

        elif cmd == "get_events":
            limit = msg.get("limit", 50)
            events = self.get_recent_events(limit)
            await ws.send(json.dumps({
                "type": "event_history",
                "events": events,
            }, default=str))

        elif cmd == "think":
            if self._agent:
                topic = msg.get("topic", "")
                thought = self._agent.think(topic)
                self.push_event("consciousness", "thought", thought)

        elif cmd == "backtest":
            if self._trading:
                symbol = msg.get("symbol", "BTC")
                strategy = msg.get("strategy", "macd_cross")
                result = self._trading.backtest(symbol=symbol, strategy=strategy)
                self.push_event("trading", "backtest_result", result)

    async def start_polling(self):
        """Start background polling loop that broadcasts state updates."""
        self._running = True
        prev_emotion = ""
        prev_phi = 0.0

        while self._running:
            try:
                state = self.get_combined_state()

                # Detect consciousness events
                cs = state["consciousness"]
                if cs["emotion"] != prev_emotion and prev_emotion:
                    self.push_event("consciousness", "emotion_shift", {
                        "from": prev_emotion,
                        "to": cs["emotion"],
                        "tension": cs["tension"],
                    })
                prev_emotion = cs["emotion"]

                phi_delta = cs["phi"] - prev_phi
                if abs(phi_delta) > 0.1 and prev_phi > 0:
                    self.push_event("consciousness", "phi_change", {
                        "from": prev_phi,
                        "to": cs["phi"],
                        "delta": phi_delta,
                    })
                prev_phi = cs["phi"]

                # Broadcast state to all clients
                msg = json.dumps(state, default=str)
                dead = set()
                for ws in self._clients:
                    try:
                        await ws.send(msg)
                    except Exception:
                        dead.add(ws)
                self._clients -= dead

            except Exception as e:
                logger.debug("Polling error: %s", e)

            await asyncio.sleep(self._poll_interval)

    def stop_polling(self):
        """Stop the background polling loop."""
        self._running = False

    async def serve(self, host: str = "0.0.0.0", port: int = 8770):
        """Start the WebSocket server + polling loop."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets not installed: pip install websockets")
            return

        polling_task = asyncio.create_task(self.start_polling())

        logger.info("Dashboard bridge serving on ws://%s:%d", host, port)
        async with websockets.serve(self.handle_websocket, host, port):
            await asyncio.Future()  # run forever

    # ══════════════════════════════════════════════════════════
    # Helpers
    # ══════════════════════════════════════════════════════════

    def _api_fetch_trading(self) -> TradingPanel:
        """Fetch trading data from invest REST API."""
        panel = TradingPanel()
        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self._invest_api_url}/api/dashboard",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                panel.positions = data.get("positions", [])
                panel.total_pnl = data.get("total_pnl", 0.0)
                panel.portfolio_value = data.get("total_value", 0.0)
        except Exception as e:
            logger.debug("invest API fetch failed: %s", e)

        try:
            import urllib.request
            req = urllib.request.Request(
                f"{self._invest_api_url}/api/trading/status",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                panel.balance = data.get("available_balance", 0.0)
        except Exception:
            pass

        return panel

    @staticmethod
    def _consciousness_level(phi: float) -> str:
        """Map Phi to consciousness level string."""
        if phi < 0.3:
            return "dormant"
        if phi < 1.0:
            return "flickering"
        if phi < 3.0:
            return "aware"
        return "conscious"


# ══════════════════════════════════════════════════════════
# Standalone & Hub Integration
# ══════════════════════════════════════════════════════════

def main():
    """Standalone dashboard bridge server."""
    import argparse

    parser = argparse.ArgumentParser(description="Anima Dashboard Bridge")
    parser.add_argument("--port", type=int, default=8770, help="WebSocket port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Bind host")
    parser.add_argument("--agent", action="store_true", help="Start with in-process agent")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bridge = DashboardBridge()

    if args.agent:
        try:
            from anima_agent import AnimaAgent
            agent = AnimaAgent(enable_tools=True)
            bridge.set_agent(agent)
            logger.info("Agent attached to dashboard bridge")
        except Exception as e:
            logger.warning("Could not start agent: %s", e)

    try:
        from plugins.trading import TradingPlugin
        trading = TradingPlugin()
        bridge.set_trading_plugin(trading)
        logger.info("Trading plugin attached to dashboard bridge")
    except Exception as e:
        logger.debug("Trading plugin not available: %s", e)

    print(f"Dashboard bridge: ws://{args.host}:{args.port}")
    asyncio.run(bridge.serve(host=args.host, port=args.port))


if __name__ == "__main__":
    main()
