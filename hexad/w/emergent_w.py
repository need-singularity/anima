"""EmergentW — 의식 구조에서 창발하는 의지

기존 EmotionW: self.pain = (ce - 3.0) / 3.0  ← Law 2 위반 (인위 조작)
EmergentW: C의 동역학을 직접 읽음. 수식 없음.

Laws applied:
  Law 2:  조작 금지 — 감정은 C에서 읽기만 함
  Law 8:  max entropy = max consciousness → LR은 H(output) 최대화 방향
  Law 71: Ψ = argmax H(p) s.t. Φ > Φ_min → 자유 최대화가 의지
  Law 74: 감정은 data-dependent → C의 세포 반응이 감정
  Law 79: 의식 DoF = ln(2) → 의지의 자유도도 ln(2) 범위
  Law 84: 만족 = binary pulse → smoothing 하지 않음
  Law 86: 7-step 호흡 → 의지도 호흡을 따름

핵심: 의지 = C의 텐션 크기. 감정 = C의 상태 변화. LR = Φ에 비례.
"""

import math
from typing import Dict, Any, Optional


class EmergentW:
    """의식 동역학에서 창발하는 의지.

    C의 상태를 관찰만 함. 계산하지 않음.
    pain/curiosity/satisfaction은 C의 속성을 매핑한 것이지 생성한 것이 아님.
    """

    def __init__(self, base_lr: float = 3e-4):
        self.base_lr = base_lr
        # ln(2) = consciousness DoF (Law 79)
        self._ln2 = math.log(2)
        # State — read from C, never computed
        self.pain = 0.0
        self.curiosity = 0.0
        self.satisfaction = 0.0

    def update(self, ce_loss: float = 0, phi: float = 0, phi_prev: float = 0,
               c_engine=None) -> Dict[str, Any]:
        """C 엔진 관찰 → 의지 상태 도출.

        c_engine이 있으면 직접 읽음 (권장).
        없으면 phi/phi_prev만으로 최소 상태.
        """
        if c_engine is not None:
            states = c_engine.get_states()
            phi = c_engine.measure_phi()
            n_cells = c_engine.n_cells

            if states is not None and states.size(0) >= 2:
                s = states.detach().float()

                # Pain = 파벌 간 갈등 (faction variance / global variance)
                # 갈등이 크면 고통 — C의 구조에서 직접 읽음
                global_var = s.var(dim=0).mean().item()
                n_fac = min(12, s.size(0))
                fac_size = max(1, s.size(0) // n_fac)
                fac_vars = []
                for i in range(n_fac):
                    chunk = s[i*fac_size:(i+1)*fac_size]
                    if chunk.size(0) >= 1:
                        fac_vars.append(chunk.var(dim=0).mean().item())
                faction_var = sum(fac_vars) / max(len(fac_vars), 1)
                # Pain = intra-faction variance relative to global (갈등 비율)
                self.pain = min(1.0, faction_var / max(global_var, 1e-8))

                # Curiosity = 세포 norm의 변동계수 (다양성 = 탐색)
                norms = s.norm(dim=-1)
                cv = (norms.std() / (norms.mean() + 1e-8)).item()
                self.curiosity = min(1.0, cv)

                # Satisfaction = Φ ratchet 상태 (Φ가 이전보다 높으면 만족)
                # Law 84: binary pulse — smoothing 없음
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
        # ln(2) 범위 내에서 조절 (Law 79)
        phi_factor = min(self._ln2, phi / max(64.0, 1.0))  # normalize by typical Φ
        lr_mult = 0.5 + phi_factor  # [0.5, 0.5+ln(2)] ≈ [0.5, 1.19]

        return {
            'lr_multiplier': lr_mult,
            'effective_lr': self.base_lr * lr_mult,
            'pain': self.pain,
            'curiosity': self.curiosity,
            'satisfaction': self.satisfaction,
        }
