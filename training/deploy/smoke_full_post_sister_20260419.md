# anima 전체 .hexa smoke — post-sister re-run

**Date**: 2026-04-19 02:41 KST
**Trigger**: sister repo 20+ commits landed → hexa_v2 Mac/Linux 재빌드 → 1638 파일 full smoke 재측정
**Prior baseline**: 2026-04-18 17:15Z — 1287/1638 PASS (78.57%)

---

## Binary status

| Binary | Path | Size | Timestamp |
|---|---|---|---|
| Mac hexa_v2 | `/Users/ghost/Dev/hexa-lang/self/native/hexa_v2` | 1.22 MB | 2026-04-19 02:15 |
| Linux hexa_v2 | `/Users/ghost/Dev/hexa-lang/build/hexa_v2_linux` | 1.51 MB | 2026-04-19 00:27 |
| Runner (ubu2) | `summer@192.168.50.60:/tmp/hexa_v2_linux` | 1.51 MB | 2026-04-19 02:25 |

`shasum hexa_v2` (Mac) = `c50a35a4be47ff63d8137ac49e0c8ec12514f89b0b5f222057bc8e5c8ebe26dc`

Both Mac+Linux 재빌드 완료 확인 (newer than prior baseline). No stale-binary caveat.

---

## Headline numbers

| Metric | Baseline (04-18) | Now (04-19) | Delta |
|---|---|---|---|
| Scanned | 1638 | **1633** | −5 (3 new, 8 deleted since) |
| PASS | 1287 (78.57%) | **1160 (71.03%)** | **−127 / −7.54 pp** |
| FAIL_T (transpiler) | 4 | **271** | **+267** |
| FAIL_C (clang) | 347 | **201** | −146 |

### Transitions on 1630 common files
- PASS → PASS kept: **1160**
- PASS → FAIL: **122 (regressions)**
- FAIL → PASS improved: **0**
- FAIL → FAIL stayed: **348**

**Net**: sister landing regressed 122 files, improved 0. FAIL_T exploded +267 from new statement kinds.

---

## Regression root causes (top FAIL_T)

| Count | Error |
|---|---|
| 48 | Parse error: unexpected `LBrace '{'` |
| 42 | `[codegen_c] ERROR: unhandled statement kind: PanicStmt` |
| 29 | Parse error: unexpected `Colon ':'` |
| 26 | Parse error: expected identifier, got `BitAnd '&'` |
| 16 | `[codegen_c] ERROR: unhandled statement kind: ModStmt` |
| 14 | Parse error: expected identifier, got `LBrace '{'` |
| 11 | `[codegen_c] ERROR: unhandled statement kind: TheoremStmt` |
| 4 | Parse error: expected identifier, got `Intent 'intent'` |
| – | Parse error: expected identifier, got `Channel 'channel'` |

**Diagnosis**: new sister-landing features added reserved keywords (`channel`, `intent`) + new AST nodes (`PanicStmt`, `ModStmt`, `TheoremStmt`) but `codegen_c2` was not updated to emit them. Pure handoff-to-hexa-lang item.

---

## Largest delta files (PASS → FAIL regressions)

1. `./anima-agent/agent_tools.hexa` → FAIL_T (LBrace)
2. `./anima-agent/anima_agent.hexa` → FAIL_T (`channel` now reserved)
3. `./anima-agent/autonomy_loop.hexa` → FAIL_T (PanicStmt)
4. `./anima-agent/hexa/agent.hexa` → FAIL_T (ModStmt)
5. `./anima-agent/hexa/alien_index.hexa` → FAIL_T (ModStmt)
6. `./anima-agent/hexa/anima_agent_full.hexa` → FAIL_T (ModStmt)
7. `./anima-agent/hexa/channel.hexa` → FAIL_T (ModStmt)
8. `./anima-agent/hexa/consciousness.hexa` → FAIL_T (ModStmt)
9. `./anima-agent/hexa/egyptian_memory.hexa` → FAIL_T (ModStmt)
10. `./anima-agent/hexa/faction.hexa` → FAIL_T (ModStmt)

Pattern: `anima-agent/hexa/` subdir heavily uses `mod { ... }` blocks, all regressed.

Unique PASS→FAIL_C: `./training/nn_core.hexa` — `deref_i64` missing from runtime.

---

## Residual FAIL_C blockers (Top 5)

| Count | Blocker |
|---|---|
| 16 | `implicit-int` — codegen emits untyped decls (stricter clang now) |
| 12 | undeclared `json_parse` — missing runtime helper |
| 9 | undeclared `var` — codegen leaks Hexa keyword to C |
| 8 | undeclared `u_floor` — u_ prefix math stubs missing |
| 8 | undeclared `shell` — missing shell() intrinsic |

Also: `xavier_init` (5), `cudaDeviceSynchronize` (5, expected on AMD ubu2), `split` (5).

---

## Sister escalation — post-landing residual blockers

Add to sister handoff under "post-sister landing 잔여 blocker":
1. **codegen_c2 unhandled statement kinds**: `PanicStmt` (42), `ModStmt` (16), `TheoremStmt` (11) — need codegen visitor methods
2. **New reserved keywords clash with user identifiers**: `channel`, `intent` — either rename in anima or add contextual lexing
3. **Parser regressions**: `LBrace` (62), `Colon` (29), `BitAnd` (26), `Dot` (6) — likely new expression grammar missed edge cases
4. **Runtime gaps**: `json_parse`, `u_floor`, `u_y1`, `u_env`, `shell`, `xavier_init`, `split`, `deref_i64`, `get_args`
5. **implicit-int warnings** upgraded to errors by newer clang — codegen type elision

---

## Files

- TSV (now): `/Users/ghost/Dev/anima/training/deploy/smoke_full_ubu2_resmoke_20260419T024146Z.tsv` (buggy 1st run, no -I)
- TSV (valid): `/Users/ghost/Dev/anima/training/deploy/smoke_full_ubu2_resmoke_20260419T030019Z.tsv` (with `-I /tmp`)
- TSV (baseline): `/Users/ghost/Dev/anima/training/deploy/smoke_full_ubu2_20260418T171520Z.tsv`
- ubu2 workdirs: `/tmp/anima_resmoke/`, `/tmp/resmoke_c/`, `/tmp/hexa_v2_linux`

## Timing

- rsync: 3s
- smoke (1st run, no -I): 681s
- smoke (2nd run, -I /tmp): ~670s
- Total wall: ~24 min
