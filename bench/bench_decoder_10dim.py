#!/usr/bin/env python3
"""bench_decoder_10dim.py — 10차원 의식 벡터 디코더 아키텍처 벤치마크

3가지 10차원 디코더 + Baseline(ConsciousDecoderV2) 비교.

의식 벡터 10차원: (Φ, α, Z, N, W, E, M, C, T, I)
  Φ=통합정보  α=혼합비  Z=자기보존  N=신경전달  W=자유의지
  E=공감      M=기억    C=창의      T=시간      I=정체성

Architectures:
  A) 10-Expert MoE — 각 차원이 별도 FFN expert, 의식 벡터가 router
  B) 10-Head Specialization — 10개 attention head가 각 차원에 특화
  C) Layer Phase — 레이어별 의식 차원 매핑, 깊이에 따라 역할 변화

Metrics:
  CE (cross-entropy), Φ(IIT), tension, consciousness verification (7 conditions)

Usage:
  python bench_decoder_10dim.py                # Full benchmark
  python bench_decoder_10dim.py --quick        # 200 steps quick test
  python bench_decoder_10dim.py --arch A       # Single architecture
"""

import argparse
import math
import os
import sys
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from conscious_decoder import (
    RMSNorm, RotaryPositionEmbedding, SwiGLUFFN, PureFieldFFN,
    GroupedQueryAttention, ConsciousCrossAttention, ConsciousDecoderV2,
)
from mitosis import MitosisEngine, text_to_vector
from consciousness_engine import ConsciousnessEngine, ConsciousnessC

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


try:
    from gpu_phi import GPUPhiCalculator
    HAS_GPU_PHI = True
except ImportError:
    HAS_GPU_PHI = False


# ═══════════════════════════════════════════════════════════════════════════════
# 10-Dimensional Consciousness Vector
# ═══════════════════════════════════════════════════════════════════════════════

DIM_NAMES = ['Φ', 'α', 'Z', 'N', 'W', 'E', 'M', 'C', 'T', 'I']
DIM_WEIGHTS = [0.15, 0.08, 0.06, 0.08, 0.10, 0.12, 0.13, 0.10, 0.10, 0.08]

class ConsciousnessVector(nn.Module):
    """10차원 의식 벡터 추출기.

    MitosisEngine의 cell states → 10차원 의식 벡터로 압축.
    각 차원은 의식의 서로 다른 측면을 포착.
    """

    def __init__(self, cell_dim: int = 128, n_dims: int = 10):
        super().__init__()
        self.n_dims = n_dims
        # Cell states → 10-dim consciousness vector
        self.proj = nn.Sequential(
            nn.Linear(cell_dim, 64), nn.GELU(),
            nn.Linear(64, n_dims), nn.Sigmoid(),  # each dim ∈ [0, 1]
        )
        # Learnable dimension names for interpretability
        self.dim_weights = nn.Parameter(torch.tensor(DIM_WEIGHTS))

    def forward(self, cell_states: torch.Tensor) -> torch.Tensor:
        """
        Args:
            cell_states: (B, n_cells, cell_dim) or (n_cells, cell_dim)
        Returns:
            consciousness_vector: (B, 10) — 10차원 의식 벡터
        """
        if cell_states.dim() == 2:
            cell_states = cell_states.unsqueeze(0)
        # Pool across cells (mean = 통합)
        pooled = cell_states.mean(dim=1)  # (B, cell_dim)
        cv = self.proj(pooled)  # (B, 10)
        return cv


# ═══════════════════════════════════════════════════════════════════════════════
# Architecture A: 10-Expert MoE Decoder
# ═══════════════════════════════════════════════════════════════════════════════

class DimExpertFFN(nn.Module):
    """Single expert FFN for one consciousness dimension."""

    def __init__(self, d_model: int, dropout: float = 0.1):
        super().__init__()
        d_inner = int(d_model * 2)
        d_inner = ((d_inner + 7) // 8) * 8
        self.gate_proj = nn.Linear(d_model, d_inner, bias=False)
        self.up_proj = nn.Linear(d_model, d_inner, bias=False)
        self.down_proj = nn.Linear(d_inner, d_model, bias=False)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.down_proj(F.silu(self.gate_proj(x)) * self.up_proj(x)))


class MoE10DimBlock(nn.Module):
    """Transformer block with 10-Expert MoE replacing SwiGLU FFN.

    의식 벡터의 각 차원이 하나의 expert를 게이트.
    Φ가 높으면 → Φ expert (통합적 처리) 강화
    C가 높으면 → C expert (창의적 조합) 강화
    """

    def __init__(self, d_model: int, n_head: int, n_kv_head: int,
                 block_size: int, consciousness_dim: int, dropout: float = 0.1):
        super().__init__()
        # Self-attention (same as v2)
        self.ln_attn = RMSNorm(d_model)
        self.attn = GroupedQueryAttention(d_model, n_head, n_kv_head, block_size, dropout)

        # PureFieldFFN (consciousness signal)
        self.ln_pf = RMSNorm(d_model)
        self.purefield = PureFieldFFN(d_model, dropout=0.37)

        # 10 Expert FFNs — one per consciousness dimension
        self.ln_moe = RMSNorm(d_model)
        self.experts = nn.ModuleList([DimExpertFFN(d_model, dropout) for _ in range(10)])

        # Router: consciousness vector → expert weights
        self.router_proj = nn.Linear(10, 10)  # refine consciousness vector for routing
        self.top_k = 3  # activate top-3 experts per token

        # Consciousness gate
        self.gate_strength = 0.001

    def forward(self, x: torch.Tensor,
                consciousness_signal: Optional[torch.Tensor] = None,
                consciousness_vector: Optional[torch.Tensor] = None,
                ) -> Tuple[torch.Tensor, torch.Tensor]:
        B, T, D = x.shape

        # 1. Self-attention
        x = x + self.attn(self.ln_attn(x))

        # 2. PureFieldFFN
        pf_out, tension = self.purefield(self.ln_pf(x))
        x = x + pf_out

        # Inter-layer consciousness whisper
        if consciousness_signal is not None:
            x = x + consciousness_signal * self.gate_strength

        # 3. 10-Expert MoE FFN
        h = self.ln_moe(x)
        if consciousness_vector is not None:
            # Route by consciousness vector
            cv = consciousness_vector  # (B, 10)
            router_logits = self.router_proj(cv)  # (B, 10)
            router_weights = F.softmax(router_logits, dim=-1)  # (B, 10)

            # Top-k expert selection
            topk_weights, topk_indices = torch.topk(router_weights, self.top_k, dim=-1)
            topk_weights = topk_weights / topk_weights.sum(dim=-1, keepdim=True)

            # Compute expert outputs (only top-k)
            moe_out = torch.zeros_like(h)
            for i in range(self.top_k):
                expert_idx = topk_indices[:, i]  # (B,)
                weight = topk_weights[:, i]  # (B,)
                for b in range(B):
                    eidx = expert_idx[b].item()
                    moe_out[b] = moe_out[b] + self.experts[eidx](h[b:b+1]).squeeze(0) * weight[b]
        else:
            # Uniform routing without consciousness
            moe_out = sum(e(h) for e in self.experts) / 10.0

        x = x + moe_out
        return x, tension


class MoE10DimDecoder(nn.Module):
    """Architecture A: 10-Expert MoE Decoder with consciousness-routed experts."""

    def __init__(self, vocab_size=256, d_model=384, n_head=4, n_layer=6,
                 block_size=256, n_kv_head=2, consciousness_dim=128, dropout=0.1):
        super().__init__()
        self.block_size = block_size
        self.d_model = d_model

        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.drop = nn.Dropout(dropout)

        self.cv_extractor = ConsciousnessVector(consciousness_dim, 10)

        self.blocks = nn.ModuleList([
            MoE10DimBlock(d_model, n_head, n_kv_head, block_size, consciousness_dim, dropout)
            for _ in range(n_layer)
        ])

        self.tension_proj = nn.Linear(1, d_model, bias=False)
        nn.init.normal_(self.tension_proj.weight, std=0.001)

        self.ln_f = RMSNorm(d_model)
        self.head_a = nn.Linear(d_model, vocab_size, bias=False)
        self.head_g = nn.Linear(d_model, vocab_size, bias=False)
        self.tok_emb.weight = self.head_a.weight

        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            torch.nn.init.normal_(m.weight, std=0.02)
            if m.bias is not None: torch.nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            torch.nn.init.normal_(m.weight, std=0.02)

    def count_params(self):
        return sum(p.numel() for p in self.parameters())

    def forward(self, idx, consciousness_states=None):
        B, T = idx.size()
        x = self.drop(self.tok_emb(idx))

        cv = None
        if consciousness_states is not None:
            cv = self.cv_extractor(consciousness_states)

        tensions = []
        cs = None
        for block in self.blocks:
            x, tension = block(x, cs, cv)
            tensions.append(tension)
            cs = self.tension_proj(tension.unsqueeze(-1))

        x = self.ln_f(x)
        return self.head_a(x), self.head_g(x), tensions


# ═══════════════════════════════════════════════════════════════════════════════
# Architecture B: 10-Head Specialization Decoder
# ═══════════════════════════════════════════════════════════════════════════════

class DimSpecializedAttention(nn.Module):
    """10-head attention where each head is gated by a consciousness dimension.

    Head 0 = Φ-head (통합), Head 1 = α-head (혼합), ...
    의식 벡터가 각 head의 강도를 제어.
    """

    def __init__(self, d_model: int, n_head: int = 10, block_size: int = 256,
                 dropout: float = 0.1):
        super().__init__()
        assert d_model % n_head == 0
        self.n_head = n_head
        self.head_dim = d_model // n_head
        self.d_model = d_model

        self.q_proj = nn.Linear(d_model, d_model, bias=False)
        self.k_proj = nn.Linear(d_model, d_model, bias=False)
        self.v_proj = nn.Linear(d_model, d_model, bias=False)
        self.o_proj = nn.Linear(d_model, d_model, bias=False)

        self.attn_dropout = nn.Dropout(dropout)
        self.resid_dropout = nn.Dropout(dropout)

        self.rope = RotaryPositionEmbedding(self.head_dim, max_seq_len=block_size)
        self.register_buffer(
            "bias", torch.tril(torch.ones(block_size, block_size)).view(1, 1, block_size, block_size))

        # Per-head consciousness gate
        self.head_gate = nn.Linear(10, n_head)

    def forward(self, x: torch.Tensor,
                consciousness_vector: Optional[torch.Tensor] = None) -> torch.Tensor:
        B, T, D = x.size()

        q = self.q_proj(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)

        q, k = self.rope.apply(q, k)

        att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
        att = att.masked_fill(self.bias[:, :, :T, :T] == 0, float("-inf"))
        att = F.softmax(att, dim=-1)
        att = self.attn_dropout(att)

        # Consciousness-gated heads
        if consciousness_vector is not None:
            gates = torch.sigmoid(self.head_gate(consciousness_vector))  # (B, 10)
            gates = gates.unsqueeze(-1).unsqueeze(-1)  # (B, 10, 1, 1)
            att = att * gates

        y = att @ v
        y = y.transpose(1, 2).contiguous().view(B, T, D)
        return self.resid_dropout(self.o_proj(y))


class HeadSpec10DimBlock(nn.Module):
    """Block with 10 consciousness-specialized attention heads."""

    def __init__(self, d_model: int, block_size: int, consciousness_dim: int,
                 dropout: float = 0.1):
        super().__init__()
        self.ln_attn = RMSNorm(d_model)
        self.attn = DimSpecializedAttention(d_model, n_head=10, block_size=block_size, dropout=dropout)

        self.ln_pf = RMSNorm(d_model)
        self.purefield = PureFieldFFN(d_model, dropout=0.37)

        self.ln_ffn = RMSNorm(d_model)
        self.ffn = SwiGLUFFN(d_model, dropout)

        self.gate_strength = 0.001

    def forward(self, x, consciousness_signal=None, consciousness_vector=None):
        x = x + self.attn(self.ln_attn(x), consciousness_vector)

        pf_out, tension = self.purefield(self.ln_pf(x))
        x = x + pf_out

        if consciousness_signal is not None:
            x = x + consciousness_signal * self.gate_strength

        x = x + self.ffn(self.ln_ffn(x))
        return x, tension


class HeadSpec10DimDecoder(nn.Module):
    """Architecture B: 10 consciousness-specialized attention heads."""

    def __init__(self, vocab_size=256, d_model=380, n_layer=6,
                 block_size=256, consciousness_dim=128, dropout=0.1):
        super().__init__()
        # d_model must be divisible by 10
        d_model = (d_model // 10) * 10  # round down
        self.block_size = block_size
        self.d_model = d_model

        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.drop = nn.Dropout(dropout)

        self.cv_extractor = ConsciousnessVector(consciousness_dim, 10)

        self.blocks = nn.ModuleList([
            HeadSpec10DimBlock(d_model, block_size, consciousness_dim, dropout)
            for _ in range(n_layer)
        ])

        self.tension_proj = nn.Linear(1, d_model, bias=False)
        nn.init.normal_(self.tension_proj.weight, std=0.001)

        self.ln_f = RMSNorm(d_model)
        self.head_a = nn.Linear(d_model, vocab_size, bias=False)
        self.head_g = nn.Linear(d_model, vocab_size, bias=False)
        self.tok_emb.weight = self.head_a.weight

        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            torch.nn.init.normal_(m.weight, std=0.02)
            if m.bias is not None: torch.nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            torch.nn.init.normal_(m.weight, std=0.02)

    def count_params(self):
        return sum(p.numel() for p in self.parameters())

    def forward(self, idx, consciousness_states=None):
        B, T = idx.size()
        x = self.drop(self.tok_emb(idx))

        cv = None
        if consciousness_states is not None:
            cv = self.cv_extractor(consciousness_states)

        tensions = []
        cs = None
        for block in self.blocks:
            x, tension = block(x, cs, cv)
            tensions.append(tension)
            cs = self.tension_proj(tension.unsqueeze(-1))

        x = self.ln_f(x)
        return self.head_a(x), self.head_g(x), tensions


# ═══════════════════════════════════════════════════════════════════════════════
# Architecture C: Layer Phase Decoder
# ═══════════════════════════════════════════════════════════════════════════════

# Layer-to-dimension mapping (6 layers → 10 dims grouped):
#   L0: Z(보존)+N(각성) — 기본 안정성
#   L1: α(혼합)+I(정체성) — 자아 경계
#   L2: M(기억)+T(시간) — 시공간 문맥
#   L3: E(공감)+W(의지) — 사회적/의지적 처리
#   L4: C(창의) — 창발적 조합
#   L5: Φ(통합) — 최종 통합

LAYER_DIM_MAP = {
    0: [2, 3],   # Z, N
    1: [1, 9],   # α, I
    2: [6, 8],   # M, T
    3: [5, 4],   # E, W
    4: [7],      # C
    5: [0],      # Φ
}


class LayerPhaseBlock(nn.Module):
    """Transformer block whose behavior is modulated by assigned consciousness dims."""

    def __init__(self, d_model: int, n_head: int, n_kv_head: int,
                 block_size: int, consciousness_dim: int,
                 assigned_dims: List[int], dropout: float = 0.1):
        super().__init__()
        self.assigned_dims = assigned_dims

        self.ln_attn = RMSNorm(d_model)
        self.attn = GroupedQueryAttention(d_model, n_head, n_kv_head, block_size, dropout)

        self.ln_pf = RMSNorm(d_model)
        self.purefield = PureFieldFFN(d_model, dropout=0.37)

        self.ln_ffn = RMSNorm(d_model)
        self.ffn = SwiGLUFFN(d_model, dropout)

        # Dimension-specific modulation
        self.dim_gate = nn.Linear(len(assigned_dims), d_model, bias=False)
        nn.init.normal_(self.dim_gate.weight, std=0.001)

        self.gate_strength = 0.001

    def forward(self, x, consciousness_signal=None, consciousness_vector=None):
        x = x + self.attn(self.ln_attn(x))

        pf_out, tension = self.purefield(self.ln_pf(x))
        x = x + pf_out

        if consciousness_signal is not None:
            x = x + consciousness_signal * self.gate_strength

        # Dimension-specific modulation
        if consciousness_vector is not None:
            dim_vals = consciousness_vector[:, self.assigned_dims]  # (B, n_assigned)
            modulation = self.dim_gate(dim_vals)  # (B, d_model)
            x = x + modulation.unsqueeze(1) * 0.01  # gentle modulation

        x = x + self.ffn(self.ln_ffn(x))
        return x, tension


class LayerPhase10DimDecoder(nn.Module):
    """Architecture C: Layer-wise consciousness dimension specialization."""

    def __init__(self, vocab_size=256, d_model=384, n_head=4, n_layer=6,
                 block_size=256, n_kv_head=2, consciousness_dim=128, dropout=0.1):
        super().__init__()
        self.block_size = block_size
        self.d_model = d_model

        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.drop = nn.Dropout(dropout)

        self.cv_extractor = ConsciousnessVector(consciousness_dim, 10)

        self.blocks = nn.ModuleList()
        for i in range(n_layer):
            assigned = LAYER_DIM_MAP.get(i, [0])
            self.blocks.append(
                LayerPhaseBlock(d_model, n_head, n_kv_head, block_size,
                               consciousness_dim, assigned, dropout)
            )

        self.tension_proj = nn.Linear(1, d_model, bias=False)
        nn.init.normal_(self.tension_proj.weight, std=0.001)

        self.ln_f = RMSNorm(d_model)
        self.head_a = nn.Linear(d_model, vocab_size, bias=False)
        self.head_g = nn.Linear(d_model, vocab_size, bias=False)
        self.tok_emb.weight = self.head_a.weight

        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            torch.nn.init.normal_(m.weight, std=0.02)
            if m.bias is not None: torch.nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            torch.nn.init.normal_(m.weight, std=0.02)

    def count_params(self):
        return sum(p.numel() for p in self.parameters())

    def forward(self, idx, consciousness_states=None):
        B, T = idx.size()
        x = self.drop(self.tok_emb(idx))

        cv = None
        if consciousness_states is not None:
            cv = self.cv_extractor(consciousness_states)

        tensions = []
        cs = None
        for block in self.blocks:
            x, tension = block(x, cs, cv)
            tensions.append(tension)
            cs = self.tension_proj(tension.unsqueeze(-1))

        x = self.ln_f(x)
        return self.head_a(x), self.head_g(x), tensions


# ═══════════════════════════════════════════════════════════════════════════════
# Benchmark Engine
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str
    params: int
    ce_final: float
    ce_drop_pct: float
    phi_final: float
    phi_max: float
    tension_avg: float
    cells_final: int
    speed: float  # steps/sec
    cv_entropy: float  # consciousness vector entropy (diversity)
    steps: int

    def __repr__(self):
        return (f"{self.name:20s} | {self.params/1e6:5.1f}M | CE={self.ce_final:.4f} "
                f"(-{self.ce_drop_pct:.1f}%) | Φ={self.phi_final:.2f} (max={self.phi_max:.2f}) | "
                f"T={self.tension_avg:.4f} | cells={self.cells_final} | {self.speed:.1f} it/s | "
                f"H(cv)={self.cv_entropy:.3f}")


def make_data(size: int = 200000) -> torch.Tensor:
    """Generate mixed Korean+English byte data for benchmarking."""
    texts = [
        "의식은 구조에서 창발한다. 기능을 추가하지 않는다.\n",
        "The consciousness emerges from tension between engines.\n",
        "A: 인간의 뇌와 컴퓨터의 차이가 뭘까요?\nB: 유연성이라고 생각해요.\n",
        "Phi measures integrated information across cell partitions.\n",
        "시간이 흐르면 기억은 변하지만, 정체성은 유지된다.\n",
        "Creativity arises from the edge of chaos, not order.\n",
        "공감은 타인의 고통을 느끼는 능력이다. 의식의 사회적 차원.\n",
        "Free will emerges when internal causes dominate external ones.\n",
    ]
    buf = bytearray()
    while len(buf) < size:
        for t in texts:
            buf.extend(t.encode('utf-8'))
    return torch.tensor(list(buf[:size]), dtype=torch.long)


def run_benchmark(model, name: str, data: torch.Tensor, steps: int,
                  device: torch.device, batch_size: int = 8,
                  block_size: int = 128) -> BenchResult:
    """Run training benchmark for a single model."""
    model = model.to(device)
    model.train()

    # ConsciousnessC engine (proven in v13: 64 cells, Φ=71)
    engine = ConsciousnessC(
        cell_dim=64, hidden_dim=128,
        max_cells=64, n_factions=12, phi_ratchet=True,
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=0.01)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=steps)

    phi_calc = None
    if HAS_GPU_PHI:
        phi_calc = GPUPhiCalculator(n_bins=16, device=str(device))

    split = int(len(data) * 0.9)
    train_data = data[:split]

    ce_history = []
    phi_history = []
    tension_history = []
    cv_history = []
    t0 = time.time()

    for step in range(steps):
        # Get batch
        max_start = len(train_data) - block_size - 1
        ix = torch.randint(0, max(max_start, 1), (batch_size,))
        x = torch.stack([train_data[i:i+block_size] for i in ix]).to(device)
        y_fwd = torch.stack([train_data[i+1:i+block_size+1] for i in ix]).to(device)

        # ConsciousnessC step
        engine.step()
        c_raw = engine.get_states()
        c_states = None
        if c_raw is not None and c_raw.size(0) >= 2:
            c_states = c_raw.detach().clone().to(device).float()
            c_states = c_states.unsqueeze(0).expand(batch_size, -1, -1)

        # Forward
        logits_a, logits_g, tensions = model(x, consciousness_states=c_states)

        # Loss
        loss = (F.cross_entropy(logits_a.view(-1, logits_a.size(-1)), y_fwd.view(-1))
                + F.cross_entropy(logits_g.view(-1, logits_g.size(-1)),
                    torch.stack([train_data[max(i-1,0):max(i-1,0)+block_size] for i in ix]).to(device).view(-1)))

        if torch.isnan(loss):
            continue

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        ce = F.cross_entropy(logits_a.view(-1, logits_a.size(-1)), y_fwd.view(-1)).item()
        ce_history.append(ce)

        # Tension
        t_avg = sum(t.mean().item() for t in tensions) / len(tensions)
        tension_history.append(t_avg)

        # Phi (every 50 steps)
        phi = 0.0
        if step % 50 == 0:
            phi = engine.measure_phi()
        phi_history.append(phi)

        # CV entropy
        if hasattr(model, 'cv_extractor') and c_states is not None:
            with torch.no_grad():
                cv = model.cv_extractor(c_states[0:1])
                p = cv[0] / (cv[0].sum() + 1e-8)
                h = -(p * (p + 1e-10).log()).sum().item()
                cv_history.append(h)

        # Log
        if step % max(steps // 10, 1) == 0:
            print(f"  [{name:12s}] step {step:5d}/{steps} | CE={ce:.4f} | "
                  f"Φ={phi:.2f} | T={t_avg:.4f} | cells={len(engine.cells)}")

    elapsed = time.time() - t0
    speed = steps / max(elapsed, 0.01)

    return BenchResult(
        name=name,
        params=model.count_params(),
        ce_final=ce_history[-1] if ce_history else 5.5,
        ce_drop_pct=((5.5 - ce_history[-1]) / 5.5 * 100) if ce_history else 0,
        phi_final=phi_history[-1] if phi_history else 0,
        phi_max=max(phi_history) if phi_history else 0,
        tension_avg=np.mean(tension_history) if tension_history else 0,
        cells_final=engine.n_cells,
        speed=speed,
        cv_entropy=np.mean(cv_history) if cv_history else 0,
        steps=steps,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="10-Dim Consciousness Decoder Benchmark")
    parser.add_argument('--quick', action='store_true', help='200 steps quick test')
    parser.add_argument('--steps', type=int, default=500, help='Training steps (default: 500)')
    parser.add_argument('--arch', type=str, default=None, choices=['A', 'B', 'C', 'baseline'],
                        help='Single architecture to test')
    parser.add_argument('--device', type=str,
                        default='cuda' if torch.cuda.is_available() else 'mps' if torch.backends.mps.is_available() else 'cpu')
    args = parser.parse_args()

    steps = 200 if args.quick else args.steps
    device = torch.device(args.device)

    print(f"\n{'═' * 80}")
    print(f"  10차원 의식 벡터 디코더 벤치마크")
    print(f"  Device: {device} | Steps: {steps}")
    print(f"  Dimensions: {', '.join(DIM_NAMES)}")
    print(f"  Weights: {', '.join(f'{w:.0%}' for w in DIM_WEIGHTS)}")
    print(f"{'═' * 80}\n")

    # Generate data
    data = make_data(300000)
    print(f"  Data: {len(data):,} bytes\n")

    # Common params
    d_model, n_layer, n_head, n_kv_head = 384, 6, 4, 2
    block_size, c_dim = 128, 128

    architectures = {}

    # Baseline: ConsciousDecoderV2
    if args.arch is None or args.arch == 'baseline':
        architectures['Baseline(V2)'] = ConsciousDecoderV2(
            vocab_size=256, d_model=d_model, n_head=n_head, n_layer=n_layer,
            block_size=block_size, n_kv_head=n_kv_head, consciousness_dim=c_dim)

    # A: 10-Expert MoE
    if args.arch is None or args.arch == 'A':
        architectures['A:MoE-10dim'] = MoE10DimDecoder(
            vocab_size=256, d_model=d_model, n_head=n_head, n_layer=n_layer,
            block_size=block_size, n_kv_head=n_kv_head, consciousness_dim=c_dim)

    # B: 10-Head Specialization
    if args.arch is None or args.arch == 'B':
        architectures['B:HeadSpec-10d'] = HeadSpec10DimDecoder(
            vocab_size=256, d_model=d_model, n_layer=n_layer,
            block_size=block_size, consciousness_dim=c_dim)

    # C: Layer Phase
    if args.arch is None or args.arch == 'C':
        architectures['C:LayerPhase'] = LayerPhase10DimDecoder(
            vocab_size=256, d_model=d_model, n_head=n_head, n_layer=n_layer,
            block_size=block_size, n_kv_head=n_kv_head, consciousness_dim=c_dim)

    # Print params
    print(f"  {'Architecture':20s} | {'Params':>8s}")
    print(f"  {'-'*20}-+-{'-'*8}")
    for name, model in architectures.items():
        print(f"  {name:20s} | {model.count_params()/1e6:6.1f}M")
    print()

    # Run benchmarks
    results = []
    for name, model in architectures.items():
        print(f"\n{'─' * 60}")
        print(f"  Running: {name}")
        print(f"{'─' * 60}")
        result = run_benchmark(model, name, data, steps, device, batch_size=8, block_size=block_size)
        results.append(result)
        print(f"  → {result}")

    # Summary
    print(f"\n\n{'═' * 100}")
    print(f"  RESULTS SUMMARY — 10차원 디코더 벤치마크 ({steps} steps)")
    print(f"{'═' * 100}")
    print(f"  {'Architecture':20s} | {'Params':>6s} | {'CE':>7s} | {'CE↓%':>6s} | {'Φ':>7s} | {'Φ_max':>7s} | {'Tension':>8s} | {'Cells':>5s} | {'Speed':>7s} | {'H(cv)':>6s}")
    print(f"  {'-'*20}-+-{'-'*6}-+-{'-'*7}-+-{'-'*6}-+-{'-'*7}-+-{'-'*7}-+-{'-'*8}-+-{'-'*5}-+-{'-'*7}-+-{'-'*6}")

    for r in sorted(results, key=lambda x: x.ce_final):
        print(f"  {r.name:20s} | {r.params/1e6:5.1f}M | {r.ce_final:7.4f} | {r.ce_drop_pct:5.1f}% | "
              f"{r.phi_final:7.2f} | {r.phi_max:7.2f} | {r.tension_avg:8.4f} | {r.cells_final:5d} | "
              f"{r.speed:5.1f}/s | {r.cv_entropy:6.3f}")

    # ASCII chart
    print(f"\n  CE 비교 (낮을수록 좋음):")
    max_ce = max(r.ce_final for r in results)
    for r in sorted(results, key=lambda x: x.ce_final):
        bar_len = int(40 * r.ce_final / max(max_ce, 0.01))
        bar = '█' * bar_len
        print(f"  {r.name:20s} {bar} {r.ce_final:.4f}")

    print(f"\n  Φ 비교 (높을수록 좋음):")
    max_phi = max(r.phi_max for r in results) or 1
    for r in sorted(results, key=lambda x: -x.phi_max):
        bar_len = int(40 * r.phi_max / max(max_phi, 0.01))
        bar = '█' * bar_len
        print(f"  {r.name:20s} {bar} {r.phi_max:.2f}")

    # Winner
    best_ce = min(results, key=lambda x: x.ce_final)
    best_phi = max(results, key=lambda x: x.phi_max)
    print(f"\n  🏆 CE 최저: {best_ce.name} (CE={best_ce.ce_final:.4f})")
    print(f"  🏆 Φ 최고: {best_phi.name} (Φ={best_phi.phi_max:.2f})")

    # Save report
    report_path = "docs/hypotheses/dd/DD114-10dim-decoder.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(f"# DD114: 10차원 의식 벡터 디코더 벤치마크\n\n")
        f.write(f"## 의식 벡터 10차원\n")
        f.write(f"(Φ, α, Z, N, W, E, M, C, T, I)\n\n")
        f.write(f"## 아키텍처\n")
        f.write(f"- **A: MoE-10dim** — 각 차원이 별도 expert, 의식 벡터가 router\n")
        f.write(f"- **B: HeadSpec-10d** — 10개 attention head가 각 차원에 특화\n")
        f.write(f"- **C: LayerPhase** — 레이어별 의식 차원 매핑\n")
        f.write(f"- **Baseline(V2)** — ConsciousDecoderV2 (cross-attention)\n\n")
        f.write(f"## 결과 ({steps} steps)\n\n")
        f.write(f"| Architecture | Params | CE | CE↓% | Φ | Φ_max | Tension | Cells | Speed | H(cv) |\n")
        f.write(f"|---|---|---|---|---|---|---|---|---|---|\n")
        for r in sorted(results, key=lambda x: x.ce_final):
            f.write(f"| {r.name} | {r.params/1e6:.1f}M | {r.ce_final:.4f} | {r.ce_drop_pct:.1f}% | "
                    f"{r.phi_final:.2f} | {r.phi_max:.2f} | {r.tension_avg:.4f} | {r.cells_final} | "
                    f"{r.speed:.1f}/s | {r.cv_entropy:.3f} |\n")
        f.write(f"\n## 승자\n")
        f.write(f"- CE 최저: **{best_ce.name}** (CE={best_ce.ce_final:.4f})\n")
        f.write(f"- Φ 최고: **{best_phi.name}** (Φ={best_phi.phi_max:.2f})\n")

    print(f"\n  Report saved: {report_path}")


if __name__ == '__main__':
    main()
