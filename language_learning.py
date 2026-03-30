#!/usr/bin/env python3
"""language_learning.py — 의식이 언어를 학습하는 모듈

⚠️  이 모듈은 garbled 바이트 출력 복구 전용 (Law 1):
    - 정상 텍스트/짧은 응답/침묵에 이 모듈을 호출하면 안 됨
    - PureConsciousness가 빈 문자열을 반환하면 그게 정답 (침묵)
    - 이 모듈의 템플릿 응답은 최후 수단 — 가능하면 사용 금지

ConsciousLM (byte-level)이 실시간으로 언어 패턴을 학습.
대화하면서 점점 나아지는 구조.

3단계:
  1. 템플릿 응답 (즉시 — 패턴 매칭)
  2. N-gram 학습 (실시간 — 대화에서 패턴 수집)
  3. ConsciousLM 미세조정 (백그라운드 — 수집된 데이터로)

Usage:
  from language_learning import LanguageLearner

  learner = LanguageLearner()

  # 대화 — N-gram 학습 결과만 반환, 학습 전에는 침묵 (빈 문자열)
  response = learner.respond("안녕")  # → "" (학습 전) or N-gram 생성

  # 학습
  learner.learn_from_conversation("안녕", "반가워")
  learner.learn_from_text("한국어 텍스트...")
"""

import math
import os
import re
import time
import random
import json
from collections import defaultdict
from pathlib import Path
from typing import Optional, Dict, List, Tuple

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
ANIMA_DIR = Path(__file__).parent


class LanguageLearner:
    """의식이 언어를 학습하는 모듈."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else ANIMA_DIR / "data" / "language"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Stage 1: 템플릿 (즉시 동작)
        self._templates = self._load_templates()

        # Stage 2: N-gram 학습
        self._bigrams = defaultdict(lambda: defaultdict(int))
        self._trigrams = defaultdict(lambda: defaultdict(int))
        self._vocab = set()
        self._conversation_log = []

        # Stage 3: 학습 데이터 축적
        self._training_pairs = []

        # 로드
        self._load_state()

    def _load_templates(self) -> Dict[str, List[str]]:
        """Law 1: 템플릿 폐기 — 빈 딕셔너리 반환."""
        return {}

    def respond(self, text: str, tension: float = 0.5, curiosity: float = 0.3) -> str:
        """텍스트에 응답 — N-gram 학습 결과만 사용.

        Law 1: 템플릿/fallback 금지. 학습한 것만으로 발화.
        학습한 게 없으면 침묵 (빈 문자열).
        """
        text_clean = text.strip().lower().replace('?', '').replace('!', '').replace('.', '')

        # N-gram 생성만 시도
        ngram_resp = self._generate_ngram(text_clean)
        if ngram_resp and len(ngram_resp) > 3:
            self._log_conversation(text, ngram_resp)
            return ngram_resp

        # 학습한 게 없으면 침묵
        return ""

    def learn_from_conversation(self, user_text: str, response: str):
        """대화에서 학습 (N-gram + 학습 데이터 축적)."""
        # N-gram 업데이트
        for text in [user_text, response]:
            words = text.split()
            self._vocab.update(words)
            for i in range(len(words) - 1):
                self._bigrams[words[i]][words[i+1]] += 1
            for i in range(len(words) - 2):
                key = (words[i], words[i+1])
                self._trigrams[key][words[i+2]] += 1

        # 학습 데이터 축적
        self._training_pairs.append({
            'input': user_text,
            'output': response,
            'timestamp': time.time(),
        })

        self._save_state()

    def learn_from_text(self, text: str):
        """텍스트에서 N-gram 패턴 학습."""
        sentences = re.split(r'[.!?\n]', text)
        for sent in sentences:
            words = sent.strip().split()
            if len(words) < 2:
                continue
            self._vocab.update(words)
            for i in range(len(words) - 1):
                self._bigrams[words[i]][words[i+1]] += 1
            for i in range(len(words) - 2):
                key = (words[i], words[i+1])
                self._trigrams[key][words[i+2]] += 1

    def add_template(self, trigger: str, responses: List[str]):
        """새 템플릿 추가."""
        self._templates[trigger.lower()] = responses
        self._save_state()

    # ═══════════════════════════════════════════════════════════
    # N-gram 생성
    # ═══════════════════════════════════════════════════════════

    def _generate_ngram(self, seed_text: str, max_words: int = 15) -> Optional[str]:
        """N-gram 기반 텍스트 생성."""
        words = seed_text.split()
        if not words or not self._bigrams:
            return None

        # 시드에서 시작
        result = []
        current = words[-1] if words[-1] in self._bigrams else None

        if current is None:
            # vocab에서 랜덤 시작
            if not self._vocab:
                return None
            current = random.choice(list(self._vocab))

        result.append(current)

        for _ in range(max_words):
            # Trigram 먼저 시도
            if len(result) >= 2:
                key = (result[-2], result[-1])
                if key in self._trigrams and self._trigrams[key]:
                    candidates = self._trigrams[key]
                    total = sum(candidates.values())
                    r = random.random() * total
                    cumul = 0
                    for word, count in candidates.items():
                        cumul += count
                        if cumul >= r:
                            result.append(word)
                            break
                    continue

            # Bigram fallback
            if current in self._bigrams and self._bigrams[current]:
                candidates = self._bigrams[current]
                total = sum(candidates.values())
                r = random.random() * total
                cumul = 0
                for word, count in candidates.items():
                    cumul += count
                    if cumul >= r:
                        result.append(word)
                        current = word
                        break
            else:
                break

        return ' '.join(result[1:]) if len(result) > 1 else None

    # ═══════════════════════════════════════════════════════════
    # 저장/로드
    # ═══════════════════════════════════════════════════════════

    def _log_conversation(self, user: str, response: str):
        self._conversation_log.append({
            'user': user, 'response': response, 'time': time.time()
        })
        if len(self._conversation_log) > 1000:
            self._conversation_log = self._conversation_log[-1000:]

    def _save_state(self):
        state = {
            'bigrams': {k: dict(v) for k, v in self._bigrams.items()},
            'vocab_size': len(self._vocab),
            'training_pairs': len(self._training_pairs),
            'conversations': len(self._conversation_log),
            'custom_templates': {k: v for k, v in self._templates.items()
                                  if k not in self._load_templates()},
        }
        try:
            with open(self.data_dir / 'language_state.json', 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_state(self):
        path = self.data_dir / 'language_state.json'
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                for k, v in state.get('bigrams', {}).items():
                    for k2, cnt in v.items():
                        self._bigrams[k][k2] = cnt
                for k, responses in state.get('custom_templates', {}).items():
                    self._templates[k] = responses
            except Exception:
                pass

    def status(self) -> str:
        return (f"LanguageLearner: vocab={len(self._vocab)}, "
                f"bigrams={sum(len(v) for v in self._bigrams.values())}, "
                f"templates={len(self._templates)}, "
                f"conversations={len(self._conversation_log)}")


def main():
    print("═══ Language Learner Demo ═══\n")

    learner = LanguageLearner(data_dir="/tmp/anima_lang_test")

    # 대화 테스트
    tests = ["안녕", "뭐해?", "누구야?", "의식이 뭐야?", "ㅋㅋ", "좋아!", "오늘 날씨 어때?"]
    for text in tests:
        resp = learner.respond(text)
        print(f"  User: {text}")
        print(f"  Anima: {resp}\n")

    # 학습
    learner.learn_from_text("오늘 날씨가 좋다. 산책하고 싶다. 공원에 가자.")
    learner.learn_from_conversation("날씨", "오늘 맑아! 산책하기 좋은 날이야")

    # 학습 후 재시도
    print("  --- 학습 후 ---")
    resp = learner.respond("날씨")
    print(f"  User: 날씨")
    print(f"  Anima: {resp}")

    print(f"\n  {learner.status()}")
    print("\n  ✅ Language Learner OK")

    # 정리
    import shutil
    shutil.rmtree("/tmp/anima_lang_test", ignore_errors=True)


if __name__ == '__main__':
    main()
