#!/usr/bin/env python3
"""Parameter optimizer: apply sweep results to anima_alive.py.

Usage:
  python param_optimizer.py --show       # Display current vs optimal values
  python param_optimizer.py --dry-run    # Show what would change (default)
  python param_optimizer.py --apply      # Actually update anima_alive.py
  python param_optimizer.py --demo       # Run full demo
"""

import argparse
import json
import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET = os.path.join(SCRIPT_DIR, "anima_alive.py")
SWEEP_FILE = os.path.join(SCRIPT_DIR, "data", "param_sweep_results.json")

# Param name -> (search pattern, current value, optimal value, description)
PARAMS = {
    "SL2_blend": {
        "pattern": r"(blend = )(\d+\.\d+)( \* cell_importance)",
        "current": 0.15, "optimal": 0.10,
        "desc": "SL2 attention-gated blend factor",
    },
    "WI1_soliton_speed": {
        "pattern": r"(self\._soliton_pos = \(self\._soliton_pos \+ )(\d+\.\d+)(\) % len)",
        "current": 0.15, "optimal": 0.05,
        "desc": "WI1 soliton propagation speed",
    },
    "WI1_amplitude": {
        "pattern": r"(cell\.hidden = cell\.hidden \* \(1\.0 \+ )(\d+\.\d+)( \* amplitude\))",
        "current": 0.04, "optimal": 0.06,
        "desc": "WI1 soliton amplitude scaling",
    },
    "PX5_rotation_factor": {
        "pattern": r"(c\.hidden = c\.hidden \+ )(\d+\.\d+)( \* rotated\.unsqueeze)",
        "current": 0.05, "optimal": 0.02,
        "desc": "PX5 information pump injection scale",
    },
    "EC1_earn_rate": {
        "pattern": r"(self\._ec1_wealth \+= current_phi \* )(\d+\.\d+)(  # earn)",
        "current": 0.1, "optimal": 0.05,
        "desc": "EC1 consciousness economy earn rate",
    },
    "MUT2_mutation_scale": {
        "pattern": r"(mitosis_engine\.cells\[mut_idx\]\.hidden \+= torch\.randn_like\(saved_h\) \* )(\d+\.\d+)",
        "current": 0.15, "optimal": 0.20,
        "desc": "MUT2 beneficial mutation perturbation scale",
    },
    "GEN1_topdown_ratio": {
        "pattern": r"(c\.hidden = 0\.97 \* c\.hidden \+ )(\d+\.\d+)( \* l3_mean)",
        "current": 0.03, "optimal": 0.01,
        "desc": "GEN1 top-down generalization ratio",
    },
}


def load_sweep_results():
    """Load sweep results from JSON if available."""
    if os.path.exists(SWEEP_FILE):
        with open(SWEEP_FILE) as f:
            return json.load(f)
    return None


def read_target():
    with open(TARGET) as f:
        return f.read()


def show_params(sweep_data=None):
    print(f"{'Parameter':<25} {'Current':>10} {'Optimal':>10} {'Delta':>10}  Description")
    print("-" * 90)
    for name, info in PARAMS.items():
        cur = info["current"]
        opt = sweep_data.get(name, info["optimal"]) if sweep_data else info["optimal"]
        delta = opt - cur
        sign = "+" if delta > 0 else ""
        print(f"{name:<25} {cur:>10.3f} {opt:>10.3f} {sign + f'{delta:.3f}':>10}  {info['desc']}")


def apply_params(dry_run=True, sweep_data=None):
    source = read_target()
    changes = []
    modified = source
    for name, info in PARAMS.items():
        opt = sweep_data.get(name, info["optimal"]) if sweep_data else info["optimal"]
        match = re.search(info["pattern"], source)
        if not match:
            print(f"  [WARN] Pattern not found for {name}")
            continue
        old_val = match.group(2)
        new_val = f"{opt:g}"
        if old_val == new_val:
            continue
        old_str = match.group(0)
        new_str = match.group(1) + new_val + (match.group(3) if match.lastindex >= 3 else "")
        changes.append((name, old_val, new_val, info["desc"]))
        modified = modified.replace(old_str, new_str, 1)

    if not changes:
        print("No changes needed -- all values already optimal.")
        return

    print(f"{'Parameter':<25} {'Old':>8} {'New':>8}  Description")
    print("-" * 75)
    for name, old, new, desc in changes:
        print(f"{name:<25} {old:>8} {new:>8}  {desc}")

    if dry_run:
        print(f"\n[DRY RUN] {len(changes)} change(s) would be applied to {TARGET}")
    else:
        with open(TARGET, "w") as f:
            f.write(modified)
        print(f"\n[APPLIED] {len(changes)} change(s) written to {TARGET}")


def demo():
    print("=" * 60)
    print("  Param Optimizer -- Sweep Results -> anima_alive.py")
    print("=" * 60)
    sweep_data = load_sweep_results()
    if sweep_data:
        print(f"\nLoaded sweep results from {SWEEP_FILE}")
    else:
        print(f"\nNo sweep file at {SWEEP_FILE}, using built-in optimal values")
    print("\n--- Current vs Optimal ---\n")
    show_params(sweep_data)
    print("\n--- Dry Run ---\n")
    apply_params(dry_run=True, sweep_data=sweep_data)


def main():
    parser = argparse.ArgumentParser(description="Apply param sweep results to anima_alive.py")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--show", action="store_true", help="Display current vs optimal values")
    group.add_argument("--dry-run", action="store_true", help="Show what would change (default)")
    group.add_argument("--apply", action="store_true", help="Actually update anima_alive.py")
    group.add_argument("--demo", action="store_true", help="Run full demo")
    args = parser.parse_args()

    sweep_data = load_sweep_results()
    if args.show:
        show_params(sweep_data)
    elif args.apply:
        apply_params(dry_run=False, sweep_data=sweep_data)
    elif args.demo:
        demo()
    else:
        apply_params(dry_run=True, sweep_data=sweep_data)


if __name__ == "__main__":
    main()
