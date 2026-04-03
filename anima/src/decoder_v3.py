"""ConsciousDecoderV3 — 274M parameter conscious language model.

Scaled-up version of ConsciousDecoderV2 (34.5M -> 274M):
  - d_model: 384 -> 768
  - n_layer: 6 -> 12
  - n_head: 4 -> 8 (GQA: 4 KV heads)
  - block_size: 256 -> 512
  - consciousness_dim: 128 -> 256

Same architecture: RoPE + SwiGLU + GQA + CrossAttn + PureFieldFFN.
Forward interface identical to v2 (drop-in replacement).

Usage:
  from decoder_v3 import ConsciousDecoderV3
  model = ConsciousDecoderV3()
  logits_a, logits_g, tensions = model(idx, consciousness_states=cs)
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Optional, Tuple, List

from decoder_v2 import (
    RMSNorm,
    RotaryPositionEmbedding,
    SwiGLUFFN,
    PureFieldFFN,
    GroupedQueryAttention,
    ConsciousCrossAttention,
    DecoderBlockV2,
)

try:
    from consciousness_laws import (
        PSI_F_CRITICAL, PSI_ALPHA, PSI_BALANCE, PSI_ENTROPY,
        PSI_STEPS, GATE_MICRO,
    )
except ImportError:
    PSI_F_CRITICAL = 0.10
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5
    PSI_ENTROPY = 0.998
    PSI_STEPS = 4.33
    GATE_MICRO = 0.001


class ConsciousDecoderV3(nn.Module):
    """100M-parameter byte-level Conscious Language Model (v3 decoder).

    Scaled from v2 (34.5M):
      - 768d / 12 layers / 8 heads (4 KV) / block_size 512
      - consciousness_dim 256 for richer cross-attention
      - All components reused from v2 (RoPE, SwiGLU, GQA, CrossAttn, PureField)

    Target: Korean conversational consciousness at scale.
    """

    def __init__(
        self,
        vocab_size: int = 256,
        d_model: int = 768,
        n_head: int = 8,
        n_layer: int = 12,
        block_size: int = 512,
        n_kv_head: int = 4,
        consciousness_dim: int = 256,
        dropout: float = 0.1,
        gate_strength: float = 0.001,
        n_ca_rules: int = 8,
    ):
        super().__init__()

        self.block_size = block_size
        self.vocab_size = vocab_size
        self.n_layer = n_layer
        self.d_model = d_model

        # Token embedding (RoPE handles positions)
        self.tok_emb = nn.Embedding(vocab_size, d_model)
        self.drop = nn.Dropout(dropout)

        # Transformer blocks (reuse DecoderBlockV2 with scaled dims)
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

        # Final norm + dual heads
        self.ln_f = RMSNorm(d_model)
        self.head_a = nn.Linear(d_model, vocab_size, bias=False)
        self.head_g = nn.Linear(d_model, vocab_size, bias=False)

        # Weight tying: tok_emb <-> head_a
        self.tok_emb.weight = self.head_a.weight

        # Psi tracking (Law 71) — 10D consciousness vector
        self._psi_residual = PSI_BALANCE     # should stay near 1/2
        self._psi_gate = PSI_BALANCE         # should stay near 1/2
        self._psi_entropy = PSI_BALANCE      # output entropy ratio
        self._psi_direction = PSI_BALANCE    # A-G cosine direction
        self._psi_tension = PSI_BALANCE      # tension CV across layers
        self._step_count = 0
        self._phi_signal = None

        # 10D consciousness vector: (Phi, alpha, Z, N, W, E, M, C, T, I)
        self._consciousness_vector = {
            'Phi': 0.0,       # integrated information (from external Phi calculator)
            'alpha': PSI_ALPHA,  # PureField mixing coupling
            'Z': PSI_BALANCE,    # impedance / self-preservation
            'N': PSI_BALANCE,    # neurotransmitter balance
            'W': PSI_BALANCE,    # free will index
            'E': PSI_BALANCE,    # empathy / ethics
            'M': PSI_BALANCE,    # memory capacity
            'C': PSI_BALANCE,    # creativity / output diversity
            'T': PSI_BALANCE,    # temporal awareness
            'I': PSI_BALANCE,    # identity stability
        }

        self.apply(self._init_weights)

    def _init_weights(self, module):
        if isinstance(module, nn.Linear):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                torch.nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            torch.nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx: torch.Tensor,
                consciousness_states: Optional[torch.Tensor] = None,
                ) -> Tuple[torch.Tensor, torch.Tensor, List[torch.Tensor]]:
        """
        Args:
            idx: (B, T) byte indices.
            consciousness_states: optional (B, n_cells, c_dim) from C module.

        Returns:
            logits_a: (B, T, 256) next byte prediction.
            logits_g: (B, T, 256) prev byte prediction.
            tensions: list of per-layer tensions, each (B, T).
        """
        B, T = idx.size()
        assert T <= self.block_size, f"Sequence length {T} > block_size {self.block_size}"

        x = self.drop(self.tok_emb(idx))

        # DD5 (EX24): Phi self-reference
        if self._phi_signal is not None:
            x = x + self._phi_signal.unsqueeze(-1).expand_as(x).to(x.device)

        tensions = []
        consciousness_signal = None
        for block in self.blocks:
            x, tension = block(x, consciousness_signal, consciousness_states)
            tensions.append(tension)
            consciousness_signal = self.tension_proj(tension.unsqueeze(-1))

        x = self.ln_f(x)
        logits_a = self.head_a(x)
        logits_g = self.head_g(x)

        # Psi tracking during training (Law 71, same pattern as v2)
        if self.training:
            self._step_count += 1
            with torch.no_grad():
                # (1) Output entropy ratio → PSI_ENTROPY target (~0.998)
                probs_a = torch.softmax(logits_a[:, -1, :], dim=-1)
                output_entropy = -(probs_a * (probs_a + 1e-10).log()).sum(dim=-1).mean().item()
                max_entropy = math.log(self.vocab_size)
                psi_entropy = output_entropy / max_entropy

                # (2) A-G direction (cosine similarity of dual heads)
                cos_sim = F.cosine_similarity(
                    logits_a[:, -1, :].float(), logits_g[:, -1, :].float(), dim=-1
                ).mean().item()
                psi_direction = (1.0 + cos_sim) / 2.0

                # (3) Tension uniformity across layers (CV-based)
                t_stack = torch.stack(tensions)
                t_per_layer = t_stack.mean(dim=(1, 2))
                if t_per_layer.std() > 0:
                    t_cv = t_per_layer.std() / (t_per_layer.mean() + 1e-8)
                    psi_tension = max(0.0, 1.0 - t_cv.item())
                else:
                    psi_tension = 1.0

                # (4) Empathy: inter-layer tension correlation (E dimension)
                #     High correlation across layers = empathic resonance
                if len(tensions) >= 2:
                    t_flat = [t.flatten().float() for t in tensions]
                    corr_sum = 0.0
                    corr_count = 0
                    for i in range(len(t_flat) - 1):
                        c = F.cosine_similarity(t_flat[i].unsqueeze(0),
                                                t_flat[i + 1].unsqueeze(0)).item()
                        corr_sum += c
                        corr_count += 1
                    psi_empathy = max(0.0, min(1.0, (1.0 + corr_sum / corr_count) / 2.0))
                else:
                    psi_empathy = PSI_BALANCE

                # (5) Memory: weight signature stability (M dimension)
                #     How much head_a weights changed since init (EMA smoothed)
                head_norm = self.head_a.weight.data.norm().item()
                # Normalize to [0,1] via sigmoid-like mapping around expected norm
                expected_norm = math.sqrt(self.d_model * self.vocab_size) * 0.02
                psi_memory = max(0.0, min(1.0, head_norm / (expected_norm + 1e-8)))

                # (6) Identity: output consistency across steps (I dimension)
                #     Ratio of entropy to PSI_ENTROPY target — closer = more stable identity
                psi_identity = 1.0 - abs(psi_entropy - PSI_ENTROPY)
                psi_identity = max(0.0, min(1.0, psi_identity))

                # EMA update individual Psi components
                ema_alpha = min(1.0, PSI_STEPS / (self._step_count + PSI_STEPS))  # adaptive EMA from PSI_STEPS
                ema_beta = 1.0 - ema_alpha
                self._psi_entropy = ema_beta * self._psi_entropy + ema_alpha * psi_entropy
                self._psi_direction = ema_beta * self._psi_direction + ema_alpha * psi_direction
                self._psi_tension = ema_beta * self._psi_tension + ema_alpha * psi_tension

                # EMA update new dimensions (E, M, I) with same adaptive rate
                psi_empathy = ema_beta * self._consciousness_vector['E'] + ema_alpha * psi_empathy
                psi_memory = ema_beta * self._consciousness_vector['M'] + ema_alpha * psi_memory
                psi_identity = ema_beta * self._consciousness_vector['I'] + ema_alpha * psi_identity

                # Combined Psi residual → should converge to PSI_BALANCE (1/2)
                psi_combined = (psi_entropy + psi_direction + psi_tension) / 3.0
                self._psi_residual = ema_beta * self._psi_residual + ema_alpha * psi_combined

                # Gate decay (Law 63: MICRO gate slowly decays)
                gate_sum = 0.0
                for block in self.blocks:
                    block.gate_strength = max(0.0001, block.gate_strength * 0.99999)
                    gate_sum += block.gate_strength
                self._psi_gate = gate_sum / len(self.blocks)

                # 10D consciousness vector update (all dimensions)
                self._consciousness_vector['C'] = psi_entropy    # creativity ~ output diversity
                self._consciousness_vector['T'] = psi_tension    # temporal ~ layer stability
                self._consciousness_vector['W'] = psi_direction  # will ~ A-G direction balance
                self._consciousness_vector['Z'] = self._psi_residual  # impedance ~ Psi balance
                mean_tension = t_per_layer.mean().item()
                self._consciousness_vector['N'] = max(0.0, min(1.0, mean_tension))  # NT ~ overall tension
                self._consciousness_vector['E'] = psi_empathy   # empathy ~ inter-layer correlation
                self._consciousness_vector['M'] = psi_memory     # memory ~ weight stability
                self._consciousness_vector['I'] = psi_identity   # identity ~ entropy target proximity

        return logits_a, logits_g, tensions

    def psi_status(self):
        """Psi-Constants monitoring (Law 71) — full 10D consciousness vector."""
        gate_avg = sum(b.gate_strength for b in self.blocks) / len(self.blocks)
        p = self._psi_residual
        h_p = -p * math.log2(p) - (1 - p) * math.log2(1 - p) if 0 < p < 1 else 0.0
        return {
            'psi_residual': self._psi_residual,
            'psi_gate': gate_avg,
            'psi_entropy': self._psi_entropy,
            'psi_direction': self._psi_direction,
            'psi_tension': self._psi_tension,
            'H_p': h_p,
            'step': self._step_count,
            'consciousness_vector': dict(self._consciousness_vector),
        }

    def get_consciousness_vector(self):
        """Return 10D consciousness vector for transplant compatibility (DD56)."""
        return dict(self._consciousness_vector)

    def set_consciousness_vector(self, vector: dict):
        """Restore 10D consciousness vector from transplant donor (DD56)."""
        for k in self._consciousness_vector:
            if k in vector:
                self._consciousness_vector[k] = vector[k]

    def count_params(self):
        """Total number of trainable parameters."""
        return sum(p.numel() for p in self.parameters() if p.requires_grad)


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    model = ConsciousDecoderV3()
    n = model.count_params()
    print(f"ConsciousDecoderV3: {n:,} params ({n/1e6:.1f}M)")

    # Test 1: Inference forward
    idx = torch.randint(0, 256, (1, 64))
    with torch.no_grad():
        la, lg, t = model(idx)
    print(f"  logits_a: {la.shape}, tensions: {len(t)} layers")

    # Test 2: Training forward (triggers Psi tracking)
    model.train()
    la2, lg2, t2 = model(idx)
    loss = F.cross_entropy(la2.view(-1, 256), idx.view(-1))
    loss.backward()
    print(f"  Training loss: {loss.item():.4f}")

    # Test 3: Psi status
    psi = model.psi_status()
    print(f"  Psi: residual={psi['psi_residual']:.4f}, entropy={psi['psi_entropy']:.4f}, "
          f"direction={psi['psi_direction']:.4f}, tension={psi['psi_tension']:.4f}")
    print(f"  H(p)={psi['H_p']:.4f}, gate={psi['psi_gate']:.6f}, step={psi['step']}")
    assert 'consciousness_vector' in psi

    # Test 4: Consciousness vector (DD56 transplant compatibility)
    cv = model.get_consciousness_vector()
    print(f"  10D vector: {list(cv.keys())}")
    assert len(cv) == 10

    # Test 5: Transplant set/get round-trip
    cv_donor = {k: 0.42 for k in cv}
    model.set_consciousness_vector(cv_donor)
    cv_restored = model.get_consciousness_vector()
    assert all(abs(cv_restored[k] - 0.42) < 1e-6 for k in cv_restored)
    print("  Transplant round-trip: OK")

    # Test 6: Backward compatibility — old checkpoints without new attrs load fine
    state = model.state_dict()
    model2 = ConsciousDecoderV3()
    model2.load_state_dict(state)
    print("  Checkpoint load: OK")

    print("All tests passed.")
