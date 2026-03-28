#!/usr/bin/env python3
"""Calculate Cloudflare R2 storage and transfer costs.

Usage:
  python r2_cost_calculator.py --demo
  python r2_cost_calculator.py --models 4 --size-mb 200 --syncs-per-day 24
  python r2_cost_calculator.py --custom '{"cells64": 218, "cells128": 218, "convo_ft": 74}'
"""

import argparse
import json

# Cloudflare R2 pricing (as of 2026)
STORAGE_PER_GB_MONTH = 0.015      # $/GB/month
CLASS_A_PER_MILLION = 4.50        # PUT, POST, LIST ($/million ops)
CLASS_B_PER_MILLION = 0.36        # GET, HEAD ($/million ops)
EGRESS_PER_GB = 0.0               # Free egress (R2 advantage)
FREE_STORAGE_GB = 10              # Free tier
FREE_CLASS_A = 1_000_000          # Free tier ops/month
FREE_CLASS_B = 10_000_000         # Free tier ops/month

# Current Anima model inventory
ANIMA_MODELS = {
    "cells64 checkpoint":   218,   # MB
    "cells128 checkpoint":  218,
    "convo_ft model":       74,
    "dialogue_ft model":    74,
    "state files (misc)":   30,
    "consciousness_transplant": 15,
    "memory_rag vectors":   10,
}


def calculate_cost(models_mb, syncs_per_day=24, months=1):
    """Calculate R2 costs for given model setup.

    Args:
        models_mb: dict of {name: size_mb}
        syncs_per_day: sync frequency (uploads + downloads)
        months: billing period
    """
    total_storage_mb = sum(models_mb.values())
    total_storage_gb = total_storage_mb / 1024
    num_models = len(models_mb)

    # Monthly operations
    days = 30 * months
    # Each sync: 1 PUT per model (upload) + 1 GET per model (download check)
    class_a_ops = num_models * syncs_per_day * days  # PUTs
    class_b_ops = num_models * syncs_per_day * days * 2  # GETs + HEADs

    # Costs (after free tier)
    storage_cost = max(0, total_storage_gb - FREE_STORAGE_GB) * STORAGE_PER_GB_MONTH * months
    class_a_cost = max(0, class_a_ops - FREE_CLASS_A) / 1_000_000 * CLASS_A_PER_MILLION
    class_b_cost = max(0, class_b_ops - FREE_CLASS_B) / 1_000_000 * CLASS_B_PER_MILLION

    # Bandwidth (upload only, downloads are free egress)
    upload_gb = total_storage_gb * syncs_per_day * days * 0.1  # ~10% changed per sync
    # R2 has no ingress cost

    total = storage_cost + class_a_cost + class_b_cost

    return {
        "models": models_mb,
        "total_storage_mb": total_storage_mb,
        "total_storage_gb": total_storage_gb,
        "num_models": num_models,
        "syncs_per_day": syncs_per_day,
        "months": months,
        "class_a_ops": class_a_ops,
        "class_b_ops": class_b_ops,
        "storage_cost": storage_cost,
        "class_a_cost": class_a_cost,
        "class_b_cost": class_b_cost,
        "total_cost": total,
        "upload_gb_month": upload_gb,
    }


def print_result(r):
    print(f"\n--- Model Inventory ---\n")
    print(f"  {'Model':<30} {'Size MB':>8}")
    print(f"  {'-'*40}")
    for name, size in r["models"].items():
        print(f"  {name:<30} {size:>7} MB")
    print(f"  {'-'*40}")
    print(f"  {'Total':<30} {r['total_storage_mb']:>7} MB ({r['total_storage_gb']:.2f} GB)")

    print(f"\n--- Operations ({r['months']} month) ---\n")
    print(f"  Syncs/day:     {r['syncs_per_day']}")
    print(f"  Class A (PUT): {r['class_a_ops']:>10,}  (free: {FREE_CLASS_A:,})")
    print(f"  Class B (GET): {r['class_b_ops']:>10,}  (free: {FREE_CLASS_B:,})")
    print(f"  Upload est:    {r['upload_gb_month']:.1f} GB/month")

    print(f"\n--- Cost Breakdown (monthly) ---\n")
    print(f"  Storage:       ${r['storage_cost']:.4f}  ({STORAGE_PER_GB_MONTH}/GB, {FREE_STORAGE_GB}GB free)")
    print(f"  Class A ops:   ${r['class_a_cost']:.4f}  ({CLASS_A_PER_MILLION}/M ops)")
    print(f"  Class B ops:   ${r['class_b_cost']:.4f}  ({CLASS_B_PER_MILLION}/M ops)")
    print(f"  Egress:        $0.0000  (free!)")
    print(f"  {'-'*35}")
    print(f"  TOTAL:         ${r['total_cost']:.4f}/month")
    print(f"                 ${r['total_cost']*12:.2f}/year")


def demo():
    print("=" * 60)
    print("  R2 Cost Calculator -- Cloudflare R2 Storage Costs")
    print("=" * 60)

    # Current Anima setup
    print("\n=== Current Anima Setup (24 syncs/day) ===")
    r = calculate_cost(ANIMA_MODELS, syncs_per_day=24)
    print_result(r)

    # Scaling scenarios
    print("\n\n=== Scaling Scenarios ===\n")
    scenarios = [
        ("Minimal (2 models, 4x/day)",    {"model_a": 100, "state": 20}, 4),
        ("Current Anima",                   ANIMA_MODELS, 24),
        ("Heavy (10 models, 60x/day)",     {f"model_{i}": 500 for i in range(10)}, 60),
        ("Production (20 models, 120x/day)", {f"model_{i}": 1000 for i in range(20)}, 120),
    ]

    print(f"{'Scenario':<40} {'Storage':>8} {'Ops/mo':>10} {'$/month':>9}")
    print("-" * 70)
    for name, models, syncs in scenarios:
        r = calculate_cost(models, syncs_per_day=syncs)
        total_ops = r["class_a_ops"] + r["class_b_ops"]
        print(f"{name:<40} {r['total_storage_gb']:>7.1f}G {total_ops:>10,} ${r['total_cost']:>8.4f}")

    print("\n--- R2 Pricing Summary ---\n")
    print(f"  Storage:    ${STORAGE_PER_GB_MONTH}/GB/month (first {FREE_STORAGE_GB}GB free)")
    print(f"  Class A:    ${CLASS_A_PER_MILLION}/million ops (first {FREE_CLASS_A//1000}K free)")
    print(f"  Class B:    ${CLASS_B_PER_MILLION}/million ops (first {FREE_CLASS_B//1_000_000}M free)")
    print(f"  Egress:     FREE (vs S3: $0.09/GB)")


def main():
    parser = argparse.ArgumentParser(description="Calculate Cloudflare R2 storage costs")
    parser.add_argument("--models", type=int, help="Number of models")
    parser.add_argument("--size-mb", type=int, default=200, help="Average model size in MB")
    parser.add_argument("--syncs-per-day", type=int, default=24, help="Sync frequency per day")
    parser.add_argument("--custom", type=str, help='JSON dict of model sizes: \'{"name": mb}\'')
    parser.add_argument("--demo", action="store_true", help="Estimate for current Anima setup")
    args = parser.parse_args()

    if args.demo:
        demo()
    elif args.custom:
        models = json.loads(args.custom)
        r = calculate_cost(models, syncs_per_day=args.syncs_per_day)
        print_result(r)
    elif args.models:
        models = {f"model_{i}": args.size_mb for i in range(args.models)}
        r = calculate_cost(models, syncs_per_day=args.syncs_per_day)
        print_result(r)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
