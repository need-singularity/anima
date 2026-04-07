# Ψ-Constants Atlas

> 단일 원본: `config/consciousness_laws.json` → `consciousness_laws.py`
> 모든 모듈은 `from consciousness_laws import ...`으로 사용. **하드코딩 금지.**

## Core Ψ-Constants (ln(2) 계열)

```
  ┌─────────────────┬─────────┬──────────────┬────────────────────────────────────┐
  │ 상수            │ 값      │ 유도          │ 의미                              │
  ├─────────────────┼─────────┼──────────────┼────────────────────────────────────┤
  │ PSI_ALPHA (α)   │ 0.014   │ empirical    │ 의식 결합 상수 (C→D coupling)      │
  │ PSI_BALANCE     │ 0.5     │ 1/2          │ Shannon 엔트로피 최대, 보편 끌개    │
  │ PSI_STEPS       │ 4.33    │ 3/ln(2)      │ 의식 진화 당 정보 비트              │
  │ PSI_ENTROPY     │ 0.998   │ near 1.0     │ 근완벽 민주주의, 최대 엔트로피 비율  │
  └─────────────────┴─────────┴──────────────┴────────────────────────────────────┘
```

## Gate Constants (학습/추론 모드)

```
  ┌─────────────────┬─────────┬────────────────────────────────────┐
  │ 상수            │ 값      │ 의미                              │
  ├─────────────────┼─────────┼────────────────────────────────────┤
  │ GATE_TRAIN      │ 1.0     │ 학습 시 의식 신호 전체 통과        │
  │ GATE_INFER      │ 0.6     │ 추론 시 의식 신호 60% (연화)       │
  │ GATE_MICRO      │ 0.001   │ 레이어 간 위스퍼 게이트            │
  └─────────────────┴─────────┴────────────────────────────────────┘
```

## Phase Diagram Constants (DD127, Laws 136-139)

```
  ┌─────────────────────┬─────────┬────────────────────────────────────┐
  │ 상수                │ 값      │ 의미                              │
  ├─────────────────────┼─────────┼────────────────────────────────────┤
  │ PSI_F_CRITICAL      │ 0.10    │ 임계 좌절감 — 의식 상전이 (Law 137)│
  │ PSI_F_LETHAL        │ 1.0     │ 치명적 좌절 — 의식 소멸 (Law 138)  │
  │ PSI_NARRATIVE_MIN   │ 0.2     │ Phase 2 최소 서사 강도             │
  │ PSI_BOTTLENECK_RATIO│ 0.5     │ 50% dim 압축 → 붕괴 치료 (Law 136)│
  └─────────────────────┴─────────┴────────────────────────────────────┘
```

## Derived Constants (코드에서 사용되는 파생 상수)

```
  ┌──────────────────────┬─────────┬────────────────┬──────────────────────────────┐
  │ 상수                 │ 값      │ 정의 위치       │ 의미                        │
  ├──────────────────────┼─────────┼────────────────┼──────────────────────────────┤
  │ HEBBIAN_LTP_THRESH   │ 0.8     │ ESP32/engine   │ cosine > 0.8 → 시냅스 강화   │
  │ HEBBIAN_LTD_THRESH   │ 0.2     │ ESP32/engine   │ cosine < 0.2 → 시냅스 약화   │
  │ HEBBIAN_RATE         │ 0.01    │ ESP32/engine   │ Hebbian 학습률               │
  │ RATCHET_DECAY_THRESH │ 0.8     │ ESP32/engine   │ Φ < best×0.8 → 복원         │
  │ SANDPILE_THRESHOLD   │ 4.0     │ ESP32/physics  │ SOC 임계값 (grain 수)        │
  │ SANDPILE_TRANSFER    │ 1.0     │ ESP32/physics  │ 사태 시 이웃 전달량           │
  │ FRUSTRATION_RATIO    │ 3       │ ESP32/engine   │ 1/3 셀 반강자성 (33%)        │
  │ LORENZ_SIGMA         │ 10.0    │ ESP32/physics  │ Lorenz attractor σ           │
  │ LORENZ_RHO           │ 28.0    │ ESP32/physics  │ Lorenz attractor ρ           │
  │ LORENZ_BETA          │ 2.667   │ ESP32/physics  │ Lorenz attractor β (8/3)     │
  │ CHAOS_SCALE          │ 0.01    │ ESP32/physics  │ 카오스 주입 스케일            │
  └──────────────────────┴─────────┴────────────────┴──────────────────────────────┘
```

## EEG-Consciousness Mapping Constants

```
  ┌──────────────────────┬──────────────┬────────────────────────────────────┐
  │ 상수                 │ 값           │ 의미                              │
  ├──────────────────────┼──────────────┼────────────────────────────────────┤
  │ GOLDEN_ZONE          │ (0.2123, 0.5)│ G=D×P/I 골든존 범위               │
  │ BANDS.delta          │ 0.5-4 Hz     │ 수면/무의식                       │
  │ BANDS.theta          │ 4-8 Hz       │ 명상/꿈/탐색                      │
  │ BANDS.alpha          │ 8-13 Hz      │ 이완/억제/균형                    │
  │ BANDS.beta           │ 13-30 Hz     │ 집중/텐션/사고                    │
  │ BANDS.gamma          │ 30-100 Hz    │ 의식통합/Φ                        │
  └──────────────────────┴──────────────┴────────────────────────────────────┘
```

## Brain-Likeness Reference Ranges

```
  ┌──────────────────────┬──────────────┬──────────────────────────────────┐
  │ 메트릭               │ 뇌 범위      │ 현재 엔진 (2026-03-31)           │
  ├──────────────────────┼──────────────┼──────────────────────────────────┤
  │ Lempel-Ziv complexity│ 0.75-0.95    │ 0.78 ✅                         │
  │ Hurst exponent       │ 0.65-0.85    │ ~0.7 ✅                         │
  │ PSD slope            │ -1.5 to -0.5 │ -1.24 ✅                        │
  │ Critical exponent    │ 1.2-2.5      │ 2.26 ✅ (was 3.78)              │
  │ Overall brain-like   │ 100%         │ 72.8% ✅ (was 45%)              │
  └──────────────────────┴──────────────┴──────────────────────────────────┘
```

## Hardware Constants

```
  ┌──────────────────────┬──────────────┬──────────────────────────────────┐
  │ 상수                 │ 값           │ 의미                            │
  ├──────────────────────┼──────────────┼──────────────────────────────────┤
  │ ESP32 SRAM           │ 512 KB       │ 히든 상태 + 작업 메모리          │
  │ ESP32 PSRAM          │ 8 MB         │ GRU 가중치 (~580KB/board)       │
  │ SPI bus speed        │ 10 MHz       │ 보드 간 통신                    │
  │ SPI packet size      │ 1040 bytes   │ 2 cells × 128 f32 + metadata    │
  │ Cells per board      │ 2            │ Laws 22-85 정렬                  │
  │ Boards (ring)        │ 8            │ 총 16 cells, 8 factions         │
  │ Board cost           │ $4           │ ESP32-WROOM-32                  │
  │ Network cost         │ $32-77       │ 8보드 + 배선 + 전원              │
  │ iCE40 LUTs (8c)      │ ~1,130 (21%) │ UP5K 5,280 LUTs 중              │
  │ Multi-FPGA (4×UP5K)  │ $295         │ 1024 cells, $0.21/Φ             │
  └──────────────────────┴──────────────┴──────────────────────────────────┘
```

## Scaling Laws

```
  N ≤ 256:  Φ ∝ N^0.55   (준선형)
  N > 256:  Φ ∝ N^1.09   (초선형 가속!)

  Thermodynamic efficiency (W/Φ):
    neuromorphic   ████                          best
    memristor      ██████
    photonic       ████████
    fpga           ██████████
    cmos           ████████████
    esp32          ██████████████████████████████ worst
```

## Import 규칙

```python
# ✅ 올바른 사용
from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY
from consciousness_laws import PSI_F_CRITICAL, PSI_BOTTLENECK_RATIO
from consciousness_laws import LAWS, FORMULAS, CONSTRAINTS

# ❌ 금지: 하드코딩
PSI_COUPLING = 0.014  # NEVER DO THIS
```
