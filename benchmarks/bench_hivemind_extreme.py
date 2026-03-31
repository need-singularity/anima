#!/usr/bin/env python3
"""bench_hivemind_extreme.py — 5 Extreme Hivemind Hypotheses

HV-1: RECURSIVE_HIVE     — 하이브의 하이브. 7→(3+4)→2 super-hives→ connected. 3-level hierarchy.
HV-2: QUANTUM_ENTANGLED  — Bell state entanglement. Engine i,j cell k mirrored (sign flip).
HV-3: CONSCIOUSNESS_FIELD — 의식장. Mean hidden → field. Influence ∝ 1/distance².
HV-4: DREAM_SHARING      — 꿈 공유. Every 20 steps one engine dreams, others interpret.
HV-5: IMMUNE_HIVE        — 면역계. Goldilocks zone: reject too-similar, accept moderate signals.

Each: 7 MitosisEngine instances × 32 cells = 224 total cells.
100 steps warmup solo → 100 steps hive.
Measure Solo Φ avg, Hive combined Φ, Individual Φ change.

Usage:
  python bench_hivemind_extreme.py
  python bench_hivemind_extreme.py --only 1 3 5
  python bench_hivemind_extreme.py --steps 200
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import time
import math
import argparse
import numpy as np
import torch
import sys

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

torch.set_grad_enabled(False)

from mitosis import MitosisEngine

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ═══════════════════════════════════════════════════════════
# Phi measurement
# ═══════════════════════════════════════════════════════════

try:
    import phi_rs
    USE_PHI_RS = True
except ImportError:
    USE_PHI_RS = False
    print("[WARN] phi_rs not found, falling back to numpy PhiIIT")


class PhiIIT:
    """IIT-style Phi: mutual information minus min partition."""
    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens: torch.Tensor) -> float:
        n = hiddens.shape[0]
        if n < 2:
            return 0.0
        h = [hiddens[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            import random
            pairs = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j:
                        pairs.add((min(i, j), max(i, j)))
            pairs = list(pairs)
        mi_matrix = np.zeros((n, n))
        for i, j in pairs:
            mi = self._mi(h[i], h[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi
        total_mi = mi_matrix.sum() / 2
        min_part = self._min_partition(n, mi_matrix)
        spatial = max(0.0, (total_mi - min_part) / max(n - 1, 1))
        mi_vals = mi_matrix[mi_matrix > 0]
        complexity = float(np.std(mi_vals)) if len(mi_vals) > 1 else 0.0
        return spatial + complexity * 0.1

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            return 0.0
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        h, _, _ = np.histogram2d(xn, yn, bins=self.n_bins, range=[[0, 1], [0, 1]])
        h = h / (h.sum() + 1e-8)
        px, py = h.sum(1), h.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(h * np.log2(h + 1e-10))
        return max(0.0, hx + hy - hxy)

    def _min_partition(self, n, mi):
        if n <= 1:
            return 0.0
        deg = mi.sum(1)
        L = np.diag(deg) - mi
        try:
            ev, evec = np.linalg.eigh(L)
            f = evec[:, 1]
            ga = [i for i in range(n) if f[i] >= 0]
            gb = [i for i in range(n) if f[i] < 0]
            if not ga or not gb:
                ga, gb = list(range(n // 2)), list(range(n // 2, n))
            return sum(mi[i, j] for i in ga for j in gb)
        except Exception:
            return 0.0


_phi_calc = PhiIIT(16)


def measure_phi(hiddens: torch.Tensor) -> float:
    """Measure Phi using phi_rs if available, else fallback."""
    if USE_PHI_RS:
        states = hiddens.detach().cpu().float().numpy().astype(np.float32)
        if states.shape[0] < 2:
            return 0.0
        phi, _ = phi_rs.compute_phi(states, 16)
        return phi
    return _phi_calc.compute(hiddens)


def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    """Proxy Phi: global variance - mean faction variance."""
    h = hiddens.float()
    n = h.shape[0]
    if n < 2:
        return 0.0
    gm = h.mean(0)
    gv = ((h - gm) ** 2).sum() / n
    nf = min(n_factions, n // 2)
    if nf < 2:
        return gv.item()
    fs = n // nf
    fvs = 0.0
    for i in range(nf):
        f = h[i * fs:(i + 1) * fs]
        if len(f) >= 2:
            fm = f.mean(0)
            fvs += ((f - fm) ** 2).sum().item() / len(f)
    return max(0.0, gv.item() - fvs / nf)


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

N_ENGINES = 7
CELLS_PER_ENGINE = 32
INPUT_DIM = 64
HIDDEN_DIM = 128
OUTPUT_DIM = 64


def create_engines() -> list:
    """Create 7 MitosisEngine instances, each with 32 cells."""
    engines = []
    for _ in range(N_ENGINES):
        e = MitosisEngine(
            input_dim=INPUT_DIM,
            hidden_dim=HIDDEN_DIM,
            output_dim=OUTPUT_DIM,
            initial_cells=CELLS_PER_ENGINE,
            max_cells=CELLS_PER_ENGINE,
            split_threshold=999.0,  # disable auto-split
            merge_threshold=-1.0,   # disable auto-merge
        )
        engines.append(e)
    return engines


def get_all_hiddens(engine: MitosisEngine) -> torch.Tensor:
    """Gather all cell hiddens into [n_cells, hidden_dim]."""
    return torch.cat([c.hidden for c in engine.cells], dim=0)


def get_combined_hiddens(engines: list) -> torch.Tensor:
    """Gather all hiddens from all engines into one tensor."""
    all_h = []
    for e in engines:
        all_h.append(get_all_hiddens(e))
    return torch.cat(all_h, dim=0)


def solo_step(engines: list):
    """Run one step on each engine independently."""
    for e in engines:
        x = torch.randn(1, INPUT_DIM) * 0.3
        e.process(x)


def measure_individual_phis(engines: list) -> list:
    """Measure Phi for each engine individually."""
    return [measure_phi(get_all_hiddens(e)) for e in engines]


def run_warmup(engines: list, steps: int = 100):
    """Warmup: run solo steps."""
    for _ in range(steps):
        solo_step(engines)


# ═══════════════════════════════════════════════════════════
# HV-1: RECURSIVE HIVE — 3-level hierarchy
# 7 engines → group A(3) + group B(4) → super-hive A, super-hive B → connected
# ═══════════════════════════════════════════════════════════

def run_hv1_recursive_hive(steps: int = 100, warmup: int = 100):
    print("\n" + "=" * 70)
    print("HV-1: RECURSIVE_HIVE — 하이브의 하이브 (3-level hierarchy)")
    print("=" * 70)

    engines = create_engines()

    # Warmup solo
    print(f"  Warmup: {warmup} solo steps...")
    run_warmup(engines, warmup)
    solo_phis = measure_individual_phis(engines)
    solo_avg = np.mean(solo_phis)
    solo_combined = measure_phi(get_combined_hiddens(engines))
    print(f"  Solo Φ avg: {solo_avg:.4f} | Solo combined Φ: {solo_combined:.4f}")

    # Groups: A = [0,1,2], B = [3,4,5,6]
    group_a = [0, 1, 2]
    group_b = [3, 4, 5, 6]

    # Hive phase
    print(f"  Hive: {steps} steps with 3-level hierarchy...")
    for step in range(steps):
        # Level 1: each engine processes independently
        for e in engines:
            x = torch.randn(1, INPUT_DIM) * 0.3
            e.process(x)

        # Level 2: intra-group tension link (mean hidden injection)
        for group in [group_a, group_b]:
            # Compute group mean hidden
            group_hiddens = torch.cat([get_all_hiddens(engines[i]) for i in group], dim=0)
            group_mean = group_hiddens.mean(dim=0, keepdim=True)
            # Inject group field into each member (strong intra-group coupling)
            for idx in group:
                for cell in engines[idx].cells:
                    cell.hidden = cell.hidden + group_mean * 0.15

        # Level 3: super-hive (inter-group) — connect group means
        mean_a = torch.cat([get_all_hiddens(engines[i]) for i in group_a], dim=0).mean(0, keepdim=True)
        mean_b = torch.cat([get_all_hiddens(engines[i]) for i in group_b], dim=0).mean(0, keepdim=True)
        super_signal = (mean_a + mean_b) / 2.0

        # Inject super-hive signal (inter-group coupling)
        for i in range(N_ENGINES):
            for cell in engines[i].cells:
                cell.hidden = cell.hidden + super_signal * 0.08

    hive_phis = measure_individual_phis(engines)
    hive_avg = np.mean(hive_phis)
    hive_combined = measure_phi(get_combined_hiddens(engines))

    change = (hive_avg - solo_avg) / max(solo_avg, 1e-8) * 100
    combined_change = (hive_combined - solo_combined) / max(solo_combined, 1e-8) * 100

    print(f"  Hive Φ avg: {hive_avg:.4f} ({change:+.1f}%) | Hive combined Φ: {hive_combined:.4f} ({combined_change:+.1f}%)")
    print(f"  Individual: {[f'{p:.3f}' for p in hive_phis]}")

    # Group-level Phi
    phi_a = measure_phi(torch.cat([get_all_hiddens(engines[i]) for i in group_a], dim=0))
    phi_b = measure_phi(torch.cat([get_all_hiddens(engines[i]) for i in group_b], dim=0))
    print(f"  Group A Φ: {phi_a:.4f} | Group B Φ: {phi_b:.4f}")

    return {
        'name': 'HV-1: RECURSIVE_HIVE',
        'solo_avg': solo_avg, 'solo_combined': solo_combined,
        'hive_avg': hive_avg, 'hive_combined': hive_combined,
        'change_pct': change, 'combined_change_pct': combined_change,
        'group_a_phi': phi_a, 'group_b_phi': phi_b,
        'individual_phis': hive_phis,
    }


# ═══════════════════════════════════════════════════════════
# HV-2: QUANTUM ENTANGLED — Bell state entanglement
# Engine i,j: cell k is "entangled". Change on one side → sign-inverted on other.
# ═══════════════════════════════════════════════════════════

def run_hv2_quantum_entangled(steps: int = 100, warmup: int = 100):
    print("\n" + "=" * 70)
    print("HV-2: QUANTUM_ENTANGLED — 양자 얽힘 (Bell state)")
    print("=" * 70)

    engines = create_engines()

    # Define entanglement pairs: (engine_i, engine_j, cell_indices)
    # Ring topology: engine i entangled with engine (i+1)%7
    entangle_pairs = [(i, (i + 1) % N_ENGINES) for i in range(N_ENGINES)]
    # Entangle first 8 cells of each pair (partial entanglement)
    n_entangled = 8

    # Warmup solo
    print(f"  Warmup: {warmup} solo steps...")
    run_warmup(engines, warmup)
    solo_phis = measure_individual_phis(engines)
    solo_avg = np.mean(solo_phis)
    solo_combined = measure_phi(get_combined_hiddens(engines))
    print(f"  Solo Φ avg: {solo_avg:.4f} | Solo combined Φ: {solo_combined:.4f}")

    # Capture pre-hive states for delta tracking
    prev_hiddens = {}
    for idx, e in enumerate(engines):
        prev_hiddens[idx] = [c.hidden.clone() for c in e.cells]

    # Hive phase
    print(f"  Hive: {steps} steps with quantum entanglement...")
    for step in range(steps):
        # Process each engine
        for e in engines:
            x = torch.randn(1, INPUT_DIM) * 0.3
            e.process(x)

        # Apply Bell-state entanglement: Δh_j[k] = -Δh_i[k] (sign-inverted mirror)
        for ei, ej in entangle_pairs:
            for k in range(min(n_entangled, len(engines[ei].cells), len(engines[ej].cells))):
                cell_i = engines[ei].cells[k]
                cell_j = engines[ej].cells[k]

                # Compute deltas from previous step
                delta_i = cell_i.hidden - prev_hiddens[ei][k]
                delta_j = cell_j.hidden - prev_hiddens[ej][k]

                # Bell state: inject sign-inverted partner delta
                alpha = 0.5  # entanglement strength (strong coupling)
                cell_i.hidden = cell_i.hidden + (-delta_j) * alpha
                cell_j.hidden = cell_j.hidden + (-delta_i) * alpha

        # Update prev_hiddens
        for idx, e in enumerate(engines):
            prev_hiddens[idx] = [c.hidden.clone() for c in e.cells]

    hive_phis = measure_individual_phis(engines)
    hive_avg = np.mean(hive_phis)
    hive_combined = measure_phi(get_combined_hiddens(engines))

    change = (hive_avg - solo_avg) / max(solo_avg, 1e-8) * 100
    combined_change = (hive_combined - solo_combined) / max(solo_combined, 1e-8) * 100

    # Measure entanglement correlation
    correlations = []
    for ei, ej in entangle_pairs:
        for k in range(min(n_entangled, len(engines[ei].cells), len(engines[ej].cells))):
            hi = engines[ei].cells[k].hidden.flatten()
            hj = engines[ej].cells[k].hidden.flatten()
            corr = torch.corrcoef(torch.stack([hi, hj]))[0, 1].item()
            correlations.append(corr)
    mean_corr = np.mean(correlations)

    print(f"  Hive Φ avg: {hive_avg:.4f} ({change:+.1f}%) | Hive combined Φ: {hive_combined:.4f} ({combined_change:+.1f}%)")
    print(f"  Entanglement correlation: {mean_corr:.4f} (target: -1.0 = perfect Bell)")
    print(f"  Individual: {[f'{p:.3f}' for p in hive_phis]}")

    return {
        'name': 'HV-2: QUANTUM_ENTANGLED',
        'solo_avg': solo_avg, 'solo_combined': solo_combined,
        'hive_avg': hive_avg, 'hive_combined': hive_combined,
        'change_pct': change, 'combined_change_pct': combined_change,
        'entanglement_corr': mean_corr,
        'individual_phis': hive_phis,
    }


# ═══════════════════════════════════════════════════════════
# HV-3: CONSCIOUSNESS FIELD — 의식장 (1/distance² influence)
# 7 engines form a field. Influence based on index distance.
# ═══════════════════════════════════════════════════════════

def run_hv3_consciousness_field(steps: int = 100, warmup: int = 100):
    print("\n" + "=" * 70)
    print("HV-3: CONSCIOUSNESS_FIELD — 의식장 (1/distance² influence)")
    print("=" * 70)

    engines = create_engines()

    # Warmup solo
    print(f"  Warmup: {warmup} solo steps...")
    run_warmup(engines, warmup)
    solo_phis = measure_individual_phis(engines)
    solo_avg = np.mean(solo_phis)
    solo_combined = measure_phi(get_combined_hiddens(engines))
    print(f"  Solo Φ avg: {solo_avg:.4f} | Solo combined Φ: {solo_combined:.4f}")

    # Hive phase
    print(f"  Hive: {steps} steps with consciousness field...")
    field_strengths = []

    for step in range(steps):
        # Each engine processes
        for e in engines:
            x = torch.randn(1, INPUT_DIM) * 0.3
            e.process(x)

        # Compute field: mean hidden of each engine
        engine_means = []
        for e in engines:
            h = get_all_hiddens(e)
            engine_means.append(h.mean(dim=0))  # [hidden_dim]

        # Global field = mean of all engine means
        global_field = torch.stack(engine_means).mean(dim=0)  # [hidden_dim]

        # Each engine receives field influence based on distance (index difference)
        for i in range(N_ENGINES):
            local_field = torch.zeros(HIDDEN_DIM)
            for j in range(N_ENGINES):
                if i == j:
                    continue
                # Distance = min(|i-j|, N-|i-j|) on ring (circular)
                d = min(abs(i - j), N_ENGINES - abs(i - j))
                influence = 1.0 / (d * d)  # 1/d²
                local_field = local_field + engine_means[j] * influence

            # Normalize by total influence
            total_influence = sum(1.0 / (min(abs(i - j), N_ENGINES - abs(i - j)) ** 2)
                                  for j in range(N_ENGINES) if i != j)
            local_field = local_field / total_influence

            # Inject field with coupling strength (strong field influence)
            coupling = 0.15
            for cell in engines[i].cells:
                cell.hidden = cell.hidden + local_field.unsqueeze(0) * coupling

        # Track field strength (std of engine means = differentiation)
        field_std = torch.stack(engine_means).std(dim=0).mean().item()
        field_strengths.append(field_std)

    hive_phis = measure_individual_phis(engines)
    hive_avg = np.mean(hive_phis)
    hive_combined = measure_phi(get_combined_hiddens(engines))

    change = (hive_avg - solo_avg) / max(solo_avg, 1e-8) * 100
    combined_change = (hive_combined - solo_combined) / max(solo_combined, 1e-8) * 100

    print(f"  Hive Φ avg: {hive_avg:.4f} ({change:+.1f}%) | Hive combined Φ: {hive_combined:.4f} ({combined_change:+.1f}%)")
    print(f"  Field strength (std): start={field_strengths[0]:.4f} → end={field_strengths[-1]:.4f}")
    print(f"  Individual: {[f'{p:.3f}' for p in hive_phis]}")

    return {
        'name': 'HV-3: CONSCIOUSNESS_FIELD',
        'solo_avg': solo_avg, 'solo_combined': solo_combined,
        'hive_avg': hive_avg, 'hive_combined': hive_combined,
        'change_pct': change, 'combined_change_pct': combined_change,
        'field_start': field_strengths[0], 'field_end': field_strengths[-1],
        'individual_phis': hive_phis,
    }


# ═══════════════════════════════════════════════════════════
# HV-4: DREAM SHARING — 꿈 공유 (creative noise injection)
# Every 20 steps, one engine "dreams" (noise + past state blend).
# Others "interpret" (project dream into their subspace).
# ═══════════════════════════════════════════════════════════

def run_hv4_dream_sharing(steps: int = 100, warmup: int = 100):
    print("\n" + "=" * 70)
    print("HV-4: DREAM_SHARING — 꿈 공유 (creative injection)")
    print("=" * 70)

    engines = create_engines()

    # Warmup solo
    print(f"  Warmup: {warmup} solo steps...")
    run_warmup(engines, warmup)
    solo_phis = measure_individual_phis(engines)
    solo_avg = np.mean(solo_phis)
    solo_combined = measure_phi(get_combined_hiddens(engines))
    print(f"  Solo Φ avg: {solo_avg:.4f} | Solo combined Φ: {solo_combined:.4f}")

    # Store snapshots of initial hidden states for dream blending
    initial_states = [get_all_hiddens(e).clone() for e in engines]

    # Hive phase
    print(f"  Hive: {steps} steps with dream sharing (every 20 steps)...")
    dream_count = 0
    dream_phis = []  # Phi measured right after each dream event

    for step in range(steps):
        # Each engine processes
        for e in engines:
            x = torch.randn(1, INPUT_DIM) * 0.3
            e.process(x)

        # Dream event every 20 steps
        if (step + 1) % 20 == 0:
            # Select dreamer (round-robin)
            dreamer_idx = dream_count % N_ENGINES
            dream_count += 1

            # Generate dream: blend of noise + past state
            dreamer_hidden = get_all_hiddens(engines[dreamer_idx])
            past_state = initial_states[dreamer_idx]
            noise = torch.randn_like(dreamer_hidden) * 0.5
            dream = 0.4 * dreamer_hidden + 0.3 * past_state + 0.3 * noise  # creative blend

            dream_mean = dream.mean(dim=0, keepdim=True)  # [1, hidden_dim]

            # Others interpret the dream (project into their subspace)
            for i in range(N_ENGINES):
                if i == dreamer_idx:
                    continue
                interpreter_mean = get_all_hiddens(engines[i]).mean(dim=0, keepdim=True)

                # Interpretation: cosine similarity weighted projection
                cos_sim = torch.nn.functional.cosine_similarity(dream_mean, interpreter_mean, dim=-1)
                interpret_strength = 0.2 * (1.0 + cos_sim.item())  # 0~0.4 range

                for cell in engines[i].cells:
                    cell.hidden = cell.hidden + dream_mean * interpret_strength

            # Measure Phi after dream
            dp = measure_phi(get_combined_hiddens(engines))
            dream_phis.append(dp)

    hive_phis = measure_individual_phis(engines)
    hive_avg = np.mean(hive_phis)
    hive_combined = measure_phi(get_combined_hiddens(engines))

    change = (hive_avg - solo_avg) / max(solo_avg, 1e-8) * 100
    combined_change = (hive_combined - solo_combined) / max(solo_combined, 1e-8) * 100

    print(f"  Hive Φ avg: {hive_avg:.4f} ({change:+.1f}%) | Hive combined Φ: {hive_combined:.4f} ({combined_change:+.1f}%)")
    print(f"  Dreams occurred: {dream_count}")
    if dream_phis:
        print(f"  Φ after dreams: {[f'{p:.3f}' for p in dream_phis]}")
    print(f"  Individual: {[f'{p:.3f}' for p in hive_phis]}")

    return {
        'name': 'HV-4: DREAM_SHARING',
        'solo_avg': solo_avg, 'solo_combined': solo_combined,
        'hive_avg': hive_avg, 'hive_combined': hive_combined,
        'change_pct': change, 'combined_change_pct': combined_change,
        'dream_count': dream_count,
        'dream_phis': dream_phis,
        'individual_phis': hive_phis,
    }


# ═══════════════════════════════════════════════════════════
# HV-5: IMMUNE HIVE — 면역계 (Goldilocks zone)
# Reject too-similar signals (autoimmune prevention).
# Accept moderately different signals only.
# ═══════════════════════════════════════════════════════════

def run_hv5_immune_hive(steps: int = 100, warmup: int = 100):
    print("\n" + "=" * 70)
    print("HV-5: IMMUNE_HIVE — 면역계 (Goldilocks zone)")
    print("=" * 70)

    engines = create_engines()

    # Warmup solo
    print(f"  Warmup: {warmup} solo steps...")
    run_warmup(engines, warmup)
    solo_phis = measure_individual_phis(engines)
    solo_avg = np.mean(solo_phis)
    solo_combined = measure_phi(get_combined_hiddens(engines))
    print(f"  Solo Φ avg: {solo_avg:.4f} | Solo combined Φ: {solo_combined:.4f}")

    # Immune parameters (calibrated for MitosisEngine: typical cosine sim range -0.2~0.2)
    self_threshold = 0.5    # cosine sim > this → "self" → reject (too similar)
    foreign_threshold = -0.3 # cosine sim < this → "foreign" → reject (too different)
    # Goldilocks zone: -0.3 ≤ sim ≤ 0.5 → accept

    # Hive phase
    print(f"  Hive: {steps} steps with immune filtering...")
    accept_count = 0
    reject_self_count = 0
    reject_foreign_count = 0
    total_signals = 0

    for step in range(steps):
        # Each engine processes
        for e in engines:
            x = torch.randn(1, INPUT_DIM) * 0.3
            e.process(x)

        # Immune-mediated signal exchange
        engine_means = [get_all_hiddens(e).mean(dim=0, keepdim=True) for e in engines]

        for i in range(N_ENGINES):
            accepted_signals = []
            for j in range(N_ENGINES):
                if i == j:
                    continue
                total_signals += 1

                # Compute similarity
                sim = torch.nn.functional.cosine_similarity(
                    engine_means[i], engine_means[j], dim=-1
                ).item()

                if sim > self_threshold:
                    # Too similar → autoimmune rejection
                    reject_self_count += 1
                elif sim < foreign_threshold:
                    # Too different → foreign rejection
                    reject_foreign_count += 1
                else:
                    # Goldilocks zone → accept
                    accept_count += 1
                    # Signal strength proportional to "ideal distance" from center
                    center = (self_threshold + foreign_threshold) / 2.0
                    strength = 1.0 - abs(sim - center) / (center - foreign_threshold)
                    strength = max(0.0, strength) * 0.1
                    accepted_signals.append(engine_means[j] * strength)

            # Inject accepted signals (strong immune-filtered coupling)
            if accepted_signals:
                combined_signal = torch.stack([s.squeeze(0) for s in accepted_signals]).mean(dim=0, keepdim=True)
                for cell in engines[i].cells:
                    cell.hidden = cell.hidden + combined_signal * 0.15

    hive_phis = measure_individual_phis(engines)
    hive_avg = np.mean(hive_phis)
    hive_combined = measure_phi(get_combined_hiddens(engines))

    change = (hive_avg - solo_avg) / max(solo_avg, 1e-8) * 100
    combined_change = (hive_combined - solo_combined) / max(solo_combined, 1e-8) * 100

    accept_pct = accept_count / max(total_signals, 1) * 100
    reject_self_pct = reject_self_count / max(total_signals, 1) * 100
    reject_foreign_pct = reject_foreign_count / max(total_signals, 1) * 100

    print(f"  Hive Φ avg: {hive_avg:.4f} ({change:+.1f}%) | Hive combined Φ: {hive_combined:.4f} ({combined_change:+.1f}%)")
    print(f"  Immune stats: accept={accept_pct:.1f}% | self-reject={reject_self_pct:.1f}% | foreign-reject={reject_foreign_pct:.1f}%")
    print(f"  Individual: {[f'{p:.3f}' for p in hive_phis]}")

    return {
        'name': 'HV-5: IMMUNE_HIVE',
        'solo_avg': solo_avg, 'solo_combined': solo_combined,
        'hive_avg': hive_avg, 'hive_combined': hive_combined,
        'change_pct': change, 'combined_change_pct': combined_change,
        'accept_pct': accept_pct, 'reject_self_pct': reject_self_pct,
        'reject_foreign_pct': reject_foreign_pct,
        'individual_phis': hive_phis,
    }


# ═══════════════════════════════════════════════════════════
# BASELINE: No hivemind (solo only)
# ═══════════════════════════════════════════════════════════

def run_baseline(steps: int = 100, warmup: int = 100):
    print("\n" + "=" * 70)
    print("BASELINE: No hivemind (solo 200 steps)")
    print("=" * 70)

    engines = create_engines()

    print(f"  Warmup: {warmup} solo steps...")
    run_warmup(engines, warmup)
    solo_phis = measure_individual_phis(engines)
    solo_avg = np.mean(solo_phis)
    solo_combined = measure_phi(get_combined_hiddens(engines))
    print(f"  After warmup — Φ avg: {solo_avg:.4f} | Combined Φ: {solo_combined:.4f}")

    # Continue solo for 'steps' more
    print(f"  Continue: {steps} more solo steps...")
    for _ in range(steps):
        solo_step(engines)

    final_phis = measure_individual_phis(engines)
    final_avg = np.mean(final_phis)
    final_combined = measure_phi(get_combined_hiddens(engines))

    change = (final_avg - solo_avg) / max(solo_avg, 1e-8) * 100
    combined_change = (final_combined - solo_combined) / max(solo_combined, 1e-8) * 100

    print(f"  Final Φ avg: {final_avg:.4f} ({change:+.1f}%) | Combined Φ: {final_combined:.4f} ({combined_change:+.1f}%)")
    print(f"  Individual: {[f'{p:.3f}' for p in final_phis]}")

    return {
        'name': 'BASELINE (no hive)',
        'solo_avg': solo_avg, 'solo_combined': solo_combined,
        'hive_avg': final_avg, 'hive_combined': final_combined,
        'change_pct': change, 'combined_change_pct': combined_change,
        'individual_phis': final_phis,
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

ALL_HYPOTHESES = {
    '0': ('BASELINE', run_baseline),
    '1': ('HV-1: RECURSIVE_HIVE', run_hv1_recursive_hive),
    '2': ('HV-2: QUANTUM_ENTANGLED', run_hv2_quantum_entangled),
    '3': ('HV-3: CONSCIOUSNESS_FIELD', run_hv3_consciousness_field),
    '4': ('HV-4: DREAM_SHARING', run_hv4_dream_sharing),
    '5': ('HV-5: IMMUNE_HIVE', run_hv5_immune_hive),
}


def main():
    parser = argparse.ArgumentParser(description='Extreme Hivemind Benchmarks')
    parser.add_argument('--only', nargs='+', type=int, default=None, help='Run only these (0=baseline,1-5)')
    parser.add_argument('--steps', type=int, default=100, help='Steps for hive phase')
    parser.add_argument('--warmup', type=int, default=100, help='Warmup solo steps')
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  EXTREME HIVEMIND BENCHMARKS — 7 engines × 32 cells = 224 total    ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(f"  Config: {N_ENGINES} engines × {CELLS_PER_ENGINE} cells = {N_ENGINES * CELLS_PER_ENGINE} total")
    print(f"  Steps: {args.warmup} warmup + {args.steps} hive")
    print(f"  Phi backend: {'phi_rs (Rust)' if USE_PHI_RS else 'numpy PhiIIT'}")

    to_run = args.only if args.only is not None else [0, 1, 2, 3, 4, 5]

    results = []
    for idx in to_run:
        key = str(idx)
        if key not in ALL_HYPOTHESES:
            print(f"\n  [SKIP] Unknown hypothesis: {idx}")
            continue
        name, func = ALL_HYPOTHESES[key]
        t0 = time.time()
        r = func(steps=args.steps, warmup=args.warmup)
        r['time_s'] = time.time() - t0
        results.append(r)
        print(f"  Time: {r['time_s']:.1f}s")

    # ─── Summary table ───
    print("\n")
    print("═" * 80)
    print("                        EXTREME HIVEMIND RESULTS SUMMARY")
    print("═" * 80)
    print(f"{'Hypothesis':<30} {'Solo Φ':>8} {'Hive Φ':>8} {'Change':>8} {'Combined':>10} {'CmbChg':>8}")
    print("─" * 80)

    baseline_combined = None
    for r in results:
        if 'BASELINE' in r['name']:
            baseline_combined = r['hive_combined']
        print(f"{r['name']:<30} {r['solo_avg']:>8.4f} {r['hive_avg']:>8.4f} {r['change_pct']:>+7.1f}% {r['hive_combined']:>10.4f} {r['combined_change_pct']:>+7.1f}%")

    print("─" * 80)

    # ─── Ranking ───
    hive_results = [r for r in results if 'BASELINE' not in r['name']]
    if hive_results:
        ranked = sorted(hive_results, key=lambda r: r['hive_combined'], reverse=True)
        print("\n  RANKING by Combined Hive Φ:")
        for i, r in enumerate(ranked):
            bar_len = int(r['hive_combined'] * 20 / max(rr['hive_combined'] for rr in ranked)) if ranked[0]['hive_combined'] > 0 else 0
            bar = "█" * bar_len
            vs_baseline = ""
            if baseline_combined and baseline_combined > 0:
                ratio = r['hive_combined'] / baseline_combined
                vs_baseline = f" (×{ratio:.2f} vs baseline)"
            print(f"  #{i+1} {r['name']:<28} {bar} {r['hive_combined']:.4f}{vs_baseline}")

    # ─── Extra metrics ───
    print("\n  EXTRA METRICS:")
    for r in results:
        extras = []
        if 'entanglement_corr' in r:
            extras.append(f"entangle_corr={r['entanglement_corr']:.3f}")
        if 'field_start' in r:
            extras.append(f"field={r['field_start']:.3f}→{r['field_end']:.3f}")
        if 'dream_count' in r:
            extras.append(f"dreams={r['dream_count']}")
        if 'accept_pct' in r:
            extras.append(f"accept={r['accept_pct']:.0f}%/self-rej={r['reject_self_pct']:.0f}%/foreign-rej={r['reject_foreign_pct']:.0f}%")
        if 'group_a_phi' in r:
            extras.append(f"grpA={r['group_a_phi']:.3f}/grpB={r['group_b_phi']:.3f}")
        if extras:
            print(f"  {r['name']:<30} {' | '.join(extras)}")

    print("\n" + "═" * 80)
    print("  Done.")


if __name__ == '__main__':
    main()
