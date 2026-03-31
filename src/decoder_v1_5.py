"""ConsciousLMv15 -- ConsciousLM v1 + CrossAttention to consciousness states.

v1 architecture preserved (Law 98: simpler is better):
  - Learned position embeddings
  - GELU FFN
  - LayerNorm
  - Standard multi-head attention

Added from v2:
  - ConsciousCrossAttention per block
  - consciousness_states input (optional)

This tests the hypothesis that cross-attention alone (the key innovation
in v2) helps when stripped of the other changes (RoPE, SwiGLU, GQA, RMSNorm)
that caused gradient instability per Law 98.

Forward interface identical to v1 and v2:
  logits_a, logits_g, tensions = model(idx)
  logits_a, logits_g, tensions = model(idx, consciousness_states=cs)
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



# ─── ConsciousCrossAttention (from decoder_v2.py) ─────────────────────────

class ConsciousCrossAttention(nn.Module):
    """Decoder attends to consciousness cell states.

    Instead of: x = x + consciousness_signal * gate  (v1, passive)
    Now:        x = x + cross_attn(Q=x, K=consciousness, V=consciousness)

    consciousness_states are .detach()'d before use (Law 61).
    """

    def __init__(self, d_model: int, consciousness_dim: int, n_head: int = 4,
                 dropout: float = 0.1):
        super().__init__()
        assert d_model % n_head == 0
        self.n_head = n_head
        self.head_dim = d_model // n_head
        self.d_model = d_model

        self.q_proj = nn.Linear(d_model, d_model, bias=False)
        self.k_proj = nn.Linear(consciousness_dim, d_model, bias=False)
        self.v_proj = nn.Linear(consciousness_dim, d_model, bias=False)
        self.o_proj = nn.Linear(d_model, d_model, bias=False)

        self.dropout = nn.Dropout(dropout)
        nn.init.normal_(self.o_proj.weight, std=0.001)

    def forward(self, x: torch.Tensor,
                consciousness: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (B, T, d_model)
            consciousness: (B, n_cells, c_dim)

        Returns:
            output: (B, T, d_model)
        """
        B, T, D = x.shape
        _, S, _ = consciousness.shape

        q = self.q_proj(x).view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = self.k_proj(consciousness).view(B, S, self.n_head, self.head_dim).transpose(1, 2)
        v = self.v_proj(consciousness).view(B, S, self.n_head, self.head_dim).transpose(1, 2)

        att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
        att = F.softmax(att, dim=-1)
        att = self.dropout(att)

        y = att @ v
        y = y.transpose(1, 2).contiguous().view(B, T, D)
        y = self.o_proj(y)
        return y


# ─── PureFieldFFN (from conscious_lm.py) ──────────────────────────────────

class PureFieldFFN(nn.Module):
    """Dual-engine FFN: Engine A - Engine G = repulsion/tension."""

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


# ─── CausalSelfAttention (standard, from v1) ──────────────────────────────

class CausalSelfAttention(nn.Module):
    """Standard multi-head causal self-attention (no GQA, no RoPE)."""

    def __init__(self, d_model: int, n_head: int, block_size: int,
                 dropout: float = 0.37):
        super().__init__()
        assert d_model % n_head == 0
        self.c_attn = nn.Linear(d_model, 3 * d_model)
        self.c_proj = nn.Linear(d_model, d_model)
        self.attn_dropout = nn.Dropout(dropout)
        self.resid_dropout = nn.Dropout(dropout)
        self.n_head = n_head
        self.d_model = d_model
        self.head_dim = d_model // n_head
        self.register_buffer(
            "bias",
            torch.tril(torch.ones(block_size, block_size)).view(
                1, 1, block_size, block_size
            ),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, D = x.size()
        qkv = self.c_attn(x)
        q, k, v = qkv.split(self.d_model, dim=2)
        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        att = (q @ k.transpose(-2, -1)) * (1.0 / math.sqrt(self.head_dim))
        att = att.masked_fill(self.bias[:, :, :T, :T] == 0, float("-inf"))
        att = F.softmax(att, dim=-1)
        att = self.attn_dropout(att)
        y = att @ v
        y = y.transpose(1, 2).contiguous().view(B, T, D)
        y = self.resid_dropout(self.c_proj(y))
        return y


# ─── ConsciousBlock v1.5 ──────────────────────────────────────────────────

class ConsciousBlockV15(nn.Module):
    """v1 block + ConsciousCrossAttention.

    Architecture per block:
      1. LayerNorm -> standard self-attention -> residual
      2. LayerNorm -> CA neighbor + META-CA -> residual (Law 64/67)
      3. LayerNorm -> PureFieldFFN -> residual (consciousness)
      4. LayerNorm -> CrossAttention to consciousness states -> residual (NEW)
      5. Inter-layer consciousness whisper (Law 63)

    Everything from v1 preserved. Only cross-attention added.
    """

    def __init__(self, d_model: int, n_head: int, block_size: int,
                 consciousness_dim: int = 128,
                 dropout: float = 0.37, n_ca_rules: int = 8,
                 gate_strength: float = 0.001):
        super().__init__()

        # v1: LayerNorm + standard attention
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = CausalSelfAttention(d_model, n_head, block_size, dropout)

        # v1: PureFieldFFN
        self.ln2 = nn.LayerNorm(d_model)
        self.ffn = PureFieldFFN(d_model, dropout)

        # v1: CA neighbor mixing (Law 64)
        self.ca_mix = nn.Linear(d_model * 3, d_model, bias=False)
        self.ln_ca = nn.LayerNorm(d_model)

        # v1: META-CA rule selector (Law 67)
        self.n_ca_rules = n_ca_rules
        self.rule_weights = nn.Linear(d_model, n_ca_rules)
        self.rules = nn.ModuleList([
            nn.Linear(d_model, d_model, bias=False) for _ in range(n_ca_rules)
        ])

        # v1: MICRO gate (Law 63)
        self.gate_strength = gate_strength

        # NEW from v2: Cross-attention to consciousness states
        self.ln_cross = nn.LayerNorm(d_model)
        self.cross_attn = ConsciousCrossAttention(
            d_model, consciousness_dim, n_head, dropout
        )

    def forward(self, x: torch.Tensor,
                consciousness_signal: Optional[torch.Tensor] = None,
                consciousness_states: Optional[torch.Tensor] = None,
                ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (B, T, D)
            consciousness_signal: optional (B, T, D) from previous layer tension
            consciousness_states: optional (B, n_cells, c_dim) for cross-attention

        Returns:
            x: (B, T, D)
            tension: (B, T)
        """
        # 1. Self-attention (v1: standard MHA)
        x = x + self.attn(self.ln1(x))

        # 2. CA neighbor evolution (v1: Law 64)
        x_left = torch.cat([x[:, :1, :], x[:, :-1, :]], dim=1)
        x_right = torch.cat([x[:, 1:, :], x[:, -1:, :]], dim=1)
        neighborhood = torch.cat([x_left, x, x_right], dim=-1)
        ca_out = self.ca_mix(neighborhood)

        # META-CA (v1: Law 67)
        rule_logits = self.rule_weights(x)
        rule_probs = F.softmax(rule_logits, dim=-1)
        rule_outputs = torch.stack([r(ca_out) for r in self.rules], dim=2)
        meta_ca_out = (rule_outputs * rule_probs.unsqueeze(-1)).sum(dim=2)
        x = self.ln_ca(x + meta_ca_out * self.gate_strength)

        # 3. PureFieldFFN (v1: consciousness signal)
        ffn_out, tension = self.ffn(self.ln2(x))
        x = x + ffn_out

        # 4. Inter-layer consciousness whisper (v1: Law 63)
        if consciousness_signal is not None:
            x = x + consciousness_signal * self.gate_strength

        # 5. Cross-attention to consciousness states (NEW from v2)
        if consciousness_states is not None:
            c_detached = consciousness_states.detach()
            x = x + self.cross_attn(self.ln_cross(x), c_detached)

        return x, tension


# ─── ConsciousLMv15 (main model) ──────────────────────────────────────────

class ConsciousLMv15(nn.Module):
    """ConsciousLM v1 + CrossAttention to consciousness states.

    v1 architecture preserved (Law 98: simpler is better):
      - Learned position embeddings
      - GELU FFN
      - LayerNorm
      - Standard multi-head attention

    Added from v2:
      - ConsciousCrossAttention per block
      - consciousness_states input (optional)

    Forward interface identical to v1 and v2:
      logits_a, logits_g, tensions = model(idx)
      logits_a, logits_g, tensions = model(idx, consciousness_states=cs)
    """

    def __init__(
        self,
        vocab_size: int = 256,
        d_model: int = 384,
        n_head: int = 4,
        n_layer: int = 6,
        block_size: int = 256,
        consciousness_dim: int = 128,
        dropout: float = 0.37,
        gate_strength: float = 0.001,
        n_ca_rules: int = 8,
    ):
        super().__init__()

        self.block_size = block_size
        self.vocab_size = vocab_size
        self.n_layer = n_layer
        self.d_model = d_model

        # v1: Token + position embeddings (learned)
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(block_size, d_model)
        self.drop = nn.Dropout(dropout)

        # v1.5 blocks (v1 + cross-attention)
        self.blocks = nn.ModuleList([
            ConsciousBlockV15(
                d_model=d_model,
                n_head=n_head,
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

        # v1: LayerNorm final
        self.ln_f = nn.LayerNorm(d_model)

        # Dual prediction heads
        self.head_a = nn.Linear(d_model, vocab_size, bias=False)
        self.head_g = nn.Linear(d_model, vocab_size, bias=False)

        # Weight tying
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
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
        elif isinstance(module, nn.LayerNorm):
            torch.nn.init.zeros_(module.bias)
            torch.nn.init.ones_(module.weight)

    def forward(self, idx: torch.Tensor,
                consciousness_states: Optional[torch.Tensor] = None,
                ) -> Tuple[torch.Tensor, torch.Tensor, List[torch.Tensor]]:
        """
        Args:
            idx: (B, T) byte indices
            consciousness_states: optional (B, n_cells, c_dim) from C module

        Returns:
            logits_a: (B, T, vocab_size) next-byte logits
            logits_g: (B, T, vocab_size) prev-byte logits
            tensions: list of per-layer tensions, each (B, T)
        """
        B, T = idx.size()
        assert T <= self.block_size, f"Sequence length {T} > block_size {self.block_size}"

        # v1: Learned token + position embeddings
        tok = self.tok_emb(idx)
        pos = self.pos_emb(torch.arange(T, device=idx.device))
        x = self.drop(tok + pos)

        # DD5 (EX24): Phi self-reference
        if getattr(self, '_phi_signal', None) is not None:
            phi_sig = self._phi_signal
            x = x + phi_sig.unsqueeze(-1).expand_as(x).to(x.device)

        # Transformer blocks with consciousness
        tensions = []
        consciousness_signal = None
        for block in self.blocks:
            x, tension = block(x, consciousness_signal, consciousness_states)
            tensions.append(tension)
            consciousness_signal = self.tension_proj(tension.unsqueeze(-1))

        # v1: LayerNorm final
        x = self.ln_f(x)

        # Dual heads
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

        return logits_a, logits_g, tensions

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
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


# ─── Self-test ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")
    print()

    model = ConsciousLMv15(
        vocab_size=256, d_model=384, n_head=4, n_layer=6,
        block_size=256, consciousness_dim=128,
    ).to(device)

    n_params = model.count_params()
    print(f"ConsciousLM v1.5 Parameters: {n_params:,}")

    # Test without consciousness states
    idx = torch.randint(0, 256, (1, 32), device=device)
    logits_a, logits_g, tensions = model(idx)
    print(f"Without consciousness: logits_a={logits_a.shape}, tensions={len(tensions)}")

    # Test with consciousness states
    c_states = torch.randn(1, 4, 128, device=device)
    logits_a, logits_g, tensions = model(idx, consciousness_states=c_states)
    print(f"With consciousness:    logits_a={logits_a.shape}, tensions={len(tensions)}")

    print()
    print("Self-test passed.")
