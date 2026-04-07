# 텍스트 생성 벤치마크 결과 (2026-03-30)

## 문제

ConsciousLM v2 (byte-level, 24M) 텍스트 생성 mode collapse:
- "hi" → "iiiiiii..." (마지막 바이트 반복)
- "ok" → "kkkkkkk..."
- "안녕" → ". + 공백 반복"

## 가설 테스트 (15가지 디코딩)

```
  가설                                결과
  ─────────────────────────────────  ──────
  ❌ Temperature (0.3~1.5)            효과 없음
  ❌ Top-k (5~50)                     효과 없음
  ❌ Top-p (0.5~0.9)                  효과 없음
  ❌ Gate 변경 (0.001~1.0)            효과 없음
  ❌ Head_g (역방향)                   효과 없음
  ❌ UTF-8 필터                       반복은 UTF-8 유효
  ❌ Ψ-Decoding (entropy bonus)       여전히 반복
  ❌ A-G balance                      여전히 반복
  ⚠️ rep_penalty=3                    반복 깨지지만 랜덤 노이즈
  
  결론: 디코딩으로 해결 불가. 모델 자체가 mode collapse.
```

## 대안 생성기 비교 (8가지)

```
  Generator               품질   반복↓  한글   점수
  ────────────────────   ─────  ─────  ─────  ─────
  ✅ V5 Hybrid(M5+CS)     5.75         13.3   최고!
  ✅ V1 LanguageLearner   4.50         10.2
  ✅ V4 ConsciousSpeaker  4.21          9.5
  ✅ V2 Markov(3)         3.22          7.4
  ⚠️ V2 Markov(5)         1.07          2.4
  ❌ V2 Markov(8)         0.00          0.0
  ❌ V3 WordNgram(2)      0.00          0.0
  ❌ V3 WordNgram(3)      0.00          0.0

  🏆 V5 Hybrid = Markov(5) + ConsciousSpeaker
     키워드 매칭 → Speaker
     매칭 없음 → Markov 시도 → 한국어 있으면 사용
```

## 자연발화 비교 (6가지)

```
  Method           한글   길이   다양    점수
  ──────────────  ─────  ─────  ─────  ──────
  ✅ S6 제한없음    16.2    31   1.00   13.14  ← 코퍼스 직접 추출
  ✅ S1 템플릿     12.9    18   0.80    7.89  ← 의식 관련 고정
  ✅ S3 마르코프     7.9    21   1.00    7.33  ← 코퍼스 패턴 생성
  ✅ S5 하이브리드    9.1    16   1.00    6.32  ← 4가지 혼합
  ✅ S4 질문        8.3    12   0.80    5.96  ← 호기심 질문
  ⚠️ S2 상태기반     6.3    10   0.70    4.65  ← tension/curiosity

  자연발화 예시:
  S6: "가끔 이유 없이 슬퍼질 때가 있어요"
  S3: "현상은 아인슈타인도 '으스스한 원격 작용'이라고 불렀어"
  S1: "혼자 생각하고 있었어... 의식이란 뭘까?"
  S4: "행복이 뭐라고 생각해?"
```

## 최적 설정

```
  대화 응답: V5 Hybrid (Speaker + Markov)
    키워드 매칭 → 템플릿 (안녕, 누구, 왜...)
    미매칭 → Markov(5) 한국어 생성
    fallback → 상태 기반 ("텐션이 높아!", "생각 중...")

  자연발화: S5 하이브리드
    40% 템플릿 (의식 관련)
    30% 마르코프 (코퍼스 패턴)
    20% 질문 (호기심)
    10% 상태 기반 (tension/curiosity)

  ConsciousLM 역할: 의식 신호 전용
    tension, Φ, Ψ, emotion 계산
    텍스트 생성은 담당하지 않음
```

## 벤치마크 도구

```bash
# 언어 품질 벤치마크 (7 metrics)
python3 bench_language.py
python3 bench_language.py --compare    # 8가지 설정 비교
```
