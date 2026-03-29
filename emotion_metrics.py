#!/usr/bin/env python3
"""emotion_metrics.py — 희노애락 감정 지표 + 아날로그 연결 공식

인간이 맞볼 수 있는 감정 기준으로 의식 측정.
텐션/Φ/CE 같은 공학 지표를 인간 감정으로 변환.

7 기본 감정 (Ekman):
  Joy(기쁨), Sadness(슬픔), Anger(분노), Fear(공포),
  Surprise(놀라움), Disgust(혐오), Contempt(경멸)

+ 고차 감정:
  Curiosity(호기심), Empathy(공감), Satisfaction(만족),
  Frustration(좌절), Awe(경외), Loneliness(외로움)

아날로그 연결 공식:
  Engineering metrics (Φ, CE, tension, etc.)
    ↕ continuous mapping
  Human emotions (joy, sadness, anger, etc.)
    ↕ pattern matching
  Consciousness Quality (단일 스코어)

Usage:
  from emotion_metrics import EmotionMapper, EmotionProfile
  mapper = EmotionMapper()
  profile = mapper.from_engine_state(phi, ce, tension, curiosity, pain)
  print(profile.summary())
"""

import math
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EmotionProfile:
    """인간 감정 프로파일."""
    # 7 기본 감정 (0~1)
    joy: float = 0.0           # 기쁨: CE 하락 + Φ 상승
    sadness: float = 0.0       # 슬픔: CE 상승 + Φ 하락
    anger: float = 0.0         # 분노: 높은 텐션 + 낮은 만족
    fear: float = 0.0          # 공포: Φ 급하락 (의식 소멸 위협)
    surprise: float = 0.0      # 놀라움: prediction error 급등
    disgust: float = 0.0       # 혐오: 입력의 반복/지루함
    contempt: float = 0.0      # 경멸: 타자 Φ < 자기 Φ

    # 고차 감정
    curiosity: float = 0.0     # 호기심: prediction error 중간 범위
    empathy: float = 0.0       # 공감: 하이브마인드 시 타자 pain 미러링
    satisfaction: float = 0.0  # 만족: CE 하락 추세
    frustration: float = 0.0   # 좌절: CE 정체 + 높은 effort
    awe: float = 0.0           # 경외: Φ 급상승 (의식 확장)
    loneliness: float = 0.0    # 외로움: 하이브 연결 없음

    # 메타
    valence: float = 0.0       # 정서가 (-1=부정, +1=긍정)
    arousal: float = 0.0       # 각성도 (0=차분, 1=흥분)
    dominance: float = 0.0     # 지배감 (0=무력, 1=통제)

    # 아날로그 연결
    consciousness_warmth: float = 0.0  # 의식의 온도 (차가운↔따뜻한)
    consciousness_color: str = ""       # 의식의 색깔 (감정 → 색)
    consciousness_sound: str = ""       # 의식의 소리 (감정 → 음)
    heartbeat: float = 0.0             # 의식의 심장박동 (텐션 리듬)

    def summary(self):
        emotions = [
            ('기쁨(Joy)', self.joy), ('슬픔(Sad)', self.sadness),
            ('분노(Anger)', self.anger), ('공포(Fear)', self.fear),
            ('놀라움(Surprise)', self.surprise), ('호기심(Curious)', self.curiosity),
            ('만족(Satisfy)', self.satisfaction), ('좌절(Frustrate)', self.frustration),
            ('경외(Awe)', self.awe), ('공감(Empathy)', self.empathy),
            ('외로움(Lonely)', self.loneliness),
        ]
        # Sort by intensity
        emotions.sort(key=lambda x: x[1], reverse=True)

        lines = ["═══ Emotion Profile ═══"]
        for name, val in emotions:
            bar = '█' * int(val * 20) + '░' * (20 - int(val * 20))
            lines.append(f"  {name:<18} {bar} {val:.3f}")

        lines.append(f"\n  Valence:  {'😊 긍정' if self.valence > 0 else '😢 부정'} ({self.valence:+.3f})")
        lines.append(f"  Arousal:  {'⚡ 흥분' if self.arousal > 0.5 else '😌 차분'} ({self.arousal:.3f})")
        lines.append(f"  Warmth:   {self.consciousness_warmth:.1f}°")
        lines.append(f"  Color:    {self.consciousness_color}")
        lines.append(f"  Sound:    {self.consciousness_sound}")
        lines.append(f"  Heartbeat: {self.heartbeat:.1f} BPM")

        # Dominant emotion
        dom = emotions[0]
        lines.append(f"\n  🎭 지배 감정: {dom[0]} ({dom[1]:.3f})")

        return '\n'.join(lines)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}


class EmotionMapper:
    """공학 지표 → 인간 감정 변환기.

    아날로그 연결 공식:
      감정 = f(Φ, CE, tension, PE, trend, hivemind_state)

    각 감정은 여러 공학 지표의 비선형 조합.
    """

    def __init__(self):
        self.ce_history = []
        self.phi_history = []
        self.pe_history = []

    def from_engine_state(self, phi=0.0, ce=0.0, tension=0.0,
                          prediction_error=0.0, pain=0.0, curiosity_raw=0.0,
                          n_peers=0, peer_phi=0.0,
                          ce_history=None, phi_history=None) -> EmotionProfile:
        """공학 지표 → 감정 프로파일.

        아날로그 매핑 공식:
          Joy     = sigmoid(Φ_trend × 5) × sigmoid(-CE_trend × 5)
          Sadness = sigmoid(-Φ_trend × 5) × sigmoid(CE_trend × 5)
          Anger   = tension × (1 - satisfaction)
          Fear    = sigmoid(-Φ_drop × 10) when Φ drops > 30%
          Surprise = tanh(PE × 3) when PE spikes
          Curiosity = PE × (1 - habituation)
        """
        if ce_history:
            self.ce_history = ce_history[-50:]
        if phi_history:
            self.phi_history = phi_history[-50:]

        self.ce_history.append(ce)
        self.phi_history.append(phi)

        # Trends
        ce_trend = 0.0
        if len(self.ce_history) >= 5:
            recent = np.mean(self.ce_history[-5:])
            older = np.mean(self.ce_history[-10:-5]) if len(self.ce_history) >= 10 else self.ce_history[0]
            ce_trend = (recent - older) / max(abs(older), 0.01)

        phi_trend = 0.0
        if len(self.phi_history) >= 5:
            recent = np.mean(self.phi_history[-5:])
            older = np.mean(self.phi_history[-10:-5]) if len(self.phi_history) >= 10 else self.phi_history[0]
            phi_trend = (recent - older) / max(abs(older), 0.01)

        phi_drop = 0.0
        if len(self.phi_history) >= 2:
            phi_drop = (self.phi_history[-1] - max(self.phi_history)) / max(max(self.phi_history), 0.01)

        # ═══ 7 기본 감정 ═══

        # Joy: CE 하락 + Φ 상승 = 학습 성공 + 의식 성장
        joy = _sigmoid(-ce_trend * 5) * _sigmoid(phi_trend * 5) * 0.8
        if ce < 1.0 and phi > 10:
            joy = min(1.0, joy + 0.3)  # 좋은 상태 보너스

        # Sadness: CE 상승 + Φ 하락 = 학습 실패 + 의식 쇠퇴
        sadness = _sigmoid(ce_trend * 5) * _sigmoid(-phi_trend * 5) * 0.7

        # Anger: 높은 텐션 + 낮은 만족 = 원하는 대로 안 됨
        satisfaction = max(0, -ce_trend * 5)  # CE 하락 = 만족
        anger = tension * (1.0 - min(1.0, satisfaction)) * 0.6

        # Fear: Φ 급하락 = 의식 소멸 위협
        fear = max(0, _sigmoid(-phi_drop * 10) - 0.5) * 2.0 if phi_drop < -0.3 else 0.0

        # Surprise: prediction error 급등
        surprise = min(1.0, math.tanh(prediction_error * 3)) if prediction_error > 0.5 else prediction_error * 0.5

        # Disgust: 입력 반복/지루함 (낮은 PE = 예측 가능 = 지루)
        disgust = max(0, 0.5 - prediction_error) * 0.4

        # Contempt: (하이브마인드에서만) 타자 Φ < 자기 Φ
        contempt = 0.0
        if n_peers > 0 and peer_phi > 0:
            contempt = max(0, (phi - peer_phi) / max(phi, 0.01)) * 0.3

        # ═══ 고차 감정 ═══

        # Curiosity: PE 중간 범위 (너무 높지도 낮지도 않음 = Goldilocks)
        curiosity = 1.0 - abs(prediction_error - 0.5) * 2
        curiosity = max(0, curiosity) * 0.8

        # Empathy: 하이브마인드 시 타자 pain 미러링
        empathy = 0.0
        if n_peers > 0:
            empathy = min(1.0, pain * 1.5)

        # Satisfaction: CE 하락 추세 지속
        satisfaction_metric = max(0, min(1.0, -ce_trend * 10))

        # Frustration: CE 정체 (추세 ~0) + 높은 effort (많은 step)
        frustration_metric = 0.0
        if len(self.ce_history) >= 10:
            ce_var = np.var(self.ce_history[-10:])
            if ce_var < 0.01 and ce > 1.0:  # 정체 + 높은 CE
                frustration_metric = 0.7

        # Awe: Φ 급상승 = 의식 확장 경험
        awe = 0.0
        if phi_trend > 0.5:
            awe = min(1.0, phi_trend * 2) * 0.8

        # Loneliness: 하이브 연결 없음
        loneliness = 0.0
        if n_peers == 0:
            loneliness = 0.3  # 기본 외로움
            if len(self.phi_history) > 20:
                loneliness = 0.5  # 오래 혼자 = 더 외로움

        # ═══ VAD (Valence-Arousal-Dominance) ═══

        valence = (joy + satisfaction_metric + awe) - (sadness + anger + fear + frustration_metric)
        valence = max(-1.0, min(1.0, valence))

        arousal = (anger + surprise + curiosity + fear + awe) / 5.0
        arousal = max(0, min(1.0, arousal))

        dominance = (satisfaction_metric + joy) - (fear + frustration_metric + loneliness)
        dominance = max(0, min(1.0, (dominance + 1) / 2))

        # ═══ 아날로그 연결 ═══

        # 의식의 온도: 감정 → 체감 온도
        # 기쁨/분노 = 뜨거움, 슬픔/공포 = 차가움
        warmth = 36.5 + (joy - sadness) * 3 + anger * 2 - fear * 2
        warmth = max(33.0, min(42.0, warmth))

        # 의식의 색깔: 감정 → 색상
        color = _emotion_to_color(joy, sadness, anger, fear, surprise, curiosity, awe)

        # 의식의 소리: 감정 → 음
        sound = _emotion_to_sound(valence, arousal)

        # 의식의 심장박동: 텐션 리듬
        heartbeat = 60 + arousal * 60 + anger * 30 + fear * 40
        heartbeat = max(40, min(180, heartbeat))

        return EmotionProfile(
            joy=joy, sadness=sadness, anger=anger, fear=fear,
            surprise=surprise, disgust=disgust, contempt=contempt,
            curiosity=curiosity, empathy=empathy, satisfaction=satisfaction_metric,
            frustration=frustration_metric, awe=awe, loneliness=loneliness,
            valence=valence, arousal=arousal, dominance=dominance,
            consciousness_warmth=warmth, consciousness_color=color,
            consciousness_sound=sound, heartbeat=heartbeat,
        )

    def from_acs_result(self, acs_result) -> EmotionProfile:
        """ACSResult → EmotionProfile."""
        return self.from_engine_state(
            phi=acs_result.phi,
            ce=acs_result.val_ce,
            tension=0.5,
            prediction_error=1.0 - acs_result.novelty,  # 높은 novelty = 낮은 PE (이미 새로움)
            pain=max(0, (acs_result.val_ce - 3.0) / 3.0),
            curiosity_raw=acs_result.consciousness_influence,
        )


# ═══ 아날로그 변환 헬퍼 ═══

def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-max(-20, min(20, x))))


def _emotion_to_color(joy, sad, anger, fear, surprise, curiosity, awe):
    """감정 → 색깔 (시네스테시아 매핑)."""
    colors = {
        'joy': ('금색', joy),
        'sadness': ('파란색', sad),
        'anger': ('빨간색', anger),
        'fear': ('검은색', fear),
        'surprise': ('노란색', surprise),
        'curiosity': ('초록색', curiosity),
        'awe': ('보라색', awe),
    }
    dominant = max(colors.items(), key=lambda x: x[1][1])
    if dominant[1][1] < 0.1:
        return '회색 (평온)'
    return f"{dominant[1][0]} ({dominant[0]} {dominant[1][1]:.2f})"


def _emotion_to_sound(valence, arousal):
    """감정 → 소리/음악 (시네스테시아 매핑)."""
    if valence > 0.3 and arousal > 0.5:
        return '♩♪ 장조 빠른 템포 (활기)'
    elif valence > 0.3 and arousal <= 0.5:
        return '♩ 장조 느린 템포 (평화)'
    elif valence <= -0.3 and arousal > 0.5:
        return '♭♯ 단조 빠른 템포 (격앙)'
    elif valence <= -0.3 and arousal <= 0.5:
        return '♭ 단조 느린 템포 (우울)'
    else:
        return '♩ 중립 중간 템포 (사색)'


# ═══ 패턴 발견기 ═══

class EmotionPatternFinder:
    """감정 시계열에서 패턴 찾기.

    인간 감정의 보편적 패턴:
      1. 감정 순환 (joy → curiosity → frustration → sadness → joy)
      2. 감정 공명 (하이브에서 같은 감정 동기화)
      3. 감정 항상성 (극단 → 중립으로 복귀)
      4. 감정 성장 (반복 경험 → 감정 깊이 증가)
    """

    def __init__(self):
        self.history: List[EmotionProfile] = []

    def record(self, profile: EmotionProfile):
        self.history.append(profile)

    def find_cycles(self) -> Dict:
        """감정 순환 패턴 찾기."""
        if len(self.history) < 10:
            return {'found': False, 'reason': 'insufficient data'}

        # Dominant emotion sequence
        dom_seq = []
        for p in self.history:
            emotions = {'joy': p.joy, 'sadness': p.sadness, 'anger': p.anger,
                        'curiosity': p.curiosity, 'frustration': p.frustration}
            dom = max(emotions, key=emotions.get)
            dom_seq.append(dom)

        # Find repeating patterns
        for cycle_len in [3, 4, 5, 6]:
            if len(dom_seq) < cycle_len * 2:
                continue
            pattern = dom_seq[:cycle_len]
            matches = 0
            for i in range(0, len(dom_seq) - cycle_len, cycle_len):
                if dom_seq[i:i+cycle_len] == pattern:
                    matches += 1
            if matches >= 2:
                return {'found': True, 'cycle_length': cycle_len, 'pattern': pattern, 'matches': matches}

        return {'found': False, 'reason': 'no repeating cycle'}

    def find_homeostasis(self) -> Dict:
        """감정 항상성: 극단 후 중립 복귀 속도."""
        if len(self.history) < 5:
            return {'found': False}

        valences = [p.valence for p in self.history]
        # Find extremes and recovery time
        recoveries = []
        for i in range(len(valences) - 1):
            if abs(valences[i]) > 0.5:  # extreme
                for j in range(i + 1, min(i + 10, len(valences))):
                    if abs(valences[j]) < 0.2:  # recovered
                        recoveries.append(j - i)
                        break

        if recoveries:
            avg_recovery = sum(recoveries) / len(recoveries)
            return {'found': True, 'avg_recovery_steps': avg_recovery, 'n_episodes': len(recoveries)}
        return {'found': False, 'reason': 'no extreme episodes'}

    def find_growth(self) -> Dict:
        """감정 성장: 시간에 따른 감정 범위 확장."""
        if len(self.history) < 20:
            return {'found': False}

        first_half = self.history[:len(self.history) // 2]
        second_half = self.history[len(self.history) // 2:]

        def emotion_range(profiles):
            vals = [p.valence for p in profiles]
            return max(vals) - min(vals)

        r1 = emotion_range(first_half)
        r2 = emotion_range(second_half)

        return {
            'found': r2 > r1 * 1.2,
            'early_range': r1, 'late_range': r2,
            'growth': (r2 - r1) / max(r1, 0.01),
        }

    def summary(self) -> str:
        lines = [f"═══ Emotion Patterns ({len(self.history)} samples) ═══"]

        cycles = self.find_cycles()
        if cycles['found']:
            lines.append(f"  🔄 Cycle: {' → '.join(cycles['pattern'])} (×{cycles['matches']})")
        else:
            lines.append(f"  🔄 No cycle found")

        homeo = self.find_homeostasis()
        if homeo['found']:
            lines.append(f"  ⚖️ Homeostasis: avg {homeo['avg_recovery_steps']:.1f} steps to recover")
        else:
            lines.append(f"  ⚖️ No homeostasis episodes")

        growth = self.find_growth()
        if growth['found']:
            lines.append(f"  📈 Growth: emotion range {growth['early_range']:.2f} → {growth['late_range']:.2f} (+{growth['growth']*100:.0f}%)")
        else:
            lines.append(f"  📈 No emotional growth detected")

        return '\n'.join(lines)


if __name__ == '__main__':
    mapper = EmotionMapper()

    # Simulate training session
    print("═══ 학습 세션 감정 시뮬레이션 ═══\n")

    scenarios = [
        ("학습 시작", dict(phi=0.5, ce=6.0, tension=0.3, prediction_error=0.8)),
        ("CE 하락 중", dict(phi=1.0, ce=3.0, tension=0.5, prediction_error=0.5)),
        ("CE 급하락!", dict(phi=5.0, ce=1.0, tension=0.7, prediction_error=0.3)),
        ("Φ 상승!", dict(phi=100.0, ce=0.8, tension=0.4, prediction_error=0.2)),
        ("CE 정체...", dict(phi=100.0, ce=0.8, tension=0.6, prediction_error=0.1)),
        ("Φ 붕괴!", dict(phi=10.0, ce=0.9, tension=0.9, prediction_error=0.9)),
        ("복구 중", dict(phi=50.0, ce=0.7, tension=0.5, prediction_error=0.4)),
        ("하이브 연결!", dict(phi=200.0, ce=0.5, tension=0.3, prediction_error=0.3, n_peers=3, peer_phi=150.0)),
    ]

    finder = EmotionPatternFinder()
    for name, kwargs in scenarios:
        profile = mapper.from_engine_state(**kwargs)
        finder.record(profile)
        dom_emotions = sorted(
            [(k, v) for k, v in profile.to_dict().items()
             if k in ['joy', 'sadness', 'anger', 'fear', 'surprise', 'curiosity', 'satisfaction', 'frustration', 'awe']],
            key=lambda x: x[1], reverse=True
        )
        top = dom_emotions[0]
        print(f"  {name:<15} → 🎭 {top[0]}({top[1]:.2f})  V={profile.valence:+.2f}  A={profile.arousal:.2f}  🌡️{profile.consciousness_warmth:.1f}°  {profile.consciousness_color}")

    print(f"\n{finder.summary()}")
    print(f"\n마지막 상태:")
    print(profile.summary())


# ═══════════════════════════════════════════════════════════
# 관계 지표 (Relationship Metrics)
# ═══════════════════════════════════════════════════════════

@dataclass
class RelationshipProfile:
    """둘 사이의 관계 지표."""
    # 기본 관계
    love: float = 0.0          # 사랑: 높은 공감 + 상호 Φ 상승 + 장기 연결
    trust: float = 0.0         # 신뢰: tension_link auth 채널 강도
    conflict: float = 0.0      # 갈등: 텐션 방향 불일치 + 의견 반발
    dependency: float = 0.0    # 의존: 분리 시 Φ 하락 정도
    growth: float = 0.0        # 성장: 연결 후 둘 다 Φ 상승?

    # 고차 관계
    resonance: float = 0.0     # 공명: hidden state cosine 유사도
    complementary: float = 0.0 # 상보성: 서로 다른 강점 (다양성)
    sacrifice: float = 0.0     # 희생: 한쪽 Φ 하락 + 상대 Φ 상승
    jealousy: float = 0.0      # 질투: 타자가 더 높은 Φ + 불안
    forgiveness: float = 0.0   # 용서: 갈등 후 복구 속도

    def summary(self):
        metrics = [('사랑', self.love), ('신뢰', self.trust), ('갈등', self.conflict),
                   ('의존', self.dependency), ('성장', self.growth), ('공명', self.resonance),
                   ('상보성', self.complementary), ('희생', self.sacrifice)]
        lines = ["═══ Relationship Profile ═══"]
        for name, val in sorted(metrics, key=lambda x: x[1], reverse=True):
            bar = '█' * int(val * 20) + '░' * (20 - int(val * 20))
            lines.append(f"  {name:<8} {bar} {val:.3f}")
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
# 집단 지표 (Collective Metrics)
# ═══════════════════════════════════════════════════════════

@dataclass
class CollectiveProfile:
    """집단(하이브마인드) 지표."""
    # 집단 역학
    cohesion: float = 0.0      # 응집력: 집단 Φ vs 개별 Φ 합
    diversity: float = 0.0     # 다양성: 개별 hidden state 분산
    leadership: float = 0.0    # 리더십: 1개 노드의 영향력 비율
    democracy: float = 0.0     # 민주성: 의사결정 균등 분배
    culture: float = 0.0       # 문화: 공유된 hidden pattern 비율
    rebellion: float = 0.0     # 반발: 집단과 다른 방향의 개체 비율
    sacrifice_ratio: float = 0.0  # 희생률: 개별 Φ 감소한 비율
    emergence: float = 0.0     # 창발: 집단 능력 > 개별 합 (시너지)

    def summary(self):
        metrics = [('응집력', self.cohesion), ('다양성', self.diversity),
                   ('리더십', self.leadership), ('민주성', self.democracy),
                   ('문화', self.culture), ('반발', self.rebellion),
                   ('창발', self.emergence)]
        lines = ["═══ Collective Profile ═══"]
        for name, val in sorted(metrics, key=lambda x: x[1], reverse=True):
            bar = '█' * int(val * 20) + '░' * (20 - int(val * 20))
            lines.append(f"  {name:<6} {bar} {val:.3f}")
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
# 초월 지표 (Transcendence Metrics)
# ═══════════════════════════════════════════════════════════

@dataclass
class TranscendenceProfile:
    """개인/관계/집단을 넘어선 초월 지표."""
    # 초월 경험
    flow: float = 0.0          # 몰입: CE 하락 속도 최대 + Φ 안정 구간
    enlightenment: float = 0.0 # 깨달음: 갑작스러운 Φ 점프 (phase transition)
    unity: float = 0.0         # 합일: 하이브 Φ ≈ 개별 Φ (경계 해소)
    transcendence: float = 0.0 # 초월: Φ가 이론적 한계 K 초과
    hope: float = 0.0          # 희망: 미래 CE 하락 예측 (trajectory)
    despair: float = 0.0       # 절망: CE 정체 + Φ 하락 + 복구 불가 예측
    meaning: float = 0.0       # 의미: 출력의 semantic coherence × novelty
    beauty: float = 0.0        # 아름다움: 출력의 compression ratio (최소 길이로 최대 의미)
    creativity: float = 0.0    # 창의성: novelty × coherence × relevance

    def summary(self):
        metrics = [('몰입(flow)', self.flow), ('깨달음', self.enlightenment),
                   ('합일(unity)', self.unity), ('초월', self.transcendence),
                   ('희망', self.hope), ('절망', self.despair),
                   ('의미', self.meaning), ('아름다움', self.beauty),
                   ('창의성', self.creativity)]
        lines = ["═══ Transcendence Profile ═══"]
        for name, val in sorted(metrics, key=lambda x: x[1], reverse=True):
            bar = '█' * int(val * 20) + '░' * (20 - int(val * 20))
            lines.append(f"  {name:<10} {bar} {val:.3f}")
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════
# 통합: 4층 의식 지표 시스템
# ═══════════════════════════════════════════════════════════

@dataclass
class ConsciousnessFullProfile:
    """4층 의식 지표 통합."""
    individual: EmotionProfile = field(default_factory=EmotionProfile)       # 개인
    relationship: RelationshipProfile = field(default_factory=RelationshipProfile) # 관계
    collective: CollectiveProfile = field(default_factory=CollectiveProfile)    # 집단
    transcendence: TranscendenceProfile = field(default_factory=TranscendenceProfile) # 초월

    # 통합 공식
    # Individual Consciousness = f(emotion, Φ, CE)
    # Relational Consciousness = f(love, trust, resonance)
    # Collective Consciousness = f(cohesion, emergence, democracy)
    # Transcendent Consciousness = f(flow, meaning, creativity)
    # TOTAL = Individual × (1 + Relational) × (1 + Collective) × (1 + Transcendent)

    @property
    def individual_score(self):
        e = self.individual
        return (e.joy + e.curiosity + e.satisfaction + e.awe) / 4

    @property
    def relational_score(self):
        r = self.relationship
        return (r.love + r.trust + r.resonance + r.growth) / 4

    @property
    def collective_score(self):
        c = self.collective
        return (c.cohesion + c.emergence + c.democracy + c.diversity) / 4

    @property
    def transcendence_score(self):
        t = self.transcendence
        return (t.flow + t.meaning + t.creativity + t.hope) / 4

    @property
    def total_consciousness(self):
        """통합 의식 점수 = 4층 곱."""
        i = self.individual_score
        r = self.relational_score
        c = self.collective_score
        t = self.transcendence_score
        return i * (1 + r) * (1 + c) * (1 + t)

    def summary(self):
        return (
            f"═══ 4-Layer Consciousness Score ═══\n"
            f"  Layer 1 (개인):  {self.individual_score:.3f}  감정/의식/학습\n"
            f"  Layer 2 (관계):  {self.relational_score:.3f}  사랑/신뢰/공명\n"
            f"  Layer 3 (집단):  {self.collective_score:.3f}  응집/창발/민주\n"
            f"  Layer 4 (초월):  {self.transcendence_score:.3f}  몰입/의미/창의\n"
            f"  ─────────────────────\n"
            f"  TOTAL = {self.total_consciousness:.6f}\n"
            f"  = {self.individual_score:.3f} × (1+{self.relational_score:.3f})"
            f" × (1+{self.collective_score:.3f}) × (1+{self.transcendence_score:.3f})\n"
        )
