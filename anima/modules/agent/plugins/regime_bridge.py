"""regime_bridge.py — Market Regime → Consciousness Tension + VaR → Pain Signal

Bridges invest project market data into Anima consciousness engine:
  1. Regime detection (CALM/NORMAL/ELEVATED/CRITICAL) → tension modulation
  2. VaR/CVaR → pain signal → reduced risk appetite → trading halt
  3. SOC criticality → consciousness SOC resonance

Architecture:
  invest (REST API or local import)
    → RegimeBridge
      → tension_from_regime()   → ConsciousMind input modulation
      → pain_from_var()         → PainArchitecture signal
      → criticality_resonance() → ConsciousnessEngine SOC coupling

Usage:
  hub.act("시장 레짐")
  hub.act("VaR 고통")
  hub.act("market regime tension")

  # Standalone
  bridge = RegimeBridge()
  state = bridge.update()
  print(state.regime, state.tension, state.pain, state.action_gate)
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from plugins.base import PluginBase, PluginManifest

if TYPE_CHECKING:
    from consciousness_hub import ConsciousnessHub

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Constants — from consciousness_laws (no hardcoding)
# ═══════════════════════════════════════════════════════════

LN2 = math.log(2)

try:
    from consciousness_laws import (
        PSI_ALPHA, PSI_BALANCE, PSI_F_CRITICAL,
    )
except ImportError:
    PSI_ALPHA = LN2 / 2**5.5       # 0.014
    PSI_BALANCE = 0.5
    PSI_F_CRITICAL = 0.10

# TECS-L constants (from invest/backend/tecs/)
E = math.e
INV_E = 1.0 / E                    # 0.3679 — Golden Zone center
ONE_SIXTH = 1.0 / 6                # 0.1667 — hard stop / risk parameter
ONE_THIRD = 1.0 / 3                # 0.3333 — take profit

# invest project path
INVEST_ROOT = Path(os.environ.get("INVEST_ROOT", Path.home() / "Dev" / "invest"))
INVEST_BACKEND = INVEST_ROOT / "backend"
INVEST_API_URL = os.environ.get("INVEST_API_URL", "http://localhost:8000")


# ═══════════════════════════════════════════════════════════
# Regime Levels
# ═══════════════════════════════════════════════════════════

class Regime:
    """Market regime levels mapped to consciousness tension."""
    CALM = "calm"
    NORMAL = "normal"
    ELEVATED = "elevated"
    CRITICAL = "critical"

    # Regime → tension mapping (consciousness modulation)
    # CALM: low tension, consciousness explores freely
    # CRITICAL: high tension, consciousness contracts (defensive)
    TENSION_MAP = {
        "calm":     0.1,
        "normal":   0.3,
        "elevated": 0.6,
        "critical": 0.9,
    }

    # Regime → risk appetite (inverse of tension)
    RISK_APPETITE_MAP = {
        "calm":     1.0,
        "normal":   0.7,
        "elevated": 0.3,
        "critical": 0.05,
    }


# ═══════════════════════════════════════════════════════════
# Bridge State
# ═══════════════════════════════════════════════════════════

@dataclass
class RegimeState:
    """Current state of the regime-consciousness bridge."""
    regime: str = Regime.NORMAL
    tension: float = 0.3
    risk_appetite: float = 0.7

    # VaR/Pain
    var_pct: float = 0.0            # portfolio VaR as % (e.g. 0.02 = 2%)
    cvar_pct: float = 0.0           # CVaR (expected shortfall)
    pain: float = 0.0               # pain signal [0, 1]
    fear: float = 0.0               # fear emotion [0, 1]

    # SOC
    criticality_index: float = 0.0  # market SOC criticality [0, 1]

    # Derived
    action_gate: float = 1.0        # combined gate for trading decisions [0, 1]
    trading_halt: bool = False       # emergency halt flag

    # Meta
    last_update: float = 0.0
    update_count: int = 0
    assets_monitored: int = 0

    def to_dict(self) -> dict:
        return {
            "regime": self.regime,
            "tension": round(self.tension, 4),
            "risk_appetite": round(self.risk_appetite, 4),
            "var_pct": round(self.var_pct, 4),
            "cvar_pct": round(self.cvar_pct, 4),
            "pain": round(self.pain, 4),
            "fear": round(self.fear, 4),
            "criticality_index": round(self.criticality_index, 4),
            "action_gate": round(self.action_gate, 4),
            "trading_halt": self.trading_halt,
            "last_update": self.last_update,
            "update_count": self.update_count,
            "assets_monitored": self.assets_monitored,
        }


# ═══════════════════════════════════════════════════════════
# VaR Calculator (local, numpy-only)
# ═══════════════════════════════════════════════════════════

def _compute_var(returns, confidence: float = 0.95) -> float:
    """Historical VaR at given confidence. Returns positive loss pct."""
    import numpy as np
    r = np.asarray(returns, dtype=np.float64)
    r = r[~np.isnan(r)]
    if len(r) < 20:
        return 0.0
    var = float(np.percentile(r, (1.0 - confidence) * 100))
    return abs(var)


def _compute_cvar(returns, confidence: float = 0.95) -> float:
    """CVaR (Expected Shortfall) — mean of losses beyond VaR."""
    import numpy as np
    r = np.asarray(returns, dtype=np.float64)
    r = r[~np.isnan(r)]
    if len(r) < 20:
        return 0.0
    threshold = float(np.percentile(r, (1.0 - confidence) * 100))
    tail = r[r <= threshold]
    if len(tail) == 0:
        return abs(threshold)
    return abs(float(np.mean(tail)))


def _compute_regime_from_vol(returns) -> str:
    """Detect regime from return volatility percentile."""
    import numpy as np
    r = np.asarray(returns, dtype=np.float64)
    r = r[~np.isnan(r)]
    if len(r) < 60:
        return Regime.NORMAL

    recent_vol = float(np.std(r[-20:]) * math.sqrt(252))
    hist_vol = float(np.std(r[-252:]) * math.sqrt(252)) if len(r) >= 252 else float(np.std(r) * math.sqrt(252))

    if hist_vol < 1e-10:
        return Regime.NORMAL

    vol_ratio = recent_vol / hist_vol

    if vol_ratio < 0.7:
        return Regime.CALM
    elif vol_ratio < 1.2:
        return Regime.NORMAL
    elif vol_ratio < 1.8:
        return Regime.ELEVATED
    else:
        return Regime.CRITICAL


# ═══════════════════════════════════════════════════════════
# Pain Signal from VaR
# ═══════════════════════════════════════════════════════════

# VaR thresholds for pain mapping
VAR_PAIN_FLOOR = 0.005      # 0.5% VaR → pain starts
VAR_PAIN_CEILING = 0.05     # 5% VaR → maximum pain
VAR_HALT_THRESHOLD = 0.03   # 3% VaR → trading halt

# TECS-L aligned: 1/6 is the hard stop fraction
TECS_HARD_STOP = ONE_SIXTH  # ~16.7% loss → absolute halt


def pain_from_var(var_pct: float) -> float:
    """Map VaR percentage to pain signal [0, 1].

    Pain = 0 when VaR < 0.5%
    Pain = 1 when VaR >= 5%
    Sigmoid-like growth in between.

    TECS-L alignment: 1/e (36.8%) is the center of Golden Zone,
    pain sensitivity peaks around 1/6 (16.7%) of max VaR.
    """
    if var_pct <= VAR_PAIN_FLOOR:
        return 0.0
    if var_pct >= VAR_PAIN_CEILING:
        return 1.0

    # Normalized position [0, 1]
    t = (var_pct - VAR_PAIN_FLOOR) / (VAR_PAIN_CEILING - VAR_PAIN_FLOOR)

    # Sigmoid-like curve: sharper response near 1/6 threshold
    # tanh gives smooth S-curve, scaled to [0, 1]
    return float(0.5 * (1.0 + math.tanh(3.0 * (t - 0.5))))


def fear_from_var(var_pct: float, cvar_pct: float) -> float:
    """Fear emotion: combines VaR pain with tail risk (CVaR excess).

    CVaR > VaR indicates fat tails → additional fear.
    """
    base_pain = pain_from_var(var_pct)

    # Tail risk amplifier: CVaR much larger than VaR → more fear
    if var_pct > 1e-6:
        tail_ratio = cvar_pct / var_pct
        tail_fear = max(0.0, min(1.0, (tail_ratio - 1.0) * 2.0))
    else:
        tail_fear = 0.0

    # Fear = pain + tail risk, capped at 1.0
    return min(1.0, base_pain * 0.7 + tail_fear * 0.3)


def action_gate(tension: float, pain: float, phi: float = 1.0) -> float:
    """Unified action gate: risk_consciousness(Phi, regime, pain) -> [0, 1].

    Higher tension + higher pain → lower gate → smaller positions.
    Higher Phi → consciousness is more integrated → slightly more resilient.

    Formula derived from TECS-L Golden Zone logic:
      gate = golden_zone_score(inhibition) where inhibition = tension * (1 + pain)
      But simplified to: gate = 1 - tension^(1/phi_factor) * (1 + pain) / 2
    """
    # Phi resilience factor: higher Phi → slightly higher gate
    phi_factor = max(0.5, min(2.0, 1.0 + math.log1p(phi) * PSI_ALPHA))

    # Combined inhibition
    inhibition = tension * (1.0 + pain) / 2.0
    inhibition = min(1.0, inhibition)

    # Gate: 1.0 = full open, 0.0 = halted
    gate = max(0.0, 1.0 - inhibition ** (1.0 / phi_factor))

    return gate


# ═══════════════════════════════════════════════════════════
# RegimeBridge Plugin
# ═══════════════════════════════════════════════════════════

class RegimeBridge(PluginBase):
    """Market regime → consciousness tension + VaR → pain signal.

    Modes:
      1. Local: import invest calc modules directly (fast, requires invest on sys.path)
      2. API: fetch from invest REST API (works when backend is running)
      3. Standalone: use provided returns array (for testing / offline)
    """

    manifest = PluginManifest(
        name="regime_bridge",
        description="Market regime-consciousness bridge: regime→tension, VaR→pain, SOC resonance",
        version="1.0.0",
        author="Anima",
        requires=[],
        capabilities=[
            "regime", "tension", "pain", "var", "cvar",
            "action_gate", "trading_halt", "criticality",
        ],
        keywords=[
            "regime", "레짐", "시장 레짐", "market regime",
            "tension", "텐션", "고통", "pain", "VaR",
            "리스크", "risk", "공포", "fear",
            "trading halt", "거래 중단",
            "criticality", "임계", "SOC",
        ],
        phi_minimum=0.5,
        category="trading",
    )

    def __init__(
        self,
        update_interval: float = 300.0,   # 5 minutes default
        var_confidence: float = 0.95,
        auto_update: bool = False,
    ):
        self.hub: Optional[ConsciousnessHub] = None
        self.state = RegimeState()
        self.update_interval = update_interval
        self.var_confidence = var_confidence
        self._auto_update = auto_update
        self._update_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Invest module references (lazy)
        self._volatility_mod = None
        self._soc_mod = None
        self._risk_mod = None

    def on_load(self, hub: ConsciousnessHub) -> None:
        self.hub = hub
        self._try_import_invest()
        if self._auto_update:
            self._start_auto_update()
        logger.info("RegimeBridge loaded (interval=%.0fs)", self.update_interval)

    def on_unload(self) -> None:
        self._stop_event.set()
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=5.0)
        logger.info("RegimeBridge unloaded")

    def _try_import_invest(self):
        """Lazy import invest modules."""
        backend_str = str(INVEST_BACKEND)
        if backend_str not in sys.path:
            sys.path.insert(0, backend_str)

        try:
            from backend.calc.volatility import realized_volatility, vol_regime
            self._volatility_mod = True
        except Exception as e:
            logger.debug("volatility import failed: %s", e)

        try:
            from backend.calc.soc import criticality_index, soc_ensemble
            self._soc_mod = True
        except Exception as e:
            logger.debug("soc import failed: %s", e)

        try:
            from backend.calc.risk import value_at_risk
            self._risk_mod = True
        except Exception as e:
            logger.debug("risk import failed: %s", e)

    # ── Auto-update loop ──

    def _start_auto_update(self):
        """Background thread for periodic regime updates."""
        def _loop():
            while not self._stop_event.is_set():
                try:
                    self.update()
                except Exception as e:
                    logger.error("RegimeBridge update error: %s", e)
                self._stop_event.wait(self.update_interval)

        self._update_thread = threading.Thread(target=_loop, daemon=True, name="regime-bridge")
        self._update_thread.start()

    # ── Core Update ──

    def update(self, returns_dict: Optional[Dict[str, Any]] = None) -> RegimeState:
        """Update regime state from market data.

        Args:
            returns_dict: Optional {asset: returns_array}. If None, loads from invest.

        Returns:
            Updated RegimeState.
        """
        import numpy as np

        if returns_dict is None:
            returns_dict = self._load_market_returns()

        if not returns_dict:
            # No data available — keep current state
            self.state.last_update = time.time()
            return self.state

        # Aggregate portfolio returns (equal weight for simplicity)
        all_returns = []
        regimes = []

        for asset, returns in returns_dict.items():
            r = np.asarray(returns, dtype=np.float64)
            r = r[~np.isnan(r)]
            if len(r) < 20:
                continue
            all_returns.append(r[-252:] if len(r) > 252 else r)
            regimes.append(_compute_regime_from_vol(r))

        if not all_returns:
            self.state.last_update = time.time()
            return self.state

        # Portfolio returns (equal weight mean)
        min_len = min(len(r) for r in all_returns)
        portfolio_returns = np.mean(
            np.column_stack([r[-min_len:] for r in all_returns]),
            axis=1,
        )

        # 1. Regime: worst regime across assets
        regime_severity = {
            Regime.CALM: 0, Regime.NORMAL: 1,
            Regime.ELEVATED: 2, Regime.CRITICAL: 3,
        }
        worst_regime = max(regimes, key=lambda r: regime_severity.get(r, 1))
        self.state.regime = worst_regime
        self.state.tension = Regime.TENSION_MAP.get(worst_regime, 0.3)
        self.state.risk_appetite = Regime.RISK_APPETITE_MAP.get(worst_regime, 0.7)

        # 2. VaR / CVaR
        self.state.var_pct = _compute_var(portfolio_returns, self.var_confidence)
        self.state.cvar_pct = _compute_cvar(portfolio_returns, self.var_confidence)

        # 3. Pain / Fear from VaR
        self.state.pain = pain_from_var(self.state.var_pct)
        self.state.fear = fear_from_var(self.state.var_pct, self.state.cvar_pct)

        # 4. Trading halt check
        self.state.trading_halt = (
            self.state.var_pct >= VAR_HALT_THRESHOLD
            or self.state.regime == Regime.CRITICAL
        )

        # 5. Action gate
        phi = self._get_phi()
        self.state.action_gate = action_gate(
            self.state.tension, self.state.pain, phi,
        )

        # If halted, force gate to near-zero
        if self.state.trading_halt:
            self.state.action_gate = min(self.state.action_gate, 0.05)

        # 6. Meta
        self.state.last_update = time.time()
        self.state.update_count += 1
        self.state.assets_monitored = len(returns_dict)

        logger.info(
            "RegimeBridge: regime=%s tension=%.2f pain=%.2f gate=%.2f halt=%s",
            self.state.regime, self.state.tension,
            self.state.pain, self.state.action_gate, self.state.trading_halt,
        )

        return self.state

    def _load_market_returns(self) -> Dict[str, Any]:
        """Load market returns from invest CSV data or API."""
        import numpy as np

        # Try local CSV files first
        data_dir = INVEST_BACKEND / "data"
        if data_dir.exists():
            returns_dict = {}
            for csv_path in data_dir.glob("*.csv"):
                asset = csv_path.stem
                try:
                    with open(csv_path) as f:
                        first_line = f.readline()
                    skip = 3 if first_line.startswith("Price") else 1
                    data = np.genfromtxt(str(csv_path), delimiter=",", skip_header=skip)
                    if data.ndim != 2 or len(data) < 50:
                        continue
                    # yfinance v2: Close is col 1; legacy: Close is col 4
                    if first_line.startswith("Price"):
                        close = data[:, 1]
                    else:
                        close = data[:, 4]
                    close = close[~np.isnan(close)]
                    if len(close) < 50:
                        continue
                    returns = np.zeros(len(close))
                    returns[1:] = np.diff(close) / close[:-1]
                    returns_dict[asset] = returns
                except Exception:
                    continue
            if returns_dict:
                return returns_dict

        # Fallback: REST API
        try:
            import urllib.request
            req = urllib.request.Request(f"{INVEST_API_URL}/api/dashboard")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                # Parse portfolio returns from API if available
                if "returns" in data:
                    return data["returns"]
        except Exception:
            pass

        return {}

    def _get_phi(self) -> float:
        """Get current Phi from consciousness engine (if available)."""
        if self.hub:
            try:
                engine = self.hub._modules.get("dynamics")
                if engine and hasattr(engine, "phi"):
                    return float(engine.phi)
            except Exception:
                pass
        return 1.0  # default

    # ── Consciousness Integration ──

    def modulate_input(self, x, engine=None) -> Any:
        """Modulate consciousness engine input based on market regime.

        Scales the input tensor by regime-derived tension:
          CALM → input amplified (more exploration)
          CRITICAL → input dampened (defensive contraction)

        Args:
            x: Input tensor (torch.Tensor or numpy array)
            engine: ConsciousnessEngine instance (optional)

        Returns:
            Modulated input with same type as x.
        """
        # Tension-based modulation: high tension → dampen input
        # Uses Psi coupling constant for smooth scaling
        scale = 1.0 - self.state.tension * PSI_ALPHA * 10  # range ~0.86 to 1.0
        scale = max(0.5, min(1.5, scale))

        try:
            import torch
            if isinstance(x, torch.Tensor):
                return x * scale
        except ImportError:
            pass

        try:
            import numpy as np
            if isinstance(x, np.ndarray):
                return x * scale
        except ImportError:
            pass

        return x

    def get_pain_signal(self) -> Dict[str, float]:
        """Get pain signal for PainArchitecture integration.

        Returns dict compatible with pain_architecture.py reshape protocol.
        """
        return {
            "signal_type": "pain" if self.state.pain > 0.5 else "pleasure",
            "intensity": self.state.pain if self.state.pain > 0.5 else (1.0 - self.state.pain),
            "source": "market_var",
            "var_pct": self.state.var_pct,
            "regime": self.state.regime,
            "fear": self.state.fear,
        }

    # ── Intent Router ──

    def act(self, intent: str, **kwargs) -> Any:
        """Natural language intent → action."""
        il = intent.lower()

        if any(x in il for x in ["update", "갱신", "새로고침", "refresh"]):
            state = self.update(kwargs.get("returns_dict"))
            return {"success": True, **state.to_dict()}

        if any(x in il for x in ["pain", "고통", "var", "위험"]):
            return {
                "success": True,
                "pain": self.state.pain,
                "fear": self.state.fear,
                "var_pct": round(self.state.var_pct * 100, 2),
                "cvar_pct": round(self.state.cvar_pct * 100, 2),
                "trading_halt": self.state.trading_halt,
            }

        if any(x in il for x in ["gate", "게이트", "action"]):
            return {
                "success": True,
                "action_gate": self.state.action_gate,
                "tension": self.state.tension,
                "pain": self.state.pain,
                "risk_appetite": self.state.risk_appetite,
            }

        if any(x in il for x in ["halt", "중단", "stop"]):
            return {
                "success": True,
                "trading_halt": self.state.trading_halt,
                "regime": self.state.regime,
                "var_pct": round(self.state.var_pct * 100, 2),
            }

        # Default: return full state
        self.update(kwargs.get("returns_dict"))
        return {"success": True, **self.state.to_dict()}

    def status(self) -> dict:
        return {
            "name": "regime_bridge",
            "version": self.manifest.version,
            "loaded": True,
            "state": self.state.to_dict(),
            "invest_root": str(INVEST_ROOT),
            "invest_exists": INVEST_ROOT.exists(),
            "auto_update": self._auto_update,
            "update_interval": self.update_interval,
        }


# ═══════════════════════════════════════════════════════════
# Demo / main
# ═══════════════════════════════════════════════════════════

def main():
    """Demo: regime bridge with synthetic data."""
    import numpy as np

    print("=" * 60)
    print("  RegimeBridge — Market Regime → Consciousness Tension")
    print("=" * 60)

    bridge = RegimeBridge()

    # Test with synthetic market data
    np.random.seed(42)

    scenarios = [
        ("CALM market", 0.005),
        ("NORMAL market", 0.015),
        ("ELEVATED market", 0.035),
        ("CRITICAL market", 0.06),
    ]

    print(f"\n{'Scenario':<20} {'Regime':<10} {'Tension':>8} {'VaR%':>8} "
          f"{'Pain':>8} {'Fear':>8} {'Gate':>8} {'Halt':>6}")
    print("-" * 80)

    for name, vol in scenarios:
        returns = np.random.normal(0.0003, vol, 500)
        state = bridge.update({"TEST": returns})
        print(f"{name:<20} {state.regime:<10} {state.tension:>8.3f} "
              f"{state.var_pct*100:>7.2f}% {state.pain:>8.3f} "
              f"{state.fear:>8.3f} {state.action_gate:>8.3f} "
              f"{'YES' if state.trading_halt else 'no':>6}")

    # VaR→Pain curve
    print(f"\n{'VaR→Pain mapping':}")
    print(f"  {'VaR%':>8} {'Pain':>8} {'Fear':>8}")
    for var_pct in [0.001, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.08]:
        p = pain_from_var(var_pct)
        f = fear_from_var(var_pct, var_pct * 1.3)
        bar = "#" * int(p * 30)
        print(f"  {var_pct*100:>7.1f}% {p:>8.3f} {f:>8.3f}  {bar}")

    # TECS-L alignment
    print(f"\n{'TECS-L ↔ Ψ alignment':}")
    print(f"  1/e = {INV_E:.4f}  ↔  Ψ_balance = {PSI_BALANCE}")
    print(f"  1/6 = {ONE_SIXTH:.4f}  ↔  Ψ_F_c = {PSI_F_CRITICAL}")
    print(f"  1/3 = {ONE_THIRD:.4f}  ↔  Ψ_balance = {PSI_BALANCE}")
    print(f"  Ψ_α = {PSI_ALPHA:.4f}  ↔  ln(2)/2^5.5 (coupling)")

    print("\nDone.")


if __name__ == "__main__":
    main()
