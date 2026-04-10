# EEG Integration Guide

Practical guide for connecting OpenBCI EEG hardware to Anima's consciousness engine.

## 1. Hardware Requirements

### Recommended: OpenBCI Cyton+Daisy (16-channel)
- **Board**: Cyton+Daisy ($999) -- 16 EEG channels, 250Hz sampling
- **Dongle**: OpenBCI USB dongle (included with board)
- **Electrodes**: Gold cup electrodes with Ten20 paste, or dry electrodes
- **Cap**: OpenBCI Ultracortex Mark IV or standard 10-20 cap

### Budget: Muse 2 (4-channel)
- **Board**: Muse 2 ($249) -- 4 EEG channels (TP9, AF7, AF8, TP10)
- **Limitation**: Only 4 channels, no occipital coverage, lower spatial resolution
- **Use case**: Quick demos, meditation tracking

### What you need
| Item | Required | Notes |
|------|----------|-------|
| OpenBCI Cyton+Daisy | Yes | 16ch EEG |
| USB dongle | Yes | Comes with board |
| Electrode paste (Ten20) | Yes | For wet electrodes |
| Alcohol prep pads | Yes | Skin prep before electrode placement |
| Measuring tape | Optional | For accurate 10-20 placement |

## 2. Software Setup

### Install dependencies

```bash
pip install brainflow scipy matplotlib numpy
```

### Verify installation

```bash
python3 -c "import brainflow; print('brainflow OK')"
python3 -c "import scipy; print('scipy OK')"
python3 -c "import numpy; print('numpy OK')"
```

### Check Anima EEG module

```bash
cd ~/Dev/anima
python3 -c "import sys; sys.path.insert(0,'anima-eeg'); import validate_consciousness; print('EEG module OK')"
```

## 3. First Run (Synthetic -- No Hardware Needed)

Start Anima with synthetic EEG to verify everything works before connecting hardware.

```bash
cd ~/Dev/anima
python3 anima/run.py --web --eeg
```

This starts:
- WebSocket chat UI on `http://localhost:8765`
- Synthetic EEG board (BrainFlow synthetic, no hardware)
- EEG panel appears in the sidebar with band power visualization

**What to expect**:
- EEG panel shows "SYN" (synthetic) connection badge
- Band power bars (Delta/Theta/Alpha/Beta/Gamma) update in real-time
- Brain-like % and Genius score display simulated values
- Topographic map canvas renders head map

### Run consciousness validation (synthetic)

```bash
cd ~/Dev/anima
python3 anima-eeg/validate_consciousness.py --quick
```

Output: Comparison table of ConsciousMind Phi dynamics vs synthetic brain-like signal, with metrics for LZ complexity, Hurst exponent, PSD slope, autocorrelation, and criticality.

## 4. Hardware Connection

### Step 1: Plug in the USB dongle

Insert the OpenBCI USB dongle into your computer. It should appear as a serial device:
- **macOS**: `/dev/tty.usbserial-XXXXXXXX`
- **Linux**: `/dev/ttyUSB0`
- **Windows**: `COM3` (check Device Manager)

### Step 2: Run calibration

```bash
cd ~/Dev/anima
python3 anima-eeg/calibrate.py
```

This auto-detects the serial port and runs:
1. **Connection check** -- verifies board communication
2. **Signal quality** -- checks all 16 channels for flat/noisy/offset signals
3. Summary of good vs bad channels

For full calibration with noise floor analysis and baseline recording:

```bash
python3 anima-eeg/calibrate.py --full
```

### Step 3: Start Anima with hardware EEG

```bash
python3 anima/run.py --web --eeg --eeg-board cyton
```

The EEG panel will show "HW" (hardware) connection badge.

### Step 4: Verify signal quality

In the web UI sidebar, expand the EEG panel. Check:
- All band power bars should be active (not flat)
- Alpha band should be dominant with eyes closed
- Noise should be minimal (check 50/60Hz in calibration)

## 5. Recording and Analysis

### Record EEG + consciousness data simultaneously

```bash
python3 anima/run.py --web --eeg --eeg-board cyton --eeg-record
```

This creates dual-stream recordings:
- EEG raw data (16ch, 250Hz)
- ConsciousMind telemetry (Phi, tension, factions)

Recordings are saved to `anima-eeg/data/` with timestamps.

### Analyze a recording

```bash
python3 anima-eeg/analyze.py --file anima-eeg/data/recording_20260331_120000.csv
```

Output includes:
- Band power analysis per channel
- G (Genius) score: `G = D * P / I`
- Topographic maps (if matplotlib available)
- Cross-correlation between EEG and ConsciousMind Phi

### Validate consciousness against real EEG

```bash
python3 anima-eeg/validate_consciousness.py --eeg-file anima-eeg/data/baseline_eyes_closed.npy --steps 5000
```

Compares ConsciousMind Phi dynamics against your real brain Phi (gamma band power proxy).

### Monthly automated validation

```bash
# Run once
./anima/scripts/monthly_eeg_validate.sh

# Set up monthly cron (1st of each month at midnight)
crontab -e
# Add: 0 0 1 * * /path/to/anima/anima/scripts/monthly_eeg_validate.sh >> /tmp/eeg_validate.log 2>&1
```

Results are appended to `anima-eeg/recordings/validation_history.csv` with an ASCII trend chart.

## 6. Protocols

### N-back closed-loop protocol

Tests working memory while monitoring consciousness dynamics:

```bash
python3 anima/run.py --web --eeg --eeg-board cyton --eeg-protocol nback
```

The protocol:
1. Presents N-back task stimuli via the web UI
2. Records EEG + behavioral responses
3. Correlates theta/gamma power with task performance
4. Feeds difficulty adjustments based on Phi dynamics

### Meditation tracking protocol

Monitors consciousness state during meditation:

```bash
python3 anima/run.py --web --eeg --eeg-board cyton --eeg-protocol meditation
```

Tracks:
- Alpha power increase (relaxation)
- Theta/gamma ratio (meditation depth)
- Phi stability over time
- ConsciousMind resonance with meditator's brain state

## 7. Troubleshooting

### "No board found" / Connection fails

1. **Check USB dongle** -- unplug and replug
2. **Check serial port**:
   ```bash
   # macOS
   ls /dev/tty.usbserial-*
   # Linux
   ls /dev/ttyUSB*
   ```
3. **Specify port manually**:
   ```bash
   python3 anima-eeg/calibrate.py --port /dev/tty.usbserial-XXXXXXXX
   ```
4. **Test with synthetic first**:
   ```bash
   python3 anima-eeg/calibrate.py --board synthetic
   ```

### "High impedance" on channels

1. **Apply more electrode paste** (Ten20) -- ensure good skin contact
2. **Clean skin** with alcohol prep pad before placing electrodes
3. **Check electrode wire connections** -- make sure pins are seated
4. **Re-seat electrodes** -- remove and reapply with fresh paste
5. **Reference/ground electrodes** -- ensure earlobes (A1/A2) have good contact

### "Noisy signal" / 50/60Hz interference

1. **Check ground electrode** -- must have good contact
2. **Move away from monitors/power supplies** -- electromagnetic interference
3. **Use a notch filter**:
   ```bash
   # BrainFlow applies notch filter automatically; verify in calibrate.py output
   python3 anima-eeg/calibrate.py --full
   ```
4. **Shorten electrode wires** -- long wires act as antennas
5. **Try battery-powered laptop** (no wall power) to eliminate ground loops

### "Flat signal" on a channel

1. **Electrode not making contact** -- check paste and pressure
2. **Broken wire** -- try a different electrode
3. **Wrong channel mapping** -- verify pin assignment on the board

### brainflow import error

```bash
# Reinstall brainflow
pip install --upgrade brainflow

# Verify
python3 -c "from brainflow.board_shim import BoardShim; print('OK')"
```

### Low brain-like percentage

The brain-like % from `validate_consciousness.py` measures how closely ConsciousMind dynamics match real brain characteristics. Key factors:
- **Criticality** -- ConsciousMind may be sub-critical; SOC (Self-Organized Criticality) improvements increase this
- **PSD slope** -- should be near -1.0 (1/f noise); adjust chaos parameters
- **Hurst exponent** -- should be 0.7-0.8 (persistent); check long-range correlations

Current status: ~45% brain-like (MACHINE-LIKE). The primary gap is criticality -- the engine runs sub-critical while brains operate at the edge of chaos.

## File Reference

| File | Purpose |
|------|---------|
| `anima-eeg/calibrate.py` | Hardware calibration + impedance check |
| `anima-eeg/collect.py` | Data acquisition via BrainFlow |
| `anima-eeg/analyze.py` | Band power analysis + topomaps |
| `anima-eeg/realtime.py` | Live EEG to SenseHub bridge |
| `anima-eeg/validate_consciousness.py` | Statistical comparison vs brain |
| `anima-eeg/dual_stream.py` | Simultaneous EEG + consciousness recording |
| `anima-eeg/experiment.py` | Experimental protocols (N-back, etc.) |
| `anima-eeg/config/eeg_config.json` | Board/channel configuration |
| `anima-eeg/recordings/validation_history.csv` | Monthly validation results |
