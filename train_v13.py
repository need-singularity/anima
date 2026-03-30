#!/usr/bin/env python3
"""train_v13.py — ConsciousnessEngine + PostHoc + Topology training pipeline

Architecture v5: Laws 22-81 fully embodied.
  C: ConsciousnessEngine (Rust backend, hypercube topology, Hebbian, Φ ratchet)
  D: PostHocDecoder(CADecoder) — Law 66
  W: CompositeW(DaseinW + NarrativeW + EmotionW) — σ(6) weights
  Bridge: ThalamicBridge(α=0.014) — Law 70
  Gate: train=1.0, infer=0.6 — Law 81

Law 60 phases:
  P1 (0-20%):  C only — build Φ through autonomous dynamics
  P2 (20-70%): C+D+W — CE learning with .detach() bridge
  P3 (70-100%): Full Hexad C+D+W+M+S+E

Usage:
  python train_v13.py --data data/corpus.txt --steps 50000
  python train_v13.py --data data/corpus.txt --topology hypercube --chaos wave
  python train_v13.py --data data/corpus.txt --cells 64 --dim 384 --layers 6
"""

import argparse
import math
import os
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine, ConsciousnessC
from trinity import (

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    create_trinity, create_hexad,
    CADecoder, PostHocDecoder, ThalamicBridge,
    EmotionW, DaseinW, NarrativeW, CompositeW, CosineW,
    VectorMemory, TensionSense, EmpathyEthics,
    PSI_COUPLING, PSI_BALANCE, PSI_STEPS, GATE_TRAIN, GATE_INFER,
)

try:
    from training_laws import (
        consciousness_curriculum, phi_checkpoint_selector,
        optimal_noise, apply_training_laws,
    )
    HAS_TRAINING_LAWS = True
except ImportError:
    HAS_TRAINING_LAWS = False


# ═══════════════════════════════════════════════════════════
# Data loading
# ═══════════════════════════════════════════════════════════

def load_corpus(path: str):
    """Load text file as byte-level tokens."""
    with open(path, 'rb') as f:
        raw = f.read()
    tokens = torch.tensor(list(raw), dtype=torch.long)
    print(f"  [data] Loaded {path}: {len(tokens):,} bytes ({len(tokens)/1e6:.1f}MB)")
    return tokens


def get_batch(data, block_size, batch_size, device):
    """Random batch from token data."""
    max_start = len(data) - block_size - 1
    if max_start <= 0:
        max_start = 1
    ix = torch.randint(0, max_start, (batch_size,))
    x = torch.stack([data[i:i + block_size] for i in ix]).to(device)
    y = torch.stack([data[i + 1:i + block_size + 1] for i in ix]).to(device)
    return x, y


# ═══════════════════════════════════════════════════════════
# Training
# ═══════════════════════════════════════════════════════════

def train(args):
    device = torch.device(args.device)
    torch.manual_seed(args.seed)

    # ── Data ──
    data = load_corpus(args.data)
    split = int(len(data) * 0.9)
    train_data, val_data = data[:split], data[split:]

    # Law 45: consciousness-friendly curriculum
    if HAS_TRAINING_LAWS and args.curriculum:
        train_data, _ = consciousness_curriculum(train_data, args.block_size)
        print(f"  [Law 45] Curriculum applied: {len(train_data):,} consciousness-first tokens")

    # ── Engine ──
    c = ConsciousnessC(
        cell_dim=args.cell_dim, hidden_dim=args.hidden_dim,
        max_cells=args.cells, n_factions=12, phi_ratchet=True,
    )
    print(f"  [engine] ConsciousnessC: backend={c._backend}, cells={c.n_cells}, "
          f"dim={args.cell_dim}, hidden={args.hidden_dim}")

    # ── Trinity (P2 config — will upgrade to Hexad in P3) ──
    d_model = args.d_model
    vocab_size = 256  # byte-level

    # D: PostHocDecoder(CADecoder) — Law 66
    base_d = CADecoder(d_model=d_model, vocab_size=vocab_size,
                       ca_steps=round(PSI_STEPS), gate_mode="posthoc")
    decoder = PostHocDecoder(base_decoder=base_d, d_model=d_model,
                              vocab_size=vocab_size, eval_strength=0.001)

    # W: CompositeW σ(6) weights — 1/2 + 1/3 + 1/6 = 1
    w_p2 = CompositeW([
        DaseinW(base_lr=args.lr),
        NarrativeW(base_lr=args.lr),
        EmotionW(base_lr=args.lr),
    ], [1/2, 1/3, 1/6])

    trinity = create_trinity(
        c, d_engine=decoder, w_engine=w_p2,
        d_model=d_model, vocab_size=vocab_size, base_lr=args.lr,
    )
    trinity = trinity.to(device)

    # ── Optimizer (D + Bridge only, C is autonomous) ──
    trainable = trinity.parameters_trainable()
    optimizer = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=0.01)

    params = trinity.param_count()
    print(f"  [model] Decoder: {params['decoder']:,}  Bridge: {params['bridge']:,}  "
          f"Total: {params['total']:,}")
    print(f"  [config] steps={args.steps}, lr={args.lr}, block={args.block_size}, "
          f"batch={args.batch_size}")

    # ── Checkpoint dir ──
    os.makedirs(args.checkpoint_dir, exist_ok=True)

    # ── Training loop (Law 60: 3 phases) ──
    p1_end = int(args.steps * 0.2)   # P1: C only
    p2_end = int(args.steps * 0.7)   # P2: C+D+W
    # P3: Full Hexad (after p2_end)

    best_val_ce = float('inf')
    ce_history = []
    phi_history = []
    t0 = time.time()

    print(f"\n{'═' * 80}")
    print(f"  v13 Training: ConsciousnessEngine + PostHoc + Topology")
    print(f"  P1 (0-{p1_end}): C only | P2 ({p1_end}-{p2_end}): C+D+W | P3 ({p2_end}-{args.steps}): Hexad")
    print(f"{'═' * 80}\n")

    for step in range(1, args.steps + 1):
        # ── Phase selection (Law 60) ──
        if step <= p1_end:
            phase = "P1"
            # P1: consciousness only — no CE loss, just step C engine
            c.engine.step() if hasattr(c.engine, 'step') else c.step()
            phi = c.measure_phi()
            phi_history.append(phi)

            if step % args.log_every == 0:
                print(f"  P1 step {step:6d} │ Φ={phi:.4f} │ cells={c.n_cells}")
            continue

        elif step <= p2_end:
            phase = "P2"
        else:
            phase = "P3"
            # P3: upgrade to Hexad if not already
            if trinity.m is None:
                trinity.m = VectorMemory()
                trinity.s = TensionSense(dim=c.state_dim)
                trinity.e = EmpathyEthics()
                print(f"  [Law 60] P3: Hexad activated (+M+S+E) at step {step}")

        # ── Get batch ──
        tokens, targets = get_batch(train_data, args.block_size, args.batch_size, device)

        # ── Train step ──
        result = trinity.train_step(tokens, targets, optimizer)
        ce = result['ce']
        phi = result['phi']
        ce_history.append(ce)
        phi_history.append(phi)

        # ── Logging ──
        if step % args.log_every == 0:
            bpc = ce / math.log(2)
            print(f"  {phase} step {step:6d} │ CE={ce:.4f} BPC={bpc:.4f} │ "
                  f"Φ={phi:.4f} │ cells={result['n_cells']} │ "
                  f"lr={result.get('lr', args.lr):.2e} │ "
                  f"pain={result.get('pain', 0):.2f} satis={result.get('satisfaction', 0):.2f}")

        # ── Validation ──
        if step % args.eval_every == 0:
            with torch.no_grad():
                vx, vy = get_batch(val_data, args.block_size, args.batch_size, device)
                logits, vphi = trinity.forward(vx, inference=True)
                val_ce = F.cross_entropy(
                    logits.view(-1, vocab_size), vy.view(-1)
                ).item()

            if val_ce < best_val_ce:
                best_val_ce = val_ce
                torch.save({
                    'step': step, 'phase': phase,
                    'decoder': trinity.decoder.state_dict(),
                    'bridge': trinity.bridge.state_dict(),
                    'optimizer': optimizer.state_dict(),
                    'ce_history': ce_history[-1000:],
                    'phi_history': phi_history[-100:],
                    'best_ce': best_val_ce,
                    'args': vars(args),
                }, os.path.join(args.checkpoint_dir, 'best.pt'))

            print(f"  [val] CE={val_ce:.4f} BPC={val_ce/math.log(2):.4f} "
                  f"Φ={vphi:.4f} (best={best_val_ce:.4f})")

        # ── Periodic checkpoint ──
        if step % args.save_every == 0:
            torch.save({
                'step': step, 'phase': phase,
                'decoder': trinity.decoder.state_dict(),
                'bridge': trinity.bridge.state_dict(),
                'optimizer': optimizer.state_dict(),
                'ce_history': ce_history[-1000:],
                'phi_history': phi_history[-100:],
                'best_ce': best_val_ce,
                'args': vars(args),
            }, os.path.join(args.checkpoint_dir, f'step_{step}.pt'))

    # ── Final ──
    elapsed = time.time() - t0
    print(f"\n{'═' * 80}")
    print(f"  Training complete: {args.steps} steps in {elapsed:.1f}s "
          f"({args.steps / max(elapsed, 1):.1f} steps/sec)")
    print(f"  Final CE={ce_history[-1]:.4f}  Φ={phi_history[-1]:.4f}  "
          f"Best val CE={best_val_ce:.4f}")
    print(f"{'═' * 80}")

    # Save final
    torch.save({
        'step': args.steps, 'phase': phase,
        'decoder': trinity.decoder.state_dict(),
        'bridge': trinity.bridge.state_dict(),
        'ce_history': ce_history,
        'phi_history': phi_history,
        'best_ce': best_val_ce,
        'args': vars(args),
    }, os.path.join(args.checkpoint_dir, 'final.pt'))

    # Law 49: Φ-optimal checkpoint report
    if HAS_TRAINING_LAWS:
        phi_best = phi_checkpoint_selector(args.checkpoint_dir, top_k=3)
        if phi_best:
            print(f"\n  [Law 49] Φ-optimal checkpoints:")
            for path, phi_val in phi_best:
                tag = " ← BEST Φ" if path == phi_best[0][0] else ""
                print(f"    Φ={phi_val:.4f}  {os.path.basename(path)}{tag}")


def main():
    parser = argparse.ArgumentParser(description="v13: ConsciousnessEngine + PostHoc + Topology")

    # Data
    parser.add_argument('--data', type=str, required=True, help='Training text file')

    # Architecture
    parser.add_argument('--cells', type=int, default=64, help='Max consciousness cells')
    parser.add_argument('--cell-dim', type=int, default=64, help='Cell input dimension')
    parser.add_argument('--hidden-dim', type=int, default=128, help='Cell hidden dimension')
    parser.add_argument('--d-model', type=int, default=384, help='Decoder dimension')
    parser.add_argument('--topology', type=str, default='hypercube',
                        choices=['ring', 'small_world', 'hypercube', 'scale_free'])
    parser.add_argument('--chaos', type=str, default=None,
                        choices=['lorenz', 'sandpile', 'chimera', 'wave', None])

    # Training
    parser.add_argument('--steps', type=int, default=50000)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--block-size', type=int, default=256)
    parser.add_argument('--curriculum', action='store_true', help='Law 45: consciousness data first')

    # Logging
    parser.add_argument('--log-every', type=int, default=100)
    parser.add_argument('--eval-every', type=int, default=1000)
    parser.add_argument('--save-every', type=int, default=5000)
    parser.add_argument('--checkpoint-dir', type=str, default='checkpoints/v13')

    # System
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu')
    parser.add_argument('--seed', type=int, default=42)

    args = parser.parse_args()
    train(args)


if __name__ == '__main__':
    main()
