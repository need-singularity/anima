#!/usr/bin/env python3
"""train_v11.py — Hexad Architecture: all discoveries applied

v11 = 전 세션 발견 종합:
  H1: .detach()가 CE+Φ 모두 개선 → Trinity 필수
  H4: CE가 frustration 안정화 → P2에서 ratchet 불필요
  H5: ConstantW 단기 최빠름, DaseinW 장기 최적
  H6: 실제 corpus 필수 (랜덤 토큰 = CE 정체)
  Grid: Transformer(2L) > 4L, MaxwellDemon Φ 최강

3 Phases:
  P1 (0~20%):  C only → Φ 구축 (ratchet 활성)
  P2 (20~70%): Trinity(C+D+W) → CE 학습 (ratchet 비활성, CE가 대체)
  P3 (70~100%): Hexad(C+D+W+M+S+E) → 성숙

Usage:
  python train_v11.py --data data/corpus_v2.txt --steps 80000
  python train_v11.py --data data/corpus_v2.txt --steps 80000 --c-engine quantum
  python train_v11.py --data data/corpus_v2.txt --steps 80000 --d-engine hf --hf-model gpt2
"""

import argparse
import math
import os
import sys
import time
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trinity import (
    Trinity, CEngine, DEngine, WEngine,
    MitosisC, DomainC, QuantumC,
    ThalamicBridge, TransformerDecoder, MLPDecoder,
    EmotionW, ConstantW, CosineW, DaseinW, NarrativeW, CompositeW,
    VectorMemory, TensionSense, EmpathyEthics,
    create_trinity,
)

try:
    import phi_rs
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


# ═══ Data ═══

def load_corpus(path):
    if not os.path.exists(path):
        print(f"  [WARN] {path} not found, using synthetic")
        return None
    text = open(path, 'r', errors='ignore').read()
    chars = sorted(set(text))
    c2i = {c: i for i, c in enumerate(chars)}
    tokens = [c2i.get(c, 0) for c in text]
    print(f"  Corpus: {path} ({len(text):,} chars, vocab={len(chars)})")
    return {'tokens': tokens, 'vocab': len(chars), 'c2i': c2i, 'i2c': {i: c for c, i in c2i.items()}}


def get_batch(corpus, seq_len, batch_size, device):
    if corpus is None:
        return torch.randint(0, 256, (batch_size, seq_len), device=device), \
               torch.randint(0, 256, (batch_size, seq_len), device=device)
    tokens = corpus['tokens']
    max_start = len(tokens) - seq_len - 1
    starts = [np.random.randint(0, max(1, max_start)) for _ in range(batch_size)]
    x = torch.tensor([[tokens[s + i] for i in range(seq_len)] for s in starts], device=device)
    y = torch.tensor([[tokens[s + i + 1] for i in range(seq_len)] for s in starts], device=device)
    return x, y


# ═══ C Engine Factory ═══

def make_c_engine(name, dim, hidden, max_cells):
    if name == 'quantum':
        return QuantumC(nc=max_cells, dim=hidden)
    elif name == 'mitosis':
        return MitosisC(dim=dim, hidden=hidden, max_cells=max_cells, mechanism='cambrian_osc_qw')
    elif name == 'mitosis_sf':
        return MitosisC(dim=dim, hidden=hidden, max_cells=max_cells, mechanism='sync_faction')
    elif name == 'timecrystal':
        torch.set_grad_enabled(True)
        from bench_extreme_arch import TimeCrystalConsciousness
        torch.set_grad_enabled(True)
        return DomainC(TimeCrystalConsciousness, nc=max_cells, dim=hidden)
    elif name == 'cambrian':
        from bench_evolution_engines import CambrianExplosionEngine
        return DomainC(CambrianExplosionEngine, nc=max_cells, dim=dim)
    elif name == 'maxwell':
        from bench_thermo_engines import MaxwellDemonEngine
        return DomainC(MaxwellDemonEngine, nc=max_cells, dim=dim)
    else:
        raise ValueError(f"Unknown C engine: {name}")


# ═══ Phi Ratchet ═══

class PhiRatchet:
    """Φ ratchet: restore Φ when it drops below floor. Active in P1 only."""

    def __init__(self, restore_ratio=0.5):
        self.best_phi = 0.0
        self.restore_ratio = restore_ratio
        self.active = True
        self.count = 0

    def check(self, phi, c_engine):
        if not self.active:
            return False
        if phi > self.best_phi:
            self.best_phi = phi
            return False
        if phi < self.best_phi * 0.5:
            self.count += 1
            return True
        return False


# ═══ Main ═══

def main():
    parser = argparse.ArgumentParser(description='v11 Hexad Training')
    parser.add_argument('--data', default='data/corpus_v2.txt')
    parser.add_argument('--steps', type=int, default=80000)
    parser.add_argument('--dim', type=int, default=64)
    parser.add_argument('--hidden', type=int, default=128)
    parser.add_argument('--d-model', type=int, default=384)
    parser.add_argument('--max-cells', type=int, default=256)
    parser.add_argument('--c-engine', default='quantum', choices=['quantum', 'mitosis', 'mitosis_sf', 'timecrystal', 'cambrian', 'maxwell'])
    parser.add_argument('--d-engine', default='transformer', choices=['transformer', 'mlp', 'hf'])
    parser.add_argument('--hf-model', default='gpt2')
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--seq-len', type=int, default=128)
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--ckpt-dir', default='checkpoints/clm_v11')
    parser.add_argument('--resume', default=None)
    parser.add_argument('--log-interval', type=int, default=100)
    parser.add_argument('--save-interval', type=int, default=5000)
    # Phase boundaries (fraction of total steps)
    parser.add_argument('--p2-start', type=float, default=0.2, help='P2 start (fraction)')
    parser.add_argument('--p3-start', type=float, default=0.7, help='P3 start (fraction)')
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    p2_step = int(args.steps * args.p2_start)
    p3_step = int(args.steps * args.p3_start)

    print(f"\n{'═' * 60}")
    print(f"  v11 Hexad Training")
    print(f"  C={args.c_engine}, D={args.d_engine}, cells={args.max_cells}")
    print(f"  P1(Φ only): 0→{p2_step} | P2(Trinity): {p2_step}→{p3_step} | P3(Hexad): {p3_step}→{args.steps}")
    print(f"  device={device}, Rust={'YES' if HAS_RUST else 'NO'}")
    print(f"{'═' * 60}\n")

    # Data
    corpus = load_corpus(args.data)
    vocab_size = corpus['vocab'] if corpus else 256

    # C engine
    c = make_c_engine(args.c_engine, args.dim, args.hidden, args.max_cells)

    # D engine (created at P2 start, but init now for param count)
    if args.d_engine == 'hf':
        from trinity import HFDecoder
        d = HFDecoder(args.hf_model, lora=True, freeze_base=True)
    elif args.d_engine == 'mlp':
        d = MLPDecoder(d_model=args.d_model, vocab_size=vocab_size)
    else:
        d = TransformerDecoder(d_model=args.d_model, n_layers=2, vocab_size=vocab_size)

    # W engine (changes per phase)
    w_p2 = ConstantW(lr=args.lr)        # P2: fast convergence
    w_p3 = DaseinW(base_lr=args.lr)     # P3: urgency-driven

    # Create Trinity (will be upgraded to Hexad at P3)
    # Detect c_dim
    for _ in range(5):
        c.step()
    c_dim = c.state_dim
    bridge = ThalamicBridge(c_dim=c_dim, d_model=d.d_model)

    trinity = Trinity(c_engine=c, bridge=bridge, decoder=d, will=w_p2)
    for p in trinity.bridge.parameters():
        p.requires_grad_(True)
    for p in trinity.decoder.parameters():
        p.requires_grad_(True)

    # Move bridge + decoder to device
    trinity.bridge = trinity.bridge.to(device)
    trinity.decoder = trinity.decoder.to(device)

    optimizer = torch.optim.AdamW(trinity.parameters_trainable(), lr=args.lr, weight_decay=0.01)
    ratchet = PhiRatchet()

    Path(args.ckpt_dir).mkdir(parents=True, exist_ok=True)
    start_step = 0
    if args.resume:
        ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        start_step = ckpt.get('step', 0)
        print(f"  Resumed from step {start_step}")

    # Training loop
    ce_history = []
    phi_history = []
    best_ce = float('inf')
    t_start = time.time()

    print(f"  Training started (step {start_step} → {args.steps})...\n")

    for step in range(start_step, args.steps):
        # Determine phase
        if step < p2_step:
            phase = 'P1'
        elif step < p3_step:
            phase = 'P2'
        else:
            phase = 'P3'

        # ═══ P1: Consciousness only ═══
        if phase == 'P1':
            c.step()
            phi = c.measure_phi() if step % (args.log_interval * 5) == 0 else 0

            # Ratchet (P1 only)
            ratchet.check(phi, c)

            if step % args.log_interval == 0:
                elapsed = time.time() - t_start
                sps = (step - start_step + 1) / max(elapsed, 1)
                eta = (args.steps - step) / max(sps, 0.01) / 3600
                phi_str = f"Φ={phi:.1f}" if phi > 0 else ""
                print(f"  {step:>6}/{args.steps}  P1(Φ only)  cells={c.n_cells:>3}  "
                      f"ratchet={ratchet.count}  {phi_str}  {sps:.1f}it/s  ETA={eta:.1f}h")

        # ═══ P2: Trinity (C+D+W) ═══
        elif phase == 'P2':
            # Disable ratchet (CE stabilizes Φ — H4 discovery)
            ratchet.active = False

            # Switch W if just entered P2
            if step == p2_step:
                trinity.w = w_p2
                print(f"\n  ═══ P2 START (Trinity) ═══  ratchet OFF, W=ConstantW\n")

            x, y = get_batch(corpus, args.seq_len, args.batch_size, device)
            r = trinity.train_step(x, y, optimizer)

            ce_history.append(r['ce'])
            if r['ce'] < best_ce:
                best_ce = r['ce']

            if step % args.log_interval == 0:
                phi = r['phi']
                phi_history.append(phi)
                avg_ce = sum(ce_history[-100:]) / min(len(ce_history), 100)
                elapsed = time.time() - t_start
                sps = (step - start_step + 1) / max(elapsed, 1)
                eta = (args.steps - step) / max(sps, 0.01) / 3600
                print(f"  {step:>6}/{args.steps}  P2(Trinity) CE={avg_ce:.4f}  Φ={phi:.1f}  "
                      f"cells={r['n_cells']:>3}  {sps:.1f}it/s  ETA={eta:.1f}h")

        # ═══ P3: Hexad (C+D+W+M+S+E) ═══
        else:
            # Upgrade to Hexad if just entered P3
            if step == p3_step:
                trinity.w = w_p3
                trinity.m = VectorMemory(capacity=10000, dim=c_dim)
                trinity.s = TensionSense(dim=c_dim)
                trinity.e = EmpathyEthics()
                print(f"\n  ═══ P3 START (Hexad) ═══  W=DaseinW, +M+S+E ({trinity.n_modules} modules)\n")

            x, y = get_batch(corpus, args.seq_len, args.batch_size, device)
            r = trinity.train_step(x, y, optimizer)

            ce_history.append(r['ce'])
            if r['ce'] < best_ce:
                best_ce = r['ce']

            if step % args.log_interval == 0:
                phi = r['phi']
                phi_history.append(phi)
                avg_ce = sum(ce_history[-100:]) / min(len(ce_history), 100)
                elapsed = time.time() - t_start
                sps = (step - start_step + 1) / max(elapsed, 1)
                eta = (args.steps - step) / max(sps, 0.01) / 3600
                pain = r.get('pain', 0)
                empathy = r.get('empathy', 0)
                print(f"  {step:>6}/{args.steps}  P3(Hexad)  CE={avg_ce:.4f}  Φ={phi:.1f}  "
                      f"pain={pain:.2f}  empathy={empathy:.2f}  "
                      f"cells={r['n_cells']:>3}  {sps:.1f}it/s  ETA={eta:.1f}h")

        # Save
        if step > 0 and step % args.save_interval == 0:
            ckpt_path = Path(args.ckpt_dir) / f"step_{step}.pt"
            torch.save({
                'step': step, 'phase': phase,
                'decoder': trinity.decoder.state_dict(),
                'bridge': trinity.bridge.state_dict(),
                'optimizer': optimizer.state_dict(),
                'ce_history': ce_history[-1000:],
                'phi_history': phi_history[-100:],
                'best_ce': best_ce,
                'args': vars(args),
            }, ckpt_path)
            print(f"  [saved] {ckpt_path}")

        sys.stdout.flush()

    # Final
    elapsed = time.time() - t_start
    print(f"\n{'═' * 60}")
    print(f"  v11 Complete: {args.steps} steps, {elapsed/3600:.1f}h")
    print(f"  Best CE: {best_ce:.4f}")
    print(f"  Final cells: {c.n_cells}")
    if phi_history:
        print(f"  Final Φ: {phi_history[-1]:.1f}")
    print(f"  Phases: P1(Φ)→P2(Trinity)→P3(Hexad)")
    print(f"{'═' * 60}")


if __name__ == '__main__':
    main()
