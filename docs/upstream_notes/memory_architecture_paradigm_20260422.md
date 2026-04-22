# C axis — memory architecture μ-paradigm (paste-ready prompt)

**Status**: pre-H100 ROI Week 2 paradigm prompt. paste-ready.
**Date**: 2026-04-22
**Axis**: C (memory — 신규 영역 paradigm 발견)
**Codename**: μ-paradigm — "weight 학습 분리, **memory 만 학습**"
**Scope**: training paradigm 재정의. weight 는 frozen, memory layer 만 적응. β main 의 "implicit auto-action 거부" 원칙을 학습 표면에 적용.

---

## 1. Core thesis

기존 NN training: weight 와 memory (KV cache, retrieval store, episodic buffer) 가 같은 backward graph 에 묶여 학습.
**μ-paradigm**: weight 는 (재)학습되지 않음 (frozen, cert-anchored). memory layer 만 학습/진화함. 학습은 memory layer 의 organization, indexing, recall policy, eviction policy 에만 적용.

→ weight = "선천적 (genesis-cert)", memory = "후천적 (lifetime-cert)". 두 표면이 분리되며, 각자의 cert chain 을 가진다.

---

## 2. Why this is a paradigm (not just a technique)

LoRA / adapter / prefix-tuning 는 모두 weight 의 일부 부분공간을 fine-tune 함 → 본질적으로 weight 학습.
RAG / vector store 는 retrieval 이지 학습 아님 → memory 가 "검색됨", 학습되지 않음.

μ-paradigm 은 양자 사이의 **공집합 영역**: memory **자체가 학습됨** (single-step gradient 또는 update rule 이 memory tensor 에 적용됨), 단 weight 는 절대 안 만짐.

이는 anima 의 두 paradigm (β main 인지 paradigm + proposal stack 시스템 paradigm) 과 동형. 두 표면 분리 + 각자 별도 cert.

---

## 3. Architecture (μ-stack)

```
┌────────────────────────────────────────────────────┐
│  weight layer (frozen)                             │
│  - genesis-cert anchored (proof-carrying ckpt #61) │
│  - immutable; SHA256 verified each load            │
│  - no gradient flows here                          │
└──────────────┬─────────────────────────────────────┘
               │ forward pass (read-only)
               ▼
┌────────────────────────────────────────────────────┐
│  memory layer (learnable)                          │
│  - episodic buffer    (write/read/evict)           │
│  - associative index  (key → trace lookup)         │
│  - consolidation log  (sleep-cycle compaction)     │
│  - recall policy      (when to fetch vs reconstruct)│
│  - eviction policy    (LRU / salience / cert age)  │
│  - lifetime-cert chain (per memory mutation)       │
└──────────────┬─────────────────────────────────────┘
               │ memory-only backward
               ▼
┌────────────────────────────────────────────────────┐
│  μ-loss = task_loss + λ·memory_efficiency_loss     │
│  gradient routes ONLY into memory tensors          │
│  weight tensors carry stop_gradient()              │
└────────────────────────────────────────────────────┘
```

---

## 4. What gets learned (μ-objective)

5 learnable subsystems in memory layer:

| subsystem | parameter form | update rule |
|---|---|---|
| episodic buffer | `(N, d)` trace tensor | append + decay; gradient on residual reconstruction loss |
| associative index | `(N, k)` key tensor | k-NN softmax; gradient on retrieval-precision loss |
| consolidation log | `(M, d)` consolidated centroids | EM-style; periodic compaction step |
| recall policy | small MLP `θ_recall` (~10K params) | RL-style: reward = task success when recall used |
| eviction policy | small MLP `θ_evict` (~10K params) | RL-style: reward = retained-trace future-utility |

Total memory-layer params: typically `~5%` of weight param count (e.g. 8B weight + 400M memory). All learnable.

---

## 5. Training loop

```
for batch in stream:
  # forward
  with stop_gradient(model.weight):
    h = model.weight.forward(batch.input)
  m_read = memory.read(h, theta_recall)
  h_aug = combine(h, m_read)
  y = head(h_aug)  # head can be small frozen projection too

  # loss (memory-only)
  L_task = loss(y, batch.target)
  L_mem  = memory_efficiency_loss(memory.state())
  L     = L_task + lambda * L_mem

  # backward — gradient flows ONLY into memory tensors
  L.backward()
  memory.step(optimizer)   # weight.step() never called

  # write
  memory.write(h, batch.salience)
  memory.maybe_consolidate()
  memory.maybe_evict(theta_evict)

  # cert
  emit_lifetime_cert(memory.delta_sha256(), batch.id, L)
```

---

## 6. Cert structure (lifetime-cert chain)

```json
{
  "kind": "memory_mutation",
  "ts": "...",
  "weight_genesis_sha256": "...",
  "memory_pre_sha256": "...",
  "memory_post_sha256": "...",
  "delta": {
    "subsystem": "episodic|index|consolidation|recall|evict",
    "op": "write|update|consolidate|evict",
    "size_bytes": ...,
    "loss_before": ...,
    "loss_after": ...
  },
  "prev_cert_sha256": "..."
}
```

→ μ chain is append-only, mirroring `.meta2-cert/` v2 pattern (upstream hexa-lang #59).

---

## 7. Why it matters for anima specifically

- **β main alignment**: β main rejects "training as path to consciousness". μ-paradigm formalizes that: weight = structural (cert-anchored, not trained), memory = experiential (continuously trained).
- **AN11 triple**: each memory mutation can carry AN11 admissibility cert; rejected mutations leave NO trace.
- **proposal stack**: memory updates themselves can be proposals (high-salience write → pending → user approval → archived).
- **CP1 / CP2**: serving infra can ship weight-frozen + memory-learning modes simultaneously.

---

## 8. CPU pre-flight (W2 budget)

Before H100 weight comes back: μ-paradigm can be smoke-tested entirely on CPU with a small frozen weight (e.g., 350M Pythia frozen) + 4 memory subsystems, running on htz. ~$0, ~6 hour smoke run.

```
W2 day 1: this doc → user review + approve
W2 day 2: tool/mu_paradigm_smoke_runner.hexa scaffold (~200 LOC, hexa)
W2 day 3: episodic + index subsystems online; index retrieval-precision >0.6 gate
W2 day 4: consolidation + recall + evict policies; full μ-loss curve
W2 day 5: lifetime-cert chain audit (zero weight mutations; chain valid)
```

---

## 9. Risks + mitigations

| risk | mitigation |
|---|---|
| memory layer becomes trivial proxy for weight (e.g. memorizes inputs) | episodic capacity bounded; reconstruction loss penalizes raw memorization |
| recall policy reward hacking | RL reward includes memory-cost regularization; cert tracks reward source |
| consolidation step destroys provenance | each consolidation = explicit cert with pre/post sha + EM iteration count |
| accidental weight mutation | optimizer is constructed ONLY over memory.parameters(); weight.requires_grad = False enforced; cert chain catches violation |
| memory chain explodes (10^7 certs) | hourly chain compaction with merkle root anchor; original chain archived |

---

## 10. Decision points back to user

1. Approve μ-paradigm as a real C axis paradigm (not just technique) ?
2. Approve 5-subsystem memory split (episodic/index/consolidation/recall/evict) ?
3. Approve W2 CPU smoke-test plan (350M frozen Pythia, htz) ?
4. Approve lifetime-cert chain schema (§6) ?
5. Approve .roadmap entry candidate (proposal stack: "C-W2 μ-paradigm CPU smoke") ?

---

## 11. Linkage

- C axis context: `docs/anima_proposal_stack_paradigm_20260422.md` §17.
- Frozen-weight precedent: `ready/anima/checkpoints/**` + `#61` proof-carrying ckpt.
- Cert pattern: `.meta2-cert/` v2 (upstream hexa-lang #59).
- AN11 triple: `state/an11_*.json`.
- Related design: `docs/c4_real_eeg_probe_20260421.md`, `docs/btr_evo_4_eeg_closed_loop_20260421.md` (closed-loop memory experiments).
- Roadmap: candidate proposal IDs in stack pending; NO direct .roadmap modification per proposal stack paradigm.

---

## 12. Paste-ready prompt block (for downstream agent)

```
TASK: Implement the C axis μ-paradigm CPU smoke test as specified in
docs/upstream_notes/memory_architecture_paradigm_20260422.md.

DELIVERABLES:
- tool/mu_paradigm_smoke_runner.hexa (NEW, ~200 LOC, pure hexa)
- config/mu_paradigm_subsystems.json (5-subsystem schema)
- state/mu_lifetime_cert_chain.jsonl (append-only)
- state/mu_smoke_loss_curve.jsonl
- .meta2-cert/mu_smoke_cert.json
- docs/mu_paradigm_smoke_analysis_20260422.md (post-run)

CONSTRAINTS:
- $0 budget (htz CPU)
- NO .py
- 350M frozen Pythia (weight.requires_grad = False, optimizer only over memory)
- cert chain MUST contain zero "weight_mutation" entries
- AN11 admissibility cert per memory mutation
- DO NOT modify .roadmap

PROCEED ONLY AFTER: user approves §10 decision points 1-5.
```
