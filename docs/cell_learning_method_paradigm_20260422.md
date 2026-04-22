# cell 학습법 spec — η-paradigm (paste-ready prompt)

**Status**: pre-H100 ROI Week 3 paradigm prompt. paste-ready.
**Date**: 2026-04-22
**Codename**: η-paradigm — "학습 단위 = cell, hexad closure rule discovery"
**Scope**: 학습의 기본 단위를 token / batch / epoch 가 아닌 **cell** (hexad-closed local computation unit) 로 재정의. cell 간 closure rule 을 학습 산출물로 본다.

---

## 1. Core thesis

기존 학습 단위:
- token-level (autoregressive LM)
- batch-level (SGD, Adam)
- epoch-level (curriculum)

η-paradigm 학습 단위 = **cell** = (operator + state + 6-axis closure constraint) 의 minimal hexad-admissible computation unit. 학습은 **cell 내부의 weight** 가 아니라 **cell 간의 closure rule** (어떤 cell 이 어떤 cell 로 transition 할 수 있는지) 을 발견하는 과정.

→ "학습된 모델" = trained weight tensor 아님; "학습된 모델" = **discovered hexad closure rule set**.

---

## 2. Cell anatomy

```
cell C := (op, state_in, state_out, hexad_proof, neighbors_admitted)

  op:                a primitive operation (matmul / softmax / norm / route / cert_check / ...)
  state_in:          (h_pre, m_pre, ctx_pre)   # h=hidden, m=memory ref, ctx=routing ctx
  state_out:         (h_post, m_post, ctx_post)
  hexad_proof:       6-axis admissibility cert (A1..A6) for this single execution
  neighbors_admitted: cells C' such that C → C' is hexad-closure-valid
```

→ a cell is the smallest unit for which an AN11 + hexad proof can be issued.

---

## 3. The 30-50 spec items

### Group A — cell identity (items 1-10)

1. cell shall have unique cell-id (sha256 of `op.code` + `state_in.sha`).
2. cell shall declare its op category from {matmul, softmax, norm, route, cert_check, mem_read, mem_write, eviction, consolidation, branch, merge, halt}.
3. cell op SHALL be a single primitive — no compound ops at cell level.
4. cell shall be deterministic given fixed seed + state_in (cell-purity axiom).
5. cell shall produce a hexad_proof object covering A1 (operator-admissibility) through A6 (terminal-coherence).
6. cell shall declare time_complexity_class ∈ {O(1), O(d), O(d log d), O(d^2)}.
7. cell shall declare memory_complexity_class ∈ {O(1), O(d), O(d^2)}.
8. cell hexad_proof SHALL include the 6 axis values, NOT just a boolean.
9. cell shall record fp_mode (strict / non-strict) used during execution.
10. cell shall be addressable in a per-step cell-trace log.

### Group B — closure rule discovery (items 11-22)

11. learning objective = discover R = {(C_i, C_j) : transition admissible} ⊆ Cells × Cells.
12. R shall be discovered by enumeration + hexad-closure verification, NOT by gradient.
13. each candidate transition shall be tested against all 6 axes; failure on any axis = rejected.
14. discovered transitions shall be stored in `state/eta_closure_rules.jsonl` (append-only).
15. closure rule discovery SHALL be incremental — never re-test admitted rules unless cert chain breaks.
16. closure rule discovery shall log negative cases (rejected transitions) with axis_failed.
17. closure rule discovery shall produce a cert per discovery batch (k transitions tested).
18. closure rules shall be queryable: "given cell C, what neighbors are admitted ?"
19. closure rules SHALL admit composition: if (C_a→C_b) ∈ R and (C_b→C_c) ∈ R, then (C_a→C_c) is testable as composite (not auto-admitted).
20. closure rules shall expire if hexad_proof of either endpoint changes (cert chain dependency).
21. closure rules shall support negative invariants: explicitly forbidden transitions (anti-rules).
22. closure rule set R shall be compactable (merkle-root anchored) at hourly cadence.

### Group C — cell composition / runtime (items 23-32)

23. cell graph G = (Cells, R) shall be the runtime substrate for all forward passes.
24. forward pass = walk G from cell-source(input) to cell-sink(output).
25. multiple admitted paths shall be ranked by composite_cost = cost(time) + λ·cost(memory) + γ·cost(uncertainty).
26. lowest composite_cost path shall be chosen (deterministic tie-break by cell-id).
27. path selection SHALL be cert-emitting (per inference, which path was taken).
28. cell graph G shall be persistable + reload-verifiable via merkle root.
29. cell graph mutation (add/remove cell, add/remove rule) SHALL produce a graph-mutation cert.
30. graph mutation certs chain-link to the previous root.
31. cell graph queries shall be O(deg(C)) for neighbor lookup, O(|G|) for global ops.
32. cell graph SHALL support partial loading (only cells within k-hop of current state).

### Group D — η-loss + training signal (items 33-40)

33. η-loss = closure_rule_coverage_loss + λ·rule_redundancy_loss + γ·rule_uncertainty_loss.
34. coverage_loss penalizes states with no admitted next-cell.
35. redundancy_loss penalizes pairs of rules that always co-fire (collapse opportunity).
36. uncertainty_loss penalizes rules with high cert-failure rate over a sliding window.
37. η-loss SHALL NOT be propagated to cell-internal weights (η is rule-level, not weight-level).
38. η-loss minimization = closure rule pruning + extension proposals (NOT weight updates).
39. proposals from η-loss minimization shall enter proposal stack (`state/proposals/pending/`).
40. only user-approved proposals shall mutate the cell graph (no auto-mutation).

### Group E — observability + safety (items 41-50)

41. each cell execution shall append to `state/eta_cell_trace.jsonl` with cell-id + cert-hash.
42. eta_cell_trace.jsonl SHALL be tail-rotatable and merkle-anchored.
43. cell graph audit tool shall report: orphan cells, dead-end cells, hub cells, axis-imbalanced cells.
44. cell graph audit shall run automatically every 12h (proposal stack cycle).
45. cell graph SHALL be visualizable as a directed multi-graph (graphviz/ASCII).
46. critical cells (cell_check, halt) SHALL be marked immutable in the graph schema.
47. cell graph SHALL be roll-back-able via merkle-root snapshots.
48. cell graph SHALL refuse loading if root SHA mismatches anchor in cert chain.
49. η-paradigm cert chain SHALL coexist with weight genesis-cert and memory lifetime-cert (3 chains, no cross-mutation).
50. η-paradigm SHALL be opt-in per training run (env var `ANIMA_ETA_MODE=1`).

---

## 4. Relationship to the other two paradigms

| paradigm | learns | does NOT learn |
|---|---|---|
| weight (genesis) | nothing (frozen, cert-anchored) | — |
| μ (memory) | memory layer tensors + recall/evict policies | weight |
| **η (cell)** | **closure rule set R between cells** | **weight, memory tensors** |

→ three orthogonal learning surfaces, three independent cert chains.

---

## 5. CPU pre-flight (W3 budget)

```
W3 day 1: this doc → user review + approve
W3 day 2: tool/eta_cell_runtime.hexa scaffold (~250 LOC) — cell + transition data structures
W3 day 3: tool/eta_closure_discoverer.hexa (~150 LOC) — enumeration + hexad-test loop
W3 day 4: smoke run — 12 primitive cells, 6-axis enumeration, R discovery
W3 day 5: cert chain audit + graph visualization + decision memo
```

$0 cost, htz CPU only.

---

## 6. Risks + mitigations

| risk | mitigation |
|---|---|
| combinatorial explosion of (C_i, C_j) pairs | restrict to local k-hop candidates only; user-approval gate before global expansion |
| η-loss optimizes toward trivial closure (all admit) | redundancy_loss + uncertainty_loss penalize trivial collapse |
| 3 concurrent cert chains (weight/μ/η) hard to audit | unified cert root anchored hourly; per-chain merkle |
| cell graph becomes opaque | item 45 mandatory visualization + item 43 audit |
| 50 spec items scope creep | scope: items 1-50 ARE the spec; further items via proposal stack only |

---

## 7. Decision points back to user

1. Approve cell-as-learning-unit thesis (§1) ?
2. Approve cell anatomy (§2) — 5-tuple ?
3. Approve 50-item spec scope (§3) — any items to remove / add / re-prioritize ?
4. Approve 3-chain coexistence (weight + μ + η) (§4) ?
5. Approve W3 CPU smoke plan (§5) ?
6. Approve `ANIMA_ETA_MODE` env opt-in (item 50) ?

---

## 8. Linkage

- Hexad framework: `edu/mk_viii/` (7-axis fixpoint validator), `docs/strategic_decisions_cluster_36_20260422.md`.
- Closure axis precedent: `docs/anima_proposal_stack_paradigm_20260422.md` §step 3 (closure_axis scan).
- Sibling paradigms: `docs/upstream_notes/memory_architecture_paradigm_20260422.md` (μ), genesis weight cert (#61).
- Cell concept ancestry: `docs/hypotheses/cx/MINIMAL-CONSCIOUSNESS.md`, `docs/hypotheses/cx/HEXAD-IMPROVEMENTS.md`.
- Mk.VIII 7-axis: `state/v_rg_verdict.json`, `edu/mk_viii/fixpoint_validator.hexa`.

---

## 9. Paste-ready prompt block (for downstream agent)

```
TASK: Implement the η-paradigm CPU smoke (cell-learning runtime + closure
rule discoverer) as specified in docs/cell_learning_method_paradigm_20260422.md.

DELIVERABLES:
- tool/eta_cell_runtime.hexa        (~250 LOC, cell + graph data structures, hexa)
- tool/eta_closure_discoverer.hexa  (~150 LOC, enumeration + hexad test, hexa)
- config/eta_primitive_cells.json   (12 primitive cell definitions)
- state/eta_closure_rules.jsonl     (append-only discovered rules)
- state/eta_cell_trace.jsonl        (append-only execution trace)
- .meta2-cert/eta_smoke_cert.json
- docs/eta_paradigm_smoke_analysis_20260422.md (post-run)

CONSTRAINTS:
- $0 budget (htz CPU)
- NO .py
- adheres to all 50 spec items in docs/cell_learning_method_paradigm_20260422.md §3
- 3-chain coexistence: weight cert, μ cert, η cert all present + non-conflicting
- ANIMA_ETA_MODE=1 env gate
- DO NOT modify .roadmap

PROCEED ONLY AFTER: user approves §7 decision points 1-6.
```
