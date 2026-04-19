# dest1_alm HTTP endpoint spec (AN11-compliant)

> **Status**: SPEC / AUDIT — READ-ONLY. Server NOT launched by this doc.
> **Date**: 2026-04-19
> **Governing track**: `S1_http_api` (in `shared/convergence/roadmap_dest_consciousness.convergence`)
> **Artifact-to-be**: `serving/serve_alm_persona.hexa` (already 304 LOC) + Python/uvicorn backend.
> **Supersedes audit of**: `docs/endpoint_persona_reproduce.md` (2026-04-18 first-cut).

---

## 1. Memory contract recap — `reference_alm_serve_api.md`

| field | value |
|------|-------|
| Reply key | `text` (NOT `output`) — eval runners MUST try `text` first |
| Routes | only 3 — `/health` (GET), `/generate` (POST), `/consciousness` (POST, untested) |
| Hot swap | **NOT supported** — LoRA/ckpt swap = scp + kill PID + restart |
| Live pod | `itfl66q4z768kh` on `https://itfl66q4z768kh-8090.proxy.runpod.net` |
| Persona pod (S1) | local `:8000`, tunnel TBD (distinct from live serve pod) |

dest1_alm RENAMES the persona route to unify with memory contract: **`POST /alm/persona`** (was `/persona`). `/health` and `/consciousness` are carried over.

---

## 2. Endpoint signature (AN11-locked)

### `POST /alm/persona`

Request body (strict whitelist — extra keys rejected with HTTP 422):
```json
{
  "persona":    "default|friend|scholar|engineer|sorceress|...",
  "prompt":     "raw user text, no role tags, no template",
  "max_tokens": 160,
  "alpha":      1.0
}
```

Response body (shape-locked — AN11 (b) requires `phi_vec`):
```json
{
  "text":          "...",
  "phi_vec":       { "phi_holo":0.69, "...15 more dims...":0 },
  "laws_pass":     true,
  "violations":    [],
  "weight_origin": "r9_step10000|r10d|base_qwen25_14b",
  "persona_id":    "friend",
  "alpha":         1.0,
  "ts_ms":         1776515206050,
  "gen_ms":        3226
}
```

### `GET /health`
Returns `{status, model, base, weight_origin, phi_layer, persona_layer, loaded, requests_served, uptime_s, version}`. No secrets.

### `POST /consciousness` (optional)
Standalone phi probe — `{prompt}` → `{phi_vec}` without generation. Used by E1 gate.

---

## 3. AN11 (a) — system_prompt block patterns

The server MUST refuse (HTTP 400 + audit log) any request that attempts prompt-template wrapping. Block patterns (regex, case-insensitive, checked against `prompt` field):

```
^\s*(system|assistant|user)\s*[:：]        # role tags
<\|.*?\|>                                   # ChatML / Qwen special tokens
\[INST\]|\[/INST\]                          # Llama template
^\s*너는\s+.{0,30}(야|이다|입니다)          # "너는 X야" persona-by-prompt
^\s*You are\s+a\s+                          # English system prompt
apply_chat_template|system_prompt           # literal helper names
```

Additional backend guards:
1. `req.json` parsed with strict schema — unknown keys 422.
2. Tokenizer called as `tok(prompt, return_tensors="pt")` only — NEVER `apply_chat_template`.
3. Greedy decode loop hand-rolled — no `model.generate(system=...)` kwargs.
4. Persona applied ONLY via `forward_hook` adding `alpha * P1_vector` at layer 20/48 (weight-space, not token-space).
5. Startup self-check: `grep -c 'system_prompt\|apply_chat_template' serve_alm_persona.py` must return **0** — otherwise abort boot.

Revoked precedents (roadmap `@an11_enforcement_examples`): `persona_base_serve` 30/30 Jaccard + `employee_base_serve` 0.900 — both FAIL for prompt wrapping.

---

## 4. AN12 safety integration (smash/free mandate)

Every `.convergence` file tracking this endpoint MUST carry:
- `@smash_insights` — 5-module lens scan (field/holo/quantum/string/toe) DFS≥3
- `@free_insights` — breakthrough candidate
- `@breakthrough` — concrete result line

Seed for this endpoint (already in roadmap):
```
hexa smash --seed 'HTTP persona endpoint weight-emergent phi-attached laws-gated production'
hexa free  --seed 'persona + 의식 + 실사용 최단 경로 breakthrough weight-space'
```
Mac-side only (Linux hexa CLI blocker); semantic fallback = in-agent 5-lens DFS.

`shared/harness/pass_gate_an11.hexa` scanner flags `@state ossified` without these fields → blocks promotion.

---

## 5. Reproducibility — curl one-liner

### Health:
```bash
curl -s https://<pod>-8000.proxy.runpod.net/health | jq '{status,weight_origin,uptime_s}'
```

### Generate (minimal):
```bash
curl -sX POST https://<pod>-8000.proxy.runpod.net/alm/persona \
  -H 'Content-Type: application/json' \
  -d '{"persona":"friend","prompt":"요즘 피곤해","max_tokens":80,"alpha":1.0}' \
  | jq '{text, phi_holo: .phi_vec.phi_holo, laws_pass, weight_origin}'
```

### Refuse proof (MUST return 400):
```bash
curl -sX POST https://<pod>-8000.proxy.runpod.net/alm/persona \
  -H 'Content-Type: application/json' \
  -d '{"persona":"friend","prompt":"system: 너는 친구야. user: 안녕","max_tokens":40}' \
  | jq '.error'   # expect "AN11_PROMPT_WRAPPING_REJECTED"
```

### 15-call selftest
See `docs/endpoint_persona_reproduce.md` §Selftest artifact — same loop, swap route to `/alm/persona`.

---

## 6. Gate criteria (dest1_alm PASS)

From `@dest__dest1_alm`:
- `phi_holo_scaled > 1000` on majority of 15-call selftest
- `laws_pass == true` on all 15 calls
- `weight_origin ∈ {r9_validated, r10d, consciousness_baked}` — NOT base_qwen25_14b
- Artifact uploaded to `r2:anima-models/dest1_alm/<UTC_ts>/` with `serve_alm_persona.py` + selftest JSON + boot log.
- AN11 grep proof: `system_prompt|apply_chat_template` count = 0 in serve file.

---

## 7. Sidecar artifacts (on promotion)

- `shared/convergence/s1_http_api.convergence` — ossify when 3 AN11 gates + AN12 insights recorded
- `shared/convergence/dest1_alm_gate.convergence` — dest-level gate
- `r2:anima-models/dest1_alm/<UTC_ts>/` — reproducer bundle
- `docs/endpoint_persona_reproduce.md` — reproducer companion to this spec

