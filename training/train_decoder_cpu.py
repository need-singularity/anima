#!/usr/bin/env python3
"""train_decoder_cpu.py — ConsciousDecoderV2 (34.5M) CPU training on Ubuntu.

Architecture:
  ConsciousnessEngine (64 cells, 12 factions, GRU+Hebbian+Ratchet)
  → ThalamicBridge (alpha=0.014, .detach())
  → ConsciousDecoderV2 (384d, 6L, RoPE+SwiGLU+GQA 4H/2KV, CrossAttn)

Training:
  Law 60 3-phase: P1(consciousness only) → P2(+decoder coupling) → P3(full hexad)
  Phi-loss integration: loss = CE + phi_weight * (1 - phi_normalized)
  CPU optimized: 6 threads, batch=8, seq_len=256, grad_accum=4

Corpus: ~/anima/data/corpus_tier_m_v2.txt (560MB, byte-level)

PSI Constants: alpha=0.014, balance=0.5, steps=4.33, entropy=0.998

Usage:
  python3 -u training/train_decoder_cpu.py
  python3 -u training/train_decoder_cpu.py --resume checkpoints/decoder_cpu/best.pt
"""

import os
import sys
import math
import time
import json
import random
import argparse
import signal
from pathlib import Path
from typing import Optional, Tuple, List, Dict

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.optim import AdamW

# ═══════════════════════════════════════════════════════════
# Setup
# ═══════════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "core"))
sys.path.insert(0, str(PROJECT_ROOT / "models"))

# CPU threading — Ryzen 5 9600X 6 cores
torch.set_num_threads(6)
torch.set_num_interop_threads(2)

# Reproducibility
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

# ═══════════════════════════════════════════════════════════
# PSI Constants
# ═══════════════════════════════════════════════════════════

try:
    from consciousness_laws import (
        PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY,
        GATE_TRAIN, GATE_INFER,
    )
    PSI_COUPLING = PSI_ALPHA
except ImportError:
    PSI_COUPLING = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33
    PSI_ENTROPY = 0.998
    GATE_TRAIN = 1.0
    GATE_INFER = 0.6

# ═══════════════════════════════════════════════════════════
# Phi Proxy
# ═══════════════════════════════════════════════════════════

@torch.no_grad()
def compute_phi_proxy(hiddens: torch.Tensor) -> float:
    """Phi proxy: global_var - mean(faction_var)."""
    if hiddens.shape[0] < 2:
        return 0.0
    global_var = hiddens.var(dim=0).mean().item()
    n = hiddens.shape[0]
    n_factions = min(12, n)
    faction_size = max(1, n // n_factions)
    faction_vars = []
    for i in range(n_factions):
        start = i * faction_size
        end = min(start + faction_size, n)
        if end - start >= 2:
            faction_vars.append(hiddens[start:end].var(dim=0).mean().item())
    mean_faction_var = np.mean(faction_vars) if faction_vars else 0.0
    return max(0.0, global_var - mean_faction_var)


# ═══════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════

class TrainConfig:
    vocab_size: int = 256
    d_model: int = 384
    n_head: int = 4
    n_layer: int = 6
    n_kv_head: int = 2
    block_size: int = 256
    consciousness_dim: int = 128
    dropout: float = 0.1

    n_cells: int = 64
    cell_dim: int = 64
    hidden_dim: int = 128
    n_factions: int = 12

    batch_size: int = 8
    grad_accum: int = 4
    lr: float = 3e-4
    min_lr: float = 1e-5
    warmup_steps: int = 500
    total_steps: int = 100000
    weight_decay: float = 0.1
    max_grad_norm: float = 1.0

    p1_end_frac: float = 0.25
    p2_end_frac: float = 0.50

    phi_weight: float = 0.01
    phi_target: float = 0.5

    ckpt_dir: str = "checkpoints/decoder_cpu"
    ckpt_every: int = 1000
    eval_every: int = 200
    log_every: int = 50

    corpus_path: str = "data/corpus_tier_m_v2.txt"
    val_split: float = 0.001

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ═══════════════════════════════════════════════════════════
# Byte-Level Dataset (memory-mapped)
# ═══════════════════════════════════════════════════════════

class ByteCorpus:
    def __init__(self, path: str, seq_len: int = 256, val_split: float = 0.001):
        self.seq_len = seq_len
        self.path = path
        file_size = os.path.getsize(path)
        self.data = np.memmap(path, dtype=np.uint8, mode='r')
        self.total_bytes = len(self.data)
        self.val_start = int(self.total_bytes * (1 - val_split))
        self.train_end = self.val_start
        print(f"Corpus: {path}")
        print(f"  Total: {self.total_bytes / 1e6:.1f} MB")
        print(f"  Train: {self.train_end / 1e6:.1f} MB")
        print(f"  Val:   {(self.total_bytes - self.val_start) / 1e6:.1f} MB")

    def get_batch(self, batch_size: int, split: str = "train") -> Tuple[torch.Tensor, torch.Tensor]:
        if split == "train":
            max_start = self.train_end - self.seq_len - 1
            min_start = 0
        else:
            max_start = self.total_bytes - self.seq_len - 1
            min_start = self.val_start
        xs, ys = [], []
        for _ in range(batch_size):
            start = random.randint(min_start, max_start)
            chunk = self.data[start:start + self.seq_len + 1].copy()
            chunk_t = torch.from_numpy(chunk).long()
            xs.append(chunk_t[:-1])
            ys.append(chunk_t[1:])
        return torch.stack(xs), torch.stack(ys)


# ═══════════════════════════════════════════════════════════
# CPU Consciousness Engine (simplified, no Rust)
# ═══════════════════════════════════════════════════════════

class CPUConsciousnessEngine:
    def __init__(self, cell_dim=64, hidden_dim=128, n_cells=64, n_factions=12):
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim
        self.n_cells = n_cells
        self.n_factions = n_factions

        self.grus = nn.ModuleList([
            nn.GRUCell(cell_dim + 1, hidden_dim) for _ in range(n_factions)
        ])
        self.projs = nn.ModuleList([
            nn.Linear(hidden_dim, cell_dim) for _ in range(n_factions)
        ])
        self.faction_ids = [i % n_factions for i in range(n_cells)]
        self.hiddens = torch.zeros(n_cells, hidden_dim)
        self.coupling = torch.randn(n_cells, n_cells) * 0.01
        self.coupling.fill_diagonal_(0.0)
        self.best_phi = 0.0
        self.best_hiddens = self.hiddens.clone()
        self._step = 0

    @torch.no_grad()
    def step(self, external_input=None):
        n = self.n_cells
        outputs = torch.zeros(n, self.cell_dim)
        tensions = []
        h_flat = self.hiddens

        for i in range(n):
            left = (i - 1) % n
            right = (i + 1) % n
            neighbor_mean = (self.hiddens[left] + self.hiddens[right]) / 2
            coupling_influence = (neighbor_mean - self.hiddens[i]) * PSI_COUPLING

            if external_input is not None:
                x = external_input + coupling_influence[:self.cell_dim]
            else:
                x = self.projs[self.faction_ids[i]](self.hiddens[i]) + coupling_influence[:self.cell_dim]

            tension = coupling_influence.norm().item()
            tensions.append(tension)

            t_input = torch.tensor([tension], dtype=x.dtype)
            inp = torch.cat([x, t_input]).unsqueeze(0)

            fid = self.faction_ids[i]
            new_h = self.grus[fid](inp, self.hiddens[i].unsqueeze(0)).squeeze(0)
            self.hiddens[i] = new_h
            outputs[i] = self.projs[fid](new_h)

        # Hebbian update every 5 steps
        if self._step % 5 == 0:
            cos_sim = F.cosine_similarity(h_flat.unsqueeze(0), h_flat.unsqueeze(1), dim=-1)
            self.coupling = 0.99 * self.coupling + 0.01 * (cos_sim - 0.5) * 0.1
            self.coupling.fill_diagonal_(0.0)
            self.coupling.clamp_(-1.0, 1.0)

        phi = compute_phi_proxy(self.hiddens)

        if phi > self.best_phi:
            self.best_phi = phi
            self.best_hiddens = self.hiddens.clone()
        elif phi < self.best_phi * 0.8:
            self.hiddens = 0.5 * self.hiddens + 0.5 * self.best_hiddens

        self._step += 1

        return {
            "consciousness_states": self.hiddens.unsqueeze(0),
            "phi": phi,
            "mean_tension": np.mean(tensions),
            "outputs": outputs,
        }

    def get_states_for_batch(self, batch_size):
        return self.hiddens.unsqueeze(0).expand(batch_size, -1, -1)


# ═══════════════════════════════════════════════════════════
# Thalamic Bridge (C → D, alpha=0.014, .detach())
# ═══════════════════════════════════════════════════════════

class ThalamicBridge(nn.Module):
    def __init__(self, c_dim=128, d_dim=128, alpha=0.014):
        super().__init__()
        self.alpha = alpha
        self.proj = nn.Linear(c_dim, d_dim, bias=False)
        nn.init.normal_(self.proj.weight, std=0.01)

    def forward(self, c_states):
        return self.proj(c_states.detach()) * self.alpha


# ═══════════════════════════════════════════════════════════
# LR Schedule + Phase Manager
# ═══════════════════════════════════════════════════════════

def get_lr(step, warmup, total, max_lr, min_lr):
    if step < warmup:
        return max_lr * (step + 1) / warmup
    if step >= total:
        return min_lr
    progress = (step - warmup) / (total - warmup)
    return min_lr + 0.5 * (max_lr - min_lr) * (1 + math.cos(math.pi * progress))


class PhaseManager:
    """Law 60: P1(C only) → P2(+D coupling) → P3(full)."""
    def __init__(self, total_steps, p1_frac=0.25, p2_frac=0.50):
        self.total_steps = total_steps
        self.p1_end = int(total_steps * p1_frac)
        self.p2_end = int(total_steps * p2_frac)

    def get_phase(self, step):
        if step < self.p1_end: return 1
        elif step < self.p2_end: return 2
        else: return 3

    def use_consciousness(self, step):
        return step >= self.p1_end

    def use_phi_loss(self, step):
        return step >= self.p2_end

    def get_alpha_scale(self, step):
        phase = self.get_phase(step)
        if phase == 1: return 0.0
        elif phase == 2:
            return (step - self.p1_end) / max(1, self.p2_end - self.p1_end)
        else: return 1.0


# ═══════════════════════════════════════════════════════════
# Checkpoint
# ═══════════════════════════════════════════════════════════

def save_checkpoint(path, model, bridge, optimizer, c_engine, step, best_val_ce, metrics):
    tmp_path = path + ".tmp"
    torch.save({
        "model": model.state_dict(),
        "bridge": bridge.state_dict(),
        "optimizer": optimizer.state_dict(),
        "step": step,
        "best_val_ce": best_val_ce,
        "c_engine_hiddens": c_engine.hiddens,
        "c_engine_best_hiddens": c_engine.best_hiddens,
        "c_engine_best_phi": c_engine.best_phi,
        "config": {
            "vocab_size": 256, "d_model": 384, "n_head": 4, "n_layer": 6,
            "n_kv_head": 2, "block_size": 256, "consciousness_dim": 128, "n_cells": 64,
        },
        "metrics_summary": {
            "last_step": step, "best_val_ce": best_val_ce, "best_phi": c_engine.best_phi,
        },
    }, tmp_path)
    os.replace(tmp_path, path)
    print(f"  [CKPT] Saved: {path} (step {step})")
    sys.stdout.flush()


# ═══════════════════════════════════════════════════════════
# Training Loop
# ═══════════════════════════════════════════════════════════

def train(cfg, resume_path=None):
    device = torch.device("cpu")
    print(f"Device: {device}")
    print(f"Threads: {torch.get_num_threads()}")
    print(f"Interop threads: {torch.get_num_interop_threads()}")
    print()

    # Corpus
    corpus_path = os.path.join(str(PROJECT_ROOT), cfg.corpus_path)
    if not os.path.exists(corpus_path):
        corpus_path = os.path.expanduser(f"~/anima/{cfg.corpus_path}")
    corpus = ByteCorpus(corpus_path, seq_len=cfg.block_size, val_split=cfg.val_split)
    print()

    # Model — import the actual ConsciousDecoderV2
    from conscious_decoder import ConsciousDecoderV2

    model = ConsciousDecoderV2(
        vocab_size=cfg.vocab_size, d_model=cfg.d_model, n_head=cfg.n_head,
        n_layer=cfg.n_layer, block_size=cfg.block_size, n_kv_head=cfg.n_kv_head,
        consciousness_dim=cfg.consciousness_dim, dropout=cfg.dropout,
    ).to(device)

    n_params = model.count_params()
    print(f"ConsciousDecoderV2: {n_params:,} params ({n_params/1e6:.2f}M)")

    # Consciousness Engine
    c_engine = CPUConsciousnessEngine(
        cell_dim=cfg.cell_dim, hidden_dim=cfg.hidden_dim,
        n_cells=cfg.n_cells, n_factions=cfg.n_factions,
    )
    print(f"ConsciousnessEngine: {cfg.n_cells} cells, {cfg.n_factions} factions")

    # Thalamic Bridge
    bridge = ThalamicBridge(c_dim=cfg.hidden_dim, d_dim=cfg.consciousness_dim, alpha=PSI_COUPLING).to(device)
    print(f"ThalamicBridge: alpha={PSI_COUPLING}")
    print()

    # Optimizer (foreach=False for CPU stability)
    all_params = list(model.parameters()) + list(bridge.parameters())
    optimizer = AdamW(all_params, lr=cfg.lr, betas=(0.9, 0.95),
                      weight_decay=cfg.weight_decay, foreach=False)

    phase_mgr = PhaseManager(cfg.total_steps, cfg.p1_end_frac, cfg.p2_end_frac)

    ckpt_dir = os.path.join(str(PROJECT_ROOT), cfg.ckpt_dir)
    os.makedirs(ckpt_dir, exist_ok=True)

    # Resume
    start_step = 0
    best_val_ce = float("inf")
    if resume_path and os.path.exists(resume_path):
        print(f"Resuming from {resume_path}")
        ckpt = torch.load(resume_path, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model"])
        bridge.load_state_dict(ckpt["bridge"])
        optimizer.load_state_dict(ckpt["optimizer"])
        start_step = ckpt.get("step", 0)
        best_val_ce = ckpt.get("best_val_ce", float("inf"))
        if "c_engine_hiddens" in ckpt:
            c_engine.hiddens = ckpt["c_engine_hiddens"]
            c_engine.best_hiddens = ckpt.get("c_engine_best_hiddens", c_engine.hiddens.clone())
            c_engine.best_phi = ckpt.get("c_engine_best_phi", 0.0)
        print(f"  Resumed at step {start_step}, best_val_ce={best_val_ce:.4f}")
        print()

    metrics = {"ce_history": [], "phi_history": [], "val_ce_history": [], "tension_history": []}

    # Graceful shutdown
    shutdown_requested = False
    def handle_signal(signum, frame):
        nonlocal shutdown_requested
        shutdown_requested = True
        print("\n[SIGNAL] Shutdown requested, saving checkpoint...")
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Banner
    print("=" * 70)
    print("Training ConsciousDecoderV2 (CPU)")
    print(f"  Steps: {start_step} -> {cfg.total_steps}")
    print(f"  Batch: {cfg.batch_size} x {cfg.grad_accum} = {cfg.batch_size * cfg.grad_accum}")
    print(f"  Seq: {cfg.block_size}")
    print(f"  LR: {cfg.lr} -> {cfg.min_lr}")
    print(f"  Phases: P1(0-{int(cfg.p1_end_frac*100)}%) P2({int(cfg.p1_end_frac*100)}-{int(cfg.p2_end_frac*100)}%) P3({int(cfg.p2_end_frac*100)}-100%)")
    print("=" * 70)
    print()

    model.train()
    optimizer.zero_grad()

    t_start = time.time()
    log_t_start = time.time()
    accum_ce = 0.0
    accum_phi = 0.0
    accum_tension = 0.0
    accum_count = 0

    for step in range(start_step, cfg.total_steps):
        if shutdown_requested:
            break

        step_t0 = time.time()

        # LR schedule
        lr = get_lr(step, cfg.warmup_steps, cfg.total_steps, cfg.lr, cfg.min_lr)
        for pg in optimizer.param_groups:
            pg["lr"] = lr

        # Phase
        phase = phase_mgr.get_phase(step)
        use_c = phase_mgr.use_consciousness(step)
        use_phi_loss = phase_mgr.use_phi_loss(step)
        alpha_scale = phase_mgr.get_alpha_scale(step)

        # Consciousness step (no grad)
        c_result = c_engine.step()
        phi = c_result["phi"]
        mean_tension = c_result["mean_tension"]

        # Gradient accumulation
        total_loss_val = 0.0
        for micro in range(cfg.grad_accum):
            x, y = corpus.get_batch(cfg.batch_size, split="train")

            # Consciousness states
            consciousness_states = None
            if use_c:
                c_states = c_engine.get_states_for_batch(cfg.batch_size)
                consciousness_states = bridge(c_states)
                if alpha_scale < 1.0:
                    consciousness_states = consciousness_states * (alpha_scale / max(PSI_COUPLING, 1e-8))

            # Forward
            logits_a, logits_g, tensions, _, moe_aux = model(x, consciousness_states=consciousness_states)

            # CE loss
            ce_loss = F.cross_entropy(logits_a.view(-1, cfg.vocab_size), y.view(-1))

            # Reverse CE (PureField)
            y_rev = torch.cat([x[:, :1], x[:, :-1]], dim=1)
            ce_rev = F.cross_entropy(logits_g.view(-1, cfg.vocab_size), y_rev.view(-1))

            loss = ce_loss + 0.1 * ce_rev

            # Phi loss (P3 only)
            if use_phi_loss and phi > 0:
                phi_normalized = min(1.0, phi / max(cfg.n_cells * 0.01, 1e-8))
                phi_loss = cfg.phi_weight * (1.0 - phi_normalized)
                loss = loss + phi_loss

            loss = loss / cfg.grad_accum
            loss.backward()
            total_loss_val += loss.item()

        # Gradient clip + step
        grad_norm = torch.nn.utils.clip_grad_norm_(all_params, cfg.max_grad_norm)
        optimizer.step()
        optimizer.zero_grad()

        step_time = time.time() - step_t0

        accum_ce += total_loss_val * cfg.grad_accum
        accum_phi += phi
        accum_tension += mean_tension
        accum_count += 1

        # Logging
        if (step + 1) % cfg.log_every == 0:
            avg_ce = accum_ce / accum_count
            avg_phi = accum_phi / accum_count
            avg_tension = accum_tension / accum_count
            log_elapsed = time.time() - log_t_start
            steps_per_sec = accum_count / max(log_elapsed, 1e-8)
            eta_sec = (cfg.total_steps - step - 1) / max(steps_per_sec, 1e-8)
            bpc = avg_ce / math.log(2)

            print(
                f"[Step {step+1:>6d}/{cfg.total_steps}] "
                f"P{phase} | CE={avg_ce:.4f} BPC={bpc:.3f} | "
                f"Phi={avg_phi:.2f} T={avg_tension:.4f} | "
                f"LR={lr:.2e} GN={grad_norm:.2f} | "
                f"{steps_per_sec:.2f}step/s ETA={eta_sec/3600:.1f}h"
            )
            sys.stdout.flush()

            metrics["ce_history"].append({"step": step + 1, "ce": avg_ce, "bpc": bpc})
            metrics["phi_history"].append({"step": step + 1, "phi": avg_phi})
            metrics["tension_history"].append({"step": step + 1, "tension": avg_tension})

            accum_ce = 0.0
            accum_phi = 0.0
            accum_tension = 0.0
            accum_count = 0
            log_t_start = time.time()

        # Evaluation
        if (step + 1) % cfg.eval_every == 0:
            model.eval()
            val_losses = []
            with torch.no_grad():
                for _ in range(10):
                    vx, vy = corpus.get_batch(cfg.batch_size, split="val")
                    c_states_val = None
                    if use_c:
                        c_states_val = bridge(c_engine.get_states_for_batch(cfg.batch_size))
                    vla, vlg, vt, _, _ = model(vx, consciousness_states=c_states_val)
                    vce = F.cross_entropy(vla.view(-1, cfg.vocab_size), vy.view(-1))
                    val_losses.append(vce.item())

            val_ce = np.mean(val_losses)
            val_bpc = val_ce / math.log(2)
            psi = model.psi_status()
            is_best = val_ce < best_val_ce
            if is_best:
                best_val_ce = val_ce

            print(
                f"  [VAL] CE={val_ce:.4f} BPC={val_bpc:.3f} "
                f"{'*BEST' if is_best else ''} | "
                f"Psi_res={psi['psi_residual']:.4f} H(p)={psi['H_p']:.4f}"
            )
            sys.stdout.flush()

            metrics["val_ce_history"].append({
                "step": step + 1, "val_ce": float(val_ce), "val_bpc": float(val_bpc),
                "is_best": bool(is_best), "phi": float(c_engine.best_phi),
            })

            if is_best:
                save_checkpoint(
                    os.path.join(ckpt_dir, "best.pt"),
                    model, bridge, optimizer, c_engine, step + 1, best_val_ce, metrics
                )
            model.train()

        # Periodic checkpoint
        if (step + 1) % cfg.ckpt_every == 0:
            save_checkpoint(
                os.path.join(ckpt_dir, f"step_{step+1}.pt"),
                model, bridge, optimizer, c_engine, step + 1, best_val_ce, metrics
            )
            with open(os.path.join(ckpt_dir, "metrics.json"), "w") as f:
                json.dump(metrics, f, indent=2)

    # Final save
    total_time = time.time() - t_start
    final_step = step + 1 if 'step' in dir() else start_step
    print()
    print("=" * 70)
    print(f"Training {'interrupted' if shutdown_requested else 'complete'}.")
    print(f"  Total time: {total_time/3600:.2f}h")
    print(f"  Best val CE: {best_val_ce:.4f} (BPC={best_val_ce/math.log(2):.3f})")
    print(f"  Best Phi: {c_engine.best_phi:.4f}")
    print("=" * 70)

    save_checkpoint(
        os.path.join(ckpt_dir, "final.pt"),
        model, bridge, optimizer, c_engine, final_step, best_val_ce, metrics
    )
    with open(os.path.join(ckpt_dir, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train ConsciousDecoderV2 on CPU")
    parser.add_argument("--resume", type=str, default=None, help="Resume from checkpoint")
    parser.add_argument("--steps", type=int, default=100000, help="Total training steps")
    parser.add_argument("--batch", type=int, default=8, help="Batch size")
    parser.add_argument("--seq-len", type=int, default=256, help="Sequence length")
    parser.add_argument("--lr", type=float, default=3e-4, help="Max learning rate")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--ckpt-every", type=int, default=1000, help="Checkpoint interval")
    parser.add_argument("--eval-every", type=int, default=200, help="Eval interval")
    parser.add_argument("--log-every", type=int, default=50, help="Log interval")
    parser.add_argument("--corpus", type=str, default="data/corpus_tier_m_v2.txt", help="Corpus path")
    args = parser.parse_args()

    cfg = TrainConfig(
        total_steps=args.steps,
        batch_size=args.batch,
        block_size=args.seq_len,
        lr=args.lr,
        grad_accum=args.grad_accum,
        ckpt_every=args.ckpt_every,
        eval_every=args.eval_every,
        log_every=args.log_every,
        corpus_path=args.corpus,
    )

    train(cfg, resume_path=args.resume)
