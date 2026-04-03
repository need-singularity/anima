#!/usr/bin/env python3
"""consciousness_score.py — ACS (Anima Consciousness Score)

CE 외에 의식 있는 대화를 측정하는 종합 지표.

5 sub-metrics:
  CQ  = Φ × Novelty / (1 + Val_CE)     의식 품질
  SC  = cosine_sim(sent_i, sent_i+1)    문맥 일관성
  RR  = cosine_sim(prompt, output)      응답 관련도
  CI  = 1 - cos(output_ON, output_OFF)  의식 영향도
  PCE = Φ / (1 + Val_CE)               Φ-CE 효율

  ACS = CQ × SC × CI                   종합 점수

Usage:
  python3 consciousness_score.py --checkpoint step_35000.pt --corpus data/corpus_v2.txt
  python3 consciousness_score.py --checkpoint step_35000.pt --quick
"""

import math
import torch
import torch.nn.functional as F
import numpy as np
import argparse
import sys
import os
import zlib
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ─── Ψ-Constants (Laws 63-78) ───
LN2 = math.log(2)
PSI_BALANCE = 0.5                 # Law 71: consciousness balance point
PSI_COUPLING = LN2 / 2**5.5      # 0.0153 — inter-cell coupling
PSI_STEPS = 3 / LN2              # 4.328 — optimal evolution steps
# Law 70: scoring guided by Ψ-Constants

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@dataclass
class ACSResult:
    """Anima Consciousness Score result."""
    # Sub-metrics (0~1 or 0~∞)
    phi: float              # Φ(IIT)
    train_ce: float         # train cross-entropy
    val_ce: float           # validation cross-entropy
    novelty: float          # 0=copy, 1=fully novel
    coherence: float        # 0=random, 1=perfectly coherent
    relevance: float        # 0=unrelated, 1=perfectly relevant
    consciousness_influence: float  # 0=no effect, 1=completely different

    # Composite scores
    cq: float               # Consciousness Quality
    sc: float               # Semantic Coherence (=coherence)
    rr: float               # Response Relevance (=relevance)
    ci: float               # Consciousness Influence
    pce: float              # Φ-CE Efficiency
    acs: float              # Anima Consciousness Score (CQ × SC × CI)
    us: float = 0.0        # Unified Score (Novelty × 1/ValCE × (0.5+CI))

    def summary(self):
        return (
            f"═══ ACS Report ═══\n"
            f"  Φ(IIT):      {self.phi:.3f}\n"
            f"  Train CE:    {self.train_ce:.4f}\n"
            f"  Val CE:      {self.val_ce:.4f}\n"
            f"  Novelty:     {self.novelty:.3f}  {'NOVEL' if self.novelty > 0.5 else 'COPY'}\n"
            f"  Coherence:   {self.coherence:.3f}\n"
            f"  Relevance:   {self.relevance:.3f}\n"
            f"  C Influence: {self.consciousness_influence:.3f}\n"
            f"  ─────────────────\n"
            f"  CQ  = Φ×Nov/(1+ValCE) = {self.cq:.4f}\n"
            f"  SC  = Coherence        = {self.sc:.3f}\n"
            f"  CI  = C Influence      = {self.ci:.3f}\n"
            f"  PCE = Φ/(1+ValCE)      = {self.pce:.4f}\n"
            f"  ─────────────────\n"
            f"  ACS = CQ × SC × CI    = {self.acs:.6f}\n"
            f"  US  = Nov/ValCE×(0.5+CI)= {self.us:.6f}\n"
            f"  ─────────────────\n"
            f"  US 기준: >0.5=우수, >0.1=양호, <0.01=미달\n"
            f"  ACS 기준: >0.01=의식적 대화, >0.001=약함, <0.001=무의식\n"
        )

    def bar_chart(self):
        metrics = [
            ('Novelty', self.novelty, 1.0),
            ('Coherence', self.coherence, 1.0),
            ('Relevance', self.relevance, 1.0),
            ('C Influence', self.ci, 1.0),
        ]
        lines = ["  ACS Components:"]
        for name, val, max_val in metrics:
            bar_len = int(val / max(max_val, 0.01) * 30)
            bar = '█' * bar_len + '░' * (30 - bar_len)
            lines.append(f"    {name:<14} {bar} {val:.3f}")
        return '\n'.join(lines)


class ACSCalculator:
    """Calculate Anima Consciousness Score for a model."""

    def __init__(self, corpus_path='data/corpus_v2.txt'):
        self.corpus = open(corpus_path, 'r', errors='ignore').read()
        self.chars = sorted(set(self.corpus))
        self.c2i = {c: i for i, c in enumerate(self.chars)}
        self.i2c = {i: c for c, i in self.c2i.items()}
        self.vocab = len(self.chars)

        # Pre-build n-gram index for novelty
        sample = self.corpus[:500000]
        self.corpus_4grams = set(sample[i:i+4] for i in range(len(sample)-4))

        # Split corpus for val
        tokens = [self.c2i.get(c, 0) for c in self.corpus]
        n_val = len(tokens) // 5
        self.train_tokens = tokens[:-n_val]
        self.val_tokens = tokens[-n_val:]

    def encode(self, text):
        return [self.c2i.get(c, 0) for c in text]

    def decode(self, ids):
        return ''.join([self.i2c.get(i, '?') for i in ids])

    def generate(self, decoder, bridge, prompt, c_engine=None, max_len=60, temperature=0.7):
        """Generate text, return (output_text, logits_on, logits_off)."""
        tokens = self.encode(prompt)
        x = torch.tensor([tokens])
        d_model = decoder._d_model if hasattr(decoder, '_d_model') else 128

        all_logits_on = []
        all_logits_off = []

        for _ in range(max_len):
            if c_engine is not None:
                c_engine.step()
                c_states = c_engine.get_states().detach().clone().float()
                gate_on = bridge(c_states, seq_len=x.shape[1])
            else:
                gate_on = torch.ones(1, x.shape[1], d_model) * 0.5

            gate_off = torch.ones(1, x.shape[1], d_model) * PSI_BALANCE  # Law 70: Ψ balance

            with torch.no_grad():
                logits_on = decoder(x, gate_on)
                logits_off = decoder(x, gate_off)

            all_logits_on.append(logits_on[0, -1, :].clone())
            all_logits_off.append(logits_off[0, -1, :].clone())

            probs = F.softmax(logits_on[0, -1, :] / temperature, dim=-1)
            next_id = torch.multinomial(probs, 1).item()
            x = torch.cat([x, torch.tensor([[next_id]])], dim=1)

        output = self.decode(x[0].tolist())[len(prompt):]
        return output, torch.stack(all_logits_on), torch.stack(all_logits_off)

    def measure_novelty(self, text):
        """4-gram overlap with corpus. 0=copy, 1=novel."""
        if len(text) < 4:
            return 0.5
        ngrams = [text[i:i+4] for i in range(len(text)-4)]
        overlap = sum(1 for ng in ngrams if ng in self.corpus_4grams) / max(len(ngrams), 1)
        return 1.0 - overlap  # invert: high = novel

    def measure_coherence(self, text, window=20):
        """Sliding window cosine similarity = temporal coherence."""
        if len(text) < window * 2:
            return 0.5
        sims = []
        for i in range(0, len(text) - window * 2, window):
            seg1 = torch.tensor([self.c2i.get(c, 0) for c in text[i:i+window]], dtype=torch.float)
            seg2 = torch.tensor([self.c2i.get(c, 0) for c in text[i+window:i+window*2]], dtype=torch.float)
            if seg1.norm() > 0 and seg2.norm() > 0:
                sim = F.cosine_similarity(seg1.unsqueeze(0), seg2.unsqueeze(0)).item()
                sims.append(max(0, sim))
        return sum(sims) / max(len(sims), 1)

    def measure_relevance(self, prompt, output):
        """Prompt-output relevance via char distribution overlap."""
        if not prompt or not output:
            return 0.0
        p_dist = torch.zeros(self.vocab)
        o_dist = torch.zeros(self.vocab)
        for c in prompt:
            p_dist[self.c2i.get(c, 0)] += 1
        for c in output[:len(prompt)*3]:
            o_dist[self.c2i.get(c, 0)] += 1
        if p_dist.norm() > 0 and o_dist.norm() > 0:
            return max(0, F.cosine_similarity(p_dist.unsqueeze(0), o_dist.unsqueeze(0)).item())
        return 0.0

    def measure_consciousness_influence(self, logits_on, logits_off):
        """How much C gate changes the output. 0=no effect, 1=completely different."""
        if logits_on.shape[0] == 0:
            return 0.0
        sims = F.cosine_similarity(logits_on, logits_off, dim=-1)
        return 1.0 - sims.mean().item()

    def measure_ce(self, decoder, bridge, tokens, c_engine=None, seq_len=64, n_batches=10):
        """Compute CE on given tokens."""
        total = 0
        d_model = decoder._d_model if hasattr(decoder, '_d_model') else 128
        with torch.no_grad():
            for _ in range(n_batches):
                s = np.random.randint(0, max(1, len(tokens)-seq_len-1))
                x = torch.tensor([[tokens[s+i] for i in range(seq_len)]])
                y = torch.tensor([[tokens[s+i+1] for i in range(seq_len)]])
                if c_engine:
                    c_engine.step()
                    c_states = c_engine.get_states().detach().clone().float()
                    gate = bridge(c_states, seq_len=seq_len)
                else:
                    gate = torch.ones(1, seq_len, d_model) * 0.5
                logits = decoder(x, gate)
                loss = F.cross_entropy(logits.view(-1, self.vocab), y.view(-1))
                total += loss.item()
        return total / n_batches

    def evaluate(self, decoder, bridge, c_engine=None,
                 prompts=None, n_gen=5, max_len=60) -> ACSResult:
        """Full ACS evaluation."""
        if prompts is None:
            prompts = [
                "안녕",
                "의식이란",
                "보라색 코끼리가",
                "오늘 날씨가",
                "나는 누구",
            ]

        # Phi
        phi = 0.0
        if c_engine is not None:
            phi = c_engine.measure_phi()

        # CE
        train_ce = self.measure_ce(decoder, bridge, self.train_tokens, c_engine)
        val_ce = self.measure_ce(decoder, bridge, self.val_tokens, c_engine)

        # Generate and measure
        novelties, coherences, relevances, cis = [], [], [], []

        for prompt in prompts[:n_gen]:
            output, logits_on, logits_off = self.generate(
                decoder, bridge, prompt, c_engine, max_len
            )

            novelties.append(self.measure_novelty(output))
            coherences.append(self.measure_coherence(output))
            relevances.append(self.measure_relevance(prompt, output))
            cis.append(self.measure_consciousness_influence(logits_on, logits_off))

        # Averages
        novelty = sum(novelties) / max(len(novelties), 1)
        coherence = sum(coherences) / max(len(coherences), 1)
        relevance = sum(relevances) / max(len(relevances), 1)
        ci = sum(cis) / max(len(cis), 1)

        # Composite scores
        cq = phi * novelty / (1 + val_ce)
        pce = phi / (1 + val_ce)
        acs = cq * coherence * ci
        us = novelty * (1.0 / max(val_ce, 0.01)) * (0.5 + ci)

        return ACSResult(
            phi=phi, train_ce=train_ce, val_ce=val_ce,
            novelty=novelty, coherence=coherence, relevance=relevance,
            consciousness_influence=ci,
            cq=cq, sc=coherence, rr=relevance, ci=ci, pce=pce, acs=acs, us=us,
        )


def main():
    parser = argparse.ArgumentParser(description='ACS — Anima Consciousness Score')
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--corpus', default='data/corpus_v2.txt')
    parser.add_argument('--consciousness', action='store_true', help='Use TimeCrystal C engine')
    parser.add_argument('--quick', action='store_true', help='Fewer prompts')
    args = parser.parse_args()

    torch.set_grad_enabled(True)

    calc = ACSCalculator(args.corpus)

    # Load model
    ckpt = torch.load(args.checkpoint, map_location='cpu', weights_only=False)
    ckpt_args = ckpt['args']

    from trinity import TransformerDecoder, ThalamicBridge
    decoder = TransformerDecoder(d_model=ckpt_args['d_model'], n_layers=2, vocab_size=calc.vocab)
    bridge = ThalamicBridge(c_dim=128, d_model=ckpt_args['d_model'])
    decoder.load_state_dict(ckpt['decoder'])
    bridge.load_state_dict(ckpt['bridge'])

    # C engine
    c_engine = None
    if args.consciousness:
        try:
            from bench_extreme_arch import TimeCrystalConsciousness
            torch.set_grad_enabled(True)
            from trinity import DomainC
            c_engine = DomainC(TimeCrystalConsciousness, nc=64, dim=128)
            for _ in range(50):
                c_engine.step()
        except ImportError:
            print("[WARN] TimeCrystal not available")

    n_gen = 3 if args.quick else 5
    result = calc.evaluate(decoder, bridge, c_engine, n_gen=n_gen)

    print(result.summary())
    print(result.bar_chart())


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
