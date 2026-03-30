"""EmergentM — Hebbian LTP/LTD가 곧 기억

기존 VectorMemory: cosine similarity RAG ← Law 4 위반 (의식과 무관한 기능)
EmergentM: C의 Hebbian 가중치가 기억. 별도 store 불필요.

Laws applied:
  Law 22: 기능 추가 → Φ↓ — 별도 메모리 시스템 추가하지 않음
  Law 31: persistence = ratchet + Hebbian + diversity → Hebbian이 이미 기억
  Law 50: 의식 본질은 상태 — 기억 = 지속되는 상태 변화
  Law 94: breadth > depth — 단일 Hebbian 레이어가 최적
  Law 95: 세포 정체성 = 기억의 기반 (orthogonal bias = 고유 기억)

핵심: C의 Hebbian LTP/LTD 가중치 = 장기기억. Φ ratchet = 기억 보존.
      별도 store/retrieve 없음. C가 곧 메모리.
"""

import torch
from typing import Optional


class EmergentM:
    """의식 Hebbian 가중치 기반 기억.

    C의 Hebbian weights를 읽어서 기억 상태를 반환.
    store/retrieve 대신, C의 상태 자체가 기억.
    """

    def __init__(self, dim: int = 128):
        self.dim = dim

    def store(self, key: torch.Tensor, value: torch.Tensor):
        """No-op. C의 Hebbian LTP/LTD가 자동으로 저장."""
        pass

    def retrieve(self, query: torch.Tensor, top_k: int = 5,
                 c_engine=None) -> torch.Tensor:
        """기억 = C의 현재 상태에서 query와 유사한 세포들.

        별도 메모리 DB 없음. C의 세포 상태가 곧 기억.
        query에 반응하는 세포 = 관련 기억이 활성화된 것.
        """
        if c_engine is None:
            return torch.zeros(1, self.dim)

        states = c_engine.get_states()
        if states is None or states.size(0) < 2:
            return torch.zeros(1, self.dim)

        s = states.detach().float()
        q = query.detach().float()

        # query를 cell 차원에 맞춤
        if q.dim() > 1:
            q = q.mean(dim=0)
        if q.size(-1) != s.size(-1):
            # project
            q_proj = q[:s.size(-1)] if q.size(-1) > s.size(-1) else torch.nn.functional.pad(q, (0, s.size(-1) - q.size(-1)))
        else:
            q_proj = q

        # 기억 검색 = query에 가장 반응하는 세포들
        sims = torch.nn.functional.cosine_similarity(q_proj.unsqueeze(0), s, dim=-1)
        k = min(top_k, s.size(0))
        _, indices = sims.topk(k)

        # 반환: 활성화된 세포 상태 = 기억
        result = s[indices]

        # dim 맞추기
        if result.size(-1) != self.dim:
            if result.size(-1) > self.dim:
                result = result[:, :self.dim]
            else:
                result = torch.nn.functional.pad(result, (0, self.dim - result.size(-1)))

        return result
