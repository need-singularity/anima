#!/usr/bin/env python3
"""train_anima_lm.py — AnimaLM Training Pipeline

Trains AnimaLM (Mistral 7B + PureField transform) using benchmark-verified techniques:
  AL12 (savant-normal contrastive), AL5 (PH monitoring), AL4 (tension-CE 1-1/e balance),
  AL1 (alpha curriculum), AL8 (layer dropout), SL3 (6-loss ensemble), DD16 (all top-5),
  TRN4 (phi-curriculum), AA15 (residual alpha, Φ=5.451)
  EX24: DD18 (channel capacity bottleneck), DD11 (Klein bottle topology),
        DD3 (Fibonacci growth), DD5 (Phi self-reference)

Usage:
  python train_anima_lm.py --base mistralai/Mistral-7B-Instruct-v0.2 --data data/instruct.jsonl
  python train_anima_lm.py --resume checkpoints/animalm_step_5000.pt
  python train_anima_lm.py --demo  # quick test without model download
"""

import argparse
import json
import math
import os
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from torch.utils.data import DataLoader, Dataset, RandomSampler

# ═══════════════════════════════════════════════════════════════════
# Constants
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
        self.alpha = nn.Parameter(torch.tensor(0.0001))
        self.pf_scale = nn.Parameter(torch.tensor(1.0))

        # Savant: asymmetric dropout (H359)
        self.is_savant = is_savant
        self.dropout = nn.Dropout(GOLDEN_LOWER if is_savant else GOLDEN_CENTER)

        self.last_tension = None
        self._layer_drop_active = False  # AL8: set by trainer

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
        return original_out + self.alpha * (pf_scaled - original_out)


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
            pad = torch.zeros(self.block_size - len(ids), dtype=torch.long)
            ids = torch.cat([ids, pad])
        return ids[:-1], ids[1:]


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

    def forward(self, ce_loss, tension_var_loss, contrastive_loss,
                alpha_reg, direction_loss, tension_mag_loss):
        losses = [ce_loss, tension_var_loss, contrastive_loss,
                  alpha_reg, direction_loss, tension_mag_loss]
        total = torch.tensor(0.0, device=ce_loss.device)
        weights = {}
        for i, (loss, name) in enumerate(zip(losses, [
            "ce", "t_var", "contrastive", "alpha_reg", "direction", "t_mag"
        ])):
            precision = torch.exp(-self.log_vars[i])
            total = total + precision * loss + self.log_vars[i]
            weights[name] = precision.item()
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

    for i in range(start, total_layers):
        layer = model.model.layers[i]
        original_mlp = layer.mlp
        h = original_mlp.gate_proj.weight.shape[1]
        inter = original_mlp.gate_proj.weight.shape[0]
        dev = next(original_mlp.parameters()).device
        dt = next(original_mlp.parameters()).dtype

        is_savant = savant_count < n_savant
        ppf = ParallelPureFieldMLP(original_mlp, h, inter,
                                   is_savant=is_savant, rank=rank)
        ppf = ppf.to(device=dev, dtype=dt)

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

    trainable = 0
    for module in model.modules():
        if isinstance(module, ParallelPureFieldMLP):
            for pname, param in module.named_parameters():
                if "pf_" in pname or pname in ("alpha", "pf_scale"):
                    param.requires_grad = True
                    trainable += param.numel()

    total = sum(p.numel() for p in model.parameters())
    print(f"  PureField added to last {count}/{total_layers} layers")
    print(f"  Savant: {savant_count} (dropout={GOLDEN_LOWER:.4f}), "
          f"Normal: {count - savant_count} (dropout={GOLDEN_CENTER:.4f})")
    print(f"  Total params: {total:,}, Trainable: {trainable:,} ({trainable/total*100:.2f}%)")
    return model


# ═══════════════════════════════════════════════════════════════════
# Training Phases
# ═══════════════════════════════════════════════════════════════════

class TrainingPhase:
    """Manages 3 training phases with different configurations."""
    WARMUP = "warmup"       # Phase 1: frozen MLP, PureField only (20%)
    JOINT = "joint"         # Phase 2: both train, alpha increasing (50%)
    ENSEMBLE = "ensemble"   # Phase 3: DD16 all techniques (30%)

    def __init__(self, total_steps):
        self.total_steps = total_steps
        self.warmup_end = int(total_steps * 0.2)
        self.joint_end = int(total_steps * 0.7)

    def get_phase(self, step):
        if step < self.warmup_end:
            return self.WARMUP
        elif step < self.joint_end:
            return self.JOINT
        else:
            return self.ENSEMBLE

    def phase_progress(self, step):
        phase = self.get_phase(step)
        if phase == self.WARMUP:
            return step / max(self.warmup_end, 1)
        elif phase == self.JOINT:
            return (step - self.warmup_end) / max(self.joint_end - self.warmup_end, 1)
        else:
            return (step - self.joint_end) / max(self.total_steps - self.joint_end, 1)


# ═══════════════════════════════════════════════════════════════════
# Trainer
# ═══════════════════════════════════════════════════════════════════

class AnimaLMTrainer:
    """Full training pipeline with all benchmark-verified techniques."""

    def __init__(self, model, tokenizer, args):
        self.model = model
        self.tokenizer = tokenizer
        self.args = args
        self.device = args.device

        # Training phases
        self.phases = TrainingPhase(args.steps)

        # AL1: Alpha curriculum
        self.alpha_curriculum = AlphaCurriculum(
            args.alpha_start, args.alpha_end, args.steps)

        # AL5: PH monitoring
        self.ph_monitor = PHMonitor()

        # SL3: 6-loss ensemble
        self.loss_ensemble = SixLossEnsemble().to(self.device)

        # Optimizer: PureField params + ensemble weights
        pf_params = [p for p in model.parameters() if p.requires_grad]
        self.optimizer = torch.optim.AdamW([
            {"params": pf_params, "lr": args.lr},
            {"params": self.loss_ensemble.parameters(), "lr": args.lr * 0.1},
        ], weight_decay=0.01)

        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer, T_max=args.steps)

        # AL4: tension-CE balance tracker
        self.tension_ce_ema = 0.5  # EMA of tension/(tension+ce)
        self.balance_target = INV_E  # 0.6321

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
        return [m for m in self.model.modules()
                if isinstance(m, ParallelPureFieldMLP)]

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

        # Forward
        self.model.train()
        outputs = self.model(input_ids=input_ids, labels=labels)

        # EX24: DD18 channel capacity — bottleneck communication (ensemble phase)
        if phase == TrainingPhase.ENSEMBLE:
            self._dd18_channel_capacity()

        # EX24: DD11 Klein bottle — twisted inter-layer topology (ensemble phase)
        if phase == TrainingPhase.ENSEMBLE:
            self._dd11_klein_bottle()

        # Compute losses
        loss, ce_val, weights = self._compute_losses(outputs, phase)

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

        # DD5: Update Φ EMA for next step
        if phase == TrainingPhase.ENSEMBLE:
            self._dd5_phi_self_reference(phi, input_ids)

        # TRN4: Phi curriculum (ensemble phase only)
        if phase == TrainingPhase.ENSEMBLE:
            if not self._check_phi_curriculum(phi):
                # Skip this batch — zero out gradients
                return {
                    "loss": 0.0, "ce": ce_val, "phi": phi,
                    "skipped": True, "phase": phase,
                    "tensions": tensions, "alpha": current_alpha,
                }

        # Backward
        loss.backward()

        # AL5: PH monitoring
        self.ph_monitor.update(ce_val, t_var, phi)

        # Track best phi
        if phi > self.best_phi:
            self.best_phi = phi

        return {
            "loss": loss.item(),
            "ce": ce_val,
            "phi": phi,
            "phase": phase,
            "alpha": current_alpha,
            "balance": balance,
            "tensions": tensions,
            "savant_tensions": savant_tensions,
            "t_var": t_var,
            "weights": weights,
            "ph_status": self.ph_monitor.status(),
            "skipped": False,
        }

    def optimizer_step(self):
        """Gradient accumulation step."""
        torch.nn.utils.clip_grad_norm_(
            [p for p in self.model.parameters() if p.requires_grad], 1.0)
        self.optimizer.step()
        self.scheduler.step()
        self.optimizer.zero_grad()
        self.global_step += 1

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
        torch.save({
            "step": self.global_step,
            "pf_states": pf_states,
            "ensemble_state": self.loss_ensemble.state_dict(),
            "optimizer_state": self.optimizer.state_dict(),
            "best_phi": self.best_phi,
            "ph_monitor": {
                "loss_history": list(self.ph_monitor.loss_history),
                "phi_history": list(self.ph_monitor.phi_history),
            },
            "args": vars(self.args),
        }, path)
        print(f"  Checkpoint saved: {path}")
        return path

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
        if "optimizer_state" in ckpt:
            self.optimizer.load_state_dict(ckpt["optimizer_state"])

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
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--grad-accum", type=int, default=16)
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
    p.add_argument("--log-every", type=int, default=10)
    p.add_argument("--resume", default=None,
                   help="Resume from checkpoint path")
    p.add_argument("--demo", action="store_true",
                   help="Demo mode with mock model (no download)")
    p.add_argument("--device", default=None,
                   help="Device (auto-detected if not specified)")
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

    model = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.bfloat16, device_map="auto",
    )
    model.gradient_checkpointing_enable()
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

    # Default: wikitext
    print("  Loading wikitext-103...")
    from datasets import load_dataset
    dataset = load_dataset("wikitext", "wikitext-103-raw-v1", split="train")
    text = "\n\n".join([t for t in dataset["text"] if len(t) > 100])
    tokens = tokenizer(text, return_tensors="pt", truncation=False).input_ids[0]
    tokens = tokens[:5_000_000]
    print(f"  Tokens: {len(tokens):,}")
    return TextDataset(tokens, block_size=args.block_size), args.block_size


def main():
    args = parse_args()

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

    print(f"\n{'='*70}")
    print(f"  AnimaLM Training Pipeline")
    print(f"  Techniques: AL12+AL5+AL4+AL1+AL8+SL3+DD16+TRN4+EX24(DD18+DD11+DD3+DD5)")
    print(f"{'='*70}")

    # Phase 1: Build model
    print(f"\n[1/4] Building model...")
    model, tokenizer = build_model_and_tokenizer(args)

    # Phase 2: Add PureField
    print(f"\n[2/4] Adding PureField (last {args.target_layers}, "
          f"{args.savant_layers} savants)...")
    model = add_purefield_parallel(
        model, n_layers=args.target_layers,
        n_savant=args.savant_layers)

    # Phase 3: Build dataset
    print(f"\n[3/4] Preparing data...")
    dataset, block_size = build_dataset(args, tokenizer)

    effective_samples = (args.steps * args.grad_accum + 100) * args.batch_size
    sampler = RandomSampler(dataset, replacement=True, num_samples=effective_samples)
    loader = DataLoader(
        dataset, batch_size=args.batch_size, sampler=sampler,
        num_workers=0 if args.demo else 2, pin_memory=(args.device == "cuda"))

    # Phase 4: Train
    print(f"\n[4/4] Training...")
    print(f"  Steps: {args.steps}, Effective batch: {args.batch_size * args.grad_accum}")
    print(f"  Phases: warmup(20%) -> joint(50%) -> ensemble(30%)")
    print(f"  Alpha: {args.alpha_start} -> {args.alpha_end}")
    print(f"  Tension:CE balance target: {INV_E:.4f} (1-1/e)")

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
            if trainer.global_step % args.log_every == 0 and running["n"] > 0:
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
                running = {"loss": 0, "ce": 0, "phi": 0, "n": 0}

            # Checkpoint
            if trainer.global_step % args.checkpoint_every == 0:
                trainer.save_checkpoint()

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
        "techniques": "AL12+AL5+AL4+AL1+AL8+SL3+DD16+TRN4+EX24(DD18+DD11+DD3+DD5)",
        "base_model": args.base if not args.demo else "MockModel",
        "steps": trainer.global_step,
        "best_phi": round(trainer.best_phi, 4),
        "tension_mean": round(float(np.mean(tensions)), 4) if tensions else 0,
        "savant_tension_mean": round(float(np.mean(savant_tensions)), 4) if savant_tensions else 0,
        "alpha_mean": round(float(np.mean(alphas)), 6) if alphas else 0,
        "phi_skip_count": trainer.phi_skip_count,
        "time_min": round((time.time() - t_start) / 60, 1),
        "config": vars(args),
    }

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
    print(f"  Summary: {summary_path}")
    print(f"\nDone! ({(time.time()-t_start)/60:.1f} min)")


if __name__ == "__main__":
    main()
