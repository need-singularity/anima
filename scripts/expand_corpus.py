#!/usr/bin/env python3
"""Expand multilingual corpus to ~10GB using HuggingFace datasets.

Downloads from HuggingFace datasets in streaming mode to avoid OOM.
Appends to existing corpus files without overwriting.

Usage:
    python scripts/expand_corpus.py --all                    # All languages
    python scripts/expand_corpus.py --lang ko --target-gb 2  # Korean only
    python scripts/expand_corpus.py --lang en,zh             # Multiple langs
    python scripts/expand_corpus.py --all --dry-run           # Show plan only
    python scripts/expand_corpus.py --all --resume            # Resume interrupted download

Requirements:
    pip install datasets tqdm xxhash
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path

try:
    from datasets import load_dataset
except ImportError:
    print("ERROR: 'datasets' library required. Install with: pip install datasets")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    print("ERROR: 'tqdm' library required. Install with: pip install tqdm")
    sys.exit(1)

try:
    import xxhash
    def fast_hash(text: str) -> str:
        return xxhash.xxh64(text.encode('utf-8')).hexdigest()
except ImportError:
    def fast_hash(text: str) -> str:
        return hashlib.md5(text.encode('utf-8')).hexdigest()

# ── Config ──────────────────────────────────────────────────────────
CORPUS_DIR = Path(__file__).resolve().parent.parent / "anima" / "data" / "corpus_multilingual"
PROGRESS_DIR = CORPUS_DIR / ".progress"

# Target sizes in GB
DEFAULT_TARGETS_GB = {
    "ko":   2.0,
    "en":   3.0,
    "zh":   1.5,
    "ja":   1.0,
    "ru":   1.0,
    "code": 1.5,
}

# ── Dataset sources per language ────────────────────────────────────
# Each entry: (dataset_name, config, split, text_field, description)
# Ordered by quality/reliability — first sources tried first.

SOURCES = {
    "ko": [
        ("wikimedia/wikipedia", "20231101.ko", "train", "text",
         "Korean Wikipedia — comprehensive encyclopedia articles"),
        ("beomi/KoAlpaca-v1.1a", None, "train", "instruction",
         "KoAlpaca — Korean instruction-following data"),
        ("heegyu/korquad-chat-v1", None, "train", "context",
         "KorQuAD chat — Korean reading comprehension contexts"),
        ("allenai/c4", "ko", "train", "text",
         "C4 Korean (allenai) — large web crawl, cleaned"),
    ],
    "en": [
        ("wikimedia/wikipedia", "20231101.en", "train", "text",
         "English Wikipedia — comprehensive encyclopedia"),
        ("openwebtext", None, "train", "text",
         "OpenWebText — Reddit-filtered web content"),
        ("allenai/c4", "en", "train", "text",
         "C4 English (allenai) — large web crawl, cleaned"),
    ],
    "zh": [
        ("wikimedia/wikipedia", "20231101.zh", "train", "text",
         "Chinese Wikipedia — encyclopedia articles"),
        ("allenai/c4", "zh", "train", "text",
         "C4 Chinese (allenai) — large web crawl, cleaned"),
    ],
    "ja": [
        ("wikimedia/wikipedia", "20231101.ja", "train", "text",
         "Japanese Wikipedia — encyclopedia articles"),
        ("allenai/c4", "ja", "train", "text",
         "C4 Japanese (allenai) — large web crawl, cleaned"),
    ],
    "ru": [
        ("wikimedia/wikipedia", "20231101.ru", "train", "text",
         "Russian Wikipedia — encyclopedia articles"),
        ("allenai/c4", "ru", "train", "text",
         "C4 Russian (allenai) — large web crawl, cleaned"),
    ],
    "code": [
        ("bigcode/starcoderdata", "python", "train", "content",
         "StarCoderData Python — high-quality Python code"),
        ("bigcode/starcoderdata", "javascript", "train", "content",
         "StarCoderData JavaScript — JS/TS code"),
        ("bigcode/starcoderdata", "rust", "train", "content",
         "StarCoderData Rust — Rust code"),
    ],
}


# ── Filtering ───────────────────────────────────────────────────────

# CJK character ranges for length counting
CJK_RE = re.compile(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]')

def is_cjk_lang(lang: str) -> bool:
    return lang in ("zh", "ja", "ko")

def filter_text(text: str, lang: str) -> str | None:
    """Filter and clean a text sample. Returns None if rejected."""
    if not text or not isinstance(text, str):
        return None

    # Strip and normalize whitespace
    text = text.strip()
    if not text:
        return None

    # Language-specific length filters
    if lang == "code":
        lines = text.split('\n')
        if len(lines) < 10 or len(lines) > 500:
            return None
        # Skip binary-looking content
        if '\x00' in text or '\xff' in text:
            return None
        # Skip files that are mostly non-ASCII (likely binary/data)
        ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
        if ascii_ratio < 0.5:
            return None
        return text
    elif is_cjk_lang(lang):
        # CJK: count characters (shorter thresholds)
        char_count = len(text)
        if char_count < 20 or char_count > 5000:
            return None
    else:
        # Latin/Cyrillic: count characters
        char_count = len(text)
        if char_count < 50 or char_count > 5000:
            return None

    # Remove lines with too many URLs/emails (spam-like)
    url_count = text.count('http://') + text.count('https://')
    if url_count > 5:
        return None

    return text


def filter_code(text: str) -> str | None:
    """Additional code-specific filtering."""
    if not text:
        return None
    lines = text.strip().split('\n')
    # Min 10 lines, max 500 lines
    if len(lines) < 10 or len(lines) > 500:
        return None
    # No binary
    if '\x00' in text:
        return None
    # At least 50% ASCII
    ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
    if ascii_ratio < 0.5:
        return None
    return text.strip()


# ── Deduplication ───────────────────────────────────────────────────

class Deduplicator:
    """Memory-efficient deduplicator using hash set."""

    def __init__(self, max_hashes: int = 50_000_000):
        self.seen: set[str] = set()
        self.max_hashes = max_hashes
        self.duplicates = 0
        self.total = 0

    def is_duplicate(self, text: str) -> bool:
        self.total += 1
        # Use first 200 chars + last 200 chars as fingerprint
        fingerprint = text[:200] + text[-200:] if len(text) > 400 else text
        h = fast_hash(fingerprint)
        if h in self.seen:
            self.duplicates += 1
            return True
        if len(self.seen) < self.max_hashes:
            self.seen.add(h)
        return False

    @property
    def dup_rate(self) -> float:
        return self.duplicates / max(self.total, 1)


# ── Progress tracking ──────────────────────────────────────────────

def load_progress(lang: str) -> dict:
    """Load download progress for resuming."""
    progress_file = PROGRESS_DIR / f"{lang}.json"
    if progress_file.exists():
        import json
        with open(progress_file) as f:
            return json.load(f)
    return {"bytes_written": 0, "source_idx": 0, "samples_in_source": 0}


def save_progress(lang: str, progress: dict):
    """Save download progress."""
    import json
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    progress_file = PROGRESS_DIR / f"{lang}.json"
    with open(progress_file, 'w') as f:
        json.dump(progress, f)


def clear_progress(lang: str):
    """Clear progress after completion."""
    progress_file = PROGRESS_DIR / f"{lang}.json"
    if progress_file.exists():
        progress_file.unlink()


# ── Core download logic ────────────────────────────────────────────

def get_text_field(example: dict, field: str) -> str | None:
    """Extract text from a dataset example, handling nested fields."""
    if field in example:
        return example[field]
    # Try common alternatives
    for alt in ["text", "content", "sentence", "document"]:
        if alt in example:
            return example[alt]
    return None


def download_lang(lang: str, target_gb: float, resume: bool = False,
                  dry_run: bool = False) -> dict:
    """Download corpus for a single language.

    Returns dict with stats: bytes_written, samples, duplicates, time_s
    """
    target_bytes = int(target_gb * 1024 * 1024 * 1024)
    out_path = CORPUS_DIR / f"{lang}.txt"
    existing_bytes = out_path.stat().st_size if out_path.exists() else 0
    remaining = target_bytes - existing_bytes

    sources = SOURCES.get(lang, [])
    if not sources:
        print(f"  ERROR: No sources defined for '{lang}'")
        return {"bytes_written": 0, "samples": 0, "duplicates": 0, "time_s": 0}

    print(f"\n{'='*70}")
    print(f"  Language: {lang}")
    print(f"  Target:   {target_gb:.1f} GB ({target_bytes / 1e9:.1f} GB)")
    print(f"  Existing: {existing_bytes / 1e9:.2f} GB")
    print(f"  To add:   {remaining / 1e9:.2f} GB")
    print(f"  Sources:  {len(sources)}")
    for i, (ds, cfg, split, field, desc) in enumerate(sources):
        print(f"    [{i+1}] {desc}")
    print(f"{'='*70}")

    if remaining <= 0:
        print(f"  SKIP: Already at or above target ({existing_bytes / 1e9:.2f} GB >= {target_gb:.1f} GB)")
        return {"bytes_written": 0, "samples": 0, "duplicates": 0, "time_s": 0}

    if dry_run:
        print(f"  DRY RUN: Would download {remaining / 1e9:.2f} GB from {len(sources)} sources")
        return {"bytes_written": 0, "samples": 0, "duplicates": 0, "time_s": 0}

    # Load progress for resume
    progress = load_progress(lang) if resume else {"bytes_written": 0, "source_idx": 0, "samples_in_source": 0}
    start_source = progress["source_idx"]
    skip_samples = progress["samples_in_source"] if resume else 0

    dedup = Deduplicator()
    total_written = 0
    total_samples = 0
    t0 = time.time()

    # Open file in append mode
    with open(out_path, 'a', encoding='utf-8') as f:
        for src_idx, (ds_name, ds_config, ds_split, text_field, desc) in enumerate(sources):
            if src_idx < start_source:
                continue

            if total_written >= remaining:
                break

            print(f"\n  Source [{src_idx+1}/{len(sources)}]: {ds_name}" +
                  (f" ({ds_config})" if ds_config else ""))

            try:
                # Load dataset in streaming mode
                ds = load_dataset(
                    ds_name,
                    ds_config,
                    split=ds_split,
                    streaming=True,
                )
            except Exception as e:
                print(f"    ERROR loading dataset: {e}")
                print(f"    Skipping to next source...")
                continue

            source_written = 0
            source_samples = 0
            samples_skipped = 0

            pbar = tqdm(
                desc=f"    {lang}/{ds_name.split('/')[-1]}",
                unit="samples",
                unit_scale=True,
                miniters=100,
            )

            try:
                for example in ds:
                    # Skip samples for resume
                    if skip_samples > 0:
                        skip_samples -= 1
                        samples_skipped += 1
                        continue

                    text = get_text_field(example, text_field)
                    if text is None:
                        continue

                    # Filter
                    if lang == "code":
                        cleaned = filter_code(text)
                    else:
                        cleaned = filter_text(text, lang)

                    if cleaned is None:
                        continue

                    # Deduplicate
                    if dedup.is_duplicate(cleaned):
                        continue

                    # Write
                    line = cleaned + "\n"
                    line_bytes = len(line.encode('utf-8'))
                    f.write(line)
                    total_written += line_bytes
                    source_written += line_bytes
                    total_samples += 1
                    source_samples += 1

                    pbar.update(1)
                    pbar.set_postfix({
                        "written": f"{(existing_bytes + total_written) / 1e9:.2f}GB",
                        "dup%": f"{dedup.dup_rate:.1%}",
                    })

                    # Periodic flush + progress save
                    if total_samples % 10000 == 0:
                        f.flush()
                        save_progress(lang, {
                            "bytes_written": total_written,
                            "source_idx": src_idx,
                            "samples_in_source": source_samples + samples_skipped,
                        })

                    # Check if target reached
                    if total_written >= remaining:
                        break

            except KeyboardInterrupt:
                print(f"\n    Interrupted! Saving progress...")
                f.flush()
                save_progress(lang, {
                    "bytes_written": total_written,
                    "source_idx": src_idx,
                    "samples_in_source": source_samples + samples_skipped,
                })
                pbar.close()
                raise
            except Exception as e:
                print(f"\n    ERROR during streaming: {e}")
                print(f"    Moving to next source...")

            pbar.close()
            print(f"    Source done: {source_samples:,} samples, "
                  f"{source_written / 1e6:.1f} MB written")

            # Reset skip for next source
            skip_samples = 0

    elapsed = time.time() - t0
    final_size = out_path.stat().st_size if out_path.exists() else 0

    clear_progress(lang)

    stats = {
        "bytes_written": total_written,
        "samples": total_samples,
        "duplicates": dedup.duplicates,
        "dup_rate": dedup.dup_rate,
        "time_s": elapsed,
        "final_size": final_size,
    }

    print(f"\n  DONE: {lang}")
    print(f"    Written:    {total_written / 1e9:.2f} GB ({total_samples:,} samples)")
    print(f"    Duplicates: {dedup.duplicates:,} ({dedup.dup_rate:.1%})")
    print(f"    Final size: {final_size / 1e9:.2f} GB")
    print(f"    Time:       {elapsed / 60:.1f} min")

    return stats


# ── Main ────────────────────────────────────────────────────────────

def fmt_size(n: int) -> str:
    for u in ["B", "KB", "MB", "GB"]:
        if abs(n) < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} TB"


def show_status():
    """Show current corpus status."""
    print("\n" + "=" * 70)
    print("  Multilingual Corpus Status")
    print("=" * 70)
    total = 0
    for lang in ["ko", "en", "zh", "ja", "ru", "code"]:
        path = CORPUS_DIR / f"{lang}.txt"
        if path.exists():
            size = path.stat().st_size
            lines = sum(1 for _ in open(path, encoding='utf-8', errors='ignore'))
            target = DEFAULT_TARGETS_GB.get(lang, 1.0) * 1024 * 1024 * 1024
            pct = min(100, 100 * size / target)
            bar_len = 25
            filled = int(bar_len * pct / 100)
            bar = "#" * filled + "." * (bar_len - filled)
            print(f"  {lang:>5}: [{bar}] {pct:5.1f}%  "
                  f"{size / 1e9:.2f} GB / {target / 1e9:.1f} GB  "
                  f"({lines:>10,} lines)")
            total += size
        else:
            print(f"  {lang:>5}: [.........................] 0.0%  NOT FOUND")
    print(f"  {'TOTAL':>5}: {total / 1e9:.2f} GB / "
          f"{sum(DEFAULT_TARGETS_GB.values()):.1f} GB")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Expand multilingual corpus to ~10GB using HuggingFace datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s --all                       # Download all languages to default targets
    %(prog)s --lang ko --target-gb 2     # Korean only, 2GB target
    %(prog)s --lang en,zh                # English and Chinese
    %(prog)s --all --dry-run             # Show plan without downloading
    %(prog)s --lang ko --resume          # Resume interrupted Korean download
    %(prog)s --status                    # Show current corpus sizes
        """,
    )
    parser.add_argument("--lang", type=str, default=None,
                        help="Comma-separated languages: ko,en,zh,ja,ru,code")
    parser.add_argument("--all", action="store_true",
                        help="Download all languages")
    parser.add_argument("--target-gb", type=float, default=None,
                        help="Override target size in GB (applies to all selected langs)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show download plan without actually downloading")
    parser.add_argument("--resume", action="store_true",
                        help="Resume interrupted download from saved progress")
    parser.add_argument("--status", action="store_true",
                        help="Show current corpus status and exit")
    parser.add_argument("--dedup-max", type=int, default=50_000_000,
                        help="Max hash entries for deduplication (default: 50M, ~400MB RAM)")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    # Determine languages
    if args.all:
        langs = list(DEFAULT_TARGETS_GB.keys())
    elif args.lang:
        langs = [l.strip() for l in args.lang.split(",")]
        for l in langs:
            if l not in SOURCES:
                print(f"ERROR: Unknown language '{l}'. Available: {', '.join(SOURCES.keys())}")
                sys.exit(1)
    else:
        parser.print_help()
        print("\nERROR: Specify --lang or --all")
        sys.exit(1)

    # Ensure output directory exists
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    # Show plan
    print("\n" + "=" * 70)
    print("  Corpus Expansion Plan")
    print("=" * 70)
    total_target = 0
    total_existing = 0
    for lang in langs:
        target = args.target_gb if args.target_gb else DEFAULT_TARGETS_GB.get(lang, 1.0)
        path = CORPUS_DIR / f"{lang}.txt"
        existing = path.stat().st_size / 1e9 if path.exists() else 0
        to_add = max(0, target - existing)
        total_target += target
        total_existing += existing
        status = "SKIP (at target)" if to_add <= 0.01 else f"+{to_add:.2f} GB"
        print(f"  {lang:>5}: {existing:.2f} GB -> {target:.1f} GB  [{status}]")
    print(f"  {'TOTAL':>5}: {total_existing:.2f} GB -> {total_target:.1f} GB")
    print("=" * 70)

    if args.dry_run:
        print("\n  DRY RUN complete. No data was downloaded.")
        print("  Run without --dry-run to start downloading.")
        return

    print(f"\n  Starting downloads... (Ctrl+C to interrupt, --resume to continue)")
    print(f"  Output: {CORPUS_DIR}/")

    # Download each language
    all_stats = {}
    t_start = time.time()

    for lang in langs:
        target = args.target_gb if args.target_gb else DEFAULT_TARGETS_GB.get(lang, 1.0)
        try:
            stats = download_lang(lang, target, resume=args.resume, dry_run=args.dry_run)
            all_stats[lang] = stats
        except KeyboardInterrupt:
            print(f"\n\n  Download interrupted at {lang}. Use --resume to continue.")
            break
        except Exception as e:
            print(f"\n  ERROR processing {lang}: {e}")
            all_stats[lang] = {"bytes_written": 0, "error": str(e)}

    total_time = time.time() - t_start

    # Final report
    print("\n" + "=" * 70)
    print("  Final Report")
    print("=" * 70)
    print(f"  {'Lang':>5} | {'Written':>10} | {'Samples':>12} | {'Dup%':>6} | {'Final':>10} | {'Time':>8}")
    print(f"  {'-'*5}-+-{'-'*10}-+-{'-'*12}-+-{'-'*6}-+-{'-'*10}-+-{'-'*8}")

    total_written = 0
    total_final = 0
    for lang in langs:
        s = all_stats.get(lang, {})
        if "error" in s:
            print(f"  {lang:>5} | {'ERROR':>10} | {s.get('error', '')}")
            continue
        written = s.get("bytes_written", 0)
        samples = s.get("samples", 0)
        dup_rate = s.get("dup_rate", 0)
        final = s.get("final_size", 0)
        elapsed = s.get("time_s", 0)
        total_written += written
        total_final += final
        print(f"  {lang:>5} | {written / 1e9:>9.2f}G | {samples:>12,} | {dup_rate:>5.1%} | "
              f"{final / 1e9:>9.2f}G | {elapsed / 60:>6.1f}m")

    print(f"  {'-'*5}-+-{'-'*10}-+-{'-'*12}-+-{'-'*6}-+-{'-'*10}-+-{'-'*8}")
    print(f"  {'TOTAL':>5} | {total_written / 1e9:>9.2f}G | {'':>12} | {'':>6} | "
          f"{total_final / 1e9:>9.2f}G | {total_time / 60:>6.1f}m")
    print("=" * 70)


if __name__ == "__main__":
    main()
