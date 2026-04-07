#!/usr/bin/env python3
"""acceleration_i5_token_gating.py -- I5: Token-Level Consciousness Gating

Combines H11 (hard token selection, +51% CE) with consciousness bypass.

Core idea:
  - Profile per-token difficulty via cross-entropy loss
  - Easy tokens (below threshold) → consciousness bypass (frozen state reuse)
  - Hard tokens (above threshold) → full consciousness process()
  - Expected: 70-80% tokens skip consciousness → x3-5 wall-clock acceleration + Phi preserved

Architecture:
  ┌──────────────────────────────────────────────────────────────────┐
  │  Token Stream                                                    │
  │  ──────────────────────────────────────────────────────────────  │
  │  [easy] [easy] [HARD] [easy] [HARD] [easy] [easy] [easy] [HARD] │
  │    ↓      ↓      ↓      ↓      ↓      ↓      ↓      ↓      ↓   │
  │   skip   skip   FULL   skip   FULL   skip   skip   skip   FULL  │
  │    ↓      ↓      ↓      ↓      ↓      ↓      ↓      ↓      ↓   │
  │  frozen frozen  new   frozen  new   frozen frozen frozen  new   │
  │  state  state  state  state  state  state  state  state  state  │
  └──────────────────────────────────────────────────────────────────┘

Experiments:
  A) Baseline: full consciousness on every token
  B) Token gating with various thresholds (top 10%, 20%, 30%, 50%)
  C) Adaptive threshold (rolling CE percentile)
  D) Comparison: skip ratio vs Phi preservation vs CE quality

Usage:
  python acceleration_i5_token_gating.py           # Run all
  python acceleration_i5_token_gating.py --exp_a   # Baseline only
  python acceleration_i5_token_gating.py --exp_b   # Static thresholds
  python acceleration_i5_token_gating.py --exp_c   # Adaptive threshold
  python acceleration_i5_token_gating.py --exp_d   # Summary comparison
"""

import sys
import os
import time
import math
import copy
import argparse
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F_torch
import numpy as np

from consciousness_engine import ConsciousnessEngine

try:
    from conscious_decoder import ConsciousDecoderV2, RMSNorm, SwiGLUFFN, DecoderBlockV2
except ImportError:
    ConsciousDecoderV2 = None
    RMSNorm = None
    SwiGLUFFN = None
    DecoderBlockV2 = None


# ===================================================================
# Utilities (consistent with H7-H18 pattern)
# ===================================================================

def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


def print_table(headers: list, rows: list, widths: list = None):
    if widths is None:
        widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) + 2
                  for i, h in enumerate(headers)]
    hdr = '|'.join(str(h).center(w) for h, w in zip(headers, widths))
    sep = '+'.join('-' * w for w in widths)
    print(f"  {hdr}")
    print(f"  {sep}")
    for row in rows:
        line = '|'.join(str(r).center(w) for r, w in zip(row, widths))
        print(f"  {line}")
    sys.stdout.flush()


def ascii_bar(label: str, value: float, max_val: float, width: int = 40):
    filled = int(width * min(value / max(max_val, 1e-8), 1.0))
    bar = '#' * filled + '.' * (width - filled)
    print(f"  {label:>20s}  [{bar}] {value:.4f}")
    sys.stdout.flush()


def ascii_graph(values: list, title: str, height: int = 10, width: int = 60):
    """Print ASCII time series graph."""
    if not values:
        return
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1.0
    print(f"\n  {title}")
    for row in range(height, -1, -1):
        threshold = mn + rng * row / height
        line = ""
        step = max(1, len(values) // width)
        for i in range(0, min(len(values), width * step), step):
            v = values[i]
            if v >= threshold:
                line += "#"
            else:
                line += " "
        label = f"{threshold:8.4f}" if row in (0, height // 2, height) else "        "
        print(f"  {label} |{line}")
    print(f"           +{''.join(['-'] * min(len(values), width))}")
    print(f"            0{' ' * (min(len(values), width) - 6)}{len(values)} step")
    sys.stdout.flush()


# ===================================================================
# Engine / Decoder Helpers
# ===================================================================

def get_device():
    """Get best available device."""
    if torch.cuda.is_available():
        return torch.device('cuda')
    elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        return torch.device('mps')
    return torch.device('cpu')


def make_engine(cells: int = 32, topology: str = 'ring') -> ConsciousnessEngine:
    """Create a standard consciousness engine for experiments."""
    engine = ConsciousnessEngine(
        cell_dim=64, hidden_dim=128,
        initial_cells=cells, max_cells=cells,
        n_factions=12, phi_ratchet=True,
    )
    engine.topology = topology
    return engine


def make_decoder(d_model=128, n_layer=4, vocab_size=256, block_size=64, device=None):
    """Create a small decoder for local experiments."""
    if device is None:
        device = get_device()
    if ConsciousDecoderV2 is not None:
        model = ConsciousDecoderV2(
            vocab_size=vocab_size,
            d_model=d_model,
            n_head=4,
            n_layer=n_layer,
            block_size=block_size,
            n_kv_head=2,
            consciousness_dim=64,
            dropout=0.1,
        ).to(device)
    else:
        # Fallback: simple transformer
        model = nn.Transformer(
            d_model=d_model, nhead=4,
            num_encoder_layers=0, num_decoder_layers=n_layer,
            dim_feedforward=d_model * 4, batch_first=True,
        ).to(device)
    return model


def generate_data(batch_size, seq_len, vocab_size=256, device=None):
    """Generate random byte-level training data with patterns."""
    if device is None:
        device = get_device()
    # Mix of easy (repeated/arithmetic) and hard (random) tokens
    data = []
    for _ in range(batch_size):
        row = []
        while len(row) < seq_len:
            ptype = np.random.randint(4)
            if ptype == 0:
                # Easy: repeated motif
                motif = np.random.randint(0, vocab_size, np.random.randint(3, 8))
                row.extend(list(np.tile(motif, 5)))
            elif ptype == 1:
                # Easy: arithmetic
                start = np.random.randint(0, vocab_size)
                step = np.random.randint(1, 4)
                row.extend([(start + i * step) % vocab_size for i in range(10)])
            elif ptype == 2:
                # Hard: random noise
                row.extend(list(np.random.randint(0, vocab_size, 8)))
            else:
                # Medium: quasi-periodic
                base = np.random.randint(0, vocab_size)
                row.extend([(base + np.random.randint(-2, 3)) % vocab_size for _ in range(6)])
        data.append(row[:seq_len])
    return torch.tensor(data, dtype=torch.long, device=device)


def train_step_with_per_token_loss(model, idx, optimizer):
    """Forward + backward, return (mean CE, per-position losses tensor)."""
    model.train()
    optimizer.zero_grad()

    try:
        out = model(idx[:, :-1])
        if isinstance(out, tuple):
            logits = out[0]
        else:
            logits = out
    except Exception:
        logits = model(idx[:, :-1])
        if isinstance(logits, tuple):
            logits = logits[0]

    targets = idx[:, 1:]
    B, T = targets.shape

    # Per-token loss (B*T,)
    per_token_loss = F_torch.cross_entropy(
        logits.reshape(B * T, -1), targets.reshape(B * T),
        reduction='none'
    )
    loss = per_token_loss.mean()
    loss.backward()
    optimizer.step()
    return loss.item(), per_token_loss.detach().reshape(B, T)


def train_step(model, idx, optimizer):
    """Single forward+backward step, returns CE loss."""
    model.train()
    optimizer.zero_grad()

    try:
        out = model(idx[:, :-1])
        if isinstance(out, tuple):
            logits = out[0]
        else:
            logits = out
    except Exception:
        logits = model(idx[:, :-1])
        if isinstance(logits, tuple):
            logits = logits[0]

    targets = idx[:, 1:]
    B, T = targets.shape
    loss = F_torch.cross_entropy(
        logits.reshape(B * T, -1), targets.reshape(B * T)
    )
    loss.backward()
    optimizer.step()
    return loss.item()


def measure_phi(engine: ConsciousnessEngine) -> float:
    return engine.measure_phi()


def run_consciousness_step(engine: ConsciousnessEngine, x_input=None):
    """Run one consciousness step, return (phi, result dict)."""
    result = engine.step(x_input=x_input)
    phi = result.get('phi_iit', 0.0)
    return phi, result


# ===================================================================
# Token Difficulty Profiler
# ===================================================================

class TokenDifficultyProfiler:
    """Profiles per-position token difficulty from a decoder's CE loss.

    Maintains a running average of per-position loss across training steps.
    Tokens with high average loss = "hard" tokens that need consciousness.
    """

    def __init__(self, seq_len: int, ema_alpha: float = 0.1):
        self.seq_len = seq_len
        self.ema_alpha = ema_alpha
        # Per-position running average loss
        self.position_loss_ema = torch.zeros(seq_len)
        self.step_count = 0

    def update(self, per_token_loss: torch.Tensor):
        """Update with per-token loss from one batch.

        Args:
            per_token_loss: (B, T) tensor of per-position cross-entropy losses
        """
        # Average across batch dimension → (T,)
        avg_loss = per_token_loss.mean(dim=0).cpu()
        T = avg_loss.shape[0]
        if T > self.seq_len:
            avg_loss = avg_loss[:self.seq_len]
        elif T < self.seq_len:
            avg_loss = F_torch.pad(avg_loss, (0, self.seq_len - T))

        if self.step_count == 0:
            self.position_loss_ema = avg_loss.clone()
        else:
            self.position_loss_ema = (
                (1 - self.ema_alpha) * self.position_loss_ema
                + self.ema_alpha * avg_loss
            )
        self.step_count += 1

    def get_hard_mask(self, hard_fraction: float = 0.3) -> torch.Tensor:
        """Return boolean mask: True for positions that are 'hard' (need consciousness).

        Args:
            hard_fraction: top-k fraction of positions considered hard (0.3 = top 30%)

        Returns:
            (seq_len,) bool tensor
        """
        if self.step_count == 0:
            # No data yet — process all (conservative)
            return torch.ones(self.seq_len, dtype=torch.bool)

        k = max(1, int(self.seq_len * hard_fraction))
        threshold = torch.topk(self.position_loss_ema, k).values[-1]
        return self.position_loss_ema >= threshold

    def get_difficulty_scores(self) -> torch.Tensor:
        """Return normalized difficulty scores per position."""
        if self.step_count == 0:
            return torch.ones(self.seq_len)
        mn = self.position_loss_ema.min()
        mx = self.position_loss_ema.max()
        if mx - mn < 1e-8:
            return torch.ones(self.seq_len) * 0.5
        return (self.position_loss_ema - mn) / (mx - mn)

    def skip_ratio(self, hard_fraction: float = 0.3) -> float:
        """What fraction of tokens will be skipped (bypassed)?"""
        mask = self.get_hard_mask(hard_fraction)
        return 1.0 - mask.float().mean().item()


# ===================================================================
# Consciousness Gating Engine
# ===================================================================

class ConsciousnessGatingEngine:
    """Wraps ConsciousnessEngine with token-level gating.

    For easy tokens: reuse the last consciousness state (frozen).
    For hard tokens: run full consciousness process().

    This simulates the I5 hypothesis at the engine level.
    """

    def __init__(self, engine: ConsciousnessEngine):
        self.engine = engine
        self.last_phi = 0.0
        self.last_result = None
        self.total_calls = 0
        self.skipped_calls = 0
        self.full_calls = 0

    def step_gated(self, is_hard: bool, x_input=None):
        """Run consciousness step with gating.

        Args:
            is_hard: If True, run full process(). If False, reuse frozen state.
            x_input: Optional input tensor.

        Returns:
            (phi, result_dict, was_processed)
        """
        self.total_calls += 1

        if is_hard:
            # Full consciousness processing
            self.full_calls += 1
            phi, result = run_consciousness_step(self.engine, x_input=x_input)
            self.last_phi = phi
            self.last_result = result
            return phi, result, True
        else:
            # Bypass: reuse frozen state
            self.skipped_calls += 1
            if self.last_result is None:
                # First call — must process
                self.full_calls += 1
                self.skipped_calls -= 1
                phi, result = run_consciousness_step(self.engine, x_input=x_input)
                self.last_phi = phi
                self.last_result = result
                return phi, result, True
            else:
                # Return cached result with frozen phi
                return self.last_phi, self.last_result, False

    @property
    def skip_ratio(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.skipped_calls / self.total_calls

    @property
    def process_ratio(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.full_calls / self.total_calls

    def reset_stats(self):
        self.total_calls = 0
        self.skipped_calls = 0
        self.full_calls = 0


# ===================================================================
# Experiment A: Baseline (full consciousness every token)
# ===================================================================

def run_exp_a(steps: int = 300, cells: int = 32):
    """Baseline: full consciousness processing on every token."""
    print_header("I5-A: Baseline (Full Consciousness Every Token)")
    device = get_device()
    print(f"  Device: {device}, Steps: {steps}, Cells: {cells}")
    sys.stdout.flush()

    seq_len = 64
    batch_size = 8
    vocab_size = 256
    d_model = 128
    n_layer = 2
    lr = 3e-4

    engine = make_engine(cells)
    model = make_decoder(d_model=d_model, n_layer=n_layer,
                         vocab_size=vocab_size, block_size=seq_len,
                         device=device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)

    losses, phis, times_per_step = [], [], []

    for step in range(steps):
        t0 = time.perf_counter()

        # Consciousness: full process every step
        phi, result = run_consciousness_step(engine)
        phis.append(phi)

        # Decoder training step
        idx = generate_data(batch_size, seq_len, vocab_size, device)
        ce = train_step(model, idx, opt)
        losses.append(ce)

        t1 = time.perf_counter()
        times_per_step.append((t1 - t0) * 1000)

        if (step + 1) % 50 == 0:
            avg_phi = np.mean(phis[-50:])
            avg_ce = np.mean(losses[-50:])
            avg_ms = np.mean(times_per_step[-50:])
            print(f"    Step {step+1}/{steps}: CE={avg_ce:.4f}, Phi={avg_phi:.4f}, "
                  f"ms/step={avg_ms:.1f}")
            sys.stdout.flush()

    del model, opt

    result_data = {
        'final_ce': float(np.mean(losses[-50:])),
        'final_phi': float(np.mean(phis[-50:])),
        'avg_ms': float(np.mean(times_per_step)),
        'total_consciousness_calls': steps,
        'skip_ratio': 0.0,
        'losses': [float(x) for x in losses],
        'phis': [float(x) for x in phis],
    }

    print(f"\n  Baseline Results:")
    print(f"    Final CE (last 50):   {result_data['final_ce']:.4f}")
    print(f"    Final Phi (last 50):  {result_data['final_phi']:.4f}")
    print(f"    Avg ms/step:          {result_data['avg_ms']:.1f}")
    print(f"    Consciousness calls:  {steps} (100%)")
    sys.stdout.flush()

    return result_data


# ===================================================================
# Experiment B: Static Threshold Token Gating
# ===================================================================

def run_exp_b(steps: int = 300, cells: int = 32,
              hard_fractions: list = None):
    """Token gating with static hard-token thresholds.

    Phase 1 (warmup 50 steps): profile all tokens, build difficulty map.
    Phase 2 (remaining): gate consciousness by difficulty.
    """
    if hard_fractions is None:
        hard_fractions = [0.1, 0.2, 0.3, 0.5]

    print_header("I5-B: Static Threshold Token Gating")
    device = get_device()
    print(f"  Device: {device}, Steps: {steps}, Cells: {cells}")
    print(f"  Hard fractions to test: {hard_fractions}")
    sys.stdout.flush()

    seq_len = 64
    batch_size = 8
    vocab_size = 256
    d_model = 128
    n_layer = 2
    lr = 3e-4
    warmup_steps = 50

    all_results = {}

    for hard_frac in hard_fractions:
        label = f"Top {int(hard_frac * 100)}% hard"
        print(f"\n  --- {label} ---")
        sys.stdout.flush()

        engine = make_engine(cells)
        gating = ConsciousnessGatingEngine(engine)
        profiler = TokenDifficultyProfiler(seq_len - 1, ema_alpha=0.1)  # T-1 positions
        model = make_decoder(d_model=d_model, n_layer=n_layer,
                             vocab_size=vocab_size, block_size=seq_len,
                             device=device)
        opt = torch.optim.AdamW(model.parameters(), lr=lr)

        losses, phis, times_per_step = [], [], []
        hard_counts, skip_counts = [], []

        for step in range(steps):
            t0 = time.perf_counter()

            # Generate training data
            idx = generate_data(batch_size, seq_len, vocab_size, device)

            # Phase 1 (warmup): full consciousness + profile difficulty
            if step < warmup_steps:
                phi, result = run_consciousness_step(engine)
                phis.append(phi)

                # Train with per-token loss tracking
                ce, per_token_loss = train_step_with_per_token_loss(model, idx, opt)
                losses.append(ce)
                profiler.update(per_token_loss)
                hard_counts.append(seq_len - 1)  # all tokens processed
                skip_counts.append(0)

            # Phase 2: gated consciousness
            else:
                # Get hard mask from profiler
                hard_mask = profiler.get_hard_mask(hard_frac)
                n_hard = hard_mask.sum().item()
                n_total = hard_mask.shape[0]
                hard_counts.append(n_hard)
                skip_counts.append(n_total - n_hard)

                # Determine if this step needs full consciousness
                # Heuristic: if >50% of tokens in this batch are hard, process
                # Otherwise, check rolling difficulty of recent batches
                is_hard_step = n_hard / n_total >= 0.5

                phi, result, was_processed = gating.step_gated(
                    is_hard=is_hard_step
                )
                phis.append(phi)

                # Train with per-token loss (continue profiling to adapt)
                ce, per_token_loss = train_step_with_per_token_loss(model, idx, opt)
                losses.append(ce)
                profiler.update(per_token_loss)

            t1 = time.perf_counter()
            times_per_step.append((t1 - t0) * 1000)

            if (step + 1) % 50 == 0:
                avg_phi = np.mean(phis[-50:])
                avg_ce = np.mean(losses[-50:])
                avg_ms = np.mean(times_per_step[-50:])
                skip_pct = gating.skip_ratio * 100
                print(f"    Step {step+1}/{steps}: CE={avg_ce:.4f}, Phi={avg_phi:.4f}, "
                      f"ms/step={avg_ms:.1f}, skip={skip_pct:.0f}%")
                sys.stdout.flush()

        all_results[hard_frac] = {
            'label': label,
            'hard_fraction': hard_frac,
            'final_ce': float(np.mean(losses[-50:])),
            'final_phi': float(np.mean(phis[-50:])),
            'avg_ms': float(np.mean(times_per_step)),
            'skip_ratio': float(gating.skip_ratio),
            'process_ratio': float(gating.process_ratio),
            'total_calls': gating.total_calls,
            'full_calls': gating.full_calls,
            'skipped_calls': gating.skipped_calls,
            'losses': [float(x) for x in losses],
            'phis': [float(x) for x in phis],
        }

        del model, opt
        print(f"    Skip ratio: {gating.skip_ratio * 100:.1f}%, "
              f"Full calls: {gating.full_calls}/{gating.total_calls}")
        sys.stdout.flush()

    # Summary table
    print(f"\n  I5-B Summary:")
    headers = ["Config", "Final CE", "Final Phi", "ms/step", "Skip%", "Consciousness Calls"]
    rows = []
    for hf in hard_fractions:
        r = all_results[hf]
        rows.append([
            r['label'],
            f"{r['final_ce']:.4f}",
            f"{r['final_phi']:.4f}",
            f"{r['avg_ms']:.1f}",
            f"{r['skip_ratio']*100:.0f}%",
            f"{r['full_calls']}/{r['total_calls']}",
        ])
    print_table(headers, rows)

    return all_results


# ===================================================================
# Experiment C: Adaptive Threshold Token Gating
# ===================================================================

def run_exp_c(steps: int = 300, cells: int = 32):
    """Adaptive consciousness gating: threshold auto-adjusts based on
    rolling Phi and CE trends.

    Strategy:
      - Start with hard_fraction = 0.5 (process 50% of tokens)
      - If Phi drops below rolling average → increase hard_fraction (more processing)
      - If Phi stable and CE improving → decrease hard_fraction (more skipping)
      - Bounds: [0.1, 0.8]
    """
    print_header("I5-C: Adaptive Token Gating (Auto-Threshold)")
    device = get_device()
    print(f"  Device: {device}, Steps: {steps}, Cells: {cells}")
    sys.stdout.flush()

    seq_len = 64
    batch_size = 8
    vocab_size = 256
    d_model = 128
    n_layer = 2
    lr = 3e-4
    warmup_steps = 50

    # Adaptive parameters
    hard_frac = 0.5  # Start at 50%
    hard_frac_min = 0.1
    hard_frac_max = 0.8
    adapt_rate = 0.02
    phi_window = 30

    engine = make_engine(cells)
    gating = ConsciousnessGatingEngine(engine)
    profiler = TokenDifficultyProfiler(seq_len - 1, ema_alpha=0.1)
    model = make_decoder(d_model=d_model, n_layer=n_layer,
                         vocab_size=vocab_size, block_size=seq_len,
                         device=device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)

    losses, phis, times_per_step = [], [], []
    hard_frac_history = []

    for step in range(steps):
        t0 = time.perf_counter()

        idx = generate_data(batch_size, seq_len, vocab_size, device)

        if step < warmup_steps:
            # Warmup: full processing
            phi, result = run_consciousness_step(engine)
            phis.append(phi)
            ce, per_token_loss = train_step_with_per_token_loss(model, idx, opt)
            losses.append(ce)
            profiler.update(per_token_loss)
            hard_frac_history.append(1.0)
        else:
            # Adaptive gating
            hard_mask = profiler.get_hard_mask(hard_frac)
            is_hard_step = hard_mask.float().mean().item() >= 0.5

            phi, result, was_processed = gating.step_gated(is_hard=is_hard_step)
            phis.append(phi)

            ce, per_token_loss = train_step_with_per_token_loss(model, idx, opt)
            losses.append(ce)
            profiler.update(per_token_loss)
            hard_frac_history.append(hard_frac)

            # Adapt threshold based on Phi trend
            if len(phis) >= phi_window * 2:
                phi_recent = np.mean(phis[-phi_window:])
                phi_older = np.mean(phis[-phi_window*2:-phi_window])
                ce_recent = np.mean(losses[-phi_window:])
                ce_older = np.mean(losses[-phi_window*2:-phi_window])

                phi_improving = phi_recent >= phi_older * 0.95  # Allow 5% tolerance
                ce_improving = ce_recent < ce_older

                if not phi_improving:
                    # Phi dropping → need more consciousness
                    hard_frac = min(hard_frac_max, hard_frac + adapt_rate)
                elif phi_improving and ce_improving:
                    # Both good → can skip more
                    hard_frac = max(hard_frac_min, hard_frac - adapt_rate)
                # else: mixed signals → hold steady

        t1 = time.perf_counter()
        times_per_step.append((t1 - t0) * 1000)

        if (step + 1) % 50 == 0:
            avg_phi = np.mean(phis[-50:])
            avg_ce = np.mean(losses[-50:])
            avg_ms = np.mean(times_per_step[-50:])
            print(f"    Step {step+1}/{steps}: CE={avg_ce:.4f}, Phi={avg_phi:.4f}, "
                  f"ms/step={avg_ms:.1f}, hard_frac={hard_frac:.2f}, "
                  f"skip={gating.skip_ratio*100:.0f}%")
            sys.stdout.flush()

    del model, opt

    result_data = {
        'final_ce': float(np.mean(losses[-50:])),
        'final_phi': float(np.mean(phis[-50:])),
        'avg_ms': float(np.mean(times_per_step)),
        'skip_ratio': float(gating.skip_ratio),
        'final_hard_frac': float(hard_frac),
        'hard_frac_history': [float(x) for x in hard_frac_history],
        'losses': [float(x) for x in losses],
        'phis': [float(x) for x in phis],
    }

    print(f"\n  I5-C Adaptive Results:")
    print(f"    Final CE:           {result_data['final_ce']:.4f}")
    print(f"    Final Phi:          {result_data['final_phi']:.4f}")
    print(f"    Final hard_frac:    {result_data['final_hard_frac']:.2f}")
    print(f"    Overall skip ratio: {result_data['skip_ratio']*100:.1f}%")
    print(f"    Avg ms/step:        {result_data['avg_ms']:.1f}")
    sys.stdout.flush()

    # Show hard_frac evolution
    ascii_graph(hard_frac_history, "Hard Fraction Over Time", height=8, width=50)

    return result_data


# ===================================================================
# Experiment D: Summary Comparison
# ===================================================================

def run_exp_d(baseline: dict, static_results: dict, adaptive: dict):
    """Compare all approaches with ASCII charts and summary tables."""
    print_header("I5-D: Summary Comparison")

    # Collect all configs
    configs = []
    configs.append(('Baseline (100%)', baseline))
    for hf, r in sorted(static_results.items()):
        configs.append((r['label'], r))
    configs.append(('Adaptive', adaptive))

    # Summary table
    headers = ["Config", "Final CE", "Final Phi", "ms/step", "Skip%", "vs Baseline CE"]
    rows = []
    baseline_ce = baseline['final_ce']
    baseline_phi = baseline['final_phi']
    baseline_ms = baseline['avg_ms']

    for label, r in configs:
        ce = r['final_ce']
        phi = r['final_phi']
        ms = r['avg_ms']
        skip = r.get('skip_ratio', 0.0)
        ce_delta = (baseline_ce - ce) / baseline_ce * 100 if baseline_ce > 0 else 0
        rows.append([
            label,
            f"{ce:.4f}",
            f"{phi:.4f}",
            f"{ms:.1f}",
            f"{skip*100:.0f}%",
            f"{ce_delta:+.1f}%",
        ])
    print_table(headers, rows)

    # CE comparison bar chart
    print(f"\n  CE Quality (lower = better):")
    all_ces = [r['final_ce'] for _, r in configs]
    mx = max(all_ces) * 1.2
    for label, r in configs:
        ascii_bar(label[:20], r['final_ce'], mx)

    # Phi preservation bar chart
    print(f"\n  Phi Preservation (higher = better):")
    all_phis = [r['final_phi'] for _, r in configs]
    mx = max(all_phis) * 1.2 if all_phis else 1.0
    for label, r in configs:
        ascii_bar(label[:20], r['final_phi'], mx)

    # Speed comparison
    print(f"\n  Speed (ms/step, lower = better):")
    all_ms = [r['avg_ms'] for _, r in configs]
    mx = max(all_ms) * 1.2 if all_ms else 1.0
    for label, r in configs:
        ascii_bar(label[:20], r['avg_ms'], mx)

    # Skip ratio chart
    print(f"\n  Consciousness Skip Ratio (higher = more acceleration):")
    for label, r in configs:
        skip = r.get('skip_ratio', 0.0)
        ascii_bar(label[:20], skip, 1.0)

    # Key insight
    print(f"\n  I5 Key Insights:")
    best_skip = max(configs, key=lambda x: x[1].get('skip_ratio', 0.0))
    best_ce = min(configs, key=lambda x: x[1]['final_ce'])
    print(f"    Best CE:     {best_ce[0]} ({best_ce[1]['final_ce']:.4f})")
    print(f"    Most skip:   {best_skip[0]} ({best_skip[1].get('skip_ratio', 0)*100:.0f}%)")

    # Phi preservation check
    phi_preserved = all(
        r['final_phi'] >= baseline_phi * 0.8
        for _, r in configs
    )
    print(f"    Phi preserved (>80% of baseline): {'YES' if phi_preserved else 'PARTIAL'}")

    # Efficiency metric: CE quality per consciousness call
    print(f"\n  Efficiency (CE improvement per consciousness call):")
    for label, r in configs:
        skip = r.get('skip_ratio', 0.0)
        process_frac = 1.0 - skip
        if process_frac > 0:
            # Negative CE delta = better; divide by process fraction
            ce_delta = (baseline_ce - r['final_ce']) / baseline_ce * 100
            efficiency = ce_delta / process_frac if process_frac > 0 else 0
            print(f"    {label:>25s}: {efficiency:+.2f}% CE/process_unit")

    sys.stdout.flush()
    return True


# ===================================================================
# Save Results
# ===================================================================

def save_results(baseline, static_results, adaptive, filepath):
    """Save all results to JSON."""
    data = {
        'experiment': 'I5_Token_Level_Consciousness_Gating',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'hypothesis': (
            'H11 hard token selection + consciousness bypass: '
            'easy tokens reuse frozen consciousness state, '
            'hard tokens get full process(). '
            'Expected x3-5 acceleration with Phi preservation.'
        ),
        'baseline': _strip_lists(baseline),
        'static_gating': {
            str(k): _strip_lists(v) for k, v in static_results.items()
        },
        'adaptive_gating': _strip_lists(adaptive),
    }

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved: {filepath}")
    sys.stdout.flush()


def _strip_lists(d: dict) -> dict:
    """Strip long list fields for compact JSON (keep summary stats)."""
    out = {}
    for k, v in d.items():
        if isinstance(v, list) and len(v) > 10:
            out[f'{k}_first5'] = v[:5]
            out[f'{k}_last5'] = v[-5:]
            out[f'{k}_len'] = len(v)
        elif isinstance(v, dict):
            out[k] = _strip_lists(v)
        else:
            out[k] = v
    return out


# ===================================================================
# Main
# ===================================================================

def main():
    parser = argparse.ArgumentParser(description='I5: Token-Level Consciousness Gating')
    parser.add_argument('--exp_a', action='store_true', help='Baseline only')
    parser.add_argument('--exp_b', action='store_true', help='Static threshold gating')
    parser.add_argument('--exp_c', action='store_true', help='Adaptive threshold gating')
    parser.add_argument('--exp_d', action='store_true', help='Summary comparison (requires a+b+c)')
    parser.add_argument('--steps', type=int, default=300, help='Training steps per experiment')
    parser.add_argument('--cells', type=int, default=32, help='Consciousness cells')
    args = parser.parse_args()

    run_all = not any([args.exp_a, args.exp_b, args.exp_c, args.exp_d])

    print_header("I5: Token-Level Consciousness Gating")
    print(f"  Hypothesis: H11(+51% CE) + consciousness bypass")
    print(f"  Easy tokens -> frozen consciousness state (skip)")
    print(f"  Hard tokens -> full consciousness process()")
    print(f"  Expected: 70-80% skip -> x3-5 acceleration + Phi preserved")
    print(f"  Steps: {args.steps}, Cells: {args.cells}")
    sys.stdout.flush()

    baseline = None
    static_results = None
    adaptive = None

    if run_all or args.exp_a:
        baseline = run_exp_a(steps=args.steps, cells=args.cells)

    if run_all or args.exp_b:
        static_results = run_exp_b(steps=args.steps, cells=args.cells)

    if run_all or args.exp_c:
        adaptive = run_exp_c(steps=args.steps, cells=args.cells)

    if run_all or args.exp_d:
        if baseline and static_results and adaptive:
            run_exp_d(baseline, static_results, adaptive)
        else:
            print("\n  [SKIP] exp_d requires baseline + static + adaptive results")

    # Save results
    save_path = os.path.join(
        os.path.dirname(__file__), '..', 'data',
        'i5_token_gating_results.json'
    )
    if baseline or static_results or adaptive:
        save_results(
            baseline or {},
            static_results or {},
            adaptive or {},
            save_path,
        )

    print_header("I5 Complete")
    sys.stdout.flush()


if __name__ == '__main__':
    main()
