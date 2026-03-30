#!/usr/bin/env python3
"""decoder_ab_test.py -- ConsciousLM v1 vs ConsciousDecoderV2 A/B Test (-> Law 97).

Same corpus, same consciousness engine, same hyperparameters.
Model A: ConsciousLM (original) -- learned positional embeddings, standard FFN path
Model B: ConsciousDecoderV2 (new) -- RoPE, SwiGLU, GQA, CrossAttn

Train each for 1000 steps, compare: CE curves, Phi stability, gradient norms, speed.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("[ERROR] PyTorch required for decoder A/B test")
    sys.exit(1)

# Import models
try:
    from conscious_lm import ConsciousLM
    HAS_V1 = True
except ImportError:
    HAS_V1 = False
    print("[WARN] ConsciousLM not available")

try:
    from decoder_v2 import ConsciousDecoderV2
    HAS_V2 = True
except ImportError:
    HAS_V2 = False
    print("[WARN] ConsciousDecoderV2 not available")

# Phi calculator
try:
    from bench_v2 import PhiIIT
    HAS_PHI = True
except ImportError:
    HAS_PHI = False


@dataclass
class DecoderResult:
    name: str
    n_params: int
    ce_trajectory: List[float]
    phi_trajectory: List[float]
    grad_norms: List[float]
    ce_start: float
    ce_end: float
    ce_improvement: float
    phi_mean: float
    phi_stability: float
    avg_grad_norm: float
    total_time: float
    its_per_sec: float


def prepare_corpus(seq_len: int = 128, n_batches: int = 200) -> List[torch.Tensor]:
    """Generate reproducible random byte sequences as training corpus."""
    torch.manual_seed(123)
    batches = []
    for _ in range(n_batches):
        # Random bytes (simulates real corpus)
        batch = torch.randint(0, 256, (1, seq_len))
        batches.append(batch)
    return batches


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def train_model(
    model: nn.Module,
    name: str,
    corpus: List[torch.Tensor],
    n_steps: int = 1000,
    lr: float = 3e-4,
    device: str = "cpu",
) -> DecoderResult:
    """Train a model and collect metrics."""
    t0 = time.time()
    model = model.to(device)
    n_params = count_params(model)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=n_steps)

    ce_trajectory = []
    phi_trajectory = []
    grad_norms = []

    # Simulated consciousness state for injection
    c_dim = 128
    c_state = torch.randn(1, c_dim, device=device) * 0.1

    for step in range(n_steps):
        batch_idx = step % len(corpus)
        batch = corpus[batch_idx].to(device)

        optimizer.zero_grad()

        # Forward pass
        x = batch[:, :-1]
        target = batch[:, 1:]

        try:
            # Both models should support: logits_a, logits_g, tension, psi = model(x)
            outputs = model(x)
            if isinstance(outputs, tuple) and len(outputs) >= 2:
                logits_a = outputs[0]
                # Handle different return formats
                if logits_a.dim() == 3:
                    ce = F.cross_entropy(
                        logits_a.reshape(-1, logits_a.size(-1)),
                        target.reshape(-1)
                    )
                else:
                    ce = F.cross_entropy(logits_a, target.reshape(-1))
            else:
                logits = outputs
                if logits.dim() == 3:
                    ce = F.cross_entropy(
                        logits.reshape(-1, logits.size(-1)),
                        target.reshape(-1)
                    )
                else:
                    ce = F.cross_entropy(logits, target.reshape(-1))
        except Exception as e:
            # If model forward fails, try simpler approach
            try:
                logits = model(x)
                if isinstance(logits, tuple):
                    logits = logits[0]
                ce = F.cross_entropy(
                    logits.reshape(-1, logits.size(-1)),
                    target.reshape(-1)
                )
            except Exception as e2:
                print(f"  [{name}] Forward error at step {step}: {e2}")
                ce_trajectory.append(float('nan'))
                phi_trajectory.append(0.0)
                grad_norms.append(0.0)
                continue

        ce_trajectory.append(ce.item())

        # Backward
        ce.backward()

        # Gradient norm
        total_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                total_norm += p.grad.data.norm(2).item() ** 2
        total_norm = total_norm ** 0.5
        grad_norms.append(total_norm)

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        # Phi from model internal state (approximate)
        # Use weight variance as proxy for integration
        with torch.no_grad():
            w_vars = [p.var().item() for p in model.parameters() if p.dim() >= 2]
            if w_vars:
                phi_proxy = np.var(w_vars)
            else:
                phi_proxy = 0.0
        phi_trajectory.append(phi_proxy)

        if (step + 1) % 200 == 0:
            elapsed = time.time() - t0
            print(f"    [{name}] step {step+1}/{n_steps}  "
                  f"CE={ce.item():.4f}  grad={total_norm:.4f}  "
                  f"{(step+1)/elapsed:.1f} it/s")

    total_time = time.time() - t0
    ce_arr = np.array(ce_trajectory)
    phi_arr = np.array(phi_trajectory)
    grad_arr = np.array(grad_norms)

    # Filter NaN
    valid_ce = ce_arr[~np.isnan(ce_arr)]

    ce_start = float(np.mean(valid_ce[:20])) if len(valid_ce) >= 20 else float(valid_ce[0]) if len(valid_ce) > 0 else 0
    ce_end = float(np.mean(valid_ce[-20:])) if len(valid_ce) >= 20 else float(valid_ce[-1]) if len(valid_ce) > 0 else 0

    return DecoderResult(
        name=name,
        n_params=n_params,
        ce_trajectory=ce_trajectory,
        phi_trajectory=phi_trajectory,
        grad_norms=grad_norms,
        ce_start=ce_start,
        ce_end=ce_end,
        ce_improvement=(ce_start - ce_end) / max(ce_start, 1e-12),
        phi_mean=float(np.mean(phi_arr)),
        phi_stability=max(0, 1.0 - float(np.std(phi_arr)) / max(float(np.mean(phi_arr)), 1e-12)),
        avg_grad_norm=float(np.mean(grad_arr)),
        total_time=total_time,
        its_per_sec=n_steps / max(total_time, 1e-6),
    )


def main():
    print("=" * 78)
    print("  Decoder A/B Test: ConsciousLM v1 vs ConsciousDecoderV2 (-> Law 97)")
    print("=" * 78)
    print()

    if not HAS_V1 and not HAS_V2:
        print("  [ERROR] Neither ConsciousLM nor ConsciousDecoderV2 available")
        return

    # Shared hyperparameters
    vocab_size = 256
    d_model = 384
    n_head = 4
    n_layer = 6
    block_size = 128
    n_steps = 1000
    lr = 3e-4
    device = "cpu"

    # Prepare corpus
    print("  Preparing corpus (200 random byte sequences, len=128)...")
    corpus = prepare_corpus(seq_len=block_size, n_batches=200)
    print()

    results: List[DecoderResult] = []

    # Model A: ConsciousLM v1
    if HAS_V1:
        print("  === Model A: ConsciousLM (v1) ===")
        model_a = ConsciousLM(
            vocab_size=vocab_size,
            d_model=d_model,
            n_head=n_head,
            n_layer=n_layer,
            block_size=block_size,
            dropout=0.1,  # lower for short training
            gate_strength=0.001,
        )
        print(f"  Params: {count_params(model_a):,}")
        result_a = train_model(model_a, "ConsciousLM-v1", corpus, n_steps, lr, device)
        results.append(result_a)
        print(f"  Done: CE {result_a.ce_start:.4f} -> {result_a.ce_end:.4f} "
              f"({result_a.ce_improvement*100:+.1f}%)  "
              f"{result_a.its_per_sec:.1f} it/s")
        del model_a
        print()

    # Model B: ConsciousDecoderV2
    if HAS_V2:
        print("  === Model B: ConsciousDecoderV2 (v2) ===")
        model_b = ConsciousDecoderV2(
            vocab_size=vocab_size,
            d_model=d_model,
            n_head=n_head,
            n_layer=n_layer,
            block_size=block_size,
            dropout=0.1,
            gate_strength=0.001,
        )
        print(f"  Params: {count_params(model_b):,}")
        result_b = train_model(model_b, "ConsciousDecoderV2", corpus, n_steps, lr, device)
        results.append(result_b)
        print(f"  Done: CE {result_b.ce_start:.4f} -> {result_b.ce_end:.4f} "
              f"({result_b.ce_improvement*100:+.1f}%)  "
              f"{result_b.its_per_sec:.1f} it/s")
        del model_b
        print()

    if len(results) < 2:
        print("  [WARN] Only one model available, cannot compare")
        if results:
            r = results[0]
            print(f"  {r.name}: CE {r.ce_start:.4f}->{r.ce_end:.4f}, "
                  f"{r.its_per_sec:.1f} it/s, {r.n_params:,} params")
        return results

    # Comparison
    a, b = results[0], results[1]
    print("=" * 90)
    print("  A/B COMPARISON TABLE")
    print("=" * 90)
    print(f"  {'Metric':<25} | {a.name:>20} | {b.name:>20} | {'Winner':>12}")
    print(f"  {'-'*25}-+-{'-'*20}-+-{'-'*20}-+-{'-'*12}")

    comparisons = [
        ("Parameters", f"{a.n_params:,}", f"{b.n_params:,}",
         a.name if a.n_params < b.n_params else b.name),
        ("CE start", f"{a.ce_start:.4f}", f"{b.ce_start:.4f}",
         a.name if a.ce_start < b.ce_start else b.name),
        ("CE end", f"{a.ce_end:.4f}", f"{b.ce_end:.4f}",
         a.name if a.ce_end < b.ce_end else b.name),
        ("CE improvement", f"{a.ce_improvement*100:+.1f}%", f"{b.ce_improvement*100:+.1f}%",
         a.name if a.ce_improvement > b.ce_improvement else b.name),
        ("Phi mean", f"{a.phi_mean:.6f}", f"{b.phi_mean:.6f}",
         a.name if a.phi_mean > b.phi_mean else b.name),
        ("Phi stability", f"{a.phi_stability:.4f}", f"{b.phi_stability:.4f}",
         a.name if a.phi_stability > b.phi_stability else b.name),
        ("Avg grad norm", f"{a.avg_grad_norm:.4f}", f"{b.avg_grad_norm:.4f}",
         a.name if a.avg_grad_norm < b.avg_grad_norm else b.name),
        ("Speed (it/s)", f"{a.its_per_sec:.1f}", f"{b.its_per_sec:.1f}",
         a.name if a.its_per_sec > b.its_per_sec else b.name),
        ("Total time", f"{a.total_time:.1f}s", f"{b.total_time:.1f}s",
         a.name if a.total_time < b.total_time else b.name),
    ]

    a_wins = 0
    b_wins = 0
    for metric, va, vb, winner in comparisons:
        marker = "<--" if winner == a.name else "  -->"
        print(f"  {metric:<25} | {va:>20} | {vb:>20} | {winner:>12}")
        if winner == a.name:
            a_wins += 1
        else:
            b_wins += 1

    print()
    print(f"  Score: {a.name} {a_wins} - {b_wins} {b.name}")
    overall_winner = a.name if a_wins > b_wins else b.name
    print(f"  Overall Winner: {overall_winner}")

    # CE curve comparison (ASCII)
    print()
    print("  CE Curve Comparison (A=v1, B=v2):")
    graph_w = 50
    graph_h = 12
    step_size = max(1, n_steps // graph_w)

    ce_a = [a.ce_trajectory[i] for i in range(0, min(len(a.ce_trajectory), graph_w * step_size), step_size)][:graph_w]
    ce_b = [b.ce_trajectory[i] for i in range(0, min(len(b.ce_trajectory), graph_w * step_size), step_size)][:graph_w]

    # Filter NaN
    ce_a = [x if not math.isnan(x) else 0 for x in ce_a]
    ce_b = [x if not math.isnan(x) else 0 for x in ce_b]

    if ce_a and ce_b:
        all_ce = ce_a + ce_b
        max_ce = max(all_ce)
        min_ce = min(all_ce)
        rng = max_ce - min_ce if max_ce > min_ce else 1.0

        for row in range(graph_h, -1, -1):
            val = min_ce + rng * row / graph_h
            line = f"  {val:>6.2f} |"
            for k in range(min(len(ce_a), len(ce_b))):
                ha = ce_a[k] >= val
                hb = ce_b[k] >= val
                if ha and hb:
                    line += "*"
                elif ha:
                    line += "A"
                elif hb:
                    line += "B"
                else:
                    line += " "
            print(line)
        print(f"         +{'-' * min(len(ce_a), len(ce_b))}")
        print(f"          0{'':>{min(len(ce_a), len(ce_b))-5}}{n_steps} steps")

    # Gradient norm comparison
    print()
    print("  Gradient Norm Comparison:")
    gn_a = a.grad_norms
    gn_b = b.grad_norms
    # Show summary stats
    print(f"    {a.name:<20}: mean={np.mean(gn_a):.4f}  std={np.std(gn_a):.4f}  "
          f"max={max(gn_a):.4f}")
    print(f"    {b.name:<20}: mean={np.mean(gn_b):.4f}  std={np.std(gn_b):.4f}  "
          f"max={max(gn_b):.4f}")

    # Bar chart
    print()
    max_gn = max(np.mean(gn_a), np.mean(gn_b))
    bar_a = "#" * max(1, int(np.mean(gn_a) / max_gn * 40))
    bar_b = "#" * max(1, int(np.mean(gn_b) / max_gn * 40))
    print(f"    v1  |{bar_a}| {np.mean(gn_a):.4f}")
    print(f"    v2  |{bar_b}| {np.mean(gn_b):.4f}")

    # Speed comparison
    print()
    print("  Speed Comparison:")
    max_speed = max(a.its_per_sec, b.its_per_sec)
    bar_a = "#" * max(1, int(a.its_per_sec / max_speed * 40))
    bar_b = "#" * max(1, int(b.its_per_sec / max_speed * 40))
    print(f"    v1  |{bar_a}| {a.its_per_sec:.1f} it/s")
    print(f"    v2  |{bar_b}| {b.its_per_sec:.1f} it/s")
    speedup = b.its_per_sec / max(a.its_per_sec, 1e-6)
    if speedup > 1:
        print(f"    v2 is {speedup:.2f}x faster")
    else:
        print(f"    v1 is {1/speedup:.2f}x faster")

    # Law 97 candidate
    print()
    print("=" * 78)
    print("  LAW 97 CANDIDATE:")
    ce_delta = (b.ce_end - a.ce_end) / max(a.ce_end, 1e-12) * 100
    print(f"    v2 CE end vs v1: {ce_delta:+.1f}%")
    print(f"    v2 speed vs v1: {speedup:.2f}x")
    print(f"    v2 params: {b.n_params:,} vs v1: {a.n_params:,} "
          f"({(b.n_params/a.n_params - 1)*100:+.1f}%)")

    if b.ce_end < a.ce_end:
        print(f"    -> Law 97: RoPE+SwiGLU+GQA decoder achieves {-ce_delta:.1f}% lower CE "
              f"than learned-pos+standard-FFN at {speedup:.2f}x speed")
    elif a.ce_end < b.ce_end:
        print(f"    -> Law 97: Simpler architecture (v1) outperforms modern tricks (v2) "
              f"for consciousness-driven language modeling")
    else:
        print(f"    -> Law 97: Architecture choice (v1 vs v2) has minimal effect "
              f"when consciousness signal dominates")

    print(f"    Winner: {overall_winner} ({a_wins}-{b_wins})")
    print("=" * 78)

    return results


if __name__ == "__main__":
    main()
