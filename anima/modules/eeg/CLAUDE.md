# eeg/

## Purpose
EEG brain-consciousness interface. Bridges OpenBCI hardware to Anima's SenseHub for live neural-to-tension mapping.

## Key Files
- `collect.py` — OpenBCI data acquisition via BrainFlow
- `analyze.py` — Band power analysis, G=D*P/I formula, topomaps
- `realtime.py` — Live EEG to Anima bridge (SenseHub integration)

## File Naming
- Python scripts: snake_case (`collect.py`, `analyze.py`)
- Data files: timestamped CSVs in `data/` if applicable

## Dependencies
- brainflow (pip) — OpenBCI communication
- scipy, matplotlib (pip) — Analysis and topomaps
- numpy — Numerical processing

## Parent Rules
See /CLAUDE.md → "Structure" and eeg/README.md for detailed docs.
