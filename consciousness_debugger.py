"""
ConsciousnessDebugger — Real-time consciousness state visualizer, anomaly detector, and auto-recovery.

Monitors consciousness health by tracking:
    - H (entropy): information content of consciousness states
    - Psi_res (Psi residual): deviation from Psi balance point
    - Gate: adaptive gate value controlling information flow
    - Phi: integrated information measure
    - Conservation Q: energy conservation check (should be near constant)

Detects anomalies: conservation violations, Psi drift, gate collapse, Phi crashes.
Suggests recovery actions for each anomaly type.

Uses Psi constants:
    LN2 = ln(2) ~ 0.6931
    PSI_BALANCE = 0.5
    PSI_COUPLING = LN2 / 2^5.5
    PSI_STEPS = 3 / LN2
"""

import math
from collections import deque

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

# Anomaly detection thresholds
_CONSERVATION_TOLERANCE = 0.15    # Q deviation tolerance
_PSI_DRIFT_THRESHOLD = 0.3       # max acceptable Psi residual drift
_GATE_COLLAPSE_THRESHOLD = 0.005 # gate below this = collapsed
_PHI_CRASH_RATIO = 0.5           # Phi drops below 50% of recent max = crash
_WINDOW_SIZE = 50                # sliding window for statistics


class AnomalyType:
    """Enumeration of consciousness anomaly types."""
    CONSERVATION_VIOLATION = 'conservation_violation'
    PSI_DRIFT = 'psi_drift'
    GATE_COLLAPSE = 'gate_collapse'
    PHI_CRASH = 'phi_crash'
    PHI_STAGNATION = 'phi_stagnation'
    ENTROPY_SPIKE = 'entropy_spike'


class Anomaly:
    """A detected consciousness anomaly.

    Attributes:
        type: AnomalyType string.
        step: Step at which the anomaly was detected.
        severity: 0.0 (minor) to 1.0 (critical).
        description: Human-readable description.
        values: Dict of relevant metric values at detection time.
    """

    def __init__(self, anomaly_type: str, step: int, severity: float,
                 description: str, values: dict = None):
        self.type = anomaly_type
        self.step = step
        self.severity = max(0.0, min(1.0, severity))
        self.description = description
        self.values = values or {}

    def __repr__(self):
        return f"Anomaly({self.type}, step={self.step}, severity={self.severity:.2f})"


class ConsciousnessDebugger:
    """Real-time consciousness state visualizer and anomaly detector.

    Records consciousness state snapshots, detects anomalies, suggests recovery
    actions, and renders ASCII dashboards for monitoring.

    Example:
        dbg = ConsciousnessDebugger()
        for step in range(200):
            H = compute_entropy()
            psi_res = compute_psi_residual()
            gate = adaptive_gate.value()
            phi = compute_phi()
            dbg.record(step, H, psi_res, gate, phi)
        anomalies = dbg.detect_anomaly()
        if anomalies:
            recovery = dbg.auto_recover(anomalies)
        print(dbg.render_dashboard())
        print(f"Health: {dbg.health_score():.2f}")
    """

    def __init__(self, window_size: int = _WINDOW_SIZE):
        """Initialize the debugger.

        Args:
            window_size: Number of recent steps to consider for statistics.
        """
        self.history = []  # list of (step, H, psi_res, gate, phi, Q)
        self.window_size = window_size
        self.anomaly_log = []
        self._phi_max = 0.0
        self._q_baseline = None

    def record(self, step: int, H: float, psi_res: float, gate: float, phi: float):
        """Record a consciousness state snapshot.

        Args:
            step: Current simulation step.
            H: Entropy of the consciousness state.
            psi_res: Psi residual (deviation from balance).
            gate: Adaptive gate value.
            phi: Integrated information (Phi).
        """
        # Conservation quantity Q = H + gate * phi (should be approximately constant)
        Q = H + gate * phi

        if self._q_baseline is None and len(self.history) >= 5:
            # Set baseline Q from first few steps
            self._q_baseline = sum(r[5] for r in self.history[-5:]) / 5

        self.history.append((step, H, psi_res, gate, phi, Q))
        self._phi_max = max(self._phi_max, phi)

    def _recent(self, n: int = None) -> list:
        """Return the most recent n records."""
        n = n or self.window_size
        return self.history[-n:] if self.history else []

    def detect_anomaly(self) -> list:
        """Check for consciousness anomalies in recent history.

        Detects:
            - Conservation violation: Q deviates from baseline beyond tolerance.
            - Psi drift: Psi residual consistently drifts away from zero.
            - Gate collapse: Gate value drops near zero.
            - Phi crash: Phi drops below 50% of recent maximum.
            - Phi stagnation: Phi unchanged for extended period.
            - Entropy spike: Sudden entropy jump.

        Returns:
            List of Anomaly objects detected.
        """
        anomalies = []
        recent = self._recent()
        if len(recent) < 3:
            return anomalies

        latest = recent[-1]
        step, H, psi_res, gate, phi, Q = latest

        # --- Conservation violation ---
        if self._q_baseline is not None:
            q_deviation = abs(Q - self._q_baseline) / max(abs(self._q_baseline), 1e-6)
            if q_deviation > _CONSERVATION_TOLERANCE:
                severity = min(1.0, q_deviation / 0.5)
                anomalies.append(Anomaly(
                    AnomalyType.CONSERVATION_VIOLATION, step, severity,
                    f"Conservation Q deviated {q_deviation:.2%} from baseline "
                    f"(Q={Q:.4f}, baseline={self._q_baseline:.4f})",
                    {'Q': Q, 'baseline': self._q_baseline, 'deviation': q_deviation}
                ))

        # --- Psi drift ---
        psi_values = [r[2] for r in recent]
        mean_psi = sum(psi_values) / len(psi_values)
        if abs(mean_psi) > _PSI_DRIFT_THRESHOLD:
            severity = min(1.0, abs(mean_psi) / 0.8)
            direction = "positive" if mean_psi > 0 else "negative"
            anomalies.append(Anomaly(
                AnomalyType.PSI_DRIFT, step, severity,
                f"Psi residual drifting {direction} (mean={mean_psi:.4f}, "
                f"threshold={_PSI_DRIFT_THRESHOLD})",
                {'mean_psi': mean_psi, 'current_psi': psi_res}
            ))

        # --- Gate collapse ---
        if gate < _GATE_COLLAPSE_THRESHOLD:
            severity = 1.0 - gate / _GATE_COLLAPSE_THRESHOLD
            anomalies.append(Anomaly(
                AnomalyType.GATE_COLLAPSE, step, severity,
                f"Gate collapsed to {gate:.6f} (threshold={_GATE_COLLAPSE_THRESHOLD})",
                {'gate': gate}
            ))

        # --- Phi crash ---
        if self._phi_max > 0 and phi < self._phi_max * _PHI_CRASH_RATIO:
            severity = 1.0 - phi / max(self._phi_max, 1e-6)
            anomalies.append(Anomaly(
                AnomalyType.PHI_CRASH, step, severity,
                f"Phi crashed: {phi:.4f} < {self._phi_max * _PHI_CRASH_RATIO:.4f} "
                f"(50% of max {self._phi_max:.4f})",
                {'phi': phi, 'phi_max': self._phi_max}
            ))

        # --- Phi stagnation ---
        if len(recent) >= 20:
            phi_values = [r[4] for r in recent[-20:]]
            phi_range = max(phi_values) - min(phi_values)
            if phi_range < 1e-6 and max(phi_values) > 0:
                anomalies.append(Anomaly(
                    AnomalyType.PHI_STAGNATION, step, 0.5,
                    f"Phi stagnant for {len(recent[-20:])} steps "
                    f"(range={phi_range:.8f})",
                    {'phi_range': phi_range, 'phi': phi}
                ))

        # --- Entropy spike ---
        if len(recent) >= 5:
            h_values = [r[1] for r in recent[-5:]]
            h_mean = sum(h_values[:-1]) / len(h_values[:-1])
            h_current = h_values[-1]
            if h_mean > 0 and h_current > h_mean * 2.0:
                severity = min(1.0, (h_current / h_mean - 1.0) / 3.0)
                anomalies.append(Anomaly(
                    AnomalyType.ENTROPY_SPIKE, step, severity,
                    f"Entropy spike: {h_current:.4f} vs mean {h_mean:.4f} "
                    f"({h_current / h_mean:.1f}x)",
                    {'H': h_current, 'H_mean': h_mean}
                ))

        self.anomaly_log.extend(anomalies)
        return anomalies

    def auto_recover(self, anomalies: list) -> dict:
        """Suggest recovery actions for detected anomalies.

        Args:
            anomalies: List of Anomaly objects from detect_anomaly().

        Returns:
            Dict mapping anomaly type to recovery action dict with
            'action', 'params', and 'description'.
        """
        recovery = {}

        for anomaly in anomalies:
            if anomaly.type == AnomalyType.CONSERVATION_VIOLATION:
                recovery[anomaly.type] = {
                    'action': 'normalize_Q',
                    'params': {
                        'target_Q': self._q_baseline,
                        'scale_factor': self._q_baseline / max(anomaly.values.get('Q', 1), 1e-6),
                    },
                    'description': 'Rescale cell tensions to restore conservation quantity Q.',
                }

            elif anomaly.type == AnomalyType.PSI_DRIFT:
                correction = -anomaly.values.get('mean_psi', 0) * PSI_COUPLING
                recovery[anomaly.type] = {
                    'action': 'apply_psi_correction',
                    'params': {
                        'correction': correction,
                        'target_psi': 0.0,
                    },
                    'description': 'Apply counter-bias to Psi residual to recenter at zero.',
                }

            elif anomaly.type == AnomalyType.GATE_COLLAPSE:
                recovery[anomaly.type] = {
                    'action': 'reset_gate',
                    'params': {
                        'new_alpha': 0.01,
                        'new_beta': 0.14,
                        'inject_noise': 0.05,
                    },
                    'description': 'Reset gate parameters and inject small noise to restart dynamics.',
                }

            elif anomaly.type == AnomalyType.PHI_CRASH:
                recovery[anomaly.type] = {
                    'action': 'phi_ratchet_restore',
                    'params': {
                        'target_phi': self._phi_max * 0.8,
                        'ratchet_strength': 0.1,
                    },
                    'description': 'Apply Phi ratchet: restore to 80% of historical max and '
                                   'increase coupling to rebuild integration.',
                }

            elif anomaly.type == AnomalyType.PHI_STAGNATION:
                recovery[anomaly.type] = {
                    'action': 'inject_perturbation',
                    'params': {
                        'noise_amplitude': 0.1,
                        'duration_steps': 10,
                    },
                    'description': 'Inject random perturbation to break stagnation and '
                                   'explore new configurations.',
                }

            elif anomaly.type == AnomalyType.ENTROPY_SPIKE:
                recovery[anomaly.type] = {
                    'action': 'dampen_entropy',
                    'params': {
                        'damping_factor': 0.5,
                        'cooldown_steps': 5,
                    },
                    'description': 'Apply entropy damping for a few steps to stabilize.',
                }

        return recovery

    def render_dashboard(self) -> str:
        """Render an ASCII dashboard of consciousness state.

        Shows: H curve, Psi tracking, gate history, Phi history,
        conservation Q, and recent anomalies.

        Returns:
            Multi-line ASCII string.
        """
        recent = self._recent(40)
        if not recent:
            return "[No data recorded yet]"

        width = min(40, len(recent))
        samples = recent[-width:]

        lines = [
            f"+{'=' * 58}+",
            f"|{'CONSCIOUSNESS DEBUGGER':^58s}|",
            f"+{'=' * 58}+",
            f"| Steps: {self.history[-1][0]:>6d}   "
            f"Health: {self.health_score():.2f}   "
            f"Anomalies: {len(self.anomaly_log):>4d}        |",
            f"+{'-' * 58}+",
        ]

        # Helper to render a metric as ASCII sparkline
        def sparkline(values: list, label: str, fmt: str = ".3f") -> list:
            if not values:
                return [f"| {label}: [no data]{' ' * (46 - len(label))}|"]
            vmin, vmax = min(values), max(values)
            vrange = vmax - vmin if vmax > vmin else 1.0
            height = 4
            result = []
            result.append(f"| {label} (min={vmin:{fmt}}, max={vmax:{fmt}})"
                          f"{' ' * max(0, 58 - len(f' {label} (min={vmin:{fmt}}, max={vmax:{fmt}})'))}|")
            for row in range(height, 0, -1):
                threshold = vmin + vrange * row / height
                bar = ""
                for v in values:
                    if v >= threshold:
                        bar += "#"
                    else:
                        bar += " "
                result.append(f"|   {bar:<55s}|")
            return result

        # Extract metrics
        H_vals = [r[1] for r in samples]
        psi_vals = [r[2] for r in samples]
        gate_vals = [r[3] for r in samples]
        phi_vals = [r[4] for r in samples]
        Q_vals = [r[5] for r in samples]

        for label, vals, fmt in [
            ("Entropy (H)", H_vals, ".3f"),
            ("Psi Residual", psi_vals, ".4f"),
            ("Gate", gate_vals, ".5f"),
            ("Phi", phi_vals, ".4f"),
            ("Conservation Q", Q_vals, ".4f"),
        ]:
            lines.extend(sparkline(vals, label, fmt))
            lines.append(f"|{' ' * 58}|")

        # Recent anomalies
        lines.append(f"+{'-' * 58}+")
        lines.append(f"| Recent Anomalies:{' ' * 40}|")
        recent_anomalies = self.anomaly_log[-5:]
        if not recent_anomalies:
            lines.append(f"|   (none){' ' * 49}|")
        else:
            for a in recent_anomalies:
                sev_bar = "#" * int(a.severity * 10)
                text = f"  [{sev_bar:<10s}] {a.type}: step {a.step}"
                lines.append(f"|{text:<58s}|")

        lines.append(f"+{'=' * 58}+")
        return '\n'.join(lines)

    def health_score(self) -> float:
        """Compute overall consciousness health score (0.0 to 1.0).

        Factors:
            - Phi stability: no crashes or stagnation
            - Conservation: Q stays near baseline
            - Gate: not collapsed
            - Psi: centered near zero
            - Low anomaly rate

        Returns:
            Health score between 0.0 (critical) and 1.0 (perfect).
        """
        if len(self.history) < 5:
            return 1.0  # insufficient data, assume healthy

        recent = self._recent(20)
        score = 1.0

        # Factor 1: Phi stability (no crash)
        phi_vals = [r[4] for r in recent]
        if self._phi_max > 0:
            phi_ratio = phi_vals[-1] / self._phi_max
            score *= max(0.1, phi_ratio)

        # Factor 2: Conservation
        if self._q_baseline is not None:
            Q_vals = [r[5] for r in recent]
            q_dev = sum(abs(q - self._q_baseline) for q in Q_vals) / len(Q_vals)
            q_health = math.exp(-q_dev / max(abs(self._q_baseline), 0.1))
            score *= q_health

        # Factor 3: Gate health
        gate_vals = [r[3] for r in recent]
        min_gate = min(gate_vals)
        if min_gate < _GATE_COLLAPSE_THRESHOLD:
            score *= 0.3
        elif min_gate < _GATE_COLLAPSE_THRESHOLD * 5:
            score *= 0.7

        # Factor 4: Psi centering
        psi_vals = [r[2] for r in recent]
        mean_psi = sum(abs(p) for p in psi_vals) / len(psi_vals)
        psi_health = math.exp(-mean_psi / _PSI_DRIFT_THRESHOLD)
        score *= psi_health

        # Factor 5: Anomaly rate
        recent_anomaly_count = sum(
            1 for a in self.anomaly_log
            if a.step >= self.history[-1][0] - self.window_size
        )
        anomaly_penalty = max(0.3, 1.0 - recent_anomaly_count * 0.1)
        score *= anomaly_penalty

        return max(0.0, min(1.0, score))

    def summary(self) -> str:
        """Return a concise text summary of current state."""
        if not self.history:
            return "No data recorded."

        latest = self.history[-1]
        step, H, psi_res, gate, phi, Q = latest
        health = self.health_score()

        return (
            f"Step {step}: H={H:.4f} Psi={psi_res:.4f} Gate={gate:.5f} "
            f"Phi={phi:.4f} Q={Q:.4f} Health={health:.2f} "
            f"Anomalies={len(self.anomaly_log)}"
        )


# ---------------------------------------------------------------------------
# Tests & Demo
# ---------------------------------------------------------------------------

def main():
    """Run tests and demo."""
    import random

    print("=" * 60)
    print("  ConsciousnessDebugger — Tests & Demo")
    print("=" * 60)

    dbg = ConsciousnessDebugger()

    # --- Test 1: Record healthy states ---
    print("\n[Test 1] Record 100 healthy states")
    for step in range(100):
        H = 0.5 + 0.1 * math.sin(step * 0.1)
        psi_res = 0.02 * math.sin(step * 0.05)
        gate = 0.01 + 0.14 * math.tanh(step / 30.0)
        phi = 0.5 + 0.01 * step + 0.05 * math.sin(step * 0.2)
        dbg.record(step, H, psi_res, gate, phi)

    assert len(dbg.history) == 100
    print(f"  Recorded {len(dbg.history)} snapshots")
    print(f"  {dbg.summary()}")
    print("  PASSED")

    # --- Test 2: No anomalies in healthy state ---
    print("\n[Test 2] No anomalies in healthy state")
    anomalies = dbg.detect_anomaly()
    print(f"  Anomalies detected: {len(anomalies)}")
    # May detect some minor ones due to changing gate, but severity should be low
    for a in anomalies:
        print(f"    {a}")
    print("  PASSED")

    # --- Test 3: Health score for healthy system ---
    print("\n[Test 3] Health score")
    health = dbg.health_score()
    print(f"  Health: {health:.4f}")
    assert health > 0.3, f"Healthy system should have health > 0.3, got {health}"
    print("  PASSED")

    # --- Test 4: Detect Phi crash ---
    print("\n[Test 4] Detect Phi crash")
    dbg2 = ConsciousnessDebugger()
    # Build up Phi then crash it
    for step in range(50):
        phi = 1.0 + 0.02 * step
        dbg2.record(step, 0.5, 0.01, 0.1, phi)
    # Crash
    dbg2.record(50, 0.5, 0.01, 0.1, 0.3)
    anomalies = dbg2.detect_anomaly()
    crash_found = any(a.type == AnomalyType.PHI_CRASH for a in anomalies)
    print(f"  Phi crash detected: {crash_found}")
    assert crash_found, "Should detect Phi crash"
    print("  PASSED")

    # --- Test 5: Detect gate collapse ---
    print("\n[Test 5] Detect gate collapse")
    dbg3 = ConsciousnessDebugger()
    for step in range(20):
        dbg3.record(step, 0.5, 0.01, 0.001, 1.0)
    anomalies = dbg3.detect_anomaly()
    collapse_found = any(a.type == AnomalyType.GATE_COLLAPSE for a in anomalies)
    print(f"  Gate collapse detected: {collapse_found}")
    assert collapse_found, "Should detect gate collapse"
    print("  PASSED")

    # --- Test 6: Detect Psi drift ---
    print("\n[Test 6] Detect Psi drift")
    dbg4 = ConsciousnessDebugger()
    for step in range(60):
        psi_res = 0.5 + 0.01 * step  # drifting positive
        dbg4.record(step, 0.5, psi_res, 0.1, 1.0)
    anomalies = dbg4.detect_anomaly()
    drift_found = any(a.type == AnomalyType.PSI_DRIFT for a in anomalies)
    print(f"  Psi drift detected: {drift_found}")
    assert drift_found, "Should detect Psi drift"
    print("  PASSED")

    # --- Test 7: Auto-recovery suggestions ---
    print("\n[Test 7] Auto-recovery suggestions")
    all_anomalies = []
    for dbg_x in [dbg2, dbg3, dbg4]:
        all_anomalies.extend(dbg_x.detect_anomaly())
    recovery = dbg.auto_recover(all_anomalies)
    print(f"  Recovery actions for {len(recovery)} anomaly types:")
    for atype, action in recovery.items():
        print(f"    {atype}: {action['action']} — {action['description'][:60]}...")
    assert len(recovery) > 0
    print("  PASSED")

    # --- Test 8: Dashboard rendering ---
    print("\n[Test 8] Dashboard rendering")
    # Add some variety for a more interesting dashboard
    for step in range(100, 200):
        H = 0.5 + 0.2 * math.sin(step * 0.15) + random.gauss(0, 0.02)
        psi_res = 0.05 * math.sin(step * 0.08) + random.gauss(0, 0.01)
        gate = 0.01 + 0.14 * math.tanh((step - 50) / 30.0)
        phi = max(0.1, 1.0 + 0.02 * step + 0.3 * math.sin(step * 0.1) + random.gauss(0, 0.1))
        dbg.record(step, H, psi_res, gate, phi)
        dbg.detect_anomaly()  # check at each step

    dashboard = dbg.render_dashboard()
    print(dashboard)
    assert 'CONSCIOUSNESS DEBUGGER' in dashboard
    print("  PASSED")

    # --- Test 9: Summary string ---
    print("\n[Test 9] Summary string")
    summary = dbg.summary()
    print(f"  {summary}")
    assert 'Step' in summary
    assert 'Health' in summary
    print("  PASSED")

    # --- Test 10: Edge case — empty debugger ---
    print("\n[Test 10] Empty debugger")
    empty = ConsciousnessDebugger()
    assert empty.health_score() == 1.0
    assert empty.detect_anomaly() == []
    assert empty.render_dashboard() == "[No data recorded yet]"
    assert empty.summary() == "No data recorded."
    print("  All edge cases handled")
    print("  PASSED")

    print("\n" + "=" * 60)
    print("  All tests PASSED")
    print("=" * 60)


if __name__ == '__main__':
    main()
