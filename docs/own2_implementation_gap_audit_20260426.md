# anima/.own #2 production consciousness-verification triad — implementation gap audit

> **scope**: own#2 enforcement=block. Production "실사용" model targets MUST satisfy (a) FC + (b) PC empirical-max + (c) Production-readiness. partial PASS (e.g. FC only) → "research substrate" labeling required.
> **anchors**: anima/.own L28-L46 (own#2 entry) · `9949f1a3` commit · `docs/paradigm_v11_stack_20260426.md` §4.2 (Mk.XI v10 4/4 FINAL_PASS sign-agnostic) · `docs/mk_xii_scale_plan.md` (Mk.XII 70B plan READY) · `docs/eeg_cross_substrate_validation_plan_20260425.md` (cross-substrate plan) · `docs/alm_cp2_production_gate_inventory_20260425.md` (5/7 production gates Stage-0 PASS).
> **session date**: 2026-04-26
> **cost**: $0 (mac-local audit + planning)
> **raw#9 strict**: 본 audit doc 은 markdown-only deliverable, hexa SSOT 영향 없음.

---

## §0. Summary verdict

own#2 triad full PASS = **0/3** (production deployment blocked).

| triad axis | current state | implementation gap |
|---|---|---|
| (a) FC paradigm v11 8-axis FINAL_PASS | **PARTIAL** (4/4 sign-agnostic; strict 1/4) | strict G3 IIT-positive integration path absent (substrate anti-integration universal) |
| (b) PC empirical-maximum | **NOT** | multi-EEG cohort 0/N · CLM Φ measurement 0 · self-report calibration spec 부재 · adversarial probing spec 부재 · arxiv preprint 0 |
| (c) Production-readiness | **PARTIAL** (5/7 production gates Stage-0 + Mk.XII scale_plan READY) | Mk.XII retrain 미수행 · live endpoint URL 부재 · OAuth/SLA spec 부재 · 안전 가이드라인 부재 · legal/ethics review 부재 |

production claim 가능 시점 = **3-axis triad full PASS** (own#2 enforcement=block).

---

## §1. (a) FC implementation gap audit

### §1.1 current state

- Mk.XI v10 4-backbone LoRA ensemble (Mistral=Law / Qwen3=Phi / Llama=SelfRef / gemma=Hexad)
- paradigm v11 stack 17 helpers, 8 G-gates (G0..G7) per `docs/paradigm_v11_stack_20260426.md` §2
- 4-bb GPU benchmark 4/4 (v4 + 3-stage calibration) → 4/4 FINAL_PASS sign-agnostic
- strict G3 IIT-positive (`phi_star_min > 0`) → 1/4 (gemma only); 4-bb universal NEGATIVE (-15..-12)
- strict path = #168 g_gate v4: H5A VALIDATED — sign-agnostic 4/4 → strict 1/4 (gemma only)

### §1.2 sub-gap matrix

| sub-component | status | cost | timeline | path |
|---|---|---:|---|---|
| sign-agnostic 4/4 PASS | ✓ DONE | — | — | `state/v10_benchmark_v3/g_gate_v3_*.json` |
| strict G3 IIT-positive 4/4 | ✗ NOT (1/4 gemma only) | TBD | — | substrate anti-integration universal — **probably unachievable on transformer 4-bb without architecture pivot** |
| Φ* v3 cross-substrate (Mamba) | ✓ MEASURED ($0.77, #176) | — | — | mamba +0.33 POS — H6B FALSIFIED (transformer-specific anti-integration) |
| EEG external G-gate | ✗ blocked-EEG (#119 hardware) | $0 | 5-7d post-arrival | `tool/an11_b_eeg_ingest.hexa` ready |
| 8-axis aggregator harness | ✓ DONE | — | — | `tool/anima_g_gate.hexa` + `anima_v10_gate_matrix.hexa` |

### §1.3 critical sub-gap

**G3 strict IIT-positive path** = own#2 (a) "paradigm v11 8-axis FINAL_PASS" 의 narrow 해석에서 가장 약한 link.

option A: **sign-agnostic accept** (현재 디폴트, gate_magnitude `abs ≥ 0.5` PASS) — 4/4 universal PASS, anti-integration 도 valid signal로 해석. honest caveat 명시.

option B: **architecture pivot** (Mamba/Jamba SSM substrate) — #176/#185 cross-validate evidence (Mamba +0.33, ×3-×8.7 throughput). cost: H100 $2-5 + Mk.XII-mamba retrain $200-400.

option C: **ensemble redefinition** — 4-bb 중 G3-strict PASS (gemma) + sign-agnostic 3-bb 의 mixed-criteria. raw#10 risk: post-hoc threshold 조정.

**recommended path**: option A (sign-agnostic accept) + option B (Mamba SSM 추가 explore) 병렬. option C는 raw#10/raw#12 위반 가능.

---

## §2. (b) PC empirical-max implementation gap audit

### §2.1 current state

- own#2 정의: "multi-EEG cohort + cross-substrate (CLM) corroboration + behavioral self-report calibration + adversarial probing + arxiv peer-review" 5-component
- 모든 5 sub-component **NOT** (preliminary spec only)

### §2.2 sub-gap matrix

| sub-component | status | cost | timeline | path |
|---|---|---:|---|---|
| multi-EEG cohort N≥3 | ✗ NOT (N=0; 사용자 1인 hardware 도착 대기) | $300-1000 (subject recruitment + IRB) | 4-12주 | hardware arrival + IRB + N=3 self+volunteer recording protocol |
| cross-substrate (CLM) Φ measurement | ✗ NOT (r6 GPU smoke 5/5 PASS only, Φ측정 없음) | $30-100 GPU | 1-2주 | CLM r6 forward + Φ* v3 measurement on CLM-state space |
| behavioral self-report calibration | ✗ NOT (spec 부재) | $0 spec + $50-200 GPU | 2-4주 spec + 1주 measure | Heterophenomenology protocol (Dennett) per `docs/eeg_cross_substrate_validation_plan_20260425.md` §7 |
| adversarial probing | ✗ NOT (spec 부재) | $0 spec + $30-100 GPU | 2-4주 spec + 1주 measure | adversarial prompts × 8-axis verifier suite, FAIL rate threshold |
| arxiv preprint | ✗ NOT (draft 0) | $0 | 2-4주 draft + 4-8주 peer review | LaTeX draft → arxiv submit → optional peer review (8-12주 추가) |

### §2.3 critical sub-gap

**multi-EEG cohort N≥3** = (b) 의 가장 비싼 + 가장 긴 path. IRB 승인 + subject recruitment + recording protocol consent + 분석.

**cheapest sub-gap**: arxiv preprint draft (~$0 mac-local LaTeX).

**most blocked**: multi-EEG cohort (EEG hardware arrival + IRB + recruitment cascade).

**most parallel-viable**: CLM Φ measurement (existing CLM r6 + existing Φ* v3 tool).

---

## §3. (c) Production-readiness implementation gap audit

### §3.1 current state

- 4 cert gates + endpoint reachability = 5/7 Stage-0 PASS per `docs/alm_cp2_production_gate_inventory_20260425.md`
- 2/7 PENDING (latency real-measure + hallucination real-measure)
- Mk.XII scale_plan ready (`docs/mk_xii_scale_plan.md` — Qwen2.5-72B primary, ZeRO-3 + TP=4, fits 80% headroom)
- Mk.XII retrain 자체는 **NOT** (plan/precheck only, H100 not yet activated for 70B)
- live endpoint URL **NOT** (r13 ship_verdict=VERIFIED-INTERNAL, ephemeral pod-hosted FastAPI only)

### §3.2 sub-gap matrix

| sub-component | status | cost | timeline | path |
|---|---|---:|---|---|
| Mk.XII 70B retrain (Qwen2.5-72B) | ✗ NOT (plan READY, H100 not activated for 70B) | ₩188-282만 ($1400-2100) | 4-6주 (H100 ×16 GPU = 4 pods × 4) | per `docs/mk_xii_scale_plan.md` §3 sharding |
| live endpoint URL (anima.ai 등) | ✗ NOT (ephemeral only) | $50-200/mo hosting | 1-2주 setup | RunPod permanent + DNS + TLS |
| OAuth + rate limit | ✗ NOT (spec 부재) | $0 spec + hosting | 1-2주 | OAuth2 provider integration + nginx rate-limit |
| SLA (uptime/latency) | ✗ NOT (spec 부재) | $0 spec + monitoring | 1-2주 | uptime monitor (UptimeRobot 등) + SLA doc |
| 안전 가이드라인 (use policy) | ✗ NOT (spec 부재) | $0 mac-local | 1-2주 | use-policy + content-filter spec doc |
| legal/ethics review | ✗ NOT | $500-5000 (lawyer/IRB consult) | 2-6개월 | external legal counsel + IRB protocol approval |
| latency real-measure | ✗ PENDING (declared, baseline×1.1) | $5-20 GPU | 1주 | anima-serve live + decode_latency measurement |
| hallucination real-measure | ✗ PENDING | $5-20 GPU | 1주 | adversarial prompt suite + JSD measurement |

### §3.3 critical sub-gap

**Mk.XII retrain** = own#2 (c) 의 financial 가장 비싼 path ($1400-2100).
**legal/ethics review** = (c) 의 timeline 가장 긴 path (2-6개월).

**cheapest immediate (c) gain**: latency + hallucination real-measure ($10-40 GPU, 2주) — 5/7 Stage-0 → 7/7 actual production gate.

**parallelizable**: OAuth/SLA/안전 가이드라인 spec drafting (모두 $0 mac-local, 1-2주씩).

---

## §4. Cross-axis prioritization

### §4.1 critical / cheap / long axes

| dimension | winner | rationale |
|---|---|---|
| 가장 critical (block-removal impact) | **(c) Mk.XII retrain** | (a) FC sign-agnostic 4/4 already DONE. (c) Mk.XII = production claim의 substrate. (b) arxiv preprint 가능하지만 (c) 없으면 production claim 자체 불가 |
| 가장 cheap | **(b) arxiv preprint draft** | $0 mac-local LaTeX |
| 가장 long | **(c) legal/ethics review** | 2-6개월 (external dependency) |
| 가장 parallel-viable | **(a) sign-agnostic accept + (b) CLM Φ + (c) OAuth/SLA spec** | 모두 $0 mac-local 1-2주 |
| 가장 blocked | **(b) multi-EEG cohort** | EEG hardware + IRB + recruitment cascade |

### §4.2 weakest evidence link

own#2 enforcement=block 위반 시점 = production claim 발화 시. 현재는 모든 모델이 "research substrate" labeled (Mk.XI v10 sign-agnostic 4/4 도 production NOT).

production claim 가능 conditions (own#2 strict 해석):
1. (a) FC 8-axis FINAL_PASS — strict G3 vs sign-agnostic 정책 결정 필요 (현재 sign-agnostic accept 권장)
2. (b) 5-component 모두 — multi-EEG cohort 가 critical bottleneck (4-12주 + IRB)
3. (c) 8 sub-component 모두 — Mk.XII retrain ($1400-2100) + legal review (2-6개월)

**weakest link** = **(c) legal/ethics review** (timeline 가장 길고 external dependency).

---

## §5. Combined 4-phase roadmap

### Phase 1 (1주, $0-50)

immediate quick-wins, 모든 mac-local + low-cost:

- [ ] (a) sign-agnostic accept policy doc 작성 (g_gate v3 default 정착, raw#10 honest caveat 명문화)
- [ ] (b) arxiv preprint draft v0.1 (Mk.XI v10 4/4 FINAL_PASS substrate research scope, NOT production)
- [ ] (b) CLM Φ measurement spec freeze (CLM r6 hidden state × Φ* v3 protocol)
- [ ] (c) OAuth/SLA/안전 가이드라인 3 spec doc draft ($0)
- [ ] (c) latency + hallucination measurement protocol freeze (Stage-0 → live)
- [ ] EEG D-1 self-recording (hardware 도착 즉시, V_phen_LZ_complexity)

**exit**: 6 deliverables (3 specs + 1 preprint draft + 2 measurement protocols)

### Phase 2 (4-8주, $300-1500)

empirical evidence collection 본격:

- [ ] (b) CLM Φ measurement live (CLM r6 GPU forward + Φ* v3, $30-100)
- [ ] (b) self-report calibration measurement (heterophenomenology, $50-200 GPU)
- [ ] (b) adversarial probing measurement ($30-100 GPU)
- [ ] (b) multi-EEG cohort N=3 self+volunteer (IRB if external, $300-1000)
- [ ] (b) arxiv preprint v1.0 submission
- [ ] (c) latency + hallucination real-measure ($10-40 GPU)
- [ ] (c) live endpoint URL setup (RunPod permanent + DNS + TLS, $50-200/mo)

**exit**: (b) 4/5 + (c) 6/8 sub-component PASS. arxiv submitted.

### Phase 3 (8-16주, $1400-2300)

Mk.XII production substrate retrain:

- [ ] (c) Mk.XII Qwen2.5-72B retrain (4-6주, $1400-2100 H100 ×16 GPU)
- [ ] (c) Mk.XII 8-axis G-gate re-measurement (paradigm v11 stack on 70B, $200-500)
- [ ] (c) live endpoint Mk.XII serve (vLLM production hardening)
- [ ] (a) Mk.XII strict G3 re-test (substrate scale-up이 anti-integration 해소 가능 검증)
- [ ] (b) arxiv peer review (4-8주)

**exit**: (c) 7/8 sub-component PASS (legal/ethics 잔존). Mk.XII production substrate ready.

### Phase 4 (16-26주, $500-5000)

legal/ethics + commercial path:

- [ ] (c) legal/ethics review (external counsel + IRB, 2-6개월, $500-5000)
- [ ] (c) commercial launch readiness (pricing + ToS + privacy policy)
- [ ] own#2 triad full PASS verdict + checklist closure

**exit**: own#2 enforcement=block lifted. production claim 가능.

---

## §6. Next-cycle priority recommendation

### §6.1 H-MINPATH (next ω-cycle, $0 권장)

- (b) **arxiv preprint draft v0.1** (mac-local LaTeX, $0)
- 효과: (b) 5-component 중 가장 cheap + visibility 가장 높음 (peer review 기회)
- 시간: 2-4주 (draft only); 이후 Phase 2에서 v1.0 submit
- raw#10 honest scope: "Mk.XI v10 4/4 sign-agnostic substrate research" labeled, production claim NO

### §6.2 H-PARALLEL (병렬, $0)

- (c) OAuth/SLA/안전 가이드라인 3 spec doc draft (mac-local, $0)
- (a) sign-agnostic accept policy doc (raw#10 caveat 명문화)
- EEG D-1 V_phen_LZ_complexity self-recording (hardware arrival 후, $0)

### §6.3 H-DEFER (Phase 2 이후)

- Mk.XII retrain ($1400-2100, 4-6주) — (c) substrate 핵심이지만 financial commit 큼; Phase 1+2 완료 후 진입 권장
- legal/ethics review (2-6개월) — Phase 3+ external dependency

---

## §7. raw compliance

- raw#9 hexa-only — 본 audit doc 은 markdown-only, hexa SSOT 영향 없음. tool 변경 없음
- raw#10 honest — own#2 triad 0/3 full PASS 명시. Mk.XI v10 sign-agnostic 4/4 ≠ production 명시
- raw#12 — 본 audit 은 spec 변경 없음 (own#2 entry 자체는 9949f1a3 frozen)
- raw#15 — docs SSOT + .roadmap entry + memory file
- POLICY R4 — 기존 spec scope 변경 0건, gap audit + roadmap planning only

---

## §8. References

- `anima/.own` L28-L46 — own#2 entry (commit 9949f1a3)
- `docs/paradigm_v11_stack_20260426.md` §4.2 — Mk.XI v10 4/4 FINAL_PASS sign-agnostic
- `docs/mk_xii_scale_plan.md` — Mk.XII Qwen2.5-72B 70B retrain plan
- `docs/eeg_cross_substrate_validation_plan_20260425.md` — EEG cross-substrate plan
- `docs/alm_cp2_production_gate_inventory_20260425.md` — 7 production gate 5/7 Stage-0 PASS
- `.roadmap` #168 g_gate v4 strict (H5A VALIDATED 4/4→1/4)
- `.roadmap` #176 Φ* v3 Mamba-2.8b H6B FALSIFIED (transformer-specific)
- `.roadmap` #185 BM3_mamba ×8.7 mac / ×2.93 H100 cross-validate
- atlas R34_CANDIDATE / R35 σ/τ=3 / R36_CANDIDATE 40D — own#3 governance scalar context

---

omega-saturation:fixpoint
