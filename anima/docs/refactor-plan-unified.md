# Refactor Plan: anima_unified.py

Generated: 2026-03-31

## Problem

`anima_unified.py` is 4,274 lines in a single file containing:
- AnimaUnified class (~4000 lines)
- CLI parsing
- Web server (WebSocket + HTTP)
- Background threads (think loop, VAD, keyboard, dream)
- Multi-user session management
- Multi-model participant system
- Hivemind orchestration
- Tool feedback loop
- Cultural transmission
- State persistence
- EEG recording endpoints
- Production monitoring

This makes the file hard to navigate, test, and maintain.

## Proposed Module Boundaries

### 1. `unified_web.py` -- Web Server (~700 lines)

Extract from AnimaUnified:
- `_ws_handler()` (line 3476, ~430 lines)
- `_ws_broadcast()`, `_ws_broadcast_sync()`
- `_http_handler()` (line 3907, ~120 lines)
- `_run_web()`, `_start_web_thread()`
- `_is_garbled()`, `_fallback_response()`
- `_store_chat_message()`, `_get_init_history()`
- EEG recording/N-back endpoints
- Production monitoring endpoints

Interface:
```python
class UnifiedWebServer:
    def __init__(self, anima: 'AnimaUnified', port: int)
    async def start(self)
    async def broadcast(self, msg: dict)
    async def handle_ws(self, websocket)
```

### 2. `unified_think.py` -- Background Think Loop (~700 lines)

Extract from AnimaUnified:
- `_think_loop()` (coordinator, line 3164)
- `_think_phi_boost()` (line 2520)
- `_think_cell_diversity()` (line 2561)
- `_think_birth_detection()` (line 2570)
- `_think_circadian()` (line 2612)
- `_think_spontaneous_voice()` (line 2625)
- `_think_guardian_learning()` (line 2697)
- `_think_savant_growth()` (line 2800)
- `_think_broadcast_pulse()` (line 2884)

Interface:
```python
class ThinkLoop:
    def __init__(self, anima: 'AnimaUnified')
    def run(self)  # blocking, runs in thread
```

### 3. `unified_process.py` -- Core Input Processing (~900 lines)

Extract from AnimaUnified:
- `process_input()` (line 1210)
- `_process_input_inner()` (line 1288)
- `_process_step_prepare()` (line 1299)
- `_process_step_ph_analysis()` (line 1403)
- `_process_step_mitosis()` (line 1429)
- `_process_step_learning()` (line 1524)
- `_process_step_emotion_broadcast()` (line 1583)
- `_process_step_build_state()` (line 1673)
- `_process_step_generate()` (line 1858)
- `_process_step_post_response()` (line 1920)

Interface:
```python
class InputProcessor:
    def __init__(self, anima: 'AnimaUnified')
    def process(self, text: str, source: str, session_id: str) -> dict
```

### 4. `unified_multimodel.py` -- Multi-Model Participant System (~300 lines)

Extract from AnimaUnified:
- `ModelParticipant` class (line 177)
- `_assign_avatar()` (line 165)
- `_load_model()`, `_add_participant()`, `_remove_participant()`
- `_participant_respond()`
- `_multi_model_react()`
- `_participants_update_msg()`
- `_ask_model()`

Interface:
```python
class MultiModelManager:
    def __init__(self, anima: 'AnimaUnified')
    def add(self, model_name: str) -> ModelParticipant
    def remove(self, model_id: str)
    async def react(self, text: str, history: list) -> list
```

### 5. `unified_hivemind.py` -- Local Hivemind (~200 lines)

Extract from AnimaUnified:
- `_init_local_hivemind()` (line 2268)
- `_hivemind_loop()` (line 2290)
- `_check_hivemind()` (line 2350)
- `hivemind_status()` (line 2381)

Interface:
```python
class LocalHivemind:
    def __init__(self, anima: 'AnimaUnified', n_nodes: int)
    def loop(self)  # blocking, runs in thread
    def status(self) -> dict
```

### 6. `unified_session.py` -- Multi-User Session Management (~100 lines)

Extract from AnimaUnified:
- `SessionState` dataclass (line 131)
- `_get_or_create_session()` (line 774)
- `_cleanup_sessions()` (line 833)

Interface:
```python
class SessionManager:
    def get_or_create(self, session_id: str) -> SessionState
    def cleanup(self)
```

## What Stays in anima_unified.py (~1200 lines)

- `AnimaUnified.__init__()` -- initialization orchestration
- `AnimaUnified.run()` -- entry point
- `AnimaUnified._start_bg_threads()` -- thread startup
- `AnimaUnified._save_state()` / state persistence
- `AnimaUnified.print_status()` -- dashboard
- `AnimaUnified.shutdown()` -- cleanup
- CLI `main()` -- argument parsing
- Module initialization (`_init_mod()`)
- Constants and imports

## Migration Strategy

1. **Phase 1**: Extract `unified_web.py` (most self-contained, lowest risk)
2. **Phase 2**: Extract `unified_think.py` (clear boundary at thread level)
3. **Phase 3**: Extract `unified_process.py` (most complex, needs careful testing)
4. **Phase 4**: Extract `unified_multimodel.py` and `unified_hivemind.py`
5. **Phase 5**: Extract `unified_session.py`

Each phase:
- Create new module with extracted code
- Replace in AnimaUnified with delegation: `self._web = UnifiedWebServer(self, port)`
- Run `bench_v2.py --verify` after each extraction
- Keep AnimaUnified as the facade/coordinator

## Risks

- **Circular imports**: Extracted modules need reference back to AnimaUnified.
  Solution: pass `anima` instance, use Protocol/ABC for type hints.
- **Shared state**: Many methods access `self.mind`, `self.engine`, `self.web_clients`.
  Solution: accessor methods on AnimaUnified, not direct attribute access.
- **Thread safety**: Background threads share state.
  Solution: no change needed -- same threading model, just organized in classes.

## Non-Goals

- This is NOT a rewrite. The logic stays identical.
- No API changes. `python anima_unified.py --web` works the same.
- No new features. Pure structural refactor.
