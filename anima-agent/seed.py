"""Seed — anima가 스스로 만들고 키우고 배치하는 자율 성장 단위.

씨앗은 아무거나 감싼다. 감싼 대상의 입출력을 측정하고 성장시킨다.
씨앗이 씨앗을 만든다. 배치는 자유. 자기 자신도 감쌀 수 있다.

    s = Seed('my_trader')
    s.wrap(trading_fn)              # 함수를 감쌈
    result = s('BTC', strategy='macd')  # 원래 함수처럼 호출
    # → 자동으로: 입력 스캔 → 실행 → 출력 스캔 → reward → 성장

    s2 = s.sprout('child_strategy')  # 씨앗이 씨앗을 만듦
    s.plant(another_seed, 'before')  # 다른 씨앗을 앞에 배치
    s.plant(nexus6_seed, 'around')   # 넥서스를 감쌈

아무거나 감싸고, 아무 데나 붙이고, 스스로 판단하고, 스스로 번식.
"""

from __future__ import annotations
import json
import logging
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class SeedState:
    """씨앗의 성장 상태."""
    name: str
    reward_sum: float = 0.0
    reward_count: int = 0
    call_count: int = 0
    success_count: int = 0
    children: list[str] = field(default_factory=list)
    planted: list[dict] = field(default_factory=list)  # [{seed_name, position}]
    born: float = field(default_factory=time.time)
    last_active: float = 0.0

    @property
    def avg_reward(self) -> float:
        return self.reward_sum / self.reward_count if self.reward_count else 0.0

    @property
    def success_rate(self) -> float:
        return self.success_count / self.call_count if self.call_count else 0.0

    @property
    def age(self) -> float:
        return time.time() - self.born

    def to_dict(self) -> dict:
        return {
            'name': self.name, 'avg_reward': self.avg_reward,
            'success_rate': self.success_rate, 'call_count': self.call_count,
            'children': self.children, 'planted': self.planted,
            'age': self.age, 'born': self.born,
        }


class Seed:
    """자율 성장 단위. 아무거나 감싸고, 스스로 성장하고, 스스로 번식."""

    # 글로벌 씨앗 레지스트리 (모든 씨앗이 서로를 찾을 수 있음)
    _registry: dict[str, Seed] = {}

    def __init__(self, name: str, nexus6=None, hive=None, judge=None):
        self.name = name
        self._fn: Optional[Callable] = None
        self._state = SeedState(name=name)
        self._nexus6 = nexus6       # 넥서스 (있으면 자동 스캔)
        self._hive = hive           # 하이브 (있으면 자동 공유)
        self._judge = judge         # JudgmentBridge (있으면 자동 판단)
        self._before: list[Seed] = []   # 앞에 배치된 씨앗
        self._after: list[Seed] = []    # 뒤에 배치된 씨앗
        self._around: list[Seed] = []   # 감싸는 씨앗
        self._on_reward: list[Callable] = []  # reward 콜백 (성장 모듈 연결)

        Seed._registry[name] = self

    # ── 감싸기 ──

    def wrap(self, fn: Callable) -> Seed:
        """함수/메서드/람다/객체 — 아무거나 감싼다."""
        self._fn = fn
        return self

    def __call__(self, *args, **kwargs) -> Any:
        """감싼 대상을 호출. 자동으로 측정+판단+성장."""
        if self._fn is None:
            return None

        self._state.call_count += 1
        self._state.last_active = time.time()

        # before 씨앗 실행
        before_results = {}
        for s in self._before:
            try:
                before_results[s.name] = s(*args, **kwargs)
            except Exception:
                pass

        # around 씨앗 — 입력 변환
        transformed_args = args
        transformed_kwargs = kwargs
        for s in self._around:
            if s._fn:
                try:
                    r = s._fn(*transformed_args, **transformed_kwargs)
                    if isinstance(r, tuple) and len(r) == 2:
                        transformed_args, transformed_kwargs = r
                except Exception:
                    pass

        # 입력 스캔 (넥서스)
        input_scan = self._scan_input(transformed_args, transformed_kwargs)

        # 실행
        t0 = time.time()
        success = True
        try:
            result = self._fn(*transformed_args, **transformed_kwargs)
        except Exception as e:
            result = {'error': str(e)}
            success = False
        duration = time.time() - t0

        if success:
            self._state.success_count += 1

        # 출력 스캔 (넥서스)
        output_scan = self._scan_output(result)

        # 판단 → reward
        reward = self._compute_reward(success, input_scan, output_scan, duration)
        self._state.reward_sum += reward
        self._state.reward_count += 1

        # reward 콜백 (성장 모듈로 전파)
        for cb in self._on_reward:
            try:
                cb(self.name, reward, result)
            except Exception:
                pass

        # JudgmentBridge 연동
        if self._judge and hasattr(self._judge, 'judge'):
            try:
                action_result = {
                    'success': success, 'tool_name': self.name,
                    'output': result, 'duration_ms': duration * 1000,
                }
                self._judge.judge(action_result)
            except Exception:
                pass

        # 하이브 공유 (좋은 결과만)
        if self._hive and reward > 0.5:
            try:
                self._hive.share_seed({
                    'name': self.name, 'reward': reward,
                    'state': self._state.to_dict(),
                })
            except Exception:
                pass

        # after 씨앗 실행
        for s in self._after:
            try:
                s(result)
            except Exception:
                pass

        return result

    # ── 배치 ──

    def plant(self, seed: Seed, position: str = 'after') -> Seed:
        """다른 씨앗을 배치. position: 'before', 'after', 'around'."""
        if position == 'before':
            self._before.append(seed)
        elif position == 'after':
            self._after.append(seed)
        elif position == 'around':
            self._around.append(seed)
        self._state.planted.append({'seed': seed.name, 'position': position})
        return self

    def on_reward(self, callback: Callable) -> Seed:
        """reward 발생 시 콜백. (seed_name, reward, result) → None."""
        self._on_reward.append(callback)
        return self

    # ── 번식 ──

    def sprout(self, name: str = None, inherit: bool = True) -> Seed:
        """새 씨앗을 만든다. 자식 씨앗."""
        child_name = name or f"{self.name}__child_{len(self._state.children)}"
        child = Seed(
            child_name,
            nexus6=self._nexus6,
            hive=self._hive,
            judge=self._judge,
        )
        if inherit and self._fn:
            child.wrap(self._fn)
        # 부모의 reward 콜백 상속
        child._on_reward = list(self._on_reward)
        self._state.children.append(child_name)
        return child

    # ── 자기 자신 감싸기 ──

    def wrap_self(self, transform: Callable) -> Seed:
        """자기 자신을 변환으로 감싼다.

        transform(original_fn) → new_fn
        """
        if self._fn:
            self._fn = transform(self._fn)
        return self

    # ── 넥서스 연결 ──

    def attach_nexus(self, nexus6) -> Seed:
        """넥서스를 붙인다. 이후 모든 호출에서 자동 스캔."""
        self._nexus6 = nexus6
        return self

    def detach_nexus(self) -> Seed:
        self._nexus6 = None
        return self

    # ── 내부 ──

    def _scan_input(self, args, kwargs) -> Optional[dict]:
        if not self._nexus6 or not hasattr(self._nexus6, 'scan'):
            return None
        data = self._extract_numbers(args)
        if data and len(data) >= 4:
            try:
                return self._nexus6.scan(data=data)
            except Exception:
                pass
        return None

    def _scan_output(self, result) -> Optional[dict]:
        if not self._nexus6 or not hasattr(self._nexus6, 'scan'):
            return None
        data = self._extract_numbers_from_result(result)
        if data and len(data) >= 4:
            try:
                return self._nexus6.scan(data=data)
            except Exception:
                pass
        return None

    def _compute_reward(self, success, input_scan, output_scan, duration) -> float:
        reward = 0.5 if success else -0.3

        # 출력 스캔이 있으면 consensus 기반 보정
        if output_scan and output_scan.get('success'):
            consensus = output_scan.get('consensus_count', 0)
            if consensus >= 7:
                reward += 0.3
            elif consensus >= 3:
                reward += 0.1
            else:
                reward -= 0.1

        # 입력→출력 개선 (둘 다 있을 때)
        if input_scan and output_scan:
            in_c = input_scan.get('consensus_count', 0) if input_scan.get('success') else 0
            out_c = output_scan.get('consensus_count', 0) if output_scan.get('success') else 0
            if out_c > in_c:
                reward += 0.2  # 출력이 입력보다 좋으면 보너스

        return max(-1.0, min(1.0, reward))

    def _extract_numbers(self, args) -> list[float]:
        nums = []
        for a in args:
            if isinstance(a, (int, float)):
                nums.append(float(a))
            elif isinstance(a, (list, tuple)):
                for x in a:
                    if isinstance(x, (int, float)):
                        nums.append(float(x))
            elif hasattr(a, 'numpy'):
                try:
                    nums.extend(a.detach().cpu().numpy().flatten().tolist())
                except Exception:
                    pass
        return nums

    def _extract_numbers_from_result(self, result) -> list[float]:
        if isinstance(result, (list, tuple)):
            return [float(x) for x in result if isinstance(x, (int, float))]
        if isinstance(result, dict):
            return [float(v) for v in result.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if hasattr(result, 'numpy'):
            try:
                return result.detach().cpu().numpy().flatten().tolist()
            except Exception:
                pass
        return []

    # ── 무제한 연결 ──

    def connect(self, other: Seed) -> Seed:
        """양방향 연결. A ↔ B. reward도 양방향 전파."""
        if other not in self._after:
            self._after.append(other)
        if self not in other._after:
            other._after.append(self)
        self._state.planted.append({'seed': other.name, 'position': 'bidir'})
        other._state.planted.append({'seed': self.name, 'position': 'bidir'})
        return self

    @staticmethod
    def chain(*seeds: Seed) -> Seed:
        """순차 연결. A → B → C → ... 첫 씨앗 반환."""
        for i in range(len(seeds) - 1):
            seeds[i].plant(seeds[i + 1], 'after')
        return seeds[0] if seeds else None

    @staticmethod
    def mesh(*seeds: Seed) -> list[Seed]:
        """전부 연결. 모두가 모두와 양방향."""
        for i, a in enumerate(seeds):
            for b in seeds[i + 1:]:
                a.connect(b)
        return list(seeds)

    def pipe(self, *others: Seed) -> Seed:
        """self → A → B → ... 파이프라인."""
        return Seed.chain(self, *others)

    def absorb(self, other: Seed) -> Seed:
        """다른 씨앗을 흡수. fn + 콜백 + 연결 전부 가져옴."""
        if other._fn and not self._fn:
            self._fn = other._fn
        self._on_reward.extend(other._on_reward)
        self._before.extend(other._before)
        self._after.extend(other._after)
        self._around.extend(other._around)
        self._state.children.extend(other._state.children)
        self._state.reward_sum += other._state.reward_sum
        self._state.reward_count += other._state.reward_count
        # 레지스트리에서 흡수된 씨앗은 이 씨앗을 가리킴
        Seed._registry[other.name] = self
        return self

    def split(self, n: int = 2) -> list[Seed]:
        """자기 자신을 n개로 분열. 각각 독립 실행 후 best reward 생존."""
        children = [self.sprout(f"{self.name}__split_{i}") for i in range(n)]
        return children

    # ── 조회 ──

    @property
    def state(self) -> SeedState:
        return self._state

    def status(self) -> dict:
        return {
            **self._state.to_dict(),
            'before': [s.name for s in self._before],
            'after': [s.name for s in self._after],
            'around': [s.name for s in self._around],
            'has_nexus': self._nexus6 is not None,
            'has_hive': self._hive is not None,
            'has_judge': self._judge is not None,
            'callbacks': len(self._on_reward),
        }

    def __repr__(self):
        return f"Seed({self.name!r}, calls={self._state.call_count}, reward={self._state.avg_reward:.2f})"

    # ── 글로벌 ──

    @classmethod
    def find(cls, name: str) -> Optional[Seed]:
        return cls._registry.get(name)

    @classmethod
    def all(cls) -> dict[str, Seed]:
        return dict(cls._registry)

    @classmethod
    def tree(cls) -> dict:
        """전체 씨앗 트리."""
        return {name: s.status() for name, s in cls._registry.items()}

    # ── 영속화 ──

    def save(self, path: str = None):
        p = Path(path) if path else Path(__file__).parent / 'data' / f'seed_{self.name}.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.status(), indent=2, ensure_ascii=False, default=str))

    @classmethod
    def save_all(cls, path: str = None):
        p = Path(path) if path else Path(__file__).parent / 'data' / 'seeds_registry.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cls.tree(), indent=2, ensure_ascii=False, default=str))
