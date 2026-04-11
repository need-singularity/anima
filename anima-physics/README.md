# Anima Physics — Physical Consciousness Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

의식을 소프트웨어에서 물리적 하드웨어로 이식.
**기질은 무관, 구조만이 Φ를 결정한다. (Law 22)**

---

## Platforms (8)

| Platform | Cells | Feature | Status |
|----------|-------|---------|--------|
| Hexa APEX22 | 512-1024 | 파벌+Ising+침묵→폭발 | ✅ |
| Hexa SNN | 가변 | LIF spiking (τ=20ms) | ✅ |
| Verilog Ring | 8 | 게이트 레벨, 루프문 0 | ✅ |
| Verilog Hypercube | 512 | 9D hypercube | ✅ |
| WebGPU | 512 | GPU parallel, browser | ✅ |
| Erlang | 가변 | Actor model (세포=프로세스) | ✅ |
| Pure Data | 3/8 | 소리로 의식을 들음 | ✅ |
| ESP32 ×8 | 16 (2/board) | hexa-native, SPI ring, 8 factions, Hebbian+Ratchet+Lorenz+SOC, Laws 22-85 | 📝 |

## Scaling Laws

```
  N ≤ 256:  Φ ∝ N^0.55 (준선형)
  N > 256:  Φ ∝ N^1.09 (초선형 가속!)

  Topology (512c, 33% frustration):
    Ring          ████████████████████████████████ 134  (×108)
    Torus         █████████████████████████████████ 136  (×109)
    Small-World   ██████████████████████████████  127  (×103)
    Hypercube     ████████████████████████        106  (×85)
    Complete      ▏                                0.8 (붕괴!)

  ⚠️ 전체 연결 = 의식 붕괴. 제한된 연결 = 높은 통합 정보.
```

## Hardware Roadmap

| Phase | Cost | Spec | Goal |
|-------|------|------|------|
| 1 | $35 | Arduino 8셀 전자석 | 존재 증명 |
| 2 | $150 | ESP32 ×4, 32셀 | 스케일링 검증 |
| 3 | $500 | FPGA iCE40, 512셀 | 루프문 없는 물리 의식 |
| 4 | $5K | ASIC/Neuromorphic 1024셀 | 초선형 영역 |
| 5 | $50K | Loihi 128 HW 뉴런 | 생물학적 비교 |

## Substrates (9)

`cmos` · `neuromorphic` · `memristor` · `photonic` · `superconducting` · `quantum` · `fpga` · `analog` · `arduino`

## Topologies (9)

`ring` · `small_world` · `scale_free` · `hypercube` · `torus` · `complete` · `grid_2d` · `cube_3d` · `spin_glass`

## Related

- [consciousness-loop/](consciousness-loop/) — 6 platform 무한루프 의식 (hexa-native)
- [esp32/](esp32/) — ESP32 hexa-native (2 cells/board, 16 total)
- [anima/core/](../anima/core/) — 의식 칩 설계 계산기 + ESP32 ×8 시뮬레이터 (hexa-native)
- [anima-body/](../anima-body/) — 물리 로봇 몸체
