# kr_gen_sentinel — B6 Report

**Status:** READY — 6/6 closed-loop tests PASS. B1 may `exec sentinel $json_path` and branch on exit code.

## Deliverables

- `training/kr_gen_sentinel.hexa` — detector (hexa-native, 260 LOC)
- `training/kr_gen_sentinel_test.hexa` — 6-case closed-loop harness
- Exit codes: `0=CLEAN`, `1=input error`, `2=COLLAPSED` (trainer abort)

## Signatures & Defaults

| Signature     | Rule                                    | Threshold |
| ------------- | --------------------------------------- | --------- |
| json_bracket  | count of `{"":""}`                      | ≥ 3       |
| charloop      | max consecutive byte run                | ≥ 10      |
| spaceloop     | count of `' '`                          | ≥ 5       |
| rolebleed     | any of `roleassistant`, `\\\\n`, `"},{":"` | ≥ 1     |
| qmark         | max consecutive `?`                     | ≥ 5       |

Sample is **flagged** if ≥1 signature fires. **COLLAPSED** when `flagged ≥ 3` out of N.

## Test Results (6/6 PASS)

| Case | Fixture                              | Expected  | Actual    | Flagged |
| ---- | ------------------------------------ | --------- | --------- | ------- |
| A    | r4 real kr_gen (diagnosis file)      | CLEAN/0   | CLEAN/0   | 0/5     |
| B    | r9 real kr_gen (diagnosis file)      | COLLAPSED/2 | COLLAPSED/2 | 4/5   |
| C    | 3 distinct sigs × 3/5 samples        | COLLAPSED/2 | COLLAPSED/2 | 3/5   |
| D    | 5 normal Korean                      | CLEAN/0   | CLEAN/0   | 0/5     |
| E    | 2/5 collapsed (below threshold)      | CLEAN/0   | CLEAN/0   | 2/5     |
| F    | empty array                          | ERROR/1   | ERROR/1   | n/a     |

## Design Notes

- Line-based JSON walker with backslash-aware quote tracking; decodes `\" \\ \n \t \r \/` only — avoids multibyte substring arithmetic per `feedback_hexa_string_api`.
- Byte-level repeat detection works for both ASCII (`nnn…`) and hangul (`로로…`) via UTF-8 continuation-byte regularity.
- Case B discriminates cleanly from Case A (0 vs 4 flagged) — 4-signal margin.
