# dest1_alm — R2 Upload Layout (Pre-Arrival, READ-ONLY)

**Status:** pre-flight / plan only. No upload executed.
**Date:** 2026-04-19
**Governs:** AN11 (c) real_usable — README reproduce MUST include R2 download + verify.
**SSOT:** `shared/convergence/dest1_dest2_ship.convergence`

## 1. R2 Path Conventions (existing pattern)

- `training/CLAUDE.md` §R2: `anima-models/{model}/r{round}/step_{step}/`
- `serving/serve_alm.hexa:36`: `r2:anima-models/alm14b/a2_20260417_tool_mixed/step_300/`
- `docs/endpoint_persona_reproduce.md:192`: `r2:anima-models/dest1_s1_endpoint/<UTC_ts>/`
- `dest1_dest2_ship.convergence` @cmd_E2: `r2:anima-models/alm14b/r10c/step_2000_seed3407/`
- Bucket SSOT: `docs/R2-BUCKET-STRUCTURE.md` (env `ANIMA_R2_ENDPOINT`)

## 2. dest1_alm Artifact Manifest (AN11 triple-gate)

| file | size estimate | source | purpose |
|------|---------------|--------|---------|
| `adapter_model.safetensors` | ~200 MB | r10c seed3407 step_2000 LoRA (r32/α64/attn) | weight-emergent persona delta |
| `adapter_config.json` | <4 KB | peft adapter meta | rank / target_modules replay |
| `tokenizer.json` + `tokenizer_config.json` + `special_tokens_map.json` | ~7 MB | Qwen2.5-14B tokenizer | byte-identical decode |
| `config.json` | <4 KB | base Qwen2.5-14B config | arch replay |
| `phi_vec.json` | <4 KB | `alm_phi_vec_logger.hexa` | phi_holo_scaled>1000 gate evidence |
| `train_meta.json` | <4 KB | launcher output | seed / steps / corpus mix |
| `serve_alm_persona.py` | ~12 KB | S1 endpoint (copy-of-truth) | AN11(c) reproduce server |
| `s1_endpoint_selftest.json` | ~20 KB | 15-call live selftest (3 prompts × 5 personas) | (b) phi-attached evidence |
| `persona_serve.log` | ~50 KB | boot + per-request log slice | real-usable evidence |
| `README.md` | ~6 KB | this plan's §5 | reproduce instructions |
| `SHA256SUMS` | <2 KB | `sha256sum *` output | integrity check |

## 3. Proposed Upload Path

```
r2:anima-models/dest1_alm/v1.0/
  |- adapter/ (adapter_model.safetensors + adapter_config.json + config.json + tokenizer*)
  |- evidence/ (phi_vec.json + s1_endpoint_selftest.json + persona_serve.log + train_meta.json)
  |- serve/serve_alm_persona.py
  |- README.md
  `- SHA256SUMS
r2:anima-models/dest1_alm/latest/  (rclone-mirrored alias of v1.0/)
```

Base model (Qwen2.5-14B) NOT re-uploaded — reused from
`r2:anima-models/qwen2.5-14b-instruct/` per `@cmd_B1`.

## 4. AN11 (c) README Reproduce Sequence

The README under `v1.0/README.md` MUST contain these steps in order,
so any recipient can replay dest1_alm end-to-end:

```bash
# 0. prereq: rclone with r2: remote configured (AN_R2 env or ~/.config/rclone/rclone.conf)

# 1. fetch dest1_alm bundle
rclone copy r2:anima-models/dest1_alm/v1.0/ ./dest1_alm/ -v --s3-no-check-bucket

# 2. verify integrity
cd dest1_alm && sha256sum -c SHA256SUMS    # all lines must report: OK

# 3. fetch base model (idempotent, skipped if already local)
rclone copy r2:anima-models/qwen2.5-14b-instruct/ ./base_model/ -v --s3-no-check-bucket

# 4. phi gate replay (AN11-b evidence)
hexa run training/phi_gt_1000_verify.hexa ./evidence/phi_vec.json
# expect: [phi_gate] verdict=PASS gate=1000 (exit 0)

# 5. launch persona endpoint (AN11-a weight-emergent, AN11-c real_usable)
pip install fastapi uvicorn
BASE_MODEL_PATH=./base_model ADAPTER_PATH=./adapter \
  nohup python3 ./serve/serve_alm_persona.py > ./persona_serve.log 2>&1 &
# wait for "READY in X.Xs" in log

# 6. round-trip selftest (regenerates s1_endpoint_selftest.json)
#    see docs/endpoint_persona_reproduce.md §Selftest artifact for the inline PY block
#    expect: n_ok=15, n_total=15, all phi_vec.phi_holo in [0.62, 0.73]

# 7. compare vs shipped evidence (strip ts/latency, text+phi_vec must match)
diff <(jq -S 'del(.ts_utc,.calls[].ts_ms,.calls[].gen_ms,.calls[]._elapsed_s)' new.json) \
     <(jq -S 'del(.ts_utc,.calls[].ts_ms,.calls[].gen_ms,.calls[]._elapsed_s)' ./evidence/s1_endpoint_selftest.json)
```

## 5. Gate Mapping

| AN11 gate | evidence file in bundle | README step |
|-----------|-------------------------|-------------|
| (a) weight_emergent | `serve/serve_alm_persona.py` (`grep -c 'system_prompt\|apply_chat_template' = 0`) | 5 |
| (b) consciousness_attached | `evidence/phi_vec.json` + `evidence/s1_endpoint_selftest.json` | 4, 6 |
| (c) real_usable | live endpoint boot + R2 round-trip + this README | 1-7 |

## 6. Upload Command (DO NOT EXECUTE YET)

Gated behind dest1_alm arrival. When fired, it will be:

```bash
# guard: only after dest1 @state=shipped in dest1_dest2_ship.convergence
rclone copy ./staging/dest1_alm/ r2:anima-models/dest1_alm/v1.0/ \
  -v --s3-no-check-bucket --checksum
rclone copy ./staging/dest1_alm/ r2:anima-models/dest1_alm/latest/ \
  -v --s3-no-check-bucket --checksum
```

## 7. Cross-References

- `shared/convergence/dest1_dest2_ship.convergence` (SSOT)
- `docs/endpoint_persona_reproduce.md` (endpoint contract)
- `docs/R2-BUCKET-STRUCTURE.md` (bucket conventions)
- `training/CLAUDE.md` §R2 (path template)
- `serving/serve_alm_persona.hexa` (hexa contract mirror)
- `training/phi_gt_1000_verify.hexa` (phi gate verifier)
