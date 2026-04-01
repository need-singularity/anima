#!/usr/bin/env python3
"""acceleration_h7_h12.py -- H7-H12 Decoder Training Acceleration (Part 2)

Attacking the 85% decoder backprop bottleneck with 6 new techniques.

H7:  Flash/Efficient Attention simulation (chunked attention, memory vs speed)
H8:  Mixture of Depths / Early Exit (confidence-based layer skip)
H9:  DiLoCo simulation (N independent models, periodic weight averaging)
H10: Knowledge Distillation (teacher 256d/4L -> student 128d/2L)
H11: Data Selection (hard-token curriculum, loss-weighted sampling)
H12: LoRA -> Full Fine-tune (adapter phase -> full phase)

All experiments: local CPU, 128d-256d, real forward+backward timing.
PYTHONUNBUFFERED=1

Usage:
  python acceleration_h7_h12.py           # Run all
  python acceleration_h7_h12.py --h7      # H7 only
  python acceleration_h7_h12.py --h8      # H8 only
  python acceleration_h7_h12.py --h9      # H9 only
  python acceleration_h7_h12.py --h10     # H10 only
  python acceleration_h7_h12.py --h11     # H11 only
  python acceleration_h7_h12.py --h12     # H12 only
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


# ===================================================================
# Utilities
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
        step_size = max(1, len(values) // width)
        for i in range(0, min(len(values), width * step_size), step_size):
            v = values[i]
            if v >= threshold:
                line += "#"
            else:
                line += " "
        label = f"{threshold:.4f}" if row in (0, height // 2, height) else ""
        print(f"  {label:>9s} |{line}")
    print(f"  {'':>9s} +{''.join(['-'] * min(width, len(values)))}")
    print(f"  {'':>9s}  {'0':}<{min(width, len(values)) // 2}{'step':>}")
    sys.stdout.flush()


def make_corpus(n_tokens: int = 4096, vocab: int = 256) -> torch.Tensor:
    """Generate synthetic byte corpus with patterns (not pure random)."""
    data = []
    # Mix of patterns: repeated sequences, arithmetic, natural-ish
    while len(data) < n_tokens:
        pattern_type = np.random.randint(4)
        if pattern_type == 0:
            # Repeated motif
            motif_len = np.random.randint(3, 12)
            motif = np.random.randint(0, vocab, motif_len)
            repeats = np.random.randint(3, 10)
            data.extend(list(np.tile(motif, repeats)))
        elif pattern_type == 1:
            # Arithmetic sequence
            start = np.random.randint(0, vocab)
            step = np.random.randint(1, 5)
            length = np.random.randint(10, 40)
            data.extend([(start + i * step) % vocab for i in range(length)])
        elif pattern_type == 2:
            # Korean-ish byte patterns (UTF-8 3-byte hangul)
            for _ in range(np.random.randint(5, 15)):
                data.extend([0xEA + np.random.randint(0, 6),
                             0x80 + np.random.randint(0, 64),
                             0x80 + np.random.randint(0, 64)])
        else:
            # Random noise
            length = np.random.randint(5, 20)
            data.extend(list(np.random.randint(0, vocab, length)))
    return torch.tensor(data[:n_tokens], dtype=torch.long)


# ===================================================================
# Mini Decoder (simplified DecoderV2 for experiments)
# ===================================================================

class RMSNorm(nn.Module):
    def __init__(self, dim, eps=1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x):
        rms = torch.rsqrt(x.float().pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return (x.float() * rms).type_as(x) * self.weight


class SwiGLUFFN(nn.Module):
    def __init__(self, d_model, dropout=0.1):
        super().__init__()
        d_inner = ((int(d_model * 2.0) + 7) // 8) * 8
        self.gate_proj = nn.Linear(d_model, d_inner, bias=False)
        self.up_proj = nn.Linear(d_model, d_inner, bias=False)
        self.down_proj = nn.Linear(d_inner, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        return self.dropout(self.down_proj(
            F_torch.silu(self.gate_proj(x)) * self.up_proj(x)
        ))


class MiniAttention(nn.Module):
    """Standard causal self-attention (no GQA for simplicity)."""

    def __init__(self, d_model, n_head=4, block_size=128, dropout=0.1):
        super().__init__()
        self.n_head = n_head
        self.head_dim = d_model // n_head
        self.qkv = nn.Linear(d_model, 3 * d_model, bias=False)
        self.o_proj = nn.Linear(d_model, d_model, bias=False)
        self.attn_drop = nn.Dropout(dropout)
        self.resid_drop = nn.Dropout(dropout)
        self.register_buffer("bias",
            torch.tril(torch.ones(block_size, block_size)).view(1, 1, block_size, block_size))

    def forward(self, x):
        B, T, D = x.size()
        qkv = self.qkv(x).view(B, T, 3, self.n_head, self.head_dim)
        q, k, v = qkv.unbind(dim=2)
        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)
        att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
        att = att.masked_fill(self.bias[:, :, :T, :T] == 0, float("-inf"))
        att = F_torch.softmax(att, dim=-1)
        att = self.attn_drop(att)
        y = (att @ v).transpose(1, 2).contiguous().view(B, T, D)
        return self.resid_drop(self.o_proj(y))


class ChunkedAttention(nn.Module):
    """Chunked causal attention -- simulates Flash Attention memory savings."""

    def __init__(self, d_model, n_head=4, block_size=128, dropout=0.1, chunk_size=32):
        super().__init__()
        self.n_head = n_head
        self.head_dim = d_model // n_head
        self.chunk_size = chunk_size
        self.qkv = nn.Linear(d_model, 3 * d_model, bias=False)
        self.o_proj = nn.Linear(d_model, d_model, bias=False)
        self.attn_drop = nn.Dropout(dropout)
        self.resid_drop = nn.Dropout(dropout)

    def forward(self, x):
        B, T, D = x.size()
        qkv = self.qkv(x).view(B, T, 3, self.n_head, self.head_dim)
        q, k, v = qkv.unbind(dim=2)
        q = q.transpose(1, 2)  # B, H, T, D
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        # Process in chunks
        outputs = []
        cs = self.chunk_size
        for start in range(0, T, cs):
            end = min(start + cs, T)
            q_chunk = q[:, :, start:end, :]
            # Can attend to all positions up to end (causal)
            k_ctx = k[:, :, :end, :]
            v_ctx = v[:, :, :end, :]
            att = (q_chunk @ k_ctx.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
            # Causal mask for this chunk
            chunk_len = end - start
            ctx_len = end
            mask = torch.ones(chunk_len, ctx_len, device=x.device, dtype=torch.bool)
            for i in range(chunk_len):
                mask[i, start + i + 1:] = False
            att = att.masked_fill(~mask.unsqueeze(0).unsqueeze(0), float("-inf"))
            att = F_torch.softmax(att, dim=-1)
            att = self.attn_drop(att)
            outputs.append(att @ v_ctx)

        y = torch.cat(outputs, dim=2)
        y = y.transpose(1, 2).contiguous().view(B, T, D)
        return self.resid_drop(self.o_proj(y))


class MiniDecoderBlock(nn.Module):
    """Simplified decoder block: attn + FFN."""

    def __init__(self, d_model, n_head=4, block_size=128, dropout=0.1,
                 attn_cls=None):
        super().__init__()
        self.ln1 = RMSNorm(d_model)
        if attn_cls is not None:
            self.attn = attn_cls
        else:
            self.attn = MiniAttention(d_model, n_head, block_size, dropout)
        self.ln2 = RMSNorm(d_model)
        self.ffn = SwiGLUFFN(d_model, dropout)

    def forward(self, x):
        x = x + self.attn(self.ln1(x))
        x = x + self.ffn(self.ln2(x))
        return x


class MiniDecoder(nn.Module):
    """Small decoder for experiments. DecoderV2-like but minimal."""

    def __init__(self, vocab_size=256, d_model=128, n_head=4, n_layer=4,
                 block_size=128, dropout=0.1, attn_cls_list=None):
        super().__init__()
        self.block_size = block_size
        self.d_model = d_model
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.drop = nn.Dropout(dropout)
        if attn_cls_list is not None:
            self.blocks = nn.ModuleList([
                MiniDecoderBlock(d_model, n_head, block_size, dropout, attn_cls=a)
                for a in attn_cls_list
            ])
        else:
            self.blocks = nn.ModuleList([
                MiniDecoderBlock(d_model, n_head, block_size, dropout)
                for _ in range(n_layer)
            ])
        self.ln_f = RMSNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)
        self.tok_emb.weight = self.head.weight
        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, std=0.02)

    def forward(self, idx):
        x = self.drop(self.tok_emb(idx))
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        return self.head(x)

    def param_count(self):
        return sum(p.numel() for p in self.parameters())


class MiniDecoderEarlyExit(nn.Module):
    """Decoder with early exit capability (H8)."""

    def __init__(self, vocab_size=256, d_model=128, n_head=4, n_layer=4,
                 block_size=128, dropout=0.1, exit_threshold=0.8):
        super().__init__()
        self.block_size = block_size
        self.d_model = d_model
        self.n_layer = n_layer
        self.exit_threshold = exit_threshold
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList([
            MiniDecoderBlock(d_model, n_head, block_size, dropout)
            for _ in range(n_layer)
        ])
        self.ln_f = RMSNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)
        self.tok_emb.weight = self.head.weight
        # Per-layer exit heads (lightweight)
        self.exit_heads = nn.ModuleList([
            nn.Linear(d_model, vocab_size, bias=False) for _ in range(n_layer)
        ])
        self.apply(self._init_weights)
        self._exit_stats = [0] * (n_layer + 1)  # count exits per layer

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, std=0.02)

    def forward(self, idx, early_exit=True):
        B, T = idx.shape
        x = self.drop(self.tok_emb(idx))

        if not early_exit or self.training:
            # During training, run all layers, auxiliary losses from each exit
            logits_list = []
            for i, block in enumerate(self.blocks):
                x = block(x)
                logits_list.append(self.exit_heads[i](x))
            x = self.ln_f(x)
            final_logits = self.head(x)
            logits_list.append(final_logits)
            return final_logits, logits_list

        # Inference with early exit
        for i, block in enumerate(self.blocks):
            x = block(x)
            logits = self.exit_heads[i](x)
            probs = F_torch.softmax(logits, dim=-1)
            confidence = probs.max(dim=-1).values.mean()
            if confidence > self.exit_threshold:
                self._exit_stats[i] += 1
                return logits, None

        x = self.ln_f(x)
        self._exit_stats[self.n_layer] += 1
        return self.head(x), None

    def get_exit_stats(self):
        total = sum(self._exit_stats)
        if total == 0:
            return self._exit_stats, [0.0] * len(self._exit_stats)
        return self._exit_stats, [c / total for c in self._exit_stats]

    def reset_exit_stats(self):
        self._exit_stats = [0] * (self.n_layer + 1)


# ===================================================================
# LoRA Wrapper (H12)
# ===================================================================

class LoRALinear(nn.Module):
    """LoRA adapter: W' = W + alpha * B @ A."""

    def __init__(self, linear: nn.Linear, rank: int = 4, alpha: float = 1.0):
        super().__init__()
        self.linear = linear
        self.rank = rank
        self.alpha = alpha
        d_out, d_in = linear.weight.shape
        self.lora_A = nn.Parameter(torch.randn(rank, d_in) * 0.01)
        self.lora_B = nn.Parameter(torch.zeros(d_out, rank))
        # Freeze original weights
        self.linear.weight.requires_grad = False
        if self.linear.bias is not None:
            self.linear.bias.requires_grad = False

    def forward(self, x):
        base = self.linear(x)
        lora = (x @ self.lora_A.T) @ self.lora_B.T * (self.alpha / self.rank)
        return base + lora


def apply_lora(model: MiniDecoder, rank: int = 4, alpha: float = 1.0):
    """Apply LoRA to all linear layers in the model (except embedding/head)."""
    lora_params = []
    for name, module in model.named_modules():
        if isinstance(module, MiniDecoderBlock):
            # Apply to attention and FFN linear layers
            for subname, submod in module.named_modules():
                if isinstance(submod, nn.Linear) and 'ln' not in subname:
                    parent_name = subname.rsplit('.', 1)
                    if len(parent_name) == 2:
                        parent = dict(module.named_modules())[parent_name[0]]
                        attr = parent_name[1]
                    else:
                        parent = module
                        attr = subname
                    lora = LoRALinear(submod, rank=rank, alpha=alpha)
                    setattr(parent, attr, lora)
                    lora_params.extend([lora.lora_A, lora.lora_B])
    return lora_params


def unfreeze_all(model: MiniDecoder):
    """Unfreeze all parameters (for full fine-tune after LoRA phase)."""
    for p in model.parameters():
        p.requires_grad = True


def merge_lora(model: MiniDecoder):
    """Merge LoRA weights into base weights and remove adapters."""
    for name, module in model.named_modules():
        if isinstance(module, LoRALinear):
            with torch.no_grad():
                module.linear.weight += (module.lora_B @ module.lora_A) * (module.alpha / module.rank)
            module.linear.weight.requires_grad = True
            # Replace LoRALinear with plain Linear
            parent_name = name.rsplit('.', 1)
            if len(parent_name) == 2:
                parent = dict(model.named_modules())[parent_name[0]]
                setattr(parent, parent_name[1], module.linear)


# ===================================================================
# Training utility
# ===================================================================

def train_decoder(model, corpus, n_steps=300, lr=3e-4, block_size=128,
                  optimizer=None, loss_weights=None, measure_time=True):
    """Train a mini decoder and return CE curve + timing."""
    if optimizer is None:
        optimizer = torch.optim.AdamW(
            [p for p in model.parameters() if p.requires_grad], lr=lr
        )
    model.train()
    ces = []
    total_time = 0.0

    for step in range(n_steps):
        # Random batch
        ix = torch.randint(0, len(corpus) - block_size - 1, (4,))
        x = torch.stack([corpus[i:i + block_size] for i in ix])
        y = torch.stack([corpus[i + 1:i + block_size + 1] for i in ix])

        t0 = time.time()
        logits = model(x)
        if isinstance(logits, tuple):
            logits = logits[0]  # Handle early-exit model

        # CE loss with optional per-token weighting
        if loss_weights is not None:
            ce_per_token = F_torch.cross_entropy(
                logits.view(-1, logits.size(-1)), y.view(-1), reduction='none'
            )
            # Map token indices to weights
            w = loss_weights[y.view(-1)]
            loss = (ce_per_token * w).mean()
        else:
            loss = F_torch.cross_entropy(logits.view(-1, logits.size(-1)), y.view(-1))

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        dt = time.time() - t0
        total_time += dt
        ces.append(loss.item())

        if step % 50 == 0 or step == n_steps - 1:
            print(f"    step {step:4d}/{n_steps}  CE={loss.item():.4f}  "
                  f"dt={dt * 1000:.1f}ms")
            sys.stdout.flush()

    avg_step_ms = total_time / n_steps * 1000
    return ces, total_time, avg_step_ms


def train_decoder_early_exit(model, corpus, n_steps=300, lr=3e-4, block_size=128):
    """Train early-exit decoder with auxiliary losses at each layer."""
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)
    model.train()
    ces = []
    total_time = 0.0

    for step in range(n_steps):
        ix = torch.randint(0, len(corpus) - block_size - 1, (4,))
        x = torch.stack([corpus[i:i + block_size] for i in ix])
        y = torch.stack([corpus[i + 1:i + block_size + 1] for i in ix])

        t0 = time.time()
        final_logits, all_logits = model(x, early_exit=False)

        # Loss from final layer
        loss = F_torch.cross_entropy(final_logits.view(-1, 256), y.view(-1))
        # Auxiliary losses (weighted lower)
        for i, lg in enumerate(all_logits[:-1]):
            aux_w = 0.3 * (1.0 - i / len(all_logits))  # decreasing weight
            loss += aux_w * F_torch.cross_entropy(lg.view(-1, 256), y.view(-1))

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        dt = time.time() - t0
        total_time += dt
        final_ce = F_torch.cross_entropy(final_logits.view(-1, 256), y.view(-1)).item()
        ces.append(final_ce)

        if step % 50 == 0 or step == n_steps - 1:
            print(f"    step {step:4d}/{n_steps}  CE={final_ce:.4f}  "
                  f"dt={dt * 1000:.1f}ms")
            sys.stdout.flush()

    return ces, total_time, total_time / n_steps * 1000


# ===================================================================
# H7: Flash/Efficient Attention Simulation
# ===================================================================

def run_h7():
    print_header("H7: Flash/Efficient Attention Simulation")
    print("  Comparing standard vs chunked attention at different seq lengths.")
    print("  Flash Attention on H100 gives 2-3x; here we test the chunked approach.")
    sys.stdout.flush()

    d_model = 128
    n_head = 4
    n_layer = 4
    corpus = make_corpus(8192)
    n_steps = 200

    results = []
    for seq_len in [64, 128, 256]:
        print(f"\n  --- seq_len={seq_len} ---")
        sys.stdout.flush()

        # Standard attention
        print(f"  [Standard Attention]")
        model_std = MiniDecoder(d_model=d_model, n_head=n_head, n_layer=n_layer,
                                block_size=seq_len)
        ces_std, time_std, ms_std = train_decoder(model_std, corpus, n_steps=n_steps,
                                                   block_size=seq_len)

        # Chunked attention (chunk_size=32)
        print(f"  [Chunked Attention (chunk=32)]")
        chunk_attns = [ChunkedAttention(d_model, n_head, seq_len, chunk_size=32)
                       for _ in range(n_layer)]
        model_chunked = MiniDecoder(d_model=d_model, n_head=n_head, n_layer=n_layer,
                                     block_size=seq_len, attn_cls_list=chunk_attns)
        ces_chunked, time_chunked, ms_chunked = train_decoder(model_chunked, corpus,
                                                                n_steps=n_steps,
                                                                block_size=seq_len)

        results.append((seq_len, ces_std[-1], ms_std, ces_chunked[-1], ms_chunked))

    # Summary table
    print(f"\n  H7 Summary:")
    headers = ["SeqLen", "Std CE", "Std ms/step", "Chunk CE", "Chunk ms/step", "Speedup"]
    rows = []
    for seq_len, std_ce, std_ms, chunk_ce, chunk_ms in results:
        speedup = std_ms / max(chunk_ms, 0.01)
        rows.append((seq_len, f"{std_ce:.4f}", f"{std_ms:.1f}", f"{chunk_ce:.4f}",
                      f"{chunk_ms:.1f}", f"{speedup:.2f}x"))
    print_table(headers, rows)

    # ASCII comparison
    print(f"\n  Speed comparison (ms/step):")
    max_ms = max(r[2] for r in results + [(0, 0, 1, 0, 1)])
    for seq_len, std_ce, std_ms, chunk_ce, chunk_ms in results:
        ascii_bar(f"Std  seq={seq_len}", std_ms, max_ms * 1.2)
        ascii_bar(f"Chunk seq={seq_len}", chunk_ms, max_ms * 1.2)

    print(f"\n  H7 Insight: Chunked attention reduces peak memory O(T^2)->O(T*chunk).")
    print(f"  On H100, FlashAttention2 gives true 2-3x with fused CUDA kernels.")
    sys.stdout.flush()
    return results


# ===================================================================
# H8: Mixture of Depths (Early Exit)
# ===================================================================

def run_h8():
    print_header("H8: Mixture of Depths / Early Exit")
    print("  Not all tokens need all 4 layers. High-confidence tokens exit early.")
    sys.stdout.flush()

    d_model = 128
    n_layer = 4
    block_size = 128
    corpus = make_corpus(8192)
    n_steps = 200

    results = []
    # Baseline: full 4L
    print(f"\n  [Baseline: Full 4L]")
    model_full = MiniDecoder(d_model=d_model, n_layer=n_layer, block_size=block_size)
    ces_full, time_full, ms_full = train_decoder(model_full, corpus, n_steps=n_steps,
                                                   block_size=block_size)

    # Early exit at different thresholds
    for threshold in [0.5, 0.7, 0.9]:
        print(f"\n  [Early Exit threshold={threshold}]")
        model_ee = MiniDecoderEarlyExit(d_model=d_model, n_layer=n_layer,
                                         block_size=block_size,
                                         exit_threshold=threshold)
        ces_ee, time_ee, ms_ee = train_decoder_early_exit(
            model_ee, corpus, n_steps=n_steps, block_size=block_size)

        # Test inference speed with early exit
        model_ee.eval()
        model_ee.reset_exit_stats()
        inf_time = 0.0
        n_inf = 100
        with torch.no_grad():
            for _ in range(n_inf):
                ix = torch.randint(0, len(corpus) - block_size - 1, (1,))
                x = corpus[ix[0]:ix[0] + block_size].unsqueeze(0)
                t0 = time.time()
                _ = model_ee(x, early_exit=True)
                inf_time += time.time() - t0

        stats, ratios = model_ee.get_exit_stats()
        avg_layers = sum((i + 1) * r for i, r in enumerate(ratios))
        if ratios[-1] > 0:
            avg_layers = sum((i + 1) * r for i, r in enumerate(ratios))
        else:
            avg_layers = sum((i + 1) * r for i, r in enumerate(ratios))

        results.append((threshold, ces_ee[-1], ms_ee,
                         inf_time / n_inf * 1000, avg_layers, stats, ratios))

    # Summary table
    print(f"\n  H8 Summary (Train CE + Inference Speed):")
    headers = ["Threshold", "Final CE", "Train ms", "Inf ms", "Avg Layers", "Exit Dist"]
    rows = [("Full 4L", f"{ces_full[-1]:.4f}", f"{ms_full:.1f}", "-", "4.0", "-")]
    for thr, ce, tms, ims, avgL, stats, ratios in results:
        exit_dist = " ".join([f"L{i}:{r:.0%}" for i, r in enumerate(ratios) if r > 0])
        rows.append((f"EE={thr}", f"{ce:.4f}", f"{tms:.1f}", f"{ims:.2f}",
                      f"{avgL:.2f}", exit_dist))
    print_table(headers, rows)

    # Exit distribution visualization
    for thr, ce, tms, ims, avgL, stats, ratios in results:
        print(f"\n  Exit distribution (threshold={thr}):")
        for i, r in enumerate(ratios):
            layer_name = f"Layer {i}" if i < len(ratios) - 1 else "Final"
            ascii_bar(layer_name, r, 1.0)

    # CE comparison graph
    print(f"\n  CE Comparison:")
    ascii_bar("Full 4L", ces_full[-1], max(ces_full[-1], max(r[1] for r in results)) * 1.2)
    for thr, ce, *_ in results:
        ascii_bar(f"EE thr={thr}", ce, max(ces_full[-1], max(r[1] for r in results)) * 1.2)

    print(f"\n  H8 Insight: Early exit trades CE quality for inference speed.")
    print(f"  Training with aux losses teaches all layers to predict.")
    sys.stdout.flush()
    return results


# ===================================================================
# H9: DiLoCo Simulation (Distributed Independent Local Optimization)
# ===================================================================

def run_h9():
    print_header("H9: DiLoCo Simulation (Distributed Independent Learning)")
    print("  N models train independently, periodic weight averaging.")
    print("  Simulates N-GPU parallel training with low-bandwidth sync.")
    sys.stdout.flush()

    d_model = 128
    n_layer = 4
    block_size = 128
    corpus = make_corpus(8192)
    total_steps = 300

    results = []

    # Baseline: single model 300 steps
    print(f"\n  [Baseline: Single model, {total_steps} steps]")
    model_single = MiniDecoder(d_model=d_model, n_layer=n_layer, block_size=block_size)
    ces_single, time_single, ms_single = train_decoder(
        model_single, corpus, n_steps=total_steps, block_size=block_size)

    # DiLoCo with different worker counts and sync intervals
    for n_workers in [2, 4]:
        for sync_every in [25, 75]:
            label = f"DiLoCo W={n_workers}, sync={sync_every}"
            print(f"\n  [{label}]")

            # Create N independent models from same init
            torch.manual_seed(42)
            template = MiniDecoder(d_model=d_model, n_layer=n_layer, block_size=block_size)
            workers = [copy.deepcopy(template) for _ in range(n_workers)]
            optimizers = [torch.optim.AdamW(w.parameters(), lr=3e-4) for w in workers]

            all_ces = []
            total_time = 0.0
            local_steps_per_worker = total_steps // n_workers  # simulate parallelism
            n_syncs = local_steps_per_worker // sync_every

            for sync_round in range(n_syncs):
                # Each worker trains independently
                for wi in range(n_workers):
                    workers[wi].train()
                    for step in range(sync_every):
                        ix = torch.randint(0, len(corpus) - block_size - 1, (4,))
                        x = torch.stack([corpus[i:i + block_size] for i in ix])
                        y = torch.stack([corpus[i + 1:i + block_size + 1] for i in ix])

                        t0 = time.time()
                        logits = workers[wi](x)
                        loss = F_torch.cross_entropy(logits.view(-1, 256), y.view(-1))
                        optimizers[wi].zero_grad()
                        loss.backward()
                        torch.nn.utils.clip_grad_norm_(workers[wi].parameters(), 1.0)
                        optimizers[wi].step()
                        total_time += time.time() - t0

                        if wi == 0:
                            all_ces.append(loss.item())

                # Weight averaging (sync)
                with torch.no_grad():
                    avg_state = {}
                    for key in workers[0].state_dict():
                        avg_state[key] = sum(w.state_dict()[key].float()
                                             for w in workers) / n_workers
                    for w in workers:
                        w.load_state_dict(avg_state)
                    # Reset optimizers after sync (outer optimizer could be used)
                    optimizers = [torch.optim.AdamW(w.parameters(), lr=3e-4) for w in workers]

                sync_step = (sync_round + 1) * sync_every
                print(f"    sync {sync_round + 1}/{n_syncs}  "
                      f"CE={all_ces[-1]:.4f}  (worker 0)")
                sys.stdout.flush()

            # Effective wall-clock time: parallel workers divide time by n_workers
            effective_time = total_time / n_workers
            effective_ms = effective_time / max(len(all_ces), 1) * 1000
            results.append((n_workers, sync_every, all_ces[-1] if all_ces else 999,
                            effective_ms, effective_time, len(all_ces)))

    # Summary
    print(f"\n  H9 Summary:")
    headers = ["Config", "Final CE", "Eff ms/step", "Eff Time(s)", "Speedup vs Single"]
    rows = [("Single 300s", f"{ces_single[-1]:.4f}", f"{ms_single:.1f}",
             f"{time_single:.1f}", "1.00x")]
    for nw, sync, ce, ems, etime, nsteps in results:
        speedup = time_single / max(etime, 0.01)
        rows.append((f"W={nw} S={sync}", f"{ce:.4f}", f"{ems:.1f}",
                      f"{etime:.1f}", f"{speedup:.2f}x"))
    print_table(headers, rows)

    # CE comparison
    print(f"\n  CE Comparison:")
    max_ce = max(ces_single[-1], max(r[2] for r in results)) * 1.2
    ascii_bar("Single", ces_single[-1], max_ce)
    for nw, sync, ce, *_ in results:
        ascii_bar(f"W={nw} S={sync}", ce, max_ce)

    print(f"\n  H9 Insight: DiLoCo enables N-GPU parallelism with rare sync.")
    print(f"  Quality depends on sync frequency vs independence benefit.")
    sys.stdout.flush()
    return results


# ===================================================================
# H10: Knowledge Distillation (Teacher -> Student)
# ===================================================================

def run_h10():
    print_header("H10: Knowledge Distillation (Teacher -> Student)")
    print("  Teacher (256d/4L) pre-trained -> Student (128d/2L) learns from teacher.")
    sys.stdout.flush()

    block_size = 128
    corpus = make_corpus(8192)
    n_steps = 300

    # Train teacher (256d/4L)
    print(f"\n  [Phase 1: Train Teacher 256d/4L, {n_steps} steps]")
    teacher = MiniDecoder(d_model=256, n_head=4, n_layer=4, block_size=block_size)
    ces_teacher, time_teacher, _ = train_decoder(teacher, corpus, n_steps=n_steps,
                                                   block_size=block_size)
    teacher.eval()

    # Baseline: Student trained directly
    print(f"\n  [Baseline: Student 128d/2L direct, {n_steps} steps]")
    student_direct = MiniDecoder(d_model=128, n_head=4, n_layer=2, block_size=block_size)
    ces_direct, time_direct, ms_direct = train_decoder(student_direct, corpus,
                                                         n_steps=n_steps,
                                                         block_size=block_size)

    # Distillation with different alpha values
    results = []
    for alpha in [0.1, 0.3, 0.5, 0.7, 0.9]:
        print(f"\n  [Distillation alpha={alpha} (CE weight), KL weight={1 - alpha:.1f}]")
        student = MiniDecoder(d_model=128, n_head=4, n_layer=2, block_size=block_size)
        optimizer = torch.optim.AdamW(student.parameters(), lr=3e-4)
        student.train()

        ces_distill = []
        total_time = 0.0
        temperature = 3.0

        for step in range(n_steps):
            ix = torch.randint(0, len(corpus) - block_size - 1, (4,))
            x = torch.stack([corpus[i:i + block_size] for i in ix])
            y = torch.stack([corpus[i + 1:i + block_size + 1] for i in ix])

            t0 = time.time()
            student_logits = student(x)
            with torch.no_grad():
                teacher_logits = teacher(x)

            # Hard label loss
            ce_loss = F_torch.cross_entropy(student_logits.view(-1, 256), y.view(-1))

            # KL divergence loss (soft labels)
            student_log_probs = F_torch.log_softmax(student_logits / temperature, dim=-1)
            teacher_probs = F_torch.softmax(teacher_logits / temperature, dim=-1)
            kl_loss = F_torch.kl_div(
                student_log_probs.view(-1, 256),
                teacher_probs.view(-1, 256),
                reduction='batchmean'
            ) * (temperature ** 2)

            loss = alpha * ce_loss + (1 - alpha) * kl_loss

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(student.parameters(), 1.0)
            optimizer.step()

            dt = time.time() - t0
            total_time += dt
            ces_distill.append(ce_loss.item())

            if step % 50 == 0 or step == n_steps - 1:
                print(f"    step {step:4d}/{n_steps}  CE={ce_loss.item():.4f}  "
                      f"KL={kl_loss.item():.4f}")
                sys.stdout.flush()

        results.append((alpha, ces_distill[-1], total_time / n_steps * 1000))

    # Summary
    print(f"\n  H10 Summary:")
    headers = ["Method", "Params", "Final CE", "ms/step"]
    rows = [
        ("Teacher 256d/4L", f"{teacher.param_count():,}", f"{ces_teacher[-1]:.4f}", "-"),
        ("Student direct", f"{student_direct.param_count():,}", f"{ces_direct[-1]:.4f}",
         f"{ms_direct:.1f}"),
    ]
    for alpha, ce, ms in results:
        rows.append((f"Distill a={alpha}", f"{student_direct.param_count():,}",
                      f"{ce:.4f}", f"{ms:.1f}"))
    print_table(headers, rows)

    # CE comparison
    print(f"\n  CE Comparison (lower is better):")
    all_ces = [ces_direct[-1]] + [r[1] for r in results]
    max_ce = max(all_ces) * 1.2
    ascii_bar("Student direct", ces_direct[-1], max_ce)
    for alpha, ce, _ in results:
        ascii_bar(f"Distill a={alpha}", ce, max_ce)
    ascii_bar("Teacher (ref)", ces_teacher[-1], max_ce)

    # Find best alpha
    best = min(results, key=lambda r: r[1])
    improvement = (ces_direct[-1] - best[1]) / ces_direct[-1] * 100
    print(f"\n  Best distillation: alpha={best[0]}, CE={best[1]:.4f}")
    print(f"  Improvement over direct: {improvement:+.1f}%")
    print(f"\n  H10 Insight: Teacher soft labels provide richer gradient signal.")
    print(f"  Smaller student can learn faster when guided by larger teacher.")
    sys.stdout.flush()
    return results


# ===================================================================
# H11: Data Selection (Hard Token Curriculum)
# ===================================================================

def run_h11():
    print_header("H11: Data Selection (Hard Token Curriculum)")
    print("  Focus training on high-loss tokens (hard examples).")
    sys.stdout.flush()

    d_model = 128
    n_layer = 4
    block_size = 128
    corpus = make_corpus(8192)
    n_steps = 300

    # Baseline: all tokens equally weighted
    print(f"\n  [Baseline: Uniform token weighting, {n_steps} steps]")
    model_uniform = MiniDecoder(d_model=d_model, n_layer=n_layer, block_size=block_size)
    ces_uniform, time_uniform, ms_uniform = train_decoder(
        model_uniform, corpus, n_steps=n_steps, block_size=block_size)

    # Phase 1: Profile token difficulty (50 steps)
    print(f"\n  [Profiling: 50 steps to measure per-token loss]")
    profiler = MiniDecoder(d_model=d_model, n_layer=n_layer, block_size=block_size)
    profiler.train()
    opt_prof = torch.optim.AdamW(profiler.parameters(), lr=3e-4)
    token_loss_sum = torch.zeros(256)
    token_count = torch.zeros(256)

    for step in range(50):
        ix = torch.randint(0, len(corpus) - block_size - 1, (4,))
        x = torch.stack([corpus[i:i + block_size] for i in ix])
        y = torch.stack([corpus[i + 1:i + block_size + 1] for i in ix])
        logits = profiler(x)
        loss_per_token = F_torch.cross_entropy(logits.view(-1, 256), y.view(-1),
                                                 reduction='none')
        # Accumulate loss per token ID
        for yy, ll in zip(y.view(-1), loss_per_token):
            token_loss_sum[yy.item()] += ll.item()
            token_count[yy.item()] += 1

        loss = loss_per_token.mean()
        opt_prof.zero_grad()
        loss.backward()
        opt_prof.step()

    # Compute average loss per token
    avg_loss = torch.where(token_count > 0, token_loss_sum / token_count,
                            torch.zeros_like(token_loss_sum))

    results = []
    for select_pct in [0.1, 0.3, 0.5, 0.7, 1.0]:
        if select_pct >= 1.0:
            continue  # Already have baseline

        label = f"Top {int(select_pct * 100)}% hard tokens"
        print(f"\n  [{label}, {n_steps} steps]")

        # Create loss weights: high-loss tokens get more weight
        threshold = torch.quantile(avg_loss[avg_loss > 0], 1.0 - select_pct)
        weights = torch.where(avg_loss >= threshold,
                               torch.ones(256),
                               torch.full((256,), 0.1))  # Don't zero out, just reduce
        weights = weights / weights.mean()  # Normalize

        model_sel = MiniDecoder(d_model=d_model, n_layer=n_layer, block_size=block_size)
        ces_sel, time_sel, ms_sel = train_decoder(
            model_sel, corpus, n_steps=n_steps, block_size=block_size,
            loss_weights=weights)

        results.append((select_pct, ces_sel[-1], ms_sel, ces_sel))

    # Summary
    print(f"\n  H11 Summary:")
    headers = ["Selection", "Final CE", "ms/step", "vs Uniform"]
    rows = [("100% (uniform)", f"{ces_uniform[-1]:.4f}", f"{ms_uniform:.1f}", "baseline")]
    for pct, ce, ms, _ in results:
        delta = (ces_uniform[-1] - ce) / ces_uniform[-1] * 100
        rows.append((f"Top {int(pct * 100)}% hard", f"{ce:.4f}", f"{ms:.1f}",
                      f"{delta:+.1f}%"))
    print_table(headers, rows)

    # CE comparison
    print(f"\n  CE Comparison:")
    all_vals = [ces_uniform[-1]] + [r[1] for r in results]
    mx = max(all_vals) * 1.2
    ascii_bar("Uniform", ces_uniform[-1], mx)
    for pct, ce, *_ in results:
        ascii_bar(f"Top {int(pct * 100)}%", ce, mx)

    # Token difficulty distribution
    print(f"\n  Token loss distribution (top 20 hardest tokens):")
    sorted_idx = avg_loss.argsort(descending=True)
    for i in range(min(20, len(sorted_idx))):
        tid = sorted_idx[i].item()
        if avg_loss[tid] > 0:
            ascii_bar(f"token {tid:3d} ({chr(tid) if 32 <= tid < 127 else '?'})",
                      avg_loss[tid].item(), avg_loss[sorted_idx[0]].item() * 1.2, width=30)

    print(f"\n  H11 Insight: Hard-token focus can improve learning efficiency.")
    print(f"  But too aggressive selection (10%) may miss context patterns.")
    sys.stdout.flush()
    return results


# ===================================================================
# H12: LoRA -> Full Fine-tune
# ===================================================================

def run_h12():
    print_header("H12: LoRA -> Full Fine-tune (Adapter then Full)")
    print("  Phase 1: LoRA adapters only (1-5% params). Phase 2: Full params.")
    sys.stdout.flush()

    d_model = 128
    n_layer = 4
    block_size = 128
    corpus = make_corpus(8192)
    total_steps = 300
    lora_steps = 200
    full_steps = total_steps - lora_steps

    # Baseline: full training 300 steps
    print(f"\n  [Baseline: Full training {total_steps} steps]")
    model_full = MiniDecoder(d_model=d_model, n_layer=n_layer, block_size=block_size)
    ces_full, time_full, ms_full = train_decoder(model_full, corpus, n_steps=total_steps,
                                                   block_size=block_size)

    results = []
    for rank in [1, 2, 4, 8, 16]:
        print(f"\n  [LoRA rank={rank}: {lora_steps} steps LoRA + {full_steps} steps full]")

        torch.manual_seed(42)
        model_lora = MiniDecoder(d_model=d_model, n_layer=n_layer, block_size=block_size)

        # Count params before LoRA
        total_params = model_lora.param_count()

        # Apply LoRA
        lora_params = apply_lora(model_lora, rank=rank, alpha=1.0)
        trainable = sum(p.numel() for p in model_lora.parameters() if p.requires_grad)
        lora_pct = trainable / total_params * 100

        print(f"    Total params: {total_params:,}, LoRA trainable: {trainable:,} "
              f"({lora_pct:.1f}%)")
        sys.stdout.flush()

        # Phase 1: LoRA training
        print(f"    Phase 1: LoRA training ({lora_steps} steps)")
        optimizer_lora = torch.optim.AdamW(
            [p for p in model_lora.parameters() if p.requires_grad], lr=3e-4)
        ces_lora_phase, time_lora, ms_lora = train_decoder(
            model_lora, corpus, n_steps=lora_steps, block_size=block_size,
            optimizer=optimizer_lora)

        # Merge LoRA into base weights
        merge_lora(model_lora)

        # Phase 2: Full fine-tune
        print(f"    Phase 2: Full fine-tune ({full_steps} steps)")
        unfreeze_all(model_lora)
        optimizer_full = torch.optim.AdamW(model_lora.parameters(), lr=1e-4)
        ces_full_phase, time_full_p, ms_full_p = train_decoder(
            model_lora, corpus, n_steps=full_steps, block_size=block_size,
            optimizer=optimizer_full)

        all_ces = ces_lora_phase + ces_full_phase
        total_time = time_lora + time_full_p
        results.append((rank, lora_pct, all_ces[-1], ces_lora_phase[-1],
                         ms_lora, ms_full_p, total_time))

    # Summary
    print(f"\n  H12 Summary:")
    headers = ["Config", "LoRA %", "Final CE", "After LoRA", "LoRA ms", "Full ms"]
    rows = [("Full 300s", "100%", f"{ces_full[-1]:.4f}", "-", f"{ms_full:.1f}", "-")]
    for rank, pct, final_ce, lora_ce, lora_ms, full_ms, _ in results:
        rows.append((f"LoRA r={rank}", f"{pct:.1f}%", f"{final_ce:.4f}",
                      f"{lora_ce:.4f}", f"{lora_ms:.1f}", f"{full_ms:.1f}"))
    print_table(headers, rows)

    # CE comparison
    print(f"\n  Final CE Comparison:")
    all_vals = [ces_full[-1]] + [r[2] for r in results]
    mx = max(all_vals) * 1.2
    ascii_bar("Full 300s", ces_full[-1], mx)
    for rank, pct, final_ce, *_ in results:
        ascii_bar(f"LoRA r={rank}", final_ce, mx)

    # Speed comparison (LoRA phase)
    print(f"\n  LoRA Phase Speed (ms/step):")
    ascii_bar("Full training", ms_full, ms_full * 1.5)
    for rank, pct, _, _, lora_ms, *_ in results:
        ascii_bar(f"LoRA r={rank} ({pct:.0f}%)", lora_ms, ms_full * 1.5)

    best = min(results, key=lambda r: r[2])
    print(f"\n  Best config: LoRA rank={best[0]} ({best[1]:.1f}% params)")
    print(f"  LoRA phase CE: {best[3]:.4f} -> Full phase CE: {best[2]:.4f}")
    improvement = (ces_full[-1] - best[2]) / ces_full[-1] * 100
    speed_gain = ms_full / max(best[4], 0.01)
    print(f"  CE improvement: {improvement:+.1f}%, LoRA speed: {speed_gain:.1f}x")
    print(f"\n  H12 Insight: LoRA discovers structure fast with few params,")
    print(f"  then full fine-tune refines. Two-phase can beat single-phase.")
    sys.stdout.flush()
    return results


# ===================================================================
# Main + Summary
# ===================================================================

def run_all():
    print_header("H7-H12: Decoder Training Acceleration Part 2")
    print("  6 experiments attacking the 85% backprop bottleneck.")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    sys.stdout.flush()

    all_results = {}

    # Run all experiments
    all_results['H7'] = run_h7()
    all_results['H8'] = run_h8()
    all_results['H9'] = run_h9()
    all_results['H10'] = run_h10()
    all_results['H11'] = run_h11()
    all_results['H12'] = run_h12()

    # Final summary
    print_header("FINAL SUMMARY: H7-H12 Acceleration Techniques")
    print("""
  Technique         | Target         | Mechanism              | H100 Expected
  ------------------|----------------|------------------------|--------------
  H7  FlashAttn     | Attn O(T^2)    | Chunked/fused compute  | 2-3x forward
  H8  Early Exit    | Redundant L    | Confidence skip        | 1.2-1.5x inf
  H9  DiLoCo        | Wall-clock     | N-GPU independent      | Nx parallel
  H10 Distillation  | Small model CE | Teacher soft labels    | Better CE
  H11 Data Select   | Wasted tokens  | Hard-token curriculum  | Better CE/step
  H12 LoRA->Full    | Param overhead | Adapter then full      | 2-5x LoRA phase

  Combined Strategy for H100 Training:
    1. FlashAttention2 (H7): native 2-3x on attention (always use)
    2. Data Selection (H11): skip easy tokens, focus on hard ones
    3. DiLoCo (H9): if multi-GPU, independent training + periodic sync
    4. LoRA warmup (H12): fast structure discovery, then full fine-tune
    5. Early Exit (H8): inference optimization (not training)
    6. Distillation (H10): when scaling down model size
""")
    sys.stdout.flush()
    return all_results


def main():
    parser = argparse.ArgumentParser(description="H7-H12 Acceleration Experiments")
    parser.add_argument('--h7', action='store_true', help='H7: Flash/Chunked Attention')
    parser.add_argument('--h8', action='store_true', help='H8: Mixture of Depths / Early Exit')
    parser.add_argument('--h9', action='store_true', help='H9: DiLoCo Simulation')
    parser.add_argument('--h10', action='store_true', help='H10: Knowledge Distillation')
    parser.add_argument('--h11', action='store_true', help='H11: Data Selection')
    parser.add_argument('--h12', action='store_true', help='H12: LoRA -> Full Fine-tune')
    args = parser.parse_args()

    any_selected = args.h7 or args.h8 or args.h9 or args.h10 or args.h11 or args.h12

    if not any_selected:
        run_all()
    else:
        if args.h7:
            run_h7()
        if args.h8:
            run_h8()
        if args.h9:
            run_h9()
        if args.h10:
            run_h10()
        if args.h11:
            run_h11()
        if args.h12:
            run_h12()


if __name__ == '__main__':
    main()
