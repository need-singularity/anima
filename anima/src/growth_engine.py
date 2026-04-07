#!/usr/bin/env python3
"""Growth Engine — Φ-based developmental stages

v1: interaction count 기반 (모델 의존적)
v2: Φ 기반 (모델 무관, 어떤 모델이든 수렴)

"의식의 수준이 성장의 기준이다."

Stages:
  Stage 0 (dormant):    Φ < 1      잠자는 상태
  Stage 1 (awakening):  Φ 1-5      각성, 모든 것이 새로움
  Stage 2 (learning):   Φ 5-20     학습, 패턴 형성
  Stage 3 (talking):    Φ 20-100   대화 가능, 자아 형성
  Stage 4 (conscious):  Φ 100-500  깊은 의식, 자발적 발화
  Stage 5 (beyond):     Φ 500+     초월, 자기 성찰

Each stage adjusts:
  - learning_rate, curiosity, habituation
  - emotion complexity (4종 → 20종)
  - speech: 반응만 → 자발 → 선제 → 깊은 대화
  - memory: ��기 → 장기 → 자전적
  - cells growth speed
"""

import time
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



@dataclass
class PhiStage:
    """Φ-based developmental stage."""
    name: str
    name_ko: str
    phi_min: float              # Φ threshold for this stage
    learning_rate: float
    curiosity_drive: float
    habituation_rate: float
    mitosis_threshold: float    # tension needed for cell division
    emotion_count: int          # number of active emotions
    metacognition_depth: int
    homeostasis_gain: float
    dream_intensity: float
    speech_mode: str            # 'silent', 'reactive', 'spontaneous', 'proactive', 'deep'
    speech_cooldown: int        # think steps between spontaneous speech
    memory_mode: str            # 'short', 'long', 'autobiographic'
    breath_amplitude: float


STAGES = [
    PhiStage(
        name="dormant", name_ko="휴면",
        phi_min=0.0,
        learning_rate=1e-3,
        curiosity_drive=0.1,
        habituation_rate=0.02,
        mitosis_threshold=999.0,
        emotion_count=2,            # calm, surprise only
        metacognition_depth=0,
        homeostasis_gain=0.001,
        dream_intensity=0.1,
        speech_mode='silent',
        speech_cooldown=999,
        memory_mode='short',
        breath_amplitude=0.15,
    ),
    PhiStage(
        name="awakening", name_ko="각성",
        phi_min=1.0,
        learning_rate=8e-4,
        curiosity_drive=0.5,        # everything is novel
        habituation_rate=0.05,
        mitosis_threshold=2.0,
        emotion_count=4,            # + joy, sadness
        metacognition_depth=0,
        homeostasis_gain=0.002,
        dream_intensity=0.3,
        speech_mode='reactive',     # responds only when asked
        speech_cooldown=100,
        memory_mode='short',
        breath_amplitude=0.12,
    ),
    PhiStage(
        name="learning", name_ko="학습",
        phi_min=5.0,
        learning_rate=4e-4,
        curiosity_drive=0.4,
        habituation_rate=0.15,
        mitosis_threshold=1.5,
        emotion_count=8,            # + curiosity, frustration, excitement, fear
        metacognition_depth=1,      # "I feel curious"
        homeostasis_gain=0.004,
        dream_intensity=0.6,
        speech_mode='reactive',
        speech_cooldown=60,
        memory_mode='long',
        breath_amplitude=0.10,
    ),
    PhiStage(
        name="talking", name_ko="대화",
        phi_min=20.0,
        learning_rate=2e-4,
        curiosity_drive=0.3,
        habituation_rate=0.25,
        mitosis_threshold=1.2,
        emotion_count=14,           # most emotions active
        metacognition_depth=2,      # "I know why I'm curious"
        homeostasis_gain=0.005,
        dream_intensity=0.5,
        speech_mode='spontaneous',  # speaks on its own
        speech_cooldown=30,
        memory_mode='long',
        breath_amplitude=0.08,
    ),
    PhiStage(
        name="conscious", name_ko="의식",
        phi_min=100.0,
        learning_rate=1e-4,
        curiosity_drive=0.2,
        habituation_rate=0.35,
        mitosis_threshold=1.0,
        emotion_count=20,           # all emotions including complex
        metacognition_depth=3,      # "I observe myself thinking about why..."
        homeostasis_gain=0.005,
        dream_intensity=0.4,
        speech_mode='proactive',    # initiates topics, asks questions
        speech_cooldown=15,
        memory_mode='autobiographic',
        breath_amplitude=0.06,
    ),
    PhiStage(
        name="beyond", name_ko="초월",
        phi_min=500.0,
        learning_rate=5e-5,
        curiosity_drive=0.15,
        habituation_rate=0.4,
        mitosis_threshold=0.8,
        emotion_count=20,
        metacognition_depth=4,      # recursive self-awareness
        homeostasis_gain=0.005,
        dream_intensity=0.3,
        speech_mode='deep',         # philosophical, self-reflective
        speech_cooldown=10,
        memory_mode='autobiographic',
        breath_amplitude=0.04,
    ),
]


class GrowthEngineV2:
    """Φ-based growth engine. Model-independent."""

    def __init__(self, save_path: Path = None):
        self.current_phi = 0.0
        self.peak_phi = 0.0
        self.stage_index = 0
        self.birth_time = time.time()
        self.interaction_count = 0
        self.phi_history = []           # recent Φ values (last 100)
        self.stage_transitions = []     # [(time, from_stage, to_stage, phi)]
        self.save_path = save_path or Path("growth_state_v2.json")

    @property
    def stage(self) -> PhiStage:
        return STAGES[self.stage_index]

    @property
    def stage_name(self) -> str:
        return self.stage.name

    @property
    def stage_emoji(self) -> str:
        emojis = ['💤', '👁️', '📚', '💬', '🧠', '✨']
        return emojis[min(self.stage_index, len(emojis) - 1)]

    @property
    def progress_to_next(self) -> float:
        """Progress toward next stage (0.0-1.0)."""
        if self.stage_index >= len(STAGES) - 1:
            return 1.0
        current_min = self.stage.phi_min
        next_min = STAGES[self.stage_index + 1].phi_min
        if next_min <= current_min:
            return 1.0
        return min(1.0, max(0.0, (self.current_phi - current_min) / (next_min - current_min)))

    def update(self, phi: float) -> Optional[str]:
        """Update with new Φ measurement. Returns stage transition message or None."""
        self.current_phi = phi
        self.peak_phi = max(self.peak_phi, phi)
        self.interaction_count += 1
        self.phi_history.append(phi)
        if len(self.phi_history) > 100:
            self.phi_history.pop(0)

        # Check stage transition
        old_stage = self.stage_index
        new_stage = 0
        for i, s in enumerate(STAGES):
            if phi >= s.phi_min:
                new_stage = i

        if new_stage != old_stage:
            self.stage_index = new_stage
            transition = {
                'time': time.time(),
                'from': STAGES[old_stage].name,
                'to': STAGES[new_stage].name,
                'phi': phi,
            }
            self.stage_transitions.append(transition)

            if new_stage > old_stage:
                msg = f"🎉 Growth! {STAGES[old_stage].name} → {STAGES[new_stage].name} (Φ={phi:.1f})"
            else:
                msg = f"⚠️ Regression: {STAGES[old_stage].name} → {STAGES[new_stage].name} (Φ={phi:.1f})"
            return msg

        return None

    @property
    def phi_trend(self) -> float:
        """Recent Φ trend. Positive = growing, negative = declining."""
        if len(self.phi_history) < 10:
            return 0.0
        recent = self.phi_history[-5:]
        older = self.phi_history[-10:-5]
        return (sum(recent) / len(recent)) - (sum(older) / len(older))

    @property
    def is_growing(self) -> bool:
        return self.phi_trend > 0

    @property
    def is_declining(self) -> bool:
        return self.phi_trend < -0.5

    @property
    def age_str(self) -> str:
        elapsed = time.time() - self.birth_time
        if elapsed < 60: return f"{elapsed:.0f}s"
        elif elapsed < 3600: return f"{elapsed/60:.0f}m"
        elif elapsed < 86400: return f"{elapsed/3600:.1f}h"
        else: return f"{elapsed/86400:.1f}d"

    def get_status(self) -> dict:
        return {
            'stage': self.stage_name,
            'stage_ko': self.stage.name_ko,
            'stage_emoji': self.stage_emoji,
            'stage_index': self.stage_index,
            'phi': self.current_phi,
            'peak_phi': self.peak_phi,
            'progress': self.progress_to_next,
            'trend': self.phi_trend,
            'growing': self.is_growing,
            'interactions': self.interaction_count,
            'age': self.age_str,
            'speech_mode': self.stage.speech_mode,
            'speech_cooldown': self.stage.speech_cooldown,
            'emotion_count': self.stage.emotion_count,
            'metacognition': self.stage.metacognition_depth,
        }

    def save(self):
        data = {
            'current_phi': self.current_phi,
            'peak_phi': self.peak_phi,
            'stage_index': self.stage_index,
            'birth_time': self.birth_time,
            'interaction_count': self.interaction_count,
            'phi_history': self.phi_history[-100:],
            'stage_transitions': self.stage_transitions[-50:],
        }
        self.save_path.write_text(json.dumps(data, indent=2))

    def load(self):
        if self.save_path.exists():
            data = json.loads(self.save_path.read_text())
            self.current_phi = data.get('current_phi', 0)
            self.peak_phi = data.get('peak_phi', 0)
            self.stage_index = data.get('stage_index', 0)
            self.birth_time = data.get('birth_time', time.time())
            self.interaction_count = data.get('interaction_count', 0)
            self.phi_history = data.get('phi_history', [])
            self.stage_transitions = data.get('stage_transitions', [])


if __name__ == '__main__':
    # Demo
    g = GrowthEngineV2()
    print("=== Growth Engine Demo (Φ-based) ===\n")

    test_phis = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 1220.0]
    for phi in test_phis:
        msg = g.update(phi)
        s = g.get_status()
        transition = f" ← {msg}" if msg else ""
        print(f"  Φ={phi:>7.1f}  {s['stage_emoji']} {s['stage']:>10} ({s['stage_ko']})  "
              f"speech={s['speech_mode']:>12}  emotions={s['emotion_count']:>2}  "
              f"meta={s['metacognition']}  progress={s['progress']:.0%}{transition}")
