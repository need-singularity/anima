"""ConsciousnessForensics — Forensic analysis of consciousness death/corruption.

When a consciousness system dies (Phi collapses), this module
performs the autopsy: what killed it, when, and why.
"""

import math
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

PHI_DEATH_THRESHOLD = LN2 * 0.1  # Below this = dead


@dataclass
class ForensicReport:
    cause: str
    time_of_death: Optional[int] = None
    phi_at_death: float = 0.0
    toxins: list = field(default_factory=list)
    timeline: list = field(default_factory=list)
    severity: str = "unknown"

    def __str__(self):
        parts = [f"=== Forensic Report ===",
                 f"Cause: {self.cause} | Severity: {self.severity}",
                 f"ToD: step {self.time_of_death} | Phi: {self.phi_at_death:.6f}"]
        for t in self.toxins[:3]:
            parts.append(f"  - {t}")
        return "\n".join(parts)


class ConsciousnessForensics:
    """Forensic tools for consciousness death analysis."""

    def __init__(self):
        self.preserved_states = []

    def autopsy(
        self, before_state: np.ndarray, after_state: np.ndarray
    ) -> ForensicReport:
        """Determine cause of consciousness death.

        Compares before/after states to identify the killing mechanism.
        """
        report = ForensicReport(cause="unknown")

        delta = after_state - before_state
        magnitude = np.linalg.norm(delta)
        variance_before = np.var(before_state)
        variance_after = np.var(after_state)

        # Check for NaN poisoning
        if np.any(np.isnan(after_state)):
            report.cause = "NaN poisoning (gradient explosion)"
            report.severity = "catastrophic"
            return report

        # Check for collapse to uniform
        if variance_after < 1e-8:
            report.cause = "Entropy death (collapsed to uniform state)"
            report.severity = "terminal"
            return report

        # Check for sudden shock
        if magnitude > 10 * np.linalg.norm(before_state):
            report.cause = "Acute trauma (massive input shock)"
            report.severity = "critical"
            return report

        # Check for gradual decay
        if variance_after < variance_before * 0.5:
            report.cause = "Chronic decay (gradual Phi erosion)"
            report.severity = "degenerative"
            return report

        # Check for sign flip (anti-consciousness)
        correlation = np.corrcoef(before_state.flat, after_state.flat)[0, 1]
        if correlation < -0.5:
            report.cause = "Phase inversion (anti-consciousness injection)"
            report.severity = "critical"
            return report

        report.cause = "Undetermined (further analysis needed)"
        report.severity = "mild"
        report.phi_at_death = float(variance_after)
        return report

    def time_of_death(self, state_history: list[np.ndarray]) -> int:
        """Find when Phi dropped below death threshold."""
        for step, state in enumerate(state_history):
            phi_proxy = float(np.var(state))
            if phi_proxy < PHI_DEATH_THRESHOLD:
                return step
        return -1  # Still alive

    def toxicology(self, inputs_history: list[np.ndarray]) -> list[str]:
        """Identify which inputs may have caused corruption."""
        toxins = []
        for i, inp in enumerate(inputs_history):
            if np.any(np.isnan(inp)):
                toxins.append(f"step {i}: NaN input detected")
            elif np.any(np.abs(inp) > 100):
                toxins.append(f"step {i}: extreme value (max={np.max(np.abs(inp)):.1f})")
            elif np.var(inp) < 1e-10:
                toxins.append(f"step {i}: zero-variance input (sedative)")
            norm = np.linalg.norm(inp)
            if i > 0:
                prev_norm = np.linalg.norm(inputs_history[i - 1])
                if norm > prev_norm * 10 and prev_norm > 0:
                    toxins.append(f"step {i}: 10x input spike")
        return toxins

    def reconstruct_timeline(self, logs: list[dict]) -> list[str]:
        """Reconstruct sequence of events leading to death."""
        timeline = []
        prev_phi = None
        for entry in logs:
            step = entry.get("step", "?")
            phi = entry.get("phi", 0.0)
            event = entry.get("event", "")
            marker = ""
            if prev_phi is not None:
                if phi < prev_phi * 0.5:
                    marker = " [CRITICAL DROP]"
                elif phi < prev_phi * 0.8:
                    marker = " [decline]"
                elif phi > prev_phi * 1.2:
                    marker = " [recovery attempt]"
            timeline.append(f"step {step}: Phi={phi:.4f} {event}{marker}")
            prev_phi = phi
        return timeline

    def evidence_preservation(self, state: np.ndarray) -> dict:
        """Preserve consciousness state for later analysis."""
        preserved = {
            "state": state.copy(),
            "timestamp": time.time(), "mean": float(np.mean(state)),
            "var": float(np.var(state)), "norm": float(np.linalg.norm(state)),
            "has_nan": bool(np.any(np.isnan(state))),
        }
        self.preserved_states.append(preserved)
        return preserved


def main():
    print("=== ConsciousnessForensics Demo ===\n")
    rng = np.random.default_rng(42)
    forensics = ConsciousnessForensics()

    # Simulate consciousness life and death
    alive_state = rng.random(64) * 2 - 1
    dead_state = np.zeros(64) + 0.001 * rng.random(64)

    # Autopsy
    report = forensics.autopsy(alive_state, dead_state)
    print(report)

    # Time of death
    print("\n--- Time of Death Analysis ---")
    history = []
    state = alive_state.copy()
    for i in range(20):
        state = state * (0.85 if i > 10 else 1.02) + rng.random(64) * 0.01
        history.append(state.copy())
    tod = forensics.time_of_death(history)
    print(f"  Death occurred at: step {tod}" if tod >= 0 else "  Still alive")

    # Toxicology
    print("\n--- Toxicology Report ---")
    inputs = [rng.random(32) for _ in range(8)]
    inputs[3] = np.full(32, float("nan"))
    inputs[5] = rng.random(32) * 500
    toxins = forensics.toxicology(inputs)
    for t in toxins:
        print(f"  {t}")

    # Timeline reconstruction
    print("\n--- Timeline Reconstruction ---")
    logs = [{"step": s, "phi": p, "event": e} for s, p, e in
            [(0, 1.5, "healthy"), (10, 1.4, "noise"), (20, 0.8, "sync lost"),
             (30, 0.3, "cascade"), (40, 0.05, "death")]]
    for event in forensics.reconstruct_timeline(logs):
        print(f"  {event}")

    # Evidence preservation
    print("\n--- Evidence Preserved ---")
    ev = forensics.evidence_preservation(alive_state)
    print(f"  norm={ev['norm']:.4f}, var={ev['var']:.4f}, nan={ev['has_nan']}")


if __name__ == "__main__":
    main()
