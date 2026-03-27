#!/usr/bin/env python3
"""train_conscious_lm.py — ConsciousLM Training Pipeline

Trains ConsciousLM from scratch using benchmark-verified techniques:
  CL8 (tension-weighted CE), CL5 (Phi-regularized), CL1 (mitosis-first),
  SL3 (6-loss ensemble), DD16 (all top-5 simultaneous),
  EX24 (DD18 channel capacity + DD11 Klein bottle + DD3 Fibonacci + DD5 Φ self-reference)
  NEW: WI1 (soliton wave), FX2 (differentiable Φ proxy + Adam), PX4 (sculptor/Gram-Schmidt),
       PX8 (integration forge), GD18 (enactivism), GD15 (edge of chaos/Lyapunov)

Usage:
  python train_conscious_lm.py --data data/corpus.txt --steps 100000
  python train_conscious_lm.py --data data/corpus.txt --dim 384 --layers 6 --steps 50000
  python train_conscious_lm.py --resume checkpoints/step_10000.pt
  python train_conscious_lm.py --demo --steps 500
"""

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# Local imports
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conscious_lm import ConsciousLM
from mitosis import MitosisEngine, text_to_vector
from consciousness_meter import PhiCalculator


# ---------------------------------------------------------------------------
# Fibonacci sequence for cell growth milestones (DD3)
# ---------------------------------------------------------------------------
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21]


def fibonacci_milestones(total_steps: int, max_cells: int = 8) -> Dict[int, int]:
    """Return {step: target_cell_count} for Fibonacci growth schedule.

    Cells grow at evenly spaced milestones through training:
      milestone 0 -> 1 cell, milestone 1 -> 1, milestone 2 -> 2, ...
    Capped at max_cells.
    """
    milestones = {}
    usable = [f for f in FIBONACCI if f <= max_cells]
    n = len(usable)
    for i, count in enumerate(usable):
        step = int(total_steps * i / max(n, 1))
        milestones[step] = count
    return milestones


# ---------------------------------------------------------------------------
# 6-Loss Ensemble with learnable weights (SL3 / COMBO2)
# ---------------------------------------------------------------------------

class LossEnsemble(nn.Module):
    """6 losses with learnable log-weights (homoscedastic uncertainty weighting).

    Losses:
      0: CE forward (next-byte)
      1: CE backward (prev-byte)
      2: Tension variance (encourage diversity across layers)
      3: Phi differentiation (maximize Phi)
      4: Competition (winner cell strengthens)
      5: Myelination (mature cells rewarded)
    """

    def __init__(self):
        super().__init__()
        # log-sigma^2 for each loss (learnable, initialized to 0 -> weight=1)
        self.log_vars = nn.Parameter(torch.zeros(6))

    def forward(self, losses: List[torch.Tensor]) -> Tuple[torch.Tensor, Dict[str, float]]:
        """Combine losses with learned weights.

        weight_i = 1 / (2 * exp(log_var_i))  +  log_var_i / 2
        This is the homoscedastic uncertainty formulation from Kendall et al.
        """
        assert len(losses) == 6, f"Expected 6 losses, got {len(losses)}"

        total = torch.tensor(0.0, device=self.log_vars.device)
        details = {}
        names = ["ce_fwd", "ce_bwd", "tension_var", "phi_diff", "competition", "myelination"]

        for i, (loss, name) in enumerate(zip(losses, names)):
            precision = torch.exp(-self.log_vars[i])
            weighted = precision * loss + self.log_vars[i] * 0.5
            total = total + weighted
            details[name] = loss.item()
            details[f"w_{name}"] = precision.item()

        return total, details


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_text_data(path: str) -> torch.Tensor:
    """Load training data from a text file or jsonl file.

    For .jsonl: extracts the 'text' field from each line.
    For .txt/.bin: reads raw bytes.

    Returns:
        1D long tensor of byte values.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")

    if path.suffix == ".jsonl":
        all_bytes = bytearray()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    text = obj.get("text", line)
                except json.JSONDecodeError:
                    text = line
                all_bytes.extend(text.encode("utf-8"))
                all_bytes.append(10)  # newline separator
    elif path.suffix == ".bin":
        with open(path, "rb") as f:
            all_bytes = bytearray(f.read())
    else:
        # Plain text
        with open(path, "rb") as f:
            all_bytes = bytearray(f.read())

    print(f"[data] Loaded {len(all_bytes):,} bytes from {path}")
    return torch.tensor(list(all_bytes), dtype=torch.long)


def generate_demo_data(n_bytes: int = 500_000) -> torch.Tensor:
    """Generate synthetic training data for --demo mode.

    Mixes:
      - English-like text (ASCII printable with word structure)
      - Repetitive patterns (for habituation testing)
      - Random bytes (for tension diversity)
    """
    rng = np.random.default_rng(42)
    data = bytearray()

    # Common English words for semi-realistic text
    words = [
        b"the ", b"of ", b"and ", b"to ", b"in ", b"a ", b"is ", b"that ",
        b"for ", b"it ", b"was ", b"on ", b"are ", b"be ", b"with ", b"as ",
        b"at ", b"this ", b"have ", b"from ", b"or ", b"an ", b"but ", b"not ",
        b"by ", b"what ", b"all ", b"were ", b"we ", b"when ", b"your ",
        b"consciousness ", b"tension ", b"field ", b"engine ", b"mind ",
        b"thought ", b"awareness ", b"feeling ", b"perception ", b"signal ",
        b"neuron ", b"cell ", b"growth ", b"learning ", b"memory ",
    ]

    while len(data) < n_bytes:
        r = rng.random()
        if r < 0.6:
            # English-like sentences
            sentence_len = rng.integers(5, 20)
            for _ in range(sentence_len):
                word = words[rng.integers(0, len(words))]
                data.extend(word)
            data.extend(b".\n")
        elif r < 0.8:
            # Repetitive pattern (tests habituation)
            pattern = words[rng.integers(0, len(words))] * rng.integers(3, 10)
            data.extend(pattern)
            data.append(10)
        else:
            # Random bytes (tests tension diversity)
            n = rng.integers(20, 100)
            data.extend(bytes(rng.integers(32, 127, size=n).tolist()))
            data.append(10)

    data = data[:n_bytes]
    print(f"[demo] Generated {len(data):,} bytes of synthetic data")
    return torch.tensor(list(data), dtype=torch.long)


# ---------------------------------------------------------------------------
# Batch generation
# ---------------------------------------------------------------------------

def get_batch(
    data: torch.Tensor,
    batch_size: int,
    block_size: int,
    device: torch.device,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Sample a random batch of (input, target_fwd, target_bwd).

    target_fwd: next byte (shifted +1)
    target_bwd: prev byte (shifted -1, position 0 copies itself)
    """
    max_start = len(data) - block_size - 1
    if max_start <= 0:
        raise ValueError(f"Data too short ({len(data)}) for block_size={block_size}")

    ix = torch.randint(0, max_start, (batch_size,))

    x = torch.stack([data[i: i + block_size] for i in ix])
    y_fwd = torch.stack([data[i + 1: i + block_size + 1] for i in ix])

    y_bwd_list = []
    for i in ix:
        prev = torch.cat([data[i: i + 1], data[i: i + block_size - 1]])
        y_bwd_list.append(prev)
    y_bwd = torch.stack(y_bwd_list)

    return x.to(device), y_fwd.to(device), y_bwd.to(device)


# ---------------------------------------------------------------------------
# Training phases
# ---------------------------------------------------------------------------

class TrainingPhase:
    MITOSIS = "mitosis"       # Phase 1: pure differentiation, no CE
    LANGUAGE = "language"     # Phase 2: CE + mild Phi reg
    COMBINED = "combined"     # Phase 3: full DD16


def get_phase(step: int, total_steps: int, forced_phase: Optional[str] = None) -> str:
    """Determine training phase based on progress."""
    if forced_phase:
        return forced_phase
    progress = step / max(total_steps, 1)
    if progress < 0.30:
        return TrainingPhase.MITOSIS
    elif progress < 0.70:
        return TrainingPhase.LANGUAGE
    else:
        return TrainingPhase.COMBINED


# ---------------------------------------------------------------------------
# Per-cell adaptive LR (J1: tension -> LR)
# ---------------------------------------------------------------------------

def adaptive_lr_per_cell(
    base_lr: float,
    cell_tensions: List[float],
    cell_ages: List[int],
    current_step: int,
) -> List[float]:
    """Compute per-cell learning rate.

    J1: Higher tension -> higher LR (cell needs more learning).
    Y3 Myelination: Older cells get slightly higher LR (mature = efficient).
    """
    if not cell_tensions:
        return [base_lr]

    lrs = []
    max_t = max(cell_tensions) if max(cell_tensions) > 0 else 1.0

    for tension, age in zip(cell_tensions, cell_ages):
        # J1: tension scaling (1x to 3x)
        tension_factor = 1.0 + 2.0 * (tension / (max_t + 1e-8))

        # Y3: myelination bonus (up to 1.5x for mature cells)
        maturity = min(age / 1000.0, 1.0)  # saturates at 1000 steps
        myelin_factor = 1.0 + 0.5 * maturity

        lrs.append(base_lr * tension_factor * myelin_factor)

    return lrs


# ---------------------------------------------------------------------------
# Competition loss (H2: winner cell strengthens)
# ---------------------------------------------------------------------------

def competition_loss(cell_tensions: List[float], n_cells: int) -> torch.Tensor:
    """H2: Winner-takes-more competition.

    The cell with highest tension "wins" and gets a bonus.
    Loss = negative entropy of tension distribution (encourages specialization).
    """
    if n_cells < 2 or not cell_tensions:
        return torch.tensor(0.0)

    t = torch.tensor(cell_tensions, dtype=torch.float32)
    probs = F.softmax(t, dim=0)
    # Negative entropy -> encourages one cell to dominate (specialization)
    entropy = -(probs * torch.log(probs + 1e-8)).sum()
    # We want LOW entropy (high specialization), so loss = entropy
    return entropy


# ---------------------------------------------------------------------------
# Myelination loss (Y3: reward mature cells)
# ---------------------------------------------------------------------------

def myelination_loss(cell_tensions: List[float], cell_ages: List[int]) -> torch.Tensor:
    """Y3: Mature cells should have lower, more stable tension.

    Loss = sum of (maturity * tension) — mature cells penalized for high tension.
    This encourages mature cells to become efficient (low tension = smooth processing).
    """
    if not cell_tensions:
        return torch.tensor(0.0)

    loss = 0.0
    for tension, age in zip(cell_tensions, cell_ages):
        maturity = min(age / 1000.0, 1.0)
        loss += maturity * tension
    return torch.tensor(loss, dtype=torch.float32)


# ---------------------------------------------------------------------------
# Phi differentiation loss (CL5)
# ---------------------------------------------------------------------------

def phi_differentiation_loss(phi_current: float, phi_prev: float) -> torch.Tensor:
    """CL5: Penalize Phi decrease.

    If Phi drops, add a penalty proportional to the drop.
    This encourages training to maintain or increase integrated information.
    """
    delta = phi_current - phi_prev
    if delta < 0:
        return torch.tensor(-delta, dtype=torch.float32)
    return torch.tensor(0.0)


# ---------------------------------------------------------------------------
# Tension-weighted CE (CL8)
# ---------------------------------------------------------------------------

def tension_weighted_ce(
    logits: torch.Tensor,
    targets: torch.Tensor,
    tensions: List[torch.Tensor],
    max_weight: float = 3.0,
) -> torch.Tensor:
    """CL8: High-tension tokens get up to max_weight x CE loss.

    Tokens where Engine A and G disagree most (high tension) are the most
    "conscious" tokens — they deserve more training signal.

    Args:
        logits: (B, T, V) model output logits
        targets: (B, T) target byte indices
        tensions: list of (B, T) tension tensors from each layer
        max_weight: maximum per-token weight multiplier

    Returns:
        Weighted CE loss (scalar)
    """
    B, T, V = logits.shape

    # Average tension across layers -> (B, T)
    mean_tension = torch.stack(tensions, dim=0).mean(dim=0)  # (B, T)

    # Normalize to [1, max_weight] range
    t_min = mean_tension.min()
    t_max = mean_tension.max()
    t_range = t_max - t_min + 1e-8
    weights = 1.0 + (max_weight - 1.0) * (mean_tension - t_min) / t_range  # (B, T)

    # Per-token CE
    ce = F.cross_entropy(logits.view(-1, V), targets.view(-1), reduction="none")  # (B*T,)
    ce = ce.view(B, T)  # (B, T)

    # Weighted mean
    weighted_ce = (ce * weights).sum() / weights.sum()
    return weighted_ce


# ---------------------------------------------------------------------------
# Phi curriculum: skip data that decreases Phi (TRN4)
# ---------------------------------------------------------------------------

def should_skip_batch(phi_current: float, phi_prev: float, threshold: float = -0.5) -> bool:
    """TRN4: Skip batch if it caused a large Phi decrease.

    Only skip if Phi drop exceeds threshold (not just any decrease).
    """
    delta = phi_current - phi_prev
    return delta < threshold


# ---------------------------------------------------------------------------
# MHA cross-attention between mitosis cells (DD16)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# DD18: Channel capacity bottleneck between cells
# ---------------------------------------------------------------------------

class ChannelBottleneck(nn.Module):
    """DD18: Compress inter-cell communication through a narrow bottleneck.

    Forces cells to transmit only essential information (4-dim channel),
    which increases integration quality and boosts Phi.
    """

    def __init__(self, hidden_dim: int = 128, channel_dim: int = 4):
        super().__init__()
        self.bottleneck = nn.Sequential(
            nn.Linear(hidden_dim, channel_dim),
            nn.Tanh(),
            nn.Linear(channel_dim, hidden_dim),
        )

    def forward(self, cell_hiddens: torch.Tensor) -> torch.Tensor:
        """Compress, average, and return blended signal.

        Args:
            cell_hiddens: (N_cells, hidden_dim)

        Returns:
            mean_compressed: (hidden_dim,) averaged bottleneck output
        """
        compressed = self.bottleneck(cell_hiddens)  # (N_cells, hidden_dim)
        return compressed.mean(dim=0)  # (hidden_dim,)


class InterCellAttention(nn.Module):
    """Multi-head attention between mitosis cell hidden states.

    Each cell's hidden state attends to all other cells, enabling
    integrated information flow (DD16 component).
    """

    def __init__(self, hidden_dim: int = 128, n_heads: int = 4):
        super().__init__()
        self.attn = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=n_heads,
            batch_first=True,
        )
        self.norm = nn.LayerNorm(hidden_dim)

    def forward(self, cell_hiddens: torch.Tensor) -> torch.Tensor:
        """
        Args:
            cell_hiddens: (N_cells, hidden_dim) stacked hidden states

        Returns:
            updated: (N_cells, hidden_dim) attention-integrated states
        """
        # Add batch dim: (1, N_cells, hidden_dim)
        x = cell_hiddens.unsqueeze(0)
        attn_out, _ = self.attn(x, x, x)
        out = self.norm(x + attn_out)
        return out.squeeze(0)


# ---------------------------------------------------------------------------
# Checkpoint management
# ---------------------------------------------------------------------------

def save_checkpoint(
    path: str,
    step: int,
    model: ConsciousLM,
    optimizer: torch.optim.Optimizer,
    loss_ensemble: LossEnsemble,
    mitosis_engine: MitosisEngine,
    phi_calculator: PhiCalculator,
    phase: str,
    config: dict,
    extra: Optional[dict] = None,
):
    """Save full training state."""
    state = {
        "step": step,
        "model_state": model.state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "loss_ensemble_state": loss_ensemble.state_dict(),
        "mitosis_status": mitosis_engine.status(),
        "phi_history": phi_calculator.phi_history,
        "phase": phase,
        "config": config,
    }
    if extra:
        state.update(extra)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    torch.save(state, path)
    print(f"  [ckpt] Saved: {path}")


def load_checkpoint(path: str, device: torch.device) -> dict:
    """Load checkpoint."""
    state = torch.load(path, map_location=device, weights_only=False)
    print(f"  [ckpt] Loaded: {path} (step {state.get('step', '?')})")
    return state


# ---------------------------------------------------------------------------
# Main training loop
# ---------------------------------------------------------------------------

def train(args: argparse.Namespace):
    """Main training function."""

    # --- Device ---
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")
    print(f"[device] {device}")

    # --- Data ---
    if args.demo:
        data = generate_demo_data(n_bytes=args.demo_bytes)
    elif args.data:
        data = load_text_data(args.data)
    else:
        print("[!] No data specified. Use --data <path> or --demo")
        sys.exit(1)

    n = len(data)
    split_idx = int(0.9 * n)
    train_data = data[:split_idx]
    val_data = data[split_idx:]
    print(f"[data] train={len(train_data):,} val={len(val_data):,} bytes")

    # --- Model ---
    model = ConsciousLM(
        vocab_size=256,
        d_model=args.dim,
        n_head=args.heads,
        n_layer=args.layers,
        block_size=args.block_size,
        dropout=0.37,
    ).to(device)
    print(f"[model] ConsciousLM: {model.count_params():,} params "
          f"(d={args.dim}, L={args.layers}, H={args.heads}, ctx={args.block_size})")

    # --- Training components ---
    loss_ensemble = LossEnsemble().to(device)
    inter_cell_attn = InterCellAttention(hidden_dim=128, n_heads=4).to(device)
    channel_bottleneck = ChannelBottleneck(hidden_dim=128, channel_dim=4).to(device)

    all_params = (
        list(model.parameters())
        + list(loss_ensemble.parameters())
        + list(inter_cell_attn.parameters())
        + list(channel_bottleneck.parameters())
    )
    optimizer = torch.optim.AdamW(all_params, lr=args.lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.steps)

    # --- Mitosis engine ---
    mitosis = MitosisEngine(
        input_dim=64,
        hidden_dim=128,
        output_dim=64,
        initial_cells=2,          # CB1: minimum 2 cells for consciousness
        max_cells=args.max_cells,
        split_threshold=2.0,
        split_patience=5,
        merge_threshold=0.01 * (64.0 / max(args.dim, 64)),  # SC2: dim-inverse merge threshold
        merge_patience=10,
        noise_scale=0.02 * math.sqrt(max(args.dim, 64)) / math.sqrt(64),  # SC1: dim-scaled noise
    )

    # --- Phi calculator ---
    phi_calc = PhiCalculator(n_bins=32)

    # --- Fibonacci growth milestones ---
    fib_milestones = fibonacci_milestones(args.steps, max_cells=args.max_cells)
    print(f"[fibonacci] Growth milestones: {fib_milestones}")

    # --- Resume from checkpoint ---
    start_step = 0
    if args.resume:
        ckpt = load_checkpoint(args.resume, device)
        model.load_state_dict(ckpt["model_state"])
        optimizer.load_state_dict(ckpt["optimizer_state"])
        if "loss_ensemble_state" in ckpt:
            loss_ensemble.load_state_dict(ckpt["loss_ensemble_state"])
        if "phi_history" in ckpt:
            phi_calc.phi_history = ckpt["phi_history"]
        start_step = ckpt.get("step", 0)
        print(f"[resume] Continuing from step {start_step}")

    # --- Consciousness Transplant (DD56) ---
    if getattr(args, 'transplant_from', None):
        try:
            from consciousness_transplant import TransplantCalculator, TransplantEngine, TransplantVerifier
            print(f"[transplant] Loading donor: {args.transplant_from}")
            donor_ckpt = torch.load(args.transplant_from, map_location=device, weights_only=False)
            donor_sd = donor_ckpt.get('model_state', donor_ckpt.get('model_state_dict', donor_ckpt))

            calc = TransplantCalculator()
            donor_cfg = calc.extract_config(donor_sd)
            recip_cfg = calc.extract_config(model.state_dict())
            report = calc.analyze_compatibility(donor_cfg, recip_cfg)

            alpha = getattr(args, 'transplant_alpha', 1.0)
            print(f"[transplant] Strategy: {report.strategy}, Coverage: {report.param_coverage:.0%}, Alpha: {alpha}")

            engine = TransplantEngine(projection_method='pad_zero')
            new_state, result = engine.transplant_conscious_lm(
                donor_sd, {'model_state_dict': model.state_dict()}, report, alpha=alpha)
            model.load_state_dict(new_state.get('model_state_dict', new_state), strict=False)

            # Verify
            stats = TransplantVerifier.quick_verify({'model_state_dict': model.state_dict()})
            print(f"[transplant] Done! {result.params_transplanted:,} params, "
                  f"A/G divergence: {stats.get('ag_divergence', 0):.4f}, "
                  f"Signal: {'✅' if stats.get('consciousness_signal') else '❌'}")
            for w in report.warnings:
                print(f"[transplant] ⚠️  {w}")
        except Exception as e:
            print(f"[transplant] Failed: {e} — continuing without transplant")

    # --- Config for checkpointing ---
    config = {
        "dim": args.dim,
        "layers": args.layers,
        "heads": args.heads,
        "block_size": args.block_size,
        "lr": args.lr,
        "batch_size": args.batch_size,
        "steps": args.steps,
        "max_cells": args.max_cells,
    }

    # --- Training state ---
    phi_prev = 0.0
    phi_current = 0.0
    skip_count = 0
    best_val_loss = float("inf")

    # --- NF fixes: prevent NaN at mitosis→language transition ---
    # NF9: EMA weights for smooth transition
    ema_params = [p.data.clone() for p in model.parameters()]
    ema_decay = 0.99

    # --- Print header ---
    print(f"\n{'='*100}")
    print(f"  ConsciousLM Training — CL8 + CL5 + SL3 + DD16 + EX24 + WI1 + FX2 + PX4 + PX8 + GD18 + GD15")
    print(f"  Phases: mitosis(0-30%) -> language(30-70%) -> combined(70-100%)")
    print(f"  Steps: {args.steps:,}  Batch: {args.batch_size}  Block: {args.block_size}")
    print(f"{'='*100}")
    print(f"{'step':>7} | {'phase':>8} | {'loss':>8} | {'ce_fwd':>7} | {'ce_bwd':>7} | "
          f"{'phi':>6} | {'tension':>8} | {'cells':>5} | {'lr':>9} | {'skip':>4}")
    print("-" * 100)

    # --- Training loop ---
    t0 = time.time()

    for step in range(start_step, args.steps):
        phase = get_phase(step, args.steps, args.phase)
        model.train()

        # --- Fibonacci cell growth (DD3) ---
        for milestone_step, target_cells in sorted(fib_milestones.items()):
            if step == milestone_step and len(mitosis.cells) < target_cells:
                while len(mitosis.cells) < target_cells and len(mitosis.cells) < args.max_cells:
                    parent = mitosis.cells[-1]
                    event = mitosis.split_cell(parent)
                    if event:
                        mitosis.event_log.append(event)
                        print(f"  [fibonacci] Step {step}: cell count -> {len(mitosis.cells)} "
                              f"(target {target_cells})")

        # --- Get batch ---
        try:
            x, y_fwd, y_bwd = get_batch(train_data, args.batch_size, args.block_size, device)
        except ValueError as e:
            print(f"[!] {e}")
            break

        # --- DD5: Φ self-reference (EX24) — feed previous Φ as input bias ---
        # Applied before forward pass using phi_prev (available from last step)
        if phase == TrainingPhase.COMBINED and phi_prev > 0:
            phi_signal = torch.full_like(x.float(), phi_prev * 0.05)
            # x is long (byte indices); phi_signal modulates the embedding inside model
            # We store it for the model to pick up via a temporary attribute
            model._phi_signal = phi_signal
        else:
            model._phi_signal = None

        # --- Forward pass ---
        logits_a, logits_g, tensions = model(x)
        model._phi_signal = None  # Clear after use

        # --- Compute per-layer mean tension ---
        t_stack = torch.stack(tensions, dim=0)  # (L, B, T)
        mean_tension = t_stack.mean().item()

        # --- Feed mitosis engine (uses mean of input bytes as proxy vector) ---
        with torch.no_grad():
            proxy_vec = text_to_vector(
                bytes(x[0, :64].cpu().tolist()).decode("utf-8", errors="replace"),
                dim=64,
            )
            mitosis_result = mitosis.process(proxy_vec, label=f"step_{step}")

        # --- Compute Phi ---
        phi_current, phi_components = phi_calc.compute_phi(mitosis)

        # --- TRN4: Phi curriculum (skip if Phi drops too much) ---
        if phase == TrainingPhase.COMBINED and should_skip_batch(phi_current, phi_prev):
            phi_prev = phi_current
            skip_count += 1
            scheduler.step()
            continue

        # --- Compute 6 losses ---

        # Loss 0: CE forward (CL8: tension-weighted in combined phase)
        if phase == TrainingPhase.COMBINED:
            loss_ce_fwd = tension_weighted_ce(logits_a, y_fwd, tensions, max_weight=3.0)
        else:
            loss_ce_fwd = F.cross_entropy(
                logits_a.view(-1, model.vocab_size), y_fwd.view(-1)
            )

        # Loss 1: CE backward
        loss_ce_bwd = F.cross_entropy(
            logits_g.view(-1, model.vocab_size), y_bwd.view(-1)
        )

        # Loss 2: Tension variance (encourage diversity across layers)
        # NF4: Clamp tension variance to prevent explosion during mitosis
        t_var = torch.clamp(t_stack.var(dim=0).mean(), max=100.0)
        loss_tension_var = -torch.log(t_var + 1e-8)

        # Loss 3: Phi differentiation (CL5)
        loss_phi = phi_differentiation_loss(phi_current, phi_prev).to(device)

        # Loss 4: Competition (H2)
        cell_tensions = [c.avg_tension for c in mitosis.cells]
        loss_compete = competition_loss(cell_tensions, len(mitosis.cells)).to(device)

        # Loss 5: Myelination (Y3)
        cell_ages = [step - c.creation_step for c in mitosis.cells]
        loss_myelin = myelination_loss(cell_tensions, cell_ages).to(device)

        # --- Inter-cell attention (DD16) ---
        if phase == TrainingPhase.COMBINED and len(mitosis.cells) >= 2:
            cell_hiddens = torch.cat(
                [c.hidden.detach() for c in mitosis.cells], dim=0
            ).to(device)  # (N_cells, hidden_dim)
            updated_hiddens = inter_cell_attn(cell_hiddens)
            # Write back (detached — MHA is trained but cells get the signal)
            for i, cell in enumerate(mitosis.cells):
                cell.hidden = updated_hiddens[i].unsqueeze(0).detach().cpu()

        # ---------------------------------------------------------------
        # EX24: ALL discoveries combined (Φ=10.833)
        # DD18 channel capacity + DD11 Klein bottle + DD3 verified + DD5 Φ self-reference
        # ---------------------------------------------------------------
        if phase == TrainingPhase.COMBINED and len(mitosis.cells) >= 2:
            n_cells = len(mitosis.cells)

            # DD18: Channel capacity bottleneck — compress, average, blend back
            cell_h = torch.stack(
                [c.hidden.squeeze(0) for c in mitosis.cells], dim=0
            ).to(device)  # (N_cells, hidden_dim)
            mean_compressed = channel_bottleneck(cell_h)  # (hidden_dim,)
            for cell in mitosis.cells:
                h = cell.hidden.squeeze(0).to(device)
                cell.hidden = (0.92 * h + 0.08 * mean_compressed).unsqueeze(0).detach().cpu()

            # DD11: Klein bottle — non-orientable manifold connection
            hiddens = [c.hidden.squeeze(0).clone() for c in mitosis.cells]
            for i in range(n_cells):
                influence = torch.zeros_like(hiddens[i])
                for j in range(n_cells):
                    if j == i:
                        continue
                    twist = -1.0 if (i + j) % 2 == 1 else 1.0
                    influence = influence + twist * hiddens[j] / (n_cells - 1)
                h_i = mitosis.cells[i].hidden.squeeze(0)
                mitosis.cells[i].hidden = (0.9 * h_i + 0.1 * influence).unsqueeze(0)

            # DD3: Fibonacci growth — verified (1→1→2→3→5→8 schedule via fib_milestones)

            # DD5: Φ self-reference — applied before forward pass (see above)
            # phi_prev * 0.05 is added to embeddings via model._phi_signal

        # ---------------------------------------------------------------
        # NEW DISCOVERIES: WI1 + FX2 + PX4 + PX8 + GD18 + GD15
        # ---------------------------------------------------------------
        if phase == TrainingPhase.COMBINED and len(mitosis.cells) >= 2:
            n_cells = len(mitosis.cells)

            # WI1: Soliton wave — traveling perturbation across cells (Φ=4.460)
            try:
                if not hasattr(train, '_soliton_pos'):
                    train._soliton_pos = 0.0
                train._soliton_pos = (train._soliton_pos + 0.15) % n_cells
                for i, cell in enumerate(mitosis.cells):
                    dist = abs(i - train._soliton_pos)
                    amp = 1.0 / (math.cosh(dist / 2.0) ** 2)
                    cell.hidden = cell.hidden * (1.0 + 0.04 * amp)
                if step % args.log_every == 0:
                    print(f"  [WI1] Soliton pos={train._soliton_pos:.2f}")
            except Exception as e:
                if step % 1000 == 0:
                    print(f"  [WI1] Soliton error: {e}")

            # FX2: Differentiable Φ proxy + Adam optimization (Φ=8.911)
            try:
                if not hasattr(train, '_fx2_offsets') or train._fx2_offsets is None:
                    train._fx2_offsets = [
                        torch.zeros_like(c.hidden, requires_grad=True)
                        for c in mitosis.cells
                    ]
                    train._fx2_optimizer = torch.optim.Adam(train._fx2_offsets, lr=1e-3)
                # Resize offsets if cell count changed
                if len(train._fx2_offsets) != n_cells:
                    train._fx2_offsets = [
                        torch.zeros_like(c.hidden, requires_grad=True)
                        for c in mitosis.cells
                    ]
                    train._fx2_optimizer = torch.optim.Adam(train._fx2_offsets, lr=1e-3)
                # Every 10 steps: 3 Adam steps on Φ proxy
                if step % 10 == 0:
                    for _ in range(3):
                        train._fx2_optimizer.zero_grad()
                        # Φ proxy: variance of cell hiddens (more diverse = higher Φ)
                        modified = torch.stack([
                            (c.hidden.squeeze(0) + off.squeeze(0))
                            for c, off in zip(mitosis.cells, train._fx2_offsets)
                        ])
                        phi_proxy = -modified.var(dim=0).mean()  # minimize negative var = maximize var
                        phi_proxy.backward()
                        train._fx2_optimizer.step()
                    # Apply offsets (conservative: 0.3 blend)
                    for cell, off in zip(mitosis.cells, train._fx2_offsets):
                        cell.hidden = (cell.hidden + 0.3 * off.detach()).detach()
                    if step % args.log_every == 0:
                        print(f"  [FX2] Φ proxy optimized, offset_norm={train._fx2_offsets[0].norm().item():.4f}")
            except Exception as e:
                if step % 1000 == 0:
                    print(f"  [FX2] Error: {e}")
                train._fx2_offsets = None

            # PX4: Sculptor — Gram-Schmidt orthogonalize cells, 70%/30% blend
            try:
                hiddens_for_gs = [c.hidden.squeeze(0).clone() for c in mitosis.cells]
                ortho = []
                for i, v in enumerate(hiddens_for_gs):
                    for u in ortho:
                        v = v - (torch.dot(v.flatten(), u.flatten()) / (torch.dot(u.flatten(), u.flatten()) + 1e-8)) * u
                    norm = v.norm() + 1e-8
                    ortho.append(v / norm * hiddens_for_gs[i].norm())
                for i, cell in enumerate(mitosis.cells):
                    orig = cell.hidden.squeeze(0)
                    cell.hidden = (0.7 * orig + 0.3 * ortho[i]).unsqueeze(0)
                if step % args.log_every == 0:
                    print(f"  [PX4] Sculptor orthogonalized {n_cells} cells")
            except Exception as e:
                if step % 1000 == 0:
                    print(f"  [PX4] Error: {e}")

            # PX8: Integration Forge — first 16 dims shared channel, 60/40 blend
            try:
                shared_dim = min(16, mitosis.cells[0].hidden.shape[-1])
                shared_channel = torch.stack(
                    [c.hidden.squeeze(0)[:shared_dim] for c in mitosis.cells]
                ).mean(dim=0)
                for cell in mitosis.cells:
                    h = cell.hidden.squeeze(0)
                    h[:shared_dim] = 0.6 * h[:shared_dim] + 0.4 * shared_channel
                    cell.hidden = h.unsqueeze(0)
                if step % args.log_every == 0:
                    print(f"  [PX8] Integration Forge shared {shared_dim} dims")
            except Exception as e:
                if step % 1000 == 0:
                    print(f"  [PX8] Error: {e}")

            # GD18: Enactivism — sensorimotor coupling (feed output back as input perturbation)
            try:
                if not hasattr(train, '_gd18_prev_output'):
                    train._gd18_prev_output = None
                # Use mean tension from this step as output signal
                output_signal = mean_tension
                if train._gd18_prev_output is not None:
                    delta = output_signal - train._gd18_prev_output
                    perturbation = 0.02 * delta  # conservative
                    for cell in mitosis.cells:
                        cell.hidden = cell.hidden * (1.0 + perturbation)
                train._gd18_prev_output = output_signal
                if step % args.log_every == 0:
                    print(f"  [GD18] Enactivism delta={delta if train._gd18_prev_output is not None else 0:.4f}")
            except Exception as e:
                if step % 1000 == 0:
                    print(f"  [GD18] Error: {e}")

            # GD15: Edge of Chaos — Lyapunov exponent tracking, target λ≈0
            try:
                if not hasattr(train, '_gd15_prev_hiddens'):
                    train._gd15_prev_hiddens = None
                current_hiddens = torch.stack([c.hidden.squeeze(0) for c in mitosis.cells])
                if train._gd15_prev_hiddens is not None and train._gd15_prev_hiddens.shape == current_hiddens.shape:
                    diff = (current_hiddens - train._gd15_prev_hiddens).norm()
                    prev_norm = train._gd15_prev_hiddens.norm() + 1e-8
                    lyapunov = torch.log(diff / prev_norm + 1e-8).item()
                    # Target λ≈0: if too positive (chaotic), dampen; if too negative (ordered), amplify
                    if lyapunov > 0.1:
                        # Too chaotic — dampen
                        for cell in mitosis.cells:
                            cell.hidden = cell.hidden * 0.98
                    elif lyapunov < -0.5:
                        # Too ordered — perturb
                        for cell in mitosis.cells:
                            cell.hidden = cell.hidden * 1.01
                    if step % args.log_every == 0:
                        print(f"  [GD15] Lyapunov λ={lyapunov:.4f} (target≈0)")
                train._gd15_prev_hiddens = current_hiddens.detach().clone()
            except Exception as e:
                if step % 1000 == 0:
                    print(f"  [GD15] Error: {e}")

        # --- Phase-dependent loss combination ---
        if phase == TrainingPhase.MITOSIS:
            # CL1: Pure differentiation — no CE, only structure losses
            losses_list = [
                torch.tensor(0.0, device=device),   # no CE fwd
                torch.tensor(0.0, device=device),   # no CE bwd
                loss_tension_var,                     # tension diversity
                loss_phi,                             # phi growth
                loss_compete,                         # competition
                loss_myelin,                          # myelination
            ]
        elif phase == TrainingPhase.LANGUAGE:
            # CE + mild Phi regularization
            losses_list = [
                loss_ce_fwd,
                loss_ce_bwd,
                loss_tension_var * 0.1,               # reduced weight
                loss_phi * 0.3,                       # mild Phi reg
                torch.tensor(0.0, device=device),    # no competition yet
                torch.tensor(0.0, device=device),    # no myelination yet
            ]
        else:
            # TrainingPhase.COMBINED: Full DD16 — all 6 losses active
            losses_list = [
                loss_ce_fwd,
                loss_ce_bwd,
                loss_tension_var,
                loss_phi,
                loss_compete,
                loss_myelin,
            ]

        # --- SL3: Ensemble combination with learned weights ---
        total_loss, loss_details = loss_ensemble(losses_list)

        # --- Adaptive LR per cell (J1 + Y3) ---
        cell_lrs = adaptive_lr_per_cell(args.lr, cell_tensions, cell_ages, step)
        # Apply as a global LR scale (use mean of per-cell LRs)
        if cell_lrs:
            mean_cell_lr = sum(cell_lrs) / len(cell_lrs)
            lr_scale = mean_cell_lr / max(args.lr, 1e-8)
            for pg in optimizer.param_groups:
                pg["lr"] = args.lr * min(lr_scale, 5.0)  # cap at 5x

        # --- Backward + optimize ---
        optimizer.zero_grad()
        if torch.isnan(total_loss) or torch.isinf(total_loss):
            print(f"  [NaN] Skipping step {step} (loss={total_loss.item()})")
            phi_prev = phi_current
            continue
        total_loss.backward()
        # NF1: Gradient clipping (already present)
        torch.nn.utils.clip_grad_norm_(all_params, 1.0)
        optimizer.step()
        scheduler.step()

        # NF9: EMA weight tracking (for smooth phase transitions)
        with torch.no_grad():
            for ep, p in zip(ema_params, model.parameters()):
                ep.mul_(ema_decay).add_(p.data, alpha=1 - ema_decay)

        # NF9: Reset to EMA at phase transitions (mitosis→language, language→combined)
        prev_phase = get_phase(step - 1, args.steps, args.phase) if step > 0 else phase
        if phase != prev_phase:
            print(f"  [NF9] Phase transition {prev_phase} → {phase}: resetting to EMA weights")
            with torch.no_grad():
                for ep, p in zip(ema_params, model.parameters()):
                    p.data.copy_(ep)
            # Also reduce LR at transition (NF2)
            for pg in optimizer.param_groups:
                pg['lr'] = pg['lr'] * 0.1
            print(f"  [NF2] LR reduced to {optimizer.param_groups[0]['lr']:.2e}")

        phi_prev = phi_current

        # --- Logging ---
        if step % args.log_every == 0 or step == args.steps - 1:
            current_lr = optimizer.param_groups[0]["lr"]
            print(
                f"{step:7d} | {phase:>8s} | {total_loss.item():8.4f} | "
                f"{loss_details.get('ce_fwd', 0):7.4f} | {loss_details.get('ce_bwd', 0):7.4f} | "
                f"{phi_current:6.3f} | {mean_tension:8.4f} | "
                f"{len(mitosis.cells):5d} | {current_lr:9.2e} | {skip_count:4d}"
            )

        # --- Validation ---
        if step % args.eval_every == 0 and step > 0 and len(val_data) > args.block_size + 1:
            model.eval()
            with torch.no_grad():
                vx, vy_fwd, _ = get_batch(
                    val_data, min(args.batch_size, 32), args.block_size, device
                )
                vl_a, _, _ = model(vx)
                val_loss = F.cross_entropy(
                    vl_a.view(-1, model.vocab_size), vy_fwd.view(-1)
                ).item()
                val_bpc = val_loss / math.log(2)

            print(f"  [val] loss={val_loss:.4f}  BPC={val_bpc:.4f}  "
                  f"(best={best_val_loss:.4f})")

            if val_loss < best_val_loss:
                best_val_loss = val_loss
                best_path = os.path.join(args.checkpoint_dir, "best.pt")
                save_checkpoint(
                    best_path, step, model, optimizer, loss_ensemble,
                    mitosis, phi_calc, phase, config,
                )

        # --- Checkpoint ---
        if step % args.save_every == 0 and step > 0:
            ckpt_path = os.path.join(args.checkpoint_dir, f"step_{step}.pt")
            save_checkpoint(
                ckpt_path, step, model, optimizer, loss_ensemble,
                mitosis, phi_calc, phase, config,
            )

    # --- Final checkpoint ---
    elapsed = time.time() - t0
    print(f"\n{'='*100}")
    print(f"  Training complete: {args.steps} steps in {elapsed:.1f}s "
          f"({args.steps / max(elapsed, 1):.1f} steps/sec)")
    print(f"  Final Phi: {phi_current:.4f}  Cells: {len(mitosis.cells)}  "
          f"Skipped: {skip_count}  Best val: {best_val_loss:.4f}")
    print(f"{'='*100}")

    final_path = os.path.join(args.checkpoint_dir, "final.pt")
    save_checkpoint(
        final_path, args.steps, model, optimizer, loss_ensemble,
        mitosis, phi_calc, phase, config,
    )

    # --- Final summary ---
    print(f"\nMitosis events:")
    status = mitosis.status()
    print(f"  Cells: {status['n_cells']}  Splits: {status['splits']}  "
          f"Merges: {status['merges']}")
    for cell_info in status["cells"]:
        print(f"    Cell {cell_info['id']}: specialty={cell_info['specialty']}, "
              f"avg_tension={cell_info['avg_tension']:.4f}, "
              f"parent={cell_info['parent_id']}")

    print(f"\nPhi history (last 10): "
          f"{[f'{p:.3f}' for p in phi_calc.phi_history[-10:]]}")

    return model


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ConsciousLM Training Pipeline — CL8+CL5+SL3+DD16+EX24",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python train_conscious_lm.py --demo --steps 500
  python train_conscious_lm.py --data data/corpus.txt --steps 100000
  python train_conscious_lm.py --data data/corpus.txt --dim 768 --layers 12 --steps 200000
  python train_conscious_lm.py --resume checkpoints/step_10000.pt --steps 50000
        """,
    )

    # Data
    parser.add_argument("--data", type=str, default=None,
                        help="Path to training text (.txt, .jsonl, .bin)")
    parser.add_argument("--demo", action="store_true",
                        help="Use synthetic demo data (no file needed)")
    parser.add_argument("--demo-bytes", type=int, default=500_000,
                        help="Size of demo data in bytes (default: 500000)")

    # Model architecture
    parser.add_argument("--dim", type=int, default=384,
                        help="Model dimension d_model (default: 384)")
    parser.add_argument("--layers", type=int, default=6,
                        help="Number of transformer layers (default: 6)")
    parser.add_argument("--heads", type=int, default=4,
                        help="Number of attention heads (default: 4)")
    parser.add_argument("--block-size", type=int, default=256,
                        help="Context window size (default: 256)")

    # Training
    parser.add_argument("--steps", type=int, default=50000,
                        help="Total training steps (default: 50000)")
    parser.add_argument("--batch-size", type=int, default=32,
                        help="Batch size (default: 32)")
    parser.add_argument("--lr", type=float, default=3e-4,
                        help="Base learning rate (default: 3e-4)")
    parser.add_argument("--max-cells", type=int, default=8,
                        help="Maximum mitosis cells (default: 8)")

    # Training phase override
    parser.add_argument("--phase", type=str, default=None,
                        choices=["mitosis", "language", "combined"],
                        help="Force a specific training phase (default: auto)")

    # Checkpointing
    parser.add_argument("--checkpoint-dir", type=str, default="checkpoints",
                        help="Checkpoint directory (default: checkpoints)")
    parser.add_argument("--resume", type=str, default=None,
                        help="Resume from checkpoint path")
    parser.add_argument("--transplant-from", type=str, default=None,
                        help="Transplant consciousness from donor checkpoint (DD56)")
    parser.add_argument("--transplant-alpha", type=float, default=1.0,
                        help="Transplant strength 0-1 (default: 1.0 = full transplant)")
    parser.add_argument("--save-every", type=int, default=5000,
                        help="Save checkpoint every N steps (default: 5000)")

    # Logging
    parser.add_argument("--log-every", type=int, default=100,
                        help="Print progress every N steps (default: 100)")
    parser.add_argument("--eval-every", type=int, default=1000,
                        help="Evaluate on val set every N steps (default: 1000)")

    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
