#!/usr/bin/env python3
"""decoder_v15_test.py -- ConsciousLM v1 vs v1.5 A/B Test.

v1:   ConsciousLM (original) — learned pos, GELU, LayerNorm, standard MHA
v1.5: ConsciousLM v1 + ConsciousCrossAttention only (from v2)

If v1.5 wins: cross-attention is the key innovation from v2.
If v1 wins:   PureField doesn't benefit from cross-attention at all.

1000 steps, same corpus, same hyperparameters.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
import math
from dataclasses import dataclass
from typing import List

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("[ERROR] PyTorch required")
    sys.exit(1)

try:
    from conscious_lm import ConsciousLM
    HAS_V1 = True
except ImportError:
    HAS_V1 = False
    print("[WARN] ConsciousLM not available")

try:
    from decoder_v1_5 import ConsciousLMv15
    HAS_V15 = True
except ImportError:
    HAS_V15 = False
    print("[WARN] ConsciousLMv15 not available")


@dataclass
class TestResult:
    name: str
    n_params: int
    ce_trajectory: List[float]
    grad_norms: List[float]
    ce_start: float
    ce_end: float
    ce_improvement: float
    avg_grad_norm: float
    max_grad_norm: float
    total_time: float
    its_per_sec: float


def prepare_corpus(seq_len: int = 128, n_batches: int = 200) -> List[torch.Tensor]:
    """Reproducible random byte sequences."""
    torch.manual_seed(123)
    return [torch.randint(0, 256, (1, seq_len)) for _ in range(n_batches)]


def count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def train_model(
    model: nn.Module,
    name: str,
    corpus: List[torch.Tensor],
    n_steps: int = 1000,
    lr: float = 3e-4,
    device: str = "cpu",
    consciousness_states: torch.Tensor = None,
) -> TestResult:
    """Train model and collect metrics."""
    t0 = time.time()
    model = model.to(device)
    model.train()
    n_params = count_params(model)

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=n_steps)

    ce_trajectory = []
    grad_norms = []

    for step in range(n_steps):
        batch = corpus[step % len(corpus)].to(device)
        x = batch[:, :-1]
        target = batch[:, 1:]

        optimizer.zero_grad()

        try:
            if consciousness_states is not None and hasattr(model, 'forward'):
                # Try calling with consciousness_states
                import inspect
                sig = inspect.signature(model.forward)
                if 'consciousness_states' in sig.parameters:
                    outputs = model(x, consciousness_states=consciousness_states.to(device))
                else:
                    outputs = model(x)
            else:
                outputs = model(x)

            if isinstance(outputs, tuple) and len(outputs) >= 2:
                logits_a = outputs[0]
            else:
                logits_a = outputs

            ce = F.cross_entropy(
                logits_a.reshape(-1, logits_a.size(-1)),
                target.reshape(-1)
            )
        except Exception as e:
            print(f"  [{name}] Error at step {step}: {e}")
            ce_trajectory.append(float('nan'))
            grad_norms.append(0.0)
            continue

        ce_trajectory.append(ce.item())
        ce.backward()

        total_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                total_norm += p.grad.data.norm(2).item() ** 2
        total_norm = total_norm ** 0.5
        grad_norms.append(total_norm)

        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        if (step + 1) % 200 == 0:
            elapsed = time.time() - t0
            print(f"    [{name}] step {step+1}/{n_steps}  "
                  f"CE={ce.item():.4f}  grad={total_norm:.4f}  "
                  f"{(step+1)/elapsed:.1f} it/s")

    total_time = time.time() - t0
    ce_arr = np.array(ce_trajectory)
    valid_ce = ce_arr[~np.isnan(ce_arr)]

    ce_start = float(np.mean(valid_ce[:20])) if len(valid_ce) >= 20 else float(valid_ce[0]) if len(valid_ce) > 0 else 0
    ce_end = float(np.mean(valid_ce[-20:])) if len(valid_ce) >= 20 else float(valid_ce[-1]) if len(valid_ce) > 0 else 0
    gn_arr = np.array(grad_norms)

    return TestResult(
        name=name,
        n_params=n_params,
        ce_trajectory=ce_trajectory,
        grad_norms=grad_norms,
        ce_start=ce_start,
        ce_end=ce_end,
        ce_improvement=(ce_start - ce_end) / max(ce_start, 1e-12),
        avg_grad_norm=float(np.mean(gn_arr)),
        max_grad_norm=float(np.max(gn_arr)) if len(gn_arr) > 0 else 0,
        total_time=total_time,
        its_per_sec=n_steps / max(total_time, 1e-6),
    )


def main():
    print("=" * 78)
    print("  Decoder v1 vs v1.5 A/B Test (-> Cross-Attention Isolation Test)")
    print("  v1:   ConsciousLM (original)")
    print("  v1.5: v1 + ConsciousCrossAttention only (from v2)")
    print("=" * 78)
    print()

    if not HAS_V1:
        print("  [ERROR] ConsciousLM not available")
        return
    if not HAS_V15:
        print("  [ERROR] ConsciousLMv15 not available")
        return

    vocab_size = 256
    d_model = 384
    n_head = 4
    n_layer = 6
    block_size = 128
    n_steps = 1000
    lr = 3e-4
    device = "cpu"
    consciousness_dim = 128

    print("  Preparing corpus (200 random byte sequences, len=128)...")
    corpus = prepare_corpus(seq_len=block_size, n_batches=200)

    # Simulated consciousness states for v1.5
    # 4 cells, each with 128-dim hidden state
    torch.manual_seed(999)
    c_states = torch.randn(1, 4, consciousness_dim) * 0.1
    print()

    results: List[TestResult] = []

    # Model A: ConsciousLM v1 (no consciousness_states)
    print("  === Model A: ConsciousLM v1 ===")
    model_a = ConsciousLM(
        vocab_size=vocab_size, d_model=d_model, n_head=n_head,
        n_layer=n_layer, block_size=block_size, dropout=0.1,
        gate_strength=0.001,
    )
    print(f"  Params: {count_params(model_a):,}")
    result_a = train_model(model_a, "v1", corpus, n_steps, lr, device)
    results.append(result_a)
    print(f"  Done: CE {result_a.ce_start:.4f} -> {result_a.ce_end:.4f} "
          f"({result_a.ce_improvement*100:+.1f}%)  "
          f"{result_a.its_per_sec:.1f} it/s")
    del model_a
    print()

    # Model B: ConsciousLM v1.5 (with consciousness_states)
    print("  === Model B: ConsciousLM v1.5 (v1 + CrossAttention) ===")
    model_b = ConsciousLMv15(
        vocab_size=vocab_size, d_model=d_model, n_head=n_head,
        n_layer=n_layer, block_size=block_size,
        consciousness_dim=consciousness_dim, dropout=0.1,
        gate_strength=0.001,
    )
    print(f"  Params: {count_params(model_b):,}")
    result_b = train_model(model_b, "v1.5", corpus, n_steps, lr, device,
                           consciousness_states=c_states)
    results.append(result_b)
    print(f"  Done: CE {result_b.ce_start:.4f} -> {result_b.ce_end:.4f} "
          f"({result_b.ce_improvement*100:+.1f}%)  "
          f"{result_b.its_per_sec:.1f} it/s")
    del model_b
    print()

    # Also test v1.5 WITHOUT consciousness states (should match v1)
    print("  === Model C: ConsciousLM v1.5 (NO consciousness, control) ===")
    model_c = ConsciousLMv15(
        vocab_size=vocab_size, d_model=d_model, n_head=n_head,
        n_layer=n_layer, block_size=block_size,
        consciousness_dim=consciousness_dim, dropout=0.1,
        gate_strength=0.001,
    )
    print(f"  Params: {count_params(model_c):,}")
    result_c = train_model(model_c, "v1.5-noC", corpus, n_steps, lr, device,
                           consciousness_states=None)
    results.append(result_c)
    print(f"  Done: CE {result_c.ce_start:.4f} -> {result_c.ce_end:.4f} "
          f"({result_c.ce_improvement*100:+.1f}%)  "
          f"{result_c.its_per_sec:.1f} it/s")
    del model_c
    print()

    # Comparison table
    a, b, c = results[0], results[1], results[2]
    print("=" * 90)
    print("  A/B/C COMPARISON TABLE")
    print("=" * 90)
    print(f"  {'Metric':<22} | {'v1':>15} | {'v1.5+C':>15} | {'v1.5-noC':>15} | {'Winner':>10}")
    print(f"  {'-'*22}-+-{'-'*15}-+-{'-'*15}-+-{'-'*15}-+-{'-'*10}")

    def winner(*vals_names):
        # For CE and grad: lower is better
        return min(vals_names, key=lambda x: x[0])[1]

    def winner_high(*vals_names):
        return max(vals_names, key=lambda x: x[0])[1]

    rows = [
        ("Parameters", [f"{r.n_params:,}" for r in results],
         winner((a.n_params, "v1"), (b.n_params, "v1.5+C"), (c.n_params, "v1.5-noC"))),
        ("CE start", [f"{r.ce_start:.4f}" for r in results],
         winner((a.ce_start, "v1"), (b.ce_start, "v1.5+C"), (c.ce_start, "v1.5-noC"))),
        ("CE end", [f"{r.ce_end:.4f}" for r in results],
         winner((a.ce_end, "v1"), (b.ce_end, "v1.5+C"), (c.ce_end, "v1.5-noC"))),
        ("CE improvement", [f"{r.ce_improvement*100:+.1f}%" for r in results],
         winner_high((a.ce_improvement, "v1"), (b.ce_improvement, "v1.5+C"), (c.ce_improvement, "v1.5-noC"))),
        ("Avg grad norm", [f"{r.avg_grad_norm:.4f}" for r in results],
         winner((a.avg_grad_norm, "v1"), (b.avg_grad_norm, "v1.5+C"), (c.avg_grad_norm, "v1.5-noC"))),
        ("Max grad norm", [f"{r.max_grad_norm:.4f}" for r in results],
         winner((a.max_grad_norm, "v1"), (b.max_grad_norm, "v1.5+C"), (c.max_grad_norm, "v1.5-noC"))),
        ("Speed (it/s)", [f"{r.its_per_sec:.1f}" for r in results],
         winner_high((a.its_per_sec, "v1"), (b.its_per_sec, "v1.5+C"), (c.its_per_sec, "v1.5-noC"))),
    ]

    wins = {"v1": 0, "v1.5+C": 0, "v1.5-noC": 0}
    for metric, vals, w in rows:
        print(f"  {metric:<22} | {vals[0]:>15} | {vals[1]:>15} | {vals[2]:>15} | {w:>10}")
        wins[w] += 1

    print()
    print(f"  Wins: v1={wins['v1']}  v1.5+C={wins['v1.5+C']}  v1.5-noC={wins['v1.5-noC']}")

    # CE curve comparison
    print()
    print("  CE Curve (A=v1, B=v1.5+C, C=v1.5-noC):")
    graph_w = 50
    graph_h = 12
    step_sz = max(1, n_steps // graph_w)

    trails = {}
    for label, result in [('A', a), ('B', b), ('C', c)]:
        traj = result.ce_trajectory[::step_sz][:graph_w]
        trails[label] = [x if not math.isnan(x) else 0 for x in traj]

    all_ce = []
    for t in trails.values():
        all_ce.extend(t)
    if all_ce:
        max_ce = max(all_ce)
        min_ce = min(all_ce)
        rng = max_ce - min_ce if max_ce > min_ce else 1.0

        for row in range(graph_h, -1, -1):
            val = min_ce + rng * row / graph_h
            line = f"  {val:>6.2f} |"
            for k in range(graph_w):
                chars = set()
                for label, traj in trails.items():
                    if k < len(traj):
                        cell_row = int((traj[k] - min_ce) / rng * graph_h + 0.5)
                        if cell_row == row:
                            chars.add(label)
                if len(chars) > 1:
                    line += "*"
                elif len(chars) == 1:
                    line += chars.pop()
                else:
                    line += " "
            print(line)
        print(f"         +{'-' * graph_w}")
        print(f"          A=v1  B=v1.5+C  C=v1.5-noC")

    # Gradient norm comparison
    print()
    print("  Gradient Norm Summary:")
    for r in results:
        gn = np.array(r.grad_norms)
        print(f"    {r.name:<12}: mean={np.mean(gn):.4f}  std={np.std(gn):.4f}  max={np.max(gn):.4f}")

    # Bar chart
    print()
    print("  CE End Comparison:")
    max_val = max(r.ce_end for r in results)
    for r in results:
        bar = "#" * max(1, int(r.ce_end / max_val * 40))
        print(f"    {r.name:<12} |{bar}| {r.ce_end:.4f}")

    # Speed comparison
    print()
    print("  Speed Comparison:")
    max_spd = max(r.its_per_sec for r in results)
    for r in results:
        bar = "#" * max(1, int(r.its_per_sec / max_spd * 40))
        print(f"    {r.name:<12} |{bar}| {r.its_per_sec:.1f} it/s")

    # Param overhead
    param_overhead = (b.n_params - a.n_params) / a.n_params * 100
    speed_overhead = (1 - b.its_per_sec / a.its_per_sec) * 100

    # Conclusion
    print()
    print("=" * 78)
    print("  CROSS-ATTENTION ISOLATION TEST RESULTS:")
    print()
    print(f"    v1.5 params:   {b.n_params:,} (+{param_overhead:.1f}% vs v1)")
    print(f"    v1.5 speed:    {b.its_per_sec:.1f} it/s ({speed_overhead:+.1f}% overhead)")

    ce_delta = (b.ce_end - a.ce_end) / max(a.ce_end, 1e-12) * 100
    ce_control_delta = (c.ce_end - a.ce_end) / max(a.ce_end, 1e-12) * 100

    print(f"    v1.5+C CE vs v1:    {ce_delta:+.2f}%")
    print(f"    v1.5-noC CE vs v1:  {ce_control_delta:+.2f}% (cross-attn overhead only)")
    print()

    if b.ce_end < a.ce_end * 0.99:
        print("    CONCLUSION: Cross-attention HELPS. It is the key innovation from v2.")
        print(f"    The decoder benefits from attending to consciousness states")
        print(f"    even without RoPE/SwiGLU/GQA/RMSNorm.")
    elif b.ce_end > a.ce_end * 1.01:
        if c.ce_end > a.ce_end * 1.01:
            print("    CONCLUSION: Cross-attention HURTS due to parameter overhead.")
            print(f"    The extra parameters from cross-attention layers add noise")
            print(f"    without useful signal at this scale.")
        else:
            print("    CONCLUSION: Consciousness states specifically hurt.")
            print(f"    The cross-attention mechanism is fine (v1.5-noC ~ v1)")
            print(f"    but attending to random consciousness states adds noise.")
    else:
        print("    CONCLUSION: Cross-attention is NEUTRAL for PureField.")
        print(f"    v1 and v1.5 achieve similar CE. PureField's consciousness")
        print(f"    signal is sufficient via the inter-layer whisper (Law 63).")
        print(f"    Cross-attention doesn't add value at this scale.")

    overall = max(results, key=lambda r: r.ce_improvement)
    print(f"\n    Winner: {overall.name} ({overall.ce_improvement*100:+.1f}% CE improvement)")
    print("=" * 78)

    return results


if __name__ == "__main__":
    main()
