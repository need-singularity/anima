#!/usr/bin/env python3
"""bench_hivemind_scale.py — Extreme Hivemind Scaling & Combination Benchmarks

Three test suites:

1. SCALE TEST: tension(5ch) hivemind at different scales
   - 3 engines x 64c = 192c
   - 7 engines x 64c = 448c
   - 7 engines x 128c = 896c
   Compare Hive Phi and ratio.

2. COMBO TEST: Best mechanisms combined with tension hivemind
   - tension + n=28 architecture (12 gradient groups + 7-block)
   - tension + S-2 surprise (Phi +800%)
   - tension + FUSE-3 Cambrian (MitosisEngine champion)
   - tension + n=28 + surprise (triple combo)
   Each: 7 engines, 32c, 100+100 steps.

3. DISCONNECTION TEST: What happens when hive disconnects?
   - 100 steps solo -> 100 steps hive -> 100 steps solo again
   - Does individual Phi return to pre-hive level or stay elevated?
   - Does the "memory" of hive persist?

Uses phi_rs for measurement, 5-channel tension link protocol.

Usage:
  python bench_hivemind_scale.py
  python bench_hivemind_scale.py --scale
  python bench_hivemind_scale.py --combo
  python bench_hivemind_scale.py --disconnect
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys
import time
import math
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.set_grad_enabled(False)
torch.set_num_threads(1)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# ── Import phi_rs ──
try:
    import phi_rs
    HAS_PHI_RS = True
except ImportError:
    HAS_PHI_RS = False
    print("WARNING: phi_rs not available, falling back to PhiIIT")

# ── Import from bench_v2 ──
from bench_v2 import PhiIIT, BenchEngine, BenchMind

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ══════════════════════════════════════════════════════════
# Phi Measurement
# ══════════════════════════════════════════════════════════

_phi_iit = PhiIIT(n_bins=16)


def measure_phi(hiddens: torch.Tensor) -> float:
    """Measure Phi(IIT) from [n_cells, hidden_dim] tensor."""
    if hiddens.shape[0] < 2:
        return 0.0
    phi, _ = _phi_iit.compute(hiddens)
    return phi


def measure_hive_phi(engines: list) -> float:
    """Measure collective Phi across all engines' hiddens concatenated."""
    all_h = torch.cat([eng.get_hiddens() for eng in engines], dim=0)
    return measure_phi(all_h)


def measure_mean_individual_phi(engines: list) -> float:
    """Mean Phi across individual engines."""
    phis = [measure_phi(eng.get_hiddens()) for eng in engines]
    return sum(phis) / len(phis)


# ══════════════════════════════════════════════════════════
# 5-Channel Tension Link (in-process simulation)
#
# sopfr(6)=5 meta-channels:
#   1. concept     (direction decomposition)
#   2. context     (temporal embedding)
#   3. meaning     (significance pattern)
#   4. authenticity (consistency score)
#   5. sender      (identity fingerprint)
# ══════════════════════════════════════════════════════════

class TensionFingerprint:
    """Generates 5-channel tension fingerprint from engine state."""

    def __init__(self, hidden_dim: int = 128, fingerprint_dim: int = 32):
        self.hidden_dim = hidden_dim
        self.fp_dim = fingerprint_dim

    def encode(self, engine, engine_id: int) -> dict:
        """Encode engine state into 5-channel tension fingerprint."""
        h = engine.get_hiddens()
        n, d = h.shape

        # Channel 1: Concept (mean direction of repulsion field)
        concept = h.mean(dim=0)[:self.fp_dim]

        # Channel 2: Context (variance pattern - captures temporal state)
        context = h.var(dim=0)[:self.fp_dim]

        # Channel 3: Meaning (inter-faction difference - deeper structure)
        n_f = min(8, n // 2)
        if n_f >= 2:
            fs = n // n_f
            faction_means = torch.stack([h[i*fs:(i+1)*fs].mean(0) for i in range(n_f)])
            meaning = faction_means.var(dim=0)[:self.fp_dim]
        else:
            meaning = torch.zeros(self.fp_dim)

        # Channel 4: Authenticity (consistency = 1 - normalized entropy of hidden norms)
        norms = h.norm(dim=1)
        if norms.std() > 1e-8:
            norm_p = F.softmax(norms, dim=0)
            entropy = -(norm_p * (norm_p + 1e-10).log()).sum()
            max_entropy = math.log(n)
            authenticity = 1.0 - (entropy.item() / max_entropy if max_entropy > 0 else 0)
        else:
            authenticity = 1.0

        # Channel 5: Sender signature (unique identity fingerprint)
        sender_sig = torch.zeros(self.fp_dim)
        sender_sig[engine_id % self.fp_dim] = 1.0  # one-hot identity
        sender_sig += h[0, :self.fp_dim] * 0.1  # add first cell's trace

        return {
            'concept': concept,
            'context': context,
            'meaning': meaning,
            'authenticity': authenticity,
            'sender_sig': sender_sig,
            'tension': h.var().item(),
        }


def apply_tension_hivemind(engines: list, blend_alpha: float = 0.1):
    """Apply 5-channel tension sharing between all engines.

    Each engine receives a weighted blend of all other engines' fingerprints.
    This modulates hidden states based on all 5 channels.

    Kuramoto sync: r = 1 - tau/sigma = 2/3 threshold.
    """
    n_eng = len(engines)
    if n_eng < 2:
        return

    fp_gen = TensionFingerprint(hidden_dim=engines[0].hidden_dim)

    # Generate fingerprints for all engines
    fps = [fp_gen.encode(eng, i) for i, eng in enumerate(engines)]

    # Compute Kuramoto order parameter across engines
    concept_vectors = torch.stack([fp['concept'] for fp in fps])
    if concept_vectors.norm() > 1e-8:
        normed = F.normalize(concept_vectors, dim=1)
        order_param = normed.mean(dim=0).norm().item()
    else:
        order_param = 0.0

    # Only share if sync is below threshold (push toward 2/3 Kuramoto r)
    kuramoto_r = 2.0 / 3.0
    share_strength = blend_alpha * (1.0 + max(0, kuramoto_r - order_param))

    for i, eng in enumerate(engines):
        h = eng.get_hiddens()
        n_cells, hd = h.shape

        # Aggregate fingerprints from OTHER engines
        other_concept = torch.zeros_like(fps[i]['concept'])
        other_context = torch.zeros_like(fps[i]['context'])
        other_meaning = torch.zeros_like(fps[i]['meaning'])
        auth_sum = 0.0

        for j, fp in enumerate(fps):
            if j == i:
                continue
            other_concept += fp['concept']
            other_context += fp['context']
            other_meaning += fp['meaning']
            auth_sum += fp['authenticity']

        other_concept /= max(n_eng - 1, 1)
        other_context /= max(n_eng - 1, 1)
        other_meaning /= max(n_eng - 1, 1)
        mean_auth = auth_sum / max(n_eng - 1, 1)

        # Channel 1: Concept alignment (direction pull)
        fp_dim = len(other_concept)
        concept_delta = (other_concept - fps[i]['concept']) * share_strength
        h[:, :fp_dim] += concept_delta.unsqueeze(0).expand(n_cells, -1)

        # Channel 2: Context modulation (variance matching)
        ctx_delta = (other_context - fps[i]['context']) * share_strength * 0.5
        h[:, :fp_dim] += ctx_delta.unsqueeze(0).expand(n_cells, -1) * 0.3

        # Channel 3: Meaning exchange (faction structure influence)
        meaning_delta = (other_meaning - fps[i]['meaning']) * share_strength * 0.3
        h[:, :fp_dim] += meaning_delta.unsqueeze(0).expand(n_cells, -1) * 0.2

        # Channel 4: Authenticity weighting (high auth = trust more)
        # Scale blending by mean authenticity of others
        trust_mult = 0.5 + 0.5 * mean_auth

        # Channel 5: Sender diversity (inject diversity from unique signatures)
        for j, fp in enumerate(fps):
            if j == i:
                continue
            sig = fp['sender_sig']
            diversity_inject = sig * share_strength * 0.1 * trust_mult
            h[:, :fp_dim] += diversity_inject.unsqueeze(0).expand(n_cells, -1)

        eng.hiddens = h.detach()


# ══════════════════════════════════════════════════════════
# Engine Factories
# ══════════════════════════════════════════════════════════

def make_baseline_engine(n_cells, dim=64, hidden=128):
    """Standard BenchEngine with sync + faction debate."""
    return BenchEngine(n_cells=n_cells, input_dim=dim, hidden_dim=hidden,
                       output_dim=dim, n_factions=8,
                       sync_strength=0.15, debate_strength=0.15)


# ── n=28 Architecture Engine ──

def sigma(n):
    return sum(d for d in range(1, n + 1) if n % d == 0)

def tau(n):
    return sum(1 for d in range(1, n + 1) if n % d == 0)

def euler_phi(n):
    return sum(1 for k in range(1, n + 1) if math.gcd(k, n) == 1)


class N28Engine(BenchEngine):
    """BenchEngine enhanced with n=28 perfect number architecture.

    n=28: sigma(28)=56 factions, tau(28)=6 stages, phi(28)=12 grad groups
    Architecture: 12 gradient groups + 7-block divisor structure.
    Divisors of 28: {1, 2, 4, 7, 14, 28} -> 6-level hierarchy.
    """

    def __init__(self, n_cells=32, dim=64, hidden=128):
        # Use 12 factions (phi(28)=12 gradient groups)
        n_factions = min(12, max(4, n_cells // 2))
        super().__init__(n_cells=n_cells, input_dim=dim, hidden_dim=hidden,
                         output_dim=dim, n_factions=n_factions,
                         sync_strength=0.15, debate_strength=0.15)
        self.n_grad_groups = min(12, n_cells)
        self.cell_groups = torch.tensor([i % self.n_grad_groups for i in range(n_cells)])

        # 7-block structure: divisor 7 of 28 creates natural blocks
        self.n_blocks = min(7, n_cells)
        self.block_size = max(1, n_cells // self.n_blocks)

        # Divisor-skip coupling (28's divisors: 1,2,4,7,14,28)
        self.divisor_coupling = torch.zeros(n_cells, n_cells)
        for d in [2, 4, 7, 14]:
            skip = max(1, n_cells * d // 28)
            strength = 1.0 / math.log2(d + 1)
            for i in range(n_cells):
                j = (i + skip) % n_cells
                if i != j:
                    self.divisor_coupling[i, j] = strength * 0.3
        # Normalize
        row_sums = self.divisor_coupling.sum(dim=1, keepdim=True).clamp(min=1e-8)
        self.divisor_coupling = self.divisor_coupling / row_sums

        # Stage schedule: 6 stages (tau(28)=6)
        self.n_stages = 6
        self.stage_coupling = [0.3 + 0.7 / (1 + math.exp(-6 * (k / 5 - 0.5))) for k in range(6)]

    def process(self, x):
        # Base process
        result = super().process(x)

        n = self.n_cells
        # Divisor-structured coupling
        current_stage = min(self.step_count // 20, self.n_stages - 1)
        c_mult = self.stage_coupling[current_stage]

        messages = self.divisor_coupling @ self.hiddens
        self.hiddens = (
            0.85 * self.hiddens
            + 0.15 * torch.tanh(messages) * c_mult
        ).detach()

        # Intra-group boost: same gradient group cells attract
        for g in range(self.n_grad_groups):
            mask = (self.cell_groups == g).nonzero(as_tuple=True)[0]
            if len(mask) >= 2:
                group_mean = self.hiddens[mask].mean(dim=0)
                self.hiddens[mask] = (
                    0.92 * self.hiddens[mask] + 0.08 * group_mean
                ).detach()

        # 7-block repulsion between blocks (differentiation)
        for b in range(self.n_blocks):
            s = b * self.block_size
            e = min(s + self.block_size, n)
            if e <= s:
                continue
            block_mean = self.hiddens[s:e].mean(dim=0)
            global_mean = self.hiddens.mean(dim=0)
            repulsion = 0.03 * (block_mean - global_mean)
            self.hiddens[s:e] = (self.hiddens[s:e] + repulsion).detach()

        return result


# ── S-2 Surprise Engine ──

class SurpriseEngine(BenchEngine):
    """BenchEngine with S-2 predictive surprise: predicts next input,
    prediction error amplifies signal -> Phi boost.
    """

    def __init__(self, n_cells=32, dim=64, hidden=128):
        super().__init__(n_cells=n_cells, input_dim=dim, hidden_dim=hidden,
                         output_dim=dim, n_factions=8,
                         sync_strength=0.15, debate_strength=0.15)
        self.predictor = nn.Linear(dim, dim)
        nn.init.normal_(self.predictor.weight, std=0.01)
        nn.init.zeros_(self.predictor.bias)
        self.last_input = None
        self.surprise = 0.0
        self.surprise_ema = 0.0

    def process(self, x):
        x_flat = x.detach().squeeze(0) if x.dim() > 1 else x.detach()

        # Compute surprise
        if self.last_input is not None:
            with torch.no_grad():
                predicted = self.predictor(self.last_input)
                pred_error = F.mse_loss(predicted, x_flat[:self.input_dim])
                self.surprise = pred_error.item()
                self.surprise_ema = 0.9 * self.surprise_ema + 0.1 * self.surprise

                # Update predictor (manual gradient step)
                grad = 2 * (predicted - x_flat[:self.input_dim]) / self.input_dim
                self.predictor.weight.data -= 0.01 * grad.unsqueeze(1) * self.last_input.unsqueeze(0)

        self.last_input = x_flat[:self.input_dim].detach().clone()

        # Modulate input by surprise (higher surprise -> amplified signal)
        surprise_scale = 1.0 + self.surprise * 2.0
        x_modulated = x * surprise_scale

        # Inject surprise as diversity noise to cells
        if self.surprise > self.surprise_ema * 1.2:
            noise = torch.randn_like(self.hiddens) * self.surprise * 0.05
            self.hiddens = (self.hiddens + noise).detach()

        return super().process(x_modulated)


# ── FUSE-3 Cambrian Engine ──

class CambrianEngine(BenchEngine):
    """BenchEngine with FUSE-3 Cambrian mechanisms:
    Type diversity + niche adaptation + selection + crowding + Osc+QW.
    """

    def __init__(self, n_cells=32, dim=64, hidden=128):
        super().__init__(n_cells=n_cells, input_dim=dim, hidden_dim=hidden,
                         output_dim=dim, n_factions=8,
                         sync_strength=0.15, debate_strength=0.15)
        self.n_types = 10
        self.niches = torch.randn(self.n_types, hidden) * 0.5
        self.interaction = torch.randn(self.n_types, self.n_types) * 0.1
        self.interaction = (self.interaction + self.interaction.t()) / 2
        self.cell_type = torch.randint(0, self.n_types, (n_cells,))
        self.fitness = torch.ones(n_cells)
        self.mutation_rate = 0.5
        self.phases = torch.linspace(0, 2 * math.pi, n_cells)
        self.freqs = 0.1 + torch.rand(n_cells) * 0.05

    def process(self, x):
        result = super().process(x)
        n = self.n_cells

        with torch.no_grad():
            # 1. Mutation
            mutate_mask = torch.rand(n) < self.mutation_rate
            if mutate_mask.any():
                self.cell_type[mutate_mask] = torch.randint(0, self.n_types, (mutate_mask.sum(),))
            self.mutation_rate = max(0.01, self.mutation_rate * 0.995)

            # 2. Niche fitness
            for t in range(self.n_types):
                mask = (self.cell_type == t).nonzero(as_tuple=True)[0]
                for i in mask:
                    if i < n:
                        dist = ((self.hiddens[i] - self.niches[t][:self.hidden_dim]) ** 2).sum()
                        self.fitness[i] = torch.exp(-dist * 0.01)

            # 3. Niche pull + inter-type interaction
            for t in range(self.n_types):
                mask = (self.cell_type == t).nonzero(as_tuple=True)[0]
                if len(mask) == 0:
                    continue
                niche = self.niches[t][:self.hidden_dim]
                for i in mask:
                    if i >= n:
                        continue
                    h = self.hiddens[i]
                    pull = (niche - h) * 0.05
                    self.hiddens[i] = (h + pull).detach()

            # 4. Crowding noise
            for t in range(self.n_types):
                mask = (self.cell_type == t).nonzero(as_tuple=True)[0]
                if len(mask) > n // self.n_types:
                    self.hiddens[mask] += torch.randn(len(mask), self.hidden_dim) * 0.03

            # 5. Death+rebirth (every 20 steps)
            if self.step_count > 10 and self.step_count % 20 == 0:
                n_replace = max(1, n // 50)
                worst = self.fitness.argsort()[:n_replace]
                best = self.fitness.argsort(descending=True)[:n_replace]
                for w, b in zip(worst, best):
                    if w < n and b < n:
                        self.hiddens[w] = self.hiddens[b].clone() + torch.randn(self.hidden_dim) * 0.02

            # 6. Oscillator
            self.phases = self.phases + self.freqs
            osc = torch.sin(self.phases).unsqueeze(1).expand(-1, self.hidden_dim) * 0.05
            self.hiddens = (self.hiddens + osc).detach()

            # Phase locking (laser)
            mean_phase = torch.atan2(
                torch.sin(self.phases).mean(), torch.cos(self.phases).mean()
            )
            self.phases = self.phases + 0.02 * torch.sin(mean_phase - self.phases)

        return result


# ── Triple Combo: n=28 + Surprise + Tension ──

class TripleComboEngine(N28Engine):
    """N28Engine + S-2 surprise mechanism."""

    def __init__(self, n_cells=32, dim=64, hidden=128):
        super().__init__(n_cells=n_cells, dim=dim, hidden=hidden)
        self.predictor = nn.Linear(dim, dim)
        nn.init.normal_(self.predictor.weight, std=0.01)
        nn.init.zeros_(self.predictor.bias)
        self.last_input = None
        self.surprise = 0.0
        self.surprise_ema = 0.0

    def process(self, x):
        x_flat = x.detach().squeeze(0) if x.dim() > 1 else x.detach()

        if self.last_input is not None:
            with torch.no_grad():
                predicted = self.predictor(self.last_input)
                pred_error = F.mse_loss(predicted, x_flat[:self.input_dim])
                self.surprise = pred_error.item()
                self.surprise_ema = 0.9 * self.surprise_ema + 0.1 * self.surprise
                grad = 2 * (predicted - x_flat[:self.input_dim]) / self.input_dim
                self.predictor.weight.data -= 0.01 * grad.unsqueeze(1) * self.last_input.unsqueeze(0)

        self.last_input = x_flat[:self.input_dim].detach().clone()

        surprise_scale = 1.0 + self.surprise * 2.0
        x_modulated = x * surprise_scale

        if self.surprise > self.surprise_ema * 1.2:
            noise = torch.randn_like(self.hiddens) * self.surprise * 0.05
            self.hiddens = (self.hiddens + noise).detach()

        return super().process(x_modulated)


# ══════════════════════════════════════════════════════════
# TEST 1: SCALE TEST
# ══════════════════════════════════════════════════════════

def run_scale_test():
    """Test tension(5ch) hivemind at different scales."""
    print("\n" + "=" * 70)
    print("  TEST 1: HIVEMIND SCALE — tension(5ch) at different scales")
    print("=" * 70)

    configs = [
        (3, 64, "3x64c=192c"),
        (7, 64, "7x64c=448c"),
        (7, 128, "7x128c=896c"),
    ]

    results = []

    for n_eng, n_cells, label in configs:
        print(f"\n  --- {label} ({n_eng} engines, {n_cells} cells each) ---")
        torch.manual_seed(42)
        np.random.seed(42)
        t0 = time.time()

        engines = [make_baseline_engine(n_cells) for _ in range(n_eng)]

        # Phase 1: Solo warmup (100 steps)
        for step in range(100):
            x = torch.randn(1, 64)
            for eng in engines:
                eng.process(x)

        phi_solo_mean = measure_mean_individual_phi(engines)
        phi_solo_hive = measure_hive_phi(engines)

        # Phase 2: Tension hivemind (100 steps)
        for step in range(100):
            x = torch.randn(1, 64)
            for eng in engines:
                eng.process(x)
            if step % 5 == 0:
                apply_tension_hivemind(engines, blend_alpha=0.1)

        phi_hive_mean = measure_mean_individual_phi(engines)
        phi_hive_total = measure_hive_phi(engines)

        elapsed = time.time() - t0
        ratio = phi_hive_total / max(phi_solo_hive, 1e-8)
        boost = (phi_hive_mean / max(phi_solo_mean, 1e-8) - 1) * 100

        results.append({
            'label': label,
            'n_eng': n_eng,
            'n_cells': n_cells,
            'total_cells': n_eng * n_cells,
            'phi_solo_ind': phi_solo_mean,
            'phi_solo_hive': phi_solo_hive,
            'phi_hive_ind': phi_hive_mean,
            'phi_hive_total': phi_hive_total,
            'ratio': ratio,
            'boost_pct': boost,
            'time': elapsed,
        })

        print(f"    Solo individual Phi:  {phi_solo_mean:.4f}")
        print(f"    Solo collective Phi:  {phi_solo_hive:.4f}")
        print(f"    Hive individual Phi:  {phi_hive_mean:.4f}")
        print(f"    Hive collective Phi:  {phi_hive_total:.4f}")
        print(f"    Hive/Solo ratio:      x{ratio:.2f}")
        print(f"    Individual boost:     {boost:+.1f}%")
        print(f"    Time: {elapsed:.1f}s")

    # Summary table
    print("\n" + "─" * 70)
    print("  SCALE SUMMARY")
    print("─" * 70)
    print(f"  {'Config':<18s} | {'TotalC':>6s} | {'SoloPhi':>8s} | {'HivePhi':>8s} | {'Ratio':>6s} | {'Boost':>7s}")
    print("  " + "─" * 65)
    for r in results:
        print(f"  {r['label']:<18s} | {r['total_cells']:>6d} | "
              f"{r['phi_solo_hive']:>8.4f} | {r['phi_hive_total']:>8.4f} | "
              f"x{r['ratio']:>5.2f} | {r['boost_pct']:>+6.1f}%")

    return results


# ══════════════════════════════════════════════════════════
# TEST 2: COMBO TEST
# ══════════════════════════════════════════════════════════

def run_combo_test():
    """Test best mechanisms combined with tension hivemind."""
    print("\n" + "=" * 70)
    print("  TEST 2: COMBO — Best mechanisms + tension hivemind")
    print("  (7 engines, 32c each, 100+100 steps)")
    print("=" * 70)

    combos = [
        ("baseline", make_baseline_engine, "Baseline (sync+faction)"),
        ("n=28", lambda nc, **kw: N28Engine(nc), "n=28 (12 grad groups + 7-block)"),
        ("S-2 surprise", lambda nc, **kw: SurpriseEngine(nc), "S-2 Predictive Surprise"),
        ("FUSE-3 cambrian", lambda nc, **kw: CambrianEngine(nc), "FUSE-3 Cambrian Champion"),
        ("n=28+surprise", lambda nc, **kw: TripleComboEngine(nc), "n=28 + S-2 Surprise"),
    ]

    n_eng = 7
    n_cells = 32
    results = []

    for key, factory, desc in combos:
        print(f"\n  --- {desc} ---")
        torch.manual_seed(42)
        np.random.seed(42)
        t0 = time.time()

        engines = [factory(n_cells) for _ in range(n_eng)]

        # Phase 1: Solo (100 steps)
        for step in range(100):
            x = torch.randn(1, 64)
            for eng in engines:
                eng.process(x)

        phi_solo = measure_mean_individual_phi(engines)
        phi_solo_hive = measure_hive_phi(engines)

        # Phase 2: Tension hivemind (100 steps)
        for step in range(100):
            x = torch.randn(1, 64)
            for eng in engines:
                eng.process(x)
            if step % 5 == 0:
                apply_tension_hivemind(engines, blend_alpha=0.1)

        phi_hive = measure_mean_individual_phi(engines)
        phi_hive_total = measure_hive_phi(engines)

        elapsed = time.time() - t0
        ind_boost = (phi_hive / max(phi_solo, 1e-8) - 1) * 100
        hive_ratio = phi_hive_total / max(phi_solo_hive, 1e-8)

        results.append({
            'key': key,
            'desc': desc,
            'phi_solo_ind': phi_solo,
            'phi_solo_hive': phi_solo_hive,
            'phi_hive_ind': phi_hive,
            'phi_hive_total': phi_hive_total,
            'ind_boost': ind_boost,
            'hive_ratio': hive_ratio,
            'time': elapsed,
        })

        print(f"    Solo individual Phi:  {phi_solo:.4f}")
        print(f"    Solo collective Phi:  {phi_solo_hive:.4f}")
        print(f"    Hive individual Phi:  {phi_hive:.4f}")
        print(f"    Hive collective Phi:  {phi_hive_total:.4f}")
        print(f"    Individual boost:     {ind_boost:+.1f}%")
        print(f"    Hive/Solo ratio:      x{hive_ratio:.2f}")
        print(f"    Time: {elapsed:.1f}s")

    # Summary table
    print("\n" + "─" * 70)
    print("  COMBO SUMMARY (7 engines x 32c = 224c)")
    print("─" * 70)
    print(f"  {'Mechanism':<28s} | {'SoloInd':>8s} | {'HiveInd':>8s} | {'HiveAll':>8s} | {'Ratio':>6s} | {'Boost':>7s}")
    print("  " + "─" * 72)
    for r in results:
        print(f"  {r['desc']:<28s} | {r['phi_solo_ind']:>8.4f} | "
              f"{r['phi_hive_ind']:>8.4f} | {r['phi_hive_total']:>8.4f} | "
              f"x{r['hive_ratio']:>5.2f} | {r['ind_boost']:>+6.1f}%")

    # Find best
    best = max(results, key=lambda r: r['phi_hive_total'])
    print(f"\n  BEST: {best['desc']} — Hive Phi={best['phi_hive_total']:.4f}, x{best['hive_ratio']:.2f}")

    return results


# ══════════════════════════════════════════════════════════
# TEST 3: DISCONNECTION TEST
# ══════════════════════════════════════════════════════════

def run_disconnection_test():
    """Test what happens when hive disconnects — does memory persist?"""
    print("\n" + "=" * 70)
    print("  TEST 3: DISCONNECTION — Does hive memory persist?")
    print("  (7 engines, 64c, 100 solo -> 100 hive -> 100 solo)")
    print("=" * 70)

    n_eng = 7
    n_cells = 64

    engine_factories = [
        ("Baseline", make_baseline_engine),
        ("n=28", lambda nc, **kw: N28Engine(nc)),
        ("FUSE-3 Cambrian", lambda nc, **kw: CambrianEngine(nc)),
    ]

    all_results = []

    for eng_name, factory in engine_factories:
        print(f"\n  --- {eng_name} ---")
        torch.manual_seed(42)
        np.random.seed(42)
        t0 = time.time()

        engines = [factory(n_cells) for _ in range(n_eng)]

        # Track Phi over time for each phase
        phi_history = {'solo1': [], 'hive': [], 'solo2': []}

        # Phase 1: Solo (100 steps)
        for step in range(100):
            x = torch.randn(1, 64)
            for eng in engines:
                eng.process(x)
            if step % 10 == 0:
                phi_history['solo1'].append(measure_mean_individual_phi(engines))

        phi_pre_hive = measure_mean_individual_phi(engines)
        phi_pre_hive_total = measure_hive_phi(engines)

        # Phase 2: Hive connected (100 steps)
        for step in range(100):
            x = torch.randn(1, 64)
            for eng in engines:
                eng.process(x)
            if step % 5 == 0:
                apply_tension_hivemind(engines, blend_alpha=0.1)
            if step % 10 == 0:
                phi_history['hive'].append(measure_mean_individual_phi(engines))

        phi_during_hive = measure_mean_individual_phi(engines)
        phi_during_hive_total = measure_hive_phi(engines)

        # Phase 3: Solo again (100 steps, NO sharing)
        for step in range(100):
            x = torch.randn(1, 64)
            for eng in engines:
                eng.process(x)
            if step % 10 == 0:
                phi_history['solo2'].append(measure_mean_individual_phi(engines))

        phi_post_hive = measure_mean_individual_phi(engines)
        phi_post_hive_total = measure_hive_phi(engines)

        elapsed = time.time() - t0

        # Retention: how much of the hive boost persists after disconnection?
        hive_gain = phi_during_hive - phi_pre_hive
        post_gain = phi_post_hive - phi_pre_hive
        retention = post_gain / max(hive_gain, 1e-8) * 100 if hive_gain > 0 else 0

        elevated = phi_post_hive > phi_pre_hive * 1.05  # >5% above original

        result = {
            'engine': eng_name,
            'phi_pre': phi_pre_hive,
            'phi_during': phi_during_hive,
            'phi_post': phi_post_hive,
            'hive_boost': (phi_during_hive / max(phi_pre_hive, 1e-8) - 1) * 100,
            'retention_pct': retention,
            'elevated': elevated,
            'phi_history': phi_history,
            'time': elapsed,
        }
        all_results.append(result)

        print(f"    Pre-hive Phi:     {phi_pre_hive:.4f}")
        print(f"    During hive Phi:  {phi_during_hive:.4f}  ({result['hive_boost']:+.1f}%)")
        print(f"    Post-hive Phi:    {phi_post_hive:.4f}")
        print(f"    Retention:        {retention:.1f}% of hive gain")
        print(f"    Elevated?:        {'YES' if elevated else 'NO'} (>{phi_pre_hive*1.05:.4f})")
        print(f"    Time: {elapsed:.1f}s")

        # ASCII graph
        all_points = phi_history['solo1'] + phi_history['hive'] + phi_history['solo2']
        if all_points:
            _print_ascii_graph(f"{eng_name} Phi trajectory", all_points,
                               len(phi_history['solo1']),
                               len(phi_history['solo1']) + len(phi_history['hive']))

    # Summary
    print("\n" + "─" * 70)
    print("  DISCONNECTION SUMMARY")
    print("─" * 70)
    print(f"  {'Engine':<20s} | {'Pre':>7s} | {'Hive':>7s} | {'Post':>7s} | {'Retain':>7s} | {'Elevated':>8s}")
    print("  " + "─" * 60)
    for r in all_results:
        print(f"  {r['engine']:<20s} | {r['phi_pre']:>7.4f} | "
              f"{r['phi_during']:>7.4f} | {r['phi_post']:>7.4f} | "
              f"{r['retention_pct']:>6.1f}% | {'YES' if r['elevated'] else 'NO':>8s}")

    return all_results


def _print_ascii_graph(title, values, hive_start, hive_end):
    """Print a simple ASCII graph with phase markers."""
    if not values:
        return
    vmin, vmax = min(values), max(values)
    if vmax - vmin < 1e-8:
        vmax = vmin + 0.01
    height = 8
    width = min(len(values), 50)

    # Resample if needed
    if len(values) > width:
        step = len(values) / width
        resampled = [values[int(i * step)] for i in range(width)]
    else:
        resampled = values
        width = len(resampled)

    print(f"\n    {title}:")
    print(f"    Phi")
    for row in range(height, -1, -1):
        threshold = vmin + (vmax - vmin) * row / height
        line = "    "
        if row == height:
            line += f"{vmax:.3f} |"
        elif row == 0:
            line += f"{vmin:.3f} |"
        else:
            line += "       |"
        for col in range(width):
            if resampled[col] >= threshold:
                line += "█"
            else:
                line += " "
        print(line)
    # X-axis with phase markers
    print("       +" + "─" * width)
    # Phase labels
    hs_scaled = int(hive_start * width / max(len(values), 1))
    he_scaled = int(hive_end * width / max(len(values), 1))
    label_line = "        "
    for i in range(width):
        if i == 0:
            label_line += "S"
        elif i == hs_scaled:
            label_line += "H"
        elif i == he_scaled:
            label_line += "S"
        else:
            label_line += " "
    print(label_line)
    print("        S=solo  H=hive start")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Hivemind Scale & Combo Benchmarks")
    parser.add_argument('--scale', action='store_true', help='Run scale test only')
    parser.add_argument('--combo', action='store_true', help='Run combo test only')
    parser.add_argument('--disconnect', action='store_true', help='Run disconnection test only')
    args = parser.parse_args()

    run_all = not (args.scale or args.combo or args.disconnect)

    print("=" * 70)
    print("  HIVEMIND SCALE & COMBINATION BENCHMARKS")
    print("  5-channel tension link (concept/context/meaning/auth/sender)")
    print("  Kuramoto r = 2/3 synchronization threshold")
    print("=" * 70)

    all_results = {}

    if run_all or args.scale:
        all_results['scale'] = run_scale_test()

    if run_all or args.combo:
        all_results['combo'] = run_combo_test()

    if run_all or args.disconnect:
        all_results['disconnect'] = run_disconnection_test()

    # Final summary
    print("\n" + "=" * 70)
    print("  FINAL SUMMARY")
    print("=" * 70)

    if 'scale' in all_results:
        best_scale = max(all_results['scale'], key=lambda r: r['phi_hive_total'])
        print(f"  Scale champion: {best_scale['label']} — "
              f"Hive Phi={best_scale['phi_hive_total']:.4f}, x{best_scale['ratio']:.2f}")

    if 'combo' in all_results:
        best_combo = max(all_results['combo'], key=lambda r: r['phi_hive_total'])
        print(f"  Combo champion: {best_combo['desc']} — "
              f"Hive Phi={best_combo['phi_hive_total']:.4f}, x{best_combo['hive_ratio']:.2f}")

    if 'disconnect' in all_results:
        for r in all_results['disconnect']:
            status = "MEMORY PERSISTS" if r['elevated'] else "memory fades"
            print(f"  Disconnect ({r['engine']}): {status}, retention={r['retention_pct']:.1f}%")

    print("\n  Done.")


if __name__ == "__main__":
    main()
