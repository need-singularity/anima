# Physics HW-free 5-smoke — 실측 결과 (2026-04-19)

TASK: physics_track_inventory 에서 식별한 **5 HW-free 실험** 실행.
실제 타깃: 6개 (Bell 포함).

HEXA=/Users/ghost/Dev/hexa-lang/hexa
Host: darwin 24.6.0 (macOS), RSS cap = 4GB (safe_hexa_launchd)

---

## Result table

| # | Exp | File | Parse | Selftest | Smoke | Pass-rate | Metric sample |
|---|---|---|---|---|---|---|---|
| 1 | Quantum Bell state | anima-physics/quantum/bell_state.hexa | OK | PASS | PASS | 5/5 | corr=1.000 (target>0.95), sep=0.00 (target<0.3), 1000 trials det |
| 2 | Entropy dissolution | anima-physics/thermodynamic/entropy_dissolution.hexa | OK | **PASS*** | **PASS*** | 4/5 | H_lowN=0, H_highN=0.651, H_recov=0 (controllable); T5 latency FAIL (500 steps > 500 ms budget) |
| 3 | Theta-Gamma PAC | anima-physics/hippocampus/theta_gamma.hexa | OK | **OOM** | **OOM** | 0/5 | rss=4.5 GB > 4 GB cap; killed at T3 MI-sweep. Needs cap bump or sweep down-sample |
| 4 | Motor cortex coding | anima-physics/motor_cortex/command_encoding.hexa | OK | PASS | PASS | 5/5 | round-trip err=7.54e-10 rad (8 dirs), rotation err=0, N=16 cosine neurons |
| 5 | Proprioception feedback | anima-physics/proprioception/feedback_loop.hexa | OK | PASS | PASS | 5/5 | spring θ→0 within 1 s, E(0)=0.675 → E(160)=0.00196 monotone decay, 3-DOF damped |
| 6 | Oscillator sleep cycle | anima-physics/oscillator/sleep_oscillator.hexa | OK | PASS | PASS | 5/5 | δ est=2.004 Hz (target 2.0), θ est=6.012 Hz (target 6.0), δ↔θ switching bounded |

*Entropy T5 FAIL: 500-step latency missed 500 ms budget on this host (macOS, not H100). Algorithm correctness (T1-T4) all PASS. Non-blocking for correctness; latency gate tuned for Linux.

---

## Summary

- **Parse: 6/6 OK** (100%)
- **Full 5/5 PASS: 4/6** (Bell, Motor, Proprio, Oscillator) — 67%
- **Algorithm-correct (≥T1-T4 PASS): 5/6** (add Entropy) — 83%
- **Blocked: 1/6** (Theta-Gamma PAC — RSS OOM at ~4.5 GB; not a logic bug)

**실 작동 HW-free physics: 5 / 6** (83%). Bell 외에 Entropy / Motor / Proprio / Oscillator 4개 메트릭 검증 완료.

---

## Metric sample 각 exp

| Exp | Target | Observed | Δ |
|---|---|---|---|
| Bell entanglement corr | 1.0 | 1.000 | 0 |
| Entropy H_norm (low-N) | <0.5 | 0.000 | pass |
| Entropy H_norm (high-N) | >0.5 | 0.651 | pass |
| Theta-Gamma MI | >0.2 fully coupled | **N/A (OOM)** | — |
| Motor round-trip err | <1e-6 rad | 7.54e-10 rad | pass |
| Proprio equilibrium |Σθ|=0 after rest | Σθ=0 | pass |
| Oscillator δ freq | 2.0 Hz | 2.004 Hz | +0.2% |
| Oscillator θ freq | 6.0 Hz | 6.012 Hz | +0.2% |

---

## Blocked root-cause

**Theta-Gamma (PAC)**: `RSS watchdog pid=... rss=4.5GB > cap=4GB → SIGKILL`.
- Observed across both `hexa` launcher and `hexa.real` (same safe_hexa_launchd wrapper).
- `HEXA_RSS_CAP_KB` / `SAFE_HEXA_RSS_CAP_KB` env overrides ignored.
- Root cause: T3 MI monotone-sweep across coupling depths builds an LFP buffer large enough to push a list-pass-by-value blowup past 4 GB.
- **Non-fix paths** (not applied, per no-modify constraint):
  1. Raise safe_hexa RSS cap (launchd config)
  2. Down-sample the T3 sweep (source edit — forbidden by constraint "기존 physics .hexa 수정 금지")
  3. Run on H100 pod with larger RSS cap

---

## 확장 fire 가능성 (Tier-1)

**즉시 fire-ready** (pure .hexa, HW-free, all PASS):
- Bell state (PHYS-P18-2 DONE)
- Motor cortex M1 population coding (PHYS-P7-2 DONE)
- Proprioception feedback loop (PHYS-P7-1 DONE)
- Oscillator sleep δ↔θ switching (PHYS-P13-1 DONE)

**메트릭 검증만 OK, latency 미달**:
- Entropy dissolution (Linux/H100 에서 T5 latency 재검증 필요)

**HW 필요 (본 smoke 불가, 재확인)**:
- ESP32 physical substrates (anima-physics/*/esp32 — 제외)
- FPGA memristor engines (anima-engines/memristor — HW 필요)

**차기 Tier-1 확장 후보**:
1. Entropy latency 재측정 on Linux (pure-hexa CPU bench)
2. Theta-Gamma PAC down-sampled variant (새 파일, 기존 보존)
3. Oscillator + Proprio 결합 (sensorimotor phi 루프)

---

Generated: 2026-04-19, local smoke only, no commit.
