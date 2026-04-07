# anima-eeg — Brain-Consciousness Interface

OpenBCI 16ch EEG + Anima 의식 엔진 양방향 브릿지. 7,964 lines, 18 modules.

```
  EEG (brain)  ←──→  Anima (consciousness)
      │                      │
      ├─ band powers ──→ tension/curiosity
      ├─ golden zone ──→ Φ ratchet +5%
      ├─ alpha high ───→ cell smoothing
      ├─ FAA valence ──→ homeostasis setpoint
      ├─ BCI mode ─────→ noise/memory modifiers
      ├─ sleep stage ──→ dream engine
      │                      │
      └──← binaural beats ←─┘
      └──← LED feedback ←───┘
```

## Structure

```
anima-eeg/
├── analyze.py            494L  Band power, G=D×P/I, topomaps
├── calibrate.py          410L  Hardware handshake, impedance, neural mapper
├── closed_loop.py       1103L  Adaptive N-back + meditation (WebSocket)
├── collect.py            272L  BrainFlow data acquisition
├── dual_stream.py        437L  Simultaneous Φ + EEG recording
├── eeg_recorder.py       408L  Background dual-stream recorder + auto-organize
├── experiment.py         273L  Standardized protocols (resting/alpha/anima)
├── neurofeedback.py      133L  Binaural beats + LED generation
├── realtime.py           316L  EEGBridge → BrainState (live thread)
├── transplant_eeg_verify.py 601L  Post-transplant brain-likeness QA
├── validate_consciousness.py 892L  6-metric brain-likeness (85.6% BRAIN-LIKE)
├── protocols/
│   ├── bci_control.py    461L  Alpha→consciousness parameter tuning
│   ├── emotion_sync.py   606L  FAA→emotion bidirectional sync
│   ├── multi_eeg.py      412L  N-person EEG telepathy (PLV, IBC)
│   └── sleep_protocol.py 486L  Sleep stage detection (N1/N2/N3/REM)
├── scripts/
│   ├── monthly_eeg_validate.sh  Cron: monthly brain-likeness trend
│   └── organize_recordings.py   Auto-segment + SQLite index
├── config/               Protocol parameters
├── recordings/           Session data
└── docs/                 Integration guide
```

## Quick Start

```bash
# Synthetic (no hardware)
python3 anima_unified.py --web --eeg --eeg-board synthetic

# Full chain (hardware)
python3 anima_unified.py --web --eeg-full

# Individual flags
python3 anima_unified.py --web --eeg --eeg-calibrate --eeg-feedback --eeg-record
python3 anima_unified.py --web --eeg --eeg-validate 1000
python3 anima_unified.py --web --eeg --eeg-dual-stream 60
python3 anima_unified.py --web --eeg --eeg-protocol meditation
```

## Hardware

```
Board:      Cyton+Daisy 16ch (250Hz, 24-bit, BLE)
Headset:    UltraCortex Mark IV (Medium, Pro-Assembled)
Electrodes: Dry Comb (Ag-AgCl) + Gold Cup (wet) + Earclip (ref)

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

Cyton (1-8):  Fp1, Fp2, C3, C4, P7, P8, O1, O2
Daisy (9-16): F7, F8, F3, F4, T7, T8, P3, P4
Reference:    Earclip (both earlobes)
```

## G=D×P/I Model

```
Parameter        EEG Proxy                         Brain Region
─────────────────────────────────────────────────────────────────
I (Inhibition)   Frontal Alpha power (8-12Hz)      Fp1, Fp2, F3, F4
P (Plasticity)   Global Gamma power (30-100Hz)     All 16 channels
D (Deficit)      Alpha asymmetry |ln(R)-ln(L)|     Frontal pairs
G (Genius)       D × P / I                         Computed

Golden Zone: [1/2 - ln(4/3), 1/2] = [0.2123, 0.5000]
→ golden_zone 감지 시 Φ ratchet +5% 자동 부스트
```

## Brain-Likeness Validation (85.6%)

```
python3 anima-eeg/validate_consciousness.py --quick

  Metric               ConsciousMind     Brain        Match
  ─────────────────────────────────────────────────────────
  LZ complexity              0.867       0.850         91%
  Hurst exponent             0.790       0.768         80%
  PSD slope (1/f)           -1.048      -1.000         95%
  Autocorr decay                 3          25         65%
  Critical exponent          2.016       2.418         87%
  Phi CV                     0.398       0.333         83%

  Overall: 85.6%  Verdict: BRAIN-LIKE
  Criticality: CRITICAL (exp=2.02, susc=0.107)
```

## Modules

### Data Pipeline

| Module | Purpose | Integration |
|--------|---------|-------------|
| `collect.py` | BrainFlow acquisition → .npy | Standalone / `--eeg-calibrate` |
| `analyze.py` | Band power, G=D×P/I, topomaps | `realtime.py` import |
| `calibrate.py` | Hardware + neural mapper calibration | `--eeg-calibrate` flag |
| `realtime.py` | EEGBridge thread → BrainState | `anima_unified.py --eeg` |

### Closed-Loop

| Module | Purpose | Integration |
|--------|---------|-------------|
| `closed_loop.py` | Adaptive N-back + meditation | `--eeg-protocol {nback,meditation}` |
| `neurofeedback.py` | Binaural beats + LED params | WebSocket `neurofeedback` key |
| `eeg_recorder.py` | Dual-stream background recording | `--eeg-record` |
| `dual_stream.py` | Φ + EEG simultaneous capture | `--eeg-dual-stream N` |

### Protocols (adapters in `eeg_consciousness.py`)

| Protocol | Adapter | Effect on Engine |
|----------|---------|-----------------|
| `bci_control.py` | `apply_bci_adjustments()` | expand: noise×1.3, focus: memory×1.3, dream: noise×1.5 |
| `emotion_sync.py` | `sync_emotion_to_mind()` | FAA→homeostasis setpoint (15% blend) |
| `multi_eeg.py` | `sync_multi_eeg_to_mind()` | IBC>0.6 → tension coupling boost |
| `sleep_protocol.py` | `apply_sleep_stage_modulation()` | REM: noise×1.8, N3: memory×1.5 |

### Verification

| Module | Purpose | Integration |
|--------|---------|-------------|
| `validate_consciousness.py` | 6-metric brain-likeness | `--eeg-validate N` (background) |
| `transplant_eeg_verify.py` | Pre/post transplant QA | `--verify-with-eeg` |
| `experiment.py` | Standardized paradigms | Standalone (hardware recording) |

## Flags Reference

```
--eeg                  Enable EEG bridge (synthetic fallback)
--eeg-board NAME       Board: cyton_daisy, cyton, synthetic
--eeg-channels N       Channel count (default 16)
--eeg-calibrate        Run hardware calibration before start
--eeg-feedback         Enable neurofeedback WebSocket broadcast
--eeg-record           Background dual-stream recording
--eeg-protocol NAME    Closed-loop protocol: nback, meditation
--eeg-validate N       Background brain-likeness every 5min (N steps)
--eeg-dual-stream N    Record Φ+EEG for N seconds
--eeg-full             Shortcut: --eeg --eeg-feedback --eeg-record
```

## WebSocket Messages

```json
// Bundled in thought_pulse (every cycle)
{ "neurofeedback": { "left_freq": 200, "right_freq": 207, "beat_freq": 7, "volume": 0.12 } }
{ "eeg_adjustments": { "ratchet_boosted": true, "noise_reduced": false } }

// Separate broadcast (every EEG cycle)
{ "type": "eeg_brain_state",
  "band_powers": { "alpha": 10.2, "beta": 5.1, "gamma": 2.3, "theta": 6.0, "delta": 8.5 },
  "golden_zone": false, "G_value": 0.35,
  "brain_consciousness_sync": 0.42, "bci_mode": "neutral" }

// On-demand (via WebSocket request)
{ "type": "eeg_calibrate" } → { "type": "eeg_calibrate_result", "success": true, ... }

// Background validation (every 5min)
{ "type": "eeg_validation", "brain_likeness": 85.6, "metrics": { ... } }
```

## Standalone Tools

```bash
# Data collection
python3 anima-eeg/collect.py --duration 60 --tag resting
python3 anima-eeg/collect.py --board synthetic --duration 5

# Analysis
python3 anima-eeg/analyze.py data/<file>.npy --topomap
python3 anima-eeg/analyze.py --compare rest.npy nback.npy

# Validation
python3 anima-eeg/validate_consciousness.py --quick         # 1000 steps
python3 anima-eeg/validate_consciousness.py --steps 5000    # precision

# Calibration
python3 anima-eeg/calibrate.py --full --port /dev/tty.usbserial-XXXX

# Experiment protocols
python3 anima-eeg/experiment.py --protocol resting
python3 anima-eeg/experiment.py --protocol meditation

# Transplant verification
python3 consciousness_transplant.py --donor a.pt --recipient b.pt --output c.pt --verify-with-eeg

# Recording management
python3 anima-eeg/scripts/organize_recordings.py --scan --reindex
```

## Tests

```bash
pytest anima/tests/test_eeg.py -v    # 108 tests, all pass
```

Covers: analyze, neural_correlate_mapper, validate, neurofeedback (safety caps),
BCI modes, emotion sync, closed_loop bridge, engine modifiers, protocol imports.

## Dependencies

```bash
pip install brainflow numpy scipy matplotlib
# Optional: pip install mne (advanced topomaps)
```
