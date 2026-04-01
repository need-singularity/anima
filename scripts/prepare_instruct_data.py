#!/usr/bin/env python3
"""prepare_instruct_data.py — Download & merge HuggingFace instruction datasets for AnimaLM 7B

Downloads Korean, English, and Code instruction datasets from HuggingFace,
converts them to a unified JSONL format, and prepares train/val splits
compatible with train_anima_lm.py InstructDataset.

Output JSONL format:
  {"instruction": "...", "input": "...", "output": "...", "lang": "ko|en|code"}

Mistral chat template format (optional --mistral-format):
  {"text": "[INST] instruction input [/INST] output</s>"}

Usage:
  python scripts/prepare_instruct_data.py
  python scripts/prepare_instruct_data.py --ko-ratio 0.4 --en-ratio 0.4 --code-ratio 0.2
  python scripts/prepare_instruct_data.py --target-count 500000 --dry-run
  python scripts/prepare_instruct_data.py --mistral-format
  python scripts/prepare_instruct_data.py --status

Requires: pip install datasets tqdm
"""

import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        desc = kwargs.get("desc", "")
        total = kwargs.get("total", None)
        for i, item in enumerate(iterable):
            if i % 10000 == 0:
                progress = f" ({i}/{total})" if total else f" ({i})"
                print(f"\r  {desc}{progress}", end="", flush=True)
            yield item
        print()

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "anima" / "data" / "instruct"

# ═══════════════════════════════════════════════════════════════════
# Dataset Registry
# ═══════════════════════════════════════════════════════════════════

DATASETS = {
    # Korean instruction datasets
    "ko": [
        {
            "name": "beomi/KoAlpaca-v1.1a",
            "split": "train",
            "streaming": False,
            "field_map": {"instruction": "instruction", "input": "input", "output": "output"},
            "description": "Korean Alpaca (52K)",
            "estimated_size": 52_000,
        },
        {
            "name": "heegyu/korquad-chat-v1",
            "split": "train",
            "streaming": False,
            "field_map": {"instruction": "question", "input": "context", "output": "answer"},
            "description": "KorQuAD chat format (60K)",
            "estimated_size": 60_000,
        },
        {
            "name": "kyujinpy/KOR-OpenOrca-Platypus-v3",
            "split": "train",
            "streaming": False,
            "field_map": {"instruction": "instruction", "input": "input", "output": "output"},
            "description": "Korean OpenOrca+Platypus (200K)",
            "estimated_size": 200_000,
        },
    ],
    # English instruction datasets
    "en": [
        {
            "name": "tatsu-lab/alpaca",
            "split": "train",
            "streaming": False,
            "field_map": {"instruction": "instruction", "input": "input", "output": "output"},
            "description": "Stanford Alpaca (52K)",
            "estimated_size": 52_000,
        },
        {
            "name": "Open-Orca/OpenOrca",
            "split": "train",
            "streaming": True,
            "field_map": {"instruction": "question", "input": "", "output": "response"},
            "max_samples": 200_000,
            "description": "OpenOrca subset (200K from 4M)",
            "estimated_size": 200_000,
        },
        {
            "name": "WizardLM/WizardLM_evol_instruct_V2_196k",
            "split": "train",
            "streaming": False,
            "field_map": {"instruction": "instruction", "input": "", "output": "output"},
            "description": "WizardLM EvolInstruct v2 (196K)",
            "estimated_size": 196_000,
        },
    ],
    # Code instruction datasets
    "code": [
        {
            "name": "sahil2801/CodeAlpaca-20k",
            "split": "train",
            "streaming": False,
            "field_map": {"instruction": "instruction", "input": "input", "output": "output"},
            "description": "CodeAlpaca (20K)",
            "estimated_size": 20_000,
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════
# Quality Filters
# ═══════════════════════════════════════════════════════════════════

MIN_INSTRUCTION_LEN = 10
MAX_INSTRUCTION_LEN = 4096
MIN_OUTPUT_LEN = 10
MAX_OUTPUT_LEN = 8192


def quality_filter(sample: dict, min_inst_len: int = MIN_INSTRUCTION_LEN,
                   max_inst_len: int = MAX_INSTRUCTION_LEN,
                   min_out_len: int = MIN_OUTPUT_LEN,
                   max_out_len: int = MAX_OUTPUT_LEN) -> bool:
    """Return True if sample passes quality checks."""
    inst = sample.get("instruction", "")
    output = sample.get("output", "")

    # Length checks
    if len(inst) < min_inst_len or len(inst) > max_inst_len:
        return False
    if len(output) < min_out_len or len(output) > max_out_len:
        return False

    # Empty/whitespace check
    if not inst.strip() or not output.strip():
        return False

    # Repeated character check (e.g., "aaaaaaa...")
    if len(set(inst.strip())) < 3:
        return False

    return True


def dedup_hash(text: str) -> str:
    """Return hash for deduplication."""
    normalized = text.strip().lower()[:200]
    return hashlib.md5(normalized.encode("utf-8", errors="ignore")).hexdigest()


# ═══════════════════════════════════════════════════════════════════
# Dataset Loaders
# ═══════════════════════════════════════════════════════════════════

def load_hf_dataset(config: dict, max_samples: int = None) -> list:
    """Load a single HuggingFace dataset and convert to unified format."""
    from datasets import load_dataset

    name = config["name"]
    split = config["split"]
    streaming = config.get("streaming", False)
    field_map = config["field_map"]
    ds_max = config.get("max_samples", max_samples)

    print(f"  Loading {name} (split={split}, streaming={streaming})...")

    try:
        if streaming:
            ds = load_dataset(name, split=split, streaming=True, trust_remote_code=True)
        else:
            ds = load_dataset(name, split=split, trust_remote_code=True)
    except Exception as e:
        print(f"  [ERROR] Failed to load {name}: {e}")
        return []

    samples = []
    count = 0

    if streaming:
        # Streaming mode: iterate and collect
        iterator = iter(ds)
        pbar = tqdm(total=ds_max, desc=f"    {name.split('/')[-1]}")
        while count < (ds_max or float("inf")):
            try:
                item = next(iterator)
            except StopIteration:
                break

            sample = _convert_sample(item, field_map)
            if sample and quality_filter(sample):
                samples.append(sample)
                count += 1
                pbar.update(1)
        pbar.close()
    else:
        # Non-streaming: direct iteration
        total = min(len(ds), ds_max) if ds_max else len(ds)
        for i, item in enumerate(tqdm(ds, total=len(ds), desc=f"    {name.split('/')[-1]}")):
            if ds_max and count >= ds_max:
                break
            sample = _convert_sample(item, field_map)
            if sample and quality_filter(sample):
                samples.append(sample)
                count += 1

    print(f"    Collected: {len(samples):,} samples")
    return samples


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

        # Handle system_prompt field (some datasets have it)
        system = str(item.get("system_prompt", item.get("system", ""))).strip()
        if system and not instruction.startswith(system):
            instruction = f"{system}\n{instruction}" if system != "" else instruction

        return {
            "instruction": instruction,
            "input": inp,
            "output": output,
        }
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════
# Mistral Chat Template Converter
# ═══════════════════════════════════════════════════════════════════

def to_mistral_format(sample: dict) -> str:
    """Convert instruction/input/output to Mistral [INST]...[/INST] format.

    Format:
      <s>[INST] {instruction} {input} [/INST] {output}</s>
    """
    inst = sample["instruction"].strip()
    inp = sample.get("input", "").strip()
    output = sample["output"].strip()

    # Combine instruction and input
    if inp:
        user_msg = f"{inst}\n\n{inp}"
    else:
        user_msg = inst

    return f"<s>[INST] {user_msg} [/INST] {output}</s>"


# ═══════════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════════

def show_status():
    """Show current dataset stats if output files exist."""
    print("=" * 65)
    print("  AnimaLM Instruct Dataset — Status")
    print("=" * 65)

    for name in ["train.jsonl", "val.jsonl", "train_mistral.jsonl", "val_mistral.jsonl"]:
        path = OUTPUT_DIR / name
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            line_count = 0
            lang_counts = Counter()
            inst_lens = []
            out_lens = []

            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line_count += 1
                    try:
                        item = json.loads(line.strip())
                        lang_counts[item.get("lang", "?")] += 1
                        inst_lens.append(len(item.get("instruction", "")))
                        out_lens.append(len(item.get("output", item.get("text", ""))))
                    except json.JSONDecodeError:
                        pass

            print(f"\n  {name}")
            print(f"    Path:    {path}")
            print(f"    Size:    {size_mb:.1f} MB")
            print(f"    Samples: {line_count:,}")

            if lang_counts:
                print(f"    Languages:")
                for lang, cnt in sorted(lang_counts.items(), key=lambda x: -x[1]):
                    pct = 100 * cnt / line_count if line_count else 0
                    print(f"      {lang}: {cnt:,} ({pct:.1f}%)")

            if inst_lens:
                avg_inst = sum(inst_lens) / len(inst_lens)
                avg_out = sum(out_lens) / len(out_lens)
                print(f"    Avg instruction len: {avg_inst:.0f} chars")
                print(f"    Avg output len:      {avg_out:.0f} chars")
        else:
            print(f"\n  {name}: NOT FOUND ({path})")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Download & prepare HuggingFace instruction datasets for AnimaLM 7B",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Default: 500K, 40/40/20 ratio
  %(prog)s --ko-ratio 0.5 --en-ratio 0.3     # More Korean
  %(prog)s --target-count 100000 --dry-run    # Preview without downloading
  %(prog)s --mistral-format                   # Also generate Mistral chat format
  %(prog)s --status                           # Show existing dataset stats
        """,
    )

    parser.add_argument("--ko-ratio", type=float, default=0.4,
                        help="Korean data ratio (default: 0.4)")
    parser.add_argument("--en-ratio", type=float, default=0.4,
                        help="English data ratio (default: 0.4)")
    parser.add_argument("--code-ratio", type=float, default=0.2,
                        help="Code data ratio (default: 0.2)")
    parser.add_argument("--target-count", type=int, default=500_000,
                        help="Target total samples (default: 500000)")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR),
                        help=f"Output directory (default: {OUTPUT_DIR})")
    parser.add_argument("--val-ratio", type=float, default=0.05,
                        help="Validation split ratio (default: 0.05)")
    parser.add_argument("--mistral-format", action="store_true",
                        help="Also generate Mistral [INST] chat template format")
    parser.add_argument("--min-inst-len", type=int, default=MIN_INSTRUCTION_LEN,
                        help=f"Minimum instruction length (default: {MIN_INSTRUCTION_LEN})")
    parser.add_argument("--max-inst-len", type=int, default=MAX_INSTRUCTION_LEN,
                        help=f"Maximum instruction length (default: {MAX_INSTRUCTION_LEN})")
    parser.add_argument("--min-out-len", type=int, default=MIN_OUTPUT_LEN,
                        help=f"Minimum output length (default: {MIN_OUTPUT_LEN})")
    parser.add_argument("--max-out-len", type=int, default=MAX_OUTPUT_LEN,
                        help=f"Maximum output length (default: {MAX_OUTPUT_LEN})")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (default: 42)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show plan without downloading")
    parser.add_argument("--status", action="store_true",
                        help="Show current dataset stats and exit")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    # Validate ratios
    total_ratio = args.ko_ratio + args.en_ratio + args.code_ratio
    if abs(total_ratio - 1.0) > 0.01:
        print(f"[WARNING] Ratios sum to {total_ratio:.2f}, normalizing to 1.0")
        args.ko_ratio /= total_ratio
        args.en_ratio /= total_ratio
        args.code_ratio /= total_ratio

    # Calculate per-language targets
    ko_target = int(args.target_count * args.ko_ratio)
    en_target = int(args.target_count * args.en_ratio)
    code_target = int(args.target_count * args.code_ratio)

    print("=" * 65)
    print("  AnimaLM 7B — HuggingFace Instruct Dataset Preparation")
    print("=" * 65)
    print(f"\n  Target: {args.target_count:,} total samples")
    print(f"  Ratios: ko={args.ko_ratio:.0%} ({ko_target:,}), "
          f"en={args.en_ratio:.0%} ({en_target:,}), "
          f"code={args.code_ratio:.0%} ({code_target:,})")
    print(f"  Split:  train={1-args.val_ratio:.0%}, val={args.val_ratio:.0%}")
    print(f"  Output: {args.output_dir}")
    print(f"  Filters: inst=[{args.min_inst_len}, {args.max_inst_len}], "
          f"out=[{args.min_out_len}, {args.max_out_len}]")

    # Show dataset plan
    print("\n  Datasets:")
    for lang, datasets in DATASETS.items():
        for ds in datasets:
            est = ds.get("estimated_size", "?")
            streaming = "streaming" if ds.get("streaming") else "full"
            print(f"    [{lang}] {ds['name']} ({ds['description']}, {streaming})")

    if args.dry_run:
        print("\n  [DRY RUN] Would download and process the above datasets.")
        print(f"  Estimated download: ~2-5 GB (streaming reduces memory usage)")
        print(f"  Estimated output: ~{args.target_count * 500 / 1e9:.1f} GB JSONL")
        print(f"  Estimated time: 20-40 minutes (depends on network speed)")
        return

    # Download and collect
    random.seed(args.seed)
    all_data = defaultdict(list)
    targets = {"ko": ko_target, "en": en_target, "code": code_target}

    t0 = time.time()

    for lang, datasets in DATASETS.items():
        lang_target = targets[lang]
        per_dataset_target = lang_target // len(datasets) + 1
        print(f"\n{'='*65}")
        print(f"  [{lang.upper()}] Target: {lang_target:,} samples "
              f"({per_dataset_target:,} per dataset)")
        print(f"{'='*65}")

        for ds_config in datasets:
            max_per_ds = ds_config.get("max_samples", per_dataset_target)
            effective_max = min(max_per_ds, per_dataset_target)
            samples = load_hf_dataset(ds_config, max_samples=effective_max)

            # Tag language
            for s in samples:
                s["lang"] = lang

            all_data[lang].extend(samples)

    # Balance to target ratios
    print(f"\n{'='*65}")
    print("  Balancing & Deduplication")
    print(f"{'='*65}")

    final_samples = []
    seen_hashes = set()
    stats = {}

    for lang in ["ko", "en", "code"]:
        pool = all_data[lang]
        random.shuffle(pool)

        target = targets[lang]
        deduped = []
        dup_count = 0

        for s in pool:
            h = dedup_hash(s["instruction"] + s["output"])
            if h not in seen_hashes:
                seen_hashes.add(h)
                deduped.append(s)
            else:
                dup_count += 1

            if len(deduped) >= target:
                break

        stats[lang] = {
            "raw": len(pool),
            "deduped": len(deduped),
            "duplicates_removed": dup_count,
            "target": target,
        }

        print(f"  [{lang}] raw={len(pool):,} -> dedup={len(deduped):,} "
              f"(removed {dup_count:,} dups), target={target:,}")

        final_samples.extend(deduped)

    # Final shuffle
    random.shuffle(final_samples)
    total = len(final_samples)

    # Train/val split
    val_count = int(total * args.val_ratio)
    train_count = total - val_count
    train_data = final_samples[:train_count]
    val_data = final_samples[train_count:]

    print(f"\n  Final: {total:,} samples (train={train_count:,}, val={val_count:,})")

    # Write output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write unified JSONL
    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "val.jsonl"

    _write_jsonl(train_data, train_path, "train")
    _write_jsonl(val_data, val_path, "val")

    # Mistral format
    if args.mistral_format:
        train_mistral_path = output_dir / "train_mistral.jsonl"
        val_mistral_path = output_dir / "val_mistral.jsonl"
        _write_mistral_jsonl(train_data, train_mistral_path, "train_mistral")
        _write_mistral_jsonl(val_data, val_mistral_path, "val_mistral")

    # Summary
    elapsed = time.time() - t0
    print(f"\n{'='*65}")
    print("  Summary")
    print(f"{'='*65}")
    print(f"  Total time:    {elapsed:.0f}s ({elapsed/60:.1f}m)")
    print(f"  Total samples: {total:,}")

    for lang in ["ko", "en", "code"]:
        s = stats[lang]
        pct = 100 * s["deduped"] / total if total else 0
        print(f"    {lang}: {s['deduped']:,} ({pct:.1f}%)")

    print(f"\n  Output files:")
    for p in [train_path, val_path]:
        if p.exists():
            sz = p.stat().st_size / (1024 * 1024)
            print(f"    {p.name}: {sz:.1f} MB")

    if args.mistral_format:
        for p in [train_mistral_path, val_mistral_path]:
            if p.exists():
                sz = p.stat().st_size / (1024 * 1024)
                print(f"    {p.name}: {sz:.1f} MB")

    # Write metadata
    meta = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "target_count": args.target_count,
        "actual_count": total,
        "train_count": train_count,
        "val_count": val_count,
        "ratios": {"ko": args.ko_ratio, "en": args.en_ratio, "code": args.code_ratio},
        "stats": stats,
        "filters": {
            "min_inst_len": args.min_inst_len,
            "max_inst_len": args.max_inst_len,
            "min_out_len": args.min_out_len,
            "max_out_len": args.max_out_len,
        },
        "seed": args.seed,
        "datasets": {lang: [d["name"] for d in ds_list] for lang, ds_list in DATASETS.items()},
    }
    meta_path = output_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"    metadata.json: saved")

    # Sample preview
    print(f"\n  --- Preview (3 samples) ---")
    for s in final_samples[:3]:
        lang = s.get("lang", "?")
        inst = s["instruction"][:70].replace("\n", " ")
        out = s["output"][:70].replace("\n", " ")
        print(f"    [{lang}] {inst}")
        print(f"         -> {out}")
        print()

    print("  Done.")


def _write_jsonl(data: list, path: Path, label: str):
    """Write samples as JSONL."""
    print(f"\n  Writing {label}: {path.name} ({len(data):,} samples)...")
    with open(path, "w", encoding="utf-8") as f:
        for sample in tqdm(data, desc=f"    {label}"):
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
    sz = path.stat().st_size / (1024 * 1024)
    print(f"    -> {sz:.1f} MB")


def _write_mistral_jsonl(data: list, path: Path, label: str):
    """Write samples in Mistral [INST] chat template format."""
    print(f"\n  Writing {label}: {path.name} ({len(data):,} samples)...")
    with open(path, "w", encoding="utf-8") as f:
        for sample in tqdm(data, desc=f"    {label}"):
            text = to_mistral_format(sample)
            row = {
                "text": text,
                "lang": sample.get("lang", ""),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    sz = path.stat().st_size / (1024 * 1024)
    print(f"    -> {sz:.1f} MB")


if __name__ == "__main__":
    main()
