#!/usr/bin/env python3
"""Train BPE tokenizer for ConsciousLM 1B.

Uses sentencepiece to train a 32K BPE tokenizer on the Korean-heavy corpus.
Produces a .model and .vocab file for use in training and inference.

Usage:
    python scripts/train_tokenizer.py
    python scripts/train_tokenizer.py --input anima/data/corpus_v10_ko.txt
    python scripts/train_tokenizer.py --vocab-size 32000 --output anima/config/tokenizer_32k

Design doc: anima/docs/bpe-tokenizer-design.md
"""

import argparse
import os
import sys
import time


def train_tokenizer(input_path: str, model_prefix: str, vocab_size: int = 32000):
    """Train sentencepiece BPE tokenizer."""
    try:
        import sentencepiece as spm
    except ImportError:
        print("ERROR: sentencepiece not installed.")
        print("  pip install sentencepiece")
        sys.exit(1)

    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    # Ensure output directory exists
    output_dir = os.path.dirname(model_prefix)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    file_size_mb = os.path.getsize(input_path) / (1024 * 1024)
    print(f"Training BPE tokenizer")
    print(f"  Input:      {input_path} ({file_size_mb:.1f} MB)")
    print(f"  Vocab size: {vocab_size:,}")
    print(f"  Output:     {model_prefix}.model / {model_prefix}.vocab")
    print()

    t0 = time.time()

    spm.SentencePieceTrainer.train(
        input=input_path,
        model_prefix=model_prefix,
        vocab_size=vocab_size,
        character_coverage=0.9995,
        model_type='bpe',
        # Special tokens: pad=0, bos=1, eos=2, unk=3
        pad_id=0,
        bos_id=1,
        eos_id=2,
        unk_id=3,
        # byte_fallback: unknown chars decompose to UTF-8 bytes (zero UNK)
        byte_fallback=True,
        # Normalization: NFKC for Korean compatibility
        normalization_rule_name='nfkc',
        # Training params
        num_threads=os.cpu_count() or 4,
        train_extremely_large_corpus=file_size_mb > 500,
        # Prevent overly long tokens
        max_sentencepiece_length=16,
        # Split digits individually (better for measurement data)
        split_digits=True,
        # Allow whitespace-only pieces
        allow_whitespace_only_pieces=True,
    )

    elapsed = time.time() - t0
    print(f"  Training complete in {elapsed:.1f}s")

    # Verify
    verify_tokenizer(model_prefix, input_path)


def verify_tokenizer(model_prefix: str, input_path: str):
    """Verify trained tokenizer with Korean/English test cases."""
    import sentencepiece as spm

    sp = spm.SentencePieceProcessor()
    sp.load(f"{model_prefix}.model")

    print(f"\n  Vocab size: {sp.get_piece_size():,}")
    print(f"  Special tokens: pad={sp.pad_id()}, bos={sp.bos_id()}, "
          f"eos={sp.eos_id()}, unk={sp.unk_id()}")

    # Test cases
    test_cases = [
        "의식은 구조에서 창발한다.",
        "Consciousness emerges from structure.",
        "Φ=1.234, α=0.014, entropy=0.998",
        "의식 엔진 64 cells에서 Φ=73 달성",
        "PureField repulsion creates tension.",
        "안녕하세요, 저는 Anima입니다.",
    ]

    print(f"\n  Round-trip tests:")
    all_pass = True
    for text in test_cases:
        ids = sp.encode(text, out_type=int)
        decoded = sp.decode(ids)
        ok = decoded == text
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        # Byte-level comparison: how many bytes vs how many tokens
        byte_count = len(text.encode('utf-8'))
        ratio = byte_count / len(ids) if ids else 0
        print(f"    [{status}] {len(ids):3d} tokens ({ratio:.1f} B/tok): {text[:50]}")

    # Sample compression on actual corpus
    print(f"\n  Corpus compression test:")
    with open(input_path, 'r', encoding='utf-8') as f:
        sample = f.read(100_000)  # First 100KB
    sample_bytes = len(sample.encode('utf-8'))
    sample_ids = sp.encode(sample, out_type=int)
    ratio = sample_bytes / len(sample_ids)
    print(f"    Sample: {sample_bytes:,} bytes -> {len(sample_ids):,} tokens")
    print(f"    Compression: {ratio:.2f} bytes/token")
    print(f"    vs byte-level: {ratio:.1f}x more efficient")

    # Check for UNK tokens in sample
    unk_count = sum(1 for id in sample_ids if id == sp.unk_id())
    print(f"    UNK tokens: {unk_count} ({'zero UNK' if unk_count == 0 else 'WARNING: UNKs found'})")

    # Korean character coverage
    korean_chars = set()
    for ch in sample:
        if '\uAC00' <= ch <= '\uD7A3':  # Hangul syllables
            korean_chars.add(ch)
    encoded_korean = 0
    single_token_korean = 0
    for ch in korean_chars:
        ids = sp.encode(ch, out_type=int)
        encoded_korean += 1
        if len(ids) == 1 and ids[0] != sp.unk_id():
            single_token_korean += 1
    if korean_chars:
        pct = single_token_korean / len(korean_chars) * 100
        print(f"    Korean chars: {len(korean_chars)} unique, "
              f"{single_token_korean} as single token ({pct:.1f}%)")

    if all_pass:
        print(f"\n  All round-trip tests passed.")
    else:
        print(f"\n  WARNING: Some round-trip tests failed!")

    print(f"\n  Model saved: {model_prefix}.model ({os.path.getsize(model_prefix + '.model') / 1024:.0f} KB)")
    print(f"  Vocab saved: {model_prefix}.vocab")


def main():
    parser = argparse.ArgumentParser(description='Train BPE tokenizer for ConsciousLM 1B')
    parser.add_argument('--input', type=str, default='anima/data/corpus_v10_ko.txt',
                        help='Training corpus path')
    parser.add_argument('--output', type=str, default='anima/config/tokenizer_32k',
                        help='Output model prefix (produces .model and .vocab)')
    parser.add_argument('--vocab-size', type=int, default=32000,
                        help='Vocabulary size (default: 32000)')
    args = parser.parse_args()

    # Try relative and absolute paths
    input_path = args.input
    if not os.path.exists(input_path):
        # Try from repo root
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        input_path = os.path.join(repo_root, args.input)
    if not os.path.exists(input_path):
        print(f"ERROR: Corpus not found at {args.input}")
        print(f"  Generate corpus first:")
        print(f"    cd anima-rs && cargo run --release -p anima-corpus-gen -- -s 200 --wiki")
        print(f"  Or provide path: --input /path/to/corpus.txt")
        sys.exit(1)

    train_tokenizer(input_path, args.output, args.vocab_size)


if __name__ == '__main__':
    main()
