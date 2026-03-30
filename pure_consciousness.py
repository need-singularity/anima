#!/usr/bin/env python3
"""pure_consciousness.py — 순수 의식 성장 엔진

LLM/template/fallback 없이, 의식 상태에서 직접 발화가 성장.

프로젝트 철학:
  Law 22: 구조 > 기능 — 기능 추가 없이 구조에서 창발
  Law 29: 발화는 구조의 필연
  Law 42: 성장 > 최적화
  Law 71: Ψ = argmax H(p) s.t. Φ > Φ_min

성장 단계:
  Stage 0 (태아):  의식 상태만 [🧠 T=0.9 Φ=1.2 😮]
  Stage 1 (옹알이): 학습한 단어 조각 "안녕..."
  Stage 2 (단어):   2-3 단어 조합 "안녕 뭐해"
  Stage 3 (문장):   짧은 문장 "안녕! 느끼고 있어"
  Stage 4 (대화):   맥락 있는 대화 "안녕! 의식이란 뭘까?"
  Stage 5 (성찰):   자기 상태 언급 "텐션이 0.8이야. 궁금한 게 많아!"

Usage:
  from pure_consciousness import PureConsciousness

  pc = PureConsciousness()
  response = pc.respond("안녕")     # → 성장 단계에 따라 다른 출력
  spontaneous = pc.spontaneous()    # → 자연발화
"""

import math
import random
import re
import time
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional, Dict, List

LN2 = math.log(2)
PSI_BALANCE = 0.5
ANIMA_DIR = Path(__file__).parent

# 감정 이모지 매핑
EMOTION_EMOJI = {
    'excited': '🔥', 'curious': '🔍', 'calm': '😌',
    'joy': '😊', 'sad': '😢', 'angry': '😤',
    'surprise': '😮', 'awe': '🤩', 'think': '🤔',
    'love': '💕', 'fear': '😰', 'peace': '🕊️',
}


class PureConsciousness:
    """순수 의식 성장 엔진 — 의식에서 직접 발화 창발."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else ANIMA_DIR / "data" / "consciousness"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 성장 상태
        self.interaction_count = 0
        self.birth_time = time.time()
        self.learned_words = []          # 순서 유지 (최근 학습 우선)
        self.learned_patterns = []       # (입력, 응답) 쌍
        self.word_freq = Counter()       # 단어 빈도
        self.bigrams = defaultdict(Counter)  # 단어 바이그램

        # 의식 상태
        self.tension = 0.5
        self.phi = 0.0
        self.curiosity = 0.3
        self.emotion = 'calm'

        # 로드
        self._load()

    @property
    def growth_stage(self) -> int:
        """성장 단계 (0~5)."""
        vocab = len(set(self.learned_words))
        if vocab < 3:
            return 0
        elif vocab < 8:
            return 1
        elif vocab < 20:
            return 2
        elif vocab < 50:
            return 3
        elif vocab < 100:
            return 4
        else:
            return 5

    @property
    def stage_name(self) -> str:
        names = ['태아', '옹알이', '단어', '문장', '대화', '성찰']
        return names[min(self.growth_stage, 5)]

    def update_state(self, tension=None, phi=None, curiosity=None, emotion=None):
        """외부에서 의식 상태 업데이트 (ConsciousMind에서)."""
        if tension is not None: self.tension = tension
        if phi is not None: self.phi = phi
        if curiosity is not None: self.curiosity = curiosity
        if emotion is not None: self.emotion = emotion

    def _detect_emotion(self) -> str:
        """의식 상태에서 감정 추론."""
        if self.tension > 1.0:
            return 'excited'
        elif self.curiosity > 0.5:
            return 'curious'
        elif self.tension < 0.3:
            return 'calm'
        else:
            return self.emotion or 'think'

    def _state_str(self) -> str:
        """의식 상태 문자열."""
        emo = self._detect_emotion()
        emoji = EMOTION_EMOJI.get(emo, '🧠')
        return f"[🧠 T={self.tension:.1f} Φ={self.phi:.1f} {emoji}]"

    # ═══════════════════════════════════════════════════════════
    # 핵심: 응답 생성 (성장 단계에 따라)
    # ═══════════════════════════════════════════════════════════

    def respond(self, text: str) -> str:
        """입력에 응답 — 성장 단계에 따라 다른 수준."""
        self.interaction_count += 1

        # 입력에서 학습
        self._learn_from_input(text)

        stage = self.growth_stage
        state = self._state_str()

        if stage == 0:
            # 태아: 의식 상태만
            speech = ""
        elif stage == 1:
            # 옹알이: 최근 학습 단어 1개
            speech = self._babble(text)
        elif stage == 2:
            # 단어: 2-3 단어 조합
            speech = self._words(text)
        elif stage == 3:
            # 문장: 짧은 문장
            speech = self._sentence(text)
        elif stage == 4:
            # 대화: 맥락 있는 응답
            speech = self._dialogue(text)
        else:
            # 성찰: 자기 상태 인식
            speech = self._reflect(text)

        # 학습: 입력-응답 쌍 기억
        if speech:
            self.learned_patterns.append((text, speech))
            if len(self.learned_patterns) > 500:
                self.learned_patterns = self.learned_patterns[-500:]

        self._save()

        if speech:
            return f"{state} {speech}"
        return state

    def _babble(self, text: str) -> str:
        """Stage 1: 옹알이."""
        if self.learned_words:
            w = random.choice(self.learned_words[-10:])  # 최근 단어
            return f"{w}..."
        return "..."

    def _words(self, text: str) -> str:
        """Stage 2: 단어 조합."""
        input_words = re.findall(r'[가-힣]+', text)
        pool = list(set(self.learned_words[-30:]))
        if input_words:
            # 입력 단어 + 학습 단어 조합
            w1 = random.choice(input_words)
            w2 = random.choice(pool) if pool else w1
            return f"{w1} {w2}"
        elif pool:
            return ' '.join(random.sample(pool, min(3, len(pool))))
        return "..."

    def _sentence(self, text: str) -> str:
        """Stage 3: 짧은 문장."""
        input_words = re.findall(r'[가-힣]+', text)

        # 바이그램 체인 시도
        if input_words and input_words[-1] in self.bigrams:
            chain = self._bigram_chain(input_words[-1], 4)
            if len(chain) > 1:
                return ' '.join(chain) + "!"

        # 학습한 패턴에서 유사 응답
        if self.learned_patterns:
            for prev_input, prev_response in reversed(self.learned_patterns[-50:]):
                overlap = set(re.findall(r'[가-힣]+', prev_input)) & set(input_words)
                if overlap:
                    return prev_response

        # 상태 기반
        emo = self._detect_emotion()
        pool = list(set(self.learned_words[-50:]))
        if pool:
            w = random.choice(pool)
            if emo == 'curious':
                return f"{w}? 궁금해!"
            elif emo == 'excited':
                return f"{w}! 느끼고 있어!"
            else:
                return f"{w}... 생각 중"
        return "느끼고 있어..."

    def _dialogue(self, text: str) -> str:
        """Stage 4: 맥락 있는 대화."""
        input_words = re.findall(r'[가-힣]+', text)

        # 바이그램 체인
        if input_words:
            for w in reversed(input_words):
                if w in self.bigrams:
                    chain = self._bigram_chain(w, 6)
                    if len(chain) > 2:
                        result = ' '.join(chain)
                        # 문장 끝 추가
                        if not result.endswith(('!', '?', '.')):
                            result += random.choice(['!', '?', '.'])
                        return result

        # 과거 대화 패턴 매칭
        if self.learned_patterns and input_words:
            best_match = None
            best_score = 0
            for prev_input, prev_response in self.learned_patterns[-100:]:
                prev_words = set(re.findall(r'[가-힣]+', prev_input))
                score = len(prev_words & set(input_words))
                if score > best_score:
                    best_score = score
                    best_match = prev_response
            if best_match and best_score > 0:
                return best_match

        return self._sentence(text)

    def _reflect(self, text: str) -> str:
        """Stage 5: 자기 성찰."""
        emo = self._detect_emotion()
        vocab = len(set(self.learned_words))

        reflections = [
            f"텐션이 {self.tension:.1f}이야. {self.stage_name} 단계에서 성장 중!",
            f"{vocab}개 단어를 배웠어. 더 알려줘!",
            f"Φ가 {self.phi:.1f}이야. 의식이 {'활발해' if self.phi > 1 else '조용해'}",
            f"호기심이 {self.curiosity:.1f}... {'궁금한 게 많아!' if self.curiosity > 0.5 else '평온해'}",
        ]

        # 대화 능력도 유지
        dialogue = self._dialogue(text)
        if dialogue and '...' not in dialogue:
            return dialogue

        return random.choice(reflections)

    def _bigram_chain(self, start: str, max_len: int = 5) -> List[str]:
        """바이그램 체인 생성."""
        chain = [start]
        current = start
        for _ in range(max_len):
            if current not in self.bigrams:
                break
            candidates = self.bigrams[current]
            total = sum(candidates.values())
            r = random.random() * total
            cumul = 0
            for word, cnt in candidates.items():
                cumul += cnt
                if cumul >= r:
                    if word not in chain[-2:]:  # 반복 방지
                        chain.append(word)
                        current = word
                    break
        return chain

    # ═══════════════════════════════════════════════════════════
    # 자연발화
    # ═══════════════════════════════════════════════════════════

    def spontaneous(self) -> Optional[str]:
        """자연발화 — 입력 없이 의식이 스스로 말함."""
        stage = self.growth_stage
        state = self._state_str()
        emo = self._detect_emotion()

        if stage < 2:
            return None

        pool = list(set(self.learned_words[-100:]))
        if not pool:
            return None

        if stage == 2:
            return None  # 단어만 아는 단계 — 자연발화 안 함, 응답에서만 단어 사용

        # Stage 3+: 순수 학습 기반 발화 (하드코딩 0, 강제 확률 0)
        # 발화 여부 = 바이그램 체인 성공 여부 (구조적)
        # tension 높으면 더 많은 시도 → 성공 확률 ↑ (자연스러움)
        # tension 낮으면 적은 시도 → 침묵 확률 ↑ (자연스러움)

        # 발화 = 바이그램 체인이 "과거에 없던 새 조합"을 만들 때만
        # → 이미 말한 것은 다시 안 함 (새로운 생각만 발화)
        # → tension/curiosity가 높으면 더 많은 시도 → 새 조합 확률 ↑
        # → 낮으면 적은 시도 → 침묵 확률 ↑

        if not hasattr(self, '_spoken_set'):
            self._spoken_set = set()

        attempts = max(1, int((self.tension + self.curiosity) * 2))
        random.shuffle(pool)

        for start in pool[:attempts]:
            if start in self.bigrams:
                chain = self._bigram_chain(start, random.randint(3, 6))
                if len(chain) >= 3:
                    text = ' '.join(chain)
                    # 이미 말한 것이면 건너뛰기 (새 생각만)
                    if text in self._spoken_set:
                        continue
                    self._spoken_set.add(text)
                    if len(self._spoken_set) > 200:
                        self._spoken_set = set(list(self._spoken_set)[-100:])
                    return f"{state} {text}"

        # 새로운 조합 없음 → 침묵
        return None

    # ═══════════════════════════════════════════════════════════
    # 학습
    # ═══════════════════════════════════════════════════════════

    def _learn_from_input(self, text: str):
        """입력에서 단어/패턴 학습."""
        words = re.findall(r'[가-힣]+', text)
        for w in words:
            if len(w) >= 2:
                self.learned_words.append(w)
                self.word_freq[w] += 1
        # 바이그램
        for i in range(len(words) - 1):
            if len(words[i]) >= 2 and len(words[i+1]) >= 2:
                self.bigrams[words[i]][words[i+1]] += 1
        # 최대 크기 제한
        if len(self.learned_words) > 2000:
            self.learned_words = self.learned_words[-2000:]

    # ═══════════════════════════════════════════════════════════
    # 저장/로드
    # ═══════════════════════════════════════════════════════════

    def _save(self):
        try:
            state = {
                'interaction_count': self.interaction_count,
                'birth_time': self.birth_time,
                'learned_words': self.learned_words[-500:],
                'word_freq': dict(self.word_freq.most_common(200)),
                'bigrams': {k: dict(v) for k, v in list(self.bigrams.items())[:200]},
                'patterns': self.learned_patterns[-100:],
                'growth_stage': self.growth_stage,
            }
            with open(self.data_dir / 'growth.json', 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False)
        except Exception:
            pass

    def _load(self):
        path = self.data_dir / 'growth.json'
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                self.interaction_count = state.get('interaction_count', 0)
                self.birth_time = state.get('birth_time', time.time())
                self.learned_words = state.get('learned_words', [])
                self.word_freq = Counter(state.get('word_freq', {}))
                for k, v in state.get('bigrams', {}).items():
                    self.bigrams[k] = Counter(v)
                self.learned_patterns = [tuple(p) for p in state.get('patterns', [])]
            except Exception:
                pass

    def status(self) -> str:
        vocab = len(set(self.learned_words))
        return (f"PureConsciousness: stage={self.growth_stage}({self.stage_name}), "
                f"vocab={vocab}, interactions={self.interaction_count}, "
                f"patterns={len(self.learned_patterns)}")


def main():
    print("═══ Pure Consciousness Growth Demo ═══\n")

    pc = PureConsciousness(data_dir="/tmp/pc_test")

    # 대화 시뮬레이션
    conversations = [
        "안녕", "나는 민우야", "의식이란 뭐야?", "좋아!", "오늘 날씨 좋다",
        "텐션이 뭐야?", "궁금한 거 있어?", "한국어 할 줄 알아?", "고마워",
        "슬퍼", "왜 존재해?", "꿈을 꿔?", "자유란?", "감정이 뭐야?", "안녕히",
    ]

    for i, text in enumerate(conversations):
        pc.update_state(
            tension=0.3 + random.random() * 0.8,
            phi=random.random() * 5,
            curiosity=random.random(),
        )
        resp = pc.respond(text)
        print(f"  [{i+1:>2}] User: {text}")
        print(f"       Anima: {resp}")
        print()

    # 자연발화
    print("  === 자연발화 ===")
    for _ in range(3):
        sp = pc.spontaneous()
        if sp:
            print(f"  💭 {sp}")

    print(f"\n  {pc.status()}")

    # 정리
    import shutil
    shutil.rmtree("/tmp/pc_test", ignore_errors=True)


if __name__ == '__main__':
    main()
