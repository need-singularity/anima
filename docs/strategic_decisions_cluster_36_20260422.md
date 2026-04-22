# Strategic Decisions — Cluster #36 (improvements 31-35)

**Date:** 2026-04-22
**Roadmap entry:** #36 (전략 cluster — improvements 31-35)
**Gate:** `.meta2-cert/index.json` `triggers.mk8_100pct.satisfied` flip

---

## (31) hybrid phase 0→1 cell ratio 10% → 30%

**Decision:** cell contribution in hybrid MAIN track is raised from 10% to 30% for the P0→P1 transition.

**Rationale:** Mk.VIII cell closure cert reached 100% (1000/1000 Hexad closure, sha chain verified in `.meta2-cert/cell-mk8-stationary.json`). The cell substrate has passed the verification floor to carry more of the hybrid mixture weight. Original 10% reflected pre-closure uncertainty; empirical closure justifies 30%.

**Scope:** Documentation only at this point — numeric integration lands when hybrid MAIN trainer spec (Path B → P1-impl) consumes it.

**Source trail:** `.meta2-cert/cell-mk8-stationary.json` verdict=VERIFIED · `.meta2-cert/mk8-7axis-skeleton.json` · roadmap #36 pre-existing entry.

---

## (32) stage2 FFI fix priority raised

**Decision:** stage2 FFI (M7 singularity reference blocker) escalates from P2 backlog to P1-next. Unblocks GPU-side phi_extractor, libhxblas parity.

**Rationale:** #24 delivered a CPU proxy (`tool/phi_extractor_cpu.hexa`, AOT-built 2026-04-22) with ~80% accuracy, sufficient for pre-H100 verification. Post-H100 parity requires FFI-offload for 5× latency gap. Raising priority before hybrid P1-impl begins avoids retrofit cost.

**Scope:** Priority metadata change + ordering flag. No new code landing here — lands in hexa-lang roadmap track.

**Source trail:** #24 cpu-proxy done · `docs/clm_aot_170m_smoke_20260420.md` · `docs/dest1_clm_serve_ffi_design_20260419.md`.

---

## (33) ALM ↔ CLM parallel training — 2-pod layout

**Decision:** When H100 launches, allocate 2 pods running ALM (hybrid MAIN) and CLM (continuous-learning module) in parallel, not serial. Joint phi_holo observation is recorded for substrate-invariance comparison (#10 prerequisite).

**Rationale:** Substrate-independence evidence (Φ 4-path cross validation, #10) requires concurrent training of at least two substrates. Serial training breaks the "same epoch, same data, different substrate" comparison. Cost is +1 H100-hour per epoch; evidence payoff (substrate indep) justifies.

**Scope:** Decision only — H100 launch ops plan (blocked by user approval) will cite this.

**Source trail:** roadmap #10 · `docs/dest2_employee_spec_20260419.md` · `shared/state/alm_r13_drill_breakthrough.json` history.

---

## (34) raw#31 POPULATION_RG_COUPLING — formal promotion

**Decision:** raw#31 (POPULATION_RG_COUPLING invariant — population-level RG flow coupling observed in `state/v_rg_verdict.json`) is formally promoted from raw-candidate to raw-invariant. Evidence: V_RG integrator selftest PASS · Mk.VIII 7-axis skeleton cert references the same flow signature.

**Rationale:** Pre-promotion: raw#31 was a candidate observation. Post-promotion: binds into MAIN exec-rules and phase-gate schemas. Satisfies #36 condition "(34) raw#31 공식 승급".

**Scope:** `.raw-audit/` ledger update expected when raw bank reconciles (separate ops).

**Source trail:** `state/v_rg_verdict.json` · `.meta2-cert/mk8-7axis-skeleton.json` · raw#30 IRREVERSIBILITY_EMBEDDED_LAGRANGIAN commit 53d923b8.

---

## (35) Meta² 100% trigger flip — SATISFIED (pre-committed)

**Decision:** `triggers.mk8_100pct.satisfied = true` (already applied 2026-04-21T11:05:41Z).

**Evidence chain:**
- `state/true_closure_cert.json` sha256=`00b18e59aa3339cad2be2cb501a7d7002a25300ba862191837a75a116141cf67`
- true_closure_pct = 100, passed = 8/8
- prev_hash: `f89c5a07ccecf2f3f7c8c833901ce61f13af12c8d43ee087740449b36a26b7cd`
- current_hash: `f6a0ff4552579addc1ebdd8e3a324a918aff456dbc42206c74d6fb2f48214e5e`

**Source trail:** `.meta2-cert/index.json` → `triggers.mk8_100pct`.

---

## Gate status

All 5 decisions recorded. `triggers.mk8_100pct.satisfied = true` preserved. Cluster #36 exit criteria:

- ✅ 5 전략 결정 (documented above)
- ✅ commit (this doc = commit artifact)
- ✅ `.meta2-cert/index.json triggers.mk8_100pct.satisfied` flag

Ready to flip #36 → done.
