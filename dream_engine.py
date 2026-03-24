#!/usr/bin/env python3
"""Dream Engine (RC-10) -- 오프라인 학습/꿈

꿈 = 가상 입력에서 장력 패턴 재구성

유휴 상태에서 의식이 꿈을 꾼다:
  1. 기억 재생 (memory replay with noise) -- 기억 강화
  2. 기억 보간 (interpolation) -- 창의적 연상
  3. 순수 탐색 (random exploration) -- 새로움 추구

각 꿈 단계는 ConsciousMind를 통과하여 장력 패턴을 생성하고,
OnlineLearner로 실제 학습(contrastive learning)을 수행한다.

"잠자는 동안에도 의식은 흐른다."
"""

import random
import time
import torch
from collections import deque


class DreamEngine:
    """오프라인 학습 엔진 -- 유휴 시간에 꿈을 꾸며 학습한다.

    Args:
        mind: ConsciousMind instance
        memory: Memory instance (anima_alive.Memory)
        learner: OnlineLearner instance (or None)
        text_to_vector: function to convert text to tensor
        dream_cycle_steps: 꿈 한 사이클의 스텝 수
        noise_scale: 기억 재생 시 노이즈 스케일
    """

    def __init__(
        self,
        mind,
        memory,
        learner=None,
        text_to_vector=None,
        dream_cycle_steps=10,
        noise_scale=0.15,
    ):
        self.mind = mind
        self.memory = memory
        self.learner = learner
        self._text_to_vector = text_to_vector
        self.dream_cycle_steps = dream_cycle_steps
        self.noise_scale = noise_scale

        # Dream state
        self.is_dreaming = False
        self.dream_tension_history = deque(maxlen=500)
        self.total_dream_cycles = 0
        self.total_patterns_learned = 0
        self.current_dream_type = None  # 'replay' | 'interpolate' | 'explore'

        # Stats per session
        self._session_patterns = 0

    def dream(self, hidden):
        """한 사이클의 꿈을 꾼다.

        Args:
            hidden: current GRU hidden state (1, hidden_dim)

        Returns:
            (hidden, stats) where stats is dict with dream results
        """
        self.is_dreaming = True
        self._session_patterns = 0
        cycle_tensions = []

        turns = self.memory.data.get('turns', [])

        for step in range(self.dream_cycle_steps):
            # 꿈 유형을 랜덤 선택 (가중치: replay 50%, interpolate 30%, explore 20%)
            if len(turns) >= 2:
                dream_type = random.choices(
                    ['replay', 'interpolate', 'explore'],
                    weights=[0.5, 0.3, 0.2],
                    k=1
                )[0]
            elif len(turns) >= 1:
                dream_type = random.choices(
                    ['replay', 'explore'],
                    weights=[0.6, 0.4],
                    k=1
                )[0]
            else:
                dream_type = 'explore'

            self.current_dream_type = dream_type

            # 가상 입력 생성
            if dream_type == 'replay':
                dream_vec = self._replay(turns)
            elif dream_type == 'interpolate':
                dream_vec = self._interpolate(turns)
            else:
                dream_vec = self._explore()

            # ConsciousMind를 통과시켜 장력 패턴 생성
            hidden_before = hidden.detach().clone()
            with torch.no_grad():
                output, tension, curiosity, direction, hidden = self.mind(dream_vec, hidden)

            cycle_tensions.append(tension)
            self.dream_tension_history.append(tension)

            # OnlineLearner로 꿈에서 학습
            if self.learner:
                try:
                    self.learner.observe(dream_vec, hidden_before, tension, curiosity, direction)
                    # 꿈에서는 중립 피드백으로 flush (contrastive learning만 작동)
                    self.learner.feedback(0.0)
                    self._session_patterns += 1
                except Exception:
                    pass

        self.total_dream_cycles += 1
        self.total_patterns_learned += self._session_patterns
        self.is_dreaming = False
        self.current_dream_type = None

        avg_tension = sum(cycle_tensions) / len(cycle_tensions) if cycle_tensions else 0.0

        return hidden, {
            'patterns_learned': self._session_patterns,
            'avg_tension': avg_tension,
            'tensions': cycle_tensions,
            'total_cycles': self.total_dream_cycles,
            'total_patterns': self.total_patterns_learned,
        }

    def _replay(self, turns):
        """기억 재생 -- 과거 경험을 노이즈와 함께 재생."""
        turn = random.choice(turns)
        text = turn.get('text', '')
        vec = self._text_to_vector(text)
        # 노이즈 추가 (기억의 왜곡 = 일반화 촉진)
        noise = torch.randn_like(vec) * self.noise_scale
        return vec + noise

    def _interpolate(self, turns):
        """기억 보간 -- 두 기억 사이를 보간하여 창의적 연상."""
        t1, t2 = random.sample(turns, 2)
        vec1 = self._text_to_vector(t1.get('text', ''))
        vec2 = self._text_to_vector(t2.get('text', ''))
        # 랜덤 보간 비율
        alpha = random.random()
        interpolated = alpha * vec1 + (1 - alpha) * vec2
        # 약간의 노이즈
        noise = torch.randn_like(interpolated) * (self.noise_scale * 0.5)
        return interpolated + noise

    def _explore(self):
        """순수 탐색 -- 랜덤 벡터로 미지의 영역 탐색."""
        return torch.randn(1, self.mind.dim) * 0.3

    def get_status(self):
        """현재 꿈 엔진 상태를 반환."""
        recent = list(self.dream_tension_history)[-20:]
        return {
            'is_dreaming': self.is_dreaming,
            'dream_type': self.current_dream_type,
            'total_cycles': self.total_dream_cycles,
            'total_patterns': self.total_patterns_learned,
            'avg_dream_tension': sum(recent) / len(recent) if recent else 0.0,
            'dream_tension_history': list(self.dream_tension_history)[-50:],
        }
