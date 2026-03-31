#!/usr/bin/env python3
"""Merge multilingual corpus at AGI ratios for tokenizer training.

Ratios: en 30%, ko 18%, code 15%, zh 15%, ja 12%, ru 10%
Each source is ~112MB, total target ~600MB with ratio sampling.
"""

import os
import sys
import time

CORPUS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          'anima', 'data', 'corpus_multilingual')
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           'anima', 'data', 'corpus_multilingual_merged.txt')

# AGI ratios
RATIOS = {
    'en':   0.30,
    'ko':   0.18,
    'code': 0.15,
    'zh':   0.15,
    'ja':   0.12,
    'ru':   0.10,
}

def main():
    print("Merging multilingual corpus at AGI ratios")
    print(f"  Output: {OUTPUT_PATH}")
    print()

    t0 = time.time()
    total_bytes = 0
    total_lines = 0

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as out:
        for lang, ratio in RATIOS.items():
            path = os.path.join(CORPUS_DIR, f'{lang}.txt')
            if not os.path.exists(path):
                print(f"  WARNING: {path} not found, skipping")
                continue

            file_size = os.path.getsize(path)
            # Each file is ~112MB. Target bytes = ratio * total_target
            # total_target = sum of all files = ~672MB
            # We sample ratio of each file's lines
            # But since all files are ~same size, ratio directly = fraction of lines to take
            # Normalize: max ratio is 0.30 (en), we want en to contribute 30% of final
            # Simple: take ratio/max_ratio of each file, but that would over-sample
            # Better: take all lines, shuffle would be ideal but memory-heavy
            # Approach: take fraction = ratio * (total_files / 1.0) of lines
            # Since ratios sum to 1.0, just take ratio * total_lines_across_all_files
            # But we want to be simpler: take ratio/0.18 * all lines (normalized to ko=100%)
            # Actually simplest: each file ~same size, take ratio proportion of each file

            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            n_total = len(lines)
            # Take this fraction of lines from the file
            # ratio represents desired share of final corpus
            # All files are ~same size, so we scale by ratio
            # Max ratio = 0.30 (en), so en gets 100% of its lines
            # Others get (their_ratio / 0.30) of their lines
            # This gives ~600MB total: 112 + 67 + 56 + 56 + 45 + 37 = 373MB
            # Actually let's just use ratio * n_total / 0.30 to normalize en=100%
            # No -- let's keep it simple. Take fraction = ratio/max(ratios) of each file.
            # en=100%, ko=60%, code=50%, zh=50%, ja=40%, ru=33%
            # Total = 112*(1+0.6+0.5+0.5+0.4+0.33) = 112*3.33 = 373MB

            # Better approach: we want the FINAL proportions to match ratios.
            # If we take all of en (n_en lines), then for ko we need:
            # n_ko_take / n_en = 0.18/0.30 => n_ko_take = n_en * 0.18/0.30
            # But n_en ~ n_ko, so n_ko_take = n_ko * 0.18/0.30 = 0.6 * n_ko

            fraction = ratio / max(RATIOS.values())
            n_take = int(n_total * fraction)
            n_take = min(n_take, n_total)

            # Write lines
            written_bytes = 0
            for line in lines[:n_take]:
                out.write(line)
                written_bytes += len(line.encode('utf-8'))

            total_bytes += written_bytes
            total_lines += n_take
            pct = ratio * 100
            print(f"  {lang:5s}: {n_take:>10,} / {n_total:>10,} lines "
                  f"({written_bytes/1024/1024:.1f} MB, target {pct:.0f}%)")

    elapsed = time.time() - t0
    print(f"\n  Total: {total_lines:,} lines, {total_bytes/1024/1024:.1f} MB")
    print(f"  Time: {elapsed:.1f}s")
    print(f"  Output: {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
