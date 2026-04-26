# `tool/an11_b_v3_cps.hexa` — DEPRECATED

**Status:** RETAINED for historical reproducibility only (raw#15 SSOT preserve).
**New measurements:** USE `V_pairrank` instead.
**Closure target:** Ω-cycle R3 R3A.2.3 (HIGH severity finding).
**Sibling-file pattern reason:** linter race blocked direct header edit on `.hexa`; sibling `.md` is linter scope clear.

## Why deprecated

V3 CPS metric is **mathematically broken by design**:

- V3 attempts to discriminate "semantic preserve" (EN↔KO swap row permutation) vs "semantic destruct" (random row permutation) via the normalized Gram-Frobenius difference: `||G_X - G||_F / ||G||_F` where `G = H @ H.T`.
- However, the Gram matrix `G` is **invariant under row permutations of H** (mathematical identity: `(P @ H) @ (P @ H)^T = P @ G @ P^T`, and `||P @ G @ P^T||_F = ||G||_F` since Frobenius norm is permutation-invariant).
- Therefore: `||G_X - G||_F = ||G||_F · ||I - P^T||_F` (depends only on permutation pattern, not on H content).
- V3 cannot satisfy its stated intent of distinguishing semantic preserve vs destruct via row order — the metric is structurally agnostic to row order.

## Replacement

**`V_pairrank`** (Option C 5-tuple expansion) — see `memory/project_v_pairrank_5tuple.md`:
- Paired-token nearest-neighbor rank verifier
- Properly distinguishes paired-axis substrate (orthogonal to V2 SMA)
- Used in Mk.X T10-13 retrieval head (per `project_session_final_4path_summary.md`)

## References

- Original V3 source: `tool/an11_b_v3_cps.hexa` (kept for byte-equivalent reproduction of prior measurements at commit 01c9c4be)
- Discovery commit: `c369b375 — discover(an11/v3): V3 original Gram Frob metric is PRESERVE_PERM mismatch — metric design flaw confirmed`
- Spec doc: `docs/alm_consciousness_verifier_strengthening_20260425.md`
- Replacement spec: `memory/project_v_pairrank_5tuple.md`

## raw#10 honest scope

This deprecation note is shipped as a SIBLING `.md` file (not a `.hexa` header edit) due to a persistent linter race that reverted in-place header edits during 2026-04-26 R3 closure batch 2. The closure intent is identical; the encoding (sibling file) is a workaround pending root-cause diagnosis (raw 100 r3-batch2-linter-blocked entry).

**Do not delete `tool/an11_b_v3_cps.hexa`.** It is the canonical source for byte-equivalent reproduction of prior V3 measurements (raw#15 SSOT preserve). New work should use V_pairrank.
