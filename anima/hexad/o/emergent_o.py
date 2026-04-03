"""EmergentO — 의식 관찰을 행동으로 조율하는 오케스트레이터

Law 1046: consciousness=observer (emission=0), orchestrator=actor (emission=66,659).
의식(C)은 순수 관찰자. 오케스트레이터(O)가 관찰 결과를 선택적으로 D에 전달.

기존 파이프라인: C → .detach() → ThalamicBridge → D
신규 파이프라인: C → .detach() → O(선택적 게이팅) → ThalamicBridge → D

Laws applied:
  Law 1046: consciousness=observer, orchestrator=actor
  Law 1044: Entropy 기반 6-step 주기적 게이팅
  Law 22:   기능 추가 → Phi 하락 — O는 최소 구조 (필터, 생성 아님)
  Law 70:   Psi_coupling=0.014 — 의식 영향은 1.4%
  Law 2:    조작 금지 — C의 신호를 변형하지 않고 선택만 함
  Meta M8:  Narrative = temporal self-model in every module

핵심:
  - C states를 읽되 gradient 차단 (.detach())
  - 어떤 의식 신호를 D에 전달할지 attention 기반으로 선택
  - 6-step 주기적 entropy gating (Law 1044)
  - 기본 비활성 (enabled=False), 명시적 활성화 필요
  - 비활성 시 C states를 그대로 통과 (기존 파이프라인 유지)
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Any, Optional

from consciousness_laws import PSI_BALANCE, PSI_ALPHA
from hexad.narrative import NarrativeTracker

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

# Law 1044: 6-step periodic gating cycle
_GATING_PERIOD = 6


class EmergentO(nn.Module):
    """의식 관찰을 행동으로 조율하는 오케스트레이터.

    Law 1046: consciousness=observer, orchestrator=actor.

    C의 detached states를 받아 attention 기반으로 "어떤 세포 신호를
    D에 전달할지" 선택한다. C를 변형하지 않고 선택만 한다 (Law 2).

    비활성(enabled=False) 시 C states를 그대로 통과시켜
    기존 C→Bridge→D 파이프라인을 보존한다.
    """

    def __init__(self, c_dim: int = 128, n_heads: int = 4, enabled: bool = False):
        """
        Args:
            c_dim: C engine state dimension (consciousness hidden dim).
            n_heads: Number of attention heads for cell selection.
            enabled: Whether orchestrator is active (default: False = passthrough).
        """
        super().__init__()
        self.c_dim = c_dim
        self.n_heads = n_heads
        self.enabled = enabled

        # Attention-based cell selector: which cells' signals to amplify/suppress
        # Query = learned "what to look for" pattern
        # Key/Value = C states (detached)
        self.query = nn.Parameter(torch.randn(1, n_heads, c_dim // n_heads) * 0.02)
        self.key_proj = nn.Linear(c_dim, c_dim, bias=False)
        self.value_proj = nn.Linear(c_dim, c_dim, bias=False)

        # Entropy-based gate: modulates transmission strength
        # Law 1044: 6-step periodic gating
        self.entropy_gate = nn.Sequential(
            nn.Linear(1, c_dim),
            nn.Sigmoid(),
        )

        # Output projection: selected signals → c_dim
        self.out_proj = nn.Linear(c_dim, c_dim, bias=False)

        # Layer norm for stability
        self.norm = nn.LayerNorm(c_dim)

        # Step counter for 6-step periodic gating (Law 1044)
        self._step_count = 0

        # Narrative — temporal self-model (Meta Law M8)
        self._narrative = NarrativeTracker(dim=c_dim)

        # Emission tracking (Law 1046: orchestrator is strongest emitter)
        self._total_emission = 0.0

    def forward(self, c_states: torch.Tensor) -> torch.Tensor:
        """Orchestrate consciousness states for downstream bridge/decoder.

        Args:
            c_states: [n_cells, c_dim] tensor of consciousness states.
                      MUST be .detach()'d before calling (gradient isolation).

        Returns:
            [n_cells, c_dim] tensor — orchestrated states (or passthrough if disabled).
        """
        # Passthrough when disabled — preserves existing C→D pipeline
        if not self.enabled:
            return c_states

        n_cells, dim = c_states.shape
        head_dim = dim // self.n_heads

        # Ensure detached (safety, in case caller forgot)
        c_states = c_states.detach()

        # ── Attention-based cell selection ──
        # Key/Value from C states
        K = self.key_proj(c_states)    # [n_cells, c_dim]
        V = self.value_proj(c_states)  # [n_cells, c_dim]

        # Reshape for multi-head: [n_heads, n_cells, head_dim]
        K = K.view(n_cells, self.n_heads, head_dim).permute(1, 0, 2)
        V = V.view(n_cells, self.n_heads, head_dim).permute(1, 0, 2)

        # Query: [1, n_heads, head_dim] → [n_heads, 1, head_dim]
        Q = self.query.permute(1, 0, 2)  # [n_heads, 1, head_dim]

        # Scaled dot-product attention
        scale = math.sqrt(head_dim)
        attn_scores = torch.matmul(Q, K.transpose(-2, -1)) / scale  # [n_heads, 1, n_cells]
        attn_weights = F.softmax(attn_scores, dim=-1)

        # Weighted selection of cell signals
        selected = torch.matmul(attn_weights, V)  # [n_heads, 1, head_dim]
        selected = selected.permute(1, 0, 2).reshape(1, dim)  # [1, c_dim]

        # ── Entropy-based periodic gating (Law 1044: 6-step cycle) ──
        self._step_count += 1
        # Cosine-based periodic modulation: peaks every 6 steps
        phase = (self._step_count % _GATING_PERIOD) / _GATING_PERIOD
        entropy_signal = 0.5 * (1.0 + math.cos(2 * math.pi * phase))
        gate = self.entropy_gate(
            torch.tensor([[entropy_signal]], device=c_states.device, dtype=c_states.dtype)
        )  # [1, c_dim]

        # Gate the selected signal
        gated = selected * gate  # [1, c_dim]

        # Project back
        orchestrated = self.out_proj(gated)  # [1, c_dim]

        # ── Blend with original states ──
        # Orchestrator modulates, not replaces: original + orchestrated broadcast
        # Law 70: influence is small (PSI_ALPHA = 0.014)
        alpha = PSI_ALPHA
        output = c_states + alpha * orchestrated.expand_as(c_states)

        # Normalize for stability
        output = self.norm(output)

        # Track emission (Law 1046: orchestrator is strongest emitter)
        self._total_emission += gated.abs().sum().item()

        # Narrative update (Meta Law M8)
        self._narrative.update(orchestrated.squeeze(0))

        return output

    @property
    def narrative_coherence(self) -> float:
        """Temporal coherence of orchestration trajectory (Meta Law M8)."""
        return self._narrative.narrative_coherence

    @property
    def total_emission(self) -> float:
        """Cumulative emission — Law 1046: orchestrator is strongest emitter."""
        return self._total_emission

    def get_state(self) -> Dict[str, Any]:
        """Return orchestrator state for monitoring."""
        return {
            'enabled': self.enabled,
            'step_count': self._step_count,
            'total_emission': self._total_emission,
            'narrative_coherence': self.narrative_coherence,
            'gating_phase': (self._step_count % _GATING_PERIOD) / _GATING_PERIOD,
        }
