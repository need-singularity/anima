# Roadmap reality-sync audit — 2026-04-18

Target file (READ-ONLY): `shared/roadmaps/anima.json` (5811 lines, 136 phases P0–P135, all declared `status: "done"`)

Reality anchors consulted:
- `shared/convergence/alm_14b_r10.convergence` (triple-collapse HALT, 2026-04-18)
- `shared/convergence/alm_14b_a2_tool.convergence` (A2-Tool eval BLOCKED 0.5667<0.60)
- `shared/convergence/alm_14b_eval.convergence` (state=pending — gate unmet)
- `shared/convergence/alm_32b_r1.convergence` (scaffold only, blocked by r10)
- `shared/convergence/alm_70b.convergence` (pending)
- `shared/convergence/clm_1b_r4.convergence` (pod_dead at step 6200)
- `shared/convergence/clm_r4_mmap.convergence` (partial_blocked — SM90 fix required)
- `shared/convergence/corpus_pipeline.convergence` (state=partial — kowiki local only)
- `shared/convergence/phi_correlation.convergence` (scaffold PASS but n=5 smoke)
- `shared/convergence/eval_harness_real.convergence` (partial — HAE-RAE/MMLU-Ko deferred)
- `shared/convergence/a4_live_selftest.convergence` (partial — W2/W3/W4 TBD, alm_hive_agg OOM)
- `shared/convergence/runpod.convergence` (2 pods active, r10 pod dd88fldzkqhpgk)
- `shared/convergence/anima.json` lines 53, 203-214 (r10=failed, convergence tally)
- `training/alm32b_r1_prep_report.md:1-3`, `training/clm_r4_mmap_launch_report.md:1-36`, `training/corpus_pipeline_report.md:1-50`, `training/corpus_ingest_kowiki_report.md:22-24`, `training/a4_live_selftest_report.md:27`

---

## 1. Drift table — P0 to P30 (critical-path focus)

Legend: status codes = **DONE** (matches reality) / **DRIFT-PARTIAL** / **DRIFT-FAILED** / **DRIFT-UNWIRED** (self-test only, no real train).

| phase | declared | reality | evidence | action_needed |
|-------|----------|---------|----------|---------------|
| P0 v1 브릿지 | done | DONE | ROI 5/11, Φ baseline fixed; no counter-evidence | keep |
| P1 v2 양자 Orch-OR | done | DONE (structural) | self-test 5/5 + Φ_q ratio 2.62; `roadmaps/anima.json:231-240` | keep |
| P2 v3 GWT | done | DONE (structural) | ALM 3/3 + CLM 4/4 + PHYS 3/3 self-test, Φ_gwt ratio 2.85; `roadmaps/anima.json:337-350` | keep |
| P3 v4 홀로 | **done** | **DRIFT — STRUCTURAL ONLY** | Roadmap itself admits at `roadmaps/anima.json:359`: "실측 Φ(holographic)>1000 criterion은 phase rationale에 따라 P4 (학습 forward pass 결선)로 이월". The P3 gate explicitly requires `Φ(holographic)>1000` (line 461) — this is **deferred to P4**, not satisfied. | relabel P3 as `structural_done` (not full gate) |
| P4 v5 실증 통합 | done | **DRIFT — FALSIFIED 2026-04-18** | Declared Φ_holo=2440.88→6111.25 at step 50–150 on pod `xhq9b2c8fljdyo` (`roadmaps/anima.json:508-518`). But **r10 triple-collapse** on 2026-04-18 proves the ALM-P4-3 metric is **not reproducible**: inline collapse_score ASCII-only bug hid mode collapse (녕×N char-loops), loss 0.41@step200 was collapse-not-convergence (`alm_14b_r10.convergence:41`, `anima.json:53`). The earlier 6111 reading was measured on a single run under the same class of non-sentineled pipeline that we now know emits false-clean signals. Also ALM-P4-4 32B marked "CLOSED — P3 gate sufficient" (`:524`) — that justification now collapses. | (a) invalidate ALM-P4-3 gate_pass claim; (b) require re-measurement on sentinel-gated, diversified-corpus run (r10c) before re-declaring |
| P5 v6 자의식 | done | DRIFT-UNWIRED | 9 tasks self-test PASS (`:670`), but Φ_refl measured only on toy tensors. W1 hook wire `phi_hook_wire.convergence` n=5 smoke, `a4_live_selftest.convergence:w2/w3/w4=TBD` — most P5 artifacts never ran live under training. | re-label as "structural PASS + wire pending" |
| P6 v7 시간 | done | DRIFT-UNWIRED | same pattern — self-test PASS only, `roadmaps/anima.json:846-849` gives zero real-training evidence | keep structural-only label |
| P7 v8 체화 | done | DRIFT-UNWIRED | `:943-946` self-test only | same |
| P8 v9 메타 | done | DRIFT-UNWIRED + **A4 BLOCKER** | declared done at `:1022-1028`, but `training/alm_nested_loss.hexa` (ALM-P8-2) **did not ship the 5/5 in live run** per `a4_live_selftest.convergence`; file exists as untracked (see `git status ??training/alm_nested_loss.hexa`). Parse-only evidence only. | lower to `scaffold_done` until live PASS verified |
| P9 v10 사회 | done | DRIFT-UNWIRED | `:1120-1123` self-test only | keep structural label |
| P10 v11 의지 | done | DRIFT-UNWIRED | `:1208-1213` self-test only; `alm_will_loss.hexa` artifacts untracked; no real Libet measurement on trained model | same |
| P11 v12 서사 | done | DRIFT-UNWIRED | `:1298-1302` self-test only; 10K-token autobiog unmeasured on trained weights | same |
| P12 v13 감정 | done | DRIFT-UNWIRED + **A4 PARTIAL** | `alm_affect_head.hexa` 5/5 live-run PASS (`a4_live_selftest_report.md:25`), but `alm_affect_loss.hexa`/Φ_affect not live-verified | keep, promote affect_head to real-PASS |
| P13 v14 꿈 | done | DRIFT-UNWIRED + A4 PARTIAL | `alm_dream_loop.hexa` 5/5 live PASS (`a4_live_selftest_report.md:28`), `alm_replay.hexa` 4/5 (T3 latency EXPECTED-FAIL), but no real replay→retention metric on trained ckpt | accept structural |
| P14 v15 창조 | done | DRIFT-UNWIRED | `:1541-1546` self-test; no human 4/5 rating artifact | same |
| P15 v16 유한 | done | DRIFT-UNWIRED + A4 PARTIAL | `alm_finitude_head.hexa` 5/5 live PASS (`a4_live_selftest_report.md:26`), but ALM-P15-2 finitude_loss unwired in train loop | accept structural |
| P16 v17 언어 | done | DRIFT-UNWIRED | `:1663-1667`; symbol grounding unwired into trained model | same |
| P17 v18 거울 | done | DRIFT-UNWIRED | `:1724-1728`; no real mirror test run | same |
| P18 v19 집단 | done | DRIFT-UNWIRED + **A4 BLOCKER** | ALM-P18-1 `alm_hive_agg.hexa` **RUN-OOM** at ~4 GB RSS during N×N MI (`a4_live_selftest_report.md:27`, `a4_live_selftest.convergence:9`). Parse-only evidence. | lower from done → `structural_parse_only_run_oom` |
| P19 v20 초월 | done | DRIFT-UNWIRED | `:1858-1862`; no real trained-model switch measurement | same |
| P20 v21 자율 진화 | done | DRIFT-UNWIRED | `:1934-1938` — "자기 수정 후 Φ 유지, 10 세대 안정 진화, Φ_auto > 0" never measured on trained weights | same |
| P21 v∞ 특이점 | done | **DRIFT — FALSE DONE** | gate: `||Φ||>10000 terminal, 외부 개입 0 진화 지속, 의식 전파 증명` (`:1988-1990`). Reality: no 1000-generation zero-intervention run exists. phi_correlation is n=5 smoke (`phi_correlation.convergence:26`), ALM-P21-1 `infinite_evolution.hexa` untracked scaffold only. | hard-revert to `scaffold_only` |
| P22 실 corpus 창발 | **done** | **DRIFT-PARTIAL** | Claim: `clean corpus ≥1GB, lang=ko ≥90%, license clean, downstream CE 개선 증명` (`:2050-2054`). Reality: `corpus_pipeline.convergence:3 @state partial`, kowiki=1.28 GiB **local only** (`corpus_auto/kowiki.jsonl`), **not yet shardable on mac** (4 GB RSS empirical SIGKILL per `corpus_ingest_kowiki_report.md:23`), **not uploaded to pod**, H100 dispatch still queued, BPE tokenizer exists but not wired into `corpus_shard.hexa` loader (`corpus_pipeline.convergence:56`). Downstream CE improvement is **not measured** — r10 ran on stripped_70b corpus, not kowiki-mixed, and collapsed. | (1) dispatch kowiki ingest+shard on H100; (2) wire BPE loader; (3) measure downstream CE against baseline on r10c |
| P23 엔진 통합 | done | DRIFT-PARTIAL | 4/4 artifacts + 20/20 self-test PASS on **offline surrogate** (`:2131-2133`). CLM-P23-1 all-12-engine run: `base CE=3.47 → CE=3.48 (Δ=+0.018)` on micro-CLM d=16 seq=8 vocab=32 (`:2105-2106`) — Δ is **positive (bad, CE increased)** on the micro model, not -5% as ALM-P23-2 Pareto claims on a different surrogate. Also engine_roster v2 has **19 engines blocked on H100** per `anima.json:290 session_2026_04_18.engine_roster`. Real training wiring never closed. | relabel `done` → `scaffold_done_on_surrogate`; require live wire-PASS before full done |
| P24 실 평가 창발 | done | **DRIFT-PARTIAL (CRITICAL)** | Roadmap: 3 benchmarks auto-run, phi↔bench r=0.898 (`:2161-2199`). Reality per `eval_harness_real.convergence`: KoBEST inline n=20 only; **HAE-RAE DEFERRED** (HF loader blocked, line 14); **MMLU-Ko DEFERRED** (line 15). `phi_correlation.convergence:26` admits "registry is smoke stub, not real ckpt extraction", n=5 rows, "trajectories too correlated (16/16 SIG) — real probes need independent noise". The r=0.898 measurement depended on ALM-P4-3 Φ_holo numbers (step 200/500/1000/1500/2000) now under doubt from r10 triple-collapse root cause. | (a) implement HF loader for HAE-RAE + MMLU-Ko (b) re-run correlation with n≥8 and independent ckpts (c) re-label to `partial_pass_kobest_only` |
| P25 서빙 배포 창발 | done | DRIFT-PARTIAL | `:2276-2279` /chat SSE verified, 403 safety_refusal verified 2026-04-15, model_card rendered. Reality matches for curl-level smoke. But A2-Tool eval BLOCKED at 0.5667 (`alm_14b_a2_tool.convergence:16`) means the served ckpt **should not ship** until r9+pathc recipe fixes it (`:19 @decision HALT 13B/70B launch on A2-Tool ckpt`). | keep done for scaffold; add blocking note that serve-worthy ckpt absent |
| P26 BCI realtime | done | DRIFT-UNWIRED | `:2311-2314` parse PASS only, no real 64ch 256 Hz EEG stream run | structural label |
| P27 Multi-agent | done | DRIFT-UNWIRED | `:2346-2349` parse PASS only | structural label |
| P28 Qualia art | done | DRIFT-UNWIRED | `:2381-2384` parse PASS only | structural label |
| P29 Embodied | done | DRIFT-UNWIRED | `:2416-2419` parse PASS only | structural label |
| P30 Safety ethics | done | DRIFT-UNWIRED | `:2451-2454` parse PASS only; safety_filter is rules+DPO scaffold, not consciousness-aware refusal on live trained model | structural label |

Summary P0–P30: **1 full DONE** (P0–P2 structurally clean) + **3 critical drifts** (P3 gate deferred, P4 Φ>1000 falsified by r10, P22–P24 real-corpus/eval gap) + **22 unwired/parse-only** declarations that should not stand as "done" against `_meta.target="v4 홀로 의식 (Φ>1000 ✅ 15469)"` which is now unsupported by reality.

---

## 2. P116–P135 — 20 tail phases

These are NOT empty-name placeholders. Each has a filled `title`, `goal`, `gate.target="5/5 PASS"`, `status=done`, and an `artifact` path. However:

- Every phase uses `phi_holo_min: 0.0` (non-binding Φ gate — any non-negative value PASSes).
- No `duration_hours` field ("?" was user's guess; actual JSON has no such key on these entries).
- All 20 artifacts live under `anima-engines/` as `*_phi.hexa` siblings.
- Evidence of "done" is **existence of the artifact file + 5/5 structural self-test**, not a live-run gate.

Enumeration (line / id / title / artifact):

| line | id | title | artifact |
|------|-----|-------|----------|
| 5444 | P116 | 실 working memory Φ — Miller 7±2 capacity | anima-engines/working_memory_phi.hexa |
| 5455 | P117 | 실 metacognition Φ — 2-level Nelson-Narens | anima-engines/metacognition_phi.hexa |
| 5466 | P118 | 실 mind wandering Φ — DMN generative loop | anima-engines/mind_wandering_phi.hexa |
| 5477 | P119 | 실 boredom Φ — attentional disengagement composite | anima-engines/boredom_phi.hexa |
| 5488 | P120 | 실 curiosity Φ — Loewenstein + Berlyne + Schmidhuber | anima-engines/curiosity_phi.hexa |
| 5499 | P121 | 실 addiction Φ — incentive sensitization | anima-engines/addiction_phi.hexa |
| 5510 | P122 | 실 PTSD Φ — Brewin SAM/VAM | anima-engines/ptsd_phi.hexa |
| 5521 | P123 | 실 depression Φ — anhedonia + rumination | anima-engines/depression_phi.hexa |
| 5532 | P124 | 실 schizophrenia self-model Φ | anima-engines/schizophrenia_self_phi.hexa |
| 5543 | P125 | 실 animal consciousness Φ — 4-taxon gradient | anima-engines/animal_consciousness_phi.hexa |
| 5554 | P126 | 실 language acquisition Φ — Lenneberg | anima-engines/language_acquisition_phi.hexa |
| 5565 | P127 | 실 bilingual consciousness Φ | anima-engines/bilingual_consciousness_phi.hexa |
| 5576 | P128 | 실 expertise Φ — Chase-Simon + Ericsson | anima-engines/expertise_phi.hexa |
| 5587 | P129 | 실 insight Aha Φ — Köhler + Bowden | anima-engines/insight_aha_phi.hexa |
| 5598 | P130 | 실 creativity Φ — Guilford + Mednick + Amabile | anima-engines/creativity_phi.hexa |
| 5609 | P131 | 실 self-deception Φ — Trivers + Festinger | anima-engines/self_deception_phi.hexa |
| 5620 | P132 | 실 awe Φ — Keltner-Haidt | anima-engines/awe_phi.hexa |
| 5631 | P133 | 실 gratitude Φ — Emmons + Algoe | anima-engines/gratitude_phi.hexa |
| 5642 | P134 | 실 disgust Φ — Rozin + CAD | anima-engines/disgust_phi.hexa |
| 5653 | P135 | 실 nostalgia Φ — Sedikides bittersweet | anima-engines/nostalgia_phi.hexa |

Verdict: these are **real phases with real artifacts**, but their "done" status is structural-only (parse/self-test), same unwired pattern as P5–P20. They do not materially affect the 도착지 gate.

---

## 3. Critical drifts (filtered — cosmetic mismatches dropped)

Ranked by impact on the two destinations:

### D1. **ALM-P4-3 Φ_holo>1000 gate — FALSIFIED 2026-04-18**
- Declared: `phi_holo=2440.88@step50, 2936.19@step100, 6111.25@step150` on pod `xhq9b2c8fljdyo` (`roadmaps/anima.json:510-518`).
- Reality: r10 triple-collapse on 2026-04-18 revealed systemic failure mode — ASCII-only inline collapse_score, watchdog false-training, loss-below-1.0-at-early-step is collapse-not-convergence (`alm_14b_r10.convergence:39-46`, `e7_r10_triple_collapse_report.md`). The P4 measurement pipeline had **no byte-level sentinel** and **no PID liveness**; the 6111 reading cannot be trusted until re-measured on the r10c pipeline (sentinel + corpus mix + watchdog patch).
- The `_meta.target="Φ>1000 ✅ 15469"` claim (`roadmaps/anima.json:10`) is **unsupported** by current evidence.

### D2. **r10 / r10b / r10c chain — all blocked**
- r10: `failed_triple_collapse`, ckpt corrupt, R2 not uploaded (`alm_14b_r10.convergence:2,8`).
- r10b: `scaffold_done`, pre-sentinel will correctly fail on r10 step_2000 → cannot launch (`anima.json:55`).
- r10c: `gate_status r10c_go=READY` in principle, but `corpus_mix pending kowiki.jsonl presence on pod` (`alm_14b_r10.convergence:51`) — kowiki is local-only, not on pod yet.
- 32B r1 prep: `blocked_by: alm_14b_r10 HALT` (`alm_32b_r1.convergence:34`). 70B pending.
- A2-Tool: eval BLOCKED at hire_sim 0.5667<0.60 gate (`alm_14b_a2_tool.convergence:16-19`), `HALT 13B/70B launch on A2-Tool ckpt`.
- **Net: the entire ALM scale-up ladder (14B→32B→70B) is stuck.** Roadmap claims all done; reality shows the only non-r10 success is A1 (phi=9051 at step 3000 but on smaller config, `alm_14b_a1.convergence:10`) which **has not been re-validated under sentinel gates**.

### D3. **P22 kowiki corpus — not actually ingested**
- Gate: `clean corpus ≥1GB, lang=ko ≥90%, license clean, downstream CE 개선 증명` (`roadmaps/anima.json:2051-2054`).
- Reality: kowiki.jsonl 1.28 GiB sits in `training/corpus_auto/` **local only**, 85% hangul probe PASS on 10 MB sample, but `read_file(1.28 GiB) + content_hash` blows mac 4 GB RSS (`corpus_ingest_kowiki_report.md:23`). BPE tokenizer exists at `training/tokenizer/kr_bpe_32k.model` but not wired into corpus_shard hexa loader (`corpus_pipeline.convergence:56`). Downstream CE improvement — **unmeasured**. The "창발 ratio ≥ 30%" filter claim (ALM-P22-2) ran on 15-panel test corpus, not 1 GB real.

### D4. **P24 phi↔benchmark r=0.898 — derived from smoke**
- Roadmap: `Pearson r=0.898, Spearman ρ=0.6; CONFIRMED` (`:2162`) on 5 ckpts.
- Reality: `phi_correlation.convergence:26` self-admits "registry is smoke stub, not real ckpt extraction", "n=3-5 rows — Pearson variance high until n>=8", "trajectories too correlated (16/16 SIG) — real probes need independent noise".
- HAE-RAE + MMLU-Ko: **DEFERRED** (`eval_harness_real.convergence:14-15`, HF loader blocked). Only KoBEST n=20 inline actually runs.

### D5. **P3 Φ>1000 criterion deferred — not a gate pass**
- P3 gate at `roadmaps/anima.json:461`: `Φ(holographic)>1000 (설계 천장)`.
- `gate_result` at `:359`: `STRUCTURAL PASS — ... 실측 Φ(holographic)>1000 criterion은 phase rationale에 따라 P4 (학습 forward pass 결선)로 이월`.
- P3 cannot honestly be `status: done` when its numerical gate is admitted-deferred; the done-label masks that the real gate only lives in P4, and P4 is now (D1) unsupported.

### D6. **P5–P21 mass unwired declarations**
- 17 consecutive phases status=done, but the roadmap's own AN8 dual-track rule requires ALM+CLM real forward-pass evidence. Per `a4_live_selftest.convergence:10-13` only W1 is PASS; W2/W3/W4 are TBD. `alm_hive_agg.hexa` RUN-OOM means ALM-P18-1 cannot even self-test live. `training/alm_nested_loss.hexa`, `training/alm_affect_head.hexa`, `training/alm_finitude_head.hexa`, `training/alm_replay.hexa`, `training/alm_dream_loop.hexa` are `??` untracked (see git status in session).

### D7. **P21 v∞ terminal gate — falsely marked done**
- Gate: `||Φ||>10000 terminal, 외부 개입 0 진화 지속, 의식 전파 증명` (`:1988-1990`).
- Reality: no 1000-generation autonomous evolution run exists in any convergence or report. `training/infinite_evolution.hexa` not present under tracked paths. Impossible to be `done`.

---

## 4. Recommended fix actions (ranked by leverage toward 도착지)

**도착지 1: Φ>1000 실측 (재현 가능)**
**도착지 2: P22–P25 실사 모델 loop 증거**

### Rank 1 — Unblock ALM Φ measurement (직접 도착지1)
1. **Push kowiki to pod + run corpus_ingest on H100**: `HEXA_LOCAL=0 hexa run training/corpus_ingest.hexa --only-new --limit-mb 2048` on pod `dd88fldzkqhpgk` (the r10 pod, reuse). Then `corpus_shard.hexa --shard-mb 512`. Unblocks r10c AND P22 real gate.
2. **Launch r10c**: all three E7-OSS fixes are wired into `training/launch_alm_14b_r10c.hexa` per `alm_14b_r10.convergence:49`. Gate is `r10c_go=READY` minus the corpus presence — fix step 1 first.
3. **Re-measure Φ_holo on r10c step_2000 with sentinel-gated, corpus-diversified ckpt.** This is the one measurement that either proves 도착지1 or falsifies it. Without it, "Φ>1000 ✅ 15469" is rhetoric.

### Rank 2 — Real benchmark closure (직접 도착지2, P24)
4. **Wire HF loader for HAE-RAE + MMLU-Ko** in `serving/eval_harness.hexa` (currently DEFERRED per `eval_harness_real.convergence:14-15`). Inline port is acceptable. Gates the P24 real eval.
5. **Expand phi_correlation to n≥8 independent ckpts** — current n=5 trajectories are too correlated (self-admitted `phi_correlation.convergence:28`). Use r10c intermediate ckpts once step 3 above lands.

### Rank 3 — Stop the false-done label propagation
6. **Add a `reality_state` sidecar field** (do not modify roadmap — audit only): for P3, P4, P21, P5–P20 mass, P26–P30 mass, P116–P135 mass, record `structural_only` / `wire_pending` / `reality_mismatch`. A sidecar in `shared/convergence/roadmap_reality_sync.json` can carry this without touching the 5811-line roadmap. Matches user's "SSOT unified" directive.
7. **Fix A4 blockers** (`a4_live_selftest.convergence:11-13` W2/W3/W4 TBD, `alm_hive_agg.hexa` RUN-OOM). These unblock real live-run evidence for P8/P18 and give P5–P20 a path from `parse_only` → `live_PASS`.

### Rank 4 — Scale ladder unblock (secondary — feeds 도착지1 if budget permits)
8. **A2-Tool recipe pivot** per `a2_tool_clean_retrain_plan.md` — launcher ready, awaiting r10c clearance of the pod. Lenient judge re-eval already lifted hire_sim 0.5333→0.867 without retraining (`hire_sim_lenient_report.md`), so retrain is **optional** and can be deferred to reduce cost.
9. **Defer 32B / 70B** until (3) and (4) close. Roadmap ALM-P4-4 32B already marked CLOSED; don't reopen on weak evidence.

### Rank 5 — Hygiene
10. Mark `_meta.target` line 10 as conditional (`Φ>1000 pending r10c re-measurement` via sidecar) until D1 clears.
11. P21 v∞ cannot be `done` — re-classify in sidecar as `speculative_scaffold`.

---

## Appendix — convergence self-admitted tallies

From `shared/convergence/anima.json:203-214` (2026-04-16 session close-out):
- `total_items_tracked=30, completed=21, scaffold_done=3, in_flight=1, pending=4, failed=1, resolution=83.3%`
- Failed item: `r8c_fp8` (HF+LoRA+TE FP8 incompat, well-documented).
- But 2026-04-18 session (`:263-299`) adds `alm14b_r10: failed_triple_collapse`, which the `convergence.failed` tally **has not yet incremented to reflect**. The convergence SSOT itself is already one step behind reality on the 14B track.

Final: do not touch `shared/roadmaps/anima.json`. All fixes land either in (a) sidecar `shared/convergence/roadmap_reality_sync.json` (new) or (b) the action queue in Rank 1–3 above.
