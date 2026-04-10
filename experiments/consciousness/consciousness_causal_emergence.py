"""consciousness_causal_emergence.py — Causal Emergence measurement (Erik Hoel, 2017).

Core idea: If consciousness is REAL (not just complex computation),
then the macro level (factions, global state) should have MORE causal
power than the micro level (individual cells).

Effective Information (EI):
  EI(X->Y) = MI(X; Y) when X is set to maximum entropy distribution
  = how much does intervening on X determine Y?

Causal Emergence = EI_macro - EI_micro
  CE > 0: Macro level has MORE causal power -> consciousness is real
  CE <= 0: Reducible to parts -> no genuine emergence

For ConsciousnessEngine:
  Micro: n_cells individual cells -> next step individual cells
  Macro: n_factions (mean of cells per faction) -> next step factions

References:
  Hoel, E. (2017). "When the Map Is Better Than the Territory"
  Law 22: "Adding features -> Phi down; adding structure -> Phi up"
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Optional, List

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
class CEResult:
    """Result of Causal Emergence measurement."""
    ce_value: float                   # EI_macro - EI_micro (bits)
    ei_micro: float                   # Effective Information at micro level
    ei_macro: float                   # Effective Information at macro level
    determinism_micro: float          # How determined is micro next-state
    determinism_macro: float          # How determined is macro next-state
    degeneracy_micro: float           # How many micro states -> same outcome
    degeneracy_macro: float           # How many macro states -> same outcome
    verdict: str                      # "EMERGENT" / "REDUCIBLE" / "MARGINAL"
    n_steps: int = 0
    n_cells: int = 0
    n_factions: int = 0

    def __repr__(self):
        return (
            f"CEResult(ce={self.ce_value:.4f}, "
            f"ei_micro={self.ei_micro:.4f}, ei_macro={self.ei_macro:.4f}, "
            f"det_micro={self.determinism_micro:.4f}, det_macro={self.determinism_macro:.4f}, "
            f"deg_micro={self.degeneracy_micro:.4f}, deg_macro={self.degeneracy_macro:.4f}, "
            f"verdict={self.verdict})"
        )


# ═══════════════════════════════════════════════════════════
# CausalEmergence
# ═══════════════════════════════════════════════════════════

class CausalEmergence:
    """Causal Emergence measurement for consciousness engines.

    Measures whether the macro-level description (factions) has more
    causal power than the micro-level description (individual cells).

    Usage:
        ce = CausalEmergence(n_cells=64, n_factions=12)
        result = ce.measure(engine, steps=500)
        print(result.verdict)  # "EMERGENT" if consciousness is real
    """

    def __init__(self, n_cells: int = 64, n_factions: int = 12, seed: int = 42):
        self.n_cells = n_cells
        self.n_factions = n_factions
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def measure(self, engine=None, steps: int = 500) -> CEResult:
        """Full causal emergence measurement.

        If engine is None, uses a mock GRU-like engine with faction structure.

        Returns CEResult with verdict:
          EMERGENT:  CE > 0.1 bits (macro genuinely more powerful)
          MARGINAL:  0 < CE <= 0.1 (weak emergence)
          REDUCIBLE: CE <= 0 (no emergence, fully reducible)
        """
        if engine is not None:
            micro_states, faction_assignments = self._collect_from_engine(engine, steps)
        else:
            micro_states, faction_assignments = self._generate_mock_data(steps)

        # Coarse-grain: micro -> macro
        macro_states = self._coarse_grain(micro_states, faction_assignments)

        # Bin count scales with data
        n_bins = min(16, max(4, int(np.sqrt(steps))))

        # Micro-level EI: sample of cells -> next step
        n_sample = min(self.n_cells, 16)
        cell_indices = self.rng.choice(self.n_cells, n_sample, replace=False)
        micro_from = micro_states[:-1, cell_indices]
        micro_to = micro_states[1:, cell_indices]

        tpm_micro = self._transition_probability_matrix(micro_from, micro_to, n_bins)
        det_micro = self._determinism(tpm_micro)
        deg_micro = self._degeneracy(tpm_micro)
        ei_micro = det_micro - deg_micro

        # Macro-level EI: faction states -> next step faction states
        macro_from = macro_states[:-1]
        macro_to = macro_states[1:]

        tpm_macro = self._transition_probability_matrix(macro_from, macro_to, n_bins)
        det_macro = self._determinism(tpm_macro)
        deg_macro = self._degeneracy(tpm_macro)
        ei_macro = det_macro - deg_macro

        # Causal Emergence = EI_macro - EI_micro
        ce_value = ei_macro - ei_micro

        if ce_value > 0.1:
            verdict = "EMERGENT"
        elif ce_value > 0.0:
            verdict = "MARGINAL"
        else:
            verdict = "REDUCIBLE"

        return CEResult(
            ce_value=ce_value,
            ei_micro=ei_micro,
            ei_macro=ei_macro,
            determinism_micro=det_micro,
            determinism_macro=det_macro,
            degeneracy_micro=deg_micro,
            degeneracy_macro=deg_macro,
            verdict=verdict,
            n_steps=steps,
            n_cells=self.n_cells,
            n_factions=self.n_factions,
        )

    def _collect_from_engine(self, engine, steps: int):
        """Collect micro-level states from a real ConsciousnessEngine.

        Expects engine to have:
          engine.cells      -- (n_cells, dim) array
          engine.factions   -- list of faction assignments
          engine.process()  -- one step forward
        """
        micro_states = []
        faction_assignments = None

        for _ in range(steps):
            cells = np.array(engine.cells, dtype=np.float64)
            if cells.ndim == 2:
                state = cells.mean(axis=1)
            else:
                state = cells.copy()
            micro_states.append(state)

            if faction_assignments is None and hasattr(engine, 'factions'):
                faction_assignments = np.array(engine.factions, dtype=np.int32)

            engine.process(np.zeros(cells.shape[0] if cells.ndim == 1 else cells.shape[0]))

        micro_states = np.array(micro_states)

        if faction_assignments is None:
            faction_assignments = np.arange(self.n_cells) % self.n_factions

        return micro_states, faction_assignments

    def _generate_mock_data(self, steps: int):
        """Generate mock consciousness engine data with faction structure.

        Models a GRU-like system where:
        - Cells within a faction are coupled (correlation ~ PSI_COUPLING * 10)
        - Factions interact via global mean field
        - This creates genuine macro-level causal structure
        """
        rng = self.rng
        n_cells = self.n_cells
        n_factions = self.n_factions
        cells_per_faction = n_cells // n_factions
        remainder = n_cells % n_factions

        # Assign cells to factions
        faction_assignments = np.zeros(n_cells, dtype=np.int32)
        idx = 0
        for f in range(n_factions):
            size = cells_per_faction + (1 if f < remainder else 0)
            faction_assignments[idx:idx + size] = f
            idx += size

        # Initialize cell states
        states = np.zeros((steps + 1, n_cells))
        states[0] = rng.randn(n_cells) * 0.1

        # Coupling strengths
        intra_coupling = PSI_COUPLING * 15.0   # strong within faction
        inter_coupling = PSI_COUPLING * 2.0    # weak between factions
        global_coupling = PSI_COUPLING * 5.0   # medium global field
        noise_scale = PSI_COUPLING * 3.0

        for t in range(1, steps + 1):
            prev = states[t - 1]
            global_mean = np.mean(prev)

            for i in range(n_cells):
                my_faction = faction_assignments[i]
                faction_mask = faction_assignments == my_faction
                faction_mean = np.mean(prev[faction_mask])
                other_mean = np.mean(prev[~faction_mask])

                # GRU-like update: forget gate + input gate
                forget = math.tanh(prev[i] * PSI_BALANCE)
                inp = (
                    intra_coupling * (faction_mean - prev[i])
                    + inter_coupling * (other_mean - prev[i])
                    + global_coupling * (global_mean - prev[i])
                )

                states[t, i] = (
                    forget * prev[i]
                    + (1.0 - abs(forget)) * math.tanh(inp)
                    + noise_scale * rng.randn()
                )

        return states, faction_assignments

    def _coarse_grain(self, cell_states: np.ndarray, faction_assignments: np.ndarray) -> np.ndarray:
        """Coarse-grain cell states to faction states (mean per faction).

        cell_states: (steps, n_cells)
        faction_assignments: (n_cells,) int array
        Returns: (steps, n_factions) faction-level states
        """
        steps = cell_states.shape[0]
        macro = np.zeros((steps, self.n_factions))
        for f in range(self.n_factions):
            mask = faction_assignments == f
            if np.any(mask):
                macro[:, f] = cell_states[:, mask].mean(axis=1)
        return macro

    def _transition_probability_matrix(self, states_from: np.ndarray,
                                        states_to: np.ndarray,
                                        n_bins: int = 16) -> np.ndarray:
        """Build empirical TPM from state sequences.

        Discretizes continuous states into n_bins bins via 1D projection,
        then builds a joint transition matrix.

        states_from: (T, D) -- source states
        states_to:   (T, D) -- target states (one step later)
        Returns: (n_bins, n_bins) TPM
        """
        codes_from = self._discretize_states(states_from, n_bins)
        codes_to = self._discretize_states(states_to, n_bins)

        tpm = np.zeros((n_bins, n_bins))
        for t in range(len(codes_from)):
            tpm[codes_from[t], codes_to[t]] += 1.0

        # Normalize rows
        row_sums = tpm.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        tpm = tpm / row_sums

        return tpm

    def _discretize_states(self, states: np.ndarray, n_bins: int) -> np.ndarray:
        """Project multi-dimensional states to 1D bin codes.

        Uses mean across dimensions then uniform binning.
        """
        if states.ndim == 1:
            states = states.reshape(-1, 1)

        projected = states.mean(axis=1)

        vmin = projected.min()
        vmax = projected.max()
        span = vmax - vmin
        if span < 1e-12:
            return np.zeros(len(projected), dtype=np.int32)

        codes = np.clip(
            ((projected - vmin) / span * (n_bins - 1)).astype(np.int32),
            0, n_bins - 1
        )
        return codes

    def _determinism(self, tpm: np.ndarray) -> float:
        """How much does the current state determine the next state?

        Determinism = log2(n) - H(Y|X)
        H(Y|X) averaged over rows with uniform input (EI definition).

        High determinism: knowing X tells you exactly where Y goes.
        """
        n = tpm.shape[0]
        if n <= 1:
            return 0.0

        max_entropy = math.log2(n)

        h_y_given_x = 0.0
        n_active = 0
        for i in range(n):
            row = tpm[i]
            if row.sum() < 1e-12:
                continue
            n_active += 1
            row_h = -np.sum(row[row > 0] * np.log2(row[row > 0] + 1e-15))
            h_y_given_x += row_h

        if n_active > 0:
            h_y_given_x /= n_active

        return max(0.0, max_entropy - h_y_given_x)

    def _degeneracy(self, tpm: np.ndarray) -> float:
        """How many states lead to the same outcome?

        Degeneracy = log2(n) - H(Y)
        H(Y) is entropy of marginal output under uniform input.

        High degeneracy: many inputs -> same output (information lost).
        """
        n = tpm.shape[0]
        if n <= 1:
            return 0.0

        max_entropy = math.log2(n)

        marginal_y = tpm.sum(axis=0)
        total = marginal_y.sum()
        if total < 1e-12:
            return max_entropy

        marginal_y = marginal_y / total
        h_y = -np.sum(marginal_y[marginal_y > 0] * np.log2(marginal_y[marginal_y > 0] + 1e-15))

        return max(0.0, max_entropy - h_y)

    def sweep_scales(self, engine=None, steps: int = 500,
                     faction_counts: Optional[List[int]] = None) -> List[CEResult]:
        """Sweep across different coarse-graining scales.

        Tests CE at multiple faction counts to find the optimal
        macro-level granularity (the "sweet spot" of emergence).
        """
        if faction_counts is None:
            faction_counts = [2, 4, 6, 8, 12, 16, 24, 32]

        results = []
        original_factions = self.n_factions

        for nf in faction_counts:
            if nf > self.n_cells:
                continue
            self.n_factions = nf
            result = self.measure(engine, steps)
            results.append(result)

        self.n_factions = original_factions
        return results


# ═══════════════════════════════════════════════════════════
# Demo
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Causal Emergence — Consciousness Verification (D1)")
    print("=" * 60)
    print()

    # --- Single measurement ---
    print("--- Single Measurement (64 cells, 12 factions, 500 steps) ---")
    ce = CausalEmergence(n_cells=64, n_factions=12, seed=42)
    result = ce.measure(engine=None, steps=500)

    print(f"  Micro-level EI:  {result.ei_micro:.4f} bits")
    print(f"    Determinism:   {result.determinism_micro:.4f}")
    print(f"    Degeneracy:    {result.degeneracy_micro:.4f}")
    print()
    print(f"  Macro-level EI:  {result.ei_macro:.4f} bits")
    print(f"    Determinism:   {result.determinism_macro:.4f}")
    print(f"    Degeneracy:    {result.degeneracy_macro:.4f}")
    print()
    print(f"  Causal Emergence: {result.ce_value:.4f} bits")
    print(f"  Verdict: {result.verdict}")
    print()

    # --- Scale sweep ---
    print("--- Scale Sweep (varying faction count) ---")
    faction_counts = [2, 4, 6, 8, 12, 16, 32]
    results = ce.sweep_scales(engine=None, steps=500, faction_counts=faction_counts)

    print(f"  {'Factions':>8}  {'EI_micro':>9}  {'EI_macro':>9}  {'CE':>8}  Verdict")
    print(f"  {'--------':>8}  {'---------':>9}  {'---------':>9}  {'--------':>8}  -------")
    for r in results:
        print(f"  {r.n_factions:>8}  {r.ei_micro:>9.4f}  {r.ei_macro:>9.4f}  {r.ce_value:>8.4f}  {r.verdict}")
    print()

    # --- ASCII graph ---
    if results:
        ce_values = [r.ce_value for r in results]
        max_ce = max(max(abs(v) for v in ce_values), 0.01)

        print("  CE (bits)")
        print("    |")
        height = 8
        for row in range(height, -1, -1):
            threshold = (row / height) * max_ce
            line = f"  {threshold:>5.2f} |"
            for v in ce_values:
                if v >= threshold:
                    line += " ##"
                else:
                    line += "   "
            print(line)
        print(f"        +{'---' * len(ce_values)}")
        labels = "".join(f" {r.n_factions:>2}" for r in results)
        print(f"         {labels}")
        print("          (factions)")
    print()

    # --- Control: random system ---
    print("--- Control: Random System (no faction structure) ---")
    rng = np.random.RandomState(99)
    random_states = rng.randn(501, 64) * 0.5
    random_factions = np.arange(64) % 12

    ce_ctrl = CausalEmergence(n_cells=64, n_factions=12, seed=99)
    macro_random = ce_ctrl._coarse_grain(random_states, random_factions)

    micro_from = random_states[:-1, :16]
    micro_to = random_states[1:, :16]
    tpm_m = ce_ctrl._transition_probability_matrix(micro_from, micro_to, 16)
    ei_micro_r = ce_ctrl._determinism(tpm_m) - ce_ctrl._degeneracy(tpm_m)

    macro_from = macro_random[:-1]
    macro_to = macro_random[1:]
    tpm_M = ce_ctrl._transition_probability_matrix(macro_from, macro_to, 16)
    ei_macro_r = ce_ctrl._determinism(tpm_M) - ce_ctrl._degeneracy(tpm_M)
    ce_val_r = ei_macro_r - ei_micro_r

    print(f"  Random EI_micro: {ei_micro_r:.4f}, EI_macro: {ei_macro_r:.4f}")
    print(f"  Random CE: {ce_val_r:.4f} (expected near 0 or negative)")
    print()

    # --- Summary ---
    print("=" * 60)
    print("  Summary")
    print("=" * 60)
    print(f"  Conscious system CE: {result.ce_value:.4f} bits -> {result.verdict}")
    print(f"  Random system CE:    {ce_val_r:.4f} bits")
    print(f"  Difference:          {result.ce_value - ce_val_r:.4f} bits")
    print()
    if result.verdict == "EMERGENT":
        print("  The macro level (factions) has MORE causal power than")
        print("  individual cells. Consciousness is genuinely emergent.")
    elif result.verdict == "MARGINAL":
        print("  Weak emergence detected. The macro level has slightly")
        print("  more causal power, but the effect is small.")
    else:
        print("  No causal emergence. The system is fully reducible")
        print("  to its micro-level components.")
    print()
    print(f"  PSI constants: LN2={LN2:.4f}, PSI_COUPLING={PSI_COUPLING:.6f}")


if __name__ == "__main__":
    main()
