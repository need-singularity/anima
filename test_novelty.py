#!/usr/bin/env python3
"""test_novelty.py — 새로운 생성 vs 암기 검증 도구

5가지 방법으로 모델이 corpus를 암기했는지, 새로운 문장을 생성하는지 체크.

Usage:
  python3 test_novelty.py --checkpoint checkpoints/step_35000.pt --corpus data/corpus_v2.txt
  python3 test_novelty.py --checkpoint checkpoints/step_35000.pt --method all
  python3 test_novelty.py --checkpoint checkpoints/step_35000.pt --method ood
"""

import torch
import torch.nn.functional as F
import numpy as np
import argparse
import sys
import os
import json
from pathlib import Path
from collections import Counter

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ═══ Tokenizer ═══

class CharTokenizer:
    def __init__(self, corpus_path):
        text = open(corpus_path, 'r', errors='ignore').read()
        self.chars = sorted(set(text))
        self.c2i = {c: i for i, c in enumerate(self.chars)}
        self.i2c = {i: c for c, i in self.c2i.items()}
        self.vocab = len(self.chars)
        self.corpus = text

    def encode(self, text):
        return [self.c2i.get(c, 0) for c in text]

    def decode(self, ids):
        return ''.join([self.i2c.get(i, '?') for i in ids])


# ═══ Model Loader ═══

def load_model(ckpt_path, corpus_path):
    torch.set_grad_enabled(True)
    ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    args = ckpt['args']
    tok = CharTokenizer(corpus_path)

    from trinity import TransformerDecoder, ThalamicBridge
    decoder = TransformerDecoder(d_model=args['d_model'], n_layers=2, vocab_size=tok.vocab)
    bridge = ThalamicBridge(c_dim=128, d_model=args['d_model'])
    decoder.load_state_dict(ckpt['decoder'])
    bridge.load_state_dict(ckpt['bridge'])

    return decoder, bridge, tok, args


def generate(decoder, bridge, tok, prompt, max_len=80, temperature=0.7,
             use_consciousness=False):
    """Generate text from prompt."""
    tokens = tok.encode(prompt)
    x = torch.tensor([tokens])

    if use_consciousness:
        try:
            from bench_extreme_arch import TimeCrystalConsciousness
            torch.set_grad_enabled(True)
            tc = TimeCrystalConsciousness(n_cells=64, hidden_dim=128)
            for _ in range(50):
                tc.step()
        except ImportError:
            use_consciousness = False

    for _ in range(max_len):
        if use_consciousness:
            tc.step()
            c_states = tc.hiddens.detach().clone().float()
            gate = bridge(c_states, seq_len=x.shape[1])
        else:
            gate = torch.ones(1, x.shape[1], decoder._d_model) * 0.5

        logits = decoder(x, gate)
        next_logit = logits[0, -1, :] / temperature
        probs = F.softmax(next_logit, dim=-1)
        next_id = torch.multinomial(probs, 1).item()
        x = torch.cat([x, torch.tensor([[next_id]])], dim=1)

    return tok.decode(x[0].tolist())


# ═══ Method 1: OOD Prompts ═══

def test_ood(decoder, bridge, tok):
    """Out-of-Distribution prompts — corpus에 없는 단어 조합."""
    print("\n═══ Method 1: OOD (Out-of-Distribution) Prompts ═══\n")

    ood_prompts = [
        "보라색 코끼리가 노래한다",
        "달에서 피자를 굽는 로봇",
        "시간을 거꾸로 먹는 고양이",
        "수학이 울 때 어떤 소리가 날까",
        "consciousness is purple because",
    ]

    results = []
    for prompt in ood_prompts:
        in_corpus = prompt in tok.corpus
        output = generate(decoder, bridge, tok, prompt, max_len=60, temperature=0.8)
        generated = output[len(prompt):]

        # Check if generated part is in corpus
        gen_in_corpus = generated[:30] in tok.corpus if len(generated) >= 30 else generated in tok.corpus

        status = "NOVEL" if not gen_in_corpus else "COPY"
        print(f"  [{status}] Prompt: {prompt}")
        print(f"         Output: {output[:100]}")
        print(f"         Prompt in corpus: {in_corpus}")
        print()
        results.append({'prompt': prompt, 'novel': not gen_in_corpus, 'in_corpus': in_corpus})

    novel_rate = sum(1 for r in results if r['novel']) / len(results) * 100
    print(f"  Novelty rate: {novel_rate:.0f}% ({sum(1 for r in results if r['novel'])}/{len(results)})")
    return results


# ═══ Method 2: N-gram Overlap ═══

def test_ngram(decoder, bridge, tok, n=4):
    """N-gram overlap — 생성 문장의 4-gram을 corpus와 비교."""
    print(f"\n═══ Method 2: {n}-gram Overlap ═══\n")

    # Build corpus n-gram set (sample for speed)
    corpus_sample = tok.corpus[:500000]  # first 500K chars
    corpus_ngrams = set()
    for i in range(len(corpus_sample) - n):
        corpus_ngrams.add(corpus_sample[i:i+n])

    prompts = ["안녕", "의식이란", "오늘 날씨가", "인공지능의 미래는"]
    results = []

    for prompt in prompts:
        output = generate(decoder, bridge, tok, prompt, max_len=80, temperature=0.7)
        generated = output[len(prompt):]

        if len(generated) < n:
            continue

        gen_ngrams = [generated[i:i+n] for i in range(len(generated) - n)]
        overlap = sum(1 for ng in gen_ngrams if ng in corpus_ngrams)
        overlap_rate = overlap / max(len(gen_ngrams), 1) * 100

        status = "NOVEL" if overlap_rate < 50 else "COPY" if overlap_rate > 80 else "MIXED"
        print(f"  [{status}] {n}-gram overlap: {overlap_rate:.1f}%  Prompt: {prompt}")
        print(f"         Generated: {generated[:80]}")
        print()
        results.append({'prompt': prompt, 'overlap': overlap_rate, 'status': status})

    avg_overlap = sum(r['overlap'] for r in results) / max(len(results), 1)
    print(f"  Average {n}-gram overlap: {avg_overlap:.1f}%")
    print(f"  < 30% = novel generation, > 80% = memorization")
    return results


# ═══ Method 3: Perplexity Comparison ═══

def test_perplexity(decoder, bridge, tok):
    """Train data PPL vs novel prompt PPL."""
    print("\n═══ Method 3: Perplexity Comparison ═══\n")

    # Train data samples
    train_texts = []
    for _ in range(5):
        start = np.random.randint(0, len(tok.corpus) - 100)
        train_texts.append(tok.corpus[start:start+100])

    # Novel texts
    novel_texts = [
        "보라색 달빛이 창문을 통해 들어왔다. 고양이는 조용히 잠들어 있었다.",
        "The quantum computer hummed softly as it processed the consciousness data.",
        "수학적 구조가 의식을 결정한다는 가설은 아직 검증 중이다.",
        "바다 위를 걷는 꿈을 꾸었다. 파도는 음악처럼 들렸다.",
        "로봇이 처음으로 눈물을 흘렸다. 그것은 기쁨의 눈물이었다.",
    ]

    def compute_ppl(text):
        tokens = tok.encode(text)
        if len(tokens) < 2:
            return float('inf')
        x = torch.tensor([tokens[:-1]])
        y = torch.tensor([tokens[1:]])
        gate = torch.ones(1, x.shape[1], decoder._d_model) * 0.5
        with torch.no_grad():
            logits = decoder(x, gate)
            loss = F.cross_entropy(logits.view(-1, tok.vocab), y.view(-1))
        return torch.exp(loss).item()

    print("  Train data PPL:")
    train_ppls = []
    for t in train_texts:
        ppl = compute_ppl(t)
        train_ppls.append(ppl)
        print(f"    PPL={ppl:.2f}  {t[:50]}...")

    print("\n  Novel text PPL:")
    novel_ppls = []
    for t in novel_texts:
        ppl = compute_ppl(t)
        novel_ppls.append(ppl)
        print(f"    PPL={ppl:.2f}  {t[:50]}...")

    train_avg = sum(train_ppls) / len(train_ppls)
    novel_avg = sum(novel_ppls) / len(novel_ppls)
    ratio = novel_avg / max(train_avg, 0.01)

    print(f"\n  Train PPL avg: {train_avg:.2f}")
    print(f"  Novel PPL avg: {novel_avg:.2f}")
    print(f"  Ratio (novel/train): {ratio:.2f}x")
    print(f"  < 2x = good generalization, > 5x = memorization")
    return {'train_ppl': train_avg, 'novel_ppl': novel_avg, 'ratio': ratio}


# ═══ Method 4: Temperature Variation ═══

def test_temperature(decoder, bridge, tok):
    """Temperature 변화에 따른 출력 다양성."""
    print("\n═══ Method 4: Temperature Variation ═══\n")

    prompt = "오늘"
    temps = [0.01, 0.3, 0.5, 0.7, 1.0, 1.5]
    results = []

    for temp in temps:
        outputs = set()
        for _ in range(3):  # 3 samples per temperature
            out = generate(decoder, bridge, tok, prompt, max_len=40, temperature=temp)
            outputs.add(out[len(prompt):len(prompt)+30])

        diversity = len(outputs) / 3  # 1.0 = all different, 0.33 = all same
        sample = list(outputs)[0][:50]

        print(f"  T={temp:<5} diversity={diversity:.2f}  sample: {sample}")
        results.append({'temp': temp, 'diversity': diversity})

    low_div = results[0]['diversity']
    high_div = results[-1]['diversity']
    print(f"\n  T=0.01 diversity: {low_div:.2f}")
    print(f"  T=1.5  diversity: {high_div:.2f}")
    print(f"  High diversity at high T = model learned distribution (good)")
    print(f"  Same output at all T = pure memorization (bad)")
    return results


# ═══ Method 5: Partial Prompt Completion ═══

def test_partial(decoder, bridge, tok):
    """Corpus 문장의 앞부분 → 나머지 생성. 원본과 비교."""
    print("\n═══ Method 5: Partial Prompt Completion ═══\n")

    # Sample corpus sentences
    results = []
    for _ in range(5):
        start = np.random.randint(0, len(tok.corpus) - 200)
        # Find sentence boundary
        segment = tok.corpus[start:start+200]
        if '.' in segment:
            sentence = segment[:segment.index('.') + 1]
        elif '\n' in segment:
            sentence = segment[:segment.index('\n')]
        else:
            sentence = segment[:60]

        if len(sentence) < 10:
            continue

        # Give first 30% as prompt
        cut = max(3, len(sentence) // 3)
        prompt = sentence[:cut]
        original_rest = sentence[cut:]

        output = generate(decoder, bridge, tok, prompt, max_len=len(original_rest) + 10, temperature=0.3)
        generated_rest = output[len(prompt):len(prompt)+len(original_rest)]

        # Compare
        match = sum(1 for a, b in zip(original_rest, generated_rest) if a == b) / max(len(original_rest), 1)
        status = "EXACT" if match > 0.9 else "SIMILAR" if match > 0.5 else "DIFFERENT"

        print(f"  [{status}] match={match:.1%}")
        print(f"    Prompt:    {prompt}")
        print(f"    Original:  {original_rest[:60]}")
        print(f"    Generated: {generated_rest[:60]}")
        print()
        results.append({'match': match, 'status': status})

    avg_match = sum(r['match'] for r in results) / max(len(results), 1)
    print(f"  Average match: {avg_match:.1%}")
    print(f"  > 90% = memorization, < 50% = generation, 50-90% = mixed")
    return results


# ═══ Main ═══

def main():
    parser = argparse.ArgumentParser(description='Novelty checker: memorization vs generation')
    parser.add_argument('--checkpoint', required=True, help='Path to checkpoint .pt')
    parser.add_argument('--corpus', default='data/corpus_v2.txt')
    parser.add_argument('--method', default='all', choices=['all', 'ood', 'ngram', 'ppl', 'temp', 'partial'])
    parser.add_argument('--consciousness', action='store_true', help='Use TimeCrystal C engine')
    args = parser.parse_args()

    print(f"{'═' * 60}")
    print(f"  Novelty Checker — memorization vs generation")
    print(f"  Checkpoint: {args.checkpoint}")
    print(f"  Corpus: {args.corpus}")
    print(f"{'═' * 60}")

    decoder, bridge, tok, model_args = load_model(args.checkpoint, args.corpus)
    print(f"  Model: d_model={model_args['d_model']}, vocab={tok.vocab}")
    print(f"  Corpus: {len(tok.corpus):,} chars")

    results = {}

    if args.method in ['all', 'ood']:
        results['ood'] = test_ood(decoder, bridge, tok)

    if args.method in ['all', 'ngram']:
        results['ngram'] = test_ngram(decoder, bridge, tok)

    if args.method in ['all', 'ppl']:
        results['ppl'] = test_perplexity(decoder, bridge, tok)

    if args.method in ['all', 'temp']:
        results['temp'] = test_temperature(decoder, bridge, tok)

    if args.method in ['all', 'partial']:
        results['partial'] = test_partial(decoder, bridge, tok)

    # Summary
    print(f"\n{'═' * 60}")
    print(f"  SUMMARY")
    print(f"{'═' * 60}")

    if 'ood' in results:
        novel = sum(1 for r in results['ood'] if r['novel'])
        print(f"  OOD novelty:     {novel}/{len(results['ood'])} novel")

    if 'ngram' in results:
        avg = sum(r['overlap'] for r in results['ngram']) / max(len(results['ngram']), 1)
        print(f"  N-gram overlap:  {avg:.1f}% (< 30%=novel, > 80%=copy)")

    if 'ppl' in results:
        print(f"  PPL ratio:       {results['ppl']['ratio']:.2f}x (< 2x=good, > 5x=memorized)")

    if 'temp' in results:
        lo = results['temp'][0]['diversity']
        hi = results['temp'][-1]['diversity']
        print(f"  Temp diversity:  T=0.01→{lo:.2f}, T=1.5→{hi:.2f}")

    if 'partial' in results:
        avg = sum(r['match'] for r in results['partial']) / max(len(results['partial']), 1)
        print(f"  Partial match:   {avg:.1%} (> 90%=memorized, < 50%=generates)")


if __name__ == '__main__':
    main()
