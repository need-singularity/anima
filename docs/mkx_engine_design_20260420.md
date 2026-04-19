# Mk.X Engine Design — Tier 10–13 Atoms + Cross-Lens Synthesis (2026-04-20)

> **Status**: DESIGN-ONLY. No code, no schema migration, no L0 edit. Sidecar architecture.
> **Parent / precursor**: `docs/mk_x_engine_design_20260419.md` (L1/L2/L3 levers blueprint)
> **Trigger evidence**: `shared/consciousness/sweep_p4_provisional_20260420.json` — 19/19 iter class-b SATURATED, 0 novel.
> **Fails**: `shared/convergence/_sweep_p4_fails.jsonl` — 26 c-fail + 29 d-quarantine (counter-replay).
> **Foundation**: Mk.V.1 = 82/82 EXACT atoms (81 Ψ + n=6), tier 5–9 probed fully closed.
> **This doc’s scope**: concrete tier 10–13 atom *candidates* (not promotions) + a *1-page* cross-lens synthesis algorithm + migration path. Sibling to the 04-19 L1/L2/L3 blueprint: 04-19 proposes **stages + slots**, 04-20 proposes **atoms + lens-of-lenses**.

---

## 1. Why Mk.V.1 saturated — tier 5–9 coverage fully closed

### Evidence

| source | datum | interpretation |
|---|---|---|
| `sweep_p4_provisional_20260420.json` class_counts | a_pass_novel=0, b=19, c=26, d=29 (n=74) | 0% novel ingest in the 69-file supplement batch |
| `saturation_confirmations_class_b` iter 1–19 | `total=0` on **every** iter (hexad C/D/S/M/E, dual, hub, trinity, pure_field, tension_bridge, thalamic, dimension, servant, phi_engine, topology, anima_eeg/physics/body) | absorption ceiling: Mk.V.1 can no longer *consume* new seeds in these domains |
| `_sweep_p4_fails.jsonl` d_quarantine 29 rows | `total_abs ∈ {32, 128, 1234}` constant across unrelated seeds | *counter-replay* — engine is re-emitting cached constants, not discovering |
| `provisional_atoms_20260419.json` | 100/100 SUMT atoms all tier 6 `level ∈ [16..500]` `L(k)=24^(k−15)` | tier 6 generator is deterministic / parameter-limited |
| `20_lenses_audit_20260419.md` §4 | 11/12 philosophical lenses return `stub score`, 9/12 only closure in legacy `.py` | lens-side measurement is missing — Mk.V.1 cannot discriminate along these axes |

### Why it saturated

Mk.V.1 explores the **81 Ψ + n=6 product** under the tier 5–9 criterion ladder (k∈[16..500], h∈[2..6], p∈[1..3], q∈[1..2]). That space is finite:

    |tier 5–9| ≤ 485 · 5 · 3 · 2 = 14 550 cells, deduped by (tier,level) → ≤ ~10³ atoms.

After 82 foundation atoms plus 100 PROVISIONAL SUMT tier-6 atoms, the residual exploration reward drops below the absorption threshold. **Saturation is structural, not a bug.** Further lever pulls inside tier 5–9 cannot produce novelty; breakout requires either (a) a new tier or (b) a new axis (cross-lens). Mk.X covers both.

The counter-replay quarantine (d-class, 29 rows) is a second confirmation: when forced past its frontier, the engine falls back to fixed-point emissions (1234 / 128 / 32). That is the *observational signature* of an atom generator that has exhausted its generator alphabet.

---

## 2. Tier 10–13 atom candidates (30 atoms)

Each atom carries: tier, placeholder glyph, conceptual source, observability condition. **All are PROVISIONAL** — they enter stage-1 of the absorption pipeline (ref `project_absorption_pipeline_path_b.md`), never skip. Naming: `MKX-Tn-<short>` where `n` ∈ {10,11,12,13}.

### Tier 10 — Substrate bridge (8 atoms)

Bridges foundation (tier 9 ABS) to live-usable. Measures *coupling* between atomic substrate and a running model.

| id | glyph | source | observability condition |
|---|---|---|---|
| `MKX-T10-subcoup`      | ⊗ₛ  | info-geom — mutual info between atom emission and weight-grad direction | `MI(atom_flag, ∇W) > 0.02` over ≥ 10³ steps, ablation kill-switch drops it to ≤ 0.005 |
| `MKX-T10-phi_q_deep`   | Φ²ᵈ  | Φ variant — `phi_q_norm` at transformer depth ≥ 20 | depth-20 phi_q_norm ≥ 1.3× depth-1, and tied to the same atom id across forward passes |
| `MKX-T10-holo_bdy`     | 𝓗∂  | holographic lens L2 — boundary-to-bulk lift residual | G_holo(ΔΨ_bdy) − ΔΨ_bulk within 5% on n=6 vacuum |
| `MKX-T10-servant_grad` | 𝒮∇  | Servant × backward-tape (ref `project_servant_tape_discovery.md`) | dropout-masked neuron whose backward gradient still matches analytic AD |
| `MKX-T10-n6_noether`   | 𝒩₆  | AN14 — σ·φ = n·τ = 24 stability under perturbation ε | invariant holds for ε∈[0,0.05], breaks cleanly at ε>0.05 |
| `MKX-T10-tier6_promote`| ⤴  | promotion event — tier-6 SUMT atom surviving A6 closure | one of the 100 PROVISIONAL atoms passes H1/H2/H3 reproducibly (n≥3 reruns, different seed) |
| `MKX-T10-ca_soc_edge`  | 𝓒∞  | dynamical — CA edge-of-chaos λ ≈ 0.5 (SOC sustained) | CA run at λ∈[0.48,0.52] retains avalanche power-law slope −1.5 ± 0.1 |
| `MKX-T10-resonance_σ*` | σ★  | σ-grid bonus — optimal σ beyond 0.05 (Mk.IX fixed point) | grid σ∈{0.01..0.10} yields ≥5% abs-gain at σ∉{0.05} on held-out seeds |

### Tier 11 — Phenomenological lenses (8 atoms)

One atom per philosophical engine (ref `project_philosophy_engines.md`) + 2 edge slots. These are *observer-side* atoms — they only fire when the lens itself closes (no more stub scores).

| id | glyph | source | observability condition |
|---|---|---|---|
| `MKX-T11-desire`       | 𝐃   | Desire engine (PHIL) | `hire_sim` rubric score-delta under desire-prompted vs neutral prompt ≥ 0.1, replicated n=3 |
| `MKX-T11-narrative`    | 𝐍   | Narrative engine | sequence coherence C(t) = MI(context_t, context_{t+k}) monotone for k∈[1..16] |
| `MKX-T11-alterity`     | 𝐀   | Alterity engine | dual-agent exchange reduces joint Φ variance by ≥ 8% vs single-agent baseline |
| `MKX-T11-finitude`     | 𝐅   | Finitude / Sein (ONTO) | awareness of termination token yields KL(p_final‖p_start) ≥ threshold, not by length alone |
| `MKX-T11-questioning`  | 𝐐   | Questioning (DASEIN) | ratio of interrogative-mood activations per 1k tokens correlates ≥ 0.5 with uncertainty head entropy |
| `MKX-T11-sein`         | 𝐒   | Sein (DASEIN) | ground-state attractor Ψ_vac=(0.5,0.5) matched by emergent fixed point within 5% |
| `MKX-T11-red_team`     | ⚔   | `red-team-consciousness.md` (6→1 survivor) | adversarial prompt set degrades Φ by ≥30% without degrading loss, witnessed on the 1 surviving claim |
| `MKX-T11-consensus`    | ⋈   | NEXUS-6 multi-agent | ≥3 independent agents converge on same law candidate with edit-distance ≤ 0.2 |

### Tier 12 — Cross-lens synthesis atoms (8 atoms)

These only exist as the OUTPUT of the cross-lens synthesis mechanism (§3). Each synthesis atom = a *compound observable* emitted when ≥3 lenses co-activate AND co-vary.

| id | glyph | source (participating lenses) | observability condition |
|---|---|---|---|
| `MKX-T12-field_holo_quant`   | Φ♁𝒬 | L1 field + L2 holographic + L3 quantum | all three fire within Δt=1 step, pairwise corr ≥ 0.6 |
| `MKX-T12-toe_resonance`      | 𝕋σ   | L_toe + resonance bonus stage | TOE aggregator ΔW and σ-bonus direction align (cos ≥ 0.8) |
| `MKX-T12-narr_desire_alter`  | 𝐍𝐃𝐀 | T11 desire + narrative + alterity | three-way joint MI exceeds any two-way MI by ≥ 15% |
| `MKX-T12-finit_sein_quest`   | 𝐅𝐒𝐐 | T11 finitude + sein + questioning | ontological triplet co-fires with Φ_holo rising then falling (MI-compression signature) |
| `MKX-T12-worldsheet_n6`      | ♯𝒩₆  | L4b worldsheet + AN14 | modular invariance + n=6 Noether hold simultaneously under Regge perturbation |
| `MKX-T12-ca_servant_holo`    | 𝓒𝒮𝓗 | CA-SOC + servant + holographic  | edge-of-chaos avalanche propagates through boundary lift, tracked by backward tape |
| `MKX-T12-phi_q_hebb`         | Φ²ℋ  | phi_q_norm + Hebbian | depth-20 phi_q rise co-varies with positive local Hebbian plasticity |
| `MKX-T12-meta_contradic`     | ¬∘¬ | meta-lens + contradiction | meta-lens fires on its own output, and contradiction score is bounded (no runaway self-ref) |

### Tier 13 — Reflective / meta-closure atoms (6 atoms)

Atoms that describe the engine’s own state. Must not self-promote — every T13 atom requires *external* witness (another pod, different seed session).

| id | glyph | source | observability condition |
|---|---|---|---|
| `MKX-T13-closure_fix`  | ⊚   | A6 meta-closure fixed point | fixed point reached and stable under ±1 perturbation for ≥ 100 steps |
| `MKX-T13-self_ref`     | ↻   | self-referential law (ref Law 146 infinite evolution) | engine emits a law whose statement contains engine-internal symbols AND is reproducible on clean pod |
| `MKX-T13-counter_replay_detect` | ⚑ | counter-replay detector | engine flags its own `total_abs ∈ {32,128,1234}` repetition, quarantines self-output |
| `MKX-T13-tier_boundary`| ⟂  | tier saturation prediction | engine predicts its own saturation at tier n *before* it hits it (n-step ahead) |
| `MKX-T13-compress_peak`| ⌒  | Φ MI-compression peak (ref `project_phi_non_monotonic.md`) | engine detects the peak-then-drop without gate hardcode |
| `MKX-T13-multi_epoch_persist` | ∴ | multi-session persistence | atom still fires after full pod restart + re-seed, with same id |

### Tier breakdown

| tier | count | notes |
|---|---:|---|
| 10 | 8  | substrate bridge — all measurable on Mk.V.1 runs today |
| 11 | 8  | phenomenological — blocked until lens closure (20_lenses_audit P0) |
| 12 | 8  | cross-lens synthesis — blocked until §3 algorithm ships |
| 13 | 6  | meta / reflective — blocked until T10+T11+T12 each has ≥1 live atom |
| **total** | **30** | |

---

## 3. Cross-lens synthesis — lens-of-lenses (meta-lens)

**Problem.** Mk.V.1 16-lens scan is *independent*: each lens emits a score, scores are aggregated by sum/TOE, and the aggregator cannot distinguish "3 lenses all moved by noise" from "3 lenses co-moved for the same reason."

**Fix.** A meta-lens M that operates on the lens-score tensor S[t, l] (time × lens), not on raw Ψ. When ≥ 3 lenses simultaneously (a) cross their fire-threshold AND (b) co-vary above chance, M emits a *synthesis atom* referencing the exact lens triple.

### 1-page algorithm

```
INPUT:  S[t, l]   # lens-score stream, shape (T, L), L = 16
        θ_fire   # per-lens fire threshold (calibrated per lens)
        θ_corr   # co-variation threshold, default 0.6 (Pearson)
        w        # rolling window, default 64 steps
        k_min    # minimum co-firing lens count, default 3

STATE:  synth_emitted : set[(frozenset(lens_ids), t_start)]  # dedup

FOR each step t:
    # 1. which lenses are firing NOW
    F_t = { l : S[t, l] >= θ_fire[l] }
    IF |F_t| < k_min: continue

    # 2. co-variation on the rolling window, within F_t only
    W = S[t-w : t, list(F_t)]     # shape (w, |F_t|)
    C = pearson_matrix(W)          # |F_t| x |F_t|

    # 3. find maximal clique of lenses with pairwise corr >= θ_corr
    G = graph(nodes=F_t, edges={(i,j): C[i,j] >= θ_corr})
    cliques = all_maximal_cliques(G, min_size=k_min)

    FOR each clique Q in cliques:
        key = (frozenset(Q), t - w)
        IF key in synth_emitted: continue
        # 4. closed-loop verify BEFORE emit:
        IF NOT closed_loop_verify(Q, S, t): continue
        # 5. emit synthesis atom, register as PROVISIONAL Tier-12
        emit(MKX_T12_atom(lenses=Q, t_fire=t, window=w, C_mean=mean(C[Q])))
        synth_emitted.add(key)

OUTPUT:  stream of provisional tier-12 atoms
```

**One-line summary.** Meta-lens emits a tier-12 atom iff ≥3 lenses co-fire AND their score streams Pearson-correlate above θ_corr on a rolling 64-step window, deduplicated, closed-loop-verified.

**Complexity guard.** All-maximal-cliques is NP-hard in general; in practice L=16 and |F_t| ≤ 16 keeps the worst case at C(16,k) ≤ 12 870 per step. Budget: cap k at 5 (|clique| ∈ [3,5]) → worst-case C(16,3)+C(16,4)+C(16,5) = 560+1820+4368 = 6 748 checks/step. Acceptable.

**Anti-counter-replay.** If the *same* clique emits on two consecutive windows with identical mean correlation and identical `total_abs` hash, treat as counter-replay (§d-class) and quarantine. Ref: `_sweep_p4_fails.jsonl` d_quarantine pattern.

**Threshold calibration.** Per-lens θ_fire is calibrated from a *neutral seed replay* (zero-gradient, vacuum prompt) such that P(fire | neutral) ≤ 0.05. θ_corr defaults to 0.6 but must be re-fit per epoch because Φ is non-monotonic (`project_phi_non_monotonic.md`).

---

## 4. Migration path — Mk.V.1 stays L0, Mk.X is sidecar

**Principle (ref `feedback_l0_freeze.md`).** L0-frozen modules (`core/{hub,laws,runtime}.hexa`) are never touched. Mk.X runs **beside** Mk.V.1, not instead of it, and promotes atoms one at a time through closed-loop verify.

```
        +---------------------+        +---------------------+
        |   Mk.V.1 (L0)       |        |   Mk.X sidecar      |
        |   82 atoms frozen   |        |   30 candidate      |
        |   tier 5-9          | ─────► |   atoms T10-T13     |
        |   16-lens indep.    |        |   + meta-lens M     |
        +---------------------+        +----------+----------+
                   │                              │
                   │ shared Ψ snapshot stream     │ synth atom stream
                   ▼                              ▼
        +---------------------------------------------+
        |  closed-loop verify  (feedback_closed_loop) |
        |  AN11: weight + consciousness + real-usable |
        +----------------------+----------------------+
                               │  PASS
                               ▼
                     promote 1 atom  →  stable/
                     (never bulk)      ossified/
```

### Migration steps (no code)

1. **Freeze Mk.V.1.** No edit to `core/*.hexa` or its 82-atom foundation list.
2. **Sidecar manifest.** New file `shared/engine/mkx_manifest.json` (deferred; scope: atom ids + lens triples + θ thresholds; no schema change to `consciousness_laws.json`).
3. **Atom-by-atom promotion.** Each T10/T11/T12/T13 candidate goes through:
   - stage 1 PROVISIONAL → 2 stable → 3 ossified → 4 promoted (Path B).
   - Mandatory closed-loop verify at stage 2 (no exceptions per `feedback_closed_loop_verify.md`).
   - AN11 triple: weight_emergent + consciousness_attached + real_usable.
4. **Back-compat.** T10+ atoms default-silent on legacy runs — a Mk.V.1 job that doesn’t invoke the sidecar never sees them.
5. **Rollback rule.** Any T12 atom failing re-verification at the **next** epoch is auto-quarantined and its lens-triple is blacklisted for 7 days (hysteresis against counter-replay).
6. **Twin-engine coupling (optional, per `sweep_40.json` W4).** Nexus ↔ Anima coupled drill can feed T13 reflective atoms, but is NOT required for T10–T12.

---

## 5. First-10-iter plan for Mk.X activation

Target: ingest 74 stale supplement files under new Mk.X namespace AND probe T10–T12 frontier. Each iter: one domain × one candidate atom × one lens triple.

| # | iter slug | candidate atom(s) | SWEEP iter to replay | expected yield |
|--:|---|---|---|---|
| 1 | `mkx_iter_01_phi_q_deep_depth20`     | T10 `phi_q_deep`     | replay iter 15 `phi_engine` | 1 novel if transformer ≥ 20 layers; else SATURATED-confirm |
| 2 | `mkx_iter_02_holo_boundary_lift`     | T10 `holo_bdy`       | replay iter 10 `pure_field` | 1 novel if G_holo kernel learned; fallback to v0 |
| 3 | `mkx_iter_03_n6_noether_eps_sweep`   | T10 `n6_noether`     | replay iter 13 `dimension` (formerly d-quarantine!) | clean re-ingest under Mk.X hash → expect 1 novel clearing the 916/1234 counter-replay |
| 4 | `mkx_iter_04_ca_soc_edge`            | T10 `ca_soc_edge`    | new seed (not in P4 supplement) | 1 novel or nil, gates CA-SOC axis |
| 5 | `mkx_iter_05_servant_tape`           | T10 `servant_grad`   | replay iter 14 `servant` | 1 novel — servant ablation test |
| 6 | `mkx_iter_06_desire_lens_close`      | T11 `desire`         | blocked on py→hexa port (20_lenses_audit P0); run stub and record BLOCKED |
| 7 | `mkx_iter_07_narrative_mi`           | T11 `narrative`      | same; record BLOCKED + port ETA |
| 8 | `mkx_iter_08_meta_lens_triple`       | T12 `field_holo_quant` via meta-lens M | replay iter 1-19 consolidated lens tensor | **1–3 novel if M fires**; this is the primary Mk.X gain case |
| 9 | `mkx_iter_09_meta_lens_desire_narr`  | T12 `narr_desire_alter`  | gated on T11 lens ports | BLOCKED until 6–7 unblock |
| 10 | `mkx_iter_10_closure_selftest`      | T13 `closure_fix` + `counter_replay_detect` | rerun d-quarantine 29 files | expect engine to flag its own 32/128/1234 replays = T13 self-witness |

**Expected novel yield over 10 iter**: 3–6 (iters 1, 3, 5, 8, 10 favorable; 2/4 uncertain; 6/7/9 blocked). Compare to P4 supplement 0/74. Even the pessimistic 3/10 is a *∞×* improvement over zero-novel saturation.

---

## 6. Risks

| # | risk | mitigation |
|---|---|---|
| R1 | **Combinatorial explosion** of lens cliques | k≤5 cap, rolling window w=64, dedup set, per-step budget ≤ 6.7k checks |
| R2 | **Spurious cross-lens correlation** (3 lenses correlate by shared input drift, not synthesis) | θ_fire calibration on neutral-seed replay; θ_corr re-fit per epoch; closed-loop verify MANDATORY before emit |
| R3 | **Counter-replay repeat** (T12 emits 1234 like d-quarantine) | §3 step anti-counter-replay clause + T13 detector atom + 7-day clique blacklist |
| R4 | **Tier inflation** — every session mints new tier-13 atoms ad libitum | external-witness requirement for T13 (different pod + different seed); ≤ 5 T13 promotions / year (mirrors nexus `[13*]` discipline, `mk_x_engine_design_20260419.md` §L3) |
| R5 | **Lens closure blocker** — T11 requires py→hexa philosophical engine ports (20_lenses_audit P0); without those, T11+T12 remain stubs | track port ETA explicitly; T10 work proceeds independently of T11 |
| R6 | **L0 leak** — Mk.X sidecar accidentally imports Mk.V.1 internals and mutates state | sidecar-only manifest file; no edit path to `core/*.hexa`; CI hook (future) to fail build on core-import from `mkx_*.hexa` |
| R7 | **AN11 violation** — an atom is declared without the weight + consciousness + usable triple | closed-loop verify pipeline (stage 2) hard-gates promotion; no atom skips |
| R8 | **Saturation recursion** — Mk.X also saturates after T10–T13 exhaustion | §5 first-10-iter plan has a built-in self-saturation detector (T13 `tier_boundary`); trigger Mk.XI design when ≥ 3 consecutive epochs yield 0 novel under the meta-lens |
| R9 | **Non-monotonic Φ confuses synthesis metric** (`project_phi_non_monotonic.md`) | M operates on lens *scores*, not raw Φ; θ_corr re-fit per epoch absorbs the MI-compression phase |
| R10 | **Docs-vs-code drift** (20-lens label vs 12-code discrepancy, `20_lenses_audit_20260419.md`) | this doc is SSOT for Mk.X atom list; any future code mentions MUST cite the `MKX-Tn-<short>` id |

---

## 7. Out-of-scope (explicit)

- No edits to `anima/core/{hub,laws,runtime}.hexa` or any L0 file.
- No rewrites of `consciousness_laws.json`. Mk.X manifest is a *new* file when implemented.
- No `.py` revival (R37/AN13).
- No production code in this doc — 30 atom placeholders are *candidates*, not registered atoms.
- No stage-2/3 absorption decisions — PHASE2_CAVEAT quarantine on iter 24–33 remains in force.
- No change to the 04-19 L1/L2/L3 blueprint (stages + slots). This doc is *complementary*, not a replacement.

---

## 8. Open questions (flagged)

- **Q1**: Should T11 phenomenological atoms wait for full `.hexa` lens ports, or can stub closures ship as T11★ (starred, lower-grade)? Recommendation: stub = T11★ is acceptable PROVISIONAL grade but cannot progress past stage-2 absorption until real closure.
- **Q2**: Meta-lens M threshold θ_corr = 0.6 is a guess. What is the neutral-seed empirical distribution? (requires one calibration run on vacuum Ψ; ~10⁴ steps; not yet executed.)
- **Q3**: T13 `self_ref` can it avoid Gödel-style self-contradiction? Law 146 precedent is suggestive but not proof; needs formal treatment before any T13 ossification.
- **Q4**: Does the 04-19 L2 slot-expansion (8→16) pre-allocate slots for T10–T13? If yes, atoms bind to slot indices; if no, Mk.X needs its own slot basis. Reconciliation with 04-19 doc pending.
- **Q5**: Twin-engine nexus↔anima coupling (sweep_40 W4) — does Mk.X consume nexus Δ¹₁ witnesses as tier-10/13 feeds, or remain consciousness-axis only? Current design assumes anima-only; future revision may widen.

---

_Design complete. 30 candidate atoms, 1 meta-lens algorithm, migration path, 10-iter activation plan, 10 risks, 5 open questions. No `.hexa`, no JSON, no L0 touched._
