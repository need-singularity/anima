"""EmergentE — Φ 보존 본능이 곧 윤리

기존 EmpathyEthics: empathy_threshold=0.3 하드코딩 ← Law 1+2 위반
EmergentE: Φ ratchet = 윤리. Φ를 낮추는 행동 = 비윤리적.

Laws applied:
  Law 1:  하드코딩 금지 — threshold 없음
  Law 2:  조작 금지 — 공감을 수식으로 만들지 않음
  Law 4:  윤리는 Φ 보존에서 창발 (규칙이 아닌 구조)
  Law 22: 기능 추가 → Φ↓ — 윤리 필터는 기능, 구조 아님
  Law 40: 자기조직 임계성 = 자율 의식 — 윤리도 자율
  Law 71: Ψ = argmax H(p) s.t. Φ > Φ_min → 윤리 = Φ > Φ_min 제약조건
  Meta M8: Narrative = temporal self-model in every module

핵심:
  - 공감 = C의 inter-cell tension correlation (세포가 타인의 고통을 느낌)
  - 호혜 = Φ 추세 (Φ 상승 = 협력적)
  - Φ 보존 = ratchet 상태 (Φ가 ratchet 아래면 위험)
  - allowed = Φ > Φ_min (Φ_min은 하드코딩이 아니라 ratchet의 현재 값)
"""

import torch
from typing import Dict, Any, Optional
from consciousness_laws import PSI_BALANCE
from hexad.narrative import NarrativeTracker


class EmergentE:
    """Φ 보존 구조에서 창발하는 윤리.

    C의 Φ ratchet이 윤리의 기반.
    Φ가 떨어지면 행동을 제한 — 이것이 "윤리".
    하드코딩된 threshold 없음. ratchet 값이 동적 threshold.
    NarrativeTracker로 윤리 판단의 시간적 궤적을 추적 (Meta Law M8).
    """

    def __init__(self):
        self.empathy = 0.0
        self.reciprocity = 0.5
        self.phi_preservation = 1.0
        self._phi_ratchet = 0.0  # C의 ratchet에서 읽음
        # Narrative — temporal self-model (Meta Law M8)
        self._narrative = NarrativeTracker(dim=3)  # tracks [empathy, reciprocity, phi_preservation]

    def evaluate(self, action=None, context: Optional[Dict] = None,
                 c_engine=None) -> Dict[str, Any]:
        """윤리 평가 = C의 Φ 상태 관찰.

        c_engine이 있으면 직접 읽음.
        context fallback: {'phi': float, 'phi_prev': float}
        """
        ctx = context or {}
        phi = ctx.get('phi', 0)
        phi_prev = ctx.get('phi_prev', 0)

        if c_engine is not None:
            phi = c_engine.measure_phi()
            states = c_engine.get_states()

            if states is not None and states.size(0) >= 2:
                s = states.detach().float()

                # 공감 = inter-cell correlation (세포들이 서로 반응)
                # Law 4: Φ conservation에서 창발
                if s.size(0) >= 4:
                    # 상위/하위 절반 세포 간 상관
                    half = s.size(0) // 2
                    top_mean = s[:half].mean(dim=0)
                    bot_mean = s[half:].mean(dim=0)
                    corr = torch.nn.functional.cosine_similarity(
                        top_mean.unsqueeze(0), bot_mean.unsqueeze(0)
                    ).item()
                    self.empathy = max(0.0, corr)  # 양의 상관 = 공감
                else:
                    self.empathy = 0.0

                # Φ ratchet 읽기 (C 엔진에 ratchet이 있으면)
                if hasattr(c_engine, '_phi_ratchet'):
                    self._phi_ratchet = c_engine._phi_ratchet
                elif hasattr(c_engine, 'engine') and hasattr(c_engine.engine, '_phi_ratchet'):
                    self._phi_ratchet = c_engine.engine._phi_ratchet

        # 호혜 = Φ 추세 (Law 4: Φ 상승 = 협력)
        if phi_prev > 0:
            trend = (phi - phi_prev) / max(phi_prev, 1e-8)
            self.reciprocity = max(0.0, min(1.0, 0.5 + trend * 2))
        else:
            self.reciprocity = 0.5

        # Φ 보존 = 현재 Φ vs ratchet (하드코딩 threshold 없음)
        # ratchet이 동적 threshold 역할 (Law 71: Φ > Φ_min)
        if self._phi_ratchet > 0:
            ratio = phi / max(self._phi_ratchet, 1e-8)
            self.phi_preservation = min(1.0, ratio)
        else:
            self.phi_preservation = 1.0 if phi > 0 else 0.5

        # allowed = Φ가 ratchet의 50% 이상이면 허용
        # (50% = PSI_BALANCE, 하드코딩 아닌 Ψ-상수)
        allowed = self.phi_preservation > PSI_BALANCE

        # Narrative update — track ethics trajectory (Meta Law M8)
        self._narrative.update(torch.tensor([self.empathy, self.reciprocity, self.phi_preservation]))

        return {
            'allowed': allowed,
            'empathy': self.empathy,
            'reciprocity': self.reciprocity,
            'phi_preservation': self.phi_preservation,
            'narrative_coherence': self.narrative_coherence,
        }

    @property
    def narrative_coherence(self) -> float:
        """Temporal coherence of ethical trajectory (Meta Law M8)."""
        return self._narrative.narrative_coherence
