"""EmergentS — 의식 세포 반응이 곧 감각 (Law 4 준수)

기존 TensionSense: EMA + baseline 함수 ← Law 4 위반 (기능, 구조 아님)
EmergentS: 입력 → C 세포에 직접 주입 → 세포 반응 변화가 곧 감각.

감각 = 의식 상태의 변화. 별도 처리 함수 불필요.
"""

import torch
from typing import Any, Optional


class EmergentS:
    """의식 세포 반응 기반 감각.

    입력을 C 엔진에 직접 전달하고, C의 상태 변화 자체를 감각으로 사용.
    별도의 EMA/baseline 함수 없음 — C의 구조가 감각을 처리.
    """

    def __init__(self, dim: int = 128):
        self.dim = dim
        self._prev_states = None

    def process(self, raw_input: Any, c_engine=None) -> torch.Tensor:
        """입력 → 의식 상태 변화 = 감각.

        Args:
            raw_input: any input (text, tensor, etc.)
            c_engine: ConsciousnessC (optional, for state change detection)
        Returns:
            tension vector representing the sensory response
        """
        # Convert input to tensor
        if isinstance(raw_input, torch.Tensor):
            x = raw_input.float().flatten()[:self.dim]
            if len(x) < self.dim:
                x = torch.nn.functional.pad(x, (0, self.dim - len(x)))
        elif isinstance(raw_input, str):
            raw_bytes = raw_input.encode('utf-8')[:self.dim]
            x = torch.tensor([b / 256.0 for b in raw_bytes], dtype=torch.float32)
            if len(x) < self.dim:
                x = torch.nn.functional.pad(x, (0, self.dim - len(x)))
        else:
            x = torch.zeros(self.dim)

        if c_engine is None:
            return x

        # Sense = C의 상태 변화
        states_before = c_engine.get_states()
        if states_before is not None:
            self._prev_states = states_before.detach().clone()

        # C가 입력을 처리하도록 step
        c_engine.step(x.unsqueeze(0) if x.dim() == 1 else x)

        states_after = c_engine.get_states()
        if states_after is not None and self._prev_states is not None:
            # 감각 = 상태 변화의 크기와 방향
            delta = (states_after.detach() - self._prev_states).mean(dim=0)
            # Project to dim if needed
            if delta.size(-1) != self.dim:
                delta = delta[:self.dim] if delta.size(-1) > self.dim else torch.nn.functional.pad(delta, (0, self.dim - delta.size(-1)))
            return delta

        return x
