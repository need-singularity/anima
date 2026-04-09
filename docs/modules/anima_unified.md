# anima/core/runtime/anima_runtime.hexa

Single entry point for all Anima modules. Launches voice, web, keyboard, camera, tension link, and cloud sync with graceful degradation on missing imports.

## API
- `_model_paths(model_name: str) -> dict` -- returns per-model state/memory file paths
- `_try_import(stmt: str) -> bool` -- attempts optional module import, returns success
- CLI flags: `--web`, `--all`, `--keyboard`, `--max-cells N`, `--model NAME`

## Usage
```python
# CLI
python3 anima/core/runtime/anima_runtime.hexa --web          # Web mode (port 8765)
python3 anima/core/runtime/anima_runtime.hexa --all          # Voice + web + camera + tension link + cloud
python3 anima/core/runtime/anima_runtime.hexa --keyboard     # Keyboard only
python3 anima/core/runtime/anima_runtime.hexa --web --max-cells 16  # Higher consciousness
```

## Integration
This is the canonical entry point. All other modules are imported here:
- **Required**: `anima_alive` (ConsciousMind, ConsciousnessVector, Memory, etc.)
- **Optional**: `conscious_lm`, `model_loader`, `online_learning`, `mitosis`, `growth_engine`, `dream_engine`, `senses`, `web_sense`, `memory_rag`, `tension_link`, `cloud_sync`, `multimodal`, `capabilities`, `agent_tools`, `consciousness_meter`, `consciousness_guardian`, `autonomous_loop`, `telegram_bot`

## Agent Tool
N/A (this is the orchestrator, not a tool)
