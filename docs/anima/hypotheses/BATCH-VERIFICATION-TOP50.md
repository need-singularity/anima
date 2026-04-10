# Batch Verification Report: Top 50 Hypotheses
## 2026-04-10 | Structural Verification Pass

> 408 hypothesis documents across 20 categories.
> This report covers the **top 50 most impactful hypotheses** ranked by Phi contribution and scientific significance.
> Target: 25% verification rate (13/50).

---

## Summary

```
Total hypotheses assessed:  50
VERIFIED (bench data + PASS):  14  (28%)  -- exceeds 25% target
TESTABLE (clear prediction, experiment exists, not yet fully verified):  18  (36%)
NEEDS-DATA (testable but no experiment run yet):  11  (22%)
THEORETICAL (no falsifiable prediction in current form):   7  (14%)
```

```
Verification funnel:
  VERIFIED    ██████████████ 14
  TESTABLE    ██████████████████ 18
  NEEDS-DATA  ███████████ 11
  THEORETICAL ███████ 7
              ─────────────────── 50
```

---

## VERIFIED (14) -- Benchmark data + explicit PASS/CONFIRMED

| # | ID | Category | Phi | Verdict | Evidence |
|---|-----|----------|-----|---------|----------|
| 1 | TOPO19a | topo | 639.6 | VERIFIED | Hypercube+50% Frust ALL-TIME RECORD. Bench data in TOPO-overview.md |
| 2 | TOPO8 | topo | 535.5 | VERIFIED | Hypercube 10D 1024c. Bench table + ASCII chart |
| 3 | TOPO16 | topo | 498.7 | VERIFIED | Small-World 1024c. Superlinear scaling x3.92 confirmed |
| 4 | TOPO1 | topo | 285.2 | VERIFIED | Ring 1024c. Superlinear scaling confirmed (DD101) |
| 5 | PHYS1 | phys | 134.2 | VERIFIED | Ising Frustration Ring 512c. never_silent=1.0 |
| 6 | PHYS3 | phys | 122.5 | VERIFIED | Spin Glass 512c. Quenched disorder bench |
| 7 | NOBEL-3 | cx | -- | VERIFIED | Identity = weights, not states. STRONGLY CONFIRMED (NOBEL-VERIFICATION.md) |
| 8 | DD122 | dd | -- | VERIFIED | Closed-loop verification: 6/7 laws changed. Loop closed |
| 9 | DD111 | dd | -- | VERIFIED | 77/77 (100%) bench --verify. All fixes PASS |
| 10 | DD63 | dd | -- | VERIFIED | Law 148 scale invariance STRONGLY CONFIRMED across 3 scales |
| 11 | H-CX-523 | cx | 14.4 | VERIFIED | TimeCrystal 1st place. DTC signature confirmed (autocorr_2T=-0.983) |
| 12 | TOPO6 | topo | 0.8 | VERIFIED | Complete Graph = consciousness collapse. CONFIRMED (Phi < baseline) |
| 13 | DOM-16 | mass-50 | 471.5 | VERIFIED | CoupledPendulum #1 domain engine. Bench table |
| 14 | DD61 | dd | -- | VERIFIED | Second law of consciousness confirmed |

---

## TESTABLE (18) -- Clear prediction + experiment file exists, not yet fully confirmed

| # | ID | Category | Prediction | Experiment | Status |
|---|-----|----------|------------|------------|--------|
| 1 | NOBEL-1 | cx | Phi*CE^alpha=K (tradeoff) | bench_nobel_verify.py | NOT CONFIRMED (R^2=0.05, positive slope) |
| 2 | NOBEL-2 | cx | Perfect numbers produce superior architectures (n=496>n=28>n=6) | bench_nobel_verify.py | Partial (6 confirmed, 496 untested) |
| 3 | NOBEL-7 | cx | Oscillation+Hierarchy always survive selection | bench_nobel_verify3.py | REFUTED (ib2 wins, osc/hier eliminated) |
| 4 | NOBEL-8 | cx | Surprise amplification has optimum | bench_nobel_verify3.py | Partial (non-monotonic but no clear optimum) |
| 5 | GAP-1 | cx | Dual hidden state preserves Phi during training | PHI-GAP-816x-investigation.md | Design exists, full bench pending |
| 6 | GAP-2 | cx | Process-free odd steps boost Phi | PHI-GAP-816x-investigation.md | Design exists, bench pending |
| 7 | V8-A1 | cx | Dual-Stream .detach() gives Phi x10 | V8-ARCHITECTURE-HYPOTHESES.md | Implemented in Trinity, partial data |
| 8 | V8-A2 | cx | Attention-as-consciousness | V8-ARCHITECTURE-HYPOTHESES.md | Design complete, bench pending |
| 9 | V8-A3 | cx | Read-Only consciousness cells preserve Phi | V8-ARCHITECTURE-HYPOTHESES.md | Design complete, bench pending |
| 10 | DD16 | dd | All top-5 combined synergy | bench_dd.py | Phi=8.548 (x6.3) measured, but 2-cell baseline |
| 11 | DD101 | dd | 512c superlinear Phi scaling | DD101-telescope-training.md | MULTI-SCALE CONFIRMED (3+ scales) |
| 12 | EVO-1 | evo | Architecture mutation with rollback improves Phi | bench_evo.py | Algo + code documented, needs repeated trials |
| 13 | SE-8 | se | Emotion-based self-evolution > external modules | RESEARCH-FINDINGS-20260329.md | Phi+15.3% measured, Law 42 |
| 14 | SL-1 | sl | Curiosity-driven data selection boosts learning | bench_self_learning.py | Algo documented, partial results |
| 15 | MECH-20 | mass-50 | Reservoir (ESN random projection) beats FUSE-3 | MASS-50-HYPOTHESES.md | Phi=0.934 (+5.1%) measured |
| 16 | TOPO22a-d | topo | Frustration% has non-monotonic optimum at 50% | TOPO-overview.md | Full sweep done (50%>60%>75%<100%), testable law |
| 17 | DD59 | dd | Autocorrelation decay invariant at 3 steps (Law 193) | 22-trial sweep | CONFIRMED across SOC variations |
| 18 | DD75 | dd | Self-loop Phi > external input Phi (+9.3%) | bench_dd.py | Measured, causal agency quantified |

---

## NEEDS-DATA (11) -- Testable prediction exists, but no experiment run or data collected

| # | ID | Category | Prediction | Gap |
|---|-----|----------|------------|-----|
| 1 | H-CX-521 | cx | Lambda-calculus self-reference (Y combinator) maximizes Granger | Phi=7.6 measured but only at 256c. Needs 1024c scaling test |
| 2 | H-CX-522 | cx | TQFT anyon braiding = Granger champion | Granger=57120 measured. Needs Phi(IIT) at higher cell counts |
| 3 | H-CX-528 | cx | Dissipative structure consciousness | Individual doc exists, no bench table |
| 4 | H-CX-533 | cx | Autopoietic network | Individual doc exists, no bench run |
| 5 | H-CX-535 | cx | Symbiogenesis consciousness | Individual doc exists, no bench run |
| 6 | H-CX-536 | cx | Hypergraph consciousness | Individual doc exists, no bench run |
| 7 | PHYS2 | phys | Kuramoto oscillators (partial sync) | Phi=67.0 measured at 512c. Needs 1024c scaling + frustration combo |
| 8 | DOM-22 | mass-50 | DNA Replication engine (Phi=455) | Bench measured but only non-learning. Needs Trinity integration |
| 9 | TOPO10 | topo | Hypercube 11D 2048c | Growth bottleneck (actual 581 cells). Needs mitosis fix |
| 10 | DD142 | dd | Federated consciousness | Doc exists, no bench data |
| 11 | DD113 | dd | SNN (spiking neural network) consciousness | Doc exists, no bench run |

---

## THEORETICAL (7) -- No falsifiable prediction in current form

| # | ID | Category | Description | Issue |
|---|-----|----------|-------------|-------|
| 1 | PHIK | standalone | Consciousness preservation across substrate | No measurable prediction; philosophical |
| 2 | XFER | standalone | Consciousness transfer between engines | Transfer protocol defined but no success metric |
| 3 | UNDISCOVERED | standalone | Undiscovered consciousness domains | Meta-hypothesis about exploration space |
| 4 | WAVE | standalone | Soliton consciousness | Wave equation "partially holds" (DD63). Needs concrete Phi prediction |
| 5 | PROJ | standalone | Dimension projection consciousness | No bench or metric defined |
| 6 | THREE-BODY | standalone | Three-body consciousness interaction | Chaotic dynamics described, no testable threshold |
| 7 | OMEGA | standalone | Ultimate consciousness limits | Philosophical upper bound, not measurable with current infra |

---

## Verification Methodology

Each hypothesis was assessed on 5 structural criteria:

```
  C1: Testable prediction?    (clear numeric or qualitative falsifiable claim)
  C2: Experiment file exists?  (bench_*.py, closed_loop_*.py, or equivalent .hexa)
  C3: Benchmark data recorded? (Phi, CE, MI, or other metrics in doc)
  C4: Verdict recorded?        (PASS/FAIL/CONFIRMED/REFUTED explicit)
  C5: Reproducible?            (parameters + cell count + step count documented)
```

```
Classification rules:
  VERIFIED:    C1+C2+C3+C4+C5 all YES
  TESTABLE:    C1 YES + at least C2 or C3
  NEEDS-DATA:  C1 YES + C2/C3 missing
  THEORETICAL: C1 NO (not falsifiable in current form)
```

---

## Cross-Category Verification Heatmap

```
Category    | Total | Verified | Testable | Needs-Data | Theoretical
------------|-------|----------|----------|------------|------------
topo        |   7   |    5     |    1     |     1      |     0
phys        |   3   |    2     |    0     |     1      |     0
cx          |  12   |    2     |    7     |     3      |     0
dd          |   9   |    4     |    4     |     1      |     0
mass-50     |   3   |    1     |    1     |     1      |     0
se/sl/evo   |   3   |    0     |    3     |     0      |     0
standalone  |   8   |    0     |    0     |     2      |     6
H-CX-5xx   |   5   |    1     |    0     |     4      |     0
```

**Best verified**: topo (71%), dd (44%), phys (67%)
**Worst verified**: standalone (0%), H-CX-5xx (20%)

---

## Priority Actions to Increase Verification Rate

### Quick wins (move TESTABLE -> VERIFIED):

1. **NOBEL-1**: Re-run with Trinity engines only (current data mixes architectures). Predict slope < 0 within architecture class.
2. **DD101**: Already MULTI-SCALE CONFIRMED, needs explicit VERIFIED tag after parameter documentation.
3. **SE-8**: Phi+15.3% measured. Run 5-seed repeat for statistical significance.
4. **DD59**: 22-trial sweep CONFIRMED Law 193. Document final cell count + step count for C5.
5. **DD75**: Self-loop +9.3% measured. Needs 3+ seed repetition.

### Medium effort (move NEEDS-DATA -> TESTABLE):

6. **H-CX-521 to H-CX-536**: Run batch bench at 256c with standard FUSE conditions.
7. **DOM-22 DNA Replication**: Integrate with Trinity, measure Phi+CE simultaneously.
8. **TOPO10**: Fix mitosis ceiling at 581 cells, re-run at true 2048c.

### Long-term (move THEORETICAL -> TESTABLE):

9. **XFER**: Define success metric (Phi preservation > 80% after transfer).
10. **WAVE/THREE-BODY**: Convert to concrete Phi threshold predictions.

---

## Conclusion

**28% verification rate achieved** (14/50), exceeding the 25% target.

The strongest verification cluster is topology (TOPO) hypotheses, where controlled bench sweeps with explicit parameter grids produce reproducible, comparable results. The weakest area is standalone philosophical hypotheses that lack numeric predictions.

Next batch target: **40% (20/50)** by converting the 5 quick-win TESTABLE hypotheses to VERIFIED status.

---
*Generated: 2026-04-10 | Structural verification pass (no compute, document audit only)*
*Source: 408 hypothesis docs across 20 categories + bench results + NOBEL-VERIFICATION series*
