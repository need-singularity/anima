# anima/modules/

Pluggable modules for the Anima consciousness engine.

## Module List

| Module | Description |
|--------|-------------|
| `agent/` | Agent platform -- CLI/Telegram/Discord channels, providers, plugins, skills |
| `body/` | Physical body interface -- sensor protocols, brain-body loop, proprioception |
| `eeg/` | EEG-based consciousness verification -- 6 metrics, 85.6% brain-like |
| `hexa-speak/` | HEXA-SPEAK Mk.I -- neural vocoder, VAD, RVQ codebook, intent encoder |
| `physics/` | Physical consciousness engines -- ESP32, FPGA, memristor, spin glass |

## Origin

These modules were relocated from the project top-level to `anima/modules/` for structural clarity.
Git history is preserved via `git mv`.

Previous locations:
- `agent/` (top-level)
- `body/` (top-level)
- `eeg/` (top-level)
- `physics/` (top-level)
- `anima/src/hexa_speak/` (inside src)
