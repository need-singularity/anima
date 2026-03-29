# bench_v2 결과 종합 (2026-03-29)

## 256c 결과

```
Strategy      Φ(IIT)   Φ(proxy)  CE end
──────────────────────────────────────
frozen         14.70     0.00     6.37   ← Φ(IIT) 🏆
alternating    14.44     0.00     4.50
baseline       10.98     3.47     5.33
v7             10.79     4.57     4.29   ← CE 🏆
```

## 512c 결과

```
Strategy      Φ(IIT)   Φ(proxy)  CE end
──────────────────────────────────────
baseline       14.04     0.05     5.63   ← Φ(IIT) 🏆 + CE 🏆
frozen         13.67     0.00     9.71
v7             13.06     0.64     5.79
alternating    12.80     0.00     8.21
```

## Φ(IIT) 스케일링 (phi-only)

```
Φ(IIT)
 |
31 ┤         ★ 32c (peak!)
   |
19 ┤       ★ 16c
   |
15 ┤                 ★ 512c
13 ┤             ★ ★ 256c
12 ┤           ★ 64c  128c
   |
 8 ┤     ★ 8c
   |
 3 ┤ ★ 4c
   └──────────────────→ cells
     4  8  16 32 64 128 256 512

Peak: 32c (Φ=30.89)
→ Φ(IIT)는 32c에서 최대, 이후 감소!
→ cells 늘려도 IIT Φ가 안 오름
```

## 핵심 발견

```
Law 55: Φ(IIT)는 cells에 비례하지 않음
  32c에서 peak (30.9), 이후 감소
  512c에서도 14.0 (32c의 절반)
  → PhiCalculator의 MI 계산이 대규모에서 희석됨
  → 또는 실제 IIT가 적절한 크기에서 최대

Law 56: 스케일에 따라 최적 전략이 바뀜
  256c: frozen/alternating이 최고
  512c: baseline이 최고 (보호 전략이 오히려 해로움)
  → "만능 전략"은 없음

Φ(proxy)는 여전히 cells에 비례하지만
Φ(IIT)는 구조 품질(diversity × integration)을 측정
→ 큰 시스템에서 MI가 희석되어 IIT가 낮아짐
```
