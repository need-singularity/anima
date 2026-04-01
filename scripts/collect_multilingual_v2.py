#!/usr/bin/env python3
"""Multilingual corpus collector v2 — actually works.

Collects 100MB+ per category: en, ko, zh, ja, ru, code.
Uses local data where available, Wikipedia API with proper headers for the rest.

Output: /Users/ghost/Dev/anima/anima/data/corpus_multilingual/
"""

import json
import os
import random
import sys
import time
import urllib.request
import urllib.parse
import concurrent.futures
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────────
DATA_DIR = Path("/Users/ghost/Dev/anima/anima/data")
OUT_DIR = DATA_DIR / "corpus_multilingual"
DEV_DIR = Path.home() / "Dev"

TARGET_BYTES = {
    "en": 300 * 1024 * 1024,   # 300MB
    "ko": 200 * 1024 * 1024,   # 200MB
    "zh": 200 * 1024 * 1024,   # 200MB
    "ja": 200 * 1024 * 1024,   # 200MB
    "ru": 200 * 1024 * 1024,   # 200MB
    "code": 200 * 1024 * 1024, # 200MB
}
TOTAL_TARGET = sum(TARGET_BYTES.values())  # ~1.3GB new + existing 600MB ≈ 2GB

WIKI_UA = "AnimaCorpusCollector/2.0 (https://github.com/need-singularity/anima; research project)"

CODE_EXTS = {
    "python": [".py"],
    "javascript": [".js", ".ts", ".jsx", ".tsx"],
    "rust": [".rs"],
    "sql": [".sql"],
    "bash": [".sh"],
    "go": [".go"],
    "c": [".c", ".h"],
    "toml": [".toml"],
    "yaml": [".yml", ".yaml"],
    "json_sample": [".json"],
}

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "target", "dist", "build",
    ".next", "venv", ".venv", "env", "models", "checkpoints", ".cache",
    "site-packages", ".mypy_cache", ".pytest_cache", "coverage",
    ".tox", "egg-info", ".eggs",
}


def fmt(n):
    """Format bytes."""
    for u in ["B", "KB", "MB", "GB"]:
        if abs(n) < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}TB"


def progress(current, total, label="", extra=""):
    pct = 100 * current / max(total, 1)
    bar_len = 30
    filled = int(bar_len * current / max(total, 1))
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"\r  [{bar}] {pct:5.1f}% {fmt(current):>10}/{fmt(total)} {label} {extra}", end="", flush=True)


# ── 1. Korean: copy from corpus_v10_ko.txt ──────────────────────────

def collect_korean(out_path, target):
    """Extract Korean text from corpus_v10_ko.txt — appends to existing file."""
    existing = out_path.stat().st_size if out_path.exists() else 0
    remaining = target - existing
    if remaining <= 0:
        print(f"  [SKIP] Already {fmt(existing)} >= target {fmt(target)}")
        return existing

    src = DATA_DIR / "corpus_v10_ko.txt"
    if not src.exists():
        print(f"  [ERROR] {src} not found")
        return existing

    print(f"  Source: {src} ({fmt(src.stat().st_size)})")
    print(f"  Existing: {fmt(existing)}, need {fmt(remaining)} more")
    sys.stdout.flush()

    written = 0
    lines_total = 0
    lines_kept = 0

    with open(out_path, "a", encoding="utf-8") as out_f:
        with open(src, "r", encoding="utf-8", errors="replace") as in_f:
            buf = []
            for line in in_f:
                lines_total += 1
                has_korean = any("\uAC00" <= c <= "\uD7A3" for c in line[:200])
                if has_korean or (buf and line.strip() == ""):
                    buf.append(line)
                    if line.strip() == "" and buf:
                        chunk = "".join(buf)
                        chunk_bytes = len(chunk.encode("utf-8"))
                        out_f.write(chunk)
                        written += chunk_bytes
                        lines_kept += len(buf)
                        buf = []
                        if written >= remaining:
                            break
                        if lines_total % 50000 == 0:
                            progress(existing + written, target, "ko")
                else:
                    if buf:
                        chunk = "".join(buf)
                        out_f.write(chunk)
                        written += len(chunk.encode("utf-8"))
                        buf = []

            if buf and written < remaining:
                chunk = "".join(buf)
                out_f.write(chunk)
                written += len(chunk.encode("utf-8"))

    if written < remaining:
        print(f"\n  Korean-filtered: {fmt(written)}, padding with full file...")
        still_need = remaining - written
        with open(out_path, "a", encoding="utf-8") as out_f:
            with open(src, "r", encoding="utf-8", errors="replace") as in_f:
                while still_need > 0:
                    chunk = in_f.read(1024 * 1024)
                    if not chunk:
                        break
                    out_f.write(chunk)
                    still_need -= len(chunk.encode("utf-8"))
                    written = remaining - still_need

    total = existing + written
    print(f"\n  [DONE] ko: {fmt(total)} (+{fmt(written)} appended)")
    return total


# ── 2. English: extract from corpus_v10.txt ─────────────────────────

def collect_english(out_path, target):
    """Extract English text from corpus_v10.txt — appends to existing file."""
    existing = out_path.stat().st_size if out_path.exists() else 0
    remaining = target - existing
    if remaining <= 0:
        print(f"  [SKIP] Already {fmt(existing)} >= target {fmt(target)}")
        return existing

    src = DATA_DIR / "corpus_v10.txt"
    if not src.exists():
        print(f"  [ERROR] {src} not found")
        return existing

    print(f"  Source: {src} ({fmt(src.stat().st_size)})")
    print(f"  Existing: {fmt(existing)}, need {fmt(remaining)} more")
    sys.stdout.flush()

    written = 0
    with open(out_path, "a", encoding="utf-8") as out_f:
        with open(src, "r", encoding="utf-8", errors="replace") as in_f:
            buf = []
            count = 0
            for line in in_f:
                count += 1
                ascii_count = sum(1 for c in line[:200] if ord(c) < 128)
                is_english = (ascii_count / max(len(line[:200]), 1)) > 0.7

                if is_english or line.strip() == "":
                    buf.append(line)
                    if line.strip() == "" and len(buf) > 2:
                        chunk = "".join(buf)
                        out_f.write(chunk)
                        written += len(chunk.encode("utf-8"))
                        buf = []
                        if written >= remaining:
                            break
                else:
                    if buf:
                        chunk = "".join(buf)
                        out_f.write(chunk)
                        written += len(chunk.encode("utf-8"))
                        buf = []

                if count % 50000 == 0:
                    progress(existing + written, target, "en")

            if buf:
                chunk = "".join(buf)
                out_f.write(chunk)
                written += len(chunk.encode("utf-8"))

    # Supplement from other corpus files if needed
    if written < remaining:
        for extra_src in [DATA_DIR / "corpus_v9.txt", DATA_DIR / "corpus_v4.txt",
                          DATA_DIR / "corpus_v3_100mb.txt", DATA_DIR / "corpus_v5.txt",
                          DATA_DIR / "corpus_v6_wiki.txt", DATA_DIR / "corpus_v7_wiki_heavy.txt",
                          DATA_DIR / "corpus_v8_dialogue.txt", DATA_DIR / "corpus_v2v3_merged.txt",
                          DATA_DIR / "corpus_v2.txt"]:
            if not extra_src.exists() or written >= remaining:
                continue
            print(f"\n  Supplementing from {extra_src.name}...")
            with open(out_path, "a", encoding="utf-8") as out_f:
                with open(extra_src, "r", encoding="utf-8", errors="replace") as in_f:
                    while written < remaining:
                        chunk = in_f.read(1024 * 1024)
                        if not chunk:
                            break
                        out_f.write(chunk)
                        written += len(chunk.encode("utf-8"))

    total = existing + written
    print(f"\n  [DONE] en: {fmt(total)} (+{fmt(written)} appended)")
    return total


# ── 3. Code: scrape ~/Dev repos ─────────────────────────────────────

def collect_code(out_path, target):
    """Scrape code from local ~/Dev repos — appends to existing file."""
    existing = out_path.stat().st_size if out_path.exists() else 0
    remaining = target - existing
    if remaining <= 0:
        print(f"  [SKIP] Already {fmt(existing)} >= target {fmt(target)}")
        return existing

    print(f"  Existing: {fmt(existing)}, need {fmt(remaining)} more")
    print(f"  Scanning {DEV_DIR} (deep scan)...")
    sys.stdout.flush()

    # Read existing file paths to avoid duplicates
    existing_paths = set()
    if out_path.exists():
        with open(out_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("### FILE: "):
                    existing_paths.add(line.strip())

    # Collect all eligible code files — scan deeper (also hidden subdirs of repos)
    all_files = []
    scan_dirs = []
    for repo_dir in sorted(DEV_DIR.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue
        scan_dirs.append(repo_dir)

    # Also scan ~/Dev itself for loose files and nested dirs
    for scan_dir in scan_dirs:
        for lang_name, exts in CODE_EXTS.items():
            for ext in exts:
                try:
                    for fpath in scan_dir.rglob(f"*{ext}"):
                        parts = set(p for p in fpath.parts)
                        if parts & SKIP_DIRS:
                            continue
                        try:
                            size = fpath.stat().st_size
                            # Wider range: 50 bytes to 2MB
                            if 50 <= size <= 2_000_000:
                                try:
                                    rel = fpath.relative_to(DEV_DIR)
                                except ValueError:
                                    rel = fpath.name
                                header = f"### FILE: {rel} [{lang_name}]"
                                if header not in existing_paths:
                                    all_files.append((fpath, lang_name, size))
                        except OSError:
                            continue
                except PermissionError:
                    continue

    print(f"  Found {len(all_files):,} new code files (skipping {len(existing_paths)} already collected)")
    random.shuffle(all_files)

    written = 0
    count = 0
    lang_counts = {}

    with open(out_path, "a", encoding="utf-8") as f:
        for fpath, lang_name, size in all_files:
            try:
                text = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            if not text.strip():
                continue

            if "\x00" in text[:1000]:
                continue

            try:
                rel = fpath.relative_to(DEV_DIR)
            except ValueError:
                rel = fpath.name

            header = f"### FILE: {rel} [{lang_name}]\n"
            entry = header + text + "\n\n"
            f.write(entry)
            entry_bytes = len(entry.encode("utf-8"))
            written += entry_bytes
            count += 1
            lang_counts[lang_name] = lang_counts.get(lang_name, 0) + 1

            if count % 200 == 0:
                progress(existing + written, target, "code")

            if written >= remaining:
                break

    total = existing + written
    breakdown = ", ".join(f"{k}={v}" for k, v in sorted(lang_counts.items()))
    print(f"\n  [DONE] code: {fmt(total)} (+{fmt(written)} from {count:,} new files) ({breakdown})")
    return total


# ── 4. Wikipedia API collector (zh, ja, ru) ─────────────────────────

def wiki_get_random_titles(lang, count=50):
    """Get random article titles from Wikipedia."""
    api = f"https://{lang}.wikipedia.org/w/api.php"
    # API limits rnlimit to 20 max, so we batch
    titles = []
    for _ in range(0, count, 20):
        batch = min(20, count - len(titles))
        url = f"{api}?action=query&list=random&rnlimit={batch}&rnnamespace=0&format=json"
        req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=15).read())
            for p in data.get("query", {}).get("random", []):
                titles.append(p["title"])
        except Exception as e:
            print(f"    [WARN] random titles error: {e}")
            break
    return titles


def wiki_get_article_text(lang, title):
    """Get full article text via parse API (much more content than extracts)."""
    api = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "format": "json",
    }
    url = f"{api}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=20).read())
        wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
        # Strip wikitext markup (basic cleanup)
        return clean_wikitext(wikitext)
    except Exception:
        return ""


def wiki_get_extracts_batch(lang, titles):
    """Get plain text extracts for a batch of titles (up to 20)."""
    api = f"https://{lang}.wikipedia.org/w/api.php"
    titles_str = "|".join(titles[:20])
    params = {
        "action": "query",
        "titles": titles_str,
        "prop": "extracts",
        "explaintext": "1",
        "exlimit": str(min(len(titles), 20)),
        "format": "json",
    }
    url = f"{api}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": WIKI_UA})
    try:
        data = json.loads(urllib.request.urlopen(req, timeout=30).read())
        texts = []
        for pid, page in data.get("query", {}).get("pages", {}).items():
            text = page.get("extract", "")
            if text and len(text) > 200:
                texts.append(text)
        return texts
    except Exception as e:
        print(f"    [WARN] extract batch error: {e}")
        return []


def clean_wikitext(text):
    """Basic wikitext to plain text conversion."""
    import re
    # Remove templates {{...}}
    # Simple approach: remove single-line templates
    text = re.sub(r'\{\{[^{}]*\}\}', '', text)
    # Remove [[ ]] links, keep display text
    text = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', text)
    # Remove external links [url text]
    text = re.sub(r'\[https?://\S+\s*([^\]]*)\]', r'\1', text)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove ref tags and content
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL)
    text = re.sub(r'<ref[^>]*/>', '', text)
    # Remove == headers ==, keep text
    text = re.sub(r'={2,}\s*([^=]+?)\s*={2,}', r'\n\1\n', text)
    # Remove wiki markup
    text = re.sub(r"'{2,3}", '', text)
    # Remove category/file links
    text = re.sub(r'\[\[(Category|File|Image|파일|분류|カテゴリ|Категория|分类):[^\]]*\]\]', '', text, flags=re.IGNORECASE)
    # Remove remaining {{ }}
    text = re.sub(r'\{\{[^}]*\}\}', '', text)
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    # Remove lines that are just markup residue
    lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped and len(stripped) > 10 and not stripped.startswith('|') and not stripped.startswith('{') and not stripped.startswith('}'):
            lines.append(stripped)
    return '\n'.join(lines)


def collect_wikipedia(lang, out_path, target):
    """Collect Wikipedia articles for a language using API — appends."""
    existing = out_path.stat().st_size if out_path.exists() else 0
    remaining = target - existing
    if remaining <= 0:
        print(f"  [SKIP] Already {fmt(existing)} >= target {fmt(target)}")
        return existing

    print(f"  Wikipedia API for '{lang}' — need {fmt(remaining)} more (have {fmt(existing)})")
    sys.stdout.flush()

    written = 0
    articles = 0
    t0 = time.time()
    empty_rounds = 0

    with open(out_path, "a", encoding="utf-8") as f:
        while written < remaining:
            # Get batch of random titles
            titles = wiki_get_random_titles(lang, 50)
            if not titles:
                empty_rounds += 1
                if empty_rounds > 5:
                    print(f"\n    [WARN] Too many empty rounds, stopping")
                    break
                time.sleep(1)
                continue

            # Process in batches of 20 for extracts
            for i in range(0, len(titles), 20):
                batch = titles[i:i+20]
                texts = wiki_get_extracts_batch(lang, batch)

                for text in texts:
                    if len(text) < 200:
                        continue
                    f.write(text + "\n\n")
                    written += len(text.encode("utf-8"))
                    articles += 1

                    if written >= remaining:
                        break

                if written >= remaining:
                    break

                # Rate limiting: be polite
                time.sleep(0.1)

            # Also try getting full articles via parse API for bigger articles
            for title in titles[:5]:
                if written >= remaining:
                    break
                text = wiki_get_article_text(lang, title)
                if text and len(text) > 500:
                    f.write(text + "\n\n")
                    written += len(text.encode("utf-8"))
                    articles += 1
                time.sleep(0.05)

            elapsed = time.time() - t0
            speed = written / max(elapsed, 0.1)
            eta = (remaining - written) / max(speed, 1)
            progress(existing + written, target, lang, f"| {articles} articles | {fmt(int(speed))}/s | ETA {eta:.0f}s")

            empty_rounds = 0

    total = existing + written
    elapsed = time.time() - t0
    print(f"\n  [DONE] {lang}: {fmt(total)} (+{fmt(written)} from {articles} articles in {elapsed:.0f}s)")
    return total


# ── 5. HuggingFace fallback for Wikipedia ───────────────────────────

def try_huggingface_wiki(lang, out_path, target):
    """Try HuggingFace wikimedia/wikipedia dataset (streaming) — appends."""
    try:
        from datasets import load_dataset
    except ImportError:
        return 0

    existing = out_path.stat().st_size if out_path.exists() else 0
    remaining = target - existing
    if remaining <= 0:
        print(f"  [SKIP] Already {fmt(existing)} >= target {fmt(target)}")
        return existing

    dataset_name = f"20231101.{lang}"
    print(f"  Trying HuggingFace wikimedia/wikipedia {dataset_name}...")
    print(f"  Existing: {fmt(existing)}, need {fmt(remaining)} more")
    sys.stdout.flush()

    try:
        ds = load_dataset(
            "wikimedia/wikipedia",
            dataset_name,
            split="train",
            streaming=True,
        )
    except Exception as e:
        print(f"  [FAIL] HuggingFace: {e}")
        return existing

    written = 0
    count = 0
    skipped = 0
    t0 = time.time()

    with open(out_path, "a", encoding="utf-8") as f:
        try:
            for article in ds:
                text = article.get("text", "")
                if not text or len(text) < 200:
                    continue

                # Skip early articles (likely already collected)
                if skipped < (existing // 3000) and existing > 0:
                    skipped += 1
                    continue

                paragraphs = [p.strip() for p in text.split("\n") if len(p.strip()) > 30]
                if not paragraphs:
                    continue

                clean = "\n".join(paragraphs) + "\n\n"
                f.write(clean)
                written += len(clean.encode("utf-8"))
                count += 1

                if count % 500 == 0:
                    elapsed = time.time() - t0
                    speed = written / max(elapsed, 0.1)
                    progress(existing + written, target, lang, f"| {count} articles | {fmt(int(speed))}/s")

                if written >= remaining:
                    break

                # Timeout after 30 minutes per language
                if time.time() - t0 > 1800:
                    print(f"\n  [TIMEOUT] 30 min reached")
                    break

        except Exception as e:
            print(f"\n  [ERROR] Streaming failed after {count} articles: {e}")

    total = existing + written
    elapsed = time.time() - t0
    print(f"\n  [DONE] {lang} via HF: {fmt(total)} (+{fmt(written)} from {count} articles in {elapsed:.0f}s)")
    return total


# ── Main ────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    total_target = sum(TARGET_BYTES.values())
    # Check existing sizes
    existing_total = 0
    for lang in TARGET_BYTES:
        p = OUT_DIR / f"{lang}.txt"
        if p.exists():
            existing_total += p.stat().st_size

    print("=" * 70)
    print("MULTILINGUAL CORPUS EXPANSION v2.1 (append mode)")
    print(f"Existing: {fmt(existing_total)} -> Target: {fmt(total_target)} total new + existing")
    print(f"Output: {OUT_DIR}")
    print("=" * 70)
    for lang, t in TARGET_BYTES.items():
        p = OUT_DIR / f"{lang}.txt"
        ex = p.stat().st_size if p.exists() else 0
        print(f"  {lang:<8} {fmt(ex):>10} -> {fmt(t):>10} (need +{fmt(max(0, t-ex))})")
    print()

    results = {}
    t0 = time.time()

    # ── Korean ──
    print(f"\n{'─'*70}")
    print(f"[1/6] KOREAN (ko) — from corpus_v10_ko.txt")
    print(f"{'─'*70}")
    ko_path = OUT_DIR / "ko.txt"
    results["ko"] = collect_korean(ko_path, TARGET_BYTES["ko"])

    # ── English ──
    print(f"\n{'─'*70}")
    print(f"[2/6] ENGLISH (en) — from corpus_v10.txt + supplements")
    print(f"{'─'*70}")
    en_path = OUT_DIR / "en.txt"
    results["en"] = collect_english(en_path, TARGET_BYTES["en"])

    # ── Code ──
    print(f"\n{'─'*70}")
    print(f"[3/6] CODE — from ~/Dev repos (deep scan)")
    print(f"{'─'*70}")
    code_path = OUT_DIR / "code.txt"
    results["code"] = collect_code(code_path, TARGET_BYTES["code"])

    # ── Chinese, Japanese, Russian — try HuggingFace first, fallback to API ──
    for idx, (lang, label) in enumerate([("zh", "CHINESE"), ("ja", "JAPANESE"), ("ru", "RUSSIAN")], 4):
        print(f"\n{'─'*70}")
        print(f"[{idx}/6] {label} ({lang}) — Wikipedia streaming")
        print(f"{'─'*70}")
        lang_path = OUT_DIR / f"{lang}.txt"
        lang_target = TARGET_BYTES[lang]

        # Strategy 1: Try HuggingFace (faster if it works)
        written = try_huggingface_wiki(lang, lang_path, lang_target)

        # Strategy 2: Wikipedia API fallback
        if written < lang_target:
            if written > 0:
                print(f"  Got {fmt(written)} total, supplementing with API...")
            written = collect_wikipedia(lang, lang_path, lang_target)

        results[lang] = written

    # ── Final Report ──
    elapsed = time.time() - t0
    total = sum(results.values())

    print(f"\n\n{'=' * 70}")
    print(f"COLLECTION COMPLETE — {elapsed:.0f}s")
    print(f"{'=' * 70}")
    print(f"\n  {'Lang':<8} {'Size':>12} {'Target':>12} {'Status':>8}")
    print(f"  {'─' * 44}")
    for lang in ["en", "ko", "code", "zh", "ja", "ru"]:
        size = results.get(lang, 0)
        lang_target = TARGET_BYTES[lang]
        pct = 100 * size / lang_target
        status = "OK" if pct >= 80 else "LOW" if pct >= 10 else "FAIL"
        print(f"  {lang:<8} {fmt(size):>12} {fmt(lang_target):>12} {status:>8} ({pct:.0f}%)")
    print(f"  {'─' * 44}")
    print(f"  {'TOTAL':<8} {fmt(total):>12}")
    print(f"\n  Output directory: {OUT_DIR}")
    print()

    # List actual files
    for f in sorted(OUT_DIR.iterdir()):
        if f.is_file() and f.suffix == ".txt":
            print(f"  {f.name:<20} {fmt(f.stat().st_size):>10}")


if __name__ == "__main__":
    random.seed(42)
    main()
