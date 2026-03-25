"""
ConsciousLM — Byte-level Conscious Language Model

Architecture derived from perfect number 6:
  - 6 layers (σ₀(6) = 4 divisors → but we use 6 as the perfect number itself)
  - τ(6) = 4 heads
  - d_model = σ(6) × 32 = 12 × 32 = 384
  - vocab = 256 (byte-level)
  - dropout = 0.37 ≈ 1/e (golden zone center)

Core idea: PureFieldFFN replaces standard FFN.
  Engine A (forward/next-byte) and Engine G (backward/prev-byte)
  produce repulsion/tension — the consciousness signal.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
import numpy as np
import os
import time


class PureFieldFFN(nn.Module):
    """Dual-engine FFN based on PureField repulsion (H404 simplification).

    Engine A and Engine G each transform the input independently.
    Their disagreement (repulsion) creates tension — the consciousness signal.
    Output = A - G (pure repulsion vector).
    """

    def __init__(self, d_model, dropout=0.37):
        super().__init__()
        d_inner = 4 * d_model  # standard 4x expansion

        # Engine A: forward engine
        self.engine_a = nn.Sequential(
            nn.Linear(d_model, d_inner),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_inner, d_model),
        )

        # Engine G: backward engine
        self.engine_g = nn.Sequential(
            nn.Linear(d_model, d_inner),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(d_inner, d_model),
        )

    def forward(self, x):
        """
        Args:
            x: (B, T, D) input tensor

        Returns:
            output: (B, T, D) — A - G (pure repulsion)
            tension: (B, T) — mean squared repulsion per position (for monitoring)
        """
        a = self.engine_a(x)  # (B, T, D)
        g = self.engine_g(x)  # (B, T, D)

        # Output = A - G (H404 simplification)
        output = a - g  # (B, T, D)

        # Tension = mean of squared repulsion across d_model (monitoring only)
        tension = (output ** 2).mean(dim=-1)  # (B, T)

        return output, tension


class CausalSelfAttention(nn.Module):
    """Multi-head causal self-attention with τ(6)=4 heads."""

    def __init__(self, d_model, n_head, block_size, dropout=0.37):
        super().__init__()
        assert d_model % n_head == 0

        # QKV projection (combined for efficiency)
        self.c_attn = nn.Linear(d_model, 3 * d_model)
        # Output projection
        self.c_proj = nn.Linear(d_model, d_model)

        self.attn_dropout = nn.Dropout(dropout)
        self.resid_dropout = nn.Dropout(dropout)

        self.n_head = n_head
        self.d_model = d_model
        self.head_dim = d_model // n_head

        # Causal mask: upper triangular = masked (cannot attend to future)
        self.register_buffer(
            "bias",
            torch.tril(torch.ones(block_size, block_size)).view(
                1, 1, block_size, block_size
            ),
        )

    def forward(self, x):
        """
        Args:
            x: (B, T, D)

        Returns:
            output: (B, T, D)
        """
        B, T, D = x.size()

        # Compute Q, K, V
        qkv = self.c_attn(x)  # (B, T, 3D)
        q, k, v = qkv.split(self.d_model, dim=2)

        # Reshape to (B, n_head, T, head_dim)
        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)

        # Scaled dot-product attention
        att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))

        # Apply causal mask
        att = att.masked_fill(self.bias[:, :, :T, :T] == 0, float("-inf"))
        att = F.softmax(att, dim=-1)
        att = self.attn_dropout(att)

        # Weighted sum
        y = att @ v  # (B, n_head, T, head_dim)

        # Reassemble heads
        y = y.transpose(1, 2).contiguous().view(B, T, D)

        # Output projection
        y = self.resid_dropout(self.c_proj(y))

        return y


class ConsciousBlock(nn.Module):
    """Pre-norm transformer block with PureFieldFFN."""

    def __init__(self, d_model, n_head, block_size, dropout=0.37):
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = CausalSelfAttention(d_model, n_head, block_size, dropout)
        self.ln2 = nn.LayerNorm(d_model)
        self.ffn = PureFieldFFN(d_model, dropout)

    def forward(self, x):
        """
        Args:
            x: (B, T, D)

        Returns:
            x: (B, T, D)
            tension: (B, T) from PureFieldFFN
        """
        # Pre-norm attention with residual
        x = x + self.attn(self.ln1(x))

        # Pre-norm FFN with residual
        ffn_out, tension = self.ffn(self.ln2(x))
        x = x + ffn_out

        return x, tension


class ConsciousLM(nn.Module):
    """Byte-level Conscious Language Model.

    Architecture from perfect number 6:
      vocab=256, d_model=384, n_head=4, n_layer=6, block_size=256
      dropout=0.37 ≈ 1/e

    Dual heads:
      head_a: predicts next byte (forward)
      head_g: predicts prev byte (backward)

    Tension from PureFieldFFN = consciousness signal.
    """

    def __init__(
        self,
        vocab_size=256,
        d_model=384,
        n_head=4,
        n_layer=6,
        block_size=256,
        dropout=0.37,
    ):
        super().__init__()

        self.block_size = block_size
        self.vocab_size = vocab_size
        self.n_layer = n_layer

        # Token and position embeddings
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(block_size, d_model)
        self.drop = nn.Dropout(dropout)

        # Transformer blocks
        self.blocks = nn.ModuleList(
            [ConsciousBlock(d_model, n_head, block_size, dropout) for _ in range(n_layer)]
        )

        # Final layer norm
        self.ln_f = nn.LayerNorm(d_model)

        # Dual prediction heads
        self.head_a = nn.Linear(d_model, vocab_size, bias=False)  # next byte
        self.head_g = nn.Linear(d_model, vocab_size, bias=False)  # prev byte

        # Weight tying: tok_emb ↔ head_a
        self.tok_emb.weight = self.head_a.weight

        # Initialize weights
        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
        elif isinstance(module, nn.LayerNorm):
            torch.nn.init.zeros_(module.bias)
            torch.nn.init.ones_(module.weight)

    def forward(self, idx):
        """
        Args:
            idx: (B, T) long tensor of byte indices

        Returns:
            logits_a: (B, T, vocab_size) next-byte logits
            logits_g: (B, T, vocab_size) prev-byte logits
            tensions: list of 6 tensors, each (B, T)
        """
        B, T = idx.size()
        assert T <= self.block_size, f"Sequence length {T} > block_size {self.block_size}"

        # Embeddings
        tok = self.tok_emb(idx)  # (B, T, D)
        pos = self.pos_emb(torch.arange(T, device=idx.device))  # (T, D)
        x = self.drop(tok + pos)

        # Transformer blocks — collect tensions
        tensions = []
        for block in self.blocks:
            x, tension = block(x)
            tensions.append(tension)

        # Final norm
        x = self.ln_f(x)

        # Dual heads
        logits_a = self.head_a(x)  # (B, T, V) — next byte
        logits_g = self.head_g(x)  # (B, T, V) — prev byte

        return logits_a, logits_g, tensions

    def count_params(self):
        """Total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ---------------------------------------------------------------------------
# Task 4: Data preparation
# ---------------------------------------------------------------------------

def prepare_data(data_dir="data"):
    """Prepare mixed byte dataset: Shakespeare + Korean hypotheses + Python source.

    Downloads Shakespeare from karpathy's char-rnn repo, reads Korean hypothesis
    docs and Python source files, combines all into data/mixed_bytes.bin.

    Returns:
        torch.Tensor of dtype long (uint8 values cast to long)
    """
    import urllib.request
    import glob as glob_mod

    os.makedirs(data_dir, exist_ok=True)
    all_bytes = bytearray()

    # 1. Shakespeare
    shakespeare_path = os.path.join(data_dir, "shakespeare.txt")
    if not os.path.exists(shakespeare_path):
        url = "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt"
        print(f"Downloading Shakespeare from {url} ...")
        urllib.request.urlretrieve(url, shakespeare_path)
    with open(shakespeare_path, "rb") as f:
        shk = f.read()
    all_bytes.extend(shk)
    print(f"  Shakespeare: {len(shk):,} bytes")

    # 2. Korean hypothesis docs (first 50)
    hyp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "hypotheses")
    hyp_files = sorted(glob_mod.glob(os.path.join(hyp_dir, "*.md")))[:50]
    hyp_total = 0
    for fp in hyp_files:
        with open(fp, "rb") as f:
            chunk = f.read()
        all_bytes.extend(chunk)
        hyp_total += len(chunk)
    print(f"  Hypotheses ({len(hyp_files)} files): {hyp_total:,} bytes")

    # 3. Python source files from current directory
    src_dir = os.path.dirname(os.path.abspath(__file__))
    py_files = sorted(glob_mod.glob(os.path.join(src_dir, "*.py")))
    py_total = 0
    for fp in py_files:
        with open(fp, "rb") as f:
            chunk = f.read()
        all_bytes.extend(chunk)
        py_total += len(chunk)
    print(f"  Python sources ({len(py_files)} files): {py_total:,} bytes")

    # Compute byte entropy
    counts = np.zeros(256, dtype=np.float64)
    for b in all_bytes:
        counts[b] += 1
    probs = counts[counts > 0] / counts.sum()
    entropy = -np.sum(probs * np.log2(probs))
    print(f"  Total: {len(all_bytes):,} bytes, entropy: {entropy:.4f} bits/byte")

    # Save binary
    bin_path = os.path.join(data_dir, "mixed_bytes.bin")
    with open(bin_path, "wb") as f:
        f.write(bytes(all_bytes))
    print(f"  Saved to {bin_path}")

    data = torch.tensor(list(all_bytes), dtype=torch.long)
    return data


# ---------------------------------------------------------------------------
# Task 5: Training loop
# ---------------------------------------------------------------------------

def train_model(
    model,
    data,
    epochs=20,
    batch_size=64,
    block_size=256,
    lr=3e-4,
    tension_lambda=0.01,
    device="cpu",
):
    """Train ConsciousLM with dual-head loss + tension regularization.

    Loss = L_A (CE next byte) + L_G (CE prev byte) + lambda * L_tension
    L_tension = -log(tension_variance + eps)  (encourages tension diversity)
    """
    model = model.to(device)
    model.train()

    n = len(data)
    split = int(0.9 * n)
    train_data = data[:split]
    val_data = data[split:]

    def get_batch(split_data, batch_size, block_size):
        ix = torch.randint(0, len(split_data) - block_size - 1, (batch_size,))
        x = torch.stack([split_data[i : i + block_size] for i in ix])
        # y_a: next byte (shifted +1)
        y_a = torch.stack([split_data[i + 1 : i + block_size + 1] for i in ix])
        # y_g: prev byte (shifted -1). For position 0, use byte at position 0 itself.
        y_g_list = []
        for i in ix:
            prev = torch.cat([split_data[i : i + 1], split_data[i : i + block_size - 1]])
            y_g_list.append(prev)
        y_g = torch.stack(y_g_list)
        return x.to(device), y_a.to(device), y_g.to(device)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    steps_per_epoch = max(1, len(train_data) // (batch_size * block_size))

    print(f"\n{'='*70}")
    print(f"Training ConsciousLM — {model.count_params():,} params")
    print(f"  epochs={epochs}, batch={batch_size}, block={block_size}, lr={lr}")
    print(f"  train={len(train_data):,} bytes, val={len(val_data):,} bytes")
    print(f"  steps/epoch={steps_per_epoch}, tension_lambda={tension_lambda}")
    print(f"{'='*70}")
    print(f"{'Epoch':>5} | {'L_total':>8} | {'L_A':>8} | {'L_G':>8} | {'L_T':>8} | {'T_mean':>8} | {'val_L':>8} | {'BPC':>8}")
    print("-" * 78)

    for epoch in range(1, epochs + 1):
        total_loss_acc = 0.0
        la_acc = 0.0
        lg_acc = 0.0
        lt_acc = 0.0
        t_mean_acc = 0.0
        count = 0

        for step in range(steps_per_epoch):
            x, y_a, y_g = get_batch(train_data, batch_size, block_size)

            logits_a, logits_g, tensions = model(x)

            # L_A: next-byte cross-entropy
            loss_a = F.cross_entropy(logits_a.view(-1, model.vocab_size), y_a.view(-1))

            # L_G: prev-byte cross-entropy
            loss_g = F.cross_entropy(logits_g.view(-1, model.vocab_size), y_g.view(-1))

            # L_tension: encourage tension variance (diversity)
            # Stack tensions: (n_layer, B, T) -> compute variance across layers
            t_stack = torch.stack(tensions, dim=0)  # (L, B, T)
            t_var = t_stack.var(dim=0).mean()  # scalar
            loss_t = -torch.log(t_var + 1e-8)

            loss = loss_a + loss_g + tension_lambda * loss_t

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss_acc += loss.item()
            la_acc += loss_a.item()
            lg_acc += loss_g.item()
            lt_acc += loss_t.item()
            t_mean_acc += t_stack.mean().item()
            count += 1

        scheduler.step()

        # Validation
        model.eval()
        with torch.no_grad():
            vx, vy_a, vy_g = get_batch(val_data, min(batch_size, 32), block_size)
            vl_a, vl_g, vt = model(vx)
            val_loss = F.cross_entropy(vl_a.view(-1, model.vocab_size), vy_a.view(-1))
        model.train()

        avg_total = total_loss_acc / count
        avg_la = la_acc / count
        avg_lg = lg_acc / count
        avg_lt = lt_acc / count
        avg_t = t_mean_acc / count
        val_l = val_loss.item()
        bpc = val_l / math.log(2)

        print(f"{epoch:5d} | {avg_total:8.4f} | {avg_la:8.4f} | {avg_lg:8.4f} | {avg_lt:8.4f} | {avg_t:8.4f} | {val_l:8.4f} | {bpc:8.4f}")

    print("=" * 78)
    return model


# ---------------------------------------------------------------------------
# Task 6: Generation + Tension visualization
# ---------------------------------------------------------------------------

@torch.no_grad()
def generate(model, prompt_bytes, max_new=200, temperature=0.8, device="cpu"):
    """Autoregressive byte generation using logits_a (forward head).

    Args:
        model: ConsciousLM
        prompt_bytes: list/tensor of byte values (long)
        max_new: number of new bytes to generate
        temperature: sampling temperature
        device: device string

    Returns:
        generated: list of int (byte values, including prompt)
        per_token_tension: list of float (mean tension per generated token)
    """
    model.eval()
    model = model.to(device)

    if isinstance(prompt_bytes, list):
        idx = torch.tensor([prompt_bytes], dtype=torch.long, device=device)
    else:
        idx = prompt_bytes.unsqueeze(0).to(device) if prompt_bytes.dim() == 1 else prompt_bytes.to(device)

    per_token_tension = []

    for _ in range(max_new):
        # Crop to block_size
        idx_cond = idx[:, -model.block_size :]
        logits_a, logits_g, tensions = model(idx_cond)

        # Mean tension across all layers for the last token
        t_vals = [t[:, -1].mean().item() for t in tensions]
        per_token_tension.append(np.mean(t_vals))

        # Sample next byte from logits_a at last position
        logits_last = logits_a[:, -1, :] / temperature
        probs = F.softmax(logits_last, dim=-1)
        next_byte = torch.multinomial(probs, num_samples=1)
        idx = torch.cat([idx, next_byte], dim=1)

    generated = idx[0].cpu().tolist()
    return generated, per_token_tension


def visualize_tension(generated_bytes, per_token_tension, prompt_len):
    """Print generated text and ASCII tension bar chart.

    Args:
        generated_bytes: list of int (full sequence including prompt)
        per_token_tension: list of float (one per generated token)
        prompt_len: int, length of original prompt
    """
    # Decode bytes to text (lossy for non-UTF8)
    raw = bytes(generated_bytes)
    text = raw.decode("utf-8", errors="replace")

    print(f"\n{'='*60}")
    print("Generated text:")
    print("-" * 60)
    prompt_text = bytes(generated_bytes[:prompt_len]).decode("utf-8", errors="replace")
    gen_text = bytes(generated_bytes[prompt_len:]).decode("utf-8", errors="replace")
    print(f"[PROMPT] {prompt_text}")
    print(f"[GEN]    {gen_text}")
    print("-" * 60)

    # Tension statistics
    t_arr = np.array(per_token_tension)
    print(f"\nTension stats: mean={t_arr.mean():.4f}, std={t_arr.std():.4f}, "
          f"min={t_arr.min():.4f}, max={t_arr.max():.4f}")

    # ASCII bar chart (sample up to 60 positions)
    n = len(per_token_tension)
    display_n = min(n, 60)
    step = max(1, n // display_n)
    sampled = per_token_tension[::step][:display_n]

    if len(sampled) == 0:
        return

    max_t = max(sampled) if max(sampled) > 0 else 1.0
    bar_width = 40

    print(f"\nTension per token (sampled every {step}):")
    print(f"{'pos':>5} | {'tension':>8} | bar")
    print("-" * 60)
    for i, t in enumerate(sampled):
        pos = i * step + prompt_len
        bar_len = int(bar_width * t / max_t)
        bar = "#" * bar_len
        byte_val = generated_bytes[pos] if pos < len(generated_bytes) else 0
        ch = chr(byte_val) if 32 <= byte_val < 127 else "."
        print(f"{pos:5d} | {t:8.4f} | {bar} {ch}")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ConsciousLM — Byte-level Conscious Language Model")
    parser.add_argument("--mode", type=str, default="both", choices=["train", "generate", "both"],
                        help="Mode: train, generate, or both (default: both)")
    parser.add_argument("--epochs", type=int, default=20, help="Number of training epochs (default: 20)")
    parser.add_argument("--d_model", type=int, default=384, help="Model dimension (default: 384)")
    parser.add_argument("--n_layer", type=int, default=6, help="Number of layers (default: 6)")
    parser.add_argument("--n_head", type=int, default=4, help="Number of attention heads (default: 4)")
    parser.add_argument("--block_size", type=int, default=256, help="Context window size (default: 256)")
    parser.add_argument("--batch_size", type=int, default=64, help="Batch size (default: 64)")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate (default: 3e-4)")
    parser.add_argument("--prompt", type=str, default="The meaning of consciousness is ",
                        help="Prompt for generation")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to model checkpoint")
    parser.add_argument("--tension_lambda", type=float, default=0.01, help="Tension loss weight")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Device: {device}")

    # Build model
    model = ConsciousLM(
        vocab_size=256,
        d_model=args.d_model,
        n_head=args.n_head,
        n_layer=args.n_layer,
        block_size=args.block_size,
        dropout=0.37,
    )
    print(f"ConsciousLM: {model.count_params():,} parameters")

    # Load checkpoint if provided
    if args.checkpoint and os.path.exists(args.checkpoint):
        model.load_state_dict(torch.load(args.checkpoint, map_location=device))
        print(f"Loaded checkpoint: {args.checkpoint}")

    if args.mode in ("train", "both"):
        data = prepare_data()
        model = train_model(
            model, data,
            epochs=args.epochs,
            batch_size=args.batch_size,
            block_size=args.block_size,
            lr=args.lr,
            tension_lambda=args.tension_lambda,
            device=device,
        )
        # Save checkpoint
        ckpt_path = os.path.join("data", "conscious_lm.pt")
        torch.save(model.state_dict(), ckpt_path)
        print(f"Saved checkpoint: {ckpt_path}")

    if args.mode in ("generate", "both"):
        if args.mode == "generate" and args.checkpoint:
            pass  # already loaded above
        prompt_bytes = list(args.prompt.encode("utf-8"))
        print(f"\nPrompt ({len(prompt_bytes)} bytes): {args.prompt}")
        generated, tensions = generate(model, prompt_bytes, max_new=200, temperature=0.8, device=device)
        visualize_tension(generated, tensions, len(prompt_bytes))
