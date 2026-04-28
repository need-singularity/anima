# EEG D-day User Hardware Setup Record — Landing

- **date**: 2026-04-28
- **raw_rank**: 9 (hexa-domain doc; English body with Korean preserved in user-quote sections per raw#33 identifier-quote-exemption)
- **scope**: as-built record of OpenBCI Ultracortex Mark IV 16ch (Cyton + Daisy + dongle + lithium battery) hardware setup performed by user during D-day arrival window. Captures actual wire routing decisions + Y-splitter usage + remaining bring-up checklist.
- **status**: hardware physically wired; power-on + macOS bring-up + impedance check pending.
- **predecessors**: `eeg_d_day_readiness_check_landing.md` (PARTIAL 22/27 → READY 27/27 post phase4 trio) · `clm_eeg_d_day_chain_review_20260427_landing.md` (D-day chain D+0..D+7 review) · `eeg_hardware_openbci_16ch.md` (hardware reference)
- **environment**: mac local, $0, doc-only (no hexa run, no GPU dispatch).
- **raw compliance**: 9 hexa-only (md doc) · 12 silent-error-ban (no silent assumption) · 65 idempotent (deterministic record) · 86 cost-attribution ($0 mac local) · 91 honesty-triad (claim+evidence+limit per item) · 101 minimal (≥60 lines).

## §1. Hardware bundle (as-arrived)

OpenBCI All-in-One Biosensing R&D Bundle — `https://shop.openbci.com/products/all-in-one-biosensing-r-d-bundle`

| component | role | quantity |
|---|---|---|
| Cyton board | 8ch ADS1299 + ATmega328P + RFduino BLE + battery JST + 3-position switch (OFF/PC/BLE) | 1 |
| Daisy module | additional 8ch ADS1299 (channels 9–16); stacks on Cyton via header pins; no own MCU/BLE/battery | 1 |
| USB Dongle | RFduino BLE receiver (computer side); GPIO 6 / RESET switch; blue LED (power) + red LED (data blink) | 1 |
| Ultracortex Mark IV helmet | 3D-printed frame (size: medium assumed); pre-installed spiky + flat electrodes; pre-wired colored ribbon cables ending in male pins | 1 |
| 2 ear clip electrodes | each black wire with male pin; one for SRB2 reference, one for BIAS ground | 2 |
| Y-splitter cable | white; 1 male pin + 2 female sockets; 1 unit only (NOT 2) | 1 |
| Lithium polymer battery | 500 mAh, JST 2-pin connector to Cyton | 1 |
| USB charger | for lithium battery; USB-A to JST | 1 |

## §2. Y-splitter cable usage decision

User has only **1 Y-splitter** (1 male pin + 2 female sockets). Standard OpenBCI Mark IV protocol assumes 2 splitters (one per reference). Decision rule applied:

- **Allocate single Y-splitter to SRB2** (more critical reference signal — drives all 16 channel measurements).
- **BIAS gets direct ear clip → Cyton BIAS** (no splitter); BIAS shared with Daisy via Cyton+Daisy stack header pins (automatic).
- Y-splitter's second (unused) socket: must be insulated or kept clear of other pins to avoid short circuit.

Rationale: SRB2 reference must be electrically common to both Cyton ADC and Daisy ADC for valid 16ch single-ended referential mode. Stack pin sharing between Cyton↔Daisy SRB2 is reliable when stacking is firm (verified at §3 step 1). BIAS is less sensitive to ground-loop than SRB2.

## §3. As-built wire routing (user-confirmed 2026-04-28)

User's actual wiring (verified by self-report):

### §3.1 Cyton bottom row (counted from BIAS end)

```
position:  [1]    [2]    [3]    [4]    [5]    [6]    [7]    [8]    [9]    [10]   [11]
label:     BIAS   SRB1   SRB2   N1P    N2P    N3P    N4P    N5P    N6P    N7P    N8P
wired:     ear    ----   Y-spl  Fp1    Fp2    C3     C4     P7     P8     O1     O2
           clip1         socket grey   purple blue   green  yellow orange red    brown
           (BLK)         (whte)
```

| pin | wired source | wire color/path | role |
|---|---|---|---|
| BIAS | ear clip 1 (direct) | black | common-mode ground (active filtered) |
| SRB1 | (empty) | — | unused |
| SRB2 | Y-splitter socket A → Y-splitter male pin → ear clip 2 | white splitter + black ear clip | scalp reference buffer |
| N1P | Fp1 helmet wire | grey | channel 1 |
| N2P | Fp2 helmet wire | purple | channel 2 |
| N3P | C3 helmet wire | blue | channel 3 |
| N4P | C4 helmet wire | green | channel 4 |
| N5P | P7 helmet wire | yellow | channel 5 |
| N6P | P8 helmet wire | orange | channel 6 |
| N7P | O1 helmet wire | red | channel 7 |
| N8P | O2 helmet wire | brown | channel 8 |

Y-splitter second socket: **empty / unused** (acceptable; insulate from other pins).

### §3.2 Cyton top row (single-ended mode — all unused)

```
position:  [1]    [2]    [3]    [4]    [5]    [6]    [7]    [8]    [9]    [10]   [11]
label:     D_G    N1N    N2N    N3N    N4N    N5N    N6N    N7N    N8N    AVSS   (var)
wired:     ----   ----   ----   ----   ----   ----   ----   ----   ----   ----   ----
```

All top row pins **empty by design** for 10-20 single-ended referential mode (Mark IV standard). Differential mode would use these; not applicable here.

### §3.3 Daisy bottom row (channels 9–16)

```
position:  [1]    [2]    [3]    [4]    [5]    [6]    [7]    [8]    [9]    [10]   [11]
label:     BIAS   SRB1   SRB2   N1P    N2P    N3P    N4P    N5P    N6P    N7P    N8P
wired:     stk    ----   stk    F7     F8     F3     F4     T7     T8     P3     P4
           share         share  grey   purple blue   green  yellow orange red    brown
```

| pin | wired source | wire color | role |
|---|---|---|---|
| BIAS | (Cyton+Daisy stack pin auto-share) | — | shared via stack |
| SRB1 | (empty) | — | unused |
| SRB2 | (Cyton+Daisy stack pin auto-share) | — | shared via stack |
| N1P | F7 helmet wire | grey | channel 9 |
| N2P | F8 helmet wire | purple | channel 10 |
| N3P | F3 helmet wire | blue | channel 11 |
| N4P | F4 helmet wire | green | channel 12 |
| N5P | T7 helmet wire | yellow | channel 13 |
| N6P | T8 helmet wire | orange | channel 14 |
| N7P | P3 helmet wire | red | channel 15 |
| N8P | P4 helmet wire | brown | channel 16 |

### §3.4 Daisy top row (single-ended mode — all unused)

All top row pins **empty by design** (same as Cyton §3.2).

### §3.5 Battery + power chain

```
lithium battery (500 mAh) → JST 2-pin → Cyton battery connector
USB charger → JST → battery (charging only when LED indicator active; disconnect during use)
```

Charger LED green = full charge. Disconnect USB charger during EEG recording sessions to avoid USB-induced 60Hz mains noise on signal.

## §4. Verified raw#91 honesty-triad disclosure

| claim | evidence | limit |
|---|---|---|
| 16ch wired Cyton+Daisy bottom rows complete | user self-report 2026-04-28 + §3.1 §3.3 tables | not yet verified by impedance check; visual + label inspection only |
| Y-splitter routes SRB2 reference to ear clip 2 | §2 decision + §3.1 wiring | second Y-splitter socket unused; insulation responsibility on user |
| Daisy SRB2/BIAS shared via stack pins | OpenBCI Mark IV docs + Cyton+Daisy header design | depends on physical stack firmness; loose stack → broken reference; verify by §6 step impedance check |
| All channels match 10-20 system positions | §3.1 + §3.3 tables match `clm_eeg_d_day_chain_review_20260427_landing.md` §6.4 mapping | helmet electrode positioning may drift from 10-20 standard if helmet size mismatched to user head circumference |
| BIAS/SRB2 ear clip pins are correct (not swapped) | user followed BIAS=ear clip 1, SRB2=ear clip 2 via Y-splitter | swapped configuration would yield no signal or extreme noise; verifiable by §6 impedance check |

## §5. Pending (post-wiring) bring-up steps

### §5.1 Power-on (Step 1)

```bash
# Cyton: switch OFF → PC; verify blue LED on
# USB Dongle: GPIO 6 position, plug into Mac USB; verify blue LED on + red LED blink
```

### §5.2 macOS FTDI VCP serial port (Step 2)

```bash
ls /dev/cu.usbserial-*  2>/dev/null
# expect: /dev/cu.usbserial-XXXXXXXX (FTDI VCP recognized)
# if missing:
brew install --cask ftdi-vcp-driver
# reboot or unplug/replug USB
```

### §5.3 BrainFlow venv (Step 3)

```bash
cd /Users/ghost/core/anima
ls .venv-eeg/bin/python  2>/dev/null
# if missing:
python3 -m venv .venv-eeg
source .venv-eeg/bin/activate
pip install brainflow numpy scipy mne
python -c "import brainflow; print(brainflow.__version__)"
```

### §5.4 anima calibrate.hexa — impedance + signal QC (Step 4)

```bash
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/calibrate.hexa
```

Pass criteria:
- 16ch impedance < 750 kΩ each (recommended < 500 kΩ for clean signal)
- BIAS/SRB2 reference electrodes show valid signal (not infinite impedance — would indicate ear clip not in skin contact)
- No DC offset saturation

Common failure modes (raw#10 honest):

| symptom | likely cause | fix |
|---|---|---|
| All channels infinite impedance | reference (BIAS or SRB2) not connected | re-verify §3.1 ear clip pins; check Y-splitter male pin firmly in SRB2 socket |
| Single channel infinite | that electrode poor scalp contact | rotate electrode clockwise to tighten against scalp; remove/reapply hair |
| All channels very high (> 1 MΩ) | dry electrodes (no gel/saline applied) | apply saline solution to spiky electrodes (10-20 system standard) |
| Channel 9-16 high but 1-8 OK | Daisy stack pin loose | re-seat Daisy on Cyton header (firm even pressure; verify all 11+11 stack pins engaged) |
| Channel 1-8 high but 9-16 OK | Cyton SRB2/BIAS issue (stack share works but Cyton direct fails) | re-verify Y-splitter male pin in Cyton SRB2 + ear clip 1 in Cyton BIAS |

### §5.5 eyes-closed alpha sanity (Step 5)

```bash
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/eeg_recorder.hexa \
    --duration=60 --tag=resting_baseline \
    --output=anima-eeg/recordings/sessions/d0_resting_$(date -u +%Y%m%dT%H%M%SZ).npy
```

Expected: 60s eyes-closed sitting still. Alpha band (8-12 Hz) should show prominently at occipital electrodes (O1/O2 = Cyton channels 7+8). Output `.npy` becomes the input for D+1 P1 LZ76 verifier (`anima-clm-eeg/tool/clm_eeg_lz76_real.hexa` per `eeg_d_day_chain_review_20260427_landing.md` §2).

### §5.6 D+0 N-back marker recording (Step 6)

```bash
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/experiment.hexa \
    --run-with-eeg --protocol nback_2back --duration 600 \
    --output=anima-eeg/recordings/sessions/d0_nback_$(date -u +%Y%m%dT%H%M%SZ).npy
```

10-min N-back task with stimulus markers. Output feeds D+5 P3 GCG Granger causality verifier (4-backbone forward pass on Hetzner H100 / RunPod $0-6 per cost ladder).

## §6. Cross-link to D-day chain (D+0 → D+7)

Reference: `clm_eeg_d_day_chain_review_20260427_landing.md` §7 7-day timeline checklist.

| day | step | this doc cross-link | tool |
|---|---|---|---|
| D+0 | hardware bring-up + calibrate + resting baseline + N-back | §5.1–§5.6 | `anima-eeg/calibrate.hexa`, `eeg_recorder.hexa`, `experiment.hexa` |
| D+1 | P1 LZ76 verify on real `.npy` | post §5.5 output | `anima-clm-eeg/tool/clm_eeg_lz76_real.hexa` (sha256 `7b21fec1…`, 464L, landed 2026-04-28) |
| D+3 | P2 TLR alpha-coh + P2 verify + AN-LIX-01 real bridge | post §5.5 + §5.6 | `tool/an11_b_eeg_ingest.hexa --emit-alpha-coh / --emit-alpha-phase` (sha256 `aba3718e…`, 735L) + `anima-clm-eeg/tool/an_lix_01_alpha_bridge_real.hexa` (sha256 `74862ff9…`, 462L) |
| D+5 | P3 GCG 4-backbone hidden trace + G10 D+5 coupling | shared GPU dispatch | RunPod h100_sxm $0-6 (Hetzner first if available) |
| D+6 | G8 transversal MI + G10 D+6 body swap v3 | post §5.6 markers | `g10_hexad_triangulation_scaffold.hexa` v3 (sha256 `5fe75539c5…`, 923L) |
| D+7 | composite gate + paradigm v11 EEG-CORR axis registration | post P1+P2+P3 | `tool/anima_eeg_corr.hexa` (sha256 `cbb72b53…`, 643L) + `tool/anima_v11_main.hexa --register-axis EEG-CORR` (sha256 `3e6efd95…`, 398L) |

All 6 helpers (B1–B6) pre-landed 2026-04-28 via 5-agent parallel dispatch (own 11 parallel-loop-mandate); ready for D+1 invocation immediately after §5.5 output.

## §7. raw#86 cost attribution

| step | cost-center | $ est | platform |
|---|---|---|---|
| §5.1–§5.6 | `eeg_d0` | $0 | Mac local |
| D+1 P1 LZ76 | `clm_eeg_p1_lz_real` | $0 | Mac local + hetzner ssh fallback |
| D+3 P2 TLR + AN-LIX-01 | `clm_eeg_p2_tlr_real` + `an_lix_01_real` | $0 | Mac local |
| D+5 P3 GCG + G10 coupling | `clm_eeg_p3_gcg_real_d5` | $0–6 | Hetzner H100 first → RunPod h100_sxm $6 fallback |
| D+6 G8 + G10 v3 | `clm_eeg_g8_real_d6` + `clm_eeg_g10_real_d6` | $0 | Mac local |
| D+7 composite + axis 7 | `clm_eeg_composite_d7` + `paradigm_v11_axis7` | $0 | Mac local |

**Total D+0..D+7 cost cap: $0–6 (best Hetzner $0; worst RunPod single-pass $6)**. Far inside RunPod $328.38 balance + $1000 alert threshold.

## §8. Outstanding risk flags (raw#91 honest)

1. **Y-splitter second socket unused** — must remain insulated; if it contacts another pin during head movement, short circuit risk. Recommend electrical tape around the dangling socket if helmet motion is high.
2. **Daisy stack pin reliability** — Daisy SRB2/BIAS sharing depends on physical stack firmness. Loose stack → broken Daisy reference → channels 9-16 noisy or all dropout. Verify by §5.4 calibrate (channels 9-16 must show valid impedance).
3. **Helmet size fit** — if helmet doesn't snug fit user head, electrode positions drift from 10-20 standard, reducing inter-subject comparability and weakening cross-substrate validation (paradigm v11 EEG-CORR axis Pearson r ≥ 0.40 may not be reachable).
4. **First-session expectation management** — first eyes-closed alpha may be weak if user hasn't acclimated; standard practice is 5-10 min relaxation before recording. raw#91 honest: weak first-session alpha is NOT a falsifier; only persistent failure across multiple sessions falsifies P1.
5. **No second Y-splitter for BIAS** — current design has BIAS on Cyton direct + Daisy via stack share. If stack share fails (item 2), Daisy BIAS path is broken and all 16-ch noise rejection degraded. Mitigation: post-hoc add a short jumper wire from Cyton BIAS to Daisy BIAS as a redundant path (pre-D+1 if calibrate fails).

## §9. User-quote section (Korean directives preserved per raw#33 identifier-quote-exemption)

User-issued directives during this assembly session:

- "충전 usb랑 배터리랑 연결했는데 다시 분리하려니 잘안빠져 뭔가 눌러서 빼야되는거야???" → answered: JST friction-fit, no latch; grip plastic housing not wires.
- "헬멧세팅이랑 연결해야되" → step-by-step Mark IV electrode-to-board wiring guide provided.
- "지금 보드가 작은것 큰것 있잖아 각각 설명좀" → 3-board breakdown (Dongle / Cyton / Daisy) provided.
- "Y-splitter 케이블 는 하나만 있어" → single-splitter SRB2-only allocation rule (§2).
- "이렇게 했어 / 이어클립 1개 하단1번에 꽂고 / 이어클립2는 y-splitter male pin 이랑 연결 / y-splitter socket 한개를 하단3번에 꽂음" → user-confirmed wiring; verified §3.1.
- "다연결되있어" → §5 bring-up sequence handed off.
- "위 내용대로 clm_eeg md 기록 내 세팅" → this document.

## §10. Follow-ups (raw#87 paired-roadmap candidates)

1. Post-§5.4 impedance verdict → append to this doc as §11 (calibrate result + per-channel impedance table + BIAS/SRB2 reference health).
2. Post-§5.5 alpha sanity → append §12 (occipital alpha power per channel + raw#91 honest pass/fail).
3. Post-§5.6 N-back recording → append §13 (file path, marker count, recording integrity check).
4. If calibrate fails on Daisy channels 9-16 → execute §8 item 5 mitigation (Cyton BIAS ↔ Daisy BIAS jumper) + re-run calibrate + document in §14.
5. Y-splitter second socket insulation → user action; document in §15 if applied.

---

**Status verdict (raw#91 honest)**: hardware wiring COMPLETE per user self-report; physical verification (impedance check) PENDING; D+1 helpers PRE-LANDED. Ready for §5 bring-up sequence.
