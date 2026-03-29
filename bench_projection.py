#!/usr/bin/env python3
"""bench_projection.py — Cross-Dimension Projection Strategy Benchmark

Tests 6 projection strategies for consciousness preservation during dimension upgrade.
Measures Phi before (source dim) and after (target dim) to compute preservation %.

Strategies:
  PROJ-1: Tiled Identity (current baseline, 432%)
  PROJ-2: PCA-based projection (preserve principal components)
  PROJ-3: Interpolation (lerp tiled identity + random orthogonal)
  PROJ-4: Learned projection (10-step reconstruction loss)
  PROJ-5: Fractal tiling (self-similar at different scales)
  PROJ-6: Adaptation steps (project + 50 sync/faction steps to re-organize)

Usage:
  python3 bench_projection.py                   # Run all strategies, all dim pairs
  python3 bench_projection.py --only 1 2 3      # Run specific strategies
  python3 bench_projection.py --dims 128 256     # Custom source→target
  python3 bench_projection.py --steps 50         # More warm-up steps
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import argparse
import sys
import os
import copy
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine
from consciousness_meter import PhiCalculator


# ─── Configuration ───

NUM_CELLS = 64
NUM_FACTIONS = 8
WARMUP_STEPS = 30
SILENCE_RATIO = 0.7
SYNC_STRENGTH = 0.15
DEBATE_STRENGTH = 0.12
IB2_TOP = 0.25
NOISE = 0.02
ADAPT_STEPS = 50  # for PROJ-6

DIM_PAIRS = [
    (128, 256),
    (128, 384),
    (128, 512),
]


@dataclass
class ProjectionResult:
    strategy: str
    strategy_id: str
    src_dim: int
    tgt_dim: int
    phi_source: float
    phi_after: float
    preservation_pct: float
    elapsed_sec: float
    extra: Dict = None

    def __post_init__(self):
        if self.extra is None:
            self.extra = {}


# ─── Warm up a source engine to build real Phi ───

def warmup_engine(dim: int, hidden: int = None, steps: int = WARMUP_STEPS,
                  cells: int = NUM_CELLS) -> Tuple[MitosisEngine, float]:
    """Create and warm up a MitosisEngine, return (engine, phi)."""
    if hidden is None:
        hidden = dim * 2
    engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=cells)
    phi_calc = PhiCalculator(n_bins=16)
    l2 = torch.zeros(hidden)

    while len(engine.cells) < cells:
        engine._create_cell(parent=engine.cells[0])

    for step_i in range(steps):
        frac = step_i / steps
        with torch.no_grad():
            cur = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            l2 = 0.9 * l2 + 0.1 * cur
            x = 0.5 * cur[:dim].unsqueeze(0) + 0.5 * l2[:dim].unsqueeze(0)

            if frac < SILENCE_RATIO:
                x = x * 0.1
            else:
                x = x * 2.0

        engine.process(x)

        with torch.no_grad():
            nc = len(engine.cells)
            fs = nc // NUM_FACTIONS
            if fs >= 2:
                facts = [engine.cells[i*fs:(i+1)*fs] for i in range(NUM_FACTIONS)]
                facts = [f for f in facts if f]
                if len(facts) >= 2:
                    ops = [torch.stack([c.hidden for c in f]).mean(dim=0) for f in facts]
                    for i, f in enumerate(facts):
                        for c in f:
                            c.hidden = (1 - SYNC_STRENGTH) * c.hidden + SYNC_STRENGTH * ops[i]
                    if frac > SILENCE_RATIO:
                        for i, f in enumerate(facts):
                            others = [ops[j] for j in range(len(facts)) if j != i]
                            if others:
                                oa = torch.stack(others).mean(dim=0)
                                for c in f[:max(1, len(f) // 4)]:
                                    c.hidden = (1 - DEBATE_STRENGTH) * c.hidden + DEBATE_STRENGTH * oa

            # IB2
            if nc >= 8:
                norms = [engine.cells[i].hidden.norm().item() for i in range(nc)]
                thr = sorted(norms, reverse=True)[max(1, int(nc * IB2_TOP))]
                for i in range(nc):
                    engine.cells[i].hidden *= 1.03 if norms[i] > thr else 0.97

            # Noise + homeostasis
            for c in engine.cells:
                c.hidden += torch.randn_like(c.hidden) * NOISE
                n = c.hidden.norm().item()
                if n > 2.0:
                    c.hidden *= 1.0 / (n + 1e-8)

    phi, _ = phi_calc.compute_phi(engine)
    return engine, phi


# ─── Extract cell hidden states ───

def extract_hiddens(engine: MitosisEngine) -> torch.Tensor:
    """Return [N, hidden_dim] tensor of all cell hidden states."""
    return torch.stack([c.hidden.squeeze().detach().clone() for c in engine.cells])


# ─── Apply projected hiddens to a new engine ───

def build_target_engine(tgt_dim: int, projected_hiddens: torch.Tensor,
                        cells: int = NUM_CELLS) -> MitosisEngine:
    """Create a target engine and inject projected hidden states."""
    hidden = tgt_dim * 2
    engine = MitosisEngine(tgt_dim, hidden, tgt_dim, initial_cells=2, max_cells=cells)

    while len(engine.cells) < cells:
        engine._create_cell(parent=engine.cells[0])

    with torch.no_grad():
        for i, c in enumerate(engine.cells):
            if i < projected_hiddens.shape[0]:
                h = projected_hiddens[i]
                # Ensure correct shape [1, hidden_dim]
                if h.dim() == 1:
                    h = h.unsqueeze(0)
                # Pad/truncate to match target hidden_dim
                if h.shape[-1] < hidden:
                    pad = torch.zeros(1, hidden - h.shape[-1])
                    h = torch.cat([h, pad], dim=-1)
                elif h.shape[-1] > hidden:
                    h = h[:, :hidden]
                c.hidden = h
    return engine


def measure_phi(engine: MitosisEngine) -> float:
    phi_calc = PhiCalculator(n_bins=16)
    phi, _ = phi_calc.compute_phi(engine)
    return phi


# ===================================================================
# PROJECTION STRATEGIES
# ===================================================================

def proj1_tiled_identity(hiddens: torch.Tensor, src_dim: int, tgt_dim: int) -> torch.Tensor:
    """PROJ-1: Tiled Identity (current baseline).
    Each new dim maps to old dim cyclically. Norm preserved."""
    src_hidden = hiddens.shape[1]
    tgt_hidden = tgt_dim * 2

    w = torch.zeros(tgt_hidden, src_hidden)
    for i in range(tgt_hidden):
        w[i, i % src_hidden] = 1.0
    w += torch.randn_like(w) * 0.01

    proj = F.linear(hiddens, w)
    # Norm preservation
    src_norms = hiddens.norm(dim=1, keepdim=True)
    tgt_norms = proj.norm(dim=1, keepdim=True).clamp(min=1e-8)
    proj = proj * (src_norms / tgt_norms)
    return proj


def proj2_pca(hiddens: torch.Tensor, src_dim: int, tgt_dim: int) -> torch.Tensor:
    """PROJ-2: PCA-based projection.
    Compute PCA of source cells, project into new space preserving principal components."""
    src_hidden = hiddens.shape[1]
    tgt_hidden = tgt_dim * 2

    # Center
    mean = hiddens.mean(dim=0, keepdim=True)
    centered = hiddens - mean

    # SVD for PCA
    U, S, Vt = torch.linalg.svd(centered, full_matrices=False)
    # Vt rows are principal components in source space
    n_components = min(src_hidden, tgt_hidden, hiddens.shape[0])

    # Build projection: map principal components to target dims
    # Target basis: first n_components dims get PCA directions, rest get tiled
    w = torch.zeros(tgt_hidden, src_hidden)

    # PCA part: scale by singular values to preserve variance structure
    for i in range(n_components):
        w[i] = Vt[i] * (S[i] / (S[0] + 1e-8))  # normalized by max singular value

    # Fill remaining dims with tiled identity (fallback)
    for i in range(n_components, tgt_hidden):
        w[i, i % src_hidden] = 1.0
        w[i] += torch.randn(src_hidden) * 0.005

    proj = F.linear(hiddens, w)
    # Norm preservation
    src_norms = hiddens.norm(dim=1, keepdim=True)
    tgt_norms = proj.norm(dim=1, keepdim=True).clamp(min=1e-8)
    proj = proj * (src_norms / tgt_norms)
    return proj


def proj3_interpolation(hiddens: torch.Tensor, src_dim: int, tgt_dim: int,
                         alpha: float = 0.3) -> torch.Tensor:
    """PROJ-3: Interpolation — lerp between tiled identity and random orthogonal.
    alpha=0 is pure tiled identity, alpha=1 is pure orthogonal."""
    src_hidden = hiddens.shape[1]
    tgt_hidden = tgt_dim * 2

    # Tiled identity matrix
    w_tiled = torch.zeros(tgt_hidden, src_hidden)
    for i in range(tgt_hidden):
        w_tiled[i, i % src_hidden] = 1.0

    # Random semi-orthogonal matrix (via QR decomposition)
    # We need shape [tgt_hidden, src_hidden]
    # QR on [max_dim, min_dim] gives orthonormal columns
    if tgt_hidden >= src_hidden:
        random_mat = torch.randn(tgt_hidden, src_hidden)
        Q, _ = torch.linalg.qr(random_mat)
        w_orth = Q[:tgt_hidden, :src_hidden]  # already correct shape
    else:
        random_mat = torch.randn(src_hidden, tgt_hidden)
        Q, _ = torch.linalg.qr(random_mat)
        w_orth = Q[:src_hidden, :tgt_hidden].T  # transpose to [tgt_hidden, src_hidden]

    # Interpolate
    w = (1 - alpha) * w_tiled + alpha * w_orth

    proj = F.linear(hiddens, w)
    # Norm preservation
    src_norms = hiddens.norm(dim=1, keepdim=True)
    tgt_norms = proj.norm(dim=1, keepdim=True).clamp(min=1e-8)
    proj = proj * (src_norms / tgt_norms)
    return proj


def proj4_learned(hiddens: torch.Tensor, src_dim: int, tgt_dim: int,
                   train_steps: int = 10) -> torch.Tensor:
    """PROJ-4: Learned projection — train a small projector on reconstruction loss.
    Learn W such that decode(encode(x)) ≈ x, then use encode for projection."""
    src_hidden = hiddens.shape[1]
    tgt_hidden = tgt_dim * 2

    # Encoder (src→tgt) + Decoder (tgt→src) for reconstruction
    encoder = nn.Linear(src_hidden, tgt_hidden, bias=False)
    decoder = nn.Linear(tgt_hidden, src_hidden, bias=False)

    # Initialize encoder with tiled identity (good starting point)
    with torch.no_grad():
        w = torch.zeros(tgt_hidden, src_hidden)
        for i in range(tgt_hidden):
            w[i, i % src_hidden] = 1.0
        encoder.weight.copy_(w)
        # Decoder = pseudoinverse init
        decoder.weight.copy_(w.T[:src_hidden, :tgt_hidden])

    optimizer = torch.optim.Adam(list(encoder.parameters()) + list(decoder.parameters()),
                                  lr=0.01)

    hiddens_train = hiddens.detach().clone()
    for step in range(train_steps):
        encoded = encoder(hiddens_train)
        reconstructed = decoder(encoded)
        loss = F.mse_loss(reconstructed, hiddens_train)

        # Also preserve pairwise distances (structure preservation)
        with torch.no_grad():
            src_dists = torch.cdist(hiddens_train, hiddens_train)
        tgt_dists = torch.cdist(encoded, encoded)
        dist_loss = F.mse_loss(tgt_dists / (src_dists.max() + 1e-8),
                                src_dists / (src_dists.max() + 1e-8))

        total_loss = loss + 0.5 * dist_loss
        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

    with torch.no_grad():
        proj = encoder(hiddens_train)
        # Norm preservation
        src_norms = hiddens.norm(dim=1, keepdim=True)
        tgt_norms = proj.norm(dim=1, keepdim=True).clamp(min=1e-8)
        proj = proj * (src_norms / tgt_norms)
    return proj


def proj5_fractal(hiddens: torch.Tensor, src_dim: int, tgt_dim: int) -> torch.Tensor:
    """PROJ-5: Fractal tiling — self-similar at different scales.
    Instead of simple cyclic repeat, use multi-scale structure:
      Scale 1: identity (1:1 mapping)
      Scale 2: averaged pairs (2:1 mapping, half resolution)
      Scale 4: averaged quads (4:1 mapping, quarter resolution)
    This preserves both fine-grained and coarse structure."""
    src_hidden = hiddens.shape[1]
    tgt_hidden = tgt_dim * 2

    w = torch.zeros(tgt_hidden, src_hidden)
    filled = 0

    # Scale 1: Direct mapping (identity tiling)
    scale1_size = min(src_hidden, tgt_hidden)
    for i in range(scale1_size):
        w[i, i % src_hidden] = 1.0
    filled = scale1_size

    # Scale 2: Averaged pairs (half resolution, fills next chunk)
    if filled < tgt_hidden:
        scale2_size = min(src_hidden // 2, tgt_hidden - filled)
        for i in range(scale2_size):
            idx1 = (2 * i) % src_hidden
            idx2 = (2 * i + 1) % src_hidden
            w[filled + i, idx1] = 0.5
            w[filled + i, idx2] = 0.5
        filled += scale2_size

    # Scale 4: Averaged quads (quarter resolution)
    if filled < tgt_hidden:
        scale4_size = min(src_hidden // 4, tgt_hidden - filled)
        for i in range(scale4_size):
            for k in range(4):
                idx = (4 * i + k) % src_hidden
                w[filled + i, idx] = 0.25
        filled += scale4_size

    # Scale 8: Averaged octets
    if filled < tgt_hidden:
        scale8_size = min(src_hidden // 8, tgt_hidden - filled)
        for i in range(scale8_size):
            for k in range(8):
                idx = (8 * i + k) % src_hidden
                w[filled + i, idx] = 0.125
        filled += scale8_size

    # Remaining: random weighted tiling with small noise
    if filled < tgt_hidden:
        for i in range(filled, tgt_hidden):
            # Random weighted combination of 3 source dims
            indices = torch.randint(0, src_hidden, (3,))
            weights = torch.softmax(torch.randn(3), dim=0)
            for j, idx in enumerate(indices):
                w[i, idx.item()] += weights[j].item()

    # Small noise to break perfect symmetry
    w += torch.randn_like(w) * 0.005

    proj = F.linear(hiddens, w)
    # Norm preservation
    src_norms = hiddens.norm(dim=1, keepdim=True)
    tgt_norms = proj.norm(dim=1, keepdim=True).clamp(min=1e-8)
    proj = proj * (src_norms / tgt_norms)
    return proj


def proj6_adaptation(hiddens: torch.Tensor, src_dim: int, tgt_dim: int,
                      adapt_steps: int = ADAPT_STEPS) -> torch.Tensor:
    """PROJ-6: Tiled identity + adaptation steps.
    After projection, run sync+faction steps to let cells self-organize."""
    # Start with tiled identity projection
    projected = proj1_tiled_identity(hiddens, src_dim, tgt_dim)

    # Build a target engine with projected hiddens
    tgt_hidden = tgt_dim * 2
    engine = MitosisEngine(tgt_dim, tgt_hidden, tgt_dim, initial_cells=2, max_cells=NUM_CELLS)
    while len(engine.cells) < NUM_CELLS:
        engine._create_cell(parent=engine.cells[0])

    # Inject projected hiddens
    with torch.no_grad():
        for i, c in enumerate(engine.cells):
            if i < projected.shape[0]:
                h = projected[i].unsqueeze(0) if projected[i].dim() == 1 else projected[i]
                if h.shape[-1] < tgt_hidden:
                    pad = torch.zeros(1, tgt_hidden - h.shape[-1])
                    h = torch.cat([h, pad], dim=-1)
                elif h.shape[-1] > tgt_hidden:
                    h = h[:, :tgt_hidden]
                c.hidden = h

    # Run adaptation: sync + faction + IB2 + noise (same as warmup)
    l2 = torch.zeros(tgt_hidden)
    for step_i in range(adapt_steps):
        frac = step_i / adapt_steps
        with torch.no_grad():
            cur = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            l2 = 0.9 * l2 + 0.1 * cur
            x = 0.5 * cur[:tgt_dim].unsqueeze(0) + 0.5 * l2[:tgt_dim].unsqueeze(0)
            if frac < SILENCE_RATIO:
                x = x * 0.1
            else:
                x = x * 2.0

        engine.process(x)

        with torch.no_grad():
            nc = len(engine.cells)
            fs = nc // NUM_FACTIONS
            if fs >= 2:
                facts = [engine.cells[i*fs:(i+1)*fs] for i in range(NUM_FACTIONS)]
                facts = [f for f in facts if f]
                if len(facts) >= 2:
                    ops = [torch.stack([c.hidden for c in f]).mean(dim=0) for f in facts]
                    for i, f in enumerate(facts):
                        for c in f:
                            c.hidden = (1 - SYNC_STRENGTH) * c.hidden + SYNC_STRENGTH * ops[i]
                    if frac > SILENCE_RATIO:
                        for i, f in enumerate(facts):
                            others = [ops[j] for j in range(len(facts)) if j != i]
                            if others:
                                oa = torch.stack(others).mean(dim=0)
                                for c in f[:max(1, len(f) // 4)]:
                                    c.hidden = (1 - DEBATE_STRENGTH) * c.hidden + DEBATE_STRENGTH * oa

            if nc >= 8:
                norms = [engine.cells[i].hidden.norm().item() for i in range(nc)]
                thr = sorted(norms, reverse=True)[max(1, int(nc * IB2_TOP))]
                for i in range(nc):
                    engine.cells[i].hidden *= 1.03 if norms[i] > thr else 0.97

            for c in engine.cells:
                c.hidden += torch.randn_like(c.hidden) * NOISE
                n = c.hidden.norm().item()
                if n > 2.0:
                    c.hidden *= 1.0 / (n + 1e-8)

    # Return the adapted hiddens
    return torch.stack([c.hidden.squeeze().detach().clone() for c in engine.cells])


# ===================================================================
# BENCHMARK RUNNER
# ===================================================================

STRATEGIES = {
    '1': ('PROJ-1: Tiled Identity', proj1_tiled_identity),
    '2': ('PROJ-2: PCA-based', proj2_pca),
    '3': ('PROJ-3: Interpolation (lerp)', proj3_interpolation),
    '4': ('PROJ-4: Learned Projection', proj4_learned),
    '5': ('PROJ-5: Fractal Tiling', proj5_fractal),
    '6': ('PROJ-6: Adaptation Steps', proj6_adaptation),
}


def run_benchmark(strategy_id: str, src_dim: int, tgt_dim: int,
                  source_engine: MitosisEngine, source_phi: float) -> ProjectionResult:
    """Run a single projection benchmark."""
    name, proj_fn = STRATEGIES[strategy_id]
    t0 = time.time()

    # Extract source hiddens
    hiddens = extract_hiddens(source_engine)

    # Project
    projected = proj_fn(hiddens, src_dim, tgt_dim)

    # Build target engine with projected hiddens
    target_engine = build_target_engine(tgt_dim, projected)

    # Measure Phi
    phi_after = measure_phi(target_engine)

    elapsed = time.time() - t0
    preservation = (phi_after / source_phi * 100) if source_phi > 0 else 0.0

    return ProjectionResult(
        strategy=name,
        strategy_id=f"PROJ-{strategy_id}",
        src_dim=src_dim,
        tgt_dim=tgt_dim,
        phi_source=source_phi,
        phi_after=phi_after,
        preservation_pct=preservation,
        elapsed_sec=elapsed,
    )


def main():
    parser = argparse.ArgumentParser(description="Cross-Dimension Projection Benchmark")
    parser.add_argument("--only", nargs="+", default=None,
                        help="Run only specific strategies (1-6)")
    parser.add_argument("--dims", nargs=2, type=int, default=None,
                        help="Custom source→target dims (e.g. --dims 128 256)")
    parser.add_argument("--steps", type=int, default=WARMUP_STEPS,
                        help="Warm-up steps for source engine")
    parser.add_argument("--cells", type=int, default=NUM_CELLS)
    args = parser.parse_args()

    num_cells = args.cells
    warmup_steps = args.steps

    torch.manual_seed(42)
    np.random.seed(42)

    strategy_ids = args.only if args.only else list(STRATEGIES.keys())
    dim_pairs = [tuple(args.dims)] if args.dims else DIM_PAIRS

    print("=" * 78)
    print("  CROSS-DIMENSION PROJECTION STRATEGY BENCHMARK")
    print("  Testing Phi preservation across dimension upgrades")
    print("=" * 78)
    print(f"  Cells: {num_cells}  |  Factions: {NUM_FACTIONS}  |  Warmup: {warmup_steps} steps")
    print(f"  Dim pairs: {dim_pairs}")
    print(f"  Strategies: {[STRATEGIES[s][0] for s in strategy_ids]}")
    print()

    all_results: List[ProjectionResult] = []

    # Cache source engines by dim (avoid re-warming for each strategy)
    source_cache: Dict[int, Tuple[MitosisEngine, float]] = {}

    for src_dim, tgt_dim in dim_pairs:
        print(f"\n{'─' * 78}")
        print(f"  Dimension: {src_dim}d → {tgt_dim}d  (×{tgt_dim/src_dim:.1f})")
        print(f"{'─' * 78}")

        # Warm up source (or use cache)
        if src_dim not in source_cache:
            print(f"  Warming up source engine ({src_dim}d, {num_cells} cells, {warmup_steps} steps)...")
            torch.manual_seed(42)
            engine, phi = warmup_engine(src_dim, steps=warmup_steps, cells=num_cells)
            source_cache[src_dim] = (engine, phi)
            print(f"  Source Phi: {phi:.4f}")
        else:
            engine, phi = source_cache[src_dim]
            print(f"  Source Phi: {phi:.4f} (cached)")

        print()
        print(f"  {'Strategy':<30} | {'Phi After':>10} | {'Preserve%':>10} | {'Time':>7}")
        print(f"  {'-'*30}-+-{'-'*10}-+-{'-'*10}-+-{'-'*7}")

        for sid in strategy_ids:
            torch.manual_seed(42)
            result = run_benchmark(sid, src_dim, tgt_dim, engine, phi)
            all_results.append(result)
            marker = " ***" if result.preservation_pct == max(
                r.preservation_pct for r in all_results
                if r.src_dim == src_dim and r.tgt_dim == tgt_dim
            ) else ""
            print(f"  {result.strategy:<30} | {result.phi_after:>10.4f} | "
                  f"{result.preservation_pct:>9.1f}% | {result.elapsed_sec:>6.2f}s{marker}")

    # ─── Summary ───
    print(f"\n\n{'=' * 78}")
    print("  SUMMARY: Best strategy per dimension pair")
    print(f"{'=' * 78}")
    print(f"  {'Dims':<15} | {'Best Strategy':<30} | {'Phi':>8} | {'Preserve%':>10}")
    print(f"  {'-'*15}-+-{'-'*30}-+-{'-'*8}-+-{'-'*10}")

    for src_dim, tgt_dim in dim_pairs:
        pair_results = [r for r in all_results if r.src_dim == src_dim and r.tgt_dim == tgt_dim]
        if pair_results:
            best = max(pair_results, key=lambda r: r.preservation_pct)
            print(f"  {src_dim}→{tgt_dim:<10} | {best.strategy:<30} | "
                  f"{best.phi_after:>8.4f} | {best.preservation_pct:>9.1f}%")

    # ─── Per-strategy average ───
    print(f"\n  {'Strategy':<30} | {'Avg Preserve%':>13} | {'Best':>10} | {'Worst':>10}")
    print(f"  {'-'*30}-+-{'-'*13}-+-{'-'*10}-+-{'-'*10}")

    for sid in strategy_ids:
        strat_results = [r for r in all_results if r.strategy_id == f"PROJ-{sid}"]
        if strat_results:
            avg = sum(r.preservation_pct for r in strat_results) / len(strat_results)
            best = max(r.preservation_pct for r in strat_results)
            worst = min(r.preservation_pct for r in strat_results)
            print(f"  {strat_results[0].strategy:<30} | {avg:>12.1f}% | "
                  f"{best:>9.1f}% | {worst:>9.1f}%")

    # ─── ASCII chart ───
    print(f"\n\n  Phi Preservation by Strategy (128→256 / 128→384 / 128→512)")
    print(f"  {'':>30} ", end="")
    for _, tgt in dim_pairs:
        print(f"{'→'+str(tgt):>12}", end="")
    print()

    for sid in strategy_ids:
        name = STRATEGIES[sid][0]
        print(f"  {name:<30} ", end="")
        for src, tgt in dim_pairs:
            rs = [r for r in all_results if r.strategy_id == f"PROJ-{sid}"
                  and r.src_dim == src and r.tgt_dim == tgt]
            if rs:
                pct = rs[0].preservation_pct
                bar_len = min(int(pct / 50), 20)  # scale: 50% per block
                bar = "█" * bar_len
                print(f" {pct:>6.0f}% {bar:<12}", end="")
            else:
                print(f" {'N/A':>6} {'':12}", end="")
        print()

    # ─── Overall champion ───
    if all_results:
        champion = max(all_results, key=lambda r: r.preservation_pct)
        print(f"\n  ★ CHAMPION: {champion.strategy}")
        print(f"    {champion.src_dim}→{champion.tgt_dim}: "
              f"Phi {champion.phi_source:.4f} → {champion.phi_after:.4f} "
              f"({champion.preservation_pct:.1f}% preserved)")

    return all_results


if __name__ == "__main__":
    results = main()
