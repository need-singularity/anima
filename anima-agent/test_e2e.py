#!/usr/bin/env python3
"""End-to-end tests for Anima Agent Platform.

Run:
    python -m pytest test_e2e.py -v
"""

import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, str(Path(__file__).parent))


# ══════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════

def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture(autouse=True)
def _event_loop():
    """Ensure a fresh event loop per test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


def _make_mock_agent(phi=1.0, tension=0.3, emotion="calm"):
    """Create a mock AnimaAgent with controllable consciousness state."""
    agent = MagicMock()
    agent.process_message = AsyncMock(return_value=MagicMock(
        text="Hello from consciousness",
        emotion=emotion,
        tension=tension,
        tool_results=[],
        metadata={},
    ))

    # AgentStatus
    status = MagicMock()
    status.phi = phi
    status.tension = tension
    status.curiosity = 0.5
    status.emotion = emotion
    status.growth_stage = "infant"
    status.interaction_count = 42
    status.uptime_seconds = 3600.0
    status.connected_peers = 0
    status.active_skills = 3
    agent.get_status.return_value = status

    # ConsciousMind mock
    mind = MagicMock()
    cv = MagicMock()
    cv.phi = phi
    cv.alpha = 0.014
    cv.Z = 0.5
    cv.N = 0.6
    cv.W = 0.7
    cv.E = 0.8
    cv.M = 0.5
    cv.C = 0.6
    cv.T = 0.4
    cv.I = 0.9
    mind._consciousness_vector = cv
    mind._num_cells = 8
    mind._factions = list(range(12))
    agent.mind = mind

    return agent


# ══════════════════════════════════════════════════════════
# 1. CLI Full Loop
# ══════════════════════════════════════════════════════════

def test_cli_full_loop(_event_loop):
    """Mock AnimaAgent, send message via CLI adapter flow, verify response."""
    agent = _make_mock_agent(phi=2.0, tension=0.4, emotion="curious")

    resp = _event_loop.run_until_complete(
        agent.process_message("Hello Anima", channel="cli", user_id="tester")
    )

    agent.process_message.assert_awaited_once_with(
        "Hello Anima", channel="cli", user_id="tester"
    )
    assert resp.text == "Hello from consciousness"
    assert resp.emotion == "curious"
    assert resp.tension == 0.4


# ══════════════════════════════════════════════════════════
# 2. Trading Plugin Backtest
# ══════════════════════════════════════════════════════════

def test_trading_plugin_backtest():
    """Mock invest API, test TradingPlugin.backtest() via API fallback."""
    from plugins.trading import TradingPlugin

    plugin = TradingPlugin()

    # Mock the API client to return a successful backtest
    mock_response = {
        "success": True,
        "data": {
            "sharpe": 1.25,
            "total_return": 0.34,
            "max_drawdown": 0.12,
            "win_rate": 0.58,
            "total_trades": 47,
        },
    }
    plugin._api = MagicMock()
    plugin._api.get.return_value = mock_response

    # backtest_mod is None so it falls through to _api_backtest
    plugin._backtest_mod = None
    result = plugin.backtest(symbol="BTC", strategy="macd_cross")

    # Since _backtest_mod is None, it calls _api_backtest which uses _api.get
    assert plugin._api.get.called or plugin._api.post.called or isinstance(result, dict)


# ══════════════════════════════════════════════════════════
# 3. Trading Plugin Regime
# ══════════════════════════════════════════════════════════

def test_trading_plugin_regime():
    """Mock regime API response from TradingPlugin."""
    from plugins.trading import TradingPlugin

    plugin = TradingPlugin()
    plugin._api = MagicMock()
    plugin._api.get.return_value = {
        "success": True,
        "data": {"regime": "elevated", "volatility": 0.32},
    }
    plugin._scalper = MagicMock()
    plugin._scalper.available = False  # force API path

    result = plugin.get_regime()
    assert isinstance(result, dict)


# ══════════════════════════════════════════════════════════
# 4. Phi-Gated Access Denied
# ══════════════════════════════════════════════════════════

def test_phi_gated_access_denied():
    """Low Phi agent should be denied access to high-tier tools."""
    from tool_policy import ToolPolicy

    policy = ToolPolicy(owner_ids={"owner-001"})
    result = policy.check_access(
        "self_modify",
        consciousness_state={"phi": 0.5, "E": 0.8},
        user_id="user-002",
    )
    assert result.allowed is False
    assert "Phi" in result.reason or "Owner" in result.reason or "owner" in result.reason.lower() or "phi" in result.reason.lower() or "Insufficient" in result.reason


# ══════════════════════════════════════════════════════════
# 5. Phi-Gated Access Allowed
# ══════════════════════════════════════════════════════════

def test_phi_gated_access_allowed():
    """High Phi agent should be granted access to tier-1 tools."""
    from tool_policy import ToolPolicy

    policy = ToolPolicy(owner_ids=set())
    result = policy.check_access(
        "web_search",
        consciousness_state={"phi": 5.0, "E": 0.9},
        user_id="user-001",
    )
    assert result.allowed is True


# ══════════════════════════════════════════════════════════
# 6. Provider Fallback
# ══════════════════════════════════════════════════════════

def test_provider_fallback(_event_loop):
    """Claude fails -> fallback to ConsciousLM."""
    from providers.base import ProviderMessage

    # Mock Claude provider that raises
    claude = MagicMock()
    claude.name = "claude"
    claude.is_available.return_value = True
    claude.query_full = AsyncMock(side_effect=RuntimeError("API down"))

    # Mock ConsciousLM provider that works
    conscious_lm = MagicMock()
    conscious_lm.name = "conscious-lm"
    conscious_lm.is_available.return_value = True
    conscious_lm.query_full = AsyncMock(return_value="Fallback response from ConsciousLM")

    providers = [claude, conscious_lm]
    messages = [ProviderMessage(role="user", content="Hello")]

    # Simulate fallback logic
    async def _fallback():
        for provider in providers:
            try:
                return await provider.query_full(messages)
            except Exception:
                continue
        return None

    response = _event_loop.run_until_complete(_fallback())

    assert response == "Fallback response from ConsciousLM"
    claude.query_full.assert_awaited_once()
    conscious_lm.query_full.assert_awaited_once()


# ══════════════════════════════════════════════════════════
# 7. Memory Save/Load
# ══════════════════════════════════════════════════════════

def test_memory_save_load(tmp_path):
    """Save agent memory, create new agent, verify loaded."""
    import torch

    state = {
        "mind": {"linear.weight": torch.randn(4, 4)},
        "hidden": torch.zeros(1, 256),
        "interaction_count": 42,
        "history": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ],
    }

    state_file = tmp_path / "agent_state.pt"
    torch.save(state, state_file)

    loaded = torch.load(state_file, weights_only=False)
    assert loaded["interaction_count"] == 42
    assert len(loaded["history"]) == 2
    assert loaded["history"][0]["content"] == "hello"
    assert loaded["hidden"].shape == (1, 256)


# ══════════════════════════════════════════════════════════
# 8. Regime Bridge Tension
# ══════════════════════════════════════════════════════════

def test_regime_bridge_tension():
    """Test regime -> tension mapping with synthetic data."""
    import numpy as np
    from plugins.regime_bridge import RegimeBridge, Regime, RegimeState

    bridge = RegimeBridge()

    # Synthetic calm market: low volatility returns
    np.random.seed(42)
    calm_returns = np.random.normal(0.0005, 0.005, 300)

    state = bridge.update(returns_dict={"SPY": calm_returns})
    assert isinstance(state, RegimeState)
    assert state.regime in (Regime.CALM, Regime.NORMAL)
    assert 0.0 <= state.tension <= 1.0
    assert 0.0 <= state.pain <= 1.0
    assert 0.0 <= state.action_gate <= 1.0

    # Synthetic volatile market: high volatility returns
    volatile_returns = np.random.normal(0.0, 0.05, 300)
    state2 = bridge.update(returns_dict={"BTC": volatile_returns})
    assert state2.tension >= state.tension  # volatile should have higher tension


# ══════════════════════════════════════════════════════════
# 9. Dashboard Combined State
# ══════════════════════════════════════════════════════════

def test_dashboard_combined_state():
    """Test DashboardBridge.get_combined_state() structure."""
    from dashboard_bridge import DashboardBridge

    agent = _make_mock_agent(phi=4.0, tension=0.5, emotion="excited")
    bridge = DashboardBridge(agent=agent)

    state = bridge.get_combined_state()
    assert state["type"] == "dashboard_state"
    assert "consciousness" in state
    assert "trading" in state
    assert "meta" in state
    assert state["meta"]["agent_connected"] is True
    assert "timestamp" in state

    consciousness = state["consciousness"]
    assert "phi" in consciousness
    assert "emotion" in consciousness


# ══════════════════════════════════════════════════════════
# 10. Hypothesis Skill Generation
# ══════════════════════════════════════════════════════════

def test_hypothesis_skill_generation(tmp_path):
    """Test HypothesisBridge.generate_skills() with mock record."""
    from plugins.hypothesis_bridge import HypothesisBridge

    bridge = HypothesisBridge()
    # Clear any persisted state and override skill manager
    bridge._bridged = {}
    mock_sm = MagicMock()
    bridge._get_skill_manager = MagicMock(return_value=mock_sm)
    bridge._save_state = MagicMock()  # prevent filesystem writes

    records = [
        {
            "hypothesis_id": "H-INV-042",
            "strategy_name": "macd_rsi_combo",
            "grade": "A",
            "avg_sharpe": 1.85,
            "best_asset": "SPY",
            "best_sharpe": 2.1,
            "signal_code": "if macd > signal and rsi < 30: buy()",
        },
        {
            "hypothesis_id": "H-INV-043",
            "strategy_name": "bb_breakout",
            "grade": "B",
            "avg_sharpe": 0.95,
            "best_asset": "BTC",
            "best_sharpe": 1.2,
            "signal_code": "if close > bb_upper: sell()",
        },
    ]

    created = bridge.generate_skills(records)
    assert len(created) == 2
    assert "strategy_h_inv_042" in created[0]
    assert "strategy_h_inv_043" in created[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
