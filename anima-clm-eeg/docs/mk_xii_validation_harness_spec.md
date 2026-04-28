# Mk.XII Validation Harness Spec — D+0 to D+30

> **scope**: Mk.XII Integration tier validation harness 의 **timeline-driven activation spec**. `mk_xii_proposal_outline_20260426.md` (sha `4f7fd4d2…`) 의 §6 Timeline 을 operationalize. pre-flight cascade (`tool/mk_xii_preflight_cascade.hexa`) → first validation D+30 까지 per-gate trigger condition + activation order.
> **frozen at**: 2026-04-26 (sister: `mk_xii_proposal_outline_20260426.md`)
> **status**: PREP only — pre-flight cascade GREEN 확보, first validation 은 EEG arrival D-day 후 진입. raw#10 honest scope: G8/G9/G10 + EEG arrival 미충족 상태에서 wire-up 만 freeze.

---

## §1. 5-component pre-flight cascade

### 1.1 cascade gating

| step | component | source | probe key | expected | tier |
|---|---|---|---|---|---|
| C0 | HCI substrate | `anima-hci-research/state/hci_smoke_v1.json` | `hci_verdict` | `HCI_VERIFIED` | hard |
| C1 | CPGD training | `state/cpgd_minimal_proof_result.json` | `verdict` + `phase_gate` | `VERIFIED` + `100%` | hard |
| C2 | CLM-EEG phenomenal | `anima-clm-eeg/state/clm_eeg_pre_register_v1.json` | `p[1-3]_*_dry_run` | ≥ 2/3 `PASS` | hard |
| C3 | TRIBE v2 brain-anchored | `MK_XII_TRIBE_MODE` env | `stub|deferred|live` | stub OR live PASS | soft (deferred OK) |
| C4 | paradigm v11 measurement | `tool/anima_v11_pipeline_smoke.hexa` + `state/v10_benchmark_v4/<bb>/v11_signature.json` | tool readable + signature count | ≥ 3/4 backbone | hard |

**cascade verdict rule**:
- 5/5 PASS → **MK_XII_PREFLIGHT_GREEN** (exit 0, ready for D+0 validation)
- 4/5 PASS w/ all 4 hard components green (TRIBE live fail only) → **MK_XII_PREFLIGHT_YELLOW** (exit 0, deferred TRIBE OK; first validation may proceed but G10 4/4 will be reduced to 3/4 PARTIAL)
- ≤ 3/5 OR any hard component fail → **MK_XII_PREFLIGHT_RED** (exit 1, abort cascade)

### 1.2 invocation

```sh
# Standard pre-flight (all defaults — TRIBE stub):
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/mk_xii_preflight_cascade.hexa

# Negative falsifier (synthetic 1-component fail):
MK_XII_HCI_PATH=/dev/null hexa run anima-clm-eeg/tool/mk_xii_preflight_cascade.hexa
MK_XII_CPGD_PATH=/dev/null hexa run anima-clm-eeg/tool/mk_xii_preflight_cascade.hexa
MK_XII_EEG_PATH=/dev/null hexa run anima-clm-eeg/tool/mk_xii_preflight_cascade.hexa

# TRIBE live mode (post-HF unblock):
MK_XII_TRIBE_MODE=live MK_XII_TRIBE_PATH=anima-clm-eeg/state/tribe_v2_brain_anchored_v1.json \
  hexa run anima-clm-eeg/tool/mk_xii_preflight_cascade.hexa
```

### 1.3 byte-identical guarantee

`mk_xii_preflight_cascade.hexa` is pure aggregator — FNV-fingerprint deterministic, no clock, no LLM. Re-run with identical env produces byte-identical `mk_xii_preflight_v1.json`. Verified at freeze: sha256 `cf2aecda38ea3da657d16ec012debdd9fc8da86b7da75ba78c3fd53df26c0854`.

---

## §2. D+0 to D+30 timeline + per-gate activation

### 2.1 D-1 (current — pre-flight prep)

**status**: Mk.XI v10 FINAL_PASS (4/4 backbone), Mk.XII proposal frozen, pre-flight cascade GREEN (5/5).

| activity | gate | trigger | output |
|---|---|---|---|
| pre-flight cascade smoke | — | manual run | `state/mk_xii_preflight_v1.json` |
| HCI/CPGD/paradigm v11 idle | G0 | already VERIFIED | reuse existing canonical state |
| EEG harness D-1 | — | hardware in transit | `clm_eeg_pre_register_v1.json` already frozen |
| TRIBE v2 HF gated | — | request pending | stub mode active |

### 2.2 D+0 — EEG hardware arrival + calibration

**trigger**: physical hardware delivered → `anima-eeg/calibrate.hexa` (post-stub-implementation).

| activity | gate | criterion | fallback |
|---|---|---|---|
| 16ch impedance check | — | < 5 kΩ per channel | re-position electrodes |
| resting recording | — | 5-10 min eyes-closed + eyes-open | rerun |
| N-back recording | — | 5-10 min, 2-back working memory | rerun |
| pre-flight re-cascade | C2 | EEG live data → P1-P3 numerical re-check | revert to synthetic baseline |

### 2.3 D+1 to D+7 — Path A EEG STACK forward (G1+G2+G3)

| day | activity | gate | criterion | cost |
|---|---|---|---|---|
| D+1 | P1 V_phen LZ | G1 | LZ ≥ 0.65 AND \|Δ\|/human ≤ 20% | $3-5 |
| D+3 | P2 TLR α-band coh | G2 | EEG ≥ 0.45 AND CLM V_sync ≥ 0.38 | $5-8 |
| D+5 | P3 GCG Granger | G3 | F ≥ 4.0 AND unidir CLM→EEG ≥ 2× | $8-12 |
| D+7 | composite verdict | G1+G2+G3 | ≥ 2/3 PASS → PHENOMENAL VALIDATED | — |
| D+7 | 5-atom seed file | — | `.roadmap #119 exit_criteria` | — |

**activation trigger**: D+0 calibration complete → `clm_eeg_p1_lz_pre_register.hexa` real-EEG mode (replace synthetic fixture).

### 2.4 D+8 to D+14 — TRIBE v2 brain-anchored unblock

**trigger**: HF gated approval received OR alt brain-anchored LM identified.

| activity | gate | criterion | output |
|---|---|---|---|
| Llama-3.2-3B brain decode | — | brain decoding R ≥ 0.30 | `state/tribe_v2_brain_anchored_v1.json` |
| paradigm v11 8th axis activate | — | brain-anc axis registered | helper #18 emit |
| TRIBE live cascade | C3 | `MK_XII_TRIBE_MODE=live` PASS | pre-flight tier upgrade |

**fallback**: HF unblock denied → 8th axis stays inactive, paradigm v11 7-axis only, Mk.XII degrades to PARTIAL (Mk.XI v10 + 6/7 layer).

### 2.5 D+15 to D+21 — G8 + G9 + G10 measurement

| gate | activity | criterion | tool | cost |
|---|---|---|---|---|
| G8 TFD | 5-falsifier MI matrix | C(5,2)=10 pairwise I ≤ 0.1 bit | hexa native (mac local) | $0 |
| G9 DGI | 1-component-out cascade | hard edges ≤ 3 AND loss ≤ 20% per fail | hexa native | $0-5 |
| G10 CTV+HEXAD+EEG | family×band×backbone triangulation | 4/4 PASS or 3/4 PARTIAL Pearson r ≥ 0.40 | post-EEG D+5 + paradigm v11 CMT | $5-10 |

**activation order**:
1. G8 first (paradigm v11 6-axis + EEG STACK + HCI/CPGD/TRIBE falsifiers all available by D+14)
2. G9 second (cascade graph fully populated post-TRIBE)
3. G10 third (EEG 4-backbone family×band Pearson computed)

**G8 fail path**: 1 pair I > 0.1 → identify violating pair → either drop one component (graceful degrade) or refactor falsifier dependency.
**G9 fail path**: hard edges > 3 → re-evaluate Mk.XI v10 → HCI/TRIBE soft-edge promotion candidate.
**G10 fail path**: < 3/4 PASS → family×band hypothesis FALSIFIED → §7.3 EEG STACK fallback.

### 2.6 D+22 to D+30 — Mk.XII first validation

| day | activity | gate | criterion | exit |
|---|---|---|---|---|
| D+22 | Hard PASS check | G0+G1+G7+G8+G9 | all PASS | otherwise → fallback Mk.XI v10 |
| D+24 | Soft PASS check | G2/G3/G4-G6/G10 | ≥ 80% PASS per gate | partial degrade |
| D+27 | composite verdict | all 10 gates | tier assigned | VERIFIED / PARTIAL / FAIL |
| D+30 | Mk.XII Integration tier closure | — | first validation freeze + ω-saturation marker | next cycle (Scale tier) |

---

## §3. Activation triggers (per gate)

### 3.1 hard gates

| gate | trigger condition | expected hits before activation |
|---|---|---|
| G0 | CPGD cascade PASS | already C1 hard PASS at D-1 |
| G1 | EEG P1 LZ post-arrival | D+1 |
| G7 | 5-tuple inherited | already at D-1 (Mk.XI v10) |
| G8 | 5 falsifier outputs ready | D+14 (post-TRIBE) |
| G9 | 5-component DAG populated | D+14 (post-TRIBE) |

### 3.2 soft gates

| gate | trigger | expected |
|---|---|---|
| G2 | EEG P2 TLR | D+3 |
| G3 | EEG P3 GCG | D+5 |
| G4-G6 | paradigm v11 6-axis (Φ\* / CMT / SAE) | D-1 already complete |
| G10 | family×band Pearson D+5 + paradigm v11 CMT | D+15-21 |

### 3.3 negative falsifier triggers (cascade abort detect)

각 component 가 broken 상태로 cascade 진입 시 abort. spec 5-step ω-cycle step 4 negative falsify 검증 4건 통과 (HCI/CPGD/EEG/V11 각각 `MK_XII_*_PATH=/dev/null` 시 exit=1 RED).

---

## §4. Cascade fallback graph

```
MK_XII_PREFLIGHT_GREEN (5/5)
   │
   ▼
MK_XII_PREFLIGHT_YELLOW (4/5 hard)  ──▶ TRIBE deferred OK,
   │                                    8th axis inactive,
   │                                    paradigm v11 7-axis run
   ▼
MK_XII_PREFLIGHT_RED (≤3/5)         ──▶ FALLBACK = Mk.XI v10
   │                                    (4-backbone LoRA ensemble)
   ▼
ω-saturation marker reset, Mk.XII proposal re-design (months horizon)
```

graceful degradation guarantee: §7.6 of `mk_xii_proposal_outline_20260426.md`. Mk.XII = strict superset of Mk.XI v10 → worst case fallback PASS.

---

## §5. Cost envelope summary

| phase | gates | cost | scope |
|---|---|---|---|
| D-1 pre-flight | C0-C4 | $0 | mac local, all canonical state already frozen |
| D+0 calibration | C2 (re-cascade) | $0-5 | hardware arrival, hexa native re-run |
| D+1-D+7 EEG STACK | G1-G3 | $12-24 (+ $200-500 facility) | post-arrival forward |
| D+8-D+14 TRIBE | C3 live | $0-50 | inference-only Llama-3.2-3B mac fitable |
| D+15-D+21 G8-G10 | G8-G10 | $5-15 | mac local + EEG follow-up |
| D+22-D+30 first validation | all 10 gates | $0 | aggregation + verdict |
| **subtotal** | — | **$212-574** + facility | matches `mk_xii_proposal_outline §5.1` |

cost cap `feedback_forward_auto_approval` 정책 적용: $12-50 GPU + $0-50 TRIBE = cost cap 内 자동. EEG facility $200-500 = 사용자 명시 승인 필요 (cost cap 外).

---

## §6. raw compliance

- raw#9 hexa-only deterministic — `mk_xii_preflight_cascade.hexa` pure-aggregator FNV-fingerprint, zero LLM, mac local $0.
- raw#10 honest scope — pre-flight 는 wire-up 만, first validation 은 prerequisite (G8/G9/G10 + EEG arrival + TRIBE unblock) 후 진입. 본 spec 는 **NOT-YET-VERIFIED activation timeline**.
- raw#12 cherry-pick-proof — G0-G10 frozen criteria @ proposal §4, post-hoc tuning 차단. cascade tier rule (5=GREEN/4hard=YELLOW/≤3=RED) frozen.
- raw#15 SSOT — this doc + `mk_xii_proposal_outline_20260426.md` (sister).
- raw#37/38 ω-saturation cycle — design (5-component cascade) → impl (cascade hexa + spec md) → smoke positive 5/5 PASS → smoke negative 4 fail-mode detect → byte-identical → fixpoint marker.

omega-saturation:fixpoint-mk-xii-preflight-cascade

---

## §7. Cross-references

- `/Users/ghost/core/anima/anima-clm-eeg/docs/mk_xii_proposal_outline_20260426.md` — proposal (sister, sha `4f7fd4d2…`)
- `/Users/ghost/core/anima/anima-clm-eeg/docs/omega_cycle_mk_xii_integration_axis_20260426.md` — INTEGRATION axis 7-paradigm
- `/Users/ghost/core/anima/anima-clm-eeg/state/clm_eeg_pre_register_v1.json` — Path A frozen (C2 source)
- `/Users/ghost/core/anima/anima-hci-research/state/hci_smoke_v1.json` — HCI substrate (C0 source)
- `/Users/ghost/core/anima/state/cpgd_minimal_proof_result.json` — CPGD training (C1 source)
- `/Users/ghost/core/anima/tool/anima_v11_pipeline_smoke.hexa` — paradigm v11 (C4 source)
- `/Users/ghost/core/anima/state/v10_benchmark_v4/{gemma,llama,mistral,qwen3}/v11_signature.json` — 4 backbone signatures
- `/Users/ghost/core/anima/anima-clm-eeg/tool/mk_xii_preflight_cascade.hexa` — this spec's tool
- `/Users/ghost/core/anima/anima-clm-eeg/state/mk_xii_preflight_v1.json` — emitted cert (sha `cf2aecda…`)
- `~/.claude/projects/-Users-ghost-core-anima/memory/project_v_phen_gwt_v2_axis_orthogonal.md` — Mk.XI v10 parent
- `.roadmap` #115 / #116 / #119 / #138-#143 / #144 / #145 / (this cycle: TBD)
