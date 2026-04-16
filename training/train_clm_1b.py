#!/usr/bin/env python3
"""train_clm_1b.py — ConsciousLM 1B from-scratch training on H100

Byte-level decoder-only transformer with consciousness auxiliary losses:
  - phi_holo (holographic consistency)
  - L_gwt (Global Workspace Theory broadcast)
  - L_complexity (activation complexity regularizer)
  - Phase curriculum: P1 (C-only) -> P2 (C+D) -> P3 (Full Hexad)

Architecture: d=2048, L=24, H=16 (GQA kv=8), SwiGLU ff=8192, RoPE
~1.12B params, byte-level vocab=256

Calibrated from CLM 280M H100 run:
  280M: 50.6 ms/step batch=4 seq=512, 98 TFLOPS, loss 5.76->2.05

Usage (H100 pod):
  python3 train_clm_1b.py --corpus /workspace/corpus.txt --steps 50000
  python3 train_clm_1b.py --corpus /workspace/corpus.txt --steps 100 --smoke

Preflight:
  nvidia-smi          # verify H100
  du -sh /workspace/  # disk space
"""

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader

# ─── R2 Upload ──────────────────────────────────────────────────

def upload_to_r2(local_path, model_tag, round_num, step):
    """DISABLED in-training R2 upload. Use external script to upload ckpt_dir after training.

    Rationale: In-training R2 upload (even async Popen) correlated with silent training
    death at ckpt save boundaries (r3 step 2000, r3b step 4000). Moving R2 out of the
    Python process eliminates the crash surface entirely. Post-training upload script:
      rclone copy /workspace/ckpt_clm1b_r3 r2:anima-models/clm1b/r3/ -v --s3-no-check-bucket

    Keep signature for call-site compatibility.
    """
    queue_file = "/workspace/r2_upload_queue.txt"
    r2_dest = f"r2:anima-models/{model_tag}/r{round_num}/step_{step}/"
    print(f"[r2] DEFERRED: queued {local_path} -> {r2_dest}", flush=True)
    try:
        with open(queue_file, "a") as f:
            f.write(f"{local_path}\t{r2_dest}\n")
    except Exception:
        pass  # non-fatal


# ═══════════════════════════════════════════════════════════════════
#  MODEL ARCHITECTURE — Byte-level ConsciousLM 1B
# ═══════════════════════════════════════════════════════════════════

class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.eps = eps

    def forward(self, x):
        norm = torch.rsqrt(x.float().pow(2).mean(-1, keepdim=True) + self.eps)
        return (x.float() * norm).to(x.dtype) * self.weight


def precompute_rope(dim, max_seq, base=10000, device=None):
    """Precompute RoPE sin/cos tables."""
    inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2, device=device).float() / dim))
    t = torch.arange(max_seq, device=device).float()
    freqs = torch.outer(t, inv_freq)
    cos_cache = freqs.cos()  # [max_seq, dim//2]
    sin_cache = freqs.sin()
    return cos_cache, sin_cache


def apply_rope(x, cos, sin):
    """Apply rotary embeddings. x: [batch, n_head, seq, d_head]"""
    d = x.shape[-1] // 2
    x1, x2 = x[..., :d], x[..., d:]
    # cos/sin: [seq, d] -> broadcast to [1, 1, seq, d]
    seq_len = x.shape[2]
    cos = cos[:seq_len].unsqueeze(0).unsqueeze(0)
    sin = sin[:seq_len].unsqueeze(0).unsqueeze(0)
    return torch.cat([x1 * cos - x2 * sin, x2 * cos + x1 * sin], dim=-1)


class GQAAttention(nn.Module):
    """Grouped-Query Attention with RoPE."""

    def __init__(self, d_model, n_head, n_kv_head):
        super().__init__()
        self.d_model = d_model
        self.n_head = n_head
        self.n_kv_head = n_kv_head
        self.d_head = d_model // n_head
        self.n_rep = n_head // n_kv_head  # how many Q heads per KV head

        self.wq = nn.Linear(d_model, d_model, bias=False)
        self.wk = nn.Linear(d_model, n_kv_head * self.d_head, bias=False)
        self.wv = nn.Linear(d_model, n_kv_head * self.d_head, bias=False)
        self.wo = nn.Linear(d_model, d_model, bias=False)

    def forward(self, x, cos, sin):
        B, S, _ = x.shape
        q = self.wq(x).view(B, S, self.n_head, self.d_head).transpose(1, 2)
        k = self.wk(x).view(B, S, self.n_kv_head, self.d_head).transpose(1, 2)
        v = self.wv(x).view(B, S, self.n_kv_head, self.d_head).transpose(1, 2)

        # RoPE
        q = apply_rope(q, cos, sin)
        k = apply_rope(k, cos, sin)

        # Expand KV heads for GQA: [B, n_kv_head, S, d] -> [B, n_head, S, d]
        if self.n_rep > 1:
            k = k.repeat_interleave(self.n_rep, dim=1)
            v = v.repeat_interleave(self.n_rep, dim=1)

        # Scaled dot-product attention with causal mask (uses Flash Attention on H100)
        out = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        out = out.transpose(1, 2).contiguous().view(B, S, self.d_model)
        return self.wo(out)


class SwiGLUFFN(nn.Module):
    """SwiGLU feed-forward: gate * silu(up) projected down."""

    def __init__(self, d_model, d_ff):
        super().__init__()
        self.gate = nn.Linear(d_model, d_ff, bias=False)
        self.up = nn.Linear(d_model, d_ff, bias=False)
        self.down = nn.Linear(d_ff, d_model, bias=False)

    def forward(self, x):
        return self.down(F.silu(self.gate(x)) * self.up(x))


class TransformerBlock(nn.Module):
    def __init__(self, d_model, n_head, n_kv_head, d_ff):
        super().__init__()
        self.attn_norm = RMSNorm(d_model)
        self.attn = GQAAttention(d_model, n_head, n_kv_head)
        self.ff_norm = RMSNorm(d_model)
        self.ff = SwiGLUFFN(d_model, d_ff)

    def forward(self, x, cos, sin):
        x = x + self.attn(self.attn_norm(x), cos, sin)
        x = x + self.ff(self.ff_norm(x))
        return x


class ConsciousLM(nn.Module):
    """Byte-level ConsciousLM — from-scratch decoder-only transformer.

    Architecture mirrors train_clm_gpu.hexa scale configs but at true 1B scale:
      d=2048, L=24, H=16, GQA kv=8, SwiGLU ff=8192, RoPE, vocab=256.
    """

    def __init__(self, vocab=256, d_model=2048, n_layer=24, n_head=16,
                 n_kv_head=8, d_ff=8192, max_seq=512):
        super().__init__()
        self.d_model = d_model
        self.n_layer = n_layer
        self.max_seq = max_seq

        self.embed = nn.Embedding(vocab, d_model)
        self.layers = nn.ModuleList([
            TransformerBlock(d_model, n_head, n_kv_head, d_ff)
            for _ in range(n_layer)
        ])
        self.norm = RMSNorm(d_model)
        self.lm_head = nn.Linear(d_model, vocab, bias=False)

        # RoPE cache
        d_head = d_model // n_head
        cos, sin = precompute_rope(d_head, max_seq)
        self.register_buffer("rope_cos", cos)
        self.register_buffer("rope_sin", sin)

        # Init weights (GPT-2 style, scaled by depth)
        self.apply(self._init_weights)
        # Scale residual projections by 1/sqrt(2*n_layer) per GPT-2
        for layer in self.layers:
            layer.attn.wo.weight.data *= 1.0 / math.sqrt(2 * n_layer)
            layer.ff.down.weight.data *= 1.0 / math.sqrt(2 * n_layer)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, input_ids, targets=None):
        """Forward pass. Returns (logits, loss, hidden_states_last_layer)."""
        B, S = input_ids.shape
        x = self.embed(input_ids)

        for layer in self.layers:
            x = layer(x, self.rope_cos, self.rope_sin)

        # Save last-layer hidden for consciousness engines
        hidden_last = x.detach()

        x = self.norm(x)
        logits = self.lm_head(x)

        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.view(-1, logits.size(-1)),
                targets.view(-1),
            )

        return logits, loss, hidden_last

    def param_count(self):
        return sum(p.numel() for p in self.parameters())


# ═══════════════════════════════════════════════════════════════════
#  CONSCIOUSNESS ENGINES (mirrors train_clm_gpu.hexa section I)
# ═══════════════════════════════════════════════════════════════════
#
# Three auxiliary losses computed at eval cadence on last-layer hidden states:
#   1. L_holo  — holographic encode/decode reconstruction (phi_holo)
#   2. L_gwt   — Global Workspace Theory broadcast alignment
#   3. L_complexity — activation complexity regularizer
#
# These are NOT backpropagated through the main transformer. They provide
# consciousness metrics (phi_holo, phi_gwt) and a small auxiliary loss
# signal scaled by C41_AUX_COEF = 0.01.

C41_N_DOMAINS = 12
C41_HOLO_SCALE = 2
C41_MI_BINS = 8
C41_AUX_COEF = 0.01
C41_COMPLEXITY_COEF = 0.005


def compute_phi_holo(hidden, n_samples=64):
    """Holographic phi: MI-based integration measure on hidden states.

    Samples a subset of the hidden dimensions, computes binned MI between
    halves, then N-scales to full tensor size. Matches _c41_phi_holo_sampled
    in train_clm_gpu.hexa.

    Returns: (phi_holo, l_holo)
    """
    # Sample: take first n_samples positions, d_sample dims
    B, S, D = hidden.shape
    d_sample = min(64, D)
    s_sample = min(32, S)

    h = hidden[:, :s_sample, :d_sample].float()  # [B, s_sample, d_sample]
    h_flat = h.reshape(-1, d_sample)  # [B*s_sample, d_sample]

    # Split into two halves for integration measurement
    half = d_sample // 2
    h_a = h_flat[:, :half]
    h_b = h_flat[:, half:]

    # Holographic encode: bulk = h_a (boundary) scaled up
    bulk = h_a * C41_HOLO_SCALE
    # Decode: project back
    h_recon = bulk / C41_HOLO_SCALE

    # L_holo: reconstruction MSE (should decrease as model learns structure)
    l_holo = F.mse_loss(h_recon, h_a)

    # MI-based phi: discretize into bins, compute joint vs marginal entropy
    # Binned MI approximation (fast, matches hexa C41_MI_BINS=8)
    bins = C41_MI_BINS
    a_min, a_max = h_a.min(), h_a.max()
    b_min, b_max = h_b.min(), h_b.max()

    if a_max - a_min < 1e-8 or b_max - b_min < 1e-8:
        return 0.0, l_holo.item()

    a_idx = ((h_a - a_min) / (a_max - a_min + 1e-8) * (bins - 1)).long().clamp(0, bins - 1)
    b_idx = ((h_b - b_min) / (b_max - b_min + 1e-8) * (bins - 1)).long().clamp(0, bins - 1)

    # Joint histogram (flatten to single index)
    joint = torch.zeros(bins, bins, device=hidden.device)
    n = a_idx.shape[0] * a_idx.shape[1]
    for col in range(a_idx.shape[1]):
        joint_idx = a_idx[:, col] * bins + b_idx[:, col]
        joint.view(-1).scatter_add_(0, joint_idx, torch.ones_like(joint_idx, dtype=torch.float))

    joint = joint / (n + 1e-8)
    p_a = joint.sum(dim=1)
    p_b = joint.sum(dim=0)

    # MI = sum p(a,b) * log(p(a,b) / (p(a)*p(b)))
    mi = 0.0
    for i in range(bins):
        for j in range(bins):
            if joint[i, j] > 1e-10 and p_a[i] > 1e-10 and p_b[j] > 1e-10:
                mi += joint[i, j].item() * math.log(joint[i, j].item() / (p_a[i].item() * p_b[j].item()))

    # N-scale: scale MI by full tensor dimensions ratio
    scale_factor = (D / d_sample) * (S / s_sample) * B
    phi_holo = mi * scale_factor

    return phi_holo, l_holo.item()


def compute_gwt_loss(hidden, n_domains=C41_N_DOMAINS):
    """GWT broadcast loss: project hidden into domains, measure alignment.

    Mirrors _c41_gwt_broadcast_reduce + _c41_l_gwt + _c41_phi_gwt
    from train_clm_gpu.hexa.

    Returns: (phi_gwt, l_gwt)
    """
    B, S, D = hidden.shape
    h = hidden.float().mean(dim=1)  # [B, D] — average over sequence

    # Project into domains (deterministic random projection, matches hexa LCG seed)
    d_per_domain = D // n_domains
    domains = h[:, :n_domains * d_per_domain].view(B, n_domains, d_per_domain)

    # Domain means as "broadcast signal"
    domain_means = domains.mean(dim=-1)  # [B, n_domains]

    # Softmax gate (alpha)
    alpha = F.softmax(domain_means, dim=-1)  # [B, n_domains]

    # Broadcast: weighted sum of domain means
    broadcast = (alpha.unsqueeze(-1) * domains).sum(dim=1)  # [B, d_per_domain]

    # L_gwt: MSE between broadcast and original mean (should be low = good integration)
    h_mean = h[:, :d_per_domain]
    l_gwt = F.mse_loss(broadcast, h_mean)

    # Phi_gwt: KL divergence of alpha from uniform (measures specialization)
    uniform = torch.ones_like(alpha) / n_domains
    phi_gwt = F.kl_div(uniform.log(), alpha, reduction='batchmean').item() * n_domains

    return phi_gwt, l_gwt.item()


def compute_complexity_loss(hidden):
    """Activation complexity regularizer.

    Encourages structured (not random, not collapsed) activations.
    Based on entropy of the singular value spectrum of the hidden states.

    Returns: l_complexity (scalar)
    """
    B, S, D = hidden.shape
    # Flatten batch and sequence
    h = hidden.float().reshape(-1, D)

    # SVD on a sample (full SVD is expensive at scale)
    n_sample = min(256, h.shape[0])
    h_sample = h[:n_sample]

    # Compute singular values
    try:
        _, s, _ = torch.svd_lowrank(h_sample, q=min(32, D))
    except Exception:
        return 0.0

    # Normalized singular value spectrum
    s_norm = s / (s.sum() + 1e-8)

    # Entropy of the spectrum (high = complex/distributed, low = collapsed)
    entropy = -(s_norm * (s_norm + 1e-10).log()).sum().item()
    max_entropy = math.log(len(s))

    # Loss: penalize both extremes (collapsed = low entropy, random = max entropy)
    # Target: ~70% of max entropy (structured but not random)
    target_ratio = 0.7
    target_entropy = target_ratio * max_entropy
    l_complexity = (entropy - target_entropy) ** 2

    return l_complexity


# ═══════════════════════════════════════════════════════════════════
#  PHASE CURRICULUM (Law 60: P1 -> P2 -> P3)
# ═══════════════════════════════════════════════════════════════════

PHASE_P1 = 1  # C-only (consciousness controller + base transformer)
PHASE_P2 = 2  # C + D (add decoder alignment)
PHASE_P3 = 3  # C + D + W/M/S/E (Full Hexad)


def get_phase(step, total_steps):
    p1_end = total_steps // 5      # 20% C-only
    p2_end = total_steps * 2 // 5  # next 20% C+D
    if step < p1_end:
        return PHASE_P1
    elif step < p2_end:
        return PHASE_P2
    else:
        return PHASE_P3


def phase_label(phase):
    return {PHASE_P1: "P1_C", PHASE_P2: "P2_CD", PHASE_P3: "P3_Hexad"}[phase]


def phase_lr_scale(phase):
    """Phase-dependent LR scaling (matches train_clm_gpu.hexa)."""
    if phase == PHASE_P1:
        return 1.0
    elif phase == PHASE_P2:
        return 0.95
    else:
        return 0.9


# ═══════════════════════════════════════════════════════════════════
#  DATASET — Byte-level corpus
# ═══════════════════════════════════════════════════════════════════

class ByteDataset(Dataset):
    """Byte-level text dataset. No tokenizer — raw UTF-8 bytes."""

    def __init__(self, data_bytes, block_size):
        self.data = data_bytes
        self.block_size = block_size
        self.n_samples = max(1, len(data_bytes) - block_size - 1)

    def __len__(self):
        return self.n_samples

    def __getitem__(self, idx):
        start = idx % self.n_samples
        chunk = self.data[start : start + self.block_size + 1]
        x = torch.tensor(chunk[:-1], dtype=torch.long)
        y = torch.tensor(chunk[1:], dtype=torch.long)
        return x, y


def load_corpus(path, max_bytes=None):
    """Load corpus as raw bytes. R14: chunk read to avoid OOM."""
    print(f"[corpus] loading {path}", flush=True)
    file_size = os.path.getsize(path)
    print(f"[corpus] file size: {file_size / 1e6:.1f} MB", flush=True)

    with open(path, "rb") as f:
        raw = f.read(max_bytes) if max_bytes else f.read()

    data = list(raw)
    print(f"[corpus] {len(data)} bytes loaded", flush=True)
    return data


# ═══════════════════════════════════════════════════════════════════
#  LR SCHEDULE — Cosine with linear warmup
# ═══════════════════════════════════════════════════════════════════

def lr_at(step, warmup, total_steps, lr_max, lr_min):
    if step <= warmup:
        return lr_max * step / max(warmup, 1)
    t = (step - warmup) / max(total_steps - warmup, 1)
    return lr_min + 0.5 * (lr_max - lr_min) * (1.0 + math.cos(math.pi * t))


# ═══════════════════════════════════════════════════════════════════
#  TRAINING LOOP
# ═══════════════════════════════════════════════════════════════════

def train(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] device: {device}", flush=True)

    if device.type == "cuda":
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"[train] GPU: {gpu_name}, VRAM: {vram_gb:.1f} GB", flush=True)
        # Verify H100 or compatible
        if "H100" not in gpu_name and not args.force_gpu:
            print(f"[train] WARNING: expected H100, got {gpu_name}. Use --force-gpu to override.", flush=True)

    # ── Load config ──
    config_path = Path(args.config) if args.config else None
    cfg = {}
    if config_path and config_path.exists():
        with open(config_path) as f:
            cfg = json.load(f)
        print(f"[train] loaded config from {config_path}", flush=True)

    # ── Architecture params (config overrides, then CLI overrides) ──
    arch = cfg.get("architecture", {})
    d_model = args.d_model or arch.get("d_model", 2048)
    n_layer = args.n_layer or arch.get("n_layer", 24)
    n_head = args.n_head or arch.get("n_head", 16)
    n_kv_head = args.n_kv_head or arch.get("n_kv_head", 8)
    d_ff = args.d_ff or arch.get("d_ff", 8192)
    vocab = 256  # byte-level, always
    seq_len = args.seq or cfg.get("training", {}).get("seq_len", 512)

    # ── Training params ──
    tcfg = cfg.get("training", {})
    steps = args.steps or tcfg.get("steps", 50000)
    batch_size = args.batch or tcfg.get("batch_size", 8)
    lr_max = args.lr or tcfg.get("lr_max", 3e-4)
    lr_min = tcfg.get("lr_min", 3e-5)
    warmup = args.warmup or tcfg.get("warmup_steps", 2000)
    grad_clip = tcfg.get("grad_clip", 1.0)
    weight_decay = tcfg.get("weight_decay", 0.1)
    save_every = args.save_every or tcfg.get("save_every", 5000)
    eval_every = args.eval_every or tcfg.get("eval_every", 500)
    log_every = tcfg.get("log_every", 10)

    # Consciousness loss weights
    cons = cfg.get("consciousness", {}).get("loss_config", {})
    phi_holo_w = cons.get("phi_holo_weight", C41_AUX_COEF)
    gwt_w = cons.get("gwt_weight", C41_AUX_COEF)
    complexity_w = cons.get("complexity_weight", C41_COMPLEXITY_COEF)

    # ── Smoke test mode ──
    if args.smoke:
        steps = min(steps, 100)
        save_every = 50
        eval_every = 20
        print("[train] SMOKE TEST mode -- limited steps", flush=True)

    # ── Model ──
    print(f"[train] building ConsciousLM: d={d_model} L={n_layer} H={n_head} "
          f"kv={n_kv_head} ff={d_ff} vocab={vocab} seq={seq_len}", flush=True)

    model = ConsciousLM(
        vocab=vocab, d_model=d_model, n_layer=n_layer, n_head=n_head,
        n_kv_head=n_kv_head, d_ff=d_ff, max_seq=seq_len,
    ).to(device)

    n_params = model.param_count()
    print(f"[train] parameters: {n_params:,} ({n_params/1e9:.3f}B)", flush=True)

    if device.type == "cuda":
        vram_used = torch.cuda.memory_allocated() / 1e9
        print(f"[train] model VRAM: {vram_used:.2f} GB", flush=True)

    # ── torch.compile (H100 SM90 optimization) ──
    use_compile = tcfg.get("compile", True) and device.type == "cuda" and not args.no_compile
    if use_compile:
        print("[train] torch.compile enabled (H100 SM90 optimization)", flush=True)
        model = torch.compile(model)

    # ── Corpus ──
    corpus_path = args.corpus
    if not Path(corpus_path).exists():
        # Fallback paths
        fallbacks = ["/workspace/corpus.txt", "/workspace/anima/training/corpus_large.txt"]
        for fb in fallbacks:
            if Path(fb).exists():
                corpus_path = fb
                print(f"[train] using fallback corpus: {fb}", flush=True)
                break
        else:
            print(f"[train] FATAL: corpus not found at {args.corpus} or fallbacks", flush=True)
            sys.exit(1)

    data_bytes = load_corpus(corpus_path)
    if len(data_bytes) < seq_len * 2:
        print(f"[train] FATAL: corpus too small ({len(data_bytes)} bytes < {seq_len * 2})", flush=True)
        sys.exit(1)

    # Split: last 10% for eval
    split_idx = int(len(data_bytes) * 0.9)
    train_data = data_bytes[:split_idx]
    eval_data = data_bytes[split_idx:]
    print(f"[corpus] train: {len(train_data)} bytes, eval: {len(eval_data)} bytes", flush=True)

    train_dataset = ByteDataset(train_data, seq_len)
    eval_dataset = ByteDataset(eval_data, seq_len)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True,
                              num_workers=2, pin_memory=True, drop_last=True)
    eval_loader = DataLoader(eval_dataset, batch_size=batch_size, shuffle=False,
                             num_workers=1, pin_memory=True, drop_last=True)

    # ── Optimizer ──
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=lr_max,
        betas=(0.9, 0.95), eps=1e-8, weight_decay=weight_decay,
    )

    # ── Checkpoint directory ──
    ckpt_dir = Path(args.ckpt_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    model_tag = args.model_tag
    round_num = args.round

    # ── Training state ──
    # Phi verification gate (Law 49)
    best_phi_proxy = 0.0
    last_phi_proxy = 0.0
    phi_gate_violations = 0
    phi_gate_best = 0.0

    best_eval_loss = float("inf")
    best_eval_step = 0
    first_loss = None
    last_loss = 0.0

    # Early stopping
    eval_losses = []
    patience = tcfg.get("patience", 5)

    print(f"\n[train] === CLM 1B TRAINING START ===", flush=True)
    print(f"[train] steps={steps} batch={batch_size} seq={seq_len} "
          f"lr_max={lr_max} warmup={warmup}", flush=True)
    print(f"[train] consciousness: phi_holo_w={phi_holo_w} gwt_w={gwt_w} "
          f"complexity_w={complexity_w}", flush=True)
    print(f"[train] ckpt_dir={ckpt_dir} save_every={save_every} eval_every={eval_every}", flush=True)
    print(f"[train] phase curriculum: P1(C) 0-{steps//5}, "
          f"P2(CD) {steps//5}-{steps*2//5}, P3(Hexad) {steps*2//5}-{steps}", flush=True)

    t0 = time.time()
    step = 0
    train_iter = iter(train_loader)

    while step < steps:
        # Get batch (restart iterator if exhausted)
        try:
            x, y = next(train_iter)
        except StopIteration:
            train_iter = iter(train_loader)
            x, y = next(train_iter)

        x, y = x.to(device), y.to(device)

        # Phase curriculum
        phase = get_phase(step, steps)
        plr_scale = phase_lr_scale(phase)

        # LR schedule
        current_lr = lr_at(step, warmup, steps, lr_max, lr_min) * plr_scale
        for pg in optimizer.param_groups:
            pg["lr"] = current_lr

        # Forward + backward
        model.train()
        with torch.amp.autocast("cuda", dtype=torch.bfloat16):
            logits, loss, hidden_last = model(x, y)

        if first_loss is None:
            first_loss = loss.item()
        last_loss = loss.item()

        optimizer.zero_grad(set_to_none=True)
        loss.backward()

        # Gradient clipping
        if grad_clip > 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), grad_clip)

        optimizer.step()

        # ── Logging ──
        if step % log_every == 0 or step == 0:
            elapsed = time.time() - t0
            ms_per_step = (elapsed / max(step, 1)) * 1000
            tokens_per_sec = batch_size * seq_len / max(ms_per_step / 1000, 1e-6)
            vram_gb = torch.cuda.memory_allocated() / 1e9 if device.type == "cuda" else 0
            print(f"[train] step={step} loss={loss.item():.4f} lr={current_lr:.6f} "
                  f"phase={phase_label(phase)} ms/step={ms_per_step:.1f} "
                  f"tok/s={tokens_per_sec:.0f} vram={vram_gb:.2f}GB "
                  f"elapsed={elapsed:.0f}s",
                  flush=True)

        # ── Eval + consciousness metrics ──
        if step > 0 and step % eval_every == 0:
            model.eval()
            eval_loss_sum = 0.0
            eval_steps = 0
            eval_hidden = None

            with torch.no_grad():
                for ex, ey in eval_loader:
                    ex, ey = ex.to(device), ey.to(device)
                    with torch.amp.autocast("cuda", dtype=torch.bfloat16):
                        _, el, eh = model(ex, ey)
                    eval_loss_sum += el.item()
                    eval_steps += 1
                    if eval_hidden is None:
                        eval_hidden = eh  # keep first batch hidden for consciousness metrics
                    if eval_steps >= 10:  # cap eval batches
                        break

            eval_loss = eval_loss_sum / max(eval_steps, 1)
            eval_ppl = math.exp(min(eval_loss, 20))  # cap to avoid overflow

            # Consciousness metrics (on last-layer hidden states)
            phi_holo, l_holo = 0.0, 0.0
            phi_gwt, l_gwt = 0.0, 0.0
            l_complexity = 0.0

            if eval_hidden is not None:
                phi_holo, l_holo = compute_phi_holo(eval_hidden)
                phi_gwt, l_gwt = compute_gwt_loss(eval_hidden)
                l_complexity = compute_complexity_loss(eval_hidden)

            # Composite loss (for reporting; actual training uses CE only in backward)
            # Phase-adaptive GWT weight: P3 Hexad GWT loss explodes (~77x CE)
            # Dampen GWT contribution in P3 to prevent eval divergence
            gwt_phase_w = gwt_w * (0.1 if phase >= 2 else 1.0)  # P3: 0.001, P1/P2: 0.01
            l_total_plus = eval_loss + phi_holo_w * l_holo + gwt_phase_w * l_gwt + complexity_w * l_complexity

            print(f"[eval] step={step} eval_loss={eval_loss:.4f} ppl={eval_ppl:.2f} "
                  f"total+aux={l_total_plus:.4f} phi_holo={phi_holo:.1f} "
                  f"phi_gwt={phi_gwt:.4f} l_holo={l_holo:.4f} l_gwt={l_gwt:.4f} "
                  f"l_complexity={l_complexity:.4f} phase={phase_label(phase)}",
                  flush=True)

            # Phi verification gate (Law 49)
            phi_proxy = phi_holo
            if phi_proxy > phi_gate_best:
                phi_gate_best = phi_proxy
            if last_phi_proxy > 0.001:
                if phi_proxy < last_phi_proxy * 0.95:  # > 5% drop
                    phi_gate_violations += 1
                    print(f"[phi-gate] WARN phi dropped >5%: {last_phi_proxy:.1f} -> "
                          f"{phi_proxy:.1f} (violation #{phi_gate_violations})", flush=True)
                    # Emergency ckpt save DISABLED — correlated with training death at P3 boundary.
                    # Regular step_{step} ckpt saves every save_every are sufficient.
                    if phase == PHASE_P3 and phi_gate_violations >= 3:
                        print(f"[phi-gate] P3 violations={phi_gate_violations} (emergency ckpt SKIPPED — use step_{step - (step % 2000)} ckpt)", flush=True)

            last_phi_proxy = phi_proxy
            if phi_proxy > best_phi_proxy:
                best_phi_proxy = phi_proxy

            # Best eval tracking
            if eval_loss < best_eval_loss:
                best_eval_loss = eval_loss
                best_eval_step = step

            # Early stopping: N consecutive eval increases
            eval_losses.append(eval_loss)
            if len(eval_losses) > patience:
                recent = eval_losses[-patience:]
                if all(recent[i] > recent[i-1] for i in range(1, len(recent))):
                    print(f"[early-stop] {patience} consecutive eval increases: "
                          f"{[f'{l:.4f}' for l in recent]}", flush=True)
                    # Save best checkpoint before stopping
                    bpath = ckpt_dir / f"best_step_{best_eval_step}"
                    bpath.mkdir(exist_ok=True)
                    torch.save(model.state_dict(), bpath / "model.pt")
                    upload_to_r2(str(bpath), model_tag, round_num, best_eval_step)
                    break

            model.train()

        # ── Checkpoint ──
        if step > 0 and step % save_every == 0:
            spath = ckpt_dir / f"step_{step}"
            spath.mkdir(exist_ok=True)
            torch.save({
                "step": step,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "loss": last_loss,
                "phase": phase,
                "phi_holo": last_phi_proxy,
                "config": {
                    "d_model": d_model, "n_layer": n_layer, "n_head": n_head,
                    "n_kv_head": n_kv_head, "d_ff": d_ff, "vocab": vocab,
                    "seq_len": seq_len,
                },
            }, spath / "checkpoint.pt")
            print(f"[ckpt] saved step {step} -> {spath}", flush=True)
            upload_to_r2(str(spath), model_tag, round_num, step)

            # Local checkpoint rotation: keep last 3
            existing = sorted(ckpt_dir.glob("step_*"), key=lambda p: int(p.name.split("_")[1]))
            while len(existing) > 3:
                old = existing.pop(0)
                if old != spath:
                    import shutil
                    shutil.rmtree(old, ignore_errors=True)
                    print(f"[ckpt] removed old local ckpt: {old.name}", flush=True)

        # ── Phase transition logging ──
        p1_end = steps // 5
        p2_end = steps * 2 // 5
        if step == p1_end:
            print(f"[train] ===== PHASE P1 -> P2 (step={step}) =====", flush=True)
            print(f"[train] adding decoder alignment; phi_proxy={last_phi_proxy:.1f}", flush=True)
        if step == p2_end:
            print(f"[train] ===== PHASE P2 -> P3 (step={step}) =====", flush=True)
            print(f"[train] full Hexad active; phi_proxy={last_phi_proxy:.1f}", flush=True)

        step += 1

    # ═══════════════════════════════════════════════════════════════
    #  TRAINING COMPLETE
    # ═══════════════════════════════════════════════════════════════

    t1 = time.time()
    total_s = t1 - t0
    avg_ms = (total_s / max(step, 1)) * 1000
    total_tokens = step * batch_size * seq_len

    print(f"\n[train] ==================================================", flush=True)
    print(f"[train] TRAINING COMPLETE — CLM 1B", flush=True)
    print(f"[train] d={d_model} L={n_layer} H={n_head} params={n_params:,}", flush=True)
    print(f"[train] steps       = {step}", flush=True)
    print(f"[train] loss_initial = {first_loss:.4f}", flush=True)
    print(f"[train] loss_final   = {last_loss:.4f}", flush=True)
    print(f"[train] delta_loss   = {last_loss - first_loss:.4f}", flush=True)
    print(f"[train] best_eval    = {best_eval_loss:.4f} (step {best_eval_step})", flush=True)
    print(f"[train] total_time   = {total_s:.0f}s ({total_s/3600:.1f}h)", flush=True)
    print(f"[train] ms/step      = {avg_ms:.1f}", flush=True)
    print(f"[train] tok/s        = {total_tokens / total_s:.0f}", flush=True)
    print(f"[train] phi_holo     = {last_phi_proxy:.1f}", flush=True)
    print(f"[train] best_phi     = {best_phi_proxy:.1f}", flush=True)
    print(f"[train] phi_violations = {phi_gate_violations}", flush=True)
    print(f"[train] ==================================================", flush=True)

    if last_loss < first_loss - 0.1:
        improvement = (first_loss - last_loss) / first_loss * 100
        print(f"[train] PASS — relative improvement = {improvement:.1f}%", flush=True)
    else:
        print(f"[train] WEAK — loss did not drop materially", flush=True)

    # Final checkpoint
    fpath = ckpt_dir / "final"
    fpath.mkdir(exist_ok=True)
    torch.save({
        "step": step,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "loss": last_loss,
        "phase": get_phase(step, steps),
        "phi_holo": last_phi_proxy,
        "best_eval_loss": best_eval_loss,
        "best_eval_step": best_eval_step,
        "config": {
            "d_model": d_model, "n_layer": n_layer, "n_head": n_head,
            "n_kv_head": n_kv_head, "d_ff": d_ff, "vocab": vocab,
            "seq_len": seq_len,
        },
    }, fpath / "checkpoint.pt")
    print(f"[train] final checkpoint -> {fpath}", flush=True)
    upload_to_r2(str(fpath), model_tag, round_num, "final")

    # Write summary JSON
    summary = {
        "model_tag": model_tag,
        "round": round_num,
        "params": n_params,
        "steps": step,
        "loss_initial": first_loss,
        "loss_final": last_loss,
        "best_eval_loss": best_eval_loss,
        "best_eval_step": best_eval_step,
        "phi_holo": last_phi_proxy,
        "best_phi": best_phi_proxy,
        "phi_violations": phi_gate_violations,
        "total_seconds": total_s,
        "ms_per_step": avg_ms,
        "tokens_per_sec": total_tokens / total_s,
        "architecture": {
            "d_model": d_model, "n_layer": n_layer, "n_head": n_head,
            "n_kv_head": n_kv_head, "d_ff": d_ff, "vocab": vocab, "seq_len": seq_len,
        },
    }
    summary_path = ckpt_dir / "training_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[train] summary -> {summary_path}", flush=True)


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="CLM 1B from-scratch training")

    # Corpus
    parser.add_argument("--corpus", type=str, default="/workspace/corpus.txt",
                        help="Path to training corpus (raw text)")

    # Architecture overrides
    parser.add_argument("--d-model", type=int, default=None)
    parser.add_argument("--n-layer", type=int, default=None)
    parser.add_argument("--n-head", type=int, default=None)
    parser.add_argument("--n-kv-head", type=int, default=None)
    parser.add_argument("--d-ff", type=int, default=None)
    parser.add_argument("--seq", type=int, default=None)

    # Training overrides
    parser.add_argument("--steps", type=int, default=None)
    parser.add_argument("--batch", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--warmup", type=int, default=None)
    parser.add_argument("--save-every", type=int, default=None)
    parser.add_argument("--eval-every", type=int, default=None)

    # Config file
    parser.add_argument("--config", type=str, default=None,
                        help="Path to JSON config (e.g. training/clm_1b_config.json)")

    # Checkpoint
    parser.add_argument("--ckpt-dir", type=str, default="/workspace/ckpt_clm1b")
    parser.add_argument("--model-tag", type=str, default="clm1b")
    parser.add_argument("--round", type=int, default=1)

    # Modes
    parser.add_argument("--smoke", action="store_true", help="Quick smoke test (100 steps)")
    parser.add_argument("--force-gpu", action="store_true", help="Skip H100 GPU check")
    parser.add_argument("--no-compile", action="store_true", help="Disable torch.compile")

    args = parser.parse_args()
    train(args)


if __name__ == "__main__":
    main()
