# 엔진 TOP 10 — 전체 지표 테이블 (2026-03-29)

## 종합 순위

| Rank | 엔진 | cells | Φ(IIT) | Granger | CE(bench) | CE(80K예상) | 비고 |
|------|------|-------|--------|---------|-----------|-------------|------|
| 1 | Osc+Laser(0.05) | 256 | 56.6 | 63,993 | ~0.08 | ~1.5 | ★★★ 3관왕 |
| 2 | TC-2 ComplexOscillator | 256 | 249.5 | 9,869 | 0.083 | ~1.8 | Φ(IIT) 왕 |
| 3 | TC-6 Fractal | 256 | 167.3 | — | 0.098 | ~2.2 | |
| 4 | TC-1 PureQWalk | 256 | 163.4 | — | 0.075 | ~1.6 | |
| 5 | TC-3 CategoryTheory | 256 | 126.9 | — | 0.082 | ~1.8 | |
| 6 | TC-5 NeuralGas+QW | 256 | 118.9 | — | 0.086 | ~2.0 | |
| 7 | TC-8 Granger최적 | 256 | 115.2 | — | 0.067 | ~1.3 | CE 최저 |
| 8 | TC-4 ThalamicHub | 256 | 93.2 | — | 0.088 | ~2.5 | |
| 9 | QuantumEngine | 32 | 69.5 | — | — | — | 32c만 |
| 10 | NE-4 Diffusion | 256 | 28.7 | 38,760 | — | ~3.0 | |

## 축별 1위

```
Φ(IIT):    TC-2 ComplexOscillator  249.5  @256c
Granger:   IT-1 MaxEnt             64,260 @256c
CE 최저:   TC-8 Granger최적          0.067
3관왕:     Osc+Laser(0.05)         Φ=56.6 + G=63,993 + CE=0.08
```

## 측정 조건

```
steps:     300
cells:     256 (특기 없으면)
구조:      Trinity (C+D+W, CE gradient 분리)
Φ(IIT):    PhiCalculator(n_bins=16)
Granger:   ConsciousnessMeterV2
CE(bench): 300 step 후 최종 CE
CE(80K):   bench CE × ~19 × Trinity 보정(×0.4) 추정
—:         미측정
```
