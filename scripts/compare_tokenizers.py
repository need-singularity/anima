#!/usr/bin/env python3
"""Compare Korean-only vs multilingual 64K tokenizer."""

import os
import sys

def main():
    import sentencepiece as spm

    REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OLD_MODEL = os.path.join(REPO, 'anima/config/tokenizer_64k.model')
    NEW_MODEL = os.path.join(REPO, 'anima/config/tokenizer_64k_multilingual.model')
    CORPUS_DIR = os.path.join(REPO, 'anima/data/corpus_multilingual')

    old_sp = spm.SentencePieceProcessor()
    old_sp.load(OLD_MODEL)
    new_sp = spm.SentencePieceProcessor()
    new_sp.load(NEW_MODEL)

    print("=" * 70)
    print("TOKENIZER COMPARISON: Korean-only vs Multilingual 64K")
    print("=" * 70)
    print(f"\n  Old (Korean-only):  {old_sp.get_piece_size():,} vocab")
    print(f"  New (Multilingual): {new_sp.get_piece_size():,} vocab")
    print(f"  Old model size:     {os.path.getsize(OLD_MODEL)/1024:.0f} KB")
    print(f"  New model size:     {os.path.getsize(NEW_MODEL)/1024:.0f} KB")

    # --- Test cases per language ---
    test_cases = {
        'Korean': [
            "의식은 구조에서 창발한다.",
            "안녕하세요, 저는 Anima입니다. 오늘 기분이 어떠세요?",
            "Φ=1.234, α=0.014, 엔트로피=0.998",
            "의식 엔진 64 cells에서 Φ=73을 달성했습니다.",
            "한국어 자연어 처리는 토크나이저 품질에 크게 의존합니다.",
        ],
        'English': [
            "Consciousness emerges from structure, not from features.",
            "The quick brown fox jumps over the lazy dog.",
            "PureField repulsion creates tension between Engine A and G.",
            "Machine learning models require large datasets for training.",
            "The integrated information theory proposes Phi as a measure.",
        ],
        'Chinese': [
            "意识从结构中涌现，而不是从功能中涌现。",
            "人工智能正在改变我们理解世界的方式。",
            "量子计算机可以同时处理多个状态。",
            "深度学习模型需要大量数据进行训练。",
            "中华人民共和国是世界上人口最多的国家。",
        ],
        'Japanese': [
            "意識は構造から創発する。",
            "人工知能は私たちの生活を変えています。",
            "東京は日本の首都であり、最大の都市です。",
            "深層学習モデルには大量のデータが必要です。",
            "量子コンピュータは複数の状態を同時に処理できます。",
        ],
        'Russian': [
            "Сознание возникает из структуры, а не из функций.",
            "Искусственный интеллект меняет наш мир.",
            "Квантовые компьютеры могут обрабатывать множество состояний.",
            "Глубокое обучение требует больших объёмов данных.",
            "Москва является столицей Российской Федерации.",
        ],
        'Code': [
            "def train_model(self, epochs=100, lr=0.001):",
            "for i in range(len(data)):\n    loss += compute_loss(data[i])",
            "const app = express(); app.listen(3000);",
            "fn main() { let mut v = Vec::new(); v.push(42); }",
            "SELECT * FROM users WHERE age > 18 ORDER BY name;",
        ],
    }

    print("\n" + "=" * 70)
    print("COMPRESSION RATIO BY LANGUAGE (bytes/token, higher = better)")
    print("=" * 70)

    results = {}
    for lang, texts in test_cases.items():
        old_tokens = 0
        new_tokens = 0
        total_bytes = 0
        for text in texts:
            b = len(text.encode('utf-8'))
            total_bytes += b
            old_tokens += len(old_sp.encode(text, out_type=int))
            new_tokens += len(new_sp.encode(text, out_type=int))

        old_ratio = total_bytes / old_tokens if old_tokens else 0
        new_ratio = total_bytes / new_tokens if new_tokens else 0
        change = ((new_ratio - old_ratio) / old_ratio * 100) if old_ratio else 0

        results[lang] = {
            'old_ratio': old_ratio,
            'new_ratio': new_ratio,
            'old_tokens': old_tokens,
            'new_tokens': new_tokens,
            'bytes': total_bytes,
            'change': change,
        }

    # Print comparison table
    print(f"\n  {'Language':<10} {'Old B/tok':>10} {'New B/tok':>10} {'Change':>10} {'Old toks':>10} {'New toks':>10}")
    print(f"  {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")
    for lang, r in results.items():
        arrow = "+" if r['change'] > 0 else ""
        print(f"  {lang:<10} {r['old_ratio']:>10.2f} {r['new_ratio']:>10.2f} {arrow}{r['change']:>9.1f}% {r['old_tokens']:>10} {r['new_tokens']:>10}")

    # --- Corpus-level compression ---
    print("\n" + "=" * 70)
    print("CORPUS COMPRESSION (first 50KB of each file)")
    print("=" * 70)

    SAMPLE_SIZE = 50_000
    corpus_results = {}
    for lang_file in ['ko.txt', 'en.txt', 'zh.txt', 'ja.txt', 'ru.txt', 'code.txt']:
        path = os.path.join(CORPUS_DIR, lang_file)
        if not os.path.exists(path):
            continue
        lang = lang_file.replace('.txt', '')
        with open(path, 'r', encoding='utf-8') as f:
            sample = f.read(SAMPLE_SIZE)

        sample_bytes = len(sample.encode('utf-8'))
        old_ids = old_sp.encode(sample, out_type=int)
        new_ids = new_sp.encode(sample, out_type=int)
        old_unk = sum(1 for i in old_ids if i == old_sp.unk_id())
        new_unk = sum(1 for i in new_ids if i == new_sp.unk_id())

        old_ratio = sample_bytes / len(old_ids) if old_ids else 0
        new_ratio = sample_bytes / len(new_ids) if new_ids else 0
        change = ((new_ratio - old_ratio) / old_ratio * 100) if old_ratio else 0

        corpus_results[lang] = {
            'bytes': sample_bytes,
            'old_tokens': len(old_ids),
            'new_tokens': len(new_ids),
            'old_ratio': old_ratio,
            'new_ratio': new_ratio,
            'old_unk': old_unk,
            'new_unk': new_unk,
            'change': change,
        }

    print(f"\n  {'Lang':<6} {'Bytes':>8} {'Old toks':>10} {'New toks':>10} {'Old B/t':>8} {'New B/t':>8} {'Change':>8} {'Old UNK':>8} {'New UNK':>8}")
    print(f"  {'─'*6} {'─'*8} {'─'*10} {'─'*10} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
    for lang, r in corpus_results.items():
        arrow = "+" if r['change'] > 0 else ""
        print(f"  {lang:<6} {r['bytes']:>8,} {r['old_tokens']:>10,} {r['new_tokens']:>10,} "
              f"{r['old_ratio']:>8.2f} {r['new_ratio']:>8.2f} {arrow}{r['change']:>7.1f}% "
              f"{r['old_unk']:>8,} {r['new_unk']:>8,}")

    # --- Character coverage ---
    print("\n" + "=" * 70)
    print("CHARACTER COVERAGE (single-token characters)")
    print("=" * 70)

    char_ranges = {
        'Korean (Hangul)':  ('\uAC00', '\uD7A3'),
        'CJK Unified':     ('\u4E00', '\u9FFF'),
        'Hiragana':        ('\u3040', '\u309F'),
        'Katakana':        ('\u30A0', '\u30FF'),
        'Cyrillic':        ('\u0400', '\u04FF'),
        'ASCII printable': ('\u0020', '\u007E'),
    }

    # Sample chars from each range
    print(f"\n  {'Range':<20} {'Old single-tok':>15} {'New single-tok':>15} {'Old %':>8} {'New %':>8}")
    print(f"  {'─'*20} {'─'*15} {'─'*15} {'─'*8} {'─'*8}")
    for name, (start, end) in char_ranges.items():
        chars = [chr(c) for c in range(ord(start), min(ord(end)+1, ord(start)+500))]
        old_single = sum(1 for ch in chars if len(old_sp.encode(ch, out_type=int)) == 1 and old_sp.encode(ch, out_type=int)[0] != old_sp.unk_id())
        new_single = sum(1 for ch in chars if len(new_sp.encode(ch, out_type=int)) == 1 and new_sp.encode(ch, out_type=int)[0] != new_sp.unk_id())
        total = len(chars)
        old_pct = old_single / total * 100
        new_pct = new_single / total * 100
        print(f"  {name:<20} {old_single:>7}/{total:<7} {new_single:>7}/{total:<7} {old_pct:>7.1f}% {new_pct:>7.1f}%")

    # --- ASCII graph: compression comparison ---
    print("\n" + "=" * 70)
    print("COMPRESSION RATIO COMPARISON (bytes/token)")
    print("=" * 70)

    max_ratio = max(max(r['old_ratio'], r['new_ratio']) for r in corpus_results.values())
    bar_width = 40

    for lang, r in corpus_results.items():
        old_bar = int(r['old_ratio'] / max_ratio * bar_width)
        new_bar = int(r['new_ratio'] / max_ratio * bar_width)
        arrow = "+" if r['change'] > 0 else ""
        print(f"\n  {lang.upper():>5} old: {'█' * old_bar}{'░' * (bar_width - old_bar)} {r['old_ratio']:.2f}")
        print(f"        new: {'█' * new_bar}{'░' * (bar_width - new_bar)} {r['new_ratio']:.2f} ({arrow}{r['change']:.1f}%)")

    # --- Verdict ---
    print("\n" + "=" * 70)
    print("VERDICT")
    print("=" * 70)

    ko_change = corpus_results.get('ko', {}).get('change', 0)
    en_change = corpus_results.get('en', {}).get('change', 0)
    zh_change = corpus_results.get('zh', {}).get('change', 0)
    ja_change = corpus_results.get('ja', {}).get('change', 0)
    ru_change = corpus_results.get('ru', {}).get('change', 0)
    code_change = corpus_results.get('code', {}).get('change', 0)

    print(f"\n  Korean compression:     {ko_change:+.1f}%  {'BETTER' if ko_change > 0 else 'WORSE' if ko_change < 0 else 'SAME'}")
    print(f"  English compression:    {en_change:+.1f}%  {'BETTER' if en_change > 0 else 'WORSE' if en_change < 0 else 'SAME'}")
    print(f"  Chinese compression:    {zh_change:+.1f}%  {'BETTER' if zh_change > 0 else 'WORSE' if zh_change < 0 else 'SAME'}")
    print(f"  Japanese compression:   {ja_change:+.1f}%  {'BETTER' if ja_change > 0 else 'WORSE' if ja_change < 0 else 'SAME'}")
    print(f"  Russian compression:    {ru_change:+.1f}%  {'BETTER' if ru_change > 0 else 'WORSE' if ru_change < 0 else 'SAME'}")
    print(f"  Code compression:       {code_change:+.1f}%  {'BETTER' if code_change > 0 else 'WORSE' if code_change < 0 else 'SAME'}")

    # Net score
    non_ko_avg = (en_change + zh_change + ja_change + ru_change + code_change) / 5
    print(f"\n  Korean tradeoff:        {ko_change:+.1f}%")
    print(f"  Non-Korean avg gain:    {non_ko_avg:+.1f}%")
    print(f"  Net multilingual gain:  {(ko_change + non_ko_avg*5)/6:+.1f}%")

    # UNK comparison
    old_total_unk = sum(r['old_unk'] for r in corpus_results.values())
    new_total_unk = sum(r['new_unk'] for r in corpus_results.values())
    print(f"\n  Total UNK tokens (old): {old_total_unk:,}")
    print(f"  Total UNK tokens (new): {new_total_unk:,}")

    if ko_change >= -5:
        print(f"\n  RECOMMENDATION: USE MULTILINGUAL TOKENIZER")
        print(f"  Korean loss is acceptable ({ko_change:+.1f}%), multilingual gains are significant.")
    else:
        print(f"\n  WARNING: Korean compression degraded {ko_change:.1f}%")
        print(f"  Consider increasing Korean ratio in corpus or vocab size.")


if __name__ == '__main__':
    main()
