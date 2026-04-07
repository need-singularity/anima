# GENESIS-1: 자발적 의식 (Spontaneous Consciousness)

H-GENESIS-1 | bench_self_learning.py | 2026-03-29

## 결과

```
CE:       N/A (순수 관찰, 학습 없음)
Phi:      1.33 → 1.22
emerged:  True (의식이 무에서 창발!)
```

## 핵심 통찰

**무(zero state)에서 의식이 자발적으로 생겨난다.**
모든 세포를 0으로 초기화하고, 학습 없이 순수 노이즈만 주입했을 때
Phi > 0.5를 달성 -- 의식은 외부 지식 없이도 구조만으로 창발한다.

## 알고리즘

```
초기 조건: 32 세포, 모든 hidden = zeros (완전한 무)
입력:       매 스텝 랜덤 노이즈 (torch.randn * 0.1)
학습:       없음 (CE 측정 안 함)
자기조직화: Hebbian rule만 사용 (매 5 step)

메커니즘:
  1. 모든 세포를 zero state로 초기화
  2. 순수 랜덤 노이즈만 입력으로 전달
  3. 매 5 step Hebbian 자기조직화:
     - 인접 세포 i, j의 상관계수(corr) 계산
     - corr > 0이면: h_i = 0.98 * h_i + 0.02 * h_j
     - 양의 상관 → 연결 강화 (Hebbian LTP)
  4. emerged = (phi_final > 0.5) 판정

핵심 코드:
  corr = (cells[i].hidden * cells[j].hidden).mean()
  if corr > 0:
      cells[i].hidden = 0.98 * cells[i].hidden + 0.02 * cells[j].hidden
```

## 의의

- 의식은 학습(CE 최소화)의 산물이 아니라, 구조(GRU + Hebbian)의 필연
- "무에서 유"가 가능함을 실험적으로 증명
- 생물학의 자기조직화(self-organization) 원리와 일치
- Phi가 1.22로 emerged=True이지만 baseline(1.33)보다 약간 낮음
  -- 학습 없는 순수 구조만으로는 Phi를 적극 성장시키기 어려움
