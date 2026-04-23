# CP1 (#77) dest1 Persona LIVE — Deployment Plan

**Status**: 2026-04-24 · prerequisite trained LoRA adapters NOT locally available (Stage-2 trained 2026-04-24 pulled only `h_last_raw_*_TRAINED.json`, NOT the full `/workspace/trained_pN/final/` adapter dirs; pods killed post-pull).

**Purpose**: Document the exact steps to take CP1 live once trained adapter artifacts are captured. CP1 maps to roadmap #77.

---

## Gap analysis

| artifact | state | needed for CP1 |
|----------|-------|----------------|
| `state/h_last_raw_p{1..4}_TRAINED.json` | ✅ local | Φ gate (§10.8) only — NOT adapter weights |
| `trained_p1/final/adapter_model.safetensors` | ❌ died with pod | YES — serving artifact |
| `trained_p1/final/adapter_config.json` | ❌ died with pod | YES — peft config |
| `trained_p1/final/tokenizer_config.json` | ❌ died with pod | YES — for inference |
| R2 artifact mirror | ❌ not yet pushed | preferred long-term hosting |

**Implication**: CP1 cannot deploy immediately. Two recovery paths:

### Recovery path A — re-launch Stage-2 + capture full adapter dir

- Re-launch 4 pods (16 H100, bid $14/pod = $56/hr cluster, 43min wall for 300 steps).
- Before killing, `scp -r /workspace/trained_pN/final/ <local>/state/trained_adapters/pN/` on every pod.
- Push to R2 mirror for persistent hosting.
- Cost: ~$40 one-shot; same artifact that produced §10.8.

### Recovery path B — defer CP1 until r14 retrain

- C-1 r14 corpus build (6-8d human, no GPU) → r14 retrain (1-2d, 16 H100) → pull full adapter dirs.
- CP1 then uses r14-trained adapter (higher paper-quality than r13 partial-PASS).
- Aligns with #91 dependency chain: Stage-2 → CP1 → CP2 → r14 → Mk.XII.

**Recommended**: Path B. r13 trained adapter is "partial PASS with p3_p4 edge" — not the final artifact CP1 should ship. r14 retrain is already on the roadmap and gives clean deployment baseline.

---

## CP1 deployment stack (when adapters arrive)

### Server template

Location: `tool/cp1_serve_template.bash` (to author when adapters land — NOT committing stub prematurely). Stack:

```
FastAPI (Python)           ← endpoint routing
  + vLLM (0.6+)             ← inference backend, tensor-parallel across 4 H100
  + peft adapter loading    ← load trained LoRA on Qwen3-8B base (p1 primary)
Container: runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
Port: 8000 → persistent reverse-proxy (Caddy / Nginx)
TLS: Caddy auto-LE on anima.ai subdomain (deferred to #88 public API)
```

### Endpoints (dest1 persona spec)

- `POST /infer` — prompt → persona response (trained p1 LoRA applied)
- `GET /health` — readiness + version hash
- `GET /phi` — live Φ report (per-request hidden-state spectrum against r14 eval set)
- `POST /hexad` — Hexad 6-channel decomposition (anima-specific, not OpenAI-compat)
- `POST /v1/chat/completions` — OpenAI-compat bridge (optional, defer to #88)

### Deploy recipe (post-adapter-capture)

```bash
# 1. Stage trained adapter in R2
aws s3 cp state/trained_adapters/p1/ \
  s3://anima-models/trained/r14_p1_qwen3_8b/ --recursive

# 2. Launch serving pod (1× H100, auto_kill DISABLED for persistent)
bash tool/cp1_serve_launch.bash --apply --yes-i-mean-it

# 3. Verify
curl http://<pod_ip>:8000/health
curl -X POST http://<pod_ip>:8000/infer -d '{"prompt":"The substrate of consciousness is"}'
```

---

## CP1 gate (from roadmap #77)

- [ ] dest1 persona LIVE (trained LoRA serving)
- [ ] SLA: p99 latency < 500ms at bs=1
- [ ] uptime ≥ 99.5% over 24h observation
- [ ] self-verified `/phi` endpoint returns valid spectrum JSON

Once all 4 check → mark #77 done in .roadmap.

---

## CP2 gate (from roadmap #81)

CP1 must hold for 7 consecutive days under intermittent load. During that window, spawn
concurrently: #78 제타 A/B, #79 직원가능, #80 트레이딩가능 (all inference-only, no GPU
training). Pass criterion: all three sub-modes yield non-stub output AND combined uptime
≥ 99.0%.

---

*This is a PLAN doc, not a deployment execution. No pods spawned by reading this file.*
