#!/usr/bin/env python3
"""Build corpus_v11 from existing multilingual data sources.

Usage:
  python scripts/build_corpus_v11.py --target-size 800  # 800MB target
  python scripts/build_corpus_v11.py --dry-run           # calculate sizes only
  python scripts/build_corpus_v11.py --stats             # analyze existing data
  python scripts/build_corpus_v11.py --target-size 800 --ko 0.35 --en 0.35 --code 0.15 --zh 0.08 --ja 0.04 --ru 0.03
"""
from __future__ import annotations

import argparse
import hashlib
import os
import random
import re
import struct
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent / "data"
MULTILINGUAL_DIR = DATA_DIR / "corpus_multilingual"
OUTPUT_DEFAULT = DATA_DIR / "corpus_v11.txt"

# ── Default language ratios (configurable via CLI) ─────────────────────────────
# ko+en dominant, code meaningful, zh/ja/ru supplementary
DEFAULT_RATIOS = {
    "ko":   0.40,
    "en":   0.40,
    "code": 0.20,
}

# Extended ratios (6-lang mode)
EXTENDED_RATIOS = {
    "ko":   0.30,
    "en":   0.30,
    "code": 0.15,
    "zh":   0.10,
    "ja":   0.08,
    "ru":   0.07,
}

# ── Data source registry ──────────────────────────────────────────────────────
SOURCES = {
    "ko":   MULTILINGUAL_DIR / "ko.txt",
    "en":   MULTILINGUAL_DIR / "en.txt",
    "code": MULTILINGUAL_DIR / "code.txt",
    "zh":   MULTILINGUAL_DIR / "zh.txt",
    "ja":   MULTILINGUAL_DIR / "ja.txt",
    "ru":   MULTILINGUAL_DIR / "ru.txt",
}

# Fallback: corpus_v10 can supplement ko if multilingual sources are absent
FALLBACK_SOURCES = {
    "ko": [DATA_DIR / "corpus_v10_ko.txt", DATA_DIR / "corpus_v10.txt"],
}

# ── Block-based sampling parameters ──────────────────────────────────────────
BLOCK_SIZE = 100        # lines per block (respect paragraph boundaries)
SHUFFLE_SEED = 42
DEDUP_JACCARD = 0.80    # trigram Jaccard threshold for dedup
DEDUP_SAMPLE = 500_000  # max lines to dedup (memory limit)

# ── Korean detection ──────────────────────────────────────────────────────────
_HANGUL_RE = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_KANA_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
_CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")


def detect_lang_ratio(text: str) -> dict[str, float]:
    """Estimate language composition from character distributions."""
    if not text:
        return {}
    total = len(text)
    hangul = len(_HANGUL_RE.findall(text))
    cjk = len(_CJK_RE.findall(text))
    kana = len(_KANA_RE.findall(text))
    cyrillic = len(_CYRILLIC_RE.findall(text))
    ascii_alpha = sum(1 for c in text if c.isascii() and c.isalpha())
    code_chars = sum(1 for c in text if c in "{}();=<>[]#//")
    return {
        "ko": hangul / total,
        "zh": cjk / total,
        "ja": kana / total,
        "ru": cyrillic / total,
        "en": ascii_alpha / total,
        "code": code_chars / total,
    }


def fmt_size(n_bytes: int | float) -> str:
    """Human-readable file size."""
    if n_bytes >= 1 << 30:
        return f"{n_bytes / (1 << 30):.2f} GB"
    if n_bytes >= 1 << 20:
        return f"{n_bytes / (1 << 20):.1f} MB"
    if n_bytes >= 1 << 10:
        return f"{n_bytes / (1 << 10):.1f} KB"
    return f"{n_bytes} B"


def file_size(path: Path) -> int:
    """File size in bytes, 0 if missing."""
    try:
        return path.stat().st_size
    except FileNotFoundError:
        return 0


def resolve_source(lang: str) -> Path | None:
    """Find the best available source file for a language."""
    primary = SOURCES.get(lang)
    if primary and primary.exists() and file_size(primary) > 0:
        return primary
    for fb in FALLBACK_SOURCES.get(lang, []):
        if fb.exists() and file_size(fb) > 0:
            return fb
    return None


# ── Trigram dedup ─────────────────────────────────────────────────────────────
def trigram_set(text: str) -> set[str]:
    """Extract character trigrams from text."""
    text = text.strip().lower()
    if len(text) < 3:
        return set()
    return {text[i:i+3] for i in range(len(text) - 2)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ── Block reader ──────────────────────────────────────────────────────────────
def read_blocks(path: Path, target_bytes: int, block_size: int, rng: random.Random) -> list[str]:
    """Read file in blocks, randomly sample to reach target_bytes.

    Strategy: scan file line counts, compute how many blocks needed,
    then reservoir-sample block indices for memory efficiency.
    """
    total_size = file_size(path)
    if total_size == 0:
        return []

    # If file is smaller than target, use everything
    if total_size <= target_bytes:
        print(f"    [INFO] Source ({fmt_size(total_size)}) <= target ({fmt_size(target_bytes)}), using all")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.readlines()

    # Estimate bytes per line from first 10K lines
    sample_lines = []
    sample_bytes = 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, line in enumerate(f):
            if i >= 10_000:
                break
            sample_lines.append(len(line.encode("utf-8")))
            sample_bytes += len(line.encode("utf-8"))

    if not sample_lines:
        return []

    avg_bytes_per_line = sample_bytes / len(sample_lines)
    est_total_lines = int(total_size / avg_bytes_per_line)
    lines_needed = int(target_bytes / avg_bytes_per_line)
    blocks_total = max(1, est_total_lines // block_size)
    blocks_needed = max(1, lines_needed // block_size)

    print(f"    Est lines: {est_total_lines:,}, need: {lines_needed:,} "
          f"({blocks_needed}/{blocks_total} blocks)")

    # Select random block indices
    if blocks_needed >= blocks_total:
        selected = set(range(blocks_total))
    else:
        selected = set(rng.sample(range(blocks_total), blocks_needed))

    # Stream through file, collecting selected blocks
    result = []
    collected_bytes = 0
    current_block = 0
    line_in_block = 0

    t0 = time.time()
    last_report = t0

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f):
            current_block = line_num // block_size
            if current_block in selected:
                result.append(line)
                collected_bytes += len(line.encode("utf-8"))

            # Progress every 5s
            now = time.time()
            if now - last_report > 5.0:
                pct = min(100, line_num / max(1, est_total_lines) * 100)
                print(f"    [{pct:5.1f}%] {line_num:,} lines, {fmt_size(collected_bytes)} collected",
                      flush=True)
                last_report = now

            # Early exit if we have enough
            if collected_bytes >= target_bytes * 1.05:
                break

    elapsed = time.time() - t0
    print(f"    Collected {len(result):,} lines ({fmt_size(collected_bytes)}) in {elapsed:.1f}s")
    return result


# ── Dedup pass ────────────────────────────────────────────────────────────────
def dedup_lines(lines: list[str], threshold: float = DEDUP_JACCARD,
                max_check: int = DEDUP_SAMPLE) -> tuple[list[str], int]:
    """Remove near-duplicate lines using trigram Jaccard similarity.

    For memory efficiency, only dedup within a sliding window.
    Returns (deduplicated lines, count removed).
    """
    if not lines:
        return lines, 0

    print(f"  Dedup: {len(lines):,} lines (Jaccard > {threshold})")
    t0 = time.time()

    # Build trigram fingerprints (hash-based for memory)
    seen_hashes: set[int] = set()
    result = []
    removed = 0
    window_trigrams: list[tuple[int, set[str]]] = []  # (hash, trigrams)
    WINDOW = 50  # compare against last N unique lines

    for i, line in enumerate(lines):
        stripped = line.strip()
        if len(stripped) < 10:
            # Keep short lines (separators, etc.) without dedup
            result.append(line)
            continue

        # Quick exact-hash dedup
        h = hash(stripped)
        if h in seen_hashes:
            removed += 1
            continue
        seen_hashes.add(h)

        # Trigram similarity check against window
        tg = trigram_set(stripped)
        is_dup = False
        for _, prev_tg in window_trigrams[-WINDOW:]:
            if jaccard(tg, prev_tg) > threshold:
                is_dup = True
                removed += 1
                break

        if not is_dup:
            result.append(line)
            window_trigrams.append((h, tg))
            # Trim window memory
            if len(window_trigrams) > WINDOW * 2:
                window_trigrams = window_trigrams[-WINDOW:]

        # Progress
        if (i + 1) % 500_000 == 0:
            print(f"    [{i+1:,}/{len(lines):,}] removed {removed:,}", flush=True)

    elapsed = time.time() - t0
    pct = removed / max(1, len(lines)) * 100
    print(f"    Removed {removed:,} ({pct:.1f}%) in {elapsed:.1f}s")
    return result, removed


# ── Validate ──────────────────────────────────────────────────────────────────
def validate_corpus(lines: list[str]) -> dict:
    """Validate corpus quality: UTF-8, language ratios, diversity."""
    total_bytes = sum(len(l.encode("utf-8")) for l in lines)
    total_lines = len(lines)

    # Sample 10K lines for language detection
    sample_size = min(10_000, total_lines)
    rng = random.Random(SHUFFLE_SEED)
    sample_indices = rng.sample(range(total_lines), sample_size) if total_lines > sample_size else range(total_lines)
    sample_text = "".join(lines[i] for i in sample_indices)
    lang_ratios = detect_lang_ratio(sample_text)

    # Trigram diversity on sample
    all_trigrams: set[str] = set()
    for i in sample_indices:
        all_trigrams |= trigram_set(lines[i].strip())
    trigram_unique = len(all_trigrams)

    # UTF-8 validity check (already loaded as str, so valid)
    # Check for null bytes or control chars
    bad_lines = 0
    for i in range(min(10_000, total_lines)):
        if "\x00" in lines[i]:
            bad_lines += 1

    return {
        "total_bytes": total_bytes,
        "total_lines": total_lines,
        "lang_ratios": lang_ratios,
        "trigram_unique": trigram_unique,
        "bad_lines": bad_lines,
    }


# ── Stats mode ────────────────────────────────────────────────────────────────
def show_stats():
    """Show statistics of existing data sources."""
    print("=" * 70)
    print("  corpus_v11 -- Data Source Analysis")
    print("=" * 70)

    total = 0
    for lang, path in sorted(SOURCES.items()):
        sz = file_size(path)
        total += sz
        status = "OK" if sz > 0 else "MISSING"
        print(f"  {lang:6s}  {fmt_size(sz):>10s}  {str(path):50s}  [{status}]")

    print(f"  {'':6s}  {'─' * 10}")
    print(f"  {'TOTAL':6s}  {fmt_size(total):>10s}")
    print()

    # Fallbacks
    print("  Fallback sources:")
    for lang, paths in FALLBACK_SOURCES.items():
        for p in paths:
            sz = file_size(p)
            if sz > 0:
                print(f"    {lang}: {p.name} ({fmt_size(sz)})")
    print()

    # Existing corpus versions
    print("  Existing corpus files:")
    for p in sorted(DATA_DIR.glob("corpus_v*.txt")):
        sz = file_size(p)
        print(f"    {p.name:40s}  {fmt_size(sz):>10s}")
    print()


# ── Dry run ───────────────────────────────────────────────────────────────────
def dry_run(target_mb: float, ratios: dict[str, float]):
    """Calculate expected sizes without reading files."""
    target_bytes = int(target_mb * 1024 * 1024)
    print("=" * 70)
    print(f"  corpus_v11 -- Dry Run (target: {fmt_size(target_bytes)})")
    print("=" * 70)
    print()

    # Normalize ratios
    total_ratio = sum(ratios.values())
    ratios = {k: v / total_ratio for k, v in ratios.items()}

    print(f"  {'Lang':6s}  {'Ratio':>7s}  {'Target':>10s}  {'Available':>10s}  {'Status':10s}")
    print(f"  {'─' * 6}  {'─' * 7}  {'─' * 10}  {'─' * 10}  {'─' * 10}")

    feasible = True
    for lang, ratio in sorted(ratios.items(), key=lambda x: -x[1]):
        needed = int(target_bytes * ratio)
        source = resolve_source(lang)
        available = file_size(source) if source else 0
        if available >= needed:
            status = "OK"
        elif available > 0:
            status = f"PARTIAL ({available * 100 // needed}%)"
        else:
            status = "MISSING"
            feasible = False
        print(f"  {lang:6s}  {ratio:6.1%}  {fmt_size(needed):>10s}  {fmt_size(available):>10s}  {status}")

    print()
    if feasible:
        print("  >> All sources available. Ready to build.")
    else:
        print("  >> Some sources missing. Build will use available data only.")
    print()


# ── Build ─────────────────────────────────────────────────────────────────────
def build_corpus(target_mb: float, ratios: dict[str, float], output: Path,
                 seed: int = SHUFFLE_SEED, skip_dedup: bool = False):
    """Build corpus_v11 from multilingual sources."""
    target_bytes = int(target_mb * 1024 * 1024)
    rng = random.Random(seed)
    t_start = time.time()

    print("=" * 70)
    print(f"  corpus_v11 Builder")
    print(f"  Target: {fmt_size(target_bytes)}  Seed: {seed}")
    print("=" * 70)
    print()

    # Normalize ratios
    total_ratio = sum(ratios.values())
    ratios = {k: v / total_ratio for k, v in ratios.items()}

    # Phase 1: Sample from each source
    print("Phase 1: Sampling from sources")
    print("-" * 50)
    all_lines: list[str] = []
    per_lang_stats: dict[str, dict] = {}

    for lang, ratio in sorted(ratios.items(), key=lambda x: -x[1]):
        needed = int(target_bytes * ratio)
        source = resolve_source(lang)
        if not source:
            print(f"  [{lang}] SKIP -- no source available")
            per_lang_stats[lang] = {"needed": needed, "got": 0, "source": "none"}
            continue

        print(f"  [{lang}] {fmt_size(needed)} from {source.name} ({fmt_size(file_size(source))})")
        lines = read_blocks(source, needed, BLOCK_SIZE, rng)
        got_bytes = sum(len(l.encode("utf-8")) for l in lines)
        all_lines.extend(lines)
        per_lang_stats[lang] = {"needed": needed, "got": got_bytes, "source": source.name}
        print(f"    Got {fmt_size(got_bytes)} ({len(lines):,} lines)")
        print()

    if not all_lines:
        print("[ERROR] No data collected. Check source files.")
        sys.exit(1)

    # Phase 2: Block shuffle
    print("Phase 2: Block shuffle")
    print("-" * 50)
    n_blocks = max(1, len(all_lines) // BLOCK_SIZE)
    blocks = [all_lines[i*BLOCK_SIZE:(i+1)*BLOCK_SIZE] for i in range(n_blocks)]
    # Include remainder
    remainder = all_lines[n_blocks * BLOCK_SIZE:]
    if remainder:
        blocks.append(remainder)
    rng.shuffle(blocks)
    all_lines = [line for block in blocks for line in block]
    print(f"  Shuffled {len(blocks):,} blocks ({len(all_lines):,} lines)")
    print()

    # Phase 3: Dedup
    removed = 0
    if not skip_dedup:
        print("Phase 3: Deduplication")
        print("-" * 50)
        all_lines, removed = dedup_lines(all_lines, DEDUP_JACCARD)
        print()
    else:
        print("Phase 3: Dedup SKIPPED (--skip-dedup)")
        print()

    # Phase 4: Validate
    print("Phase 4: Validation")
    print("-" * 50)
    val = validate_corpus(all_lines)
    print(f"  Total: {fmt_size(val['total_bytes'])} ({val['total_lines']:,} lines)")
    print(f"  Language ratios (sample):")
    for lang, ratio in sorted(val["lang_ratios"].items(), key=lambda x: -x[1]):
        if ratio > 0.01:
            print(f"    {lang:6s}: {ratio:6.1%}")
    print(f"  Trigram unique: {val['trigram_unique']:,}")
    print(f"  Bad lines: {val['bad_lines']}")
    print()

    # Phase 5: Write output
    print("Phase 5: Writing output")
    print("-" * 50)
    output.parent.mkdir(parents=True, exist_ok=True)
    t_write = time.time()
    with open(output, "w", encoding="utf-8") as f:
        for i, line in enumerate(all_lines):
            f.write(line)
            if (i + 1) % 1_000_000 == 0:
                print(f"  [{i+1:,}/{len(all_lines):,}] written", flush=True)
    write_elapsed = time.time() - t_write
    final_size = file_size(output)
    print(f"  Written: {output}")
    print(f"  Size: {fmt_size(final_size)} in {write_elapsed:.1f}s")
    print()

    # Phase 6: Report
    total_elapsed = time.time() - t_start
    print("=" * 70)
    print("  BUILD REPORT")
    print("=" * 70)
    print(f"  Output:      {output}")
    print(f"  Final size:  {fmt_size(final_size)} (target: {fmt_size(target_bytes)})")
    print(f"  Lines:       {val['total_lines']:,}")
    print(f"  Dedup:       {removed:,} removed")
    print(f"  Time:        {total_elapsed:.1f}s")
    print()
    print(f"  {'Lang':6s}  {'Target':>10s}  {'Got':>10s}  {'%':>6s}  {'Source'}")
    print(f"  {'─' * 6}  {'─' * 10}  {'─' * 10}  {'─' * 6}  {'─' * 20}")
    for lang in sorted(per_lang_stats.keys()):
        s = per_lang_stats[lang]
        pct = s["got"] / max(1, s["needed"]) * 100
        print(f"  {lang:6s}  {fmt_size(s['needed']):>10s}  {fmt_size(s['got']):>10s}  {pct:5.1f}%  {s['source']}")
    print()
    print(f"  Detected language distribution:")
    for lang, ratio in sorted(val["lang_ratios"].items(), key=lambda x: -x[1]):
        bar = "#" * int(ratio * 50)
        if ratio > 0.01:
            print(f"    {lang:6s} {bar} {ratio:.1%}")
    print()

    # MD5 for reproducibility
    md5 = hashlib.md5()
    with open(output, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    print(f"  MD5: {md5.hexdigest()}")
    print("=" * 70)


# ── CLI ───────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build corpus_v11 from multilingual data sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build_corpus_v11.py --stats                         # analyze sources
  python build_corpus_v11.py --dry-run                       # check feasibility
  python build_corpus_v11.py --target-size 800               # build 800MB (ko40/en40/code20)
  python build_corpus_v11.py --target-size 1000 --6lang      # 1GB with 6 languages
  python build_corpus_v11.py --target-size 500 --ko 0.5 --en 0.3 --code 0.2
        """,
    )
    p.add_argument("--stats", action="store_true", help="Show data source statistics")
    p.add_argument("--dry-run", action="store_true", help="Calculate sizes without building")
    p.add_argument("--target-size", type=float, default=800, help="Target size in MB (default: 800)")
    p.add_argument("--output", type=str, default=None, help="Output path (default: data/corpus_v11.txt)")
    p.add_argument("--seed", type=int, default=SHUFFLE_SEED, help="Random seed (default: 42)")
    p.add_argument("--skip-dedup", action="store_true", help="Skip deduplication pass")

    # Language ratios
    p.add_argument("--6lang", action="store_true", dest="six_lang",
                   help="Use 6-language mode (ko/en/code/zh/ja/ru)")
    p.add_argument("--ko", type=float, default=None, help="Korean ratio")
    p.add_argument("--en", type=float, default=None, help="English ratio")
    p.add_argument("--code", type=float, default=None, help="Code ratio")
    p.add_argument("--zh", type=float, default=None, help="Chinese ratio")
    p.add_argument("--ja", type=float, default=None, help="Japanese ratio")
    p.add_argument("--ru", type=float, default=None, help="Russian ratio")

    return p.parse_args()


def build_ratios(args: argparse.Namespace) -> dict[str, float]:
    """Build language ratios from CLI args."""
    if args.six_lang:
        base = dict(EXTENDED_RATIOS)
    else:
        base = dict(DEFAULT_RATIOS)

    # Override with explicit values
    for lang in ["ko", "en", "code", "zh", "ja", "ru"]:
        val = getattr(args, lang, None)
        if val is not None:
            base[lang] = val

    # Remove zero-ratio languages
    return {k: v for k, v in base.items() if v > 0}


def main():
    args = parse_args()

    if args.stats:
        show_stats()
        return

    ratios = build_ratios(args)

    if args.dry_run:
        dry_run(args.target_size, ratios)
        return

    output = Path(args.output) if args.output else OUTPUT_DEFAULT
    build_corpus(
        target_mb=args.target_size,
        ratios=ratios,
        output=output,
        seed=args.seed,
        skip_dedup=args.skip_dedup,
    )


if __name__ == "__main__":
    main()
