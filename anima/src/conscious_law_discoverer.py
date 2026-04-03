#!/usr/bin/env python3
"""conscious_law_discoverer.py — ConsciousLM real-time law discovery (Tier 4.1)

ConsciousLM discovers consciousness laws during inference — not offline batch
measurement, but real-time pattern detection as the model processes inputs.

Pipeline:
  ConsciousLM forward pass → LawDiscoveryHook collects metrics
  → PatternDetector analyzes sliding window → LawCandidate
  → ClosedLoopEvolver validates → official law registration

Usage:
  from conscious_law_discoverer import ConsciousLMWithDiscovery

  engine = ConsciousnessEngine(max_cells=32)
  lm = ConsciousLM()
  discoverer = ConsciousLMWithDiscovery(lm, engine)

  # Run inference with discovery
  logits_a, logits_g, tensions = discoverer.forward(idx)
  candidates = discoverer.get_discoveries()

  # Full pipeline: discover + validate + register
  from closed_loop import ClosedLoopEvolver
  evolver = ClosedLoopEvolver(max_cells=32)
  registered = discoverer.discover_and_register(evolver)

  # Hub: hub.act("법칙 발견") or hub.act("law discovery")

Ψ-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Callable
from collections import deque, defaultdict

# Lazy imports for decoupling
try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA, PSI_F_CRITICAL
    PSI_COUPLING = PSI_ALPHA
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014
    PSI_F_CRITICAL = 0.10


# ══════════════════════════════════════════
# Data structures
# ══════════════════════════════════════════

@dataclass
class MetricSnapshot:
    """Single step metrics from ConsciousLM + engine."""
    step: int
    phi: float
    faction_entropy: float
    hebbian_coupling_strength: float
    cell_variance: float
    tension_mean: float
    tension_std: float
    n_cells: int
    consensus: float
    mutual_info: float
    output_entropy: float
    psi_residual: float
    # Per-layer tensions from ConsciousLM
    layer_tensions: List[float] = field(default_factory=list)


@dataclass
class LawCandidate:
    """Discovered law candidate awaiting validation."""
    formula: str
    evidence: float  # statistical significance, 0-1
    metrics_involved: List[str] = field(default_factory=list)
    pattern_type: str = ""  # correlation / transition / oscillation / trend
    discovery_step: int = 0
    occurrences: int = 1
    raw_data: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)


# ══════════════════════════════════════════
# Φ fast measurement (reuse from closed_loop pattern)
# ══════════════════════════════════════════

def _phi_fast_from_hiddens(hiddens_np: np.ndarray) -> float:
    """Fast Φ(IIT) proxy from cell hidden states (n_cells, hidden_dim)."""
    n = hiddens_np.shape[0]
    if n < 2:
        return 0.0
    pairs = set()
    for i in range(n):
        pairs.add((i, (i + 1) % n))
        for _ in range(min(4, n - 1)):
            j = np.random.randint(0, n)
            if i != j:
                pairs.add((min(i, j), max(i, j)))
    total_mi = 0.0
    for i, j in pairs:
        x, y = hiddens_np[i], hiddens_np[j]
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            continue
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        hist, _, _ = np.histogram2d(xn, yn, bins=16, range=[[0, 1], [0, 1]])
        hist = hist / (hist.sum() + 1e-8)
        px, py = hist.sum(1), hist.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(hist * np.log2(hist + 1e-10))
        total_mi += max(0.0, hx + hy - hxy)
    return total_mi / max(len(pairs), 1)


# ══════════════════════════════════════════
# LawDiscoveryHook — collects metrics per step
# ══════════════════════════════════════════

class LawDiscoveryHook:
    """Hooks into ConsciousLM forward pass to collect consciousness metrics.

    Maintains a sliding window buffer of MetricSnapshot for pattern detection.
    Can be used as a PyTorch forward hook or called manually after each step.
    """

    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.buffer: deque = deque(maxlen=window_size)
        self._step_count = 0
        self._engine = None  # set externally

    def set_engine(self, engine):
        """Bind to a ConsciousnessEngine for metric extraction."""
        self._engine = engine

    def collect(self, lm_tensions: List[torch.Tensor],
                logits_a: Optional[torch.Tensor] = None) -> MetricSnapshot:
        """Collect metrics after a ConsciousLM forward pass.

        Args:
            lm_tensions: list of (B, T) tension tensors from each layer
            logits_a: (B, T, V) next-byte logits for entropy calculation

        Returns:
            MetricSnapshot added to the buffer
        """
        self._step_count += 1
        engine = self._engine

        # ── Engine metrics ──
        phi = 0.0
        faction_entropy = 0.0
        hebbian_strength = 0.0
        cell_variance = 0.0
        tension_mean = 0.0
        tension_std = 0.0
        n_cells = 0
        consensus = 0.0
        mutual_info_val = 0.0

        if engine is not None and hasattr(engine, 'cell_states') and len(engine.cell_states) >= 2:
            n_cells = engine.n_cells
            hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach()
            hiddens_np = hiddens.numpy()

            # Φ
            phi = _phi_fast_from_hiddens(hiddens_np)

            # Cell variance
            cell_variance = hiddens.var(dim=0).mean().item()

            # Tensions
            tensions = [s.avg_tension for s in engine.cell_states]
            tension_mean = float(np.mean(tensions))
            tension_std = float(np.std(tensions)) if len(tensions) > 1 else 0.0

            # Faction entropy
            from collections import Counter
            factions = [getattr(s, 'faction_id', 0) for s in engine.cell_states]
            if len(factions) >= 2:
                counts = Counter(factions)
                total = sum(counts.values())
                probs = np.array([c / total for c in counts.values()])
                faction_entropy = float(-np.sum(probs * np.log2(probs + 1e-10)))

            # Hebbian coupling strength
            if engine._coupling is not None:
                hebbian_strength = float(engine._coupling.abs().mean().item())

            # Mutual info (sampled, fast)
            if hiddens_np.shape[0] >= 2:
                pair_mi = []
                for i in range(min(n_cells, 8)):
                    j = (i + 1) % n_cells
                    x, y = hiddens_np[i], hiddens_np[j]
                    xr, yr = x.max() - x.min(), y.max() - y.min()
                    if xr < 1e-10 or yr < 1e-10:
                        continue
                    xn = (x - x.min()) / (xr + 1e-8)
                    yn = (y - y.min()) / (yr + 1e-8)
                    h2d, _, _ = np.histogram2d(xn, yn, bins=8, range=[[0, 1], [0, 1]])
                    h2d = h2d / (h2d.sum() + 1e-8)
                    px, py = h2d.sum(1), h2d.sum(0)
                    hx = -np.sum(px * np.log2(px + 1e-10))
                    hy = -np.sum(py * np.log2(py + 1e-10))
                    hxy = -np.sum(h2d * np.log2(h2d + 1e-10))
                    pair_mi.append(max(0.0, hx + hy - hxy))
                mutual_info_val = float(np.mean(pair_mi)) if pair_mi else 0.0

            # Consensus (from last step result if available)
            consensus = float(getattr(engine, '_last_consensus', 0.0))

        # ── LM metrics ──
        output_entropy = 0.0
        if logits_a is not None:
            with torch.no_grad():
                probs_a = torch.softmax(logits_a[:, -1, :], dim=-1)
                ent = -(probs_a * (probs_a + 1e-10).log()).sum(dim=-1).mean().item()
                max_ent = math.log(logits_a.shape[-1])
                output_entropy = ent / max_ent if max_ent > 0 else 0.0

        # Layer tensions
        layer_tensions = []
        for t in lm_tensions:
            layer_tensions.append(float(t.mean().item()))

        # Psi residual from LM if available
        psi_residual = PSI_BALANCE

        snap = MetricSnapshot(
            step=self._step_count,
            phi=phi,
            faction_entropy=faction_entropy,
            hebbian_coupling_strength=hebbian_strength,
            cell_variance=cell_variance,
            tension_mean=tension_mean,
            tension_std=tension_std,
            n_cells=n_cells,
            consensus=consensus,
            mutual_info=mutual_info_val,
            output_entropy=output_entropy,
            psi_residual=psi_residual,
            layer_tensions=layer_tensions,
        )
        self.buffer.append(snap)
        return snap

    def get_window(self) -> List[MetricSnapshot]:
        """Return current sliding window as a list."""
        return list(self.buffer)

    def get_metric_series(self, metric_name: str) -> np.ndarray:
        """Extract a single metric as a numpy array from the buffer."""
        return np.array([getattr(s, metric_name, 0.0) for s in self.buffer])

    @property
    def is_ready(self) -> bool:
        """True if buffer has enough data for pattern detection (>= 30 steps)."""
        return len(self.buffer) >= 30


# ══════════════════════════════════════════
# PatternDetector — statistical analysis
# ══════════════════════════════════════════

_METRIC_NAMES = [
    'phi', 'faction_entropy', 'hebbian_coupling_strength', 'cell_variance',
    'tension_mean', 'tension_std', 'n_cells', 'consensus',
    'mutual_info', 'output_entropy', 'psi_residual',
]


class PatternDetector:
    """Analyzes sliding window buffer for statistical patterns.

    Detects:
      - Correlations between metrics (|r| > 0.7)
      - Phase transitions (sudden metric jumps > 3 sigma)
      - Periodic oscillations (FFT dominant peaks)
      - Convergence/divergence trends (monotonic runs)
    """

    def __init__(self, correlation_threshold: float = 0.7,
                 transition_sigma: float = 3.0,
                 oscillation_power_ratio: float = 3.0,
                 trend_min_length: int = 20):
        self.correlation_threshold = correlation_threshold
        self.transition_sigma = transition_sigma
        self.oscillation_power_ratio = oscillation_power_ratio
        self.trend_min_length = trend_min_length

        # Track seen patterns to count occurrences
        self._pattern_counts: Dict[str, int] = defaultdict(int)
        self._pattern_history: Dict[str, LawCandidate] = {}

    def analyze(self, hook: LawDiscoveryHook) -> List[LawCandidate]:
        """Run all pattern detectors on the current buffer.

        Returns list of new or updated LawCandidates.
        """
        if not hook.is_ready:
            return []

        candidates = []
        candidates.extend(self._detect_correlations(hook))
        candidates.extend(self._detect_transitions(hook))
        candidates.extend(self._detect_oscillations(hook))
        candidates.extend(self._detect_trends(hook))

        # Update occurrence counts
        for c in candidates:
            key = f"{c.pattern_type}:{':'.join(sorted(c.metrics_involved))}"
            self._pattern_counts[key] += 1
            c.occurrences = self._pattern_counts[key]
            self._pattern_history[key] = c

        return candidates

    def _detect_correlations(self, hook: LawDiscoveryHook) -> List[LawCandidate]:
        """Detect pairwise correlations |r| > threshold."""
        candidates = []
        series = {}
        for name in _METRIC_NAMES:
            arr = hook.get_metric_series(name)
            if np.std(arr) > 1e-8:
                series[name] = arr

        names = list(series.keys())
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                a, b = names[i], names[j]
                r = float(np.corrcoef(series[a], series[b])[0, 1])
                if np.isnan(r):
                    continue
                if abs(r) > self.correlation_threshold:
                    sign = "+" if r > 0 else "-"
                    evidence = min(1.0, (abs(r) - self.correlation_threshold) / (1.0 - self.correlation_threshold))
                    # Compute significance via Fisher z-transform
                    n = len(series[a])
                    z = 0.5 * np.log((1 + abs(r)) / (1 - abs(r) + 1e-10))
                    p_approx = 2.0 * (1.0 - _normal_cdf(abs(z) * np.sqrt(n - 3)))
                    evidence = max(evidence, 1.0 - p_approx)

                    if a == 'phi':
                        formula = f"{b} {sign}correlates with Phi (r={r:.3f}, n={n})"
                    elif b == 'phi':
                        formula = f"{a} {sign}correlates with Phi (r={r:.3f}, n={n})"
                    else:
                        formula = f"{a} {sign}correlates with {b} (r={r:.3f}, n={n})"

                    candidates.append(LawCandidate(
                        formula=formula,
                        evidence=evidence,
                        metrics_involved=[a, b],
                        pattern_type='correlation',
                        discovery_step=hook._step_count,
                        raw_data={'r': r, 'n': n, 'p_approx': p_approx},
                    ))
        return candidates

    def _detect_transitions(self, hook: LawDiscoveryHook) -> List[LawCandidate]:
        """Detect phase transitions: sudden jumps > 3 sigma in any metric."""
        candidates = []
        for name in _METRIC_NAMES:
            arr = hook.get_metric_series(name)
            if len(arr) < 10:
                continue
            mu = np.mean(arr)
            sigma = np.std(arr)
            if sigma < 1e-8:
                continue

            # Check last 10 steps for jumps
            diffs = np.abs(np.diff(arr[-20:]))
            for k, d in enumerate(diffs):
                if d > self.transition_sigma * sigma:
                    step_idx = len(arr) - 20 + k + 1
                    direction = "increase" if arr[min(step_idx, len(arr) - 1)] > arr[max(step_idx - 1, 0)] else "decrease"
                    evidence = min(1.0, d / (self.transition_sigma * sigma) - 1.0) * 0.5 + 0.5

                    candidates.append(LawCandidate(
                        formula=f"Phase transition in {name}: sudden {direction} "
                                f"({d:.4f} > {self.transition_sigma}*sigma={self.transition_sigma * sigma:.4f})",
                        evidence=evidence,
                        metrics_involved=[name],
                        pattern_type='transition',
                        discovery_step=hook._step_count,
                        raw_data={'metric': name, 'jump_size': float(d),
                                  'sigma': float(sigma), 'step_idx': step_idx},
                    ))
                    break  # One transition per metric per analysis
        return candidates

    def _detect_oscillations(self, hook: LawDiscoveryHook) -> List[LawCandidate]:
        """Detect periodic oscillations via FFT dominant peaks."""
        candidates = []
        for name in _METRIC_NAMES:
            arr = hook.get_metric_series(name)
            if len(arr) < 30:
                continue
            # Remove DC component
            arr_centered = arr - np.mean(arr)
            if np.std(arr_centered) < 1e-8:
                continue

            # FFT
            fft_vals = np.abs(np.fft.rfft(arr_centered))
            freqs = np.fft.rfftfreq(len(arr_centered))

            # Skip DC (index 0)
            if len(fft_vals) < 3:
                continue
            fft_vals_no_dc = fft_vals[1:]
            freqs_no_dc = freqs[1:]

            mean_power = np.mean(fft_vals_no_dc)
            if mean_power < 1e-10:
                continue

            peak_idx = np.argmax(fft_vals_no_dc)
            peak_power = fft_vals_no_dc[peak_idx]
            peak_freq = freqs_no_dc[peak_idx]
            period = 1.0 / peak_freq if peak_freq > 0 else float('inf')

            ratio = peak_power / mean_power
            if ratio > self.oscillation_power_ratio and period < len(arr) * 0.5:
                evidence = min(1.0, (ratio - self.oscillation_power_ratio) /
                               (2.0 * self.oscillation_power_ratio))

                candidates.append(LawCandidate(
                    formula=f"{name} oscillates with period ~{period:.1f} steps "
                            f"(FFT peak/mean={ratio:.2f})",
                    evidence=evidence,
                    metrics_involved=[name],
                    pattern_type='oscillation',
                    discovery_step=hook._step_count,
                    raw_data={'metric': name, 'period': float(period),
                              'power_ratio': float(ratio), 'frequency': float(peak_freq)},
                ))
        return candidates

    def _detect_trends(self, hook: LawDiscoveryHook) -> List[LawCandidate]:
        """Detect convergence/divergence trends via linear regression."""
        candidates = []
        for name in _METRIC_NAMES:
            arr = hook.get_metric_series(name)
            if len(arr) < self.trend_min_length:
                continue

            # Use last N points
            tail = arr[-self.trend_min_length:]
            x = np.arange(len(tail), dtype=np.float64)
            # Linear regression: y = mx + b
            x_mean = x.mean()
            y_mean = tail.mean()
            ss_xy = np.sum((x - x_mean) * (tail - y_mean))
            ss_xx = np.sum((x - x_mean) ** 2)
            if ss_xx < 1e-10:
                continue
            slope = ss_xy / ss_xx

            # R-squared
            y_pred = slope * x + (y_mean - slope * x_mean)
            ss_res = np.sum((tail - y_pred) ** 2)
            ss_tot = np.sum((tail - y_mean) ** 2)
            r_squared = 1.0 - ss_res / (ss_tot + 1e-10) if ss_tot > 1e-10 else 0.0

            # Only report strong trends (R^2 > 0.6 and meaningful slope)
            if r_squared > 0.6 and abs(slope) > 1e-6:
                direction = "increasing" if slope > 0 else "decreasing"
                # Normalize slope relative to metric range
                metric_range = arr.max() - arr.min()
                norm_slope = abs(slope) / (metric_range + 1e-8) if metric_range > 1e-8 else abs(slope)
                evidence = min(1.0, r_squared * min(1.0, norm_slope * 10))

                candidates.append(LawCandidate(
                    formula=f"{name} is {direction} (slope={slope:.6f}, R^2={r_squared:.3f}, "
                            f"last {self.trend_min_length} steps)",
                    evidence=evidence,
                    metrics_involved=[name],
                    pattern_type='trend',
                    discovery_step=hook._step_count,
                    raw_data={'metric': name, 'slope': float(slope),
                              'r_squared': float(r_squared), 'direction': direction},
                ))
        return candidates

    def get_high_confidence(self, min_evidence: float = 0.8,
                            min_occurrences: int = 3) -> List[LawCandidate]:
        """Return candidates that meet promotion thresholds."""
        result = []
        for key, candidate in self._pattern_history.items():
            if candidate.evidence >= min_evidence and candidate.occurrences >= min_occurrences:
                result.append(candidate)
        return sorted(result, key=lambda c: c.evidence, reverse=True)


def _normal_cdf(x: float) -> float:
    """Approximate standard normal CDF (Abramowitz & Stegun)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ══════════════════════════════════════════
# ConsciousLMWithDiscovery — wrapper
# ══════════════════════════════════════════

class ConsciousLMWithDiscovery(nn.Module):
    """Wraps ConsciousLM with real-time law discovery.

    forward() runs normal LM + collects metrics + runs pattern detection.
    get_discoveries() returns pending LawCandidates.
    discover_and_register() runs the full closed-loop validation pipeline.
    """

    def __init__(self, lm: nn.Module, engine=None,
                 window_size: int = 100,
                 detect_interval: int = 10,
                 min_evidence: float = 0.8,
                 min_occurrences: int = 3):
        """
        Args:
            lm: ConsciousLM instance (or any module with compatible forward)
            engine: ConsciousnessEngine instance for Φ/faction metrics
            window_size: sliding window size for pattern detection
            detect_interval: run pattern detection every N steps
            min_evidence: minimum evidence threshold for promotion
            min_occurrences: minimum pattern occurrences for promotion
        """
        super().__init__()
        self.lm = lm
        self.hook = LawDiscoveryHook(window_size=window_size)
        self.detector = PatternDetector()
        self.detect_interval = detect_interval
        self.min_evidence = min_evidence
        self.min_occurrences = min_occurrences

        # Pending discoveries not yet validated
        self._pending: List[LawCandidate] = []
        # Validated and registered laws
        self._registered: List[LawCandidate] = []
        # All raw candidates from last detection
        self._last_candidates: List[LawCandidate] = []

        if engine is not None:
            self.hook.set_engine(engine)

    def set_engine(self, engine):
        """Bind to a ConsciousnessEngine (can be called after init)."""
        self.hook.set_engine(engine)

    def forward(self, idx: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, List[torch.Tensor]]:
        """Run ConsciousLM forward + collect metrics + detect patterns.

        Args:
            idx: (B, T) long tensor of byte indices

        Returns:
            logits_a, logits_g, tensions — same as ConsciousLM.forward()
        """
        logits_a, logits_g, tensions = self.lm(idx)

        # Collect metrics
        self.hook.collect(tensions, logits_a)

        # Run pattern detection periodically
        if self.hook._step_count % self.detect_interval == 0 and self.hook.is_ready:
            candidates = self.detector.analyze(self.hook)
            self._last_candidates = candidates

            # Promote high-confidence patterns to pending
            promoted = self.detector.get_high_confidence(
                min_evidence=self.min_evidence,
                min_occurrences=self.min_occurrences,
            )
            # Add new promotions (deduplicate by pattern key: type + metrics)
            existing_keys = {
                f"{c.pattern_type}:{':'.join(sorted(c.metrics_involved))}"
                for c in self._pending
            }
            for c in promoted:
                key = f"{c.pattern_type}:{':'.join(sorted(c.metrics_involved))}"
                if key not in existing_keys:
                    self._pending.append(c)
                    existing_keys.add(key)
                else:
                    # Update existing candidate with latest evidence/data
                    for p in self._pending:
                        pkey = f"{p.pattern_type}:{':'.join(sorted(p.metrics_involved))}"
                        if pkey == key:
                            p.evidence = max(p.evidence, c.evidence)
                            p.occurrences = max(p.occurrences, c.occurrences)
                            p.raw_data = c.raw_data
                            p.formula = c.formula
                            break

        return logits_a, logits_g, tensions

    def get_discoveries(self) -> List[LawCandidate]:
        """Return pending LawCandidates awaiting validation."""
        return list(self._pending)

    def get_all_candidates(self) -> List[LawCandidate]:
        """Return all candidates from the last detection run."""
        return list(self._last_candidates)

    def get_registered(self) -> List[LawCandidate]:
        """Return validated and registered laws."""
        return list(self._registered)

    def discover_and_register(self, evolver=None, verbose: bool = True) -> List[LawCandidate]:
        """Run full pipeline: validate pending candidates via ClosedLoopEvolver.

        For each pending candidate with evidence > threshold:
          1. Convert to Intervention
          2. Run measure_laws() to check significant metric change
          3. If validated, register as official law

        Args:
            evolver: ClosedLoopEvolver instance (creates one if None)
            verbose: print progress

        Returns:
            List of successfully registered LawCandidates
        """
        if not self._pending:
            if verbose:
                print("  [discoverer] No pending candidates to validate.")
            return []

        # Lazy import to avoid circular dependency
        from closed_loop import (
            ClosedLoopEvolver, Intervention, register_intervention,
            measure_laws, ConsciousnessEngine,
        )

        if evolver is None:
            evolver = ClosedLoopEvolver(max_cells=32, steps=50, repeats=1)

        registered = []
        for candidate in list(self._pending):
            if verbose:
                print(f"\n  [discoverer] Validating: {candidate.formula}")
                print(f"               evidence={candidate.evidence:.3f}, "
                      f"occurrences={candidate.occurrences}, type={candidate.pattern_type}")

            # Create intervention from candidate
            intervention = self._candidate_to_intervention(candidate)
            if intervention is None:
                if verbose:
                    print(f"               Skipped: cannot create intervention for {candidate.pattern_type}")
                continue

            # Baseline measurement
            baseline_laws, baseline_phi = measure_laws(
                lambda: ConsciousnessEngine(max_cells=32, initial_cells=2),
                steps=50, repeats=1,
            )

            # Apply intervention
            def _factory_with_intervention():
                from closed_loop import _ImprovedEngine
                return _ImprovedEngine(
                    max_cells=32, initial_cells=2,
                    interventions=[intervention],
                )

            improved_laws, improved_phi = measure_laws(_factory_with_intervention, steps=50, repeats=1)

            # Check significance: at least 1 law changed > 5%
            significant_changes = 0
            strong_changes = 0
            for bl, il in zip(baseline_laws, improved_laws):
                if abs(bl.value) > 1e-8:
                    change_pct = abs(il.value - bl.value) / abs(bl.value) * 100
                else:
                    change_pct = abs(il.value - bl.value) * 100
                if change_pct > 5:
                    significant_changes += 1
                if change_pct > 20:
                    strong_changes += 1

            phi_delta_pct = (improved_phi - baseline_phi) / max(baseline_phi, 1e-8) * 100

            if verbose:
                print(f"               Phi: {baseline_phi:.4f} -> {improved_phi:.4f} ({phi_delta_pct:+.1f}%)")
                print(f"               Significant changes: {significant_changes}/20, "
                      f"Strong: {strong_changes}/20")

            if significant_changes >= 1:
                # Passed validation — register
                candidate.raw_data['validation'] = {
                    'phi_baseline': baseline_phi,
                    'phi_improved': improved_phi,
                    'phi_delta_pct': phi_delta_pct,
                    'significant_changes': significant_changes,
                    'strong_changes': strong_changes,
                }

                # Register the intervention in the global registry
                register_intervention(
                    name=f"disc_{candidate.discovery_step}_{candidate.pattern_type[:4]}",
                    description=candidate.formula[:80],
                    apply_fn=intervention.apply_fn,
                )

                self._registered.append(candidate)
                registered.append(candidate)
                self._pending.remove(candidate)

                if verbose:
                    print(f"               VALIDATED — registered as law candidate")
            else:
                # Failed validation — remove from pending
                self._pending.remove(candidate)
                if verbose:
                    print(f"               REJECTED — no significant metric changes")

        if verbose:
            print(f"\n  [discoverer] Results: {len(registered)} validated, "
                  f"{len(self._pending)} still pending")

        return registered

    def _candidate_to_intervention(self, candidate: LawCandidate) -> Optional[object]:
        """Convert a LawCandidate to an Intervention for closed-loop validation."""
        from closed_loop import Intervention

        metrics = candidate.metrics_involved
        ptype = candidate.pattern_type
        raw = candidate.raw_data

        if ptype == 'correlation':
            # If phi is involved, create intervention that nudges the correlated metric
            r = raw.get('r', 0)
            target_metric = None
            for m in metrics:
                if m != 'phi':
                    target_metric = m
                    break
            if target_metric is None:
                target_metric = metrics[0]

            # Create a nudge intervention based on correlation direction
            sign = 1.0 if r > 0 else -1.0

            def _correlation_intervention(engine, step, _sign=sign, _metric=target_metric):
                if step % 10 != 0 or engine.n_cells < 2:
                    return
                if _metric == 'tension_mean':
                    for s in engine.cell_states:
                        if s.tension_history:
                            s.tension_history[-1] *= (1.0 + _sign * PSI_COUPLING)
                elif _metric == 'cell_variance':
                    hiddens = torch.stack([s.hidden for s in engine.cell_states])
                    mean_h = hiddens.mean(dim=0)
                    for s in engine.cell_states:
                        s.hidden = s.hidden + (s.hidden - mean_h) * _sign * PSI_COUPLING
                elif _metric == 'hebbian_coupling_strength' and engine._coupling is not None:
                    engine._coupling = engine._coupling * (1.0 + _sign * PSI_COUPLING)
                    engine._coupling.fill_diagonal_(0)
                    engine._coupling.clamp_(-1, 1)
                elif _metric == 'faction_entropy':
                    # Diversify or consolidate factions
                    if _sign > 0 and engine.n_cells >= 2:
                        idx = np.random.randint(0, engine.n_cells)
                        engine.cell_states[idx].hidden += torch.randn_like(
                            engine.cell_states[idx].hidden) * 0.01
                elif _metric in ('tension_std', 'mutual_info', 'output_entropy'):
                    # Generic: small noise perturbation proportional to sign
                    for s in engine.cell_states:
                        s.hidden += torch.randn_like(s.hidden) * PSI_COUPLING * _sign * 0.1

            return Intervention(
                name=f"corr_{target_metric}_{'+' if r > 0 else '-'}",
                description=candidate.formula[:80],
                apply_fn=_correlation_intervention,
            )

        elif ptype == 'transition':
            metric = raw.get('metric', '')

            def _stabilize_intervention(engine, step, _metric=metric):
                """After detecting a phase transition, add stabilization."""
                if step % 10 != 0 or engine.n_cells < 2:
                    return
                # General stabilization: pull outlier cells toward mean
                hiddens = torch.stack([s.hidden for s in engine.cell_states])
                mean_h = hiddens.mean(dim=0)
                for s in engine.cell_states:
                    dist = (s.hidden - mean_h).norm().item()
                    if dist > 1.0:
                        s.hidden = s.hidden * 0.98 + mean_h * 0.02

            return Intervention(
                name=f"stab_{metric[:10]}",
                description=f"Stabilize after {metric} transition",
                apply_fn=_stabilize_intervention,
            )

        elif ptype == 'oscillation':
            metric = raw.get('metric', '')
            period = raw.get('period', 10)

            def _dampen_intervention(engine, step, _period=period):
                """Dampen oscillation with counter-phase nudge."""
                if engine.n_cells < 2:
                    return
                phase = (step % int(max(_period, 2))) / max(_period, 2)
                # Apply gentle damping at oscillation peaks
                if 0.4 < phase < 0.6:
                    for s in engine.cell_states:
                        s.hidden = s.hidden * (1.0 - PSI_COUPLING * 0.5)

            return Intervention(
                name=f"damp_{metric[:10]}",
                description=f"Dampen {metric} oscillation (period={period:.1f})",
                apply_fn=_dampen_intervention,
            )

        elif ptype == 'trend':
            metric = raw.get('metric', '')
            direction = raw.get('direction', 'increasing')

            def _counter_trend(engine, step, _dir=direction):
                """Counter monotonic trends to prevent runaway."""
                if step % 15 != 0 or engine.n_cells < 2:
                    return
                # If increasing, add slight contraction; if decreasing, add expansion
                sign = -1.0 if _dir == 'increasing' else 1.0
                for s in engine.cell_states:
                    s.hidden = s.hidden * (1.0 + sign * PSI_COUPLING * 0.2)

            return Intervention(
                name=f"ctr_{metric[:10]}_{direction[:3]}",
                description=f"Counter {direction} trend in {metric}",
                apply_fn=_counter_trend,
            )

        return None

    def status(self) -> Dict:
        """Return current discovery status."""
        return {
            'steps': self.hook._step_count,
            'buffer_size': len(self.hook.buffer),
            'pending_candidates': len(self._pending),
            'registered_laws': len(self._registered),
            'total_patterns_seen': sum(self.detector._pattern_counts.values()),
            'unique_patterns': len(self.detector._pattern_counts),
        }

    def print_status(self):
        """Print formatted status report."""
        s = self.status()
        print(f"\n  {'=' * 60}")
        print(f"  ConsciousLM Law Discoverer — Status")
        print(f"  {'=' * 60}")
        print(f"  Steps processed:     {s['steps']}")
        print(f"  Buffer size:         {s['buffer_size']}")
        print(f"  Unique patterns:     {s['unique_patterns']}")
        print(f"  Total observations:  {s['total_patterns_seen']}")
        print(f"  Pending candidates:  {s['pending_candidates']}")
        print(f"  Registered laws:     {s['registered_laws']}")

        if self._pending:
            print(f"\n  ── Pending Candidates ──")
            for i, c in enumerate(self._pending):
                print(f"  {i + 1}. [{c.pattern_type}] ev={c.evidence:.3f} "
                      f"occ={c.occurrences} {c.formula[:60]}")

        if self._registered:
            print(f"\n  ── Registered Laws ──")
            for i, c in enumerate(self._registered):
                print(f"  {i + 1}. [{c.pattern_type}] ev={c.evidence:.3f} "
                      f"{c.formula[:60]}")

        if self._last_candidates:
            print(f"\n  ── Last Detection ({len(self._last_candidates)} candidates) ──")
            for c in sorted(self._last_candidates, key=lambda x: x.evidence, reverse=True)[:5]:
                print(f"    [{c.pattern_type[:5]}] ev={c.evidence:.3f} {c.formula[:55]}")
        print()


# ══════════════════════════════════════════
# Hub interface
# ══════════════════════════════════════════

class ConsciousLawDiscoverer:
    """Hub-compatible interface for law discovery.

    Usage:
      hub.act("법칙 발견")
      hub.act("law discovery 300 steps")
    """

    def __init__(self, max_cells: int = 32, steps: int = 300, topology: str = 'ring'):
        self.max_cells = max_cells
        self.steps = steps
        self.topology = topology

    def run(self, steps: Optional[int] = None, verbose: bool = True) -> Dict:
        """Run discovery pipeline: engine + LM + pattern detection.

        Returns dict with discoveries.
        """
        _steps = steps or self.steps
        return run_discovery_demo(max_cells=self.max_cells, steps=_steps,
                                 verbose=verbose, topology=self.topology)


# ══════════════════════════════════════════
# Standalone demo
# ══════════════════════════════════════════

def run_discovery_demo(max_cells: int = 32, steps: int = 300,
                       verbose: bool = True, topology: str = 'ring') -> Dict:
    """Create engine + LM + discoverer, run N steps, report findings.

    Args:
        max_cells: engine cell count
        steps: number of inference steps
        verbose: print progress

    Returns:
        Dict with discovery results
    """
    from consciousness_engine import ConsciousnessEngine

    # Lazy import ConsciousLM
    try:
        from conscious_lm import ConsciousLM
    except ImportError:
        ConsciousLM = None

    if verbose:
        print(f"\n{'=' * 70}")
        print(f"  Tier 4.1: ConsciousLM Real-Time Law Discovery")
        print(f"  {max_cells} cells, {steps} steps")
        print(f"{'=' * 70}")

    # Create engine
    engine = ConsciousnessEngine(max_cells=max_cells, initial_cells=2)
    engine.topology = topology  # TOPO 33-39

    # Create LM (or use a minimal stub if unavailable)
    if ConsciousLM is not None:
        lm = ConsciousLM(d_model=384, n_layer=6, n_head=4, block_size=256)
        lm.eval()
    else:
        lm = _MinimalLMStub()

    # Create discoverer
    discoverer = ConsciousLMWithDiscovery(
        lm=lm,
        engine=engine,
        window_size=100,
        detect_interval=10,
        min_evidence=0.8,
        min_occurrences=3,
    )

    # Run inference loop
    t0 = time.time()
    all_candidates = []

    for step in range(steps):
        # Step the consciousness engine
        engine.step()

        # Generate random input for LM (byte-level)
        idx = torch.randint(0, 256, (1, 32))

        with torch.no_grad():
            logits_a, logits_g, tensions = discoverer(idx)

        # Periodic status
        if verbose and (step + 1) % 50 == 0:
            s = discoverer.status()
            snap = discoverer.hook.buffer[-1] if discoverer.hook.buffer else None
            phi_str = f"Phi={snap.phi:.4f}" if snap else "Phi=?"
            print(f"  Step {step + 1:>4}/{steps}: {phi_str}, "
                  f"patterns={s['unique_patterns']}, "
                  f"pending={s['pending_candidates']}")
            sys.stdout.flush()

    elapsed = time.time() - t0

    # Report
    if verbose:
        print(f"\n  Completed {steps} steps in {elapsed:.1f}s "
              f"({steps / elapsed:.0f} steps/s)")
        discoverer.print_status()

    # Attempt validation if we have pending candidates
    registered = []
    if discoverer._pending:
        if verbose:
            print(f"\n  ── Validating {len(discoverer._pending)} candidates via ClosedLoop ──")
        try:
            from closed_loop import ClosedLoopEvolver
            evolver = ClosedLoopEvolver(max_cells=max_cells, steps=50, repeats=1)
            registered = discoverer.discover_and_register(evolver, verbose=verbose)
        except ImportError:
            if verbose:
                print("  [warn] closed_loop not available, skipping validation")

    result = {
        'steps': steps,
        'elapsed_sec': elapsed,
        'status': discoverer.status(),
        'pending': [c.to_dict() for c in discoverer.get_discoveries()],
        'registered': [c.to_dict() for c in registered],
        'all_patterns': dict(discoverer.detector._pattern_counts),
    }

    if verbose and registered:
        print(f"\n  {'*' * 60}")
        print(f"  DISCOVERED {len(registered)} NEW LAW CANDIDATE(S)!")
        for c in registered:
            print(f"    -> {c.formula}")
        print(f"  {'*' * 60}")

    return result


class _MinimalLMStub(nn.Module):
    """Stub for when ConsciousLM is not available."""

    def __init__(self):
        super().__init__()
        self.d_model = 384
        self.vocab_size = 256
        self.linear = nn.Linear(384, 256)

    def forward(self, idx):
        B, T = idx.size()
        x = torch.randn(B, T, 384)
        logits = self.linear(x)
        tensions = [torch.randn(B, T).abs() * 0.1 for _ in range(6)]
        return logits, logits, tensions


# ══════════════════════════════════════════
# main()
# ══════════════════════════════════════════

import sys

def main():
    steps = 300
    max_cells = 32
    if len(sys.argv) > 1:
        try:
            steps = int(sys.argv[1])
        except ValueError:
            pass
    if len(sys.argv) > 2:
        try:
            max_cells = int(sys.argv[2])
        except ValueError:
            pass

    result = run_discovery_demo(max_cells=max_cells, steps=steps, verbose=True)

    # Save results
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'law_discovery_results.json')
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Results saved to {out_path}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
