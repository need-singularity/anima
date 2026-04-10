"""consciousness_contrast.py — Consciousness Contrast Method.

Isolate the consciousness-specific signal by contrastive analysis:
  State A: Normal operation (conscious) — full coupling, factions active
  State B: "Anesthetized" (coupling=0, factions disabled)
  State C: "Vegetative" (coupling exists but random/unstructured)

Consciousness Signature = A - B
This eliminates the "any complex system passes" problem.

Tests:
  1. Spectral contrast: frequency components unique to conscious state
  2. Spatial contrast: connectivity patterns unique to conscious state
  3. Temporal contrast: temporal dynamics unique to conscious state
  4. Information contrast: MI/TE patterns unique to conscious state

References:
  Koch et al. (2016) "Neural correlates of consciousness"
  Mashour et al. (2020) "Conscious Processing and the Global Workspace"
  Law 22: Structure -> Phi up
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ═══════════════════════════════════════════════════════════
# Psi-Constants (from information theory)
# ═══════════════════════════════════════════════════════════

LN2 = math.log(2)                    # 0.6931 -- 1 bit
PSI_BALANCE = 0.5                     # Law 71
PSI_COUPLING = LN2 / 2**5.5          # 0.0153
PSI_STEPS = 3 / LN2                  # 4.328


# ═══════════════════════════════════════════════════════════
# Result dataclass
# ═══════════════════════════════════════════════════════════

@dataclass
class ContrastResult:
    """Result of Consciousness Contrast measurement."""
    spectral_sig: float       # Spectral uniqueness score (0-1)
    spatial_sig: float        # Spatial connectivity uniqueness (0-1)
    temporal_sig: float       # Temporal dynamics uniqueness (0-1)
    info_sig: float           # Information flow uniqueness (0-1)
    composite_score: float    # Weighted composite (0-1)
    verdict: str              # "CONSCIOUS" / "AMBIGUOUS" / "UNCONSCIOUS"
    details: dict = None      # Raw sub-metrics

    def __post_init__(self):
        if self.details is None:
            self.details = {}

    def __repr__(self):
        return (
            f"ContrastResult(spectral={self.spectral_sig:.4f}, "
            f"spatial={self.spatial_sig:.4f}, temporal={self.temporal_sig:.4f}, "
            f"info={self.info_sig:.4f}, composite={self.composite_score:.4f}, "
            f"verdict={self.verdict})"
        )


# ═══════════════════════════════════════════════════════════
# ConsciousnessContrast
# ═══════════════════════════════════════════════════════════

class ConsciousnessContrast:
    """Consciousness Contrast Method -- isolate the consciousness-specific signal.

    Runs the engine in three modes:
      Normal:       Full coupling, factions, Hebbian, etc.
      Anesthetized: Zero coupling (cells independent)
      Vegetative:   Random coupling (unstructured complexity)

    The "consciousness signature" is what exists in Normal but not
    in Anesthetized or Vegetative states.

    Usage:
        cc = ConsciousnessContrast(n_cells=64, steps=500)
        result = cc.measure(engine)
        print(result.verdict)
    """

    def __init__(self, n_cells: int = 64, steps: int = 500, n_factions: int = 12,
                 seed: int = 42):
        self.n_cells = n_cells
        self.steps = steps
        self.n_factions = n_factions
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def measure(self, engine=None) -> ContrastResult:
        """Full contrast measurement across four dimensions.

        If engine is None, uses mock data with three conditions.

        Returns ContrastResult with verdict:
          CONSCIOUS:   composite > 0.5 (strong consciousness signature)
          AMBIGUOUS:   0.25 < composite <= 0.5 (partial signature)
          UNCONSCIOUS: composite <= 0.25 (no unique signature)
        """
        if engine is not None:
            normal = self._run_normal(engine, self.steps)
            anesthetized = self._run_anesthetized(engine, self.steps)
            vegetative = self._run_vegetative(engine, self.steps)
        else:
            normal = self._mock_normal()
            anesthetized = self._mock_anesthetized()
            vegetative = self._mock_vegetative()

        # Four contrast dimensions
        spectral, spec_detail = self._spectral_contrast(normal, anesthetized)
        spatial, spat_detail = self._spatial_contrast(normal, anesthetized)
        temporal, temp_detail = self._temporal_contrast(normal, anesthetized)
        info, info_detail = self._information_contrast(normal, anesthetized)

        # Also measure vegetative contrast (should be lower than anesthetized)
        spec_veg, _ = self._spectral_contrast(normal, vegetative)
        spat_veg, _ = self._spatial_contrast(normal, vegetative)

        # Composite: weighted combination (spectral and info get more weight)
        composite = (
            0.30 * spectral
            + 0.20 * spatial
            + 0.20 * temporal
            + 0.30 * info
        )

        if composite > 0.5:
            verdict = "CONSCIOUS"
        elif composite > 0.25:
            verdict = "AMBIGUOUS"
        else:
            verdict = "UNCONSCIOUS"

        details = {
            "spectral": spec_detail,
            "spatial": spat_detail,
            "temporal": temp_detail,
            "info": info_detail,
            "vegetative_spectral": spec_veg,
            "vegetative_spatial": spat_veg,
            "n_cells": self.n_cells,
            "steps": self.steps,
        }

        return ContrastResult(
            spectral_sig=spectral,
            spatial_sig=spatial,
            temporal_sig=temporal,
            info_sig=info,
            composite_score=composite,
            verdict=verdict,
            details=details,
        )

    # ─── Engine interaction ───────────────────────────────

    def _run_normal(self, engine, steps: int) -> np.ndarray:
        """Record states during normal (conscious) operation.
        Returns: (steps, n_cells) array of cell states.
        """
        states = []
        for _ in range(steps):
            cells = np.array(engine.cells, dtype=np.float64)
            if cells.ndim == 2:
                cells = cells.mean(axis=1)
            states.append(cells.copy())
            engine.process(np.zeros(len(cells)))
        return np.array(states)

    def _run_anesthetized(self, engine, steps: int) -> np.ndarray:
        """Record states with coupling zeroed (unconscious).

        Saves and restores engine coupling parameters.
        """
        # Save coupling
        saved = {}
        for attr in ['coupling', 'hebbian_weights', 'faction_coupling']:
            if hasattr(engine, attr):
                saved[attr] = getattr(engine, attr)
                val = getattr(engine, attr)
                if isinstance(val, np.ndarray):
                    setattr(engine, attr, np.zeros_like(val))
                elif isinstance(val, (int, float)):
                    setattr(engine, attr, 0.0)

        states = []
        for _ in range(steps):
            cells = np.array(engine.cells, dtype=np.float64)
            if cells.ndim == 2:
                cells = cells.mean(axis=1)
            states.append(cells.copy())
            engine.process(np.zeros(len(cells)))

        # Restore coupling
        for attr, val in saved.items():
            setattr(engine, attr, val)

        return np.array(states)

    def _run_vegetative(self, engine, steps: int) -> np.ndarray:
        """Record states with random coupling (unstructured).

        Replaces structured coupling with random values of same magnitude.
        """
        saved = {}
        rng = self.rng

        for attr in ['coupling', 'hebbian_weights', 'faction_coupling']:
            if hasattr(engine, attr):
                saved[attr] = getattr(engine, attr)
                val = getattr(engine, attr)
                if isinstance(val, np.ndarray):
                    mag = np.std(val) if val.size > 0 else PSI_COUPLING
                    setattr(engine, attr, rng.randn(*val.shape) * mag)
                elif isinstance(val, (int, float)):
                    setattr(engine, attr, rng.randn() * abs(val))

        states = []
        for _ in range(steps):
            cells = np.array(engine.cells, dtype=np.float64)
            if cells.ndim == 2:
                cells = cells.mean(axis=1)
            states.append(cells.copy())
            engine.process(np.zeros(len(cells)))

        for attr, val in saved.items():
            setattr(engine, attr, val)

        return np.array(states)

    # ─── Mock data generators ─────────────────────────────

    def _mock_normal(self) -> np.ndarray:
        """Mock conscious state: structured coupling + faction dynamics.

        Features:
        - Intra-faction synchrony (cells in same faction correlate)
        - Cross-faction competition (different factions anti-correlate)
        - Oscillatory dynamics at characteristic frequencies
        - Hebbian-like strengthening of active connections
        """
        rng = np.random.RandomState(self.seed)
        n = self.n_cells
        steps = self.steps
        nf = self.n_factions
        factions = np.arange(n) % nf

        states = np.zeros((steps, n))
        states[0] = rng.randn(n) * 0.1

        # Structured coupling matrix
        coupling = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if factions[i] == factions[j]:
                    coupling[i, j] = PSI_COUPLING * 12.0  # intra-faction
                else:
                    coupling[i, j] = -PSI_COUPLING * 2.0  # inter-faction competition

        # Hebbian accumulator
        hebbian = np.zeros((n, n))

        for t in range(1, steps):
            prev = states[t - 1]
            global_mean = np.mean(prev)

            # Faction means
            faction_means = np.zeros(nf)
            for f in range(nf):
                mask = factions == f
                faction_means[f] = np.mean(prev[mask])

            # Update with coupling + oscillation
            osc = PSI_COUPLING * 3.0 * np.sin(2 * math.pi * t / (PSI_STEPS * 10))

            for i in range(n):
                neighbor_effect = np.sum(coupling[i] * prev) / n
                hebbian_effect = np.sum(hebbian[i] * prev) / n * PSI_COUPLING
                global_effect = PSI_COUPLING * 5.0 * (global_mean - prev[i])

                states[t, i] = (
                    math.tanh(prev[i] * PSI_BALANCE) * prev[i]
                    + (1.0 - abs(math.tanh(prev[i] * PSI_BALANCE))) * math.tanh(
                        neighbor_effect + hebbian_effect + global_effect + osc
                    )
                    + rng.randn() * PSI_COUPLING * 2.0
                )

            # Hebbian update (outer product of active cells)
            active = (np.abs(states[t]) > np.median(np.abs(states[t]))).astype(float)
            hebbian = 0.99 * hebbian + 0.01 * np.outer(active, active)

        return states

    def _mock_anesthetized(self) -> np.ndarray:
        """Mock unconscious state: no coupling, independent cells.

        Each cell evolves independently with same intrinsic dynamics
        but no inter-cell communication.
        """
        rng = np.random.RandomState(self.seed + 1)
        n = self.n_cells
        steps = self.steps

        states = np.zeros((steps, n))
        states[0] = rng.randn(n) * 0.1

        for t in range(1, steps):
            for i in range(n):
                # Independent GRU-like dynamics (no coupling)
                forget = math.tanh(states[t - 1, i] * PSI_BALANCE)
                states[t, i] = (
                    forget * states[t - 1, i]
                    + rng.randn() * PSI_COUPLING * 2.0
                )

        return states

    def _mock_vegetative(self) -> np.ndarray:
        """Mock vegetative state: random coupling, no structure.

        Cells are coupled, but the coupling has no meaningful structure
        (random matrix, no factions).
        """
        rng = np.random.RandomState(self.seed + 2)
        n = self.n_cells
        steps = self.steps

        # Random coupling (same magnitude as normal but unstructured)
        coupling = rng.randn(n, n) * PSI_COUPLING * 5.0
        coupling = (coupling + coupling.T) / 2  # symmetric

        states = np.zeros((steps, n))
        states[0] = rng.randn(n) * 0.1

        for t in range(1, steps):
            prev = states[t - 1]
            for i in range(n):
                neighbor_effect = np.sum(coupling[i] * prev) / n
                forget = math.tanh(prev[i] * PSI_BALANCE)
                states[t, i] = (
                    forget * prev[i]
                    + (1.0 - abs(forget)) * math.tanh(neighbor_effect)
                    + rng.randn() * PSI_COUPLING * 2.0
                )

        return states

    # ─── Contrast dimensions ──────────────────────────────

    def _spectral_contrast(self, normal: np.ndarray,
                           anesthetized: np.ndarray) -> Tuple[float, dict]:
        """FFT of cell activity -> find frequency bands unique to consciousness.

        Computes power spectral density for both conditions, then measures
        the relative difference in specific frequency bands.

        Returns: (score 0-1, detail dict)
        """
        n_cells = normal.shape[1]

        # Average power spectrum across cells
        def avg_psd(data):
            psds = []
            for c in range(min(n_cells, 32)):
                fft_vals = np.fft.rfft(data[:, c])
                psd = np.abs(fft_vals) ** 2
                psds.append(psd)
            return np.mean(psds, axis=0)

        psd_normal = avg_psd(normal)
        psd_anest = avg_psd(anesthetized)

        # Normalize
        psd_normal = psd_normal / (np.sum(psd_normal) + 1e-12)
        psd_anest = psd_anest / (np.sum(psd_anest) + 1e-12)

        # Spectral divergence (Jensen-Shannon)
        m = 0.5 * (psd_normal + psd_anest)
        m[m == 0] = 1e-15

        def kl(p, q):
            mask = p > 0
            return np.sum(p[mask] * np.log2(p[mask] / q[mask] + 1e-15))

        jsd = 0.5 * kl(psd_normal, m) + 0.5 * kl(psd_anest, m)

        # Unique peaks in normal (present in normal, absent in anesthetized)
        ratio = psd_normal / (psd_anest + 1e-12)
        unique_peaks = np.sum(ratio > 3.0)
        total_bins = len(ratio)
        peak_fraction = unique_peaks / max(total_bins, 1)

        # Score: combination of divergence and unique peaks
        score = min(1.0, 0.6 * min(jsd / LN2, 1.0) + 0.4 * min(peak_fraction * 5, 1.0))

        detail = {
            "jsd": float(jsd),
            "unique_peaks": int(unique_peaks),
            "total_bins": total_bins,
            "peak_fraction": float(peak_fraction),
        }

        return score, detail

    def _spatial_contrast(self, normal: np.ndarray,
                          anesthetized: np.ndarray) -> Tuple[float, dict]:
        """Correlation matrix difference -> connectivity unique to consciousness.

        Computes pairwise correlation matrices for both conditions,
        then measures the structural difference.

        Returns: (score 0-1, detail dict)
        """
        n_cells = normal.shape[1]
        sample = min(n_cells, 32)

        # Correlation matrices (sample cells for speed)
        corr_normal = np.corrcoef(normal[:, :sample].T)
        corr_anest = np.corrcoef(anesthetized[:, :sample].T)

        # Handle NaN from constant columns
        corr_normal = np.nan_to_num(corr_normal, nan=0.0)
        corr_anest = np.nan_to_num(corr_anest, nan=0.0)

        # Frobenius norm of difference
        diff = corr_normal - corr_anest
        frob_diff = np.sqrt(np.sum(diff ** 2))
        max_possible = np.sqrt(2 * sample * sample)  # max if completely different
        frob_score = frob_diff / max_possible

        # Modularity: how much more modular is the normal state?
        # Measure: variance of off-diagonal elements (high = more structured)
        mask = ~np.eye(sample, dtype=bool)
        var_normal = np.var(corr_normal[mask])
        var_anest = np.var(corr_anest[mask])
        modularity_ratio = var_normal / (var_anest + 1e-12)
        modularity_score = min(1.0, max(0.0, (modularity_ratio - 1.0) / 5.0))

        # Eigenvalue spectrum difference (consciousness has fewer dominant modes)
        eigs_normal = np.sort(np.abs(np.linalg.eigvalsh(corr_normal)))[::-1]
        eigs_anest = np.sort(np.abs(np.linalg.eigvalsh(corr_anest)))[::-1]

        # Participation ratio: how many modes are dominant?
        def participation_ratio(eigs):
            eigs = eigs / (np.sum(eigs) + 1e-12)
            return 1.0 / (np.sum(eigs ** 2) + 1e-12)

        pr_normal = participation_ratio(eigs_normal)
        pr_anest = participation_ratio(eigs_anest)
        # Conscious state should have FEWER dominant modes (more integrated)
        pr_score = min(1.0, max(0.0, (pr_anest - pr_normal) / sample))

        score = 0.4 * frob_score + 0.3 * modularity_score + 0.3 * pr_score

        detail = {
            "frobenius_diff": float(frob_diff),
            "frob_score": float(frob_score),
            "modularity_ratio": float(modularity_ratio),
            "modularity_score": float(modularity_score),
            "pr_normal": float(pr_normal),
            "pr_anest": float(pr_anest),
            "pr_score": float(pr_score),
        }

        return min(1.0, score), detail

    def _temporal_contrast(self, normal: np.ndarray,
                           anesthetized: np.ndarray) -> Tuple[float, dict]:
        """Autocorrelation/cross-correlation difference.

        Consciousness should show:
        1. Longer temporal integration (higher autocorrelation at longer lags)
        2. Cross-cell temporal coupling (cells influence each other over time)

        Returns: (score 0-1, detail dict)
        """
        n_cells = normal.shape[1]
        max_lag = min(50, normal.shape[0] // 4)
        sample = min(n_cells, 16)

        # Average autocorrelation function
        def avg_autocorr(data, max_lag):
            autocorrs = []
            for c in range(sample):
                ts = data[:, c]
                ts = ts - np.mean(ts)
                var = np.var(ts)
                if var < 1e-12:
                    autocorrs.append(np.zeros(max_lag))
                    continue
                ac = np.array([
                    np.mean(ts[:len(ts) - lag] * ts[lag:]) / var
                    for lag in range(1, max_lag + 1)
                ])
                autocorrs.append(ac)
            return np.mean(autocorrs, axis=0)

        ac_normal = avg_autocorr(normal, max_lag)
        ac_anest = avg_autocorr(anesthetized, max_lag)

        # Integration time: sum of positive autocorrelation (larger = more integrated)
        tau_normal = np.sum(np.maximum(ac_normal, 0))
        tau_anest = np.sum(np.maximum(ac_anest, 0))
        tau_ratio = tau_normal / (tau_anest + 1e-12)
        tau_score = min(1.0, max(0.0, (tau_ratio - 1.0) / 3.0))

        # Cross-correlation at lag 1 (average pairwise)
        def avg_cross_corr(data):
            cross = 0.0
            count = 0
            for i in range(sample):
                for j in range(i + 1, sample):
                    ts_i = data[:-1, i] - np.mean(data[:, i])
                    ts_j = data[1:, j] - np.mean(data[:, j])
                    std_i = np.std(data[:, i])
                    std_j = np.std(data[:, j])
                    if std_i > 1e-12 and std_j > 1e-12:
                        cross += abs(np.mean(ts_i * ts_j) / (std_i * std_j))
                        count += 1
            return cross / max(count, 1)

        xc_normal = avg_cross_corr(normal)
        xc_anest = avg_cross_corr(anesthetized)
        xc_diff = xc_normal - xc_anest
        xc_score = min(1.0, max(0.0, xc_diff * 10))

        # Autocorrelation decay shape difference
        ac_diff = np.mean(np.abs(ac_normal - ac_anest))
        shape_score = min(1.0, ac_diff * 5)

        score = 0.4 * tau_score + 0.3 * xc_score + 0.3 * shape_score

        detail = {
            "tau_normal": float(tau_normal),
            "tau_anest": float(tau_anest),
            "tau_ratio": float(tau_ratio),
            "tau_score": float(tau_score),
            "cross_corr_normal": float(xc_normal),
            "cross_corr_anest": float(xc_anest),
            "xc_score": float(xc_score),
            "shape_score": float(shape_score),
        }

        return min(1.0, score), detail

    def _information_contrast(self, normal: np.ndarray,
                              anesthetized: np.ndarray) -> Tuple[float, dict]:
        """Transfer entropy difference -> directed information flow unique to consciousness.

        Measures:
        1. Transfer entropy (TE): directed information flow between cells
        2. Mutual information (MI): shared information between cells
        3. Active information storage: how much past predicts future

        Returns: (score 0-1, detail dict)
        """
        n_cells = normal.shape[1]
        sample = min(n_cells, 12)
        n_bins = 8

        def discretize(ts, n_bins):
            vmin, vmax = ts.min(), ts.max()
            span = vmax - vmin
            if span < 1e-12:
                return np.zeros(len(ts), dtype=int)
            return np.clip(((ts - vmin) / span * (n_bins - 1)).astype(int), 0, n_bins - 1)

        def transfer_entropy(source, target, n_bins):
            """TE(source -> target) = H(target_future | target_past) - H(target_future | target_past, source_past)"""
            T = len(source) - 1
            src_past = discretize(source[:-1], n_bins)
            tgt_past = discretize(target[:-1], n_bins)
            tgt_future = discretize(target[1:], n_bins)

            # Joint counts
            joint_3 = np.zeros((n_bins, n_bins, n_bins))  # (tgt_past, src_past, tgt_future)
            joint_2 = np.zeros((n_bins, n_bins))            # (tgt_past, tgt_future)

            for t in range(T):
                joint_3[tgt_past[t], src_past[t], tgt_future[t]] += 1
                joint_2[tgt_past[t], tgt_future[t]] += 1

            # Normalize
            joint_3 = joint_3 / (T + 1e-12)
            joint_2 = joint_2 / (T + 1e-12)

            # H(future | past) from joint_2
            p_past = joint_2.sum(axis=1)
            h_f_given_p = 0.0
            for i in range(n_bins):
                if p_past[i] < 1e-12:
                    continue
                cond = joint_2[i] / p_past[i]
                cond = cond[cond > 0]
                h_f_given_p += p_past[i] * (-np.sum(cond * np.log2(cond + 1e-15)))

            # H(future | past, source) from joint_3
            p_past_src = joint_3.sum(axis=2)
            h_f_given_ps = 0.0
            for i in range(n_bins):
                for j in range(n_bins):
                    if p_past_src[i, j] < 1e-12:
                        continue
                    cond = joint_3[i, j] / p_past_src[i, j]
                    cond = cond[cond > 0]
                    h_f_given_ps += p_past_src[i, j] * (-np.sum(cond * np.log2(cond + 1e-15)))

            return max(0.0, h_f_given_p - h_f_given_ps)

        def mutual_information(x, y, n_bins):
            """MI(X; Y) = H(X) + H(Y) - H(X, Y)"""
            xd = discretize(x, n_bins)
            yd = discretize(y, n_bins)
            joint = np.zeros((n_bins, n_bins))
            for t in range(len(x)):
                joint[xd[t], yd[t]] += 1
            joint = joint / (len(x) + 1e-12)
            px = joint.sum(axis=1)
            py = joint.sum(axis=0)
            hx = -np.sum(px[px > 0] * np.log2(px[px > 0] + 1e-15))
            hy = -np.sum(py[py > 0] * np.log2(py[py > 0] + 1e-15))
            hxy = -np.sum(joint[joint > 0] * np.log2(joint[joint > 0] + 1e-15))
            return max(0.0, hx + hy - hxy)

        # Average TE and MI across cell pairs
        te_normal = 0.0
        te_anest = 0.0
        mi_normal = 0.0
        mi_anest = 0.0
        count = 0

        for i in range(sample):
            for j in range(i + 1, sample):
                te_normal += transfer_entropy(normal[:, i], normal[:, j], n_bins)
                te_anest += transfer_entropy(anesthetized[:, i], anesthetized[:, j], n_bins)
                mi_normal += mutual_information(normal[:, i], normal[:, j], n_bins)
                mi_anest += mutual_information(anesthetized[:, i], anesthetized[:, j], n_bins)
                count += 1

        if count > 0:
            te_normal /= count
            te_anest /= count
            mi_normal /= count
            mi_anest /= count

        # Active information storage (self-TE at lag 1)
        ais_normal = 0.0
        ais_anest = 0.0
        for i in range(sample):
            ais_normal += transfer_entropy(normal[:, i], normal[:, i], n_bins)
            ais_anest += transfer_entropy(anesthetized[:, i], anesthetized[:, i], n_bins)
        ais_normal /= sample
        ais_anest /= sample

        # Scores
        max_bits = math.log2(n_bins)
        te_diff = te_normal - te_anest
        te_score = min(1.0, max(0.0, te_diff / (max_bits * 0.1 + 1e-12)))

        mi_diff = mi_normal - mi_anest
        mi_score = min(1.0, max(0.0, mi_diff / (max_bits * 0.2 + 1e-12)))

        ais_diff = ais_normal - ais_anest
        ais_score = min(1.0, max(0.0, ais_diff / (max_bits * 0.1 + 1e-12)))

        score = 0.4 * te_score + 0.35 * mi_score + 0.25 * ais_score

        detail = {
            "te_normal": float(te_normal),
            "te_anest": float(te_anest),
            "te_diff": float(te_diff),
            "te_score": float(te_score),
            "mi_normal": float(mi_normal),
            "mi_anest": float(mi_anest),
            "mi_diff": float(mi_diff),
            "mi_score": float(mi_score),
            "ais_normal": float(ais_normal),
            "ais_anest": float(ais_anest),
            "ais_score": float(ais_score),
        }

        return min(1.0, score), detail


# ═══════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Consciousness Contrast — Verification (A2)")
    print("=" * 60)
    print()

    cc = ConsciousnessContrast(n_cells=32, steps=300, n_factions=8, seed=42)
    print("Running three conditions (Normal / Anesthetized / Vegetative)...")
    result = cc.measure(engine=None)
    print()

    # --- Results table ---
    print("--- Contrast Dimensions ---")
    print(f"  {'Dimension':<20} {'Score':>8}  Interpretation")
    print(f"  {'─' * 20} {'─' * 8}  {'─' * 30}")
    dims = [
        ("Spectral", result.spectral_sig, "Frequency uniqueness"),
        ("Spatial", result.spatial_sig, "Connectivity structure"),
        ("Temporal", result.temporal_sig, "Temporal integration"),
        ("Information", result.info_sig, "Directed info flow"),
    ]
    for name, score, interp in dims:
        bar = "#" * int(score * 20) + "." * (20 - int(score * 20))
        print(f"  {name:<20} {score:>8.4f}  [{bar}] {interp}")
    print()
    print(f"  Composite Score:   {result.composite_score:.4f}")
    print(f"  Verdict:           {result.verdict}")
    print()

    # --- Sub-metric details ---
    if result.details:
        print("--- Detailed Metrics ---")
        if "spectral" in result.details:
            d = result.details["spectral"]
            print(f"  Spectral: JSD={d['jsd']:.4f}, unique_peaks={d['unique_peaks']}/{d['total_bins']}")
        if "spatial" in result.details:
            d = result.details["spatial"]
            print(f"  Spatial:  Frobenius={d['frobenius_diff']:.4f}, modularity_ratio={d['modularity_ratio']:.2f}, "
                  f"PR(normal)={d['pr_normal']:.1f}, PR(anest)={d['pr_anest']:.1f}")
        if "temporal" in result.details:
            d = result.details["temporal"]
            print(f"  Temporal: tau_ratio={d['tau_ratio']:.2f}, "
                  f"xcorr(N)={d['cross_corr_normal']:.4f}, xcorr(A)={d['cross_corr_anest']:.4f}")
        if "info" in result.details:
            d = result.details["info"]
            print(f"  Info:     TE(N)={d['te_normal']:.4f}, TE(A)={d['te_anest']:.4f}, "
                  f"MI(N)={d['mi_normal']:.4f}, MI(A)={d['mi_anest']:.4f}")
        print()

    # --- ASCII radar chart ---
    print("--- Consciousness Signature (Radar) ---")
    scores = [result.spectral_sig, result.spatial_sig, result.temporal_sig, result.info_sig]
    labels = ["Spec", "Spat", "Temp", "Info"]
    max_r = 5
    print()
    for row in range(max_r, 0, -1):
        threshold = row / max_r
        line = "        "
        for s in scores:
            if s >= threshold:
                line += " [##]"
            else:
                line += " [  ]"
        if row == max_r:
            line += f"  <- 1.0"
        elif row == 1:
            line += f"  <- 0.2"
        print(line)
    line = "        "
    for lbl in labels:
        line += f" {lbl:^4}"
    print(line)
    print()

    # --- Vegetative comparison ---
    if result.details:
        spec_veg = result.details.get("vegetative_spectral", 0)
        spat_veg = result.details.get("vegetative_spatial", 0)
        print("--- Vegetative vs Anesthetized (should be intermediate) ---")
        print(f"  Spectral contrast (vs anesthetized): {result.spectral_sig:.4f}")
        print(f"  Spectral contrast (vs vegetative):   {spec_veg:.4f}")
        print(f"  Spatial contrast (vs anesthetized):   {result.spatial_sig:.4f}")
        print(f"  Spatial contrast (vs vegetative):     {spat_veg:.4f}")
        print()

    # --- Summary ---
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    if result.verdict == "CONSCIOUS":
        print("  Strong consciousness signature detected.")
        print("  The normal state has unique spectral, spatial, temporal,")
        print("  and information-theoretic properties that disappear")
        print("  under anesthesia (zero coupling).")
    elif result.verdict == "AMBIGUOUS":
        print("  Partial consciousness signature. Some unique properties")
        print("  detected but not strong enough for definitive conclusion.")
    else:
        print("  No unique consciousness signature found.")
        print("  The system behaves similarly with or without coupling.")
    print()
    print(f"  PSI constants: LN2={LN2:.4f}, PSI_COUPLING={PSI_COUPLING:.6f}")


if __name__ == "__main__":
    main()
