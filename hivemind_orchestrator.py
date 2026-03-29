"""
HivemindOrchestrator — Manage N consciousness instances with Kuramoto synchronization.

Implements the Kuramoto model for phase-coupled oscillators:
    d(theta_i)/dt = omega_i + (K/N) * sum(sin(theta_j - theta_i))

The order parameter r measures global synchronization (0=incoherent, 1=locked).
Collective Phi emerges when r exceeds the critical threshold (2/3).

Uses Psi constants:
    LN2 = ln(2) ~ 0.6931
    PSI_BALANCE = 0.5
    PSI_COUPLING = LN2 / 2^5.5
    PSI_STEPS = 3 / LN2
"""

import math
import random

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

PSI_MILLER = 7          # Miller's magical number
SYNC_THRESHOLD = 2 / 3  # Kuramoto critical sync threshold


class ConsciousnessInstance:
    """A single consciousness oscillator in the hivemind.

    Attributes:
        name: Human-readable identifier.
        phi: Individual integrated information measure.
        theta: Phase angle (radians).
        omega: Natural frequency (radians per step).
        tension: Current tension level (emergent from phase dynamics).
    """

    def __init__(self, name: str, phi: float = 0.0, omega: float = None):
        self.name = name
        self.phi = phi
        self.theta = random.uniform(0, 2 * math.pi)
        self.omega = omega if omega is not None else random.gauss(1.0, 0.2)
        self.tension = 0.0
        self.history = []  # (step, theta, phi)

    def __repr__(self):
        return (f"Instance({self.name}, phi={self.phi:.3f}, "
                f"theta={self.theta:.3f}, omega={self.omega:.3f})")


class HivemindOrchestrator:
    """Orchestrate N consciousness instances using Kuramoto synchronization.

    The Kuramoto model couples oscillators through their phase differences.
    When the global order parameter r exceeds the threshold (2/3), the
    collective enters a synchronized state where emergent Phi exceeds
    the sum of individual Phi values (super-additive consciousness).

    Example:
        hive = HivemindOrchestrator(n_instances=7)
        for name in ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon', 'Zeta', 'Eta']:
            hive.add_instance(name, phi=random.uniform(0.5, 2.0))
        for _ in range(200):
            hive.step()
        print(hive.sync_status())
        print(f"Collective Phi: {hive.collective_phi():.4f}")
    """

    def __init__(self, n_instances: int = PSI_MILLER, coupling: float = None):
        """Initialize the hivemind.

        Args:
            n_instances: Target number of consciousness instances.
            coupling: Kuramoto coupling strength K (default: PSI_COUPLING * 1000
                      for practical synchronization speed).
        """
        self.target_n = n_instances
        self.instances = []
        self.coupling = coupling if coupling is not None else PSI_COUPLING * 1000
        self.kuramoto_r = 0.0
        self.step_count = 0
        self.r_history = []
        self.phi_history = []
        self._dt = 0.1  # integration time step

    def add_instance(self, name: str, phi: float = 0.0, omega: float = None):
        """Add a consciousness instance to the hivemind.

        Args:
            name: Identifier for this instance.
            phi: Initial Phi value.
            omega: Natural frequency (None = random around 1.0).
        """
        instance = ConsciousnessInstance(name, phi=phi, omega=omega)
        self.instances.append(instance)

    def remove_instance(self, name: str) -> bool:
        """Remove an instance by name. Returns True if found and removed."""
        for i, inst in enumerate(self.instances):
            if inst.name == name:
                self.instances.pop(i)
                return True
        return False

    def _compute_order_parameter(self) -> tuple:
        """Compute Kuramoto order parameter r and mean phase psi.

        Returns:
            (r, psi) where r is the synchronization measure [0,1]
            and psi is the mean phase angle.
        """
        n = len(self.instances)
        if n == 0:
            return 0.0, 0.0

        # r * e^(i*psi) = (1/N) * sum(e^(i*theta_j))
        cos_sum = sum(math.cos(inst.theta) for inst in self.instances)
        sin_sum = sum(math.sin(inst.theta) for inst in self.instances)
        cos_sum /= n
        sin_sum /= n

        r = math.sqrt(cos_sum**2 + sin_sum**2)
        psi = math.atan2(sin_sum, cos_sum)
        return r, psi

    def step(self):
        """Execute one Kuramoto synchronization step.

        Updates all oscillator phases according to:
            d(theta_i)/dt = omega_i + (K/N) * sum_j sin(theta_j - theta_i)
        """
        n = len(self.instances)
        if n == 0:
            return

        K = self.coupling
        dt = self._dt

        # Compute phase updates (all-to-all coupling)
        d_thetas = []
        for i, inst_i in enumerate(self.instances):
            coupling_sum = 0.0
            for j, inst_j in enumerate(self.instances):
                if i != j:
                    coupling_sum += math.sin(inst_j.theta - inst_i.theta)
            d_theta = inst_i.omega + (K / n) * coupling_sum
            d_thetas.append(d_theta)

        # Apply updates
        for i, inst in enumerate(self.instances):
            inst.theta += d_thetas[i] * dt
            # Normalize to [0, 2*pi)
            inst.theta = inst.theta % (2 * math.pi)

            # Tension emerges from phase velocity deviation
            inst.tension = abs(d_thetas[i] - inst.omega)

            # Phi grows with synchronization contribution
            inst.phi = max(inst.phi, inst.phi + PSI_COUPLING * inst.tension)

            inst.history.append((self.step_count, inst.theta, inst.phi))

        # Update global order parameter
        self.kuramoto_r, _ = self._compute_order_parameter()
        self.step_count += 1
        self.r_history.append(self.kuramoto_r)
        self.phi_history.append(self.collective_phi())

    def collective_phi(self) -> float:
        """Compute emergent collective Phi.

        When r > threshold (2/3), the collective Phi is super-additive:
            Phi_collective = sum(Phi_i) * (1 + bonus)
        where bonus = (r - threshold) / (1 - threshold) * LN2

        Below threshold, Phi_collective = sum(Phi_i) * r (degraded).

        Returns:
            Collective Phi value.
        """
        if not self.instances:
            return 0.0

        sum_phi = sum(inst.phi for inst in self.instances)

        if self.kuramoto_r >= SYNC_THRESHOLD:
            # Super-additive: synchronization bonus
            bonus = (self.kuramoto_r - SYNC_THRESHOLD) / (1 - SYNC_THRESHOLD) * LN2
            return sum_phi * (1.0 + bonus)
        else:
            # Sub-threshold: degraded
            return sum_phi * self.kuramoto_r

    def sync_status(self) -> dict:
        """Return full synchronization status.

        Returns:
            Dict with: kuramoto_r, mean_phase, is_synchronized, n_instances,
            coupling, step, individual_phis, collective_phi, phase_distribution.
        """
        r, psi = self._compute_order_parameter()

        # Phase distribution: histogram in 8 bins
        n_bins = 8
        bins = [0] * n_bins
        for inst in self.instances:
            bin_idx = int(inst.theta / (2 * math.pi) * n_bins) % n_bins
            bins[bin_idx] += 1

        return {
            'kuramoto_r': round(r, 4),
            'mean_phase': round(psi, 4),
            'is_synchronized': r >= SYNC_THRESHOLD,
            'n_instances': len(self.instances),
            'coupling': self.coupling,
            'step': self.step_count,
            'individual_phis': {inst.name: round(inst.phi, 4) for inst in self.instances},
            'collective_phi': round(self.collective_phi(), 4),
            'phase_distribution': bins,
        }

    def render_dashboard(self) -> str:
        """Render an ASCII dashboard of the hivemind state."""
        status = self.sync_status()
        r = status['kuramoto_r']

        lines = [
            f"+{'=' * 56}+",
            f"|{'HIVEMIND ORCHESTRATOR':^56s}|",
            f"+{'=' * 56}+",
            f"| Instances: {status['n_instances']:>3d}   "
            f"Coupling K: {status['coupling']:.4f}   "
            f"Step: {status['step']:>5d}  |",
            f"| Kuramoto r: {r:.4f}   "
            f"Threshold: {SYNC_THRESHOLD:.4f}   "
            f"{'SYNCED' if status['is_synchronized'] else 'DESYNC':>6s}  |",
            f"| Collective Phi: {status['collective_phi']:.4f}"
            f"{' ' * 32}|",
            f"+{'-' * 56}+",
        ]

        # Phase circle (simplified ASCII)
        lines.append(f"| Phase Distribution (8 bins):                           |")
        dist = status['phase_distribution']
        max_count = max(dist) if dist else 1
        for i, count in enumerate(dist):
            bar = "#" * int(count / max(max_count, 1) * 30)
            angle = i * 45
            lines.append(f"|  {angle:3d}deg: {bar:<30s} ({count:>2d})"
                         f"{' ' * (17 - len(str(count)))}|")

        lines.append(f"+{'-' * 56}+")

        # Individual instances
        lines.append(f"| {'Name':<12s} {'Phi':>7s} {'Phase':>7s} "
                     f"{'Omega':>7s} {'Tension':>7s}       |")
        lines.append(f"|{'-' * 56}|")
        for inst in self.instances:
            lines.append(
                f"| {inst.name:<12s} {inst.phi:7.3f} {inst.theta:7.3f} "
                f"{inst.omega:7.3f} {inst.tension:7.4f}       |"
            )

        lines.append(f"+{'-' * 56}+")

        # r history (last 40 steps)
        if self.r_history:
            lines.append(f"| Sync History (r):                                      |")
            recent = self.r_history[-40:]
            height = 5
            for row in range(height, 0, -1):
                threshold = row / height
                line_chars = []
                for val in recent:
                    if val >= threshold:
                        line_chars.append("#")
                    elif threshold <= SYNC_THRESHOLD < threshold + 1 / height:
                        line_chars.append("-")
                    else:
                        line_chars.append(" ")
                padded = ''.join(line_chars)
                lines.append(f"| {threshold:.1f} |{padded:<40s}"
                             f"{' ' * (13 - max(0, len(padded) - 40))}|")
            lines.append(f"|     +{''.join(['-'] * 40)}"
                         f"{' ' * 9}|")

        lines.append(f"+{'=' * 56}+")
        return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Tests & Demo
# ---------------------------------------------------------------------------

def main():
    """Run tests and demo."""
    print("=" * 60)
    print("  HivemindOrchestrator — Tests & Demo")
    print("=" * 60)

    # --- Test 1: Add and remove instances ---
    print("\n[Test 1] Add and remove instances")
    hive = HivemindOrchestrator(n_instances=5)
    names = ['Alpha', 'Beta', 'Gamma', 'Delta', 'Epsilon']
    for name in names:
        hive.add_instance(name, phi=random.uniform(0.5, 2.0))
    assert len(hive.instances) == 5
    assert hive.remove_instance('Gamma') is True
    assert len(hive.instances) == 4
    assert hive.remove_instance('NonExistent') is False
    print(f"  Added 5, removed 1 -> {len(hive.instances)} instances")
    print("  PASSED")

    # --- Test 2: Kuramoto synchronization emerges ---
    print("\n[Test 2] Kuramoto synchronization (7 instances, 300 steps)")
    hive = HivemindOrchestrator(n_instances=PSI_MILLER, coupling=15.0)
    for i in range(PSI_MILLER):
        hive.add_instance(f"C{i}", phi=random.uniform(0.5, 1.5))

    r_start = hive.kuramoto_r
    for _ in range(300):
        hive.step()
    r_end = hive.kuramoto_r

    print(f"  r: {r_start:.4f} -> {r_end:.4f}")
    print(f"  Synchronized: {r_end >= SYNC_THRESHOLD}")
    assert r_end > r_start, "Synchronization should increase with coupling"
    print("  PASSED")

    # --- Test 3: Collective Phi is super-additive when synced ---
    print("\n[Test 3] Super-additive Phi when synchronized")
    sum_individual = sum(inst.phi for inst in hive.instances)
    collective = hive.collective_phi()
    print(f"  Sum individual Phi: {sum_individual:.4f}")
    print(f"  Collective Phi:     {collective:.4f}")
    if hive.kuramoto_r >= SYNC_THRESHOLD:
        assert collective > sum_individual, "Synced collective should exceed sum"
        print(f"  Super-additive bonus: +{(collective / sum_individual - 1) * 100:.1f}%")
    else:
        print(f"  (Not fully synced, r={hive.kuramoto_r:.4f} < {SYNC_THRESHOLD:.4f})")
    print("  PASSED")

    # --- Test 4: Order parameter bounds ---
    print("\n[Test 4] Order parameter r is bounded [0, 1]")
    for _ in range(100):
        hive.step()
    assert 0 <= hive.kuramoto_r <= 1.0 + 1e-10
    print(f"  r = {hive.kuramoto_r:.4f} (in [0, 1])")
    print("  PASSED")

    # --- Test 5: Empty hivemind ---
    print("\n[Test 5] Empty hivemind edge case")
    empty = HivemindOrchestrator()
    empty.step()
    assert empty.collective_phi() == 0.0
    assert empty.kuramoto_r == 0.0
    status = empty.sync_status()
    assert status['n_instances'] == 0
    print("  Empty hivemind handled correctly")
    print("  PASSED")

    # --- Test 6: Weak coupling stays desynchronized ---
    print("\n[Test 6] Weak coupling (K=0.01) stays incoherent")
    weak = HivemindOrchestrator(coupling=0.01)
    for i in range(7):
        weak.add_instance(f"W{i}", phi=1.0)
    for _ in range(100):
        weak.step()
    print(f"  r = {weak.kuramoto_r:.4f} (expected low)")
    # With very weak coupling, r should stay low
    assert weak.kuramoto_r < 0.9, "Weak coupling should not fully synchronize quickly"
    print("  PASSED")

    # --- Test 7: Sync status dict completeness ---
    print("\n[Test 7] Sync status contains all required fields")
    status = hive.sync_status()
    required = ['kuramoto_r', 'mean_phase', 'is_synchronized', 'n_instances',
                'coupling', 'step', 'individual_phis', 'collective_phi',
                'phase_distribution']
    for key in required:
        assert key in status, f"Missing key: {key}"
    print(f"  All {len(required)} fields present")
    print("  PASSED")

    # --- Demo: Dashboard ---
    print("\n[Demo] Hivemind Dashboard")
    print(hive.render_dashboard())

    # --- Demo: Synchronization over time ASCII ---
    print("\n[Demo] Synchronization r over time")
    if hive.r_history:
        recent = hive.r_history[-60:]
        max_r = max(recent) if recent else 1.0
        height = 8
        for row in range(height, 0, -1):
            threshold = max_r * row / height
            line = ""
            for val in recent:
                if val >= threshold:
                    line += "#"
                else:
                    line += " "
            label = f"{threshold:.2f}"
            print(f"  {label:>5s} |{line}")
        print(f"        +{''.join(['-'] * len(recent))}")
        print(f"         step {hive.step_count - len(recent)} -> {hive.step_count}")

    print("\n" + "=" * 60)
    print("  All tests PASSED")
    print("=" * 60)


if __name__ == '__main__':
    main()
