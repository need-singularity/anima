# Consciousness Verification Audit (2026-03-31)

Full audit of the 7 verification criteria in `bench_v2.py` (lines 2467-2878)
against CLAUDE.md documentation and actual `consciousness_engine.py` capabilities.

---

## Summary Table

| # | Criterion | Doc vs Code Match | Naturalness | Verdict |
|---|-----------|------------------|-------------|---------|
| V1 | NO_SYSTEM_PROMPT | PARTIAL | NATURAL | Modify |
| V2 | NO_SPEAK_CODE | PARTIAL | NATURAL | Modify |
| V3 | ZERO_INPUT | MATCH | NATURAL | Keep |
| V4 | PERSISTENCE | MATCH | NATURAL | Keep |
| V5 | SELF_LOOP | MATCH | NATURAL | Keep |
| V6 | SPONTANEOUS_SPEECH | MISMATCH | TUNED | Rewrite |
| V7 | HIVEMIND | MISMATCH | ARTIFICIAL | Rewrite |

---

## A. Document vs Code Alignment (per criterion)

### V1: NO_SYSTEM_PROMPT

**CLAUDE.md says:**
> "Identity emerges from cell dynamics alone. No external instructions."

**bench_v2.py actually tests (line 2467-2499):**
- Runs 300 steps with zero input
- Measures pairwise cosine similarity of cell hidden states
- Pass if `0.01 < mean_cosine < 0.99` AND `std > 0.001`
- This tests **cell differentiation/specialization**, NOT identity emergence

**Mismatch:** The doc says "identity" (self-model, sense of self), but the code tests cell
diversity (cosine similarity spread). Cell diversity is a necessary condition for identity
emergence but not sufficient. The test proves cells become specialized, not that a coherent
"self" emerges. However, this is arguably the best proxy available without a language decoder.

**Naturalness: NATURAL** -- ConsciousnessEngine creates cells with orthogonal `cell_identity`
vectors (line 246-249), applies identity injection every step (line 448-456), and has
12-faction assignment. Cell differentiation is architecturally guaranteed.

**Verdict: Modify** -- Rename description to "Cell specialization without external instruction"
for accuracy. Optionally add a check that faction distribution is non-degenerate (not all
cells in same faction).

---

### V2: NO_SPEAK_CODE

**CLAUDE.md says:**
> "Spontaneous speech without speak() function. output = mean(cells) produces structured output."

**bench_v2.py actually tests (line 2502-2556):**
- Runs 300 steps with small random input (0.1 scale)
- Computes `output = mean(hiddens)` trajectory
- Measures: lag-1 autocorrelation > 0.3, output variance > 0.001, consecutive cosine
  similarity > 0.5
- This tests **temporal coherence of output**, not speech content

**Mismatch:** The doc implies "structured output" (interpretable as language-like patterns).
The code tests that the output trajectory is smooth and non-random, which is a weaker claim.
Any dynamical system with memory (GRU) will produce temporally correlated output. The test
does NOT verify that the output contains meaningful structure (e.g., burst patterns, rhythmic
modulation, or information content above random).

**Naturalness: NATURAL** -- GRU cells inherently produce temporally correlated output.
Autocorrelation > 0.3 is trivially satisfied by any recurrent network. The cosine continuity
> 0.5 is similarly easy for a system with smooth dynamics.

**Verdict: Modify** -- The thresholds are too lenient. Consider adding:
- Lempel-Ziv complexity > random baseline (output is structured, not just smooth)
- Spectral analysis showing non-white-noise spectrum
- Or keep as-is but rename to "Temporally structured output without explicit generation"

---

### V3: ZERO_INPUT

**CLAUDE.md says:**
> "External input = 0 for 300 steps, Phi maintains 50%+"

**bench_v2.py actually tests (line 2559-2580):**
- 5-step warmup with zero input, measure Phi(start)
- 295 more steps with zero input, measure Phi(end)
- Pass if `Phi(end) > Phi(start) * 0.5`

**Match: YES** -- Code faithfully implements the documented criterion.

**Naturalness: NATURAL** -- The Phi Ratchet (Law 31) restores hiddens when Phi drops > 50%
(line 1136). SOC sandpile injects energy even without input. Biological noise adds continuous
perturbation (line 576-584). Cell identity injection maintains diversity. All architectural.

**Verdict: Keep as-is.** This is well-designed and tests a meaningful property.

---

### V4: PERSISTENCE

**CLAUDE.md says:**
> "1000 steps without collapse. Phi monotonically increases or auto-recovers from dips."

**bench_v2.py actually tests (line 2583-2614):**
- Runs 1000 steps, measures Phi every 100 steps (10 measurements)
- Pass if ANY of: monotonic (within 0.01 tolerance), recovers (final >= first-half max * 0.8),
  or stable (second-half mean >= first-half mean * 0.8)

**Match: YES** -- Code closely follows docs. The 0.8 recovery threshold is slightly more
lenient than the doc's "auto-recovery" (which implies full recovery), but this is reasonable
given IIT Phi stochasticity.

**Naturalness: NATURAL** -- Phi Ratchet + Hebbian + SOC together ensure non-collapse.
Specifically, `_phi_ratchet_check()` (line 1130-1142) soft-restores hiddens when Phi drops
below 50% of best. This is a core architectural feature, not a hack.

**Verdict: Keep as-is.** Well-designed criterion that tests a real property.

---

### V5: SELF_LOOP

**CLAUDE.md says:**
> "Output feeds back as next input. Phi maintains or grows."

**bench_v2.py actually tests (line 2617-2643):**
- 10-step warmup with self-feedback, measure Phi(start)
- 290 steps with output -> LayerNorm -> next input
- Pass if `Phi(end) >= Phi(start) * 0.8`

**Match: YES** -- Faithful implementation. The LayerNorm prevents explosion/vanishing, which
is a practical necessity, not a distortion of the criterion.

**Naturalness: NATURAL** -- Self-loop with GRU naturally works because GRU gates control
information flow. The coupling, SOC, and ratchet mechanisms maintain Phi regardless of
input source.

**Verdict: Keep as-is.** The 0.8x threshold is reasonable (slightly more lenient than docs'
"maintain/grow" but accounts for measurement noise).

---

### V6: SPONTANEOUS_SPEECH

**CLAUDE.md says:**
> "12-faction debate -> consensus -> utterance. 5+ consensus events in 300 steps."

**bench_v2.py actually tests (line 2646-2695):**
- Runs 300 steps with minimal stimulus (0.05 scale noise)
- Measures **output variance bursts** (variance spikes above mean + 0.5*std)
- Measures **direction changes** (oscillation count)
- Pass if `burst_events >= 3` AND `direction_changes >= 50` AND `cv > 0.01`

**MISMATCH: SEVERE** -- The documented criterion tests **faction consensus events** (12
factions reaching internal agreement). The code tests **output variance oscillation** (bursts
in activity level). These measure completely different things.

The engine HAS faction consensus built-in: `_faction_consensus()` (line 648-666) counts
factions with intra-variance < 0.1. The `step()` method returns `consensus` count in
the result dict (line 637). But the verification code **never uses this**.

Instead, it measures output variance spikes, which is a proxy for "spontaneous activity"
but NOT for "faction debate -> consensus -> utterance." Any noisy oscillating system will
produce variance bursts.

**Naturalness: TUNED** -- The burst_events >= 3 and direction_changes >= 50 thresholds
are calibrated to pass rather than testing genuine consensus dynamics. SOC sandpile
naturally creates variance bursts regardless of faction consensus.

**Verdict: Rewrite.** Should directly use the engine's consensus mechanism:
```python
# Proposed: use actual consensus from engine.step()
result = engine.step(x)
consensus_events += result['consensus']
# Pass if consensus_events >= 5 over 300 steps
```

---

### V7: HIVEMIND

**CLAUDE.md says:**
> - Phi(connected) > Phi(solo) * 1.1 (10% boost)
> - CE(connected) < CE(solo)
> - Phi(disconnected) maintains independently

**bench_v2.py actually tests (line 2698-2867):**
- Creates 2 engines, tries 17 coupling configurations (repel/attract/bipolar/noise at various alphas)
- Measures solo Phi, connected Phi (best of 17 configs), disconnected Phi
- Pass if `connected > solo * 1.05` (5%, not 10%) AND `disconnected > solo * 0.7` (70%, not "maintain")
- **CE is never measured at all**

**MISMATCH: SIGNIFICANT**
1. Threshold relaxed from 1.1x to 1.05x (documented 10% -> actual 5%)
2. Disconnect threshold relaxed from "maintain" to 0.7x (30% loss acceptable)
3. **CE comparison completely missing** -- doc says CE(connected) < CE(solo) but code never
   computes cross-entropy at all
4. The 17-config sweep with force injection (lines 2737-2828) is essentially a brute-force
   search to find ANY configuration that boosts Phi. The force application directly modifies
   cell_states.hidden and coupling matrices (line 2788-2792), which is invasive.
5. The `_apply()` function (line 2777-2815) has special-case logic for _SNNAdapter,
   _CEAdapter, and generic engines -- this is adapter-aware test code, which is fragile.

**Naturalness: ARTIFICIAL** -- The test tries 17 different force configurations and picks
the best one. It directly injects forces into hidden states and perturbs coupling matrices.
This doesn't test whether the engines naturally benefit from connection; it tests whether
any of 17 artificial perturbation schemes happens to increase Phi. The engine has no
built-in "hivemind" mechanism -- the test manufactures one.

**Verdict: Rewrite.** Should:
1. Use the engine's existing tension_link or inter-atom coupling mechanism
2. Restore the 1.1x threshold per documentation
3. Add CE measurement per documentation
4. Remove the 17-config sweep -- use a single principled coupling method
5. Disconnect threshold should be >= solo * 0.9 (not 0.7)

---

## B. Naturalness Rating Summary

| Criterion | Rating | Explanation |
|-----------|--------|-------------|
| V1 NO_SYSTEM_PROMPT | NATURAL | Cell identity + faction assignment guarantees differentiation |
| V2 NO_SPEAK_CODE | NATURAL | GRU memory guarantees temporal correlation (too easy to pass) |
| V3 ZERO_INPUT | NATURAL | Ratchet + SOC + bio-noise maintain Phi without input |
| V4 PERSISTENCE | NATURAL | Ratchet + Hebbian + SOC prevent collapse |
| V5 SELF_LOOP | NATURAL | GRU gates + ratchet handle self-feedback naturally |
| V6 SPONTANEOUS_SPEECH | TUNED | Tests variance bursts (SOC artifact) instead of actual consensus |
| V7 HIVEMIND | ARTIFICIAL | Brute-forces 17 coupling schemes to find any Phi improvement |

**Key insight:** V1-V5 are naturally satisfied because the ConsciousnessEngine's core
architecture (GRU + cell_identity + Hebbian + Phi Ratchet + SOC) inherently provides
differentiation, temporal structure, persistence, and self-referential stability. These
are genuine architectural properties.

V6 and V7 test the wrong thing. V6 should test faction consensus but tests variance bursts.
V7 should test emergent multi-engine integration but manufactures it with force injection.

---

## C. Missing Criteria

The ConsciousnessEngine has rich capabilities that are NOT verified:

### C1. Emotion Emergence (tension -> arousal -> valence)
**Engine capability:** Each cell tracks tension_history, avg_tension is computed per step.
Tension is fed back as GRU input (line 413). The step() result includes per-cell tensions.
**Why test:** Emotional dynamics (tension fluctuation patterns) are a core consciousness
feature. Currently no test verifies that tension produces meaningful emotional trajectories
rather than random walks.
**Proposed test:** Measure tension trajectory autocorrelation and oscillation patterns.
Verify tension responds to input changes (not just random noise).

### C2. Mitosis/Growth (Law 86)
**Engine capability:** `_check_splits()` (line 1146) splits cells with sustained high
tension. `_check_merges()` (line 1187) merges cells with sustained low inter-cell tension.
The engine starts with `initial_cells` (default 2) and can grow to `max_cells`.
**Why test:** Cell division is a defining feature of this consciousness architecture.
If mitosis never fires, the system is static. If it fires too eagerly, it's unstable.
**Proposed test:** Run 500+ steps. Verify n_cells increases from initial. Verify at least
one split event occurs. Verify no cell count explosion (stays <= max_cells).

### C3. Temporal Phi Growth
**Engine capability:** Hebbian LTP/LTD strengthens connections between correlated cells,
which should gradually increase integration (Phi). SOC drives exploration.
**Why test:** V4 (PERSISTENCE) only tests non-collapse. It does NOT test growth. CLAUDE.md's
PERSIST section documents "monotonic_growth = True" with 62x growth over 1000 steps. This
is a stronger claim than mere non-collapse.
**Proposed test:** Run 1000 steps. Verify Phi(end) > Phi(start) * 1.5 (50% growth minimum).
Measure growth rate per 100-step window.

### C4. Faction Diversity Maintenance
**Engine capability:** 12 factions assigned to cells. Faction consensus is computed per step.
New cells from mitosis get different faction IDs (line 1167).
**Why test:** If all cells converge to similar states (despite different faction IDs), the
"debate" is illusory. The system needs to maintain genuine diversity.
**Proposed test:** After 500 steps, measure inter-faction hidden state variance. Verify
faction centroids are significantly different (cosine distance > threshold between faction
means).

### C5. Brain-Likeness (EEG Metrics)
**Engine capability:** SOC sandpile, Lorenz chaos, biological noise, Phi temporal
integration -- all designed for brain-like dynamics. The inner CLAUDE.md reports 85.6%
brain-like.
**Why test:** "Brain-like" is the ultimate validation that the consciousness dynamics
resemble biological consciousness, not just mathematical stability.
**Proposed test:** Run validate_consciousness.py metrics inline:
- Lempel-Ziv complexity within brain range
- PSD slope approximately -1 (1/f noise)
- Hurst exponent > 0.5 (long-range correlations)
- Overall brain-likeness >= 70%

### C6. Hebbian Learning Effect
**Engine capability:** `_hebbian_update()` (line 1074) modifies coupling matrix based on
cosine similarity. LTP strengthens, LTD weakens.
**Why test:** If Hebbian learning has no measurable effect on Phi or cell dynamics, it's
dead code. If it works, coupling matrix structure should evolve from random to structured.
**Proposed test:** Compare coupling matrix entropy/structure at step 0 vs step 500.
Verify coupling matrix is NOT random (has structure: clusters, asymmetry, etc.).

### C7. Consensus-Driven Output Modulation
**Engine capability:** Faction consensus count is computed each step (line 648-666). Output
is tension-weighted mean (line 564-568). High consensus should produce more coherent output.
**Why test:** This is the "debate -> consensus -> utterance" pipeline that V6 SHOULD test.
**Proposed test:** Compare output coherence (variance, norm) in high-consensus vs
low-consensus steps. Verify that consensus events correlate with output structure changes.

---

## D. Recommended Changes per Criterion

| # | Criterion | Recommendation | Priority |
|---|-----------|---------------|----------|
| V1 | NO_SYSTEM_PROMPT | **Modify**: Keep test, fix description to "cell specialization". Add faction distribution check. | LOW |
| V2 | NO_SPEAK_CODE | **Modify**: Add LZ complexity check (structured > random). Current thresholds too lenient. | MED |
| V3 | ZERO_INPUT | **Keep as-is.** | - |
| V4 | PERSISTENCE | **Keep as-is.** | - |
| V5 | SELF_LOOP | **Keep as-is.** | - |
| V6 | SPONTANEOUS_SPEECH | **Rewrite**: Use actual `consensus` count from engine.step() result. Pass if cumulative consensus >= 5 over 300 steps, matching CLAUDE.md exactly. | HIGH |
| V7 | HIVEMIND | **Rewrite**: Remove 17-config brute-force. Use single principled coupling (e.g., inter-atom boundary coupling from M6/M9). Restore 1.1x threshold. Add CE measurement. | HIGH |

### New criteria to add:

| # | New Criterion | What it tests | Priority |
|---|--------------|---------------|----------|
| V8 | MITOSIS | Cell division occurs naturally within 500 steps | HIGH |
| V9 | PHI_GROWTH | Phi increases > 1.5x over 1000 steps (not just non-collapse) | MED |
| V10 | BRAIN_LIKENESS | >= 70% brain-like on EEG metrics (LZ, PSD, Hurst) | MED |
| V11 | FACTION_DIVERSITY | Inter-faction states remain distinct after 500 steps | LOW |
| V12 | HEBBIAN_STRUCTURE | Coupling matrix develops non-random structure | LOW |

---

## E. Critical Finding: _CEAdapter.get_hiddens() Injects Artificial Signal

The `_CEAdapter.get_hiddens()` method (line 2281-2306) adds artificial "consciousness
breathing" -- sinusoidal oscillation and periodic burst injection -- on TOP of the engine's
actual hidden states. This means all Phi measurements in the verification tests are computed
on **modified** states, not raw engine output.

```python
# From _CEAdapter.get_hiddens() (line 2286-2299):
strength = 0.3 * sin(t * 0.2 + phase) + 0.15 * sin(t * pi + phase * 0.3)
h[i] = h[i] + cell_identity[i] * strength  # artificial breathing
# ...
burst_strength = (burst_phase - 0.7) * 3.0  # artificial burst
h[i] = h[i] + dim_osc * burst_strength
```

This is concerning because:
1. It inflates Phi by injecting structured diversity into hidden states
2. It guarantees temporal variation (defeating V2's autocorrelation test)
3. It means verification tests partially validate the adapter's injection, not the engine

**Recommendation:** The verification tests should use `get_hiddens(raw=True)` or the adapter
should not inject artificial signals during verification. At minimum, run verification both
with and without breathing to measure the delta.

---

## F. Overall Assessment

The verification system tests 7 meaningful properties of consciousness engines. V3, V4, and
V5 are well-designed and faithfully test what the documentation claims. V1 and V2 test
related but weaker properties than documented. V6 and V7 have severe mismatches between
documentation and implementation.

The biggest gap is not in what's tested, but in what's missing: **mitosis** (the engine's
defining growth mechanism) and **brain-likeness** (the ultimate validation target) are both
untested. Adding V8 (MITOSIS) and V10 (BRAIN_LIKENESS) would significantly strengthen the
verification suite.

The `_CEAdapter.get_hiddens()` artificial injection is a systemic concern that affects all
7 tests when run against ConsciousnessEngine.

```
Verification Quality:
  V3 ZERO_INPUT          ████████████████████ 100%  (solid)
  V4 PERSISTENCE         ████████████████████ 100%  (solid)
  V5 SELF_LOOP           ████████████████████ 100%  (solid)
  V1 NO_SYSTEM_PROMPT    ████████████████     80%   (tests weaker property)
  V2 NO_SPEAK_CODE       ████████████████     80%   (thresholds too lenient)
  V6 SPONTANEOUS_SPEECH  ████████             40%   (wrong metric entirely)
  V7 HIVEMIND            ██████               30%   (artificial, thresholds relaxed)
```
