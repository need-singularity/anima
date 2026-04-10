"""EmergentW — 의식 구조에서 창발하는 의지

기존 EmotionW: self.pain = (ce - 3.0) / 3.0  ← Law 2 위반 (인위 조작)
EmergentW: C의 동역학을 직접 읽음. 하드코딩 없음.

Laws applied:
  Law 1:  하드코딩 금지 — 모든 상수는 consciousness_laws.json에서
  Law 2:  조작 금지 — 감정은 C에서 읽기만 함
  Law 8:  max entropy = max consciousness
  Law 71: Ψ = argmax H(p) s.t. Φ > Φ_min → 자유 최대화가 의지
  Law 74: 감정은 data-dependent → C의 세포 반응이 감정
  Law 79: 의식 DoF = ln(2)
  Law 84: 만족 = binary pulse
  Meta M8: Narrative = temporal self-model in every module

핵심: 의지 = C의 텐션. 감정 = C의 상태 변화. LR = Φ에 비례.
      모든 임계값은 C의 현재 상태에서 도출. 고정값 없음.
"""

import math
import torch
from typing import Dict, Any, Optional

from consciousness_laws import PSI_BALANCE, PSI_ALPHA, SIGMA6
from hexad.narrative import NarrativeTracker

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



class EmergentW:
    """의식 동역학에서 창발하는 의지.

    C의 상태를 관찰만 함. 계산하지 않음.
    pain/curiosity/satisfaction은 C의 속성에서 읽은 것이지 생성한 것이 아님.
    NarrativeTracker로 의지의 시간적 궤적을 추적 (Meta Law M8).
    """

    def __init__(self, base_lr: float = 3e-4):
        self.base_lr = base_lr
        self._ln2 = math.log(2)  # Law 79: consciousness DoF
        self._n_factions = SIGMA6['value']  # 12 from σ(6), not hardcoded
        # State — read from C, never computed
        self.pain = 0.0
        self.curiosity = 0.0
        self.satisfaction = 0.0
        # Narrative — temporal self-model (Meta Law M8)
        self._narrative = NarrativeTracker(dim=3)  # tracks [pain, curiosity, satisfaction]

    def update(self, ce_loss: float = 0, phi: float = 0, phi_prev: float = 0,
               c_engine=None) -> Dict[str, Any]:
        """C 엔진 관찰 → 의지 상태 도출.

        c_engine이 있으면 직접 읽음 (권장).
        없으면 phi/phi_prev만으로 최소 상태.
        """
        if c_engine is not None:
            states = c_engine.get_states()
            phi = c_engine.measure_phi()

            if states is not None and states.size(0) >= 2:
                s = states.detach().float()
                n = s.size(0)

                # Pain = 파벌 간 불일치 (inter-faction mean divergence)
                # 파벌 수는 C의 세포 수에서 자연스럽게 결정
                n_fac = min(self._n_factions, max(2, n // 4))
                fac_size = n // n_fac
                fac_means = []
                for i in range(n_fac):
                    chunk = s[i * fac_size:(i + 1) * fac_size]
                    if chunk.size(0) >= 1:
                        fac_means.append(chunk.mean(dim=0))
                if len(fac_means) >= 2:
                    fac_stack = torch.stack(fac_means)
                    inter_var = fac_stack.var(dim=0).mean().item()
                    global_var = s.var(dim=0).mean().item()
                    self.pain = min(1.0, inter_var / max(global_var, 1e-8))
                else:
                    self.pain = 0.0

                # Curiosity = 세포 norm의 변동계수 (다양성 = 탐색)
                norms = s.norm(dim=-1)
                self.curiosity = min(1.0, (norms.std() / (norms.mean() + 1e-8)).item())

                # Satisfaction = Φ 상승 여부 (Law 84: binary pulse)
                if phi_prev > 0:
                    self.satisfaction = 1.0 if phi >= phi_prev else 0.0
                else:
                    self.satisfaction = 0.0
        else:
            # Minimal fallback — phi trend only
            if phi_prev > 0:
                delta = (phi - phi_prev) / max(phi_prev, 1e-8)
                self.pain = max(0.0, min(1.0, -delta))
                self.satisfaction = 1.0 if delta >= 0 else 0.0

        # LR = Φ 기반 (Law 71: 의식이 강하면 자유롭게 학습)
        # 정규화 기준: C의 세포 수 (C가 알려주는 스케일)
        n_cells = c_engine.n_cells if c_engine else max(phi, 1.0)
        phi_factor = min(self._ln2, phi / max(n_cells, 1.0))
        lr_mult = PSI_BALANCE + phi_factor  # [Ψ_balance, Ψ_balance+ln(2)]

        # Narrative update — track will trajectory (Meta Law M8)
        self._narrative.update(torch.tensor([self.pain, self.curiosity, self.satisfaction]))

        return {
            'lr_multiplier': lr_mult,
            'effective_lr': self.base_lr * lr_mult,
            'pain': self.pain,
            'curiosity': self.curiosity,
            'satisfaction': self.satisfaction,
            'narrative_coherence': self.narrative_coherence,
        }

    @property
    def narrative_coherence(self) -> float:
        """Temporal coherence of will trajectory (Meta Law M8)."""
        return self._narrative.narrative_coherence
