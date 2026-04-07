#!/usr/bin/env python3
"""Download and convert code instruction datasets from Hugging Face.

Saves to data/instruct/code_extra.jsonl in the standard format:
    {"instruction": ..., "input": ..., "output": ..., "lang": "code"}

Usage:
    python scripts/expand_instruct_code.py                        # CodeFeedback (default)
    python scripts/expand_instruct_code.py --source magicoder     # Magicoder-OSS
    python scripts/expand_instruct_code.py --source both          # both datasets
    python scripts/expand_instruct_code.py --merge                # merge into train.jsonl
    python scripts/expand_instruct_code.py --max-samples 30000    # limit samples
    python scripts/expand_instruct_code.py --dry-run              # show info only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "instruct"

# Dataset configs
SOURCES = {
    "codefeedback": {
        "hf_id": "m-a-p/CodeFeedback-Filtered-Instruction",
        "desc": "~60K code instruction-response pairs",
        "fields": {"instruction": "query", "output": "answer"},
    },
    "magicoder": {
        "hf_id": "ise-uiuc/Magicoder-OSS-Instruct-75K",
        "desc": "~75K code instruction pairs (OSS-based)",
        "fields": {"instruction": "problem", "output": "solution"},
    },
}

FILTERS = {
    "min_inst_len": 10,
    "max_inst_len": 4096,
    "min_out_len": 10,
    "max_out_len": 8192,
}


def download_dataset(source_key: str, max_samples: Optional[int] = None) -> list[dict]:
    """Download from HF and convert to standard format."""
    try:
        from datasets import load_dataset
    except ImportError:
        print("[ERROR] pip install datasets  (required for HF download)")
        sys.exit(1)

    cfg = SOURCES[source_key]
    print(f"\n>> Downloading {cfg['hf_id']} ({cfg['desc']})")
    ds = load_dataset(cfg["hf_id"], split="train")
    print(f"   Raw samples: {len(ds):,}")

    field_map = cfg["fields"]
    rows = []
    skipped = 0
    for item in ds:
        inst = str(item.get(field_map["instruction"], "")).strip()
        out = str(item.get(field_map["output"], "")).strip()

        # Apply filters
        if len(inst) < FILTERS["min_inst_len"] or len(inst) > FILTERS["max_inst_len"]:
            skipped += 1
            continue
        if len(out) < FILTERS["min_out_len"] or len(out) > FILTERS["max_out_len"]:
            skipped += 1
            continue

        rows.append({
            "instruction": inst,
            "input": "",
            "output": out,
            "lang": "code",
        })

        if max_samples and len(rows) >= max_samples:
            break

    print(f"   Converted: {len(rows):,}  (skipped: {skipped:,})")
    return rows


def save_jsonl(rows: list[dict], path: Path):
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"   Saved: {path} ({size_mb:.1f} MB, {len(rows):,} samples)")


def merge_into_train(code_path: Path, train_path: Path):
    """Append code_extra.jsonl into train.jsonl (no dedup, just concat)."""
    if not code_path.exists():
        print(f"[ERROR] {code_path} not found, run without --merge first")
        sys.exit(1)
    if not train_path.exists():
        print(f"[ERROR] {train_path} not found")
        sys.exit(1)

    with open(code_path, "r") as f:
        new_rows = sum(1 for _ in f)

    with open(code_path, "r") as src, open(train_path, "a") as dst:
        for line in src:
            dst.write(line)

    size_mb = train_path.stat().st_size / 1024 / 1024
    print(f"\n>> Merged {new_rows:,} code samples into {train_path.name} ({size_mb:.1f} MB)")
    print("   [NOTE] Run rebalance_instruct.py after merging to fix ratios")


def main():
    parser = argparse.ArgumentParser(description="Expand code instruction data from HF")
    parser.add_argument("--source", choices=["codefeedback", "magicoder", "both"],
                        default="codefeedback")
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--max-samples", type=int, default=None, help="Limit per source")
    parser.add_argument("--output", type=str, default="code_extra.jsonl")
    parser.add_argument("--merge", action="store_true", help="Merge into train.jsonl")
    parser.add_argument("--dry-run", action="store_true", help="Show dataset info only")
    args = parser.parse_args()

    if args.merge:
        merge_into_train(args.data_dir / args.output, args.data_dir / "train.jsonl")
        return

    if args.dry_run:
        print("\n>> Available sources:")
        for key, cfg in SOURCES.items():
            print(f"   {key}: {cfg['hf_id']} — {cfg['desc']}")
        print(f"\n   Filters: {FILTERS}")
        print(f"   Output: {args.data_dir / args.output}")
        return

    sources = list(SOURCES.keys()) if args.source == "both" else [args.source]
    all_rows = []
    for src in sources:
        rows = download_dataset(src, args.max_samples)
        all_rows.extend(rows)

    # Dedup by instruction text
    seen = set()
    deduped = []
    for row in all_rows:
        key = row["instruction"][:200]
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    print(f"\n>> Total: {len(all_rows):,} → deduped: {len(deduped):,}")

    output_path = args.data_dir / args.output
    save_jsonl(deduped, output_path)
    print("\n>> Next steps:")
    print(f"   1. Review: head -5 {output_path}")
    print(f"   2. Merge:  python scripts/expand_instruct_code.py --merge")
    print(f"   3. Rebalance: python scripts/rebalance_instruct.py")


if __name__ == "__main__":
    main()
