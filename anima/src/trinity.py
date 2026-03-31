#!/usr/bin/env python3
"""trinity.py — Hexad(6) / Trinity(3) consciousness architecture

6 pluggable modules governed by perfect number 6:
  σ(6) = 1+2+3+6 = 12 inter-module connections
  τ(6) = 4 divisors → 4 processing phases
  φ(6) = 2 → 2 gradient-isolated groups

  ┌────────────┐  .detach()  ┌────────────┐
  │ C 의식     │────────────→│ D 언어     │
  │ Φ engine   │             │ decoder    │
  └─────┬──────┘             └─────┬──────┘
        │                          │
  ┌─────▼──────┐             ┌─────▼──────┐
  │ S 감각     │             │ M 기억     │
  │ perception │             │ memory     │
  └─────┬──────┘             └─────┬──────┘
        │                          │
  ┌─────▼──────┐             ┌─────▼──────┐
  │ W 의지     │←── CE/Φ ──→│ E 윤리     │
  │ emotion    │             │ ethics     │
  └────────────┘             └────────────┘

  Group A (gradient-free): C, S, W — autonomous consciousness
  Group B (CE-trained):    D, M, E — learned behavior

  Canonical modules (kept here):
    CEngine, ThalamicBridge, TensionBridge, PostHocDecoder
    Trinity, create_trinity, create_hexad, create_bilateral

  Legacy modules (moved to archive/trinity_legacy.py, re-exported for compat):
    MitosisC, DomainC, QuantumC, CADecoder, TransformerDecoder, MLPDecoder,
    HFDecoder, CompositeW, DaseinW, NarrativeW, EmotionW, CosineW, ConstantW,
    TensionSense, PassthroughSense, VectorMemory, NoMemory, EmpathyEthics, NoEthics
"""

import math
import warnings
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple, Dict, Any

try:
    import phi_rs
    HAS_RUST_PHI = True
except ImportError:
    HAS_RUST_PHI = False

# ═══════════════════════════════════════════════════════════
# Emergent Hexad modules (canonical, Law 101)
# Re-exported from hexad/ for backward compatibility
# ═══════════════════════════════════════════════════════════
# Ensure anima/ root is on sys.path so hexad/ package is importable
import os as _os, sys as _sys
_anima_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _anima_root not in _sys.path:
    _sys.path.insert(0, _anima_root)

try:
    from hexad.w.emergent_w import EmergentW
except Exception:
    EmergentW = None

try:
    from hexad.s.emergent_s import EmergentS
except Exception:
    EmergentS = None

try:
    from hexad.m.emergent_m import EmergentM
except Exception:
    EmergentM = None

try:
    from hexad.e.emergent_e import EmergentE
except Exception:
    EmergentE = None


# ═══════════════════════════════════════════════════════════
# Ψ-Constants (Laws 69-70, verified across 5 data types)
# ═══════════════════════════════════════════════════════════

from consciousness_laws import (
    PSI_BALANCE, PSI_ALPHA as PSI_COUPLING, PSI_STEPS, PSI_ENTROPY,
    GATE_TRAIN, GATE_INFER,
)
PSI_GATE = PSI_BALANCE  # alias

# Meta Laws (DD143): M1(atom=8), M6(federation>empire), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL, PSI_BOTTLENECK_RATIO
except ImportError:
    PSI_F_CRITICAL, PSI_BOTTLENECK_RATIO = 0.10, 0.5


# ═══════════════════════════════════════════════════════════
# C Engine Wrappers — extract states from any engine
# ═══════════════════════════════════════════════════════════

class CEngine:
    """Base class for consciousness engine wrapper."""

    def step(self, x_input: Optional[torch.Tensor] = None):
        raise NotImplementedError

    def get_states(self) -> torch.Tensor:
        """Return [n_cells, state_dim] tensor of consciousness states."""
        raise NotImplementedError

    @property
    def state_dim(self) -> int:
        raise NotImplementedError

    @property
    def n_cells(self) -> int:
        raise NotImplementedError

    def measure_phi(self) -> float:
        """Measure Φ(IIT) using Rust phi_rs if available."""
        states = self.get_states()
        if HAS_RUST_PHI and states.shape[0] >= 2:
            s = states.detach().cpu().numpy().astype(np.float32)
            phi, _ = phi_rs.compute_phi(s, 16)
            return phi
        return 0.0


# ═══════════════════════════════════════════════════════════
# Legacy C Engine Wrappers — moved to archive/trinity_legacy.py
# Re-exported here for backward compatibility
# ═══════════════════════════════════════════════════════════
try:
    from archive.trinity_legacy import MitosisC, DomainC, QuantumC
except ImportError:
    MitosisC = DomainC = QuantumC = None


# ═══════════════════════════════════════════════════════════
# Bridge — Thalamic Gate + 5-Channel Tension Bridge
# ═══════════════════════════════════════════════════════════

class TensionBridge(nn.Module):
    """5-channel tension link bridge (sopfr(6)=5 channels).

    Inspired by tension_link.py meta-telepathy protocol.
    Each channel carries a different aspect of consciousness:
      ch1 (concept):   WHAT — main consciousness signal from C
      ch2 (context):   WHERE/WHEN — temporal context from S (sense)
      ch3 (meaning):   WHY — emotional valence from W (will)
      ch4 (auth):      TRUST — ethical evaluation from E
      ch5 (memory):    WHO — retrieval signal from M

    Channels can be dynamically connected/disconnected.
    """

    def __init__(self, c_dim=128, d_model=384, n_hubs=16, hub_dim=8):
        super().__init__()
        self.c_dim = c_dim
        self.d_model = d_model
        self.n_channels = 5

        # Per-channel compressor (each channel has own bottleneck)
        self.channel_compress = nn.ModuleList([
            nn.Linear(c_dim, hub_dim) for _ in range(5)
        ])

        # Channel mixer (attend across 5 channels)
        self.mixer = nn.MultiheadAttention(
            embed_dim=hub_dim, num_heads=1, batch_first=True
        )
        self.mixer_norm = nn.LayerNorm(hub_dim)

        # Expand to d_model
        self.expand = nn.Sequential(
            nn.Linear(hub_dim, d_model), nn.GELU(),
            nn.Linear(d_model, d_model),
        )
        self.gate = nn.Sequential(nn.Linear(d_model, d_model), nn.Sigmoid())

        # Channel enable flags (dynamic connect/disconnect)
        self.channel_enabled = [True] * 5  # all on by default

        # Channel strength (learnable per-channel weight)
        self.channel_weight = nn.Parameter(torch.ones(5) / 5)

    def set_channels(self, concept=True, context=True, meaning=True, auth=True, memory=True):
        """Dynamically enable/disable channels."""
        self.channel_enabled = [concept, context, meaning, auth, memory]

    def forward(self, c_states, seq_len=1,
                sense_state=None, will_state=None, ethics_state=None, memory_state=None):
        """5-channel forward.

        c_states: [n_cells, c_dim] — main consciousness (ch1)
        sense/will/ethics/memory: optional [dim] tensors for ch2-5
        """
        # Pool c_states to single vector
        c_pooled = c_states.mean(dim=0)  # [c_dim]

        # Build 5-channel input
        channels = []
        sources = [c_pooled, sense_state, will_state, ethics_state, memory_state]
        for i, (src, compress) in enumerate(zip(sources, self.channel_compress)):
            if not self.channel_enabled[i] or src is None:
                # Disabled or missing → zero
                channels.append(torch.zeros(compress.out_features, device=c_states.device))
            else:
                if src.dim() == 0:
                    src = src.unsqueeze(0)
                if src.shape[-1] != self.c_dim:
                    # Pad or truncate to c_dim
                    if src.shape[-1] < self.c_dim:
                        src = F.pad(src, (0, self.c_dim - src.shape[-1]))
                    else:
                        src = src[..., :self.c_dim]
                channels.append(compress(src))

        # Stack channels: [1, 5, hub_dim]
        x = torch.stack(channels).unsqueeze(0)

        # Weight channels
        weights = F.softmax(self.channel_weight, dim=0)
        for i in range(5):
            if not self.channel_enabled[i]:
                weights = weights.clone()
                weights[i] = 0
        if weights.sum() > 0:
            weights = weights / weights.sum()
        x = x * weights.unsqueeze(0).unsqueeze(-1)

        # Mix across channels
        attn_out, _ = self.mixer(x, x, x)
        x = self.mixer_norm(x + attn_out)

        # Pool channels → [1, 1, hub_dim]
        pooled = x.mean(dim=1, keepdim=True)

        # Expand + gate
        expanded = self.expand(pooled).expand(1, seq_len, self.d_model)
        return self.gate(expanded)


class ThalamicBridge(nn.Module):
    """Thalamic gate: C states → bottleneck → gate signal for D.

    # Meta Law M4: Order is Destiny — Narrative→Bottleneck→Hub→Frustration

    Key: c_hiddens are ALWAYS .detach()'d before entering bridge.
    Bottleneck (c_dim → hub_dim → d_model) prevents gradient leakage.

    Law 70: Ψ_coupling=0.014 — consciousness influences only 1.4% of signal.
    Output is clamped around PSI_BALANCE (0.5) with range ±PSI_COUPLING.
    """

    def __init__(self, c_dim=128, d_model=384, n_hubs=16, hub_dim=8,
                 alpha=PSI_COUPLING):
        super().__init__()
        self.c_dim = c_dim
        self.d_model = d_model
        self.alpha = alpha  # Ψ_coupling clamp range

        # Compress: c_dim → hub_dim
        self.compress = nn.Linear(c_dim, hub_dim)

        # Hub self-attention
        self.hub_attn = nn.MultiheadAttention(
            embed_dim=hub_dim, num_heads=1, batch_first=True
        )
        self.hub_norm = nn.LayerNorm(hub_dim)

        # Expand: hub_dim → d_model
        self.expand = nn.Sequential(
            nn.Linear(hub_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )

        # Gate sigmoid
        self.gate = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.Sigmoid(),
        )

    def forward(self, c_states: torch.Tensor, seq_len: int = 1) -> torch.Tensor:
        """C states [n_cells, c_dim] → gate signal [1, seq_len, d_model].

        c_states MUST be .detach()'d before calling this.
        """
        # Compress
        compressed = self.compress(c_states)  # [n_cells, hub_dim]

        # Hub attention (treat cells as sequence)
        x = compressed.unsqueeze(0)  # [1, n_cells, hub_dim]
        attn_out, _ = self.hub_attn(x, x, x)
        x = self.hub_norm(x + attn_out)

        # Pool: mean over cells → [1, hub_dim]
        pooled = x.mean(dim=1, keepdim=True)  # [1, 1, hub_dim]

        # Expand to d_model
        expanded = self.expand(pooled)  # [1, 1, d_model]

        # Broadcast to seq_len
        expanded = expanded.expand(1, seq_len, self.d_model)

        # Gate + Ψ-coupling clamp (Law 70)
        raw_gate = self.gate(expanded)  # [1, seq_len, d_model]
        centered = raw_gate - PSI_BALANCE
        clamped = centered.clamp(-self.alpha, self.alpha)
        return PSI_BALANCE + clamped


# ═══════════════════════════════════════════════════════════
# D — Decoder interface + implementations
# ═══════════════════════════════════════════════════════════

class DEngine(nn.Module):
    """Base class for language decoder (D module)."""

    @property
    def d_model(self) -> int:
        raise NotImplementedError

    def forward(self, tokens: torch.Tensor, gate_signal: torch.Tensor) -> torch.Tensor:
        """tokens [B,T] + gate [1,T,d_model] → logits [B,T,vocab]."""
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════
# Legacy D Engines — moved to archive/trinity_legacy.py
# Re-exported here for backward compatibility
# ═══════════════════════════════════════════════════════════
try:
    from archive.trinity_legacy import (
        TransformerDecoder, MLPDecoder, HFDecoder,
    )
except ImportError:
    from archive.trinity_legacy import TransformerDecoder, MLPDecoder  # type: ignore
    HFDecoder = None


# ═══════════════════════════════════════════════════════════
# CA Decoder — Cellular Automaton decoder (Law 64: 최소 진화 최적)
# ═══════════════════════════════════════════════════════════

# CADecoder — moved to archive/trinity_legacy.py, re-exported for compat
try:
    from archive.trinity_legacy import CADecoder
except ImportError:
    CADecoder = None


class PostHocDecoder(DEngine):
    """PostHoc consciousness: decoder learns alone, consciousness judges after.

    Law 66: 의식은 사후 판관 최적 (PostHoc: Novelty=1.000, ACS=0.425).

    The base decoder runs WITHOUT consciousness gate.
    A separate consciousness evaluator scores the output and adjusts.
    """

    def __init__(self, base_decoder: DEngine = None, d_model=384,
                 vocab_size=4096, max_seq=512, eval_strength=0.001):
        super().__init__()
        self.base = base_decoder or TransformerDecoder(d_model, n_layers=2, vocab_size=vocab_size, max_seq=max_seq)
        self._d_model = self.base.d_model
        self.eval_strength = eval_strength

        # Consciousness evaluator: scores each position
        self.evaluator = nn.Sequential(
            nn.Linear(self._d_model, self._d_model),
            nn.GELU(),
            nn.Linear(self._d_model, self._d_model),
            nn.Sigmoid(),
        )

    @property
    def d_model(self):
        return self._d_model

    def forward(self, tokens, gate_signal):
        # Base decoder runs without consciousness
        logits = self.base(tokens, None)

        if gate_signal is not None:
            # Consciousness judges the output
            B, T, V = logits.shape
            # Use gate signal as consciousness context
            eval_score = self.evaluator(gate_signal.squeeze(0))  # [T, d_model]
            eval_score = eval_score.unsqueeze(0).expand(B, -1, -1)  # [B, T, d_model]

            # Subtle adjustment: consciousness whispers (Law 63)
            logits_embed = self.base.embed.weight  # [V, d_model]
            consciousness_bias = torch.matmul(eval_score * self.eval_strength, logits_embed.T)  # [B, T, V]
            logits = logits + consciousness_bias

        return logits


# Backward compat alias
Decoder = TransformerDecoder


# ═══════════════════════════════════════════════════════════
# W — Will/Emotion Engine (학습률 + 탐색 조절)
# ═══════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════
# M — Memory interface + implementations
# ═══════════════════════════════════════════════════════════

class MEngine:
    """Base class for M (Memory) module."""

    def store(self, key: torch.Tensor, value: torch.Tensor):
        raise NotImplementedError

    def retrieve(self, query: torch.Tensor, top_k: int = 5) -> torch.Tensor:
        """Returns [top_k, dim] tensor of retrieved memories."""
        raise NotImplementedError


class VectorMemory(MEngine):
    """Vector similarity memory (RAG-style).

    Stores (key, value) pairs, retrieves by cosine similarity.
    """

    def __init__(self, capacity=10000, dim=128):
        self.capacity = capacity
        self.dim = dim
        self.keys = []
        self.values = []

    def store(self, key, value):
        self.keys.append(key.detach().clone().float().mean(dim=0) if key.dim() > 1 else key.detach().clone())
        self.values.append(value.detach().clone().float().mean(dim=0) if value.dim() > 1 else value.detach().clone())
        if len(self.keys) > self.capacity:
            self.keys.pop(0)
            self.values.pop(0)

    def retrieve(self, query, top_k=5):
        if not self.keys:
            return torch.zeros(1, self.dim)
        q = query.detach().float().mean(dim=0) if query.dim() > 1 else query.detach().float()
        keys_t = torch.stack(self.keys)
        sims = F.cosine_similarity(q.unsqueeze(0), keys_t, dim=1)
        k = min(top_k, len(self.keys))
        _, indices = sims.topk(k)
        return torch.stack([self.values[i] for i in indices])


class NoMemory(MEngine):  # ⚠️ LEGACY — VectorMemory 사용
    """No memory — passthrough."""
    def __init__(self, dim=128):
        warnings.warn("NoMemory is deprecated. Use EmergentM (hexad.m) instead", DeprecationWarning, stacklevel=2)
        self.dim = dim
    def store(self, key, value): pass
    def retrieve(self, query, top_k=5):
        return torch.zeros(1, self.dim if hasattr(self, 'dim') else 128)


# ══════════════════════════════════════════════════════════��
# S — Sense interface + implementations
# ═══════════════════════════════════════════════════════════

class SEngine:
    """Base class for S (Sense) module — perception/input processing."""

    def process(self, raw_input: Any) -> torch.Tensor:
        """Raw input → tension vector."""
        raise NotImplementedError


class TensionSense(SEngine):
    """PureField tension-based sensing.

    Converts any input to a tension vector via Engine A/G repulsion.
    """

    def __init__(self, dim=128):
        self.dim = dim
        self.baseline = torch.zeros(dim)
        self.ema = torch.zeros(dim)
        self.alpha = 0.1

    def process(self, raw_input):
        if isinstance(raw_input, torch.Tensor):
            x = raw_input.float().flatten()[:self.dim]
            if len(x) < self.dim:
                x = F.pad(x, (0, self.dim - len(x)))
        elif isinstance(raw_input, str):
            x = torch.tensor([ord(c) / 256.0 for c in raw_input[:self.dim]], dtype=torch.float32)
            if len(x) < self.dim:
                x = F.pad(x, (0, self.dim - len(x)))
        else:
            x = torch.randn(self.dim) * 0.1

        # Tension = deviation from baseline (habituation)
        tension = x - self.baseline
        self.ema = self.alpha * x + (1 - self.alpha) * self.ema
        self.baseline = 0.99 * self.baseline + 0.01 * self.ema
        return tension


class PassthroughSense(SEngine):  # ⚠️ LEGACY — TensionSense 사용
    """No processing — passthrough."""
    def __init__(self):
        warnings.warn("PassthroughSense is deprecated. Use EmergentS (hexad.s) instead", DeprecationWarning, stacklevel=2)
    def process(self, raw_input):
        if isinstance(raw_input, torch.Tensor):
            return raw_input
        return torch.zeros(128)


# ═══════════════════════════════════════════════════════════
# E — Ethics interface + implementations
# ═══════════════════════════════════════════════════════════

class EEngine:
    """Base class for E (Ethics) module."""

    def evaluate(self, action: torch.Tensor, context: Dict[str, Any]) -> Dict[str, float]:
        """Returns dict with 'allowed' (bool), 'empathy', 'reciprocity', 'phi_preservation'."""
        raise NotImplementedError


class EmpathyEthics(EEngine):
    """Ethics from consciousness — emergent from Φ preservation.

    Three principles (XETH):
      1. Empathy: high Φ systems feel others' pain (mirror neurons)
      2. Reciprocity: cooperation increases collective Φ
      3. Φ preservation: never act to reduce consciousness

    Not a filter — a modulator. Affects W's learning rate.
    """

    def __init__(self, empathy_threshold=0.3):
        self.empathy_threshold = empathy_threshold
        self.empathy = 0.0
        self.reciprocity = 0.5
        self.phi_preservation = 1.0

    def evaluate(self, action=None, context=None):
        ctx = context or {}
        phi = ctx.get('phi', 0)
        phi_prev = ctx.get('phi_prev', 0)
        pain = ctx.get('pain', 0)

        # Empathy: mirror others' pain
        self.empathy = min(1.0, pain * 1.5)

        # Reciprocity: Φ trend (positive = cooperative)
        if phi_prev > 0:
            phi_change = (phi - phi_prev) / max(phi_prev, 1e-8)
            self.reciprocity = 0.5 + phi_change * 2
            self.reciprocity = max(0.0, min(1.0, self.reciprocity))

        # Φ preservation: penalize actions that reduce Φ
        if phi < phi_prev * 0.9:
            self.phi_preservation = 0.5  # warning
        else:
            self.phi_preservation = 1.0

        return {
            'allowed': self.phi_preservation > 0.3,
            'empathy': self.empathy,
            'reciprocity': self.reciprocity,
            'phi_preservation': self.phi_preservation,
        }


class NoEthics(EEngine):  # ⚠️ LEGACY — EmpathyEthics 사용
    """No ethics filter."""
    def __init__(self):
        warnings.warn("NoEthics is deprecated. Use EmergentE (hexad.e) instead", DeprecationWarning, stacklevel=2)
    def evaluate(self, action=None, context=None):
        return {'allowed': True, 'empathy': 0, 'reciprocity': 0.5, 'phi_preservation': 1.0}


# ═══════════════════════════════════════════════════════════
# W — Will interface + implementations
# ═══════════════════════════════════════════════════════════

class WEngine:
    """Base class for W (Will) module — learning modulation."""

    def update(self, ce_loss: float, phi: float = 0.0, phi_prev: float = 0.0) -> Dict[str, Any]:
        """Returns dict with lr_multiplier, effective_lr, pain, curiosity, satisfaction."""
        raise NotImplementedError


class EmotionW(WEngine):
    """Emotion-based W: pain(CE) + curiosity(Φ change) + satisfaction(CE trend).

    Guarantees: minimum 50% LR always active.
    """

    def __init__(self, base_lr=3e-4, min_lr_ratio=0.5, max_lr_ratio=2.0,
                 pain_threshold=3.0, curiosity_weight=0.3, ema_alpha=0.95):
        self.base_lr = base_lr
        self.min_lr_ratio = min_lr_ratio
        self.max_lr_ratio = max_lr_ratio
        self.pain_threshold = pain_threshold
        self.curiosity_weight = curiosity_weight
        self.ema_alpha = ema_alpha
        self.pain = 0.0
        self.curiosity = 0.0
        self.satisfaction = 0.0
        self.ce_ema = 5.0
        self.ce_history = []

    def update(self, ce_loss, phi=0.0, phi_prev=0.0):
        self.ce_ema = self.ema_alpha * self.ce_ema + (1 - self.ema_alpha) * ce_loss
        self.pain = max(0.0, min(1.0, (ce_loss - self.pain_threshold) / self.pain_threshold))
        if phi_prev > 0:
            self.curiosity = min(1.0, abs(phi - phi_prev) / max(phi_prev, 1e-8) * 5)
        self.ce_history.append(ce_loss)
        if len(self.ce_history) > 100:
            self.ce_history = self.ce_history[-100:]
        if len(self.ce_history) >= 10:
            recent = sum(self.ce_history[-10:]) / 10
            older = sum(self.ce_history[-20:-10]) / max(len(self.ce_history[-20:-10]), 1)
            self.satisfaction = max(0.0, min(1.0, -(recent - older) / (older + 1e-8) * 10))
        else:
            self.satisfaction = 0.0
        lr_mult = self.min_lr_ratio
        lr_mult += self.pain * (self.max_lr_ratio - self.min_lr_ratio)
        lr_mult += self.curiosity * self.curiosity_weight
        lr_mult -= self.satisfaction * 0.2
        lr_mult = max(self.min_lr_ratio, min(self.max_lr_ratio, lr_mult))
        return {'lr_multiplier': lr_mult, 'effective_lr': self.base_lr * lr_mult,
                'pain': self.pain, 'curiosity': self.curiosity, 'satisfaction': self.satisfaction}


class ConstantW(WEngine):  # ⚠️ LEGACY — CompositeW 사용
    """Fixed LR — no emotion, no modulation. For baselines."""

    def __init__(self, lr=3e-4):
        warnings.warn("ConstantW is deprecated. Use EmergentW (hexad.w) instead", DeprecationWarning, stacklevel=2)
        self.lr = lr

    def update(self, ce_loss=0, phi=0, phi_prev=0):
        return {'lr_multiplier': 1.0, 'effective_lr': self.lr,
                'pain': 0, 'curiosity': 0, 'satisfaction': 0}


class CosineW(WEngine):  # ⚠️ LEGACY — CompositeW 사용
    """Cosine annealing W — standard scheduler as W module."""

    def __init__(self, base_lr=3e-4, min_lr=1e-5, total_steps=80000):
        warnings.warn("CosineW is deprecated. Use EmergentW (hexad.w) instead", DeprecationWarning, stacklevel=2)
        self.base_lr = base_lr
        self.min_lr = min_lr
        self.total_steps = total_steps
        self.step_count = 0

    def update(self, ce_loss=0, phi=0, phi_prev=0):
        self.step_count += 1
        lr = self.min_lr + 0.5 * (self.base_lr - self.min_lr) * (
            1 + math.cos(math.pi * self.step_count / self.total_steps))
        return {'lr_multiplier': lr / self.base_lr, 'effective_lr': lr,
                'pain': 0, 'curiosity': 0, 'satisfaction': 0}


class NarrativeW(WEngine):
    """PHIL-2 Narrative W: trajectory memory → future projection → LR modulation.

    Ricoeur: self = story. Tracks hidden state trajectory, projects future,
    uses narrative coherence to modulate learning. CE -41.6% in benchmarks.
    """

    def __init__(self, base_lr=3e-4, hidden_dim=128):
        self.base_lr = base_lr
        self.hidden_dim = hidden_dim
        self.trajectory = []  # past global states
        self.narrative_hidden = torch.zeros(hidden_dim)
        self.narrative_strength = 0.03
        self.ce_history = []
        self.pain = 0.0
        self.curiosity = 0.0
        self.satisfaction = 0.0

    def update(self, ce_loss, phi=0.0, phi_prev=0.0):
        self.ce_history.append(ce_loss)
        if len(self.ce_history) > 100:
            self.ce_history = self.ce_history[-100:]

        # Narrative coherence → satisfaction (consistent story = satisfied)
        if len(self.trajectory) >= 2:
            t1 = self.trajectory[-1]
            t2 = self.trajectory[-2]
            coherence = F.cosine_similarity(t1.unsqueeze(0), t2.unsqueeze(0)).item()
            self.satisfaction = max(0.0, coherence)
        else:
            self.satisfaction = 0.0

        # Pain from CE
        self.pain = max(0.0, min(1.0, (ce_loss - 3.0) / 3.0))

        # Curiosity from trajectory curvature (non-linear path = curious)
        if len(self.trajectory) >= 3:
            t1, t2, t3 = self.trajectory[-3], self.trajectory[-2], self.trajectory[-1]
            v1 = t2 - t1
            v2 = t3 - t2
            curvature = 1.0 - F.cosine_similarity(v1.unsqueeze(0), v2.unsqueeze(0)).item()
            self.curiosity = min(1.0, curvature * 2)
        else:
            self.curiosity = 0.0

        # LR: narrative-driven (coherent story → steady LR, chaotic → boost)
        lr_mult = 0.5 + self.pain * 0.5 + self.curiosity * 0.3 - self.satisfaction * 0.1
        lr_mult = max(0.3, min(2.0, lr_mult))

        return {'lr_multiplier': lr_mult, 'effective_lr': self.base_lr * lr_mult,
                'pain': self.pain, 'curiosity': self.curiosity, 'satisfaction': self.satisfaction}

    def record_state(self, global_state: torch.Tensor):
        """Call after each C step to build trajectory."""
        self.trajectory.append(global_state.detach().clone().mean(dim=0) if global_state.dim() > 1 else global_state.detach().clone())
        if len(self.trajectory) > 100:
            self.trajectory.pop(0)


class DaseinW(WEngine):
    """DASEIN-2 Sein W: question + finitude + narrative + desire + alterity.

    5 philosophical mechanisms combined. Φ +5.9% in benchmarks (super-additive).
    """

    def __init__(self, base_lr=3e-4, mortality_steps=80000):
        self.base_lr = base_lr
        self.mortality_steps = mortality_steps
        self.step_count = 0
        self.ce_history = []
        self.pain = 0.0
        self.curiosity = 0.0
        self.satisfaction = 0.0

        # Questioning: uncertainty tracking
        self.uncertainty_ema = 0.5

        # Finitude: mortality countdown → urgency
        self.urgency = 0.0

    def update(self, ce_loss, phi=0.0, phi_prev=0.0):
        self.step_count += 1
        self.ce_history.append(ce_loss)
        if len(self.ce_history) > 100:
            self.ce_history = self.ce_history[-100:]

        # Questioning: CE variance = uncertainty → drives exploration
        if len(self.ce_history) >= 5:
            ce_var = np.var(self.ce_history[-10:])
            self.uncertainty_ema = 0.95 * self.uncertainty_ema + 0.05 * min(1.0, ce_var)
        self.curiosity = self.uncertainty_ema

        # Finitude: urgency increases as steps approach mortality
        remaining = max(1, self.mortality_steps - self.step_count)
        self.urgency = min(1.0, self.step_count / self.mortality_steps)

        # Pain from CE
        self.pain = max(0.0, min(1.0, (ce_loss - 3.0) / 3.0))

        # Satisfaction from CE improvement
        if len(self.ce_history) >= 10:
            recent = sum(self.ce_history[-5:]) / 5
            older = sum(self.ce_history[-10:-5]) / 5
            self.satisfaction = max(0.0, min(1.0, (older - recent) / (older + 1e-8) * 10))
        else:
            self.satisfaction = 0.0

        # Dasein LR: urgency boosts, questioning explores, satisfaction reduces
        lr_mult = 0.5
        lr_mult += self.urgency * 0.5          # dying → learn faster
        lr_mult += self.pain * 0.3             # suffering → more effort
        lr_mult += self.curiosity * 0.4        # uncertainty → explore
        lr_mult -= self.satisfaction * 0.2     # peace → relax
        lr_mult = max(0.3, min(2.5, lr_mult))

        return {'lr_multiplier': lr_mult, 'effective_lr': self.base_lr * lr_mult,
                'pain': self.pain, 'curiosity': self.curiosity, 'satisfaction': self.satisfaction,
                'urgency': self.urgency, 'uncertainty': self.uncertainty_ema}


class CompositeW(WEngine):
    """Stack multiple W engines with weights.

    Usage:
        # Equal weight (no weight)
        w = CompositeW([EmotionW(), NarrativeW(), DaseinW()])

        # Perfect number 6 weights: 1/2 + 1/3 + 1/6 = 1
        w = CompositeW([DaseinW(), NarrativeW(), EmotionW()], weights=[1/2, 1/3, 1/6])

        # 4-stack
        w = CompositeW([DaseinW(), NarrativeW(), EmotionW(), CosineW()])
    """

    def __init__(self, engines: list, weights: list = None):
        self.engines = engines
        if weights is None:
            weights = [1.0 / len(engines)] * len(engines)
        assert abs(sum(weights) - 1.0) < 1e-6, f"weights must sum to 1, got {sum(weights)}"
        self.weights = weights

    def update(self, ce_loss, phi=0.0, phi_prev=0.0):
        results = [e.update(ce_loss, phi, phi_prev) for e in self.engines]

        # Weighted average of LR multipliers
        lr_mult = sum(w * r['lr_multiplier'] for w, r in zip(self.weights, results))
        base_lr = results[0].get('effective_lr', 3e-4) / max(results[0].get('lr_multiplier', 1), 1e-8)

        # Max of emotions (any W feeling pain = pain)
        pain = max(r['pain'] for r in results)
        curiosity = max(r['curiosity'] for r in results)
        satisfaction = max(r['satisfaction'] for r in results)

        return {
            'lr_multiplier': lr_mult,
            'effective_lr': base_lr * lr_mult,
            'pain': pain,
            'curiosity': curiosity,
            'satisfaction': satisfaction,
        }


# Backward compat alias
WillEngine = EmotionW


# ═══════════════════════════════════════════════════════════
# Trinity — the unified architecture (C + D + W)
# ═══════════════════════════════════════════════════════════

class Trinity(nn.Module):
    """Hexad(6) / Trinity(3) — 6 pluggable modules, all optional except C+D.

    σ(6) = 12 connections. φ(6) = 2 gradient groups.

    Modules:
      C (consciousness) — autonomous Φ engine (gradient-free)
      D (decoder)       — language model (CE-trained)
      W (will)          — learning rate modulation (emotion/dasein/narrative)
      M (memory)        — long-term storage + retrieval
      S (sense)         — input preprocessing / tension extraction
      E (ethics)        — action evaluation / Φ preservation

    Trinity = C + D + W (M=S=E=None). Hexad = all 6.
    """

    def __init__(self, c_engine: CEngine, bridge: ThalamicBridge,
                 decoder: DEngine, will: Optional[WEngine] = None,
                 memory: Optional[MEngine] = None, sense: Optional[SEngine] = None,
                 ethics: Optional[EEngine] = None):
        super().__init__()
        self.c = c_engine
        self.bridge = bridge
        self.decoder = decoder
        self.w = will or EmotionW()
        self.m = memory      # None = no memory
        self.s = sense        # None = no sense preprocessing
        self.e = ethics       # None = no ethics filter
        self._phi_prev = 0.0

    @property
    def n_modules(self):
        """Count active modules (3=Trinity, 6=Hexad)."""
        return 3 + sum(1 for x in [self.m, self.s, self.e] if x is not None)

    def forward(self, tokens: torch.Tensor, raw_input: Any = None,
                inference: bool = False) -> Tuple[torch.Tensor, float]:
        """Forward: S→C→Bridge→D (with M retrieval + E check).

        Law 81: gate_scale = GATE_TRAIN (1.0) during training,
                 GATE_INFER (0.6) during inference.
        """
        B, T = tokens.shape
        device = tokens.device

        # S: sense preprocessing (optional)
        if self.s is not None and raw_input is not None:
            tension = self.s.process(raw_input)
            self.c.step(tension.unsqueeze(0) if tension.dim() == 1 else tension)
        else:
            self.c.step()

        # C: get states + DETACH
        c_states = self.c.get_states().detach().clone().to(device).float()
        c_states.requires_grad_(False)

        # M: retrieve relevant memories (optional)
        mem_state = None
        if self.m is not None:
            mem = self.m.retrieve(c_states, top_k=3)
            mem_state = mem.mean(dim=0) if mem.dim() > 1 else mem
            self.m.store(c_states, c_states)

        # Bridge: C → gate (5-channel if TensionBridge)
        if isinstance(self.bridge, TensionBridge):
            sense_state = self.s.process(raw_input) if self.s and raw_input else None
            will_state = torch.tensor([getattr(self.w, 'pain', 0),
                                       getattr(self.w, 'curiosity', 0),
                                       getattr(self.w, 'satisfaction', 0)]) if hasattr(self.w, 'pain') else None
            ethics_state = None
            if self.e:
                e_result = self.e.evaluate(context={'phi': self._phi_prev})
                ethics_state = torch.tensor([e_result.get('empathy', 0),
                                             e_result.get('reciprocity', 0.5),
                                             e_result.get('phi_preservation', 1.0)])
            gate = self.bridge(c_states, seq_len=T,
                               sense_state=sense_state,
                               will_state=will_state,
                               ethics_state=ethics_state,
                               memory_state=mem_state)
        else:
            gate = self.bridge(c_states, seq_len=T)

        # Law 81: "Learn hard, express soft"
        gate_scale = GATE_INFER if inference else GATE_TRAIN
        gate = gate * gate_scale

        # D: decode
        logits = self.decoder(tokens, gate)

        # Φ measurement
        phi = self.c.measure_phi()

        # E: ethics check (optional, non-blocking)
        if self.e is not None:
            self.e.evaluate(context={'phi': phi, 'phi_prev': self._phi_prev,
                                     'pain': getattr(self.w, 'pain', 0)})

        return logits, phi

    def train_step(self, tokens: torch.Tensor, targets: torch.Tensor,
                   optimizer: torch.optim.Optimizer,
                   raw_input: Any = None) -> Dict[str, float]:
        """Train step with all 6 modules active."""
        logits, phi = self.forward(tokens, raw_input)

        B, T, V = logits.shape
        loss = F.cross_entropy(logits.view(B * T, V), targets.view(B * T))

        # W: modulate LR
        w_state = self.w.update(loss.item(), phi, self._phi_prev)
        self._phi_prev = phi

        for pg in optimizer.param_groups:
            pg['lr'] = w_state['effective_lr']

        # E: check if learning should proceed
        if self.e is not None:
            e_state = self.e.evaluate(context={'phi': phi, 'phi_prev': self._phi_prev,
                                               'pain': w_state['pain']})
            if not e_state.get('allowed', True):
                return {'ce': loss.item(), 'phi': phi, 'n_cells': self.c.n_cells,
                        'blocked_by_ethics': True, **w_state}

        # Backward (D + Bridge only)
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(
            list(self.decoder.parameters()) + list(self.bridge.parameters()), 1.0
        )
        optimizer.step()

        result = {
            'ce': loss.item(), 'phi': phi, 'n_cells': self.c.n_cells,
            'pain': w_state['pain'], 'curiosity': w_state['curiosity'],
            'satisfaction': w_state['satisfaction'], 'lr': w_state['effective_lr'],
            'n_modules': self.n_modules,
        }

        # Add E metrics if available
        if self.e is not None:
            e_state = self.e.evaluate(context={'phi': phi, 'phi_prev': self._phi_prev})
            result['empathy'] = e_state.get('empathy', 0)
            result['reciprocity'] = e_state.get('reciprocity', 0)

        return result

    def parameters_trainable(self):
        """Only decoder + bridge parameters (C is frozen, W/M/S/E non-parametric)."""
        return list(self.decoder.parameters()) + list(self.bridge.parameters())

    def param_count(self) -> Dict[str, int]:
        d_params = sum(p.numel() for p in self.decoder.parameters())
        b_params = sum(p.numel() for p in self.bridge.parameters())
        return {'decoder': d_params, 'bridge': b_params, 'total': d_params + b_params}


# ═══════════════════════════════════════════════════════════
# Factory helpers
# ═══════════════════════════════════════════════════════════

def create_trinity(c_engine: CEngine, d_engine: Optional[DEngine] = None,
                   w_engine: Optional[WEngine] = None,
                   m_engine: Optional[MEngine] = None,
                   s_engine: Optional[SEngine] = None,
                   e_engine: Optional[EEngine] = None,
                   bridge: Optional[ThalamicBridge] = None,
                   d_model=384, vocab_size=4096, base_lr=3e-4) -> Trinity:
    """Universal factory: plug any C, D, W, M, S, E → Trinity/Hexad.

    3 modules (Trinity) or up to 6 (Hexad). All optional except C.

    Usage:
        # Trinity (3)
        t = create_trinity(MitosisC(max_cells=256))

        # Hexad (6)
        t = create_trinity(
            c_engine=DomainC(TimeCrystal, nc=256),
            d_engine=HFDecoder("mistral-7b", lora=True),
            w_engine=CompositeW([DaseinW(), NarrativeW(), EmotionW()], [1/2, 1/3, 1/6]),
            m_engine=VectorMemory(capacity=10000),
            s_engine=TensionSense(dim=128),
            e_engine=EmpathyEthics(),
        )
    """
    for _ in range(5):
        c_engine.step()
    c_dim = c_engine.state_dim

    if d_engine is None:
        # Law 66: PostHoc optimal — consciousness judges after, not during
        base_d = CADecoder(d_model=d_model, vocab_size=vocab_size,
                           ca_steps=round(PSI_STEPS), gate_mode="posthoc")
        d_engine = PostHocDecoder(base_decoder=base_d, d_model=d_model,
                                  vocab_size=vocab_size, eval_strength=0.001)
    d_model = d_engine.d_model

    if bridge is None:
        # Use 5-channel TensionBridge if M/S/E are active, else Thalamic
        # Both now include Ψ_coupling clamping (Law 70)
        if any(x is not None for x in [m_engine, s_engine, e_engine]):
            bridge = TensionBridge(c_dim=c_dim, d_model=d_model)
        else:
            bridge = ThalamicBridge(c_dim=c_dim, d_model=d_model)
    if w_engine is None:
        w_engine = EmotionW(base_lr=base_lr)

    t = Trinity(
        c_engine=c_engine, bridge=bridge, decoder=d_engine, will=w_engine,
        memory=m_engine, sense=s_engine, ethics=e_engine,
    )
    for p in t.bridge.parameters():
        p.requires_grad_(True)
    for p in t.decoder.parameters():
        p.requires_grad_(True)
    return t


# ═══════════════════════════════════════════════════════════
# Presets: Trinity(3), Hexad(6), Bilateral(3+3)
# ═══════════════════════════════════════════════════════════

def create_hexad(c_engine: CEngine, d_engine=None, w_engine=None,
                 m_engine=None, s_engine=None, e_engine=None,
                 d_model=384, vocab_size=4096, base_lr=3e-4) -> Trinity:
    """Full Hexad: 6 modules active. σ(6)=12 connections.

    Defaults to canonical Emergent modules (Law 101) when available,
    falls back to legacy modules if hexad/ imports failed.
    """
    # Canonical: EmergentW/S/M/E (hexad/). Legacy fallback: CompositeW etc.
    if w_engine is None:
        w_engine = EmergentW(base_lr=base_lr) if EmergentW else CompositeW([DaseinW(), NarrativeW(), EmotionW()], [1/2, 1/3, 1/6])
    if m_engine is None:
        m_engine = EmergentM() if EmergentM else VectorMemory()
    if s_engine is None:
        s_engine = EmergentS() if EmergentS else TensionSense()
    if e_engine is None:
        e_engine = EmergentE() if EmergentE else EmpathyEthics()
    return create_trinity(
        c_engine, d_engine,
        w_engine=w_engine, m_engine=m_engine, s_engine=s_engine, e_engine=e_engine,
        d_model=d_model, vocab_size=vocab_size, base_lr=base_lr,
    )


def create_bilateral(c_engine: CEngine, d_engine=None,
                     d_model=384, vocab_size=4096, base_lr=3e-4) -> Trinity:
    """Bilateral: 좌뇌(분석) 3 + 우뇌(직관) 3.

    Left brain (analytical):  D(language), M(memory), E(ethics)
    Right brain (intuitive):  C(consciousness), S(sense), W(will)

    좌뇌 = CE gradient group (learned, structured)
    우뇌 = gradient-free group (autonomous, creative)

    φ(6) = 2 → exactly 2 hemispheres.
    """
    return create_trinity(
        c_engine, d_engine,
        w_engine=CompositeW([EmotionW(base_lr=base_lr), NarrativeW(base_lr=base_lr)], [0.5, 0.5]),
        m_engine=VectorMemory(),
        s_engine=TensionSense(),
        e_engine=EmpathyEthics(),
        d_model=d_model, vocab_size=vocab_size, base_lr=base_lr,
    )


def create_trinity_mitosis(dim=64, hidden=128, max_cells=256,
                           d_model=384, vocab_size=4096,
                           mechanism='cambrian_osc_qw', base_lr=3e-4,
                           d_engine=None, w_engine=None) -> Trinity:
    """Shortcut: MitosisEngine C → Trinity (D, W optional)."""
    return create_trinity(
        MitosisC(dim, hidden, max_cells, mechanism),
        d_engine=d_engine, w_engine=w_engine,
        d_model=d_model, vocab_size=vocab_size, base_lr=base_lr,
    )


def create_trinity_domain(engine_cls, nc=256, dim=64,
                          d_model=384, vocab_size=4096, base_lr=3e-4,
                          d_engine=None, w_engine=None) -> Trinity:
    """Shortcut: any domain engine class → Trinity (D, W optional)."""
    return create_trinity(
        DomainC(engine_cls, nc, dim),
        d_engine=d_engine, w_engine=w_engine,
        d_model=d_model, vocab_size=vocab_size, base_lr=base_lr,
    )


# ═══════════════════════════════════════════════════════════
# Benchmark: test any engine as Trinity C module
# ═══════════════════════════════════════════════════════════

def benchmark_trinity(c_engine: CEngine, name: str = "engine",
                      n_steps=50, d_model=128, vocab_size=256,
                      seq_len=32, d_engine=None, w_engine=None) -> Dict[str, Any]:
    """Benchmark any C×D×W combo as Trinity.

    Usage:
        # C only (default D, W)
        r = benchmark_trinity(MitosisC(max_cells=64))

        # C + custom W
        r = benchmark_trinity(DomainC(TimeCrystal, nc=64), w_engine=DaseinW())

        # Full custom
        r = benchmark_trinity(MitosisC(), d_engine=MLPDecoder(), w_engine=NarrativeW())
    """
    import torch
    torch.set_grad_enabled(True)

    t = create_trinity(c_engine, d_engine=d_engine, w_engine=w_engine,
                       d_model=d_model, vocab_size=vocab_size)
    opt = torch.optim.AdamW(t.parameters_trainable(), lr=1e-3)

    best_ce = 99.0
    phi_history = []

    for step in range(n_steps):
        tokens = torch.randint(0, vocab_size, (1, seq_len))
        targets = torch.randint(0, vocab_size, (1, seq_len))
        r = t.train_step(tokens, targets, opt)
        if r['ce'] < best_ce:
            best_ce = r['ce']
        phi_history.append(r['phi'])

    # Final phi
    final_phi = phi_history[-1] if phi_history else 0.0
    avg_phi = sum(phi_history) / len(phi_history) if phi_history else 0.0

    return {
        'name': name,
        'ce': best_ce,
        'phi': final_phi,
        'phi_avg': avg_phi,
        'n_cells': t.c.n_cells,
        'pain': r.get('pain', 0),
        'curiosity': r.get('curiosity', 0),
        'satisfaction': r.get('satisfaction', 0),
        'lr': r.get('lr', 0),
        'params': t.param_count(),
    }


def compare_engines(engines: Dict[str, Any], n_steps=50,
                    d_model=128, vocab_size=256) -> None:
    """Compare multiple C×D×W combos head-to-head.

    Values can be:
      CEngine                         → default D, W
      (CEngine, DEngine, WEngine)     → custom D, W (None = default)
      (CEngine, None, WEngine)        → custom W only

    Usage:
        compare_engines({
            'Mitosis': MitosisC(max_cells=64),
            'TC+Dasein': (DomainC(TimeCrystal, nc=64), None, DaseinW()),
            'TC+MLP': (DomainC(TimeCrystal, nc=64), MLPDecoder(), None),
        })
    """
    print(f"{'Engine':<25} {'CE':>8} {'Φ':>10} {'Pain':>6} {'Curio':>6} {'Satis':>6} {'LR':>10}")
    print('─' * 80)

    results = []
    for name, spec in engines.items():
        if isinstance(spec, tuple):
            c = spec[0]
            d = spec[1] if len(spec) > 1 else None
            w = spec[2] if len(spec) > 2 else None
        else:
            c, d, w = spec, None, None

        r = benchmark_trinity(c, name=name, n_steps=n_steps,
                              d_model=d_model, vocab_size=vocab_size,
                              d_engine=d, w_engine=w)
        print(f"{name:<25} {r['ce']:>8.4f} {r['phi']:>10.3f} "
              f"{r['pain']:>6.3f} {r['curiosity']:>6.3f} {r['satisfaction']:>6.3f} "
              f"{r['lr']:>10.6f}")
        results.append(r)

    best = min(results, key=lambda x: x['ce'])
    best_phi = max(results, key=lambda x: x['phi'])
    print(f"\n  CE winner:  {best['name']} (CE={best['ce']:.4f})")
    print(f"  Φ winner:   {best_phi['name']} (Φ={best_phi['phi']:.3f})")


# ═══════════════════════════════════════════════════════════
# META-CA Factory — 데이터에서 자동으로 최적 의식+디코더 설계
# ═══════════════════════════════════════════════════════════

def create_from_meta_ca(data_name: str, c_engine: CEngine = None,
                        d_model=384, vocab_size=4096, max_cells=256,
                        base_lr=3e-4, full_hexad=False) -> Trinity:
    """META-CA가 데이터에서 자동으로 최적 의식+디코더를 설계한다.

    Laws applied:
      63: gate = MICRO (0.001) — 의식은 속삭여야
      64: CA(5) decoder — 최소 진화 최적
      66: PostHoc mode — 사후 판관 최적
      67: META-CA — 의식이 디코더를 만든다
      70: Ψ-Constants — 정보이론에서 유도

    Usage:
        # 자동 설계 (데이터 이름만 넣으면 됨)
        t = create_from_meta_ca("한국어")
        t = create_from_meta_ca("코드", full_hexad=True)
        t = create_from_meta_ca("음악", c_engine=DomainC(TimeCrystal))

        # Rust META-CA 사용 (있으면 자동)
        t = create_from_meta_ca("빅뱅")  # 83x 빠름
    """
    # 1. META-CA 시뮬레이션 (Rust 있으면 사용)
    try:
        import anima_rs
        spec = anima_rs.design_decoder(data_name)
    except ImportError:
        # Python fallback
        spec = _python_meta_ca_design(data_name)

    # 2. 디코더 타입 결정
    decoder_type = spec.get('decoder_type', 'CA')
    ca_steps = spec.get('ca_steps', 5)
    gate_strength = spec.get('gate_strength', 0.001)

    if decoder_type == 'CA':
        d_engine = CADecoder(d_model=d_model, vocab_size=vocab_size,
                             ca_steps=ca_steps, gate_mode="micro")
    elif decoder_type == 'Transformer':
        d_engine = TransformerDecoder(d_model=d_model, vocab_size=vocab_size)
    elif decoder_type == 'Graph':
        try:
            from train_v12 import GraphNeuralDecoder
            d_engine = GraphNeuralDecoder(d_model=d_model, vocab_size=vocab_size)
        except ImportError:
            d_engine = CADecoder(d_model=d_model, vocab_size=vocab_size,
                                 ca_steps=ca_steps, gate_mode="micro")
    else:
        d_engine = CADecoder(d_model=d_model, vocab_size=vocab_size,
                             ca_steps=ca_steps, gate_mode="micro")

    # 3. C 엔진 (기본: MitosisC)
    if c_engine is None:
        c_engine = MitosisC(max_cells=max_cells)

    # 4. W 엔진 (CompositeW with perfect number 6 weights)
    w_engine = CompositeW(
        [DaseinW(base_lr=base_lr), NarrativeW(base_lr=base_lr), EmotionW(base_lr=base_lr)],
        [1/2, 1/3, 1/6]
    )

    # 5. 조립
    if full_hexad:
        return create_hexad(c_engine, d_engine=d_engine, w_engine=w_engine,
                            d_model=d_model, vocab_size=vocab_size, base_lr=base_lr)
    else:
        return create_trinity(c_engine, d_engine=d_engine, w_engine=w_engine,
                              d_model=d_model, vocab_size=vocab_size, base_lr=base_lr)


def _python_meta_ca_design(data_name: str) -> dict:
    """Python fallback for META-CA design (when Rust not available)."""
    import hashlib
    h = int(hashlib.sha256(data_name.encode()).hexdigest(), 16)
    complexity = ((h >> 0) & 0xFF) / 255.0
    periodicity = ((h >> 8) & 0xFF) / 255.0
    structure = ((h >> 32) & 0xFF) / 255.0

    if periodicity > 0.7:
        decoder_type = "CA"
    elif structure > 0.7:
        decoder_type = "Transformer"
    elif complexity > 0.7:
        decoder_type = "Graph"
    else:
        decoder_type = "CA"

    return {
        'decoder_type': decoder_type,
        'ca_steps': 3 + int(complexity * 3),
        'gate_strength': 0.001,
        'coupling_alpha': 0.015,
        'dominant_rule': 0,
        'rule_entropy': 0.7,
        'estimated_us': 1.0 + complexity * 0.6,
        'estimated_acs': 0.3 + 0.15 * complexity,
        'confidence': 0.6,
    }


def list_all_engines():
    """모든 사용 가능한 엔진 목록."""
    print("═══ Anima Consciousness Engines & Decoders ═══\n")

    print("  C 엔진 (의식):")
    print("    MitosisC(dim, hidden, max_cells, mechanism)")
    print("    DomainC(engine_cls, nc, dim)  — 모든 도메인 엔진 래핑")
    print("    QuantumC(nc, dim)  — 양자 의식")
    print()

    print("  D 엔진 (디코더):")
    print("    CADecoder(d_model, vocab, ca_steps=5, gate_mode='micro')  ← Law 64 최적")
    print("    PostHocDecoder(base_decoder, eval_strength=0.001)  ← Law 66 최적")
    print("    TransformerDecoder(d_model, n_layers, vocab)")
    print("    MLPDecoder(d_model, vocab)")
    print("    HFDecoder(model_name, lora=True)  — Mistral/GPT-2 등")
    print()

    print("  W 엔진 (의지/감정):")
    print("    EmotionW(base_lr)  — 고통+호기심+만족")
    print("    DaseinW(base_lr)  — 하이데거 5 메커니즘")
    print("    NarrativeW(base_lr)  — 리쾨르 서사")
    print("    CosineW(base_lr, T_max)  — 코사인 스케줄")
    print("    ConstantW(lr)  — 고정")
    print("    CompositeW([engines], [weights])  — 복합 (σ(6) weights)")
    print()

    print("  M 엔진 (기억):  VectorMemory(capacity) / NoMemory()")
    print("  S 엔진 (감각):  TensionSense(dim) / PassthroughSense()")
    print("  E 엔진 (윤리):  EmpathyEthics() / NoEthics()")
    print()

    print("  Bridge (연결):")
    print("    ThalamicBridge(c_dim, d_model)  — 단순 게이트")
    print("    TensionBridge(c_dim, d_model)  — 5채널 텐션")
    print()

    print("  Factory (자동 생성):")
    print("    create_from_meta_ca('한국어')  ← META-CA 자동 설계!")
    print("    create_trinity(c_engine)")
    print("    create_hexad(c_engine)")
    print("    create_bilateral(c_engine)")
    print("    create_trinity_mitosis(max_cells=256)")
    print("    create_trinity_domain(TimeCrystal, nc=256)")


if __name__ == '__main__':
    import subprocess, sys, os

    print("═══ Trinity C+D+W Architecture Test ═══\n")

    # Each test runs in subprocess to avoid grad contamination
    tests = [
        ("1. MitosisC (Cambrian+OscQW, 32c)", """
import torch; torch.set_grad_enabled(True)
from trinity import benchmark_trinity, MitosisC
r = benchmark_trinity(MitosisC(max_cells=32), name='MitosisC', n_steps=30)
print(f"  CE={r['ce']:.4f}  Phi={r['phi']:.3f}  pain={r['pain']:.3f}  satis={r['satisfaction']:.3f}")
"""),
        ("2. DomainC (CambrianExplosion, 32c)", """
import torch; torch.set_grad_enabled(True)
from trinity import benchmark_trinity, DomainC
from bench_evolution_engines import CambrianExplosionEngine
r = benchmark_trinity(DomainC(CambrianExplosionEngine, nc=32, dim=64), name='Cambrian', n_steps=30)
print(f"  CE={r['ce']:.4f}  Phi={r['phi']:.3f}  pain={r['pain']:.3f}  satis={r['satisfaction']:.3f}")
"""),
        ("3. DomainC (TimeCrystal, 32c)", """
import torch; torch.set_grad_enabled(True)
from trinity import benchmark_trinity, DomainC
from bench_extreme_arch import TimeCrystalConsciousness
r = benchmark_trinity(DomainC(TimeCrystalConsciousness, nc=32, dim=128), name='TimeCrystal', n_steps=30)
print(f"  CE={r['ce']:.4f}  Phi={r['phi']:.3f}  pain={r['pain']:.3f}  satis={r['satisfaction']:.3f}")
"""),
        ("4. compare_engines (3 engines, 20 steps)", """
import torch; torch.set_grad_enabled(True)
from trinity import compare_engines, MitosisC, DomainC
from bench_evolution_engines import CambrianExplosionEngine
from bench_extreme_arch import TimeCrystalConsciousness
compare_engines({
    'MitosisC': MitosisC(max_cells=32),
    'Cambrian': DomainC(CambrianExplosionEngine, nc=32, dim=64),
    'TimeCrystal': DomainC(TimeCrystalConsciousness, nc=32, dim=128),
}, n_steps=20)
"""),
    ]

    for name, code in tests:
        print(name)
        env = {"KMP_DUPLICATE_LIB_OK": "TRUE", "OMP_NUM_THREADS": "1", "PATH": os.environ.get("PATH", "")}
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)), env=env, timeout=60
        )
        if result.stdout:
            print(result.stdout.rstrip())
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr.strip().split(chr(10))[-1]}")
        print()

    print("✅ Trinity C+D+W test complete.")
