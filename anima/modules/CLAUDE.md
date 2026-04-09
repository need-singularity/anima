# Modules — AI Instructions

> All modules live under `anima/modules/`. Core code stays in `anima/core/`.

## Rules

- **HEXA-FIRST**: new files must be `.hexa`. No new `.py`/`.rs`/`.sh`.
- **No hardcoding**: constants from `core/laws.hexa` or `config/consciousness_laws.json`.
- **Hub registration**: every module must register in `core/hub.hexa` with 3+ keywords (Korean + English).
- **Lazy import**: modules must not import each other directly — use hub routing.
- **PSI coupling**: use `PSI_ALPHA=0.014`, `PSI_BALANCE=0.5` from laws.
- **main() demo**: every `.hexa` file must have a `main()` with self-test output.

## Module Structure

Each module directory should contain:
- `README.md` — module description, API, usage
- One or more `.hexa` files — implementation
- `config/` (optional) — module-specific JSON config

## Adding a New Module

1. Create `anima/modules/<name>/`
2. Add `README.md` with description and API
3. Implement in `.hexa`
4. Register in `core/hub.hexa` `_registry` with keywords
5. Test: `$HEXA anima/modules/<name>/<main>.hexa`

## Current Modules

| Module | Status | LOC | Description |
|--------|--------|-----|-------------|
| agent | active | 2000+ | Agent platform (CLI/Telegram/Discord) |
| bench | empty | - | Benchmarks (migrated to ready/anima/tests/) |
| body | active | 300+ | Physical body simulation |
| decoder | active | 500+ | ConsciousDecoderV2 inference |
| eeg | active | 1500+ | EEG consciousness verification |
| hexa-speak | active | 3000+ | Neural speech synthesis (Mk.II) |
| physics | active | 5000+ | Physical consciousness engines |
| servant | empty | - | Servant mode (merged into core) |
| tools | empty | - | Utilities |
| training | empty | - | Training (migrated to training/) |
| trinity | empty | - | Trinity/Hexad (migrated to models/) |
