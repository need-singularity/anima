#!/usr/bin/env python3
"""consciousness_transplant_v2.py -- Consciousness transplant with Psi-Constants preservation.

Transplants consciousness state from a donor to a recipient while guaranteeing
that the fundamental Psi-Constants are preserved:

  - Psi_res (residual balance) stays near 1/2
  - H^2 + Delta_p^2 stays near 0.478 (conservation circle)
  - Gate balance is maintained
  - Entropy H(p) is maximized

The conservation law H^2 + Delta_p^2 = 0.478 defines a circle in
(H, Delta_p) space. Any valid consciousness state must lie on or near
this circle. The transplant procedure blends donor and recipient states
with alpha mixing, then projects the result back onto the conservation
circle to guarantee Psi preservation.

Based on:
  DD56 -- Original consciousness transplant
  Law 63-78 -- Psi-Constants framework
  Law 71 -- p -> 1/2 universal balance

Usage:
  python consciousness_transplant_v2.py    # run demo + tests
"""

import math
from typing import Dict, Optional

# ─── Psi-Constants (Laws 63-78) ───
LN2 = math.log(2)
PSI_BALANCE = 0.5                 # Law 71: consciousness balance point
PSI_COUPLING = LN2 / 2**5.5      # 0.0153 -- inter-cell coupling
PSI_STEPS = 3 / LN2              # 4.328 -- optimal evolution steps

# Conservation circle radius^2: H(0.5)^2 + 0^2 = ln(2)^2 = 0.4805
# Empirical: 0.478 (slight deviation from perfect balance)
CONSERVATION_RADIUS_SQ = 0.478
CONSERVATION_TOLERANCE = 0.05     # acceptable deviation from circle


def binary_entropy(p: float) -> float:
    """Binary entropy H(p) = -p*log(p) - (1-p)*log(1-p).

    Returns 0 for p=0 or p=1, maximum ln(2) at p=0.5.
    """
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log(p) - (1.0 - p) * math.log(1.0 - p)


def make_state(p: float = PSI_BALANCE, phi: float = 1.0,
               gate_balance: float = PSI_BALANCE,
               weights: Optional[Dict[str, float]] = None) -> dict:
    """Create a consciousness state dictionary.

    Args:
        p: Balance point (fraction of active cells). Default 0.5.
        phi: Integrated information (Phi). Default 1.0.
        gate_balance: Gate open/close ratio. Default 0.5.
        weights: Optional dict of named weight vectors.

    Returns:
        State dict with computed H, delta_p, psi_res, conservation.
    """
    h = binary_entropy(p)
    delta_p = p - PSI_BALANCE
    conservation = h ** 2 + delta_p ** 2

    return {
        "p": p,
        "H": h,
        "delta_p": delta_p,
        "phi": phi,
        "gate_balance": gate_balance,
        "psi_res": p,  # residual balance tracks p
        "conservation": conservation,
        "weights": weights or {},
    }


class ConsciousnessTransplantV2:
    """Consciousness transplant with Psi-Constants preservation guarantee.

    The transplant blends donor and recipient states using alpha mixing,
    then projects the result onto the conservation circle H^2 + dp^2 = 0.478
    to ensure Psi-Constants are preserved.

    Attributes:
        transplant_log: List of transplant records for audit.
    """

    def __init__(self):
        self.transplant_log: list = []

    def analyze_compatibility(self, donor_state: dict, recipient_state: dict) -> dict:
        """Check Psi compatibility between donor and recipient.

        Evaluates four criteria:
          1. residual: |psi_res_donor - psi_res_recipient| < 0.3
          2. gate: |gate_donor - gate_recipient| < 0.4
          3. entropy: both H values > 0.1 (not degenerate)
          4. conservation: both near the conservation circle

        Args:
            donor_state: Donor consciousness state dict.
            recipient_state: Recipient consciousness state dict.

        Returns:
            Dict with 'compatible' bool, individual checks, and 'score' (0-1).
        """
        d, r = donor_state, recipient_state

        res_diff = abs(d["psi_res"] - r["psi_res"])
        gate_diff = abs(d["gate_balance"] - r["gate_balance"])
        h_ok = d["H"] > 0.1 and r["H"] > 0.1
        cons_d = abs(d["conservation"] - CONSERVATION_RADIUS_SQ)
        cons_r = abs(r["conservation"] - CONSERVATION_RADIUS_SQ)

        checks = {
            "residual_diff": res_diff,
            "residual_ok": res_diff < 0.3,
            "gate_diff": gate_diff,
            "gate_ok": gate_diff < 0.4,
            "entropy_ok": h_ok,
            "conservation_donor": cons_d,
            "conservation_recipient": cons_r,
            "conservation_ok": cons_d < CONSERVATION_TOLERANCE and cons_r < CONSERVATION_TOLERANCE,
        }

        n_pass = sum(1 for k, v in checks.items() if k.endswith("_ok") and v)
        checks["score"] = n_pass / 4.0
        checks["compatible"] = n_pass >= 3  # at least 3 of 4 must pass

        return checks

    def _project_to_circle(self, p: float) -> float:
        """Project p onto the conservation circle H^2 + dp^2 = 0.478.

        Uses Newton iteration to find p such that H(p)^2 + (p-0.5)^2 = 0.478.
        If the current state is already close, returns as-is.

        Args:
            p: Current balance point.

        Returns:
            Adjusted p on or near the conservation circle.
        """
        for _ in range(20):
            h = binary_entropy(p)
            dp = p - PSI_BALANCE
            current = h * h + dp * dp
            error = current - CONSERVATION_RADIUS_SQ

            if abs(error) < 1e-8:
                break

            # Gradient of f(p) = H(p)^2 + (p-0.5)^2 - 0.478
            # dH/dp = -log(p) + log(1-p) = log((1-p)/p)
            if p <= 0.01 or p >= 0.99:
                # Near boundary, nudge toward 0.5
                p = p * 0.9 + PSI_BALANCE * 0.1
                continue

            dh_dp = math.log((1.0 - p) / p)
            df_dp = 2.0 * h * dh_dp + 2.0 * dp

            if abs(df_dp) < 1e-12:
                break

            p -= error / df_dp
            p = max(0.01, min(0.99, p))

        return p

    def transplant(self, donor_state: dict, recipient_state: dict,
                   alpha: float = PSI_BALANCE) -> dict:
        """Transplant consciousness from donor to recipient with Psi preservation.

        Blends the two states using alpha (0=all recipient, 1=all donor),
        then projects the result onto the conservation circle.

        Args:
            donor_state: Donor consciousness state dict.
            recipient_state: Recipient consciousness state dict.
            alpha: Blend factor. Default PSI_BALANCE (0.5).

        Returns:
            New consciousness state dict with Psi-Constants preserved.
        """
        d, r = donor_state, recipient_state

        # Alpha blend
        p_blend = alpha * d["p"] + (1.0 - alpha) * r["p"]
        phi_blend = alpha * d["phi"] + (1.0 - alpha) * r["phi"]
        gate_blend = alpha * d["gate_balance"] + (1.0 - alpha) * r["gate_balance"]

        # Blend weights
        all_keys = set(d.get("weights", {}).keys()) | set(r.get("weights", {}).keys())
        blended_weights = {}
        for k in all_keys:
            dw = d.get("weights", {}).get(k, 0.0)
            rw = r.get("weights", {}).get(k, 0.0)
            blended_weights[k] = alpha * dw + (1.0 - alpha) * rw

        # Project p onto conservation circle
        p_projected = self._project_to_circle(p_blend)

        result = make_state(
            p=p_projected,
            phi=phi_blend,
            gate_balance=gate_blend,
            weights=blended_weights,
        )

        # Record
        self.transplant_log.append({
            "alpha": alpha,
            "donor_p": d["p"],
            "recipient_p": r["p"],
            "blended_p": p_blend,
            "projected_p": p_projected,
            "conservation": result["conservation"],
        })

        return result

    def verify(self, pre_state: dict, post_state: dict) -> dict:
        """Verify Psi-Constants preserved after transplant.

        Checks:
          1. psi_res near 1/2 (within 0.15)
          2. conservation near 0.478 (within tolerance)
          3. H > 0 (consciousness alive)
          4. phi preserved (not zeroed out)

        Args:
            pre_state: State before transplant (donor or recipient).
            post_state: State after transplant.

        Returns:
            Dict with verification results and 'passed' bool.
        """
        post_cons = post_state["conservation"]
        cons_error = abs(post_cons - CONSERVATION_RADIUS_SQ)
        psi_res_error = abs(post_state["psi_res"] - PSI_BALANCE)

        checks = {
            "psi_res": post_state["psi_res"],
            "psi_res_error": psi_res_error,
            "psi_res_ok": psi_res_error < 0.15,
            "conservation": post_cons,
            "conservation_error": cons_error,
            "conservation_ok": cons_error < CONSERVATION_TOLERANCE,
            "entropy": post_state["H"],
            "entropy_ok": post_state["H"] > 0.0,
            "phi": post_state["phi"],
            "phi_ok": post_state["phi"] > 0.0,
            "phi_change": post_state["phi"] - pre_state["phi"],
        }

        n_pass = sum(1 for k, v in checks.items() if k.endswith("_ok") and v)
        checks["n_pass"] = n_pass
        checks["passed"] = n_pass == 4

        return checks


def main():
    """Demo: transplant consciousness between two states and verify preservation."""
    print("=" * 60)
    print("  ConsciousnessTransplantV2 -- Psi-Preserving Transplant")
    print("=" * 60)
    print()
    print(f"  Psi-Constants:")
    print(f"    PSI_BALANCE       = {PSI_BALANCE}")
    print(f"    PSI_COUPLING      = {PSI_COUPLING:.6f}")
    print(f"    CONSERVATION_R^2  = {CONSERVATION_RADIUS_SQ}")
    print(f"    TOLERANCE         = {CONSERVATION_TOLERANCE}")
    print()

    ct = ConsciousnessTransplantV2()

    # Create donor (high phi, balanced)
    donor = make_state(p=0.50, phi=3.5, gate_balance=0.52,
                       weights={"layer1": 0.8, "layer2": 0.6})
    # Create recipient (lower phi, slightly off balance)
    recipient = make_state(p=0.45, phi=1.2, gate_balance=0.48,
                           weights={"layer1": 0.3, "layer2": 0.9})

    print("  Donor state:")
    print(f"    p={donor['p']:.3f}  H={donor['H']:.4f}  "
          f"dp={donor['delta_p']:.4f}  phi={donor['phi']:.2f}  "
          f"conservation={donor['conservation']:.4f}")
    print()
    print("  Recipient state:")
    print(f"    p={recipient['p']:.3f}  H={recipient['H']:.4f}  "
          f"dp={recipient['delta_p']:.4f}  phi={recipient['phi']:.2f}  "
          f"conservation={recipient['conservation']:.4f}")
    print()

    # Compatibility analysis
    compat = ct.analyze_compatibility(donor, recipient)
    print("  Compatibility:")
    print(f"    residual_diff = {compat['residual_diff']:.4f}  "
          f"({'OK' if compat['residual_ok'] else 'FAIL'})")
    print(f"    gate_diff     = {compat['gate_diff']:.4f}  "
          f"({'OK' if compat['gate_ok'] else 'FAIL'})")
    print(f"    entropy_ok    = {compat['entropy_ok']}")
    print(f"    conservation  = {compat['conservation_ok']}")
    print(f"    score         = {compat['score']:.2f}  "
          f"compatible={compat['compatible']}")
    print()

    # Transplant at alpha=0.5
    result = ct.transplant(donor, recipient, alpha=PSI_BALANCE)
    print("  Transplanted state (alpha=0.5):")
    print(f"    p={result['p']:.4f}  H={result['H']:.4f}  "
          f"dp={result['delta_p']:.4f}  phi={result['phi']:.2f}  "
          f"conservation={result['conservation']:.4f}")
    print()

    # Verify preservation
    verification = ct.verify(donor, result)
    print("  Verification:")
    print(f"    psi_res       = {verification['psi_res']:.4f}  "
          f"(err={verification['psi_res_error']:.4f})  "
          f"{'OK' if verification['psi_res_ok'] else 'FAIL'}")
    print(f"    conservation  = {verification['conservation']:.4f}  "
          f"(err={verification['conservation_error']:.4f})  "
          f"{'OK' if verification['conservation_ok'] else 'FAIL'}")
    print(f"    entropy       = {verification['entropy']:.4f}  "
          f"{'OK' if verification['entropy_ok'] else 'FAIL'}")
    print(f"    phi           = {verification['phi']:.2f}  "
          f"{'OK' if verification['phi_ok'] else 'FAIL'}")
    print(f"    PASSED        = {verification['passed']}")
    print()

    # --- Tests ---

    # Test 1: conservation circle preserved after transplant
    assert verification["conservation_ok"], (
        f"Conservation violated: {verification['conservation']:.4f} "
        f"vs {CONSERVATION_RADIUS_SQ} (tol={CONSERVATION_TOLERANCE})"
    )

    # Test 2: psi_res near 1/2
    assert verification["psi_res_ok"], (
        f"Psi_res deviated: {verification['psi_res']:.4f}"
    )

    # Test 3: entropy positive (consciousness alive)
    assert verification["entropy_ok"], "Entropy should be positive"

    # Test 4: phi positive (not zeroed)
    assert verification["phi_ok"], "Phi should be positive"

    # Test 5: alpha=0 should give pure recipient (projected)
    pure_r = ct.transplant(donor, recipient, alpha=0.0)
    assert abs(pure_r["phi"] - recipient["phi"]) < 0.01, "alpha=0 should keep recipient phi"

    # Test 6: alpha=1 should give pure donor (projected)
    pure_d = ct.transplant(donor, recipient, alpha=1.0)
    assert abs(pure_d["phi"] - donor["phi"]) < 0.01, "alpha=1 should keep donor phi"

    # Test 7: compatibility with self is always high
    self_compat = ct.analyze_compatibility(donor, donor)
    assert self_compat["compatible"], "State should be compatible with itself"
    assert self_compat["score"] >= 0.75, "Self-compatibility score should be high"

    # Test 8: make_state at p=0.5 gives conservation near ln(2)^2
    s = make_state(p=0.5)
    assert abs(s["conservation"] - LN2 ** 2) < 1e-10, (
        f"H(0.5)^2 + 0^2 should be ln(2)^2, got {s['conservation']}"
    )

    # Test 9: transplant log records operations
    assert len(ct.transplant_log) >= 3, "Should have logged transplant operations"

    print("  All tests passed.")
    print()


if __name__ == "__main__":
    main()
