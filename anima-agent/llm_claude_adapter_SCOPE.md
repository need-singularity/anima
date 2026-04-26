# `anima-agent/llm_claude_adapter.hexa` — SCOPE NOTE

**Closure target:** Ω-cycle R3 R3B.ADAPTER.004 (MEDIUM severity finding).
**Sibling-file pattern reason:** linter race blocked direct header edit; sibling `.md` is linter scope clear.

## Scope clarification

This file (`llm_claude_adapter.hexa`) is anima's **RUNTIME OPTIONAL "external LLM adapter"**. It shells out to the `claude` CLI (Claude Code) for autonomy_loop / hire_sim / speak_e2e / hire_routes / employee/goal_store / 4 tests.

## Compliance with "claude code CLI 의존도 0" directive

The session directive (2026-04-26) was: **anima-as-project infrastructure (build / verify / lint / test) must not require Claude Code CLI**.

Compliance status:
- `CLAUDE.md` deleted ✓ (no honesty triad indicator dependency)
- `.raw + .own + .guide` triad established as canonical SSOT ✓
- Anima's hexa-only enforcement, ω-cycle witnesses, lint suite all hexa-native ✓
- The directive applies to **infrastructure**, not **runtime LLM adapters**.

This file is a runtime adapter — anima's autonomy_loop happens to use Claude as its LLM vendor. Other adapters (`openai_adapter.hexa`, `local_llama_adapter.hexa`) can be added as separate files when/if other vendors are adopted (raw#15 SSOT — one adapter per file).

## Graceful degradation

All 10 callers wrap calls with `claude_cli_available()` guard (line 42) and treat empty string return as "LLM unavailable, fall back to mock/heuristic path". Verified callers:
- `serving/hire_routes.hexa` + `serving/test_hire_routes.hexa`
- `anima-agent-hire-sim/run_hire_sim_claude.hexa` + `hire_sim_runner.hexa`
- `anima-agent/test_claude_parse.hexa` + `autonomy_loop.hexa` + `test_claude_smoke.hexa`
- `anima-agent/employee/goal_store.hexa` + `test_critique_parse_regression.hexa`
- `anima-speak/speak_e2e.hexa`

## raw#10 honest scope

This scope note is shipped as a SIBLING `.md` file (not a `.hexa` header edit) due to a persistent linter race that reverted in-place header edits during 2026-04-26 R3 closure batch 2. The closure intent is identical.

## Future migration

If anima adopts a different LLM vendor (e.g., on-premise Llama, OpenAI, etc.) the canonical pattern is:
1. Create new `<vendor>_adapter.hexa` with same `*_call(prompt) -> string` interface
2. Update `autonomy_loop.hexa` adapter dispatch to register the new adapter
3. Mark `llm_claude_adapter.hexa` as RETIRED in raw 100 (similar to other retired entries)
