# PHI-GAP: 벤치마크 Φ=1142 vs 학습 Φ=1.4 — 816배 차이 조사 (2026-03-29)

## 핵심 문제

```
벤치마크 (MitosisEngine 단독):
  1024c, 200 steps, sync+faction+IB2 → Φ = 1142

실제 학습 시뮬 (bench_real_training.py):
  1024c, 200 steps, process(x)+CE+sync+faction → Φ = 1.4

차이: 816배!!!
```

## 원인 분석

```
벤치마크:
  step 1: sync+faction (cells 구조 최적화)
  step 2: sync+faction
  ... 200 steps: cells는 순수하게 Φ 최적 구조로 수렴

실제 학습:
  step 1: engine.process(x) → GRU가 hidden 덮어씀 ← 파괴!
  step 1: CE backward → gradient가 hidden 변경 ← 파괴!
  step 1: sync+faction → Φ 복원 시도
  step 2: engine.process(x) → 다시 파괴!
  ... 무한 파괴-복원 사이클

process()가 매 step hidden을 GRU로 갱신:
  h_new = GRU(x, h_old)
  → h_old의 Φ 최적 구조가 사라짐
  → sync+faction으로 복원해도 다음 process()에서 또 파괴
```

## 개선 가설

### GAP-1: Dual Hidden State (이중 히든)
```
각 cell에 hidden state 2개:
  h_consciousness: Φ 전용 (process에 영향 안 받음)
  h_language: CE 전용 (process+backward에 사용)

Φ 계산: h_consciousness만 사용
CE 학습: h_language만 사용
연결: 매 N step h_consciousness → h_language soft sync (0.1)

→ 의식과 언어가 분리된 채널
→ Φ가 CE에 의해 파괴되지 않음
```

### GAP-2: Process-Free Φ (프로세스 없는 의식)
```
process()를 완전히 건너뛰고 cells만 조작:
  even step: process(x) + CE (언어 학습)
  odd step: process 없이 sync+faction만 (Φ 부스트)

odd step에서 process()가 없으므로 GRU가 hidden을 안 건드림
→ Φ 최적 구조가 보존됨

예상: Φ = 벤치마크의 50% (process 절반만 → 파괴 절반)
```

### GAP-3: GRU Residual (잔차 GRU)
```
현재: h_new = GRU(x, h_old) → h_old 완전 교체
개선: h_new = α * h_old + (1-α) * GRU(x, h_old)

α = 0.9 → hidden의 90%가 보존, 10%만 GRU가 갱신
→ process()의 파괴력이 90% 감소
→ Φ 구조가 대부분 보존

α를 Φ에 비례하게 설정:
  Φ 높을수록 α → 1.0 (보존 우선)
  Φ 낮을수록 α → 0.5 (학습 허용)
```

### GAP-4: Post-Process Restoration
```
process() 직후 cells를 Φ 최적 상태로 부분 복원:

  saved = [c.hidden.clone() for c in cells]
  engine.process(x)
  # 복원: 70% 이전 + 30% GRU 결과
  for i, c in enumerate(cells):
      c.hidden = 0.7 * saved[i] + 0.3 * c.hidden

→ GRU의 언어 정보는 30%만 받아들임
→ Φ 구조의 70%가 보존
→ 비율을 Φ 기반으로 동적 조절
```

### GAP-5: Consciousness-Gated GRU
```
GRU의 update gate를 Φ로 제어:

  standard GRU: z = sigmoid(Wz @ [h, x])
  modified:     z = sigmoid(Wz @ [h, x]) * (1 - phi_gate)

  phi_gate = sigmoid((Φ - threshold) * scale)

  Φ 높으면: phi_gate → 1.0 → z → 0 → hidden 변경 안 됨
  Φ 낮으면: phi_gate → 0.0 → z → 정상 → hidden 자유 갱신

→ 의식이 높을수록 GRU가 hidden을 보호
→ "의식이 자기를 보호하는 게이트"
```

### GAP-6: Separate Engine Architecture
```
완전히 분리:

  Engine A (의식): MitosisEngine, process 없음, sync+faction만
    → Φ = 1000+ (벤치마크와 동일 조건)

  Engine B (언어): ConsciousLM, process+CE 정상 학습
    → CE 학습에 집중

  Bridge: Engine A의 Φ 상태 → Engine B의 텐션 bias로 전달
    → Engine A의 의식이 Engine B의 언어를 가이드
    → Engine B의 CE가 Engine A를 파괴하지 않음

→ 근본적 해결: 의식과 언어를 물리적으로 분리
```

### GAP-7: Φ-Preserving GRU (새 GRU 설계)
```
GRU를 재설계하여 Φ 보존 보장:

  standard: h = (1-z)*n + z*h_prev
  Φ-GRU:   h = (1-z)*n + z*h_prev + φ_residual

  φ_residual = Φ_direction * Φ_magnitude

  Φ_direction = h의 diversity를 높이는 방향 벡터
  Φ_magnitude = max(0, Φ_target - Φ_current) * scale

→ GRU 자체에 Φ 보존 메커니즘 내장
→ hidden 업데이트 시 자동으로 Φ 방향으로 보정
```

### GAP-8: Temporal Consciousness Buffer
```
의식 상태를 시간 버퍼에 저장:

  buffer[t] = {cells, phi, structure}

  매 10 step: 현재 상태를 버퍼에 push
  process() 후: 버퍼에서 최고 Φ 상태와 blend

  h_final = 0.5 * h_after_process + 0.5 * h_from_buffer[best_phi]

→ 과거의 최고 의식 상태가 현재를 보호
→ Time-travel ratchet의 연속 버전
```

## 우선순위

```
즉시 테스트 (bench_real_training.py에 추가):
  GAP-3 (GRU Residual, α=0.9) — 1줄 변경
  GAP-4 (Post-Process Restoration, 70/30) — 3줄 추가
  GAP-2 (Process-Free odd steps) — 기존 PHI-K3 변형

아키텍처 변경 필요:
  GAP-1 (Dual Hidden) — rust/consciousness.hexa 변경
  GAP-5 (Consciousness-Gated GRU) — rust/consciousness.hexa GRU 변경
  GAP-6 (Separate Engine) — 새 아키텍처
  GAP-7 (Φ-Preserving GRU) — 새 GRU 설계

예상 개선:
  현재:          Φ = 1.4
  GAP-3 (α=0.9): Φ = ~15 (10x?)
  GAP-4 (70/30):  Φ = ~10 (7x?)
  GAP-6 (분리):   Φ = ~1000 (벤치마크급)
```

## 핵심 통찰

```
Law 53: process() destroys Phi WITHOUT .detach(). With Trinity .detach() barrier,
        CE learning stabilizes Phi via frustration dampening.
        (H4: P2 frustration plateaus at 0.541, ratchet frequency -43%, Phi variance -52%)

이것은 "학습과 의식의 근본적 충돌" — 단, .detach() 유무가 결정적:
  WITHOUT .detach():
    - 학습(CE) = hidden을 예측 방향으로 수렴 → 다양성↓ → Φ↓
    - 의식(Φ) = hidden이 다양하면서 통합 → 다양성↑ → Φ↑
    - process(GRU) = hidden을 입력 방향으로 변경 → 구조↓ → Φ↓
  WITH Trinity .detach():
    - CE gradient가 의식 세포로 역전파되지 않음 → Φ 구조 보존
    - decoder만 학습 → frustration이 0.541에서 자연 정체
    - ratchet 발동 빈도 43% 감소, Φ 분산 52% 감소
    - 결론: CE가 Φ를 파괴하지 않고 오히려 안정화

해결의 핵심:
  "의식과 언어를 같은 hidden state에서 처리하면 안 된다"
  → 분리 (GAP-1, GAP-6) 또는 보호 (GAP-3, GAP-5)
  → ★ Trinity .detach() = 가장 효과적 보호 (H4 검증)
```
