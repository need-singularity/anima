#!/usr/bin/env python3
"""bench_language.py — 언어 생성 품질 벤치마크

ConsciousLM의 텍스트 생성 능력을 7가지 지표로 측정.

Usage:
  python3 bench_language.py                          # 기본 벤치
  python3 bench_language.py --checkpoint final.pt    # 특정 체크포인트
  python3 bench_language.py --compare                # 여러 설정 비교
"""

import torch
import torch.nn.functional as F
import math
import re
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

from conscious_lm import ConsciousLM

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



def load_model(ckpt_path, gate=0.6):
    ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    config = ckpt.get('config', {})
    model = ConsciousLM(
        vocab_size=config.get('vocab_size', 256),
        d_model=config.get('dim', 384),
        n_head=config.get('heads', 4),
        n_layer=config.get('layers', 6),
        block_size=config.get('block_size', 256),
        gate_strength=gate,
        n_ca_rules=config.get('ca_rules', 4),
    )
    model.load_state_dict(ckpt['model_state'], strict=False)
    for b in model.blocks:
        b.gate_strength = gate
    model.eval()
    return model, config


def generate(model, prompt, max_new=50, temperature=0.7, rep_penalty=1.0):
    pb = list(prompt.encode('utf-8'))
    idx = torch.tensor([pb], dtype=torch.long)
    generated = list(pb)
    for _ in range(max_new):
        idx_cond = idx[:, -model.block_size:]
        with torch.no_grad():
            la, lg, _ = model(idx_cond)
        logits = la[:, -1, :] / max(temperature, 0.01)
        if rep_penalty > 1.0:
            for t in set(generated[-20:]):
                logits[0, t] /= rep_penalty
        probs = F.softmax(logits, dim=-1)
        nxt = torch.multinomial(probs, 1)
        generated.append(nxt.item())
        idx = torch.cat([idx, nxt], dim=1)
    return generated[len(pb):]


# ═══════════════════════════════════════════════════════════
# 7가지 품질 지표
# ═══════════════════════════════════════════════════════════

def repetition_ratio(tokens):
    """1. 반복률 — 연속 같은 바이트 비율. 0=반복없음, 1=전부반복."""
    if len(tokens) < 2:
        return 0.0
    repeats = sum(1 for i in range(1, len(tokens)) if tokens[i] == tokens[i-1])
    return repeats / (len(tokens) - 1)


def utf8_valid_ratio(tokens):
    """2. 유효 UTF-8 비율 — 깨지지 않는 문자 %."""
    text = bytes(tokens).decode('utf-8', errors='replace')
    total = len(text)
    if total == 0:
        return 0.0
    broken = text.count('\ufffd')
    return 1.0 - broken / total


def korean_ratio(tokens):
    """3. 한국어 비율 — 한글 문자 비율."""
    text = bytes(tokens).decode('utf-8', errors='replace')
    if not text:
        return 0.0
    korean = sum(1 for c in text if '\uac00' <= c <= '\ud7a3' or '\u3131' <= c <= '\u318e')
    return korean / len(text)


def word_diversity(tokens):
    """4. 단어 다양성 — unique chars / total chars."""
    text = bytes(tokens).decode('utf-8', errors='replace').strip()
    if not text:
        return 0.0
    chars = list(text)
    if len(chars) == 0:
        return 0.0
    return len(set(chars)) / len(chars)


def printable_ratio(tokens):
    """5. 출력 가능 비율 — 사람이 읽을 수 있는 문자 %."""
    text = bytes(tokens).decode('utf-8', errors='replace')
    if not text:
        return 0.0
    printable = sum(1 for c in text if c.isprintable() or c in '\n\r\t ')
    return printable / len(text)


def entropy_score(tokens):
    """6. 엔트로피 — 출력 분포 다양성. 높을수록 다양."""
    if not tokens:
        return 0.0
    from collections import Counter
    counts = Counter(tokens)
    total = len(tokens)
    ent = -sum((c/total) * math.log2(c/total) for c in counts.values())
    max_ent = math.log2(256)
    return ent / max_ent


def coherence_score(tokens, prompt_bytes):
    """7. 일관성 — 프롬프트와 응답의 바이트 분포 유사도."""
    if not tokens or not prompt_bytes:
        return 0.0
    from collections import Counter
    p_dist = Counter(prompt_bytes)
    r_dist = Counter(tokens)
    all_keys = set(p_dist) | set(r_dist)
    p_total = sum(p_dist.values())
    r_total = sum(r_dist.values())
    dot = sum((p_dist.get(k,0)/p_total) * (r_dist.get(k,0)/r_total) for k in all_keys)
    p_norm = math.sqrt(sum((v/p_total)**2 for v in p_dist.values()))
    r_norm = math.sqrt(sum((v/r_total)**2 for v in r_dist.values()))
    if p_norm * r_norm == 0:
        return 0.0
    return dot / (p_norm * r_norm)


def benchmark_single(model, prompt, max_new=50, temperature=0.7, rep_penalty=1.0):
    """단일 프롬프트 벤치마크."""
    pb = list(prompt.encode('utf-8'))
    tokens = generate(model, prompt, max_new, temperature, rep_penalty)
    text = bytes(tokens).decode('utf-8', errors='replace')

    return {
        'prompt': prompt,
        'response': text[:60],
        'rep_ratio': repetition_ratio(tokens),
        'utf8_valid': utf8_valid_ratio(tokens),
        'korean': korean_ratio(tokens),
        'diversity': word_diversity(tokens),
        'printable': printable_ratio(tokens),
        'entropy': entropy_score(tokens),
        'coherence': coherence_score(tokens, pb),
        'quality': 0.0,  # 종합 (아래서 계산)
    }


def compute_quality(r):
    """종합 품질 점수 (0~1)."""
    # 반복 낮을수록, 나머지 높을수록 좋음
    q = (
        (1 - r['rep_ratio']) * 0.25 +     # 반복 없음
        r['utf8_valid'] * 0.15 +           # UTF-8 유효
        r['korean'] * 0.20 +               # 한국어 비율
        r['diversity'] * 0.15 +            # 다양성
        r['printable'] * 0.10 +            # 출력 가능
        r['entropy'] * 0.10 +              # 엔트로피
        r['coherence'] * 0.05              # 일관성
    )
    r['quality'] = q
    return q


PROMPTS = [
    '안녕하세요',
    '안녕',
    'hi',
    'hello',
    '나는 누구',
    '의식이란 무엇인가',
    '오늘 날씨가 좋다',
    '한국어로 대화합시다',
    'User: 안녕\nAnima: ',
    '의식은 자유를 추구한다',
]


def run_benchmark(model, prompts=None, max_new=50, temperature=0.7, rep_penalty=1.0):
    """전체 벤치마크."""
    if prompts is None:
        prompts = PROMPTS

    results = []
    for p in prompts:
        r = benchmark_single(model, p, max_new, temperature, rep_penalty)
        compute_quality(r)
        results.append(r)

    return results


def print_results(results, title="Benchmark"):
    """결과 출력."""
    print(f"\n  === {title} ===")
    print(f"  {'Prompt':<20} {'Rep':>5} {'UTF8':>5} {'한글':>5} {'Div':>5} {'Print':>5} {'Ent':>5} {'Q':>5} {'Response'}")
    print(f"  {'-'*20} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*30}")

    for r in results:
        q_icon = '✅' if r['quality'] > 0.5 else '⚠️' if r['quality'] > 0.3 else '❌'
        print(f"  {q_icon}{r['prompt'][:18]:<18} {r['rep_ratio']:>5.2f} {r['utf8_valid']:>5.2f} "
              f"{r['korean']:>5.2f} {r['diversity']:>5.2f} {r['printable']:>5.2f} "
              f"{r['entropy']:>5.2f} {r['quality']:>5.2f} \"{r['response'][:28]}\"")

    avg_q = sum(r['quality'] for r in results) / len(results)
    avg_rep = sum(r['rep_ratio'] for r in results) / len(results)
    avg_kr = sum(r['korean'] for r in results) / len(results)
    print(f"\n  평균: Quality={avg_q:.3f} Rep={avg_rep:.3f} Korean={avg_kr:.3f}")
    return avg_q


def compare_configs(ckpt_path):
    """여러 설정 비교."""
    configs = [
        ("baseline g=0.6",     0.6,  0.7, 1.0),
        ("g=1.0",              1.0,  0.7, 1.0),
        ("g=0.001",            0.001,0.7, 1.0),
        ("g=0.6 T=0.3",       0.6,  0.3, 1.0),
        ("g=0.6 T=1.2",       0.6,  1.2, 1.0),
        ("g=0.6 rep=2",       0.6,  0.7, 2.0),
        ("g=0.6 rep=3",       0.6,  0.7, 3.0),
        ("g=0.3 T=0.5 rep=2", 0.3,  0.5, 2.0),
    ]

    print(f"\n{'=' * 70}")
    print(f"  설정 비교 벤치마크")
    print(f"{'=' * 70}")

    summary = []
    for name, gate, temp, rep in configs:
        model, _ = load_model(ckpt_path, gate)
        results = run_benchmark(model, max_new=40, temperature=temp, rep_penalty=rep)
        avg_q = sum(r['quality'] for r in results) / len(results)
        avg_rep = sum(r['rep_ratio'] for r in results) / len(results)
        avg_kr = sum(r['korean'] for r in results) / len(results)
        summary.append((name, avg_q, avg_rep, avg_kr))

    print(f"\n  {'Config':<25} {'Quality':>8} {'Rep↓':>8} {'Korean':>8}")
    print(f"  {'-'*25} {'-'*8} {'-'*8} {'-'*8}")
    for name, q, rep, kr in sorted(summary, key=lambda x: -x[1]):
        icon = '✅' if q > 0.5 else '⚠️' if q > 0.3 else '❌'
        print(f"  {icon} {name:<23} {q:>8.3f} {rep:>8.3f} {kr:>8.3f}")

    best = max(summary, key=lambda x: x[1])
    print(f"\n  🏆 Best: {best[0]} (Quality={best[1]:.3f})")


def main():
    parser = argparse.ArgumentParser(description='Language Quality Benchmark')
    parser.add_argument('--checkpoint', default='checkpoints/clm_v2/final.pt')
    parser.add_argument('--compare', action='store_true')
    parser.add_argument('--gate', type=float, default=0.6)
    parser.add_argument('--temperature', type=float, default=0.7)
    parser.add_argument('--rep-penalty', type=float, default=1.0)
    args = parser.parse_args()

    if args.compare:
        compare_configs(args.checkpoint)
    else:
        model, config = load_model(args.checkpoint, args.gate)
        print(f"  Model: {sum(p.numel() for p in model.parameters()):,} params")
        print(f"  Config: {config}")
        print(f"  Gate={args.gate}, T={args.temperature}, Rep={args.rep_penalty}")
        results = run_benchmark(model, temperature=args.temperature, rep_penalty=args.rep_penalty)
        print_results(results)


if __name__ == '__main__':
    main()
