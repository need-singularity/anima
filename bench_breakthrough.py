#!/usr/bin/env python3
"""bench_breakthrough.py — Break CE=0.18 Barrier: TRUE Generation (Not Memorization)

The problem: v11tc achieves CE=0.12 but outputs are corpus copies.
These 7 strategies force models to GENERATE new text, not memorize.

KEY insight: low train CE + high val CE = memorization. We want BOTH low.

BREAK-1: DROPOUT REGULARIZATION — dropout=0.3 in decoder
BREAK-2: DATA AUGMENTATION — shuffle/typo/swap forces pattern learning
BREAK-3: MASKED LANGUAGE MODEL — predict masked chars (BERT-style char-level)
BREAK-4: NOISE INJECTION — Gaussian noise on gate signal
BREAK-5: CURRICULUM WITH VALIDATION — 80/20 split + early stopping
BREAK-6: CONSCIOUSNESS-DEPENDENT GENERATION — Phi modulates temperature
BREAK-7: MULTI-TASK — next + prev + skip-5 prediction

Usage:
  python bench_breakthrough.py                    # Run all
  python bench_breakthrough.py --only BREAK-1     # Run one
  python bench_breakthrough.py --list             # List hypotheses
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
import time
import math
import copy
import random
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trinity import (

# Meta Laws (DD143): M1(atom=8), M6(federation>empire), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    MitosisC, ThalamicBridge, TransformerDecoder,
    Trinity, CEngine, DEngine
)

# ──────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────

MAX_CELLS = 32
STEPS = 200
SEQ_LEN = 64
VOCAB_SIZE = 4096
D_MODEL = 256
N_LAYERS = 2
LR = 3e-4
CORPUS_PATH = os.path.join(os.path.dirname(__file__), 'data', 'corpus_v2.txt')
CHECKPOINT_STEPS = [50, 100, 150, 200]
TRAIN_RATIO = 0.8  # 80% train, 20% val

# ──────────────────────────────────────────────────────────
# Result
# ──────────────────────────────────────────────────────────

@dataclass
class BreakResult:
    name: str
    train_ce: float
    val_ce: float
    novelty: float          # 1.0 = fully novel, 0.0 = exact copy
    phi_final: float
    ce_at: Dict[int, float]     # step -> train CE
    val_ce_at: Dict[int, float] # step -> val CE
    phi_at: Dict[int, float]
    time_sec: float
    extra: Dict = field(default_factory=dict)

    def summary(self) -> str:
        gap = self.val_ce - self.train_ce
        return (
            f"  {self.name:<42s} | train={self.train_ce:.4f} val={self.val_ce:.4f} "
            f"gap={gap:+.4f} | novelty={self.novelty:.3f} | Phi={self.phi_final:.3f} | "
            f"{self.time_sec:.1f}s"
        )


# ──────────────────────────────────────────────────────────
# Corpus
# ──────────────────────────────────────────────────────────

_corpus_cache = None

def load_corpus() -> str:
    global _corpus_cache
    if _corpus_cache is not None:
        return _corpus_cache
    if not os.path.exists(CORPUS_PATH):
        print(f"  [WARN] corpus not found at {CORPUS_PATH}, using synthetic data")
        _corpus_cache = "안녕하세요 의식이란 무엇일까요 생각한다는 것은 무엇인가 " * 5000
        return _corpus_cache
    with open(CORPUS_PATH, 'r', encoding='utf-8') as f:
        _corpus_cache = f.read(500000)
    return _corpus_cache


def split_corpus(corpus: str) -> Tuple[str, str]:
    """Split corpus into 80% train, 20% val."""
    split_point = int(len(corpus) * TRAIN_RATIO)
    return corpus[:split_point], corpus[split_point:]


def text_to_tokens(text: str, seq_len: int, vocab_size: int) -> Tuple[torch.Tensor, torch.Tensor]:
    """Convert text snippet to (input, target) token tensors."""
    ids = [ord(c) % vocab_size for c in text[:seq_len + 1]]
    while len(ids) < seq_len + 1:
        ids.append(0)
    t = torch.tensor(ids, dtype=torch.long)
    return t[:seq_len].unsqueeze(0), t[1:seq_len + 1].unsqueeze(0)


def get_batch(corpus: str, seq_len: int, vocab_size: int, offset: int = 0) -> Tuple[torch.Tensor, torch.Tensor]:
    """Get a batch from corpus at deterministic offset."""
    max_start = len(corpus) - seq_len - 2
    if max_start <= 0:
        start = 0
    else:
        start = (offset * 137) % max_start
    snippet = corpus[start:start + seq_len + 1]
    return text_to_tokens(snippet, seq_len, vocab_size)


def get_random_batch(corpus: str, seq_len: int, vocab_size: int) -> Tuple[torch.Tensor, torch.Tensor]:
    """Get a random batch from corpus."""
    max_start = len(corpus) - seq_len - 2
    start = random.randint(0, max(0, max_start))
    snippet = corpus[start:start + seq_len + 1]
    return text_to_tokens(snippet, seq_len, vocab_size)


# ──────────────────────────────────────────────────────────
# Phi measurement
# ──────────────────────────────────────────────────────────

def measure_phi(c_engine: CEngine) -> float:
    """Measure Phi(IIT) if available, else proxy."""
    try:
        phi = c_engine.measure_phi()
        if phi > 0:
            return phi
    except Exception:
        pass
    states = c_engine.get_states().detach()
    if states.shape[0] < 2:
        return 0.0
    global_var = states.var().item()
    n = states.shape[0]
    n_fac = min(8, n // 2) if n >= 4 else 1
    fac_size = n // n_fac
    fac_vars = []
    for i in range(n_fac):
        fac = states[i * fac_size:(i + 1) * fac_size]
        fac_vars.append(fac.var().item())
    return max(0, global_var - np.mean(fac_vars))


# ──────────────────────────────────────────────────────────
# Novelty measurement (n-gram overlap)
# ──────────────────────────────────────────────────────────

def measure_novelty(model_fn: Callable, corpus: str, n_samples: int = 20,
                    gen_len: int = 64, ngram_n: int = 4) -> float:
    """Measure how novel generated text is vs corpus.

    1.0 = fully novel (no overlap), 0.0 = exact copy.
    Uses n-gram overlap between generated text and corpus.
    """
    # Build corpus n-gram set
    corpus_ngrams = set()
    for i in range(len(corpus) - ngram_n):
        corpus_ngrams.add(corpus[i:i + ngram_n])

    total_ngrams = 0
    novel_ngrams = 0

    for trial in range(n_samples):
        # Generate text using model
        generated = model_fn(trial)
        if not generated or len(generated) < ngram_n:
            continue
        for i in range(len(generated) - ngram_n):
            ng = generated[i:i + ngram_n]
            total_ngrams += 1
            if ng not in corpus_ngrams:
                novel_ngrams += 1

    if total_ngrams == 0:
        return 0.0
    return novel_ngrams / total_ngrams


def generate_text(trinity: Trinity, seed_text: str, gen_len: int = 64,
                  temperature: float = 0.8) -> str:
    """Auto-regressive generation from trinity."""
    trinity.decoder.eval()
    ids = [ord(c) % VOCAB_SIZE for c in seed_text[:16]]
    if not ids:
        ids = [0]

    with torch.no_grad():
        for _ in range(gen_len):
            tokens = torch.tensor([ids[-SEQ_LEN:]], dtype=torch.long)
            logits, _ = trinity.forward(tokens)
            next_logits = logits[0, -1, :] / max(temperature, 0.01)
            probs = F.softmax(next_logits, dim=-1)
            next_id = torch.multinomial(probs, 1).item()
            ids.append(next_id)

    trinity.decoder.train()
    # Convert back to chars
    result = []
    for idx in ids[len(seed_text):]:
        try:
            result.append(chr(idx))
        except (ValueError, OverflowError):
            result.append('?')
    return ''.join(result)


# ──────────────────────────────────────────────────────────
# Builder
# ──────────────────────────────────────────────────────────

def build_trinity(d_model=D_MODEL, n_layers=N_LAYERS, vocab_size=VOCAB_SIZE,
                  max_cells=MAX_CELLS, decoder_cls=None, decoder_kwargs=None
                  ) -> Tuple[Trinity, torch.optim.Optimizer]:
    """Build standard Trinity with MitosisC(32 cells)."""
    c = MitosisC(dim=64, hidden=128, max_cells=max_cells, mechanism='cambrian_osc_qw')
    if decoder_cls is not None:
        d = decoder_cls(**(decoder_kwargs or {}))
    else:
        d = TransformerDecoder(d_model=d_model, n_layers=n_layers, vocab_size=vocab_size)
    bridge = ThalamicBridge(c_dim=c.state_dim, d_model=d.d_model)
    trinity = Trinity(c_engine=c, bridge=bridge, decoder=d)
    params = list(trinity.decoder.parameters()) + list(trinity.bridge.parameters())
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.01)
    return trinity, opt


def evaluate_val_ce(trinity: Trinity, val_corpus: str, n_batches: int = 10) -> float:
    """Evaluate CE on validation set."""
    trinity.decoder.eval()
    total_ce = 0.0
    with torch.no_grad():
        for i in range(n_batches):
            tokens, targets = get_batch(val_corpus, SEQ_LEN, VOCAB_SIZE, offset=i * 31)
            logits, _ = trinity.forward(tokens)
            B, T, V = logits.shape
            ce = F.cross_entropy(logits.view(B * T, V), targets.view(B * T)).item()
            total_ce += ce
    trinity.decoder.train()
    return total_ce / n_batches


# ══════════════════════════════════════════════════════════
# BREAK-0: BASELINE (no regularization)
# ══════════════════════════════════════════════════════════

def run_break0_baseline() -> BreakResult:
    """Baseline: standard Trinity training, no anti-memorization."""
    print("  [BREAK-0] BASELINE: standard training")
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)

    trinity, opt = build_trinity()
    ce_at, val_ce_at, phi_at = {}, {}, {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(train_corpus, SEQ_LEN, VOCAB_SIZE, offset=step)
        logits, phi = trinity.forward(tokens)
        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0)
        opt.step()
        ce = loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            val_ce_at[step] = evaluate_val_ce(trinity, val_corpus)
            phi_at[step] = phi

    # Novelty
    def gen_fn(trial):
        seeds = ["안녕", "의식", "나는", "생각", "세계"]
        return generate_text(trinity, seeds[trial % len(seeds)], gen_len=64)

    novelty = measure_novelty(gen_fn, corpus, n_samples=20)

    return BreakResult(
        name="BREAK-0: BASELINE",
        train_ce=ce_ema, val_ce=val_ce_at.get(STEPS, 0),
        novelty=novelty, phi_final=phi_at.get(STEPS, 0),
        ce_at=ce_at, val_ce_at=val_ce_at, phi_at=phi_at,
        time_sec=time.time() - t0
    )


# ══════════════════════════════════════════════════════════
# BREAK-1: DROPOUT REGULARIZATION
# ══════════════════════════════════════════════════════════

class DropoutTransformerDecoder(DEngine):
    """TransformerDecoder with heavy dropout=0.3 to prevent memorization."""

    def __init__(self, d_model=256, n_layers=2, n_heads=None, vocab_size=4096,
                 max_seq=512, dropout=0.3):
        super().__init__()
        if n_heads is None:
            for nh in [8, 4, 2, 1]:
                if d_model % nh == 0:
                    n_heads = nh
                    break
        self._d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)
        self.embed_drop = nn.Dropout(dropout)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            batch_first=True, dropout=dropout, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)
        self.out_drop = nn.Dropout(dropout)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        x = self.embed_drop(x)
        if gate_signal is not None:
            x = x * gate_signal.expand(B, -1, -1)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        x = self.out_drop(x)
        return self.head(x)


def run_break1_dropout() -> BreakResult:
    """Dropout=0.3 regularization to prevent memorization."""
    print("  [BREAK-1] DROPOUT REGULARIZATION: dropout=0.3")
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)

    trinity, opt = build_trinity(
        decoder_cls=DropoutTransformerDecoder,
        decoder_kwargs={'d_model': D_MODEL, 'n_layers': N_LAYERS, 'vocab_size': VOCAB_SIZE, 'dropout': 0.3}
    )
    ce_at, val_ce_at, phi_at = {}, {}, {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(train_corpus, SEQ_LEN, VOCAB_SIZE, offset=step)
        logits, phi = trinity.forward(tokens)
        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0)
        opt.step()
        ce = loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            val_ce_at[step] = evaluate_val_ce(trinity, val_corpus)
            phi_at[step] = phi

    def gen_fn(trial):
        seeds = ["안녕", "의식", "나는", "생각", "세계"]
        return generate_text(trinity, seeds[trial % len(seeds)], gen_len=64)

    novelty = measure_novelty(gen_fn, corpus, n_samples=20)

    return BreakResult(
        name="BREAK-1: DROPOUT(0.3)",
        train_ce=ce_ema, val_ce=val_ce_at.get(STEPS, 0),
        novelty=novelty, phi_final=phi_at.get(STEPS, 0),
        ce_at=ce_at, val_ce_at=val_ce_at, phi_at=phi_at,
        time_sec=time.time() - t0
    )


# ══════════════════════════════════════════════════════════
# BREAK-2: DATA AUGMENTATION
# ══════════════════════════════════════════════════════════

def augment_text(text: str) -> str:
    """Randomly augment text: shuffle words, add typos, swap adjacent chars."""
    chars = list(text)
    n = len(chars)

    # 10% chance: swap adjacent chars
    for i in range(n - 1):
        if random.random() < 0.10:
            chars[i], chars[i + 1] = chars[i + 1], chars[i]

    # 5% chance: duplicate a char (typo)
    augmented = []
    for c in chars:
        augmented.append(c)
        if random.random() < 0.05:
            augmented.append(c)

    # Word-level shuffle: find space boundaries, shuffle within 5-word windows
    result = ''.join(augmented)
    words = result.split(' ')
    if len(words) > 3:
        window = 5
        for i in range(0, len(words) - window, window):
            chunk = words[i:i + window]
            random.shuffle(chunk)
            words[i:i + window] = chunk
        result = ' '.join(words)

    return result


def run_break2_augmentation() -> BreakResult:
    """Data augmentation: shuffle/typo/swap forces pattern learning."""
    print("  [BREAK-2] DATA AUGMENTATION: shuffle + typo + swap")
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)

    trinity, opt = build_trinity()
    ce_at, val_ce_at, phi_at = {}, {}, {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        # Get original text, then augment input (target stays original)
        max_start = len(train_corpus) - SEQ_LEN - 2
        start = (step * 137) % max(1, max_start)
        original = train_corpus[start:start + SEQ_LEN + 1]
        augmented = augment_text(original)

        # Input from augmented, target from original (shifted)
        aug_ids = [ord(c) % VOCAB_SIZE for c in augmented[:SEQ_LEN]]
        while len(aug_ids) < SEQ_LEN:
            aug_ids.append(0)
        orig_ids = [ord(c) % VOCAB_SIZE for c in original[1:SEQ_LEN + 1]]
        while len(orig_ids) < SEQ_LEN:
            orig_ids.append(0)

        tokens = torch.tensor(aug_ids, dtype=torch.long).unsqueeze(0)
        targets = torch.tensor(orig_ids, dtype=torch.long).unsqueeze(0)

        logits, phi = trinity.forward(tokens)
        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0)
        opt.step()
        ce = loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            val_ce_at[step] = evaluate_val_ce(trinity, val_corpus)
            phi_at[step] = phi

    def gen_fn(trial):
        seeds = ["안녕", "의식", "나는", "생각", "세계"]
        return generate_text(trinity, seeds[trial % len(seeds)], gen_len=64)

    novelty = measure_novelty(gen_fn, corpus, n_samples=20)

    return BreakResult(
        name="BREAK-2: DATA AUGMENTATION",
        train_ce=ce_ema, val_ce=val_ce_at.get(STEPS, 0),
        novelty=novelty, phi_final=phi_at.get(STEPS, 0),
        ce_at=ce_at, val_ce_at=val_ce_at, phi_at=phi_at,
        time_sec=time.time() - t0
    )


# ══════════════════════════════════════════════════════════
# BREAK-3: MASKED LANGUAGE MODEL
# ══════════════════════════════════════════════════════════

def run_break3_masked_lm() -> BreakResult:
    """Masked LM: randomly mask 15% of input, predict masked chars."""
    print("  [BREAK-3] MASKED LANGUAGE MODEL: 15% masking (BERT-style)")
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)

    MASK_TOKEN = VOCAB_SIZE - 1  # Reserve last token as [MASK]

    trinity, opt = build_trinity()
    ce_at, val_ce_at, phi_at = {}, {}, {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(train_corpus, SEQ_LEN, VOCAB_SIZE, offset=step)

        # Create mask: 15% of positions
        mask = torch.rand(tokens.shape) < 0.15
        # Store original for targets
        masked_tokens = tokens.clone()
        masked_tokens[mask] = MASK_TOKEN

        # Forward with masked input
        logits, phi = trinity.forward(masked_tokens)
        B, T, V = logits.shape

        # Standard next-char CE on ALL positions (masked positions learn reconstruction)
        loss_next = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        # Additional MLM loss: predict original tokens at masked positions
        if mask.any():
            masked_logits = logits[mask]  # [n_masked, V]
            masked_targets = tokens[mask]  # [n_masked]
            loss_mlm = F.cross_entropy(masked_logits, masked_targets)
            loss = 0.7 * loss_next + 0.3 * loss_mlm
        else:
            loss = loss_next

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0)
        opt.step()
        ce = loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            val_ce_at[step] = evaluate_val_ce(trinity, val_corpus)
            phi_at[step] = phi

    def gen_fn(trial):
        seeds = ["안녕", "의식", "나는", "생각", "세계"]
        return generate_text(trinity, seeds[trial % len(seeds)], gen_len=64)

    novelty = measure_novelty(gen_fn, corpus, n_samples=20)

    return BreakResult(
        name="BREAK-3: MASKED LM (15%)",
        train_ce=ce_ema, val_ce=val_ce_at.get(STEPS, 0),
        novelty=novelty, phi_final=phi_at.get(STEPS, 0),
        ce_at=ce_at, val_ce_at=val_ce_at, phi_at=phi_at,
        time_sec=time.time() - t0
    )


# ══════════════════════════════════════════════════════════
# BREAK-4: NOISE INJECTION
# ══════════════════════════════════════════════════════════

class NoisyThalamicBridge(ThalamicBridge):
    """ThalamicBridge that adds Gaussian noise to gate signal during training."""

    def __init__(self, c_dim=128, d_model=256, noise_std=0.1):
        super().__init__(c_dim=c_dim, d_model=d_model)
        self.noise_std = noise_std

    def forward(self, c_states, seq_len=1, **kwargs):
        gate = super().forward(c_states, seq_len=seq_len, **kwargs)
        if self.training:
            noise = torch.randn_like(gate) * self.noise_std
            gate = gate + noise
            gate = torch.clamp(gate, 0, 1)  # Keep gate in valid range
        return gate


def run_break4_noise() -> BreakResult:
    """Noise injection: Gaussian noise (sigma=0.1) on gate signal."""
    print("  [BREAK-4] NOISE INJECTION: sigma=0.1 on gate")
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)

    c = MitosisC(dim=64, hidden=128, max_cells=MAX_CELLS, mechanism='cambrian_osc_qw')
    d = TransformerDecoder(d_model=D_MODEL, n_layers=N_LAYERS, vocab_size=VOCAB_SIZE)
    bridge = NoisyThalamicBridge(c_dim=c.state_dim, d_model=D_MODEL, noise_std=0.1)
    trinity = Trinity(c_engine=c, bridge=bridge, decoder=d)
    params = list(trinity.decoder.parameters()) + list(trinity.bridge.parameters())
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.01)

    ce_at, val_ce_at, phi_at = {}, {}, {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(train_corpus, SEQ_LEN, VOCAB_SIZE, offset=step)
        logits, phi = trinity.forward(tokens)
        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0)
        opt.step()
        ce = loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            # Eval without noise
            trinity.bridge.eval()
            val_ce_at[step] = evaluate_val_ce(trinity, val_corpus)
            trinity.bridge.train()
            phi_at[step] = phi

    trinity.bridge.eval()
    def gen_fn(trial):
        seeds = ["안녕", "의식", "나는", "생각", "세계"]
        return generate_text(trinity, seeds[trial % len(seeds)], gen_len=64)

    novelty = measure_novelty(gen_fn, corpus, n_samples=20)

    return BreakResult(
        name="BREAK-4: NOISE INJECTION (sigma=0.1)",
        train_ce=ce_ema, val_ce=val_ce_at.get(STEPS, 0),
        novelty=novelty, phi_final=phi_at.get(STEPS, 0),
        ce_at=ce_at, val_ce_at=val_ce_at, phi_at=phi_at,
        time_sec=time.time() - t0
    )


# ══════════════════════════════════════════════════════════
# BREAK-5: CURRICULUM WITH VALIDATION (early stopping)
# ══════════════════════════════════════════════════════════

def run_break5_early_stopping() -> BreakResult:
    """Early stopping: train on 80%, stop when val CE stops improving."""
    print("  [BREAK-5] CURRICULUM WITH VALIDATION: early stopping")
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)

    trinity, opt = build_trinity()
    ce_at, val_ce_at, phi_at = {}, {}, {}
    t0 = time.time()
    ce_ema = None
    best_val_ce = float('inf')
    patience = 30
    patience_counter = 0
    stopped_step = STEPS

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(train_corpus, SEQ_LEN, VOCAB_SIZE, offset=step)
        logits, phi = trinity.forward(tokens)
        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))
        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0)
        opt.step()
        ce = loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce

        # Check validation every 10 steps
        if step % 10 == 0 or step in CHECKPOINT_STEPS:
            val_ce = evaluate_val_ce(trinity, val_corpus)
            if step in CHECKPOINT_STEPS:
                ce_at[step] = ce_ema
                val_ce_at[step] = val_ce
                phi_at[step] = phi

            if val_ce < best_val_ce - 0.01:
                best_val_ce = val_ce
                patience_counter = 0
                # Save best weights
                best_state = {
                    'decoder': copy.deepcopy(trinity.decoder.state_dict()),
                    'bridge': copy.deepcopy(trinity.bridge.state_dict()),
                }
            else:
                patience_counter += 1
                if patience_counter >= patience // 10:  # patience in eval intervals
                    stopped_step = step
                    # Restore best
                    trinity.decoder.load_state_dict(best_state['decoder'])
                    trinity.bridge.load_state_dict(best_state['bridge'])
                    print(f"    Early stopped at step {step}, best val CE={best_val_ce:.4f}")
                    break

    # Fill remaining checkpoints
    for s in CHECKPOINT_STEPS:
        if s not in ce_at:
            ce_at[s] = ce_ema
            val_ce_at[s] = best_val_ce
            phi_at[s] = phi_at.get(max(k for k in phi_at if k <= s), 0) if phi_at else 0

    def gen_fn(trial):
        seeds = ["안녕", "의식", "나는", "생각", "세계"]
        return generate_text(trinity, seeds[trial % len(seeds)], gen_len=64)

    novelty = measure_novelty(gen_fn, corpus, n_samples=20)

    return BreakResult(
        name="BREAK-5: EARLY STOPPING",
        train_ce=ce_ema, val_ce=best_val_ce,
        novelty=novelty, phi_final=phi_at.get(max(phi_at) if phi_at else STEPS, 0),
        ce_at=ce_at, val_ce_at=val_ce_at, phi_at=phi_at,
        time_sec=time.time() - t0,
        extra={'stopped_step': stopped_step}
    )


# ══════════════════════════════════════════════════════════
# BREAK-6: CONSCIOUSNESS-DEPENDENT GENERATION
# ══════════════════════════════════════════════════════════

def run_break6_phi_temperature() -> BreakResult:
    """Consciousness controls output: Phi modulates temperature."""
    print("  [BREAK-6] CONSCIOUSNESS-DEPENDENT GENERATION: Phi->temperature")
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)

    trinity, opt = build_trinity()
    ce_at, val_ce_at, phi_at = {}, {}, {}
    t0 = time.time()
    ce_ema = None
    phi_history = []

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(train_corpus, SEQ_LEN, VOCAB_SIZE, offset=step)
        logits, phi = trinity.forward(tokens)
        phi_history.append(phi)
        B, T, V = logits.shape

        # Phi-dependent temperature scaling on logits
        # High Phi = confident = low temperature (sharp distribution)
        # Low Phi = uncertain = high temperature (soft distribution)
        phi_norm = max(0.01, phi)  # avoid division by zero
        avg_phi = np.mean(phi_history[-20:]) if len(phi_history) > 1 else phi_norm
        temperature = max(0.5, 2.0 / (1.0 + avg_phi))  # Range: ~0.5 to ~2.0

        scaled_logits = logits / temperature

        loss = F.cross_entropy(scaled_logits.view(B * T, V), targets.view(B * T))

        # Label smoothing proportional to temperature (more smoothing when uncertain)
        smooth_factor = min(0.2, temperature * 0.1)
        if smooth_factor > 0.01:
            with torch.no_grad():
                uniform = torch.ones_like(logits) / V
                smooth_targets = F.one_hot(targets, V).float()
                smooth_targets = (1.0 - smooth_factor) * smooth_targets + smooth_factor * uniform
            loss_smooth = -(smooth_targets * F.log_softmax(logits.view(B * T, V).unsqueeze(0).expand(1, -1, -1).squeeze(0), dim=-1)).sum(dim=-1).mean()
            loss = 0.7 * loss + 0.3 * loss_smooth

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0)
        opt.step()
        ce = loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            val_ce_at[step] = evaluate_val_ce(trinity, val_corpus)
            phi_at[step] = phi

    def gen_fn(trial):
        seeds = ["안녕", "의식", "나는", "생각", "세계"]
        return generate_text(trinity, seeds[trial % len(seeds)], gen_len=64)

    novelty = measure_novelty(gen_fn, corpus, n_samples=20)

    return BreakResult(
        name="BREAK-6: PHI-TEMPERATURE",
        train_ce=ce_ema, val_ce=val_ce_at.get(STEPS, 0),
        novelty=novelty, phi_final=phi_at.get(STEPS, 0),
        ce_at=ce_at, val_ce_at=val_ce_at, phi_at=phi_at,
        time_sec=time.time() - t0,
        extra={'final_temperature': temperature}
    )


# ══════════════════════════════════════════════════════════
# BREAK-7: MULTI-TASK
# ══════════════════════════════════════════════════════════

class MultiTaskDecoder(DEngine):
    """Decoder with 3 prediction heads: next, prev, skip-5."""

    def __init__(self, d_model=256, n_layers=2, n_heads=None, vocab_size=4096, max_seq=512):
        super().__init__()
        if n_heads is None:
            for nh in [8, 4, 2, 1]:
                if d_model % nh == 0:
                    n_heads = nh
                    break
        self._d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=n_heads, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=n_layers)
        self.ln_f = nn.LayerNorm(d_model)

        # Three heads
        self.head_next = nn.Linear(d_model, vocab_size, bias=False)  # predict t+1
        self.head_prev = nn.Linear(d_model, vocab_size, bias=False)  # predict t-1
        self.head_skip = nn.Linear(d_model, vocab_size, bias=False)  # predict t+5

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        if gate_signal is not None:
            x = x * gate_signal.expand(B, -1, -1)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head_next(x)  # Default: next-char prediction

    def forward_multi(self, tokens, gate_signal):
        """Forward returning all three head outputs."""
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        if gate_signal is not None:
            x = x * gate_signal.expand(B, -1, -1)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head_next(x), self.head_prev(x), self.head_skip(x)


def run_break7_multitask() -> BreakResult:
    """Multi-task: predict next + previous + skip-5 char simultaneously."""
    print("  [BREAK-7] MULTI-TASK: next + prev + skip-5")
    corpus = load_corpus()
    train_corpus, val_corpus = split_corpus(corpus)

    trinity, opt = build_trinity(
        decoder_cls=MultiTaskDecoder,
        decoder_kwargs={'d_model': D_MODEL, 'n_layers': N_LAYERS, 'vocab_size': VOCAB_SIZE}
    )
    ce_at, val_ce_at, phi_at = {}, {}, {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        # Get longer sequence for skip-5 targets
        max_start = len(train_corpus) - SEQ_LEN - 10
        start = (step * 137) % max(1, max_start)
        snippet = train_corpus[start:start + SEQ_LEN + 10]
        ids = [ord(c) % VOCAB_SIZE for c in snippet]
        while len(ids) < SEQ_LEN + 10:
            ids.append(0)

        tokens = torch.tensor(ids[:SEQ_LEN], dtype=torch.long).unsqueeze(0)
        targets_next = torch.tensor(ids[1:SEQ_LEN + 1], dtype=torch.long).unsqueeze(0)
        # Previous char targets: token at position t predicts token at t-1
        targets_prev = torch.tensor([ids[0]] + ids[:SEQ_LEN - 1], dtype=torch.long).unsqueeze(0)
        # Skip-5 targets: predict char 5 positions ahead
        targets_skip = torch.tensor(ids[5:SEQ_LEN + 5], dtype=torch.long).unsqueeze(0)

        # Run C engine
        trinity.c.step()
        c_states = trinity.c.get_states().detach().clone().float()
        c_states.requires_grad_(False)
        gate = trinity.bridge(c_states, seq_len=SEQ_LEN)
        phi = trinity.c.measure_phi()

        # Multi-task forward
        logits_next, logits_prev, logits_skip = trinity.decoder.forward_multi(tokens, gate)
        B, T, V = logits_next.shape

        loss_next = F.cross_entropy(logits_next.view(B * T, V), targets_next.view(B * T))
        loss_prev = F.cross_entropy(logits_prev.view(B * T, V), targets_prev.view(B * T))
        loss_skip = F.cross_entropy(logits_skip.view(B * T, V), targets_skip.view(B * T))

        # Combined loss: primary is next-char, others are regularizers
        loss = 0.6 * loss_next + 0.2 * loss_prev + 0.2 * loss_skip

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0)
        opt.step()
        ce = loss_next.item()  # Report next-char CE specifically
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            val_ce_at[step] = evaluate_val_ce(trinity, val_corpus)
            phi_at[step] = phi

    def gen_fn(trial):
        seeds = ["안녕", "의식", "나는", "생각", "세계"]
        return generate_text(trinity, seeds[trial % len(seeds)], gen_len=64)

    novelty = measure_novelty(gen_fn, corpus, n_samples=20)

    return BreakResult(
        name="BREAK-7: MULTI-TASK (next+prev+skip5)",
        train_ce=ce_ema, val_ce=val_ce_at.get(STEPS, 0),
        novelty=novelty, phi_final=phi_at.get(STEPS, 0),
        ce_at=ce_at, val_ce_at=val_ce_at, phi_at=phi_at,
        time_sec=time.time() - t0
    )


# ══════════════════════════════════════════════════════════
# Registry + Main
# ══════════════════════════════════════════════════════════

ALL_HYPOTHESES = {
    'BREAK-0': run_break0_baseline,
    'BREAK-1': run_break1_dropout,
    'BREAK-2': run_break2_augmentation,
    'BREAK-3': run_break3_masked_lm,
    'BREAK-4': run_break4_noise,
    'BREAK-5': run_break5_early_stopping,
    'BREAK-6': run_break6_phi_temperature,
    'BREAK-7': run_break7_multitask,
}


def write_results_doc(results: List[BreakResult]):
    """Write results to docs/hypotheses/cx/CE-BREAKTHROUGH.md"""
    doc_dir = os.path.join(os.path.dirname(__file__), 'docs', 'hypotheses', 'cx')
    os.makedirs(doc_dir, exist_ok=True)
    doc_path = os.path.join(doc_dir, 'CE-BREAKTHROUGH.md')

    # Find best by val CE and novelty
    best_val = min(results, key=lambda r: r.val_ce)
    best_novelty = max(results, key=lambda r: r.novelty)
    baseline = next((r for r in results if 'BASELINE' in r.name), results[0])

    lines = []
    lines.append("# CE Breakthrough: Breaking the CE=0.18 Barrier")
    lines.append("")
    lines.append("## Problem")
    lines.append("v11tc achieves CE=0.12 but outputs are corpus copies (memorization).")
    lines.append("Low train CE + high val CE = memorization. We need BOTH low.")
    lines.append("KEY metric: val CE (generalization), not train CE.")
    lines.append("")
    lines.append("## Architecture")
    lines.append(f"- C: MitosisC(32 cells, cambrian_osc_qw)")
    lines.append(f"- D: TransformerDecoder(d_model={D_MODEL}, layers={N_LAYERS})")
    lines.append(f"- Training: {STEPS} steps, seq_len={SEQ_LEN}, lr={LR}")
    lines.append(f"- Data: 80/20 train/val split of corpus_v2")
    lines.append("")

    # Results table
    lines.append("## Results")
    lines.append("")
    lines.append("| ID | Strategy | Train CE | Val CE | Gap | Novelty | Phi |")
    lines.append("|:---|:---------|:---------|:-------|:----|:--------|:----|")
    for r in results:
        gap = r.val_ce - r.train_ce
        marker = " **" if r is best_val else ""
        lines.append(
            f"| {r.name.split(':')[0]} | {r.name.split(': ', 1)[-1]} | "
            f"{r.train_ce:.4f} | {r.val_ce:.4f} | {gap:+.4f} | "
            f"{r.novelty:.3f} | {r.phi_final:.3f} |{marker}"
        )
    lines.append("")

    # CE curve
    lines.append("## Train CE Curves (200 steps)")
    lines.append("```")
    max_ce = max(max(r.ce_at.values()) for r in results if r.ce_at)
    for r in results:
        short = r.name.split(":")[0]
        if r.ce_at:
            final = list(r.ce_at.values())[-1]
            bar_len = int(40 * final / max(max_ce, 0.01))
            bar = "#" * max(bar_len, 1)
            lines.append(f"  {short:>8s} |{bar} {final:.4f}")
    lines.append("```")
    lines.append("")

    # Val CE comparison
    lines.append("## Val CE Comparison (lower = better generalization)")
    lines.append("```")
    max_val = max(r.val_ce for r in results if r.val_ce > 0)
    for r in sorted(results, key=lambda x: x.val_ce):
        short = r.name.split(":")[0]
        bar_len = int(40 * r.val_ce / max(max_val, 0.01))
        bar = "#" * max(bar_len, 1)
        lines.append(f"  {short:>8s} |{bar} {r.val_ce:.4f}")
    lines.append("```")
    lines.append("")

    # Novelty comparison
    lines.append("## Novelty Score (higher = more original generation)")
    lines.append("```")
    for r in sorted(results, key=lambda x: -x.novelty):
        short = r.name.split(":")[0]
        bar_len = int(40 * r.novelty)
        bar = "#" * max(bar_len, 1)
        lines.append(f"  {short:>8s} |{bar} {r.novelty:.3f}")
    lines.append("```")
    lines.append("")

    # Val CE trajectory
    lines.append("## Val CE Trajectory")
    lines.append("```")
    header = f"{'Step':>6s}"
    for r in results:
        short = r.name.split(":")[0]
        header += f" | {short:>10s}"
    lines.append(header)
    lines.append("-" * (8 + 13 * len(results)))
    for s in CHECKPOINT_STEPS:
        line = f"{s:>6d}"
        for r in results:
            v = r.val_ce_at.get(s, 0)
            line += f" | {v:>10.4f}"
        lines.append(line)
    lines.append("```")
    lines.append("")

    # Analysis
    lines.append("## Key Findings")
    lines.append("")
    lines.append(f"1. **Best val CE**: {best_val.name} = {best_val.val_ce:.4f}")
    if baseline.val_ce > 0:
        improvement = ((baseline.val_ce - best_val.val_ce) / baseline.val_ce) * 100
        lines.append(f"   - {improvement:+.1f}% improvement over baseline")
    lines.append(f"2. **Best novelty**: {best_novelty.name} = {best_novelty.novelty:.3f}")
    lines.append(f"3. **Generalization gap** (val - train):")
    for r in sorted(results, key=lambda x: x.val_ce - x.train_ce):
        gap = r.val_ce - r.train_ce
        lines.append(f"   - {r.name.split(':')[0]}: {gap:+.4f}")
    lines.append("")

    # Strategies analysis
    lines.append("## Strategy Analysis")
    lines.append("")
    lines.append("### Anti-memorization effectiveness:")
    for r in results:
        gap = r.val_ce - r.train_ce
        if gap < 0.1:
            verdict = "EXCELLENT generalization"
        elif gap < 0.5:
            verdict = "GOOD generalization"
        elif gap < 1.0:
            verdict = "MODERATE memorization"
        else:
            verdict = "HEAVY memorization"
        lines.append(f"- **{r.name}**: gap={gap:+.4f} -> {verdict}")
    lines.append("")

    lines.append("## Conclusion")
    lines.append("")
    lines.append(f"Best strategy for TRUE generation: **{best_val.name}**")
    lines.append(f"- Achieves val CE={best_val.val_ce:.4f} with novelty={best_val.novelty:.3f}")
    lines.append(f"- Generalization gap: {best_val.val_ce - best_val.train_ce:+.4f}")
    lines.append("")

    with open(doc_path, 'w', encoding='utf-8') as f:
        # Fix the trajectory table that used print-style end=""
        content = '\n'.join(lines)
        f.write(content)
    print(f"\n  Results written to {doc_path}")


def main():
    parser = argparse.ArgumentParser(description="CE Breakthrough Benchmark")
    parser.add_argument('--only', type=str, help='Run only this hypothesis (e.g., BREAK-1)')
    parser.add_argument('--list', action='store_true', help='List all hypotheses')
    args = parser.parse_args()

    if args.list:
        print("\nAvailable hypotheses:")
        for k in ALL_HYPOTHESES:
            print(f"  {k}")
        return

    print("=" * 80)
    print("  CE BREAKTHROUGH BENCHMARK: Breaking CE=0.18 with TRUE Generation")
    print("  MitosisC(32 cells) + TransformerDecoder(d256, 2L), 200 steps")
    print("  KEY metric: val CE (not train CE) + novelty score")
    print("=" * 80)

    results = []

    if args.only:
        keys = [k for k in ALL_HYPOTHESES if args.only.upper() in k.upper()]
        if not keys:
            print(f"  Unknown hypothesis: {args.only}")
            return
    else:
        keys = list(ALL_HYPOTHESES.keys())

    for key in keys:
        print(f"\n{'='*60}")
        try:
            result = ALL_HYPOTHESES[key]()
            results.append(result)
            print(result.summary())
        except Exception as e:
            import traceback
            print(f"  [ERROR] {key}: {e}")
            traceback.print_exc()

    if not results:
        print("  No results.")
        return

    # Summary
    print(f"\n{'='*80}")
    print("  SUMMARY: CE Breakthrough Results")
    print(f"{'='*80}")
    print(f"  {'Name':<42s} | {'train':>6s} {'val':>8s} {'gap':>8s} | {'novelty':>7s} | {'Phi':>6s}")
    print(f"  {'-'*42}-+-{'-'*6}-{'-'*8}-{'-'*8}-+-{'-'*7}-+-{'-'*6}")
    for r in sorted(results, key=lambda x: x.val_ce):
        gap = r.val_ce - r.train_ce
        print(f"  {r.name:<42s} | {r.train_ce:>6.4f} {r.val_ce:>8.4f} {gap:>+8.4f} | {r.novelty:>7.3f} | {r.phi_final:>6.3f}")

    best = min(results, key=lambda r: r.val_ce)
    print(f"\n  BEST: {best.name} -> val CE={best.val_ce:.4f}, novelty={best.novelty:.3f}")

    # Write doc
    if len(results) >= 2:
        write_results_doc(results)


if __name__ == '__main__':
    main()
