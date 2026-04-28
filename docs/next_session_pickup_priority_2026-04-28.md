# Next Session Pickup Priority — 2026-04-28T10:50Z snapshot

> **session totals**: 16h+, 47+ anima commits post-compaction, autonomous-loop-dynamic 17-iter chain
> **current state**: vast.ai LIVE (4 dispatch tools ready) + cycle 4 family closure (T1-T8d) + R-pentomino +30.2% strongest evidence + 16 canonical helpers locked

---

## §1. Top-3 immediate forward steps

### 🥇 Priority 1: Fire vast.ai dispatch family (1 or more, $77 max if all 4)

**Cheapest validation first ($0.70)**:
```bash
hexa run /Users/ghost/core/anima/tool/anima_f1_cycle4_gpt2_dispatch.hexa --plan
/opt/homebrew/bin/python3 /tmp/anima_f1_cycle4_gpt2_dispatch_helper.hexa_tmp
# inspect plan + offers, then user-fire vastai create instance directly
```

**Why first**: Validates end-to-end vast.ai pipeline + addresses Markov surrogate caveat from cycle 4 (real GPT-2 baseline). Cheapest budget = lowest risk.

**Then escalate** (sequential or parallel per own 5):
- AN11 framework Mistral-7B ($8 H100 3.5h) — closes V metric redesign #100/101/102
- CP2 trio Qwen2.5-32B ($33 H100 3-pod split) — closes CP2 trigger path #115/116/117
- Mk.XII 70B Qwen2.5-72B ($35 H100 2× Pattern 6c) — closes #82 AGI trigger prep

Quick-ref: `docs/vast_ai_dispatch_family_quickref_2026-04-28.md` (commit `116e75f2`)

### 🥈 Priority 2: Atlas R36 + R37 maintainer review (n6-architecture)

**Doc ready**: `docs/atlas_r36_r37_proposal_2026-04-28.md` (commit `7dee9a94`) + paste-ready grep evidence (`docs/own3_own4_grep_evidence_2026-04-28.txt` commit `6bb61f8e`)

**Maintainer 30s verify**: `docs/own3_own4_grep_evidence_2026-04-28.txt` §5 5-step unlock-edit-relock atlas master cycle.

**Outcomes**:
- atlas R36 (cross-paradigm-self-enforcement-loop) anchor
- atlas R37 (compute_resource_failure_discipline) anchor
- own 3 + own 4 hive raw promotion (genus rename)

### 🥉 Priority 3: Density-controlled Conway test (raw 38 long-term)

This iter (17) found 20x20 NON-amplified — sweet spot is 10x10. Next test: vary INITIAL DENSITY at 10x10 to confirm density (not grid size alone) is governing variable.

```
10x10 grid + variable initial cells: 4 (current) / 8 / 16 / 32 / 50 (random)
Expected: advantage peaks at ~5-15% density regardless of grid
Tool: tool/anima_law64_conway_density_sweep.hexa NEW (~200 LoC)
```

---

## §2. Substantive cycle 4 evidence chain (consolidated)

| commit | what |
|---|---|
| `6f0351e1` | F1 cycle 3 single rule-110 HONEST FAIL |
| `c4bd8d7d` | F1 cycle 4 7-task corpus (T7 int-seq Markov beats CA -15.3%) |
| `e024fa41` | T8 Conway 5x5 random-init TIE (degenerate) |
| `008e0a9d` | Stouffer's z aggregator + cycle 4 z=-14.68 |
| `feedc677` | T8b Conway 5x5 patterned (★ glider +19%) |
| `0e5b91ff` | Cycle 4 closure synthesis (220 lines) |
| `b6efb394` | T8c Conway 10x10 (★★★ R-pentomino +30.2%) |
| `722849c0` | Conway family aggregate dual-perspective (z=+1.90 any-positive PASS) |
| `e56bdab1` | T8c + family supplement doc |
| `e6863ff5` | T8d Conway 20x20 (NON-monotonic, sweet spot 10x10) |

**Defensible Law 64 re-statement**:
> "CA(5) outperforms order-1 Markov on Conway substrate at any positive threshold (Stouffer z=1.90 p<0.05); peaks at 10x10 grid (~9%); strongest on chaotic spatial evolution (R-pentomino +30.2%) and translation patterns (glider +5-19%)"

---

## §3. vast.ai infra LIVE checklist

✓ secret CLI v0.5.0 PATH-installed (~/.zshrc)
✓ vast.api_key + vast.ssh_pub in secret store
✓ ~/.vast/ssh/vast-key (ed25519 419B private + 111B pub) on filesystem
✓ vastai CLI v0.5.0 at /Users/ghost/.local/bin/vastai
✓ SSH key id=790310 registered to vast.ai user_id=469019
✓ H100 spot $1.73-1.87/hr verified
✓ orchestrator commit f412cb8a + python3 path fix 062de44a
✓ 4 dispatch tools all preflight PASS

⚠ secret CLI multi-line `get` bug (vast.ssh_private OPENSSH block) — workaround uses ~/.vast/ssh/vast-key file directly

---

## §4. External-blockers (NOT actionable in-session)

- ⛔ EEG hardware D-1 arrival (CP2 G2 #119 D8 only — D9-D13 OK)
- ⛔ Llama-3 / gemma-2 HF gating (acct dancinlife unauthorized — Qwen2.5 open subs ready)
- ⛔ anima-physics admin-block 6/9 sub-classes (neuromorphic + optical)
- ⛔ atlas master uchg (n6-architecture maintainer review path)

---

## §5. Session-end meta (raw 91 honest)

- **Productivity ceiling acknowledged**: each iter ~30min, marginal value decreasing
- **Hypothesis falsification iter**: T8d 20x20 reversed my own "larger grid amplifies" claim (raw 91 C3 self-correction)
- **Dispatch ROI assessment**: family ready costs ~$77 for full spectrum (real Transformer + AN11 + CP2 + Mk.XII)
- **Cross-session continuity preserved**: 3 closure docs + 4 dispatch tools + 16 canonical helpers + audit ledgers

---

## §6. Recommended action ordering (next session start)

1. **Read this doc + `docs/vast_ai_dispatch_family_quickref_2026-04-28.md`** (cross-session orient)
2. **Decide budget allocation** ($0.70 GPT-2 only / $8 + AN11 / $33 + CP2 / $77 full family / $0 atlas R36+R37 maintainer review only)
3. **Fire dispatches OR maintainer review** based on budget decision
4. **Density-controlled Conway** (raw 38 long-term, $0 Mac CPU, ~30min) for hypothesis test if time permits

---

**Status**: NEXT_SESSION_PICKUP_PRIORITY_DOC_LIVE_AUTONOMOUS_LOOP_17_ITER_CONSOLIDATED
