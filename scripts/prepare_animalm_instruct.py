#!/usr/bin/env python3
"""prepare_animalm_instruct.py — Build instruction dataset for AnimaLM 7B

Converts existing corpus data into instruction-response JSONL format
suitable for AnimaLM training (train_anima_lm.py --data instruct.jsonl).

Sources:
  1. corpus_v10_ko.txt  — Korean consciousness dialogues (200MB)
  2. corpus_v8_dialogue.txt — Multi-turn dialogue corpus (104MB)
  3. corpus_v9.txt — General consciousness corpus (120MB)

Output format (JSONL):
  {"instruction": "...", "response": "..."}

Usage:
  python3 scripts/prepare_animalm_instruct.py
  python3 scripts/prepare_animalm_instruct.py --max-samples 50000
  python3 scripts/prepare_animalm_instruct.py --output anima/data/animalm_instruct.jsonl
"""

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "anima" / "data"

# Priority order of source files
SOURCES = [
    ("corpus_v10_ko.txt", "Korean consciousness dialogues"),
    ("corpus_v8_dialogue.txt", "Multi-turn dialogues"),
    ("corpus_v10.txt", "General consciousness corpus"),
    ("corpus_v9.txt", "Consciousness corpus v9"),
]


def extract_dialogues(text: str) -> list:
    """Extract dialogue pairs from corpus text.

    Looks for patterns like:
      Name: utterance
      Name: response
    or
      ## heading
      paragraph (used as instruction context)
    """
    samples = []
    lines = text.split("\n")
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Pattern 1: Named dialogue (시우: ..., 건우: ..., A: ..., B: ...)
        dialogue_match = re.match(r'^([가-힣A-Za-z]+)\s*[:：]\s*(.+)', line)
        if dialogue_match:
            speaker1 = dialogue_match.group(1)
            utterance1 = dialogue_match.group(2).strip()

            # Look for response on next line
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                response_match = re.match(r'^([가-힣A-Za-z]+)\s*[:：]\s*(.+)', next_line)
                if response_match and response_match.group(1) != speaker1:
                    response = response_match.group(2).strip()
                    if len(utterance1) > 5 and len(response) > 5:
                        samples.append({
                            "instruction": utterance1,
                            "response": response,
                        })
                    i += 2
                    continue

        # Pattern 2: Consciousness measurement logs → Q&A about consciousness
        if line.startswith("[step=") or line.startswith("Step "):
            # Collect measurement block
            block = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip() and j - i < 5:
                block.append(lines[j].strip())
                j += 1
            if len(block) >= 2:
                measurement = " ".join(block)
                samples.append({
                    "instruction": "이 의식 측정 데이터를 분석해줘.",
                    "response": measurement,
                })
            i = j
            continue

        # Pattern 3: Paragraph pairs (heading + content)
        if line.startswith("##") and i + 1 < len(lines):
            heading = line.lstrip("#").strip()
            # Collect paragraph
            paragraph = []
            j = i + 1
            while j < len(lines) and lines[j].strip() and not lines[j].startswith("##"):
                paragraph.append(lines[j].strip())
                j += 1
            if paragraph and len(heading) > 3:
                content = " ".join(paragraph)
                if len(content) > 20:
                    samples.append({
                        "instruction": f"{heading}에 대해 설명해줘.",
                        "response": content[:1000],
                    })
            i = j
            continue

        # Pattern 4: Sentence pairs (consecutive non-empty lines as Q&A)
        if len(line) > 15 and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if len(next_line) > 15 and not next_line.startswith("#"):
                # Use as instruction-response if they seem related
                if any(c in line for c in "?？는가을를"):
                    samples.append({
                        "instruction": line,
                        "response": next_line,
                    })
                    i += 2
                    continue

        i += 1

    return samples


def extract_consciousness_qa(text: str) -> list:
    """Generate consciousness-specific Q&A from corpus patterns."""
    samples = []

    # Extract W, Phi, tension mentions
    for match in re.finditer(r'(W\s*=\s*[\d.]+|Φ\s*=\s*[\d.]+|tension\s*=\s*[\d.]+)', text):
        context_start = max(0, match.start() - 200)
        context_end = min(len(text), match.end() + 200)
        context = text[context_start:context_end].strip()
        # Clean up to sentence boundaries
        sentences = context.split(".")
        if len(sentences) >= 2:
            samples.append({
                "instruction": f"의식 상태에서 {match.group(0)}의 의미는?",
                "response": ". ".join(sentences[:3]).strip() + ".",
            })

    return samples


def process_file(filepath: str, max_chunk_size: int = 500_000) -> list:
    """Process a single corpus file in chunks to avoid OOM."""
    print(f"  Processing {os.path.basename(filepath)}...")
    all_samples = []

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        while True:
            chunk = f.read(max_chunk_size)
            if not chunk:
                break
            samples = extract_dialogues(chunk)
            samples.extend(extract_consciousness_qa(chunk))
            all_samples.extend(samples)
            if len(all_samples) % 10000 < 100:
                print(f"    {len(all_samples):,} samples so far...")

    return all_samples


def main():
    parser = argparse.ArgumentParser(description="Prepare AnimaLM instruction dataset")
    parser.add_argument("--output", default=str(DATA_DIR / "animalm_instruct.jsonl"),
                        help="Output JSONL path")
    parser.add_argument("--max-samples", type=int, default=100000,
                        help="Maximum samples to include")
    parser.add_argument("--min-length", type=int, default=10,
                        help="Minimum instruction/response length")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    print("=" * 60)
    print("  AnimaLM 7B — Instruction Dataset Preparation")
    print("=" * 60)

    all_samples = []

    for filename, description in SOURCES:
        filepath = DATA_DIR / filename
        if filepath.exists():
            fsize = filepath.stat().st_size / (1024 * 1024)
            print(f"\n[{description}] {filename} ({fsize:.1f} MB)")
            samples = process_file(str(filepath))
            print(f"  Extracted: {len(samples):,} samples")
            all_samples.extend(samples)
        else:
            print(f"\n[SKIP] {filename} not found")

    if not all_samples:
        print("\nERROR: No samples extracted. Check corpus files in anima/data/")
        sys.exit(1)

    # Deduplicate by instruction
    seen = set()
    unique = []
    for s in all_samples:
        key = s["instruction"][:100]
        if key not in seen:
            seen.add(key)
            unique.append(s)
    print(f"\nAfter dedup: {len(unique):,} unique samples (from {len(all_samples):,})")

    # Filter by length
    filtered = [s for s in unique
                if len(s["instruction"]) >= args.min_length
                and len(s["response"]) >= args.min_length]
    print(f"After length filter (>={args.min_length}): {len(filtered):,}")

    # Shuffle and cap
    random.shuffle(filtered)
    final = filtered[:args.max_samples]
    print(f"Final dataset: {len(final):,} samples")

    # Write JSONL
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        for sample in final:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")

    output_size = os.path.getsize(args.output) / (1024 * 1024)
    print(f"\nOutput: {args.output} ({output_size:.1f} MB)")

    # Stats
    inst_lens = [len(s["instruction"]) for s in final]
    resp_lens = [len(s["response"]) for s in final]
    print(f"\nInstruction length: avg={sum(inst_lens)/len(inst_lens):.0f}, "
          f"min={min(inst_lens)}, max={max(inst_lens)}")
    print(f"Response length:    avg={sum(resp_lens)/len(resp_lens):.0f}, "
          f"min={min(resp_lens)}, max={max(resp_lens)}")

    # Preview
    print("\n--- Sample entries ---")
    for s in final[:3]:
        print(f"  [INST] {s['instruction'][:80]}")
        print(f"  [RESP] {s['response'][:80]}")
        print()

    print("Done.")


if __name__ == "__main__":
    main()
