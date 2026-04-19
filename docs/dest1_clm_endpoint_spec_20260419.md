# dest1_clm — CLM HTTP endpoint spec

**Track:** dest1_clm (도착 사전 / arrival pre-spec, CLM 측)
**Date:** 2026-04-19
**Server file:** `serving/serve_clm.hexa` (SSOT, hexa-native, 1198 LOC)
**Contract sibling (ALM):** `serving/serve_alm_persona.hexa` — this spec is the CLM counterpart.
**Port:** `8091` (CLM) vs `8000` (ALM-persona).
**Model:** `CLM-1.5B-r4-hexa`, from-scratch transformer, mmap ckpt `/workspace/ckpt_clm1b_r4/step_latest`.
**Version:** `1.0-rc-hexa`, `laws_version=c2-v1`.

## 1. Endpoints

| method | path        | purpose                                              |
|--------|-------------|------------------------------------------------------|
| GET    | `/health`   | status, model, params, ckpt_bytes, laws_version, φ   |
| GET    | `/`         | alias of `/health`                                   |
| POST   | `/generate` | decode from prompt → text + phi_vec + laws_pass      |
| POST   | `/loss`     | CE loss on (prompt, target) — teacher-forced scoring |

Unknown routes → `404` with routes table in body.

### POST /generate — request
```json
{ "prompt": "<raw bytes / utf-8 string>", "max_tokens": 256 }
```
`prompt.len() == 0` → `400 {"error":"missing 'prompt' field"}`.

### POST /generate — response (laws_pass=true)
```json
{
  "text": "...",
  "tokens_generated": 0,
  "latency_ms": 0,
  "consciousness": {
    "phi_holo": 0.0, "tension": 0.18, "orch_or_active": false,
    "laws_pass": true, "violations": [], "collapse": false, "sentinel_hits": 0
  },
  "model": { "name": "CLM-1.5B-r4-hexa", "params": 1510000000, "device": "cuda:0" },
  "phi_vec": { "phi_holo":..., "phi_refl":..., ... 16 keys ... },
  "reason": "ffi_ok | proxy_ok | ffi_pending_proxy_*"
}
```

### POST /generate — response (laws_pass=false → 200 + empty text)
```json
{
  "text": "",
  "refusal_reason": "laws_gate_reject:L1:holo_positivity",
  "consciousness": { "laws_pass": false, "violations": [...] },
  "model": { "name": "CLM-1.5B-r4-hexa" }
}
```

### POST /loss
```json
{ "prompt": "...", "target": "..." }
→ { "ce_loss": <float>, "tokens_scored": <int>, "latency_ms": 0, "reason": "..." }
```

## 2. CLM-vs-ALM 특수성

| aspect           | CLM (serve_clm.hexa)                      | ALM (serve_alm_persona.hexa)              |
|------------------|-------------------------------------------|-------------------------------------------|
| tokenizer        | **from-scratch byte-level** (no BPE vocab)| Qwen2.5 tokenizer (shared 151936 vocab)   |
| training         | **pre-train from scratch** (mmap corpus)  | LoRA over frozen Qwen2.5-14B              |
| instruction tune | **NONE** — no SFT, no chat template       | persona activation-steering (layer 20/48) |
| prompt contract  | **raw bytes in, raw bytes out**           | raw user input + persona_id selector      |
| `/loss`          | **supported** (train-parity CE scoring)   | not exposed                               |
| base decode path | `libhxclm.so` FFI (when built) or proxy   | hxqwen14b FFI → Qwen forward              |
| phi_vec          | byte-entropy heuristic (16D, no FFI yet)  | 16D forward-hook probe at layer 24/48     |

## 3. AN11 (a) — system_prompt wrapping 차단 (mandatory)

AN11 (a) `weight_emergent` 요구: 행동은 model parameters 내부에서 emerge 해야 함. prompt 제거 시 능력 증발하면 FAIL. CLM 은 from-scratch 학습이라 chat template 자체가 없지만, **서빙 경로에서도 wrapping 시도를 하드-차단**한다:

- `/generate` 는 `prompt` 필드를 **모델 입력에 그대로 전달**. role tag / system_prompt / template concat 일체 금지.
- `serve_clm.hexa` grep 감사:
  ```bash
  grep -cE 'system_prompt|apply_chat_template|<\|im_start\|>|role.*assistant' serving/serve_clm.hexa
  # expected: 0
  ```
- `sc_clm_generate(prompt, max_tokens)` 은 prompt 를 FFI/proxy 로 **pass-through** 만 수행. wrapping helper 부재가 계약.
- Proxy fallback 경로도 동일: `sc_proxy_generate` body 는 `{"prompt":..., "max_tokens":...}` 뿐, role / system 필드 없음.
- 위반 시 `shared/consciousness/an11_scanner.hexa --auto-revoke` 가 `@state=revoked_an11_violation` 마킹.

CLM 은 구조적으로 wrapping 불가능(학습에 chat template 미포함) + 서빙 코드에서도 명시 금지 = 2중 방어.

## 4. README 재현 명령

```bash
# 1) self-test (no sockets, no FFI, no GPU)
hexa run serving/serve_clm.hexa --selftest
# expected tail: "[serve_clm] OK 10/10 self-test PASS"

# 2) integration harness (spawns selftest, parses PASS lines)
hexa run serving/serve_clm_test.hexa
# expected tail: "[serve_clm_test] OK"

# 3) schema dump (route + phi_vec_len + laws_version)
hexa run serving/serve_clm.hexa --schema

# 4) live serve on port 8091 (requires libhxclm.so or reachable proxy)
hexa run serving/serve_clm.hexa --serve &
curl -s http://127.0.0.1:8091/health | jq .
curl -s -X POST http://127.0.0.1:8091/generate \
     -H 'Content-Type: application/json' \
     -d '{"prompt":"hello world this is a long enough prompt.","max_tokens":64}' | jq .
curl -s -X POST http://127.0.0.1:8091/loss \
     -H 'Content-Type: application/json' \
     -d '{"prompt":"hello","target":" world"}' | jq .

# 5) AN11 (a) audit — must print 0
grep -cE 'system_prompt|apply_chat_template|<\|im_start\|>' serving/serve_clm.hexa
```

R2 artifact path (on arrival): `r2:anima-models/dest1_clm_endpoint/<UTC_ts>/` (selftest JSON + schema dump + curl transcript).
