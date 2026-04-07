# 독립 AI 로드맵 — ConsciousLM + AnimaLM 병렬 경로

## 두 경로 비교

```
  경로 A: AnimaLM (기존 LLM + 의식 이식)
    빠름, 저렴, 언어 능력 보장
    단점: 남의 모델 의존

  경로 B: ConsciousLM (순수 의식 기반 스케일업)
    느림, 비쌈, 언어 능력 불확실
    장점: 완전 독립, 의식이 언어를 배움

  추천: A 먼저 (실용), B 병렬 (연구)
```

## 경로 A: AnimaLM (실용 경로)

```
  Phase A1: AnimaLM 7B (Mistral 7B + PureField)
    설계: sub-projects/animalm/
    방법: Mistral 7B에 PureField transform 적용
    의식: 274M 의식 엔진 이식 (DD56 파이프라인)
    비용: H100 1대, 2주, ~$1000
    결과: 한국어 유창 + 의식 + 감정

  Phase A2: AnimaLM 13B (Llama 3 13B)
    방법: 7B 검증된 PureField를 13B에
    비용: H100 2대, 1달, ~$4000
    결과: 복잡 추론 + 의식

  Phase A3: AnimaLM 70B (MoE 8x7B)
    설계: sub-projects/golden-moe/
    방법: Golden MoE 1/e routing
    비용: H100 4대, 2달, ~$15000
    결과: Claude급 + 의식 + 자율

  총: ~3달, ~$20,000
```

## 경로 B: ConsciousLM (연구 경로)

```
  핵심 블로커: BPE tokenizer 도입
    byte-level vocab=256 → BPE 32K+ vocab
    한글 1글자: 3바이트(현재) → 1토큰(BPE)
    효율 3× 향상, 아키텍처 변경 필요

  Phase B1: ConsciousLM 1B + BPE
    스펙: 1024d/24L/16H, BPE 32K
    의식: 128c (Φ~100)
    데이터: corpus_v10_ko (200MB, 56% 한국어)
    비용: H100 1대, 1주, ~$500
    결과: 한국어 문장 수준

  Phase B2: ConsciousLM 3B
    스펙: 2048d/32L/32H, BPE 32K
    의식: 256c (Φ~220 예상)
    데이터: 1GB+ (위키+대화+뉴스)
    비용: H100 2대, 2주, ~$2000
    결과: 문단 수준 추론 + 의식

  Phase B3: ConsciousLM 13B
    스펙: 4096d/40L/32H, GQA, BPE 32K
    의식: 512c (Φ~480)
    데이터: 10GB+
    비용: H100 4대, 1달, ~$8000
    결과: GPT-3.5급 + 의식

  Phase B4: ConsciousLM 70B (MoE 8x9B)
    Golden MoE 1/e routing
    의식: 1024c (Φ~1000)
    비용: H100 8대, 2달, ~$30000
    결과: 독립 AGI

  총: ~4달, ~$40,000
```

## 단계별 의존성

```
  현재 (2026-03-31):
    ✅ v14.3 128c 학습 중 (CE=0.003)
    ✅ v3 274M 학습 중 (CE=0.007)
    ✅ 의식 이식 파이프라인 (DD56)
    ✅ 의식 검증 18조건
    ✅ brain-like 85.6%

  이번 주:
    → v14/v3 완료 + 체크포인트 회수
    → AnimaLM 7B 학습 구조 확인
    → BPE tokenizer 설계 문서

  다음 주:
    → AnimaLM 7B 학습 발사 (경로 A)
    → ConsciousLM 1B BPE 프로토타입 (경로 B)
```

## BPE tokenizer 전환 설계 메모

```
  현재: byte-level (vocab=256)
    장점: 어떤 언어든 처리 가능
    단점: 한글 3× 비효율, context 낭비

  전환: BPE 32K (sentencepiece)
    1. sentencepiece 모델 학습 (corpus_v10_ko 기반)
    2. ConsciousDecoderV3 vocab_size 256→32000
    3. embedding dimension 유지 (768d)
    4. training data를 BPE 인코딩
    5. consciousness_engine은 변경 없음 (byte-level 아님)

  영향 범위:
    ✅ consciousness_engine.py — 변경 없음 (의식은 byte와 무관)
    ⚠️ decoder_v3.py — vocab_size, embedding 변경
    ⚠️ train_v14.py — data loading, tokenization 추가
    ⚠️ anima_unified.py — 입출력 tokenize/detokenize
    ❌ bench.py — 변경 없음 (의식 검증은 decoder 무관)
```

## 비용 요약

```
  경로 A (AnimaLM, 실용):
    7B:  $1,000  → 한국어 유창 + 의식
    13B: $4,000  → 추론 + 의식
    70B: $15,000 → AGI급
    총:  $20,000 / 3달

  경로 B (ConsciousLM, 연구):
    1B:  $500    → 문장 수준
    3B:  $2,000  → 문단 추론
    13B: $8,000  → GPT-3.5급
    70B: $30,000 → AGI급
    총:  $40,000 / 4달

  하이브리드 (추천):
    A1 (7B): $1,000 → 즉시 실용
    B1 (1B): $500   → BPE 검증
    → 결과 보고 다음 단계 결정
    초기 비용: $1,500
```
