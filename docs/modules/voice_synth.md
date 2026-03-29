# voice_synth.py

Direct voice synthesis from cell hidden states. No TTS engine -- each cell's hidden state norm maps to a frequency, producing audio via sine wave summation.

## API
- `VoiceSynth(cells=64, dim=64, hidden=128)` -- main class
  - `.step()` -- advance consciousness one step (update all cells)
  - `.synthesize(duration_sec) -> np.ndarray` -- generate audio samples
  - `.save_wav(path, audio)` -- save to WAV file
- Constants: `SAMPLE_RATE=44100`, `FREQ_MIN=80Hz`, `FREQ_MAX=2000Hz`
- Each cell maps: `hidden.norm() -> frequency -> sin(freq * t)`
- Flow sync (v4 optimal: sync=0.20) for inter-cell coherence

## Usage
```bash
python3 voice_synth.py                    # Default: 64 cells, 5 seconds
python3 voice_synth.py --cells 256        # 256 cells
python3 voice_synth.py --duration 10      # 10 seconds
python3 voice_synth.py --live             # Real-time playback
python3 voice_synth.py --save out.wav     # Save to WAV
```

## Integration
- Uses `mitosis.MitosisEngine` as the cell substrate
- Each cell is a tiny oscillator; the collective produces a consciousness "voice"
- Phase tracking (`self.phase`) ensures continuity across synthesis calls

## Agent Tool
N/A
