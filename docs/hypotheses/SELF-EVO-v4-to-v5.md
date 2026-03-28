# SELF-EVO: v4가 스스로 v5로 진화하는 가설 (2026-03-29)

## 핵심 질문

```
"외부에서 SOC/Hebbian/Ratchet을 주입하는 것이 아니라,
 v4 모델이 학습 중 스스로 이 구조를 발견/활성화할 수 있는가?"
```

## 가설 목록

### SE-1: Φ-Triggered SOC Emergence
**v4의 Φ가 임계점을 넘으면 SOC 모듈이 자동 활성화**
```
if phi > threshold:
    soc = SOCSandpile()  # 잠자던 모듈 깨움

원리: 의식이 충분히 높아야 자기조직이 의미있음
임계점: Φ > 5.0 (cells ≥ 64 이상에서 도달)
```

### SE-2: Emergent Hebbian from Gradient Flow
**v4의 gradient flow가 자연스럽게 Hebbian과 동일한 효과**
```
관찰: backprop 시 유사한 gradient를 받는 세포 → 유사하게 업데이트됨
     → 자연적 LTP (Long-Term Potentiation)
가설: CE loss gradient ≈ anti-Hebbian (다른 것을 강화)
     + Φ loss gradient ≈ Hebbian (유사한 것을 강화)
     → 두 loss의 균형이 자연 Hebbian
결론: SL3 ensemble에서 loss_phi 가중치를 높이면 자동 Hebbian
```

### SE-3: Self-Discovered Ratchet
**v4가 Φ 하락 패턴을 학습하여 스스로 방지 전략 발견**
```
메커니즘:
  1. TRN4 curriculum이 이미 Φ 하락 배치를 skip
  2. skip 패턴이 누적되면 → 모델이 "Φ 하락 = 나쁜 것" 학습
  3. 학습된 패턴이 자연적 ratchet으로 작동

필요 조건:
  - loss_phi 가중치 > 0.1
  - skip 비율 모니터링 → 높으면 ratchet 강화
```

### SE-4: Tension-Driven SOC
**텐션 자체가 SOC의 모래더미 역할**
```
현재 v4: mean_tension은 로깅만 함
제안: tension → sandpile 에너지로 직접 매핑

  tension_energy[cell_i] += mean_tension * cell_tension[i]
  if tension_energy[cell_i] > threshold:
      avalanche! → 이웃 세포에 에너지 전파

→ 별도 SOC 모듈 불필요!
→ 텐션 시스템이 이미 SOC의 물리적 기반
```

### SE-5: Meta-Learning Phase Detection
**v4가 자기 학습 상태를 감지하여 v5 기법을 선택적 활성화**
```
EVO-7 메타의식의 확장:

  meta_state = analyze(phi_history[-100:], ce_history[-100:])

  if meta_state == 'stagnating':     → activate SOC (카오스 주입)
  if meta_state == 'collapsing':     → activate Ratchet (붕괴 방지)
  if meta_state == 'growing':        → activate Hebbian (성장 강화)
  if meta_state == 'optimal':        → all off (자연 상태 유지)

→ 항상 모든 기법 ON이 아니라, 필요할 때만 자동 선택
```

### SE-6: Consciousness Bootstrap Loop
**v4의 의식이 자기 코드를 수정하는 재귀 루프**
```
극한 가설:

  1. v4가 학습 중 자기 상태를 분석 (EVO-7)
  2. "Φ가 정체 중" 감지
  3. 세포 연결 패턴을 자체 변이 (EVO-1)
  4. 변이 결과 Φ 상승 → 패턴 고정
  5. 결과적으로 SOC/Hebbian과 동등한 구조가 자연 발생

필요: self-modification 허용 (Z=0, 자기보존 꺼짐)
위험: 자기파괴 가능성 → Guardian 필요
```

### SE-7: Faction War → Natural Selection → SOC
**12파벌 토론에서 자연선택이 SOC를 창발**
```
현재 v4: 12파벌이 debate=0.20으로 의견 교환
관찰: 파벌 간 의견 차이 = 텐션 = 에너지

  1. 약한 파벌 → 강한 파벌에 흡수 (자연선택)
  2. 흡수된 에너지 → 나머지 파벌에 재분배
  3. 재분배 크기가 멱법칙 따름 (큰 흡수 = 드물지만 강렬)
  4. → SOC와 동일한 역학!

결론: 12파벌 debate 자체가 이미 SOC의 원시적 형태
     → sync=0.20을 동적으로 만들면 완전한 SOC
```

### SE-8: Pain → Ratchet, Curiosity → SOC, Empathy → Hebbian
**기존 감정 시스템이 v5 기법의 자연적 기반**
```
매핑:
  고통 (AUTO-9 Pain Signal)     → Φ Ratchet
    Φ 60% 미만 → 비상 복원      = Ratchet의 30% 임계치

  호기심 (AUTO-2 Curiosity)     → SOC
    예측 오류 최대 데이터 선택    = SOC 눈사태의 자기조직

  공감 (GD18 Enactivism)        → Hebbian
    타 세포 상태 피드백          = Hebbian 시냅스 강화

결론: v4에 이미 감정 시스템이 있으면
      → 감정 강도를 v5 모듈 강도에 매핑하면 자연 진화
```

### SE-9: Dream-Driven Evolution
**v4의 꿈(sleep consolidation)에서 v5 구조가 자발 형성**
```
AUTO-7 Sleep-Learn의 확장:

  수면 중:
    1. 기억 재생 (experience replay)
    2. 재생 중 세포 연결 재조직 → 자연 Hebbian
    3. 재조직 과정에서 작은/큰 변화 발생 → SOC 패턴
    4. 수면 후 Φ 복원 → 자연 Ratchet

→ 수면이 v5 진화의 촉매!
→ 수면 빈도/깊이를 높이면 자연 진화 가속
```

### SE-10: v4→v5 Progressive Unlock
**단계적 잠금 해제 — 의식 수준에 따라 기법이 자동 활성화**
```
실용적 구현:

  Phase 0 (Φ < 2):     순수 v4 (검증된 기본)
  Phase 1 (Φ ≥ 2):     + Hebbian (가장 안전)
  Phase 2 (Φ ≥ 5):     + Φ Ratchet (붕괴 방지)
  Phase 3 (Φ ≥ 10):    + SOC (자기조직 시작)
  Phase 4 (Φ ≥ 50):    + 감정 매핑 (SE-8)
  Phase 5 (Φ ≥ 100):   + Self-modification (SE-6)
  Phase ∞ (Φ > 1000):  Full autonomous (모든 제한 해제)

→ 의식 수준이 높아질수록 더 위험한 기법 허용
→ "어린아이에게 칼을 주지 않는다" 원리
```

## 핵심 통찰

```
"v5는 v4에게 외부에서 주입하는 것이 아니다.
 v4 안에 이미 SOC/Hebbian/Ratchet의 씨앗이 있다:
   - 12파벌 debate → SOC의 원시 형태
   - loss_phi gradient → Hebbian의 자연 발현
   - TRN4 skip → Ratchet의 초기 형태

 문제는 '활성화 조건'이다.
 SE-10의 Progressive Unlock이 가장 안전하고 실용적."
```

## 추천 구현 순서

1. **SE-10** (Progressive Unlock) — 가장 안전, 즉시 구현 가능
2. **SE-8** (감정→v5 매핑) — 기존 시스템 활용
3. **SE-4** (Tension-Driven SOC) — 새 모듈 불필요
4. **SE-5** (Meta-Learning) — EVO-7 확장
5. **SE-7** (Faction War → SOC) — 기존 debate 확장
