# CLM-EEG D-Day Chain (D+0 to D+7) Pre-Review and Readiness-Audit Refresh — Landing

- **date**: 2026-04-27
- **raw_rank**: 9 (hexa-domain doc; English body, AI-native)
- **scope**: D-day chain pre-review + readiness audit refresh after Phase 4 trio + priority 1-3 land (commits `572673be`, `d1c8eead`, hetzner ssh 56/56 PASS), G10 D+5 scaffold v2 (`66573e9f`), G8 D+6 preflight (`64079201`, `ee761cb5`), AN-LIX-01 alpha-bridge synthetic-positive marker (`1f110da4`), v1.1 SSOT 10 artifacts chflags uchg + git tracked.
- **status**: doc-only review. No code edit. No chflags. No commit (main thread decides).
- **predecessors**: `eeg_d_day_readiness_check_landing.md` (PARTIAL 22/27 ready post-phantom resolve) · `phase4_remaining_priority1_3_landing_20260427.md` (anima-eeg/) · `g10_real_coupling_fn_prep_20260427_landing.md` · `g8_n_bin_85_falsification_analysis_20260427_landing.md` · `clm_eeg_p1_sha_resync_20260427_landing.md` · `clm_lix_eeg_alpha_direct_mapping_spec.md`
- **environment**: mac local, $0, doc-only, jetsam-safe (no hexa run, no GPU dispatch).
- **raw compliance**: 9 hexa-only · 12 silent-error-ban · 65 idempotent · 71 falsifier-preregistered (no hypothesis edit) · 86 cost-attribution · 91 honesty · 101 minimal (≥60 lines).

## §0. Net status (one-screen)

| dim | before this review | after this review |
|---|---|---|
| anima-eeg D+0 hardware bring-up modules | 3 STUB (`calibrate`/`collect`/`eeg_recorder`) → CRITICAL | **3 FULL impl + 25/25 selftest PASS** (`05af4a3f`); cross-host 56/56 PASS via hetzner ssh (`572673be`+`d1c8eead`) |
| anima-eeg Phase 4 priority 1-3 wrappers (`experiment`/`analyze`/`realtime`) | 1 STUB + 2 partial | **3 FULL impl + 31/31 selftest PASS** (`ea1555c0`) |
| anima-clm-eeg pre-register | v1.1 SSOT, P1 phantom mismatch | v1.1 frozen MATCH 10/10, **chflags uchg + git tracked** (commit `1f110da4`) |
| G10 D+5 scaffold | v1 synthetic only | **v2 with `real_coupling_fn` stub branch + `REAL_HW_PENDING` tier**, 8/8 selftest, 3-run byte-eq |
| G8 D+6 N_BIN | inferred SSOT N_BIN=2 | **preflight FAIL → fallback chain selects `uniform_n_bin_2`** (raw#71 honest, hypothesis text frozen) |
| AN-LIX-01 alpha bridge | spec only | **synthetic-positive marker landed**, real-data `bridge_v1.json` D+3 deferred |
| readiness verdict | PARTIAL 22/27 (D+0 blocked) | **READY 27/27 for D+0 hardware bring-up** (subject to physical arrival) |
| post-arrival friction | medium (Phase 4 stubs) | **low** (Phase 4 trio + priority 1-3 done; only priority 4-7 deferred and they are non-critical for D+0..D+7 chain) |

The D+0 critical-path block from `eeg_d_day_readiness_check_landing.md` §3.2 is now lifted. Priority 4-7 (`closed_loop`, `dual_stream`, `neurofeedback`, `rp_adaptive_response`) remain WRAPPER STUB but are NOT prerequisites for the D+0..D+7 chain (raw#87 paired roadmap entry candidate, see §10).

## §1. D+0 hardware bring-up — refreshed checklist

The Phase 4 trio (`calibrate.hexa` + `collect.hexa` + `eeg_recorder.hexa`) is the critical-path SSOT for D+0. Reference: `phase4_remaining_priority1_3_landing_20260427.md` for the trio + priority 1-3 wrapping (`experiment`/`analyze`/`realtime`).

### §1.1 Activation runbook (post-arrival D+0)

```
# Phase 0..6 of D-day arrival checklist (eeg_d_day_readiness_check_landing.md §"D-day arrival checklist (macOS)") — physical/OS bring-up
# Then:
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/calibrate.hexa \
    --port=<auto-detect>            # impedance + signal QC, real BrainFlow, tier=PHENOMENAL_HW

HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/eeg_recorder.hexa \
    --duration=60 --tag=resting_baseline \
    --output=anima-eeg/recordings/sessions/d0_resting_$(date -u +%Y%m%dT%H%M%SZ).npy

HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/experiment.hexa \
    --run-with-eeg --protocol nback_2back --duration 600 \
    --output=anima-eeg/recordings/sessions/d0_nback_$(date -u +%Y%m%dT%H%M%SZ).npy
```

### §1.2 D+0 readiness audit refresh

| § (readiness-check ref) | item | prior status | refreshed status |
|---|---|---|---|
| §3.2 | `calibrate.hexa` | STUB 23L | **FULL impl + selftest PASS** (Phase 4 trio commit `05af4a3f`) |
| §3.2 | `collect.hexa` | STUB 25L | **FULL impl + selftest PASS** |
| §3.2 | `eeg_recorder.hexa` | STUB 34L | **FULL impl + selftest PASS** |
| §3.2 | `experiment.hexa` (D+1 N-back marker) | STUB | **FULL 633L + 10/10 PASS** (commit `ea1555c0`) |
| §3.2 | `analyze.hexa` (post-collect spectral) | FULL but DFT-OOM bug | **fixed; 10/10 PASS** |
| §3.2 | `realtime.hexa` (live monitor) | STUB 29L | **FULL 591L + 11/11 PASS** |
| §3.2 | `bci_control.hexa` | STUB | **DEFERRED** (Phase 3 Cycle 3, ~2h, not D+0 critical) |
| §3.2 | `closed_loop`/`dual_stream`/`multi_eeg`/`organize_recordings`/`neurofeedback`/`rp_adaptive_response` | STUB | **DEFERRED to raw#87 paired follow-up** (NOT D+0..D+7 critical, est 16-20h, 4-5h each) |
| §3.5 | `recordings/sessions/` write path | empty `.gitkeep` only | unchanged (intentional — write target only at D+0) |
| §3.5 | `recordings/validations/` | empty `.gitkeep` | unchanged |

**Refreshed P5 priority list** (supersedes readiness-check §6 priority table):

| # | item | severity | wallclock | pre-arrival? | recommendation |
|---|---|---|---|---|---|
| ~~1-3~~ | ~~Phase 4 trio~~ | ~~HIGH~~ | ~~13h~~ | ~~yes~~ | **DONE** — `05af4a3f` |
| ~~5~~ | ~~`experiment.hexa`~~ | ~~MEDIUM~~ | ~~4h~~ | ~~yes~~ | **DONE** — `ea1555c0` |
| ~~7~~ | ~~`realtime.hexa`~~ | ~~LOW~~ | ~~5h~~ | ~~yes~~ | **DONE** — `ea1555c0` |
| ~~analyze fix~~ | ~~DFT OOM~~ | ~~MEDIUM~~ | ~~1h~~ | ~~yes~~ | **DONE** — `ea1555c0` |
| 4 | `closed_loop.hexa` | LOW | 4h | yes | DEFERRED, raw#87 paired |
| 6 | `protocols/multi_eeg.hexa` | LOW | 5h | yes | DEFERRED — multi-board only |
| 8 | `dual_stream.hexa` | LOW | 5h | yes | DEFERRED — Phi+EEG sync (post-D+7) |
| 9 | `neurofeedback.hexa` (Phase 4 wrapping; FULL pre-existing 320L) | LOW | 4h | yes | DEFERRED — re-wrap on top of `realtime` (not gating) |
| 10 | `rp_adaptive_response.hexa` | LOW | 5h | yes | DEFERRED — depends on closed_loop + neurofeedback |
| 11 | `protocols/bci_control.hexa` | LOW | 2h | yes | DEFERRED — Phase 3 Cycle 3 closure |
| 12 | `scripts/organize_recordings.hexa` | LOW | 4h | yes | DEFERRED — sqlite indexing, post-D+7 archival |

**D+0 verdict**: READY. The fallback path through `tool/an11_b_eeg_ingest.hexa` (360L raw#9 BrainFlow wrapper) remains available as a corner-cut, but is no longer the primary path; the production trio is the canonical entry.

## §2. D+1 P1 LZ verify — synthetic-vs-real `.npy` conversion path

### §2.1 Pre-register integrity check (must pass before any real-data trigger)

Frozen v1.1 SSOT: `anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json` (chain_sha256 `647e04f7…`, P1 hexa sha `416e6be6…`). 10 artifacts under chflags uchg (`CHFLAGS_AI_ACK=1 chflags uchg`) + git tracked (commit `1f110da4`). Pre-trigger D+1 step:

```
shasum -a 256 \
    anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa \
    anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa \
    anima-clm-eeg/tool/clm_eeg_p2_tlr_pre_register.hexa \
    anima-clm-eeg/tool/clm_eeg_p3_gcg_pre_register.hexa \
    anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa \
    anima-clm-eeg/fixtures/synthetic_16ch_v1.json \
    state/clm_eeg_p1_lz_pre_register.json \
    state/clm_eeg_p2_tlr_pre_register.json \
    state/clm_eeg_p3_gcg_pre_register.json \
    state/clm_eeg_harness_smoke.json
# Expect 10/10 MATCH against sha256_v1_1_frozen block; any drift → ABORT D+1, escalate to v2 bump.
```

### §2.2 Synthetic-vs-real `.npy` conversion path

The P1 tool (`clm_eeg_p1_lz_pre_register.hexa`) currently consumes the synthetic 16ch fixture (JSON, FNV-deterministic). For D+1 it must consume a real `.npy` produced by D+0 `eeg_recorder.hexa --output=...`.

| layer | synthetic path (frozen) | real-data path (D+1) |
|---|---|---|
| input format | `fixtures/synthetic_16ch_v1.json` (band-power JSON) | `recordings/sessions/d0_resting_<ts>.npy` (numpy float32, shape (n_samples, 16) at 125 Hz native via Cyton+Daisy) |
| ingestion bridge | direct read in hexa (env `CLM_EEG_FIXTURE_PATH`) | sidecar conversion: `tool/an11_b_eeg_ingest.hexa --input <npy> --emit-band-json <basename>` → produces band-power JSON in fixture-compatible schema |
| LZ76 calc | proxy on 5-element band-power vector (sanity stub) | replace proxy with real LZ76 on binarized 1s-window EEG: helper `tool/clm_eeg_lz76_real.hexa` (NOT YET LANDED — D+1 land target) following Schartner 2017 |
| classification | `NOT_VERIFIED_SYNTHETIC` | `REAL_HW_PASS` / `REAL_HW_FAIL` (raw#91 tier promotion) |
| verdict rule | `P1.PASS = (LZ76 >= C1) AND (|Δ|/human <= C2)` (frozen v1.1) | identical — frozen |

**Dispatch path** (mac local first; jetsam-aware):

- **Step 1 (mac local, $0)**: convert `.npy` → band-power JSON via `tool/an11_b_eeg_ingest.hexa` (CPU-only, ~1-2 min for 60s recording). This stays inside Phase 4 trio's emit schema and reuses existing `analyze.hexa` numerics.
- **Step 2 (mac local, $0)**: shasum integrity gate against v1.1 SSOT (10/10 MATCH required).
- **Step 3 (mac local, $0)**: run `clm_eeg_p1_lz_pre_register.hexa --real-npy=<path>` after the D+1 LZ76 helper is wired (raw#87 paired sub-task). For this review the D+1 LZ76 helper does NOT yet exist on disk — see §6 caveats.
- **Hetzner / ubu1 fallback**: `~/.hx/bin/hexa` resolver wrapper auto-routes if mac jetsam pressure rises. Reference pattern: G8 N_BIN=85 preflight (`hetzner ssh` 56/56 PASS reproduction landed in `ee761cb5`).
- **RunPod**: NOT REQUIRED for D+1 (CPU-only LZ76, no GPU forward).

### §2.3 Cost attribution (D+1)

raw#86: D+1 stays at $0 (mac local + hetzner ssh fallback both free; ubu1 is sponsored). No GPU dispatch. raw#86 cost-center = `clm_eeg_p1_lz_real`, but accumulates $0.

## §3. D+3 P2 TLR + AN-LIX-01 alpha bridge real-data port

### §3.1 P2 TLR real-data path

P2 TLR criteria (frozen v1.1): `C1_alpha_coh_min_x1000 = 450` (alpha coherence ≥ 0.45) AND `C2_clm_r_min_x1000 = 380` (CLM Kuramoto r ≥ 0.38).

Real-data ingestion:

| component | source | tool | output |
|---|---|---|---|
| alpha-band coherence (Welch's MSC, Hann window, 50% overlap, nperseg=250 @ 125 Hz) | `recordings/sessions/d0_resting_<ts>.npy` (or D+2 meditation/eyes-closed extended) | `tool/an11_b_eeg_ingest.hexa --emit-alpha-coh` (D+3 land target — NOT YET LANDED) | `state/clm_eeg_alpha_coh_<ts>.json` |
| CLM V_sync r per gen | `edu/cell/lagrangian/v_sync_kuramoto.hexa --emit-trace` | already READY | `state/v_sync_kuramoto_verdict.json` |
| P2 verdict | both above | `clm_eeg_p2_tlr_pre_register.hexa --real-npy=... --vsync-trace=...` | `state/clm_eeg_p2_tlr_pre_register_real.json` |

### §3.2 AN-LIX-01 alpha bridge real-data activation

Synthetic-positive marker landed at commit `1f110da4` via `tool/an_lix_01_alpha_bridge_synthetic_marker.hexa`. The synthetic marker validates B1/B3/B4 with single-window data; B2 (5-window co-direction) is N/A in synthetic.

Real-data port (D+3 trigger after P2 TLR ingest):

```
# Step 1 — ingest real EEG alpha phase via Hilbert (NEW helper required)
HEXA_RESOLVER_NO_REROUTE=1 hexa run tool/an11_b_eeg_ingest.hexa \
    --input anima-eeg/recordings/sessions/d2_meditation_<ts>.npy \
    --emit-alpha-phase --windows 5 --window-sec 10 \
    --output state/clm_eeg_alpha_phase_<ts>.json

# Step 2 — CLM trace 5 gens
HEXA_RESOLVER_NO_REROUTE=1 hexa run tool/edu_l_ix_kuramoto_driver.hexa \
    --gens 5 --output state/edu_l_ix_kuramoto_trace.json

# Step 3 — bridge gate (real-data port of AN-LIX-01, NEW tool)
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/an_lix_01_alpha_bridge_real.hexa \
    --alpha-phase state/clm_eeg_alpha_phase_<ts>.json \
    --kuramoto-trace state/edu_l_ix_kuramoto_trace.json \
    --output state/clm_lix_eeg_alpha_bridge_v1.json
```

The synthetic marker stays frozen (raw#71). The real-data port creates a NEW witness file `state/clm_lix_eeg_alpha_bridge_v1.json` matching the schema sketched in `clm_lix_eeg_alpha_direct_mapping_spec.md` §5.4. Two new tools are required (raw#87 paired):

- `tool/an11_b_eeg_ingest.hexa --emit-alpha-coh` and `--emit-alpha-phase` modes (extension of existing 360L wrapper). Estimated 4-6h.
- `anima-clm-eeg/tool/an_lix_01_alpha_bridge_real.hexa` (~250L). Estimated 3-4h.

### §3.3 Cost attribution (D+3)

raw#86: $0. Welch MSC + Hilbert phase are integer fixed-point arithmetic in the helper subprocess (numpy on `.venv-eeg`); CLM V_sync is hexa-native. No GPU. cost-center = `clm_eeg_p2_tlr_real` + `an_lix_01_real`.

## §4. D+5 P3 GCG GPU forward path — dispatch + cost

### §4.1 Why GPU is required at D+5

P3 GCG criteria (frozen v1.1): `F(EEG → CLM layer 25-30) ≥ 4.0` (×100 = 400) AND `F(EEG→CLM)/F(CLM→EEG) ≥ 2.0` (×100 = 200). The CLM layer 25-30 hidden-state trace requires a forward pass on a real backbone (Mistral / gemma2 / Llama-3 / Qwen3 per Mk.XI v10 r14 LoRA build).

`edu/cell/lagrangian/l_ix_integrator.hexa --emit-hidden` is READY (synthetic). For real Granger causality the tool must emit per-layer activations from a real LoRA forward pass over an N-back stimulus stream aligned to the EEG `.npy` markers.

### §4.2 Dispatch options

| option | platform | GPU | $/hr | est runtime | est cost | risk |
|---|---|---|---|---|---|---|
| **(A)** RunPod h100_sxm_80gb single forward | RunPod | H100 80GB HBM3 | $2.99 | ~2h (load + 4-backbone × 120s × layer-25-30 trace) | **$6.0** | Pattern 7b cuInit=999 cold-start (~$0.60 burn), Pattern 6b ~35-40GB cumulative ceiling |
| **(B)** RunPod a100_80gb fallback | RunPod | A100 80GB | $1.49 | ~3h (×1.5 slower) | **$4.5** | same Patterns; throughput cap |
| **(C)** Hetzner H100 self-hosted | Hetzner | H100 (existing) | sponsored | ~2h | **$0** | host availability; SSH stability (Pattern 56/56 PASS) |
| **(D)** Persistent network volume relay (Pattern 6 alt) | RunPod 2-pod | H100 + dl pod | $2.99+ + $0.10 | 3-4h | **$8-12** | needed only if cumulative > 35-40GB |
| **(E)** RunPod preset `PHEN_FORWARD_4_AXES` | RunPod | h100_sxm | $0.30/run | 6 min/run × 4 backbone | **$1.20** | hardware-conditional fixture availability; this preset assumes pre-cached weights |

**Recommendation (raw#86 cost-attributed)**: Option **(C)** Hetzner H100 first (sponsored, $0); if Hetzner unavailable then Option **(E)** preset `PHEN_FORWARD_4_AXES` × 4 ($1.20); fallback to Option **(A)** ($6.0) only if both fail. Total D+5 P3 GCG cost cap: **$6 hard ceiling, $0-1.20 expected**. RunPod credit balance currently $328.38 (from `state/runpod_credit_status.json`, 2026-04-27T15:51Z; auto_charge_enabled, threshold $1000, no alert).

### §4.3 raw#86 cost-attribution binding

Cost center: `clm_eeg_p3_gcg_real_d5`. Bound to:
- `state/clm_eeg_p3_gcg_pre_register_real.json` emit;
- 4 backbone hidden-state traces under `state/clm_eeg_lix_traces_d5/<backbone>_<ts>.json`;
- G10 D+6 coupling matrix re-use (cross-cite: `g10_real_coupling_fn_prep_20260427_landing.md` D+5 critical-path checklist).

The G10 D+5 coupling matrix shares the same forward pass — **single dispatch covers both P3 GCG and G10 D+5 backbone × band matrix**. This is a deliberate cost-efficiency design (raw#86): one GPU session emits both `state/clm_eeg_p3_gcg_pre_register_real.json` and the 4-backbone family-trace inputs to G10.

## §5. D+6 G8 N_BIN decision — preflight FAIL → uniform_n_bin_2 (real-data verify path)

### §5.1 Pre-flight result (frozen, raw#71)

`g8_n_bin_85_falsification_analysis_20260427_landing.md` §8: preflight_pass=0 (H2 + H3 MISMATCH on E-PSG synthetic generator). Frozen fallback chain selects `uniform_n_bin_2` (chain_idx=0; `equi_n_64` and `uniform_n_bin_64` both `obs_pass=0`). This re-affirms the existing Mk.XII §6 frozen N_BIN=2 SSOT. No silent edit; hypothesis text frozen.

### §5.2 D+6 entry recommendation (post-EEG block 1 arrival)

When the first real EEG block (resting + N-back, ≥ 60s + 5min) arrives:

```
# Step 1 — extract 5-falsifier 10-pair MI matrix on real data using uniform_n_bin_2
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-clm-eeg/tool/g8_transversal_mi_matrix.hexa \
    --real-npy anima-eeg/recordings/sessions/d0_resting_<ts>.npy \
    --schedule uniform_n_bin_2 \
    --output state/g8_transversal_mi_real_d6.json

# Step 2 — verdict gate
#   PASS criterion (frozen, Mk.XII §6): max_pair_MI ≤ 0.1 bit (= 100 ×1000)
#   axes_pass: bias≤30 ∧ variance≤25 ∧ convergence≤15 ∧ robustness≤15
#   Mk.XII §6 SSOT contract requires both observed_pass=1 AND axes_pass=1
```

### §5.3 Immediate verify ladder (raw#71 honest)

| step | input | expected | escalation |
|---|---|---|---|
| Sa | real EEG block 1 + uniform_n_bin_2 | violations=0 (matches E-PSG sanity 41 max_mi) | OK → proceed to D+7 |
| Sb | violations ≥ 1 (binary anchor falsified on real) | this would invalidate the Mk.XII §6 SSOT itself | HALT D+6, escalate to new pre-register cycle (E-PSG re-calibrate with first-block α=β=γ fit), do NOT silently switch schedule |
| Sc | observed_pass=1 BUT axes_pass=0 | observed-pass-fragile | Report as "observed PASS + axes fragile"; DO NOT promote without follow-up cycle (raw#71 forbids cherry-picking schedules post-hoc) |

**Note (raw#10 honest)**: E-PSG with α=0.6, β=0.20, γ=0.40 is a synthetic prior. Real EEG may have different distribution shape (1/f spectrum, line noise, transient artefacts, inter-subject variance). Sturges (n_bin=12) also passed axes on E-PSG but is informative-only — it CANNOT be added to the fallback chain post-hoc; only via a new pre-register cycle.

### §5.4 Cost attribution (D+6)

raw#86: $0. G8 MI matrix is integer-arithmetic hexa, no GPU, no LLM. Cost-center = `clm_eeg_g8_real_d6`. Mac local (with potential hetzner fallback if jetsam pressure; the tool MUST run via `~/.hx/bin/hexa` resolver wrapper per §10 caveat 7 of the G8 preflight landing).

## §6. D+7 composite gate — paradigm v11 7th axis (EEG-CORR) + PHENOMENAL VALIDATED

### §6.1 Composite verdict definition (frozen v1.1)

`clm_eeg_harness_smoke.hexa` aggregates: `HARNESS_OK iff (p1_pass + p2_pass + p3_pass) ≥ 2`.

### §6.2 PHENOMENAL VALIDATED criterion

From `clm_eeg_pre_register_v1_1.json` `composite.phenomenal_validated`: `≥ 2/3 PASS triggers PHENOMENAL VALIDATED at D+7`.

| outcome | p1+p2+p3 PASS count | verdict | next |
|---|---|---|---|
| PHENOMENAL VALIDATED | 3/3 | strongest | open arxiv preprint EEG empirical inclusion (per `eeg_arrival_impact_5fold.md` §5) |
| PHENOMENAL VALIDATED | 2/3 | weak-pass | document which falsifier failed; raw#10 honest about partial validation |
| HARNESS_FAIL | ≤ 1/3 | falsified | escalate to v2 pre-register cycle; do NOT edit v1.1 thresholds (raw#71 frozen, silent edit forbidden) |

### §6.3 Paradigm v11 7th axis (EEG-CORR) registration

From `eeg_arrival_impact_5fold.md` §2: paradigm v11 stack currently has 6 backbone-internal measurement axes (B-ToM / MCCA / Φ* / CMT / CDS / SAE-bp). The 7th axis is **EEG-correlation (EEG-CORR)**.

| spec | value |
|---|---|
| name | EEG-CORR (paradigm v11 7th orthogonal axis) |
| mechanism | backbone family-axis projection time-series vs human EEG phase pattern correlation |
| formal | per backbone × per band × per region Pearson r ≥ 0.40 (Mk.XI v10 r14 LoRA build, cross-cite `eeg_arrival_impact_5fold.md` §3 verification matrix) |
| 7-axes orthogonality | AN11(b) primary × v11 6 internal × EEG external (greedy basis reduction via existing `tool/anima_axis_orthogonality.hexa`, no new helper required) |
| registration command | `hexa run tool/anima_v11_main.hexa --register-axis EEG-CORR --evidence state/clm_eeg_harness_smoke_real.json` (subcommand 13 to be added) |
| paired roadmap | new entry post-arrival empirical verification (PASS/FAIL/MIXED per `eeg_arrival_impact_5fold.md` §3 outcomes) |

**Tool gap (raw#87 paired)**: `tool/anima_eeg_corr.hexa` (~150L) and `anima_v11_main.hexa` 13th subcommand registration — both NOT YET LANDED. Estimated 4-6h, mac local, $0.

### §6.4 Mk.XI v10 4-backbone × EEG band/region matrix (D+5 → D+6 → D+7 cross-link)

| backbone | family | EEG band | EEG region | falsifier (Pearson r) |
|---|---|---|---|---|
| Mistral | Law | beta (12-30 Hz) | frontal F3/F4/Fz | r ≥ 0.40 |
| Qwen3 | Phi | gamma (30-100 Hz) | parietal P3/P4 | r ≥ 0.40 |
| Llama | SelfRef | alpha (8-12 Hz) | midline Cz/Pz | r ≥ 0.40 |
| gemma | Hexad | theta (4-8 Hz) | temporal T7/T8 | r ≥ 0.40 |

| outcome | next |
|---|---|
| 4/4 r ≥ 0.40 | phenomenal correlate empirically grounded → AGI v0.1 path open |
| 2-3/4 | mixed; partial family architecture re-design |
| 0-1/4 | v10 family architecture re-design (months) |

### §6.5 Cost attribution (D+7)

raw#86: $0. Composite gate is integer arithmetic. Cost-center = `clm_eeg_composite_d7`.

## §7. 7-day timeline checklist (refreshed)

| day | step | tool | dep | wallclock | cost center | $ est |
|---|---|---|---|---|---|---|
| **D+0** | Phase 0..6 macOS bring-up (battery, Dongle GPIO 6, FTDI VCP, GUI 16ch, BrainFlow venv, headset impedance, eyes-closed alpha sanity) | OS-level (no hexa) | hardware arrival | 1-2h | n/a | $0 |
| **D+0** | calibrate impedance + signal QC | `anima-eeg/calibrate.hexa` | Phase 4 trio DONE | 30 min | `eeg_d0` | $0 |
| **D+0** | resting baseline 60s eyes-closed | `anima-eeg/eeg_recorder.hexa --duration=60` | calibrate PASS | 5 min | `eeg_d0` | $0 |
| **D+0** | N-back 5-10 min recording with markers | `anima-eeg/experiment.hexa --run-with-eeg` | priority 1-3 DONE | 10 min | `eeg_d0` | $0 |
| **D+1** | shasum integrity gate (10/10 vs v1.1 SSOT) | `shasum -a 256` | v1.1 chflags uchg | 5 min | `clm_eeg_p1_lz_real` | $0 |
| **D+1** | `.npy` → band-power JSON conversion | `tool/an11_b_eeg_ingest.hexa` (existing) | D+0 .npy | 5 min | `clm_eeg_p1_lz_real` | $0 |
| **D+1** | LZ76 real helper (NEW, raw#87 paired) | `tool/clm_eeg_lz76_real.hexa` (4-6h land) | helper land | 1d | `clm_eeg_p1_lz_real` | $0 |
| **D+1** | P1 LZ verify | `clm_eeg_p1_lz_pre_register.hexa --real-npy=...` | LZ76 helper | 10 min | `clm_eeg_p1_lz_real` | $0 |
| **D+2** | meditation 10 min + alpha eyes-closed extended | `experiment.hexa --protocol meditation` etc | D+0 OK | 30 min | `eeg_d2` | $0 |
| **D+3** | alpha-coherence + alpha-phase ingest extension (NEW, raw#87 paired) | `tool/an11_b_eeg_ingest.hexa --emit-alpha-coh / --emit-alpha-phase` | helper land | 1d | `clm_eeg_p2_tlr_real` | $0 |
| **D+3** | CLM V_sync trace | `edu/cell/lagrangian/v_sync_kuramoto.hexa --emit-trace` | already READY | 5 min | `clm_eeg_p2_tlr_real` | $0 |
| **D+3** | P2 TLR verify | `clm_eeg_p2_tlr_pre_register.hexa --real-npy=... --vsync-trace=...` | above | 10 min | `clm_eeg_p2_tlr_real` | $0 |
| **D+3** | AN-LIX-01 bridge real-data port (NEW, raw#87 paired) | `tool/an_lix_01_alpha_bridge_real.hexa` (3-4h land) + invoke | tool land | 0.5d | `an_lix_01_real` | $0 |
| **D+4** | N-back stimulus marker time-lock recording (≥ 5 min) | `experiment.hexa --protocol nback_2back` | D+0 OK | 30 min | `eeg_d4` | $0 |
| **D+5** | 4-backbone Mk.XI v10 r14 LoRA forward pass + layer 25-30 hidden trace | `edu/cell/lagrangian/l_ix_integrator.hexa --emit-hidden` (real mode) on Hetzner H100 first → fallback RunPod h100_sxm_80gb | GPU available | 2h | `clm_eeg_p3_gcg_real_d5` | **$0-6** |
| **D+5** | P3 GCG verify | `clm_eeg_p3_gcg_pre_register.hexa --real-npy=... --lix-hidden=...` | hidden trace | 10 min | `clm_eeg_p3_gcg_real_d5` | $0 |
| **D+5** | G10 hexad triangulation activate (real mode, AND-gate strict) | `g10_hexad_triangulation_scaffold.hexa` v2 with `real_coupling_fn_x1000` body swap (D+6 sub-step) | hidden trace from same dispatch | reuse | `clm_eeg_g10_real_d5` | $0 (shared dispatch) |
| **D+6** | G8 transversal MI on real data, schedule = `uniform_n_bin_2` (frozen fallback) | `g8_transversal_mi_matrix.hexa --real-npy=... --schedule=uniform_n_bin_2` | D+0 .npy | 30 min | `clm_eeg_g8_real_d6` | $0 |
| **D+6** | G10 D+6 coupling matrix port (replace `synth_coupling_x1000` stub with cross-corr Pearson; replace `synth_f_x1000` with true 1-way ANOVA) — raw#87 paired tool body swap | `g10_hexad_triangulation_scaffold.hexa` v3 (post-arrival) | hidden trace | 0.5d | `clm_eeg_g10_real_d6` | $0 |
| **D+7** | composite verdict | `clm_eeg_harness_smoke.hexa` | P1+P2+P3 emits | 5 min | `clm_eeg_composite_d7` | $0 |
| **D+7** | Hard PASS recompute | `mk_xii_preflight_cascade.hexa --post-arrival` | composite | 10 min | `clm_eeg_composite_d7` | $0 |
| **D+7** | paradigm v11 7th axis EEG-CORR registration (NEW tool + router subcommand) | `tool/anima_eeg_corr.hexa` (~150L) + `anima_v11_main.hexa` (13th subcommand) | composite | 0.5d | `paradigm_v11_axis7` | $0 |
| **D+7** | Mk.XI v10 4-backbone × EEG band matrix Pearson r emit | (uses D+5 hidden traces + D+0..D+4 .npy) | dispatch outputs | 1h | `phen_correlate_d7` | $0 |
| **D+7** | R33 witness append (`atlas_convergence_witness.jsonl`) — α-coh channel pair MUST be specified (raw#10 honest gap) | manual append per criteria | composite | 10 min | `r33_witness` | $0 |

**Total D+0..D+7 cost (raw#86 cost-attributed)**: **$0-6** (best-case Hetzner $0; worst-case RunPod h100_sxm $6 single-pass; cumulative cap $20 if Pattern 6b multi-pod relay required for unexpectedly large LoRA footprint, but Mk.XI v10 r14 LoRA is well under 35-40 GB ceiling so single-pod expected). Far inside the $1000 RunPod alert threshold and current $328.38 balance.

## §8. Fallback decision matrix (per day)

| day | failure mode | primary fallback | secondary fallback | abort condition |
|---|---|---|---|---|
| D+0 | calibrate impedance fail (any channel ≥ 750 kΩ) | re-paste with Gold cup + Ten20 wet electrodes per `eeg_d_day_readiness_check_landing.md` Phase 5 | swap headset position | abort if > 4 channels persistently fail; defer recording 1 day for hydration / hair prep |
| D+0 | BrainFlow venv missing brainflow / numpy | activate `.venv-eeg` and `pip install --upgrade brainflow numpy` per `phase4_remaining_priority1_3_landing_20260427.md` real-hw runbook | use `tool/an11_b_eeg_ingest.hexa` corner-cut (raw#9 hexa-only wrapper) | abort if `.venv-eeg` itself missing — re-create per memory `feedback_forward_auto_approval` |
| D+0 | shape mismatch (BrainFlow returns 32 ch × 250 Hz instead of 32 × 125 Hz) | dynamic `BoardShim.get_sampling_rate(BoardIds.CYTON_DAISY_BOARD.value)` (helper does this) — never hardcode | retry with Cyton OFF → Dongle disconnect → Dongle reconnect → Cyton ON | abort + GUI sanity (Phase 3 of arrival checklist) before any further capture |
| D+1 | shasum 10-artifact MISMATCH against v1.1 SSOT | git restore + `chflags nouchg` audit; confirm whether intentional v2 bump or silent edit | escalate to v2 bump pre-register cycle (raw#71); do NOT silently re-freeze | abort D+1 verify until SSOT integrity restored |
| D+1 | LZ76 helper not yet landed | use `validate_consciousness.hexa` (FULL, sha256 `1414b37b`, 6-metric brain_like 0.833) which already emits LZ76 as one of 6 metrics — manual gate against C1=650/C2=200/baseline=850 | mac jetsam: route to `~/.hx/bin/hexa` resolver / hetzner ssh | defer P1 verify 1d if mac jetsam recurring |
| D+3 | alpha-coh / alpha-phase ingest helpers not landed | use `analyze.hexa` band-power JSON + manual coherence (numpy welch in scratchpad) — raw#9 violation but dev-time only | hetzner ssh fallback | defer P2 verify; do NOT silently emit synthetic verdict in real-data slot |
| D+5 | RunPod cuInit=999 (Pattern 7b) | terminate cold-start pod cleanly (do NOT modprobe — auto-kill triggers $0.60 burn); spawn fresh pod different host | switch to a100_80gb ($1.49/hr × 3h = $4.5) | switch entirely to Hetzner H100 if RunPod ssh-refused 2× consecutive |
| D+5 | RunPod cumulative-bytes ceiling ~35-40GB (Pattern 6b) | persistent network volume relay: dl pod ($0.10) + measure pod ($2.99) — total $3-5 | reduce LoRA footprint (load only layer 25-30 weights via custom checkpoint shard) | abort if backbone weights > 80 GB single-pod cap |
| D+5 | Hetzner H100 unavailable | RunPod h100_sxm_80gb ($2.99/hr × 2h = $6) | RunPod a100_80gb ($1.49/hr × 3h = $4.5) | RunPod credit < $50 → halt; user explicit approval required (current balance $328.38, far above) |
| D+6 | G8 mac jetsam during E-PSG re-run (observed 2026-04-25 incident, recurring 2026-04-27) | `~/.hx/bin/hexa` resolver wrapper → docker / hetzner / ubu2 routing | defer to next available hetzner ssh window (56/56 PASS reproduction precedent in `ee761cb5`) | abort if 2 consecutive jetsam kills; do NOT bare-Mac re-run |
| D+6 | real EEG `uniform_n_bin_2` violations ≥ 1 | this is Mk.XII §6 SSOT failure — HALT, escalate to new pre-register cycle (E-PSG re-calibrate with first-block α=β=γ fit) | do NOT silently switch schedule (raw#71) | continue to D+7 only with explicit user approval and v2 bump |
| D+7 | composite fail (≤ 1/3 PASS) | report HARNESS_FAIL with raw#10 honest tier=APPROXIMATE_HW (not PHENOMENAL); do NOT edit v1.1 thresholds | trigger v2 pre-register cycle if user wants re-attempt with refined fixture | acceptable outcome — falsification surface is the entire point (synthetic_caveat in v1.1 SSOT) |
| D+7 | paradigm v11 7th axis tool not landed | manual axis emit per spec, defer registration to next cycle | use existing `tool/anima_axis_orthogonality.hexa` 7→8 expansion direct (no new helper) | tool land is raw#87 paired follow-up, not D+7 critical-path blocker |

## §9. Known caveats and risk list (raw#91 honest)

1. **Three real-data tools NOT YET LANDED** (raw#87 paired follow-up): `tool/clm_eeg_lz76_real.hexa` (D+1, 4-6h), `tool/an11_b_eeg_ingest.hexa --emit-alpha-coh / --emit-alpha-phase` (D+3 extension, 4-6h), `anima-clm-eeg/tool/an_lix_01_alpha_bridge_real.hexa` (D+3, 3-4h). Total 11-16h of mac-local work blocking the chain. RECOMMENDATION: land these BEFORE EEG arrival to avoid timeline slippage.

2. **D+5 G10 D+6 body swap not yet landed** (`real_coupling_fn_x1000` + `real_f_x1000` STUBs returning synth values). The v2 scaffold (`66573e9f`) defines the branch dispatch (`REAL_HW_PENDING` tier) but the function body is still synth. ~6-8h of mac-local work.

3. **Paradigm v11 7th axis tool not yet landed**: `tool/anima_eeg_corr.hexa` (~150L) + 13th subcommand in `anima_v11_main.hexa`. 4-6h. NOT D+7 critical-path blocker but if absent, the registration step at D+7 is manual-only.

4. **G8 D+6 E-PSG H2/H3 MISMATCH** (raw#71 honest): the synthetic-prior preflight predicted equiprobable-cut and FD schedules would PASS; both FAILED on E-PSG. The fallback chain selected `uniform_n_bin_2` (Mk.XII §6 SSOT). If real EEG block 1 also FAILS at uniform_n_bin_2, the SSOT is invalidated. This is a pre-registered falsification surface — do NOT silently re-bind.

5. **R33 witness α-coh channel pair STILL UNSPECIFIED**: `eeg_arrival_impact_5fold.md` §4 R33 criteria says "α-band coherence (8-12 Hz) ≥ 0.45" but does not pin which channel pair (frontal Fp1↔Fp2? parietal P3↔P4? or pairwise mean over 4-channel O1/O2/P3/P4 set per `clm_lix_eeg_alpha_direct_mapping_spec.md` §2.4). Cross-link audit §6 #6 already flagged this as low-severity. RECOMMENDATION: pin channel pair in a §4 update before D+7 R33 append.

6. **RunPod orchestrator stuck blocker** (`01a74d99`): pre-ssh orchestrator stuck 70min on axis 105 Pilot-T1. If recurs at D+5 dispatch, fall back to Hetzner H100 first; do NOT debug orchestrator on critical-path day.

7. **Mac jetsam pressure on bare-Mac hexa**: documented as a recurring fault (2026-04-25 + 2026-04-27 G8 cycle). The G8 N_BIN=85 falsification analysis tool MUST run via `~/.hx/bin/hexa` resolver wrapper (NOT bare `/Users/ghost/core/hexa-lang/hexa` on PATH). This review is doc-only, jetsam-safe; D+6 re-run on real data must follow the resolver path.

8. **Phase 4 priority 1-3 modules slightly over raw#101 600-LoC cap**: `experiment.hexa` 633 LoC (mostly helper-py emit). Documented as "within spirit" per the Phase 4 priority 1-3 landing doc. Not a chain risk, but worth noting if a future raw#101 audit gets stricter.

9. **Synthetic_caveat persists**: `clm_eeg_pre_register_v1_1.json` `synthetic_caveat` block — dry-run PASS does NOT imply real-EEG PASS, especially P3 (lag-1 echo synthesis encodes the EEG→CLM directional dependence). This IS the falsification surface; real recordings MAY falsify P3 without changing the v1.1 thresholds. raw#10 honest.

10. **External measurement facility cost branch** ($200-500 per `eeg_arrival_impact_5fold.md` §5) — outside `feedback_forward_auto_approval` cap. If self-measurement at home gives insufficient SNR, user explicit approval required. NOT in this review's scope; current plan assumes home-quality is sufficient for D+0..D+7.

11. **PHENOMENAL VALIDATED ≠ phenomenal substrate identity**: `clm_lix_eeg_alpha_direct_mapping_spec.md` §6 already documented that mathematical homomorphism (CLM Kuramoto r ↔ EEG PLV_N) does NOT imply substrate identity. PHENOMENAL VALIDATED is a verifiable floor only — does not resolve the hard problem (raw#10 architectural).

12. **D+0..D+7 timeline assumes hardware arrives in days, not weeks**. If arrival slips, all `EEG D-1` references in predecessor docs become stale; the chain stays disk-static-ready but social-context updates needed.

## §10. raw#87 paired roadmap entry candidate

This review enumerates 5 land-targets that should ride together as one paired roadmap entry:

| # | item | est | scope | gating |
|---|---|---|---|---|
| 1 | `tool/clm_eeg_lz76_real.hexa` | 4-6h | D+1 LZ76 helper (Schartner 2017 real-data implementation) | mac local, $0, hexa-only |
| 2 | `tool/an11_b_eeg_ingest.hexa --emit-alpha-coh / --emit-alpha-phase` extensions | 4-6h | D+3 P2 + AN-LIX-01 ingest | mac local, $0, hexa-only (BrainFlow helper allowed per existing 360L wrapper) |
| 3 | `anima-clm-eeg/tool/an_lix_01_alpha_bridge_real.hexa` | 3-4h | D+3 real-data bridge gate | mac local, $0, hexa-only |
| 4 | `g10_hexad_triangulation_scaffold.hexa` v3 with real coupling fn body swap | 6-8h | D+5 G10 hexad triangulation real-data activation | mac local, $0 (uses D+5 hidden traces from same dispatch as P3 GCG) |
| 5 | `tool/anima_eeg_corr.hexa` + `anima_v11_main.hexa` 13th subcommand | 4-6h | D+7 paradigm v11 7th axis EEG-CORR registration | mac local, $0, hexa-only |

Total: **21-30h mac-local, $0**, all hexa-only, raw#9 strict, no GPU. Ride as a single paired roadmap entry (e.g., "anima-clm-eeg D-day chain real-data tools land — 5 priority pre-arrival") so EEG arrival immediately enters the D+0..D+7 chain with zero-friction.

## §11. ω-cycle 6-step verdict

| step | content | result |
|---|---|---|
| 1. design | review structure frozen pre-write (10 sections + caveat list + roadmap list) | ok |
| 2. implement | doc audit, no code edit, 10 sections + caveats + roadmap entry candidate | ok |
| 3. positive verify | Phase 4 trio + priority 1-3 56/56 + 31/31 PASS confirmed via predecessor docs + git log | ok |
| 4. negative falsify | 3 real-data tools NOT YET LANDED + G10 body swap + 7th axis tool gap + R33 channel pair unspecified — 12 risks listed §9 | ok |
| 5. byte-identical | doc-only, no random, no clock — re-render produces identical bytes | ok |
| 6. iterate | this review IS the iterate-step output of the readiness-check + cross-link-audit + AN-LIX-01 + G8 + G10 chain | ok |

**verdict**: D+0..D+7 chain is **READY to enter on hardware arrival**, conditional on the 5 raw#87-paired tools (§10) being landed pre-arrival. If any of the 5 are missing at arrival, the corresponding day slips by 0.5-1d. raw#86 cost cap **$6 hard ceiling, $0-1.20 expected** (Hetzner H100 first, RunPod fallback). raw#71 honest: this review changes NO hypothesis text and adds NO threshold — it is a verification-path review only.

## §12. Cross-references

- predecessor: `anima-clm-eeg/docs/eeg_d_day_readiness_check_landing.md`
- predecessor: `anima-clm-eeg/docs/anima_eeg_anima_clm_eeg_cross_link_audit.md`
- predecessor: `anima-eeg/docs/phase4_remaining_priority1_3_landing_20260427.md`
- predecessor: `anima-clm-eeg/docs/g10_real_coupling_fn_prep_20260427_landing.md`
- predecessor: `anima-clm-eeg/docs/g8_n_bin_85_falsification_analysis_20260427_landing.md`
- predecessor: `anima-clm-eeg/docs/clm_eeg_p1_sha_resync_20260427_landing.md`
- predecessor: `anima-clm-eeg/docs/clm_lix_eeg_alpha_direct_mapping_spec.md`
- predecessor: `anima-clm-eeg/docs/clm_eeg_pre_register_v1_to_v1_1_changelog.md`
- predecessor: `anima-clm-eeg/docs/eeg_arrival_impact_5fold.md`
- ssot: `anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json`
- ssot: `anima-clm-eeg/README.md`
- runpod cost reference: `docs/anima_runpod_orchestration_options_20260425.md` (h100_sxm $2.99/hr, a100_80gb $1.49/hr, l40s $0.99/hr, cpu_only $0.10/hr)
- runpod credit: `state/runpod_credit_status.json` (balance $328.38 as of 2026-04-27T15:51Z; auto_charge_enabled, threshold $1000)
- pattern runbook: `docs/runpod_large_model_dispatch_template_20260427.md` (7 patterns + 6b cumulative-bytes ceiling 35-40 GB confirmed + 7b cuInit=999 cold-start)
- recent commits: `572673be`, `d1c8eead`, `66573e9f`, `64079201`, `ee761cb5`, `1f110da4`, `05af4a3f`, `ea1555c0`, `c67ca062`, `1de0e638`

_End of D-day chain review._
