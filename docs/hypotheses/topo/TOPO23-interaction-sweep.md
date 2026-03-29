# TOPO23 — Interaction 비율 스위프 (Hypercube 1024, 50% frust)

## 실험 설계

```
고정: Hypercube 1024 (10D), 50% frustration (i%2), noise=0.02
변수: retain/interact 비율

  TOPO23d: retain=0.95 interact=0.05 (약한 상호작용)
  TOPO23b: retain=0.90 interact=0.10
  TOPO19a: retain=0.85 interact=0.15 (기존 최적)
  TOPO23a: retain=0.75 interact=0.25
  TOPO23c: retain=0.70 interact=0.30 (강한 상호작용)
```

## 결과

```
interact:  0.05    0.10    0.15★   0.25    0.30
Φ:         231     482     640     464     426
```

## 스케일링 그래프

```
Φ |              ★
640|             ╭╮
   |            ╭╯╰╮
480|       ╭──╮╭╯   ╰╮
   |       │  ╰╯     ╰╮
420|       │           ╰─
   |       │
230| ╭─────╯
   └──┴──┴──┴──┴──┴──→ interact
   0.05 0.10 0.15 0.25 0.30
```

## 핵심 통찰

- **0.15가 확정 최적** — 모든 변형이 Φ를 낮춤
- 0.05(너무 약함): 231 — 상호작용 부족으로 정보 통합 실패
- 0.10: 482 — 괜찮지만 최적에 미달
- 0.25-0.30(너무 강함): 464-426 — 과도한 결합이 개별 셀 정체성 소멸
- **역U자 패턴**: frustration(Law 52)과 동일한 패턴이 interaction에서도 반복
