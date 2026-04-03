#!/usr/bin/env python3
"""accel_batch_runner.py — Batch evaluation pipeline for acceleration hypotheses.

Evaluates 304 brainstorm-stage hypotheses by:
1. Mapping each to an Intervention (via accel_intervention_map)
2. Running the engine N times with the intervention
3. Measuring Phi retention vs. baseline
4. Auto-promoting stage in acceleration_hypotheses.json

Verdict logic:
  CV > 50%        → REJECTED (not reproducible)
  retention < 90% → REJECTED (Phi loss too high)
  retention ≥ 95% → APPLIED (excellent)
  90–95%          → VERIFIED (acceptable)
  no template     → UNMAPPABLE (stays brainstorm)

Usage:
    python accel_batch_runner.py                      # full pipeline
    python accel_batch_runner.py --batch 0            # batch 0 (first 50)
    python accel_batch_runner.py --series I           # I series only
    python accel_batch_runner.py --dry-run            # mapping check only
    python accel_batch_runner.py --id I1,I2           # specific IDs
    python accel_batch_runner.py --report             # status report
    python accel_batch_runner.py --cells 32 --steps 100 --repeats 3
"""

import sys
import os
import json
import copy
import time
import argparse
import math
from typing import Dict, List, Optional, Tuple

# ── path setup ──────────────────────────────────────────────────────────────
_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import torch
import numpy as np

from consciousness_engine import ConsciousnessEngine
from accel_intervention_map import (
    map_hypothesis_to_intervention,
    INTERVENTION_TEMPLATES,
    Intervention,
)

# ── JSON path ────────────────────────────────────────────────────────────────
_DEFAULT_JSON = os.path.join(
    os.path.dirname(_SRC), "config", "acceleration_hypotheses.json"
)

# ── Batch size ───────────────────────────────────────────────────────────────
BATCH_SIZE = 50


# ══════════════════════════════════════════════════════════════════════════════
# Phi measurement (fast proxy — avoids engine's heavy _measure_phi_iit)
# ══════════════════════════════════════════════════════════════════════════════

def _measure_phi_fast(engine: ConsciousnessEngine) -> float:
    """Fast Phi proxy: pairwise MI between cell hidden states."""
    if engine.n_cells < 2:
        return 0.0
    hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
    n = hiddens.shape[0]

    # Sample pairs (limit for speed)
    pairs = set()
    for i in range(n):
        pairs.add((i, (i + 1) % n))
    for _ in range(min(6, n * (n - 1) // 2)):
        i, j = np.random.randint(0, n, size=2)
        if i != j:
            pairs.add((min(i, j), max(i, j)))

    total_mi = 0.0
    for i, j in pairs:
        x, y = hiddens[i], hiddens[j]
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            continue
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        hist, _, _ = np.histogram2d(xn, yn, bins=8, range=[[0, 1], [0, 1]])
        hist = hist / (hist.sum() + 1e-8)
        px, py = hist.sum(1), hist.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(hist * np.log2(hist + 1e-10))
        total_mi += max(0.0, hx + hy - hxy)

    return total_mi / max(len(pairs), 1)


# ══════════════════════════════════════════════════════════════════════════════
# Baseline measurement
# ══════════════════════════════════════════════════════════════════════════════

def measure_baseline(
    n_cells: int = 16,
    n_steps: int = 50,
    seed: int = 42,
) -> Dict:
    """Run engine without intervention, return phi stats.

    Returns:
        dict with: mean_phi, std_phi, min_phi, max_phi, phi_history
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    engine = ConsciousnessEngine(
        cell_dim=32, hidden_dim=64, initial_cells=n_cells,
        max_cells=n_cells, n_factions=min(12, n_cells)
    )
    phi_history = []
    for step in range(n_steps):
        engine.step()
        phi = _measure_phi_fast(engine)
        phi_history.append(phi)

    phi_arr = np.array(phi_history)
    result = {
        "mean_phi": float(phi_arr.mean()),
        "std_phi": float(phi_arr.std()),
        "min_phi": float(phi_arr.min()),
        "max_phi": float(phi_arr.max()),
        "phi_history": phi_history,
    }
    return result


# ══════════════════════════════════════════════════════════════════════════════
# Single hypothesis evaluation
# ══════════════════════════════════════════════════════════════════════════════

def evaluate_hypothesis(
    hyp: Dict,
    n_cells: int = 16,
    n_steps: int = 50,
    n_repeats: int = 3,
    baseline: Optional[Dict] = None,
) -> Dict:
    """Map hypothesis to intervention, run n_repeats times, measure phi retention.

    Returns:
        dict with: id, name, verdict, avg_retention, cv, phi_runs, mapped_template, elapsed_sec
    """
    t0 = time.time()
    hyp_id = hyp.get("id", "?")
    hyp_name = hyp.get("name", "?")

    # 1. Map to intervention
    intervention = map_hypothesis_to_intervention(hyp)

    if intervention is None:
        return {
            "id": hyp_id,
            "name": hyp_name,
            "verdict": "UNMAPPABLE",
            "avg_retention": None,
            "cv": None,
            "phi_runs": [],
            "mapped_template": None,
            "elapsed_sec": time.time() - t0,
        }

    # 2. Compute baseline if not provided
    if baseline is None:
        baseline = measure_baseline(n_cells=n_cells, n_steps=n_steps, seed=42)
    baseline_mean = baseline["mean_phi"]

    # 3. Run n_repeats evaluations
    phi_means = []
    for repeat in range(n_repeats):
        torch.manual_seed(42 + repeat)
        np.random.seed(42 + repeat)

        engine = ConsciousnessEngine(
            cell_dim=32, hidden_dim=64, initial_cells=n_cells,
            max_cells=n_cells, n_factions=min(12, n_cells)
        )
        phi_history = []
        for step in range(n_steps):
            try:
                intervention.apply(engine, step)
            except Exception:
                pass  # intervention failure → continue without it
            engine.step()
            phi = _measure_phi_fast(engine)
            phi_history.append(phi)

        phi_means.append(float(np.mean(phi_history)))

    # 4. Compute retention and CV
    phi_arr = np.array(phi_means)
    avg_phi = float(phi_arr.mean())
    std_phi = float(phi_arr.std())

    if baseline_mean > 1e-8:
        avg_retention = avg_phi / baseline_mean * 100.0
    else:
        avg_retention = 100.0  # baseline is zero → can't compare

    cv = (std_phi / (avg_phi + 1e-8)) * 100.0  # coefficient of variation (%)

    # 5. Verdict logic
    if cv > 50.0:
        verdict = "REJECTED"
        reason = f"CV={cv:.1f}% > 50% (not reproducible)"
    elif avg_retention < 90.0:
        verdict = "REJECTED"
        reason = f"retention={avg_retention:.1f}% < 90%"
    elif avg_retention >= 95.0:
        verdict = "APPLIED"
        reason = f"retention={avg_retention:.1f}% >= 95% (excellent)"
    else:
        verdict = "VERIFIED"
        reason = f"retention={avg_retention:.1f}% in [90%, 95%)"

    return {
        "id": hyp_id,
        "name": hyp_name,
        "verdict": verdict,
        "reason": reason,
        "avg_retention": avg_retention,
        "avg_phi": avg_phi,
        "baseline_phi": baseline_mean,
        "cv": cv,
        "phi_runs": phi_means,
        "mapped_template": intervention.name,
        "elapsed_sec": time.time() - t0,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Batch evaluation
# ══════════════════════════════════════════════════════════════════════════════

def batch_evaluate(
    hypotheses: List[Dict],
    n_cells: int = 16,
    n_steps: int = 50,
    n_repeats: int = 3,
    baseline: Optional[Dict] = None,
) -> List[Dict]:
    """Evaluate a list of hypotheses, printing progress.

    Returns list of result dicts.
    """
    if baseline is None:
        print(f"[batch_evaluate] Computing baseline ({n_cells}c, {n_steps}s)...")
        sys.stdout.flush()
        baseline = measure_baseline(n_cells=n_cells, n_steps=n_steps, seed=42)
        print(f"[batch_evaluate] Baseline phi={baseline['mean_phi']:.4f}")
        sys.stdout.flush()

    results = []
    total = len(hypotheses)
    for idx, hyp in enumerate(hypotheses):
        result = evaluate_hypothesis(
            hyp, n_cells=n_cells, n_steps=n_steps,
            n_repeats=n_repeats, baseline=baseline
        )
        results.append(result)
        verdict = result["verdict"]
        template = result.get("mapped_template") or "NONE"
        ret = result.get("avg_retention")
        ret_str = f"{ret:.1f}%" if ret is not None else "N/A"
        elapsed = result.get("elapsed_sec", 0)
        print(
            f"  [{idx+1}/{total}] {result['id']:8s} | {verdict:10s} | "
            f"ret={ret_str:7s} | tpl={template:22s} | {elapsed:.1f}s"
        )
        sys.stdout.flush()

    return results


# ══════════════════════════════════════════════════════════════════════════════
# JSON update
# ══════════════════════════════════════════════════════════════════════════════

def update_json(
    hyp_id: str,
    result: Dict,
    json_path: str = _DEFAULT_JSON,
) -> None:
    """Update a single hypothesis in the JSON file with evaluation results.

    Promotes stage from 'brainstorm' to verdict-based stage.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    hyps = data["hypotheses"]
    if hyp_id not in hyps:
        return

    hyp = hyps[hyp_id]
    verdict = result["verdict"]

    # Update stage
    if verdict == "APPLIED":
        hyp["stage"] = "applied"
    elif verdict == "VERIFIED":
        hyp["stage"] = "verified"
    elif verdict == "REJECTED":
        hyp["stage"] = "rejected"
    elif verdict == "UNMAPPABLE":
        hyp["stage"] = "brainstorm"  # stays brainstorm
    else:
        hyp["stage"] = "brainstorm"

    # Update verdict field
    if verdict != "UNMAPPABLE":
        hyp["verdict"] = result.get("reason", verdict)

    # Update metrics
    if hyp.get("metrics") is None:
        hyp["metrics"] = {}
    if result.get("avg_retention") is not None:
        hyp["metrics"]["phi_retention"] = f"{result['avg_retention']:.1f}%"
    if result.get("avg_phi") is not None:
        hyp["metrics"]["avg_phi"] = round(result["avg_phi"], 4)
    if result.get("cv") is not None:
        hyp["metrics"]["cv_pct"] = round(result["cv"], 1)
    if result.get("mapped_template"):
        hyp["metrics"]["intervention"] = result["mapped_template"]

    # Update _meta total counts if present
    if "_meta" in data:
        meta = data["_meta"]
        # Recount
        stages = {}
        for h in hyps.values():
            s = h.get("stage", "brainstorm")
            stages[s] = stages.get(s, 0) + 1
        meta["total_hypotheses"] = len(hyps)
        for k, v in stages.items():
            meta[f"total_{k}"] = v

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# Load helpers
# ══════════════════════════════════════════════════════════════════════════════

def load_brainstorm_hypotheses(
    json_path: str = _DEFAULT_JSON,
    series: Optional[str] = None,
    ids: Optional[List[str]] = None,
) -> List[Dict]:
    """Load brainstorm-stage hypotheses, optionally filtered by series or IDs."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    hyps = data["hypotheses"]
    result = []

    for k, h in hyps.items():
        if h.get("stage") != "brainstorm":
            continue
        if ids is not None and k not in ids:
            continue
        if series is not None and h.get("series") != series:
            continue
        result.append(h)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# Report
# ══════════════════════════════════════════════════════════════════════════════

def print_report(json_path: str = _DEFAULT_JSON) -> None:
    """Print current status report from acceleration_hypotheses.json."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    hyps = data["hypotheses"]
    from collections import Counter
    stage_counts = Counter(h.get("stage", "?") for h in hyps.values())
    total = len(hyps)

    print("=" * 60)
    print("  Acceleration Hypotheses — Status Report")
    print("=" * 60)
    sys.stdout.flush()
    print(f"  Total:       {total}")
    for stage, count in sorted(stage_counts.items()):
        pct = count / total * 100
        bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
        print(f"  {stage:12s} {bar} {count:4d} ({pct:.1f}%)")
        sys.stdout.flush()
    print("=" * 60)
    sys.stdout.flush()

    # List applied hypotheses
    applied = [(k, h) for k, h in hyps.items() if h.get("stage") == "applied"]
    if applied:
        print(f"\n  Applied ({len(applied)}):")
        for k, h in applied[:10]:
            print(f"    {k}: {h.get('name','?')[:50]}")
            sys.stdout.flush()
        if len(applied) > 10:
            print(f"    ... and {len(applied) - 10} more")
            sys.stdout.flush()

    # List rejected hypotheses
    rejected = [(k, h) for k, h in hyps.items() if h.get("stage") == "rejected"]
    if rejected:
        print(f"\n  Rejected ({len(rejected)}):")
        for k, h in rejected[:5]:
            print(f"    {k}: {h.get('name','?')[:50]}")
            sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
# Main pipeline orchestrator
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(
    batch_idx: Optional[int] = None,
    series: Optional[str] = None,
    ids: Optional[List[str]] = None,
    dry_run: bool = False,
    n_cells: int = 16,
    n_steps: int = 50,
    n_repeats: int = 3,
    json_path: str = _DEFAULT_JSON,
) -> None:
    """Main orchestrator for the acceleration hypothesis pipeline.

    Args:
        batch_idx: If set, run only batch N (each batch = BATCH_SIZE hypotheses)
        series:    If set, run only this series (e.g., 'I', 'H')
        ids:       If set, run only these IDs (e.g., ['I1', 'I2'])
        dry_run:   Only check mapping — don't run engine
        n_cells:   Number of cells for evaluation
        n_steps:   Steps per run
        n_repeats: Cross-validation repeats
        json_path: Path to acceleration_hypotheses.json
    """
    print(f"\n{'='*60}")
    print(f"  Acceleration Pipeline")
    print(f"  cells={n_cells}, steps={n_steps}, repeats={n_repeats}")
    if dry_run:
        print("  MODE: DRY RUN (mapping check only)")
    print(f"{'='*60}\n")
    sys.stdout.flush()

    # Load hypotheses
    all_brainstorm = load_brainstorm_hypotheses(json_path=json_path, series=series, ids=ids)
    print(f"[pipeline] Loaded {len(all_brainstorm)} brainstorm hypotheses")
    sys.stdout.flush()

    if not all_brainstorm:
        print("[pipeline] No brainstorm hypotheses to process.")
        sys.stdout.flush()
        return

    # Apply batch slicing
    if batch_idx is not None:
        start = batch_idx * BATCH_SIZE
        end = start + BATCH_SIZE
        all_brainstorm = all_brainstorm[start:end]
        print(f"[pipeline] Batch {batch_idx}: items {start}–{min(end, len(all_brainstorm)+start)}")
        sys.stdout.flush()

    # Dry-run mode: just report mapping
    if dry_run:
        print("\n[dry-run] Mapping check:")
        print(f"  {'ID':8s} | {'Template':25s} | {'Category':30s} | Name")
        print(f"  {'-'*8} | {'-'*25} | {'-'*30} | {'-'*30}")
        sys.stdout.flush()

        mapped = 0
        unmapped = 0
        for hyp in all_brainstorm:
            iv = map_hypothesis_to_intervention(hyp)
            template = iv.name if iv else "UNMAPPABLE"
            cat = (hyp.get("category") or "")[:30]
            name = hyp.get("name", "")[:30]
            print(f"  {hyp['id']:8s} | {template:25s} | {cat:30s} | {name}")
            sys.stdout.flush()
            if iv:
                mapped += 1
            else:
                unmapped += 1

        print(f"\n[dry-run] Mapped: {mapped}, Unmapped: {unmapped}")
        sys.stdout.flush()
        return

    # Compute baseline once
    print("[pipeline] Computing baseline...")
    sys.stdout.flush()
    baseline = measure_baseline(n_cells=n_cells, n_steps=n_steps, seed=42)
    print(f"[pipeline] Baseline phi={baseline['mean_phi']:.4f} (std={baseline['std_phi']:.4f})")
    sys.stdout.flush()

    # Counters
    verdict_counts = {"APPLIED": 0, "VERIFIED": 0, "REJECTED": 0, "UNMAPPABLE": 0}
    t_start = time.time()

    print(f"\n[pipeline] Evaluating {len(all_brainstorm)} hypotheses...\n")
    sys.stdout.flush()

    for idx, hyp in enumerate(all_brainstorm):
        result = evaluate_hypothesis(
            hyp, n_cells=n_cells, n_steps=n_steps,
            n_repeats=n_repeats, baseline=baseline
        )
        verdict = result["verdict"]
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        template = result.get("mapped_template") or "NONE"
        ret = result.get("avg_retention")
        ret_str = f"{ret:.1f}%" if ret is not None else "N/A"
        elapsed = result.get("elapsed_sec", 0)

        print(
            f"  [{idx+1}/{len(all_brainstorm)}] {result['id']:8s} | {verdict:10s} | "
            f"ret={ret_str:7s} | tpl={template:22s} | {elapsed:.1f}s"
        )
        sys.stdout.flush()

        # Update JSON in-place
        update_json(result["id"], result, json_path=json_path)

    total_elapsed = time.time() - t_start

    # Summary
    print(f"\n{'='*60}")
    print(f"  Pipeline complete — {len(all_brainstorm)} evaluated in {total_elapsed:.1f}s")
    print(f"  APPLIED:    {verdict_counts.get('APPLIED', 0)}")
    print(f"  VERIFIED:   {verdict_counts.get('VERIFIED', 0)}")
    print(f"  REJECTED:   {verdict_counts.get('REJECTED', 0)}")
    print(f"  UNMAPPABLE: {verdict_counts.get('UNMAPPABLE', 0)}")
    print(f"{'='*60}\n")
    sys.stdout.flush()


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Acceleration hypothesis batch runner"
    )
    parser.add_argument("--batch", type=int, default=None,
                        help=f"Run only batch N (each batch = {BATCH_SIZE} items)")
    parser.add_argument("--series", type=str, default=None,
                        help="Run only this series (e.g., I, H, F)")
    parser.add_argument("--id", type=str, default=None,
                        help="Comma-separated hypothesis IDs (e.g., I1,I2,I3)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Check mapping only, don't run engine")
    parser.add_argument("--report", action="store_true",
                        help="Print status report and exit")
    parser.add_argument("--cells", type=int, default=16,
                        help="Number of cells for evaluation (default: 16)")
    parser.add_argument("--steps", type=int, default=50,
                        help="Steps per run (default: 50)")
    parser.add_argument("--repeats", type=int, default=3,
                        help="Cross-validation repeats (default: 3)")
    parser.add_argument("--json", type=str, default=_DEFAULT_JSON,
                        help="Path to acceleration_hypotheses.json")

    args = parser.parse_args()

    if args.report:
        print_report(json_path=args.json)
        return

    ids_list = [x.strip() for x in args.id.split(",")] if args.id else None

    run_pipeline(
        batch_idx=args.batch,
        series=args.series,
        ids=ids_list,
        dry_run=args.dry_run,
        n_cells=args.cells,
        n_steps=args.steps,
        n_repeats=args.repeats,
        json_path=args.json,
    )


if __name__ == "__main__":
    main()
