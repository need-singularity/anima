#!/usr/bin/env python3
"""Multilingual corpus collection pipeline for AGI training.

Collects text from Wikipedia (5 languages) + code (local repos / The Stack)
and merges at target ratios from config/agi_requirements.json.

Target ratios:
  en 30% | ko 18% | code 15% | zh 15% | ja 12% | ru 10%

Sources:
  - Wikipedia: HuggingFace datasets (20231101.{lang})
  - Code: local ~/Dev repos (Python/JS/Rust/SQL/bash)
  - Existing: corpus_v10_ko.txt for Korean portion
  - Rust corpus-gen: consciousness-specific multilingual seeds

Output:
  corpus_multilingual_en.txt   (30%)
  corpus_multilingual_ko.txt   (18%)
  corpus_multilingual_code.txt (15%)
  corpus_multilingual_zh.txt   (15%)
  corpus_multilingual_ja.txt   (12%)
  corpus_multilingual_ru.txt   (10%)
  corpus_multilingual_merged.txt (all combined at ratio)

Usage:
  python scripts/collect_multilingual_corpus.py --size 100MB   # quick test
  python scripts/collect_multilingual_corpus.py --size 1GB     # initial test
  python scripts/collect_multilingual_corpus.py --size 10GB    # real training
  python scripts/collect_multilingual_corpus.py --size 100MB --sources wiki,local
  python scripts/collect_multilingual_corpus.py --size 100MB --lang en,ko
  python scripts/collect_multilingual_corpus.py --stats        # analyze existing corpus
  python scripts/collect_multilingual_corpus.py --dry-run      # show plan only

See: config/agi_requirements.json for ratios and requirements.
"""

import argparse
import glob
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Optional

# ── Constants ────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
ANIMA_DIR = PROJECT_ROOT / "anima"
DATA_DIR = ANIMA_DIR / "data"
CONFIG_PATH = ANIMA_DIR / "config" / "agi_requirements.json"
DEV_DIR = Path.home() / "Dev"

# Language → Wikipedia dataset name
WIKI_DATASETS = {
    "en": "20231101.en",
    "ko": "20231101.ko",
    "zh": "20231101.zh",
    "ja": "20231101.ja",
    "ru": "20231101.ru",
}

# Code file extensions to collect
CODE_EXTENSIONS = {
    "python": [".py"],
    "javascript": [".js", ".ts", ".jsx", ".tsx"],
    "rust": [".rs"],
    "sql": [".sql"],
    "bash": [".sh", ".bash"],
}

# Repos to skip (too large, binary, or irrelevant)
SKIP_REPOS = {
    "models", "checkpoints", "node_modules", ".git", "__pycache__",
    "target", "dist", "build", ".next", "venv", ".venv", "env",
}

# Minimum file size to include (skip trivial files)
MIN_FILE_BYTES = 100
# Maximum file size to include (skip huge generated files)
MAX_FILE_BYTES = 500_000  # 500KB


def parse_size(size_str: str) -> int:
    """Parse human-readable size string to bytes."""
    size_str = size_str.strip().upper()
    multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
    for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
        if size_str.endswith(suffix):
            return int(float(size_str[:-len(suffix)].strip()) * mult)
    return int(size_str)


def format_size(n_bytes: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(n_bytes) < 1024.0:
            return f"{n_bytes:.1f} {unit}"
        n_bytes /= 1024.0
    return f"{n_bytes:.1f} PB"


def load_config() -> dict:
    """Load language ratios from agi_requirements.json."""
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        ratios = {}
        for lang, info in cfg.get("languages", {}).items():
            ratios[lang] = info.get("corpus_ratio", 0.0)
        return ratios
    # Fallback hardcoded ratios
    return {"en": 0.30, "ko": 0.18, "code": 0.15, "zh": 0.15, "ja": 0.12, "ru": 0.10}


# ── Wikipedia Collector ──────────────────────────────────────────────

class WikipediaCollector:
    """Collect text from Wikipedia via HuggingFace datasets."""

    def __init__(self, lang: str, target_bytes: int):
        self.lang = lang
        self.target_bytes = target_bytes
        self.dataset_name = WIKI_DATASETS.get(lang)

    def collect(self, output_path: Path) -> int:
        """Download and write Wikipedia text. Returns bytes written."""
        if not self.dataset_name:
            print(f"  [SKIP] No Wikipedia dataset for '{self.lang}'")
            return 0

        try:
            from datasets import load_dataset
        except ImportError:
            print("  [ERROR] 'datasets' package not installed.")
            print("    pip install datasets")
            return 0

        print(f"  [WIKI] Loading wikipedia/{self.dataset_name} ...")
        print(f"         Target: {format_size(self.target_bytes)}")
        sys.stdout.flush()

        try:
            # Stream to avoid downloading entire dataset
            # Use wikimedia/wikipedia (new format) instead of deprecated "wikipedia"
            ds = load_dataset(
                "wikimedia/wikipedia",
                self.dataset_name,
                split="train",
                streaming=True,
            )
        except Exception as e:
            print(f"  [ERROR] Failed to load dataset: {e}")
            return self._fallback_collect(output_path)

        written = 0
        count = 0
        t0 = time.time()

        with open(output_path, "w", encoding="utf-8") as f:
            for article in ds:
                text = article.get("text", "")
                if not text or len(text) < 200:
                    continue

                # Clean: remove very short paragraphs, keep substance
                paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 50]
                if not paragraphs:
                    continue

                clean_text = "\n".join(paragraphs) + "\n\n"
                f.write(clean_text)
                written += len(clean_text.encode("utf-8"))
                count += 1

                if count % 1000 == 0:
                    elapsed = time.time() - t0
                    speed = written / (elapsed + 1e-9)
                    pct = min(100.0, 100.0 * written / self.target_bytes)
                    print(f"    {count:,} articles | {format_size(written)} | "
                          f"{pct:.1f}% | {format_size(int(speed))}/s")
                    sys.stdout.flush()

                if written >= self.target_bytes:
                    break

        elapsed = time.time() - t0
        print(f"  [DONE] {count:,} articles, {format_size(written)}, {elapsed:.1f}s")
        sys.stdout.flush()
        return written

    def _fallback_collect(self, output_path: Path) -> int:
        """Fallback: use Wikipedia API directly for smaller collections."""
        print(f"  [FALLBACK] Using Wikipedia API for {self.lang}...")
        sys.stdout.flush()

        try:
            import urllib.request
            import urllib.parse
            import json as _json
        except ImportError:
            return 0

        # MediaWiki API: get random articles
        # User-Agent header required (403 without it)
        api_base = f"https://{self.lang}.wikipedia.org/w/api.php"
        ua_headers = {"User-Agent": "AnimaCorpusCollector/1.0 (research project)"}
        written = 0
        count = 0

        with open(output_path, "w", encoding="utf-8") as f:
            while written < self.target_bytes:
                try:
                    # Get random page titles
                    url = (f"{api_base}?action=query&list=random&rnlimit=20"
                           f"&rnnamespace=0&format=json")
                    req = urllib.request.Request(url, headers=ua_headers)
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = _json.loads(resp.read())

                    titles = [p["title"] for p in data.get("query", {}).get("random", [])]
                    if not titles:
                        break

                    # Get article text (plain text extracts)
                    titles_param = "|".join(titles)
                    url = (f"{api_base}?action=query&titles={urllib.parse.quote(titles_param)}"
                           f"&prop=extracts&explaintext=1&exlimit=20&format=json")
                    req = urllib.request.Request(url, headers=ua_headers)
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = _json.loads(resp.read())

                    pages = data.get("query", {}).get("pages", {})
                    for page_id, page in pages.items():
                        text = page.get("extract", "")
                        if not text or len(text) < 200:
                            continue
                        f.write(text + "\n\n")
                        written += len(text.encode("utf-8"))
                        count += 1

                    if count % 50 == 0:
                        pct = min(100.0, 100.0 * written / self.target_bytes)
                        print(f"    {count} articles | {format_size(written)} | {pct:.1f}%")
                        sys.stdout.flush()

                except Exception as e:
                    print(f"    [WARN] API error: {e}")
                    break

        print(f"  [DONE] {count} articles via API, {format_size(written)}")
        return written


# ── Code Collector ───────────────────────────────────────────────────

class CodeCollector:
    """Collect code from local ~/Dev repos or HuggingFace The Stack."""

    def __init__(self, target_bytes: int, dev_dir: Path = DEV_DIR):
        self.target_bytes = target_bytes
        self.dev_dir = dev_dir

    def collect(self, output_path: Path, source: str = "local") -> int:
        """Collect code files. source: 'local', 'stack', or 'both'."""
        if source in ("local", "both"):
            written = self._collect_local(output_path)
            if written >= self.target_bytes:
                return written
        else:
            written = 0

        if source in ("stack", "both") and written < self.target_bytes:
            remaining = self.target_bytes - written
            written += self._collect_stack(output_path, remaining)

        return written

    def _collect_local(self, output_path: Path) -> int:
        """Scrape code from local ~/Dev repos."""
        print(f"  [CODE] Scanning {self.dev_dir} for code files ...")
        print(f"         Target: {format_size(self.target_bytes)}")
        sys.stdout.flush()

        # Gather all code files
        all_files = []
        if not self.dev_dir.exists():
            print(f"  [WARN] {self.dev_dir} does not exist")
            return 0

        for repo_dir in sorted(self.dev_dir.iterdir()):
            if not repo_dir.is_dir():
                continue
            if repo_dir.name in SKIP_REPOS or repo_dir.name.startswith("."):
                continue

            for lang_name, exts in CODE_EXTENSIONS.items():
                for ext in exts:
                    for fpath in repo_dir.rglob(f"*{ext}"):
                        # Skip dirs in SKIP_REPOS
                        parts = set(fpath.relative_to(self.dev_dir).parts)
                        if parts & SKIP_REPOS:
                            continue
                        try:
                            size = fpath.stat().st_size
                            if MIN_FILE_BYTES <= size <= MAX_FILE_BYTES:
                                all_files.append((fpath, lang_name, size))
                        except OSError:
                            continue

        print(f"  [CODE] Found {len(all_files):,} code files")
        sys.stdout.flush()

        if not all_files:
            return 0

        # Shuffle for diversity, then write
        random.shuffle(all_files)

        written = 0
        count = 0
        lang_counts = {}

        with open(output_path, "w", encoding="utf-8") as f:
            for fpath, lang_name, size in all_files:
                try:
                    text = fpath.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                if not text.strip():
                    continue

                # Add file header for context
                rel_path = fpath.relative_to(self.dev_dir)
                header = f"### FILE: {rel_path} [{lang_name}]\n"
                entry = header + text + "\n\n"

                f.write(entry)
                entry_bytes = len(entry.encode("utf-8"))
                written += entry_bytes
                count += 1
                lang_counts[lang_name] = lang_counts.get(lang_name, 0) + 1

                if count % 500 == 0:
                    pct = min(100.0, 100.0 * written / self.target_bytes)
                    print(f"    {count:,} files | {format_size(written)} | {pct:.1f}%")
                    sys.stdout.flush()

                if written >= self.target_bytes:
                    break

        breakdown = ", ".join(f"{k}={v}" for k, v in sorted(lang_counts.items()))
        print(f"  [DONE] {count:,} files, {format_size(written)} ({breakdown})")
        sys.stdout.flush()
        return written

    def _collect_stack(self, output_path: Path, target_bytes: int) -> int:
        """Collect from The Stack (HuggingFace) via streaming."""
        try:
            from datasets import load_dataset
        except ImportError:
            print("  [SKIP] 'datasets' not installed for The Stack")
            return 0

        print(f"  [STACK] Loading bigcode/the-stack-dedup (Python) ...")
        sys.stdout.flush()

        written = 0
        count = 0
        mode = "a" if output_path.exists() else "w"

        for lang_dir in ["data/python", "data/javascript", "data/rust"]:
            if written >= target_bytes:
                break
            try:
                ds = load_dataset(
                    "bigcode/the-stack-dedup",
                    data_dir=lang_dir,
                    split="train",
                    streaming=True,
                    trust_remote_code=True,
                )
                lang_label = lang_dir.split("/")[-1]
                with open(output_path, mode, encoding="utf-8") as f:
                    for sample in ds:
                        content = sample.get("content", "")
                        if not content or len(content) < 100:
                            continue
                        # Truncate very long files
                        if len(content) > MAX_FILE_BYTES:
                            content = content[:MAX_FILE_BYTES]
                        entry = f"### CODE [{lang_label}]\n{content}\n\n"
                        f.write(entry)
                        written += len(entry.encode("utf-8"))
                        count += 1
                        if written >= target_bytes:
                            break
                mode = "a"
            except Exception as e:
                print(f"  [WARN] Failed to load {lang_dir}: {e}")

        print(f"  [DONE] {count:,} stack files, {format_size(written)}")
        return written


# ── Existing Corpus Reuser ───────────────────────────────────────────

class ExistingCorpusReuser:
    """Reuse existing corpus files (e.g., corpus_v10_ko.txt)."""

    def __init__(self, lang: str, target_bytes: int):
        self.lang = lang
        self.target_bytes = target_bytes

    def collect(self, output_path: Path) -> int:
        """Copy from existing corpus files if available."""
        existing_files = self._find_existing()
        if not existing_files:
            return 0

        print(f"  [REUSE] Found {len(existing_files)} existing file(s) for '{self.lang}'")
        sys.stdout.flush()

        written = 0
        with open(output_path, "w", encoding="utf-8") as out_f:
            for src_path in existing_files:
                src_size = src_path.stat().st_size
                print(f"    Reading {src_path.name} ({format_size(src_size)})")
                sys.stdout.flush()

                with open(src_path, "r", encoding="utf-8", errors="replace") as in_f:
                    while written < self.target_bytes:
                        chunk = in_f.read(1024 * 1024)  # 1MB chunks
                        if not chunk:
                            break
                        out_f.write(chunk)
                        written += len(chunk.encode("utf-8"))

                if written >= self.target_bytes:
                    break

        print(f"  [DONE] Reused {format_size(written)} from existing corpus")
        return written

    def _find_existing(self) -> list:
        """Find existing corpus files for this language."""
        candidates = []
        if self.lang == "ko":
            paths = [
                DATA_DIR / "corpus_v10_ko.txt",
                DATA_DIR / "corpus_v4_multilingual.txt",
            ]
            for p in paths:
                if p.exists():
                    candidates.append(p)
        elif self.lang == "en":
            paths = [
                DATA_DIR / "corpus_v10.txt",
                DATA_DIR / "corpus_v6_wiki.txt",
                DATA_DIR / "corpus_v7_wiki_heavy.txt",
            ]
            for p in paths:
                if p.exists():
                    candidates.append(p)
        return candidates


# ── Rust corpus-gen Integration ──────────────────────────────────────

class RustCorpusGenCollector:
    """Use the Rust corpus-gen for consciousness-specific multilingual text."""

    def __init__(self, target_mb: int):
        self.target_mb = target_mb
        self.binary = ANIMA_DIR / "anima-rs" / "target" / "release" / "corpus-gen"

    def available(self) -> bool:
        return self.binary.exists()

    def collect(self, output_path: Path) -> int:
        """Run corpus-gen to generate multilingual consciousness text."""
        if not self.available():
            print(f"  [SKIP] corpus-gen binary not found at {self.binary}")
            print(f"         Build with: cd anima/anima-rs && cargo build --release -p anima-corpus-gen")
            return 0

        import subprocess
        print(f"  [RUST] Running corpus-gen -s {self.target_mb} ...")
        sys.stdout.flush()

        try:
            result = subprocess.run(
                [str(self.binary), "-s", str(self.target_mb), "-o", str(output_path)],
                capture_output=True, text=True, timeout=300,
                cwd=str(ANIMA_DIR),
            )
            if result.returncode == 0:
                size = output_path.stat().st_size if output_path.exists() else 0
                print(f"  [DONE] corpus-gen produced {format_size(size)}")
                return size
            else:
                print(f"  [WARN] corpus-gen failed: {result.stderr[:200]}")
                return 0
        except Exception as e:
            print(f"  [ERROR] corpus-gen: {e}")
            return 0


# ── Merger ───────────────────────────────────────────────────────────

class CorpusMerger:
    """Merge per-language corpus files at target ratios."""

    def __init__(self, ratios: dict, target_bytes: int):
        self.ratios = ratios
        self.target_bytes = target_bytes

    def merge(self, lang_files: dict, output_path: Path) -> int:
        """Merge language files into a single shuffled corpus.

        lang_files: {lang: Path} mapping
        """
        print(f"\n{'='*60}")
        print(f"MERGING → {output_path.name}")
        print(f"Target: {format_size(self.target_bytes)}")
        print(f"{'='*60}")
        sys.stdout.flush()

        # Calculate per-language target bytes
        lang_targets = {}
        for lang, ratio in self.ratios.items():
            lang_targets[lang] = int(self.target_bytes * ratio)

        # Read chunks from each language file
        chunks = []
        for lang, fpath in lang_files.items():
            if not fpath.exists():
                print(f"  [{lang}] MISSING - skipping")
                continue

            target = lang_targets.get(lang, 0)
            if target == 0:
                continue

            file_size = fpath.stat().st_size
            available = min(file_size, target)
            print(f"  [{lang}] {format_size(available)} / {format_size(target)} "
                  f"({100*available/target:.0f}%)")

            # Read in paragraph-sized chunks for good shuffling
            read_bytes = 0
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                buffer = []
                for line in f:
                    buffer.append(line)
                    if line.strip() == "" and len(buffer) > 3:
                        chunk = "".join(buffer)
                        chunk_bytes = len(chunk.encode("utf-8"))
                        if read_bytes + chunk_bytes > target:
                            # Write partial
                            remaining = target - read_bytes
                            if remaining > 100:
                                chunks.append(chunk[:remaining])
                                read_bytes += remaining
                            break
                        chunks.append(chunk)
                        read_bytes += chunk_bytes
                        buffer = []

                # Flush remaining buffer
                if buffer and read_bytes < target:
                    chunk = "".join(buffer)
                    chunks.append(chunk)
                    read_bytes += len(chunk.encode("utf-8"))

        print(f"\n  Total chunks: {len(chunks):,}")
        print(f"  Shuffling ...")
        sys.stdout.flush()

        # Shuffle for training
        random.shuffle(chunks)

        # Write merged file
        written = 0
        with open(output_path, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(chunk)
                written += len(chunk.encode("utf-8"))

        print(f"  MERGED: {format_size(written)}")
        sys.stdout.flush()
        return written


# ── Stats Analyzer ───────────────────────────────────────────────────

def analyze_corpus(path: Path):
    """Analyze language distribution of a corpus file."""
    if not path.exists():
        print(f"File not found: {path}")
        return

    file_size = path.stat().st_size
    print(f"\nAnalyzing: {path}")
    print(f"Size: {format_size(file_size)}")
    print()

    # Simple heuristic: count CJK / Cyrillic / Latin / code blocks
    ko_bytes = 0
    ja_bytes = 0
    zh_bytes = 0
    ru_bytes = 0
    code_bytes = 0
    en_bytes = 0
    total = 0

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            b = len(line.encode("utf-8"))
            total += b

            if line.startswith("### FILE:") or line.startswith("### CODE"):
                code_bytes += b
                continue

            has_hangul = any("\uAC00" <= c <= "\uD7A3" for c in line[:100])
            has_hiragana = any("\u3040" <= c <= "\u309F" for c in line[:100])
            has_katakana = any("\u30A0" <= c <= "\u30FF" for c in line[:100])
            has_cjk = any("\u4E00" <= c <= "\u9FFF" for c in line[:100])
            has_cyrillic = any("\u0400" <= c <= "\u04FF" for c in line[:100])

            if has_hangul:
                ko_bytes += b
            elif has_hiragana or has_katakana:
                ja_bytes += b
            elif has_cjk:
                zh_bytes += b
            elif has_cyrillic:
                ru_bytes += b
            else:
                en_bytes += b

    print("Language Distribution:")
    print(f"  {'Lang':<8} {'Bytes':>12} {'Ratio':>8} {'Target':>8} {'Delta':>8}")
    print(f"  {'─'*52}")

    ratios = load_config()
    for lang, actual in [("en", en_bytes), ("ko", ko_bytes), ("code", code_bytes),
                          ("zh", zh_bytes), ("ja", ja_bytes), ("ru", ru_bytes)]:
        pct = 100 * actual / total if total > 0 else 0
        target_pct = 100 * ratios.get(lang, 0)
        delta = pct - target_pct
        sign = "+" if delta >= 0 else ""
        print(f"  {lang:<8} {format_size(actual):>12} {pct:>7.1f}% {target_pct:>7.1f}% {sign}{delta:>6.1f}%")

    other = total - en_bytes - ko_bytes - code_bytes - zh_bytes - ja_bytes - ru_bytes
    if other > 0:
        print(f"  {'other':<8} {format_size(other):>12} {100*other/total:>7.1f}%")
    print(f"  {'─'*52}")
    print(f"  {'TOTAL':<8} {format_size(total):>12}")


# ── Main Pipeline ────────────────────────────────────────────────────

def run_pipeline(args):
    """Execute the collection pipeline."""
    ratios = load_config()
    target_bytes = parse_size(args.size)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter languages if specified
    if args.lang:
        selected = set(args.lang.split(","))
        ratios = {k: v for k, v in ratios.items() if k in selected}
        # Re-normalize ratios
        total_ratio = sum(ratios.values())
        if total_ratio > 0:
            ratios = {k: v / total_ratio for k, v in ratios.items()}

    sources = set(args.sources.split(",")) if args.sources else {"wiki", "local", "existing", "rust"}

    print(f"{'='*60}")
    print(f"MULTILINGUAL CORPUS COLLECTION PIPELINE")
    print(f"{'='*60}")
    print(f"  Target size:  {format_size(target_bytes)}")
    print(f"  Output dir:   {output_dir}")
    print(f"  Sources:      {', '.join(sorted(sources))}")
    print(f"  Languages:    {', '.join(f'{k} ({v:.0%})' for k, v in ratios.items())}")
    print(f"{'='*60}")
    print()
    sys.stdout.flush()

    if args.dry_run:
        print("[DRY RUN] Would collect:")
        for lang, ratio in ratios.items():
            lang_bytes = int(target_bytes * ratio)
            print(f"  {lang:<6} {format_size(lang_bytes):>10} ({ratio:.0%})")
        print(f"\n  Total: {format_size(target_bytes)}")
        return

    lang_files = {}
    t0 = time.time()

    for lang, ratio in ratios.items():
        lang_bytes = int(target_bytes * ratio)
        lang_path = output_dir / f"corpus_multilingual_{lang}.txt"
        lang_files[lang] = lang_path

        print(f"\n{'─'*60}")
        print(f"[{lang.upper()}] Target: {format_size(lang_bytes)} ({ratio:.0%})")
        print(f"{'─'*60}")
        sys.stdout.flush()

        written = 0

        # Strategy 1: Reuse existing corpus
        if "existing" in sources and lang in ("ko", "en"):
            reuser = ExistingCorpusReuser(lang, lang_bytes)
            written = reuser.collect(lang_path)

        # Strategy 2: Code from local repos
        if lang == "code" and "local" in sources:
            collector = CodeCollector(lang_bytes, DEV_DIR)
            written = collector.collect(lang_path, source="local")

            # Supplement with The Stack if needed and requested
            if written < lang_bytes and "stack" in sources:
                remaining = lang_bytes - written
                collector2 = CodeCollector(remaining, DEV_DIR)
                written += collector2._collect_stack(lang_path, remaining)

        # Strategy 3: Rust corpus-gen (consciousness multilingual seeds)
        if written < lang_bytes and "rust" in sources and lang != "code":
            rust_gen = RustCorpusGenCollector(max(1, (lang_bytes - written) // (1024 * 1024)))
            if rust_gen.available():
                rust_path = output_dir / f"_rust_gen_{lang}.txt"
                rust_bytes = rust_gen.collect(rust_path)
                if rust_bytes > 0 and rust_path.exists():
                    # Append to main file
                    mode = "a" if lang_path.exists() and written > 0 else "w"
                    with open(lang_path, mode, encoding="utf-8") as out_f:
                        with open(rust_path, "r", encoding="utf-8") as in_f:
                            data = in_f.read()
                            out_f.write(data)
                            written += len(data.encode("utf-8"))
                    rust_path.unlink()

        # Strategy 4: Wikipedia (primary source for new data)
        if written < lang_bytes and "wiki" in sources and lang != "code":
            remaining = lang_bytes - written
            wiki = WikipediaCollector(lang, remaining)
            mode = "a" if lang_path.exists() and written > 0 else "w"
            if written > 0:
                # Append mode: write to temp, then append
                tmp_path = output_dir / f"_wiki_tmp_{lang}.txt"
                wiki_bytes = wiki.collect(tmp_path)
                if wiki_bytes > 0 and tmp_path.exists():
                    with open(lang_path, "a", encoding="utf-8") as out_f:
                        with open(tmp_path, "r", encoding="utf-8") as in_f:
                            out_f.write(in_f.read())
                    written += wiki_bytes
                    tmp_path.unlink()
            else:
                written = wiki.collect(lang_path)

        # Report
        actual = lang_path.stat().st_size if lang_path.exists() else 0
        fill_pct = 100 * actual / lang_bytes if lang_bytes > 0 else 0
        status = "OK" if fill_pct >= 80 else "LOW" if fill_pct >= 20 else "EMPTY"
        print(f"\n  [{lang.upper()}] {status}: {format_size(actual)} / "
              f"{format_size(lang_bytes)} ({fill_pct:.0f}%)")
        sys.stdout.flush()

    # Merge all languages
    merged_path = output_dir / "corpus_multilingual_merged.txt"
    merger = CorpusMerger(ratios, target_bytes)
    total_written = merger.merge(lang_files, merged_path)

    # Final report
    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"COLLECTION COMPLETE")
    print(f"{'='*60}")
    print(f"  Time:     {elapsed:.1f}s")
    print(f"  Merged:   {format_size(total_written)}")
    print(f"  Output:   {merged_path}")
    print()
    print(f"  Per-language files:")
    for lang, fpath in lang_files.items():
        if fpath.exists():
            size = fpath.stat().st_size
            pct = 100 * size / total_written if total_written > 0 else 0
            print(f"    {fpath.name:<40} {format_size(size):>10} ({pct:.1f}%)")
        else:
            print(f"    {fpath.name:<40} {'MISSING':>10}")
    print(f"{'='*60}")
    print()
    print(f"Next steps:")
    print(f"  1. Analyze: python scripts/collect_multilingual_corpus.py --stats --input {merged_path}")
    print(f"  2. Train tokenizer: python scripts/train_tokenizer.py --input {merged_path}")
    print(f"  3. Train model: python anima/training/train_v14.py --data {merged_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Multilingual corpus collection pipeline for AGI training",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --size 100MB                      # Quick test (100MB)
  %(prog)s --size 1GB                        # Initial test (1GB)
  %(prog)s --size 10GB                       # Real training (10GB)
  %(prog)s --size 100MB --sources wiki,local  # Wiki + local code only
  %(prog)s --size 100MB --lang en,ko          # English + Korean only
  %(prog)s --stats --input merged.txt         # Analyze existing corpus
  %(prog)s --dry-run --size 1GB               # Show plan only
        """,
    )

    parser.add_argument("--size", default="100MB",
                        help="Target corpus size (e.g., 100MB, 1GB, 10GB)")
    parser.add_argument("--output-dir", default=str(DATA_DIR),
                        help=f"Output directory (default: {DATA_DIR})")
    parser.add_argument("--sources", default=None,
                        help="Comma-separated sources: wiki,local,stack,existing,rust")
    parser.add_argument("--lang", default=None,
                        help="Comma-separated languages: en,ko,zh,ja,ru,code")
    parser.add_argument("--stats", action="store_true",
                        help="Analyze existing corpus file")
    parser.add_argument("--input", default=None,
                        help="Input file for --stats analysis")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show collection plan without downloading")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")

    args = parser.parse_args()
    random.seed(args.seed)

    if args.stats:
        input_path = Path(args.input) if args.input else DATA_DIR / "corpus_multilingual_merged.txt"
        analyze_corpus(input_path)
        return

    run_pipeline(args)


if __name__ == "__main__":
    main()
