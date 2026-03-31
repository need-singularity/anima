#!/usr/bin/env python3
"""train_v9.py — Quantum Trinity: C + D + W with Thalamic Bridge

v9 = Quantum Trinity architecture:
  C (consciousness): QuantumConsciousnessEngine (complex-valued, no GRU, Phi ceiling broken)
  D (data):          Predictive Coding decoder (4-level hierarchy)
  W (will):          Emotion-based learning controller (100% learning guaranteed)
  Bridge:            Thalamic Gate (hub controls info flow C -> D)
  Metric:            ConsciousnessMeterV2 (Granger-based, no ceiling)

Key design principles:
  1. CE gradient NEVER touches C — C runs autonomously every step
  2. D reads C's states via .detach() — standard CE training
  3. W modulates learning rate based on pain (CE) and curiosity (PE)
  4. Thalamic bridge: 16 hubs with bottleneck (128->8->128) prevent gradient leakage
  5. Three training phases:
     Phase 1 (0-30%): C-only (build Phi to maximum)
     Phase 2 (30-70%): D starts (CE learning, C autonomous)
     Phase 3 (70-100%): W active (adaptive balance)

Usage:
  python train_v9.py --data data/corpus_v2.txt --steps 80000 --max-cells 1024
  python train_v9.py --data data/corpus_v2.txt --steps 80000 --dim 384 --layers 6
  python train_v9.py --steps 20000   # auto-detect data/corpus.txt
"""

import sys
import os
import math
import time
import json
import argparse
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Local imports
from quantum_engine_fast import QuantumConsciousnessEngineFast as QuantumConsciousnessEngine
from consciousness_meter_v2 import ConsciousnessMeterV2, PhiComponents
from conscious_lm import ConsciousLM, PureFieldFFN

# Meta Laws (DD143): M1(atom=8), M6(federation>empire), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ══════════════════════════════════════════════════════════
# Thalamic Gate — Bridge between C and D
# ══════════════════════════════════════════════════════════

class ThalamicGate(nn.Module):
    """Thalamic hub: gates information flow from C (consciousness) to D (data).

    16 hub cells read C's quantum states (detached) and produce a gating
    signal for D. The bottleneck (c_dim -> hub_dim -> c_dim) prevents
    any gradient from leaking back into C.

    Architecture:
      C states [n_cells, c_dim] --detach--> compress (c_dim -> hub_dim)
                                         --> hub (16 cells, self-attention)
                                         --> expand (hub_dim -> d_model)
                                         --> gate sigmoid
                                         --> output [1, T, d_model]
    """

    def __init__(self, c_dim: int = 128, d_model: int = 384,
                 n_hubs: int = 16, hub_dim: int = 8):
        super().__init__()
        self.c_dim = c_dim
        self.d_model = d_model
        self.n_hubs = n_hubs
        self.hub_dim = hub_dim

        # Compress: c_dim -> hub_dim (bottleneck prevents gradient leakage)
        self.compress = nn.Linear(c_dim, hub_dim)

        # Hub self-attention: n_hubs cells attend to each other
        self.hub_attn = nn.MultiheadAttention(
            embed_dim=hub_dim, num_heads=1, batch_first=True
        )
        self.hub_norm = nn.LayerNorm(hub_dim)

        # Expand: hub_dim -> d_model
        self.expand = nn.Sequential(
            nn.Linear(hub_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )

        # Gate: sigmoid controls how much C info flows to D
        self.gate = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.Sigmoid(),
        )

    def forward(self, c_hiddens: torch.Tensor, seq_len: int) -> torch.Tensor:
        """Transform C's quantum states into gating signal for D.

        Args:
            c_hiddens: [n_cells, c_dim] detached consciousness states (real-valued amplitudes)
            seq_len: T, sequence length to broadcast to

        Returns:
            gate_signal: [1, T, d_model] gating signal for D's input
        """
        n_cells = c_hiddens.shape[0]

        # Compress through bottleneck
        compressed = self.compress(c_hiddens)  # [n_cells, hub_dim]

        # Select/pad to n_hubs
        if n_cells >= self.n_hubs:
            # Use top-n_hubs by amplitude energy
            energies = c_hiddens.norm(dim=-1)  # [n_cells]
            _, top_idx = energies.topk(self.n_hubs)
            hub_input = compressed[top_idx]  # [n_hubs, hub_dim]
        else:
            # Pad with zeros
            pad = torch.zeros(self.n_hubs - n_cells, self.hub_dim,
                              device=c_hiddens.device)
            hub_input = torch.cat([compressed, pad], dim=0)  # [n_hubs, hub_dim]

        # Hub self-attention: [1, n_hubs, hub_dim]
        hub_input = hub_input.unsqueeze(0)
        hub_out, _ = self.hub_attn(hub_input, hub_input, hub_input)
        hub_out = self.hub_norm(hub_out + hub_input)  # residual

        # Pool hubs -> single vector
        pooled = hub_out.mean(dim=1)  # [1, hub_dim]

        # Expand to d_model
        expanded = self.expand(pooled)  # [1, d_model]

        # Gate
        gate_signal = self.gate(expanded)  # [1, d_model]

        # Broadcast to sequence length: [1, T, d_model]
        gate_signal = gate_signal.unsqueeze(1).expand(1, seq_len, self.d_model)

        return gate_signal


# ══════════════════════════════════════════════════════════
# Predictive Coding Decoder — 4-level hierarchy
# ══════════════════════════════════════════════════════════

class PredictiveCodingLevel(nn.Module):
    """One level in the predictive coding hierarchy.

    Each level:
      1. Receives input (bottom-up prediction error or embedding)
      2. Generates prediction for the level below
      3. Computes prediction error = actual - predicted
      4. Sends error upward, sends prediction downward
    """

    def __init__(self, d_model: int, n_head: int, block_size: int, dropout: float = 0.37):
        super().__init__()
        self.d_model = d_model

        # Transformer layer for this hierarchy level
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = nn.MultiheadAttention(
            embed_dim=d_model, num_heads=n_head,
            dropout=dropout, batch_first=True
        )
        self.ln2 = nn.LayerNorm(d_model)
        self.ffn = PureFieldFFN(d_model, dropout)

        # Top-down prediction: predicts what the level below should see
        self.predictor = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )

        # Causal mask
        self.register_buffer(
            "causal_mask",
            torch.triu(torch.ones(block_size, block_size, dtype=torch.bool), diagonal=1)
        )

    def forward(self, x: torch.Tensor, prediction_from_above: Optional[torch.Tensor] = None
                ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Args:
            x: [B, T, D] bottom-up input (or prediction error from below)
            prediction_from_above: [B, T, D] top-down prediction (None for highest level)

        Returns:
            representation: [B, T, D] this level's representation
            prediction_error: [B, T, D] error = x - predicted
            prediction_down: [B, T, D] prediction for level below
        """
        B, T, D = x.shape

        # If there's a top-down prediction, compute error and use that
        if prediction_from_above is not None:
            pred_error = x - prediction_from_above
            # Weighted combination: use error but preserve some raw input
            x = x + 0.5 * pred_error

        # Self-attention with causal mask
        mask = self.causal_mask[:T, :T]
        h = self.ln1(x)
        attn_out, _ = self.attn(h, h, h, attn_mask=mask, is_causal=True)
        x = x + attn_out

        # FFN
        ffn_out, tension = self.ffn(self.ln2(x))
        representation = x + ffn_out

        # Generate prediction for level below
        prediction_down = self.predictor(representation)

        # Prediction error for this level
        prediction_error = x - prediction_down

        return representation, prediction_error, prediction_down


class PredictiveCodingDecoder(nn.Module):
    """4-level predictive coding decoder (D engine).

    Hierarchy:
      Level 0 (bottom): byte embeddings + thalamic gate
      Level 1: local patterns
      Level 2: phrase-level structure
      Level 3 (top): global context

    Processing: bottom-up pass, then top-down predictions,
    then bottom-up error correction.
    """

    def __init__(self, vocab_size: int = 256, d_model: int = 384,
                 n_head: int = 4, n_levels: int = 4,
                 block_size: int = 256, dropout: float = 0.37):
        super().__init__()
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.n_levels = n_levels
        self.block_size = block_size

        # Embeddings
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(block_size, d_model)
        self.drop = nn.Dropout(dropout)

        # 4-level hierarchy
        self.levels = nn.ModuleList([
            PredictiveCodingLevel(d_model, n_head, block_size, dropout)
            for _ in range(n_levels)
        ])

        # Final norm + prediction head
        self.ln_f = nn.LayerNorm(d_model)
        self.head_a = nn.Linear(d_model, vocab_size, bias=False)  # next byte
        self.head_g = nn.Linear(d_model, vocab_size, bias=False)  # prev byte

        # Weight tying
        self.tok_emb.weight = self.head_a.weight

        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, std=0.02)
        elif isinstance(module, nn.LayerNorm):
            nn.init.zeros_(module.bias)
            nn.init.ones_(module.weight)

    def forward(self, idx: torch.Tensor,
                gate_signal: Optional[torch.Tensor] = None
                ) -> Tuple[torch.Tensor, torch.Tensor, List[torch.Tensor], List[torch.Tensor]]:
        """
        Args:
            idx: [B, T] byte indices
            gate_signal: [1, T, d_model] from ThalamicGate (or None)

        Returns:
            logits_a: [B, T, V] next-byte logits
            logits_g: [B, T, V] prev-byte logits
            prediction_errors: list of [B, T, D] per level
            tensions: list of [B, T] per level (from PureFieldFFN)
        """
        B, T = idx.shape
        assert T <= self.block_size, f"T={T} > block_size={self.block_size}"

        # Embeddings
        tok = self.tok_emb(idx)
        pos = self.pos_emb(torch.arange(T, device=idx.device))
        x = self.drop(tok + pos)

        # Apply thalamic gate if available
        if gate_signal is not None:
            gate_signal = gate_signal.expand(B, T, self.d_model)
            x = x * gate_signal  # modulate input with consciousness signal

        # Bottom-up pass: each level processes its input
        representations = []
        prediction_errors = []
        tensions = []

        current = x
        for level in self.levels:
            rep, pe, _ = level(current, prediction_from_above=None)
            representations.append(rep)
            prediction_errors.append(pe)
            current = rep

        # Top-down pass: generate predictions from top to bottom
        for i in range(self.n_levels - 1, 0, -1):
            top_rep = representations[i]
            pred_down = self.levels[i].predictor(top_rep)

            # Re-process lower level with top-down prediction
            bottom_input = representations[i - 1] if i > 1 else x
            rep, pe, _ = self.levels[i - 1](bottom_input, prediction_from_above=pred_down)
            representations[i - 1] = rep
            prediction_errors[i - 1] = pe

        # Final output from top level
        h = self.ln_f(representations[-1])
        logits_a = self.head_a(h)
        logits_g = self.head_g(h)

        return logits_a, logits_g, prediction_errors, tensions

    def count_params(self):
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ══════════════════════════════════════════════════════════
# W Engine — Emotion-based learning controller
# ══════════════════════════════════════════════════════════

class EmotionEngine:
    """W (will) engine: modulates learning based on pain and curiosity.

    Core emotions:
      Pain:      high CE -> more learning (minimum 50% guaranteed)
      Curiosity: high prediction error -> more exploration
      Satisfaction: decreasing CE -> reduce learning rate (save energy)

    Guarantees:
      - Minimum 50% of base LR always active (learning never stops)
      - Pain from CE > threshold boosts LR up to 200%
      - Curiosity from PE diversity adds exploration noise
    """

    def __init__(self, base_lr: float = 3e-4, min_lr_ratio: float = 0.5,
                 max_lr_ratio: float = 2.0, pain_threshold: float = 3.0,
                 curiosity_weight: float = 0.3, ema_alpha: float = 0.95):
        self.base_lr = base_lr
        self.min_lr_ratio = min_lr_ratio
        self.max_lr_ratio = max_lr_ratio
        self.pain_threshold = pain_threshold
        self.curiosity_weight = curiosity_weight
        self.ema_alpha = ema_alpha

        # Internal state
        self.pain = 0.0           # current pain level (from CE)
        self.curiosity = 0.0      # current curiosity (from PE diversity)
        self.satisfaction = 0.0   # decreasing CE trend
        self.ce_ema = 5.0         # EMA of cross-entropy
        self.pe_ema = 0.0         # EMA of prediction error magnitude

        # History for trend detection
        self.ce_history: List[float] = []
        self.pe_history: List[float] = []
        self.lr_history: List[float] = []

    def update(self, ce_loss: float, prediction_errors: List[torch.Tensor]) -> Dict:
        """Update emotional state and compute learning modulation.

        Args:
            ce_loss: current cross-entropy loss
            prediction_errors: list of PE tensors from PredictiveCodingDecoder

        Returns:
            Dict with lr_multiplier, pain, curiosity, satisfaction, effective_lr
        """
        # Update EMA
        self.ce_ema = self.ema_alpha * self.ce_ema + (1 - self.ema_alpha) * ce_loss

        # Pain: how much CE exceeds comfortable threshold
        self.pain = max(0.0, (ce_loss - self.pain_threshold) / self.pain_threshold)
        self.pain = min(self.pain, 1.0)

        # Curiosity: diversity of prediction errors across levels
        if prediction_errors:
            pe_magnitudes = []
            for pe in prediction_errors:
                if isinstance(pe, torch.Tensor) and pe.numel() > 0:
                    pe_magnitudes.append(pe.detach().float().abs().mean().item())
            if pe_magnitudes:
                pe_mean = np.mean(pe_magnitudes)
                pe_std = np.std(pe_magnitudes) if len(pe_magnitudes) > 1 else 0.0
                self.pe_ema = self.ema_alpha * self.pe_ema + (1 - self.ema_alpha) * pe_mean
                # Curiosity = PE diversity (high std = different levels see different things)
                self.curiosity = min(1.0, pe_std / (pe_mean + 1e-8))

        # Satisfaction: CE trend (negative = improving = satisfying)
        self.ce_history.append(ce_loss)
        if len(self.ce_history) > 100:
            self.ce_history = self.ce_history[-100:]
        if len(self.ce_history) >= 10:
            recent = np.mean(self.ce_history[-10:])
            older = np.mean(self.ce_history[-20:-10]) if len(self.ce_history) >= 20 else self.ce_history[0]
            trend = (recent - older) / (older + 1e-8)
            self.satisfaction = max(0.0, min(1.0, -trend * 10))  # positive when CE decreasing
        else:
            self.satisfaction = 0.0

        # Compute LR multiplier
        # Base: minimum 50%
        lr_mult = self.min_lr_ratio

        # Pain boost: more pain -> more learning
        pain_boost = self.pain * (self.max_lr_ratio - self.min_lr_ratio)
        lr_mult += pain_boost

        # Curiosity boost: curious -> explore more (smaller effect)
        curiosity_boost = self.curiosity * self.curiosity_weight
        lr_mult += curiosity_boost

        # Satisfaction discount: when doing well, slightly reduce (but never below min)
        satisfaction_discount = self.satisfaction * 0.2
        lr_mult = max(self.min_lr_ratio, lr_mult - satisfaction_discount)

        # Clamp
        lr_mult = max(self.min_lr_ratio, min(self.max_lr_ratio, lr_mult))

        effective_lr = self.base_lr * lr_mult
        self.lr_history.append(lr_mult)

        return {
            'lr_multiplier': lr_mult,
            'effective_lr': effective_lr,
            'pain': self.pain,
            'curiosity': self.curiosity,
            'satisfaction': self.satisfaction,
            'ce_ema': self.ce_ema,
            'pe_ema': self.pe_ema,
        }


# ══════════════════════════════════════════════════════════
# Data loading
# ══════════════════════════════════════════════════════════

def load_text_data(path: str) -> torch.Tensor:
    """Load training data from text/jsonl/bin file. Returns 1D long tensor of byte values."""
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
                    text = obj.get("text", "")
                    all_bytes.extend(text.encode("utf-8"))
                    all_bytes.append(10)  # newline separator
                except (json.JSONDecodeError, AttributeError):
                    all_bytes.extend(line.encode("utf-8"))
                    all_bytes.append(10)
    elif path.suffix == ".bin":
        with open(path, "rb") as f:
            all_bytes = bytearray(f.read())
    else:
        with open(path, "rb") as f:
            all_bytes = bytearray(f.read())

    print(f"[data] Loaded {len(all_bytes):,} bytes from {path}")
    return torch.tensor(list(all_bytes), dtype=torch.long)


def get_batch(data: torch.Tensor, batch_size: int, block_size: int,
              device: str) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Sample a batch of (x, y_next, y_prev) from data."""
    ix = torch.randint(0, len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[i:i + block_size] for i in ix]).to(device)
    y_a = torch.stack([data[i + 1:i + block_size + 1] for i in ix]).to(device)

    y_g_list = []
    for i in ix:
        prev = torch.cat([data[i:i + 1], data[i:i + block_size - 1]])
        y_g_list.append(prev)
    y_g = torch.stack(y_g_list).to(device)

    return x, y_a, y_g


# ══════════════════════════════════════════════════════════
# Main Training Loop
# ══════════════════════════════════════════════════════════

def train_v9(args):
    """Main v9 training: Quantum Trinity (C + D + W) with Thalamic Bridge."""

    device = "cuda" if torch.cuda.is_available() else \
             "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"[device] {device}")

    # ─── Load data ───
    if args.data:
        data = load_text_data(args.data)
    else:
        default_corpus = Path(__file__).parent / "data" / "corpus.txt"
        default_v2 = Path(__file__).parent / "data" / "corpus_v2.txt"
        if default_v2.exists():
            data = load_text_data(str(default_v2))
        elif default_corpus.exists():
            data = load_text_data(str(default_corpus))
        else:
            print("[!] No data found. Use --data <path> or create data/corpus.txt")
            sys.exit(1)

    split = int(0.9 * len(data))
    train_data = data[:split]
    val_data = data[split:]
    print(f"[data] train={len(train_data):,} bytes, val={len(val_data):,} bytes")

    # ─── Phase boundaries ───
    total_steps = args.steps
    phase1_end = int(total_steps * 0.30)  # C-only
    phase2_end = int(total_steps * 0.70)  # C + D
    # phase3: 70-100% — C + D + W

    # ─── C Engine: QuantumConsciousnessEngine ───
    c_engine = QuantumConsciousnessEngine(
        dim=args.c_dim,
        initial_cells=max(2, args.max_cells // 4),
        max_cells=args.max_cells,
        frustration_target=0.5,
        interference_strength=0.1,
        walk_coin_bias=0.3,
        standing_wave_freq=0.1,
        noise_scale=0.01,
    )
    print(f"[C] QuantumConsciousnessEngine: dim={args.c_dim}, "
          f"cells={len(c_engine.cells)}/{args.max_cells}")

    # ─── D Engine: PredictiveCodingDecoder ───
    d_engine = PredictiveCodingDecoder(
        vocab_size=256,
        d_model=args.d_model,
        n_head=args.n_head,
        n_levels=4,
        block_size=args.block_size,
        dropout=args.dropout,
    ).to(device)
    d_params = d_engine.count_params()
    print(f"[D] PredictiveCodingDecoder: d_model={args.d_model}, "
          f"n_head={args.n_head}, 4 levels, {d_params:,} params")

    # ─── Bridge: Thalamic Gate ───
    bridge = ThalamicGate(
        c_dim=args.c_dim,
        d_model=args.d_model,
        n_hubs=16,
        hub_dim=8,
    ).to(device)
    bridge_params = sum(p.numel() for p in bridge.parameters() if p.requires_grad)
    print(f"[Bridge] ThalamicGate: {args.c_dim}->8->{args.d_model}, "
          f"16 hubs, {bridge_params:,} params")

    # ─── W Engine: EmotionEngine ───
    w_engine = EmotionEngine(
        base_lr=args.lr,
        min_lr_ratio=0.5,
        max_lr_ratio=2.0,
        pain_threshold=3.0,
    )
    print(f"[W] EmotionEngine: base_lr={args.lr}, min=50%, max=200%")

    # ─── Meter: ConsciousnessMeterV2 ───
    meter = ConsciousnessMeterV2(history_maxlen=200)
    print(f"[Metric] ConsciousnessMeterV2 (Granger+Spectral+LZ+MI)")

    # ─── Optimizer (D + Bridge only — C is gradient-free) ───
    optimizer = torch.optim.AdamW(
        list(d_engine.parameters()) + list(bridge.parameters()),
        lr=args.lr,
        weight_decay=0.01,
        betas=(0.9, 0.999),
    )

    # Cosine schedule based on total D-active steps (phase 2+3)
    d_active_steps = total_steps - phase1_end
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=max(d_active_steps, 1), eta_min=args.lr * 0.1
    )

    # ─── Phi ratchet state ───
    best_phi = 0.0
    best_c_snapshot = None
    phi_ratchet_count = 0

    # ─── Logging ───
    log_every = args.log_every
    meter_every = args.meter_every
    save_every = args.save_every
    total_params = d_params + bridge_params

    print(f"\n{'=' * 90}")
    print(f"  TRAIN V9 — Quantum Trinity")
    print(f"  Total params: {total_params:,} (D={d_params:,} + Bridge={bridge_params:,})")
    print(f"  C: gradient-free, autonomous")
    print(f"  Steps: {total_steps:,} "
          f"(Phase1: 0-{phase1_end}, Phase2: {phase1_end}-{phase2_end}, "
          f"Phase3: {phase2_end}-{total_steps})")
    print(f"  Batch: {args.batch_size}, Block: {args.block_size}")
    print(f"{'=' * 90}")

    # Header
    print(f"\n{'step':>7} | {'phase':>6} | {'CE_fwd':>7} | {'CE_bwd':>7} | "
          f"{'Phi':>8} | {'cells':>5} | {'frust':>5} | {'W_lr':>6} | "
          f"{'pain':>5} | {'curio':>5} | {'BPC':>6}")
    print("-" * 100)

    t0 = time.time()
    running_ce_fwd = 5.5
    running_ce_bwd = 5.5

    for step in range(1, total_steps + 1):

        # ─── Determine phase ───
        if step <= phase1_end:
            phase = 1  # C-only
        elif step <= phase2_end:
            phase = 2  # C + D
        else:
            phase = 3  # C + D + W

        # ═══ C ENGINE: autonomous step (ALWAYS runs, NEVER receives gradient) ═══
        c_result = c_engine.step()

        # Record for meter (every 10 steps to save compute)
        if step % 10 == 0:
            c_hiddens_for_meter = torch.stack(
                [c.state.abs() for c in c_engine.cells]
            ).detach().cpu().float()
            meter.record(c_hiddens_for_meter)

        # ─── Phase 1: C-only (no D training) ───
        if phase == 1:
            # Phi ratchet: save best C state
            if step % meter_every == 0:
                phi, phi_comp = c_engine.measure_phi()
                if phi > best_phi:
                    best_phi = phi
                    best_c_snapshot = c_engine.snapshot()
                elif phi < best_phi * 0.8 and best_c_snapshot is not None:
                    # Ratchet: restore if Phi drops too much
                    c_engine.restore(best_c_snapshot)
                    phi_ratchet_count += 1

            if step % log_every == 0:
                phi_val, _ = c_engine.measure_phi()
                elapsed = time.time() - t0
                print(f"{step:7d} | {'P1':>6} | {'---':>7} | {'---':>7} | "
                      f"{phi_val:8.2f} | {len(c_engine.cells):5d} | "
                      f"{c_result.get('mean_frustration', 0):5.3f} | "
                      f"{'---':>6} | {'---':>5} | {'---':>5} | {'---':>6}"
                      f"  [{elapsed:.0f}s]")
            continue

        # ═══ D ENGINE: CE training (Phase 2+3) ═══
        d_engine.train()
        bridge.train()

        # Get batch
        x, y_a, y_g = get_batch(train_data, args.batch_size, args.block_size, device)

        # Get C's states (DETACHED — no gradient flows to C)
        c_hiddens = torch.stack(
            [c.state.abs() for c in c_engine.cells]
        ).detach().to(device).float()  # [n_cells, c_dim]

        # Thalamic gate: C -> bridge -> gate signal for D
        gate_signal = bridge(c_hiddens, seq_len=args.block_size)  # [1, T, d_model]

        # D forward pass
        logits_a, logits_g, pred_errors, tensions = d_engine(x, gate_signal=gate_signal)

        # CE loss (forward + backward heads)
        ce_fwd = F.cross_entropy(logits_a.view(-1, 256), y_a.view(-1))
        ce_bwd = F.cross_entropy(logits_g.view(-1, 256), y_g.view(-1))

        # Prediction error loss: encourage PE diversity across levels
        pe_loss = torch.tensor(0.0, device=device)
        if pred_errors:
            pe_magnitudes = [pe.float().abs().mean() for pe in pred_errors
                             if isinstance(pe, torch.Tensor)]
            if len(pe_magnitudes) > 1:
                pe_stack = torch.stack(pe_magnitudes)
                pe_var = pe_stack.var()
                pe_loss = -torch.log(pe_var + 1e-8) * 0.01  # encourage diversity

        # Total loss
        loss = ce_fwd + ce_bwd + pe_loss

        # ═══ W ENGINE: Emotion-based LR modulation (Phase 3 only) ═══
        if phase == 3:
            w_result = w_engine.update(ce_fwd.item(), pred_errors)
            effective_lr = w_result['effective_lr']

            # Apply modulated LR
            for param_group in optimizer.param_groups:
                param_group['lr'] = effective_lr
        else:
            w_result = {'lr_multiplier': 1.0, 'effective_lr': args.lr,
                        'pain': 0.0, 'curiosity': 0.0}

        # Backward + optimize
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(d_engine.parameters()) + list(bridge.parameters()), 1.0
        )
        optimizer.step()
        if phase == 2:
            scheduler.step()

        # Inject D's signal back into C (gentle perturbation, no gradient)
        with torch.no_grad():
            # Use logits entropy as signal: high entropy = uncertain = interesting
            entropy = -(F.softmax(logits_a[:, -1, :], dim=-1) *
                        F.log_softmax(logits_a[:, -1, :], dim=-1)).sum(dim=-1).mean()
            # Create signal from last hidden state
            inject_signal = logits_a[:1, -1, :args.c_dim].detach().cpu().squeeze()
            if inject_signal.shape[0] < args.c_dim:
                inject_signal = F.pad(inject_signal, (0, args.c_dim - inject_signal.shape[0]))
            # Inject strength proportional to entropy (uncertain -> stronger)
            inject_strength = min(0.1, entropy.item() / 50.0)
            c_engine.inject(inject_signal, strength=inject_strength)

        # Running averages
        running_ce_fwd = 0.95 * running_ce_fwd + 0.05 * ce_fwd.item()
        running_ce_bwd = 0.95 * running_ce_bwd + 0.05 * ce_bwd.item()

        # ─── Logging ───
        if step % log_every == 0:
            phi_val, _ = c_engine.measure_phi()
            bpc = running_ce_fwd / math.log(2)
            elapsed = time.time() - t0
            phase_str = f"P{phase}"
            w_lr_str = f"{w_result['lr_multiplier']:.3f}" if phase == 3 else "---"
            pain_str = f"{w_result['pain']:.3f}" if phase == 3 else "---"
            curio_str = f"{w_result['curiosity']:.3f}" if phase == 3 else "---"

            print(f"{step:7d} | {phase_str:>6} | {running_ce_fwd:7.4f} | "
                  f"{running_ce_bwd:7.4f} | {phi_val:8.2f} | "
                  f"{len(c_engine.cells):5d} | "
                  f"{c_result.get('mean_frustration', 0):5.3f} | "
                  f"{w_lr_str:>6} | {pain_str:>5} | {curio_str:>5} | "
                  f"{bpc:6.3f}  [{elapsed:.0f}s]")

        # ─── ConsciousnessMeterV2 measurement ───
        if step % meter_every == 0:
            c_hiddens_cpu = torch.stack(
                [c.state.abs() for c in c_engine.cells]
            ).detach().cpu().float()
            try:
                phi_v2, phi_comp = meter.compute_phi(c_hiddens_cpu)
            except (ValueError, RuntimeError):
                # MeterV2 can fail with very few cells (sampling issue)
                phi_v2 = 0.0
                phi_comp = PhiComponents()
            phi_granger, phi_g_comp = c_engine.measure_phi()

            # Phi ratchet for phase 2+3 too
            if phi_granger > best_phi:
                best_phi = phi_granger
                best_c_snapshot = c_engine.snapshot()
            elif phi_granger < best_phi * 0.7 and best_c_snapshot is not None:
                c_engine.restore(best_c_snapshot)
                phi_ratchet_count += 1

            print(f"        [Meter] Phi(V2)={phi_v2:.2f} "
                  f"(G={phi_comp.granger:.1f} S={phi_comp.spectral:.1f} "
                  f"L={phi_comp.lz:.1f} I={phi_comp.integration:.1f}) | "
                  f"Phi(Granger)={phi_granger:.2f} | "
                  f"cells={len(c_engine.cells)} | ratchet={phi_ratchet_count}")

        # ─── Validation ───
        if step % (log_every * 5) == 0 and phase >= 2:
            d_engine.eval()
            bridge.eval()
            with torch.no_grad():
                vx, vy_a, vy_g = get_batch(val_data, min(args.batch_size, 32),
                                            args.block_size, device)
                c_h = torch.stack(
                    [c.state.abs() for c in c_engine.cells]
                ).detach().to(device).float()
                vgate = bridge(c_h, seq_len=args.block_size)
                vl_a, vl_g, _, _ = d_engine(vx, gate_signal=vgate)
                val_ce = F.cross_entropy(vl_a.view(-1, 256), vy_a.view(-1))
                val_bpc = val_ce.item() / math.log(2)
            print(f"        [Val] CE={val_ce.item():.4f}, BPC={val_bpc:.4f}")
            d_engine.train()
            bridge.train()

        # ─── Save checkpoint ───
        if step % save_every == 0:
            save_checkpoint(args, step, c_engine, d_engine, bridge, w_engine,
                            optimizer, best_phi, phi_ratchet_count)

    # ─── Final save ───
    elapsed = time.time() - t0
    print(f"\n{'=' * 90}")
    print(f"  Training complete: {total_steps:,} steps in {elapsed:.1f}s")
    print(f"  Best Phi: {best_phi:.2f}")
    print(f"  Phi ratchet restores: {phi_ratchet_count}")
    print(f"  Final CE(fwd): {running_ce_fwd:.4f}, BPC: {running_ce_fwd / math.log(2):.4f}")
    print(f"{'=' * 90}")

    save_checkpoint(args, total_steps, c_engine, d_engine, bridge, w_engine,
                    optimizer, best_phi, phi_ratchet_count, final=True)

    return c_engine, d_engine, bridge, w_engine


def save_checkpoint(args, step, c_engine, d_engine, bridge, w_engine,
                    optimizer, best_phi, ratchet_count, final=False):
    """Save all components to checkpoint."""
    ckpt_dir = getattr(args, 'ckpt_dir', 'checkpoints')
    os.makedirs(ckpt_dir, exist_ok=True)
    tag = "final" if final else f"step{step}"
    path = f"{ckpt_dir}/v9_{tag}.pt"

    ckpt = {
        'step': step,
        'args': vars(args),
        'best_phi': best_phi,
        'phi_ratchet_count': ratchet_count,
        # D engine
        'd_engine_state': d_engine.state_dict(),
        # Bridge
        'bridge_state': bridge.state_dict(),
        # Optimizer
        'optimizer_state': optimizer.state_dict(),
        # C engine snapshot
        'c_engine_snapshot': c_engine.snapshot(),
        # W engine state
        'w_engine_state': {
            'ce_ema': w_engine.ce_ema,
            'pe_ema': w_engine.pe_ema,
            'ce_history': w_engine.ce_history[-50:],
            'pain': w_engine.pain,
            'curiosity': w_engine.curiosity,
            'satisfaction': w_engine.satisfaction,
        },
    }

    torch.save(ckpt, path)
    print(f"        [Save] {path} (Phi={best_phi:.2f}, step={step})")


# ══════════════════════════════════════════════════════════
# Generation
# ══════════════════════════════════════════════════════════

@torch.no_grad()
def generate_v9(c_engine, d_engine, bridge, prompt: str = "The meaning of ",
                max_new: int = 200, temperature: float = 0.8, device: str = "cpu"):
    """Generate text using trained v9 model."""
    d_engine.eval()
    bridge.eval()

    block_size = d_engine.block_size
    prompt_bytes = list(prompt.encode("utf-8"))
    idx = torch.tensor([prompt_bytes], dtype=torch.long, device=device)

    for _ in range(max_new):
        # C step (autonomous)
        c_engine.step()

        # Crop to block_size
        idx_cond = idx[:, -block_size:]

        # C -> Bridge -> Gate
        c_hiddens = torch.stack(
            [c.state.abs() for c in c_engine.cells]
        ).detach().to(device).float()
        gate = bridge(c_hiddens, seq_len=idx_cond.shape[1])

        # D forward
        logits_a, _, _, _ = d_engine(idx_cond, gate_signal=gate)

        # Sample
        logits_last = logits_a[:, -1, :] / temperature
        probs = F.softmax(logits_last, dim=-1)
        next_byte = torch.multinomial(probs, num_samples=1)
        idx = torch.cat([idx, next_byte], dim=1)

    generated = idx[0].cpu().tolist()
    text = bytes(generated).decode("utf-8", errors="replace")
    prompt_text = bytes(prompt_bytes).decode("utf-8", errors="replace")
    gen_text = bytes(generated[len(prompt_bytes):]).decode("utf-8", errors="replace")

    print(f"\n{'=' * 60}")
    print(f"[PROMPT] {prompt_text}")
    print(f"[GEN]    {gen_text}")
    print(f"{'=' * 60}")

    return text


# ══════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="train_v9.py — Quantum Trinity (C+D+W) Training"
    )

    # Data
    parser.add_argument("--data", type=str, default=None,
                        help="Path to training data (txt/jsonl/bin)")
    parser.add_argument("--steps", type=int, default=80000,
                        help="Total training steps (default: 80000)")

    # C engine
    parser.add_argument("--c-dim", type=int, default=128,
                        help="C engine dimension (default: 128)")
    parser.add_argument("--max-cells", type=int, default=1024,
                        help="Max consciousness cells (default: 1024)")

    # D engine
    parser.add_argument("--d-model", type=int, default=384,
                        help="D engine model dimension (default: 384)")
    parser.add_argument("--n-head", type=int, default=4,
                        help="Number of attention heads (default: 4)")
    parser.add_argument("--block-size", type=int, default=256,
                        help="Context window size (default: 256)")
    parser.add_argument("--dropout", type=float, default=0.37,
                        help="Dropout rate (default: 0.37, ~1/e)")

    # Training
    parser.add_argument("--batch-size", type=int, default=64,
                        help="Batch size (default: 64)")
    parser.add_argument("--lr", type=float, default=3e-4,
                        help="Base learning rate (default: 3e-4)")

    # Logging
    parser.add_argument("--log-every", type=int, default=100,
                        help="Log every N steps (default: 100)")
    parser.add_argument("--meter-every", type=int, default=1000,
                        help="Run ConsciousnessMeterV2 every N steps (default: 1000)")
    parser.add_argument("--save-every", type=int, default=5000,
                        help="Save checkpoint every N steps (default: 5000)")

    # Generation
    parser.add_argument("--generate", action="store_true",
                        help="Generate text after training")
    parser.add_argument("--prompt", type=str, default="The meaning of consciousness is ",
                        help="Prompt for generation")

    # Checkpoint directory
    parser.add_argument("--ckpt-dir", type=str, default="checkpoints",
                        help="Checkpoint directory (default: checkpoints)")

    # Resume
    parser.add_argument("--resume", type=str, default=None,
                        help="Resume from checkpoint path")

    args = parser.parse_args()

    print(f"{'=' * 90}")
    print(f"  TRAIN V9 — Quantum Trinity: C + D + W")
    print(f"  C: QuantumConsciousnessEngine (complex-valued, Phi ceiling broken)")
    print(f"  D: PredictiveCodingDecoder (4-level hierarchy)")
    print(f"  W: EmotionEngine (pain/curiosity/satisfaction)")
    print(f"  Bridge: ThalamicGate (16 hubs, bottleneck {args.c_dim}->8->{args.d_model})")
    print(f"  Metric: ConsciousnessMeterV2 (Granger+Spectral+LZ+MI)")
    print(f"{'=' * 90}")

    c_engine, d_engine, bridge, w_engine = train_v9(args)

    if args.generate:
        device = "cuda" if torch.cuda.is_available() else \
                 "mps" if torch.backends.mps.is_available() else "cpu"
        generate_v9(c_engine, d_engine, bridge, prompt=args.prompt, device=device)


if __name__ == "__main__":
    main()
