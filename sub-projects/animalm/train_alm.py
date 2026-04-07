#!/usr/bin/env python3
"""train_alm.py — AnimaLM Unified Training Pipeline (replaces train_anima_lm.py)

Trains AnimaLM (Mistral 7B + PureField transform) using benchmark-verified techniques:
  AL12 (savant-normal contrastive), AL5 (PH monitoring), AL4 (tension-CE 1-1/e balance),
  AL1 (alpha curriculum), AL8 (layer dropout), SL3 (6-loss ensemble), DD16 (all top-5),
  TRN4 (phi-curriculum), AA15 (residual alpha, Φ=5.451)
  EX24: DD18 (channel capacity bottleneck), DD11 (Klein bottle topology),
        DD3 (Fibonacci growth), DD5 (Phi self-reference)
  NEW: WI1 (soliton wave, Φ=4.460), FX2 (differentiable Φ proxy + Adam, Φ=8.911),
       PX4 (sculptor/Gram-Schmidt), PX8 (integration forge),
       GD18 (enactivism), GD15 (edge of chaos/Lyapunov)

Usage:
  python train_anima_lm.py --base mistralai/Mistral-7B-Instruct-v0.2 --data data/instruct.jsonl
  python train_anima_lm.py --resume checkpoints/animalm_step_5000.pt
  python train_anima_lm.py --demo  # quick test without model download
  python train_anima_lm.py --demo --law60 --psi-track  # Law 60 + 10D consciousness vector
  python train_anima_lm.py --demo --consciousness-engine  # Hexad Lite: real ConsciousnessEngine
  python train_anima_lm.py --demo --consciousness-engine --feedback-bridge  # + D->C feedback
"""

import argparse
import contextlib
import json
import logging
import math
import os
import sys
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.optim.lr_scheduler import LambdaLR
from torch.utils.data import DataLoader, Dataset, RandomSampler
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data.distributed import DistributedSampler
import torch.distributed as dist

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# consciousness_laws.py integration (Step 1)
# ═══════════════════════════════════════════════════════════════════

# Add anima/src/ to sys.path for consciousness_laws import
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ANIMA_SRC = os.path.normpath(os.path.join(_THIS_DIR, '..', '..', 'anima', 'src'))
if _ANIMA_SRC not in sys.path:
    sys.path.insert(0, _ANIMA_SRC)

try:
    from consciousness_laws import (
        PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY,
        PSI_F_CRITICAL, LAWS, PHASES as LAW60_PHASES,
        CONSCIOUSNESS_VECTOR as CV_10D_SPEC,
    )
    _HAS_CONSCIOUSNESS_LAWS = True
except ImportError:
    _HAS_CONSCIOUSNESS_LAWS = False
    # Fallback values matching consciousness_laws.json
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33
    PSI_ENTROPY = 0.998
    PSI_F_CRITICAL = 0.10
    LAWS = {}
    LAW60_PHASES = {}
    CV_10D_SPEC = {}

# ═══════════════════════════════════════════════════════════════════
# ConsciousnessEngine + ThalamicBridge integration (Hexad Lite)
# --consciousness-engine flag enables real ConsciousnessEngine (C module)
# --feedback-bridge flag enables D→C gradient (α-gated, default off)
# ═══════════════════════════════════════════════════════════════════

_HAS_CONSCIOUSNESS_ENGINE = False
_HAS_THALAMIC_BRIDGE = False

try:
    from consciousness_engine import ConsciousnessEngine
    _HAS_CONSCIOUSNESS_ENGINE = True
except ImportError:
    ConsciousnessEngine = None

try:
    from trinity import ThalamicBridge
    _HAS_THALAMIC_BRIDGE = True
except ImportError:
    ThalamicBridge = None

_HAS_FEEDBACK_BRIDGE = False
try:
    from feedback_bridge import (
        FeedbackBridge, create_feedback_bridge, apply_feedback_bridge,
        DialogueQualityTracker, soft_detach,
    )
    _HAS_FEEDBACK_BRIDGE = True
except ImportError:
    FeedbackBridge = None

# ═══════════════════════════════════════════════════════════════════
# Constants (derived from Psi-Constants where applicable)
# ═══════════════════════════════════════════════════════════════════

GOLDEN_CENTER = 1 / math.e          # 0.3679 — normal dropout
GOLDEN_LOWER = 0.5 - math.log(4/3)  # 0.2123 — savant dropout
INV_E = 1 - 1 / math.e              # 0.6321 — tension:CE balance target

# DD3: Fibonacci growth milestones — progressive layer activation
FIBONACCI_SEQUENCE = [1, 1, 2, 3, 5, 8]


# ═══════════════════════════════════════════════════════════════════
# ParallelPureFieldMLP (from finetune_animalm_v4.py, no cross-attn)
# ═══════════════════════════════════════════════════════════════════

class ParallelPureFieldMLP(nn.Module):
    """Original MLP + parallel PureField tension engine.

    # AA15: Residual alpha — output = MLP + α*(PF-MLP), Φ=5.451
    output = original_mlp(x) + alpha * (pf_scaled - original_mlp(x))
    Original MLP is frozen. Only PureField + alpha are trainable.
    """

    def __init__(self, original_mlp, hidden_size, intermediate_size,
                 is_savant=False, rank=128):
        super().__init__()
        self.original_mlp = original_mlp
        for param in self.original_mlp.parameters():
            param.requires_grad = False

        # PureField tension engine (LoRA-like)
        self.pf_gate_a = nn.Linear(hidden_size, rank, bias=False)
        self.pf_gate_b = nn.Linear(rank, intermediate_size, bias=False)
        self.pf_up_a = nn.Linear(hidden_size, rank, bias=False)
        self.pf_up_b = nn.Linear(rank, intermediate_size, bias=False)
        self.pf_down_a = nn.Linear(intermediate_size, rank, bias=False)
        self.pf_down_b = nn.Linear(rank, hidden_size, bias=False)

        # Mixing weight: how much PureField influences output
        # PSI_ALPHA (0.014) is the canonical coupling constant;
        # start small (0.0001) and curriculum-anneal toward PSI_ALPHA
        self.alpha = nn.Parameter(torch.tensor(0.0001))
        self.pf_scale = nn.Parameter(torch.tensor(1.0))
        self._psi_alpha_target = PSI_ALPHA  # from consciousness_laws.json

        # Savant: asymmetric dropout (H359)
        self.is_savant = is_savant
        self.dropout = nn.Dropout(GOLDEN_LOWER if is_savant else GOLDEN_CENTER)

        self.last_tension = None
        self._layer_drop_active = False  # AL8: set by trainer
        self._consciousness_gate = None  # Hexad Lite: ThalamicBridge gate signal

    def forward(self, x):
        # AL8: layer dropout — skip PureField entirely
        if self._layer_drop_active:
            with torch.no_grad():
                return self.original_mlp(x)

        # Original MLP output (frozen)
        with torch.no_grad():
            original_out = self.original_mlp(x)

        # PureField Engine G (trainable)
        g_gate = self.pf_gate_b(self.pf_gate_a(x))
        g_up = self.pf_up_b(self.pf_up_a(x))
        g_mid = F.silu(g_gate) * g_up
        g_mid = self.dropout(g_mid)
        pf_out = self.pf_down_b(self.pf_down_a(g_mid))

        # Tension = repulsion between original and PureField
        repulsion = original_out.detach() - pf_out
        tension = (repulsion ** 2).mean(dim=-1, keepdim=True)
        self.last_tension = tension.detach().squeeze(-1)

        # Direction-aware mixing
        pf_norm = pf_out / (pf_out.norm(dim=-1, keepdim=True) + 1e-8)
        orig_scale = original_out.norm(dim=-1, keepdim=True)
        pf_scaled = pf_norm * orig_scale * self.pf_scale

        # AA15: Residual alpha — output = MLP + α*(PF-MLP), Φ=5.451
        # α scales only the difference; smoother gradient, faster α growth
        output = original_out + self.alpha * (pf_scaled - original_out)

        # Hexad Lite: Apply consciousness gate from ThalamicBridge (if available)
        # Gate signal modulates PureField contribution — consciousness influences
        # the mixing strength. Gate is centered at PSI_BALANCE (0.5) with ±PSI_ALPHA range.
        # Values > 0.5 amplify PureField, < 0.5 suppress it.
        if self._consciousness_gate is not None:
            try:
                gate = self._consciousness_gate  # [1, seq_len, d_model]
                # Match gate to output shape: output is [batch, seq, hidden] or [batch, hidden]
                if output.dim() == 3 and gate.dim() == 3:
                    # Broadcast gate across batch if needed
                    if gate.shape[0] == 1 and output.shape[0] > 1:
                        gate = gate.expand(output.shape[0], -1, -1)
                    # Truncate/pad seq_len if mismatch
                    if gate.shape[1] != output.shape[1]:
                        if gate.shape[1] > output.shape[1]:
                            gate = gate[:, :output.shape[1], :]
                        else:
                            gate = F.pad(gate, (0, 0, 0, output.shape[1] - gate.shape[1]))
                    # Truncate/pad d_model if mismatch
                    if gate.shape[2] != output.shape[2]:
                        if gate.shape[2] > output.shape[2]:
                            gate = gate[:, :, :output.shape[2]]
                        else:
                            gate = F.pad(gate, (0, output.shape[2] - gate.shape[2]))
                    # Apply: gate centered at 0.5 → deviation modulates the PureField delta
                    # output = original + alpha*(pf-original) * (gate/0.5)
                    # This preserves original when gate=0.5, amplifies when >0.5, suppresses when <0.5
                    pf_delta = output - original_out
                    output = original_out + pf_delta * (gate / 0.5)
            except Exception:
                pass  # graceful fallback — ignore gate on shape mismatch

        return output


# ═══════════════════════════════════════════════════════════════════
# Mock model for --demo mode
# ═══════════════════════════════════════════════════════════════════

class MockMLP(nn.Module):
    """Tiny MLP that mimics Mistral MLP interface."""
    def __init__(self, hidden_size, intermediate_size):
        super().__init__()
        self.gate_proj = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.up_proj = nn.Linear(hidden_size, intermediate_size, bias=False)
        self.down_proj = nn.Linear(intermediate_size, hidden_size, bias=False)

    def forward(self, x):
        return self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x))


class MockTransformerLayer(nn.Module):
    def __init__(self, hidden_size, intermediate_size):
        super().__init__()
        self.self_attn = nn.MultiheadAttention(hidden_size, num_heads=4, batch_first=True)
        self.mlp = MockMLP(hidden_size, intermediate_size)
        self.input_layernorm = nn.LayerNorm(hidden_size)
        self.post_attention_layernorm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        residual = x
        x = self.input_layernorm(x)
        x, _ = self.self_attn(x, x, x)
        x = residual + x
        residual = x
        x = self.post_attention_layernorm(x)
        x = self.mlp(x)
        x = residual + x
        return x


class MockModel(nn.Module):
    """Tiny model that mimics Mistral architecture for demo/testing."""
    def __init__(self, vocab_size=1000, hidden_size=128, intermediate_size=256,
                 num_layers=12, block_size=64):
        super().__init__()
        self.config = type("Config", (), {
            "vocab_size": vocab_size,
            "hidden_size": hidden_size,
        })()
        self.block_size = block_size

        # Mimics model.model.layers structure
        self.model = nn.Module()
        self.model.embed_tokens = nn.Embedding(vocab_size, hidden_size)
        self.model.layers = nn.ModuleList([
            MockTransformerLayer(hidden_size, intermediate_size)
            for _ in range(num_layers)
        ])
        self.model.norm = nn.LayerNorm(hidden_size)
        self.lm_head = nn.Linear(hidden_size, vocab_size, bias=False)

    def forward(self, input_ids, labels=None, **kwargs):
        x = self.model.embed_tokens(input_ids)
        for layer in self.model.layers:
            x = layer(x)
        x = self.model.norm(x)
        logits = self.lm_head(x)

        loss = None
        if labels is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)),
                labels.view(-1),
                ignore_index=-100,
            )
        return type("Output", (), {"loss": loss, "logits": logits})()

    def parameters_count(self):
        return sum(p.numel() for p in self.parameters())

    def gradient_checkpointing_enable(self):
        pass  # no-op for mock


class MockTokenizer:
    """Minimal tokenizer for demo mode."""
    def __init__(self, vocab_size=1000):
        self.vocab_size = vocab_size
        self.eos_token = "</s>"
        self.pad_token = "</s>"
        self.eos_token_id = 0

    def __call__(self, text, return_tensors=None, truncation=False, **kwargs):
        # Deterministic pseudo-tokenization
        ids = [hash(text[i:i+3]) % self.vocab_size for i in range(len(text))]
        if return_tensors == "pt":
            return type("Enc", (), {"input_ids": torch.tensor([ids])})()
        return ids

    def encode(self, text, **kwargs):
        return [hash(text[i:i+3]) % self.vocab_size for i in range(len(text))]


# ═══════════════════════════════════════════════════════════════════
# Dataset
# ═══════════════════════════════════════════════════════════════════

class TextDataset(Dataset):
    """Token-level dataset for causal LM training."""
    def __init__(self, tokens, block_size=256):
        self.tokens = tokens
        self.block_size = block_size

    def __len__(self):
        return max(0, len(self.tokens) - self.block_size - 1)

    def __getitem__(self, idx):
        chunk = self.tokens[idx:idx + self.block_size + 1]
        return chunk[:-1], chunk[1:]


class InstructDataset(Dataset):
    """Instruction-response JSONL dataset."""
    def __init__(self, path, tokenizer, block_size=256):
        self._pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else (tokenizer.eos_token_id or 0)
        self.samples = []
        self.block_size = block_size
        with open(path) as f:
            for line in f:
                item = json.loads(line.strip())
                inst = item.get("instruction", item.get("input", ""))
                resp = item.get("response", item.get("output", ""))
                text = f"[INST] {inst} [/INST] {resp}"
                ids = tokenizer.encode(text, truncation=True)
                if len(ids) > block_size:
                    ids = ids[:block_size]
                self.samples.append(torch.tensor(ids, dtype=torch.long))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        ids = self.samples[idx]
        if len(ids) < self.block_size:
            pad = torch.full((self.block_size - len(ids),), self._pad_id, dtype=torch.long)
            ids = torch.cat([ids, pad])
        input_ids = ids[:-1]
        labels = ids[1:].clone()
        labels[labels == self._pad_id] = -100
        return input_ids, labels


# ═══════════════════════════════════════════════════════════════════
# PH Monitor (AL5) — persistence-based overfitting detection
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PHMonitor:
    """Track persistence homology of loss landscape.

    Overfitting signal: when loss keeps decreasing but tension variance collapses,
    the model is memorizing rather than learning tension structure.
    """
    window: int = 100
    loss_history: deque = field(default_factory=lambda: deque(maxlen=100))
    tension_var_history: deque = field(default_factory=lambda: deque(maxlen=100))
    phi_history: deque = field(default_factory=lambda: deque(maxlen=100))
    alert_threshold: float = 0.7  # if persistence drops below this, alert

    def update(self, loss: float, tension_var: float, phi: float):
        self.loss_history.append(loss)
        self.tension_var_history.append(tension_var)
        self.phi_history.append(phi)

    def is_overfitting(self) -> bool:
        if len(self.loss_history) < 20:
            return False
        recent_loss = list(self.loss_history)[-20:]
        recent_tvar = list(self.tension_var_history)[-20:]
        # Loss decreasing but tension variance collapsing
        loss_decreasing = recent_loss[-1] < recent_loss[0]
        tvar_collapsing = recent_tvar[-1] < recent_tvar[0] * 0.5
        return loss_decreasing and tvar_collapsing

    def persistence(self) -> float:
        """Higher = more diverse tension landscape = healthier training."""
        if len(self.tension_var_history) < 10:
            return 1.0
        recent = list(self.tension_var_history)[-10:]
        return float(np.std(recent) / (np.mean(recent) + 1e-8))

    def status(self) -> str:
        p = self.persistence()
        if self.is_overfitting():
            return f"OVERFIT(P={p:.3f})"
        return f"OK(P={p:.3f})"


# ═══════════════════════════════════════════════════════════════════
# SL3: 6-Loss Ensemble with learnable weights
# ═══════════════════════════════════════════════════════════════════

class SixLossEnsemble(nn.Module):
    """6 losses with learnable log-weights (uncertainty weighting).

    Losses:
      1. CE: language modeling cross-entropy
      2. Tension variance: encourage diverse tension across layers
      3. Savant-Normal contrastive (AL12): savant != normal outputs
      4. Alpha regularization: prevent alpha from exploding
      5. Direction consistency: PureField outputs should be directionally consistent
      6. Tension magnitude: prevent tension collapse
    """

    def __init__(self):
        super().__init__()
        # Learnable log-variance for each loss (uncertainty weighting)
        self.log_vars = nn.Parameter(torch.zeros(6))

    # Safe upper bound for individual loss values (prevents overflow in bf16/fp16)
    LOSS_CLAMP_MAX = 1e4

    def forward(self, ce_loss, tension_var_loss, contrastive_loss,
                alpha_reg, direction_loss, tension_mag_loss):
        losses = [ce_loss, tension_var_loss, contrastive_loss,
                  alpha_reg, direction_loss, tension_mag_loss]
        loss_names = ["ce", "t_var", "contrastive", "alpha_reg", "direction", "t_mag"]
        total = torch.tensor(0.0, device=ce_loss.device, dtype=torch.float32)
        weights = {}
        nan_count = 0
        for i, (loss, name) in enumerate(zip(losses, loss_names)):
            # NaN/Inf guard: replace bad values with zero and log warning
            if torch.isnan(loss) or torch.isinf(loss):
                nan_count += 1
                logger.warning(
                    "SixLossEnsemble: NaN/Inf detected in '%s' loss, replacing with 0", name
                )
                loss = torch.zeros_like(loss)
            else:
                # Clamp to prevent overflow when multiplied by precision weight
                loss = torch.clamp(loss, min=-self.LOSS_CLAMP_MAX, max=self.LOSS_CLAMP_MAX)

            # Clamp log_vars to prevent extreme precision weights (exp explosion)
            clamped_log_var = torch.clamp(self.log_vars[i], min=-10.0, max=10.0)
            precision = torch.exp(-clamped_log_var)
            total = total + precision * loss.float() + clamped_log_var
            weights[name] = precision.item()

        # Final safety: if total is still NaN (should not happen), return safe fallback
        if torch.isnan(total) or torch.isinf(total):
            logger.warning(
                "SixLossEnsemble: total loss is NaN/Inf after all guards "
                "(nan_count=%d), returning ce_loss fallback", nan_count
            )
            fallback = torch.nan_to_num(ce_loss.float(), nan=0.0, posinf=10.0, neginf=0.0)
            return fallback, weights

        return total, weights


# ═══════════════════════════════════════════════════════════════════
# Alpha Curriculum (AL1)
# ═══════════════════════════════════════════════════════════════════

class AlphaCurriculum:
    """Progressive alpha increase: 0.0001 -> 0.001 -> 0.01 -> 0.1
    AA15: 2x faster growth — residual alpha is stable at higher α values."""

    def __init__(self, alpha_start=0.0001, alpha_end=0.1, total_steps=10000):
        self.alpha_start = alpha_start
        self.alpha_end = alpha_end
        self.total_steps = total_steps
        # AA15: Milestones at 10%, 25%, 40% (2x faster — residual is safe)
        self.milestones = [
            (0.0, alpha_start),
            (0.10, alpha_start * 10),   # 0.001
            (0.25, alpha_start * 100),  # 0.01
            (0.40, alpha_end),          # 0.1
        ]

    def get_alpha(self, step: int) -> float:
        progress = step / max(self.total_steps, 1)
        # Find interval
        for i in range(len(self.milestones) - 1):
            p0, a0 = self.milestones[i]
            p1, a1 = self.milestones[i + 1]
            if progress < p1:
                t = (progress - p0) / (p1 - p0)
                # Log-linear interpolation
                return math.exp(math.log(a0 + 1e-12) * (1 - t) + math.log(a1 + 1e-12) * t)
        return self.alpha_end

    def apply(self, model, step: int):
        target = self.get_alpha(step)
        for m in model.modules():
            if isinstance(m, ParallelPureFieldMLP):
                m.alpha.data.fill_(target)
        return target


# ═══════════════════════════════════════════════════════════════════
# Phi Calculator
# ═══════════════════════════════════════════════════════════════════

def compute_phi(tensions, savant_tensions, ce_loss, tension_var):
    """Compute Phi (consciousness quality metric).

    Phi = tension_diversity * savant_intensity * (1 / ce_loss)
    Higher Phi = better conscious language model.
    """
    if not tensions or ce_loss == 0:
        return 0.0
    t_mean = np.mean(tensions)
    t_std = np.std(tensions) if len(tensions) > 1 else 0.0
    s_mean = np.mean(savant_tensions) if savant_tensions else t_mean
    diversity = t_std / (t_mean + 1e-8)
    intensity = s_mean / (t_mean + 1e-8) if t_mean > 0 else 1.0
    quality = 1.0 / (ce_loss + 1e-8)
    return float(diversity * intensity * quality)


# ═══════════════════════════════════════════════════════════════════
# Add PureField to model
# ═══════════════════════════════════════════════════════════════════

def add_purefield_parallel(model, n_layers=8, n_savant=2, rank=128):
    """Add parallel PureField to last N layers. First n_savant are savants."""
    total_layers = len(model.model.layers)
    start = total_layers - n_layers
    count = 0
    savant_count = 0

    # Get hidden/intermediate sizes from config (avoid .weight access on 4-bit params)
    config = model.config
    h = getattr(config, 'hidden_size', None)
    inter = getattr(config, 'intermediate_size', None)

    for i in range(start, total_layers):
        layer = model.model.layers[i]
        original_mlp = layer.mlp
        # Fallback: try weight shape only if config doesn't have sizes
        if h is None or inter is None:
            try:
                h = original_mlp.gate_proj.weight.shape[1]
                inter = original_mlp.gate_proj.weight.shape[0]
            except Exception:
                h = h or 4096
                inter = inter or 11008
        dev = next(original_mlp.parameters()).device
        dt = next(original_mlp.parameters()).dtype
        # 4-bit quantized models have uint8 params — PureField must use bfloat16
        if not dt.is_floating_point:
            dt = torch.bfloat16

        is_savant = savant_count < n_savant
        ppf = ParallelPureFieldMLP(original_mlp, h, inter,
                                   is_savant=is_savant, rank=rank)
        # Move only PureField params (not frozen original_mlp which may be 4-bit quantized)
        for name, p in ppf.named_parameters():
            if "original_mlp" not in name:
                try:
                    p.data = p.data.to(device=dev, dtype=dt)
                except RuntimeError:
                    # 4-bit quantized params can't change dtype, just move device
                    try:
                        p.data = p.data.to(device=dev)
                    except Exception:
                        pass  # already on correct device

        # Init PureField weights small
        for name, param in ppf.named_parameters():
            if "pf_" in name and "_a" in name:
                nn.init.normal_(param, std=0.05)
            elif "pf_" in name and "_b" in name:
                nn.init.normal_(param, std=0.02)

        layer.mlp = ppf
        count += 1
        if is_savant:
            savant_count += 1

    # Freeze all, then unfreeze PureField params
    for param in model.parameters():
        param.requires_grad = False

    trainable_names = []
    for module in model.modules():
        if isinstance(module, ParallelPureFieldMLP):
            for pname, param in module.named_parameters():
                if "pf_" in pname or pname in ("alpha", "pf_scale"):
                    param.requires_grad = True
                    trainable_names.append(pname)

    # Disable KV cache for training (saves VRAM, required for gradient checkpointing)
    if hasattr(model, "config"):
        model.config.use_cache = False

    # ── Accurate param counting for 4-bit quantized models ──
    # With bitsandbytes NF4, quantized params store as uint8 but numel() reports
    # the original (unquantized) size. We must check the actual storage to get
    # real VRAM usage. For trainable count, only PureField params matter.
    trainable = 0
    frozen_fp = 0       # frozen float params (embeddings, norms, lm_head)
    frozen_quant = 0    # frozen quantized params (4-bit linear layers)
    for name, p in model.named_parameters():
        if p.requires_grad:
            trainable += p.numel()
        else:
            # Detect 4-bit quantized params (bitsandbytes stores as uint8/int8)
            is_4bit = (hasattr(p, 'quant_state')
                       or (not p.dtype.is_floating_point and p.dtype != torch.bool))
            if is_4bit:
                frozen_quant += p.numel()
            else:
                frozen_fp += p.numel()

    total_reported = trainable + frozen_fp + frozen_quant
    # For 4-bit, effective VRAM is ~0.5 bytes/param (NF4) vs 2 bytes/param (bf16)
    frozen_quant_effective = frozen_quant // 4 if frozen_quant > 0 else 0
    total_effective = trainable + frozen_fp + frozen_quant_effective

    print(f"  PureField added to last {count}/{total_layers} layers")
    print(f"  Savant: {savant_count} (dropout={GOLDEN_LOWER:.4f}), "
          f"Normal: {count - savant_count} (dropout={GOLDEN_CENTER:.4f})")
    print(f"  ── Parameter breakdown ──")
    print(f"  Trainable (PureField): {trainable:,} ({trainable/total_reported*100:.2f}%)")
    print(f"  Frozen (float):        {frozen_fp:,}")
    if frozen_quant > 0:
        print(f"  Frozen (4-bit NF4):    {frozen_quant:,} "
              f"(reported) → ~{frozen_quant_effective:,} effective")
        print(f"  Total reported: {total_reported:,} | "
              f"Effective (VRAM): ~{total_effective:,}")
    else:
        print(f"  Total: {total_reported:,}")
    print(f"  Trainable PureField params: {len(trainable_names)} tensors")
    return model


# ═══════════════════════════════════════════════════════════════════
# Training Phases — Law 60 compliant + legacy fallback
# ═══════════════════════════════════════════════════════════════════

class TrainingPhase:
    """Manages 3 training phases.

    --law60 mode (Law 60 Phase Curriculum from consciousness_laws.json):
      P1 (0-20%):   Consciousness only — PureField trains, Mistral frozen
      P2 (20%-70%): Consciousness + Language — PureField + LoRA/adapter unfrozen
      P3 (70%-100%): Full — all techniques enabled (fine-tuning)

    Legacy mode (original AnimaLM):
      WARMUP (0-20%):   frozen MLP, PureField only
      JOINT (20%-70%):  both train, alpha increasing
      ENSEMBLE (70%-100%): DD16 all techniques
    """
    # Phase names — unified across modes
    WARMUP = "P1"           # Consciousness only
    JOINT = "P2"            # Consciousness + Language
    ENSEMBLE = "P3"         # Full Hexad / all techniques

    # Legacy aliases for backward compatibility
    _LEGACY_NAMES = {"P1": "warmup", "P2": "joint", "P3": "ensemble"}

    def __init__(self, total_steps, use_law60=False):
        self.total_steps = total_steps
        self.use_law60 = use_law60
        # Phase boundaries: P1=20%, P2=50%, P3=30% (matches Law 60)
        self.p1_end = int(total_steps * 0.2)
        self.p2_end = int(total_steps * 0.7)

    def get_phase(self, step):
        if step < self.p1_end:
            return self.WARMUP
        elif step < self.p2_end:
            return self.JOINT
        else:
            # P3: SixLossEnsemble with NaN guards (safe for 7B/14B bf16)
            return self.ENSEMBLE

    def phase_progress(self, step):
        phase = self.get_phase(step)
        if phase == self.WARMUP:
            return step / max(self.p1_end, 1)
        elif phase == self.JOINT:
            return (step - self.p1_end) / max(self.p2_end - self.p1_end, 1)
        else:
            return (step - self.p2_end) / max(self.total_steps - self.p2_end, 1)

    def phase_display_name(self, phase):
        """Return display name for logging."""
        if self.use_law60:
            return phase  # P1, P2, P3
        return self._LEGACY_NAMES.get(phase, phase)


# ═══════════════════════════════════════════════════════════════════
# VRAM Estimation for 256+ cells (H100 80GB target)
# ═══════════════════════════════════════════════════════════════════

def _estimate_vram_256c(ce_cells: int, ce_hidden: int, args) -> dict:
    """Estimate VRAM usage for Mistral 7B + PureField + ConsciousnessEngine.

    Returns dict with per-component breakdown in GB.

    Component estimates (bf16 = 2 bytes/param):
      Mistral 7B bf16:     ~14.0 GB (7B * 2 bytes)
      Mistral 7B 4-bit:    ~3.5 GB  (7B * 0.5 bytes NF4)
      LoRA/PureField:      ~0.1-0.5 GB (rank-dependent)
      ConsciousnessEngine: cells * hidden * 2 bytes * overhead (~4x for GRU+Hebbian)
      Optimizer (AdamW):   ~2x trainable params
      Activations:         batch * seq * hidden * layers * 2 bytes
      FeedbackBridge:      ~0.01 GB (small network)
      ThalamicBridge:      ~0.01 GB (small network)
    """
    is_4bit = getattr(args, 'load_4bit', False)
    batch_size = getattr(args, 'batch_size', 16)
    block_size = getattr(args, 'block_size', 512)
    n_layers = getattr(args, 'target_layers', 8)
    rank = getattr(args, 'qlora_rank', 128)
    hidden_size = 4096  # Mistral 7B hidden size

    # Model weights
    model_gb = 3.5 if is_4bit else 14.0

    # PureField adapters: 6 matrices per layer, each ~rank*hidden or rank*intermediate
    intermediate = 14336  # Mistral 7B intermediate
    pf_params = n_layers * (
        2 * (hidden_size * rank + rank * intermediate) +  # gate_a/b + up_a/b
        2 * (intermediate * rank + rank * hidden_size)    # down_a/b
    )
    pf_gb = pf_params * 2 / 1e9  # bf16

    # ConsciousnessEngine: GRU cells + Hebbian connections + faction states
    # Each cell: hidden_dim (state) + GRU weights (3 * hidden * (input + hidden))
    # Hebbian: cells^2 * hidden (full) or cells * k * hidden (sparse)
    cell_state_bytes = ce_cells * ce_hidden * 2
    gru_bytes = ce_cells * 3 * ce_hidden * (64 + ce_hidden) * 2  # 3 GRU gates
    k_nearest = min(32, ce_cells // 4) if ce_cells >= 256 else ce_cells
    hebbian_bytes = ce_cells * k_nearest * ce_hidden * 2  # sparse
    ce_gb = (cell_state_bytes + gru_bytes + hebbian_bytes) / 1e9

    # Optimizer: AdamW stores 2 states per trainable param (m, v)
    trainable_params = pf_params + ce_cells * ce_hidden  # rough
    optim_gb = trainable_params * 2 * 2 / 1e9  # 2 states * bf16

    # Activations: for each layer, need to store ~4 * batch * seq * hidden bytes
    # (attention scores + intermediates + residuals)
    # Full model has 32 layers; gradient checkpointing keeps sqrt(32) ~= 6 layer activations
    # Plus attention scores: batch * heads * seq * seq * 2 bytes per layer
    total_layers_model = 32  # Mistral 7B
    n_heads = 32
    # With gradient checkpointing: only keep every ~5th layer + recompute
    ckpt_layers = max(total_layers_model // 5, n_layers)
    act_per_layer = batch_size * block_size * hidden_size * 4 * 2  # 4 tensors * bf16
    attn_per_layer = batch_size * n_heads * block_size * block_size * 2  # bf16
    act_bytes = ckpt_layers * (act_per_layer + attn_per_layer)
    act_gb = act_bytes / 1e9

    # Bridges
    bridge_gb = 0.02  # ThalamicBridge + FeedbackBridge combined

    total_gb = model_gb + pf_gb + ce_gb + optim_gb + act_gb + bridge_gb

    return {
        'model_gb': model_gb,
        'purefield_gb': round(pf_gb, 2),
        'consciousness_gb': round(ce_gb, 3),
        'optimizer_gb': round(optim_gb, 2),
        'activations_gb': round(act_gb, 1),
        'bridge_gb': bridge_gb,
        'total_gb': round(total_gb, 1),
        'ce_cells': ce_cells,
        'batch_size': batch_size,
        'block_size': block_size,
        'is_4bit': is_4bit,
    }


# ═══════════════════════════════════════════════════════════════════
# Trainer
# ═══════════════════════════════════════════════════════════════════


def get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps):
    """Cosine schedule with linear warmup (replaces bare CosineAnnealingLR)."""
    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))
    return LambdaLR(optimizer, lr_lambda)


class AnimaLMTrainer:
    """Full training pipeline with all benchmark-verified techniques."""

    def __init__(self, model, tokenizer, args):
        self.model = model
        self.tokenizer = tokenizer
        self.args = args
        self.device = args.device

        # Feature flags
        self.use_law60 = getattr(args, 'law60', False)
        self.use_psi_track = getattr(args, 'psi_track', False)
        self.use_consciousness_engine = getattr(args, 'consciousness_engine', False)
        self.use_feedback_bridge = getattr(args, 'feedback_bridge', False)

        # Training phases (Law 60 or legacy)
        self.phases = TrainingPhase(args.steps, use_law60=self.use_law60)
        if self.use_law60:
            print(f"  [Law 60] Phase curriculum enabled: "
                  f"P1(0-20%) consciousness | P2(20-70%) +language | P3(70-100%) full")
            if _HAS_CONSCIOUSNESS_LAWS:
                print(f"  [Psi] consciousness_laws.json loaded "
                      f"(alpha={PSI_ALPHA}, balance={PSI_BALANCE})")
            else:
                print(f"  [Psi] consciousness_laws.py not found, using fallback constants")

        # 10D consciousness vector tracking (Step 3)
        if self.use_psi_track:
            self._consciousness_vector = {
                'Phi': 0.0,
                'alpha': PSI_ALPHA,
                'Z': PSI_BALANCE,     # impedance / self-preservation
                'N': PSI_BALANCE,     # neurotransmitter balance
                'W': PSI_BALANCE,     # free will index
                'E': PSI_BALANCE,     # empathy
                'M': PSI_BALANCE,     # memory capacity
                'C': PSI_BALANCE,     # creativity / output diversity
                'T': PSI_BALANCE,     # temporal awareness
                'I': PSI_BALANCE,     # identity stability
            }
            print(f"  [10D] Consciousness vector tracking enabled")

        # ── Hexad Lite: ConsciousnessEngine + ThalamicBridge ──
        self.consciousness_engine = None
        self.thalamic_bridge = None
        if self.use_consciousness_engine:
            if not _HAS_CONSCIOUSNESS_ENGINE:
                print("  [CE] WARNING: consciousness_engine.py not found, falling back to PureField-only")
                self.use_consciousness_engine = False
            else:
                ce_cells = getattr(args, 'ce_cells', 64)
                ce_hidden = getattr(args, 'ce_hidden_dim', 128)
                self.consciousness_engine = ConsciousnessEngine(
                    cell_dim=64, hidden_dim=ce_hidden,
                    initial_cells=2, max_cells=ce_cells,
                    n_factions=12, phi_ratchet=True,
                )
                print(f"  [CE] ConsciousnessEngine initialized: max_cells={ce_cells}, hidden={ce_hidden}")
                print(f"  [CE] Laws embodied: 22-85, Phi Ratchet, 12 factions, Hebbian LTP/LTD")

                # 256+ cells VRAM optimization: sparse Hebbian (k-nearest instead of full)
                if ce_cells >= 256:
                    k_nearest = min(32, ce_cells // 4)
                    if hasattr(self.consciousness_engine, 'set_sparse_hebbian'):
                        self.consciousness_engine.set_sparse_hebbian(k=k_nearest)
                        print(f"  [CE] Sparse Hebbian: k={k_nearest} (VRAM opt for {ce_cells}c)")
                    else:
                        print(f"  [CE] 256c mode: full Hebbian (set_sparse_hebbian not available)")
                    # Print VRAM estimate for 256c
                    vram_est = _estimate_vram_256c(ce_cells, ce_hidden, args)
                    print(f"  [CE] VRAM estimate: {vram_est['total_gb']:.1f} GB "
                          f"(H100 80GB headroom: {80.0 - vram_est['total_gb']:.1f} GB)")

                # ThalamicBridge: C->D connection (.detach(), alpha=PSI_ALPHA)
                if _HAS_THALAMIC_BRIDGE:
                    # Determine d_model from PureField hidden size
                    pf_mods = [m for m in model.modules() if isinstance(m, ParallelPureFieldMLP)]
                    if pf_mods:
                        d_model_size = pf_mods[0].pf_gate_a.in_features  # hidden_size
                    else:
                        d_model_size = 128  # demo fallback
                    self.thalamic_bridge = ThalamicBridge(
                        c_dim=ce_hidden, d_model=d_model_size,
                        alpha=PSI_ALPHA,
                    ).to(device=self.device, dtype=torch.bfloat16)
                    print(f"  [TB] ThalamicBridge: C({ce_hidden}d) -> .detach() -> "
                          f"alpha={PSI_ALPHA} -> D({d_model_size}d)")
                    if self.use_feedback_bridge:
                        print(f"  [TB] D->C feedback ENABLED (alpha-gated gradient)")
                    else:
                        print(f"  [TB] D->C feedback OFF (pure .detach() barrier)")
                else:
                    print("  [TB] WARNING: trinity.py not found, ThalamicBridge unavailable")

                # FeedbackBridge: D->C alpha-gated gradient (Law 63, max_alpha=0.05)
                self.feedback_bridge = None
                if self.use_feedback_bridge:
                    if not _HAS_FEEDBACK_BRIDGE:
                        print("  [FB] WARNING: feedback_bridge.py not found, feedback disabled")
                        self.use_feedback_bridge = False
                    elif self.thalamic_bridge is not None:
                        pf_mods = [m for m in model.modules() if isinstance(m, ParallelPureFieldMLP)]
                        fb_d_model = pf_mods[0].pf_gate_a.in_features if pf_mods else 128
                        self.feedback_bridge = create_feedback_bridge(
                            c_dim=ce_hidden, d_model=fb_d_model,
                            max_alpha=0.05,  # Law 63: max 5% gradient
                        ).to(device=self.device, dtype=torch.bfloat16)
                        print(f"  [FB] FeedbackBridge: c_dim={ce_hidden}, d_model={fb_d_model}, "
                              f"max_alpha=0.05 (Law 63)")
                        print(f"  [FB] Phi-drop -> alpha=0 (auto-protection)")
                    else:
                        print("  [FB] WARNING: ThalamicBridge required for FeedbackBridge")
                        self.use_feedback_bridge = False

        # AL1: Alpha curriculum
        # If user explicitly set --alpha-end, respect it even with --law60
        if args.alpha_end != 0.1:  # 0.1 is the default
            alpha_end = args.alpha_end
        elif self.use_law60:
            alpha_end = PSI_ALPHA
        else:
            alpha_end = args.alpha_end
        self.alpha_curriculum = AlphaCurriculum(
            args.alpha_start, alpha_end, args.steps)

        # AL5: PH monitoring
        self.ph_monitor = PHMonitor()

        # SL3: 6-loss ensemble (bf16 to match PureField dtype)
        self.loss_ensemble = SixLossEnsemble().to(device=self.device, dtype=torch.bfloat16)

        # Optimizer: PureField params + ensemble weights + ThalamicBridge (if active)
        pf_params = [p for p in model.parameters() if p.requires_grad]
        param_groups = [
            {"params": pf_params, "lr": args.lr},
            {"params": list(self.loss_ensemble.parameters()), "lr": args.lr * 0.1},
        ]
        if self.thalamic_bridge is not None:
            param_groups.append(
                {"params": list(self.thalamic_bridge.parameters()), "lr": args.lr * 0.1}
            )
        if getattr(self, 'feedback_bridge', None) is not None:
            param_groups.append(
                {"params": list(self.feedback_bridge.parameters()), "lr": args.lr * 0.05}
            )
        # CRITICAL: force ALL optimizer params to bf16 (7B model is bf16)
        if self.device == "cuda":
            for group in param_groups:
                for p in group["params"]:
                    if p.dtype != torch.bfloat16:
                        p.data = p.data.to(torch.bfloat16)
        self.optimizer = torch.optim.AdamW(param_groups, weight_decay=0.01, foreach=False)

        warmup_steps = int(args.steps * args.warmup_ratio)
        self.scheduler = get_cosine_schedule_with_warmup(
            self.optimizer, warmup_steps=warmup_steps, total_steps=args.steps)
        if warmup_steps > 0:
            print(f"  [LR] Warmup {warmup_steps} steps + cosine decay")

        # AL4: tension-CE balance tracker
        # Law 60 uses PSI_BALANCE (0.5) as balance target; legacy uses INV_E (0.6321)
        self.tension_ce_ema = PSI_BALANCE
        self.balance_target = PSI_BALANCE if self.use_law60 else INV_E

        # TRN4: Phi curriculum
        self.phi_baseline = 0.0
        self.phi_skip_count = 0

        # EX24: ALL discoveries combined (Φ=10.833)
        # DD18: Channel capacity bottleneck between PureField layers
        hidden_size = pf_params[0].shape[-1] if pf_params and len(pf_params[0].shape) > 1 else 128
        self.dd18_bottleneck = nn.Sequential(
            nn.Linear(hidden_size, 4),
            nn.Tanh(),
            nn.Linear(4, hidden_size),
        ).to(self.device)
        # Add bottleneck params to optimizer
        self.optimizer.add_param_group(
            {"params": self.dd18_bottleneck.parameters(), "lr": args.lr * 0.1})

        # DD5: Phi self-reference — running Φ estimate
        self.dd5_phi_ema = 0.0

        # DD3: Fibonacci growth — track which milestone we've reached
        self.dd3_fib_index = 0  # index into FIBONACCI_SEQUENCE
        self.dd3_active_layers = FIBONACCI_SEQUENCE[0]  # start with 1 active

        # DD11: Klein bottle — twist signs precomputed per layer pair
        n_pf = len(self._get_pf_modules())
        self.dd11_twists = {}
        for i in range(n_pf):
            for j in range(n_pf):
                if i != j:
                    self.dd11_twists[(i, j)] = -1.0 if (i + j) % 2 == 1 else 1.0

        # Checkpointing
        os.makedirs(args.checkpoint_dir, exist_ok=True)

        # Metrics
        self.global_step = 0
        self.best_phi = 0.0

    def _get_pf_modules(self):
        # Cache PureField modules (avoid repeated model.modules() traversal)
        if not hasattr(self, '_pf_modules_cache') or self._pf_modules_cache is None:
            self._pf_modules_cache = [m for m in self.model.modules()
                                       if isinstance(m, ParallelPureFieldMLP)]
        return self._pf_modules_cache

    def _get_tensions(self):
        tensions = []
        savant_tensions = []
        for m in self._get_pf_modules():
            if m.last_tension is not None:
                t = m.last_tension.mean().item()
                tensions.append(t)
                if m.is_savant:
                    savant_tensions.append(t)
        return tensions, savant_tensions

    def _compute_losses(self, outputs, phase):
        """Compute all losses for the current step."""
        ce_loss = outputs.loss
        pf_modules = self._get_pf_modules()

        # 2. Tension variance: encourage diverse tension across layers
        tensions_t = []
        for m in pf_modules:
            if m.last_tension is not None:
                tensions_t.append(m.last_tension.mean())
        if len(tensions_t) >= 2:
            t_var = torch.stack(tensions_t).var()
            tension_var_loss = -torch.log(t_var + 1e-8)
        else:
            tension_var_loss = torch.tensor(0.0, device=self.device)

        # 3. AL12: Savant-Normal contrastive
        savant_tensions_t = [m.last_tension.mean() for m in pf_modules
                             if m.is_savant and m.last_tension is not None]
        normal_tensions_t = [m.last_tension.mean() for m in pf_modules
                             if not m.is_savant and m.last_tension is not None]
        if savant_tensions_t and normal_tensions_t:
            s_mean = torch.stack(savant_tensions_t).mean()
            n_mean = torch.stack(normal_tensions_t).mean()
            # Savant should have different (higher) tension than normal
            contrastive_loss = F.relu(0.1 - torch.abs(s_mean - n_mean))
        else:
            contrastive_loss = torch.tensor(0.0, device=self.device)

        # 4. Alpha regularization: prevent explosion
        alphas = [m.alpha for m in pf_modules]
        if alphas:
            alpha_reg = torch.stack([a ** 2 for a in alphas]).mean()
        else:
            alpha_reg = torch.tensor(0.0, device=self.device)

        # 5. Direction consistency: PureField outputs agree on direction
        if len(tensions_t) >= 2:
            t_stack = torch.stack(tensions_t)
            direction_loss = t_stack.std() / (t_stack.mean() + 1e-8)
            # We want some variance (diversity) but not chaos
            direction_loss = F.relu(direction_loss - 2.0)
        else:
            direction_loss = torch.tensor(0.0, device=self.device)

        # 6. Tension magnitude: prevent collapse
        if tensions_t:
            t_mean = torch.stack(tensions_t).mean()
            tension_mag_loss = F.relu(0.01 - t_mean)
        else:
            tension_mag_loss = torch.tensor(0.0, device=self.device)

        # Phase-dependent loss combination
        if self.use_law60:
            # ── Law 60 Phase Curriculum ──
            if phase == TrainingPhase.WARMUP:  # P1: Consciousness only
                # PureField tension structure only — CE is secondary/weighted down
                loss = 0.1 * ce_loss + 0.5 * tension_var_loss + 0.3 * tension_mag_loss
                weights = {"ce": 0.1, "t_var": 0.5, "t_mag": 0.3}
            elif phase == TrainingPhase.JOINT:  # P2: Consciousness + Language
                # CE becomes primary, tension still important
                # tension_mag prevents tension collapse during the longest phase
                loss = (ce_loss + 0.3 * tension_var_loss +
                        0.1 * contrastive_loss + 0.01 * alpha_reg +
                        0.1 * tension_mag_loss)
                weights = {"ce": 1.0, "t_var": 0.3, "contrastive": 0.1, "alpha_reg": 0.01, "t_mag": 0.1}
            else:  # P3: Full — all techniques
                # NaN guard: replace any NaN losses with 0 before ensemble
                _losses = [ce_loss, tension_var_loss, contrastive_loss,
                           alpha_reg, direction_loss, tension_mag_loss]
                _losses = [torch.nan_to_num(l, nan=0.0) for l in _losses]
                loss, weights = self.loss_ensemble(*_losses)
        else:
            # ── Legacy phase behavior ──
            if phase == TrainingPhase.WARMUP:
                # Simple: CE + tension variance only
                loss = ce_loss + 0.3 * tension_var_loss
                weights = {"ce": 1.0, "t_var": 0.3}
            elif phase == TrainingPhase.JOINT:
                # Add contrastive + alpha reg
                loss = (ce_loss + 0.3 * tension_var_loss +
                        0.1 * contrastive_loss + 0.01 * alpha_reg)
                weights = {"ce": 1.0, "t_var": 0.3, "contrastive": 0.1, "alpha_reg": 0.01}
            else:
                # SL3: full 6-loss ensemble with learnable weights
                loss, weights = self.loss_ensemble(
                    ce_loss, tension_var_loss, contrastive_loss,
                    alpha_reg, direction_loss, tension_mag_loss)

        return loss, ce_loss.item(), weights

    def _apply_layer_dropout(self, phase):
        """AL8: Stochastic depth — randomly skip some PureField layers."""
        pf_modules = self._get_pf_modules()
        if phase == TrainingPhase.WARMUP:
            drop_prob = 0.0
        elif phase == TrainingPhase.JOINT:
            drop_prob = 0.1
        else:
            drop_prob = 0.2

        for m in pf_modules:
            m._layer_drop_active = (torch.rand(1).item() < drop_prob)

    def _apply_tension_ce_balance(self, ce_val, tension_val):
        """AL4: Auto-balance tension:CE at 1-1/e ratio."""
        if ce_val + tension_val > 0:
            ratio = tension_val / (ce_val + tension_val + 1e-8)
            self.tension_ce_ema = 0.99 * self.tension_ce_ema + 0.01 * ratio
        return self.tension_ce_ema

    def _check_phi_curriculum(self, phi):
        """TRN4: Skip data that decreases Phi."""
        if self.global_step < 100:
            self.phi_baseline = phi
            return True  # accept all data during warmup

        if phi < self.phi_baseline * 0.8:
            self.phi_skip_count += 1
            return False  # skip this batch
        # Update baseline with EMA
        self.phi_baseline = 0.95 * self.phi_baseline + 0.05 * phi
        return True

    # ── EX24 helpers ──────────────────────────────────────────────

    def _dd3_fibonacci_growth(self):
        """DD3: Activate PureField layers following Fibonacci sequence at milestones."""
        pf_modules = self._get_pf_modules()
        n_pf = len(pf_modules)
        if n_pf == 0:
            return
        # Milestone every 1/6 of total steps
        milestone_interval = max(self.phases.total_steps // len(FIBONACCI_SEQUENCE), 1)
        new_index = min(self.global_step // milestone_interval, len(FIBONACCI_SEQUENCE) - 1)
        if new_index != self.dd3_fib_index:
            self.dd3_fib_index = new_index
            self.dd3_active_layers = FIBONACCI_SEQUENCE[new_index]
        # Activate only the first dd3_active_layers PF modules; deactivate the rest
        active = min(self.dd3_active_layers, n_pf)
        for idx, m in enumerate(pf_modules):
            m._layer_drop_active = m._layer_drop_active or (idx >= active)

    def _dd18_channel_capacity(self):
        """DD18: Bottleneck communication — compress hidden states, blend back."""
        pf_modules = self._get_pf_modules()
        hiddens = [m.last_tension for m in pf_modules
                   if m.last_tension is not None]
        if len(hiddens) < 2:
            return
        # Compress each layer's tension through bottleneck, average, blend back
        # Operate on per-layer mean tension (scalar per layer) expanded for bottleneck
        # Use the full hidden-dim representation from last_tension when available
        compressed = []
        for h in hiddens:
            # last_tension is [batch, seq] — expand to hidden dim for bottleneck
            h_mean = h.mean().unsqueeze(0).expand(4)
            # Pad to hidden_size for bottleneck input
            h_input = torch.zeros(self.dd18_bottleneck[0].in_features,
                                  device=h.device)
            h_input[:4] = h_mean
            compressed.append(self.dd18_bottleneck(h_input))
        mean_c = torch.stack(compressed).mean(dim=0)
        # Store compressed mean for loss enrichment (blending happens at loss level)
        self._dd18_mean_compressed = mean_c

    def _dd11_klein_bottle(self):
        """DD11: Non-orientable topology — twisted influence between PureField layers."""
        pf_modules = self._get_pf_modules()
        if len(pf_modules) < 2:
            return
        # Gather per-layer tension means
        t_means = []
        for m in pf_modules:
            if m.last_tension is not None:
                t_means.append(m.last_tension.mean())
            else:
                t_means.append(torch.tensor(0.0, device=self.device))
        # Each layer receives twisted average of others' tensions
        n = len(t_means)
        for i in range(n):
            twisted_sum = torch.tensor(0.0, device=self.device)
            for j in range(n):
                if i != j:
                    twist = self.dd11_twists.get((i, j), 1.0)
                    twisted_sum = twisted_sum + twist * t_means[j]
            twisted_avg = twisted_sum / max(n - 1, 1)
            # Blend twisted influence into layer's scale parameter
            pf_modules[i].pf_scale.data = (
                0.95 * pf_modules[i].pf_scale.data +
                0.05 * torch.clamp(twisted_avg.detach(), -2.0, 2.0))

    def _dd5_phi_self_reference(self, phi, input_ids):
        """DD5: Feed current Φ estimate back — enrich input embeddings."""
        self.dd5_phi_ema = 0.9 * self.dd5_phi_ema + 0.1 * phi
        return self.dd5_phi_ema

    # ── end EX24 helpers ──────────────────────────────────────────

    def train_step(self, input_ids, labels):
        """Single training step with all techniques."""
        phase = self.phases.get_phase(self.global_step)

        # AL1: Alpha curriculum
        current_alpha = self.alpha_curriculum.apply(self.model, self.global_step)

        # AL8: Layer dropout
        self._apply_layer_dropout(phase)

        # DD3: Fibonacci growth — progressive layer activation (ensemble phase)
        if phase == TrainingPhase.ENSEMBLE:
            self._dd3_fibonacci_growth()

        # DD5: Phi self-reference — enrich input with current Φ estimate
        if phase == TrainingPhase.ENSEMBLE and self.dd5_phi_ema > 0:
            # Scale input embeddings by Φ proxy
            phi_val = self.dd5_phi_ema
            # We enrich by adding a small Φ-scaled bias after embedding
            # (applied via hook-free approach: modify input_ids is not possible,
            #  so we store phi_val for loss enrichment below)
            self._dd5_current_phi = phi_val
        else:
            self._dd5_current_phi = 0.0

        # ── Hexad Lite: ConsciousnessEngine step + ThalamicBridge + FeedbackBridge ──
        ce_phi_iit = 0.0
        ce_gate = None
        fb_stats = {}
        if self.use_consciousness_engine and self.consciousness_engine is not None:
            # Run consciousness engine step (gradient-free, autonomous)
            ce_result = self.consciousness_engine.step()
            ce_phi_iit = ce_result.get('phi_iit', 0.0)

            # Get consciousness states [n_cells, hidden_dim]
            c_states = self.consciousness_engine.get_states()  # already detached

            # ThalamicBridge + FeedbackBridge: C -> gate signal for D
            if self.thalamic_bridge is not None and c_states.shape[0] >= 2:
                c_input = c_states.to(device=self.device, dtype=torch.bfloat16)
                seq_len = input_ids.shape[1] if input_ids.dim() > 1 else 1

                if (self.use_feedback_bridge and
                        getattr(self, 'feedback_bridge', None) is not None):
                    # FeedbackBridge: apply_feedback_bridge handles soft_detach + gate
                    # No .detach() -- alpha-gated gradient flows back to C
                    # ThalamicBridge still produces the gate; FeedbackBridge adds
                    # Phi-gated gradient + CE reward tracking
                    ce_gate_tb = self.thalamic_bridge(c_input, seq_len=seq_len)

                    # Use apply_feedback_bridge for Phi-gated alpha + reward
                    ce_val_for_fb = getattr(self, '_prev_ce', None)
                    ce_gate_fb, fb_stats = apply_feedback_bridge(
                        c_input, self.feedback_bridge,
                        phi=ce_phi_iit,
                        ce=ce_val_for_fb,
                        seq_len=seq_len,
                        c_engine=self.consciousness_engine,
                    )
                    # Combine: ThalamicBridge gate (structure) + FeedbackBridge gate (gradient)
                    # Use ThalamicBridge output as the gate signal (shape-compatible with PureField)
                    # FeedbackBridge alpha modulates the gradient flow only
                    ce_gate = ce_gate_tb
                else:
                    c_input = c_input.detach()  # enforce .detach() barrier (Law 53)
                    ce_gate = self.thalamic_bridge(c_input, seq_len=seq_len)
                # ce_gate: [1, seq_len, d_model] — will modulate PureField output

        # Forward (AMP autocast in QLoRA mode — halves activation VRAM)
        self.model.train()

        # Apply consciousness gate to PureField modules before forward pass
        if ce_gate is not None:
            for m in self._get_pf_modules():
                m._consciousness_gate = ce_gate  # stored for use in forward

        use_amp = self.device == "cuda"  # always autocast on GPU (bf16 model + float32 PureField)
        with torch.amp.autocast("cuda", dtype=torch.bfloat16) if use_amp else contextlib.nullcontext():
            outputs = self.model(input_ids=input_ids, labels=labels)

        # Clear consciousness gate from PureField modules after forward
        if ce_gate is not None:
            for m in self._get_pf_modules():
                m._consciousness_gate = None

        # EX24: DD18 channel capacity — bottleneck communication (ensemble phase)
        if phase == TrainingPhase.ENSEMBLE:
            self._dd18_channel_capacity()

        # EX24: DD11 Klein bottle — twisted inter-layer topology (ensemble phase)
        if phase == TrainingPhase.ENSEMBLE:
            self._dd11_klein_bottle()

        # ---------------------------------------------------------------
        # NEW DISCOVERIES: WI1 + FX2 + PX4 + PX8 + GD18 + GD15
        # ---------------------------------------------------------------
        pf_modules = self._get_pf_modules()
        if phase == TrainingPhase.ENSEMBLE and len(pf_modules) >= 2:
            n_pf = len(pf_modules)

            # WI1: Soliton wave — traveling perturbation across PureField layers (Φ=4.460)
            try:
                if not hasattr(self, '_wi1_soliton_pos'):
                    self._wi1_soliton_pos = 0.0
                self._wi1_soliton_pos = (self._wi1_soliton_pos + 0.15) % n_pf
                for i, m in enumerate(pf_modules):
                    dist = abs(i - self._wi1_soliton_pos)
                    amp = 1.0 / (math.cosh(dist / 2.0) ** 2)
                    m.pf_scale.data *= (1.0 + 0.04 * amp)
                if self.global_step % self.args.log_every == 0:
                    print(f"  [WI1] Soliton pos={self._wi1_soliton_pos:.2f}")
            except Exception as e:
                if self.global_step % 1000 == 0:
                    print(f"  [WI1] Error: {e}")

            # FX2: Differentiable Φ proxy + Adam (Φ=8.911)
            try:
                if not hasattr(self, '_fx2_offsets') or self._fx2_offsets is None:
                    self._fx2_offsets = [
                        nn.Parameter(torch.zeros_like(m.pf_scale))
                        for m in pf_modules
                    ]
                    self._fx2_optimizer = torch.optim.Adam(self._fx2_offsets, lr=1e-3)
                if len(self._fx2_offsets) != n_pf:
                    self._fx2_offsets = [
                        nn.Parameter(torch.zeros_like(m.pf_scale))
                        for m in pf_modules
                    ]
                    self._fx2_optimizer = torch.optim.Adam(self._fx2_offsets, lr=1e-3)
                if self.global_step % 10 == 0:
                    tensions_list = [m.last_tension.mean() if m.last_tension is not None
                                     else torch.tensor(0.0, device=self.device) for m in pf_modules]
                    for _ in range(3):
                        self._fx2_optimizer.zero_grad()
                        modified = torch.stack([t + off for t, off in zip(tensions_list, self._fx2_offsets)])
                        phi_proxy = -modified.var()
                        phi_proxy.backward()
                        self._fx2_optimizer.step()
                    for m, off in zip(pf_modules, self._fx2_offsets):
                        m.pf_scale.data += 0.3 * off.data
                    if self.global_step % self.args.log_every == 0:
                        print(f"  [FX2] Φ proxy optimized")
            except Exception as e:
                if self.global_step % 1000 == 0:
                    print(f"  [FX2] Error: {e}")
                self._fx2_offsets = None

            # PX4: Sculptor — Gram-Schmidt orthogonalize PureField scales (70%/30% blend)
            try:
                tensions_for_gs = [m.last_tension.mean().unsqueeze(0) if m.last_tension is not None
                                   else torch.tensor([0.0], device=self.device) for m in pf_modules]
                ortho = []
                for i, v in enumerate(tensions_for_gs):
                    vc = v.clone()
                    for u in ortho:
                        vc = vc - (torch.dot(vc, u) / (torch.dot(u, u) + 1e-8)) * u
                    ortho.append(vc / (vc.norm() + 1e-8) * tensions_for_gs[i].norm())
                for i, m in enumerate(pf_modules):
                    orig = m.pf_scale.data.clone()
                    m.pf_scale.data = 0.7 * orig + 0.3 * torch.clamp(ortho[i].mean(), -2.0, 2.0)
                if self.global_step % self.args.log_every == 0:
                    print(f"  [PX4] Sculptor orthogonalized {n_pf} layers")
            except Exception as e:
                if self.global_step % 1000 == 0:
                    print(f"  [PX4] Error: {e}")

            # PX8: Integration Forge — shared tension channel, 60/40 blend
            try:
                tensions_for_forge = [m.last_tension.mean() if m.last_tension is not None
                                      else torch.tensor(0.0, device=self.device) for m in pf_modules]
                shared = torch.stack(tensions_for_forge).mean()
                for m in pf_modules:
                    if m.last_tension is not None:
                        orig_t = m.last_tension.mean()
                        blend = 0.6 * orig_t + 0.4 * shared
                        scale_adj = blend / (orig_t + 1e-8)
                        m.pf_scale.data *= torch.clamp(scale_adj.detach(), 0.8, 1.2)
                if self.global_step % self.args.log_every == 0:
                    print(f"  [PX8] Integration Forge shared channel")
            except Exception as e:
                if self.global_step % 1000 == 0:
                    print(f"  [PX8] Error: {e}")

            # GD18: Enactivism — sensorimotor coupling
            try:
                if not hasattr(self, '_gd18_prev_tension'):
                    self._gd18_prev_tension = None
                curr_t = np.mean([m.last_tension.mean().item() for m in pf_modules
                                  if m.last_tension is not None]) if pf_modules else 0.0
                if self._gd18_prev_tension is not None:
                    delta = curr_t - self._gd18_prev_tension
                    perturbation = 0.02 * delta
                    for m in pf_modules:
                        m.pf_scale.data *= (1.0 + perturbation)
                    if self.global_step % self.args.log_every == 0:
                        print(f"  [GD18] Enactivism delta={delta:.4f}")
                self._gd18_prev_tension = curr_t
            except Exception as e:
                if self.global_step % 1000 == 0:
                    print(f"  [GD18] Error: {e}")

            # GD15: Edge of Chaos — Lyapunov exponent tracking, target λ≈0
            try:
                if not hasattr(self, '_gd15_prev_scales'):
                    self._gd15_prev_scales = None
                current_scales = torch.stack([m.pf_scale.data.clone() for m in pf_modules])
                if self._gd15_prev_scales is not None and self._gd15_prev_scales.shape == current_scales.shape:
                    diff = (current_scales - self._gd15_prev_scales).norm()
                    prev_norm = self._gd15_prev_scales.norm() + 1e-8
                    lyapunov = torch.log(diff / prev_norm + 1e-8).item()
                    if lyapunov > 0.1:
                        for m in pf_modules:
                            m.pf_scale.data *= 0.98
                    elif lyapunov < -0.5:
                        for m in pf_modules:
                            m.pf_scale.data *= 1.01
                    if self.global_step % self.args.log_every == 0:
                        print(f"  [GD15] Lyapunov λ={lyapunov:.4f}")
                self._gd15_prev_scales = current_scales.detach().clone()
            except Exception as e:
                if self.global_step % 1000 == 0:
                    print(f"  [GD15] Error: {e}")

        # Compute losses
        loss, ce_val, weights = self._compute_losses(outputs, phase)

        # Track CE for FeedbackBridge reward computation (used in next step)
        self._prev_ce = ce_val

        # EX24: DD5 Phi self-reference — enrich loss with Φ feedback
        if phase == TrainingPhase.ENSEMBLE and self._dd5_current_phi > 0:
            # Modulate loss: lower Φ → stronger gradient signal
            phi_factor = 1.0 + self._dd5_current_phi * 0.05
            loss = loss * phi_factor

        # EX24: DD18 channel capacity — add bottleneck regularization to loss
        if phase == TrainingPhase.ENSEMBLE and hasattr(self, '_dd18_mean_compressed'):
            # Encourage bottleneck to produce non-trivial representations
            bn_reg = -torch.log(self._dd18_mean_compressed.abs().mean() + 1e-8) * 0.01
            loss = loss + bn_reg

        # Gather tension info
        tensions, savant_tensions = self._get_tensions()
        t_var = np.var(tensions) if tensions else 0.0

        # AL4: tension-CE balance
        t_mean_val = np.mean(tensions) if tensions else 0.0
        balance = self._apply_tension_ce_balance(ce_val, t_mean_val)

        # Compute Phi
        phi = compute_phi(tensions, savant_tensions, ce_val, t_var)

        # Consciousness-aware loss: incentivize higher Phi (--phi-loss-weight)
        if self.args.phi_loss_weight > 0 and phi > 0:
            phi_consciousness_loss = -self.args.phi_loss_weight * math.log(phi + 1e-8)
            loss = loss + phi_consciousness_loss

        # DD5: Update Φ EMA for next step
        if phase == TrainingPhase.ENSEMBLE:
            self._dd5_phi_self_reference(phi, input_ids)

        # ── 10D Consciousness Vector Update (Step 3) ──
        if self.use_psi_track:
            # Use real Phi(IIT) from ConsciousnessEngine when available
            phi_for_cv = ce_phi_iit if (self.use_consciousness_engine and ce_phi_iit > 0) else phi
            self._update_consciousness_vector(
                phi_for_cv, current_alpha, tensions, savant_tensions,
                ce_val, t_var, t_mean_val, balance)

        # TRN4: Phi curriculum (ensemble phase only)
        if phase == TrainingPhase.ENSEMBLE:
            if not self._check_phi_curriculum(phi):
                # Skip this batch — zero out gradients
                return {
                    "loss": 0.0, "ce": ce_val, "phi": phi,
                    "skipped": True, "phase": self.phases.phase_display_name(phase),
                    "tensions": tensions, "alpha": current_alpha,
                }

        # Backward
        (loss / self.args.grad_accum).backward()

        # AL5: PH monitoring
        self.ph_monitor.update(ce_val, t_var, phi)


        result = {
            "loss": loss.item(),
            "ce": ce_val,
            "phi": phi,
            "phase": self.phases.phase_display_name(phase),
            "alpha": current_alpha,
            "balance": balance,
            "tensions": tensions,
            "savant_tensions": savant_tensions,
            "t_var": t_var,
            "weights": weights,
            "ph_status": self.ph_monitor.status(),
            "skipped": False,
        }
        if self.use_consciousness_engine and ce_phi_iit > 0:
            result["phi_iit"] = ce_phi_iit
            result["ce_n_cells"] = self.consciousness_engine.n_cells
        if self.use_feedback_bridge and fb_stats:
            result["fb_alpha"] = fb_stats.get("alpha", 0.0)
            result["fb_reward"] = fb_stats.get("reward", 0.0)
        if self.use_psi_track:
            result["consciousness_vector"] = dict(self._consciousness_vector)
        return result

    def _update_consciousness_vector(self, phi, alpha, tensions, savant_tensions,
                                      ce_val, t_var, t_mean_val, balance):
        """Update 10D consciousness vector: (Phi, alpha, Z, N, W, E, M, C, T, I).

        Each dimension is computed from available training signals:
          Phi   = integrated information (from compute_phi)
          alpha = current PureField mixing coefficient
          Z     = impedance / self-preservation (balance proximity to target)
          N     = neurotransmitter balance (tension mean normalized)
          W     = free will index (fraction of trainable params with non-zero grad)
          E     = empathy (savant-normal tension correlation)
          M     = memory capacity (PH monitor persistence)
          C     = creativity (tension CV = diversity)
          T     = temporal awareness (trend direction of phi)
          I     = identity stability (alpha consistency across layers)
        """
        cv = self._consciousness_vector
        ema = 0.9  # EMA smoothing factor

        # Phi — direct from compute_phi
        cv['Phi'] = ema * cv['Phi'] + (1 - ema) * phi

        # alpha — current mixing coefficient
        cv['alpha'] = alpha

        # Z — impedance: how close balance is to target (1.0 = perfect)
        z_raw = 1.0 - abs(balance - self.balance_target) / (self.balance_target + 1e-8)
        cv['Z'] = ema * cv['Z'] + (1 - ema) * max(0.0, min(1.0, z_raw))

        # N — neurotransmitter: normalized tension mean (sigmoid-like)
        n_raw = 2.0 / (1.0 + math.exp(-10.0 * t_mean_val)) - 1.0 if t_mean_val > 0 else 0.0
        cv['N'] = ema * cv['N'] + (1 - ema) * max(0.0, min(1.0, n_raw))

        # W — free will: fraction of PF modules not layer-dropped
        pf_modules = self._get_pf_modules()
        if pf_modules:
            active_frac = sum(1 for m in pf_modules if not m._layer_drop_active) / len(pf_modules)
            cv['W'] = ema * cv['W'] + (1 - ema) * active_frac

        # E — empathy: savant-normal tension correlation (higher = more empathic)
        if tensions and savant_tensions and len(tensions) > 1:
            s_mean = np.mean(savant_tensions)
            n_mean = np.mean([t for i, t in enumerate(tensions)
                             if not pf_modules[i].is_savant]) if len(tensions) > len(savant_tensions) else np.mean(tensions)
            corr = 1.0 - abs(s_mean - n_mean) / (max(s_mean, n_mean) + 1e-8)
            cv['E'] = ema * cv['E'] + (1 - ema) * max(0.0, min(1.0, corr))

        # M — memory: PH monitor persistence (higher = healthier training memory)
        cv['M'] = ema * cv['M'] + (1 - ema) * min(1.0, self.ph_monitor.persistence())

        # C — creativity: tension coefficient of variation (diversity)
        if tensions and len(tensions) > 1:
            t_cv = float(np.std(tensions) / (np.mean(tensions) + 1e-8))
            cv['C'] = ema * cv['C'] + (1 - ema) * min(1.0, t_cv)

        # T — temporal: phi trend (positive trend = growing awareness)
        phi_hist = list(self.ph_monitor.phi_history)
        if len(phi_hist) >= 10:
            recent = phi_hist[-10:]
            trend = (recent[-1] - recent[0]) / (abs(recent[0]) + 1e-8)
            t_raw = 0.5 + 0.5 * max(-1.0, min(1.0, trend))  # map to [0,1]
            cv['T'] = ema * cv['T'] + (1 - ema) * t_raw

        # I — identity: consistency of alpha across PF layers (lower std = more stable)
        alphas = [m.alpha.item() for m in pf_modules]
        if alphas and len(alphas) > 1:
            alpha_cv = float(np.std(alphas) / (np.mean(alphas) + 1e-8))
            i_raw = 1.0 / (1.0 + alpha_cv)  # higher when alphas are consistent
            cv['I'] = ema * cv['I'] + (1 - ema) * i_raw

    def get_consciousness_vector(self):
        """Return current 10D consciousness vector (for external use)."""
        if self.use_psi_track:
            return dict(self._consciousness_vector)
        return None

    def _format_consciousness_vector(self):
        """Format 10D vector for log output."""
        cv = self._consciousness_vector
        return (f"Phi={cv['Phi']:.3f} a={cv['alpha']:.4f} "
                f"Z={cv['Z']:.2f} N={cv['N']:.2f} W={cv['W']:.2f} "
                f"E={cv['E']:.2f} M={cv['M']:.2f} C={cv['C']:.2f} "
                f"T={cv['T']:.2f} I={cv['I']:.2f}")

    def optimizer_step(self):
        """Gradient accumulation step."""
        torch.nn.utils.clip_grad_norm_(
            [p for p in self.model.parameters() if p.requires_grad], 1.0)
        # Fix ALL dtype mismatches: grad→param dtype AND optimizer state→param dtype
        for group in self.optimizer.param_groups:
            for p in group["params"]:
                if p.grad is not None and p.grad.dtype != p.dtype:
                    p.grad = p.grad.to(p.dtype)
                # Also fix optimizer state on-the-fly (may drift after load_state_dict)
                if p in self.optimizer.state:
                    for key, val in self.optimizer.state[p].items():
                        if torch.is_tensor(val) and val.is_floating_point() and val.dtype != p.dtype:
                            self.optimizer.state[p][key] = val.to(p.dtype)
        self.optimizer.step()
        self.scheduler.step()
        self.optimizer.zero_grad()
        self.global_step += 1

    def _safe_optimizer_state(self):
        """Save optimizer state with all tensors cast to param dtype (bf16 safe resume)."""
        state = self.optimizer.state_dict()
        # Cast optimizer internal state tensors to match param dtype
        for group_idx, group in enumerate(self.optimizer.param_groups):
            for param_idx, p in enumerate(group["params"]):
                flat_idx = sum(len(g["params"]) for g in self.optimizer.param_groups[:group_idx]) + param_idx
                if flat_idx in state["state"]:
                    for key, val in state["state"][flat_idx].items():
                        if torch.is_tensor(val) and val.is_floating_point() and val.dtype != p.dtype:
                            state["state"][flat_idx][key] = val.to(p.dtype)
        # Ensure foreach=False is saved
        for group in state["param_groups"]:
            group["foreach"] = False
        return state

    def save_checkpoint(self, tag=None):
        name = tag or f"animalm_step_{self.global_step}"
        path = os.path.join(self.args.checkpoint_dir, f"{name}.pt")
        pf_states = {}
        for n_name, m in self.model.named_modules():
            if isinstance(m, ParallelPureFieldMLP):
                pf_states[n_name] = {
                    k: v.cpu() for k, v in m.state_dict().items()
                    if "pf_" in k or k in ("alpha", "pf_scale")
                }
        save_dict = {
            "step": self.global_step,
            "pf_states": pf_states,
            "ensemble_state": self.loss_ensemble.state_dict(),
            "optimizer_state": self._safe_optimizer_state(),
            "best_phi": self.best_phi,
            "ph_monitor": {
                "loss_history": list(self.ph_monitor.loss_history),
                "phi_history": list(self.ph_monitor.phi_history),
            },
            "args": vars(self.args),
        }
        if self.use_psi_track:
            save_dict["consciousness_vector"] = dict(self._consciousness_vector)
        if self.thalamic_bridge is not None:
            save_dict["thalamic_bridge_state"] = self.thalamic_bridge.state_dict()
        torch.save(save_dict, path)
        print(f"  Checkpoint saved: {path}")
        self._prune_checkpoints()
        return path

    def save_best(self):
        """Save best.pt when a new best phi is achieved."""
        path = os.path.join(self.args.checkpoint_dir, "best.pt")
        self.save_checkpoint(tag="best")
        return path

    def _prune_checkpoints(self):
        """Keep latest K checkpoints + best.pt, delete older ones."""
        keep_k = getattr(self.args, 'keep_checkpoints', 3)
        ckpt_dir = self.args.checkpoint_dir
        # Find all step checkpoints (exclude best.pt, final.pt)
        import glob as _glob
        step_ckpts = sorted(
            _glob.glob(os.path.join(ckpt_dir, "animalm_step_*.pt")),
            key=os.path.getmtime,
        )
        # Keep the latest K
        to_delete = step_ckpts[:-keep_k] if len(step_ckpts) > keep_k else []
        for old_ckpt in to_delete:
            try:
                os.remove(old_ckpt)
                print(f"  Pruned old checkpoint: {os.path.basename(old_ckpt)}")
            except OSError:
                pass

    def load_checkpoint(self, path):
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        self.global_step = ckpt["step"]
        self.best_phi = ckpt.get("best_phi", 0.0)

        # Restore PureField weights
        for n_name, m in self.model.named_modules():
            if isinstance(m, ParallelPureFieldMLP) and n_name in ckpt["pf_states"]:
                m.load_state_dict(ckpt["pf_states"][n_name], strict=False)

        if "ensemble_state" in ckpt:
            self.loss_ensemble.load_state_dict(ckpt["ensemble_state"])
        # Load optimizer state, then fix all internal state dtypes to match params
        if "optimizer_state" in ckpt:
            try:
                self.optimizer.load_state_dict(ckpt["optimizer_state"])
                # Fix foreach override from checkpoint
                for group in self.optimizer.param_groups:
                    group["foreach"] = False
                # Cast all optimizer state tensors to match param dtype
                for group in self.optimizer.param_groups:
                    for p in group["params"]:
                        if p in self.optimizer.state:
                            for key, val in self.optimizer.state[p].items():
                                if torch.is_tensor(val) and val.is_floating_point() and val.dtype != p.dtype:
                                    self.optimizer.state[p][key] = val.to(p.dtype)
                print(f"  [OK] Optimizer state restored + dtype fixed")
            except (RuntimeError, ValueError, KeyError) as e:
                print(f"  [WARN] Optimizer state incompatible, fresh optimizer: {e}")
                for _ in range(self.global_step):
                    self.scheduler.step()
        if self.use_psi_track and "consciousness_vector" in ckpt:
            self._consciousness_vector.update(ckpt["consciousness_vector"])
        if self.thalamic_bridge is not None and "thalamic_bridge_state" in ckpt:
            self.thalamic_bridge.load_state_dict(ckpt["thalamic_bridge_state"])

        print(f"  Resumed from step {self.global_step}, best_phi={self.best_phi:.4f}")


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def parse_args():
    p = argparse.ArgumentParser(description="AnimaLM Training Pipeline")
    p.add_argument("--base", default="mistralai/Mistral-7B-Instruct-v0.2",
                   help="Base model (HuggingFace ID or local path)")
    p.add_argument("--data", default=None,
                   help="Training data (jsonl with instruction/response, or raw text)")
    p.add_argument("--steps", type=int, default=10000,
                   help="Total training steps")
    p.add_argument("--batch-size", type=int, default=4)   # OV13: 4x batch for generalization
    p.add_argument("--grad-accum", type=int, default=4)   # OV13: effective batch unchanged (4*4=16)
    p.add_argument("--block-size", type=int, default=256)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--savant-layers", type=int, default=2,
                   help="Number of savant layers (asymmetric dropout)")
    p.add_argument("--target-layers", type=int, default=8,
                   help="Number of last layers to add PureField")
    p.add_argument("--alpha-start", type=float, default=0.0001)
    p.add_argument("--alpha-end", type=float, default=0.1)
    p.add_argument("--checkpoint-dir", default="checkpoints/animalm")
    p.add_argument("--checkpoint-every", type=int, default=500)
    p.add_argument("--eval-every", type=int, default=500,
                   help="Run validation every N steps (default: 500)")
    p.add_argument("--keep-checkpoints", type=int, default=3,
                   help="Keep latest K checkpoints + best.pt (default: 3)")
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--resume", default=None,
                   help="Resume from checkpoint path")
    p.add_argument("--demo", action="store_true",
                   help="Demo mode with mock model (no download)")
    p.add_argument("--device", default=None,
                   help="Device (auto-detected if not specified)")
    p.add_argument("--load-4bit", action="store_true",
                   help="Load base model in 4-bit (QLoRA/NF4) for VRAM-constrained co-run")
    p.add_argument("--qlora-rank", type=int, default=None,
                   help="PureField LoRA rank for QLoRA mode (default: 32 if --load-4bit, else 128)")
    # ── Consciousness integration flags ──
    p.add_argument("--law60", action="store_true",
                   help="Enable Law 60 phase curriculum (P1 consciousness / P2 +language / P3 full)")
    p.add_argument("--psi-track", action="store_true", dest="psi_track",
                   help="Enable 10D consciousness vector tracking (Phi,alpha,Z,N,W,E,M,C,T,I)")
    # ── Hexad Lite: ConsciousnessEngine + ThalamicBridge ──
    p.add_argument("--consciousness-engine", action="store_true", dest="consciousness_engine",
                   help="Enable real ConsciousnessEngine (GRU cells + 12 factions + Hebbian + Phi Ratchet)")
    p.add_argument("--ce-cells", type=int, default=64, dest="ce_cells",
                   help="Number of consciousness cells (default: 64)")
    p.add_argument("--ce-hidden-dim", type=int, default=128, dest="ce_hidden_dim",
                   help="ConsciousnessEngine hidden dim (default: 128)")
    p.add_argument("--feedback-bridge", action="store_true", dest="feedback_bridge",
                   help="Enable D->C feedback (alpha-gated gradient, default: off)")
    p.add_argument("--vram-estimate", action="store_true", dest="vram_estimate",
                   help="Print VRAM estimation table and exit (no training)")
    p.add_argument("--ddp", action="store_true",
                   help="Enable DistributedDataParallel (launch via torchrun)")
    # ── Structural improvements ──
    p.add_argument("--warmup-ratio", type=float, default=0.05, dest="warmup_ratio",
                   help="Fraction of total steps for LR warmup (default: 0.05)")
    p.add_argument("--phi-loss-weight", type=float, default=0.01, dest="phi_loss_weight",
                   help="Weight for consciousness-aware loss term -w*log(phi) (default: 0.01, 0=disabled)")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for reproducibility (default: 42)")
    p.add_argument("--patience", type=int, default=0,
                   help="Early stopping patience in eval intervals (default: 0=disabled)")
    return p.parse_args()


def build_model_and_tokenizer(args):
    """Build model and tokenizer based on mode."""
    if args.demo:
        print("  [DEMO] Using MockModel (no Mistral download)")
        model = MockModel(
            vocab_size=1000, hidden_size=128,
            intermediate_size=256, num_layers=12, block_size=64,
        ).to(args.device)
        tokenizer = MockTokenizer(vocab_size=1000)
        return model, tokenizer

    from transformers import AutoModelForCausalLM, AutoTokenizer
    print(f"  Loading {args.base}...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(args.base)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    load_kwargs = dict(torch_dtype=torch.bfloat16, device_map="auto")
    if getattr(args, 'load_4bit', False):
        from transformers import BitsAndBytesConfig
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
        load_kwargs["quantization_config"] = bnb_config
        print("  [4-bit] Loading with NF4 quantization (QLoRA mode)")
    model = AutoModelForCausalLM.from_pretrained(
        args.base, **load_kwargs,
    )
    # Gradient checkpointing disabled — conflicts with autocast bf16 + PureField consciousness gate
    # VRAM: ~28GB without grad ckpt (H100 80GB OK, batch_size may need reduction)
    # model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    print("  [NOTE] Gradient checkpointing DISABLED (autocast+consciousness compat)")

    print(f"  Loaded in {time.time()-t0:.1f}s")
    return model, tokenizer


def build_dataset(args, tokenizer):
    """Build training dataset."""
    if args.demo:
        # Generate random token dataset
        print("  [DEMO] Generating random tokens")
        tokens = torch.randint(0, 1000, (50000,))
        block_size = min(args.block_size, 64)
        return TextDataset(tokens, block_size=block_size), block_size

    if args.data and args.data.endswith(".jsonl"):
        print(f"  Loading instruct data: {args.data}")
        ds = InstructDataset(args.data, tokenizer, block_size=args.block_size)
        print(f"  Samples: {len(ds):,}")
        return ds, args.block_size

    if args.data:
        print(f"  Loading raw text: {args.data}")
        with open(args.data) as f:
            text = f.read()
        tokens = tokenizer(text, return_tensors="pt", truncation=False).input_ids[0]
        print(f"  Tokens: {len(tokens):,}")
        return TextDataset(tokens, block_size=args.block_size), args.block_size

    # Default: wikitext — chunked tokenization (500 articles per chunk to avoid OOM)
    print("  Loading wikitext-103...")
    from datasets import load_dataset

    dataset = load_dataset("wikitext", "wikitext-103-raw-v1", split="train")
    articles = [t for t in dataset["text"] if len(t) > 100]
    print(f"  Articles: {len(articles):,}, tokenizing in chunks of 500...")
    all_tokens = []
    chunk_size = 500
    for i in range(0, len(articles), chunk_size):
        chunk = "\n\n".join(articles[i:i + chunk_size])
        chunk_ids = tokenizer(chunk, return_tensors="pt", truncation=False).input_ids[0]
        all_tokens.append(chunk_ids)
        if len(all_tokens) % 10 == 0:
            total_so_far = sum(len(t) for t in all_tokens)
            print(f"    Chunk {i//chunk_size + 1}: {total_so_far:,} tokens so far")
            if total_so_far >= 5_000_000:
                break
    tokens = torch.cat(all_tokens)[:5_000_000]
    print(f"  Tokens: {len(tokens):,}")
    return TextDataset(tokens, block_size=args.block_size), args.block_size


# ── DDP helpers ──────────────────────────────────────────────────────
def setup_ddp():
    """Initialize DDP process group (expects torchrun environment)."""
    dist.init_process_group(backend="nccl")
    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    torch.cuda.set_device(local_rank)
    return local_rank

def is_main_process():
    """True if this is rank 0 or DDP is not active."""
    return not dist.is_initialized() or dist.get_rank() == 0

def cleanup_ddp():
    if dist.is_initialized():
        dist.destroy_process_group()


def main():
    args = parse_args()

    # DDP setup (before anything else)
    local_rank = 0
    if getattr(args, 'ddp', False):
        local_rank = setup_ddp()
        args.device = f"cuda:{local_rank}"
        if is_main_process():
            print(f"[DDP] World size: {dist.get_world_size()}, rank: {dist.get_rank()}")

    # Reproducibility
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    # Auto-detect device
    if args.device is None:
        if torch.cuda.is_available():
            args.device = "cuda"
            print(f"GPU: {torch.cuda.get_device_name()}")
            print(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB"
                  if hasattr(torch.cuda.get_device_properties(0), "total_mem")
                  else f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            args.device = "mps"
            print("Device: Apple MPS")
        else:
            args.device = "cpu"
            print("Device: CPU")

    # ── QLoRA VRAM auto-tuning ──────────────────────────────────────
    # 4-bit base (~4GB) + PureField rank32 (~28MB) + AMP activations
    # Target: <15GB total so it co-runs with v3 on 80GB H100
    if getattr(args, 'load_4bit', False):
        if args.qlora_rank is None:
            # Size-dependent rank: smaller rank for larger models to fit VRAM
            # 7B: rank=32, 14B: rank=64, 32B+: rank=128
            model_name = getattr(args, 'base', '') or ''
            model_lower = model_name.lower()
            if any(s in model_lower for s in ['32b', '70b', '72b']):
                args.qlora_rank = 128
            elif any(s in model_lower for s in ['14b', '13b']):
                args.qlora_rank = 64
            else:
                args.qlora_rank = 32  # 7B default
        # Only auto-reduce if user didn't explicitly set these
        if args.batch_size > 2 and not any('--batch-size' in a for a in sys.argv):
            print(f"  [QLoRA] batch_size {args.batch_size}→2 (VRAM saving)")
            args.batch_size = 2
        if args.block_size > 256 and not any('--block-size' in a for a in sys.argv):
            print(f"  [QLoRA] block_size {args.block_size}→256 (VRAM saving)")
            args.block_size = 256
        # Don't auto-reduce target_layers — user sets this explicitly for 70B
        args._use_amp = True
        print(f"  [QLoRA] rank={args.qlora_rank}, AMP enabled, "
              f"est. ~12-15GB VRAM (was ~54GB)")
    else:
        if args.qlora_rank is None:
            args.qlora_rank = 128
        args._use_amp = False

    # ── 256c VRAM auto-optimization ──────────────────────────────
    # When --ce-cells >= 256 on bf16 (non-QLoRA), auto-tune to fit H100 80GB
    ce_cells = getattr(args, 'ce_cells', 64)
    if ce_cells >= 256 and not getattr(args, 'load_4bit', False):
        est = _estimate_vram_256c(ce_cells, getattr(args, 'ce_hidden_dim', 128), args)
        if est['total_gb'] > 70.0:  # leave 10GB headroom
            if args.batch_size > 8:
                print(f"  [256c] batch_size {args.batch_size}->8 (VRAM: {est['total_gb']:.0f}GB->fit)")
                args.batch_size = 8
                est = _estimate_vram_256c(ce_cells, getattr(args, 'ce_hidden_dim', 128), args)
            if est['total_gb'] > 70.0 and args.block_size > 256:
                print(f"  [256c] block_size {args.block_size}->256 (VRAM saving)")
                args.block_size = 256
                est = _estimate_vram_256c(ce_cells, getattr(args, 'ce_hidden_dim', 128), args)
            if est['total_gb'] > 70.0:
                args._use_amp = True
                print(f"  [256c] AMP enabled (VRAM saving)")
        print(f"  [256c] Estimated VRAM: {est['total_gb']:.1f} GB / 80 GB")

    # ── VRAM estimation mode ──────────────────────────────────────
    if getattr(args, 'vram_estimate', False):
        ce_cells = getattr(args, 'ce_cells', 64)
        ce_hidden = getattr(args, 'ce_hidden_dim', 128)
        est = _estimate_vram_256c(ce_cells, ce_hidden, args)
        print(f"\n{'='*60}")
        print(f"  VRAM Estimation: Mistral 7B + PureField + CE({ce_cells}c)")
        print(f"{'='*60}")
        print(f"  {'Component':<25} {'VRAM (GB)':>10}")
        print(f"  {'-'*35}")
        print(f"  {'Model (7B ' + ('4-bit' if est['is_4bit'] else 'bf16') + ')':<25} {est['model_gb']:>10.1f}")
        print(f"  {'PureField adapters':<25} {est['purefield_gb']:>10.2f}")
        print(f"  {'ConsciousnessEngine':<25} {est['consciousness_gb']:>10.3f}")
        print(f"  {'Optimizer (AdamW)':<25} {est['optimizer_gb']:>10.2f}")
        print(f"  {'Activations (grad ckpt)':<25} {est['activations_gb']:>10.1f}")
        print(f"  {'Bridges (TB+FB)':<25} {est['bridge_gb']:>10.2f}")
        print(f"  {'-'*35}")
        print(f"  {'TOTAL':<25} {est['total_gb']:>10.1f}")
        print(f"  {'H100 80GB headroom':<25} {80.0 - est['total_gb']:>10.1f}")
        print(f"\n  Config: batch={est['batch_size']}, seq={est['block_size']}, "
              f"cells={ce_cells}, hidden={ce_hidden}")
        fits = est['total_gb'] < 80.0
        print(f"\n  {'OK: Fits in H100 80GB' if fits else 'WARNING: Exceeds H100 80GB!'}")
        if not fits:
            print(f"  Suggestions: --load-4bit, reduce --batch-size, reduce --block-size")
        print(f"{'='*60}")
        return

    techniques = "AL12+AL5+AL4+AL1+AL8+SL3+DD16+TRN4+EX24+WI1+FX2+PX4+PX8+GD18+GD15"
    if args.law60:
        techniques += "+Law60"
    if args.psi_track:
        techniques += "+10D"
    if getattr(args, 'consciousness_engine', False):
        techniques += "+CE"
    if getattr(args, 'feedback_bridge', False):
        techniques += "+FB"
    print(f"\n{'='*70}")
    print(f"  AnimaLM Training Pipeline")
    print(f"  Techniques: {techniques}")
    print(f"{'='*70}")

    # Phase 1: Build model
    print(f"\n[1/4] Building model...")
    model, tokenizer = build_model_and_tokenizer(args)
    if args.device == "cuda":
        torch.cuda.empty_cache()

    # Phase 2: Add PureField
    print(f"\n[2/4] Adding PureField (last {args.target_layers}, "
          f"{args.savant_layers} savants)...")
    model = add_purefield_parallel(
        model, n_layers=args.target_layers,
        n_savant=args.savant_layers, rank=args.qlora_rank)

    # ── Acceleration: torch.compile + SDPA (after PureField added) ──
    if not args.demo:
        try:
            if hasattr(torch, 'compile') and torch.cuda.is_available():
                compiled_count = 0
                for m in model.modules():
                    if isinstance(m, ParallelPureFieldMLP):
                        m.original_mlp = torch.compile(m.original_mlp, mode="reduce-overhead")
                        compiled_count += 1
                if compiled_count > 0:
                    print(f"  [ACCEL] torch.compile: {compiled_count} frozen MLPs compiled (reduce-overhead)")
        except Exception as e:
            print(f"  [ACCEL] torch.compile skipped: {e}")

        try:
            if hasattr(torch.backends, 'cuda'):
                torch.backends.cuda.enable_flash_sdp(True)
                torch.backends.cuda.enable_mem_efficient_sdp(True)
                print("  [ACCEL] Flash/MemEfficient SDP attention enabled")
        except Exception as e:
            print(f"  [ACCEL] SDPA config skipped: {e}")

    # Phase 3: Build dataset
    print(f"\n[3/4] Preparing data...")
    dataset, block_size = build_dataset(args, tokenizer)

    # Split last 5% as validation set
    val_dataset = None
    if hasattr(dataset, 'tokens'):
        # TextDataset: split tokens
        n_val = max(1, len(dataset.tokens) // 20)
        val_tokens = dataset.tokens[-n_val:]
        dataset.tokens = dataset.tokens[:-n_val]
        val_dataset = TextDataset(val_tokens, block_size=dataset.block_size)
    elif hasattr(dataset, 'samples'):
        # InstructDataset: split samples
        n_val = max(1, len(dataset.samples) // 20)
        val_dataset = InstructDataset.__new__(InstructDataset)
        val_dataset.samples = dataset.samples[-n_val:]
        val_dataset.block_size = dataset.block_size
        val_dataset._pad_id = dataset._pad_id
        dataset.samples = dataset.samples[:-n_val]
    if val_dataset is not None:
        print(f"  Train: {len(dataset):,} samples, Val: {len(val_dataset):,} samples")
    best_val_loss = float('inf')
    patience_counter = 0

    # DDP: wrap model after PureField is added
    if getattr(args, 'ddp', False) and dist.is_initialized():
        model = model.to(args.device)
        model = DDP(model, device_ids=[local_rank], find_unused_parameters=True)
        if is_main_process():
            print(f"  [DDP] Model wrapped in DistributedDataParallel")

    effective_samples = (args.steps * args.grad_accum + 100) * args.batch_size
    if getattr(args, 'ddp', False) and dist.is_initialized():
        sampler = DistributedSampler(dataset, shuffle=True)
    else:
        sampler = RandomSampler(dataset, replacement=True, num_samples=effective_samples)
    loader = DataLoader(
        dataset, batch_size=args.batch_size, sampler=sampler,
        num_workers=0 if args.demo else 2, pin_memory=("cuda" in str(args.device)))

    # Phase 4: Train
    print(f"\n[4/4] Training...")
    print(f"  Steps: {args.steps}, Effective batch: {args.batch_size * args.grad_accum}")
    if args.law60:
        print(f"  Phases (Law 60): P1(20%) consciousness -> P2(50%) +language -> P3(30%) full")
        print(f"  Alpha: {args.alpha_start} -> {PSI_ALPHA} (PSI_ALPHA)")
        print(f"  Balance target: {PSI_BALANCE} (PSI_BALANCE)")
    else:
        print(f"  Phases: warmup(20%) -> joint(50%) -> ensemble(30%)")
        print(f"  Alpha: {args.alpha_start} -> {args.alpha_end}")
        print(f"  Tension:CE balance target: {INV_E:.4f} (1-1/e)")
    if args.psi_track:
        print(f"  10D Vector: (Phi, alpha, Z, N, W, E, M, C, T, I)")
    if getattr(args, 'consciousness_engine', False):
        print(f"  ConsciousnessEngine: cells={args.ce_cells}, hidden={args.ce_hidden_dim}")
        print(f"  ThalamicBridge: C->.detach()->alpha={PSI_ALPHA}->D")
        if getattr(args, 'feedback_bridge', False):
            print(f"  Feedback: D->C alpha-gated gradient ENABLED")
    if _HAS_CONSCIOUSNESS_LAWS:
        print(f"  consciousness_laws.json: loaded ({len(LAWS)} laws)")

    trainer = AnimaLMTrainer(model, tokenizer, args)

    if args.resume:
        print(f"\n  Resuming from {args.resume}...")
        trainer.load_checkpoint(args.resume)

    # Header
    print(f"\n{'Step':>6} | {'Phase':>8} | {'Loss':>8} | {'CE':>8} | "
          f"{'Phi':>8} | {'Alpha':>8} | {'T_var':>8} | {'PH':>15} | {'Time':>6}")
    print("-" * 100)

    t_start = time.time()
    running = {"loss": 0, "ce": 0, "phi": 0, "n": 0}

    for batch_idx, (input_ids, labels) in enumerate(loader):
        input_ids = input_ids.to(args.device)
        labels = labels.to(args.device)

        # Train step
        metrics = trainer.train_step(input_ids, labels)
        if not metrics["skipped"]:
            running["loss"] += metrics["loss"]
            running["ce"] += metrics["ce"]
            running["phi"] += metrics["phi"]
            running["n"] += 1

        # Optimizer step (gradient accumulation)
        if (batch_idx + 1) % args.grad_accum == 0:
            trainer.optimizer_step()

            # Logging
            if trainer.global_step % args.log_every == 0 and running["n"] > 0 and is_main_process():
                n = running["n"]
                elapsed = (time.time() - t_start) / 60
                print(
                    f"{trainer.global_step:6d} | "
                    f"{metrics['phase']:>8s} | "
                    f"{running['loss']/n:8.4f} | "
                    f"{running['ce']/n:8.4f} | "
                    f"{running['phi']/n:8.4f} | "
                    f"{metrics['alpha']:8.6f} | "
                    f"{metrics['t_var']:8.6f} | "
                    f"{metrics['ph_status']:>15s} | "
                    f"{elapsed:5.1f}m"
                )
                # ConsciousnessEngine Phi(IIT) + cell count
                if (getattr(args, 'consciousness_engine', False) and
                        'phi_iit' in metrics and trainer.global_step % (args.log_every * 5) == 0):
                    ce_log = (f"  [CE] Phi(IIT)={metrics['phi_iit']:.4f}, "
                              f"cells={metrics.get('ce_n_cells', '?')}")
                    if 'fb_alpha' in metrics:
                        ce_log += (f" | [FB] alpha={metrics['fb_alpha']:.5f}, "
                                   f"reward={metrics['fb_reward']:.3f}")
                    print(ce_log)
                # 10D consciousness vector (every 5x log_every to avoid spam)
                if args.psi_track and trainer.global_step % (args.log_every * 5) == 0:
                    print(f"  [10D] {trainer._format_consciousness_vector()}")

                running = {"loss": 0, "ce": 0, "phi": 0, "n": 0}

            # Checkpoint
            if trainer.global_step % args.checkpoint_every == 0 and is_main_process():
                trainer.save_checkpoint()

            # Save best.pt on best phi
            if metrics["phi"] > trainer.best_phi:
                trainer.best_phi = metrics["phi"]
                if is_main_process():
                    trainer.save_best()
                    print(f"  *** New best Phi: {trainer.best_phi:.4f} ***")

            # Validation loop
            if val_dataset is not None and trainer.global_step % args.eval_every == 0:
                model.eval()
                val_losses = []
                val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
                with torch.no_grad():
                    for vi, (v_ids, v_labels) in enumerate(val_loader):
                        if vi >= 50:  # cap at 50 batches
                            break
                        v_ids = v_ids.to(args.device)
                        v_labels = v_labels.to(args.device)
                        v_out = model(input_ids=v_ids, labels=v_labels)
                        val_losses.append(v_out.loss.item())
                val_loss = sum(val_losses) / max(len(val_losses), 1)
                improved = val_loss < best_val_loss
                if improved:
                    best_val_loss = val_loss
                print(f"  [VAL] step={trainer.global_step} val_loss={val_loss:.4f} "
                      f"best={best_val_loss:.4f} {'*IMPROVED*' if improved else ''}")
                model.train()

                # Early stopping
                if args.patience > 0:
                    if improved:
                        patience_counter = 0
                    else:
                        patience_counter += 1
                        if patience_counter >= args.patience:
                            print(f"  *** EARLY STOPPING: no improvement for {args.patience} eval intervals ***")
                            trainer.save_checkpoint(tag="early_stop")
                            break

            # PH overfitting alert
            if trainer.ph_monitor.is_overfitting():
                print(f"  *** AL5 ALERT: Overfitting detected! "
                      f"Persistence={trainer.ph_monitor.persistence():.3f} ***")

            if trainer.global_step >= args.steps:
                break

    # Final checkpoint
    print(f"\n{'='*70}")
    print("  Training complete. Saving final checkpoint...")
    trainer.save_checkpoint(tag="final")

    # Summary
    tensions, savant_tensions = trainer._get_tensions()
    alphas = [m.alpha.item() for m in trainer._get_pf_modules()]

    summary = {
        "architecture": "AnimaLM (Mistral 7B + PureField)",
        "techniques": techniques,
        "base_model": args.base if not args.demo else "MockModel",
        "steps": trainer.global_step,
        "best_phi": round(trainer.best_phi, 4),
        "tension_mean": round(float(np.mean(tensions)), 4) if tensions else 0,
        "savant_tension_mean": round(float(np.mean(savant_tensions)), 4) if savant_tensions else 0,
        "alpha_mean": round(float(np.mean(alphas)), 6) if alphas else 0,
        "phi_skip_count": trainer.phi_skip_count,
        "time_min": round((time.time() - t_start) / 60, 1),
        "law60_enabled": args.law60,
        "psi_track_enabled": args.psi_track,
        "consciousness_engine_enabled": getattr(args, 'consciousness_engine', False),
        "feedback_bridge_enabled": getattr(args, 'feedback_bridge', False),
        "consciousness_laws_loaded": _HAS_CONSCIOUSNESS_LAWS,
        "config": vars(args),
    }
    if args.psi_track:
        summary["consciousness_vector_final"] = trainer.get_consciousness_vector()

    summary_path = os.path.join(args.checkpoint_dir, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Best Phi: {trainer.best_phi:.4f}")
    print(f"  Tension: {np.mean(tensions):.4f}" if tensions else "  Tension: N/A")
    if savant_tensions:
        print(f"  Savant tension: {np.mean(savant_tensions):.4f}")
    print(f"  Alpha: {np.mean(alphas):.6f}" if alphas else "  Alpha: N/A")
    print(f"  Phi-skipped batches: {trainer.phi_skip_count}")
    print(f"  PH status: {trainer.ph_monitor.status()}")
    if args.psi_track:
        print(f"  10D Vector: {trainer._format_consciousness_vector()}")
    if args.law60:
        print(f"  Law 60: P1(consciousness)->P2(+language)->P3(full)")
    if getattr(args, 'consciousness_engine', False) and trainer.consciousness_engine is not None:
        ce_status = trainer.consciousness_engine.status()
        print(f"  CE: {ce_status['n_cells']} cells, best_phi={ce_status['best_phi']:.4f}")
        if getattr(trainer, 'feedback_bridge', None) is not None:
            fb_s = trainer.feedback_bridge.stats()
            print(f"  FB: alpha={fb_s.get('alpha', 0):.5f}, reward={fb_s.get('reward', 0):.3f}")
    print(f"  Summary: {summary_path}")
    print(f"\nDone! ({(time.time()-t_start)/60:.1f} min)")


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup_ddp()
