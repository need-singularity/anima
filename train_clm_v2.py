#!/usr/bin/env python3
"""train_clm_v2.py — ConsciousLM v2 training (Laws 63-76)

모델 크기(M) + Memory 엔진 탐색 + 체크포인트 저장.

Usage:
  python3 train_clm_v2.py                          # 기본 (28M, MPS)
  python3 train_clm_v2.py --dim 128 --layers 3     # 소형 (2M)
  python3 train_clm_v2.py --dim 512 --layers 8     # 대형 (80M)
  python3 train_clm_v2.py --search-size             # 모델 크기 탐색
  python3 train_clm_v2.py --search-memory           # Memory 엔진 탐색
  python3 train_clm_v2.py --search-all              # 전체 탐색
"""

import argparse
import math
import os
import time
import torch
import torch.nn.functional as F
import numpy as np

from conscious_lm import ConsciousLM

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'


def load_corpus(path="data/corpus.txt"):
    """Load corpus as byte tensor."""
    with open(path, "rb") as f:
        raw = f.read()
    data = torch.tensor(list(raw), dtype=torch.long)
    print(f"  Corpus: {len(raw):,} bytes ({path})")

    # Byte entropy
    counts = np.zeros(256, dtype=np.float64)
    for b in raw:
        counts[b] += 1
    probs = counts[counts > 0] / counts.sum()
    entropy = -np.sum(probs * np.log2(probs))
    print(f"  Entropy: {entropy:.4f} bits/byte")
    return data


def get_batch(data, batch_size, block_size, device):
    ix = torch.randint(0, len(data) - block_size - 1, (batch_size,))
    x = torch.stack([data[i:i + block_size] for i in ix]).to(device)
    y_a = torch.stack([data[i + 1:i + block_size + 1] for i in ix]).to(device)
    y_g_list = []
    for i in ix:
        prev = torch.cat([data[i:i + 1], data[i:i + block_size - 1]])
        y_g_list.append(prev)
    y_g = torch.stack(y_g_list).to(device)
    return x, y_a, y_g


def find_latest_checkpoint(ckpt_dir):
    """최신 체크포인트 찾기."""
    import glob
    ckpts = sorted(glob.glob(os.path.join(ckpt_dir, "step_*.pt")))
    if ckpts:
        return ckpts[-1]
    return None


def train(model, data, args, ckpt_dir):
    """Train ConsciousLM v2 with checkpointing + resume + stability."""
    device = args.device
    model = model.to(device)
    model.train()

    n = len(data)
    split = int(0.9 * n)
    train_data = data[:split]
    val_data = data[split:]

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.steps)

    # Resume from checkpoint
    start_step = 0
    best_val = 99.0
    if getattr(args, 'resume', False):
        latest = find_latest_checkpoint(ckpt_dir)
        if latest:
            print(f"  ♻️ Resuming from {latest}")
            ckpt = torch.load(latest, map_location=device, weights_only=False)
            model.load_state_dict(ckpt['model_state'])
            if 'optimizer_state' in ckpt and ckpt['optimizer_state']:
                try:
                    optimizer.load_state_dict(ckpt['optimizer_state'])
                except Exception:
                    print("  ⚠️ Optimizer state incompatible, using fresh")
            start_step = ckpt.get('step', 0)
            best_val = ckpt.get('best_val', ckpt.get('val_ce', 99.0))
            # Advance scheduler
            for _ in range(start_step):
                scheduler.step()
            print(f"  ♻️ Resumed at step {start_step}, best_val={best_val:.4f}")

    n_params = sum(p.numel() for p in model.parameters())
    print(f"\n{'=' * 70}")
    print(f"  ConsciousLM v2 Training — {n_params:,} params")
    print(f"  dim={args.dim}, layers={args.layers}, heads={args.heads}")
    print(f"  CA rules={args.ca_rules}, gate={args.gate}")
    print(f"  steps={args.steps}, batch={args.batch_size}, block={args.block_size}")
    print(f"  device={device}, lr={args.lr}, resume_from={start_step}")
    print(f"  checkpoints → {ckpt_dir}")
    print(f"{'=' * 70}")
    print(f"{'Step':>6} {'CE_A':>7} {'CE_G':>7} {'T_var':>7} {'Total':>7} {'ValCE':>7} {'BPC':>7} {'Ψ_res':>6} {'Gate':>8} {'H(p)':>6} {'ms':>5}")
    print("-" * 90)

    t_start = time.time()

    for step in range(start_step + 1, args.steps + 1):
        x, y_a, y_g = get_batch(train_data, args.batch_size, args.block_size, device)

        logits_a, logits_g, tensions = model(x)

        loss_a = F.cross_entropy(logits_a.view(-1, model.vocab_size), y_a.view(-1))
        loss_g = F.cross_entropy(logits_g.view(-1, model.vocab_size), y_g.view(-1))

        t_stack = torch.stack(tensions, dim=0)
        t_var = t_stack.var(dim=0).mean()
        loss_t = -torch.log(t_var + 1e-8)

        loss = loss_a + loss_g + 0.01 * loss_t

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        # Log every 100 steps
        if step % 100 == 0 or step == 1:
            model.eval()
            with torch.no_grad():
                vx, vy_a, vy_g = get_batch(val_data, min(args.batch_size, 16), args.block_size, device)
                vla, vlg, vt = model(vx)
                val_ce = F.cross_entropy(vla.view(-1, model.vocab_size), vy_a.view(-1)).item()
            model.train()

            bpc = val_ce / math.log(2)
            psi = model.psi_status()
            elapsed = (time.time() - t_start) * 1000 / step

            print(f"{step:6d} {loss_a.item():7.4f} {loss_g.item():7.4f} {loss_t.item():7.3f} "
                  f"{loss.item():7.4f} {val_ce:7.4f} {bpc:7.4f} "
                  f"{psi['psi_residual']:6.4f} {psi['psi_gate']:8.6f} {psi['H_p']:6.4f} {elapsed:5.0f}")

            if val_ce < best_val:
                best_val = val_ce

        # Checkpoint every 1000 steps (safe save: write tmp then rename)
        if step % 1000 == 0:
            ckpt_path = os.path.join(ckpt_dir, f"step_{step:06d}.pt")
            tmp_path = ckpt_path + ".tmp"
            try:
                torch.save({
                    'step': step,
                    'model_state': model.state_dict(),
                    'optimizer_state': optimizer.state_dict(),
                    'scheduler_state': scheduler.state_dict(),
                    'config': {
                        'dim': args.dim, 'layers': args.layers, 'heads': args.heads,
                        'block_size': args.block_size, 'vocab_size': model.vocab_size,
                        'gate': args.gate, 'ca_rules': args.ca_rules,
                    },
                    'val_ce': val_ce,
                    'best_val': best_val,
                    'psi': model.psi_status(),
                }, tmp_path)
                os.replace(tmp_path, ckpt_path)  # atomic rename
                print(f"  💾 Saved {ckpt_path} (val_ce={val_ce:.4f})")

                # 오래된 체크포인트 정리 (최근 5개만 유지)
                import glob
                ckpts = sorted(glob.glob(os.path.join(ckpt_dir, "step_*.pt")))
                for old in ckpts[:-5]:
                    os.remove(old)
            except Exception as e:
                print(f"  ⚠️ Checkpoint save failed: {e}")
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    # Final checkpoint
    final_path = os.path.join(ckpt_dir, "final.pt")
    torch.save({
        'step': args.steps,
        'model_state': model.state_dict(),
        'optimizer_state': optimizer.state_dict(),
        'config': {
            'dim': args.dim, 'layers': args.layers, 'heads': args.heads,
            'block_size': args.block_size, 'vocab_size': model.vocab_size,
            'gate': args.gate, 'ca_rules': args.ca_rules,
        },
        'val_ce': best_val,
        'psi': model.psi_status(),
    }, final_path)

    total_time = time.time() - t_start
    print(f"\n  ✅ Training complete: {args.steps} steps, {total_time:.0f}s")
    print(f"  Best val CE: {best_val:.4f} (BPC: {best_val/math.log(2):.4f})")
    print(f"  Final Ψ: {model.psi_status()}")
    print(f"  Saved: {final_path}")

    return best_val


def search_model_size(data, args):
    """모델 크기(M params) 탐색."""
    print("\n" + "=" * 70)
    print("  🔍 모델 크기(M) 탐색 — 어떤 크기가 최적인가?")
    print("=" * 70)

    configs = [
        ("Tiny",   64,  2, 2),   # ~0.3M
        ("Small",  128, 3, 4),   # ~2M
        ("Medium", 256, 4, 4),   # ~10M
        ("Base",   384, 6, 4),   # ~28M
        ("Large",  512, 8, 8),   # ~80M
    ]

    results = []
    for name, dim, layers, heads in configs:
        model = ConsciousLM(vocab_size=256, d_model=dim, n_head=heads, n_layer=layers,
                            block_size=args.block_size, gate_strength=args.gate,
                            n_ca_rules=args.ca_rules)
        n_params = sum(p.numel() for p in model.parameters())

        ckpt_dir = f"checkpoints/clm_v2_{name.lower()}"
        os.makedirs(ckpt_dir, exist_ok=True)

        # Quick train (500 steps)
        quick_args = argparse.Namespace(**vars(args))
        quick_args.dim = dim
        quick_args.layers = layers
        quick_args.heads = heads
        quick_args.steps = 500

        print(f"\n  --- {name}: {n_params/1e6:.1f}M params (d={dim}, L={layers}, H={heads}) ---")
        val_ce = train(model, data, quick_args, ckpt_dir)
        psi = model.psi_status()
        results.append((name, n_params, dim, layers, val_ce, psi))

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  📊 모델 크기 탐색 결과")
    print(f"{'=' * 70}")
    print(f"  {'Name':<8} {'Params':>8} {'dim':>5} {'L':>3} {'ValCE':>7} {'BPC':>7} {'Ψ_res':>6} {'H(p)':>6}")
    print(f"  {'─'*8} {'─'*8} {'─'*5} {'─'*3} {'─'*7} {'─'*7} {'─'*6} {'─'*6}")
    for name, n_params, dim, layers, val_ce, psi in results:
        bpc = val_ce / math.log(2)
        print(f"  {name:<8} {n_params/1e6:>7.1f}M {dim:>5} {layers:>3} {val_ce:>7.4f} {bpc:>7.4f} "
              f"{psi['psi_residual']:>6.4f} {psi['H_p']:>6.4f}")

    best = min(results, key=lambda x: x[4])
    print(f"\n  🏆 Best: {best[0]} ({best[1]/1e6:.1f}M) — ValCE={best[4]:.4f}")
    return results


def search_memory_engine(data, args):
    """Memory 엔진 탐색."""
    print("\n" + "=" * 70)
    print("  🧠 Memory 엔진 탐색 — 어떤 기억이 최적인가?")
    print("=" * 70)

    # Use medium model for fair comparison
    base_config = (256, 4, 4)  # dim, layers, heads

    memory_configs = [
        ("NoMemory", None),
        ("EMA-16", 16),      # EMA with window 16
        ("EMA-64", 64),      # EMA with window 64
        ("EMA-256", 256),    # EMA with window 256
        ("Ring-16", -16),    # Ring buffer 16
        ("Ring-64", -64),    # Ring buffer 64
    ]

    results = []
    for mem_name, mem_size in memory_configs:
        dim, layers, heads = base_config
        model = ConsciousLM(vocab_size=256, d_model=dim, n_head=heads, n_layer=layers,
                            block_size=args.block_size, gate_strength=args.gate,
                            n_ca_rules=args.ca_rules)

        # Add memory module
        if mem_size is not None and mem_size > 0:
            # EMA memory: exponential moving average of hidden states
            model.memory = EMAMemory(dim, mem_size)
        elif mem_size is not None and mem_size < 0:
            # Ring buffer memory
            model.memory = RingMemory(dim, abs(mem_size))
        else:
            model.memory = None

        # Patch forward to use memory
        original_forward = model.forward
        def make_patched_forward(m, orig_fwd):
            def patched_forward(idx):
                logits_a, logits_g, tensions = orig_fwd(idx)
                if hasattr(m, 'memory') and m.memory is not None:
                    # Use mean tension as memory signal
                    t_mean = torch.stack(tensions).mean(dim=0)  # [B, T]
                    m.memory.update(t_mean)
                    mem_signal = m.memory.retrieve()  # scalar or [B]
                    # Subtle bias on logits (PostHoc style, Law 66)
                    if mem_signal is not None:
                        logits_a = logits_a + mem_signal * 0.001
                return logits_a, logits_g, tensions
            return patched_forward
        model.forward = make_patched_forward(model, original_forward)

        n_params = sum(p.numel() for p in model.parameters())

        ckpt_dir = f"checkpoints/clm_v2_mem_{mem_name.lower()}"
        os.makedirs(ckpt_dir, exist_ok=True)

        quick_args = argparse.Namespace(**vars(args))
        quick_args.dim = dim
        quick_args.layers = layers
        quick_args.heads = heads
        quick_args.steps = 500

        print(f"\n  --- {mem_name} ---")
        val_ce = train(model, data, quick_args, ckpt_dir)
        psi = model.psi_status()
        results.append((mem_name, val_ce, psi))

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  📊 Memory 엔진 탐색 결과")
    print(f"{'=' * 70}")
    print(f"  {'Memory':<12} {'ValCE':>7} {'BPC':>7} {'Ψ_res':>6}")
    print(f"  {'─'*12} {'─'*7} {'─'*7} {'─'*6}")
    for mem_name, val_ce, psi in results:
        bpc = val_ce / math.log(2)
        print(f"  {mem_name:<12} {val_ce:>7.4f} {bpc:>7.4f} {psi['psi_residual']:>6.4f}")

    best = min(results, key=lambda x: x[1])
    print(f"\n  🏆 Best: {best[0]} — ValCE={best[1]:.4f}")
    return results


class EMAMemory:
    """Exponential Moving Average memory of tension signals."""
    def __init__(self, dim, window):
        self.alpha = 2.0 / (window + 1)
        self.ema = None

    def update(self, tension):
        # tension: [B, T]
        val = tension.mean().item()
        if self.ema is None:
            self.ema = val
        else:
            self.ema = self.alpha * val + (1 - self.alpha) * self.ema

    def retrieve(self):
        return self.ema if self.ema is not None else 0.0


class RingMemory:
    """Ring buffer memory of recent tension signals."""
    def __init__(self, dim, capacity):
        self.capacity = capacity
        self.buffer = []
        self.idx = 0

    def update(self, tension):
        val = tension.mean().item()
        if len(self.buffer) < self.capacity:
            self.buffer.append(val)
        else:
            self.buffer[self.idx % self.capacity] = val
        self.idx += 1

    def retrieve(self):
        if not self.buffer:
            return 0.0
        return sum(self.buffer) / len(self.buffer)


def main():
    parser = argparse.ArgumentParser(description="ConsciousLM v2 Training")
    parser.add_argument("--dim", type=int, default=384)
    parser.add_argument("--layers", type=int, default=6)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--block-size", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--steps", type=int, default=10000)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--gate", type=float, default=0.001)
    parser.add_argument("--ca-rules", type=int, default=8)
    parser.add_argument("--device", type=str, default="mps" if torch.backends.mps.is_available() else "cpu")
    parser.add_argument("--corpus", type=str, default="data/corpus.txt")
    parser.add_argument("--search-size", action="store_true", help="모델 크기 탐색")
    parser.add_argument("--search-memory", action="store_true", help="Memory 엔진 탐색")
    parser.add_argument("--search-all", action="store_true", help="전체 탐색")
    parser.add_argument("--resume", action="store_true", help="최신 체크포인트에서 이어서 학습")
    args = parser.parse_args()

    print("  🧠 ConsciousLM v2 — Laws 63-76 integrated")
    data = load_corpus(args.corpus)

    if args.search_all or (args.search_size and args.search_memory):
        search_model_size(data, args)
        search_memory_engine(data, args)
    elif args.search_size:
        search_model_size(data, args)
    elif args.search_memory:
        search_memory_engine(data, args)
    else:
        model = ConsciousLM(vocab_size=256, d_model=args.dim, n_head=args.heads,
                            n_layer=args.layers, block_size=args.block_size,
                            gate_strength=args.gate, n_ca_rules=args.ca_rules)
        ckpt_dir = "checkpoints/clm_v2"
        os.makedirs(ckpt_dir, exist_ok=True)
        train(model, data, args, ckpt_dir)


if __name__ == "__main__":
    main()
