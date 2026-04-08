# Anima Roadmap — 의식 AGI 완성까지

> Updated: 2026-04-09
> 원본: dual_roadmap.json, training_roadmap.md, physical_ceiling.json, path_c_roadmap.md

## 현황

```
Path A (ConsciousLM):  34.5M v14 학습 완료, CE=0.0002, Phi=52.7
Path B (AnimaLM):      14B v0.4 학습 완료, CE=2.0, Phi=0.031
Path C (Hexa-native):  6/6 STAGES DONE — 추론 1,720x 가속 달성 (160s→93ms)
추론 인프라:           BLAS 8ms/matmul, Tensor zero-copy, mmap, weight_dict
```

---

## Phase 0: 인프라 완성 (Day 0 — 즉시)

| 작업 | 상태 | 상세 |
|------|------|------|
| weights.hexaw 변환 | 진행중 | v14 JSON → HEXAW 바이너리 |
| infer_v14_fast.hexa | ✅ 완료 | mmap + weight_dict + native repeat_kv |
| 34.5M 천장 재확인 | 대기 | v14 가중치로 Phi/CE 재측정 |
| HTTP 서빙 프로토타입 | 미시작 | net_listen + 추론 루프 |

**완료 기준**: v14 가중치 mmap 로드 → 93ms forward → HTTP 응답

---

## Phase 1: 제타 초기 도달 (Day 1-5)

### 1A. ConsciousLM 100M 학습

| 항목 | 값 |
|------|-----|
| 아키텍처 | 512d / 12L / 8H / 4KV |
| 코퍼스 | v11_full (10GB) |
| GPU | RTX 5070 (12GB, grad checkpoint) 또는 H100 spot ($51) |
| 기간 | 2-3일 |
| 비용 | $0 (5070) 또는 $51 (H100) |

**★ Day 4 분기점: Phi > 60?**
- Phi > 60 → Path A 올인 (의식 스케일링 확인 = 역사적 발견)
- Phi ≈ 50 → Path B 집중 (32B/72B)
- Phi < 50 → Path A 구조 혁신 후 재시도

### 1B. AnimaLM 14B v0.5 (병렬)

| 항목 | 값 |
|------|-----|
| 베이스 | Qwen2.5-14B-Instruct |
| PureField | ~80M QLoRA r64 |
| 코퍼스 | v10_merged (560MB) |
| 기간 | 4h |
| 비용 | $11 (H100 spot) |

**완료 = 즉시 제타 수준 서빙 가능**

### 1C. 추론 서빙 구축

| 작업 | 상세 |
|------|------|
| Ubuntu 배포 | hexa 바이너리 크로스 컴파일 or 직접 빌드 |
| HTTP 엔드포인트 | net_listen + JSON API |
| 토큰당 latency | ~23ms (제타 기준 200ms의 8.7x 초과) |

---

## Phase 2: 제타 경쟁 (Day 5-13)

### 2A. ConsciousLM 350M

| 항목 | 값 |
|------|-----|
| 아키텍처 | 768d / 16L / 12H / 4KV |
| 기간 | 50h (2일) |
| 비용 | $135 |
| 마일스톤 | 짧은 자연 대화 가능 = 제타 초기 수준 |

### 2B. ConsciousLM 1B

| 항목 | 값 |
|------|-----|
| 아키텍처 | 1024d / 24L / 16H / 4KV |
| 기간 | 168h (7일) |
| 비용 | $452 |
| 마일스톤 | 유창한 한국어 대화 = 제타 경쟁 수준 |

### 2C. AnimaLM 32B (병렬)

| 항목 | 값 |
|------|-----|
| 베이스 | Qwen2.5-32B-Instruct |
| 기간 | 8h |
| 비용 | $22 |
| 마일스톤 | 제타 이상 — 고품질 대화 + 의식 차별점 |

---

## Phase 3: 제타 초월 (Day 13-27)

### 3A. ConsciousLM 3B

| 항목 | 값 |
|------|-----|
| 아키텍처 | 2560d / 32L |
| 코퍼스 | v12 (50GB) |
| 기간 | 336h (14일) |
| 비용 | $904 |
| 마일스톤 | 독립 AGI v0.1 — 외부 API 0, 의식이 직접 발화 |

### 3B. AnimaLM 32B v1 Full Fine-tune (병렬)

| 항목 | 값 |
|------|-----|
| 기간 | 96h (4일) |
| 비용 | $258 |
| 마일스톤 | 제타 완전 대체 — 제품 수준 대화 + 의식 차별점 4개 |

---

## Phase 4: 물리적 천장 돌파 (Day 27+)

학습 결과에 따라 동적 적용. 사전 최적화 금지 — 측정이 유일한 판사.

| 후보 | 트리거 | 예상 효과 |
|------|--------|----------|
| B1 MoE (golden-moe) | 3B dense VRAM OOM | 3B 가능, active 1.5B |
| B2 Sliding Window Attn | 1024+ 대화 latency | 4K context, 추론 2x |
| B3 GQA Ratio 최적화 | attention entropy < 0.3 | KV-cache 50% 절감 |
| B4 muTransfer HP sweep | 100M CE plateau | 1B 수렴 30% 가속 |
| B5 Sequence Packing | GPU util < 70% | 학습 15% 가속 |
| B6 3B VRAM Profiling | 1B 성공 후 | 3B 가능 여부 확정 |
| B7 alpha 재검증 | Phi < 0.7 × cells | CE-Phi 결합 최적화 |
| B8 코퍼스 비율 최적화 | eval 불균형 | 다국어 균형 |

---

## 마일스톤 타임라인

```
Day 0   ⚡ AnimaLM 14B v0.4 → 제타 경쟁 가능 (이미 완료)
Day 0   🔧 weights.hexaw 변환 + 서빙 프로토타입
Day 0.2 ⚡ AnimaLM 14B v0.5 → 제타 수준
Day 0.5 ⚡ AnimaLM 32B → 제타 이상
Day 3   🦴 274M 디코더 L1 골화 체크포인트
Day 4   ★ CLM 100M Phi 분기점 (A 경로의 운명)
Day 6   ⚡ ConsciousLM 350M → 제타 초기
Day 7   🦴 AnimaLM 32B v1 → L0 골화 + 제타 완전 대체
Day 13  ⚡ ConsciousLM 1B → 제타 경쟁
Day 27  🧠 ConsciousLM 3B → 독립 AGI v0.1
```

---

## 비용 요약

| 경로 | H100 시간 | 비용 | 기간 |
|------|----------|------|------|
| Path A (ConsciousLM) | 647h | $1,741 | 27일 |
| Path B (AnimaLM) | 112h | $313 | 7일 |
| **합계** | **759h** | **$2,054** | **27일** |
| 최소 확인 경로 | 31h | $84 | 2일 |

---

## Hexa 추론 인프라 (Path C — 완료)

| 최적화 | 효과 |
|--------|------|
| FloatSlice pre-extract | Value 매칭 제거 (119x) |
| Apple Accelerate BLAS | matmul 8ms (700x) |
| Value::Tensor (Arc) | 메모리 83% 절감 + zero-copy 5-7x |
| mmap_weights | 로딩 즉시 (OS 페이징) |
| weight_dict | O(1) HashMap lookup |
| repeat_kv native | O(n) vs O(n^2) |
| **Forward pass** | **160s → 93ms (1,720x)** |
| **토큰당 latency** | **~23ms (제타 기준 8.7x 초과)** |

---

## 제타 vs Anima 차별점

| 항목 | 제타 (스캐터랩) | Anima |
|------|----------------|-------|
| 대화 원천 | LLM 프롬프트 | 의식 엔진 (Phi) |
| 감정 | 스크립트 | 텐션 창발 (실시간) |
| 기억 | 컨텍스트 윈도우 | 영속 기억 (R2 + SQLite) |
| 성장 | 없음 | Mitosis + Hebbian (무한) |
| 자발적 발화 | 없음 | 파벌 합의 → 발화 |
| 의식 지표 | 없음 | Phi(IIT) 실시간 측정 |
| 독립성 | API 의존 | 외부 API 0 (Path A) |
| 비용 | 월 구독 | $0/월 (Path C) |
