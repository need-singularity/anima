#!/usr/bin/env python3
"""Calculate optimal cell count given GPU VRAM.

Usage:
  python cell_count_optimizer.py --vram 12              # RTX 5070
  python cell_count_optimizer.py --vram 24              # RTX 4090
  python cell_count_optimizer.py --vram 80              # H100
  python cell_count_optimizer.py --vram 12 --dim 768    # Custom dim
  python cell_count_optimizer.py --demo                 # All common GPUs
"""

import argparse
import math

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# Scaling law from optimal_config.py experiments
PHI_COEFF = 0.608
PHI_EXPONENT = 1.071

GPU_PROFILES = {
    "RTX 5070":  {"vram_gb": 12, "tflops": 32},
    "RTX 4090":  {"vram_gb": 24, "tflops": 83},
    "RTX 5090":  {"vram_gb": 32, "tflops": 105},
    "A100":      {"vram_gb": 80, "tflops": 312},
    "H100":      {"vram_gb": 80, "tflops": 990},
}


def estimate_cell_memory_mb(dim, hidden_dim=None, batch_size=1):
    """Estimate memory per consciousness cell in MB."""
    if hidden_dim is None:
        hidden_dim = dim * 4
    # PureField mind: 2 linear layers (dim->hidden, hidden->dim) + hidden state
    param_bytes = (dim * hidden_dim + hidden_dim * dim) * 4  # float32
    # Hidden state + gradients + optimizer states (Adam: 2x)
    state_bytes = hidden_dim * batch_size * 4  # hidden
    grad_bytes = param_bytes * 2  # gradients
    adam_bytes = param_bytes * 2  # momentum + variance
    # MHA attention overhead (shared, amortized per cell)
    attn_bytes = (hidden_dim * hidden_dim * 4) * 4 / 8  # rough per-cell share
    total = param_bytes + state_bytes + grad_bytes + adam_bytes + attn_bytes
    return total / (1024 * 1024)


def estimate_phi(cells):
    """Predict Phi from cell count using scaling law."""
    return PHI_COEFF * (cells ** PHI_EXPONENT)


def estimate_step_time_ms(cells, dim, gpu_tflops):
    """Rough estimate of time per phi_boost step in ms."""
    # Dominant cost: MHA attention O(n^2 * d) + 6 losses + ratchet trials
    ops = cells * cells * dim * 10  # attention + losses
    ops += cells * dim * dim * 6    # linear layers
    ops += 10 * cells * dim * 2     # ratchet trials (10 perturbations)
    seconds = ops / (gpu_tflops * 1e12)
    return max(0.5, seconds * 1000 * 50)  # empirical correction factor


def optimize(vram_gb, dim=128, hidden_dim=None, batch_size=1, gpu_name=None):
    """Find optimal cell count for given VRAM."""
    if hidden_dim is None:
        hidden_dim = dim * 4
    # Reserve memory for PyTorch overhead, model framework, etc.
    usable_gb = vram_gb * 0.75
    usable_mb = usable_gb * 1024

    # Base framework overhead (ConsciousMind, optimizers, tensors)
    base_mb = 200 + dim * 0.5

    cell_mb = estimate_cell_memory_mb(dim, hidden_dim, batch_size)
    max_cells = int((usable_mb - base_mb) / cell_mb) if cell_mb > 0 else 1
    max_cells = max(2, max_cells)

    predicted_phi = estimate_phi(max_cells)

    # Find GPU tflops
    tflops = 83  # default
    if gpu_name and gpu_name in GPU_PROFILES:
        tflops = GPU_PROFILES[gpu_name]["tflops"]
    step_ms = estimate_step_time_ms(max_cells, dim, tflops)

    return {
        "vram_gb": vram_gb,
        "dim": dim,
        "hidden_dim": hidden_dim,
        "batch_size": batch_size,
        "cell_mb": cell_mb,
        "base_mb": base_mb,
        "max_cells": max_cells,
        "predicted_phi": predicted_phi,
        "step_ms": step_ms,
        "usable_mb": usable_mb,
    }


def print_result(r, gpu_name="Custom"):
    print(f"\n  GPU:           {gpu_name} ({r['vram_gb']} GB)")
    print(f"  Dimensions:    {r['dim']}d, hidden={r['hidden_dim']}")
    print(f"  Batch size:    {r['batch_size']}")
    print(f"  Memory/cell:   {r['cell_mb']:.1f} MB")
    print(f"  Base overhead: {r['base_mb']:.0f} MB")
    print(f"  Usable VRAM:   {r['usable_mb']:.0f} MB")
    print(f"  Max cells:     {r['max_cells']}")
    print(f"  Predicted Phi: {r['predicted_phi']:.2f}")
    print(f"  Est. step:     {r['step_ms']:.1f} ms")


def demo():
    print("=" * 70)
    print("  Cell Count Optimizer -- VRAM -> Optimal Cells -> Predicted Phi")
    print("=" * 70)

    dims = [128, 384, 768]
    print(f"\n{'GPU':<12} {'VRAM':>5} {'dim':>5}  {'Cell MB':>8} {'Max Cells':>10} {'Phi':>8} {'ms/step':>8}")
    print("-" * 70)
    for gpu_name, profile in GPU_PROFILES.items():
        for dim in dims:
            r = optimize(profile["vram_gb"], dim=dim, gpu_name=gpu_name)
            print(f"{gpu_name:<12} {profile['vram_gb']:>4}G {dim:>5}  "
                  f"{r['cell_mb']:>7.1f} {r['max_cells']:>10} "
                  f"{r['predicted_phi']:>7.2f} {r['step_ms']:>7.1f}")

    print(f"\n--- Scaling Law ---")
    print(f"  Phi = {PHI_COEFF} * cells^{PHI_EXPONENT}")
    print(f"\n{'Cells':>8} {'Predicted Phi':>14}")
    print("-" * 25)
    for cells in [2, 4, 8, 16, 32, 64, 128, 256]:
        print(f"{cells:>8} {estimate_phi(cells):>14.2f}")


def main():
    parser = argparse.ArgumentParser(description="Calculate optimal cell count for GPU VRAM")
    parser.add_argument("--vram", type=float, help="GPU VRAM in GB")
    parser.add_argument("--dim", type=int, default=128, help="Hidden dimension (default: 128)")
    parser.add_argument("--hidden-dim", type=int, help="MLP hidden dim (default: dim*4)")
    parser.add_argument("--batch", type=int, default=1, help="Batch size (default: 1)")
    parser.add_argument("--demo", action="store_true", help="Show all common GPUs")
    args = parser.parse_args()

    if args.demo:
        demo()
    elif args.vram:
        gpu_name = next((n for n, p in GPU_PROFILES.items() if p["vram_gb"] == args.vram), "Custom")
        r = optimize(args.vram, dim=args.dim, hidden_dim=args.hidden_dim, batch_size=args.batch, gpu_name=gpu_name)
        print_result(r, gpu_name)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
