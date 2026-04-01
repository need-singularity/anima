#!/usr/bin/env python3
"""Instruct data rebalancing: adjust en/ko/code ratios via down/up-sampling.

Usage:
    python scripts/rebalance_instruct.py                          # default 40/40/20
    python scripts/rebalance_instruct.py --en 0.3 --ko 0.5 --code 0.2
    python scripts/rebalance_instruct.py --dry-run                # stats only
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "instruct"


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def save_jsonl(rows: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def group_by_lang(rows: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        lang = row.get("lang", "unknown")
        groups[lang].append(row)
    return dict(groups)


def resample(groups: dict[str, list[dict]], targets: dict[str, int], seed: int) -> list[dict]:
    """Resample each lang group to target count. Upsample by repeating."""
    rng = random.Random(seed)
    result = []
    for lang, target_n in targets.items():
        pool = groups.get(lang, [])
        if not pool:
            print(f"  [WARN] no samples for lang={lang}, skipping")
            continue
        if target_n <= len(pool):
            # downsample
            result.extend(rng.sample(pool, target_n))
        else:
            # upsample: full copies + remainder
            full_copies = target_n // len(pool)
            remainder = target_n % len(pool)
            for _ in range(full_copies):
                result.extend(pool)
            result.extend(rng.sample(pool, remainder))
    rng.shuffle(result)
    return result


def compute_targets(groups: dict[str, list[dict]], ratios: dict[str, float]) -> dict[str, int]:
    """Compute target counts. Total = max(current_total, sum needed to fill all ratios)."""
    current_total = sum(len(v) for v in groups.values())
    # Find the lang that requires the most scaling
    # total * ratio[lang] = target[lang], and target[lang] >= current[lang] for upsampled langs
    # We want total such that no lang needs more than what ratio allows
    # Use: total = max over langs of (current[lang] / ratio[lang]) for langs that need upsampling
    candidates = []
    for lang, ratio in ratios.items():
        n = len(groups.get(lang, []))
        if ratio > 0:
            candidates.append(n / ratio)
    total = int(max(candidates)) if candidates else current_total
    targets = {}
    for lang, ratio in ratios.items():
        targets[lang] = int(total * ratio)
    return targets


def print_stats(label: str, groups: dict[str, list[dict]]):
    total = sum(len(v) for v in groups.values())
    print(f"\n{'='*50}")
    print(f"  {label}")
    print(f"{'='*50}")
    print(f"  {'Lang':<10} {'Count':>10} {'Ratio':>10}")
    print(f"  {'-'*30}")
    for lang in sorted(groups.keys()):
        n = len(groups[lang])
        pct = n / total * 100 if total > 0 else 0
        print(f"  {lang:<10} {n:>10,} {pct:>9.1f}%")
    print(f"  {'-'*30}")
    print(f"  {'TOTAL':<10} {total:>10,}")


def process_file(input_path: Path, output_path: Path, ratios: dict[str, float],
                 seed: int, dry_run: bool):
    if not input_path.exists():
        print(f"  [SKIP] {input_path.name} not found")
        return

    print(f"\n>> Processing {input_path.name}")
    rows = load_jsonl(input_path)
    groups = group_by_lang(rows)
    print_stats("BEFORE", groups)

    targets = compute_targets(groups, ratios)
    print(f"\n  Targets: {', '.join(f'{k}={v:,}' for k, v in targets.items())}")

    if dry_run:
        print("  [DRY RUN] skipping write")
        return

    balanced = resample(groups, targets, seed)
    balanced_groups = group_by_lang(balanced)
    print_stats("AFTER", balanced_groups)

    save_jsonl(balanced, output_path)
    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"\n  Saved: {output_path} ({size_mb:.1f} MB, {len(balanced):,} samples)")


def main():
    parser = argparse.ArgumentParser(description="Rebalance instruct data by language")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--en", type=float, default=0.4, help="English ratio (default 0.4)")
    parser.add_argument("--ko", type=float, default=0.4, help="Korean ratio (default 0.4)")
    parser.add_argument("--code", type=float, default=0.2, help="Code ratio (default 0.2)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true", help="Show stats without writing")
    parser.add_argument("--suffix", default="_balanced", help="Output file suffix")
    args = parser.parse_args()

    ratios = {"en": args.en, "ko": args.ko, "code": args.code}
    ratio_sum = sum(ratios.values())
    if abs(ratio_sum - 1.0) > 0.01:
        print(f"[ERROR] Ratios must sum to 1.0, got {ratio_sum:.2f}")
        sys.exit(1)

    print(f"Target ratios: en={args.en:.0%} ko={args.ko:.0%} code={args.code:.0%}")
    print(f"Seed: {args.seed}")

    for name in ["train", "val"]:
        input_path = args.data_dir / f"{name}.jsonl"
        output_path = args.data_dir / f"{name}{args.suffix}.jsonl"
        process_file(input_path, output_path, ratios, args.seed, args.dry_run)

    if not args.dry_run:
        print("\n>> Done. Balanced files saved with suffix '{}'".format(args.suffix))


if __name__ == "__main__":
    main()
