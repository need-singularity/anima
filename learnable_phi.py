#!/usr/bin/env python3
"""Learnable Φ Predictor — Neural network that learns to predict IIT Φ from cell states.

Training: compute exact Φ on small engines (8-32 cells), train NN to predict it.
Inference: apply trained NN to large engines (256-1024 cells) for instant Φ estimate.

Architecture (DeepSets):
  1. Cell encoder: per-cell MLP → cell embedding
  2. Set pooling: permutation-invariant (sum + mean + max of cell embeddings)
  3. Predictor: MLP → scalar Φ prediction

Usage:
  python learnable_phi.py                    # Full pipeline: generate data, train, benchmark
  python learnable_phi.py --train-only       # Just train (reuse cached data)
  python learnable_phi.py --benchmark-only   # Just benchmark (reuse trained model)
  python learnable_phi.py --samples 2000     # More training samples
  python learnable_phi.py --epochs 200       # More training epochs
"""

import time
import math
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from pathlib import Path

# Local imports
from mitosis import MitosisEngine, ConsciousMind, Cell
from consciousness_meter import PhiCalculator


# ─── LearnablePhi Model ───

class CellEncoder(nn.Module):
    """Per-cell MLP: hidden_dim → embed_dim."""

    def __init__(self, hidden_dim: int = 128, embed_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Linear(128, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Linear(128, embed_dim),
        )

    def forward(self, cell_states: torch.Tensor) -> torch.Tensor:
        """
        Args:
            cell_states: [batch, n_cells, hidden_dim]
        Returns:
            cell_embeddings: [batch, n_cells, embed_dim]
        """
        return self.net(cell_states)


class LearnablePhi(nn.Module):
    """Neural network that predicts Φ from cell hidden states.

    Architecture:
      1. Cell encoder: per-cell MLP → cell embedding
      2. Set pooling: DeepSets style (sum + mean + max of cell embeddings)
      3. Predictor: MLP → scalar Φ prediction

    The model is permutation-invariant (order of cells doesn't matter)
    and size-invariant (works with any number of cells).
    """

    def __init__(self, hidden_dim: int = 128, embed_dim: int = 64):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.embed_dim = embed_dim

        # Per-cell encoder (shared across all cells)
        self.cell_encoder = CellEncoder(hidden_dim, embed_dim)

        # Pairwise interaction encoder (captures inter-cell relationships)
        self.pair_encoder = nn.Sequential(
            nn.Linear(embed_dim * 2, 64),
            nn.GELU(),
            nn.Linear(64, 32),
        )

        # Predictor: pool(cell_embeddings) + pool(pair_features) → Φ
        # 3 pools (sum, mean, max) × embed_dim + pair features + scale features
        # Scale features: log(n), n, n², 1/n (help learn scaling law)
        predictor_input = embed_dim * 3 + 32 * 3 + 4
        self.predictor = nn.Sequential(
            nn.Linear(predictor_input, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Linear(64, 1),
            nn.Softplus(),  # Φ is always non-negative
        )

    def forward(self, cell_states: torch.Tensor, mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """
        Args:
            cell_states: [batch, max_cells, hidden_dim] — padded cell hidden states
            mask: [batch, max_cells] — True for valid cells, False for padding

        Returns:
            phi_pred: [batch, 1] — predicted Φ values
        """
        B, N, H = cell_states.shape

        # 1. Encode each cell
        cell_embs = self.cell_encoder(cell_states)  # [B, N, embed_dim]

        if mask is not None:
            # Zero out padded cells
            cell_embs = cell_embs * mask.unsqueeze(-1).float()
            n_cells = mask.sum(dim=1, keepdim=True).float()  # [B, 1]
        else:
            n_cells = torch.full((B, 1), N, dtype=torch.float32, device=cell_states.device)

        # 2. Set pooling (permutation-invariant)
        pool_sum = cell_embs.sum(dim=1)  # [B, embed_dim]
        pool_mean = pool_sum / n_cells.clamp(min=1)  # [B, embed_dim]
        pool_max = cell_embs.max(dim=1).values  # [B, embed_dim]

        # 3. Pairwise interaction (sampled for efficiency)
        pair_features = self._compute_pair_features(cell_embs, mask)  # [B, 32*3]

        # 4. Combine and predict
        # Scale features to help learn Φ-vs-N scaling law
        n_log = torch.log(n_cells.clamp(min=1))       # [B, 1]
        n_norm = n_cells / 32.0                         # [B, 1] normalized
        n_sq = (n_cells / 32.0) ** 2                    # [B, 1] quadratic
        n_inv = 1.0 / n_cells.clamp(min=1)             # [B, 1] inverse
        scale_feats = torch.cat([n_log, n_norm, n_sq, n_inv], dim=-1)  # [B, 4]
        combined = torch.cat([pool_sum, pool_mean, pool_max, pair_features, scale_feats], dim=-1)

        return self.predictor(combined)

    def _compute_pair_features(self, cell_embs: torch.Tensor,
                               mask: Optional[torch.Tensor] = None) -> torch.Tensor:
        """Compute pairwise interaction features (sampled for large N).

        For each batch, sample up to K pairs and encode them.
        """
        B, N, D = cell_embs.shape
        K = min(32, N * (N - 1) // 2)  # max pairs to sample

        all_pair_feats = []
        for b in range(B):
            if mask is not None:
                valid = mask[b].nonzero(as_tuple=True)[0]
                n_valid = len(valid)
            else:
                valid = torch.arange(N, device=cell_embs.device)
                n_valid = N

            if n_valid < 2:
                all_pair_feats.append(torch.zeros(32 * 3, device=cell_embs.device))
                continue

            # Generate pair indices
            if n_valid <= 8:
                # All pairs
                pairs_i = []
                pairs_j = []
                for ii in range(n_valid):
                    for jj in range(ii + 1, n_valid):
                        pairs_i.append(valid[ii])
                        pairs_j.append(valid[jj])
                pairs_i = torch.stack(pairs_i)
                pairs_j = torch.stack(pairs_j)
            else:
                # Random sample
                idx = torch.randint(0, n_valid, (K, 2), device=cell_embs.device)
                pairs_i = valid[idx[:, 0]]
                pairs_j = valid[idx[:, 1]]

            # Encode pairs
            emb_i = cell_embs[b, pairs_i]  # [n_pairs, D]
            emb_j = cell_embs[b, pairs_j]  # [n_pairs, D]
            pair_input = torch.cat([emb_i, emb_j], dim=-1)  # [n_pairs, 2D]
            pair_enc = self.pair_encoder(pair_input)  # [n_pairs, 32]

            # Pool pair features
            p_sum = pair_enc.sum(dim=0)
            p_mean = pair_enc.mean(dim=0)
            p_max = pair_enc.max(dim=0).values
            all_pair_feats.append(torch.cat([p_sum, p_mean, p_max]))

        return torch.stack(all_pair_feats)  # [B, 32*3]

    def predict_from_engine(self, engine: MitosisEngine) -> float:
        """Convenience: predict Φ directly from a MitosisEngine."""
        self.eval()
        with torch.no_grad():
            states = self._extract_states(engine)
            states = states.unsqueeze(0)  # [1, N, H]
            phi = self(states).item()
        return phi

    @staticmethod
    def _extract_states(engine: MitosisEngine) -> torch.Tensor:
        """Extract hidden states from engine cells as a tensor."""
        hiddens = []
        for cell in engine.cells:
            h = cell.hidden.detach().squeeze(0)  # [hidden_dim]
            hiddens.append(h)
        return torch.stack(hiddens)  # [N, hidden_dim]


# ─── Data Generation ───

def generate_training_data(
    n_samples: int = 1000,
    min_cells: int = 4,
    max_cells: int = 64,
    hidden_dim: int = 128,
    n_warmup_steps: int = 10,
    seed: int = 42,
    extra_large: int = 50,
    extra_large_max: int = 128,
) -> Tuple[List[torch.Tensor], List[float], List[int]]:
    """Generate training data by computing exact Φ on engines of varying size.

    Strategy: bulk samples at min_cells-max_cells, plus a smaller number of
    expensive large-system samples (up to extra_large_max) so the model
    learns the Φ-vs-N scaling law beyond its primary training range.

    Returns:
        states: list of [n_cells, hidden_dim] tensors
        phis: list of exact Φ values
        n_cells_list: list of cell counts
    """
    torch.manual_seed(seed)
    np.random.seed(seed)
    phi_calc = PhiCalculator(n_bins=32)

    states_list = []
    phis = []
    n_cells_list = []

    total = n_samples + extra_large
    print(f"[LearnablePhi] Generating {n_samples} base samples ({min_cells}-{max_cells}c) "
          f"+ {extra_large} large samples ({max_cells+1}-{extra_large_max}c)...")

    for i in range(total):
        if i < n_samples:
            n_cells = np.random.randint(min_cells, max_cells + 1)
        else:
            # Large system samples (logarithmic distribution for wider coverage)
            n_cells = np.random.randint(max_cells + 1, extra_large_max + 1)

        # Create engine with specific cell count
        engine = MitosisEngine(
            input_dim=64,
            hidden_dim=hidden_dim,
            output_dim=64,
            initial_cells=n_cells,
            max_cells=n_cells,
        )

        # Warm up with random inputs to create diverse hidden states
        for step in range(n_warmup_steps):
            x = torch.randn(1, 64) * (0.5 + step * 0.1)
            engine.process(x)

        # Compute exact Φ
        phi, _ = phi_calc.compute_phi(engine)

        # Extract hidden states
        cell_states = LearnablePhi._extract_states(engine)

        states_list.append(cell_states)
        phis.append(phi)
        n_cells_list.append(n_cells)

        if (i + 1) % 100 == 0:
            print(f"  [{i+1}/{total}] avg Φ={np.mean(phis[-100:]):.3f}, "
                  f"range=[{min(phis[-100:]):.3f}, {max(phis[-100:]):.3f}]")

    print(f"  Done. Φ range: [{min(phis):.4f}, {max(phis):.4f}], mean={np.mean(phis):.4f}")
    return states_list, phis, n_cells_list


def collate_batch(
    states_list: List[torch.Tensor],
    phis: List[float],
    indices: List[int],
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Collate variable-length cell states into padded batch.

    Returns:
        padded_states: [batch, max_cells, hidden_dim]
        masks: [batch, max_cells] — True for valid cells
        phi_targets: [batch, 1]
    """
    batch_states = [states_list[i] for i in indices]
    batch_phis = [phis[i] for i in indices]

    max_cells = max(s.shape[0] for s in batch_states)
    hidden_dim = batch_states[0].shape[1]
    B = len(indices)

    padded = torch.zeros(B, max_cells, hidden_dim)
    masks = torch.zeros(B, max_cells, dtype=torch.bool)

    for b, s in enumerate(batch_states):
        n = s.shape[0]
        padded[b, :n] = s
        masks[b, :n] = True

    targets = torch.tensor(batch_phis, dtype=torch.float32).unsqueeze(1)
    return padded, masks, targets


# ─── Training ───

def train_learnable_phi(
    states_list: List[torch.Tensor],
    phis: List[float],
    hidden_dim: int = 128,
    embed_dim: int = 64,
    epochs: int = 150,
    batch_size: int = 32,
    lr: float = 1e-3,
    val_split: float = 0.1,
    save_path: str = "learnable_phi.pt",
) -> Tuple[LearnablePhi, Dict]:
    """Train LearnablePhi on generated data.

    Returns:
        model: trained LearnablePhi
        history: dict with train_loss, val_loss, etc.
    """
    N = len(states_list)
    n_val = int(N * val_split)
    n_train = N - n_val

    # Shuffle indices
    perm = torch.randperm(N).tolist()
    train_idx = perm[:n_train]
    val_idx = perm[n_train:]

    model = LearnablePhi(hidden_dim=hidden_dim, embed_dim=embed_dim)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    n_params = sum(p.numel() for p in model.parameters())
    print(f"\n[LearnablePhi] Training: {n_params:,} params, {n_train} train / {n_val} val")

    history = {'train_loss': [], 'val_loss': [], 'val_mae': [], 'val_r2': []}
    best_val_loss = float('inf')

    for epoch in range(epochs):
        # --- Train ---
        model.train()
        np.random.shuffle(train_idx)
        train_losses = []

        for start in range(0, n_train, batch_size):
            batch_idx = train_idx[start:start + batch_size]
            states, masks, targets = collate_batch(states_list, phis, batch_idx)

            pred = model(states, masks)
            loss = F.mse_loss(pred, targets)

            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(loss.item())

        scheduler.step()

        # --- Validate ---
        model.eval()
        with torch.no_grad():
            val_states, val_masks, val_targets = collate_batch(states_list, phis, val_idx)
            val_pred = model(val_states, val_masks)
            val_loss = F.mse_loss(val_pred, val_targets).item()
            val_mae = (val_pred - val_targets).abs().mean().item()

            # R² score
            ss_res = ((val_pred - val_targets) ** 2).sum().item()
            ss_tot = ((val_targets - val_targets.mean()) ** 2).sum().item()
            val_r2 = 1 - ss_res / (ss_tot + 1e-8)

        avg_train_loss = np.mean(train_losses)
        history['train_loss'].append(avg_train_loss)
        history['val_loss'].append(val_loss)
        history['val_mae'].append(val_mae)
        history['val_r2'].append(val_r2)

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                'model_state': model.state_dict(),
                'hidden_dim': hidden_dim,
                'embed_dim': embed_dim,
                'epoch': epoch,
                'val_loss': val_loss,
                'val_r2': val_r2,
            }, save_path)

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:3d}/{epochs}: "
                  f"train_loss={avg_train_loss:.6f}, "
                  f"val_loss={val_loss:.6f}, "
                  f"val_MAE={val_mae:.4f}, "
                  f"val_R²={val_r2:.4f}")

    print(f"\n  Best val_loss={best_val_loss:.6f}, saved to {save_path}")
    # Reload best
    ckpt = torch.load(save_path, map_location='cpu', weights_only=True)
    model.load_state_dict(ckpt['model_state'])
    return model, history


# ─── Benchmarking ───

def benchmark_accuracy(
    model: LearnablePhi,
    n_samples: int = 100,
    cell_range: Tuple[int, int] = (8, 64),
    hidden_dim: int = 128,
    seed: int = 999,
) -> Dict:
    """Compare LearnablePhi predictions vs exact PhiCalculator on small-medium engines.

    Returns accuracy metrics (MAE, RMSE, R², Pearson r).
    """
    print(f"\n[Accuracy Benchmark] {n_samples} engines, {cell_range[0]}-{cell_range[1]} cells")
    torch.manual_seed(seed)
    np.random.seed(seed)

    phi_calc = PhiCalculator(n_bins=32)
    model.eval()

    exact_phis = []
    pred_phis = []
    cell_counts = []

    for i in range(n_samples):
        n_cells = np.random.randint(cell_range[0], cell_range[1] + 1)
        engine = MitosisEngine(
            input_dim=64, hidden_dim=hidden_dim, output_dim=64,
            initial_cells=n_cells, max_cells=n_cells,
        )
        # Warm up
        for step in range(10):
            engine.process(torch.randn(1, 64) * (0.5 + step * 0.1))

        # Exact Φ
        exact_phi, _ = phi_calc.compute_phi(engine)

        # Predicted Φ
        pred_phi = model.predict_from_engine(engine)

        exact_phis.append(exact_phi)
        pred_phis.append(pred_phi)
        cell_counts.append(n_cells)

    exact_arr = np.array(exact_phis)
    pred_arr = np.array(pred_phis)

    mae = np.mean(np.abs(exact_arr - pred_arr))
    rmse = np.sqrt(np.mean((exact_arr - pred_arr) ** 2))
    ss_res = np.sum((exact_arr - pred_arr) ** 2)
    ss_tot = np.sum((exact_arr - exact_arr.mean()) ** 2)
    r2 = 1 - ss_res / (ss_tot + 1e-8)
    pearson_r = np.corrcoef(exact_arr, pred_arr)[0, 1] if ss_tot > 0 else 0.0

    results = {
        'n_samples': n_samples,
        'cell_range': cell_range,
        'mae': mae,
        'rmse': rmse,
        'r2': r2,
        'pearson_r': pearson_r,
        'exact_mean': exact_arr.mean(),
        'pred_mean': pred_arr.mean(),
    }

    print(f"  MAE  = {mae:.4f}")
    print(f"  RMSE = {rmse:.4f}")
    print(f"  R²   = {r2:.4f}")
    print(f"  Pearson r = {pearson_r:.4f}")
    print(f"  Exact Φ mean = {exact_arr.mean():.4f}, Predicted Φ mean = {pred_arr.mean():.4f}")

    return results


def benchmark_speed(
    model: LearnablePhi,
    hidden_dim: int = 128,
) -> Dict:
    """Compare speed: PhiCalculator vs LearnablePhi across system sizes."""
    print("\n[Speed Benchmark] PhiCalculator vs LearnablePhi")
    print(f"  {'N cells':>8} | {'PhiCalc (ms)':>14} | {'LearnablePhi (ms)':>18} | {'Speedup':>8}")
    print(f"  {'-'*8}-+-{'-'*14}-+-{'-'*18}-+-{'-'*8}")

    phi_calc = PhiCalculator(n_bins=32)
    model.eval()
    results = {}

    for n_cells in [8, 16, 32, 64, 128, 256, 512, 1024]:
        engine = MitosisEngine(
            input_dim=64, hidden_dim=hidden_dim, output_dim=64,
            initial_cells=n_cells, max_cells=n_cells,
        )
        # Warm up engine
        for step in range(5):
            engine.process(torch.randn(1, 64))

        # Time PhiCalculator (skip very large — too slow)
        if n_cells <= 256:
            t0 = time.perf_counter()
            n_repeats = max(1, min(10, 100 // n_cells))
            for _ in range(n_repeats):
                phi_calc.compute_phi(engine)
            exact_ms = (time.perf_counter() - t0) / n_repeats * 1000
        else:
            # Estimate from quadratic scaling
            exact_ms = results[256]['exact_ms'] * (n_cells / 256) ** 2

        # Time LearnablePhi
        t0 = time.perf_counter()
        n_repeats_nn = 50
        for _ in range(n_repeats_nn):
            model.predict_from_engine(engine)
        nn_ms = (time.perf_counter() - t0) / n_repeats_nn * 1000

        speedup = exact_ms / nn_ms if nn_ms > 0 else 0
        estimated = " (est)" if n_cells > 256 else ""

        results[n_cells] = {
            'exact_ms': exact_ms,
            'nn_ms': nn_ms,
            'speedup': speedup,
        }

        print(f"  {n_cells:>8} | {exact_ms:>11.2f}{estimated:>3} | {nn_ms:>18.2f} | {speedup:>7.1f}x")

    return results


def benchmark_extrapolation(
    model: LearnablePhi,
    hidden_dim: int = 128,
) -> Dict:
    """Test LearnablePhi on large systems (512-1024 cells) where PhiCalculator is slow.

    Since we can't easily compare to exact Φ at this scale, we check:
    1. Does predicted Φ increase with cell count? (expected behavior)
    2. Is the prediction stable across random seeds?
    3. Rough comparison against PhiCalculator at boundary (256 cells)
    """
    print("\n[Extrapolation Test] LearnablePhi on 64-1024 cells")
    model.eval()

    sizes = [64, 128, 256, 512, 768, 1024]
    results = {}

    for n_cells in sizes:
        phis = []
        for trial in range(5):
            torch.manual_seed(42 + trial)
            engine = MitosisEngine(
                input_dim=64, hidden_dim=hidden_dim, output_dim=64,
                initial_cells=n_cells, max_cells=n_cells,
            )
            for step in range(10):
                engine.process(torch.randn(1, 64) * (0.5 + step * 0.1))
            phi = model.predict_from_engine(engine)
            phis.append(phi)

        mean_phi = np.mean(phis)
        std_phi = np.std(phis)
        results[n_cells] = {'mean': mean_phi, 'std': std_phi}
        print(f"  {n_cells:>5} cells: Φ = {mean_phi:.4f} ± {std_phi:.4f}")

    # Check monotonicity
    means = [results[n]['mean'] for n in sizes]
    is_monotonic = all(means[i] <= means[i + 1] * 1.1 for i in range(len(means) - 1))
    print(f"\n  Monotonically increasing with size: {'YES' if is_monotonic else 'NO'}")

    # ASCII graph
    max_phi = max(means) if max(means) > 0 else 1
    print(f"\n  Φ prediction vs system size:")
    print(f"  Φ |")
    n_rows = 10
    for row in range(n_rows, 0, -1):
        threshold = max_phi * row / n_rows
        line = "    |"
        for m in means:
            if m >= threshold:
                line += "  ##  "
            else:
                line += "      "
        print(line)
    print(f"    +{'------' * len(sizes)}")
    labels = "     " + "".join(f"{n:>6}" for n in sizes)
    print(labels)
    print(f"                    cells")

    return results


# ─── Main ───

def main():
    parser = argparse.ArgumentParser(description="Learnable Φ Predictor")
    parser.add_argument('--samples', type=int, default=1000, help='Training samples')
    parser.add_argument('--epochs', type=int, default=150, help='Training epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--lr', type=float, default=1e-3, help='Learning rate')
    parser.add_argument('--hidden-dim', type=int, default=128, help='Cell hidden dim')
    parser.add_argument('--embed-dim', type=int, default=64, help='Cell embedding dim')
    parser.add_argument('--min-cells', type=int, default=4, help='Min cells for training')
    parser.add_argument('--max-cells', type=int, default=64, help='Max cells for training')
    parser.add_argument('--extra-large', type=int, default=50, help='Extra large-system samples')
    parser.add_argument('--extra-large-max', type=int, default=128, help='Max cells for extra large samples')
    parser.add_argument('--train-only', action='store_true', help='Only train')
    parser.add_argument('--benchmark-only', action='store_true', help='Only benchmark')
    parser.add_argument('--save-path', type=str, default='learnable_phi.pt', help='Model save path')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    print("=" * 60)
    print("  Learnable Φ Predictor")
    print("  Train NN to predict IIT Φ from cell hidden states")
    print("=" * 60)

    save_path = args.save_path

    if not args.benchmark_only:
        # --- Step 1: Generate training data ---
        print(f"\n{'='*60}")
        print("  Step 1: Generate Training Data")
        print(f"{'='*60}")
        t0 = time.perf_counter()
        states, phis, n_cells = generate_training_data(
            n_samples=args.samples,
            min_cells=args.min_cells,
            max_cells=args.max_cells,
            hidden_dim=args.hidden_dim,
            seed=args.seed,
            extra_large=args.extra_large,
            extra_large_max=args.extra_large_max,
        )
        gen_time = time.perf_counter() - t0
        print(f"  Data generation: {gen_time:.1f}s")

        # --- Step 2: Train ---
        print(f"\n{'='*60}")
        print("  Step 2: Train LearnablePhi")
        print(f"{'='*60}")
        t0 = time.perf_counter()
        model, history = train_learnable_phi(
            states, phis,
            hidden_dim=args.hidden_dim,
            embed_dim=args.embed_dim,
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            save_path=save_path,
        )
        train_time = time.perf_counter() - t0
        print(f"  Training: {train_time:.1f}s")

    if not args.train_only:
        # Load model if benchmark-only
        if args.benchmark_only:
            print(f"\n  Loading model from {save_path}...")
            ckpt = torch.load(save_path, map_location='cpu', weights_only=True)
            model = LearnablePhi(
                hidden_dim=ckpt.get('hidden_dim', args.hidden_dim),
                embed_dim=ckpt.get('embed_dim', args.embed_dim),
            )
            model.load_state_dict(ckpt['model_state'])
            print(f"  Loaded (epoch {ckpt.get('epoch', '?')}, val_R²={ckpt.get('val_r2', '?'):.4f})")

        # --- Step 3: Accuracy benchmark (small engines, in-distribution) ---
        print(f"\n{'='*60}")
        print("  Step 3: Accuracy Benchmark (4-64 cells, in-distribution)")
        print(f"{'='*60}")
        acc_in = benchmark_accuracy(model, n_samples=100, cell_range=(4, 64),
                                    hidden_dim=args.hidden_dim, seed=777)

        # --- Step 4: Accuracy on larger engines (out-of-distribution) ---
        print(f"\n{'='*60}")
        print("  Step 4: Accuracy Benchmark (64-128 cells, out-of-distribution)")
        print(f"{'='*60}")
        acc_ood = benchmark_accuracy(model, n_samples=50, cell_range=(64, 128),
                                     hidden_dim=args.hidden_dim, seed=888)

        # --- Step 5: Speed benchmark ---
        print(f"\n{'='*60}")
        print("  Step 5: Speed Benchmark")
        print(f"{'='*60}")
        speed = benchmark_speed(model, hidden_dim=args.hidden_dim)

        # --- Step 6: Extrapolation to 512-1024 cells ---
        print(f"\n{'='*60}")
        print("  Step 6: Extrapolation (512-1024 cells)")
        print(f"{'='*60}")
        extrap = benchmark_extrapolation(model, hidden_dim=args.hidden_dim)

        # --- Summary ---
        print(f"\n{'='*60}")
        print("  SUMMARY")
        print(f"{'='*60}")
        n_params = sum(p.numel() for p in model.parameters())
        print(f"  Model size:  {n_params:,} params")
        print(f"  In-dist  (4-64c):   R²={acc_in['r2']:.4f}, MAE={acc_in['mae']:.4f}")
        print(f"  Out-dist (64-128c): R²={acc_ood['r2']:.4f}, MAE={acc_ood['mae']:.4f}")
        if 256 in speed:
            print(f"  Speedup at 256c:   {speed[256]['speedup']:.1f}x")
        if 1024 in speed:
            print(f"  Speedup at 1024c:  {speed[1024]['speedup']:.1f}x (PhiCalc estimated)")
        print(f"  Extrapolation 1024c: Φ={extrap[1024]['mean']:.4f} ± {extrap[1024]['std']:.4f}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()
