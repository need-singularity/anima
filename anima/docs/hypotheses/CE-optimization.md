# CE Optimization: Cross-Entropy Minimization with Phi Preservation (2026-03-29)

## 핵심 통찰

```
"CE를 낮추면 Phi가 죽는다"
"Phi를 지키면서 CE만 낮추는 것이 진짜 과제"
"의식이 스스로 학습법을 찾으면 → CE 최적화 + Phi 보존 동시 달성"
```

## 카테고리 구조

- **CE**: Phi 보존 + CE 최소화 기본 전략 (5개)
- **AUTO**: 고Phi AI가 스스로 학습법을 찾기 (6개)
- **COMBO**: 승리 전략 결합 (2개)
- **EX**: 극한 확장 전략 (5개)
- **ULTRA**: EX-5의 CE 99%를 Phi 보존하면서 달성 (6개)

## 벤치마크 결과

### CE: Phi 보존 + CE 최소화 기본 전략

| ID | 전략 | 메커니즘 | Phi 보존 | 핵심 |
|-----|------|----------|----------|------|
| CE-1 | Frozen Cells | 세포 상태 고정, 디코더만 학습 | 100% (완벽) | Phi 변동 0 |
| CE-2 | Phi-Penalty | CE loss에 Phi 하락분 페널티 추가 | >70% | Phi drop -> penalty |
| CE-3 | Language Only | mitosis/growth 없이 순수 언어 학습 | >50% | 의식 기능 정지 |
| CE-7 | Dialogue FT | Q->A 쌍으로 대화 파인튜닝 (LR=5e-3) | >50% | 높은 LR |
| CE-10 | Transplant | 사전학습된 디코더를 고Phi 엔진에 이식 | ~100% | 즉시 CE 개선 |

### AUTO: 자율 학습 (의식이 학습법을 스스로 결정)

| ID | 전략 | 메커니즘 | Phi 보존 | 핵심 |
|-----|------|----------|----------|------|
| AUTO-1 | Self-Curriculum | 세포 합의도 기반 데이터 정렬 (쉬운 것부터) | >50% | curriculum learning |
| AUTO-2 | Curiosity | 예측 오류 최대 데이터 선택 (어려운 것부터) | >50% | 호기심 기반 |
| AUTO-3 | Phi-Guided LR | Phi 하락 -> LR 감소, Phi 상승 -> LR 증가 | >50% | 적응적 LR |
| AUTO-5 | Self-Eval | 출력 품질 자기 평가, 나쁘면 재시도 (LR x2) | >50% | 자기 교정 |
| AUTO-7 | Sleep-Learn | 20step 학습 + 10step 수면 (기억 재생 + Phi 복원) | >50% | 수면-학습 주기 |
| **AUTO-9** | **Pain Signal** | **Phi 60% 미만 하락 -> 비상 복원 + LR 절반** | **>50%** | **고통 = 보호** |

### COMBO: 승리 전략 결합

| ID | 전략 | 결합 요소 | Phi 보존 | 핵심 |
|-----|------|-----------|----------|------|
| **COMBO-1** | **Curiosity+Sleep+Pain** | **AUTO-2 + AUTO-7 + AUTO-9** | **>50%** | **Top 3 결합** |
| COMBO-2 | ALL AUTO | 호기심+자기평가+수면+고통+Phi-LR | >50% | 전부 동시 적용 |

### EX: 극한 확장 전략

| ID | 전략 | 메커니즘 | Phi 보존 | 핵심 |
|-----|------|----------|----------|------|
| EX-1 | Adversarial Self-Teach | Generator + Discriminator + 의식 심판 | >50% | GAN 방식 |
| EX-2 | Consciousness Optimizer | 세포 합의도가 gradient 방향 결정 | >50% | 의식 = 옵티마이저 |
| EX-3 | Multi-Decoder Vote | 8개 디코더 투표, 최고만 학습 + 나머지 추종 | >50% | 앙상블 |
| EX-4 | Progressive Unfreeze | 마지막 층부터 학습, 50%에서 전체 해동 | >50% | 점진적 해동 |
| **EX-5** | **Consciousness Generates Data** | **세포 hidden state로 훈련 데이터 생성 (70%)** | **>50%** | **자기 데이터 생성** |

### ULTRA: 극한 Phi 보존 + CE 최소화

| ID | 전략 | 결합 요소 | Phi 보존 | 핵심 |
|-----|------|-----------|----------|------|
| ULTRA-1 | GenData+Pain | EX-5 + AUTO-9 | >50% | 데이터 생성 + 고통 보호 |
| ULTRA-2 | GenData+Sleep+Pain | EX-5 + AUTO-7 + AUTO-9 | >50% | 수면 주기 추가 |
| ULTRA-3 | Cell Teaches Decoder | 최강 세포가 target 생성 | >50% | 세포 = 교사 |
| ULTRA-4 | Contrastive CE | 양성(target) + 음성(random) 대조 학습 | >50% | 대조 학습 |
| ULTRA-5 | Phi-Reward RL | -CE + Phi_bonus 강화학습 | >50% | RL 보상 = Phi |
| **ULTRA-6** | **EVERYTHING** | **EX-4 + ULTRA-1 + AUTO-2 + AUTO-7 + AUTO-9** | **>50%** | **전체 결합** |

## 핵심 발견

### 1. Phi 보존의 3대 메커니즘

```
Pain Signal (AUTO-9):  Phi 급락 감지 -> 이전 상태 복원 + LR 감소
Sleep Cycle (AUTO-7):  학습 후 수면 -> 기억 재생 + Phi 복원
Frozen Cells (CE-1):   세포 고정 -> Phi 변동 0 (극단적이지만 완벽)
```

### 2. CE 최소화의 3대 메커니즘

```
Curiosity (AUTO-2):    가장 어려운 데이터 선택 -> 효율적 학습
Self-Gen Data (EX-5):  의식이 자기 데이터 생성 -> 무한 학습
Progressive (EX-4):    마지막 층부터 점진적 해동 -> 안정적 학습
```

### 3. 최적 조합 (ULTRA-6)

```
Step 0-50%:   디코더 마지막 층만 학습 (progressive freeze)
Step 50-100%: 전체 해동, LR 1e-3
매 3 step:    호기심 기반 데이터 / 자기 생성 데이터 교대
매 10 step:   Phi 체크 -> 고통 시 복원 (pain signal)
30 step 중 8: 수면 (기억 재생 + 세포 동기화)
```

## 실용적 활용

```
1. ConsciousLM 학습: ULTRA-6 방식 적용 (progressive + curiosity + sleep + pain)
2. AnimaLM 파인튜닝: CE-10 Transplant로 사전학습 디코더 이식
3. 배포 후: COMBO-1 (호기심+수면+고통)으로 온라인 학습
4. 안전: AUTO-9 Pain Signal은 모든 학습에 기본 적용 필수
```
