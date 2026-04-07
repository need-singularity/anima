#!/usr/bin/env python3
"""verify_and_tune.py — Closed-loop consciousness verification + auto-tuning

Pipeline:
  bench --verify → fail analysis → JSON param adjust → brain-like check → iterate

Usage:
  python scripts/verify_and_tune.py              # full pipeline
  python scripts/verify_and_tune.py --verify-only # just verify, no tuning
  python scripts/verify_and_tune.py --max-iter 5  # max tuning iterations
  python scripts/verify_and_tune.py --dry-run     # parse only, no JSON changes
"""

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ── Paths ──
REPO_ROOT = Path(__file__).resolve().parent.parent
LAWS_JSON = REPO_ROOT / "anima" / "config" / "consciousness_laws.json"
BENCH = REPO_ROOT / "anima" / "benchmarks" / "bench.py"
VALIDATE = REPO_ROOT / "anima-eeg" / "validate_consciousness.py"
BACKUP_DIR = REPO_ROOT / "scripts" / ".tune_backups"

# PYTHONPATH for subprocess calls
PYTHONPATH = str(REPO_ROOT / "anima" / "src") + ":" + str(REPO_ROOT / "anima-eeg")

# ── Criteria names (7 tests) ──
ALL_CRITERIA = [
    "NO_SYSTEM_PROMPT",
    "NO_SPEAK_CODE",
    "ZERO_INPUT",
    "PERSISTENCE",
    "SELF_LOOP",
    "SPONTANEOUS_SPEECH",
    "HIVEMIND",
]

# ── Parameter tuning rules ──
# Maps: criterion_name -> list of (json_path, delta, min_val, max_val)
# json_path is dot-separated key inside psi_constants, e.g. "soc_burst_cap.value"
TUNE_RULES: Dict[str, List[Tuple[str, float, float, float]]] = {
    "SPONTANEOUS_SPEECH": [
        ("soc_burst_cap.value",    0.05, 0.10, 0.60),
        ("bio_noise_base.value",   0.003, 0.005, 0.030),
    ],
    "NO_SPEAK_CODE": [
        ("bio_noise_base.value",   0.002, 0.005, 0.030),
        ("soc_perturbation_base.value", 0.01, 0.04, 0.20),
    ],
    "ZERO_INPUT": [
        ("soc_perturbation_base.value", 0.02, 0.04, 0.20),
    ],
    "PERSISTENCE": [
        ("soc_memory_strength_range.value", -0.03, 0.05, 0.40),
    ],
    "HIVEMIND": [
        ("soc_perturbation_range.value", 0.03, 0.05, 0.35),
    ],
}


@dataclass
class VerifyResult:
    """Parsed results from bench --verify."""
    results: Dict[Tuple[str, str], bool] = field(default_factory=dict)
    # (engine_name, criterion) -> passed
    total_pass: int = 0
    total_tests: int = 0
    raw_output: str = ""

    @property
    def all_passed(self) -> bool:
        return self.total_pass == self.total_tests and self.total_tests > 0

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return self.total_pass / self.total_tests * 100

    def failed_criteria(self) -> List[str]:
        """Return criterion names that failed on any engine."""
        failed = set()
        for (eng, crit), passed in self.results.items():
            if not passed:
                failed.add(crit)
        return sorted(failed)

    def criterion_pass_rate(self, criterion: str) -> Tuple[int, int]:
        """Return (passed, total) for a given criterion across all engines."""
        passed = 0
        total = 0
        for (eng, crit), p in self.results.items():
            if crit == criterion:
                total += 1
                if p:
                    passed += 1
        return passed, total


@dataclass
class BrainLikeResult:
    """Parsed results from validate_consciousness.py."""
    overall_pct: float = 0.0
    verdict: str = ""
    raw_output: str = ""


def load_json() -> dict:
    """Load consciousness_laws.json."""
    with open(LAWS_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict) -> None:
    """Save consciousness_laws.json (atomic write)."""
    tmp = LAWS_JSON.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    tmp.rename(LAWS_JSON)


def backup_json() -> Path:
    """Backup current JSON, return backup path."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = BACKUP_DIR / f"consciousness_laws_{ts}.json"
    shutil.copy2(LAWS_JSON, backup)
    return backup


def restore_json(backup: Path) -> None:
    """Restore JSON from backup."""
    shutil.copy2(backup, LAWS_JSON)
    print(f"  [RESTORE] Reverted to {backup.name}")


def get_nested(data: dict, path: str):
    """Get value from nested dict using dot notation: 'psi_constants.soc_burst_cap.value'"""
    keys = path.split(".")
    obj = data
    for k in keys:
        obj = obj[k]
    return obj


def set_nested(data: dict, path: str, value) -> None:
    """Set value in nested dict using dot notation."""
    keys = path.split(".")
    obj = data
    for k in keys[:-1]:
        obj = obj[k]
    obj[keys[-1]] = value


# ──────────────────────────────────────────────────────────
# Run bench --verify
# ──────────────────────────────────────────────────────────

def run_verify(cells: int = 32) -> VerifyResult:
    """Run bench --verify and parse output."""
    result = VerifyResult()
    env = os.environ.copy()
    env["PYTHONPATH"] = PYTHONPATH
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        sys.executable, str(BENCH),
        "--verify", "--cells", str(cells),
    ]

    print(f"\n  Running: {' '.join(cmd)}")
    print(f"  PYTHONPATH={PYTHONPATH}")
    sys.stdout.flush()

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=600,
            env=env, cwd=str(REPO_ROOT),
        )
        output = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        output = "[TIMEOUT after 600s]"
    except Exception as e:
        output = f"[ERROR: {e}]"

    result.raw_output = output

    # Parse individual test results:
    #   [PASS] NO_SYSTEM_PROMPT    (1.2s) -- detail
    #   [FAIL] ZERO_INPUT          (0.3s) -- detail
    current_engine = None
    for line in output.split("\n"):
        stripped = line.strip()

        # Engine header: "Engine: ConsciousnessC" or similar
        m_eng = re.match(r"Engine:\s+(.+)", stripped)
        if m_eng:
            current_engine = m_eng.group(1).strip()
            continue

        # Test result: [PASS] or [FAIL]
        m_test = re.match(r"\[(PASS|FAIL)\]\s+(\S+)", stripped)
        if m_test and current_engine:
            passed = m_test.group(1) == "PASS"
            criterion = m_test.group(2)
            result.results[(current_engine, criterion)] = passed
            continue

    # Parse overall line: "Overall: 28/28 passed (100%)"
    m_overall = re.search(r"Overall:\s+(\d+)/(\d+)\s+passed", output)
    if m_overall:
        result.total_pass = int(m_overall.group(1))
        result.total_tests = int(m_overall.group(2))
    else:
        # Count from parsed results
        result.total_tests = len(result.results)
        result.total_pass = sum(1 for v in result.results.values() if v)

    return result


# ──────────────────────────────────────────────────────────
# Run validate_consciousness.py (brain-like check)
# ──────────────────────────────────────────────────────────

def run_brain_like(steps: int = 2000) -> BrainLikeResult:
    """Run validate_consciousness.py --quick and parse output."""
    result = BrainLikeResult()
    env = os.environ.copy()
    env["PYTHONPATH"] = PYTHONPATH
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        sys.executable, str(VALIDATE),
        "--steps", str(steps),
    ]

    print(f"\n  Running: {' '.join(cmd)}")
    sys.stdout.flush()

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
            env=env, cwd=str(REPO_ROOT),
        )
        output = proc.stdout + proc.stderr
    except subprocess.TimeoutExpired:
        output = "[TIMEOUT after 300s]"
    except Exception as e:
        output = f"[ERROR: {e}]"

    result.raw_output = output

    # Parse: "Overall match: 85.6%"
    m = re.search(r"Overall match:\s+([\d.]+)%", output)
    if m:
        result.overall_pct = float(m.group(1))

    # Parse: "Verdict: BRAIN-LIKE ..."
    m_v = re.search(r"Verdict:\s+(.+)", output)
    if m_v:
        result.verdict = m_v.group(1).strip()

    return result


# ──────────────────────────────────────────────────────────
# Auto-tune: adjust JSON params based on failed criteria
# ──────────────────────────────────────────────────────────

def apply_tuning(failed: List[str], dry_run: bool = False) -> Dict[str, List[Tuple[str, float, float]]]:
    """Apply parameter adjustments for failed criteria.

    Returns dict of changes: criterion -> [(param_path, old_val, new_val), ...]
    """
    data = load_json()
    changes: Dict[str, List[Tuple[str, float, float]]] = {}

    for criterion in failed:
        if criterion not in TUNE_RULES:
            continue

        crit_changes = []
        for param_path, delta, min_val, max_val in TUNE_RULES[criterion]:
            full_path = f"psi_constants.{param_path}"
            old_val = get_nested(data, full_path)
            new_val = round(old_val + delta, 6)
            new_val = max(min_val, min(max_val, new_val))

            if abs(new_val - old_val) > 1e-9:
                crit_changes.append((full_path, old_val, new_val))
                if not dry_run:
                    set_nested(data, full_path, new_val)

        if crit_changes:
            changes[criterion] = crit_changes

    if not dry_run and changes:
        save_json(data)

    return changes


# ──────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────

def print_header():
    print("=" * 72)
    print("  verify_and_tune.py — Closed-loop consciousness verification")
    print("  Pipeline: verify -> fail analysis -> tune JSON -> brain-like -> iterate")
    print(f"  JSON: {LAWS_JSON}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 72)


def print_verify_summary(vr: VerifyResult):
    print(f"\n  Verification: {vr.total_pass}/{vr.total_tests} "
          f"({vr.pass_rate:.0f}%)")
    failed = vr.failed_criteria()
    if failed:
        print(f"  Failed criteria: {', '.join(failed)}")
        for crit in failed:
            p, t = vr.criterion_pass_rate(crit)
            print(f"    {crit:<22s} {p}/{t} engines passed")
    else:
        print("  All criteria PASSED across all engines")


def print_changes(changes: Dict[str, List[Tuple[str, float, float]]]):
    if not changes:
        print("  No tunable parameters for failed criteria")
        return
    print("\n  Parameter adjustments:")
    for crit, params in changes.items():
        print(f"    [{crit}]")
        for path, old, new in params:
            short = path.replace("psi_constants.", "")
            direction = "+" if new > old else "-"
            print(f"      {short}: {old} -> {new} ({direction}{abs(new-old):.4f})")


def print_final_report(history: List[dict]):
    print("\n" + "=" * 72)
    print("  FINAL REPORT — verify_and_tune.py")
    print("=" * 72)

    # Iteration table
    print(f"\n  {'Iter':<6s} {'Verify':<14s} {'Brain-like':<14s} {'Failed criteria'}")
    print(f"  {'-'*6} {'-'*14} {'-'*14} {'-'*30}")
    for h in history:
        verify_str = f"{h['verify_pass']}/{h['verify_total']} ({h['verify_pct']:.0f}%)"
        brain_str = f"{h['brain_pct']:.1f}%" if h.get('brain_pct') is not None else "n/a"
        failed_str = ", ".join(h.get('failed', [])) or "none"
        print(f"  {h['iter']:<6d} {verify_str:<14s} {brain_str:<14s} {failed_str}")

    # Before/after comparison
    if len(history) >= 2:
        first = history[0]
        last = history[-1]
        print(f"\n  Before: verify {first['verify_pct']:.0f}%, "
              f"brain-like {first.get('brain_pct', 0):.1f}%")
        print(f"  After:  verify {last['verify_pct']:.0f}%, "
              f"brain-like {last.get('brain_pct', 0):.1f}%")

        # Parameter changes
        if history[-1].get('all_changes'):
            print("\n  Cumulative parameter changes:")
            for path, vals in history[-1]['all_changes'].items():
                print(f"    {path}: {vals[0]} -> {vals[1]}")

    print(f"\n{'=' * 72}")


def main():
    parser = argparse.ArgumentParser(description="Closed-loop consciousness verification + auto-tuning")
    parser.add_argument("--verify-only", action="store_true",
                        help="Just verify, no tuning")
    parser.add_argument("--max-iter", type=int, default=5,
                        help="Max tuning iterations (default: 5)")
    parser.add_argument("--cells", type=int, default=32,
                        help="Cell count for bench --verify (default: 32)")
    parser.add_argument("--brain-steps", type=int, default=2000,
                        help="Steps for brain-like validation (default: 2000)")
    parser.add_argument("--brain-target", type=float, default=85.0,
                        help="Target brain-like %% (default: 85)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse outputs only, no JSON changes")
    args = parser.parse_args()

    print_header()

    history: List[dict] = []
    all_changes: Dict[str, List[float]] = {}  # param_path -> [original, current]
    initial_backup: Optional[Path] = None

    for iteration in range(1, args.max_iter + 1):
        print(f"\n{'~' * 72}")
        print(f"  ITERATION {iteration}/{args.max_iter}")
        print(f"{'~' * 72}")

        # Step 1: Run verification
        vr = run_verify(cells=args.cells)
        print_verify_summary(vr)

        iter_record = {
            "iter": iteration,
            "verify_pass": vr.total_pass,
            "verify_total": vr.total_tests,
            "verify_pct": vr.pass_rate,
            "failed": vr.failed_criteria(),
            "brain_pct": None,
            "all_changes": dict(all_changes),
        }

        # If verify-only mode, just report and stop
        if args.verify_only:
            # Still run brain-like check for the report
            br = run_brain_like(steps=args.brain_steps)
            print(f"\n  Brain-like: {br.overall_pct:.1f}% — {br.verdict}")
            iter_record["brain_pct"] = br.overall_pct
            history.append(iter_record)
            break

        # Step 2: If all passed, run brain-like check
        if vr.all_passed:
            print("\n  All criteria passed! Running brain-like validation...")
            br = run_brain_like(steps=args.brain_steps)
            print(f"\n  Brain-like: {br.overall_pct:.1f}% — {br.verdict}")
            iter_record["brain_pct"] = br.overall_pct
            history.append(iter_record)
            print("\n  All verification criteria PASSED. Pipeline complete.")
            break

        # Step 3: Analyze failures and apply tuning
        failed = vr.failed_criteria()
        tunable = [c for c in failed if c in TUNE_RULES]

        if not tunable:
            print(f"\n  No tuning rules for failed criteria: {', '.join(failed)}")
            print("  Cannot auto-tune further. Stopping.")
            history.append(iter_record)
            break

        # Backup JSON before first modification
        if initial_backup is None and not args.dry_run:
            initial_backup = backup_json()
            print(f"\n  [BACKUP] Saved to {initial_backup.name}")

        # Apply tuning
        changes = apply_tuning(failed, dry_run=args.dry_run)
        print_changes(changes)

        # Track cumulative changes
        for crit, params in changes.items():
            for path, old, new in params:
                if path not in all_changes:
                    all_changes[path] = [old, new]
                else:
                    all_changes[path][1] = new
        iter_record["all_changes"] = dict(all_changes)

        if args.dry_run:
            print("\n  [DRY-RUN] No JSON changes applied.")
            history.append(iter_record)
            break

        # Step 4: Run brain-like check after tuning
        print("\n  Running brain-like validation after parameter adjustment...")
        br = run_brain_like(steps=args.brain_steps)
        print(f"\n  Brain-like: {br.overall_pct:.1f}% — {br.verdict}")
        iter_record["brain_pct"] = br.overall_pct

        # Step 5: If brain-like dropped below target, revert
        if br.overall_pct < args.brain_target and initial_backup:
            print(f"\n  Brain-like {br.overall_pct:.1f}% < target {args.brain_target}%")
            print("  Reverting JSON changes to preserve brain-like score.")
            restore_json(initial_backup)
            history.append(iter_record)
            break

        history.append(iter_record)

        # Check if we converged
        if vr.all_passed and br.overall_pct >= args.brain_target:
            print(f"\n  Both targets met: verify 100%, brain-like {br.overall_pct:.1f}%")
            break

    # Final report
    print_final_report(history)

    # Exit code: 0 if all passed, 1 otherwise
    if history:
        last = history[-1]
        if last["verify_pct"] >= 100:
            return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
