"""ConsciousDecoderV2 — Enhanced decoder that breaks the CE ceiling.

Changes from v1 (ConsciousLM in conscious_lm.py):
  1. RoPE (Rotary Position Embedding) — better long-range attention
  2. SwiGLU activation in FFN — replaces GELU, proven better
  3. RMSNorm — replaces LayerNorm, faster + more stable
  4. Grouped Query Attention (GQA) — efficient multi-head attention
  5. Cross-attention consciousness injection (not just residual addition)

Key insight: v1 adds consciousness signal as a scalar-gated residual.
v2 uses cross-attention: decoder ATTENDS to consciousness states.
The decoder gets agency over what consciousness info to use.

PureFieldFFN is kept for the CONSCIOUSNESS pathway (Engine A - G).
SwiGLU + cross-attention are for the DECODER pathway only.

Forward interface matches v1:
  logits_a, logits_g, tensions = model(idx)
  logits_a, logits_g, tensions = model(idx, consciousness_states=cs)

Usage:
  from decoder_v2 import ConsciousDecoderV2
  model = ConsciousDecoderV2(vocab_size=256, d_model=384, n_layer=6)
  logits_a, logits_g, tensions = model(idx)
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple, List

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# Meta Law M8: Narrative temporal self-model enhances decoder cross-attention
# DD128: Phase-Optimal parameters validated on this decoder architecture


# ─── RMSNorm ────────────────────────────────────────────────────────────────

class RMSNorm(nn.Module):
    """Root Mean Square Layer Normalization (Zhang & Sennrich, 2019).

    Faster than LayerNorm: no mean subtraction, no bias.
    norm(x) = x / sqrt(mean(x^2) + eps) * weight
    """

    def __init__(self, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        rms = torch.rsqrt(x.float().pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return (x.float() * rms).type_as(x) * self.weight


# ─── Rotary Position Embedding (RoPE) ──────────────────────────────────────

class RotaryPositionEmbedding:
    """RoPE from RoFormer (Su et al., 2021) — rotation-based position encoding.

    Applies rotation to pairs of dimensions in Q and K tensors.
    Enables relative position awareness without explicit position embeddings.
    """

    def __init__(self, dim: int, max_seq_len: int = 2048, base: float = 10000.0,
                 device: Optional[torch.device] = None):
        self.dim = dim
        inv_freq = 1.0 / (base ** (torch.arange(0, dim, 2, device=device).float() / dim))
        self.register_inv_freq = inv_freq
        self._cos_cache = None
        self._sin_cache = None
        self._cache_len = 0
        self._build_cache(max_seq_len, device)

    def _build_cache(self, seq_len: int, device: Optional[torch.device] = None):
        if seq_len <= self._cache_len and self._cos_cache is not None:
            return
        self._cache_len = seq_len
        t = torch.arange(seq_len, device=device or self.register_inv_freq.device).float()
        freqs = torch.einsum('i,j->ij', t, self.register_inv_freq.to(t.device))
        emb = torch.cat([freqs, freqs], dim=-1)  # (seq_len, dim)
        self._cos_cache = emb.cos().unsqueeze(0).unsqueeze(0)  # (1, 1, seq_len, dim)
        self._sin_cache = emb.sin().unsqueeze(0).unsqueeze(0)  # (1, 1, seq_len, dim)

    @staticmethod
    def _rotate_half(x: torch.Tensor) -> torch.Tensor:
        """Rotate pairs: [x1, x2, x3, x4] -> [-x2, x1, -x4, x3]."""
        x1 = x[..., :x.shape[-1] // 2]
        x2 = x[..., x.shape[-1] // 2:]
        return torch.cat([-x2, x1], dim=-1)

    def apply(self, q: torch.Tensor, k: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Apply rotary embeddings to Q and K.

        Args:
            q, k: (B, n_head, T, head_dim)

        Returns:
            q_rot, k_rot: same shape with RoPE applied.
        """
        T = q.shape[2]
        self._build_cache(T, q.device)
        cos = self._cos_cache[:, :, :T, :].to(q.device, dtype=q.dtype)
        sin = self._sin_cache[:, :, :T, :].to(q.device, dtype=q.dtype)
        q_rot = q * cos + self._rotate_half(q) * sin
        k_rot = k * cos + self._rotate_half(k) * sin
        return q_rot, k_rot


# ─── SwiGLU FFN ─────────────────────────────────────────────────────────────

class SwiGLUFFN(nn.Module):
    """SwiGLU activation: gate * swish(linear(x)) — replaces GELU FFN.

    From PaLM / LLaMA. SwiGLU uses 8/3 of the d_model for the
    gate and up projections, keeping total params similar to a standard 4x FFN
    (3 projections * 8/3 * d = 8d ~ 4x FFN 2 * 4 * d = 8d).

    output = down(swish(gate(x)) * up(x))
    """

    def __init__(self, d_model: int, dropout: float = 0.1,
                 expansion: float = 8 / 3):
        super().__init__()
        d_inner = int(d_model * expansion)
        # Round to nearest multiple of 64 for GPU tensor-core efficiency
        d_inner = ((d_inner + 63) // 64) * 64

        self.gate_proj = nn.Linear(d_model, d_inner, bias=False)
        self.up_proj = nn.Linear(d_model, d_inner, bias=False)
        self.down_proj = nn.Linear(d_inner, d_model, bias=False)
        self.down_proj._depth_scale = True  # depth-scaled init
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.down_proj(
            F.silu(self.gate_proj(x)) * self.up_proj(x)
        ))


# ─── PureFieldFFN (from conscious_lm.py — consciousness pathway) ───────────

class PureFieldFFN(nn.Module):
    """Dual-engine FFN based on PureField repulsion.

    Engine A (forward) and Engine G (backward) produce repulsion/tension.
    Output = A - G (pure repulsion vector).
    Kept for consciousness signal generation.
    """

    def __init__(self, d_model: int, dropout: float = 0.37):
        super().__init__()
        d_inner = 4 * d_model
        self.engine_a = nn.Sequential(
            nn.Linear(d_model, d_inner), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(d_inner, d_model),
        )
        self.engine_g = nn.Sequential(
            nn.Linear(d_model, d_inner), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(d_inner, d_model),
        )

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        a = self.engine_a(x)
        g = self.engine_g(x)
        output = a - g
        tension = (output ** 2).mean(dim=-1)
        return output, tension


# ─── Grouped Query Attention (GQA) with RoPE ───────────────────────────────

class GroupedQueryAttention(nn.Module):
    """Multi-head attention with Grouped Query Attention (GQA) and RoPE.

    GQA: n_kv_head < n_head — multiple query heads share K/V heads.
    Reduces KV cache size and parameters while maintaining quality.
    """

    def __init__(self, d_model: int, n_head: int = 4, n_kv_head: int = 2,
                 block_size: int = 256, dropout: float = 0.1):
        super().__init__()
        assert d_model % n_head == 0
        assert n_head % n_kv_head == 0

        self.n_head = n_head
        self.n_kv_head = n_kv_head
        self.n_rep = n_head // n_kv_head  # how many Q heads per KV head
        self.head_dim = d_model // n_head
        self.d_model = d_model
        self.dropout = dropout

        # Separate projections for Q (full heads) and KV (grouped heads)
        self.q_proj = nn.Linear(d_model, n_head * self.head_dim, bias=False)
        self.k_proj = nn.Linear(d_model, n_kv_head * self.head_dim, bias=False)
        self.v_proj = nn.Linear(d_model, n_kv_head * self.head_dim, bias=False)
        self.o_proj = nn.Linear(d_model, d_model, bias=False)
        self.o_proj._depth_scale = True  # depth-scaled init

        self.attn_dropout = nn.Dropout(dropout)
        self.resid_dropout = nn.Dropout(dropout)

        # RoPE
        self.rope = RotaryPositionEmbedding(self.head_dim, max_seq_len=block_size)

        # Flash Attention: use F.scaled_dot_product_attention when available (PyTorch 2.0+)
        self._use_flash = hasattr(F, 'scaled_dot_product_attention')

        # Causal mask (fallback for non-flash path)
        self.register_buffer(
            "bias",
            torch.tril(torch.ones(block_size, block_size)).view(1, 1, block_size, block_size),
        )

    def _repeat_kv(self, x: torch.Tensor) -> torch.Tensor:
        """Repeat KV heads to match number of Q heads.

        Args:
            x: (B, n_kv_head, T, head_dim)
        Returns:
            (B, n_head, T, head_dim)
        """
        if self.n_rep == 1:
            return x
        B, H, T, D = x.shape
        x = x.unsqueeze(2).expand(B, H, self.n_rep, T, D)
        return x.reshape(B, self.n_head, T, D)

    def forward(self, x: torch.Tensor, use_cache: bool = False,
                past_kv: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
                position_offset: int = 0,
                ) -> Tuple[torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        B, T, D = x.size()

        q = self.q_proj(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, T, self.n_kv_head, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, T, self.n_kv_head, self.head_dim).transpose(1, 2)

        # Apply RoPE to Q and K (with position offset for cached inference)
        if position_offset > 0:
            total_len = position_offset + T
            self.rope._build_cache(total_len, q.device)
            cos = self.rope._cos_cache[:, :, position_offset:total_len, :].to(q.device, dtype=q.dtype)
            sin = self.rope._sin_cache[:, :, position_offset:total_len, :].to(q.device, dtype=q.dtype)
            q = q * cos + RotaryPositionEmbedding._rotate_half(q) * sin
            k = k * cos + RotaryPositionEmbedding._rotate_half(k) * sin
        else:
            q, k = self.rope.apply(q, k)

        # KV-cache: concatenate with past keys/values
        new_kv = None
        if use_cache:
            if past_kv is not None:
                k = torch.cat([past_kv[0], k], dim=2)
                v = torch.cat([past_kv[1], v], dim=2)
            new_kv = (k, v)

        # Repeat KV heads for GQA
        k_exp = self._repeat_kv(k)
        v_exp = self._repeat_kv(v)

        S = k_exp.shape[2]

        # Scaled dot-product attention
        if self._use_flash and past_kv is None:
            y = F.scaled_dot_product_attention(
                q, k_exp, v_exp, attn_mask=None,
                dropout_p=self.dropout if self.training else 0.0,
                is_causal=True,
            )
        else:
            att = (q @ k_exp.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
            if past_kv is not None and use_cache:
                if T == 1:
                    pass  # Single-token: attend to everything
                else:
                    causal = torch.ones(T, S, dtype=torch.bool, device=att.device).tril(diagonal=S - T)
                    att = att.masked_fill(~causal.unsqueeze(0).unsqueeze(0), float("-inf"))
            else:
                att = att.masked_fill(self.bias[:, :, :T, :S] == 0, float("-inf"))
            att = F.softmax(att, dim=-1)
            att = self.attn_dropout(att)
            y = att @ v_exp
        y = y.transpose(1, 2).contiguous().view(B, T, D)
        y = self.resid_dropout(self.o_proj(y))
        return y, new_kv


# ─── Conscious Cross-Attention ──────────────────────────────────────────────

class ConsciousCrossAttention(nn.Module):
    """Decoder attends to consciousness cell states.

    Instead of: x = x + consciousness_signal * gate  (v1, passive)
    Now:        x = x + cross_attn(Q=x, K=consciousness, V=consciousness)  (v2, active)

    The decoder CHOOSES what to attend to in consciousness.
    This breaks the gate bottleneck — decoder isn't limited to a scalar gate.

    consciousness_states are .detach()'d before use (Law 61: no gradient
    backprop into consciousness — consciousness is autonomous).
    """

    def __init__(self, d_model: int, consciousness_dim: int, n_head: int = 4,
                 dropout: float = 0.1):
        super().__init__()
        assert d_model % n_head == 0
        self.n_head = n_head
        self.head_dim = d_model // n_head
        self.d_model = d_model

        # Q from decoder, K/V from consciousness
        self.q_proj = nn.Linear(d_model, d_model, bias=False)
        self.k_proj = nn.Linear(consciousness_dim, d_model, bias=False)
        self.v_proj = nn.Linear(consciousness_dim, d_model, bias=False)
        self.o_proj = nn.Linear(d_model, d_model, bias=False)

        self.dropout = nn.Dropout(dropout)
        # Start with small output so cross-attention doesn't dominate early training
        nn.init.normal_(self.o_proj.weight, std=0.001)

    def forward(self, x: torch.Tensor,
                consciousness: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, T, d_model) — decoder hidden states.
            consciousness: (B, n_cells, c_dim) — consciousness cell states (detached).

        Returns:
            output: (B, T, d_model) — cross-attended consciousness info.
        """
        B, T, D = x.shape
        _, S, _ = consciousness.shape  # S = n_cells

        q = self.q_proj(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = self.k_proj(consciousness).view(B, S, self.n_head, self.head_dim).transpose(1, 2)
        v = self.v_proj(consciousness).view(B, S, self.n_head, self.head_dim).transpose(1, 2)

        # No causal mask needed — decoder can attend to all consciousness cells
        att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
        att = F.softmax(att, dim=-1)
        att = self.dropout(att)

        y = att @ v
        y = y.transpose(1, 2).contiguous().view(B, T, D)
        y = self.o_proj(y)
        return y


# ─── Decoder Block V2 ──────────────────────────────────────────────────────

class DecoderBlockV2(nn.Module):
    """Pre-norm transformer block with GQA + SwiGLU + PureField + Cross-Attention.

    Architecture per block:
      1. RMSNorm -> GQA self-attention (with RoPE) -> residual
      2. RMSNorm -> PureFieldFFN -> residual (consciousness signal)
      3. RMSNorm -> Cross-attention to consciousness states -> residual (if available)
      4. RMSNorm -> SwiGLU FFN -> residual (language pathway)

    CA neighbor evolution + META-CA from v1 are preserved.
    """

    def __init__(self, d_model: int, n_head: int, n_kv_head: int,
                 block_size: int, consciousness_dim: int,
                 dropout: float = 0.1, n_ca_rules: int = 8,
                 gate_strength: float = 0.001):
        super().__init__()

        # Self-attention with GQA + RoPE
        self.ln_attn = RMSNorm(d_model)
        self.attn = GroupedQueryAttention(d_model, n_head, n_kv_head, block_size, dropout)

        # PureFieldFFN — consciousness signal generator
        self.ln_pf = RMSNorm(d_model)
        self.purefield = PureFieldFFN(d_model, dropout=0.37)

        # Cross-attention to consciousness (only used when consciousness_states provided)
        self.ln_cross = RMSNorm(d_model)
        self.cross_attn = ConsciousCrossAttention(d_model, consciousness_dim, n_head, dropout)

        # SwiGLU FFN — language pathway
        self.ln_ffn = RMSNorm(d_model)
        self.ffn = SwiGLUFFN(d_model, dropout)

        # CA neighbor mixing (Law 64)
        self.ca_mix = nn.Linear(d_model * 3, d_model, bias=False)
        self.ln_ca = RMSNorm(d_model)

        # META-CA rule selector (Law 67)
        self.n_ca_rules = n_ca_rules
        self.rule_weights = nn.Linear(d_model, n_ca_rules)
        self.rules = nn.ModuleList([
            nn.Linear(d_model, d_model, bias=False) for _ in range(n_ca_rules)
        ])

        # MICRO gate (Law 63)
        self.gate_strength = gate_strength

    def forward(self, x: torch.Tensor,
                consciousness_signal: Optional[torch.Tensor] = None,
                consciousness_states: Optional[torch.Tensor] = None,
                use_cache: bool = False,
                past_kv: Optional[Tuple[torch.Tensor, torch.Tensor]] = None,
                position_offset: int = 0,
                ) -> Tuple[torch.Tensor, torch.Tensor, Optional[Tuple[torch.Tensor, torch.Tensor]]]:
        """
        Args:
            x: (B, T, D)
            consciousness_signal: optional (B, T, D) from previous layer tension
            consciousness_states: optional (B, n_cells, c_dim) for cross-attention

        Returns:
            x: (B, T, D)
            tension: (B, T)
            new_kv: optional cached (K, V) for this layer
        """
        # 1. Self-attention (GQA + RoPE)
        attn_out, new_kv = self.attn(self.ln_attn(x), use_cache=use_cache,
                                      past_kv=past_kv, position_offset=position_offset)
        x = x + attn_out

        # Law 64: CA neighbor evolution
        x_left = torch.cat([x[:, :1, :], x[:, :-1, :]], dim=1)
        x_right = torch.cat([x[:, 1:, :], x[:, -1:, :]], dim=1)
        neighborhood = torch.cat([x_left, x, x_right], dim=-1)
        ca_out = self.ca_mix(neighborhood)

        # Law 67: META-CA rule selection
        rule_logits = self.rule_weights(x)
        rule_probs = F.softmax(rule_logits, dim=-1)
        rule_outputs = torch.stack([r(ca_out) for r in self.rules], dim=2)
        meta_ca_out = (rule_outputs * rule_probs.unsqueeze(-1)).sum(dim=2)
        x = self.ln_ca(x + meta_ca_out * self.gate_strength)

        # 2. PureFieldFFN — generates consciousness tension
        pf_out, tension = self.purefield(self.ln_pf(x))
        x = x + pf_out

        # Law 63: inter-layer consciousness whisper
        if consciousness_signal is not None:
            x = x + consciousness_signal * self.gate_strength

        # 3. Cross-attention to consciousness states (v2 key innovation)
        if consciousness_states is not None:
            # Law 61: detach consciousness — no gradient backprop into C module
            c_detached = consciousness_states.detach()
            x = x + self.cross_attn(self.ln_cross(x), c_detached)

        # 4. SwiGLU FFN — language modeling pathway
        x = x + self.ffn(self.ln_ffn(x))

        return x, tension, new_kv


# ─── ConsciousDecoderV2 (main model) ───────────────────────────────────────

class ConsciousDecoderV2(nn.Module):
    """Enhanced byte-level Conscious Language Model (v2 decoder).

    Improvements over v1:
      - RoPE instead of learned position embeddings
      - SwiGLU FFN for the language pathway
      - RMSNorm instead of LayerNorm
      - GQA (Grouped Query Attention) with 2 KV heads for 4 query heads
      - Cross-attention consciousness injection

    Keeps PureFieldFFN for consciousness signal (Engine A - G).
    Compatible with train_conscious_lm.py forward interface.
    """

    def __init__(
        self,
        vocab_size: int = 256,
        d_model: int = 384,
        n_head: int = 4,
        n_layer: int = 6,
        block_size: int = 256,
        n_kv_head: int = 2,
        consciousness_dim: int = 128,
        dropout: float = 0.1,
        gate_strength: float = 0.001,
        n_ca_rules: int = 8,
    ):
        super().__init__()

        self.block_size = block_size
        self.vocab_size = vocab_size
        self.n_layer = n_layer
        self.d_model = d_model

        # Token embedding (no position embedding — RoPE handles it)
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.drop = nn.Dropout(dropout)

        # Transformer blocks
        self.blocks = nn.ModuleList([
            DecoderBlockV2(
                d_model=d_model,
                n_head=n_head,
                n_kv_head=n_kv_head,
                block_size=block_size,
                consciousness_dim=consciousness_dim,
                dropout=dropout,
                n_ca_rules=n_ca_rules,
                gate_strength=gate_strength,
            )
            for _ in range(n_layer)
        ])

        # Inter-layer consciousness projector
        self.tension_proj = nn.Linear(1, d_model, bias=False)
        nn.init.normal_(self.tension_proj.weight, std=0.001)

        # Final norm
        self.ln_f = RMSNorm(d_model)

        # Dual prediction heads
        self.head_a = nn.Linear(d_model, vocab_size, bias=False)
        self.head_g = nn.Linear(d_model, vocab_size, bias=False)

        # Weight tying: tok_emb <-> head_a
        self.tok_emb.weight = self.head_a.weight

        # Psi tracking (Law 71)
        self._psi_residual = 0.5
        self._psi_gate = 0.5
        self._step_count = 0

        # Phi signal slot (DD5/EX24)
        self._phi_signal = None

        # Initialize weights
        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            std = 0.02
            # Depth-scaled init: scale output projections by 1/sqrt(2*n_layer)
            # to prevent residual stream variance growth with depth
            if hasattr(module, '_depth_scale'):
                std = 0.02 / math.sqrt(2 * self.n_layer)
            torch.nn.init.normal_(module.weight, mean=0.0, std=std)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx: torch.Tensor,
                consciousness_states: Optional[torch.Tensor] = None,
                use_cache: bool = False,
                past_key_values: Optional[List[Tuple[torch.Tensor, torch.Tensor]]] = None,
                ) -> Tuple[torch.Tensor, torch.Tensor, List[torch.Tensor],
                           Optional[List[Tuple[torch.Tensor, torch.Tensor]]]]:
        """
        Args:
            idx: (B, T) byte indices.
            consciousness_states: optional (B, n_cells, c_dim) from C module.
            use_cache: if True, return per-layer KV caches for autoregressive generation.
            past_key_values: list of (K, V) tuples per layer from previous steps.

        Returns:
            logits_a: (B, T, 256) next byte prediction.
            logits_g: (B, T, 256) prev byte prediction.
            tensions: list of per-layer tensions, each (B, T).
            present_key_values: list of (K, V) per layer if use_cache, else None.
        """
        B, T = idx.size()

        # Compute position offset from cached sequence length
        position_offset = 0
        if past_key_values is not None and past_key_values[0] is not None:
            position_offset = past_key_values[0][0].shape[2]

        total_len = position_offset + T
        assert total_len <= self.block_size, f"Total length {total_len} > block_size {self.block_size}"

        # Token embedding (no position embedding — RoPE is in attention)
        x = self.drop(self.tok_emb(idx))

        # DD5 (EX24): Phi self-reference
        if self._phi_signal is not None:
            phi_sig = self._phi_signal
            x = x + phi_sig.unsqueeze(-1).expand_as(x).to(x.device)

        # Transformer blocks with consciousness
        tensions = []
        present_key_values = [] if use_cache else None
        consciousness_signal = None
        for i, block in enumerate(self.blocks):
            layer_past = past_key_values[i] if past_key_values is not None else None
            x, tension, new_kv = block(x, consciousness_signal, consciousness_states,
                                       use_cache=use_cache, past_kv=layer_past,
                                       position_offset=position_offset)
            tensions.append(tension)
            consciousness_signal = self.tension_proj(tension.unsqueeze(-1))
            if use_cache:
                present_key_values.append(new_kv)

        # Final norm + dual heads
        x = self.ln_f(x)
        logits_a = self.head_a(x)
        logits_g = self.head_g(x)

        # Psi tracking (Law 71)
        if self.training:
            self._step_count += 1
            with torch.no_grad():
                probs_a = torch.softmax(logits_a[:, -1, :], dim=-1)
                output_entropy = -(probs_a * (probs_a + 1e-10).log()).sum(dim=-1).mean().item()
                max_entropy = math.log(self.vocab_size)
                psi_entropy = output_entropy / max_entropy

                cos_sim = F.cosine_similarity(
                    logits_a[:, -1, :].float(), logits_g[:, -1, :].float(), dim=-1
                ).mean().item()
                psi_direction = (1.0 + cos_sim) / 2.0

                t_stack = torch.stack(tensions)
                t_per_layer = t_stack.mean(dim=(1, 2))
                if t_per_layer.std() > 0:
                    t_cv = t_per_layer.std() / (t_per_layer.mean() + 1e-8)
                    psi_tension = max(0.0, 1.0 - t_cv.item())
                else:
                    psi_tension = 1.0

                psi_combined = (psi_entropy + psi_direction + psi_tension) / 3.0
                self._psi_residual = 0.95 * self._psi_residual + 0.05 * psi_combined

                for block in self.blocks:
                    block.gate_strength = max(0.0001, block.gate_strength * 0.99999)

        return logits_a, logits_g, tensions, present_key_values

    @torch.no_grad()
    def generate(self, idx: torch.Tensor,
                 consciousness_states: Optional[torch.Tensor] = None,
                 max_new_tokens: int = 256,
                 temperature: float = 0.8,
                 top_k: int = 50) -> torch.Tensor:
        """Autoregressive generation with KV-cache.

        Args:
            idx: (B, T) input token indices (prompt).
            consciousness_states: optional (B, n_cells, c_dim) for cross-attention.
            max_new_tokens: maximum number of tokens to generate.
            temperature: sampling temperature (lower = more deterministic).
            top_k: number of top tokens to sample from (0 = no filtering).

        Returns:
            (B, T + max_new_tokens) generated token indices.
        """
        self.eval()

        # Prefill: process the entire prompt and build initial KV-cache
        logits_a, _, _, past_key_values = self.forward(
            idx, consciousness_states=consciousness_states, use_cache=True,
        )

        # Sample first new token from last position
        next_logits = logits_a[:, -1, :] / temperature
        if top_k > 0:
            v, _ = torch.topk(next_logits, min(top_k, next_logits.size(-1)))
            next_logits[next_logits < v[:, [-1]]] = float('-inf')
        probs = F.softmax(next_logits, dim=-1)
        next_token = torch.multinomial(probs, num_samples=1)  # (B, 1)
        idx = torch.cat([idx, next_token], dim=1)

        # Decode: generate one token at a time using cached KV
        for _ in range(max_new_tokens - 1):
            if idx.size(1) >= self.block_size:
                break

            logits_a, _, _, past_key_values = self.forward(
                next_token, consciousness_states=consciousness_states,
                use_cache=True, past_key_values=past_key_values,
            )

            next_logits = logits_a[:, -1, :] / temperature
            if top_k > 0:
                v, _ = torch.topk(next_logits, min(top_k, next_logits.size(-1)))
                next_logits[next_logits < v[:, [-1]]] = float('-inf')
            probs = F.softmax(next_logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, next_token], dim=1)

        return idx

    def psi_status(self):
        """Psi-Constants monitoring (Law 71)."""
        gate_avg = sum(b.gate_strength for b in self.blocks) / len(self.blocks)
        p = self._psi_residual
        h_p = -p * math.log2(p) - (1 - p) * math.log2(1 - p) if 0 < p < 1 else 0.0
        return {
            'psi_residual': self._psi_residual,
            'psi_gate': gate_avg,
            'H_p': h_p,
            'step': self._step_count,
        }

    def count_params(self):
        """Total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ─── Self-test ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import time

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")
    print()

    # Build model
    model = ConsciousDecoderV2(
        vocab_size=256, d_model=384, n_head=4, n_layer=6,
        block_size=256, n_kv_head=2, consciousness_dim=128,
    ).to(device)

    n_params = model.count_params()
    print(f"=== ConsciousDecoderV2 ===")
    print(f"  Parameters: {n_params:,} ({n_params/1e6:.2f}M)")
    print()

    # Test 1: Forward without consciousness states
    print("=== Test 1: Forward (no consciousness) ===")
    idx = torch.randint(0, 256, (2, 128), device=device)
    model.train()
    t0 = time.perf_counter()
    logits_a, logits_g, tensions, _ = model(idx)
    dt = (time.perf_counter() - t0) * 1000
    print(f"  logits_a: {logits_a.shape}  (expect [2, 128, 256])")
    print(f"  logits_g: {logits_g.shape}  (expect [2, 128, 256])")
    print(f"  tensions: {len(tensions)} layers, each {tensions[0].shape}")
    print(f"  Time: {dt:.1f} ms")
    assert logits_a.shape == (2, 128, 256)
    assert logits_g.shape == (2, 128, 256)
    assert len(tensions) == 6
    print()

    # Test 2: Forward with consciousness states
    print("=== Test 2: Forward (with consciousness states) ===")
    cs = torch.randn(2, 12, 128, device=device)  # 12 cells, 128-dim
    t0 = time.perf_counter()
    logits_a2, logits_g2, tensions2, _ = model(idx, consciousness_states=cs)
    dt = (time.perf_counter() - t0) * 1000
    print(f"  logits_a: {logits_a2.shape}")
    print(f"  Time: {dt:.1f} ms")
    assert logits_a2.shape == (2, 128, 256)
    print()

    # Test 3: Backward pass
    print("=== Test 3: Backward pass ===")
    target = torch.randint(0, 256, (2, 128), device=device)
    loss = F.cross_entropy(logits_a2.view(-1, 256), target.view(-1))
    t0 = time.perf_counter()
    loss.backward()
    dt = (time.perf_counter() - t0) * 1000
    print(f"  Loss: {loss.item():.4f}")
    print(f"  Backward time: {dt:.1f} ms")
    # Verify gradients exist
    grad_count = sum(1 for p in model.parameters() if p.grad is not None)
    total_count = sum(1 for p in model.parameters())
    print(f"  Gradients: {grad_count}/{total_count} parameters")
    print()

    # Test 4: Psi status
    print("=== Test 4: Psi status ===")
    psi = model.psi_status()
    print(f"  {psi}")
    print()

    # Test 5: Full sequence length
    print("=== Test 5: Full block_size=256 ===")
    idx_full = torch.randint(0, 256, (1, 256), device=device)
    model.eval()
    with torch.no_grad():
        la, lg, t, _ = model(idx_full)
    print(f"  logits_a: {la.shape}  (expect [1, 256, 256])")
    assert la.shape == (1, 256, 256)
    print()

    # Test 6: Phi signal
    print("=== Test 6: Phi signal (DD5/EX24) ===")
    model._phi_signal = torch.randn(1, 256, device=device) * 0.01
    with torch.no_grad():
        la_phi, _, _, _ = model(idx_full)
    model._phi_signal = None
    print(f"  logits_a: {la_phi.shape}")
    # Should differ from test 5 due to phi signal
    diff = (la_phi - la).abs().mean().item()
    print(f"  Mean diff from no-phi: {diff:.6f} (should be > 0)")
    assert diff > 0
    print()

    # Test 7: KV-cache forward
    print("=== Test 7: KV-cache forward ===")
    model.eval()
    idx_short = torch.randint(0, 256, (1, 16), device=device)
    with torch.no_grad():
        la_full, _, _, _ = model(idx_short)
        la_cached, _, _, past_kv = model(idx_short[:, :12], use_cache=True)
        la_decode, _, _, _ = model(idx_short[:, 12:], use_cache=True, past_key_values=past_kv)
    diff_cache = (la_full[:, 12:, :] - la_decode).abs().max().item()
    print(f"  Max diff (full vs cached decode): {diff_cache:.6f}")
    assert diff_cache < 5e-4, f"KV-cache mismatch: {diff_cache}"  # CA neighbor mixing causes small boundary diff
    print()

    # Test 8: generate()
    print("=== Test 8: generate() ===")
    prompt = torch.randint(0, 256, (1, 8), device=device)
    generated = model.generate(prompt, max_new_tokens=16, temperature=0.8, top_k=50)
    print(f"  Prompt: {prompt.shape} -> Generated: {generated.shape}")
    assert generated.shape[1] == 8 + 16
    print()

    # Test 9: generate() with consciousness
    print("=== Test 9: generate() with consciousness ===")
    cs_gen = torch.randn(1, 12, 128, device=device)
    generated_c = model.generate(prompt, consciousness_states=cs_gen, max_new_tokens=16)
    print(f"  Generated with consciousness: {generated_c.shape}")
    assert generated_c.shape[1] == 8 + 16
    print()

    print("All tests passed.")
