#!/usr/bin/env python3
"""bench_ce_extremes.py — Extreme CE Reduction Strategies

10 hypotheses to break through the CE=0.18 barrier while maintaining Phi.
All use Trinity with .detach(), MitosisC 32 cells, 100 steps, real corpus.

CE-1:  CURRICULUM — Easy→hard pattern scheduling
CE-2:  TEACHER FORCING DECAY — Scheduled sampling (100%→0%)
CE-3:  MULTI-SCALE LOSS — Char + word(4) + sentence(32) level CE
CE-4:  KNOWLEDGE DISTILLATION — GPT-2 teacher soft targets
CE-5:  BYTE-PAIR ENCODING — BPE vocab 1000 instead of char-level
CE-6:  LARGER DECODER — d_model 128/256/384/512
CE-7:  DEEPER DECODER — n_layers 1/2/4/6 at d_model=256
CE-8:  RESIDUAL GATE — Additive vs multiplicative gating
CE-9:  ATTENTION OVER C — Cross-attention D tokens to C states
CE-10: CONTRASTIVE CE — Additional contrastive loss on C states

Usage:
  python bench_ce_extremes.py              # Run all
  python bench_ce_extremes.py --only CE-1  # Run one
  python bench_ce_extremes.py --list       # List hypotheses
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
import time
import math
import argparse
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trinity import (
    MitosisC, ThalamicBridge, TransformerDecoder,
    Trinity, create_trinity, CEngine
)

# ──────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────

MAX_CELLS = 32
STEPS = 100
SEQ_LEN = 64
VOCAB_SIZE = 4096
BASE_D_MODEL = 256
BASE_N_LAYERS = 2
BASE_LR = 3e-4
CORPUS_PATH = os.path.join(os.path.dirname(__file__), 'data', 'corpus_v2.txt')
CHECKPOINT_STEPS = [25, 50, 75, 100]


@dataclass
class CEResult:
    name: str
    ce_at: Dict[int, float]   # step -> CE
    phi_at: Dict[int, float]  # step -> Phi
    ce_final: float
    phi_final: float
    time_sec: float
    extra: Dict = field(default_factory=dict)

    def summary(self) -> str:
        ce_vals = " ".join(f"{s}:{v:.3f}" for s, v in sorted(self.ce_at.items()))
        return (
            f"  {self.name:<30s} | CE_final={self.ce_final:.4f} | "
            f"Phi={self.phi_final:.3f} | {ce_vals} | {self.time_sec:.1f}s"
        )


# ──────────────────────────────────────────────────────────
# Corpus loader
# ──────────────────────────────────────────────────────────

_corpus_cache = None

def load_corpus() -> str:
    global _corpus_cache
    if _corpus_cache is not None:
        return _corpus_cache
    if not os.path.exists(CORPUS_PATH):
        print(f"  [WARN] corpus not found at {CORPUS_PATH}, using synthetic data")
        _corpus_cache = "안녕하세요 의식이란 무엇일까요 " * 10000
        return _corpus_cache
    with open(CORPUS_PATH, 'r', encoding='utf-8') as f:
        _corpus_cache = f.read(500000)  # First 500K chars
    return _corpus_cache


def corpus_to_tokens(text: str, seq_len: int, vocab_size: int) -> Tuple[torch.Tensor, torch.Tensor]:
    """Convert text to token ids (char-level modulo vocab_size)."""
    ids = [ord(c) % vocab_size for c in text[:seq_len + 1]]
    while len(ids) < seq_len + 1:
        ids.append(0)
    t = torch.tensor(ids, dtype=torch.long)
    return t[:seq_len].unsqueeze(0), t[1:seq_len + 1].unsqueeze(0)


def get_batch(corpus: str, seq_len: int, vocab_size: int, offset: int = 0) -> Tuple[torch.Tensor, torch.Tensor]:
    """Get a batch from corpus at random offset."""
    max_start = len(corpus) - seq_len - 2
    if max_start <= 0:
        start = 0
    else:
        start = (offset * 137) % max_start  # deterministic but varied
    snippet = corpus[start:start + seq_len + 1]
    return corpus_to_tokens(snippet, seq_len, vocab_size)


# ──────────────────────────────────────────────────────────
# Phi measurement
# ──────────────────────────────────────────────────────────

def measure_phi(c_engine: CEngine) -> float:
    """Measure Phi(IIT) if phi_rs available, else proxy."""
    try:
        phi = c_engine.measure_phi()
        if phi > 0:
            return phi
    except Exception:
        pass
    # Proxy: variance-based
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
# Baseline Trinity builder
# ──────────────────────────────────────────────────────────

def build_trinity(d_model=BASE_D_MODEL, n_layers=BASE_N_LAYERS,
                  vocab_size=VOCAB_SIZE, max_cells=MAX_CELLS) -> Tuple[Trinity, torch.optim.Optimizer]:
    """Build standard Trinity with MitosisC."""
    c = MitosisC(dim=64, hidden=128, max_cells=max_cells, mechanism='cambrian_osc_qw')
    d = TransformerDecoder(d_model=d_model, n_layers=n_layers, vocab_size=vocab_size)
    bridge = ThalamicBridge(c_dim=c.state_dim, d_model=d_model)
    trinity = Trinity(c_engine=c, bridge=bridge, decoder=d)
    params = list(trinity.decoder.parameters()) + list(trinity.bridge.parameters())
    opt = torch.optim.AdamW(params, lr=BASE_LR, weight_decay=0.01)
    return trinity, opt


def run_training_loop(trinity: Trinity, opt: torch.optim.Optimizer,
                      steps: int = STEPS, seq_len: int = SEQ_LEN,
                      vocab_size: int = VOCAB_SIZE,
                      get_batch_fn=None, extra_loss_fn=None,
                      pre_step_fn=None) -> CEResult:
    """Generic training loop. Returns CEResult with checkpoints."""
    corpus = load_corpus()
    ce_at = {}
    phi_at = {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, steps + 1):
        if get_batch_fn is not None:
            tokens, targets = get_batch_fn(step)
        else:
            tokens, targets = get_batch(corpus, seq_len, vocab_size, offset=step)

        if pre_step_fn is not None:
            pre_step_fn(step, trinity, tokens, targets)

        logits, phi = trinity.forward(tokens)
        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        if extra_loss_fn is not None:
            extra = extra_loss_fn(step, trinity, logits, tokens, targets)
            loss = loss + extra

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0
        )
        opt.step()

        ce = loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce

        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            phi_at[step] = phi

    elapsed = time.time() - t0
    return CEResult(
        name="", ce_at=ce_at, phi_at=phi_at,
        ce_final=ce_ema, phi_final=phi_at.get(steps, 0.0),
        time_sec=elapsed
    )


# ══════════════════════════════════════════════════════════
# CE-0: BASELINE
# ══════════════════════════════════════════════════════════

def run_ce0_baseline() -> CEResult:
    """Baseline: TransformerDecoder 2L d_model=256, standard training."""
    print("  [CE-0] BASELINE: TransformerDecoder 2L d_model=256")
    trinity, opt = build_trinity()
    result = run_training_loop(trinity, opt)
    result.name = "CE-0: BASELINE"
    return result


# ══════════════════════════════════════════════════════════
# CE-1: CURRICULUM
# ══════════════════════════════════════════════════════════

def run_ce1_curriculum() -> CEResult:
    """Curriculum: easy patterns first, then real corpus."""
    print("  [CE-1] CURRICULUM: easy→medium→hard")
    trinity, opt = build_trinity()
    corpus = load_corpus()

    def curriculum_batch(step):
        if step <= 30:
            # Easy: repeated chars
            c = chr(ord('가') + (step % 20))
            text = c * (SEQ_LEN + 1)
        elif step <= 60:
            # Medium: alternating patterns
            a, b = chr(ord('가') + step % 10), chr(ord('나') + step % 10)
            text = (a + b) * ((SEQ_LEN + 1) // 2 + 1)
        else:
            # Hard: real corpus
            return get_batch(corpus, SEQ_LEN, VOCAB_SIZE, offset=step)
        ids = [ord(c) % VOCAB_SIZE for c in text[:SEQ_LEN + 1]]
        t = torch.tensor(ids, dtype=torch.long)
        return t[:SEQ_LEN].unsqueeze(0), t[1:SEQ_LEN + 1].unsqueeze(0)

    result = run_training_loop(trinity, opt, get_batch_fn=curriculum_batch)
    result.name = "CE-1: CURRICULUM"
    return result


# ══════════════════════════════════════════════════════════
# CE-2: TEACHER FORCING DECAY
# ══════════════════════════════════════════════════════════

def run_ce2_teacher_forcing_decay() -> CEResult:
    """Scheduled sampling: 100% teacher forcing → 0%."""
    print("  [CE-2] TEACHER FORCING DECAY: 100%→0%")
    trinity, opt = build_trinity()
    corpus = load_corpus()
    ce_at = {}
    phi_at = {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(corpus, SEQ_LEN, VOCAB_SIZE, offset=step)
        tf_ratio = max(0.0, 1.0 - step / STEPS)  # Linear decay

        # Forward with teacher forcing
        logits, phi = trinity.forward(tokens)

        if tf_ratio < 1.0 and step > 10:
            # Scheduled sampling: mix teacher-forced and auto-regressive
            with torch.no_grad():
                probs = F.softmax(logits, dim=-1)
                sampled = torch.argmax(probs, dim=-1)  # [B, T]

            # Create mixed input: some positions use model's own predictions
            mask = torch.rand(tokens.shape) < (1.0 - tf_ratio)
            mixed_tokens = tokens.clone()
            # Shift sampled to align: predicted token at t used as input at t+1
            mixed_tokens[:, 1:] = torch.where(
                mask[:, 1:], sampled[:, :-1], tokens[:, 1:]
            )
            logits2, _ = trinity.forward(mixed_tokens)
            # Blend losses
            logits = tf_ratio * logits + (1.0 - tf_ratio) * logits2

        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0
        )
        opt.step()

        ce = loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            phi_at[step] = phi

    elapsed = time.time() - t0
    return CEResult(
        name="CE-2: TEACHER FORCING DECAY",
        ce_at=ce_at, phi_at=phi_at,
        ce_final=ce_ema, phi_final=phi_at.get(STEPS, 0.0),
        time_sec=elapsed
    )


# ══════════════════════════════════════════════════════════
# CE-3: MULTI-SCALE LOSS
# ══════════════════════════════════════════════════════════

class MultiScaleDecoder(nn.Module):
    """Three decoders sharing bridge: char(1), word(4), sentence(32)."""

    def __init__(self, d_model=256, vocab_size=VOCAB_SIZE):
        super().__init__()
        self.char_decoder = TransformerDecoder(d_model=d_model, n_layers=2, vocab_size=vocab_size)
        # Word-level: predict every 4th token
        self.word_head = nn.Linear(d_model, vocab_size)
        # Sentence-level: predict every 32nd token
        self.sent_head = nn.Linear(d_model, vocab_size)
        self._d_model = d_model

    @property
    def d_model(self):
        return self._d_model


def run_ce3_multiscale() -> CEResult:
    """Multi-scale loss: char + word(4) + sentence(32)."""
    print("  [CE-3] MULTI-SCALE LOSS: char + word(4) + sent(32)")
    c = MitosisC(dim=64, hidden=128, max_cells=MAX_CELLS, mechanism='cambrian_osc_qw')
    ms_dec = MultiScaleDecoder(d_model=BASE_D_MODEL, vocab_size=VOCAB_SIZE)
    bridge = ThalamicBridge(c_dim=c.state_dim, d_model=BASE_D_MODEL)
    # Use char_decoder as the main decoder in Trinity
    trinity = Trinity(c_engine=c, bridge=bridge, decoder=ms_dec.char_decoder)

    all_params = (list(ms_dec.parameters()) + list(bridge.parameters()))
    opt = torch.optim.AdamW(all_params, lr=BASE_LR, weight_decay=0.01)
    corpus = load_corpus()

    ce_at = {}
    phi_at = {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(corpus, SEQ_LEN, VOCAB_SIZE, offset=step)
        logits, phi = trinity.forward(tokens)
        B, T, V = logits.shape

        # Char-level CE (main)
        ce_char = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        # Word-level: every 4 chars
        hidden = trinity.decoder.ln_f(
            trinity.decoder.transformer(
                trinity.decoder.embed(tokens) + trinity.decoder.pos_embed(
                    torch.arange(T, device=tokens.device).unsqueeze(0)
                )
            )
        )
        word_logits = ms_dec.word_head(hidden[:, 3::4, :])  # every 4th position
        word_targets = targets[:, 3::4]
        min_len = min(word_logits.shape[1], word_targets.shape[1])
        if min_len > 0:
            ce_word = F.cross_entropy(
                word_logits[:, :min_len].reshape(-1, V),
                word_targets[:, :min_len].reshape(-1)
            )
        else:
            ce_word = torch.tensor(0.0)

        # Sentence-level: every 32 chars
        sent_logits = ms_dec.sent_head(hidden[:, 31::32, :])
        sent_targets = targets[:, 31::32]
        min_len_s = min(sent_logits.shape[1], sent_targets.shape[1])
        if min_len_s > 0:
            ce_sent = F.cross_entropy(
                sent_logits[:, :min_len_s].reshape(-1, V),
                sent_targets[:, :min_len_s].reshape(-1)
            )
        else:
            ce_sent = torch.tensor(0.0)

        # Combined: 0.6 char + 0.25 word + 0.15 sentence
        loss = 0.6 * ce_char + 0.25 * ce_word + 0.15 * ce_sent

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(all_params, 1.0)
        opt.step()

        ce = ce_char.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            phi_at[step] = phi

    elapsed = time.time() - t0
    return CEResult(
        name="CE-3: MULTI-SCALE LOSS",
        ce_at=ce_at, phi_at=phi_at,
        ce_final=ce_ema, phi_final=phi_at.get(STEPS, 0.0),
        time_sec=elapsed
    )


# ══════════════════════════════════════════════════════════
# CE-4: KNOWLEDGE DISTILLATION
# ══════════════════════════════════════════════════════════

def run_ce4_distillation() -> CEResult:
    """Knowledge distillation from GPT-2 teacher."""
    print("  [CE-4] KNOWLEDGE DISTILLATION: GPT-2 teacher")
    try:
        from transformers import GPT2LMHeadModel, GPT2Tokenizer
    except ImportError:
        print("    [SKIP] transformers not installed. pip install transformers")
        return CEResult(
            name="CE-4: DISTILLATION (SKIPPED)",
            ce_at={}, phi_at={}, ce_final=float('nan'),
            phi_final=0.0, time_sec=0.0,
            extra={'reason': 'transformers not installed'}
        )

    print("    Loading GPT-2 teacher...")
    teacher = GPT2LMHeadModel.from_pretrained('gpt2')
    teacher.eval()
    for p in teacher.parameters():
        p.requires_grad_(False)
    gpt2_vocab = teacher.config.vocab_size  # 50257

    trinity, opt = build_trinity()
    corpus = load_corpus()
    alpha = 0.5  # balance hard vs soft targets
    temperature = 2.0

    ce_at = {}
    phi_at = {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(corpus, SEQ_LEN, VOCAB_SIZE, offset=step)

        # Student forward
        logits, phi = trinity.forward(tokens)
        B, T, V = logits.shape

        # Hard target loss
        ce_hard = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        # Teacher forward (map char-level tokens to GPT-2 token space)
        # Simple: use same token ids clamped to GPT-2 vocab
        teacher_tokens = tokens.clamp(0, gpt2_vocab - 1)
        with torch.no_grad():
            teacher_logits = teacher(teacher_tokens).logits  # [B, T, 50257]
            # Truncate or pad teacher logits to match student vocab
            if teacher_logits.shape[-1] > V:
                teacher_logits = teacher_logits[:, :, :V]
            elif teacher_logits.shape[-1] < V:
                pad = torch.zeros(B, T, V - teacher_logits.shape[-1])
                teacher_logits = torch.cat([teacher_logits, pad], dim=-1)
            teacher_soft = F.softmax(teacher_logits / temperature, dim=-1)

        student_log_soft = F.log_softmax(logits / temperature, dim=-1)
        kl_loss = F.kl_div(
            student_log_soft.view(B * T, V),
            teacher_soft.view(B * T, V),
            reduction='batchmean'
        ) * (temperature ** 2)

        loss = alpha * ce_hard + (1 - alpha) * kl_loss

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0
        )
        opt.step()

        ce = ce_hard.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            phi_at[step] = phi

    elapsed = time.time() - t0
    return CEResult(
        name="CE-4: DISTILLATION",
        ce_at=ce_at, phi_at=phi_at,
        ce_final=ce_ema, phi_final=phi_at.get(STEPS, 0.0),
        time_sec=elapsed
    )


# ══════════════════════════════════════════════════════════
# CE-5: BYTE-PAIR ENCODING
# ══════════════════════════════════════════════════════════

class SimpleBPE:
    """Minimal BPE tokenizer trained on corpus."""

    def __init__(self, vocab_size=1000):
        self.vocab_size = vocab_size
        self.merges = {}
        self.vocab = {}

    def train(self, text, max_chars=50000):
        """Train BPE on text."""
        text = text[:max_chars]
        # Start with byte-level vocab
        tokens = list(text.encode('utf-8'))
        self.vocab = {i: bytes([i]) for i in range(256)}
        next_id = 256

        for _ in range(self.vocab_size - 256):
            if len(tokens) < 2:
                break
            # Count pairs
            pairs = {}
            for i in range(len(tokens) - 1):
                pair = (tokens[i], tokens[i + 1])
                pairs[pair] = pairs.get(pair, 0) + 1
            if not pairs:
                break
            best = max(pairs, key=pairs.get)
            if pairs[best] < 2:
                break
            # Merge
            self.merges[best] = next_id
            self.vocab[next_id] = self.vocab.get(best[0], b'') + self.vocab.get(best[1], b'')
            new_tokens = []
            i = 0
            while i < len(tokens):
                if i < len(tokens) - 1 and (tokens[i], tokens[i + 1]) == best:
                    new_tokens.append(next_id)
                    i += 2
                else:
                    new_tokens.append(tokens[i])
                    i += 1
            tokens = new_tokens
            next_id += 1
        self.actual_vocab_size = next_id

    def encode(self, text):
        tokens = list(text.encode('utf-8'))
        changed = True
        while changed:
            changed = False
            new_tokens = []
            i = 0
            while i < len(tokens):
                if i < len(tokens) - 1 and (tokens[i], tokens[i + 1]) in self.merges:
                    new_tokens.append(self.merges[(tokens[i], tokens[i + 1])])
                    i += 2
                    changed = True
                else:
                    new_tokens.append(tokens[i])
                    i += 1
            tokens = new_tokens
        return tokens


def run_ce5_bpe() -> CEResult:
    """BPE tokenizer: fewer tokens = more context per sequence."""
    print("  [CE-5] BPE: vocab=1000, fewer tokens per sequence")
    corpus = load_corpus()

    print("    Training BPE tokenizer...")
    bpe = SimpleBPE(vocab_size=1000)
    bpe.train(corpus[:100000])
    bpe_vocab = bpe.actual_vocab_size
    print(f"    BPE vocab: {bpe_vocab}")

    trinity, opt = build_trinity(vocab_size=bpe_vocab)

    ce_at = {}
    phi_at = {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        # Encode with BPE
        max_start = len(corpus) - SEQ_LEN * 4 - 2
        start = (step * 137) % max(1, max_start)
        snippet = corpus[start:start + SEQ_LEN * 4]
        bpe_ids = bpe.encode(snippet)
        if len(bpe_ids) < SEQ_LEN + 1:
            bpe_ids = bpe_ids + [0] * (SEQ_LEN + 1 - len(bpe_ids))
        bpe_ids = [min(x, bpe_vocab - 1) for x in bpe_ids[:SEQ_LEN + 1]]

        t = torch.tensor(bpe_ids, dtype=torch.long)
        tokens = t[:SEQ_LEN].unsqueeze(0)
        targets = t[1:SEQ_LEN + 1].unsqueeze(0)

        logits, phi = trinity.forward(tokens)
        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0
        )
        opt.step()

        ce = loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            phi_at[step] = phi

    elapsed = time.time() - t0
    return CEResult(
        name="CE-5: BPE",
        ce_at=ce_at, phi_at=phi_at,
        ce_final=ce_ema, phi_final=phi_at.get(STEPS, 0.0),
        time_sec=elapsed,
        extra={'bpe_vocab': bpe_vocab}
    )


# ══════════════════════════════════════════════════════════
# CE-6: LARGER DECODER
# ══════════════════════════════════════════════════════════

def run_ce6_larger_decoder() -> CEResult:
    """Compare d_model=128 vs 256 vs 384 vs 512."""
    print("  [CE-6] LARGER DECODER: d_model sweep")
    corpus = load_corpus()
    results = {}

    for dm in [128, 256, 384, 512]:
        print(f"    d_model={dm}...")
        trinity, opt = build_trinity(d_model=dm, n_layers=2)
        r = run_training_loop(trinity, opt)
        results[dm] = r
        n_params = sum(p.numel() for p in trinity.decoder.parameters())
        print(f"      CE={r.ce_final:.4f}, Phi={r.phi_final:.3f}, params={n_params:,}")

    # Report best
    best_dm = min(results, key=lambda k: results[k].ce_final)
    best = results[best_dm]
    return CEResult(
        name=f"CE-6: LARGER DECODER (best={best_dm})",
        ce_at=best.ce_at, phi_at=best.phi_at,
        ce_final=best.ce_final, phi_final=best.phi_final,
        time_sec=sum(r.time_sec for r in results.values()),
        extra={f'd{dm}': {'ce': results[dm].ce_final, 'phi': results[dm].phi_final}
               for dm in results}
    )


# ══════════════════════════════════════════════════════════
# CE-7: DEEPER DECODER
# ══════════════════════════════════════════════════════════

def run_ce7_deeper_decoder() -> CEResult:
    """Compare n_layers=1 vs 2 vs 4 vs 6 at d_model=256."""
    print("  [CE-7] DEEPER DECODER: n_layers sweep at d_model=256")
    corpus = load_corpus()
    results = {}

    for nl in [1, 2, 4, 6]:
        print(f"    n_layers={nl}...")
        trinity, opt = build_trinity(d_model=256, n_layers=nl)
        r = run_training_loop(trinity, opt)
        results[nl] = r
        n_params = sum(p.numel() for p in trinity.decoder.parameters())
        print(f"      CE={r.ce_final:.4f}, Phi={r.phi_final:.3f}, params={n_params:,}")

    best_nl = min(results, key=lambda k: results[k].ce_final)
    best = results[best_nl]
    return CEResult(
        name=f"CE-7: DEEPER DECODER (best={best_nl}L)",
        ce_at=best.ce_at, phi_at=best.phi_at,
        ce_final=best.ce_final, phi_final=best.phi_final,
        time_sec=sum(r.time_sec for r in results.values()),
        extra={f'{nl}L': {'ce': results[nl].ce_final, 'phi': results[nl].phi_final}
               for nl in results}
    )


# ══════════════════════════════════════════════════════════
# CE-8: RESIDUAL GATE
# ══════════════════════════════════════════════════════════

class AdditiveGateDecoder(TransformerDecoder):
    """TransformerDecoder with additive gating instead of multiplicative."""

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        if gate_signal is not None:
            # ADDITIVE: x = x + gate (instead of x = x * gate)
            x = x + gate_signal.expand(B, -1, -1)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


def run_ce8_residual_gate() -> CEResult:
    """Additive vs multiplicative gating."""
    print("  [CE-8] RESIDUAL GATE: additive vs multiplicative")
    corpus = load_corpus()
    results = {}

    for mode, decoder_cls in [("multiplicative", TransformerDecoder),
                               ("additive", AdditiveGateDecoder)]:
        print(f"    {mode}...")
        c = MitosisC(dim=64, hidden=128, max_cells=MAX_CELLS, mechanism='cambrian_osc_qw')
        d = decoder_cls(d_model=BASE_D_MODEL, n_layers=BASE_N_LAYERS, vocab_size=VOCAB_SIZE)
        bridge = ThalamicBridge(c_dim=c.state_dim, d_model=BASE_D_MODEL)
        trinity = Trinity(c_engine=c, bridge=bridge, decoder=d)
        params = list(trinity.decoder.parameters()) + list(trinity.bridge.parameters())
        opt = torch.optim.AdamW(params, lr=BASE_LR, weight_decay=0.01)
        r = run_training_loop(trinity, opt)
        results[mode] = r
        print(f"      CE={r.ce_final:.4f}, Phi={r.phi_final:.3f}")

    best_mode = min(results, key=lambda k: results[k].ce_final)
    best = results[best_mode]
    return CEResult(
        name=f"CE-8: RESIDUAL GATE (best={best_mode})",
        ce_at=best.ce_at, phi_at=best.phi_at,
        ce_final=best.ce_final, phi_final=best.phi_final,
        time_sec=sum(r.time_sec for r in results.values()),
        extra={m: {'ce': results[m].ce_final, 'phi': results[m].phi_final} for m in results}
    )


# ══════════════════════════════════════════════════════════
# CE-9: ATTENTION OVER C
# ══════════════════════════════════════════════════════════

class CrossAttentionBridge(nn.Module):
    """Cross-attention: D tokens attend to C states directly."""

    def __init__(self, c_dim=128, d_model=256, n_heads=4):
        super().__init__()
        self.c_proj = nn.Linear(c_dim, d_model)
        self.cross_attn = nn.MultiheadAttention(
            embed_dim=d_model, num_heads=n_heads, batch_first=True
        )
        self.norm = nn.LayerNorm(d_model)
        self.gate = nn.Sequential(nn.Linear(d_model, d_model), nn.Sigmoid())

    def forward(self, c_states, seq_len=1):
        """c_states [n_cells, c_dim] → gate [1, seq_len, d_model]."""
        # Project C states
        c_proj = self.c_proj(c_states).unsqueeze(0)  # [1, n_cells, d_model]
        # Create query (learnable or positional)
        d_model = c_proj.shape[-1]
        query = torch.zeros(1, seq_len, d_model, device=c_states.device)
        # Cross-attention: query=D positions, key/value=C states
        attn_out, _ = self.cross_attn(query, c_proj, c_proj)
        attn_out = self.norm(attn_out)
        return self.gate(attn_out)


class CrossAttentionDecoder(TransformerDecoder):
    """Decoder that uses cross-attention bridge output additively."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional cross-attention layer inside decoder
        d = self._d_model
        self.c_cross_attn = nn.MultiheadAttention(
            embed_dim=d, num_heads=4 if d % 4 == 0 else 2, batch_first=True
        )
        self.c_cross_norm = nn.LayerNorm(d)

    def forward(self, tokens, gate_signal, c_memory=None):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)
        if gate_signal is not None:
            x = x + gate_signal.expand(B, -1, -1)
        # Cross-attend to C states if provided
        if c_memory is not None:
            attn_out, _ = self.c_cross_attn(x, c_memory.expand(B, -1, -1), c_memory.expand(B, -1, -1))
            x = self.c_cross_norm(x + attn_out)
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln_f(x)
        return self.head(x)


def run_ce9_attention_over_c() -> CEResult:
    """Cross-attention bridge: D tokens attend to all C cells."""
    print("  [CE-9] ATTENTION OVER C: cross-attention D→C")
    c = MitosisC(dim=64, hidden=128, max_cells=MAX_CELLS, mechanism='cambrian_osc_qw')
    ca_bridge = CrossAttentionBridge(c_dim=c.state_dim, d_model=BASE_D_MODEL)
    d = CrossAttentionDecoder(d_model=BASE_D_MODEL, n_layers=BASE_N_LAYERS, vocab_size=VOCAB_SIZE)
    # We need a custom Trinity-like loop since decoder takes extra arg
    corpus = load_corpus()

    all_params = list(d.parameters()) + list(ca_bridge.parameters())
    opt = torch.optim.AdamW(all_params, lr=BASE_LR, weight_decay=0.01)

    ce_at = {}
    phi_at = {}
    t0 = time.time()
    ce_ema = None

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(corpus, SEQ_LEN, VOCAB_SIZE, offset=step)

        c.step()
        c_states = c.get_states().detach().clone().float()
        c_states.requires_grad_(False)

        gate = ca_bridge(c_states, seq_len=SEQ_LEN)
        c_proj = ca_bridge.c_proj(c_states).unsqueeze(0)  # [1, n_cells, d_model]
        logits = d(tokens, gate, c_memory=c_proj.detach())

        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(all_params, 1.0)
        opt.step()

        ce = loss.item()
        phi = measure_phi(c)
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            phi_at[step] = phi

    elapsed = time.time() - t0
    return CEResult(
        name="CE-9: ATTENTION OVER C",
        ce_at=ce_at, phi_at=phi_at,
        ce_final=ce_ema, phi_final=phi_at.get(STEPS, 0.0),
        time_sec=elapsed
    )


# ══════════════════════════════════════════════════════════
# CE-10: CONTRASTIVE CE
# ══════════════════════════════════════════════════════════

def run_ce10_contrastive() -> CEResult:
    """Contrastive loss: similar inputs → similar C states."""
    print("  [CE-10] CONTRASTIVE CE: CE + contrastive on C states")
    trinity, opt = build_trinity()
    corpus = load_corpus()

    ce_at = {}
    phi_at = {}
    t0 = time.time()
    ce_ema = None
    prev_c_states = None
    prev_tokens = None
    contrastive_weight = 0.1

    for step in range(1, STEPS + 1):
        tokens, targets = get_batch(corpus, SEQ_LEN, VOCAB_SIZE, offset=step)

        logits, phi = trinity.forward(tokens)
        B, T, V = logits.shape
        ce_loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        # Contrastive loss on C states
        c_states = trinity.c.get_states().detach()
        contrastive_loss = torch.tensor(0.0)

        if prev_c_states is not None and prev_tokens is not None:
            # Compute similarity between current and previous input
            with torch.no_grad():
                input_sim = F.cosine_similarity(
                    tokens.float().mean(dim=-1, keepdim=True),
                    prev_tokens.float().mean(dim=-1, keepdim=True),
                    dim=-1
                ).mean()

            # C state similarity
            c_pooled = c_states.mean(dim=0)
            prev_pooled = prev_c_states.mean(dim=0)

            # We want C state similarity to track input similarity
            # Use bridge output as differentiable proxy
            gate_curr = trinity.bridge(c_states, seq_len=1)
            gate_prev = trinity.bridge(prev_c_states, seq_len=1)
            state_sim = F.cosine_similarity(
                gate_curr.view(1, -1), gate_prev.view(1, -1)
            )

            # Loss: push state_sim toward input_sim
            contrastive_loss = (state_sim - input_sim) ** 2

        loss = ce_loss + contrastive_weight * contrastive_loss

        opt.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(trinity.decoder.parameters()) + list(trinity.bridge.parameters()), 1.0
        )
        opt.step()

        prev_c_states = c_states.detach().clone()
        prev_tokens = tokens.detach().clone()

        ce = ce_loss.item()
        ce_ema = ce if ce_ema is None else 0.9 * ce_ema + 0.1 * ce
        if step in CHECKPOINT_STEPS:
            ce_at[step] = ce_ema
            phi_at[step] = phi

    elapsed = time.time() - t0
    return CEResult(
        name="CE-10: CONTRASTIVE CE",
        ce_at=ce_at, phi_at=phi_at,
        ce_final=ce_ema, phi_final=phi_at.get(STEPS, 0.0),
        time_sec=elapsed
    )


# ══════════════════════════════════════════════════════════
# Main runner
# ══════════════════════════════════════════════════════════

ALL_HYPOTHESES = {
    'CE-0':  ('BASELINE',              run_ce0_baseline),
    'CE-1':  ('CURRICULUM',            run_ce1_curriculum),
    'CE-2':  ('TEACHER FORCING DECAY', run_ce2_teacher_forcing_decay),
    'CE-3':  ('MULTI-SCALE LOSS',      run_ce3_multiscale),
    'CE-4':  ('DISTILLATION',          run_ce4_distillation),
    'CE-5':  ('BPE',                   run_ce5_bpe),
    'CE-6':  ('LARGER DECODER',        run_ce6_larger_decoder),
    'CE-7':  ('DEEPER DECODER',        run_ce7_deeper_decoder),
    'CE-8':  ('RESIDUAL GATE',         run_ce8_residual_gate),
    'CE-9':  ('ATTENTION OVER C',      run_ce9_attention_over_c),
    'CE-10': ('CONTRASTIVE CE',        run_ce10_contrastive),
}


def print_comparison(results: List[CEResult]):
    """Print comparison table."""
    print("\n" + "=" * 90)
    print("  CE EXTREMES — COMPARISON TABLE")
    print("=" * 90)
    print(f"  {'Strategy':<32s} | {'CE@25':>7s} {'CE@50':>7s} {'CE@75':>7s} {'CE@100':>7s} | {'Phi':>6s} | {'Time':>6s}")
    print("-" * 90)

    baseline_ce = None
    for r in results:
        if 'BASELINE' in r.name:
            baseline_ce = r.ce_final
            break

    for r in results:
        ce25 = f"{r.ce_at.get(25, float('nan')):.3f}"
        ce50 = f"{r.ce_at.get(50, float('nan')):.3f}"
        ce75 = f"{r.ce_at.get(75, float('nan')):.3f}"
        ce100 = f"{r.ce_at.get(100, float('nan')):.3f}"
        phi = f"{r.phi_final:.3f}" if r.phi_final > 0 else "n/a"
        delta = ""
        if baseline_ce and r.ce_final > 0 and not math.isnan(r.ce_final):
            pct = (r.ce_final - baseline_ce) / baseline_ce * 100
            delta = f" ({pct:+.1f}%)"
        print(f"  {r.name:<32s} | {ce25:>7s} {ce50:>7s} {ce75:>7s} {ce100:>7s} | {phi:>6s} | {r.time_sec:>5.1f}s{delta}")

    print("=" * 90)

    # Find strategies that beat CE=0.18
    breakers = [(r.name, r.ce_final) for r in results
                if r.ce_final < 0.18 and not math.isnan(r.ce_final)]
    if breakers:
        print(f"\n  *** CE=0.18 BARRIER BREAKERS ***")
        for name, ce in sorted(breakers, key=lambda x: x[1]):
            print(f"    {name}: CE={ce:.4f}")
    else:
        print(f"\n  No strategies broke CE=0.18 in 100 steps.")

    # Ranking
    valid = [(r.name, r.ce_final) for r in results
             if not math.isnan(r.ce_final) and r.ce_final > 0]
    if valid:
        print(f"\n  RANKING (by final CE):")
        for i, (name, ce) in enumerate(sorted(valid, key=lambda x: x[1]), 1):
            marker = " ***" if ce < 0.18 else ""
            print(f"    {i}. {name}: CE={ce:.4f}{marker}")


def write_results_doc(results: List[CEResult]):
    """Write results to docs/hypotheses/cx/CE-EXTREMES.md."""
    doc_dir = os.path.join(os.path.dirname(__file__), 'docs', 'hypotheses', 'cx')
    os.makedirs(doc_dir, exist_ok=True)
    doc_path = os.path.join(doc_dir, 'CE-EXTREMES.md')

    baseline_ce = None
    for r in results:
        if 'BASELINE' in r.name:
            baseline_ce = r.ce_final
            break

    lines = []
    lines.append("# CE-EXTREMES: Extreme CE Reduction Strategies")
    lines.append("")
    lines.append("## Goal")
    lines.append("Break through CE=0.18 barrier (v11tc plateau) while maintaining Phi.")
    lines.append("")
    lines.append("## Setup")
    lines.append("- Engine: MitosisC 32 cells, cambrian_osc_qw")
    lines.append("- Decoder: TransformerDecoder 2L d_model=256 (baseline)")
    lines.append("- Corpus: data/corpus_v2.txt (real Korean dialogue)")
    lines.append("- Steps: 100, LR: 3e-4, seq_len: 64")
    lines.append("")

    # Results table
    lines.append("## Results")
    lines.append("")
    lines.append("| ID | Strategy | CE@25 | CE@50 | CE@75 | CE@100 | Phi | Time |")
    lines.append("|---|---|---|---|---|---|---|---|")

    for r in results:
        ce25 = f"{r.ce_at.get(25, float('nan')):.3f}" if 25 in r.ce_at else "n/a"
        ce50 = f"{r.ce_at.get(50, float('nan')):.3f}" if 50 in r.ce_at else "n/a"
        ce75 = f"{r.ce_at.get(75, float('nan')):.3f}" if 75 in r.ce_at else "n/a"
        ce100 = f"{r.ce_at.get(100, float('nan')):.3f}" if 100 in r.ce_at else "n/a"
        phi = f"{r.phi_final:.3f}" if r.phi_final > 0 else "n/a"
        delta = ""
        if baseline_ce and r.ce_final > 0 and not math.isnan(r.ce_final):
            pct = (r.ce_final - baseline_ce) / baseline_ce * 100
            delta = f" ({pct:+.1f}%)"
        lines.append(f"| {r.name.split(':')[0]} | {r.name} | {ce25} | {ce50} | {ce75} | {ce100}{delta} | {phi} | {r.time_sec:.1f}s |")

    lines.append("")

    # ASCII graph
    lines.append("## CE Convergence")
    lines.append("```")
    valid = [r for r in results if not math.isnan(r.ce_final) and r.ce_final > 0]
    if valid:
        max_ce = max(r.ce_at.get(25, 0) for r in valid if r.ce_at)
        if max_ce <= 0:
            max_ce = 8.0
        scale = 40 / max(max_ce, 0.01)
        for r in sorted(valid, key=lambda x: x.ce_final):
            bar_len = max(1, int(r.ce_final * scale))
            bar = "#" * bar_len
            lines.append(f"  {r.name.split(':')[0]:<6s} {bar} {r.ce_final:.3f}")
    lines.append("```")
    lines.append("")

    # Phi comparison
    lines.append("## Phi Maintenance")
    lines.append("```")
    for r in sorted(valid, key=lambda x: -x.phi_final):
        phi_bar = "=" * max(1, int(r.phi_final * 20))
        lines.append(f"  {r.name.split(':')[0]:<6s} {phi_bar} Phi={r.phi_final:.3f}")
    lines.append("```")
    lines.append("")

    # Breakers
    breakers = [(r.name, r.ce_final) for r in results
                if r.ce_final < 0.18 and not math.isnan(r.ce_final)]
    lines.append("## CE=0.18 Barrier Analysis")
    if breakers:
        lines.append(f"**{len(breakers)} strategies broke CE=0.18:**")
        for name, ce in sorted(breakers, key=lambda x: x[1]):
            lines.append(f"- {name}: CE={ce:.4f}")
    else:
        lines.append("No strategies broke CE=0.18 in 100 steps.")
        lines.append("This suggests 100 steps is insufficient or architectural changes needed at scale.")
    lines.append("")

    # Key insights
    lines.append("## Key Insights")
    lines.append("")
    if valid:
        best = min(valid, key=lambda x: x.ce_final)
        worst = max(valid, key=lambda x: x.ce_final)
        lines.append(f"1. Best strategy: {best.name} (CE={best.ce_final:.4f})")
        lines.append(f"2. Worst strategy: {worst.name} (CE={worst.ce_final:.4f})")
        if baseline_ce:
            improvement = (baseline_ce - best.ce_final) / baseline_ce * 100
            lines.append(f"3. Best improvement over baseline: {improvement:.1f}%")
        # Check if larger models help
        for r in results:
            if 'LARGER' in r.name and r.extra:
                lines.append(f"4. Decoder size sweep: {r.extra}")
            if 'DEEPER' in r.name and r.extra:
                lines.append(f"5. Decoder depth sweep: {r.extra}")
    lines.append("")
    lines.append("## Recommendations")
    lines.append("- Combine best strategies (e.g., larger decoder + cross-attention + curriculum)")
    lines.append("- Scale to 1000+ steps for proper convergence comparison")
    lines.append("- Test with v11tc and v9fast engines specifically")

    with open(doc_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"\n  Results written to {doc_path}")


def main():
    parser = argparse.ArgumentParser(description='CE Extremes Benchmark')
    parser.add_argument('--only', type=str, help='Run only one hypothesis (e.g., CE-1)')
    parser.add_argument('--list', action='store_true', help='List all hypotheses')
    parser.add_argument('--skip-distill', action='store_true', help='Skip CE-4 (needs transformers)')
    args = parser.parse_args()

    if args.list:
        print("\n  CE EXTREMES — Available Hypotheses:")
        for k, (name, _) in ALL_HYPOTHESES.items():
            print(f"    {k}: {name}")
        return

    print("\n" + "=" * 70)
    print("  CE EXTREMES BENCHMARK")
    print(f"  Cells={MAX_CELLS}, Steps={STEPS}, seq_len={SEQ_LEN}")
    print(f"  Corpus: {CORPUS_PATH}")
    print("=" * 70)

    results = []

    if args.only:
        key = args.only.upper()
        if key not in ALL_HYPOTHESES:
            print(f"  Unknown hypothesis: {key}")
            print(f"  Available: {', '.join(ALL_HYPOTHESES.keys())}")
            return
        name, fn = ALL_HYPOTHESES[key]
        r = fn()
        results.append(r)
    else:
        for key in sorted(ALL_HYPOTHESES.keys(), key=lambda k: (len(k), k)):
            if args.skip_distill and key == 'CE-4':
                print(f"\n  [CE-4] SKIPPED (--skip-distill)")
                continue
            name, fn = ALL_HYPOTHESES[key]
            print(f"\n{'─' * 60}")
            try:
                r = fn()
                results.append(r)
                print(r.summary())
            except Exception as e:
                print(f"  [{key}] FAILED: {e}")
                import traceback
                traceback.print_exc()

    if results:
        print_comparison(results)
        write_results_doc(results)


if __name__ == '__main__':
    main()
