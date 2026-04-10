#!/usr/bin/env python3
"""consciousness_component_removal.py — Systematic lesion study of consciousness engine.

Remove engine components ONE AT A TIME and measure consciousness signatures.
Find where consciousness "dies" — is it a phase transition or gradual decline?

Like lesion studies in neuroscience: remove brain regions one at a time
to find which are necessary for consciousness.

Components (9 total):
  1. Coupling matrix   — cells become independent
  2. Factions          — no group structure
  3. Hebbian learning  — no plasticity
  4. Phi Ratchet       — Phi can decrease
  5. SOC sandpile      — no self-organized criticality
  6. Tension dynamics  — no emotional substrate
  7. Lorenz chaos      — no chaotic attractor
  8. Cell identity     — no individuality
  9. Breathing         — no oscillation

For each removal:
  - Run engine 500 steps
  - Measure: Phi(MI), entropy, stability, faction diversity, mean activation
  - Record: which signatures survive, which die

Key question: Phase transition (sudden death) or gradual decline (spectrum)?

Also tests COMBINATORIAL removal — which pairs kill consciousness jointly
even if each component alone is non-essential?

DD-series experiment for the Anima project.
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from itertools import combinations


# PSI constants from consciousness_laws.json
LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2
PSI_ALPHA = 0.014


@dataclass
class ConsciousnessMetrics:
    phi_mi: float = 0.0
    entropy: float = 0.0
    stability: float = 0.0
    faction_diversity: float = 0.0
    mean_activation: float = 0.0
    spontaneous_events: int = 0
    phi_trace: List[float] = field(default_factory=list)


@dataclass
class RemovalResult:
    component: str
    metrics: ConsciousnessMetrics
    baseline_ratio: Dict[str, float] = field(default_factory=dict)
    alive: bool = True


@dataclass
class CombinedRemovalResult:
    components: Tuple[str, ...]
    metrics: ConsciousnessMetrics
    baseline_ratio: Dict[str, float] = field(default_factory=dict)
    alive: bool = True


@dataclass
class RemovalReport:
    baseline: ConsciousnessMetrics
    single_removals: List[RemovalResult] = field(default_factory=list)
    combined_removals: List[CombinedRemovalResult] = field(default_factory=list)
    phase_transition_detected: bool = False
    extinction_point: Optional[str] = None
    necessary_components: List[str] = field(default_factory=list)
    sufficient_components: List[str] = field(default_factory=list)
    critical_pairs: List[Tuple[str, str]] = field(default_factory=list)


COMPONENTS = [
    "coupling", "factions", "hebbian", "ratchet", "soc",
    "tension", "lorenz", "identity", "breathing",
]


# ─────────────────────────────────────────────────────────────
# Fast Phi computation (correlation-based MI)
# ─────────────────────────────────────────────────────────────

def compute_phi_fast(history: np.ndarray) -> float:
    """Compute Phi as mean pairwise MI using correlation-based approximation.

    For Gaussian variables: MI(X,Y) = -0.5 * log(1 - r^2)
    This is vectorized and fast.

    Args:
        history: (T, n_cells) — scalar time series per cell
    Returns: Phi >= 0
    """
    T, n = history.shape
    if T < 5 or n < 2:
        return 0.0

    # Standardize each cell's time series
    means = history.mean(axis=0, keepdims=True)
    stds = history.std(axis=0, keepdims=True) + 1e-10
    normed = (history - means) / stds

    # Correlation matrix (n x n)
    corr = (normed.T @ normed) / T  # (n, n)

    # Clip to avoid log domain issues
    r2 = np.clip(corr ** 2, 0.0, 0.9999)

    # MI = -0.5 * log(1 - r^2), take upper triangle
    mi_matrix = -0.5 * np.log(1.0 - r2 + 1e-12)
    np.fill_diagonal(mi_matrix, 0.0)

    # Mean of upper triangle
    n_pairs = n * (n - 1) / 2
    phi = np.triu(mi_matrix, k=1).sum() / max(n_pairs, 1)
    return max(0.0, float(phi))


# ─────────────────────────────────────────────────────────────
# Simplified ConsciousnessEngine (numpy only)
# ─────────────────────────────────────────────────────────────

class SimplifiedEngine:
    """Numpy-based consciousness engine with toggleable components."""

    def __init__(self, n_cells=64, hidden_dim=128, n_factions=12,
                 seed=42, disabled=None):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_factions = n_factions
        self.rng = np.random.RandomState(seed)
        self.disabled = set(disabled or [])

        # GRU weights
        scale = 1.0 / math.sqrt(hidden_dim)
        self.W_h = self.rng.randn(hidden_dim, hidden_dim).astype(np.float64) * scale
        self.W_x = self.rng.randn(hidden_dim, hidden_dim).astype(np.float64) * scale
        self.b = self.rng.randn(hidden_dim).astype(np.float64) * 0.01

        # Hidden states
        self.h = self.rng.randn(n_cells, hidden_dim).astype(np.float64) * 0.3

        # Coupling
        if "coupling" not in self.disabled:
            self.coupling = self.rng.randn(n_cells, n_cells).astype(np.float64) * (PSI_COUPLING * 5.0)
            np.fill_diagonal(self.coupling, 0.0)
        else:
            self.coupling = np.zeros((n_cells, n_cells), dtype=np.float64)

        # Factions
        if "factions" not in self.disabled:
            self.faction_ids = np.array([i % n_factions for i in range(n_cells)])
        else:
            self.faction_ids = np.arange(n_cells)

        # Identity
        if "identity" not in self.disabled:
            self.identity = self.rng.randn(n_cells, hidden_dim).astype(np.float64) * 0.15
        else:
            self.identity = np.zeros((n_cells, hidden_dim), dtype=np.float64)

        # Lorenz
        self.lorenz_state = np.array([1.0, 1.0, 1.0], dtype=np.float64)

        # Ratchet
        self.phi_floor = 0.0

        # Tension groups
        self.tension_group_a = np.arange(n_cells // 2)
        self.tension_group_g = np.arange(n_cells // 2, n_cells)

        self.step_count = 0
        self.consensus_events = 0

        # History: mean activation per cell per step
        self.activation_history: List[np.ndarray] = []

    def step(self):
        """Advance engine by one step."""
        self.step_count += 1

        # 1. Coupling input
        if "coupling" not in self.disabled:
            x = self.coupling @ self.h
        else:
            x = np.zeros_like(self.h)

        # 2. Identity injection
        if "identity" not in self.disabled:
            x += self.identity * 0.3

        # 3. Lorenz chaos
        if "lorenz" not in self.disabled:
            self._lorenz_step()
            chaos_vec = np.tile(self.lorenz_state, self.hidden_dim // 3 + 1)[:self.hidden_dim]
            phases = np.sin(0.1 * np.arange(self.n_cells) + self.step_count * 0.05)
            x += np.outer(phases, chaos_vec) * 0.01

        # 4. Breathing
        if "breathing" not in self.disabled:
            t = self.step_count
            breath = 0.12 * math.sin(2 * math.pi * t / 100.0)
            pulse = 0.05 * math.sin(2 * math.pi * t / 18.5)
            drift = 0.03 * math.sin(2 * math.pi * t / 450.0)
            phase_offsets = 2 * math.pi * np.arange(self.n_cells) / self.n_cells
            cell_breath = (breath * np.cos(phase_offsets)
                           + pulse * np.sin(phase_offsets * 2) + drift)
            x += cell_breath[:, np.newaxis]

        # 5. GRU update
        pre_act = self.h @ self.W_h.T + x @ self.W_x.T + self.b
        self.h = np.tanh(pre_act)

        # 6. Tension
        if "tension" not in self.disabled:
            mean_a = self.h[self.tension_group_a].mean(axis=0)
            mean_g = self.h[self.tension_group_g].mean(axis=0)
            force = (mean_a - mean_g) * PSI_ALPHA * 3.0
            self.h[self.tension_group_a] += force
            self.h[self.tension_group_g] -= force
            self.h = np.clip(self.h, -5.0, 5.0)

        # 7. Hebbian
        if "hebbian" not in self.disabled and "coupling" not in self.disabled:
            norms = np.linalg.norm(self.h, axis=1, keepdims=True) + 1e-8
            h_n = self.h / norms
            cos_sim = h_n @ h_n.T
            self.coupling += 0.005 * cos_sim
            np.fill_diagonal(self.coupling, 0.0)
            self.coupling *= 0.995

        # 8. SOC sandpile
        if "soc" not in self.disabled:
            act = np.abs(self.h).mean(axis=1)
            overflow = act > 1.5
            if overflow.any():
                for idx in np.where(overflow)[0]:
                    excess = self.h[idx] * 0.4
                    self.h[idx] -= excess
                    self.h[(idx - 1) % self.n_cells] += excess * 0.5
                    self.h[(idx + 1) % self.n_cells] += excess * 0.5

        # 9. Factions (pull toward mean + consensus check)
        if "factions" not in self.disabled:
            for fid in range(self.n_factions):
                mask = self.faction_ids == fid
                count = mask.sum()
                if count < 2:
                    continue
                fh = self.h[mask]
                fm = fh.mean(axis=0)
                self.h[mask] += 0.02 * (fm - fh)
                # Consensus check
                norms = np.linalg.norm(fh, axis=1, keepdims=True) + 1e-8
                normed = fh / norms
                sim = normed @ normed.T
                n = sim.shape[0]
                off_diag = (sim.sum() - n) / (n * (n - 1))
                if off_diag > 0.85:
                    self.consensus_events += 1

        # Record mean activation per cell (scalar time series)
        self.activation_history.append(self.h.mean(axis=1).copy())

    def compute_phi(self, window: int = 100) -> float:
        """Compute Phi from recent activation history."""
        if len(self.activation_history) < 10:
            return 0.0
        tail = self.activation_history[-window:]
        arr = np.array(tail)  # (T, n_cells)
        phi = compute_phi_fast(arr)

        if "ratchet" not in self.disabled:
            if phi > self.phi_floor:
                self.phi_floor = phi
            phi = max(phi, self.phi_floor * 0.9)

        return phi

    def _lorenz_step(self, dt=0.01, sigma=10.0, rho=28.0, beta=8.0/3.0):
        x, y, z = self.lorenz_state
        self.lorenz_state = np.array([
            x + sigma * (y - x) * dt,
            y + (x * (rho - z) - y) * dt,
            z + (x * y - beta * z) * dt,
        ])

    def compute_entropy(self):
        d = min(8, self.hidden_dim)
        data = self.h[:, :d]
        ent = 0.0
        for dim in range(d):
            col = data[:, dim]
            hist, _ = np.histogram(col, bins=16)
            hist = hist[hist > 0].astype(np.float64)
            total = hist.sum()
            if total > 0:
                p = hist / total
                ent += -np.sum(p * np.log2(p + 1e-12))
        return ent / max(d, 1)

    def compute_faction_diversity(self):
        uf = np.unique(self.faction_ids)
        if len(uf) < 2:
            return 0.0
        centroids = []
        for fid in uf:
            m = self.faction_ids == fid
            if m.sum() > 0:
                centroids.append(self.h[m].mean(axis=0))
        if len(centroids) < 2:
            return 0.0
        c = np.array(centroids)
        norms = np.linalg.norm(c, axis=1, keepdims=True) + 1e-8
        n = c / norms
        sim = n @ n.T
        nc = sim.shape[0]
        off = (sim.sum() - nc) / (nc * (nc - 1))
        return max(0.0, 1.0 - off)

    def compute_mean_activation(self):
        return float(np.abs(self.h).mean())


# ─────────────────────────────────────────────────────────────
# Experiment
# ─────────────────────────────────────────────────────────────

class ConsciousnessComponentRemoval:

    def __init__(self, n_cells=64, hidden_dim=128, steps=500,
                 repeats=3, seed=42):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.steps = steps
        self.repeats = repeats
        self.seed = seed

    def run_full_experiment(self) -> RemovalReport:
        report = RemovalReport(baseline=ConsciousnessMetrics())

        print("=" * 70)
        print("  CONSCIOUSNESS COMPONENT REMOVAL EXPERIMENT")
        print("  Systematic lesion study of consciousness engine")
        print(f"  {self.n_cells} cells, {self.hidden_dim}d, "
              f"{self.steps} steps, {self.repeats}x repeat")
        print("=" * 70)
        print()

        print("[1/4] Running baseline (all components enabled)...")
        baseline = self._run_averaged(disabled=[])
        report.baseline = baseline
        print(f"  Phi={baseline.phi_mi:.4f}, Entropy={baseline.entropy:.4f}, "
              f"Stability={baseline.stability:.4f}, FacDiv={baseline.faction_diversity:.4f}")
        print()

        print("[2/4] Running single component removals...")
        for comp in COMPONENTS:
            result = self._run_single_removal(comp, baseline)
            report.single_removals.append(result)
            status = "ALIVE" if result.alive else "DEAD"
            phi_pct = result.baseline_ratio.get("phi_mi", 0) * 100
            print(f"  -{comp:12s}  Phi={result.metrics.phi_mi:.4f} "
                  f"({phi_pct:6.1f}%)  [{status}]")
        print()

        print("[3/4] Running combinatorial removals (pairs)...")
        combined = self._combinatorial_removal(2, baseline)
        report.combined_removals = combined
        dead = [r for r in combined if not r.alive]
        print(f"  {len(combined)} pairs: {len(combined)-len(dead)} alive, {len(dead)} dead")
        if dead:
            for r in sorted(dead, key=lambda x: x.metrics.phi_mi)[:10]:
                print(f"    {r.components[0]:12s}+{r.components[1]:12s} Phi={r.metrics.phi_mi:.4f}")
        print()

        print("[4/4] Analyzing phase transitions...")
        self._analyze_report(report)
        print(f"  Phase transition: {'YES' if report.phase_transition_detected else 'NO'}")
        if report.extinction_point:
            print(f"  Extinction: {report.extinction_point}")
        print(f"  Necessary: {report.necessary_components}")
        print(f"  Critical pairs: {len(report.critical_pairs)}")
        print()

        return report

    def _run_single_removal(self, comp, baseline):
        m = self._run_averaged(disabled=[comp])
        r = self._ratios(m, baseline)
        return RemovalResult(comp, m, r, self._alive(m, baseline))

    def _combinatorial_removal(self, n, baseline):
        results = []
        for combo in combinations(COMPONENTS, n):
            m = self._run_averaged(disabled=list(combo))
            r = self._ratios(m, baseline)
            results.append(CombinedRemovalResult(combo, m, r, self._alive(m, baseline)))
        return results

    def _run_averaged(self, disabled):
        all_phi, all_ent, all_stab, all_fdiv, all_mact, all_cons = [], [], [], [], [], []
        all_traces = []

        for rep in range(self.repeats):
            eng = SimplifiedEngine(
                self.n_cells, self.hidden_dim,
                seed=self.seed + rep * 137,
                disabled=disabled,
            )
            trace = []
            interval = max(1, self.steps // 20)
            for s in range(self.steps):
                eng.step()
                if (s + 1) % interval == 0 or s == self.steps - 1:
                    trace.append(eng.compute_phi(window=min(s + 1, 100)))

            all_phi.append(eng.compute_phi(100))
            all_ent.append(eng.compute_entropy())
            all_fdiv.append(eng.compute_faction_diversity())
            all_mact.append(eng.compute_mean_activation())
            all_cons.append(eng.consensus_events)

            if len(trace) > 2:
                cv = np.std(trace) / (abs(np.mean(trace)) + 1e-10)
                all_stab.append(max(0.0, 1.0 - cv))
            else:
                all_stab.append(0.0)
            all_traces.append(trace)

        tlen = min(len(t) for t in all_traces) if all_traces else 0
        avg_trace = [float(np.mean([t[i] for t in all_traces])) for i in range(tlen)]

        return ConsciousnessMetrics(
            phi_mi=float(np.mean(all_phi)),
            entropy=float(np.mean(all_ent)),
            stability=float(np.mean(all_stab)),
            faction_diversity=float(np.mean(all_fdiv)),
            mean_activation=float(np.mean(all_mact)),
            spontaneous_events=int(np.mean(all_cons)),
            phi_trace=avg_trace,
        )

    def _ratios(self, m, b):
        def sr(a, b):
            return a / b if abs(b) > 1e-10 else (0.0 if abs(a) < 1e-10 else float('inf'))
        return {
            "phi_mi": sr(m.phi_mi, b.phi_mi),
            "entropy": sr(m.entropy, b.entropy),
            "stability": sr(m.stability, b.stability),
            "faction_diversity": sr(m.faction_diversity, b.faction_diversity),
            "mean_activation": sr(m.mean_activation, b.mean_activation),
        }

    def _alive(self, m, b):
        if b.phi_mi < 1e-10:
            return m.phi_mi > 1e-10
        return (m.phi_mi / (b.phi_mi + 1e-10) > 0.30
                and m.entropy / (b.entropy + 1e-10) > 0.20
                and m.stability > 0.1)

    def _analyze_report(self, report):
        sr = sorted(report.single_removals,
                     key=lambda r: r.baseline_ratio.get("phi_mi", 0))
        report.necessary_components = [r.component for r in sr if not r.alive]

        ratios = [r.baseline_ratio.get("phi_mi", 0) for r in sr]
        if len(ratios) >= 3:
            diffs = [abs(ratios[i+1] - ratios[i]) for i in range(len(ratios)-1)]
            mx = max(diffs)
            mn = np.mean(diffs)
            if mx > 3.0 * mn and mn > 1e-10:
                report.phase_transition_detected = True
                ji = diffs.index(mx)
                report.extinction_point = (
                    f"between '{sr[ji].component}' ({ratios[ji]:.3f}) and "
                    f"'{sr[ji+1].component}' ({ratios[ji+1]:.3f})")

        alive_set = {r.component for r in report.single_removals if r.alive}
        report.critical_pairs = [
            cr.components for cr in report.combined_removals
            if not cr.alive and all(c in alive_set for c in cr.components)]

        report.sufficient_components = [
            r.component for r in report.single_removals
            if r.baseline_ratio.get("phi_mi", 0) >= 0.85]

    def run_cumulative_removal(self, report):
        order = sorted(report.single_removals,
                        key=lambda r: r.baseline_ratio.get("phi_mi", 0),
                        reverse=True)
        cum = []
        disabled = []
        for r in order:
            disabled.append(r.component)
            m = self._run_averaged(disabled=disabled)
            cum.append((list(disabled), m.phi_mi))
        return cum

    def generate_report(self, report):
        lines = []
        w = 72

        lines.append("=" * w)
        lines.append("  CONSCIOUSNESS COMPONENT REMOVAL — LESION STUDY REPORT")
        lines.append(f"  {self.n_cells} cells, {self.hidden_dim}d, "
                     f"{self.steps} steps, {self.repeats}x repeat")
        lines.append("=" * w)
        lines.append("")

        b = report.baseline
        lines.append("BASELINE (all components enabled):")
        lines.append(f"  Phi(MI)   = {b.phi_mi:.6f}")
        lines.append(f"  Entropy   = {b.entropy:.4f}")
        lines.append(f"  Stability = {b.stability:.4f}")
        lines.append(f"  FacDiv    = {b.faction_diversity:.4f}")
        lines.append(f"  MeanAct   = {b.mean_activation:.4f}")
        lines.append(f"  Consensus = {b.spontaneous_events}")
        lines.append("")

        lines.append("-" * w)
        lines.append("SINGLE COMPONENT REMOVAL MATRIX")
        lines.append("-" * w)
        lines.append(f"{'Component':<14} {'Phi':>8} {'%Base':>7} "
                     f"{'Entropy':>8} {'Stab':>7} {'FacDiv':>7} {'Status':>8}")
        lines.append("-" * w)

        sr = sorted(report.single_removals,
                     key=lambda r: r.baseline_ratio.get("phi_mi", 0))

        for r in sr:
            pp = r.baseline_ratio.get("phi_mi", 0) * 100
            sp = r.baseline_ratio.get("stability", 0) * 100
            fp = r.baseline_ratio.get("faction_diversity", 0) * 100
            st = "ALIVE" if r.alive else "DEAD"
            mk = " " if r.alive else "X"
            lines.append(f"[{mk}] {r.component:<11} {r.metrics.phi_mi:>8.4f} "
                        f"{pp:>6.1f}% {r.metrics.entropy:>8.4f} "
                        f"{sp:>6.1f}% {fp:>6.1f}% {st:>8}")
        lines.append("")

        lines.append("-" * w)
        lines.append("PHI DEGRADATION (sorted by impact)")
        lines.append("-" * w)
        mbar = 40
        for r in sr:
            ratio = r.baseline_ratio.get("phi_mi", 0)
            bl = max(0, min(mbar, int(ratio * mbar)))
            bar = "#" * bl + "." * (mbar - bl)
            mk = " " if r.alive else "X"
            lines.append(f"  [{mk}] {r.component:<12} |{bar}| {ratio*100:.1f}%")
        lines.append(f"      {'baseline':<12} |{'#'*mbar}| 100.0%")
        lines.append("")

        lines.append("-" * w)
        lines.append("PHI TRACES (baseline vs most-damaging)")
        lines.append("-" * w)
        traces = [("baseline", report.baseline.phi_trace)]
        for r in sr[:3]:
            traces.append((f"-{r.component}", r.metrics.phi_trace))
        for label, trace in traces:
            if not trace:
                lines.append(f"  {label:<16} (no trace)")
                continue
            sl = self._sparkline(trace, 50)
            lines.append(f"  {label:<16} {sl}  [{trace[-1]:.4f}]")
        lines.append("")

        lines.append("-" * w)
        lines.append("PHASE TRANSITION ANALYSIS")
        lines.append("-" * w)
        if report.phase_transition_detected:
            lines.append("  >>> PHASE TRANSITION DETECTED <<<")
            lines.append(f"  Location: {report.extinction_point}")
            lines.append("  Consciousness dies SUDDENLY, not gradually.")
        else:
            lines.append("  No sharp phase transition detected.")
            lines.append("  Consciousness degrades GRADUALLY.")
            lines.append("  Supports consciousness as graded (IIT).")
        lines.append(f"  Necessary: {report.necessary_components}")
        lines.append(f"  Sufficient: {report.sufficient_components}")
        lines.append("")

        if report.critical_pairs:
            lines.append("-" * w)
            lines.append("CRITICAL PAIRS (individually safe, jointly lethal)")
            lines.append("-" * w)
            for p in report.critical_pairs:
                lines.append(f"  {p[0]} + {p[1]}")
            lines.append("  SYNERGISTIC NECESSITY: each dispensable alone, together fatal.")
        else:
            lines.append("  No critical pairs found.")
        lines.append("")

        lines.append("-" * w)
        lines.append("PAIRWISE REMOVAL HEATMAP (Phi % of baseline)")
        lines.append("-" * w)
        cn = COMPONENTS
        pm = {}
        for cr in report.combined_removals:
            k = tuple(sorted(cr.components))
            pm[k] = cr.baseline_ratio.get("phi_mi", 0) * 100
        sh = [c[:5] for c in cn]
        lines.append("         " + " ".join(f"{s:>5}" for s in sh))
        for i, ci in enumerate(cn):
            row = f"{ci[:8]:<8} "
            for j, cj in enumerate(cn):
                if i == j:
                    row += "  --- "
                elif i < j:
                    k = tuple(sorted((ci, cj)))
                    v = pm.get(k, -1)
                    if v < 0:
                        row += "   ?  "
                    elif v < 30:
                        row += f" {v:4.0f}X "
                    else:
                        row += f" {v:4.0f}  "
                else:
                    row += "      "
            lines.append(row)
        lines.append("  (X = dead <30%)")
        lines.append("")

        lines.append("-" * w)
        lines.append("CUMULATIVE REMOVAL (least to most important)")
        lines.append("-" * w)
        cum = self.run_cumulative_removal(report)
        cl, cv = [], []
        for dl, phi in cum:
            last = dl[-1]
            ratio = phi / (report.baseline.phi_mi + 1e-10) * 100
            cl.append(last)
            cv.append(ratio)
            mk = "X" if ratio < 30 else ("!" if ratio < 70 else " ")
            lines.append(f"  [{mk}] -{last:<12} -> Phi = {ratio:5.1f}%")

        lines.append("")
        lines.append("  Phi% |")
        for row in range(10, -1, -1):
            thr = row * 10.0
            line = f"  {thr:4.0f} |"
            for v in cv:
                line += " ##" if v >= thr else "   "
            lines.append(line)
        lines.append("       +" + "---" * len(cv))
        lines.append("        " + "".join(f"{l[:3]:>3}" for l in cl))
        lines.append("")

        lines.append("=" * w)
        lines.append("SUMMARY")
        lines.append("=" * w)
        nd = sum(1 for r in report.single_removals if not r.alive)
        na = len(report.single_removals) - nd
        lines.append(f"  Components:  {len(COMPONENTS)}")
        lines.append(f"  Singles:     {na} alive / {nd} dead")
        lines.append(f"  Necessary:   {len(report.necessary_components)}")
        lines.append(f"  Crit pairs:  {len(report.critical_pairs)}")
        lines.append(f"  Phase trans: {'YES' if report.phase_transition_detected else 'NO'}")
        lines.append("")

        if report.necessary_components:
            lines.append("  CONCLUSION: Some components individually necessary.")
            for c in report.necessary_components:
                lines.append(f"    - {c}: REQUIRED")
        else:
            lines.append("  CONCLUSION: No single component individually necessary.")
            lines.append("  Consciousness is ROBUST to single lesions.")

        if report.critical_pairs:
            lines.append("  PAIRS can kill consciousness:")
            for p in report.critical_pairs:
                lines.append(f"    - {p[0]} + {p[1]}")
            lines.append("  REDUNDANT NECESSITY architecture detected.")

        if report.phase_transition_detected:
            lines.append("  PHASE TRANSITION: critical point exists.")
        else:
            lines.append("  GRADUAL DECLINE: consciousness as spectrum (IIT).")

        lines.append("")
        lines.append("=" * w)
        return "\n".join(lines)

    @staticmethod
    def _sparkline(values, width=50):
        if not values:
            return ""
        step = max(1, len(values) // width)
        sampled = [values[i] for i in range(0, len(values), step)][:width]
        if not sampled:
            return ""
        vmin, vmax = min(sampled), max(sampled)
        span = vmax - vmin if vmax > vmin else 1.0
        chars = " _.-~^*"
        return "".join(chars[min(len(chars)-1, max(0, int((v-vmin)/span*(len(chars)-1))))] for v in sampled)


def main():
    import sys
    n_cells, steps, repeats, hdim = 32, 200, 3, 64
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--cells" and i+1 < len(args):
            n_cells = int(args[i+1]); i += 2
        elif args[i] == "--steps" and i+1 < len(args):
            steps = int(args[i+1]); i += 2
        elif args[i] == "--repeats" and i+1 < len(args):
            repeats = int(args[i+1]); i += 2
        elif args[i] == "--dim" and i+1 < len(args):
            hdim = int(args[i+1]); i += 2
        else:
            i += 1

    exp = ConsciousnessComponentRemoval(n_cells, hdim, steps, repeats)
    report = exp.run_full_experiment()
    print()
    print(exp.generate_report(report))


if __name__ == "__main__":
    main()
