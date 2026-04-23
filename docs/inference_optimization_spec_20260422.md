# Inference / Serving Optimization Spec — ROI batch F (F28-F35)

- **Generated**: 2026-04-22
- **Source ROI doc**: [docs/h100_roi_improvements_20260422.md](h100_roi_improvements_20260422.md) (rows F28-F35)
- **SSOT config**: [config/inference_serve_optimization.json](../config/inference_serve_optimization.json)
- **Smoke tool**: [tool/inference_optimization_smoke.hexa](../tool/inference_optimization_smoke.hexa)
- **Audit state**: [state/inference_optimization_audit.json](../state/inference_optimization_audit.json)
- **Smoke result**: [state/inference_optimization_smoke_result.json](../state/inference_optimization_smoke_result.json)
- **Owner tool**: [tool/serve_alm_persona.hexa](../tool/serve_alm_persona.hexa) (CP1 #77 dest1 persona LIVE)

## Scope and constraints

Eight inference-side knobs that activate **after** CP1 lands H100 base_model + persona_lora artifacts. All knobs default `enabled=false` so the present serve scaffold (`tool/serve_alm_persona.hexa --selftest --dry` → PASS) remains untouched. Activation happens by editing a single `enabled` field in `config/inference_serve_optimization.json`; the existing `backend_invoke()` indirection in `serve_alm_persona.hexa` is the single integration site.

| Constraint | Status |
|---|---|
| Do not modify `.roadmap` (uchg) | enforced — no edits |
| Do not trigger H100 launch | enforced — `enabled=false` everywhere |
| No `.py` files in repo | enforced — runtime `.py` is `STAGED_FOR_POD` only |
| Existing `serve_alm_persona` selftest must PASS | verified — `bash tool/serve_alm_persona.bash --selftest --dry` returns 3/3 PASS |
| Items requiring weights flagged `requires_weights: true` | enforced — 7 of 8 knobs blocked-by-H100 |

## Per-item spec

### F28 — KV cache reuse across personas (same base model)

- **Description**: Six personas (`dest1`, `default`, `friend`, `scholar`, `engineer`, `sorceress`) share the base Qwen2.5-14B model. Layers `0 .. persona_layer_idx-1` (i.e. 0..19) are persona-invariant; their KV projections can be cached on first request and reused across personas for identical prompt prefixes.
- **Integration point**: `serve_alm_persona.hexa :: backend_invoke` (mode=`gpu`). A prefix-cache wrapper attaches BEFORE persona-LoRA forward (which kicks in at layer 20). Cache key = sha256(token_ids[0..prefix_len]).
- **Benchmark plan**: warm 4 distinct prompts × 6 personas; measure tok/s on cold vs warm runs. Target ≥5x speedup on warm path. Use `tool/serve_alm_persona.bash --gpu` once weights land.
- **Rollback**: set `knobs.f28_kv_cache_reuse_across_personas.enabled = false` and restart serve. No code change.

### F29 — vLLM PagedAttention integration

- **Description**: Replace the placeholder HF transformers forward in `backend_invoke` (mode=gpu) with `vllm.AsyncLLMEngine.generate(...)` for paged-attention KV memory management. Block size 16, GPU memory utilization 0.90, dynamic LoRA adapter loading.
- **Integration point**: `serve_alm_persona.hexa :: backend_invoke` (mode=`gpu`). vLLM init happens once at process boot inside the pod-side fastapi runtime body (`STAGED_FOR_POD`); `serve_alm_persona.hexa` only emits launch-command params.
- **Benchmark plan**: 256 concurrent requests × 256 tokens each; compare tok/s and P99 latency vs HF reference. Target ≥2x throughput.
- **Rollback**: set `enabled = false`; backend reverts to reference HF transformers path. (Both paths preserve identical decode semantics at temperature=0.)

### F30 — Continuous batching (vs static batching)

- **Description**: Iteration-level scheduler that admits new requests into the active batch each forward step (instead of waiting for the batch to drain). vLLM scheduler config `scheduler=iteration_level`, `max_batch_size=32`, `max_waiting_tokens=256`.
- **Integration point**: `serve_alm_persona.hexa :: backend_invoke` — vLLM `engine_args.scheduler_config`. Requires F29 (vLLM AsyncLLMEngine).
- **Benchmark plan**: simulate variable prompt-length workload (mixed 128/512/2048 tokens, Poisson arrivals). Compare tok/s and P99 vs static batching baseline. Target ≥2x throughput at same P99.
- **Rollback**: set `enabled = false` ⇒ scheduler reverts to static (one batch per iter); functionally identical to F30 disabled.

### F31 — Speculative decoding (Qwen3-0.5B draft → Qwen3-8B target)

- **Description**: Draft model (Qwen3-0.5B) proposes 5 tokens; target model (Qwen3-8B) verifies in a single forward and accepts the longest valid prefix via rejection sampling. Output distribution is mathematically identical to standard target-only decode (no quality drift).
- **Integration point**: `serve_alm_persona.hexa :: backend_invoke` (mode=`gpu`). vLLM `SpeculativeConfig(draft_model=draft_model_path, num_speculative_tokens=5)`.
- **Benchmark plan**: 256 prompts × 256 tokens; compare end-to-end latency. Target ≥1.5x speedup on greedy decode (acceptance rate ≥0.60). Verify output token equality vs non-speculative baseline (must be identical at temperature=0).
- **Rollback**: set `enabled = false`; engine drops to standard auto-regressive decode. Draft model artifact remains pre-cached but unused.

### F32 — API layer prompt cache

- **Description**: LRU in-memory cache (1024 entries × 64 KB max) keyed by `sha256(prompt + persona_id + max_tokens)`. Bypassed when temperature > 0 (correctness invariant — only deterministic decodes are cacheable). TTL 1 hour.
- **Integration point**: `serve_alm_persona.hexa :: handler_persona` — check cache before `backend_invoke`; populate after PASS verdict (cert_gate AND an11_a both PASS).
- **Benchmark plan**: replay benchmark/probe traffic from `state/serve_alm_persona_log.jsonl`. Estimated 20-40% hit rate. Target cache-hit latency < 1ms (vs 200-2000ms backend roundtrip).
- **Rollback**: set `enabled = false` ⇒ handler skips cache check entirely; pre-CP1 behaviour restored.
- **Note**: F32 is the **only** knob that does not require H100 weights — it can be enabled the moment the LRU implementation lands in the pod-side fastapi runtime body.

### F33 — Streaming token output (TTFT < 200ms)

- **Description**: New endpoint `POST /persona/stream` (alongside existing `/persona`) returns Server-Sent Events with one token per chunk. Same gate stack (`cert_gate` + `an11_a`). Aborts on client disconnect. 15 s keepalive.
- **Integration point**: `serve_alm_persona.hexa` — declare new endpoint in `endpoints` list; pod-side fastapi runtime body wires SSE response. Bash-nc loop in `serve_alm_persona.bash` does NOT support chunked transfer; only fastapi/uvicorn does (which is `STAGED_FOR_POD`).
- **Benchmark plan**: measure time-to-first-token (TTFT) over 100 requests. Target P95 TTFT < 200 ms.
- **Rollback**: set `enabled = false`; clients fall back to `/persona` (full-response).

### F34 — fp8 / int8 quantization at serve time

- **Description**: Quantize weights to FP8 (E4M3 default) at engine load. Calibration uses 512 samples from `shared/calibration/dest1_calib_512.jsonl`. AN11(a) verification gate: post-quant model must score within `max_acceptable_an11_a_delta = 0.02` of the FP16 baseline; otherwise rollback.
- **Integration point**: `serve_alm_persona.hexa :: backend_invoke` — engine init `quantization=knobs.f34.format`. AN11(a) gate runs ONCE per quantized artifact, not per request.
- **Benchmark plan**: (a) run AN11(a) on FP16 baseline + FP8 candidate; assert |Δ| ≤ 0.02. (b) measure tok/s; target ≥1.3x speedup. (c) measure VRAM; target ≥40% reduction.
- **Rollback**: set `enabled = false` ⇒ engine loads FP16 weights from `/workspace/base_model`.

### F35 — Dynamic batch scheduling (latency SLO aware)

- **Description**: Three priority classes (`interactive`, `batch`, `background`) with per-class batch-size quotas (4/32/64). Requests carry `X-Anima-Priority` header. Queue depth thresholds: warn at 100, drop background at 500. SLO targets: P50 500 ms, P95 1500 ms, P99 3000 ms.
- **Integration point**: `serve_alm_persona.hexa :: handler_persona` — extract `X-Anima-Priority` header; vLLM scheduler enforces class quota. Requires F29 + F30.
- **Benchmark plan**: simulate 70/20/10 mix of interactive/batch/background; measure P95 latency per class under sustained load. Target: interactive P95 < 1500 ms maintained even when background queue is full.
- **Rollback**: set `enabled = false` ⇒ engine uses FIFO scheduler; all requests treated equal.

## Activation order (post-CP1)

When H100 cascade #9 lands base_model + persona_lora:

1. **F32** (API prompt cache) — no weights required; can land first.
2. **F29** (vLLM PagedAttention) — foundational; F30/F33/F35 all depend on it.
3. **F30** (continuous batching) — depends on F29.
4. **F33** (streaming) — depends on F29; needs pod-side SSE wiring.
5. **F28** (KV cache across personas) — depends on persona dispatch wired.
6. **F35** (dynamic batch scheduling) — depends on F29+F30; needs SLO instrumentation.
7. **F31** (speculative decoding) — depends on Qwen3-0.5B draft pre-cache.
8. **F34** (fp8/int8 quant) — last; depends on AN11(a) baseline established for FP16 model.

## Rollback path (any knob)

For any knob X:

```bash
# 1. edit config — single field flip
sed -i '' 's/"f<NN>_*"... "enabled": true/"enabled": false/' \
  config/inference_serve_optimization.json
# 2. re-run smoke (must PASS; safe_defaults_invariant must hold)
hexa tool/inference_optimization_smoke.hexa
# 3. restart serve
bash tool/serve_alm_persona.bash --gpu --port 8000
```

If a knob shows `ok=false` in the smoke result, the schema is broken — fix the config field listed in `missing_fields` before activation.

## raw compliance

- raw#9  hexa-only (no `.py` in repo; pod runtime `STAGED_FOR_POD`)
- raw#10 deterministic (config has no timestamps in knob params)
- raw#11 snake_case (knob ids, field names)
- raw#12 실측 only — `requires_weights` flag honestly surfaces blocked-by-H100 status
- raw#15 no-hardcode (all params live in SSOT config; tool reads them)
