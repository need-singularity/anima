# P25 Φ Correlation Dashboard Reader — B5 Report

**Status**: PARSE-OK RUN-OK (all 3 files, <60s).
**Constraint compliance**: HEXA-FIRST strict (no .py/.rs/.sh); no commit; SSOT `shared/state/phi_corr_history.jsonl` NOT populated (A1 producer owns it).

## Deliverables

| file                                         | lines | parse | self-test |
|----------------------------------------------|-------|-------|-----------|
| `training/phi_corr_history_reader.hexa`      | 408   | OK    | PASS      |
| `training/phi_corr_dashboard.hexa`           | 443   | OK    | PASS      |
| `training/phi_corr_dashboard_daily.hexa`     | 475   | OK    | PASS      |

## Classifier gates

- `STABLE` : |r_pearson| ≥ 0.50 at last run
- `WEAK`   : 0.20 ≤ |r| < 0.50
- `DECAY`  : current weight < 0.70 × historical peak
- `PRUNE`  : |r| < 0.20 for ≥ 3 consecutive runs

## Self-test (5 synthetic runs × 4 dims)

```
+------------------+-------+------+---------+-----------+
| dim              | runs  | |r|  | weight  |  status   |
+------------------+-------+------+---------+-----------+
| phi_holo         |   5   | 0.90 |   0.900 | STABLE    |
| phi_decay        |   5   | 0.20 |   0.200 | DECAY     |
| phi_prune        |   5   | 0.08 |   0.080 | PRUNE     |
| phi_weak         |   5   | 0.29 |   0.290 | WEAK      |
+------------------+-------+------+---------+-----------+
```

All 4 categories correctly flagged; counts STABLE=1/WEAK=1/DECAY=1/PRUNE=1.

## Cron hookup

```
hexa run training/phi_corr_dashboard_daily.hexa
  → writes shared/state/phi_corr_dashboard.md
```

Empty-state verified (runs=0 → placeholder md, no crash).

## Hexa pitfalls bit

- `drop` is a reserved keyword (Drop token) — renamed local var to `drop_ratio`.
- All JSON parsing uses `.index_of` / `.substring` / `.split` per `feedback_hexa_string_api`; no `.find` / `.char_at`.
- Each of the 3 files is self-contained (no cross-file imports) per `feedback_hexa_silent_exit_5_imports`.
