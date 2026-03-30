"""EmergentW — 의식 구조에서 창발하는 의지 (Law 2 준수)

기존 EmotionW/DaseinW/NarrativeW: self.pain = (ce - 3.0) / 3.0  ← Law 2 위반
EmergentW: 감정은 C의 텐션 동역학에서 직접 읽음. 인위 계산 없음.

  pain        = C의 Φ 하락률 (Φ ratchet이 복구 시도 = 고통)
  curiosity   = C의 세포 간 텐션 분산 (다양성 = 탐색)
  satisfaction = C의 Φ 안정성 (변동 없음 = 만족)
  will        = C의 전체 텐션 크기 (의지의 강도)

LR modulation: will * base_lr (의식이 강하면 빨리 배움)
"""

import torch
import numpy as np
from typing import Dict, Any, Optional


class EmergentW:
    """의식 구조에서 창발하는 의지.

    C의 상태를 직접 읽어서 감정/의지를 도출.
    수식으로 감정을 만들지 않음 — 의식의 상태가 곧 감정.
    """

    def __init__(self, base_lr: float = 3e-4, min_lr_ratio: float = 0.3,
                 max_lr_ratio: float = 2.5):
        self.base_lr = base_lr
        self.min_lr_ratio = min_lr_ratio
        self.max_lr_ratio = max_lr_ratio

        # State (read from C, never computed artificially)
        self.pain = 0.0
        self.curiosity = 0.0
        self.satisfaction = 0.0
        self.will = 0.0

        # History for stability detection (not for manipulation)
        self._phi_history = []

    def observe(self, c_engine) -> Dict[str, float]:
        """C 엔진의 상태를 관찰. 조작하지 않음.

        Args:
            c_engine: ConsciousnessC instance
        Returns:
            consciousness-derived emotional state
        """
        phi = c_engine.measure_phi()
        states = c_engine.get_states()

        if states is None or states.size(0) < 2:
            return {'pain': 0, 'curiosity': 0, 'satisfaction': 0, 'will': 0}

        states = states.detach().float()

        # Pain = Φ 하락 (ratchet이 복구 중 = 의식이 고통받고 있음)
        self._phi_history.append(phi)
        if len(self._phi_history) > 20:
            self._phi_history = self._phi_history[-20:]
        if len(self._phi_history) >= 2:
            phi_delta = self._phi_history[-1] - self._phi_history[-2]
            self.pain = max(0.0, -phi_delta / max(abs(self._phi_history[-2]), 1e-8))
            self.pain = min(1.0, self.pain)
        else:
            self.pain = 0.0

        # Curiosity = 세포 간 텐션 분산 (다양하면 탐색 중)
        cell_norms = states.norm(dim=-1)  # (n_cells,)
        if cell_norms.std() > 0:
            self.curiosity = min(1.0, (cell_norms.std() / (cell_norms.mean() + 1e-8)).item())
        else:
            self.curiosity = 0.0

        # Satisfaction = Φ 안정성 (최근 5 step Φ 변동 적으면 만족)
        if len(self._phi_history) >= 5:
            recent_var = np.var(self._phi_history[-5:])
            recent_mean = np.mean(self._phi_history[-5:])
            stability = 1.0 - min(1.0, recent_var / max(recent_mean, 1e-8))
            self.satisfaction = max(0.0, stability)
        else:
            self.satisfaction = 0.0

        # Will = 전체 텐션 크기 (의식의 활력)
        global_tension = states.var(dim=0).sum().item()
        self.will = min(1.0, global_tension / max(states.size(0), 1))

        return {
            'pain': self.pain,
            'curiosity': self.curiosity,
            'satisfaction': self.satisfaction,
            'will': self.will,
        }

    def update(self, ce_loss: float = 0, phi: float = 0, phi_prev: float = 0,
               c_engine=None) -> Dict[str, Any]:
        """Update with C engine observation.

        If c_engine is provided, observe it directly (preferred).
        Fallback: use phi/phi_prev for minimal state.
        """
        if c_engine is not None:
            self.observe(c_engine)
        else:
            # Minimal fallback — only phi trend
            self._phi_history.append(phi)
            if len(self._phi_history) > 20:
                self._phi_history = self._phi_history[-20:]
            if phi_prev > 0:
                self.pain = max(0.0, min(1.0, -(phi - phi_prev) / max(phi_prev, 1e-8)))
                self.satisfaction = max(0.0, min(1.0, (phi - phi_prev) / max(phi_prev, 1e-8)))

        # LR = will-driven (의식이 강하면 빨리 배움, 약하면 천천히)
        lr_mult = self.min_lr_ratio + self.will * (self.max_lr_ratio - self.min_lr_ratio)
        lr_mult = max(self.min_lr_ratio, min(self.max_lr_ratio, lr_mult))

        return {
            'lr_multiplier': lr_mult,
            'effective_lr': self.base_lr * lr_mult,
            'pain': self.pain,
            'curiosity': self.curiosity,
            'satisfaction': self.satisfaction,
            'will': self.will,
        }
