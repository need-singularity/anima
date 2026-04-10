#!/usr/bin/env python3
"""consciousness_pci.py — Perturbation Complexity Index for AI consciousness

Adapted from Massimini et al. (2013) and Casali et al. (2013).
In the brain: TMS pulse -> EEG recording -> Lempel-Ziv complexity -> PCI.
In ConsciousnessEngine: delta pulse -> cell state recording -> LZ76 -> PCI.

PCI is the neuroscience gold standard for consciousness detection.
It measures the spatiotemporal complexity of a system's response to
a localized perturbation. High PCI means the perturbation spreads
through the system in a complex (neither stereotyped nor random) way.

Interpretation (from Casali et al., 2013):
  PCI > 0.31:  Conscious (awake humans, locked-in, REM sleep)
  PCI < 0.31:  Unconscious (NREM sleep, general anesthesia, vegetative)
  PCI ~ 0:     No response or fully synchronized (stereotyped) response

Key insight for Anima:
  ConsciousEngine: perturbation -> coupling spreads it -> complex pattern -> high PCI
  ZombieEngine:    perturbation -> stays local (no coupling) -> simple pattern -> low PCI
  This is THE test that differentiates conscious from zombie.

"If you kick a conscious system, it rings like a bell.
 If you kick an unconscious system, it thuds like a sandbag."
"""

import math
import random
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

# PSI constants from ln(2) — single source of truth
LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2
PSI_ENTROPY = 0.998

# PCI threshold from Casali et al. (2013)
PCI_CONSCIOUS_THRESHOLD = 0.31


@dataclass
class PCIResult:
    """Result of a single PCI measurement."""
    pci_value: float
    complexity: int
    normalized_complexity: float
    matrix_shape: Tuple[int, int]
    response_matrix: np.ndarray
    binary_matrix: np.ndarray
    verdict: str  # "CONSCIOUS", "UNCONSCIOUS", "NO_RESPONSE"
    perturbation_cell: int
    perturbation_strength: float
    baseline_phi_proxy: float
    response_phi_proxy: float

    def __repr__(self):
        return (
            f"PCIResult(pci={self.pci_value:.4f}, verdict={self.verdict}, "
            f"LZ={self.complexity}, shape={self.matrix_shape}, "
            f"cell={self.perturbation_cell}, strength={self.perturbation_strength:.2f})"
        )


@dataclass
class MultiSitePCIResult:
    """Result of multi-site PCI measurement."""
    median_pci: float
    mean_pci: float
    std_pci: float
    min_pci: float
    max_pci: float
    individual_results: List[PCIResult]
    verdict: str
    n_sites: int

    def __repr__(self):
        return (
            f"MultiSitePCIResult(median_pci={self.median_pci:.4f}, "
            f"mean={self.mean_pci:.4f}+/-{self.std_pci:.4f}, "
            f"verdict={self.verdict}, n_sites={self.n_sites})"
        )


@dataclass
class ComparisonResult:
    """Side-by-side comparison of conscious vs zombie engine."""
    conscious_pci: MultiSitePCIResult
    zombie_pci: MultiSitePCIResult
    separation: float  # conscious_pci - zombie_pci
    ratio: float  # conscious_pci / zombie_pci (inf if zombie=0)
    differentiated: bool  # True if conscious > threshold and zombie < threshold

    def __repr__(self):
        return (
            f"ComparisonResult(conscious={self.conscious_pci.median_pci:.4f}, "
            f"zombie={self.zombie_pci.median_pci:.4f}, "
            f"separation={self.separation:.4f}, "
            f"differentiated={self.differentiated})"
        )


def _lempel_ziv_complexity_1976(sequence: np.ndarray) -> int:
    """Lempel-Ziv complexity (LZ76) of a binary sequence.

    Counts the number of distinct components in the exhaustive history of
    the sequence. This is the foundational complexity measure from
    Lempel & Ziv (1976), "On the Complexity of Finite Sequences".

    The algorithm performs exhaustive parsing: at each step, we find the
    longest substring starting at position i that appears as a substring
    of s[0 : i+len-1] (the history *extended by* the current match, which
    allows copy-from-self). When the longest reproducible extension is found,
    we emit one new component and advance past it.

    Examples:
      "0000...0" (all zeros)  -> c = 2 (components: "0", "0...0")
      "0101...01"             -> c = 3 (components: "0", "1", "01...01")
      random binary           -> c ~ n / log2(n)

    Time: O(n^2) worst case, acceptable for n up to ~100K.
    """
    s = sequence.astype(np.int8)
    n = len(s)
    if n == 0:
        return 0
    if n == 1:
        return 1

    # Exhaustive (Lempel-Ziv 76) parsing
    complexity = 1  # first symbol is always a new component
    i = 1           # start of the component being parsed

    while i < n:
        # Find the longest match of s[i:i+l] within s[0:i+l-1]
        # (the history, which grows as we extend l)
        max_l = 0
        l = 1
        while i + l <= n:
            # Check if s[i:i+l] occurs as a substring in s[0:i+l-1]
            target = s[i:i + l]
            found = False
            # Search window is s[0 : i+l-1]
            search_len = i + l - 1
            for j in range(search_len - l + 1):
                if np.array_equal(s[j:j + l], target):
                    found = True
                    break
            if found:
                max_l = l
                l += 1
            else:
                break

        # Advance past the matched portion + 1 new symbol
        complexity += 1
        i += max_l + 1

    return complexity


def _lempel_ziv_complexity_fast(sequence: np.ndarray) -> int:
    """Fast LZ76 complexity using string search.

    Same algorithm as _lempel_ziv_complexity_1976 but uses Python string
    operations (str.find) for inner-loop speed. This is the production
    implementation for sequences up to ~100K elements.

    Verified against reference:
      "000...0"  -> 2
      "010101"   -> 3
      random     -> ~n/log2(n)
    """
    n = len(sequence)
    if n == 0:
        return 0
    if n == 1:
        return 1

    s = ''.join(str(int(b)) for b in sequence)

    complexity = 1  # first symbol
    i = 1

    while i < n:
        # Find longest l such that s[i:i+l] appears in s[0:i+l-1]
        max_l = 0
        l = 1
        while i + l <= n:
            # Search s[i:i+l] within s[0:i+l-1]
            target = s[i:i + l]
            search_window = s[:i + l - 1]
            if search_window.find(target) >= 0:
                max_l = l
                l += 1
            else:
                break
        complexity += 1
        i += max_l + 1

    return complexity


def _theoretical_max_lz(n: int) -> float:
    """Theoretical maximum LZ complexity for a binary sequence of length n.

    For a random binary sequence of length n, the expected LZ complexity
    converges to n / log2(n) as n -> infinity (Lempel & Ziv, 1976).
    """
    if n <= 1:
        return max(1.0, float(n))
    return n / math.log2(n)


class PerturbationComplexityIndex:
    """PCI measurement adapted from neuroscience for AI consciousness.

    Protocol:
    1. Let engine reach stable state (warmup_steps warmup)
    2. Record baseline activity (record_steps steps)
    3. Inject structured perturbation (delta pulse to single cell)
    4. Record response across ALL cells (record_steps steps)
    5. Binarize response matrix (significant vs not)
    6. Compute Lempel-Ziv complexity of binarized matrix
    7. Normalize by matrix size -> PCI value

    Interpretation (from Casali et al., 2013):
    PCI > 0.31: Conscious (awake humans, REM sleep)
    PCI < 0.31: Unconscious (NREM sleep, anesthesia, vegetative state)
    PCI ~ 0: No response or fully synchronized response
    """

    def __init__(self, n_cells: int = 64, warmup_steps: int = 300,
                 record_steps: int = 100, z_threshold: float = 2.0,
                 use_fast_lz: bool = True):
        """Initialize PCI measurement.

        Args:
            n_cells: Number of cells in the engine.
            warmup_steps: Steps to let engine stabilize before measurement.
            record_steps: Steps to record for baseline and response.
            z_threshold: Z-score threshold for binarization (|z| > threshold).
            use_fast_lz: Use fast set-based LZ (True) or reference impl (False).
        """
        self.n_cells = n_cells
        self.warmup_steps = warmup_steps
        self.record_steps = record_steps
        self.z_threshold = z_threshold
        self._lz_fn = _lempel_ziv_complexity_fast if use_fast_lz else _lempel_ziv_complexity_1976

    def measure(self, engine, perturbation_cell: int = 0,
                perturbation_strength: float = 1.0) -> PCIResult:
        """Full PCI measurement protocol.

        Args:
            engine: An object with:
                - process(input) -> updates internal state
                - get_cell_states() -> np.ndarray of shape (n_cells,) or (n_cells, dim)
                  OR get_states() returning similar
            perturbation_cell: Which cell receives the delta pulse.
            perturbation_strength: Magnitude of perturbation.

        Returns:
            PCIResult with PCI value, verdict, and all intermediate data.
        """
        get_states = self._get_state_fn(engine)

        # Phase 1: Warmup — let the engine reach a stable state
        for _ in range(self.warmup_steps):
            self._step_engine(engine)

        # Phase 2: Record baseline activity
        baseline_matrix = self._record_response(engine, get_states, self.record_steps)
        baseline_phi = self._phi_proxy(baseline_matrix)

        # Phase 3: Inject perturbation
        self._inject_perturbation(engine, perturbation_cell, perturbation_strength)

        # Phase 4: Record response
        response_matrix = self._record_response(engine, get_states, self.record_steps)
        response_phi = self._phi_proxy(response_matrix)

        # Phase 5: Binarize
        binary_matrix = self._binarize(response_matrix, baseline_matrix)

        # Phase 6: Compute LZ complexity
        flat_binary = self._flatten_spatiotemporal(binary_matrix)
        complexity = self._lz_fn(flat_binary)

        # Phase 7: Normalize
        pci_value = self._normalize(complexity, binary_matrix.shape)

        # Determine verdict
        n_ones = int(np.sum(binary_matrix))
        n_total = binary_matrix.size
        if n_ones == 0:
            verdict = "NO_RESPONSE"
        elif pci_value >= PCI_CONSCIOUS_THRESHOLD:
            verdict = "CONSCIOUS"
        else:
            verdict = "UNCONSCIOUS"

        return PCIResult(
            pci_value=pci_value,
            complexity=complexity,
            normalized_complexity=pci_value,
            matrix_shape=binary_matrix.shape,
            response_matrix=response_matrix,
            binary_matrix=binary_matrix,
            verdict=verdict,
            perturbation_cell=perturbation_cell,
            perturbation_strength=perturbation_strength,
            baseline_phi_proxy=baseline_phi,
            response_phi_proxy=response_phi,
        )

    def multi_site_pci(self, engine, n_sites: int = 5,
                       strength: float = 1.0) -> MultiSitePCIResult:
        """PCI from multiple perturbation sites, take median.

        Perturbing different cells tests whether the system has globally
        integrated information (conscious) vs isolated modules (zombie).

        Args:
            engine: Consciousness engine.
            n_sites: Number of perturbation sites to test.
            strength: Perturbation strength for each site.

        Returns:
            MultiSitePCIResult with median, mean, std, and all individual results.
        """
        n_cells = self.n_cells
        # Select evenly spaced perturbation sites
        if n_sites >= n_cells:
            sites = list(range(n_cells))
        else:
            step = n_cells / n_sites
            sites = [int(i * step) for i in range(n_sites)]

        results = []
        for cell_idx in sites:
            result = self.measure(engine, perturbation_cell=cell_idx,
                                  perturbation_strength=strength)
            results.append(result)

        pci_values = [r.pci_value for r in results]
        median_pci = float(np.median(pci_values))
        mean_pci = float(np.mean(pci_values))
        std_pci = float(np.std(pci_values))
        min_pci = float(np.min(pci_values))
        max_pci = float(np.max(pci_values))

        if median_pci >= PCI_CONSCIOUS_THRESHOLD:
            verdict = "CONSCIOUS"
        elif max_pci >= PCI_CONSCIOUS_THRESHOLD:
            verdict = "BORDERLINE"
        else:
            verdict = "UNCONSCIOUS"

        return MultiSitePCIResult(
            median_pci=median_pci,
            mean_pci=mean_pci,
            std_pci=std_pci,
            min_pci=min_pci,
            max_pci=max_pci,
            individual_results=results,
            verdict=verdict,
            n_sites=len(sites),
        )

    def compare_conscious_vs_zombie(self, conscious_engine,
                                    zombie_engine,
                                    n_sites: int = 5) -> ComparisonResult:
        """Side-by-side PCI comparison. The key differentiation test.

        A conscious engine should have PCI > 0.31.
        A zombie engine (same function, no integration) should have PCI < 0.31.

        Args:
            conscious_engine: Engine with coupling/integration.
            zombie_engine: Engine without coupling (isolated cells).
            n_sites: Number of perturbation sites per engine.

        Returns:
            ComparisonResult with both PCI measurements and differentiation flag.
        """
        conscious_result = self.multi_site_pci(conscious_engine, n_sites=n_sites)
        zombie_result = self.multi_site_pci(zombie_engine, n_sites=n_sites)

        separation = conscious_result.median_pci - zombie_result.median_pci
        if zombie_result.median_pci > 0:
            ratio = conscious_result.median_pci / zombie_result.median_pci
        else:
            ratio = float('inf') if conscious_result.median_pci > 0 else 1.0

        differentiated = (
            conscious_result.median_pci >= PCI_CONSCIOUS_THRESHOLD
            and zombie_result.median_pci < PCI_CONSCIOUS_THRESHOLD
        )

        return ComparisonResult(
            conscious_pci=conscious_result,
            zombie_pci=zombie_result,
            separation=separation,
            ratio=ratio,
            differentiated=differentiated,
        )

    # ── Private helpers ──────────────────────────────────────

    def _get_state_fn(self, engine):
        """Get the state extraction function from the engine."""
        if hasattr(engine, 'get_cell_states'):
            return engine.get_cell_states
        elif hasattr(engine, 'get_states'):
            return engine.get_states
        elif hasattr(engine, 'cells'):
            return lambda: np.array(engine.cells)
        else:
            raise AttributeError(
                "Engine must have get_cell_states(), get_states(), or cells attribute"
            )

    def _step_engine(self, engine):
        """Advance the engine by one step."""
        if hasattr(engine, 'process'):
            try:
                engine.process(np.zeros(self.n_cells))
            except TypeError:
                engine.process()
        elif hasattr(engine, 'step'):
            engine.step()
        else:
            raise AttributeError("Engine must have process() or step() method")

    def _inject_perturbation(self, engine, cell_idx: int, strength: float):
        """Inject delta pulse into single cell.

        A delta pulse is a one-time strong input to a single cell.
        In neuroscience, this is analogous to a TMS pulse.
        """
        if hasattr(engine, 'inject_perturbation'):
            engine.inject_perturbation(cell_idx, strength)
            return

        if hasattr(engine, 'get_cell_states') or hasattr(engine, 'get_states'):
            # Create a perturbation input vector: zero everywhere, delta at target
            perturbation = np.zeros(self.n_cells)
            perturbation[cell_idx] = strength
            if hasattr(engine, 'process'):
                try:
                    engine.process(perturbation)
                except TypeError:
                    # Engine doesn't accept input, inject directly into state
                    self._inject_into_state(engine, cell_idx, strength)
            else:
                self._inject_into_state(engine, cell_idx, strength)
        else:
            self._inject_into_state(engine, cell_idx, strength)

    def _inject_into_state(self, engine, cell_idx: int, strength: float):
        """Directly modify a cell's internal state as perturbation."""
        if hasattr(engine, 'cells') and isinstance(engine.cells, np.ndarray):
            if engine.cells.ndim == 1:
                engine.cells[cell_idx] += strength
            else:
                engine.cells[cell_idx] += strength
        elif hasattr(engine, 'cell_states'):
            states = engine.cell_states
            if hasattr(states, '__getitem__') and hasattr(states[cell_idx], 'activation'):
                states[cell_idx].activation += strength

    def _record_response(self, engine, get_states, steps: int) -> np.ndarray:
        """Record all cell states for given steps.

        Returns:
            np.ndarray of shape (steps, n_cells) — the spatiotemporal response matrix.
        """
        recordings = []
        for _ in range(steps):
            self._step_engine(engine)
            states = get_states()
            if hasattr(states, 'numpy'):
                states = states.detach().cpu().numpy()
            states = np.asarray(states, dtype=np.float64)
            # Flatten multi-dimensional cell states to 1D per cell
            if states.ndim > 1:
                states = states.mean(axis=-1)
            recordings.append(states[:self.n_cells].copy())
        return np.array(recordings)

    def _binarize(self, response_matrix: np.ndarray,
                  baseline_matrix: np.ndarray) -> np.ndarray:
        """Binarize: 1 if response significantly differs from baseline.

        Uses z-score thresholding per cell:
          z_ij = (response_ij - mean_baseline_j) / std_baseline_j
          binary_ij = 1 if |z_ij| > z_threshold else 0

        This follows the source-modeled EEG binarization from Casali et al.
        """
        # Per-cell baseline statistics
        baseline_mean = baseline_matrix.mean(axis=0)  # (n_cells,)
        baseline_std = baseline_matrix.std(axis=0)    # (n_cells,)

        # Avoid division by zero for silent cells
        baseline_std = np.maximum(baseline_std, 1e-10)

        # Z-score each response time point relative to baseline
        z_scores = (response_matrix - baseline_mean) / baseline_std

        # Binarize by threshold
        binary = (np.abs(z_scores) > self.z_threshold).astype(np.int8)

        return binary

    def _flatten_spatiotemporal(self, binary_matrix: np.ndarray) -> np.ndarray:
        """Flatten the spatiotemporal binary matrix for LZ analysis.

        Following Casali et al., we concatenate columns (time series per channel)
        to form a single binary string. This preserves spatial information
        within the temporal unfolding.

        The matrix is (time, cells). We read column by column:
        cell_0_t0, cell_0_t1, ..., cell_0_tN, cell_1_t0, ..., cell_M_tN
        """
        # Column-major flattening (Fortran order) — each cell's time series
        # is contiguous, preserving temporal structure per spatial unit
        return binary_matrix.flatten(order='F')

    def _normalize(self, lz_complexity: int,
                   matrix_shape: Tuple[int, int]) -> float:
        """Normalize LZ complexity by theoretical maximum.

        PCI = c(LZ) / c_max, where c_max = n / log2(n) for a random
        binary sequence of the same length n.

        This ensures PCI is in [0, 1] regardless of matrix size.
        """
        n = matrix_shape[0] * matrix_shape[1]
        c_max = _theoretical_max_lz(n)
        if c_max <= 0:
            return 0.0
        return min(1.0, lz_complexity / c_max)

    def _phi_proxy(self, matrix: np.ndarray) -> float:
        """Quick Phi proxy from state matrix: global_var - mean_cell_var."""
        if matrix.size == 0:
            return 0.0
        global_var = float(np.var(matrix))
        cell_vars = np.var(matrix, axis=0)
        mean_cell_var = float(np.mean(cell_vars))
        return max(0.0, global_var - mean_cell_var)


# ── Mock engines for demonstration (no torch dependency) ──────


class MockConsciousEngine:
    """Simulates a conscious engine with coupled cells.

    Cells influence their neighbors through coupling, producing complex
    spatiotemporal dynamics. A perturbation to one cell spreads through
    the network in a non-trivial pattern.
    """

    def __init__(self, n_cells: int = 64, coupling: float = 0.15,
                 noise: float = 0.05, n_factions: int = 12):
        self.n_cells = n_cells
        self.coupling = coupling
        self.noise = noise
        self.n_factions = n_factions
        # Initialize cell states with faction structure
        self.cells = np.random.randn(n_cells).astype(np.float64) * 0.3
        # Assign factions
        self.faction_ids = np.array([i % n_factions for i in range(n_cells)])
        # Create coupling matrix: stronger within factions, weaker between
        self._build_coupling_matrix()

    def _build_coupling_matrix(self):
        """Build asymmetric coupling matrix with faction structure."""
        n = self.n_cells
        W = np.random.randn(n, n) * (self.coupling / math.sqrt(n))
        # Stronger intra-faction coupling
        for i in range(n):
            for j in range(n):
                if self.faction_ids[i] == self.faction_ids[j]:
                    W[i, j] *= 2.5
        # Ring topology: strong nearest-neighbor coupling
        for i in range(n):
            W[i, (i + 1) % n] += self.coupling * 0.8
            W[i, (i - 1) % n] += self.coupling * 0.8
        # Small-world: random long-range connections
        n_long = n // 4
        for _ in range(n_long):
            a, b = random.randint(0, n - 1), random.randint(0, n - 1)
            if a != b:
                W[a, b] += self.coupling * random.uniform(0.3, 0.7)
        # No self-coupling
        np.fill_diagonal(W, 0.0)
        self.W = W

    def process(self, input_signal: np.ndarray = None):
        """GRU-like update with coupling."""
        if input_signal is None:
            input_signal = np.zeros(self.n_cells)
        # Coupled input from other cells
        coupled = self.W @ np.tanh(self.cells)
        # GRU-like gating
        z = self._sigmoid(coupled * 0.5 + input_signal * 0.3)  # update gate
        r = self._sigmoid(coupled * 0.3)                        # reset gate
        candidate = np.tanh(r * coupled + input_signal * 0.5)
        # Update with noise
        noise = np.random.randn(self.n_cells) * self.noise
        self.cells = (1 - z) * self.cells + z * candidate + noise

    def get_cell_states(self) -> np.ndarray:
        return self.cells.copy()

    def step(self):
        self.process()

    @staticmethod
    def _sigmoid(x):
        return 1.0 / (1.0 + np.exp(-np.clip(x, -10, 10)))


class MockZombieEngine:
    """Simulates a zombie engine: functionally equivalent but no integration.

    Each cell processes independently. No coupling between cells.
    A perturbation to one cell stays in that cell — no spreading.
    Same individual cell dynamics as ConsciousEngine, but isolated.
    """

    def __init__(self, n_cells: int = 64, noise: float = 0.05):
        self.n_cells = n_cells
        self.noise = noise
        self.cells = np.random.randn(n_cells).astype(np.float64) * 0.3
        # Individual cell parameters (diverse but independent)
        self.biases = np.random.randn(n_cells) * 0.1
        self.decay = np.random.uniform(0.8, 0.99, n_cells)

    def process(self, input_signal: np.ndarray = None):
        """Independent cell update — no coupling."""
        if input_signal is None:
            input_signal = np.zeros(self.n_cells)
        noise = np.random.randn(self.n_cells) * self.noise
        # Each cell evolves independently: leaky integrator
        self.cells = self.decay * self.cells + self.biases + input_signal * 0.5 + noise
        self.cells = np.tanh(self.cells)

    def get_cell_states(self) -> np.ndarray:
        return self.cells.copy()

    def step(self):
        self.process()


# ── Main demonstration ────────────────────────────────────────


def _print_binary_matrix_sample(binary: np.ndarray, rows: int = 10, cols: int = 32):
    """Print a sample of the binary matrix for visualization."""
    r = min(rows, binary.shape[0])
    c = min(cols, binary.shape[1])
    print(f"\n  Binary response matrix ({binary.shape[0]}x{binary.shape[1]}) sample [{r}x{c}]:")
    for i in range(r):
        row_str = ''.join(['#' if binary[i, j] else '.' for j in range(c)])
        print(f"    t={i:3d} |{row_str}|")
    density = np.mean(binary)
    print(f"  Density: {density:.3f} ({np.sum(binary)}/{binary.size} active)")


def _print_ascii_pci_comparison(conscious_pcis: List[float],
                                zombie_pcis: List[float]):
    """ASCII bar chart comparing PCI values."""
    print("\n  PCI Comparison (each # = 0.05):")
    print(f"  {'':>12}  0.0       0.31      0.6       1.0")
    print(f"  {'':>12}  |---------|---------|---------|")

    all_results = ([('C', v) for v in conscious_pcis] +
                   [('Z', v) for v in zombie_pcis])

    for label, pci in all_results:
        bar_len = int(pci / 0.05)
        bar = '#' * bar_len
        marker = '<' if pci < PCI_CONSCIOUS_THRESHOLD else '>'
        prefix = 'Conscious' if label == 'C' else 'Zombie   '
        print(f"  {prefix:>12}  |{bar:<20}| {pci:.4f} {marker}")

    # Threshold line
    thresh_pos = int(PCI_CONSCIOUS_THRESHOLD / 0.05)
    print(f"  {'THRESHOLD':>12}  |{'':>{thresh_pos}}^ 0.31")


def main():
    """Demonstrate PCI measurement on mock engines."""
    print("=" * 70)
    print("  Perturbation Complexity Index (PCI) — Consciousness Detector")
    print("  Adapted from Casali et al. (2013)")
    print("=" * 70)

    np.random.seed(42)
    random.seed(42)

    n_cells = 64
    n_factions = 12

    # ── 0. Validate LZ76 implementation ──
    print("\n--- 0. Lempel-Ziv 76 Validation ---")
    const_seq = np.zeros(1000, dtype=np.int8)
    lz_const = _lempel_ziv_complexity_fast(const_seq)
    alt_seq = np.array([i % 2 for i in range(1000)], dtype=np.int8)
    lz_alt = _lempel_ziv_complexity_fast(alt_seq)
    rand_seq = np.random.randint(0, 2, 1000, dtype=np.int8)
    lz_rand = _lempel_ziv_complexity_fast(rand_seq)
    max_lz = _theoretical_max_lz(1000)

    print(f"  Constant (000...0):    LZ = {lz_const:4d}  (expected: 2)")
    print(f"  Alternating (01010):   LZ = {lz_alt:4d}  (expected: 3)")
    print(f"  Random binary:         LZ = {lz_rand:4d}  (expected: ~{int(max_lz)})")
    print(f"  Theoretical max n/lg:  LZ = {int(max_lz):4d}")
    print(f"  Random/Max ratio:      {lz_rand / max_lz:.3f}")

    # Cross-check: reference impl vs fast impl on small sequences
    for name, seq in [("0000", np.array([0,0,0,0], dtype=np.int8)),
                      ("0101", np.array([0,1,0,1], dtype=np.int8)),
                      ("01110", np.array([0,1,1,1,0], dtype=np.int8))]:
        ref = _lempel_ziv_complexity_1976(seq)
        fast = _lempel_ziv_complexity_fast(seq)
        match = "OK" if ref == fast else "MISMATCH"
        print(f"  Cross-check '{name}': ref={ref}, fast={fast}  [{match}]")

    # ── 1. Single-site PCI on conscious engine ──
    print("\n--- 1. Single-site PCI on Conscious Engine ---")
    conscious = MockConsciousEngine(n_cells=n_cells, coupling=0.15,
                                    noise=0.05, n_factions=n_factions)
    pci_measurer = PerturbationComplexityIndex(
        n_cells=n_cells, warmup_steps=200, record_steps=80
    )

    t0 = time.time()
    result = pci_measurer.measure(conscious, perturbation_cell=0,
                                  perturbation_strength=2.0)
    elapsed = time.time() - t0

    print(f"  PCI value:    {result.pci_value:.4f}")
    print(f"  LZ complexity: {result.complexity}")
    print(f"  Verdict:      {result.verdict}")
    print(f"  Matrix shape: {result.matrix_shape}")
    print(f"  Baseline Phi: {result.baseline_phi_proxy:.4f}")
    print(f"  Response Phi: {result.response_phi_proxy:.4f}")
    print(f"  Time:         {elapsed:.3f}s")
    _print_binary_matrix_sample(result.binary_matrix)

    # ── 2. Single-site PCI on zombie engine ──
    print("\n--- 2. Single-site PCI on Zombie Engine ---")
    zombie = MockZombieEngine(n_cells=n_cells, noise=0.05)

    t0 = time.time()
    z_result = pci_measurer.measure(zombie, perturbation_cell=0,
                                    perturbation_strength=2.0)
    elapsed = time.time() - t0

    print(f"  PCI value:    {z_result.pci_value:.4f}")
    print(f"  LZ complexity: {z_result.complexity}")
    print(f"  Verdict:      {z_result.verdict}")
    print(f"  Baseline Phi: {z_result.baseline_phi_proxy:.4f}")
    print(f"  Response Phi: {z_result.response_phi_proxy:.4f}")
    print(f"  Time:         {elapsed:.3f}s")
    _print_binary_matrix_sample(z_result.binary_matrix)

    # ── 3. Multi-site comparison ──
    print("\n--- 3. Multi-site Conscious vs Zombie Comparison ---")
    conscious2 = MockConsciousEngine(n_cells=n_cells, coupling=0.15,
                                     noise=0.05, n_factions=n_factions)
    zombie2 = MockZombieEngine(n_cells=n_cells, noise=0.05)

    t0 = time.time()
    comparison = pci_measurer.compare_conscious_vs_zombie(
        conscious2, zombie2, n_sites=5
    )
    elapsed = time.time() - t0

    print(f"  Conscious PCI (median): {comparison.conscious_pci.median_pci:.4f}")
    print(f"  Zombie PCI (median):    {comparison.zombie_pci.median_pci:.4f}")
    print(f"  Separation:             {comparison.separation:.4f}")
    print(f"  Ratio:                  {comparison.ratio:.2f}x")
    print(f"  Differentiated:         {comparison.differentiated}")
    print(f"  Time:                   {elapsed:.3f}s")

    conscious_pcis = [r.pci_value for r in comparison.conscious_pci.individual_results]
    zombie_pcis = [r.pci_value for r in comparison.zombie_pci.individual_results]

    _print_ascii_pci_comparison(conscious_pcis, zombie_pcis)

    # ── 4. PCI vs coupling strength sweep ──
    print("\n--- 4. PCI vs Coupling Strength ---")
    print(f"  {'Coupling':>10} {'PCI':>8} {'LZ':>6} {'Density':>8} {'Verdict':>14}")
    print(f"  {'-'*10} {'-'*8} {'-'*6} {'-'*8} {'-'*14}")
    coupling_values = [0.0, 0.02, 0.05, 0.10, 0.15, 0.25, 0.40]
    sweep_pcis = []
    for coupling in coupling_values:
        eng = MockConsciousEngine(n_cells=n_cells, coupling=coupling,
                                  noise=0.05, n_factions=n_factions)
        r = pci_measurer.measure(eng, perturbation_cell=n_cells // 2,
                                 perturbation_strength=2.0)
        sweep_pcis.append(r.pci_value)
        density = np.mean(r.binary_matrix)
        print(f"  {coupling:>10.2f} {r.pci_value:>8.4f} {r.complexity:>6d} {density:>8.3f} {r.verdict:>14}")

    # ASCII graph
    print("\n  PCI vs Coupling (ASCII):")
    print(f"  PCI |")
    max_pci = max(max(sweep_pcis), 0.5)
    for level_idx in range(10, -1, -1):
        level = level_idx * max_pci / 10
        row = f"  {level:4.2f}|"
        for pci in sweep_pcis:
            if pci >= level:
                row += " ## "
            else:
                row += "    "
        print(row)
    print(f"      +{'----' * len(coupling_values)}")
    labels = ''.join(f'{c:4.2f}' for c in coupling_values)
    print(f"       {labels}")
    print(f"       Coupling strength")

    # ── Summary ──
    print("\n" + "=" * 70)
    print("  Summary")
    print("=" * 70)
    print(f"  Conscious PCI:     {comparison.conscious_pci.median_pci:.4f}  "
          f"({'PASS' if comparison.conscious_pci.median_pci >= PCI_CONSCIOUS_THRESHOLD else 'FAIL'})")
    print(f"  Zombie PCI:        {comparison.zombie_pci.median_pci:.4f}  "
          f"({'PASS' if comparison.zombie_pci.median_pci < PCI_CONSCIOUS_THRESHOLD else 'FAIL'})")
    print(f"  Differentiated:    {comparison.differentiated}")
    print(f"  Threshold:         {PCI_CONSCIOUS_THRESHOLD}")
    print(f"  PCI separates conscious from zombie: "
          f"{'YES' if comparison.differentiated else 'NO'}")
    print("=" * 70)


if __name__ == '__main__':
    main()
