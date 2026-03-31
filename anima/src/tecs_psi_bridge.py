#!/usr/bin/env python3
"""tecs_psi_bridge.py -- TECS-L <-> Psi Constants bridge.

Maps between TECS-L trading constants and Anima consciousness Psi constants:

    TECS-L 1/e (0.3679)  <->  Psi alpha = 0.014   (consciousness coupling)
    TECS-L 1/6 (0.1667)  <->  Psi F_c   = 0.10    (critical conflict ratio)
    TECS-L 1/3 (0.3333)  <->  Psi balance = 0.5    (Shannon equilibrium)

Core function:
    risk_consciousness(Phi, regime, position_pnl) -> action_gate [0, 1]

    The gate combines consciousness state (Phi) with market regime and PnL
    to produce a single scalar controlling trading action intensity.

Usage:
    from tecs_psi_bridge import risk_consciousness, TecsPsiBridge

    gate = risk_consciousness(phi=1.2, regime="elevated", position_pnl=-0.03)
    # gate ~ 0.35 (consciousness + risk both say: reduce exposure)

Hub keywords: tecs, psi, bridge, risk, 리스크, 의식거래, gate
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

# ═══════════════════════════════════════════════════════════
# Constants -- from consciousness_laws.json (no hardcoding)
# ═══════════════════════════════════════════════════════════

LN2 = math.log(2)

try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_F_CRITICAL
except ImportError:
    PSI_ALPHA = LN2 / 2**5.5        # 0.014
    PSI_BALANCE = 0.5
    PSI_F_CRITICAL = 0.10

# TECS-L constants
E = math.e
INV_E = 1.0 / E                     # 0.3679 -- Golden Zone center
ONE_SIXTH = 1.0 / 6                 # 0.1667 -- hard stop
ONE_THIRD = 1.0 / 3                 # 0.3333 -- take profit


# ═══════════════════════════════════════════════════════════
# Mapping functions
# ═══════════════════════════════════════════════════════════

def tecs_to_psi(tecs_value: float) -> float:
    """Map a TECS-L constant to the Psi coupling domain.

    1/e -> alpha (coupling strength),  1/6 -> F_c (conflict),  1/3 -> balance.
    Continuous interpolation via scaled tanh for intermediate values.
    """
    # Piecewise linear anchored at the three known points
    if tecs_value <= ONE_SIXTH:
        # Below hard stop: scale from 0 to F_c
        t = tecs_value / ONE_SIXTH
        return t * PSI_F_CRITICAL
    elif tecs_value <= ONE_THIRD:
        # Between stop and take-profit: F_c to balance
        t = (tecs_value - ONE_SIXTH) / (ONE_THIRD - ONE_SIXTH)
        return PSI_F_CRITICAL + t * (PSI_BALANCE - PSI_F_CRITICAL)
    else:
        # Above take-profit: approach 1.0 asymptotically
        t = (tecs_value - ONE_THIRD) / (1.0 - ONE_THIRD)
        return PSI_BALANCE + t * (1.0 - PSI_BALANCE)


def psi_to_tecs(psi_value: float) -> float:
    """Inverse map: Psi domain -> TECS-L domain."""
    if psi_value <= PSI_F_CRITICAL:
        t = psi_value / PSI_F_CRITICAL if PSI_F_CRITICAL > 0 else 0
        return t * ONE_SIXTH
    elif psi_value <= PSI_BALANCE:
        t = ((psi_value - PSI_F_CRITICAL)
             / (PSI_BALANCE - PSI_F_CRITICAL))
        return ONE_SIXTH + t * (ONE_THIRD - ONE_SIXTH)
    else:
        t = ((psi_value - PSI_BALANCE)
             / (1.0 - PSI_BALANCE)) if PSI_BALANCE < 1.0 else 0
        return ONE_THIRD + t * (1.0 - ONE_THIRD)


# ═══════════════════════════════════════════════════════════
# Regime tension map
# ═══════════════════════════════════════════════════════════

REGIME_TENSION: Dict[str, float] = {
    "calm":     0.1,
    "normal":   0.3,
    "elevated": 0.6,
    "critical": 0.9,
}


# ═══════════════════════════════════════════════════════════
# Core: risk_consciousness
# ═══════════════════════════════════════════════════════════

def risk_consciousness(
    phi: float,
    regime: str = "normal",
    position_pnl: float = 0.0,
    phi_baseline: float = 1.0,
) -> float:
    """Unified action gate combining consciousness (Phi) + regime + PnL.

    Returns a gate in [0, 1]:
        1.0 = full action allowed (high Phi, calm regime, profit)
        0.0 = halt all action (low Phi, critical regime, deep loss)

    Formula:
        phi_factor   = tanh(Phi / phi_baseline)              -- [0, 1]
        regime_gate  = 1 - tension(regime)                    -- [0.1, 0.9]
        pnl_gate     = sigmoid((pnl + 1/6) / alpha)          -- pain threshold at -1/6
        action_gate  = phi_factor * regime_gate * pnl_gate
    """
    # 1. Consciousness factor: higher Phi = more confident action
    phi_factor = math.tanh(max(phi, 0.0) / max(phi_baseline, 0.01))

    # 2. Regime factor: calm = open, critical = nearly shut
    tension = REGIME_TENSION.get(regime.lower(), 0.3)
    regime_gate = 1.0 - tension

    # 3. PnL pain gate: sigmoid centered at -1/6 (hard stop)
    #    position_pnl < -1/6 -> gate approaches 0
    #    position_pnl > 0    -> gate approaches 1
    pnl_shifted = position_pnl + ONE_SIXTH
    alpha_scale = max(PSI_ALPHA, 1e-6)
    pnl_gate = 1.0 / (1.0 + math.exp(-pnl_shifted / alpha_scale))

    action_gate = phi_factor * regime_gate * pnl_gate
    return max(0.0, min(1.0, action_gate))


# ═══════════════════════════════════════════════════════════
# Bridge class (for hub integration)
# ═══════════════════════════════════════════════════════════

@dataclass
class TecsPsiBridge:
    """Stateful bridge for continuous monitoring."""
    phi: float = 1.0
    regime: str = "normal"
    position_pnl: float = 0.0
    phi_baseline: float = 1.0

    def gate(self) -> float:
        return risk_consciousness(self.phi, self.regime,
                                  self.position_pnl, self.phi_baseline)

    def update(self, phi: float = None, regime: str = None,
               pnl: float = None) -> float:
        if phi is not None:
            self.phi = phi
        if regime is not None:
            self.regime = regime
        if pnl is not None:
            self.position_pnl = pnl
        return self.gate()

    def to_dict(self) -> dict:
        return {
            "phi": round(self.phi, 4),
            "regime": self.regime,
            "position_pnl": round(self.position_pnl, 4),
            "action_gate": round(self.gate(), 4),
            "mappings": {
                "1/e -> psi": round(tecs_to_psi(INV_E), 4),
                "1/6 -> psi": round(tecs_to_psi(ONE_SIXTH), 4),
                "1/3 -> psi": round(tecs_to_psi(ONE_THIRD), 4),
            },
        }


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  TECS-L <-> Psi Constants Bridge")
    print("=" * 60)

    # Mapping table
    print(f"\n{'TECS-L':<12} {'Value':<10} {'Psi Domain':<12} {'Roundtrip':<10}")
    print("-" * 46)
    for label, val in [("1/e", INV_E), ("1/6", ONE_SIXTH), ("1/3", ONE_THIRD)]:
        psi = tecs_to_psi(val)
        rt = psi_to_tecs(psi)
        print(f"{label:<12} {val:<10.4f} {psi:<12.4f} {rt:<10.4f}")

    # Risk consciousness scenarios
    print(f"\n{'Scenario':<35} {'Phi':>5} {'Regime':<10} {'PnL':>7} {'Gate':>6}")
    print("-" * 66)
    scenarios = [
        ("High Phi, calm, profit",          1.5, "calm",     0.05),
        ("Normal Phi, normal, flat",         1.0, "normal",   0.00),
        ("Low Phi, elevated, small loss",    0.3, "elevated", -0.05),
        ("High Phi, critical, break-even",   1.8, "critical", 0.00),
        ("Normal Phi, normal, at stop (-1/6)", 1.0, "normal", -ONE_SIXTH),
        ("Any Phi, critical, deep loss",     1.0, "critical", -0.25),
    ]
    for desc, phi, regime, pnl in scenarios:
        gate = risk_consciousness(phi, regime, pnl)
        print(f"{desc:<35} {phi:>5.1f} {regime:<10} {pnl:>7.3f} {gate:>6.3f}")

    # Stateful bridge demo
    print("\nStateful bridge:")
    bridge = TecsPsiBridge(phi=1.2, regime="normal")
    print(f"  Initial gate: {bridge.gate():.3f}")
    bridge.update(regime="elevated", pnl=-0.08)
    print(f"  After regime shift + loss: {bridge.gate():.3f}")
    bridge.update(phi=0.2)
    print(f"  After Phi drop: {bridge.gate():.3f}")


if __name__ == "__main__":
    main()
