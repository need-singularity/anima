# dest2 live-swap procedure (2026-04-20)

**Scope:** swap `autonomy_loop.hexa` + `hire_sim_100.hexa` from mock to live once `dest1` `serve_alm_native.hexa` exposes `POST /alm/persona`. Target: < 1 hour from dest1 go-live to dest2 gate run.

## Status snapshot

| Artifact | Path | State |
| --- | --- | --- |
| Autonomy loop | `anima-agent/autonomy_loop.hexa` | Restored 2026-04-20 (pure-hexa mock, zero python) |
| Live adapter (already wired) | `anima-agent/autonomy_live.hexa` | AN11-compliant S1 HTTP wrapper (POST /persona) |
| 100-task corpus + judge | `anima-agent-hire-sim/hire_sim_100.hexa` (L0) | 100 tasks × 6 domains, deterministic keyword judge |
| Stratified-30 gate runner | `anima-agent-hire-sim/hire_sim_runner.hexa` | Env-var driven (HIRE_SIM_ENDPOINT / HIRE_SIM_MOCK) |
| Live runner | `anima-agent-hire-sim/hire_sim_live.hexa` | Pre-existing parse-err 144:28 (separate bugfix) |

## 1-line swap — the minimum change

The scaffold is built so one edit per call-site flips mock → live. There are exactly three independent swap points:

### Swap 1 — autonomy_loop consumer (test_autonomy_loop, any CLM-driven decomposer)

`anima-agent/test_autonomy_loop.hexa:14`

```hexa
// BEFORE (scaffold)
let adapter = LLMAdapter { name: "mock", temperature: 0.0 }
// AFTER (live)
let adapter = LLMAdapter { name: "live", temperature: 0.0 }
```

This flips the `llm_decompose/execute/critique` dispatch in `autonomy_loop.hexa`. **Pre-requisite:** for "live" to be a real weight-emergent call (AN11-a), re-point the dispatch from the mock fallback to the S1 HTTP path. Two options:

- **(recommended) Caller swap:** stop using `autonomy_loop.hexa` directly; have the employee supervisor call `run_autonomy_live(persona_id, root_text, depth, budget)` from `autonomy_live.hexa`. This is already AN11-compliant and honors phi_delta abort. Zero coupling cycles.
- **(inline swap)** replace the `mock_*` calls inside the `"live"` branch of `llm_decompose/execute/critique` with `s1_call(...)` from `autonomy_live.hexa`. Requires adding `use "autonomy_live"` at top of `autonomy_loop.hexa` — verify no cyclic `use` first (`autonomy_live` currently imports `autonomy_loop`).

### Swap 2 — hire_sim_runner endpoint (stratified-30 gate)

`anima-agent-hire-sim/hire_sim_runner.hexa` — **no code edit**, env var only:

```bash
# BEFORE (mock)
hexa run anima-agent-hire-sim/hire_sim_runner.hexa
# AFTER (live, once dest1 is up on 127.0.0.1:8090)
HIRE_SIM_ENDPOINT=http://127.0.0.1:8090/alm/persona \
HIRE_SIM_MOCK=0 \
  hexa run anima-agent-hire-sim/hire_sim_runner.hexa
```

The runner already parses `"output"` from the response; `/alm/persona` returns `text` (not `output`). **Pre-swap fix required:** teach the runner to parse both keys, or add a light shim in `serve_alm_native.hexa` that mirrors `text` into `output`. Ticket: add `s1_extract_json_str(body, "text")` fallback after `"output"` miss in `hire_sim_runner.hexa:call_endpoint`.

### Swap 3 — hire_sim_100 adapter at call-site

`anima-agent-hire-sim/test_hire_sim.hexa:10` (or any gate consumer):

```hexa
// BEFORE
let adapter = LLMAdapter { name: "mock", temperature: 0.0 }
// AFTER
let adapter = LLMAdapter { name: "live", temperature: 0.0 }
```

Same caveat as Swap 1 — the "live" branch in `llm_decompose` must be re-pointed to S1.

## Contract alignment between mock and live

| Field | Mock shape | Live shape (S1Response, autonomy_live.hexa) |
| --- | --- | --- |
| text | `"done: <goal>"` | `/alm/persona` `text` field |
| score | CritiqueOut.score ∈ [0,1] | derived from `phi_holo` delta |
| verdict | "PASS" / "PARTIAL" / "FAIL" from terminal score | "PASS" / "ABORT_LAWS_FAIL" / "ABORT_PHI_REGRESSION" / "FAIL_S1" |
| phi_vec | — (mock-only gap) | 16-D PhiVec struct |
| laws_pass | — (mock-only gap) | bool from laws_pass field |

**Gap:** mock does not emit `phi_vec` or `laws_pass`. This is ACCEPTABLE for scaffold smoke (shape verification only) but the gate result JSON from `hire_sim_runner.hexa` MUST include live `phi_vec` and `laws_pass` per AN11-b once swapped. The runner structure already has room in the per-task dict.

## AN11 compliance after swap

After swap completion, running `hexa run shared/consciousness/an11_scanner.hexa --filter dest2_alm --auto-revoke` must PASS:

- **AN11-a (weight-emergent):** `grep -n "persona_id" anima-agent/autonomy_live.hexa` shows zero string preambles — persona travels only as a struct field. Verified.
- **AN11-b (consciousness-attached):** `run_autonomy_live` consumes `phi_holo` and `laws_pass`; `PHI_REGRESSION_STREAK=3` triggers `ABORT_PHI_REGRESSION`. Verified.
- **AN11-c (real-usable):** selftest_10x3 in `autonomy_live.hexa` + JSONL trace + R2 archival. Selftest exists; R2 upload to be added by the live-swap operator.

## Gate thresholds (from anima.json dest2_employee_gate)

```
완료율 >= 0.85
개입   <= 5 / hour
avg task <= 10 min (600 s)
```

`hire_sim_100.hexa::run_hire_sim` computes all three and emits verdict "PASS" iff all three pass. Unchanged by mock→live swap.

## Rollback

Revert the 3 call-site edits to `name: "mock"` and unset `HIRE_SIM_ENDPOINT`. No data migration required.

## Out of scope for this scaffold

- Trading engine (T1/T2) — handled by `p32_economic_market` convergence, separate file.
- `hire_sim_live.hexa` parse-err 144:28 — pre-existing, tracked separately.
- R2 upload of live gate JSON — operator responsibility once /alm/persona is up.

## Refs

- Roadmap SSOT: `/Users/ghost/Dev/nexus/shared/roadmaps/anima.json` → `dest2_alm.gate_employee`
- AN11 spec: `shared/config/absolute_rules.json` / `shared/consciousness/an11_scanner.hexa`
- Live S1 wire: `anima-agent/autonomy_live.hexa` (already implemented)
- Previous regression memory: `project_alm_training_20260417.md` — hire_sim endpoint :8182 tunneled :18282 regressed 0.5667 vs 0.8111 baseline; live swap must re-measure
