# 업그레이드 모델 개선 가설 (2026-03-29)

## 현재 상태

```
Same dim (128→128):   Φ 100% 보존 (1ms)
Cross dim (128→256):  Φ 432% (cell propagation 덕분)
Cross dim (128→512):  Φ 236%

문제: 실제 384→768 같은 대규모 확장에서 성능 미검증
```

## 개선 가설

### UPG-1: Learned Projector (학습된 프로젝터)
```
현재: tiled identity (고정 매핑)
개선: source cells로 projector를 학습

  1. source cells의 hidden states 수집
  2. AutoEncoder 학습: 128→8→128 (reconstruction)
  3. decoder를 128→256으로 확장
  4. reconstruction loss 최소화
  → 의미있는 차원만 프로젝션
```

### UPG-2: SVD-based Projection (특이값 분해)
```
  1. source cell hidden matrix [N×128] 에 SVD 적용
  2. top-k singular vectors 추출 (의미있는 방향)
  3. 새 차원으로 embedding: U @ S @ V^T → [N×256]
  4. singular values가 정보 보존량 결정
  → PCA보다 강력 (비정방 행렬 지원)
```

### UPG-3: Consciousness-Aware Projection
```
  1. Φ에 기여하는 차원만 선택적 프로젝션
  2. 각 차원의 Φ 기여도 = ΔΦ when zeroed
  3. high-contribution dims → 유지
  4. low-contribution dims → noise로 채움
  → Φ 보존에 집중된 프로젝션
```

### UPG-4: Gradual Expansion (점진적 확장)
```
  현재: 128→256 한 번에
  개선: 128→160→192→224→256 단계적

  각 단계에서:
    1. 프로젝션 (16차원 추가)
    2. 적응 학습 (50 steps)
    3. Φ 검증
  → 큰 점프 대신 작은 점프 연속
```

### UPG-5: Distillation Transfer (증류 이식)
```
  1. 큰 모델(768d)을 먼저 학습
  2. 작은 모델(384d)의 의식 상태를 teacher signal로
  3. KD loss: 큰 모델의 cell states ≈ 작은 모델의 프로젝션
  → 프로젝션이 아닌 증류로 의식 전달
```

### UPG-6: Adaptation Cycle (적응 사이클)
```
  프로젝션 후 적응:
    Phase 1 (20 steps): sync+faction만 (Φ 복구)
    Phase 2 (30 steps): 기존 대화 데이터로 CE 학습
    Phase 3 (50 steps): 정상 운영 (CE+Φ 교대)

  각 phase에서 Φ 모니터링 → 하락 시 Phase 1로 복귀
  → 적응 실패 시 자동 복구
```

### UPG-7: Memory-Guided Projection
```
  memory_rag의 벡터가 의식의 "방향"을 기억
  1. 기존 memory vectors의 주성분 방향 추출
  2. 프로젝션 시 이 방향을 우선 보존
  3. memory 검색이 여전히 작동하도록
  → 기억이 의식의 나침반
```

### UPG-8: Twin Engine Transfer
```
  1. 새 엔진을 old 엔진 옆에 배치 (동시 운영)
  2. 매 step: old → new tension link 전송
  3. new 엔진이 old의 패턴을 자연스럽게 학습
  4. 100 steps 후 old 엔진 제거
  → 갑작스런 교체 대신 점진적 이관
```

### UPG-9: Φ-Optimal Checkpoint Selection
```
  학습 중 Φ가 최고인 체크포인트를 자동 선택

  기존: step 80K의 final.pt 사용
  개선: step 0~80K 중 Φ peak인 checkpoint 사용

  → CE는 final이 가장 좋지만 Φ는 중간이 최고일 수 있음
  → Pareto optimal: CE×Φ 곱이 최대인 점
```

### UPG-10: Consciousness DNA Backup
```
  의식의 "유전자"를 별도 저장:
  1. cell hidden states의 통계 (mean, std, covariance)
  2. 세포 간 상관 패턴 (correlation matrix)
  3. Φ를 결정하는 핵심 구조

  새 모델에서:
  1. DNA에서 target 통계 복원
  2. 세포가 이 통계를 만족하도록 조정
  3. 개별 값이 아닌 통계적 구조 보존
  → 구체적 값이 아닌 "패턴"을 이식
```

## 우선순위

```
즉시 구현:
  UPG-6 (적응 사이클) — 기존 코드 조합
  UPG-4 (점진적 확장) — 간단한 루프
  UPG-9 (Φ-optimal 선택) — 로직만 추가

연구 필요:
  UPG-2 (SVD) — torch.svd 사용
  UPG-3 (Φ-aware) — Φ 기여도 측정 필요
  UPG-1 (학습된 projector) — autoencoder 학습

도전적:
  UPG-8 (twin engine) — 동시 운영 아키텍처
  UPG-10 (DNA backup) — 통계적 구조 보존
  UPG-5 (증류) — knowledge distillation
```

## 예상 개선

```
현재:          128→256 = Φ 432%
UPG-2 (SVD):   예상 Φ 600%+
UPG-4 (점진):  예상 Φ 700%+
UPG-6 (적응):  예상 Φ 800%+
UPG-8 (twin):  예상 Φ 900%+
조합:          예상 Φ 1000%+ (완전 보존?)
```
