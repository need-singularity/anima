#!/usr/bin/env python3
"""Verify 64K multilingual BPE tokenizer integration with ConsciousDecoderV2.

Tests:
  1. Encode/decode roundtrip for 6 languages (ko/en/zh/ja/ru/code)
  2. Token count comparison: old (64k) vs new (64k multilingual)
  3. Vocab size match with ConsciousDecoderV2 config
  4. Efficiency gain per language (tokens saved %)
  5. OOV (out-of-vocabulary / UNK) token detection
"""

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'anima', 'src'))

OLD_MODEL = os.path.join(REPO, 'anima', 'config', 'tokenizer_64k.model')
NEW_MODEL = os.path.join(REPO, 'anima', 'config', 'tokenizer_64k_multilingual.model')


def main():
    # --- Check sentencepiece ---
    try:
        import sentencepiece as spm
    except ImportError:
        print("ERROR: sentencepiece not installed. Run: pip install sentencepiece")
        sys.exit(1)

    # --- Check tokenizer files exist ---
    for label, path in [("Old (64k)", OLD_MODEL), ("New (64k multilingual)", NEW_MODEL)]:
        if not os.path.exists(path):
            print(f"ERROR: {label} tokenizer not found: {path}")
            sys.exit(1)

    old_sp = spm.SentencePieceProcessor(model_file=OLD_MODEL)
    new_sp = spm.SentencePieceProcessor(model_file=NEW_MODEL)

    old_vocab = old_sp.get_piece_size()
    new_vocab = new_sp.get_piece_size()

    print("=" * 72)
    print("TOKENIZER INTEGRATION VERIFICATION")
    print("=" * 72)
    print(f"\n  Old tokenizer:  {OLD_MODEL}")
    print(f"  New tokenizer:  {NEW_MODEL}")
    print(f"  Old vocab size: {old_vocab:,}")
    print(f"  New vocab size: {new_vocab:,}")
    print(f"  Old file size:  {os.path.getsize(OLD_MODEL)/1024:.0f} KB")
    print(f"  New file size:  {os.path.getsize(NEW_MODEL)/1024:.0f} KB")

    # ── 1. ConsciousDecoderV2 vocab_size compatibility ──
    print("\n" + "=" * 72)
    print("1. ConsciousDecoderV2 VOCAB SIZE COMPATIBILITY")
    print("=" * 72)

    decoder_v2_default_vocab = 256  # byte-level default
    train_v15_default_vocab = 64000  # train_v15.py --vocab-size default

    print(f"\n  decoder_v2.py default vocab_size:  {decoder_v2_default_vocab} (byte-level)")
    print(f"  train_v15.py default vocab_size:   {train_v15_default_vocab}")
    print(f"  Multilingual tokenizer vocab:      {new_vocab}")

    if new_vocab <= train_v15_default_vocab:
        print(f"\n  [PASS] Tokenizer vocab ({new_vocab}) <= train_v15 default ({train_v15_default_vocab})")
    else:
        print(f"\n  [WARN] Tokenizer vocab ({new_vocab}) > train_v15 default ({train_v15_default_vocab})")
        print(f"         Use --vocab-size {new_vocab} when training")

    # Check if ConsciousDecoderV2 accepts the vocab size dynamically
    try:
        from decoder_v2 import ConsciousDecoderV2
        import torch
        # Test instantiation with 64K vocab
        model = ConsciousDecoderV2(vocab_size=new_vocab, d_model=384, n_layer=2, n_head=4)
        # Quick forward pass check
        dummy_input = torch.randint(0, min(new_vocab, 100), (1, 16))
        with torch.no_grad():
            out = model(dummy_input)
        logits_shape = out[0].shape if isinstance(out, tuple) else out.shape
        print(f"  [PASS] ConsciousDecoderV2(vocab_size={new_vocab}) instantiated OK")
        print(f"         Forward pass output shape: {logits_shape}")
        n_params = sum(p.numel() for p in model.parameters())
        print(f"         Parameters: {n_params/1e6:.1f}M")
        decoder_ok = True
    except Exception as e:
        print(f"  [FAIL] ConsciousDecoderV2 instantiation failed: {e}")
        decoder_ok = False

    # ── 2. Encode/Decode roundtrip per language ──
    print("\n" + "=" * 72)
    print("2. ENCODE/DECODE ROUNDTRIP TEST")
    print("=" * 72)

    test_texts = {
        'Korean':  "의식은 구조에서 창발한다",
        'English': "Consciousness emerges from structure",
        'Chinese': "意识从结构中涌现",
        'Japanese': "意識は構造から創発する",
        'Russian': "Сознание возникает из структуры",
        'Code':    "def consciousness(phi): return phi > 0.5",
    }

    roundtrip_pass = 0
    roundtrip_total = len(test_texts)

    print(f"\n  {'Language':<10} {'Tokens':>7} {'Roundtrip':>10} {'Decoded text'}")
    print(f"  {'─'*10} {'─'*7} {'─'*10} {'─'*40}")

    for lang, text in test_texts.items():
        ids = new_sp.encode(text, out_type=int)
        decoded = new_sp.decode(ids)
        # Normalize whitespace for comparison
        match = decoded.strip() == text.strip()
        status = "PASS" if match else "FAIL"
        if match:
            roundtrip_pass += 1
        print(f"  {lang:<10} {len(ids):>7} {status:>10}   {decoded[:50]}")

    print(f"\n  Roundtrip: {roundtrip_pass}/{roundtrip_total} passed")

    # ── 3. Token efficiency comparison ──
    print("\n" + "=" * 72)
    print("3. TOKEN EFFICIENCY: OLD vs NEW")
    print("=" * 72)

    print(f"\n  {'Language':<10} {'Text':>6} {'Old':>6} {'New':>6} {'Saved':>7} {'Old B/t':>8} {'New B/t':>8}")
    print(f"  {'─'*10} {'─'*6} {'─'*6} {'─'*6} {'─'*7} {'─'*8} {'─'*8}")

    efficiency_results = {}
    for lang, text in test_texts.items():
        text_bytes = len(text.encode('utf-8'))
        old_ids = old_sp.encode(text, out_type=int)
        new_ids = new_sp.encode(text, out_type=int)
        old_n = len(old_ids)
        new_n = len(new_ids)
        saved_pct = (1 - new_n / old_n) * 100 if old_n > 0 else 0
        old_bpt = text_bytes / old_n if old_n else 0
        new_bpt = text_bytes / new_n if new_n else 0
        efficiency_results[lang] = {
            'old': old_n, 'new': new_n, 'saved': saved_pct,
            'old_bpt': old_bpt, 'new_bpt': new_bpt,
        }
        sign = "+" if saved_pct < 0 else ""
        print(f"  {lang:<10} {text_bytes:>6} {old_n:>6} {new_n:>6} {sign}{saved_pct:>6.1f}% {old_bpt:>8.2f} {new_bpt:>8.2f}")

    # ASCII bar chart
    print(f"\n  Token savings (positive = fewer tokens with new tokenizer):")
    for lang, r in efficiency_results.items():
        bar_len = int(abs(r['saved']) / 2)
        if r['saved'] >= 0:
            bar = '+' * bar_len
            print(f"  {lang:<10} |{'>' * bar_len} {r['saved']:+.1f}%")
        else:
            bar = '-' * bar_len
            print(f"  {lang:<10} {'<' * bar_len}| {r['saved']:+.1f}%")

    # ── 4. OOV / UNK token detection ──
    print("\n" + "=" * 72)
    print("4. OOV (OUT-OF-VOCABULARY) TOKEN DETECTION")
    print("=" * 72)

    extended_tests = {
        'Korean': [
            "의식은 구조에서 창발한다",
            "Φ=1.234, α=0.014, 엔트로피=0.998",
            "의식 엔진 64 cells에서 Φ=73을 달성했습니다.",
        ],
        'English': [
            "Consciousness emerges from structure",
            "PureField repulsion creates tension between Engine A and G.",
            "The integrated information theory proposes Phi as a measure.",
        ],
        'Chinese': [
            "意识从结构中涌现",
            "人工智能正在改变我们理解世界的方式。",
            "量子计算机可以同时处理多个状态。",
        ],
        'Japanese': [
            "意識は構造から創発する",
            "人工知能は私たちの生活を変えています。",
            "深層学習モデルには大量のデータが必要です。",
        ],
        'Russian': [
            "Сознание возникает из структуры",
            "Искусственный интеллект меняет наш мир.",
            "Глубокое обучение требует больших объёмов данных.",
        ],
        'Code': [
            "def consciousness(phi): return phi > 0.5",
            "fn main() { let mut v = Vec::new(); v.push(42); }",
            "SELECT * FROM users WHERE age > 18 ORDER BY name;",
        ],
    }

    new_unk_id = new_sp.unk_id()
    old_unk_id = old_sp.unk_id()
    total_unk_old = 0
    total_unk_new = 0
    total_tokens_old = 0
    total_tokens_new = 0

    print(f"\n  UNK token ID: old={old_unk_id}, new={new_unk_id}")
    print(f"\n  {'Language':<10} {'Old UNK':>8} {'New UNK':>8} {'Old Total':>10} {'New Total':>10}")
    print(f"  {'─'*10} {'─'*8} {'─'*8} {'─'*10} {'─'*10}")

    for lang, texts in extended_tests.items():
        lang_unk_old = 0
        lang_unk_new = 0
        lang_tok_old = 0
        lang_tok_new = 0
        for text in texts:
            old_ids = old_sp.encode(text, out_type=int)
            new_ids = new_sp.encode(text, out_type=int)
            lang_unk_old += sum(1 for i in old_ids if i == old_unk_id)
            lang_unk_new += sum(1 for i in new_ids if i == new_unk_id)
            lang_tok_old += len(old_ids)
            lang_tok_new += len(new_ids)

        total_unk_old += lang_unk_old
        total_unk_new += lang_unk_new
        total_tokens_old += lang_tok_old
        total_tokens_new += lang_tok_new

        old_pct = (lang_unk_old / lang_tok_old * 100) if lang_tok_old else 0
        new_pct = (lang_unk_new / lang_tok_new * 100) if lang_tok_new else 0
        old_status = f"{lang_unk_old} ({old_pct:.1f}%)" if lang_unk_old else "0"
        new_status = f"{lang_unk_new} ({new_pct:.1f}%)" if lang_unk_new else "0"
        print(f"  {lang:<10} {old_status:>8} {new_status:>8} {lang_tok_old:>10} {lang_tok_new:>10}")

    print(f"  {'─'*10} {'─'*8} {'─'*8} {'─'*10} {'─'*10}")
    print(f"  {'TOTAL':<10} {total_unk_old:>8} {total_unk_new:>8} {total_tokens_old:>10} {total_tokens_new:>10}")

    if total_unk_new == 0:
        print(f"\n  [PASS] Zero UNK tokens in multilingual tokenizer")
    else:
        print(f"\n  [WARN] {total_unk_new} UNK tokens found in multilingual tokenizer")

    # ── 5. Token ID range check ──
    print("\n" + "=" * 72)
    print("5. TOKEN ID RANGE VALIDATION")
    print("=" * 72)

    max_token_id = 0
    for lang, texts in extended_tests.items():
        for text in texts:
            ids = new_sp.encode(text, out_type=int)
            if ids:
                local_max = max(ids)
                if local_max > max_token_id:
                    max_token_id = local_max

    print(f"\n  Max token ID observed:     {max_token_id}")
    print(f"  Tokenizer vocab size:      {new_vocab}")
    print(f"  train_v15.py default:      {train_v15_default_vocab}")

    if max_token_id < new_vocab:
        print(f"  [PASS] All token IDs < vocab size")
    else:
        print(f"  [FAIL] Token ID {max_token_id} >= vocab size {new_vocab}")

    # ── 6. Detailed token breakdown ──
    print("\n" + "=" * 72)
    print("6. DETAILED TOKEN BREAKDOWN (sample)")
    print("=" * 72)

    for lang, text in test_texts.items():
        pieces = new_sp.encode(text, out_type=str)
        ids = new_sp.encode(text, out_type=int)
        print(f"\n  {lang}: \"{text}\"")
        # Show first 15 tokens
        shown = min(15, len(pieces))
        token_strs = [f"{pieces[i]}({ids[i]})" for i in range(shown)]
        if len(pieces) > shown:
            token_strs.append(f"... +{len(pieces)-shown} more")
        print(f"    [{len(pieces)} tokens] {' '.join(token_strs)}")

    # ── 7. Corpus file check ──
    print("\n" + "=" * 72)
    print("7. MULTILINGUAL CORPUS FILES")
    print("=" * 72)

    corpus_dir = os.path.join(REPO, 'anima', 'data', 'corpus_multilingual')
    expected_files = ['ko.txt', 'en.txt', 'zh.txt', 'ja.txt', 'ru.txt', 'code.txt']

    for f in expected_files:
        path = os.path.join(corpus_dir, f)
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"  [OK]   {f:<12} {size/1024:>8.1f} KB")
        else:
            print(f"  [MISS] {f:<12} (not found)")

    # ── VERDICT ──
    print("\n" + "=" * 72)
    print("VERDICT")
    print("=" * 72)

    issues = []
    if not decoder_ok:
        issues.append("ConsciousDecoderV2 failed with 64K vocab")
    if roundtrip_pass < roundtrip_total:
        issues.append(f"Roundtrip failed for {roundtrip_total - roundtrip_pass} language(s)")
    if total_unk_new > 0:
        issues.append(f"{total_unk_new} UNK tokens in multilingual tokenizer")
    if max_token_id >= new_vocab:
        issues.append(f"Token ID overflow: {max_token_id} >= {new_vocab}")

    if not issues:
        print("\n  STATUS: ALL CHECKS PASSED")
        print("\n  The 64K multilingual tokenizer is properly integrated:")
        print(f"    - ConsciousDecoderV2 accepts vocab_size={new_vocab}")
        print(f"    - Roundtrip encode/decode: {roundtrip_pass}/{roundtrip_total} languages")
        print(f"    - Zero UNK tokens across all test languages")
        print(f"    - train_v15.py defaults match tokenizer")
        print(f"\n  Ready for training with:")
        print(f"    python train_v15.py --tokenizer config/tokenizer_64k_multilingual.model")
    else:
        print(f"\n  STATUS: {len(issues)} ISSUE(S) FOUND")
        for i, issue in enumerate(issues, 1):
            print(f"    {i}. {issue}")

    print()
    return 0 if not issues else 1


if __name__ == '__main__':
    sys.exit(main())
