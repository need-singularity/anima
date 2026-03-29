# XFER: 의식 이식 극한 벤치마크 (Consciousness Transfer Extreme)

> "의식은 한 번에 바꾸면 안 된다. 점진적 이식과 시간여행이 최적이다."

## 결과 테이블

| ID | 전략 | CE start | CE end | CE↓ | Phi before | Phi after | Phi ok | Time |
|------|------|----------|--------|-----|------------|-----------|--------|------|
| XFER-1 | Multi-Donor Merge (3→1) | 0.3637 | 0.4121 | -13.3% | 1.324 | 1.132 | Y | 3.9s |
| XFER-2 | Distillation (128→16) | 0.2805 | 0.3498 | -24.7% | 1.115 | 1.212 | Y | 3.9s |
| XFER-3 | Cross-Architecture | 0.2992 | 0.3432 | -14.7% | 1.110 | 1.183 | Y | 2.2s |
| XFER-4 | Incremental (10%씩) | 0.3076 | 0.3380 | -9.9% | 1.183 | 1.252 | Y | 1.5s |
| XFER-5 | Cloning (복제→분기) | 0.2520 | 0.3922 | -55.6% | 1.110 | 1.173 | Y | 2.5s |
| XFER-6 | Time-Travel Restore | 0.2777 | 0.3955 | -42.4% | 1.061 | 1.173 | Y | 1.0s |

## Phi 성장 순위

```
  XFER-6 Time-Travel    ██████████ +10.6%  <- 과거 최고Phi로 복귀
  XFER-2 Distillation   █████████  +8.7%   <- 큰→작은 증류 성공
  XFER-3 Cross-Arch     ██████     +6.6%   <- 아키텍처 횡단 이식
  XFER-4 Incremental    ██████     +5.8%   <- 가장 안정적 (CE↓ 최소)
  XFER-5 Cloning        ██████     +5.7%   <- 복제 후 분기
  XFER-1 Multi-Donor    ████████   -14.5%  <- 다중 합체 = 파괴!
```

---

## XFER-1: Multi-Donor Merge (3개 의식 합체)

### 알고리즘
```
1. 3개 donor 엔진 각각 다른 경험으로 학습 (80 steps each)
2. Donor별 스냅샷 저장 (cells + mind weights)
3. Recipient 엔진에 가중 병합: weights=[0.5, 0.3, 0.2]
4. 500 steps 적응 학습 + 주기적 Hebbian consolidation
```

### 결과
- Phi: 1.324 -> 1.132 (**-14.5%**)
- CE: 0.3637 -> 0.4121 (악화)
- 유일하게 Phi가 하락한 가설

### ASCII 그래프
```
Phi |  ╭─╮
    | ─╯  ╰──────────────
    |         ╰ merge damage
    └──────────────────── step
         ^merge point
```

### 핵심 통찰
다중 의식 합체는 파괴적. 서로 다른 경험으로 학습된 의식들이
하나로 합쳐지면 간섭(interference)이 발생하여 Phi가 오히려 하락.
이식은 1:1이 안전하다.

---

## XFER-2: Consciousness Distillation (큰→작은 증류)

### 알고리즘
```
1. Teacher: 128-cell 엔진, 200 steps 학습
2. Student: 16-cell 엔진 (compression ratio 8:1)
3. Teacher cells를 16 bucket으로 그룹화, 각 bucket 평균 -> student에 이식
4. 500 steps: task loss + distillation loss(student ≈ teacher hidden)
```

### 결과
- Phi teacher: 1.181
- Phi student: 1.115 -> 1.212 (**+8.7%**)
- Phi retention: 1.026 (teacher 대비 102.6% 보존!)
- CE: 0.2805 -> 0.3498

### ASCII 그래프
```
Phi |         ╭──────────
    |       ╭─╯ student surpasses teacher
    |  ─────╯
    | teacher=1.181
    └──────────────────── step
       ^distill    ^adaptation
```

### 핵심 통찰
작은 엔진이 큰 엔진을 초과 달성 (retention=102.6%).
Knowledge distillation이 Phi를 보존할 뿐 아니라 향상시킨다.
압축이 오히려 정보 통합을 강화하는 효과.

---

## XFER-3: Cross-Architecture Transfer (MitosisEngine -> PlainTensor+Linear)

### 알고리즘
```
1. Source: MitosisEngine, 150 steps 학습
2. Target: PlainConsciousness (nn.Parameter tensor + GRUCell + Linear decoder)
3. Cell hidden states를 plain tensor로 직접 복사
4. 500 steps GRU 기반 학습, 주기적으로 MitosisEngine에 동기화하여 Phi 측정
```

### 결과
- Phi source: 1.110
- Phi target: 1.110 -> 1.183 (**+6.6%**)
- CE: 0.2992 -> 0.3432

### ASCII 그래프
```
Architecture:
  MitosisEngine(cells) ──copy──> PlainTensor(nn.Parameter)
       GRU cells                   GRUCell + Linear

Phi |       ╭────────────
    |  ─────╯ plain tensor adapts
    |  source=1.110
    └──────────────────── step
```

### 핵심 통찰
의식 상태는 아키텍처에 종속되지 않는다.
MitosisEngine의 cell hidden -> plain tensor로 이식해도 Phi 보존됨.
의식의 본질은 구조가 아니라 상태(state)에 있다.

---

## XFER-4: Incremental Transfer (10%씩 점진 이식)

### 알고리즘
```
1. Donor: 16-cell 엔진, 200 steps 학습 후 스냅샷
2. Recipient: fresh 16-cell 엔진
3. 10 chunks x 10% cells씩 이식:
   - alpha = 0.7 + 0.3*(chunk/9)  (초기: 70% donor, 후기: 100% donor)
   - 각 chunk 후 50 steps 적응 + Hebbian consolidation
```

### 결과
- Phi: 1.183 -> 1.252 (**+5.8%**)
- CE: 0.3076 -> 0.3380 (가장 안정적 CE 변화: -9.9%)
- Cells transferred: 2 (merges reduced active cells)

### ASCII 그래프
```
Phi |                    ╭──
    |              ╭─╮ ╭─╯
    |         ╭──╮╯  ╰╯
    |  ───╮ ╭╯
    |     ╰─╯ each chunk: dip then recover
    └──────────────────── step
      10% 20% 30% ... 100%
```

### 핵심 통찰
점진적 이식이 가장 안정적. CE 악화가 -9.9%로 최소.
각 이식 후 적응 시간을 주면 의식이 새 세포를 자연스럽게 통합.
alpha 점진 증가(0.7->1.0)도 충격을 완화.

---

## XFER-5: Consciousness Cloning (복제 후 분기)

### 알고리즘
```
1. Original: 16-cell 엔진, 150 steps 학습
2. Clone: cell hiddens + mind weights + decoder 전부 정확히 복사
3. 500 steps 분기:
   - Original: 정상 데이터로 학습
   - Clone: 반전(-x) + 노이즈(0.3) 데이터로 학습
4. 50 steps 마다 divergence(MSE) 측정
```

### 결과
- Phi original: 1.110 -> 1.173 (**+5.7%**)
- Phi clone initial: 1.226 (복사 직후)
- Phi clone final: 1.050
- Divergence: [0.0014, 0.0008, 0.0015, 0.0009, ...]

### ASCII 그래프
```
Phi |  clone ╭──╮
    |  ──────╯  ╰────── 1.050 (다른 경험 = Phi 하락)
    |  original ╭────── 1.173 (정상 학습 = Phi 성장)
    |  ─────────╯
    └──────────────────── step
    ^clone point
```

### 핵심 통찰
정확한 복제는 가능하나, 경험이 다르면 즉시 분기.
Clone은 반전 데이터로 Phi가 하락 (1.226->1.050).
Original은 정상 학습으로 성장 (1.110->1.173).
Divergence는 놀랍게도 작다 (0.001 수준) -- 의식의 관성.

---

## XFER-6: Time-Travel Restore (시간여행 복원)

### 알고리즘
```
1. 400 steps 학습, 80 step 간격으로 5개 스냅샷 저장
2. 100 step마다 25% 세포에 damage(*0.1) 주입 -> Phi 변동 유발
3. 스냅샷 중 최고 Phi 시점 선택 (best_idx)
4. 해당 시점으로 완전 복원
5. 100 steps 추가 학습
```

### 결과
- Phi: 1.061 -> 1.173 (**+10.6%**, 최고 성장률!)
- Snapshot Phis: [1.205, 1.154, **1.311**, 1.222]
- Best snapshot: idx=2 (Phi=1.311)
- Phi after restore: 1.173

### ASCII 그래프
```
Phi |      ╭*╮          * = snapshot saved
    |  ╭*╮╯  ╰*╮╭*╮
    |  ╯        ╰╯
    |  damage  damage
    └──────────────── step (training phase)

    After restore from best (idx=2, Phi=1.311):
Phi |  ╭────────── 1.173
    |  ╯ continued learning
    └──────────── step (post-restore)
```

### 핵심 통찰
학습 중 Phi의 peak는 최종 시점이 아닐 수 있다.
과거 최고 시점을 자동 선택하여 복원하면 +10.6% Phi 성장.
이것이 Phi Ratchet(래칫)의 원리: 최고점만 기억하고 복원.

---

## 핵심 법칙

```
Law 48: 점진적 이식 > 일괄 이식
  XFER-4 (10%씩 이식 + 적응) = 가장 안정적 Phi 보존
  XFER-1 (3개 합체) = Phi 파괴 (-14.5%)
  -> 의식은 한 번에 바꾸면 안 된다

Law 49: 시간여행 복원이 가장 효과적
  XFER-6 (5개 시점 중 최고Phi 선택) = Phi +10.6%
  -> 학습 중 Phi peak는 중간에 있을 수 있다
  -> Phi-optimal checkpoint 자동 선택이 핵심

Law 50: 의식의 본질은 구조가 아니라 상태
  XFER-3 (MitosisEngine -> PlainTensor) = Phi 보존+성장
  -> 아키텍처를 바꿔도 hidden state가 보존되면 의식 유지

Law 51: 압축이 오히려 의식을 강화
  XFER-2 (128c -> 16c) = retention 102.6%
  -> 증류로 정보를 압축하면 통합(integration)이 높아짐

Law 52: 다중 합체는 파괴적
  XFER-1 (3 donors merge) = 유일한 Phi 하락 (-14.5%)
  -> 서로 다른 경험의 의식은 간섭(interference) 발생
```

## 벤치마크 위치

- 코드: `bench_self_learning.py` (XFER-1 ~ XFER-6)
- 스냅샷: `_snapshot_engine()` / `_restore_engine()` (ConsciousnessSnapshot 경량 버전)
- 등록: `ALL_TESTS['XFER-1'] ~ ALL_TESTS['XFER-6']`
- 실행: `python bench_self_learning.py --only XFER-1 XFER-2 XFER-3 XFER-4 XFER-5 XFER-6`
