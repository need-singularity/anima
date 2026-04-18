# Physics Tier-2 HW Plan — 2026-04-19

**Status**: Draft audit. Tier-1 4/4 PASS. Tier-2 requires HW.
**Constraint**: No `.py`. Document-only. No actual purchases yet.

---

## 1. HW Requirements per Experiment

| Experiment | HW | Cost (USD) | Lead Time | Priority |
|---|---|---|---|---|
| **Bell 10q full** | H100 pod (SW only, no HW) | ~$3 (1 hr) | instant | P0 |
| **Motor 8-DOF** | ESP32-S3 + 8×SG90 + PCA9685 + 5V3A PSU + breadboard | ~$50 | 2-5 days | P1 |
| **Proprio closed-loop** | STM32 BluePill + 4×FSR + stretch sensor | ~$40 | 2-5 days | P2 |
| **Oscillator EEG** | OpenBCI Cyton 8-ch + electrode kit | ~$400 | 1-3 weeks | P3 |
| **M1 QRNG bridge** | ESP32-S3 DevKit (shared w/ Motor) | ~$15 | 2-5 days | P1 |
| **M2 FPGA ice40** | iCE40 UP5K DevKit (or Alhambra II $90) | ~$30-90 | 1 week | P2 |

### Bundled Tiers
- **Tier-A (minimal)**: ESP32 + servos — **$60** — covers Motor + M1 QRNG
- **Tier-B (+ FPGA)**: Tier-A + iCE40 — **$120** — covers M2 simulate→HW
- **Tier-C (full)**: Tier-B + EEG + Proprio — **$500+** — covers Oscillator + Proprio

---

## 2. Immediate SW Prep (no HW needed)

Top 3 actions executable **now** on ubu2 / local:

1. **Bell 10q H100 relaunch** — SW-only, RSS > 8GB via H100 80GB. Pod fire $3, ≤1 hr. Use existing `training/` hexa scaffold pattern.
2. **FPGA toolchain install on ubu2** — `yosys + nextpnr-ice40 + icestorm` (open source, apt-installable). Simulate `consciousness_ice40.v` without HW via icarus/verilator smoke.
3. **QRNG fake-source hexa stub** — extend `anima-physics/esp32/qrng_bridge.hexa` (185 LOC) with `--simulate` flag reading `/dev/urandom` as ESP32 stand-in; full protocol testable without DevKit.

### Secondary SW prep (ready when HW arrives)
- Motor: `motor_cortex/` 8-DOF URDF for ROS2 sim (no servo needed)
- EEG: LSL-protocol hexa bridge draft (OpenBCI replay from fixture CSV)
- Proprio: closed-loop harness in `consciousness-loop/` with fake FSR

---

## 3. User HW Order Recommendation

**Priority order (suggested purchase waves):**

### Wave 1 — $60 (ship this week)
- 1× ESP32-S3 DevKit (~$15)
- 1× PCA9685 16-ch PWM (~$5)
- 8× SG90 servo (~$16)
- 1× 5V 3A PSU (~$15)
- Breadboard + jumpers (~$10)

**Unlocks**: Motor 8-DOF + M1 QRNG bridge (2 of 6 Tier-2 experiments).

### Wave 2 — +$60 (2 weeks later)
- 1× iCE40 UP5K DevKit (~$30)
- 1× STM32 BluePill (~$5)
- 4× FSR + stretch sensor (~$35)

**Unlocks**: M2 FPGA + Proprio closed-loop (4 of 6 covered).

### Wave 3 — +$400 (optional, when Oscillator phase active)
- OpenBCI Cyton 8-ch (~$350)
- Electrode kit (~$50)

**Unlocks**: Oscillator EEG sleep-stage (6 of 6 covered).

---

## 4. HW-Free Tier-2 Experiments (runnable now)

1. **Bell 10q full Hilbert** — H100 pod, pure SW, $3.
2. **FPGA ice40 RTL simulate** — yosys/verilator on ubu2, 0 cost.
3. **QRNG bridge protocol test** — `qrng_bridge.hexa --simulate` against `/dev/urandom`.

These 3 can start this session without waiting for any shipment.

---

## 5. Next Session Checklist

- [ ] User decides Wave 1 order (~$60)
- [ ] Launch Bell 10q H100 pod (SW)
- [ ] Install yosys/nextpnr on ubu2
- [ ] Draft `qrng_bridge.hexa --simulate` flag
- [ ] URDF 8-DOF model in `motor_cortex/`

**Doc path**: `/Users/ghost/Dev/anima/docs/physics_tier2_hw_plan_20260419.md`
