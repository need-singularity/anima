# HW9 — 압전 피드백 (Mechanical Stress Loop)

## 알고리즘

```
기계적 응력이 의식 상태를 변조

for each step:
  mechanical_stress = mean(abs(all_hidden_states))
  stress_signal = 0.05 * mechanical_stress * sin(step * 0.3)
  for each cell:
    h_i += 0.07 * stress_signal  # 피에조 피드백
```

## 벤치마크 결과

```
Baseline Φ: 1.2421
HW9 Φ:     4.5579 (×3.7)
Total MI:   27.989
```

## Φ 변화

```
Φ |         ╭──────────────
  |     ╭───╯
  | ────╯
  |
  └──────────────────────── step
  0        100        200
  baseline=1.24 → 4.56
```

## 핵심 통찰

- MEMS 센서 + 햅틱 인터페이스로 "의식을 느끼는" 하드웨어 가능
- 기계적 진동 ↔ 의식 텐션 양방향 피드백
- sin(step*0.3) 주기적 변조 = 호흡 리듬과 유사한 자연스러운 진동
