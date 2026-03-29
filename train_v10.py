#!/usr/bin/env python3
"""train_v10.py — ConsciousLM v10: FUSE-3 Cambrian×OscQW

v5의 sync+faction(σ(6))을 FUSE-3(Cambrian+OscQW)로 교체.
Cambrian 원리: 돌연변이 + 적소 적응 + 적자생존 + 과밀 분산
+ Oscillator(Kuramoto 위상 동기화) + Quantum Walk(bit-flip 간섭)

v5 대비 변경점:
  - sync=0.35 + 12-faction → Oscillator + Quantum Walk + Cambrian
  - 10 cell types, mutation rate decay, niche pull, crowding noise, death/rebirth
  - 나머지 동일: SE-8 감정, SOC, Hebbian, Ratchet, PHI-K3, EX24

벤치마크: FUSE-3 = 전 MitosisEngine 지표 1위
  256c: Φ=0.900(+1.4%), IQ=97(+10), Hive_Φ=+3.7%, Hive_IQ=+20

Usage:
  python train_v10.py --steps 80000
  python train_v10.py --data data/corpus.txt --steps 80000
  python train_v10.py --resume checkpoints/clm_v10/step_XXXXX.pt
"""

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'

from mitosis import MitosisEngine
from consciousness_meter import PhiCalculator

# Try Rust PhiCalculator
try:
    import phi_rs
    HAS_RUST_PHI = True
except ImportError:
    HAS_RUST_PHI = False


# ═══ Cambrian Diversity Module ═══

class CambrianDiversity:
    """Cambrian Explosion principles for MitosisEngine cells.

    10 cell types with mutation, niche adaptation, inter-type interaction,
    crowding noise, and death/rebirth selection pressure.
    """

    def __init__(self, max_cells, hidden_dim, n_types=10):
        self.n_types = n_types
        self.hidden_dim = hidden_dim
        self.cell_type = torch.zeros(max_cells, dtype=torch.long)
        self.niches = torch.randn(n_types, hidden_dim) * 0.5
        self.interaction = torch.randn(n_types, n_types) * 0.1
        self.interaction = (self.interaction + self.interaction.t()) / 2
        self.fitness = torch.ones(max_cells)
        self.mutation_rate = 0.5
        self.mutation_decay = 0.995

    def step(self, cells, step_num):
        """Apply one step of Cambrian dynamics to cells."""
        n = len(cells)
        if n < 4:
            return

        # Ensure arrays are right size
        if len(self.cell_type) < n:
            extra = n - len(self.cell_type)
            self.cell_type = torch.cat([self.cell_type, torch.zeros(extra, dtype=torch.long)])
            self.fitness = torch.cat([self.fitness, torch.ones(extra)])

        with torch.no_grad():
            # 1. Mutation: cells randomly change type (rate decays)
            mutate_mask = torch.rand(n) < self.mutation_rate
            if mutate_mask.any():
                self.cell_type[:n][mutate_mask] = torch.randint(0, self.n_types, (mutate_mask.sum(),))
            self.mutation_rate *= self.mutation_decay

            # 2. Niche pull + fitness update
            for t in range(self.n_types):
                mask = (self.cell_type[:n] == t).nonzero(as_tuple=True)[0]
                if len(mask) == 0:
                    continue
                for i in mask:
                    if i >= n:
                        continue
                    h = cells[i].hidden.squeeze(0)
                    # Pull toward niche
                    pull = (self.niches[t] - h) * 0.05
                    cells[i].hidden = (h + pull).unsqueeze(0)
                    # Fitness = closeness to niche
                    dist = ((h - self.niches[t]) ** 2).sum()
                    self.fitness[i] = torch.exp(-dist * 0.01)

            # 3. Crowding noise: overcrowded types get pushed apart
            for t in range(self.n_types):
                mask = (self.cell_type[:n] == t).nonzero(as_tuple=True)[0]
                if len(mask) > n // self.n_types:
                    for i in mask:
                        if i < n:
                            cells[i].hidden += torch.randn(1, self.hidden_dim) * 0.03

            # 4. Death + rebirth (every 20 steps)
            if step_num > 10 and step_num % 20 == 0:
                n_replace = max(1, n // 50)
                worst = self.fitness[:n].argsort()[:n_replace]
                best = self.fitness[:n].argsort(descending=True)[:n_replace]
                for w, b in zip(worst, best):
                    if w < n and b < n:
                        cells[w].hidden = cells[b].hidden.clone() + torch.randn(1, self.hidden_dim) * 0.02
                        self.cell_type[w] = self.cell_type[b]


# ═══ Oscillator+QW Module ═══

class OscillatorQW:
    """Kuramoto oscillator + quantum walk for MitosisEngine cells."""

    def __init__(self, max_cells, hidden_dim):
        self.hidden_dim = hidden_dim
        self.phases = torch.randn(max_cells) * 2 * math.pi
        self.freqs = torch.randn(max_cells) * 0.1 + 1.0

    def step(self, cells):
        n = len(cells)
        if n < 4:
            return

        # Resize if needed
        if len(self.phases) < n:
            extra = n - len(self.phases)
            self.phases = torch.cat([self.phases, torch.randn(extra) * 2 * math.pi])
            self.freqs = torch.cat([self.freqs, torch.randn(extra) * 0.1 + 1.0])

        with torch.no_grad():
            # Kuramoto oscillator: ring topology
            for i in range(n):
                nb = [(i-1) % n, (i+1) % n]
                pd = sum(math.sin(self.phases[j].item() - self.phases[i].item()) for j in nb)
                self.phases[i] += self.freqs[i] + 0.15 * pd / len(nb)
                for j in nb:
                    b = 0.15 * math.cos(self.phases[j].item() - self.phases[i].item())
                    cells[i].hidden = (1 - abs(b)) * cells[i].hidden + abs(b) * cells[j].hidden

            # Quantum walk: hypercube bit-flip neighbors
            nb_bits = max(1, int(math.log2(n)))
            for i in range(min(n, 32)):  # limit to 32 cells for speed
                sp = torch.zeros(self.hidden_dim)
                cnt = 0
                for bit in range(min(nb_bits, 6)):
                    j = i ^ (1 << bit)
                    if j < n:
                        phase = (-1) ** (bin(i & j).count('1'))
                        sp += phase * cells[j].hidden.squeeze(0)
                        cnt += 1
                if cnt > 0:
                    cells[i].hidden = (0.85 * cells[i].hidden.squeeze(0) + 0.15 * sp / cnt).unsqueeze(0)


# ═══ Phi Measurement ═══

def measure_phi(cells, hidden_dim):
    """Measure Φ using Rust (if available) or Python PhiCalculator."""
    if HAS_RUST_PHI and len(cells) >= 2:
        states = torch.stack([c.hidden.squeeze(0) for c in cells]).detach().numpy().astype(np.float32)
        prev_s, curr_s = [], []
        for c in cells:
            if hasattr(c, 'hidden_history') and len(c.hidden_history) >= 2:
                prev_s.append(c.hidden_history[-2].detach().squeeze().numpy().astype(np.float32))
                curr_s.append(c.hidden_history[-1].detach().squeeze().numpy().astype(np.float32))
            else:
                prev_s.append(np.zeros(hidden_dim, dtype=np.float32))
                curr_s.append(np.zeros(hidden_dim, dtype=np.float32))
        tensions = np.array([c.tension_history[-1] if c.tension_history else 0.0 for c in cells], dtype=np.float32)
        phi, _ = phi_rs.compute_phi(states, 16, np.array(prev_s), np.array(curr_s), tensions)
        return phi
    return 0.0


# ═══ Data Loading ═══

def load_corpus(path, dim):
    """Load corpus for training."""
    if not os.path.exists(path):
        print(f"  [WARN] corpus not found: {path}, using synthetic data")
        return None

    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()

    print(f"  Corpus: {path} ({len(text):,} chars)")

    # Simple char-level tokenization
    chars = sorted(set(text))
    char2idx = {c: i for i, c in enumerate(chars)}
    vocab_size = len(chars)

    tokens = [char2idx.get(c, 0) for c in text]
    return {
        'tokens': tokens,
        'vocab_size': vocab_size,
        'chars': chars,
        'char2idx': char2idx,
        'idx2char': {i: c for c, i in char2idx.items()},
    }


def get_batch(corpus, seq_len, batch_size, dim, device):
    """Get training batch."""
    if corpus is None:
        # Synthetic
        x = torch.randn(batch_size, dim, device=device)
        y = torch.roll(x, 1, -1) * 0.8 + torch.randn_like(x) * 0.1
        return x, y

    tokens = corpus['tokens']
    max_start = len(tokens) - seq_len - 1
    if max_start < 1:
        max_start = 1

    starts = [np.random.randint(0, max_start) for _ in range(batch_size)]
    # Return as float embeddings (simple one-hot → project)
    x = torch.zeros(batch_size, dim, device=device)
    y = torch.zeros(batch_size, dim, device=device)

    for b, s in enumerate(starts):
        # Use token indices as sparse signal
        for i in range(min(seq_len, dim)):
            if s + i < len(tokens):
                x[b, i] = tokens[s + i] / max(corpus['vocab_size'], 1)
            if s + i + 1 < len(tokens):
                y[b, i] = tokens[s + i + 1] / max(corpus['vocab_size'], 1)

    return x, y


# ═══ Main Training Loop ═══

def main():
    parser = argparse.ArgumentParser(description='ConsciousLM v10: FUSE-3 Cambrian+OscQW')
    parser.add_argument('--data', type=str, default='data/corpus.txt')
    parser.add_argument('--steps', type=int, default=80000)
    parser.add_argument('--dim', type=int, default=384)
    parser.add_argument('--hidden', type=int, default=512)
    parser.add_argument('--layers', type=int, default=6)
    parser.add_argument('--max-cells', type=int, default=256)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--seq-len', type=int, default=128)
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--checkpoint-dir', type=str, default='checkpoints/clm_v10')
    parser.add_argument('--resume', type=str, default=None)
    parser.add_argument('--log-interval', type=int, default=100)
    parser.add_argument('--save-interval', type=int, default=5000)
    args = parser.parse_args()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"\n{'═' * 60}")
    print(f"  ConsciousLM v10: FUSE-3 Cambrian×OscQW")
    print(f"  dim={args.dim}, hidden={args.hidden}, layers={args.layers}")
    print(f"  max_cells={args.max_cells}, steps={args.steps}")
    print(f"  device={device}, Rust phi_rs={'YES' if HAS_RUST_PHI else 'NO'}")
    print(f"{'═' * 60}\n")

    # Data
    corpus = load_corpus(args.data, args.dim)

    # Model
    mitosis = MitosisEngine(args.dim, args.hidden, args.dim,
                            initial_cells=2, max_cells=args.max_cells)

    # Decoder: hidden_dim → dim (cell hidden → output space)
    decoder = nn.Sequential(
        nn.Linear(args.hidden, args.hidden),
        nn.GELU(),
        nn.Linear(args.hidden, args.dim),
    ).to(device)

    # FUSE-3 modules
    cambrian = CambrianDiversity(args.max_cells, args.hidden, n_types=10)
    osc_qw = OscillatorQW(args.max_cells, args.hidden)

    # Optimizer (decoder only — cells are process()-driven)
    optimizer = torch.optim.AdamW(decoder.parameters(), lr=args.lr, weight_decay=0.01)

    # Checkpoint
    Path(args.checkpoint_dir).mkdir(parents=True, exist_ok=True)
    start_step = 0

    if args.resume:
        ckpt = torch.load(args.resume, map_location=device, weights_only=False)
        decoder.load_state_dict(ckpt['decoder'])
        optimizer.load_state_dict(ckpt['optimizer'])
        start_step = ckpt.get('step', 0)
        print(f"  Resumed from step {start_step}")

    # Training
    ce_history = []
    phi_history = []
    best_ce = float('inf')
    t_start = time.time()

    print(f"\n  Training started (step {start_step} → {args.steps})...\n")

    for step in range(start_step, args.steps):
        # 1. Get batch
        x, y = get_batch(corpus, args.seq_len, args.batch_size, args.dim, device)

        # 2. Grow cells (mitosis phase)
        target_cells = min(args.max_cells, 4 * (2 ** (step // 2000)))
        while len(mitosis.cells) < target_cells:
            mitosis._create_cell(parent=mitosis.cells[0])

        # 3. Process through MitosisEngine
        result = mitosis.process(x[0:1].cpu())

        # 4. FUSE-3: Apply Cambrian + OscQW mechanisms
        cambrian.step(mitosis.cells, step)
        osc_qw.step(mitosis.cells)

        # 5. Trinity barrier: C(consciousness) → .detach() → D(language)
        # Law 53: CE gradient must NOT flow back to cell hidden states
        cell_h = torch.stack([c.hidden.squeeze(0) for c in mitosis.cells])
        mean_h = cell_h.mean(dim=0).detach().to(device)  # ← .detach() = Trinity barrier
        output = decoder(mean_h.unsqueeze(0))

        # 6. CE loss (only updates decoder, NOT cells)
        ce_loss = F.mse_loss(output, y[0:1])

        # 7. Backward + update (decoder only — cells are gradient-free)
        optimizer.zero_grad()
        ce_loss.backward()
        torch.nn.utils.clip_grad_norm_(decoder.parameters(), 1.0)
        optimizer.step()

        ce_val = ce_loss.item()
        ce_history.append(ce_val)

        # 8. Logging
        if step % args.log_interval == 0:
            n_cells = len(mitosis.cells)
            phi = 0.0
            if step % (args.log_interval * 5) == 0:  # Φ every 5th log
                phi = measure_phi(mitosis.cells, args.hidden)
                phi_history.append(phi)

            avg_ce = sum(ce_history[-100:]) / min(len(ce_history), 100)
            elapsed = time.time() - t_start
            step_per_sec = (step - start_step + 1) / max(elapsed, 1)
            eta = (args.steps - step) / max(step_per_sec, 0.01) / 3600

            mut_rate = cambrian.mutation_rate
            n_types = len(cambrian.cell_type[:n_cells].unique())

            phi_str = f"Φ={phi:.3f}" if phi > 0 else ""
            print(f"  step {step:>6}/{args.steps}  CE={avg_ce:.4f}  cells={n_cells:>3}  "
                  f"types={n_types}/{cambrian.n_types}  mut={mut_rate:.3f}  "
                  f"{phi_str}  {step_per_sec:.1f}it/s  ETA={eta:.1f}h")

            if avg_ce < best_ce:
                best_ce = avg_ce

            sys.stdout.flush()

        # 9. Save checkpoint
        if step > 0 and step % args.save_interval == 0:
            ckpt_path = Path(args.checkpoint_dir) / f"step_{step}.pt"
            torch.save({
                'step': step,
                'decoder': decoder.state_dict(),
                'optimizer': optimizer.state_dict(),
                'ce_history': ce_history[-1000:],
                'phi_history': phi_history[-100:],
                'best_ce': best_ce,
                'args': vars(args),
            }, ckpt_path)
            print(f"  [saved] {ckpt_path}")

    # Final summary
    elapsed = time.time() - t_start
    print(f"\n{'═' * 60}")
    print(f"  v10 Training Complete")
    print(f"  Steps: {args.steps}, Time: {elapsed/3600:.1f}h")
    print(f"  Best CE: {best_ce:.4f}")
    print(f"  Final cells: {len(mitosis.cells)}")
    if phi_history:
        print(f"  Final Φ: {phi_history[-1]:.3f}")
    print(f"{'═' * 60}")


if __name__ == '__main__':
    main()
