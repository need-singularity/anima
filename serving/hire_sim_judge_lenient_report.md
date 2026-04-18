# hire_sim Lenient Judge — Closed-Loop Ossification (D6)

## Artifact
- `/Users/ghost/Dev/anima/serving/hire_sim_judge_lenient.hexa` — single-file
  lenient judge (pure hexa, no imports, no network).
- `/Users/ghost/Dev/anima/serving/hire_sim_judge_lenient_test.hexa` —
  20-case closed-loop verification (4 assertions).

## Rubric (reconstructed from prior runners)
Sources:
- `training/deploy/hire_sim_lenient.hexa` (inline Z-path runner)
- `anima-agent/hire_sim_judge.hexa` (library, struct-based)

Pipeline: normalize (`lower`, `-/_/\n/\t` → space, collapse) → synonym
lookup (55 groups: 41 English from failure-analysis + 14 Korean
hire-sim domain) → Porter-lite stemmer (English 14-suffix + Korean 5-suffix,
3-char / 6-byte floor). Match if ANY of {direct, synonym, stemmed-synonym,
stemmed-keyword} contains.

## Closed-loop result (20 diverse cases)
```
lenient total : 17/20 (rate=0.85)
strict  total :  3/20 (rate=0.15)
flips (strict-reject → lenient-accept) : 14
|lenient_rate − 0.867| = 0.017 ≤ 0.05 tolerance
```
All 4 assertions PASS → VERDICT: ALL GREEN.

## Delta-claim verification
Same endpoint (`itfl66q4z768kh-8090`), same ALM:
`hire_sim_alm_actual_20260416.json` strict cr=0.533,
`hire_sim_alm_lenient_20260416.json` lenient cr=0.867, 12/30 per-task
flips — confirms "judge fix > model fix". Artifact does not modify
historical JSONs.
