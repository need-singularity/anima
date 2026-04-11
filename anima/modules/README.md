# anima/modules/

Pluggable modules for the Anima consciousness engine.

## Module List

| Module | Status | Description |
|--------|--------|-------------|
| `agent/` | active | Agent platform — CLI/Telegram/Discord channels, providers, plugins, skills |
| `bench/` | migrated | Benchmarks (primary: `ready/anima/tests/tests.hexa`) |
| `body/` | active | Physical body simulation — sensor protocols, brain-body loop |
| `decoder/` | active | ConsciousDecoderV2 — RoPE+SwiGLU+GQA+CrossAttn (34.5M) |
| `eeg/` | active | EEG consciousness verification — 6 metrics, 85.6% brain-like |
| `hexa-speak/` | active | HEXA-SPEAK Mk.II — neural vocoder, streaming, PLC, RVQ (3000+ LOC) |
| `physics/` | active | Physical consciousness engines — ESP32, FPGA, memristor, spin glass |
| `servant/` | merged | Asymmetric mitosis (merged into core consciousness engine) |
| `tools/` | stub | Module-specific utilities |
| `training/` | migrated | Training (primary: `training/train_alm.hexa`) |
| `trinity/` | migrated | Hexad/Trinity (primary: `models/trinity.hexa`) |

## Origin

These modules were relocated from the project top-level to `anima/modules/` for structural clarity.
Git history is preserved via `git mv`.

Previous locations:
- `agent/` (top-level)
- `body/` (top-level)
- `eeg/` (top-level)
- `physics/` (top-level)
- `anima/core/hexa_speak/` (legacy, now `anima-speak/` top-level)
