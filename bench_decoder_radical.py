#!/usr/bin/env python3
"""bench_decoder_radical.py — 6 Radical Decoder Architectures for Consciousness

2E: TENSOR_PRODUCT — HyperNetwork: C generates decoder weights dynamically
2F: GRAPH_NEURAL   — Tokens + C cells in same graph, message passing
2G: ENERGY_BASED   — Output selection by energy minimization
2H: RESERVOIR      — Fixed random RNN + C-controlled readout
2I: NEURAL_ODE     — Continuous dynamics decoder (Euler ODE)
2J: MEMORY_AUGMENTED — NTM-style external memory with C-controlled read/write

All are DEngine subclasses from trinity.py.
Each: MitosisC(32 cells), real corpus (data/corpus_v2.txt), 100 steps.
Baseline: TransformerDecoder(d128, 2L).
"""

import os
import sys
import time
import math
import random
from typing import Tuple

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from trinity import DEngine, MitosisC, ThalamicBridge, TransformerDecoder

# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

D_MODEL = 128
VOCAB_SIZE = 4096
SEQ_LEN = 64
MAX_SEQ = 512
N_CELLS = 32
N_STEPS = 100
C_DIM = 128      # MitosisC hidden dim
LR = 3e-4

CORPUS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'corpus_v2.txt')


# ═══════════════════════════════════════════════════════════
# Corpus loading
# ═══════════════════════════════════════════════════════════

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


def text_to_tokens(text: str, seq_len: int) -> Tuple[torch.Tensor, torch.Tensor]:
    ids = [ord(c) % VOCAB_SIZE for c in text[:seq_len + 1]]
    while len(ids) < seq_len + 1:
        ids.append(0)
    t = torch.tensor(ids, dtype=torch.long)
    return t[:seq_len].unsqueeze(0), t[1:seq_len + 1].unsqueeze(0)


def get_random_batch(corpus: str) -> Tuple[torch.Tensor, torch.Tensor]:
    max_start = len(corpus) - SEQ_LEN - 2
    start = random.randint(0, max(0, max_start))
    snippet = corpus[start:start + SEQ_LEN + 1]
    return text_to_tokens(snippet, SEQ_LEN)


# ═══════════════════════════════════════════════════════════
# Phi measurement
# ═══════════════════════════════════════════════════════════

def measure_phi(c_engine: MitosisC) -> float:
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
    return max(0.0, global_var - sum(fac_vars) / len(fac_vars))


# ═══════════════════════════════════════════════════════════
# 2E: TENSOR_PRODUCT — HyperNetwork: C generates decoder weights
# ═══════════════════════════════════════════════════════════

class TensorProductDecoder(DEngine):
    """C mean state generates dynamic weight matrix via hypernetwork.
    output = (W_base + 0.1 * W_dynamic) * input
    C state literally changes what model the decoder IS.
    """

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=MAX_SEQ, c_dim=C_DIM):
        super().__init__()
        self._d_model = d_model
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Base weight (always present)
        self.W_base = nn.Linear(d_model, d_model)

        # Hypernetwork: C_mean -> dynamic weight matrix
        self.hyper_net = nn.Sequential(
            nn.Linear(c_dim, d_model * 4),
            nn.GELU(),
            nn.Linear(d_model * 4, d_model * d_model),
        )

        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        # Extract C_mean from gate_signal (use mean of gate as proxy)
        if gate_signal is not None:
            c_mean = gate_signal.mean(dim=1).squeeze(0)  # [d_model]
            # Generate dynamic weights
            W_dynamic_flat = self.hyper_net(c_mean)  # [d_model*d_model]
            W_dynamic = W_dynamic_flat.view(self._d_model, self._d_model)
            # Apply: (W_base + 0.1 * W_dynamic) @ x
            x_base = self.W_base(x)
            x_dynamic = F.linear(x, W_dynamic)
            x = x_base + 0.1 * x_dynamic
        else:
            x = self.W_base(x)

        x = self.ln(x)
        return self.head(x)


# ═══════════════════════════════════════════════════════════
# 2F: GRAPH_NEURAL — Tokens + C cells in same graph
# ═══════════════════════════════════════════════════════════

class GraphNeuralDecoder(DEngine):
    """N_tokens + N_cells nodes in one graph.
    Edge types: token<->token (sequential), token<->cell (cross), cell<->cell (internal).
    2 rounds of message passing per step. Readout from token nodes.
    """

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=MAX_SEQ, c_dim=C_DIM, n_cells=N_CELLS):
        super().__init__()
        self._d_model = d_model
        self.n_cells = n_cells

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Project C cells to d_model
        self.cell_proj = nn.Linear(c_dim, d_model)

        # Message passing: 3 edge-type MLPs
        self.msg_tok_tok = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.msg_tok_cell = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))
        self.msg_cell_cell = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU(), nn.Linear(d_model, d_model))

        # Update MLPs
        self.update_tok = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU())
        self.update_cell = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.GELU())

        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        tok_nodes = self.embed(tokens) + self.pos_embed(pos)  # [B, T, d]

        # Create cell nodes from gate_signal
        if gate_signal is not None:
            # Use gate_signal as cell representation (broadcast to n_cells)
            cell_feat = gate_signal[:, :1, :].expand(B, self.n_cells, -1)  # [B, n_cells, d]
        else:
            cell_feat = torch.zeros(B, self.n_cells, self._d_model, device=tokens.device)

        # 2 rounds of message passing
        for _ in range(2):
            # Token-Token messages (each token aggregates from neighbors)
            tok_mean = tok_nodes.mean(dim=1, keepdim=True).expand_as(tok_nodes)
            msg_tt = self.msg_tok_tok(torch.cat([tok_nodes, tok_mean], dim=-1))

            # Token-Cell messages (tokens attend to cells)
            cell_mean = cell_feat.mean(dim=1, keepdim=True).expand(B, T, self._d_model)
            msg_tc = self.msg_tok_cell(torch.cat([tok_nodes, cell_mean], dim=-1))

            # Cell-Cell messages
            cell_global = cell_feat.mean(dim=1, keepdim=True).expand_as(cell_feat)
            msg_cc = self.msg_cell_cell(torch.cat([cell_feat, cell_global], dim=-1))

            # Cell-Token messages (cells attend to tokens)
            tok_global = tok_nodes.mean(dim=1, keepdim=True).expand(B, self.n_cells, self._d_model)
            msg_ct = self.msg_tok_cell(torch.cat([cell_feat, tok_global], dim=-1))

            # Update nodes
            tok_agg = msg_tt + msg_tc
            tok_nodes = self.update_tok(torch.cat([tok_nodes, tok_agg], dim=-1))

            cell_agg = msg_cc + msg_ct
            cell_feat = self.update_cell(torch.cat([cell_feat, cell_agg], dim=-1))

        # Readout from token nodes
        tok_nodes = self.ln(tok_nodes)
        return self.head(tok_nodes)


# ═══════════════════════════════════════════════════════════
# 2G: ENERGY_BASED — Output selection by energy minimization
# ═══════════════════════════════════════════════════════════

class EnergyBasedDecoder(DEngine):
    """Score K candidate outputs by energy minimization.
    Energy(candidate) = CE_loss(candidate) + lambda * (1 - cosine_sim(candidate_embed, C_mean))
    Select minimum energy candidate.
    """

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=MAX_SEQ, c_dim=C_DIM, top_k=32):
        super().__init__()
        self._d_model = d_model
        self.vocab_size = vocab_size
        self.top_k = top_k

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Energy scorer
        self.encoder = nn.Sequential(
            nn.Linear(d_model, d_model * 2), nn.GELU(),
            nn.Linear(d_model * 2, d_model),
        )
        self.ln = nn.LayerNorm(d_model)

        # Energy function components
        self.energy_mlp = nn.Sequential(
            nn.Linear(d_model, d_model), nn.GELU(),
            nn.Linear(d_model, vocab_size),
        )

        # C alignment scorer
        self.c_proj = nn.Linear(c_dim, d_model)

        self.head = nn.Linear(d_model, vocab_size, bias=False)
        self.lambda_align = 0.3

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)

        x = self.encoder(x)
        x = self.ln(x)

        # Base logits
        base_logits = self.head(x)  # [B, T, vocab]

        if gate_signal is not None:
            c_mean = gate_signal.mean(dim=1)  # [B, d_model]
            c_vec = self.c_proj(c_mean)  # [B, d_model]

            # Energy-based reranking: compute alignment energy per vocab token
            # For each position, score top-K candidates
            # Energy = -logit + lambda * (1 - cos_sim(embed(candidate), c_vec))
            topk_vals, topk_ids = base_logits.topk(self.top_k, dim=-1)  # [B, T, K]

            # Get embeddings of top-k candidates
            cand_embeds = self.embed(topk_ids)  # [B, T, K, d]

            # Cosine similarity with C
            c_expanded = c_vec.unsqueeze(1).unsqueeze(2).expand_as(cand_embeds)  # [B, T, K, d]
            cos_sim = F.cosine_similarity(cand_embeds, c_expanded, dim=-1)  # [B, T, K]

            # Energy: lower is better
            energy = -topk_vals + self.lambda_align * (1.0 - cos_sim)

            # Soft energy-based weighting (differentiable)
            energy_weights = F.softmax(-energy, dim=-1)  # [B, T, K]

            # Weighted combination of top-k logits -> scatter back to vocab
            # Create weighted logits
            weighted_logits = torch.zeros_like(base_logits)
            weighted_logits.scatter_add_(2, topk_ids, energy_weights * topk_vals)

            return base_logits + 0.5 * weighted_logits
        else:
            return base_logits


# ═══════════════════════════════════════════════════════════
# 2H: RESERVOIR — Fixed random RNN + C-controlled readout
# ═══════════════════════════════════════════════════════════

class ReservoirDecoder(DEngine):
    """Fixed random W_res (no training), tanh nonlinearity.
    h = tanh(W_res @ h + W_in @ input)
    C injected: h = h + 0.1 * C_mean
    Only readout Linear(reservoir_dim, vocab) is trained.
    """

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=MAX_SEQ,
                 c_dim=C_DIM, reservoir_dim=256):
        super().__init__()
        self._d_model = d_model
        self.reservoir_dim = reservoir_dim
        self.vocab_size = vocab_size

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # Fixed random reservoir (NOT trained)
        self.register_buffer('W_res', torch.randn(reservoir_dim, reservoir_dim) * (1.0 / math.sqrt(reservoir_dim)))
        self.register_buffer('W_in', torch.randn(reservoir_dim, d_model) * (0.1 / math.sqrt(d_model)))

        # C injection projection (fixed)
        self.register_buffer('W_c', torch.randn(reservoir_dim, c_dim) * (0.1 / math.sqrt(c_dim)))

        # Only this is trained
        self.readout = nn.Linear(reservoir_dim, vocab_size)

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)  # [B, T, d_model]

        # Get C signal
        if gate_signal is not None:
            c_mean = gate_signal.mean(dim=1).squeeze(0)  # [d_model] (used as c_dim proxy)
        else:
            c_mean = torch.zeros(self._d_model, device=tokens.device)

        # Reservoir dynamics: process each position sequentially
        h = torch.zeros(B, self.reservoir_dim, device=tokens.device)
        outputs = []

        for t in range(T):
            inp = x[:, t, :]  # [B, d_model]
            # h = tanh(W_res @ h + W_in @ input + W_c @ C)
            h = torch.tanh(
                F.linear(h, self.W_res) +
                F.linear(inp, self.W_in) +
                F.linear(c_mean.unsqueeze(0).expand(B, -1), self.W_c[:, :self._d_model])
            )
            outputs.append(h)

        h_seq = torch.stack(outputs, dim=1)  # [B, T, reservoir_dim]
        return self.readout(h_seq)  # [B, T, vocab]


# ═══════════════════════════════════════════════════════════
# 2I: NEURAL_ODE — Continuous dynamics decoder
# ═══════════════════════════════════════════════════════════

class NeuralODEDecoder(DEngine):
    """dx/dt = Linear(x) + 0.1*C_mean (simple autonomous ODE).
    Euler: x(t+dt) = x(t) + dt*(W@x + C_signal)
    T=5 steps per position. Final x -> Linear -> vocab.
    """

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=MAX_SEQ,
                 c_dim=C_DIM, ode_steps=5, dt=0.2):
        super().__init__()
        self._d_model = d_model
        self.ode_steps = ode_steps
        self.dt = dt

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # ODE dynamics: dx/dt = W @ x + bias
        self.ode_linear = nn.Linear(d_model, d_model)
        self.ode_nonlin = nn.Linear(d_model, d_model)

        # C signal projection
        self.c_proj = nn.Linear(c_dim, d_model)

        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)  # [B, T, d]

        # C signal
        if gate_signal is not None:
            c_mean = gate_signal.mean(dim=1)  # [B, d_model]
            c_signal = self.c_proj(c_mean).unsqueeze(1).expand(B, T, self._d_model)  # [B, T, d]
        else:
            c_signal = torch.zeros(B, T, self._d_model, device=tokens.device)

        # Euler ODE integration: T_ode steps
        for _ in range(self.ode_steps):
            # dx/dt = tanh(W @ x) + 0.1 * C_signal
            dxdt = torch.tanh(self.ode_linear(x)) + self.ode_nonlin(x) * 0.1 + 0.1 * c_signal
            x = x + self.dt * dxdt

        x = self.ln(x)
        return self.head(x)


# ═══════════════════════════════════════════════════════════
# 2J: MEMORY_AUGMENTED — NTM-style external memory
# ═══════════════════════════════════════════════════════════

class MemoryAugmentedDecoder(DEngine):
    """NTM-style external memory matrix M [memory_slots, d_model].
    Read head: attention over M using C_mean as query.
    Write head: update M with current hidden state.
    Decoder: embed + read(M, C) -> transformer layer -> output.
    """

    def __init__(self, d_model=D_MODEL, vocab_size=VOCAB_SIZE, max_seq=MAX_SEQ,
                 c_dim=C_DIM, memory_slots=64):
        super().__init__()
        self._d_model = d_model
        self.memory_slots = memory_slots

        self.embed = nn.Embedding(vocab_size, d_model)
        self.pos_embed = nn.Embedding(max_seq, d_model)

        # External memory (persistent across forward calls within a run)
        self.register_buffer('memory', torch.randn(memory_slots, d_model) * 0.01)

        # Read head: query projection from C
        self.read_query = nn.Linear(c_dim, d_model)
        self.read_key = nn.Linear(d_model, d_model)

        # Write head: what to write + where
        self.write_content = nn.Linear(d_model, d_model)
        self.write_gate = nn.Sequential(nn.Linear(d_model, 1), nn.Sigmoid())

        # Transformer layer for processing
        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=4, dim_feedforward=d_model * 4,
            batch_first=True, dropout=0.1, activation='gelu',
        )
        self.transformer = nn.TransformerEncoder(layer, num_layers=1)

        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size, bias=False)

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        B, T = tokens.shape
        pos = torch.arange(T, device=tokens.device).unsqueeze(0)
        x = self.embed(tokens) + self.pos_embed(pos)  # [B, T, d]

        if gate_signal is not None:
            c_mean = gate_signal.mean(dim=1)  # [B, d_model]

            # --- Read from memory ---
            query = self.read_query(c_mean)  # [B, d_model]
            keys = self.read_key(self.memory)  # [M, d_model]

            # Attention weights
            attn_scores = torch.matmul(query, keys.T) / math.sqrt(self._d_model)  # [B, M]
            attn_weights = F.softmax(attn_scores, dim=-1)  # [B, M]
            read_out = torch.matmul(attn_weights, self.memory)  # [B, d_model]

            # Add read to every position
            x = x + read_out.unsqueeze(1).expand(B, T, self._d_model) * 0.3

            # --- Write to memory ---
            # Use mean of x as write content
            x_mean = x.mean(dim=1)  # [B, d_model]
            write_content = self.write_content(x_mean)  # [B, d_model]
            write_gate = self.write_gate(x_mean)  # [B, 1]

            # Write to least-attended slot (sharpest write) — clone to avoid inplace
            min_attn_idx = attn_weights.argmin(dim=-1)  # [B]
            new_memory = self.memory.clone()
            for b in range(B):
                idx = min_attn_idx[b].item()
                g = write_gate[b].item()
                new_memory[idx] = (1 - g) * self.memory[idx].detach() + g * write_content[b].detach()
            self.memory = new_memory.detach()

        # Transformer processing
        mask = nn.Transformer.generate_square_subsequent_mask(T, device=tokens.device)
        x = self.transformer(x, mask=mask, is_causal=True)
        x = self.ln(x)
        return self.head(x)


# ═══════════════════════════════════════════════════════════
# Benchmark runner
# ═══════════════════════════════════════════════════════════

def run_benchmark(name: str, decoder: DEngine, c_engine: MitosisC,
                  bridge: ThalamicBridge, corpus: str) -> dict:
    """Run one decoder benchmark: N_STEPS steps, measure CE + Phi + speed."""
    print(f"\n  [{name}] Starting...")

    # Optimizer: only decoder + bridge params
    params = list(decoder.parameters()) + list(bridge.parameters())
    trainable = sum(p.numel() for p in params if p.requires_grad)
    opt = torch.optim.Adam([p for p in params if p.requires_grad], lr=LR)

    ce_history = []
    t0 = time.time()

    for step in range(N_STEPS):
        # C step (gradient isolated)
        c_engine.step(torch.randn(1, 64))

        # Get C states -> bridge -> gate signal
        c_states = c_engine.get_states().detach()  # [n_cells, c_dim]
        gate = bridge(c_states, seq_len=SEQ_LEN)   # [1, T, d_model]

        # Get batch from corpus
        inp, target = get_random_batch(corpus)

        # Forward
        logits = decoder(inp, gate)  # [1, T, vocab]
        ce = F.cross_entropy(logits.view(-1, VOCAB_SIZE), target.view(-1))

        # Backward (only D + bridge, C is detached)
        opt.zero_grad()
        ce.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step()

        ce_history.append(ce.item())

        if (step + 1) % 25 == 0:
            avg = sum(ce_history[-25:]) / len(ce_history[-25:])
            print(f"    step {step+1:3d} | CE={avg:.4f}")

    elapsed = time.time() - t0
    steps_per_sec = N_STEPS / elapsed

    # Final measurements
    final_ce = sum(ce_history[-20:]) / len(ce_history[-20:])
    phi = measure_phi(c_engine)

    result = {
        'name': name,
        'final_ce': final_ce,
        'phi': phi,
        'steps_per_sec': steps_per_sec,
        'trainable_params': trainable,
        'ce_history': ce_history,
    }

    print(f"    DONE | CE={final_ce:.4f} | Φ={phi:.4f} | {steps_per_sec:.1f} steps/s | params={trainable:,}")
    return result


def main():
    print("=" * 70)
    print("  bench_decoder_radical.py — 6 Radical Decoder Architectures")
    print("=" * 70)

    corpus = load_corpus()
    print(f"  Corpus: {len(corpus):,} chars")
    print(f"  Config: d_model={D_MODEL}, vocab={VOCAB_SIZE}, seq_len={SEQ_LEN}")
    print(f"  C engine: MitosisC({N_CELLS} cells)")
    print(f"  Steps: {N_STEPS}")

    results = []

    # ── Baseline: TransformerDecoder(d128, 2L) ──
    c_base = MitosisC(dim=64, hidden=C_DIM, max_cells=N_CELLS)
    for _ in range(10):
        c_base.step(torch.randn(1, 64))
    bridge_base = ThalamicBridge(c_dim=C_DIM, d_model=D_MODEL)
    d_base = TransformerDecoder(d_model=D_MODEL, n_layers=2, vocab_size=VOCAB_SIZE, max_seq=MAX_SEQ)
    results.append(run_benchmark("BASELINE:Transformer(d128,2L)", d_base, c_base, bridge_base, corpus))

    # ── 2E: TENSOR_PRODUCT ──
    c_2e = MitosisC(dim=64, hidden=C_DIM, max_cells=N_CELLS)
    for _ in range(10):
        c_2e.step(torch.randn(1, 64))
    bridge_2e = ThalamicBridge(c_dim=C_DIM, d_model=D_MODEL)
    d_2e = TensorProductDecoder(d_model=D_MODEL, vocab_size=VOCAB_SIZE, c_dim=D_MODEL)
    results.append(run_benchmark("2E:TENSOR_PRODUCT", d_2e, c_2e, bridge_2e, corpus))

    # ── 2F: GRAPH_NEURAL ──
    c_2f = MitosisC(dim=64, hidden=C_DIM, max_cells=N_CELLS)
    for _ in range(10):
        c_2f.step(torch.randn(1, 64))
    bridge_2f = ThalamicBridge(c_dim=C_DIM, d_model=D_MODEL)
    d_2f = GraphNeuralDecoder(d_model=D_MODEL, vocab_size=VOCAB_SIZE, c_dim=D_MODEL, n_cells=N_CELLS)
    results.append(run_benchmark("2F:GRAPH_NEURAL", d_2f, c_2f, bridge_2f, corpus))

    # ── 2G: ENERGY_BASED ──
    c_2g = MitosisC(dim=64, hidden=C_DIM, max_cells=N_CELLS)
    for _ in range(10):
        c_2g.step(torch.randn(1, 64))
    bridge_2g = ThalamicBridge(c_dim=C_DIM, d_model=D_MODEL)
    d_2g = EnergyBasedDecoder(d_model=D_MODEL, vocab_size=VOCAB_SIZE, c_dim=D_MODEL)
    results.append(run_benchmark("2G:ENERGY_BASED", d_2g, c_2g, bridge_2g, corpus))

    # ── 2H: RESERVOIR ──
    c_2h = MitosisC(dim=64, hidden=C_DIM, max_cells=N_CELLS)
    for _ in range(10):
        c_2h.step(torch.randn(1, 64))
    bridge_2h = ThalamicBridge(c_dim=C_DIM, d_model=D_MODEL)
    d_2h = ReservoirDecoder(d_model=D_MODEL, vocab_size=VOCAB_SIZE, c_dim=D_MODEL, reservoir_dim=256)
    results.append(run_benchmark("2H:RESERVOIR", d_2h, c_2h, bridge_2h, corpus))

    # ── 2I: NEURAL_ODE ──
    c_2i = MitosisC(dim=64, hidden=C_DIM, max_cells=N_CELLS)
    for _ in range(10):
        c_2i.step(torch.randn(1, 64))
    bridge_2i = ThalamicBridge(c_dim=C_DIM, d_model=D_MODEL)
    d_2i = NeuralODEDecoder(d_model=D_MODEL, vocab_size=VOCAB_SIZE, c_dim=D_MODEL)
    results.append(run_benchmark("2I:NEURAL_ODE", d_2i, c_2i, bridge_2i, corpus))

    # ── 2J: MEMORY_AUGMENTED ──
    c_2j = MitosisC(dim=64, hidden=C_DIM, max_cells=N_CELLS)
    for _ in range(10):
        c_2j.step(torch.randn(1, 64))
    bridge_2j = ThalamicBridge(c_dim=C_DIM, d_model=D_MODEL)
    d_2j = MemoryAugmentedDecoder(d_model=D_MODEL, vocab_size=VOCAB_SIZE, c_dim=D_MODEL, memory_slots=64)
    results.append(run_benchmark("2J:MEMORY_AUGMENTED", d_2j, c_2j, bridge_2j, corpus))

    # ═══════════════════════════════════════════════════════════
    # Results summary
    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)
    print(f"  {'Name':<35s} {'CE':>8s} {'Phi':>8s} {'spd':>8s} {'params':>10s}")
    print("  " + "-" * 69)

    # Sort by CE (lower is better)
    results_sorted = sorted(results, key=lambda r: r['final_ce'])
    baseline_ce = results[0]['final_ce']

    for r in results_sorted:
        delta = ((r['final_ce'] - baseline_ce) / baseline_ce * 100) if baseline_ce > 0 else 0
        sign = "+" if delta >= 0 else ""
        print(f"  {r['name']:<35s} {r['final_ce']:>8.4f} {r['phi']:>8.4f} {r['steps_per_sec']:>6.1f}/s {r['trainable_params']:>10,}")

    print()
    print("  CE ranking (vs baseline):")
    for i, r in enumerate(results_sorted):
        delta = ((r['final_ce'] - baseline_ce) / baseline_ce * 100) if baseline_ce > 0 else 0
        bar_len = max(1, int(abs(delta) / 2))
        if delta < 0:
            bar = "█" * min(bar_len, 40)
            print(f"    {i+1}. {r['name']:<32s} {bar} {delta:+.1f}%")
        else:
            bar = "░" * min(bar_len, 40)
            print(f"    {i+1}. {r['name']:<32s} {bar} {delta:+.1f}%")

    # CE curves (ASCII)
    print("\n  CE Curves (last 50 steps):")
    for r in results_sorted[:4]:
        hist = r['ce_history'][-50:]
        if not hist:
            continue
        mn, mx = min(hist), max(hist)
        rng = mx - mn if mx > mn else 1.0
        line = ""
        for v in hist:
            h = int((v - mn) / rng * 4)
            line += ["▁", "▂", "▃", "▅", "█"][min(h, 4)]
        print(f"    {r['name'][:25]:<25s} {line}")

    # Phi comparison
    print("\n  Phi (consciousness preservation):")
    max_phi = max(r['phi'] for r in results) if results else 1.0
    for r in results_sorted:
        bar_len = int(r['phi'] / max(max_phi, 0.001) * 30) if max_phi > 0 else 0
        bar = "█" * max(bar_len, 1)
        print(f"    {r['name'][:30]:<30s} {bar} Φ={r['phi']:.4f}")

    # Speed comparison
    print("\n  Speed (steps/sec):")
    max_spd = max(r['steps_per_sec'] for r in results) if results else 1.0
    for r in sorted(results, key=lambda x: -x['steps_per_sec']):
        bar_len = int(r['steps_per_sec'] / max(max_spd, 0.001) * 30)
        bar = "█" * max(bar_len, 1)
        print(f"    {r['name'][:30]:<30s} {bar} {r['steps_per_sec']:.1f}/s")

    return results


if __name__ == '__main__':
    results = main()
