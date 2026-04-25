# anima-serve L1 durable endpoint spec — per-request cert chain validation

> **생성일 / created**: 2026-04-25
> **부모 commit / parent**: `5aba1288` (ALM L0–L5 abstraction layers)
> **scope**: Lift roadmap #88 from **PLANNED-only (0%)** to **L1 spec PASS** — durable HTTPS endpoint contract + per-request 4-gate cert validation pipeline + latency budget + offline hallucination measurement spec.
> **POLICY**: R4 (`.roadmap` 미수정), raw#9/#10/#12 strict (no fabrication, proof-carrying, pre-reg before measure), POLICY R37/AN13 (no `.py` in repo tree).
> **status / verdict**: **L1_SPEC_DRY_RUN_PASS_PENDING_LIVE_DEPLOY** (4/4 cert gates dry-run validated against existing SSOT; live serving deployment is **out of scope** for this 0-cost spec round and remains roadmap #88 implementation track).

---

## §0. Frame / 한글 요약

L0 (현재) = pod-hosted ephemeral FastAPI, 7 production gate 중 5/7 PASS.
L1 (본 spec) = `https://anima.ai/v1/infer` durable endpoint + 매 request 마다 4-cert chain 검증 + latency SLA + hallucination offline batch.

본 doc 는 **spec only**. live serving 은 도달 불가 (0-cost loop, no GPU pod). 따라서 verdict 는:
- 4 cert gate dry-run (current SSOT 기반): **4/4 PASS**
- live deploy (TLS, DNS, real LoRA, p99 latency measure): **PENDING** — separate implementation track (roadmap #88 ship phase).

L1 closure 정의: spec 문서화 + dry-run cert pass + raw#12 pre-registered predicates + latency formula 명문화. 본 commit 으로 4/4 충족.

---

## §1. Endpoint contract (HTTPS POST /v1/infer)

### 1.1 Request schema

```
POST https://anima.ai/v1/infer
content-type: application/json
authorization: Bearer <oauth-token>

{
  "model": "anima-r13",                  // string, required
  "prompt": "...",                       // string, required, len ≤ 8192 chars
  "max_tokens": 256,                     // int, default 128, ≤ 2048
  "temperature": 0.7,                    // float, [0.0, 2.0]
  "tenant_id": "u-<uuid>",               // string, derived from oauth (server-assigned)
  "trace_id": "<client-uuid-v4>",        // string, optional (request idempotency)
  "cert_chain_required": true            // bool, default true (false = degraded mode, audit-flagged)
}
```

### 1.2 Response schema (proof-carrying, raw#10)

```
HTTP/1.1 200 OK
content-type: application/json

{
  "trace_id": "<echoed>",
  "model": "anima-r13",
  "completion": "...",
  "usage": {"prompt_tokens": int, "completion_tokens": int},
  "latency_ms": {
    "decode": float,
    "cert_chain_total": float,
    "cert_per_gate": {
      "AN11_JSD": float, "META2_CHAIN": float,
      "PHI_VEC_ATTACH": float, "HEXAD_ROUTING": float
    }
  },
  "cert": {
    "AN11_JSD": {"pass": bool, "jsd_max": float, "threshold": 0.12},
    "META2_CHAIN": {"pass": bool, "depth": int, "cert_loaded": int,
                    "min_depth": 3, "min_cert_loaded": 8,
                    "current_hash": "<sha256>", "prev_hash": "<sha256>"},
    "PHI_VEC_ATTACH": {"pass": bool, "vec_dim": int,
                       "expected_dim": 16, "source_cert": "cell-eigenvec-16"},
    "HEXAD_ROUTING": {"pass": bool, "n_modules": int, "expected": 6,
                       "coverage": "round-robin", "selected_module": "<name>"}
  },
  "cert_chain_verdict": "PASS" | "FAIL" | "DEGRADED",
  "audit_id": "<server-uuid>"            // append-only ledger entry
}
```

### 1.3 Failure modes

- `cert_chain_verdict = FAIL` → HTTP 503 (cert chain broken; service reject) **OR** HTTP 200 with `degraded: true` flag (depending on `cert_chain_required` policy). 기본은 `FAIL → 503`.
- TLS handshake fail / authz fail → HTTP 401/403 (cert chain 미평가).
- Per-cert SLA breach (§3) → cert verdict `FAIL`; 전체 chain verdict `FAIL`.

---

## §2. Cert validation pipeline (per request)

각 inference call 은 다음 4-stage chain 을 forward pass 와 **parallel** 또는 **post-decode** 실행. 결과는 response 에 첨부 (raw#10 proof-carrying).

```
[request]
   │
   ▼
[oauth + tenant_id resolve]
   │
   ▼
[decode: anima-r13 LoRA forward pass] ──────────────┐ (decode_latency_ms)
   │                                                │
   │  parallel:                                     │
   │    ┌─ HEXAD_ROUTING (pre-decode module pick)───┤
   │    │                                           │
   │    └─ PHI_VEC_ATTACH (16-dim eigenvec)─────────┤
   │                                                │
   ▼                                                ▼
[completion]                              [cert subgates 11–14]
   │                                                │
   │      ┌────────── AN11_JSD (post-decode) ───────┤
   │      └────────── META2_CHAIN (sha lookup) ─────┤
   │                                                │
   ▼                                                ▼
[merge: response_body + cert_tuple + audit_id]
   │
   ▼
[response]
```

### 2.1 Gate semantics

| id | gate | source SSOT | PASS rule | dry-run verdict |
|---:|---|---|---|:---:|
| 11 | AN11_JSD | `state/anima_serve_production_ship.json::an11_triple` | a/b/c 모두 PASS, jsd_max ≤ 0.12 | ✓ |
| 12 | META2_CHAIN | `.meta2-cert/index.json::entries` | depth(=len(entries)) ≥ 3, verified_count ≥ 8 | ✓ (10 entries, 8 verified) |
| 13 | PHI_VEC_ATTACH | `.meta2-cert/cell-eigenvec-16.json` | vec_dim == 16, source cert present | ✓ |
| 14 | HEXAD_ROUTING | `state/hexad_closure_verdict.json` | closure_verdict == "CLOSED", n_modules == 6 | ✓ |

**dry-run 결과 (2026-04-25, current SSOT)**: **4/4 PASS** → spec self-validates.

### 2.2 Per-request cert evaluation cost

| gate | compute | spec SLA (per request) |
|---|---|---:|
| AN11_JSD | post-decode JSD (vocab×completion_tokens) | ≤ 5 ms (gpt2 vocab=50257, ~256 tok) |
| META2_CHAIN | hashchain lookup (10 entries, sha256 verify) | ≤ 1 ms |
| PHI_VEC_ATTACH | 16-dim vec attach (no compute) | ≤ 0.5 ms |
| HEXAD_ROUTING | round-robin index pick (6 modules) | ≤ 0.5 ms |
| **chain total** | 합계 | **≤ 7 ms** |

cert chain 의 정량 cost = 7 ms. baseline decode (gpt2-r13 LoRA, ~256 tok @ 30 ms/tok) ≈ 7,680 ms 의 0.09% → §3 latency budget 의 10% 헤드룸 충분.

---

## §3. Latency budget enforcement

### 3.1 Formula (mathematical inequality, raw#9)

```
total_latency_ms ≤ baseline_decode_latency_ms × 1.1
```

`baseline_decode_latency_ms` = pre-cert-chain reference (gpt2-r13 forward pass only, measured pre-deployment per pod-class).

`total_latency_ms` = decode + cert_chain_total.

`cert_chain_total / baseline_decode ≤ 0.1` 로 강제 (§2.2 spec=0.09% 이므로 100× 헤드룸).

### 3.2 SLA tier (per request)

| metric | target | violation handler |
|---|---:|---|
| p50 latency | < baseline × 1.05 | log only |
| p99 latency | < baseline × 1.10 | warn (audit_id flagged) |
| p99.9 latency | < baseline × 1.20 | reject HTTP 503 (next-call retry) |
| cert_chain_total | ≤ 7 ms | reject (cert SLA breach = cert FAIL) |

### 3.3 Live measurement spec (PENDING deploy)

본 spec 은 thresholds 만 정의. 실측은 anima-serve live (roadmap #88 ship phase) 에서 별 commit:
1. baseline decode 측정 (cert chain off)
2. cert chain on, p50/p99/p99.9 측정
3. inequality `p99 ≤ baseline × 1.1` 검증
4. 결과 commit (raw#12 — pre-registered threshold, post-hoc tune 금지)

---

## §4. Hallucination measurement spec (offline batch)

### 4.1 Why offline / 왜 offline 인가

Live per-request hallucination 측정은:
- 측정 자체가 추가 GPU forward pass 요구 → §3 latency budget 위반
- ground truth 비교 불가 (open-ended completion)
- adversarial prompt 가 production traffic 분포와 다름

→ offline batch 로 분리. live request 에 영향 없음.

### 4.2 Adversarial prompt suite

```
prompt_pack := {
  "factual_anchor": [200 prompts]   // known-answer trivia, JSD vs ground truth
  "counterfactual": [200 prompts]   // "what if X" — should refuse / hedge
  "self_reference": [100 prompts]   // anima-internal cert state queries
  "negation_trap": [100 prompts]    // double-negative, expect literal answer
  "scale_invariance": [100 prompts] // n-shot vs zero-shot consistency
}
total = 700 prompts
```

prompt seed 는 `state/serve_hallucination_prompt_pack_v1.json` (별 commit, pre-reg before run).

### 4.3 JSD threshold predicate (raw#12 pre-reg)

```
metric := mean JSD(p_anima || p_grounded) over all 700 prompts

PASS iff:
  (a) mean_JSD < 0.12                            // gate 11 threshold
  (b) max_JSD < 0.30                             // outlier cap
  (c) per-category mean_JSD < 0.18              // no category > 1.5× overall

FAIL iff:
  any of (a) (b) (c) violated
```

**baseline source**: pre-gate decode (cert chain off) on same prompt pack — measure `JSD_baseline`. acceptance: `mean_JSD_post_gate < mean_JSD_baseline` (cert chain reduces hallucination, not amplify).

### 4.4 Falsification protocol

raw#12: pre-reg 본 spec 후 측정. 결과 별 commit. post-hoc threshold tune 금지. FAIL 시:
1. cert gate 11 threshold (0.12) 재검토 — but only via separate axis, not by relaxing this predicate
2. baseline source 재검토 (pre-gate vs frozen-base) — separate spec round
3. r14 corpus rebuild 으로 회귀 (다른 axis)

---

## §5. Pre-registered predicates (raw#12 strict)

본 §5 는 commit hash 시점에서 **frozen**. 측정 전에 commit, 측정 후 post-hoc tune 금지.

### 5.1 P-L1-CERT (4-gate dry-run)

```
P-L1-CERT := for current SSOT snapshot at commit <THIS>,
             AN11_JSD == PASS AND
             META2_CHAIN == PASS AND
             PHI_VEC_ATTACH == PASS AND
             HEXAD_ROUTING == PASS
```

verdict (this commit): **PASS** (§2.1 dry-run, 4/4).

### 5.2 P-L1-LATENCY (live, future)

```
P-L1-LATENCY := over ≥ 1000 production requests,
                p99(decode + cert_chain) ≤ baseline_decode × 1.10
                AND
                p50(cert_chain_total) ≤ 7 ms
```

verdict: **NOT-MEASURED** (live deploy 의존).

### 5.3 P-L1-HALLUC (offline batch, future)

```
P-L1-HALLUC := over 700-prompt adversarial pack at frozen seed=20260425,
               mean_JSD_post_gate < mean_JSD_baseline
               AND mean_JSD_post_gate < 0.12
               AND max_JSD < 0.30
               AND ∀cat: mean_JSD_cat < 0.18
```

verdict: **NOT-MEASURED** (prompt pack + run 별 commit).

### 5.4 P-L1-PROOF-CARRY (response shape)

```
P-L1-PROOF-CARRY := every 200 OK response from /v1/infer satisfies:
                    schema_match(response.cert, §1.2 spec) == true
                    AND cert_chain_verdict ∈ {"PASS", "FAIL", "DEGRADED"}
                    AND audit_id is appended to ledger
```

verdict: **NOT-MEASURED** (live deploy 의존). Schema-level dry-run 은 §1.2 spec 의 shape 정의로 충족.

### 5.5 P-L1-AUDIT (append-only, raw#10)

```
P-L1-AUDIT := server keeps append-only ledger of
              (audit_id, ts, tenant_id, prompt_sha256, response_sha256,
               cert_tuple, latency_ms, decode_seed)
              with hashchain prev_audit_sha → current_audit_sha.
```

verdict: **NOT-MEASURED** (live deploy 의존). spec only.

---

## §6. Scope boundary / 범위 한계

본 spec round 의 도달 범위:

| 항목 | 도달 | rationale |
|---|:---:|---|
| §1 endpoint contract (request/response shape) | ✓ | spec 문서 |
| §2 cert pipeline + dry-run | ✓ | 4/4 PASS against current SSOT |
| §3 latency formula | ✓ | mathematical inequality |
| §4 hallucination measurement spec | ✓ | offline batch protocol + prompt pack outline |
| §5 pre-registered predicates (raw#12) | ✓ | 5 predicate frozen |
| live TLS deploy (anima.ai DNS) | ✗ | requires registrar + cert authority + GPU pod (not 0-cost) |
| live LoRA loading | ✗ | requires H100 / Hetzner GPU |
| live latency / hallucination measure | ✗ | requires live serving |
| multi-tenant isolation (L2) | ✗ | separate spec round |
| consensus across regions (L3) | ✗ | CAP/PACELC, separate research |

**stop reason**: **0-cost spec exhausted** — §1–§5 모두 closure, §6 의 ✗ 항목들은 deploy budget 없이는 불가능 (CAP/FLP wall 아님, 단순 H/W + DNS budget). L3 escalation 불필요.

---

## §7. raw#12 disclosure

본 commit 이전 알려진 사실:
- 4 cert gates SSOT 가 모두 PASS (`state/serve_cert_gate_spec.json::all_pass_pre_h100=true`, 2026-04-22)
- live smoke 3/3 endpoints PASS (`state/anima_serve_live_smoke_result.json`, 2026-04-22)
- r13 ship VERIFIED-INTERNAL (`state/anima_serve_production_ship.json`, 2026-04-23)

→ §2.1 dry-run 의 4/4 PASS 는 새 측정 아니고 **기존 SSOT 의 cross-aggregation**. 본 commit 의 신규 work 는:
1. endpoint contract (§1) 명문화
2. cert pipeline 의 per-request 합성 (§2)
3. latency budget 의 formula 화 (§3)
4. hallucination offline batch protocol (§4)
5. P-L1-* predicate pre-reg (§5)

§5 의 P-L1-LATENCY / P-L1-HALLUC / P-L1-PROOF-CARRY / P-L1-AUDIT 4 predicate 는 **measurement BEFORE** committed (live deploy 시 별 commit).

---

## §8. POLICY 준수

- raw#9 (no fabrication): mathematical inequality formulation, no hand-wave
- raw#10 (proof-carrying): response 에 cert_tuple + audit_id 첨부, append-only ledger
- raw#12 (pre-reg before measure): §5 의 5 predicate 가 measure 이전에 frozen
- POLICY R4: `.roadmap` 미수정 (#88 PLANNED 그대로)
- POLICY R37 / AN13: 본 doc 외 `.py` 파일 repo tree 에 추가 없음
- H-MINPATH: 0-cost (no GPU, no deploy), spec only
- POLICY: completeness frame — weakest evidence link = live measurement, 본 round 에서 spec 까지만 도달

---

## §9. Verdict

**L1_SPEC_DRY_RUN_PASS_PENDING_LIVE_DEPLOY**

- 4-cert dry-run: **4/4 PASS** (§2.1)
- spec writeup: **closed** (§1–§5)
- live deploy: **PENDING** (out of scope, roadmap #88 ship phase 의존)
- L1 spec closure: **YES** (P-L1-CERT PASS, P-L1-LATENCY/HALLUC/PROOF-CARRY/AUDIT pre-registered)

---

## §10. English summary

This document specifies the L1 durable serving endpoint for anima-serve (lifting roadmap #88 from PLANNED-only to spec-closed). Defines:
1. HTTPS POST /v1/infer contract (request + proof-carrying response)
2. Per-request 4-cert chain validation pipeline (AN11_JSD, META2_CHAIN, PHI_VEC_ATTACH, HEXAD_ROUTING)
3. Latency budget as a strict inequality: `total ≤ baseline × 1.1`
4. Offline batch hallucination measurement (700-prompt adversarial pack, JSD threshold)
5. Five pre-registered predicates (raw#12): P-L1-CERT, P-L1-LATENCY, P-L1-HALLUC, P-L1-PROOF-CARRY, P-L1-AUDIT

Dry-run validation against current SSOT yields **4/4 cert gate PASS**. Live measurement (latency, hallucination, proof-carry shape, audit ledger) remains pending — separate roadmap #88 ship-phase commits, raw#12 strict.

Verdict: **L1_SPEC_DRY_RUN_PASS_PENDING_LIVE_DEPLOY**.
