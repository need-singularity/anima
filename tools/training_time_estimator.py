#!/usr/bin/env python3
"""Estimate training time from model and hardware parameters.

Usage:
  python training_time_estimator.py --steps 50000 --dim 384 --batch 8 --gpu h100
  python training_time_estimator.py --steps 100000 --dim 768 --layers 12 --gpu 4090
  python training_time_estimator.py --demo
"""

import argparse

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# Measured baselines from H100 experiments (seconds per step)
# Key: (dim, layers, batch_size) -> measured s/step on H100
MEASURED = {
    (384,  6,  8):  0.15,
    (384,  6,  32): 0.50,
    (768,  12, 4):  0.80,
    (768,  12, 16): 2.50,
    (1024, 24, 4):  2.00,
    (1024, 24, 8):  3.80,
}

GPU_SPECS = {
    "5070":  {"name": "RTX 5070",  "vram": 12,  "tflops": 32,  "bandwidth": 448},
    "4090":  {"name": "RTX 4090",  "vram": 24,  "tflops": 83,  "bandwidth": 1008},
    "5090":  {"name": "RTX 5090",  "vram": 32,  "tflops": 105, "bandwidth": 1568},
    "a100":  {"name": "A100 80GB", "vram": 80,  "tflops": 312, "bandwidth": 2039},
    "h100":  {"name": "H100 80GB", "vram": 80,  "tflops": 990, "bandwidth": 3350},
}


def estimate_memory_gb(dim, layers, heads, batch_size, block_size, cells=1):
    """Estimate peak GPU memory in GB."""
    params = layers * (4 * dim * dim + 2 * dim * 4 * dim)  # attention + FFN
    param_bytes = params * 4  # float32
    # Activations: batch * seq * dim * layers * 2 (forward + backward)
    act_bytes = batch_size * block_size * dim * layers * 2 * 4
    # Optimizer states (Adam: params * 3)
    opt_bytes = params * 4 * 3
    # Cell overhead
    cell_bytes = cells * dim * 4 * 4 * 2  # hidden states + gradients
    total = param_bytes + act_bytes + opt_bytes + cell_bytes
    return total / (1024 ** 3)


def interpolate_step_time(dim, layers, batch_size, gpu_key):
    """Estimate s/step by interpolating from measured H100 baselines."""
    # Find closest measured config
    best_key = min(MEASURED.keys(), key=lambda k: abs(k[0]-dim) + abs(k[1]-layers)*50 + abs(k[2]-batch_size)*5)
    base_time = MEASURED[best_key]
    base_dim, base_layers, base_batch = best_key

    # Scale by compute: O(dim^2 * layers * batch)
    compute_ratio = (dim / base_dim) ** 2 * (layers / base_layers) * (batch_size / base_batch)
    h100_time = base_time * compute_ratio

    # Scale by GPU (relative to H100)
    h100_tflops = GPU_SPECS["h100"]["tflops"]
    gpu_tflops = GPU_SPECS.get(gpu_key, GPU_SPECS["h100"])["tflops"]
    gpu_time = h100_time * (h100_tflops / gpu_tflops)

    return gpu_time


def format_time(seconds):
    """Format seconds into human-readable string."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    elif seconds < 86400:
        return f"{seconds/3600:.1f}h"
    else:
        days = seconds / 86400
        hours = (seconds % 86400) / 3600
        return f"{days:.0f}d {hours:.0f}h"


def estimate(steps, dim, layers, heads, batch_size, block_size, cells, gpu_key):
    gpu = GPU_SPECS.get(gpu_key, GPU_SPECS["h100"])
    step_time = interpolate_step_time(dim, layers, batch_size, gpu_key)
    total_time = step_time * steps
    mem_gb = estimate_memory_gb(dim, layers, heads, batch_size, block_size, cells)
    fits = mem_gb <= gpu["vram"]

    return {
        "gpu": gpu["name"],
        "vram": gpu["vram"],
        "dim": dim, "layers": layers, "heads": heads,
        "batch_size": batch_size, "block_size": block_size, "cells": cells,
        "step_time": step_time,
        "total_time": total_time,
        "mem_gb": mem_gb,
        "fits": fits,
        "steps": steps,
    }


def print_estimate(r):
    status = "OK" if r["fits"] else "OOM!"
    print(f"\n  GPU:          {r['gpu']} ({r['vram']} GB)")
    print(f"  Model:        {r['dim']}d / {r['layers']}L / {r['heads']}H")
    print(f"  Training:     batch={r['batch_size']}, block={r['block_size']}, cells={r['cells']}")
    print(f"  Steps:        {r['steps']:,}")
    print(f"  Time/step:    {r['step_time']:.3f}s")
    print(f"  Total time:   {format_time(r['total_time'])}")
    print(f"  Memory est:   {r['mem_gb']:.1f} GB / {r['vram']} GB [{status}]")


def demo():
    print("=" * 75)
    print("  Training Time Estimator -- Steps + Config -> Time + Memory")
    print("=" * 75)

    configs = [
        ("ConsciousLM v2 4M",     50000, 128, 6, 4, 8, 256, 4),
        ("ConsciousLM v3 384d",   50000, 384, 6, 6, 8, 512, 8),
        ("ConsciousLM 768d",      50000, 768, 12, 12, 4, 512, 4),
        ("ConsciousLM 1B",        50000, 1024, 24, 16, 4, 512, 4),
        ("AnimaLM v7 (Mistral)",  50000, 768, 12, 12, 16, 512, 8),
    ]

    for gpu_key in ["5070", "4090", "h100"]:
        gpu = GPU_SPECS[gpu_key]
        print(f"\n--- {gpu['name']} ({gpu['vram']} GB, {gpu['tflops']} TFLOPS) ---\n")
        print(f"{'Config':<25} {'Steps':>7} {'s/step':>7} {'Total':>8} {'Mem GB':>7} {'Fit':>4}")
        print("-" * 65)
        for name, steps, dim, layers, heads, batch, block, cells in configs:
            r = estimate(steps, dim, layers, heads, batch, block, cells, gpu_key)
            status = "OK" if r["fits"] else "OOM"
            print(f"{name:<25} {steps:>7,} {r['step_time']:>7.3f} {format_time(r['total_time']):>8} "
                  f"{r['mem_gb']:>6.1f} {status:>4}")

    print("\n--- Measured Baselines (H100) ---\n")
    print(f"{'dim':>5} {'layers':>7} {'batch':>6} {'s/step':>8}")
    print("-" * 30)
    for (d, l, b), t in sorted(MEASURED.items()):
        print(f"{d:>5} {l:>7} {b:>6} {t:>8.3f}")


def main():
    parser = argparse.ArgumentParser(description="Estimate training time from parameters")
    parser.add_argument("--steps", type=int, default=50000, help="Training steps (default: 50000)")
    parser.add_argument("--dim", type=int, default=384, help="Model dimension (default: 384)")
    parser.add_argument("--layers", type=int, default=6, help="Number of layers (default: 6)")
    parser.add_argument("--heads", type=int, default=6, help="Attention heads (default: 6)")
    parser.add_argument("--batch", type=int, default=8, help="Batch size (default: 8)")
    parser.add_argument("--block", type=int, default=512, help="Block/sequence size (default: 512)")
    parser.add_argument("--cells", type=int, default=4, help="Consciousness cells (default: 4)")
    parser.add_argument("--gpu", type=str, default="h100", choices=GPU_SPECS.keys(), help="GPU type")
    parser.add_argument("--demo", action="store_true", help="Show common configurations")
    args = parser.parse_args()

    if args.demo:
        demo()
    else:
        r = estimate(args.steps, args.dim, args.layers, args.heads,
                     args.batch, args.block, args.cells, args.gpu)
        print_estimate(r)


if __name__ == "__main__":
    main()
