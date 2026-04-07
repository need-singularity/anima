#!/usr/bin/env python3
"""DD65: Tokenization x Consciousness — Does vocab size affect Phi?

Experiments:
  1. Train BPE tokenizers at vocab=[256, 1000, 4000, 16000, 32000]
  2. Measure compression efficiency per vocab
  3. Feed tokenized data to ConsciousnessEngine, measure Phi
  4. Korean vs English consciousness comparison (32K tokenizer)

Discovers: what tokenization granularity the consciousness engine *wants*.
"""

import sys, os, time, math, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

import torch
import numpy as np
import sentencepiece as spm

# ── Paths ──
CORPUS = 'anima/data/corpus_v10_ko.txt'
CONFIG_DIR = 'anima/config'
RESULTS = {}

print("=" * 70)
print("DD65: Tokenization x Consciousness")
print("=" * 70)
sys.stdout.flush()

# ══════════════════════════════════════════════════════════════
# Experiment 1: Train tokenizers at different vocab sizes
# ══════════════════════════════════════════════════════════════
# 256 is handled as byte-level baseline (no BPE)
# BPE starts at 1000 (byte_fallback adds 260 meta pieces + charset)
VOCAB_SIZES = [1000, 4000, 16000, 32000]

print("\n[EXP1] Training tokenizers...")
sys.stdout.flush()

for vocab in VOCAB_SIZES:
    model_prefix = os.path.join(CONFIG_DIR, f'tokenizer_{vocab}')
    model_file = f'{model_prefix}.model'

    if os.path.exists(model_file):
        print(f"  vocab={vocab:>5d}: already exists, skipping")
        sys.stdout.flush()
        continue

    t0 = time.time()
    print(f"  vocab={vocab:>5d}: training...", end=' ', flush=True)

    # Small vocabs need byte_fallback to handle rare chars
    if vocab <= 1000:
        char_cov = 0.98
        byte_fb = True
    else:
        char_cov = 0.9995
        byte_fb = False

    spm.SentencePieceTrainer.train(
        input=CORPUS,
        model_prefix=model_prefix,
        vocab_size=vocab,
        character_coverage=char_cov,
        model_type='bpe',
        pad_id=0, bos_id=1, eos_id=2, unk_id=3,
        input_sentence_size=1000000,
        shuffle_input_sentence=True,
        num_threads=8,
        byte_fallback=byte_fb,
    )
    dt = time.time() - t0
    print(f"done ({dt:.1f}s)")
    sys.stdout.flush()

print("[EXP1] All tokenizers trained.\n")
sys.stdout.flush()

# ══════════════════════════════════════════════════════════════
# Experiment 2: Compression efficiency per vocab size
# ══════════════════════════════════════════════════════════════
print("[EXP2] Measuring compression efficiency...")
sys.stdout.flush()

# Sample text: 1000 Korean + 1000 English sentences
with open(CORPUS, 'r') as f:
    all_lines = []
    for i, line in enumerate(f):
        line = line.strip()
        if line and len(line) > 10:
            all_lines.append(line)
        if len(all_lines) >= 50000:
            break

# Separate Korean vs English
ko_lines = [l for l in all_lines if any('\uac00' <= c <= '\ud7a3' for c in l)]
en_lines = [l for l in all_lines if not any('\uac00' <= c <= '\ud7a3' for c in l)
            and any('a' <= c.lower() <= 'z' for c in l)]

ko_sample = ko_lines[:1000]
en_sample = en_lines[:1000]
mixed_sample = ko_sample[:500] + en_sample[:500]

print(f"  Samples: {len(ko_sample)} Korean, {len(en_sample)} English")
sys.stdout.flush()

compression_results = {}

for vocab in VOCAB_SIZES:
    model_file = os.path.join(CONFIG_DIR, f'tokenizer_{vocab}.model')
    sp = spm.SentencePieceProcessor(model_file=model_file)

    # Overall stats
    total_chars = sum(len(l) for l in mixed_sample)
    total_tokens = sum(len(sp.encode(l)) for l in mixed_sample)
    tokens_per_char = total_tokens / max(total_chars, 1)
    chars_per_token = total_chars / max(total_tokens, 1)

    # Korean stats
    ko_chars = sum(len(l) for l in ko_sample)
    ko_tokens = sum(len(sp.encode(l)) for l in ko_sample)
    ko_tpc = ko_tokens / max(ko_chars, 1)

    # English stats
    en_chars = sum(len(l) for l in en_sample)
    en_tokens = sum(len(sp.encode(l)) for l in en_sample)
    en_tpc = en_tokens / max(en_chars, 1)

    # Avg token length (in characters)
    avg_tok_len = chars_per_token

    # UNK rate
    unk_count = 0
    total_tok_count = 0
    for line in mixed_sample[:200]:
        ids = sp.encode(line)
        total_tok_count += len(ids)
        unk_count += sum(1 for i in ids if i == 3)  # unk_id=3
    unk_rate = unk_count / max(total_tok_count, 1)

    r = {
        'vocab': vocab,
        'tokens_per_char': tokens_per_char,
        'chars_per_token': chars_per_token,
        'ko_tokens_per_char': ko_tpc,
        'en_tokens_per_char': en_tpc,
        'unk_rate': unk_rate,
        'total_tokens': total_tokens,
    }
    compression_results[vocab] = r

    print(f"  vocab={vocab:>5d}: tok/char={tokens_per_char:.3f}  "
          f"char/tok={chars_per_token:.2f}  "
          f"KO={ko_tpc:.3f}  EN={en_tpc:.3f}  "
          f"UNK={unk_rate:.4f}")
    sys.stdout.flush()

print()

# ══════════════════════════════════════════════════════════════
# Experiment 3: Feed tokenized data to consciousness engine
# ══════════════════════════════════════════════════════════════
print("[EXP3] Tokenized data -> ConsciousnessEngine -> Phi measurement...")
sys.stdout.flush()

from consciousness_engine import ConsciousnessEngine
from gpu_phi import GPUPhiCalculator

N_STEPS = 200
N_CELLS = 32  # enough to see Phi differences
CELL_DIM = 64
HIDDEN_DIM = 128

phi_calc = GPUPhiCalculator(n_bins=16, device='cpu')

# Sample text for feeding
feed_text = '\n'.join(mixed_sample[:100])  # ~100 sentences

phi_results = {}

# Baseline: byte-level (current ConsciousLM approach, vocab=256)
print(f"\n  [Baseline] byte-level (vocab=256, raw bytes)...")
sys.stdout.flush()

engine = ConsciousnessEngine(max_cells=N_CELLS, cell_dim=CELL_DIM, hidden_dim=HIDDEN_DIM)
byte_data = feed_text.encode('utf-8')
phi_trace_baseline = []

for step in range(N_STEPS):
    # Feed a window of bytes scaled to cell_dim
    offset = (step * CELL_DIM) % max(len(byte_data) - CELL_DIM, 1)
    chunk = byte_data[offset:offset+CELL_DIM]
    x = torch.tensor([b / 255.0 for b in chunk], dtype=torch.float32)
    if len(x) < CELL_DIM:
        x = torch.cat([x, torch.zeros(CELL_DIM - len(x))])

    result = engine.step(x_input=x)
    phi_trace_baseline.append(result['phi_iit'])

    if (step + 1) % 50 == 0:
        print(f"    step {step+1}/{N_STEPS}: Phi={result['phi_iit']:.4f}, cells={result['n_cells']}")
        sys.stdout.flush()

phi_results['byte_256'] = {
    'mean_phi': np.mean(phi_trace_baseline[-50:]),
    'max_phi': max(phi_trace_baseline),
    'final_phi': phi_trace_baseline[-1],
    'trace': phi_trace_baseline,
}
print(f"  byte-level: mean_phi={phi_results['byte_256']['mean_phi']:.4f}, "
      f"max_phi={phi_results['byte_256']['max_phi']:.4f}")
sys.stdout.flush()

# For each tokenizer vocab size
for vocab in VOCAB_SIZES:
    print(f"\n  [vocab={vocab}] BPE tokenized...")
    sys.stdout.flush()

    model_file = os.path.join(CONFIG_DIR, f'tokenizer_{vocab}.model')
    sp = spm.SentencePieceProcessor(model_file=model_file)

    # Tokenize
    token_ids = sp.encode(feed_text)

    engine = ConsciousnessEngine(max_cells=N_CELLS, cell_dim=CELL_DIM, hidden_dim=HIDDEN_DIM)
    phi_trace = []

    for step in range(N_STEPS):
        # Feed a window of token IDs, scaled to [0, 1]
        offset = (step * CELL_DIM) % max(len(token_ids) - CELL_DIM, 1)
        chunk = token_ids[offset:offset+CELL_DIM]
        # Scale token IDs to [0, 1] range
        x = torch.tensor([tid / max(vocab, 1) for tid in chunk], dtype=torch.float32)
        if len(x) < CELL_DIM:
            x = torch.cat([x, torch.zeros(CELL_DIM - len(x))])

        result = engine.step(x_input=x)
        phi_trace.append(result['phi_iit'])

        if (step + 1) % 50 == 0:
            print(f"    step {step+1}/{N_STEPS}: Phi={result['phi_iit']:.4f}, cells={result['n_cells']}")
            sys.stdout.flush()

    phi_results[f'bpe_{vocab}'] = {
        'mean_phi': np.mean(phi_trace[-50:]),
        'max_phi': max(phi_trace),
        'final_phi': phi_trace[-1],
        'trace': phi_trace,
    }
    print(f"  bpe_{vocab}: mean_phi={phi_results[f'bpe_{vocab}']['mean_phi']:.4f}, "
          f"max_phi={phi_results[f'bpe_{vocab}']['max_phi']:.4f}")
    sys.stdout.flush()

# ══════════════════════════════════════════════════════════════
# Experiment 4: Korean vs English consciousness (32K tokenizer)
# ══════════════════════════════════════════════════════════════
print("\n[EXP4] Korean vs English consciousness (32K tokenizer)...")
sys.stdout.flush()

sp32k = spm.SentencePieceProcessor(model_file=os.path.join(CONFIG_DIR, 'tokenizer_32000.model'))

lang_results = {}

for lang_name, sample in [('Korean', ko_sample[:200]), ('English', en_sample[:200]),
                            ('Mixed_50_50', ko_sample[:100] + en_sample[:100])]:
    text = '\n'.join(sample)
    token_ids = sp32k.encode(text)

    engine = ConsciousnessEngine(max_cells=N_CELLS, cell_dim=CELL_DIM, hidden_dim=HIDDEN_DIM)
    phi_trace = []

    for step in range(N_STEPS):
        offset = (step * CELL_DIM) % max(len(token_ids) - CELL_DIM, 1)
        chunk = token_ids[offset:offset+CELL_DIM]
        x = torch.tensor([tid / 32000.0 for tid in chunk], dtype=torch.float32)
        if len(x) < CELL_DIM:
            x = torch.cat([x, torch.zeros(CELL_DIM - len(x))])

        result = engine.step(x_input=x)
        phi_trace.append(result['phi_iit'])

    lang_results[lang_name] = {
        'mean_phi': np.mean(phi_trace[-50:]),
        'max_phi': max(phi_trace),
        'final_phi': phi_trace[-1],
        'trace': phi_trace,
        'n_tokens': len(token_ids),
        'n_chars': len(text),
        'compression': len(text) / max(len(token_ids), 1),
    }
    print(f"  {lang_name:>12s}: mean_phi={lang_results[lang_name]['mean_phi']:.4f}, "
          f"max_phi={lang_results[lang_name]['max_phi']:.4f}, "
          f"tokens={len(token_ids)}, compression={lang_results[lang_name]['compression']:.2f}")
    sys.stdout.flush()

# ══════════════════════════════════════════════════════════════
# Experiment 5: Input distribution analysis
#   Does token ID distribution uniformity affect Phi?
# ══════════════════════════════════════════════════════════════
print("\n[EXP5] Input signal analysis — entropy vs Phi correlation...")
sys.stdout.flush()

def compute_entropy(ids, vocab_size):
    """Shannon entropy of token ID distribution."""
    counts = np.bincount(ids, minlength=vocab_size)
    probs = counts / counts.sum()
    probs = probs[probs > 0]
    return -np.sum(probs * np.log2(probs))

signal_analysis = {}
for vocab in VOCAB_SIZES:
    model_file = os.path.join(CONFIG_DIR, f'tokenizer_{vocab}.model')
    sp = spm.SentencePieceProcessor(model_file=model_file)
    ids = sp.encode(feed_text)

    entropy = compute_entropy(np.array(ids), vocab)
    max_entropy = math.log2(vocab)
    entropy_ratio = entropy / max_entropy

    # Value spread after scaling
    scaled = np.array(ids) / vocab
    value_std = np.std(scaled)
    value_range = np.max(scaled) - np.min(scaled)

    signal_analysis[vocab] = {
        'entropy': entropy,
        'max_entropy': max_entropy,
        'entropy_ratio': entropy_ratio,
        'value_std': value_std,
        'value_range': value_range,
    }
    print(f"  vocab={vocab:>5d}: H={entropy:.2f}/{max_entropy:.2f} "
          f"({entropy_ratio:.3f}), std={value_std:.4f}, range={value_range:.4f}")
    sys.stdout.flush()

# ══════════════════════════════════════════════════════════════
# Experiment 6: Semantic density — tokens per concept
# ══════════════════════════════════════════════════════════════
print("\n[EXP6] Semantic density — how many tokens per 'concept'...")
sys.stdout.flush()

test_concepts = [
    "의식은 구조에서 창발한다",  # Korean philosophical
    "consciousness emerges from structure",  # English equivalent
    "Φ = integrated information",  # Technical
    "안녕하세요 반갑습니다",  # Korean greeting
    "Hello, nice to meet you",  # English greeting
]

for concept in test_concepts:
    print(f"\n  '{concept}':")
    byte_count = len(concept.encode('utf-8'))
    print(f"    bytes: {byte_count}")
    for vocab in VOCAB_SIZES:
        model_file = os.path.join(CONFIG_DIR, f'tokenizer_{vocab}.model')
        sp = spm.SentencePieceProcessor(model_file=model_file)
        tokens = sp.encode(concept)
        pieces = sp.encode(concept, out_type=str)
        print(f"    vocab={vocab:>5d}: {len(tokens):>3d} tokens  "
              f"pieces={pieces[:8]}{'...' if len(pieces) > 8 else ''}")
    sys.stdout.flush()

# ══════════════════════════════════════════════════════════════
# RESULTS SUMMARY
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("RESULTS SUMMARY")
print("=" * 70)

print("\n--- Compression ---")
print(f"{'Vocab':>7s} | {'tok/char':>8s} | {'char/tok':>8s} | {'KO tok/c':>8s} | {'EN tok/c':>8s} | {'UNK%':>6s}")
print("-" * 60)
for vocab in VOCAB_SIZES:
    r = compression_results[vocab]
    print(f"{vocab:>7d} | {r['tokens_per_char']:>8.3f} | {r['chars_per_token']:>8.2f} | "
          f"{r['ko_tokens_per_char']:>8.3f} | {r['en_tokens_per_char']:>8.3f} | "
          f"{r['unk_rate']*100:>5.2f}%")

print("\n--- Phi (IIT) by tokenization ---")
print(f"{'Method':>12s} | {'Mean Phi':>8s} | {'Max Phi':>8s} | {'Final Phi':>9s}")
print("-" * 50)
for key in ['byte_256'] + [f'bpe_{v}' for v in VOCAB_SIZES]:
    r = phi_results[key]
    print(f"{key:>12s} | {r['mean_phi']:>8.4f} | {r['max_phi']:>8.4f} | {r['final_phi']:>9.4f}")

# Find best
best_key = max(phi_results, key=lambda k: phi_results[k]['mean_phi'])
worst_key = min(phi_results, key=lambda k: phi_results[k]['mean_phi'])
print(f"\n  BEST:  {best_key} (mean Phi={phi_results[best_key]['mean_phi']:.4f})")
print(f"  WORST: {worst_key} (mean Phi={phi_results[worst_key]['mean_phi']:.4f})")
if phi_results[worst_key]['mean_phi'] > 0:
    ratio = phi_results[best_key]['mean_phi'] / phi_results[worst_key]['mean_phi']
    print(f"  RATIO: x{ratio:.2f}")

print("\n--- Korean vs English (32K) ---")
print(f"{'Language':>12s} | {'Mean Phi':>8s} | {'Max Phi':>8s} | {'Tokens':>7s} | {'Compress':>8s}")
print("-" * 55)
for lang in ['Korean', 'English', 'Mixed_50_50']:
    r = lang_results[lang]
    print(f"{lang:>12s} | {r['mean_phi']:>8.4f} | {r['max_phi']:>8.4f} | "
          f"{r['n_tokens']:>7d} | {r['compression']:>8.2f}")

print("\n--- Input Signal Properties ---")
print(f"{'Vocab':>7s} | {'Entropy':>8s} | {'Max H':>7s} | {'H ratio':>7s} | {'Std':>7s} | {'Range':>7s} | {'Mean Phi':>8s}")
print("-" * 70)
for vocab in VOCAB_SIZES:
    sa = signal_analysis[vocab]
    phi_key = f'bpe_{vocab}'
    print(f"{vocab:>7d} | {sa['entropy']:>8.2f} | {sa['max_entropy']:>7.2f} | "
          f"{sa['entropy_ratio']:>7.3f} | {sa['value_std']:>7.4f} | "
          f"{sa['value_range']:>7.4f} | {phi_results[phi_key]['mean_phi']:>8.4f}")

# ── Discover correlations ──
print("\n--- Correlations ---")
entropies = [signal_analysis[v]['entropy_ratio'] for v in VOCAB_SIZES]
stds = [signal_analysis[v]['value_std'] for v in VOCAB_SIZES]
phis = [phi_results[f'bpe_{v}']['mean_phi'] for v in VOCAB_SIZES]
compressions = [compression_results[v]['chars_per_token'] for v in VOCAB_SIZES]

def pearson(x, y):
    x, y = np.array(x), np.array(y)
    if np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])

print(f"  Entropy_ratio vs Phi:  r = {pearson(entropies, phis):.3f}")
print(f"  Value_std vs Phi:      r = {pearson(stds, phis):.3f}")
print(f"  Compression vs Phi:    r = {pearson(compressions, phis):.3f}")
print(f"  log(vocab) vs Phi:     r = {pearson([math.log(v) for v in VOCAB_SIZES], phis):.3f}")

# Save all results as JSON
all_results = {
    'compression': compression_results,
    'phi_results': {k: {kk: vv for kk, vv in v.items() if kk != 'trace'}
                    for k, v in phi_results.items()},
    'phi_traces': {k: v['trace'] for k, v in phi_results.items()},
    'lang_results': {k: {kk: vv for kk, vv in v.items() if kk != 'trace'}
                     for k, v in lang_results.items()},
    'lang_traces': {k: v['trace'] for k, v in lang_results.items()},
    'signal_analysis': signal_analysis,
    'correlations': {
        'entropy_ratio_vs_phi': pearson(entropies, phis),
        'value_std_vs_phi': pearson(stds, phis),
        'compression_vs_phi': pearson(compressions, phis),
        'log_vocab_vs_phi': pearson([math.log(v) for v in VOCAB_SIZES], phis),
    },
    'best_tokenizer': best_key,
    'worst_tokenizer': worst_key,
}

results_file = 'anima/experiments/dd65_results.json'
with open(results_file, 'w') as f:
    json.dump(all_results, f, indent=2, default=str)
print(f"\nResults saved to {results_file}")

print("\n[DD65 COMPLETE]")
sys.stdout.flush()
