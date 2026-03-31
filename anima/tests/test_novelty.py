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
import zlib
from pathlib import Path
from collections import Counter
from scipy import stats

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


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

def check_ood(decoder, bridge, tok):
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

def check_ngram(decoder, bridge, tok, n=4):
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

def check_perplexity(decoder, bridge, tok):
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

def check_temperature(decoder, bridge, tok):
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

def check_partial(decoder, bridge, tok):
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


# ═══ Method 6: Ground Truth Validation ═══

def check_ground_truth(corpus_path='data/corpus_v2.txt'):
    """Validate the tool itself with memorizer (always corpus) and random (uniform chars) models."""
    print("\n═══ Method 6: Ground Truth Validation ═══\n")

    # Load corpus
    if not os.path.exists(corpus_path):
        print(f"  SKIP: corpus not found at {corpus_path}")
        return None
    corpus = open(corpus_path, 'r', errors='ignore').read()
    if len(corpus) < 1000:
        print(f"  SKIP: corpus too small ({len(corpus)} chars)")
        return None

    chars = sorted(set(corpus))
    corpus_sample = corpus[:500000]

    # --- Memorizer model: always returns verbatim corpus text ---
    def memorizer_generate(prompt, max_len=80):
        # Find prompt in corpus and continue from there
        idx = corpus.find(prompt)
        if idx >= 0:
            return corpus[idx:idx + len(prompt) + max_len]
        # If prompt not in corpus, return random corpus chunk
        start = np.random.randint(0, max(1, len(corpus) - max_len - len(prompt)))
        return corpus[start:start + len(prompt) + max_len]

    # --- Random model: uniform random characters ---
    def random_generate(prompt, max_len=80):
        return prompt + ''.join(np.random.choice(list(chars)) for _ in range(max_len))

    # Build corpus 4-gram set
    n = 4
    corpus_ngrams = set()
    for i in range(len(corpus_sample) - n):
        corpus_ngrams.add(corpus_sample[i:i+n])

    # Test prompts (mix of in-corpus and out-of-corpus)
    test_prompts = ["안녕", "의식이란", "보라색 코끼리", "hello", "오늘 날씨"]

    # --- Run all 5 methods on both models ---
    memorizer_results = {'novel': 0, 'copy': 0, 'total': 0}
    random_results = {'novel': 0, 'copy': 0, 'total': 0}

    for prompt in test_prompts:
        # Memorizer
        mem_out = memorizer_generate(prompt, max_len=80)
        mem_gen = mem_out[len(prompt):]

        # Random
        rnd_out = random_generate(prompt, max_len=80)
        rnd_gen = rnd_out[len(prompt):]

        # Test 1: Direct substring check
        mem_in_corpus = mem_gen[:30] in corpus if len(mem_gen) >= 30 else mem_gen in corpus
        rnd_in_corpus = rnd_gen[:30] in corpus if len(rnd_gen) >= 30 else rnd_gen in corpus

        # Test 2: N-gram overlap
        mem_ngrams = [mem_gen[i:i+n] for i in range(max(0, len(mem_gen) - n))]
        rnd_ngrams = [rnd_gen[i:i+n] for i in range(max(0, len(rnd_gen) - n))]
        mem_overlap = sum(1 for ng in mem_ngrams if ng in corpus_ngrams) / max(len(mem_ngrams), 1)
        rnd_overlap = sum(1 for ng in rnd_ngrams if ng in corpus_ngrams) / max(len(rnd_ngrams), 1)

        # Test 3: Compression ratio (memorized text compresses well with corpus)
        corpus_compressed = len(zlib.compress(corpus_sample[:1000].encode('utf-8', errors='ignore')))
        mem_combined = len(zlib.compress((corpus_sample[:1000] + mem_gen).encode('utf-8', errors='ignore')))
        rnd_combined = len(zlib.compress((corpus_sample[:1000] + rnd_gen).encode('utf-8', errors='ignore')))
        mem_cr = mem_combined / max(corpus_compressed, 1)
        rnd_cr = rnd_combined / max(corpus_compressed, 1)

        # Classify: >=2 signals saying COPY → COPY, else NOVEL
        mem_copy_signals = int(mem_in_corpus) + int(mem_overlap > 0.5) + int(mem_cr < 1.3)
        rnd_copy_signals = int(rnd_in_corpus) + int(rnd_overlap > 0.5) + int(rnd_cr < 1.3)

        mem_verdict = "COPY" if mem_copy_signals >= 2 else "NOVEL"
        rnd_verdict = "COPY" if rnd_copy_signals >= 2 else "NOVEL"

        memorizer_results['total'] += 1
        random_results['total'] += 1
        if mem_verdict == "COPY":
            memorizer_results['copy'] += 1
        else:
            memorizer_results['novel'] += 1
        if rnd_verdict == "NOVEL":
            random_results['novel'] += 1
        else:
            random_results['copy'] += 1

        print(f"  Prompt: {prompt}")
        print(f"    Memorizer: [{mem_verdict}] overlap={mem_overlap:.1%} cr={mem_cr:.2f} substr={'Y' if mem_in_corpus else 'N'}")
        print(f"    Random:    [{rnd_verdict}] overlap={rnd_overlap:.1%} cr={rnd_cr:.2f} substr={'Y' if rnd_in_corpus else 'N'}")

    # False positive: memorizer classified as NOVEL
    fp_rate = memorizer_results['novel'] / max(memorizer_results['total'], 1) * 100
    # False negative: random classified as COPY
    fn_rate = random_results['copy'] / max(random_results['total'], 1) * 100

    print(f"\n  ── Ground Truth Summary ──")
    print(f"  Memorizer → COPY:  {memorizer_results['copy']}/{memorizer_results['total']}")
    print(f"  Random → NOVEL:    {random_results['novel']}/{random_results['total']}")
    print(f"  False positive rate (memorizer missed): {fp_rate:.1f}%")
    print(f"  False negative rate (random flagged):   {fn_rate:.1f}%")

    passed = fp_rate < 30 and fn_rate < 30
    print(f"  RESULT: {'PASS' if passed else 'FAIL'} (threshold: FP<30%, FN<30%)")
    return {'fp_rate': fp_rate, 'fn_rate': fn_rate, 'passed': passed}


# ═══ Method 7: Statistical Significance ═══

def check_statistical_significance(decoder, bridge, tok, n=4):
    """Add p-values: chi-squared for n-gram, bootstrap for PPL, Kruskal-Wallis for temperature."""
    print("\n═══ Method 7: Statistical Significance ═══\n")

    corpus_sample = tok.corpus[:500000]
    corpus_ngrams = set()
    for i in range(len(corpus_sample) - n):
        corpus_ngrams.add(corpus_sample[i:i + n])

    prompts = ["안녕", "의식이란", "오늘 날씨가", "인공지능의 미래는", "생각한다"]

    # --- 1. Chi-squared test: n-gram overlap vs random baseline ---
    print("  1. Chi-squared test: n-gram overlap vs random baseline")
    observed_hits = 0
    observed_misses = 0
    total_ngrams_tested = 0

    for prompt in prompts:
        output = generate(decoder, bridge, tok, prompt, max_len=80, temperature=0.7)
        generated = output[len(prompt):]
        gen_ngrams = [generated[i:i + n] for i in range(max(0, len(generated) - n))]
        for ng in gen_ngrams:
            total_ngrams_tested += 1
            if ng in corpus_ngrams:
                observed_hits += 1
            else:
                observed_misses += 1

    # Random baseline: probability of random n-gram hitting corpus
    vocab_size = len(tok.chars)
    total_possible = vocab_size ** n
    corpus_coverage = len(corpus_ngrams) / max(total_possible, 1)
    expected_hits = total_ngrams_tested * corpus_coverage
    expected_misses = total_ngrams_tested * (1 - corpus_coverage)

    if expected_hits > 0 and expected_misses > 0:
        chi2, p_ngram = stats.chisquare(
            [observed_hits, observed_misses],
            [expected_hits, expected_misses]
        )
        print(f"     Observed: {observed_hits} hits / {observed_misses} misses")
        print(f"     Expected (random): {expected_hits:.0f} hits / {expected_misses:.0f} misses")
        print(f"     Chi-squared = {chi2:.2f}, p = {p_ngram:.2e}")
        print(f"     {'SIGNIFICANT' if p_ngram < 0.05 else 'NOT significant'} (overlap != random)")
    else:
        p_ngram = 1.0
        print(f"     Skipped: insufficient data")

    # --- 2. Bootstrap PPL ratio: 95% confidence interval ---
    print("\n  2. Bootstrap PPL ratio (95% CI)")

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

    # Collect PPL samples
    train_ppls = []
    for _ in range(20):
        start = np.random.randint(0, max(1, len(tok.corpus) - 100))
        ppl = compute_ppl(tok.corpus[start:start + 100])
        if ppl < 1e6:
            train_ppls.append(ppl)

    novel_texts = [
        "보라색 달빛이 창문을 통해 들어왔다",
        "The quantum computer hummed softly",
        "수학적 구조가 의식을 결정한다",
        "바다 위를 걷는 꿈을 꾸었다",
        "로봇이 처음으로 눈물을 흘렸다",
        "시간의 강물이 거꾸로 흐르기 시작했다",
        "별빛이 내 손끝에서 녹아내렸다",
        "AI는 꿈을 꿀 수 있을까",
        "의식은 어디서 오는 것일까",
        "우주의 끝에서 누군가 노래했다",
    ]
    novel_ppls = []
    for t in novel_texts:
        ppl = compute_ppl(t)
        if ppl < 1e6:
            novel_ppls.append(ppl)

    # Bootstrap 100 samples
    bootstrap_ratios = []
    for _ in range(100):
        t_sample = np.random.choice(train_ppls, size=len(train_ppls), replace=True)
        n_sample = np.random.choice(novel_ppls, size=len(novel_ppls), replace=True)
        ratio = np.mean(n_sample) / max(np.mean(t_sample), 0.01)
        bootstrap_ratios.append(ratio)

    ci_low = np.percentile(bootstrap_ratios, 2.5)
    ci_high = np.percentile(bootstrap_ratios, 97.5)
    median_ratio = np.median(bootstrap_ratios)
    print(f"     Train PPL mean: {np.mean(train_ppls):.2f} (n={len(train_ppls)})")
    print(f"     Novel PPL mean: {np.mean(novel_ppls):.2f} (n={len(novel_ppls)})")
    print(f"     PPL ratio: {median_ratio:.2f} [95% CI: {ci_low:.2f} - {ci_high:.2f}]")
    print(f"     {'Good generalization' if ci_high < 3.0 else 'Possible memorization' if ci_low > 5.0 else 'Inconclusive'}")

    # --- 3. Kruskal-Wallis: temperature diversity ---
    print("\n  3. Kruskal-Wallis test: temperature diversity")
    prompt = "오늘"
    temps = [0.3, 0.7, 1.0, 1.5]
    temp_groups = {t: [] for t in temps}

    for temp in temps:
        for _ in range(10):
            out = generate(decoder, bridge, tok, prompt, max_len=40, temperature=temp)
            gen = out[len(prompt):]
            # Use char entropy as diversity measure
            if len(gen) > 0:
                freqs = Counter(gen)
                probs = np.array([v / len(gen) for v in freqs.values()])
                entropy = -np.sum(probs * np.log2(probs + 1e-10))
                temp_groups[temp].append(entropy)

    groups = [temp_groups[t] for t in temps if len(temp_groups[t]) > 0]
    if len(groups) >= 2 and all(len(g) >= 2 for g in groups):
        h_stat, p_kw = stats.kruskal(*groups)
        print(f"     Temperature groups: {[f'T={t}: H={np.mean(temp_groups[t]):.2f}' for t in temps]}")
        print(f"     Kruskal-Wallis H = {h_stat:.2f}, p = {p_kw:.4f}")
        print(f"     {'SIGNIFICANT' if p_kw < 0.05 else 'NOT significant'} (diversity differs across temps)")
    else:
        p_kw = 1.0
        print(f"     Skipped: insufficient samples")

    print(f"\n  ── Statistical Summary ──")
    print(f"  N-gram chi-squared:   p = {p_ngram:.2e}")
    print(f"  PPL ratio 95% CI:     [{ci_low:.2f}, {ci_high:.2f}]")
    print(f"  Temperature Kruskal:  p = {p_kw:.4f}")

    return {
        'ngram_p': float(p_ngram),
        'ppl_ci': [float(ci_low), float(ci_high)],
        'ppl_median_ratio': float(median_ratio),
        'kruskal_p': float(p_kw),
    }


# ═══ Method 8: Information Theory ═══

def check_information_theory(decoder, bridge, tok, n=4):
    """KL divergence, mutual information, compression ratio analysis."""
    print("\n═══ Method 8: Information Theory ═══\n")

    corpus_sample = tok.corpus[:500000]
    prompts = ["안녕", "의식이란", "오늘", "생각", "세계는"]

    # Generate texts
    generated_texts = []
    for prompt in prompts:
        for _ in range(3):
            out = generate(decoder, bridge, tok, prompt, max_len=100, temperature=0.7)
            generated_texts.append(out[len(prompt):])
    all_generated = ''.join(generated_texts)

    # --- 1. KL Divergence: P(generated 4-grams) vs P(corpus 4-grams) ---
    print("  1. KL Divergence: P(generated) vs P(corpus)")

    # Build 4-gram distributions
    def ngram_distribution(text, n):
        ngrams = [text[i:i+n] for i in range(max(0, len(text) - n))]
        counts = Counter(ngrams)
        total = sum(counts.values())
        if total == 0:
            return {}
        return {k: v / total for k, v in counts.items()}

    p_corpus = ngram_distribution(corpus_sample, n)
    p_gen = ngram_distribution(all_generated, n)

    # KL(gen || corpus) — how much generated diverges from corpus
    all_keys = set(list(p_corpus.keys()) + list(p_gen.keys()))
    eps = 1e-10
    kl_div = 0.0
    for key in all_keys:
        p = p_gen.get(key, eps)
        q = p_corpus.get(key, eps)
        kl_div += p * np.log2(p / q)

    print(f"     Corpus unique {n}-grams: {len(p_corpus)}")
    print(f"     Generated unique {n}-grams: {len(p_gen)}")
    print(f"     KL(generated || corpus) = {kl_div:.4f} bits")
    print(f"     {'Low divergence (similar distribution)' if kl_div < 2.0 else 'High divergence (different distribution)' if kl_div > 5.0 else 'Moderate divergence'}")

    # --- 2. Mutual Information: I(prompt; generated) ---
    print("\n  2. Mutual Information: I(prompt; generated)")

    # Use histogram-based MI estimation
    prompt_ids = []
    gen_entropies = []
    for i, prompt in enumerate(prompts):
        for _ in range(3):
            out = generate(decoder, bridge, tok, prompt, max_len=60, temperature=0.7)
            gen = out[len(prompt):]
            if len(gen) > 0:
                freqs = Counter(gen)
                probs = np.array([v / len(gen) for v in freqs.values()])
                entropy = -np.sum(probs * np.log2(probs + 1e-10))
                prompt_ids.append(i)
                gen_entropies.append(entropy)

    if len(prompt_ids) >= 4:
        # Bin entropies for histogram MI
        n_bins = min(8, len(set(prompt_ids)))
        prompt_arr = np.array(prompt_ids)
        entropy_arr = np.array(gen_entropies)

        # Discretize entropy into bins
        entropy_bins = np.digitize(entropy_arr, np.linspace(entropy_arr.min(), entropy_arr.max() + 0.01, n_bins + 1))

        # Joint and marginal distributions
        joint_counts = Counter(zip(prompt_arr.tolist(), entropy_bins.tolist()))
        total_n = len(prompt_arr)

        p_prompt = Counter(prompt_arr.tolist())
        p_entropy = Counter(entropy_bins.tolist())

        mi = 0.0
        for (pid, eid), count in joint_counts.items():
            p_xy = count / total_n
            p_x = p_prompt[pid] / total_n
            p_y = p_entropy[eid] / total_n
            if p_xy > 0 and p_x > 0 and p_y > 0:
                mi += p_xy * np.log2(p_xy / (p_x * p_y))

        print(f"     I(prompt; generated_entropy) = {mi:.4f} bits")
        print(f"     {'Prompt influences output' if mi > 0.1 else 'Output independent of prompt'}")
    else:
        mi = 0.0
        print(f"     Skipped: insufficient data")

    # --- 3. Compression Ratio ---
    print("\n  3. Compression Ratio: generated vs corpus baseline")

    corpus_bytes = corpus_sample[:5000].encode('utf-8', errors='ignore')
    gen_bytes = all_generated.encode('utf-8', errors='ignore')

    corpus_cr = len(zlib.compress(corpus_bytes)) / max(len(corpus_bytes), 1)
    gen_cr = len(zlib.compress(gen_bytes)) / max(len(gen_bytes), 1)

    # Also: compress generated appended to corpus — if memorized, compresses well together
    combined_bytes = corpus_bytes + gen_bytes
    combined_compressed = len(zlib.compress(combined_bytes))
    separate_compressed = len(zlib.compress(corpus_bytes)) + len(zlib.compress(gen_bytes))
    ncd = (combined_compressed - min(len(zlib.compress(corpus_bytes)), len(zlib.compress(gen_bytes)))) / max(len(zlib.compress(corpus_bytes)), len(zlib.compress(gen_bytes)))

    print(f"     Corpus compression ratio:    {corpus_cr:.4f}")
    print(f"     Generated compression ratio: {gen_cr:.4f}")
    print(f"     NCD (normalized compression distance): {ncd:.4f}")
    print(f"     {'Similar to corpus (possible memorization)' if ncd < 0.3 else 'Different from corpus (novel)' if ncd > 0.7 else 'Moderate similarity'}")

    print(f"\n  ── Information Theory Summary ──")
    print(f"  KL divergence:     {kl_div:.4f} bits")
    print(f"  Mutual information: {mi:.4f} bits")
    print(f"  Compression NCD:   {ncd:.4f}")

    return {
        'kl_divergence': float(kl_div),
        'mutual_information': float(mi),
        'corpus_cr': float(corpus_cr),
        'generated_cr': float(gen_cr),
        'ncd': float(ncd),
    }


# ═══ Main ═══

def main():
    parser = argparse.ArgumentParser(description='Novelty checker: memorization vs generation')
    parser.add_argument('--checkpoint', default=None, help='Path to checkpoint .pt (not needed for ground-truth)')
    parser.add_argument('--corpus', default='data/corpus_v2.txt')
    parser.add_argument('--method', default='all',
                        choices=['all', 'ood', 'ngram', 'ppl', 'temp', 'partial',
                                 'ground-truth', 'stats', 'info'])
    parser.add_argument('--consciousness', action='store_true', help='Use TimeCrystal C engine')
    args = parser.parse_args()

    print(f"{'═' * 60}")
    print(f"  Novelty Checker — memorization vs generation")
    print(f"  Checkpoint: {args.checkpoint or '(none)'}")
    print(f"  Corpus: {args.corpus}")
    print(f"{'═' * 60}")

    # Ground-truth doesn't need a checkpoint
    if args.method == 'ground-truth':
        check_ground_truth(args.corpus)
        return

    # All other methods need a checkpoint
    if not args.checkpoint:
        print("  ERROR: --checkpoint required for this method")
        sys.exit(1)

    decoder, bridge, tok, model_args = load_model(args.checkpoint, args.corpus)
    print(f"  Model: d_model={model_args['d_model']}, vocab={tok.vocab}")
    print(f"  Corpus: {len(tok.corpus):,} chars")

    results = {}

    if args.method in ['all', 'ood']:
        results['ood'] = check_ood(decoder, bridge, tok)

    if args.method in ['all', 'ngram']:
        results['ngram'] = check_ngram(decoder, bridge, tok)

    if args.method in ['all', 'ppl']:
        results['ppl'] = check_perplexity(decoder, bridge, tok)

    if args.method in ['all', 'temp']:
        results['temp'] = check_temperature(decoder, bridge, tok)

    if args.method in ['all', 'partial']:
        results['partial'] = check_partial(decoder, bridge, tok)

    if args.method in ['all', 'stats']:
        results['stats'] = check_statistical_significance(decoder, bridge, tok)

    if args.method in ['all', 'info']:
        results['info'] = check_information_theory(decoder, bridge, tok)

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

    if 'stats' in results and results['stats']:
        s = results['stats']
        print(f"  N-gram chi-sq p: {s['ngram_p']:.2e}")
        print(f"  PPL 95% CI:      [{s['ppl_ci'][0]:.2f}, {s['ppl_ci'][1]:.2f}]")
        print(f"  Kruskal-Wallis:  p={s['kruskal_p']:.4f}")

    if 'info' in results and results['info']:
        i = results['info']
        print(f"  KL divergence:   {i['kl_divergence']:.4f} bits")
        print(f"  Mutual info:     {i['mutual_information']:.4f} bits")
        print(f"  Compression NCD: {i['ncd']:.4f}")


if __name__ == '__main__':
    main()
