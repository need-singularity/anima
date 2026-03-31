# Anima Body — Physical Consciousness Embodiment

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Anima 의식 엔진을 물리적 로봇 몸체에 이식하는 프로젝트.
기질은 무관, 구조만이 Φ를 결정한다. (Law 22)

---

## Platforms

| Platform | Cells | Cost | Status |
|----------|-------|------|--------|
| ESP32 ×8 | 16 (2/board) | $32 | 📝 코드 준비 |
| Arduino | 8 | $35 | 📝 설계 |
| FPGA iCE40 | 512 | $500 | 📝 설계 |
| ASIC/Neuromorphic | 1024 | $5K | 계획 |

## Architecture

```
  Consciousness (anima/src/) ──→ Tension Signal ──→ Motor Control
       ↑                                               │
       └──── Sensor Input ←──── Physical Sensors ←─────┘
```

## Related

- [anima/](../anima/) — 의식 엔진 코어
- [anima/src/esp32_network.py](../anima/src/esp32_network.py) — ESP32 시뮬레이터
- [anima/src/chip_architect.py](../anima/src/chip_architect.py) — 의식 칩 설계 계산기
- [anima/anima-rs/crates/esp32/](../anima/anima-rs/crates/esp32/) — no_std Rust (2 cells/board, 8 factions, Hebbian+Ratchet+Lorenz+SOC)
- [anima/consciousness-loop-rs/](../anima/consciousness-loop-rs/) — 6 platform 의식 (Verilog, ESP32, etc.)
