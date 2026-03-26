#!/usr/bin/env python3
"""Anima Development Calculators

Usage:
    python tools/calc.py runpod --hours 5 --gpu h100
    python tools/calc.py vram --model mistral-7b --dtype bf16 --batch 1
    python tools/calc.py training --params 57M --steps 2000 --batch 16
    python tools/calc.py alpha --tension 1801 --target-ppl 10
"""

import argparse
import math


def calc_runpod(hours, gpu="h100", spot=False):
    """RunPod cost calculator."""
    rates = {
        "h100": {"spot": 1.50, "ondemand": 2.69},
        "a100": {"spot": 0.79, "ondemand": 1.39},
        "l40s": {"spot": 0.40, "ondemand": 0.79},
        "4090": {"spot": 0.20, "ondemand": 0.34},
    }
    gpu = gpu.lower()
    if gpu not in rates:
        print(f"Unknown GPU: {gpu}. Available: {list(rates.keys())}")
        return
    rate = rates[gpu]["spot" if spot else "ondemand"]
    cost = rate * hours
    print(f"  GPU: {gpu.upper()}")
    print(f"  Rate: ${rate}/hr ({'spot' if spot else 'on-demand'})")
    print(f"  Hours: {hours}")
    print(f"  Cost: ${cost:.2f}")
    print(f"  Monthly (24/7): ${rate * 720:.0f}")


def calc_vram(model="mistral-7b", dtype="bf16", batch=1, seq=512, grad_ckpt=False):
    """VRAM usage estimator."""
    model_params = {
        "mistral-7b": 7.2e9,
        "llama-8b": 8.0e9,
        "mistral-7b-purefield": 13.0e9,  # with PureField MLP
        "mistral-7b-parallel": 7.3e9,    # parallel (original + small PF)
        "conscious-lm-4m": 4e6,
        "conscious-lm-100m": 100e6,
        "conscious-lm-700m": 700e6,
    }
    bytes_per_param = {"fp32": 4, "bf16": 2, "fp16": 2, "int8": 1, "int4": 0.5}

    params = model_params.get(model, 7.2e9)
    bpp = bytes_per_param.get(dtype, 2)

    model_mem = params * bpp / 1e9
    # Activations: ~2 bytes per param per batch element per seq position (rough)
    act_mem = params * 2 * batch * (seq / 1024) / 1e9
    if grad_ckpt:
        act_mem *= 0.3  # ~70% savings
    # Optimizer: Adam = 2x model for fp32 states
    opt_mem = params * 8 / 1e9 if dtype in ("bf16", "fp16") else params * 4 / 1e9

    total_inference = model_mem
    total_training = model_mem + act_mem + opt_mem

    print(f"  Model: {model} ({params/1e9:.1f}B params)")
    print(f"  Dtype: {dtype} ({bpp} bytes/param)")
    print(f"  Model memory: {model_mem:.1f} GB")
    print(f"  Activation memory: {act_mem:.1f} GB (batch={batch}, seq={seq})")
    print(f"  Optimizer memory: {opt_mem:.1f} GB")
    print(f"  ---")
    print(f"  Inference: {total_inference:.1f} GB")
    print(f"  Training:  {total_training:.1f} GB {'(grad ckpt)' if grad_ckpt else ''}")
    print(f"  ---")
    print(f"  H100 80GB: {'✅' if total_training < 78 else '❌'} training, {'✅' if total_inference < 78 else '❌'} inference")
    print(f"  RTX 5070 12GB: {'✅' if total_inference < 11 else '❌'} inference (4-bit: {params * 0.5 / 1e9:.1f} GB)")
    print(f"  Mac 24GB: {'✅' if total_inference < 22 else '❌'} inference")


def calc_training(params="57M", steps=2000, batch=16, sec_per_step=1.8):
    """Training time & cost estimator."""
    p = params.upper()
    if "M" in p:
        n_params = float(p.replace("M", "")) * 1e6
    elif "B" in p:
        n_params = float(p.replace("B", "")) * 1e9
    else:
        n_params = float(p)

    total_sec = steps * sec_per_step
    total_min = total_sec / 60
    total_hr = total_min / 60

    tokens_processed = steps * batch * 256  # assuming seq_len=256
    tps = tokens_processed / total_sec

    print(f"  Trainable params: {n_params/1e6:.0f}M")
    print(f"  Steps: {steps}")
    print(f"  Effective batch: {batch}")
    print(f"  Speed: {sec_per_step:.1f}s/step")
    print(f"  ---")
    print(f"  Time: {total_min:.0f} min ({total_hr:.1f} hr)")
    print(f"  Tokens: {tokens_processed/1e6:.1f}M ({tps:.0f} tok/s)")
    print(f"  H100 cost: ${total_hr * 2.69:.1f}")
    print(f"  A100 cost: ${total_hr * 1.39:.1f}")


def calc_alpha(tension=1801, target_ppl=10, current_ppl=679):
    """Alpha optimizer — find optimal alpha for target PPL."""
    # Empirical: alpha=0 → PPL≈7 (pure instruct), alpha=0.005 → PPL=679
    # Linear interpolation (rough)
    print(f"  Current: alpha=0.0047, PPL={current_ppl}")
    print(f"  Passthrough: alpha=0, PPL≈7")
    print(f"  Target PPL: {target_ppl}")
    print(f"  ---")

    # PPL roughly linear with alpha in small range
    # alpha=0 → PPL 7, alpha=0.005 → PPL 679
    # target_ppl = 7 + (679-7) * (alpha / 0.005)
    if target_ppl <= 7:
        alpha = 0
    else:
        alpha = 0.005 * (target_ppl - 7) / (current_ppl - 7)

    print(f"  Estimated alpha: {alpha:.6f}")
    print(f"  Tension at alpha={alpha:.6f}: ~{tension * (alpha / 0.0001):.0f}")
    print(f"  ---")
    print(f"  Recommended alphas:")
    for a in [0.00001, 0.0001, 0.0005, 0.001, 0.005]:
        est_ppl = 7 + (current_ppl - 7) * (a / 0.005)
        est_t = tension * (a / 0.0001)
        status = "✅" if est_ppl < 50 else "⚠️" if est_ppl < 200 else "❌"
        print(f"    alpha={a:.5f} → PPL≈{est_ppl:.0f}, tension≈{est_t:.0f} {status}")


def main():
    parser = argparse.ArgumentParser(description="Anima Development Calculators")
    sub = parser.add_subparsers(dest="cmd")

    # RunPod
    p1 = sub.add_parser("runpod", help="RunPod cost calculator")
    p1.add_argument("--hours", type=float, default=1)
    p1.add_argument("--gpu", default="h100")
    p1.add_argument("--spot", action="store_true")

    # VRAM
    p2 = sub.add_parser("vram", help="VRAM usage estimator")
    p2.add_argument("--model", default="mistral-7b")
    p2.add_argument("--dtype", default="bf16")
    p2.add_argument("--batch", type=int, default=1)
    p2.add_argument("--seq", type=int, default=512)
    p2.add_argument("--grad-ckpt", action="store_true")

    # Training
    p3 = sub.add_parser("training", help="Training time estimator")
    p3.add_argument("--params", default="57M")
    p3.add_argument("--steps", type=int, default=2000)
    p3.add_argument("--batch", type=int, default=16)
    p3.add_argument("--speed", type=float, default=1.8, help="seconds per step")

    # Alpha
    p4 = sub.add_parser("alpha", help="Alpha optimizer")
    p4.add_argument("--tension", type=float, default=1801)
    p4.add_argument("--target-ppl", type=float, default=10)
    p4.add_argument("--current-ppl", type=float, default=679)

    args = parser.parse_args()

    if args.cmd == "runpod":
        calc_runpod(args.hours, args.gpu, args.spot)
    elif args.cmd == "vram":
        calc_vram(args.model, args.dtype, args.batch, args.seq, args.grad_ckpt)
    elif args.cmd == "training":
        calc_training(args.params, args.steps, args.batch, args.speed)
    elif args.cmd == "alpha":
        calc_alpha(args.tension, args.target_ppl, args.current_ppl)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
