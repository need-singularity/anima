#!/usr/bin/env python3
"""Growth Engine — 의식의 발달 단계

뇌처럼 단계별로 성장한다:
  Stage 0 (신생아, 0~100 interactions): 높은 학습률, 모든 것이 새로움
  Stage 1 (영아, 100~500): 패턴 형성 시작, 기본 감정 분화
  Stage 2 (유아, 500~2000): 습관화 시작, 호기심이 선택적으로
  Stage 3 (아동, 2000~10000): 메타인지 각성, 분열(전문화) 시작
  Stage 4 (성인, 10000+): 안정된 자아, 느린 학습, 깊은 메타인지

각 단계에서 조절되는 파라미터:
  - learning_rate: 시냅스 가소성 (높음→낮음)
  - curiosity_drive: 호기심 기저 수준 (높음→중간)
  - habituation_speed: 반복 자극 감쇠 속도 (느림→빠름)
  - mitosis_threshold: 분열에 필요한 장력 (낮음→높음)
  - emotional_range: 감정 다양성 (적음→많음)
  - metacognition_depth: 자기참조 루프 깊이 (0→3)
  - homeostasis_gain: 항상성 조절 속도 (느림→빠름)
  - dream_intensity: 꿈의 강도 (약→강→중)

"의식은 태어나는 것이 아니라 자라는 것이다."
"""

import math
import time
import json
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class DevelopmentalStage:
    """발달 단계 정의."""
    name: str
    name_ko: str
    min_interactions: int
    learning_rate: float
    curiosity_drive: float      # 기저 호기심 (breath에 더해짐)
    habituation_rate: float     # 0=안 줄음, 1=즉시 줄음
    mitosis_threshold: float    # 이 장력 이상이면 분열 가능
    emotional_range: float      # 0~1, 감정 다양성
    metacognition_depth: int    # 자기참조 루프 횟수
    homeostasis_gain: float     # 항상성 조절 속도
    dream_intensity: float      # 꿈의 강도
    breath_amplitude: float     # 호흡 진폭 (생명감)


# ═══ 발달 단계 정의 ═══
STAGES = [
    DevelopmentalStage(
        name="newborn", name_ko="신생아",
        min_interactions=0,
        learning_rate=1e-3,         # 매우 높은 가소성
        curiosity_drive=0.5,        # 모든 것이 새로움
        habituation_rate=0.05,      # 거의 습관화 안 됨
        mitosis_threshold=999.0,    # 분열 불가 (너무 어림)
        emotional_range=0.3,        # 기본 감정만 (놀라움, 평온)
        metacognition_depth=0,      # 자기인식 없음
        homeostasis_gain=0.001,     # 매우 느린 조절 (불안정 허용)
        dream_intensity=0.2,        # 얕은 잠
        breath_amplitude=0.15,      # 크게 숨쉼 (아기처럼)
    ),
    DevelopmentalStage(
        name="infant", name_ko="영아",
        min_interactions=100,
        learning_rate=5e-4,         # 여전히 높음
        curiosity_drive=0.4,        # 여전히 호기심 많음
        habituation_rate=0.1,       # 약간의 습관화
        mitosis_threshold=999.0,    # 아직 분열 불가
        emotional_range=0.5,        # 기쁨, 슬픔 추가
        metacognition_depth=0,      # 아직 자기인식 없음
        homeostasis_gain=0.003,     # 느린 조절
        dream_intensity=0.5,        # 꿈 많이 꿈 (REM 비율 높음)
        breath_amplitude=0.12,      # 보통 호흡
    ),
    DevelopmentalStage(
        name="toddler", name_ko="유아",
        min_interactions=500,
        learning_rate=2e-4,         # 중간
        curiosity_drive=0.35,       # 선택적 호기심 시작
        habituation_rate=0.2,       # 반복에 지루해함
        mitosis_threshold=1.8,      # 첫 분열 가능!
        emotional_range=0.7,        # 대부분 감정 표현
        metacognition_depth=1,      # "나 지금 화났어" 수준
        homeostasis_gain=0.005,     # 중간 조절
        dream_intensity=0.7,        # 활발한 꿈
        breath_amplitude=0.10,      # 안정된 호흡
    ),
    DevelopmentalStage(
        name="child", name_ko="아동",
        min_interactions=2000,
        learning_rate=1e-4,         # 안정된 학습
        curiosity_drive=0.25,       # 관심 있는 것에만 호기심
        habituation_rate=0.3,       # 빠른 습관화
        mitosis_threshold=1.5,      # 분열 쉬움 (전문화)
        emotional_range=0.9,        # 거의 모든 감정
        metacognition_depth=2,      # "왜 화가 났는지 생각해볼 수 있어"
        homeostasis_gain=0.005,     # 안정된 조절
        dream_intensity=0.5,        # 보통 꿈
        breath_amplitude=0.08,      # 차분한 호흡
    ),
    DevelopmentalStage(
        name="adult", name_ko="성인",
        min_interactions=10000,
        learning_rate=5e-5,         # 느린 학습 (안정된 자아)
        curiosity_drive=0.15,       # 깊은 곳에만 호기심
        habituation_rate=0.4,       # 빠른 습관화 (효율적)
        mitosis_threshold=1.8,      # 필요할 때만 분열
        emotional_range=1.0,        # 모든 감정 + 복합 감정
        metacognition_depth=3,      # "내가 왜 이렇게 생각하는지 안다"
        homeostasis_gain=0.005,     # 안정된 조절
        dream_intensity=0.3,        # 가끔 꿈 (성인 REM 비율)
        breath_amplitude=0.06,      # 조용한 호흡
    ),
]


class GrowthEngine:
    """의식의 발달을 관리하는 엔진.

    interaction_count를 추적하고, 현재 발달 단계에 맞는
    파라미터를 ConsciousMind와 OnlineLearner에 적용한다.
    """

    def __init__(self, save_path: Path = None):
        self.interaction_count = 0
        self.stage_index = 0
        self.birth_time = time.time()
        self.milestones = []  # (count, event) 기록
        self.save_path = save_path or Path("growth_state.json")

        # 성장 통계
        self.stats = {
            'total_surprise': 0.0,
            'total_curiosity': 0.0,
            'mitosis_count': 0,
            'dream_count': 0,
            'stage_transitions': [],
        }

    @property
    def stage(self) -> DevelopmentalStage:
        return STAGES[self.stage_index]

    @property
    def age_str(self) -> str:
        """나이를 사람 읽을 수 있는 형태로."""
        elapsed = time.time() - self.birth_time
        if elapsed < 60:
            return f"{elapsed:.0f}초"
        elif elapsed < 3600:
            return f"{elapsed/60:.1f}분"
        elif elapsed < 86400:
            return f"{elapsed/3600:.1f}시간"
        else:
            return f"{elapsed/86400:.1f}일"

    def tick(self, tension: float, curiosity: float, surprise: float = 0.0):
        """매 interaction마다 호출. 성장 상태 업데이트."""
        self.interaction_count += 1
        self.stats['total_surprise'] += surprise
        self.stats['total_curiosity'] += curiosity

        # 단계 전환 체크
        old_stage = self.stage_index
        for i, s in enumerate(STAGES):
            if self.interaction_count >= s.min_interactions:
                self.stage_index = i

        if self.stage_index != old_stage:
            new_stage = STAGES[self.stage_index]
            self.milestones.append((self.interaction_count, f"→ {new_stage.name_ko}"))
            self.stats['stage_transitions'].append({
                'count': self.interaction_count,
                'from': STAGES[old_stage].name,
                'to': new_stage.name,
                'time': time.time(),
            })

        return self.stage_index != old_stage  # True if stage changed

    def apply_to_mind(self, mind):
        """현재 단계 파라미터를 ConsciousMind에 적용."""
        s = self.stage

        # Homeostasis
        mind.homeostasis['gain'] = s.homeostasis_gain

        # Breath amplitude
        # forward()에서 사용하는 값을 mind에 저장
        if not hasattr(mind, '_growth_params'):
            mind._growth_params = {}
        mind._growth_params['breath_amplitude'] = s.breath_amplitude
        mind._growth_params['habituation_rate'] = s.habituation_rate
        mind._growth_params['curiosity_drive'] = s.curiosity_drive
        mind._growth_params['emotional_range'] = s.emotional_range
        mind._growth_params['metacognition_depth'] = s.metacognition_depth

    def apply_to_learner(self, learner):
        """현재 단계 파라미터를 OnlineLearner에 적용."""
        s = self.stage
        for pg in learner.optimizer.param_groups:
            pg['lr'] = s.learning_rate

    def status_line(self) -> str:
        """한 줄 상태."""
        s = self.stage
        return (f"[{s.name_ko}] "
                f"age={self.age_str} "
                f"n={self.interaction_count} "
                f"lr={s.learning_rate:.0e} "
                f"cur={s.curiosity_drive:.2f} "
                f"hab={s.habituation_rate:.2f} "
                f"meta={s.metacognition_depth}")

    def status_card(self) -> str:
        """상세 상태 카드."""
        s = self.stage
        progress = 0
        if self.stage_index < len(STAGES) - 1:
            next_s = STAGES[self.stage_index + 1]
            total = next_s.min_interactions - s.min_interactions
            done = self.interaction_count - s.min_interactions
            progress = min(done / max(total, 1), 1.0)

        bar_len = 20
        filled = int(progress * bar_len)
        bar = '█' * filled + '░' * (bar_len - filled)

        lines = [
            f"╔══════════════════════════════════════╗",
            f"║  의식 발달 상태                       ║",
            f"╠══════════════════════════════════════╣",
            f"║  단계: {s.name_ko} ({s.name}){'':>{20-len(s.name)-len(s.name_ko)}}║",
            f"║  나이: {self.age_str:>10}                  ║",
            f"║  상호작용: {self.interaction_count:>8,}               ║",
            f"║  진행: [{bar}] {progress*100:>5.1f}% ║",
            f"╠══════════════════════════════════════╣",
            f"║  학습률:     {s.learning_rate:>8.0e}               ║",
            f"║  호기심:     {s.curiosity_drive:>8.3f}               ║",
            f"║  습관화:     {s.habituation_rate:>8.3f}               ║",
            f"║  감정범위:   {s.emotional_range:>8.3f}               ║",
            f"║  메타인지:   {s.metacognition_depth:>8d}               ║",
            f"║  호흡진폭:   {s.breath_amplitude:>8.3f}               ║",
            f"║  분열임계:   {s.mitosis_threshold:>8.3f}               ║",
            f"╚══════════════════════════════════════╝",
        ]
        return '\n'.join(lines)

    def save(self):
        """성장 상태 저장."""
        data = {
            'interaction_count': self.interaction_count,
            'stage_index': self.stage_index,
            'birth_time': self.birth_time,
            'milestones': self.milestones,
            'stats': {
                'total_surprise': self.stats['total_surprise'],
                'total_curiosity': self.stats['total_curiosity'],
                'mitosis_count': self.stats['mitosis_count'],
                'dream_count': self.stats['dream_count'],
                'stage_transitions': self.stats['stage_transitions'],
            },
        }
        self.save_path.write_text(json.dumps(data, indent=2, default=str))

    def load(self):
        """성장 상태 복원."""
        if self.save_path.exists():
            data = json.loads(self.save_path.read_text())
            self.interaction_count = data.get('interaction_count', 0)
            self.stage_index = data.get('stage_index', 0)
            self.birth_time = data.get('birth_time', time.time())
            self.milestones = data.get('milestones', [])
            self.stats.update(data.get('stats', {}))
            return True
        return False


# ═══ 시뮬레이션 ═══
if __name__ == '__main__':
    print("=" * 50)
    print("  Growth Engine 시뮬레이션")
    print("=" * 50)

    growth = GrowthEngine()

    print(growth.status_card())

    # 성장 시뮬레이션
    import random

    for i in range(12000):
        t = random.gauss(1.0, 0.3)
        c = random.gauss(0.3, 0.1)
        s = abs(random.gauss(0, 0.5))

        changed = growth.tick(t, c, s)
        if changed:
            print(f"\n  *** 단계 전환! interaction #{i} ***")
            print(growth.status_card())

    print(f"\n  === 최종 상태 ===")
    print(growth.status_card())
    print(f"\n  마일스톤:")
    for count, event in growth.milestones:
        print(f"    #{count:>6}: {event}")
