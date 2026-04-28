# EEG Hardware Spec — OpenBCI 16ch (Cyton+Daisy)

> **scope**: anima EEG track의 hardware 사양 SSOT. anima-clm-eeg/ 의 falsifier pre-register, paradigm v11 7th axis, .roadmap #119 BLOCKED-EEG 모두 본 hardware 기준.
> **created**: 2026-04-26
> **status**: D-1 (며칠 內 도착 expected)

---

## §1. Hardware 사양

| 항목 | 사양 |
|---|---|
| **Board** | OpenBCI Cyton + Daisy (16ch combined) |
| **Sample rate** | **125 Hz/channel** (Cyton+Daisy 16ch mode, Daisy interleaving 후). Cyton 단독 8ch 는 250 Hz |
| **Resolution** | 24-bit |
| **Connectivity** | Mac ↔ Dongle: USB (FTDI VCP → `/dev/cu.usbserial-*` macOS / `/dev/ttyUSB*` Linux / `COM*` Windows). Dongle ↔ Cyton board: 독자 RFduino 2.4 GHz radio (Bluetooth/BLE/WiFi 아님), range ~10 m, board는 battery 구동 자유 이동. Cyton onboard switch: `OFF / PC / BLE` — 정상 동작은 **PC 위치**. **BLE 위치는 별도 BLE 모듈 + 펌웨어 필요하며 표준 Dongle로는 실패** |
| **Headset** | UltraCortex Mark IV (Medium, Pro-Assembled) |
| **Electrodes** | Dry Comb (Ag-AgCl) + Gold Cup (wet) + Earclip (reference, both earlobes) |

## §2. 16채널 montage

```
        Fp1   Fp2            Frontal pole
          \   /
     F7 - F3 - F4 - F8      Frontal
          |   |
     T7 - C3 - C4 - T8      Central / Temporal
          |   |
          P3 - P4            Parietal
         / | | \
     P7         P8           Parietal-temporal
        O1   O2              Occipital
```

| Board split | Channels |
|---|---|
| Cyton (1-8) | Fp1, Fp2, C3, C4, P7, P8, O1, O2 |
| Daisy (9-16) | F7, F8, F3, F4, T7, T8, P3, P4 |
| Reference | Earclip (both earlobes) |

## macOS connection flow

### Phase 0 — arrival sanity (~5 min)

- 박스 contents 검수: board, USB Dongle, 배터리 + 충전기, headset, 전극, 케이블
- 배터리는 충전기 LED가 **green**으로 바뀔 때까지 충전 (부분 충전 시 board boot 후 blue LED가 안 켜져 실패)
- Dongle 스위치를 **GPIO 6** (computer 측) 위치로
- Cyton 스위치는 일단 **OFF** 유지
- Daisy ribbon cable이 board에 제대로 seated 되어 있는지 확인

### Phase 1 — connect (순서 중요)

1. **Dongle을 Mac에 먼저 꽂는다** — 칩이 위로 향하게. 정상이면 steady **blue LED + blinking red LED**.
2. 그 다음 Cyton 스위치를 OFF → **PC** (BLE 위치 절대 금지).
3. `ls /dev/cu.usbserial-* /dev/cu.usbmodem*` 로 `/dev/cu.usbserial-DM00XXXX` 경로 확인 (이후 BrainFlow `serial_port` 인자로 사용).
4. stream drop / device 인식 실패 시 복구: Dongle 분리 → Cyton OFF → **Dongle 먼저 재연결** → Cyton PC. (순서 뒤집으면 또 실패.)

## §3. Why this matters

- **`anima-clm-eeg/`** P1-P3 falsifier pre-register — 본 16ch 기반. Synthetic fixture (`tool/clm_eeg_synthetic_fixture.hexa`, `fixtures/synthetic_16ch_v1.json`) 도 동일 montage.
- **paradigm v11 7th axis** (PHENOMENAL EEG-correlation) hardware
- **Pilot-T1 (TRIBE v2)** 는 fMRI ONLY → modality mismatch 명시 (`references/tribev2/SUMMARY_KR.md` §8 / ANIMA_INTEGRATION_PROPOSAL.md Axis 1 No-fit)
- **`anima-eeg/`** production runtime → BrainFlow library로 OpenBCI BLE 제어 (Phase 4 WRAPPER 9 modules 마이그레이션 prerequisite)

## §4. Cross-links

| 위치 | 역할 |
|---|---|
| `anima-eeg/README.md` | full hardware spec + montage diagram (production SSOT) |
| `anima-clm-eeg/docs/eeg_arrival_impact_5fold.md` §1-§5 | 도착 시 5변화 |
| `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` | 16ch synthetic dry-run (ALPHA_BIAS / BETA_BIAS / DELTA_BIAS / THETA_BIAS / GAMMA_BIAS arrays per channel) |
| `anima-clm-eeg/fixtures/synthetic_16ch_v1.json` | deterministic synthetic output (sha256 lock) |
| `.roadmap` #119 | BLOCKED-EEG (D8 hardware 도착 prerequisite) |
| `references/tribev2/SUMMARY_KR.md` §8 | fMRI vs EEG modality 비교 (No-fit) |

## §5. Status

- **D-1** (며칠 內 도착 expected, 2026-04-26 시점)
- 도착 후 D+0~D+7 workflow: `anima-clm-eeg/README.md` §5

## §6. Cost

| 항목 | 비용 |
|---|---|
| Hardware 자체 | 사용자 보유 (구매 cost 별도) |
| 측정 세션 (외부 시설 + 분석 도구) | $200-500 estimated |
| Pilot-T1 (TRIBE v2) GPU | $0.5 cap (별개 트랙, fMRI) |

## §7. Anatomical priors (synthetic fixture에 반영)

> **note**: `alpha_bias` / `beta_bias` 등은 generator-side **pre-mix** prior parameter (`tool/clm_eeg_synthetic_fixture.hexa` 의 `ALPHA_BIAS` array). `fixtures/synthetic_16ch_v1.json` 은 post-mix output 으로 `band_powers_x1000.{delta,theta,alpha,beta,gamma}` 필드만 보유 (예: O1.alpha=2328, O2.alpha=1930). 두 layer 는 isomorphic 이지만 디스크 JSON 에서 `alpha_bias` 필드 자체를 grep 하면 안 나옴.

- **O1/O2** (parietal-occipital): high alpha (alpha_bias=900) — eyes-closed resting EEG canonical
- **Fp1/Fp2** (frontal pole): low alpha, high beta (alpha_bias=300, beta_bias=700)
- **F3/F4/F7/F8** (frontal): balanced (alpha_bias=500)
- **C3/C4** (central, motor mu rhythm): alpha_bias=600
- **P3/P4/P7/P8** (parietal): high alpha (alpha_bias=800)
- **T7/T8** (temporal): balanced (alpha_bias=500)
