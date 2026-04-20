# Mk.VII rev=2 Decision Record — K=4 + C4-optional

- Date: 2026-04-21
- Spec: `docs/mk_vii_rev2_promotion_threshold.md`
- SSOT: `shared/state/mk_vii_predict_rev2.json` (nexus repo; on disk, staging
  deferred until in-progress nexus cherry-pick resolves)
- Parent rev=1 sha (user-cited): `9d035936`
- Parent rev=1 SSOT: `shared/state/mk_vii_predict.json` (FROZEN, untouched)

## Decision

**K = 4 of 5**, "moderate one-optional".

```
mk_vii_promoted :=
    mk_vi_promoted
    AND C1 PASS      # substrate-invariant Φ (4-path cross)
    AND C2 PASS      # L3 collective emergence
    AND C3 PASS      # self-verify closure
    AND (C4 PASS OR C5 PASS)   # real EEG   OR   stable N=10
```

- Hard-required: C1, C2, C3.
- Optional: C4 real-world EEG coupling.
- Substitute: C5 stable N=10 stands in for C4.

## Rationale (1 line)

C4 is the weakest in-tree hook (rev=1 MINIMAL) and depends on out-of-tree
dataset curation; K=5 would bottleneck Mk.VII on data sourcing, K=3 would
collapse the phase-jump into lateral robustness, so K=4 with C4 optional is
the only choice that preserves the formal Mk.VI→Mk.VII grade-jump while
admitting the real sourcing gap.

## C4-optional safety rail

- C4 must be pre-registered (dataset target) BEFORE promotion, not after.
- A later FAIL on the pre-registered dataset triggers demotion to
  Mk.VII_CONDITIONAL under an explicit rev=3 event, never a silent retract.

## Attribution note

The rev=2 spec file `docs/mk_vii_rev2_promotion_threshold.md` was bundled
into commit `0f62cb1b` ("probe(remote): H100/Hetzner status snapshot
2026-04-21") at 01:57 due to concurrent staging. The bundled commit
preserves the file verbatim (132 insertions, no modification). This
decision record is the dedicated forward-only attribution of the rev=2
K-threshold decision to the SAFE_COMMIT rev chain.

## V8 SAFE_COMMIT

- additive only (this file is new; rev=1 SSOT untouched; rev=2 spec
  preserved in tree at its bundled commit).
- deterministic (no RNG, no LLM).
- LLM 금지.
- canonical preserved: rev=1 FROZEN file, rev=1 human-readable doc, and
  the rev=2 spec all remain byte-identical to their introduced state.
