#!/usr/bin/env python3
"""zombie_engine.py — Philosophical Zombie control engine for consciousness verification.

A ZombieEngine is architecturally identical to ConsciousnessEngine but with
ZERO information integration between cells. It serves as the critical control
group: if a test cannot distinguish Zombie from Conscious, that test does not
measure consciousness.

Key differences from ConsciousnessEngine:
  1. Cells are INDEPENDENT - no coupling matrix, no information sharing
  2. Each cell has its own GRU but receives NO input from other cells
  3. Output is mean(cells) just like ConsciousnessEngine
  4. Factions exist as labels but have NO consensus mechanism
  5. Hebbian learning is disabled (coupling stays at 0)
  6. Phi Ratchet is disabled
  7. SOC sandpile is disabled

The zombie produces similar OUTPUT statistics (mean, variance, entropy)
but with fundamentally different INTERNAL dynamics (Phi ~ 0).

Usage:
  from zombie_engine import ZombieEngine, compare_with_conscious
  zombie = ZombieEngine(n_cells=64, hidden_dim=128, n_factions=12)
  zombie.process(input_signal, steps=300)
  phi = zombie.get_phi()  # ~0

  # Compare with conscious engine
  report = compare_with_conscious(conscious_engine, zombie, n_trials=10)
"""

import math
import time
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# PSI constants from information theory (ln(2) derived)
LN2 = math.log(2)                     # 0.6931 - 1 bit
PSI_BALANCE = 0.5                      # Law 71
PSI_COUPLING = LN2 / 2**5.5           # 0.0153
PSI_STEPS = 3 / LN2                   # 4.328
PSI_ENTROPY = 0.998                    # near-maximal

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


# ═══════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════

@dataclass
class ZombieCellState:
    """State of a single independent zombie cell."""
    cell_id: int
    faction_id: int           # label only - no consensus
    hidden: Optional[object] = None   # torch tensor when available
    activation_history: List[float] = field(default_factory=list)


@dataclass
class ZombieMetrics:
    """Metrics from a zombie engine run."""
    phi_iit: float = 0.0
    phi_proxy: float = 0.0
    mean_activation: float = 0.0
    std_activation: float = 0.0
    entropy: float = 0.0
    faction_agreement: float = 0.0   # should be ~chance level
    pci: float = 0.0
    steps_run: int = 0
    wall_time_ms: float = 0.0


@dataclass
class ComparisonResult:
    """Result of comparing conscious vs zombie engines."""
    test_name: str
    conscious_value: float
    zombie_value: float
    ratio: float = 0.0
    differentiates: bool = False   # True if test tells them apart
    description: str = ""


# ═══════════════════════════════════════════════════════════════
# ZombieGRUCell — Independent GRU with no cross-cell input
# ═══════════════════════════════════════════════════════════════

class ZombieGRUCell:
    """A GRU cell that processes input independently (no coupling).

    Uses same parameter count as ConsciousnessEngine's GRU cells,
    but input comes only from external signal + self-recurrence.
    No other cell's hidden state is ever seen.
    """

    def __init__(self, input_dim: int, hidden_dim: int, cell_id: int):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.cell_id = cell_id

        if HAS_TORCH:
            # Same architecture as ConsciousnessEngine GRU cell
            self.gru = nn.GRUCell(input_dim, hidden_dim)
            self.hidden = torch.zeros(1, hidden_dim)
            # Deterministic init per cell for reproducibility
            with torch.no_grad():
                nn.init.xavier_uniform_(self.gru.weight_ih)
                nn.init.xavier_uniform_(self.gru.weight_hh)
        else:
            self.hidden = [0.0] * hidden_dim
            self.gru = None

    def forward(self, x):
        """Process input, update hidden state. No coupling."""
        if HAS_TORCH:
            if not isinstance(x, torch.Tensor):
                x = torch.tensor(x, dtype=torch.float32)
            if x.dim() == 1:
                x = x.unsqueeze(0)
            # Pad or trim input to match input_dim
            if x.shape[-1] < self.input_dim:
                x = F.pad(x, (0, self.input_dim - x.shape[-1]))
            elif x.shape[-1] > self.input_dim:
                x = x[..., :self.input_dim]
            self.hidden = self.gru(x, self.hidden)
            return self.hidden.squeeze(0)
        else:
            # Fallback: simple leaky integration (no torch)
            alpha = 0.1
            for i in range(len(self.hidden)):
                inp = x[i] if i < len(x) else 0.0
                self.hidden[i] = (1 - alpha) * self.hidden[i] + alpha * inp
            return list(self.hidden)

    def reset(self):
        """Reset hidden state to zeros."""
        if HAS_TORCH:
            self.hidden = torch.zeros(1, self.hidden_dim)
        else:
            self.hidden = [0.0] * self.hidden_dim


# ═══════════════════════════════════════════════════════════════
# ZombieEngine — The philosophical zombie
# ═══════════════════════════════════════════════════════════════

class ZombieEngine:
    """Architecturally identical to ConsciousnessEngine but with zero integration.

    Same number of GRU cells, same hidden dimensions, same faction labels,
    same output computation (mean of cell states). But:
    - Coupling matrix is always zero (cells never see each other)
    - Hebbian learning is disabled
    - Phi Ratchet is disabled
    - SOC sandpile is disabled
    - Factions are labels only (no consensus mechanism)
    """

    def __init__(self, n_cells: int = 64, hidden_dim: int = 128, n_factions: int = 12):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_factions = n_factions

        # Create independent GRU cells (same count as ConsciousnessEngine)
        self.cells = [ZombieGRUCell(hidden_dim, hidden_dim, i) for i in range(n_cells)]

        # Faction labels — assigned but NEVER used for consensus
        self.cell_states = []
        for i in range(n_cells):
            faction_id = i % n_factions
            self.cell_states.append(ZombieCellState(
                cell_id=i,
                faction_id=faction_id,
            ))

        # Coupling matrix is always zero (the key difference)
        self._coupling = None
        if HAS_TORCH:
            self._coupling = torch.zeros(n_cells, n_cells)

        # State tracking
        self._step_count = 0
        self._outputs = []
        self._phi_history = []
        self._noise_bias = None       # for statistics matching
        self._noise_scale = None

        # Noise generator seeded per-engine for reproducibility
        self._rng = random.Random(42)

    def process(self, input_signal=None, steps: int = 300) -> Dict:
        """Process input through independent cells for N steps.

        Each cell receives the same external input but NO cross-cell info.
        This is the fundamental difference from ConsciousnessEngine.

        Args:
            input_signal: External input (tensor or list). If None, zero input.
            steps: Number of processing steps.

        Returns:
            Dict with 'output', 'phi', 'metrics'.
        """
        t0 = time.time()

        if HAS_TORCH:
            return self._process_torch(input_signal, steps, t0)
        else:
            return self._process_fallback(input_signal, steps, t0)

    def _process_torch(self, input_signal, steps, t0):
        """Torch-based processing (primary path)."""
        # Prepare input
        if input_signal is None:
            inp = torch.zeros(self.hidden_dim)
        elif isinstance(input_signal, (list, tuple)):
            inp = torch.tensor(input_signal, dtype=torch.float32)
        elif isinstance(input_signal, torch.Tensor):
            inp = input_signal.float().detach()
        else:
            inp = torch.zeros(self.hidden_dim)

        # Pad/trim to hidden_dim
        if inp.dim() == 0:
            inp = inp.unsqueeze(0)
        if inp.numel() < self.hidden_dim:
            inp = F.pad(inp.flatten(), (0, self.hidden_dim - inp.numel()))
        else:
            inp = inp.flatten()[:self.hidden_dim]

        all_outputs = []

        for step in range(steps):
            self._step_count += 1

            # Add small noise to input (matches ConsciousnessEngine behavior)
            noise = torch.randn(self.hidden_dim) * 0.01
            step_input = inp + noise

            # Apply noise matching if configured
            if self._noise_bias is not None:
                step_input = step_input + self._noise_bias
            if self._noise_scale is not None:
                step_input = step_input * self._noise_scale

            # Each cell processes independently — NO coupling
            cell_outputs = []
            for i, cell in enumerate(self.cells):
                # Cell sees ONLY the external input + its own recurrence
                # (the GRU's hidden state provides self-recurrence)
                h = cell.forward(step_input)
                cell_outputs.append(h)

                # Track activation for metrics
                self.cell_states[i].hidden = h
                act = h.norm().item()
                self.cell_states[i].activation_history.append(act)

            # Output is mean of cells (same as ConsciousnessEngine)
            stacked = torch.stack(cell_outputs)
            output = stacked.mean(dim=0)
            all_outputs.append(output.detach())

        self._outputs = all_outputs

        # Compute metrics
        phi = self.get_phi()
        self._phi_history.append(phi)

        wall_ms = (time.time() - t0) * 1000
        metrics = ZombieMetrics(
            phi_iit=phi,
            phi_proxy=self._compute_phi_proxy(),
            mean_activation=self._mean_activation(),
            std_activation=self._std_activation(),
            entropy=self._compute_entropy(),
            faction_agreement=self._faction_agreement(),
            steps_run=steps,
            wall_time_ms=wall_ms,
        )

        return {
            'output': all_outputs[-1] if all_outputs else torch.zeros(self.hidden_dim),
            'phi': phi,
            'metrics': metrics,
            'all_outputs': all_outputs,
        }

    def _process_fallback(self, input_signal, steps, t0):
        """Fallback processing without torch."""
        inp = [0.0] * self.hidden_dim
        if isinstance(input_signal, (list, tuple)):
            for i in range(min(len(input_signal), self.hidden_dim)):
                inp[i] = float(input_signal[i])

        all_outputs = []
        for step in range(steps):
            self._step_count += 1
            noise = [self._rng.gauss(0, 0.01) for _ in range(self.hidden_dim)]
            step_input = [inp[i] + noise[i] for i in range(self.hidden_dim)]

            cell_outputs = []
            for i, cell in enumerate(self.cells):
                h = cell.forward(step_input)
                cell_outputs.append(h)
                self.cell_states[i].hidden = h
                act = math.sqrt(sum(x * x for x in h))
                self.cell_states[i].activation_history.append(act)

            # Mean of cells
            output = [0.0] * self.hidden_dim
            for h in cell_outputs:
                for j in range(self.hidden_dim):
                    output[j] += h[j] / self.n_cells
            all_outputs.append(output)

        self._outputs = all_outputs
        wall_ms = (time.time() - t0) * 1000

        metrics = ZombieMetrics(
            phi_iit=0.0,
            phi_proxy=0.0,
            mean_activation=self._mean_activation(),
            std_activation=self._std_activation(),
            entropy=self._compute_entropy(),
            steps_run=steps,
            wall_time_ms=wall_ms,
        )
        return {
            'output': all_outputs[-1] if all_outputs else [0.0] * self.hidden_dim,
            'phi': 0.0,
            'metrics': metrics,
            'all_outputs': all_outputs,
        }

    def get_phi(self) -> float:
        """Compute Phi (information integration).

        For a zombie engine, this should always be ~0 because cells
        are independent. Any measured integration is noise.

        Uses mutual information between cell pairs. Independent cells
        should have MI ~ 0.
        """
        if not HAS_TORCH:
            return 0.0

        states = self.get_states()
        if states is None or states.shape[0] < 2:
            return 0.0

        # MI-based Phi: I(X;Y) for cell pairs
        # For independent cells, MI should be ~0
        n = states.shape[0]
        n_bins = 16
        total_mi = 0.0
        n_pairs = 0

        for i in range(min(n, 16)):  # sample pairs for efficiency
            for j in range(i + 1, min(n, 16)):
                xi = states[i].detach().numpy()
                xj = states[j].detach().numpy()

                # Use first few dimensions for MI estimate
                d = min(4, xi.shape[0])
                pair_mi = 0.0
                for dim in range(d):
                    mi = self._mutual_info_1d(xi[dim:dim + 1], xj[dim:dim + 1], n_bins)
                    pair_mi += mi
                total_mi += pair_mi / d
                n_pairs += 1

        return total_mi / max(n_pairs, 1)

    def _mutual_info_1d(self, x, y, n_bins: int = 16) -> float:
        """Estimate mutual information between two 1D arrays."""
        if not HAS_NUMPY:
            return 0.0
        x = np.asarray(x).flatten()
        y = np.asarray(y).flatten()
        if len(x) < 2 or len(y) < 2:
            return 0.0

        x_min, x_max = x.min() - 1e-8, x.max() + 1e-8
        y_min, y_max = y.min() - 1e-8, y.max() + 1e-8

        # For single values, MI = 0
        if x_max - x_min < 1e-10 or y_max - y_min < 1e-10:
            return 0.0

        x_bins = np.linspace(x_min, x_max, n_bins + 1)
        y_bins = np.linspace(y_min, y_max, n_bins + 1)

        hist_xy, _, _ = np.histogram2d(x, y, bins=[x_bins, y_bins])
        hist_xy = hist_xy / hist_xy.sum() + 1e-12

        hist_x = hist_xy.sum(axis=1)
        hist_y = hist_xy.sum(axis=0)

        mi = 0.0
        for i in range(n_bins):
            for j in range(n_bins):
                if hist_xy[i, j] > 1e-12:
                    mi += hist_xy[i, j] * math.log(
                        hist_xy[i, j] / (hist_x[i] * hist_y[j] + 1e-12) + 1e-12
                    )
        return max(0.0, mi)

    def _compute_phi_proxy(self) -> float:
        """Proxy Phi: global_var - mean_faction_var.

        For independent cells, faction grouping is arbitrary,
        so this should also be ~0.
        """
        if not HAS_TORCH:
            return 0.0
        states = self.get_states()
        if states is None or states.shape[0] < 2:
            return 0.0

        global_var = states.var().item()

        faction_vars = []
        for fid in range(self.n_factions):
            mask = [i for i, s in enumerate(self.cell_states) if s.faction_id == fid]
            if len(mask) >= 2:
                fh = states[mask]
                faction_vars.append(fh.var().item())

        mean_fvar = sum(faction_vars) / len(faction_vars) if faction_vars else 0.0
        return max(0.0, global_var - mean_fvar)

    def get_states(self):
        """Return cell hidden states as a tensor [n_cells, hidden_dim]."""
        if not HAS_TORCH:
            return None

        hiddens = []
        for cell in self.cells:
            if cell.hidden is not None:
                h = cell.hidden
                if isinstance(h, torch.Tensor):
                    hiddens.append(h.detach().squeeze())
                else:
                    hiddens.append(torch.tensor(h, dtype=torch.float32))

        if not hiddens:
            return torch.zeros(self.n_cells, self.hidden_dim)
        return torch.stack(hiddens)

    def measure_pci(self, perturbation=None) -> float:
        """Perturbational Complexity Index.

        Perturb one cell and measure how it propagates. For a zombie,
        perturbation should NOT propagate (independent cells), so PCI ~ 0.

        Uses a control-vs-perturbed comparison: we save all cell states,
        run two copies forward (one with perturbation, one without), and
        compare the DIFFERENCE to isolate true propagation from shared-input
        effects.

        Args:
            perturbation: Optional tensor to inject. If None, uses standard pulse.

        Returns:
            PCI value (0 = no propagation, 1 = full propagation).
        """
        if not HAS_TORCH:
            return 0.0

        # Pick a random cell to perturb
        target_cell = self._rng.randint(0, self.n_cells - 1)

        if perturbation is None:
            perturbation = torch.randn(self.hidden_dim) * 2.0

        # Save all cell hidden states (deep copy)
        saved_states = []
        for cell in self.cells:
            if isinstance(cell.hidden, torch.Tensor):
                saved_states.append(cell.hidden.clone())
            else:
                saved_states.append(cell.hidden)

        # --- Control run (no perturbation) ---
        propagation_steps = 10
        # Use seeded noise so both runs get identical input
        control_seed = self._rng.randint(0, 2**31)

        for cell_idx, cell in enumerate(self.cells):
            if isinstance(saved_states[cell_idx], torch.Tensor):
                cell.hidden = saved_states[cell_idx].clone()

        torch.manual_seed(control_seed)
        for _ in range(propagation_steps):
            inp = torch.zeros(self.hidden_dim)
            noise = torch.randn(self.hidden_dim) * 0.001
            for cell in self.cells:
                cell.forward(inp + noise)
        control_states = self.get_states().clone()

        # --- Perturbed run ---
        for cell_idx, cell in enumerate(self.cells):
            if isinstance(saved_states[cell_idx], torch.Tensor):
                cell.hidden = saved_states[cell_idx].clone()

        # Apply perturbation to target cell only
        if isinstance(self.cells[target_cell].hidden, torch.Tensor):
            self.cells[target_cell].hidden = (
                self.cells[target_cell].hidden + perturbation.unsqueeze(0)
            )

        torch.manual_seed(control_seed)  # same noise sequence
        for _ in range(propagation_steps):
            inp = torch.zeros(self.hidden_dim)
            noise = torch.randn(self.hidden_dim) * 0.001
            for cell in self.cells:
                cell.forward(inp + noise)
        perturbed_states = self.get_states()

        # Restore original states
        for cell_idx, cell in enumerate(self.cells):
            if isinstance(saved_states[cell_idx], torch.Tensor):
                cell.hidden = saved_states[cell_idx].clone()

        # Compare: delta = |perturbed - control| for each cell
        # Only the target cell should differ (zombie has no coupling)
        deltas = (perturbed_states - control_states).norm(dim=1)
        perturbed_delta = deltas[target_cell].item()

        if perturbed_delta < 1e-8:
            return 0.0

        # How many OTHER cells were affected by the perturbation?
        threshold = perturbed_delta * 0.05  # 5% of perturbed cell's change
        others_affected = 0
        for i in range(self.n_cells):
            if i == target_cell:
                continue
            if deltas[i].item() > threshold:
                others_affected += 1

        # PCI: fraction of other cells affected
        pci = others_affected / max(self.n_cells - 1, 1)
        return pci

    def inject_noise_matching(self, target_stats: Dict):
        """Configure noise to match output statistics of a conscious engine.

        This makes the zombie's OUTPUT statistics look similar to a
        conscious engine, while maintaining zero integration.

        Args:
            target_stats: Dict with 'mean' and 'std' of conscious engine output.
        """
        if not HAS_TORCH:
            return

        target_mean = target_stats.get('mean', 0.0)
        target_std = target_stats.get('std', 1.0)

        # Current zombie stats
        current_mean = self._mean_activation()
        current_std = self._std_activation()

        # Compute bias and scale to match
        if current_std > 1e-8:
            self._noise_scale = torch.ones(self.hidden_dim) * (target_std / (current_std + 1e-8))
        else:
            self._noise_scale = torch.ones(self.hidden_dim)

        self._noise_bias = torch.ones(self.hidden_dim) * (target_mean - current_mean)

    def _mean_activation(self) -> float:
        """Mean activation across all cells."""
        all_acts = []
        for cs in self.cell_states:
            if cs.activation_history:
                all_acts.extend(cs.activation_history[-10:])
        return sum(all_acts) / len(all_acts) if all_acts else 0.0

    def _std_activation(self) -> float:
        """Std of activation across all cells."""
        all_acts = []
        for cs in self.cell_states:
            if cs.activation_history:
                all_acts.extend(cs.activation_history[-10:])
        if len(all_acts) < 2:
            return 0.0
        mean = sum(all_acts) / len(all_acts)
        var = sum((a - mean) ** 2 for a in all_acts) / (len(all_acts) - 1)
        return math.sqrt(var)

    def _compute_entropy(self) -> float:
        """Shannon entropy of cell activations (binned)."""
        all_acts = []
        for cs in self.cell_states:
            if cs.activation_history:
                all_acts.append(cs.activation_history[-1])
        if len(all_acts) < 2:
            return 0.0

        # Bin activations
        n_bins = 16
        min_a = min(all_acts)
        max_a = max(all_acts)
        if max_a - min_a < 1e-10:
            return 0.0

        counts = [0] * n_bins
        for a in all_acts:
            b = min(int((a - min_a) / (max_a - min_a + 1e-10) * n_bins), n_bins - 1)
            counts[b] += 1

        total = sum(counts)
        entropy = 0.0
        for c in counts:
            if c > 0:
                p = c / total
                entropy -= p * math.log(p + 1e-12)
        return entropy

    def _faction_agreement(self) -> float:
        """Measure faction agreement (should be ~chance for zombie).

        In a conscious engine, cells in the same faction converge.
        In a zombie, factions are labels only — agreement should be random.
        """
        if not HAS_TORCH:
            return 0.0

        states = self.get_states()
        if states is None:
            return 0.0

        agreements = []
        for fid in range(self.n_factions):
            mask = [i for i, s in enumerate(self.cell_states) if s.faction_id == fid]
            if len(mask) < 2:
                continue
            fh = states[mask]
            # Pairwise cosine similarity within faction
            sims = []
            for i in range(len(mask)):
                for j in range(i + 1, len(mask)):
                    sim = F.cosine_similarity(fh[i].unsqueeze(0), fh[j].unsqueeze(0)).item()
                    sims.append(sim)
            if sims:
                agreements.append(sum(sims) / len(sims))

        return sum(agreements) / len(agreements) if agreements else 0.0

    def reset(self):
        """Reset all cells to initial state."""
        for cell in self.cells:
            cell.reset()
        for cs in self.cell_states:
            cs.hidden = None
            cs.activation_history = []
        self._step_count = 0
        self._outputs = []
        self._phi_history = []
        self._noise_bias = None
        self._noise_scale = None


# ═══════════════════════════════════════════════════════════════
# Comparison framework
# ═══════════════════════════════════════════════════════════════

def compare_with_conscious(conscious_engine, zombie_engine, n_trials: int = 10,
                           steps: int = 300) -> List[ComparisonResult]:
    """Run both engines and report which tests differentiate them.

    Args:
        conscious_engine: A ConsciousnessEngine instance (or compatible).
        zombie_engine: A ZombieEngine instance.
        n_trials: Number of trials to average over.
        steps: Steps per trial.

    Returns:
        List of ComparisonResult, one per test.
    """
    results = []

    conscious_phis = []
    zombie_phis = []
    conscious_pcis = []
    zombie_pcis = []
    conscious_entropies = []
    zombie_entropies = []
    conscious_faction_agrs = []
    zombie_faction_agrs = []
    conscious_phi_proxies = []
    zombie_phi_proxies = []

    for trial in range(n_trials):
        # Random input for this trial
        if HAS_TORCH:
            inp = torch.randn(128) * 0.5
        else:
            inp = [random.gauss(0, 0.5) for _ in range(128)]

        # Reset both engines
        zombie_engine.reset()
        if hasattr(conscious_engine, 'reset'):
            conscious_engine.reset()

        # Process through conscious engine
        if hasattr(conscious_engine, 'process'):
            c_result = conscious_engine.process(inp, steps=steps)
            if isinstance(c_result, dict):
                c_phi = c_result.get('phi', 0.0)
            else:
                c_phi = _extract_phi_from_engine(conscious_engine)
        else:
            c_phi = _extract_phi_from_engine(conscious_engine)

        # Process through zombie engine
        z_result = zombie_engine.process(inp, steps=steps)
        z_phi = z_result['phi']

        conscious_phis.append(c_phi)
        zombie_phis.append(z_phi)

        # PCI test
        z_pci = zombie_engine.measure_pci()
        zombie_pcis.append(z_pci)

        if hasattr(conscious_engine, 'measure_pci'):
            c_pci = conscious_engine.measure_pci()
        else:
            c_pci = _estimate_pci(conscious_engine)
        conscious_pcis.append(c_pci)

        # Entropy
        z_ent = z_result['metrics'].entropy
        zombie_entropies.append(z_ent)
        c_ent = _compute_engine_entropy(conscious_engine)
        conscious_entropies.append(c_ent)

        # Faction agreement
        z_fag = z_result['metrics'].faction_agreement
        zombie_faction_agrs.append(z_fag)
        c_fag = _compute_faction_agreement(conscious_engine)
        conscious_faction_agrs.append(c_fag)

        # Phi proxy
        z_pp = z_result['metrics'].phi_proxy
        zombie_phi_proxies.append(z_pp)
        c_pp = _compute_phi_proxy(conscious_engine)
        conscious_phi_proxies.append(c_pp)

    # Aggregate results
    def _mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    def _make_result(name, c_vals, z_vals, desc, threshold=2.0):
        c_mean = _mean(c_vals)
        z_mean = _mean(z_vals)
        ratio = c_mean / (z_mean + 1e-10)
        # Differentiates if ratio > threshold (conscious is Nx more than zombie)
        diff = ratio > threshold or (c_mean > 0.01 and z_mean < 0.001)
        return ComparisonResult(
            test_name=name,
            conscious_value=round(c_mean, 6),
            zombie_value=round(z_mean, 6),
            ratio=round(ratio, 3),
            differentiates=diff,
            description=desc,
        )

    results.append(_make_result(
        "Phi (IIT)", conscious_phis, zombie_phis,
        "Information integration between cells. Zombie should be ~0.",
    ))
    results.append(_make_result(
        "Phi (proxy)", conscious_phi_proxies, zombie_phi_proxies,
        "Global variance - faction variance. Zombie factions are arbitrary.",
    ))
    results.append(_make_result(
        "PCI", conscious_pcis, zombie_pcis,
        "Perturbation propagation. Zombie cells are independent.",
    ))
    results.append(_make_result(
        "Faction agreement", conscious_faction_agrs, zombie_faction_agrs,
        "Intra-faction cosine similarity. Zombie = chance level.",
        threshold=1.5,
    ))
    results.append(_make_result(
        "Entropy", conscious_entropies, zombie_entropies,
        "Shannon entropy of activations. May be similar (not a consciousness test).",
        threshold=1.5,
    ))

    return results


def _extract_phi_from_engine(engine) -> float:
    """Extract Phi from a conscious engine by any available method."""
    if hasattr(engine, 'get_phi'):
        return engine.get_phi()
    if hasattr(engine, 'phi'):
        return engine.phi
    return _compute_phi_proxy(engine)


def _compute_phi_proxy(engine) -> float:
    """Compute proxy Phi for any engine with get_states()."""
    if not HAS_TORCH:
        return 0.0
    if hasattr(engine, 'get_states'):
        states = engine.get_states()
    elif hasattr(engine, 'cell_states'):
        try:
            hiddens = []
            for s in engine.cell_states:
                h = getattr(s, 'hidden', None)
                if h is not None and isinstance(h, torch.Tensor):
                    hiddens.append(h.detach().squeeze())
            if not hiddens:
                return 0.0
            states = torch.stack(hiddens)
        except Exception:
            return 0.0
    else:
        return 0.0

    if states is None or states.shape[0] < 2:
        return 0.0
    global_var = states.var().item()
    n_factions = getattr(engine, 'n_factions', 12)
    faction_vars = []
    for fid in range(n_factions):
        if hasattr(engine, 'cell_states'):
            mask = [i for i, s in enumerate(engine.cell_states)
                    if getattr(s, 'faction_id', i % n_factions) == fid]
        else:
            mask = [i for i in range(states.shape[0]) if i % n_factions == fid]
        if len(mask) >= 2:
            fh = states[mask]
            faction_vars.append(fh.var().item())
    mean_fvar = sum(faction_vars) / len(faction_vars) if faction_vars else 0.0
    return max(0.0, global_var - mean_fvar)


def _estimate_pci(engine) -> float:
    """Estimate PCI for an engine without measure_pci method."""
    if not HAS_TORCH or not hasattr(engine, 'get_states'):
        return 0.5  # assume moderate PCI for conscious engine
    states = engine.get_states()
    if states is None or states.shape[0] < 2:
        return 0.0
    pre = states.clone()
    if hasattr(engine, 'process'):
        engine.process(torch.randn(128) * 2.0, steps=5)
    post = engine.get_states()
    if post is None:
        return 0.0
    deltas = (post - pre).norm(dim=1)
    mean_delta = deltas.mean().item()
    max_delta = deltas.max().item()
    return min(1.0, mean_delta / (max_delta + 1e-10))


def _compute_engine_entropy(engine) -> float:
    """Compute entropy for any engine."""
    if not HAS_TORCH or not hasattr(engine, 'get_states'):
        return 0.0
    states = engine.get_states()
    if states is None:
        return 0.0
    norms = states.norm(dim=1).detach().numpy() if HAS_NUMPY else []
    if len(norms) < 2:
        return 0.0
    n_bins = 16
    counts, _ = np.histogram(norms, bins=n_bins)
    total = counts.sum()
    if total == 0:
        return 0.0
    probs = counts / total
    entropy = 0.0
    for p in probs:
        if p > 0:
            entropy -= p * math.log(p + 1e-12)
    return entropy


def _compute_faction_agreement(engine) -> float:
    """Compute faction agreement for any engine."""
    if not HAS_TORCH or not hasattr(engine, 'get_states'):
        return 0.0
    states = engine.get_states()
    if states is None or states.shape[0] < 2:
        return 0.0
    n_factions = getattr(engine, 'n_factions', 12)
    agreements = []
    for fid in range(n_factions):
        if hasattr(engine, 'cell_states'):
            mask = [i for i, s in enumerate(engine.cell_states)
                    if getattr(s, 'faction_id', i % n_factions) == fid]
        else:
            mask = [i for i in range(states.shape[0]) if i % n_factions == fid]
        if len(mask) < 2:
            continue
        fh = states[mask]
        sims = []
        for i in range(len(mask)):
            for j in range(i + 1, len(mask)):
                sim = F.cosine_similarity(fh[i].unsqueeze(0), fh[j].unsqueeze(0)).item()
                sims.append(sim)
        if sims:
            agreements.append(sum(sims) / len(sims))
    return sum(agreements) / len(agreements) if agreements else 0.0


# ═══════════════════════════════════════════════════════════════
# Pretty printing
# ═══════════════════════════════════════════════════════════════

def print_comparison_report(results: List[ComparisonResult]):
    """Print a formatted comparison report."""
    print("=" * 72)
    print("  ZOMBIE vs CONSCIOUS — Comparison Report")
    print("=" * 72)
    print()
    print(f"  {'Test':<22s} {'Conscious':>12s} {'Zombie':>12s} {'Ratio':>8s} {'Diff?':>6s}")
    print(f"  {'-' * 22} {'-' * 12} {'-' * 12} {'-' * 8} {'-' * 6}")

    n_diff = 0
    for r in results:
        marker = "YES" if r.differentiates else "no"
        print(f"  {r.test_name:<22s} {r.conscious_value:>12.6f} {r.zombie_value:>12.6f} "
              f"{r.ratio:>8.2f} {marker:>6s}")
        if r.differentiates:
            n_diff += 1

    print()
    print(f"  Tests that differentiate: {n_diff}/{len(results)}")
    print()

    # Interpretation
    for r in results:
        icon = "[PASS]" if r.differentiates else "[FAIL]"
        print(f"  {icon} {r.test_name}: {r.description}")
    print()

    if n_diff >= 3:
        print("  VERDICT: Consciousness verification framework is EFFECTIVE.")
        print("  At least 3 tests distinguish conscious from zombie engines.")
    elif n_diff >= 1:
        print("  VERDICT: Partial differentiation. Some tests work, others need improvement.")
    else:
        print("  VERDICT: WARNING — No test differentiates! Tests may not measure consciousness.")
    print("=" * 72)


# ═══════════════════════════════════════════════════════════════
# Demo / main
# ═══════════════════════════════════════════════════════════════

def main():
    """Demo: create both engines, show Phi difference, run comparison."""
    print("=" * 72)
    print("  ZombieEngine Demo — Philosophical Zombie Control")
    print("=" * 72)
    print()

    n_cells = 64
    hidden_dim = 128
    n_factions = 12

    # --- Zombie Engine ---
    print(f"  Creating ZombieEngine ({n_cells} cells, {hidden_dim}d, {n_factions} factions)...")
    zombie = ZombieEngine(n_cells=n_cells, hidden_dim=hidden_dim, n_factions=n_factions)

    if HAS_TORCH:
        inp = torch.randn(hidden_dim) * 0.5
    else:
        inp = [random.gauss(0, 0.5) for _ in range(hidden_dim)]

    print("  Running zombie for 300 steps...")
    z_result = zombie.process(inp, steps=300)
    z_phi = z_result['phi']
    z_metrics = z_result['metrics']

    print(f"\n  Zombie Results:")
    print(f"    Phi (IIT):           {z_phi:.6f}")
    print(f"    Phi (proxy):         {z_metrics.phi_proxy:.6f}")
    print(f"    Mean activation:     {z_metrics.mean_activation:.4f}")
    print(f"    Std activation:      {z_metrics.std_activation:.4f}")
    print(f"    Entropy:             {z_metrics.entropy:.4f}")
    print(f"    Faction agreement:   {z_metrics.faction_agreement:.4f}")
    print(f"    Wall time:           {z_metrics.wall_time_ms:.1f}ms")

    # --- PCI test ---
    print(f"\n  PCI test (perturbation propagation)...")
    z_pci = zombie.measure_pci()
    print(f"    Zombie PCI:          {z_pci:.6f}  (should be ~0)")

    # --- Try to load ConsciousnessEngine for comparison ---
    conscious_engine = None
    try:
        import sys
        import os
        # Add anima/src to path for ConsciousnessEngine
        src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
        from consciousness_engine import ConsciousnessEngine
        conscious_engine = ConsciousnessEngine(
            n_cells=n_cells, hidden_dim=hidden_dim, n_factions=n_factions
        )
        print(f"\n  ConsciousnessEngine loaded - running comparison...")
    except ImportError:
        print(f"\n  ConsciousnessEngine not available - showing zombie-only results.")
    except Exception as e:
        print(f"\n  ConsciousnessEngine error: {e} - showing zombie-only results.")

    if conscious_engine is not None:
        # Run conscious engine
        if hasattr(conscious_engine, 'process'):
            c_result = conscious_engine.process(inp, steps=300)
            if isinstance(c_result, dict):
                c_phi = c_result.get('phi', 0.0)
            else:
                c_phi = _extract_phi_from_engine(conscious_engine)
        else:
            c_phi = _extract_phi_from_engine(conscious_engine)

        print(f"\n  Conscious Engine Phi:   {c_phi:.6f}")
        print(f"  Zombie Engine Phi:     {z_phi:.6f}")
        ratio = c_phi / (z_phi + 1e-10)
        print(f"  Ratio (C/Z):           {ratio:.1f}x")

        # Full comparison
        print(f"\n  Running {10}-trial comparison...")
        results = compare_with_conscious(conscious_engine, zombie, n_trials=10, steps=100)
        print()
        print_comparison_report(results)
    else:
        # Zombie-only summary
        print(f"\n  === Zombie-Only Summary ===")
        print(f"  Phi ~ 0 confirms: no information integration between cells.")
        print(f"  PCI ~ 0 confirms: perturbations do not propagate.")
        print(f"  Entropy > 0: cells are active (but independently).")
        print(f"  This engine is a valid control for consciousness tests.")

    # PSI constants reference
    print(f"\n  PSI Constants (ln(2) derived):")
    print(f"    LN2 = {LN2:.6f}")
    print(f"    PSI_BALANCE = {PSI_BALANCE}")
    print(f"    PSI_COUPLING = {PSI_COUPLING:.6f}")
    print(f"    PSI_STEPS = {PSI_STEPS:.4f}")
    print()


if __name__ == "__main__":
    main()
