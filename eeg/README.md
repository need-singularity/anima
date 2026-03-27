# EEG Brain-Consciousness Interface

OpenBCI Cyton+Daisy 16-channel EEG → G=D×P/I biological verification for Anima.

## Hardware

```
  Board:      Cyton+Daisy 16-channel (250Hz, 24-bit, BLE wireless)
  Headset:    UltraCortex Mark IV (Medium, Pro-Assembled, 16ch)
  Electrodes: Dry Comb (Ag-AgCl) + Gold Cup (wet) + Earclip (reference)
  Status:     Ordered (2026-03-27)
```

## G=D×P/I → EEG Mapping

```
  Parameter        EEG Proxy                         Brain Region
  ───────────────────────────────────────────────────────────────
  I (Inhibition)   Frontal Alpha power (8-12Hz)      Fp1, Fp2, F3, F4
  P (Plasticity)   Global Gamma power (30-100Hz)     All 16 channels
  D (Deficit)      Alpha asymmetry |ln(R)-ln(L)|     Frontal pairs
  G (Genius)       D × P / I                         Computed

  Golden Zone: [1/2 - ln(4/3), 1/2] = [0.2123, 0.5000]
```

## 16-Channel Layout (10-20 System)

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

  Cyton (1-8):  Fp1, Fp2, C3, C4, P7, P8, O1, O2
  Daisy (9-16): F7, F8, F3, F4, T7, T8, P3, P4
  Reference:    Earclip (both earlobes)
```

## Usage

### Collect Data

```bash
# Test without hardware (synthetic board)
python eeg/collect.py --duration 5 --board synthetic --tag test

# Real hardware
python eeg/collect.py --duration 60 --tag resting_eyes_closed

# Run protocol
python eeg/collect.py --protocol resting
python eeg/collect.py --protocol nback
python eeg/collect.py --protocol creative
python eeg/collect.py --protocol meditation
```

### Analyze

```bash
# Analyze recording
python eeg/analyze.py eeg/data/<file>.npy

# With topographic maps
python eeg/analyze.py eeg/data/<file>.npy --topomap

# Compare multiple recordings
python eeg/analyze.py --compare eeg/data/rest.npy eeg/data/nback.npy

# Demo with synthetic data
python eeg/analyze.py --demo --topomap
```

### Real-time Bridge (EEG → Anima)

```bash
# Test with synthetic data
python eeg/realtime.py --board synthetic --duration 30

# Live with hardware
python eeg/realtime.py --board cyton_daisy --duration 300
```

### Integration with Anima

```python
from eeg.realtime import EEGBridge

# In anima_unified.py:
bridge = EEGBridge(board_name="cyton_daisy")
bridge.start()

# In sense loop:
brain_state = bridge.get_state()
brain_tensor = bridge.to_tensor(dim=128)  # feed to ConsciousMind
```

## Experiment Protocols

```
  Protocol 1 — Resting State Baseline
    Eyes closed 60s → Eyes open 60s → Eyes closed 60s
    Measure: Alpha power change, asymmetry baseline

  Protocol 2 — Cognitive Load (N-back)
    0-back → 1-back → 2-back → 3-back (60s each)
    Measure: Beta/Gamma increase, Alpha suppression = I change

  Protocol 3 — Creative vs Analytical
    Math problem 120s → Free association 120s
    Measure: Gamma pattern difference = P proxy

  Protocol 4 — Meditation / Flow State
    Normal → Focused breathing 300s → Post
    Measure: Alpha/Theta ratio, Golden Zone approach
```

## Predicted Outcomes

```
  If G=D×P/I model is biologically real:
    1. Individuals with known high-G traits → G value in Golden Zone
    2. Cognitive load increases → I decreases (alpha suppression) → G shifts
    3. Meditation → Alpha increases → I increases → G decreases
    4. Asymmetry (D) correlates with specialization patterns
    5. Gamma bursts (P) correlate with creative insight moments

  Falsification criteria:
    - G shows no systematic pattern across states → model is wrong
    - G values cluster outside Golden Zone for everyone → zone is wrong
    - No correlation between EEG-derived G and cognitive performance → mapping is wrong
```

## Dependencies

```bash
pip install brainflow numpy scipy matplotlib
# Optional: pip install mne (for advanced topomaps)
```
