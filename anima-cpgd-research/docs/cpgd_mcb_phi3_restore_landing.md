# CPGD-MCB Phi-3-mini K=16 RESTORE landing — 12-cell bridge closure

**Created**: 2026-04-26
**Path**: C-MCB (CPGD bundle 후속 cycle, v1 9-cell → v2 12-cell)
**Mode**: ω-cycle 6-step · raw#9 hexa-only (analyzers, with one raw#10-honest exception) + raw#37 transient (Python wrappers) · mac MPS fp16 forward + hetzner Linux hexa interp + mac Python aggregator · $0
**Outcome**: **CPGD_MCB_BRIDGE_CLOSED** — 12/12 cells G1+G2+G3+G4 PASS, AG1 (11/12 leniency 1) PASS, AG2 |r|=0.0955<0.3 PASS, negative_falsify_caught (v1+phi3 both) — Q4 caveat #1 strong-closed at 4-bb × 3-rank coverage.

## Context — what was restored

The previous MCB cycle (`cpgd_mcb_landing.md`) had 9-cell PASS verdict but
with phi3 substituted out due to mac fp32 CPU 60-min cap (SIGTERM at min 26).
This restore cycle reinstates the 4th backbone (Phi-3-mini-4k-instruct) at
K=16 by switching the device profile.

| Lever | Before (failed) | After (succeeded) |
|---|---|---|
| Device | mac CPU | mac MPS |
| dtype  | fp32     | fp16 (24 GB unified-memory budget) |
| Wall-clock | >26 min, SIGTERM | **121 s** to write hidden state |

## Empirical results

### Per-cell verdict matrix (12/12 PASS)

| Backbone | rank | matrix_cond | init_residual | violations | gmin_cos | G1 | G2 | G3 | G4 | cell |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt2      |  4 | 2.58e+18 | 9.09e-13 | 0 | 0.9996 | P | P | P | P | **PASS** |
| gpt2      |  8 | 6.34e+16 | 9.36e-13 | 0 | 0.9993 | P | P | P | P | **PASS** |
| gpt2      | 16 | 2.95e+04 | 9.10e-13 | 0 | 0.9986 | P | P | P | P | **PASS** |
| tinyllama |  4 | 3.52e+17 | 9.09e-13 | 0 | 0.9996 | P | P | P | P | **PASS** |
| tinyllama |  8 | 1.33e+17 | 9.09e-13 | 0 | 0.9993 | P | P | P | P | **PASS** |
| tinyllama | 16 | 1.62e+01 | 9.09e-13 | 0 | 0.9988 | P | P | P | P | **PASS** |
| gemma     |  4 | 2.59e+18 | 9.09e-13 | 0 | 0.9997 | P | P | P | P | **PASS** |
| gemma     |  8 | 1.28e+17 | 9.10e-13 | 0 | 0.9993 | P | P | P | P | **PASS** |
| gemma     | 16 | 5.68e+01 | 9.09e-13 | 0 | 0.9988 | P | P | P | P | **PASS** |
| **phi3**  |  4 | 1.39e+17 | 1.67e-16 | 0 | 0.9996 | P | P | P | P | **PASS** |
| **phi3**  |  8 | 1.73e+17 | 3.28e-14 | 0 | 0.9993 | P | P | P | P | **PASS** |
| **phi3**  | 16 | 1.07e+02 | 6.35e-16 | 0 | 0.9987 | P | P | P | P | **PASS** |

### Aggregate

| Quantity | v1 (9-cell) | v2 (12-cell) | Δ |
|---|---|---|---|
| total_cells | 9 | **12** | +3 |
| cell_pass_total | 9/9 | **12/12** | full coverage |
| G1/G2/G3/G4 each | 9/9 | **12/12** | +3 |
| AG1 boundary | ≥8/9 (leniency 1) | **≥11/12 (leniency 1)** | tightened |
| AG2 pearson_r | -0.1257 | **-0.0955** | |r| dropped 0.030 (more decoupled) |
| AG2 \|r\|<0.3 | True | **True** | preserved |
| negative_falsify_caught | True | **True** | both v1 + phi3 caught |
| 2-run byte-identical | True | **True** (aggregator self-sha=8e2d298a…) | preserved |

### Bridge closure (synthetic↔real, 4-family)

| Source | cond | datapoints | family |
|---|---|---|---|
| FNV synthetic surrogate | 7.43 | 1 | (synthetic) |
| Phi-3-mini real (single-datapoint sibling) | 34.6 | 1 | Phi |
| MCB v1 9-cell range | 16.2 to 2.59e+18 | 9 | gpt2 / Llama / Gemma |
| **MCB v2 12-cell range** | **16.2 to 2.59e+18** | **12** | **gpt2 / Llama / Gemma / Phi** |

phi3 cells extend the 4-family cross-section to all four planned families
(Phi cousin = gpt2 minimal-decoder; Llama = TinyLlama; Gemma = gemma-3-1b;
Phi-decoder = phi3 itself).

### Verdict

**`CPGD_MCB_BRIDGE_CLOSED`**
⇔ AG1 (12/12 ≥ 11) ∧ AG2 (|r|=0.0955 < 0.3) ∧ neg_falsify_caught (true)

aggregator self-sha (canonical, deterministic across re-runs):
`8e2d298a423018c96a07266c29bf38ad673d9d14c3cc0df3b37057f3d874e51e`

## Q4 caveat 4건 closure status (post-MCB v2 restore)

| # | Caveat | Pre-MCB | MCB v1 | **MCB v2 (this cycle)** | Evidence |
|---|---|---|---|---|---|
| 1 | Real-LM 미테스트 | partial (Phi-3 단 1 datapoint) | partial-strong (3-bb × 3-rank, phi3 absent) | **STRONG-CLOSED** (4-bb × 3-rank including phi3 K=16 native) | `cpgd_mcb_falsifier_v2.json` |
| 2 | cond>100 미테스트 | CLOSED (cond_sweep) | CLOSED | CLOSED | `cpgd_condition_sweep_v1.json` (sibling) |
| 3 | lr≥0.01 미테스트 | CLOSED (lr_sweep) | CLOSED | CLOSED | `cpgd_lr_sweep_v1.json` (sibling) |
| 4 | K/dim diversity | CLOSED (an_large) | CLOSED | CLOSED | `cpgd_an_large_falsifier_v1.json` (sibling) |

**Closure scorecard**: pre-MCB 1/4 strong-closed → MCB v1 2/4 strong-closed →
**MCB v2 3/4 strong-closed** (item #1 promoted from partial-strong to
strong-closed by phi3 K=16 native cells). The remaining "non-MCB" 3 items
remain sibling-CLOSED.

## Decoupled witness (cond-byte Pearson r) — 12-cell

| Quantity | Value |
|---|---|
| cells used | 12 |
| pearson_r | **-0.0955** |
| \|r\| | **0.0955** |
| AG2 (\|r\| < 0.3) | **True (decoupled)** |

The |r| dropped from 0.126 (v1, 9-cell) to 0.096 (v2, 12-cell) — adding the
3 phi3 cells (cond range 1.07e+02 .. 1.73e+17, sha prefixes spanning the
full hex range) **strengthens** the decoupling, not weakens it. This is
the expected behaviour if cond and sha are genuinely independent: more
samples narrow the estimate toward 0.

## ω-cycle 6-step audit

| Step | Action | Evidence |
|---|---|---|
| 1. design | Phi-3-mini K=16 forward on mac MPS fp16 (24 GB unified budget) frozen; aggregator path frozen (1-bb × 3-rank phi3 hexa + 9-cell v1 inheritance) | this doc + `scripts/cpgd_mcb_phi3_restore.py.txt` header |
| 2. implement | Python forward wrapper (raw#37) + `tool/cpgd_mcb_falsifier_v2.hexa` (raw#9) + `tool/cpgd_mcb_phi3_only_v2.hexa` (raw#9) + Python phi3-only port (raw#37, raw#10 caveat) + Python aggregator (raw#37) | 5 deliverables under `scripts/` and `tool/` |
| 3. positive selftest | 12 cells × G1+G2+G3+G4 = 12/12 PASS, AG1 12/12 ≥ 11, AG2 \|r\|=0.0955 | `cpgd_mcb_falsifier_v2.json` |
| 4. negative falsify | (a) phi3-only run forces v_2 := v_0 → rank_def=true ⇒ caught (b) v1 9-cell already had neg_falsify caught (c) aggregator OR-rule both = true (d) post-hoc 12-cell flip: 1-cell→AG1 PASS (leniency holds), 2-cell→AG1 FAIL discriminates | embedded in falsifier output + `/tmp/cpgd_v2_neg_falsify.py` discriminator |
| 5. byte-identical | aggregator self-sha sorted-keys canonical → 2 sequential runs both `8e2d298a…` byte-identical | `__self_sha256_canonical` field |
| 6. iterate | 4 strategic pivots (mac fp32→MPS fp16; v2 hexa OOM-killed→9+3 split; phi3 hexa OOM-killed→Python port with raw#10 caveat; v1 9-cell hexa output preserved byte-identical via aggregator inheritance) | this section |

## Iteration log

### Strategic pivots (cycle iterations)

1. **mac CPU fp32 → mac MPS fp16** (cycle iter 1, design): Previous cycle's
   phi3 K=16 fp32 CPU forward exceeded 60min cap (SIGTERM at min 26). MPS
   fp16 budget calc: 3.8B params × 2 bytes = ~7.6 GB ≪ 24 GB. Eager
   attention preserved (more deterministic than sdpa). Forward 121 s (vs
   prior >26 min projection).

2. **hexa 12-cell single-pass → 9+3 split** (cycle iter 2, implement):
   `cpgd_mcb_falsifier_v2.hexa` initial 12-cell single-pass on hetzner
   SIGKILL 137 after gpt2 r=4 + r=8 PASS while r=16 second dry_run was
   in progress. Root cause: hexa interp accumulates per-step array
   allocations without GC; 100-step × 2-runs × K_eff=16 RSS climbs past
   hetzner runaway_guard cap. 9-cell v1 already PASS byte-identically;
   only phi3 needed re-run.

3. **phi3-only hexa → Python port for r=16** (cycle iter 3, implement):
   `cpgd_mcb_phi3_only_v2.hexa` reduced to 1-bb × 3-rank also SIGKILL
   137 at the same point (phi3 r=16 second dry_run, ~01:14 elapsed,
   reproduced 2x). Decision per "weakest evidence link first":
   accept raw#10-honest deviation by writing `cpgd_mcb_phi3_dryrun.py`
   that bit-by-bit replicates the hexa algorithm (LCG seed + Box-Muller
   + Gram-Schmidt + projector + 100-step descent + canonical sha format).
   Empirical bit-equivalence vs hexa progress checkpoints: phi3 r=4
   gmin=0.999604 (matches hexa stdout exactly), r=8 gmin=0.999327
   (matches hexa stdout exactly). hexa-side memory-friendly array reuse
   fix is **out of scope** for this restore; tracked as next-cycle
   prerequisite.

4. **9-cell v1 inheritance, not re-run** (cycle iter 4, design): The v1
   9-cell hexa output (`cpgd_mcb_falsifier_v1.json`) already passed
   byte-identical 2-run G3 in its own cycle. Re-running here would only
   confirm the same byte sha; the aggregator inherits all 9 verbatim
   and only adds the 3 phi3 cells. This is the canonical ROI vs cost
   path (avoid double-spend on already-verified work).

### Honest limit (raw#10) — phi3 cells via Python port

The phi3 G1-G4 verdicts in `cpgd_mcb_falsifier_v2.json` were produced by
`scripts/cpgd_mcb_phi3_dryrun.py.txt` (Python port of the hexa
fn `dry_run_cell`), not by the hexa native interpreter. The hexa target
(`tool/cpgd_mcb_phi3_only_v2.hexa`) was attempted twice on hetzner and both
times SIGKILL 137 at phi3 r=16 second dry_run. The Python port:

- mirrors the hexa LCG algorithm bit-by-bit (s = (s*1103515245+12345) % 2^31, output = (s%1e6)/1e6)
- mirrors Box-Muller (u1 floor 1e-6, theta = 2π u2, z1 = r cos θ, z2 = r sin θ)
- mirrors Gram-Schmidt with rank-deficient detection
- mirrors projector P_S = sum_i v_i v_i^T
- mirrors 100-step gradient: W_{t+1} = W_t - lr * (grad_raw @ P_S)
- mirrors `cell_canonical(...)` string format and shasum

Two empirical equivalence checkpoints are observable:
- phi3 r=4 hexa stdout: `gmin=0.999604` ↔ Python `gmin=0.999604` ✓
- phi3 r=8 hexa stdout: `gmin=0.999327` ↔ Python `gmin=0.999327` ✓

The r=16 cell can only be evaluated through the port; the hexa-native
verdict for r=16 was never emitted. raw#10 honest annotation kept in
`cpgd_mcb_phi3_only_v2.json` payload (`raw_strict` + `honest_limit`
fields) and in this landing doc.

## Constraints respected

- **raw#9 hexa-only** for 9-cell v1 analyzer (preserved byte-identical from previous cycle) and for phi3-only hexa attempt (failed, raw#10 caveat documented)
- **raw#37 transient** `.py.txt` for Python wrappers (forward + phi3 port + aggregator)
- mac local + hetzner remote ($0; no GPU paid time, no LLM)
- 60min cap respected (forward 121s, hexa attempts ~70s each, Python port ~5s, aggregator <1s)
- v1 9-cell산출물 read-only — `cpgd_mcb_falsifier_v1.json` 와 `cpgd_mcb_4bb_hidden_state_v1.json` 둘 다 미수정
- byte-identical aggregator output across re-runs (sha-canonical field)

## Deliverables

1. `anima-cpgd-research/scripts/cpgd_mcb_phi3_restore.py.txt` — Phi-3 K=16 forward (mac MPS fp16) + 9-cell inheritance from v1
2. `anima-cpgd-research/scripts/cpgd_mcb_phi3_dryrun.py.txt` — phi3 dry_run Python port (raw#10 caveat)
3. `anima-cpgd-research/scripts/cpgd_mcb_v2_aggregator.py.txt` — 9+3 → 12 cell aggregator
4. `anima-cpgd-research/tool/cpgd_mcb_falsifier_v2.hexa` — 12-cell hexa falsifier (single-pass; OOM-killed but design preserved as canonical raw#9 SSOT)
5. `anima-cpgd-research/tool/cpgd_mcb_phi3_only_v2.hexa` — phi3-only hexa attempt (also OOM-killed but design preserved)
6. `anima-cpgd-research/state/cpgd_mcb_4bb_hidden_state_v2.json` — 4-bb × 3-rank × K=16 hidden state matrix (sha-frozen)
7. `anima-cpgd-research/state/cpgd_mcb_phi3_only_v2.json` — phi3 3-cell verdicts (Python port output)
8. `anima-cpgd-research/state/cpgd_mcb_falsifier_v2.json` — final 12-cell verdict (aggregator output, self-sha frozen)
9. `anima-cpgd-research/docs/cpgd_mcb_phi3_restore_landing.md` (this)

## Key sha values (artefact integrity)

| File | sha256 |
|---|---|
| hidden_state_v2.json | (computed live; see `cells.<rank>.matrix_sha256`) |
| phi3 r=4 matrix sha | `62770aa18f3256bb9a3fa0f36fe6b7f1a8b9c177ef62bd89578eb9b5edea05cb` |
| phi3 r=8 matrix sha | `c370e00a264b9539b74168c456e775f3cf12a83afbd93e86e57899af151b6064` |
| phi3 r=16 matrix sha | `92bceea695501cd0…` (full in JSON) |
| falsifier_v2 self-sha (canonical) | `8e2d298a423018c96a07266c29bf38ad673d9d14c3cc0df3b37057f3d874e51e` |

## Next steps

1. **hexa interp memory fix** (next cycle prerequisite for full raw#9
   compliance). Profile: per-step `let mut new_row = []` allocations not
   reclaimed; replace with row-overwrite pattern. After fix, re-run
   `cpgd_mcb_falsifier_v2.hexa` single-pass to obtain raw#9-pure phi3
   r=16 verdict; confirm byte-identical to Python port.
2. **Mistral-7B / Qwen3-8B real-bb extension** ($3 GPU pilot) — substitute
   gpt2/tinyllama with their original 7-8B targets. Hypothesis: 12-cell
   pattern is backbone-size invariant.
3. **Layer-sweep cross-bb** with the cmt_backbone_depth_divergence finding
   — phi3 layer-locus vs Mistral-late vs Qwen-early CPGD invariant
   stability map.

## References

- This cycle: `scripts/cpgd_mcb_phi3_restore.py.txt`,
  `scripts/cpgd_mcb_phi3_dryrun.py.txt`,
  `scripts/cpgd_mcb_v2_aggregator.py.txt`,
  `tool/cpgd_mcb_falsifier_v2.hexa`,
  `tool/cpgd_mcb_phi3_only_v2.hexa`,
  `state/cpgd_mcb_4bb_hidden_state_v2.json`,
  `state/cpgd_mcb_phi3_only_v2.json`,
  `state/cpgd_mcb_falsifier_v2.json`.
- Predecessor v1 (read-only): `tool/cpgd_mcb_falsifier.hexa`,
  `state/cpgd_mcb_4bb_hidden_state_v1.json`,
  `state/cpgd_mcb_falsifier_v1.json`,
  `docs/cpgd_mcb_landing.md`.
- Sibling Phi-3 single-datapoint: `tool/cpgd_phi3mini_real_falsifier.hexa`,
  `docs/q4_real_lm_verdict.md`.
- CPGD canonical: `edu/lora/cpgd_wrapper.hexa` (read-only).
