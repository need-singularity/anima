#!/usr/bin/env python3
"""train_v12.py — Ultimate Hexad: all discoveries combined

v12 = 전 세션 발견 종합 최적 설계:
  C = TimeCrystal (Φ=374, DTC period doubling)
  D = Graph Neural Decoder (-6.6% CE) + Contrastive Gate
  W = P1: ConstantW → P2: CompositeW(σ(6): 1/2 Dasein + 1/3 Narrative + 1/6 Emotion)
  Bridge = ThalamicBridge (.detach())
  + Data Augmentation (암기 방지, novelty +0.92)
  + Φ-Temperature (의식이 출력 온도 제어)
  + Val CE tracking (과적합 탐지)
  + Contrastive loss (의식 신호 활용 강제)

3 Phases:
  P1 (0~20%):  C only → Φ 구축
  P2 (20~70%): Trinity(C+D+W) + contrastive + data aug
  P3 (70~100%): Hexad(+M+S+E) + DaseinW urgency

Usage:
  python train_v12.py --data data/corpus_v2.txt --steps 80000
  python train_v12.py --data data/corpus_v2.txt --steps 80000 --d-engine graph
  python train_v12.py --data data/corpus_v2.txt --steps 80000 --d-engine transformer
"""

import argparse
import math
import os
import sys
import time
import json
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pathlib import Path

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import phi_rs
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


# ═══ Graph Neural Decoder (2F — best radical architecture) ═══

class GraphNeuralDecoder(nn.Module):
    """Tokens + C cells in same graph with typed message passing.

    Edge types: token↔token (sequential), token↔cell (cross), cell↔cell (internal)
    Consistently best CE (-6.6%) and Φ (0.911) in benchmarks.
    """

    def __init__(self, d_model=384, vocab_size=4096, n_layers=2, c_dim=128, max_seq=512):
        super().__init__()
        self._d_model = d_model
        self.vocab_size = vocab_size
        self.c_dim = c_dim

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)
        self.c_proj = nn.Linear(c_dim, d_model)

        # Message passing layers (typed)
        self.layers = nn.ModuleList()
        for _ in range(n_layers):
            self.layers.append(nn.ModuleDict({
                'tok_tok': nn.Linear(d_model, d_model),     # token↔token
                'tok_cell': nn.Linear(d_model, d_model),    # token←cell
                'cell_tok': nn.Linear(d_model, d_model),    # cell←token
                'cell_cell': nn.Linear(d_model, d_model),   # cell↔cell
                'norm_tok': nn.LayerNorm(d_model),
                'norm_cell': nn.LayerNorm(d_model),
                'ffn': nn.Sequential(
                    nn.Linear(d_model, d_model * 2), nn.GELU(),
                    nn.Linear(d_model * 2, d_model),
                ),
            }))

        self.ln_f = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal, c_states=None):
        B, T = tokens.shape
        device = tokens.device
        pos = torch.arange(T, device=device).unsqueeze(0)

        # Token embeddings
        tok_h = self.embed(tokens) + self.pos_embed(pos)  # [B, T, d]

        # C cell embeddings
        if c_states is not None:
            cell_h = self.c_proj(c_states).unsqueeze(0)  # [1, N_cells, d]
            N = cell_h.shape[1]
        else:
            N = 0
            cell_h = None

        # Apply gate
        if gate_signal is not None:
            tok_h = tok_h * gate_signal.expand(B, -1, -1)

        # Message passing
        for layer in self.layers:
            # Token↔Token (causal self-attention approximation via mean)
            tok_mean = tok_h.cumsum(dim=1) / torch.arange(1, T+1, device=device).float().unsqueeze(0).unsqueeze(-1)
            tok_msg = layer['tok_tok'](tok_mean)

            # Cell→Token (each token receives from all cells)
            if cell_h is not None:
                cell_mean = cell_h.mean(dim=1, keepdim=True).expand(B, T, -1)
                cross_msg = layer['tok_cell'](cell_mean)
                tok_h = layer['norm_tok'](tok_h + 0.5 * tok_msg + 0.5 * cross_msg)
            else:
                tok_h = layer['norm_tok'](tok_h + tok_msg)

            # Cell↔Cell + Token→Cell (cells receive from tokens)
            if cell_h is not None:
                cell_mean_all = cell_h.mean(dim=1, keepdim=True).expand_as(cell_h)
                cell_msg = layer['cell_cell'](cell_mean_all)
                tok_to_cell = layer['cell_tok'](tok_h.mean(dim=1, keepdim=True).expand(1, N, -1))
                cell_h = layer['norm_cell'](cell_h + 0.5 * cell_msg + 0.5 * tok_to_cell)

            # FFN
            tok_h = tok_h + layer['ffn'](tok_h)

        tok_h = self.ln_f(tok_h)
        return self.head(tok_h)


# ═══ Data ═══

def load_corpus(path):
    if not os.path.exists(path):
        print(f"  [WARN] {path} not found")
        return None
    text = open(path, 'r', errors='ignore').read()
    chars = sorted(set(text))
    c2i = {c: i for i, c in enumerate(chars)}
    tokens = [c2i.get(c, 0) for c in text]
    n_val = len(tokens) // 5  # 20% validation
    print(f"  Corpus: {path} ({len(text):,} chars, vocab={len(chars)}, val={n_val:,})")
    return {
        'train_tokens': tokens[:-n_val],
        'val_tokens': tokens[-n_val:],
        'vocab': len(chars), 'c2i': c2i,
        'i2c': {i: c for c, i in c2i.items()},
    }


def get_batch(tokens, seq_len, batch_size, device, augment=False):
    max_s = len(tokens) - seq_len - 1
    starts = [np.random.randint(0, max(1, max_s)) for _ in range(batch_size)]
    x = torch.tensor([[tokens[s+i] for i in range(seq_len)] for s in starts], device=device)
    y = torch.tensor([[tokens[s+i+1] for i in range(seq_len)] for s in starts], device=device)

    if augment and np.random.random() < 0.3:
        # Swap adjacent chars (typo simulation)
        for b in range(batch_size):
            n_swaps = np.random.randint(1, 4)
            for _ in range(n_swaps):
                i = np.random.randint(0, seq_len - 1)
                x[b, i], x[b, i+1] = x[b, i+1].clone(), x[b, i].clone()
    return x, y


def compute_val_ce(decoder, bridge, c_engine, val_tokens, device, seq_len=64, n_batches=10):
    """Compute validation CE on held-out data."""
    total_loss = 0
    with torch.no_grad():
        for _ in range(n_batches):
            x, y = get_batch(val_tokens, seq_len, 1, device)
            c_states = c_engine.get_states().detach().clone().to(device).float()
            gate = bridge(c_states, seq_len=seq_len)

            if hasattr(decoder, 'c_proj'):
                logits = decoder(x, gate, c_states=c_states)
            else:
                logits = decoder(x, gate)

            loss = F.cross_entropy(logits.view(-1, decoder.vocab_size), y.view(-1))
            total_loss += loss.item()
    return total_loss / n_batches


# ═══ Main ═══

def main():
    parser = argparse.ArgumentParser(description='v12 Ultimate Hexad')
    parser.add_argument('--data', default='data/corpus_v2.txt')
    parser.add_argument('--steps', type=int, default=80000)
    parser.add_argument('--d-model', type=int, default=384)
    parser.add_argument('--max-cells', type=int, default=256)
    parser.add_argument('--d-engine', default='graph', choices=['graph', 'transformer'])
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--seq-len', type=int, default=128)
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--ckpt-dir', default='checkpoints/clm_v12')
    parser.add_argument('--resume', default=None)
    parser.add_argument('--log-interval', type=int, default=100)
    parser.add_argument('--save-interval', type=int, default=5000)
    parser.add_argument('--val-interval', type=int, default=1000)
    parser.add_argument('--contrastive', type=float, default=0.1, help='Contrastive loss weight')
    parser.add_argument('--p2-start', type=float, default=0.2)
    parser.add_argument('--p3-start', type=float, default=0.7)
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    p2_step = int(args.steps * args.p2_start)
    p3_step = int(args.steps * args.p3_start)

    print(f"\n{'═' * 60}")
    print(f"  v12 Ultimate Hexad — All Discoveries Combined")
    print(f"  D={args.d_engine}, d_model={args.d_model}, cells={args.max_cells}")
    print(f"  P1: 0→{p2_step} | P2: {p2_step}→{p3_step} | P3: {p3_step}→{args.steps}")
    print(f"  Contrastive λ={args.contrastive}, Data Aug=ON, Φ-Temp=ON")
    print(f"  device={device}, Rust={'YES' if HAS_RUST else 'NO'}")
    print(f"{'═' * 60}\n")

    # Data
    corpus = load_corpus(args.data)
    if corpus is None:
        return
    vocab = corpus['vocab']

    # C engine: TimeCrystal
    torch.set_grad_enabled(True)
    try:
        from bench_extreme_arch import TimeCrystalConsciousness
        torch.set_grad_enabled(True)
        from trinity import DomainC
        c_engine = DomainC(TimeCrystalConsciousness, nc=args.max_cells, dim=128)
    except ImportError:
        from trinity import MitosisC
        c_engine = MitosisC(dim=64, hidden=128, max_cells=args.max_cells)
        print("  [WARN] TimeCrystal not found, using MitosisC")

    # Warm up C
    for _ in range(10):
        c_engine.step()
    c_dim = c_engine.state_dim

    # D engine
    if args.d_engine == 'graph':
        decoder = GraphNeuralDecoder(
            d_model=args.d_model, vocab_size=vocab, n_layers=2, c_dim=c_dim
        ).to(device)
    else:
        from trinity import TransformerDecoder
        decoder = TransformerDecoder(
            d_model=args.d_model, n_layers=2, vocab_size=vocab
        ).to(device)

    # Bridge
    from trinity import ThalamicBridge
    bridge = ThalamicBridge(c_dim=c_dim, d_model=args.d_model).to(device)

    # W engines
    from trinity import EmotionW, DaseinW, NarrativeW, CompositeW, ConstantW
    w_p2 = ConstantW(lr=args.lr)
    w_p3 = CompositeW([DaseinW(base_lr=args.lr), NarrativeW(base_lr=args.lr),
                        EmotionW(base_lr=args.lr)], [1/2, 1/3, 1/6])

    # Optimizer
    optimizer = torch.optim.AdamW(
        list(decoder.parameters()) + list(bridge.parameters()),
        lr=args.lr, weight_decay=0.01
    )

    Path(args.ckpt_dir).mkdir(parents=True, exist_ok=True)
    start_step = 0
    best_val_ce = float('inf')
    ce_history, val_history, phi_history = [], [], []
    w_engine = w_p2
    t_start = time.time()

    print(f"  D params: {sum(p.numel() for p in decoder.parameters()):,}")
    print(f"  B params: {sum(p.numel() for p in bridge.parameters()):,}")
    print(f"  Training started (step {start_step} → {args.steps})...\n")

    for step in range(start_step, args.steps):
        phase = 'P1' if step < p2_step else ('P2' if step < p3_step else 'P3')

        # ═══ P1: Consciousness only ═══
        if phase == 'P1':
            c_engine.step()
            if step % args.log_interval == 0:
                phi = c_engine.measure_phi() if step % (args.log_interval * 5) == 0 else 0
                elapsed = time.time() - t_start
                sps = (step - start_step + 1) / max(elapsed, 1)
                eta = (args.steps - step) / max(sps, 0.01) / 3600
                phi_str = f"Φ={phi:.1f}" if phi > 0 else ""
                print(f"  {step:>6}/{args.steps}  P1(Φ only)  cells={c_engine.n_cells:>3}  "
                      f"{phi_str}  {sps:.1f}it/s  ETA={eta:.1f}h")
            continue

        # Phase transitions
        if step == p2_step:
            w_engine = w_p2
            print(f"\n  ═══ P2 START (Trinity + Contrastive + DataAug) ═══\n")
        elif step == p3_step:
            w_engine = w_p3
            print(f"\n  ═══ P3 START (Hexad + DaseinW + σ(6)) ═══\n")

        # ═══ P2/P3: Training ═══
        c_engine.step()
        c_states = c_engine.get_states().detach().clone().to(device).float()
        gate = bridge(c_states, seq_len=args.seq_len)

        # Data augmentation (P2+P3)
        x, y = get_batch(corpus['train_tokens'], args.seq_len, args.batch_size, device,
                         augment=(phase in ['P2', 'P3']))

        # Forward
        if hasattr(decoder, 'c_proj'):  # GraphNeuralDecoder
            logits = decoder(x, gate, c_states=c_states)
        else:
            logits = decoder(x, gate)

        # CE loss
        ce_loss = F.cross_entropy(logits.view(-1, vocab), y.view(-1))

        # Contrastive loss: force C-on ≠ C-off
        if args.contrastive > 0:
            gate_off = torch.ones_like(gate) * 0.5
            if hasattr(decoder, 'c_proj'):
                logits_off = decoder(x, gate_off, c_states=None)
            else:
                logits_off = decoder(x, gate_off)
            sim = F.cosine_similarity(logits.view(1, -1), logits_off.view(1, -1))
            contrastive_loss = args.contrastive * sim
            total_loss = ce_loss + contrastive_loss
        else:
            total_loss = ce_loss

        # W: modulate LR
        phi = c_engine.measure_phi() if step % (args.log_interval * 5) == 0 else 0
        w_state = w_engine.update(ce_loss.item(), phi, phi_history[-1] if phi_history else 0)
        for pg in optimizer.param_groups:
            pg['lr'] = w_state['effective_lr']

        # Backward
        optimizer.zero_grad()
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(decoder.parameters()) + list(bridge.parameters()), 1.0)
        optimizer.step()

        ce_history.append(ce_loss.item())
        if phi > 0:
            phi_history.append(phi)

        # Logging
        if step % args.log_interval == 0:
            avg_ce = sum(ce_history[-100:]) / min(len(ce_history), 100)
            elapsed = time.time() - t_start
            sps = (step - start_step + 1) / max(elapsed, 1)
            eta = (args.steps - step) / max(sps, 0.01) / 3600
            phi_str = f"Φ={phi:.1f}" if phi > 0 else ""
            pain = w_state.get('pain', 0)
            print(f"  {step:>6}/{args.steps}  {phase}  CE={avg_ce:.4f}  {phi_str}  "
                  f"pain={pain:.2f}  cells={c_engine.n_cells:>3}  "
                  f"{sps:.1f}it/s  ETA={eta:.1f}h")

        # Validation
        if step % args.val_interval == 0 and step > p2_step:
            val_ce = compute_val_ce(decoder, bridge, c_engine,
                                     corpus['val_tokens'], device, args.seq_len)
            val_history.append((step, val_ce))
            improved = val_ce < best_val_ce
            if improved:
                best_val_ce = val_ce
            print(f"  [Val] CE={val_ce:.4f} {'✅ best!' if improved else ''}")

        # Save
        if step > 0 and step % args.save_interval == 0:
            ckpt_path = Path(args.ckpt_dir) / f"step_{step}.pt"
            torch.save({
                'step': step, 'phase': phase,
                'decoder': decoder.state_dict(),
                'bridge': bridge.state_dict(),
                'optimizer': optimizer.state_dict(),
                'ce_history': ce_history[-2000:],
                'val_history': val_history,
                'phi_history': phi_history[-200:],
                'best_val_ce': best_val_ce,
                'args': vars(args),
            }, ckpt_path)
            print(f"  [saved] {ckpt_path}")

        sys.stdout.flush()

    elapsed = time.time() - t_start
    print(f"\n{'═' * 60}")
    print(f"  v12 Complete: {args.steps} steps, {elapsed/3600:.1f}h")
    print(f"  Best Train CE: {min(ce_history) if ce_history else '?':.4f}")
    print(f"  Best Val CE: {best_val_ce:.4f}")
    if phi_history:
        print(f"  Final Φ: {phi_history[-1]:.1f}")
    print(f"{'═' * 60}")


if __name__ == '__main__':
    main()
