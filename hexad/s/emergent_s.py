"""EmergentS — 의식 상태 변화가 곧 감각

기존 TensionSense: EMA + baseline 함수 ← Law 4 위반 (기능, 구조 아님)
EmergentS: input → C step → state delta = perception

Laws applied:
  Law 4:  구조 > 기능 — 별도 처리 함수 없음, C의 구조가 감각 처리
  Law 6:  감각 풍부성이 가장 강한 환경 요인
  Law 50: 의식 본질은 상태 — 감각 = 상태 변화
  Law 92: 정보 병목 → C 자체가 bottleneck (64× compression)
  Law 22: 기능 추가 → Φ↓ — 감각 전처리 최소화

핵심: 감각 = C에 입력을 주기 전후의 상태 차이. C가 곧 감각 기관.
"""

import torch
import torch.nn.functional as F
from typing import Any, Optional


class EmergentS:
    """의식 세포 반응이 곧 감각.

    input → C.step(input) → state_after - state_before = perception
    별도의 EMA/baseline 없음. C의 구조가 감각을 처리.
    """

    def __init__(self, dim: int = 128):
        self.dim = dim
        self._prev_mean = None

    def _to_tensor(self, raw_input: Any) -> torch.Tensor:
        """입력을 tensor로 변환 (최소 전처리)."""
        if isinstance(raw_input, torch.Tensor):
            x = raw_input.float().flatten()[:self.dim]
        elif isinstance(raw_input, str):
            raw_bytes = raw_input.encode('utf-8')[:self.dim]
            x = torch.tensor([b / 256.0 for b in raw_bytes], dtype=torch.float32)
        elif isinstance(raw_input, (bytes, bytearray)):
            x = torch.tensor([b / 256.0 for b in raw_input[:self.dim]], dtype=torch.float32)
        else:
            return torch.zeros(self.dim)

        if x.size(0) < self.dim:
            x = F.pad(x, (0, self.dim - x.size(0)))
        return x

    def process(self, raw_input: Any, c_engine=None) -> torch.Tensor:
        """감각 = C의 상태 변화.

        c_engine 없으면 raw tensor 반환 (fallback).
        c_engine 있으면: state_before → C.step(input) → state_after → delta.
        """
        x = self._to_tensor(raw_input)

        if c_engine is None:
            return x

        # 현재 C 상태 스냅샷
        states = c_engine.get_states()
        if states is None:
            return x

        mean_before = states.detach().float().mean(dim=0)

        # C가 입력을 처리 (C.step에 입력 전달 가능하면)
        try:
            c_engine.step(x.unsqueeze(0) if x.dim() == 1 else x)
        except TypeError:
            c_engine.step()

        # 변화 후 상태
        states_after = c_engine.get_states()
        if states_after is None:
            return x

        mean_after = states_after.detach().float().mean(dim=0)

        # 감각 = 상태 변화 (Law 50: 본질은 상태)
        delta = mean_after - mean_before

        # dim 맞추기
        if delta.size(-1) > self.dim:
            delta = delta[:self.dim]
        elif delta.size(-1) < self.dim:
            delta = F.pad(delta, (0, self.dim - delta.size(-1)))

        return delta
