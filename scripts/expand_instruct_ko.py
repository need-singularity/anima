#!/usr/bin/env python3
"""expand_instruct_ko.py — Download additional Korean instruct datasets and append to existing data.

Downloads Korean instruction datasets from HuggingFace, deduplicates against
existing data, and appends new samples to train.jsonl / val.jsonl.

Output format (same as existing):
  {"instruction": "...", "input": "...", "output": "...", "lang": "ko"}

Usage:
  python scripts/expand_instruct_ko.py                    # Download all, append
  python scripts/expand_instruct_ko.py --dry-run           # Preview without downloading
  python scripts/expand_instruct_ko.py --target 100000     # Target total Korean samples
  python scripts/expand_instruct_ko.py --status             # Show current Korean stats

Requires: pip install datasets tqdm
"""

import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        desc = kwargs.get("desc", "")
        total = kwargs.get("total", None)
        for i, item in enumerate(iterable):
            if i % 5000 == 0:
                progress = f" ({i}/{total})" if total else f" ({i})"
                print(f"\r  {desc}{progress}", end="", flush=True)
            yield item
        print()

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "anima" / "data" / "instruct"

# ═══════════════════════════════════════════════════════════════════
# Additional Korean Datasets
# ═══════════════════════════════════════════════════════════════════

KO_DATASETS = [
    {
        "name": "nlpai-lab/kullm-v2",
        "split": "train",
        "streaming": False,
        "field_map": {"instruction": "instruction", "input": "input", "output": "output"},
        "description": "KULLM v2 Korean instructions (~150K)",
        "estimated_size": 150_000,
    },
    {
        "name": "heegyu/ko-chatgpt-dataset",
        "split": "train",
        "streaming": False,
        # This dataset may have different field names — we try multiple mappings
        "field_map": {"instruction": "prompt", "input": "", "output": "completion"},
        "alt_field_maps": [
            {"instruction": "instruction", "input": "input", "output": "output"},
            {"instruction": "question", "input": "", "output": "answer"},
            {"instruction": "prompt", "input": "", "output": "response"},
            {"instruction": "text", "input": "", "output": ""},
        ],
        "description": "Korean ChatGPT dataset (~10K)",
        "estimated_size": 10_000,
    },
    {
        "name": "changpt/ko-lima-vicuna",
        "split": "train",
        "streaming": False,
        "field_map": {"instruction": "instruction", "input": "input", "output": "output"},
        "alt_field_maps": [
            {"instruction": "question", "input": "", "output": "answer"},
            {"instruction": "prompt", "input": "", "output": "response"},
            {"instruction": "conversations", "input": "", "output": ""},
        ],
        "description": "Korean LIMA + Vicuna (~10K)",
        "estimated_size": 10_000,
    },
    {
        "name": "kyujinpy/ko-platypus-v3",
        "split": "train",
        "streaming": False,
        "field_map": {"instruction": "instruction", "input": "input", "output": "output"},
        "alt_field_maps": [
            {"instruction": "question", "input": "", "output": "answer"},
        ],
        "description": "Korean Platypus v3 (~25K)",
        "estimated_size": 25_000,
    },
    {
        "name": "FreedomIntelligence/evol-instruct-korean",
        "split": "train",
        "streaming": False,
        "field_map": {"instruction": "instruction", "input": "input", "output": "output"},
        "alt_field_maps": [
            {"instruction": "question", "input": "", "output": "answer"},
            {"instruction": "prompt", "input": "", "output": "response"},
        ],
        "description": "Korean EvolInstruct (~70K)",
        "estimated_size": 70_000,
    },
    {
        "name": "dbdu/ShareGPT-74k-ko",
        "split": "train",
        "streaming": False,
        "field_map": {"instruction": "conversations", "input": "", "output": ""},
        "is_conversation": True,
        "description": "Korean ShareGPT 74K conversations",
        "estimated_size": 74_000,
    },
]


# ═══════════════════════════════════════════════════════════════════
# Quality Filters (same as prepare_instruct_data.py)
# ═══════════════════════════════════════════════════════════════════

MIN_INSTRUCTION_LEN = 10
MAX_INSTRUCTION_LEN = 4096
MIN_OUTPUT_LEN = 10
MAX_OUTPUT_LEN = 8192


def quality_filter(sample: dict) -> bool:
    """Return True if sample passes quality checks."""
    inst = sample.get("instruction", "")
    output = sample.get("output", "")
    if len(inst) < MIN_INSTRUCTION_LEN or len(inst) > MAX_INSTRUCTION_LEN:
        return False
    if len(output) < MIN_OUTPUT_LEN or len(output) > MAX_OUTPUT_LEN:
        return False
    if not inst.strip() or not output.strip():
        return False
    if len(set(inst.strip())) < 3:
        return False
    return True


def dedup_hash(text: str) -> str:
    """Return hash for deduplication (same as prepare_instruct_data.py)."""
    normalized = text.strip().lower()[:200]
    return hashlib.md5(normalized.encode("utf-8", errors="ignore")).hexdigest()


# ═══════════════════════════════════════════════════════════════════
# Dataset Loaders
# ═══════════════════════════════════════════════════════════════════

def _convert_sample(item: dict, field_map: dict) -> dict:
    """Convert a HuggingFace dataset row to unified format."""
    try:
        inst_field = field_map.get("instruction", "instruction")
        input_field = field_map.get("input", "")
        output_field = field_map.get("output", "output")

        instruction = str(item.get(inst_field, "")).strip() if inst_field else ""
        inp = str(item.get(input_field, "")).strip() if input_field else ""
        output = str(item.get(output_field, "")).strip() if output_field else ""

        if not instruction and not output:
            return None

        return {
            "instruction": instruction,
            "input": inp,
            "output": output,
            "lang": "ko",
        }
    except Exception:
        return None


def _convert_conversation(item: dict) -> list:
    """Convert a multi-turn conversation dataset row to instruction/output pairs."""
    results = []
    convs = item.get("conversations", item.get("conversation", []))

    if isinstance(convs, str):
        # Try JSON parse
        try:
            convs = json.loads(convs)
        except (json.JSONDecodeError, TypeError):
            return results

    if not isinstance(convs, list):
        return results

    # Extract human/assistant pairs
    for i in range(len(convs) - 1):
        turn = convs[i]
        next_turn = convs[i + 1]

        # Get role and content
        if isinstance(turn, dict):
            role = turn.get("role", turn.get("from", "")).lower()
            content = turn.get("content", turn.get("value", ""))
        else:
            continue

        if isinstance(next_turn, dict):
            next_role = next_turn.get("role", next_turn.get("from", "")).lower()
            next_content = next_turn.get("content", next_turn.get("value", ""))
        else:
            continue

        if role in ("human", "user") and next_role in ("assistant", "gpt", "bot"):
            sample = {
                "instruction": str(content).strip(),
                "input": "",
                "output": str(next_content).strip(),
                "lang": "ko",
            }
            if quality_filter(sample):
                results.append(sample)

    return results


def load_ko_dataset(config: dict, seen_hashes: set, max_samples: int = None) -> list:
    """Load a single Korean HuggingFace dataset, deduplicate, and return new samples."""
    from datasets import load_dataset

    name = config["name"]
    split = config["split"]
    field_map = config["field_map"]
    is_conversation = config.get("is_conversation", False)

    print(f"\n  Loading {name} (split={split})...", flush=True)

    try:
        ds = load_dataset(name, split=split, trust_remote_code=True)
    except Exception as e:
        print(f"  [ERROR] Failed to load {name}: {e}", flush=True)
        # Try alternative names/configs
        for alt_name in [name.replace("-", "_"), name]:
            try:
                ds = load_dataset(alt_name, split=split, trust_remote_code=True)
                break
            except Exception:
                continue
        else:
            return []

    print(f"    Raw size: {len(ds):,}", flush=True)

    # Detect field names from first item
    if len(ds) > 0:
        first = ds[0]
        fields = list(first.keys())
        print(f"    Fields: {fields}", flush=True)

        # Auto-detect best field mapping
        actual_map = _detect_field_map(first, config)
        if actual_map:
            field_map = actual_map
            print(f"    Using fields: inst={field_map.get('instruction','')}, "
                  f"out={field_map.get('output','')}", flush=True)

    samples = []
    dup_count = 0

    for item in tqdm(ds, total=len(ds), desc=f"    {name.split('/')[-1]}"):
        if max_samples and len(samples) >= max_samples:
            break

        if is_conversation:
            pairs = _convert_conversation(item)
            for s in pairs:
                h = dedup_hash(s["instruction"] + s["output"])
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    samples.append(s)
                else:
                    dup_count += 1
        else:
            sample = _convert_sample(item, field_map)
            if sample and quality_filter(sample):
                h = dedup_hash(sample["instruction"] + sample["output"])
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    samples.append(sample)
                else:
                    dup_count += 1

    print(f"    New samples: {len(samples):,} (skipped {dup_count:,} duplicates)", flush=True)
    return samples


def _detect_field_map(first_item: dict, config: dict) -> dict:
    """Auto-detect the best field mapping from a dataset's first item."""
    fields = set(first_item.keys())

    # Check primary mapping
    fm = config["field_map"]
    inst_f = fm.get("instruction", "")
    out_f = fm.get("output", "")
    if inst_f in fields and (not out_f or out_f in fields):
        return fm

    # Check alternatives
    for alt in config.get("alt_field_maps", []):
        inst_f = alt.get("instruction", "")
        out_f = alt.get("output", "")
        if inst_f in fields and (not out_f or out_f in fields):
            return alt

    # Common field name patterns
    common_patterns = [
        {"instruction": "instruction", "input": "input", "output": "output"},
        {"instruction": "question", "input": "context", "output": "answer"},
        {"instruction": "prompt", "input": "", "output": "completion"},
        {"instruction": "prompt", "input": "", "output": "response"},
        {"instruction": "input", "input": "", "output": "output"},
        {"instruction": "query", "input": "", "output": "response"},
        {"instruction": "text", "input": "", "output": "label"},
    ]
    for pattern in common_patterns:
        inst_f = pattern.get("instruction", "")
        out_f = pattern.get("output", "")
        if inst_f in fields and (not out_f or out_f in fields):
            return pattern

    return None


# ═══════════════════════════════════════════════════════════════════
# Build existing hash set
# ═══════════════════════════════════════════════════════════════════

def load_existing_hashes(output_dir: Path) -> set:
    """Load MD5 hashes of all existing instructions for dedup."""
    hashes = set()
    for fname in ["train.jsonl", "val.jsonl"]:
        path = output_dir / fname
        if not path.exists():
            continue
        print(f"  Building hash index from {fname}...", end="", flush=True)
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    h = dedup_hash(item.get("instruction", "") + item.get("output", ""))
                    hashes.add(h)
                    count += 1
                except (json.JSONDecodeError, KeyError):
                    pass
        print(f" {count:,} entries", flush=True)
    return hashes


def count_existing_ko(output_dir: Path) -> int:
    """Count existing Korean samples."""
    count = 0
    for fname in ["train.jsonl", "val.jsonl"]:
        path = output_dir / fname
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    if item.get("lang") == "ko":
                        count += 1
                except (json.JSONDecodeError, KeyError):
                    pass
    return count


# ═══════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════

def show_status():
    """Show current Korean instruct stats."""
    print("=" * 65)
    print("  Korean Instruct Data — Status")
    print("=" * 65)

    meta_path = OUTPUT_DIR / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        ko_stats = meta.get("stats", {}).get("ko", {})
        total = meta.get("actual_count", 0)
        print(f"\n  Total samples:  {total:,}")
        print(f"  Korean samples: {ko_stats.get('deduped', 0):,}")
        print(f"  Korean target:  {ko_stats.get('target', 200000):,}")
        print(f"  Korean ratio:   {ko_stats.get('deduped', 0) / max(total, 1):.1%}")
        print(f"  Datasets used:  {meta.get('datasets', {}).get('ko', [])}")
    else:
        print("  No metadata.json found")

    # Live count
    ko_count = count_existing_ko(OUTPUT_DIR)
    print(f"\n  Live Korean count: {ko_count:,}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Expand Korean instruct data by downloading additional HuggingFace datasets",
    )
    parser.add_argument("--target", type=int, default=150_000,
                        help="Target total Korean samples (default: 150000)")
    parser.add_argument("--val-ratio", type=float, default=0.05,
                        help="Fraction of new samples for validation (default: 0.05)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without downloading")
    parser.add_argument("--status", action="store_true",
                        help="Show current Korean stats and exit")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    print("=" * 65)
    print("  Korean Instruct Data Expansion")
    print("=" * 65)

    # Current stats
    existing_ko = count_existing_ko(OUTPUT_DIR)
    needed = max(0, args.target - existing_ko)

    print(f"\n  Current Korean samples: {existing_ko:,}")
    print(f"  Target:                 {args.target:,}")
    print(f"  Need to add:            {needed:,}")
    print(f"\n  New datasets to try:")
    for ds in KO_DATASETS:
        print(f"    - {ds['name']} ({ds['description']})")

    if needed == 0:
        print(f"\n  Already at target! Nothing to do.")
        return

    if args.dry_run:
        total_est = sum(d.get("estimated_size", 0) for d in KO_DATASETS)
        print(f"\n  [DRY RUN] Would download ~{total_est:,} estimated samples")
        print(f"  After dedup, expect ~{int(total_est * 0.7):,} new samples")
        return

    # Build dedup hash set from existing data
    print(f"\n  Building dedup index from existing data...")
    seen_hashes = load_existing_hashes(OUTPUT_DIR)
    print(f"  Existing hash count: {len(seen_hashes):,}")

    # Download and collect
    random.seed(args.seed)
    t0 = time.time()
    all_new = []

    for ds_config in KO_DATASETS:
        if len(all_new) >= needed:
            print(f"\n  Reached target ({len(all_new):,} >= {needed:,}), skipping remaining datasets.")
            break

        remaining = needed - len(all_new)
        samples = load_ko_dataset(ds_config, seen_hashes, max_samples=remaining)
        all_new.extend(samples)
        print(f"  Running total: {len(all_new):,} new Korean samples", flush=True)

    if not all_new:
        print("\n  No new samples collected. All datasets failed or fully duplicated.")
        return

    # Shuffle
    random.shuffle(all_new)

    # Split train/val
    val_count = max(1, int(len(all_new) * args.val_ratio))
    train_new = all_new[val_count:]
    val_new = all_new[:val_count]

    print(f"\n{'=' * 65}")
    print(f"  Appending {len(all_new):,} new Korean samples")
    print(f"    train: +{len(train_new):,}")
    print(f"    val:   +{len(val_new):,}")
    print(f"{'=' * 65}")

    # Append to train.jsonl
    train_path = OUTPUT_DIR / "train.jsonl"
    print(f"\n  Appending to {train_path.name}...", flush=True)
    with open(train_path, "a", encoding="utf-8") as f:
        for sample in train_new:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"    +{len(train_new):,} lines appended", flush=True)

    # Append to val.jsonl
    val_path = OUTPUT_DIR / "val.jsonl"
    print(f"  Appending to {val_path.name}...", flush=True)
    with open(val_path, "a", encoding="utf-8") as f:
        for sample in val_new:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"    +{len(val_new):,} lines appended", flush=True)

    # Update metadata.json
    meta_path = OUTPUT_DIR / "metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    # Recount everything
    total_train = sum(1 for _ in open(train_path, "r", encoding="utf-8"))
    total_val = sum(1 for _ in open(val_path, "r", encoding="utf-8"))
    total_all = total_train + total_val

    # Count per language
    lang_counts = Counter()
    for fname in ["train.jsonl", "val.jsonl"]:
        with open(OUTPUT_DIR / fname, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    item = json.loads(line.strip())
                    lang_counts[item.get("lang", "?")] += 1
                except (json.JSONDecodeError, KeyError):
                    pass

    # Update metadata
    meta["actual_count"] = total_all
    meta["train_count"] = total_train
    meta["val_count"] = total_val

    if "stats" not in meta:
        meta["stats"] = {}
    meta["stats"]["ko"] = {
        "raw": meta["stats"].get("ko", {}).get("raw", 0) + len(all_new),
        "deduped": lang_counts.get("ko", 0),
        "duplicates_removed": meta["stats"].get("ko", {}).get("duplicates_removed", 0),
        "target": 200_000,
    }

    # Add new dataset names
    existing_ko_ds = meta.get("datasets", {}).get("ko", [])
    new_ds_names = [d["name"] for d in KO_DATASETS]
    for name in new_ds_names:
        if name not in existing_ko_ds:
            existing_ko_ds.append(name)
    if "datasets" not in meta:
        meta["datasets"] = {}
    meta["datasets"]["ko"] = existing_ko_ds

    meta["last_expansion"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    meta["expansion_added"] = len(all_new)

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"  metadata.json updated", flush=True)

    # Summary
    elapsed = time.time() - t0
    print(f"\n{'=' * 65}")
    print(f"  Summary")
    print(f"{'=' * 65}")
    print(f"  Time:              {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"  New Korean added:  {len(all_new):,}")
    print(f"    train:           +{len(train_new):,}")
    print(f"    val:             +{len(val_new):,}")
    print(f"  Total samples now: {total_all:,}")
    print(f"  Per language:")
    for lang in sorted(lang_counts.keys()):
        cnt = lang_counts[lang]
        pct = 100 * cnt / total_all if total_all else 0
        print(f"    {lang}: {cnt:,} ({pct:.1f}%)")

    # File sizes
    for p in [train_path, val_path]:
        sz = p.stat().st_size / (1024 * 1024)
        lines = sum(1 for _ in open(p, "r", encoding="utf-8"))
        print(f"  {p.name}: {sz:.1f} MB, {lines:,} lines")

    # Preview
    print(f"\n  --- Preview (3 new samples) ---")
    for s in all_new[:3]:
        inst = s["instruction"][:80].replace("\n", " ")
        out = s["output"][:80].replace("\n", " ")
        print(f"    [ko] {inst}")
        print(f"         -> {out}")
        print()

    print("  Done.")


if __name__ == "__main__":
    main()
