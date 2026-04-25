# Anima Evolution L0 — Archive Gate Fix 2026-04-25

> **목적**: docs/anima_evolution_archive_attempt_20260425.md §3 에서 진단된 `_verify_module_selftest()` leaky gate (commit ef8c8713) hardening. `raw#12 honesty` 적용 — leaky gate 로 발생한 075 archive 를 revert.
>
> **결과**: gate 3 단 hardening (extension + leak guard + marker), 7/7 selftest PASS, 075 → approved/ 복귀 (archived/ 0 카드).

---

## §1. Leak 재정의

`tool/proposal_archive.hexa` 의 prior `_verify_module_selftest()` (line 321-337):

```sh
hexa <module_abs> --selftest >/tmp/...out 2>&1
echo $?
```

문제: hexa CLI 는 `<module_abs>` 를 subcommand 로 해석. `.hexa` 가 아닌 file (md/json/py) 에 대해 `error: unknown subcommand '<path>'` 출력 후 **exit 0** 반환. 결과적으로 file 만 존재하면 PASS 판정.

**검증 reproduce** (fix 전):
```bash
$ /Users/ghost/core/hexa-lang/hexa docs/alm_an11_a_weight_emergent_r6_evidence_20260425.md --selftest ; echo EXIT=$?
error: unknown subcommand '...'
HEXA — self-hosted language toolchain ...
EXIT=0
```

---

## §2. Fix — 3 단 enforcement

`_verify_module_selftest(module_abs)` 패치 (tool/proposal_archive.hexa):

| layer | check | rationale |
|---|---|---|
| 1 | `_ends_with(module_abs, ".hexa")` | hexa-runtime 외 file (md/json/py 등) 거부. 가장 직접적인 차단. |
| 2 | wrapper output 에 `"unknown subcommand"` 포함 시 강제 FAIL | hexa CLI default-success leak 방어. layer 1 우회 시도 (e.g., 빈 .hexa 파일이 향후 hexa CLI 변경으로 unknown 처리될 경우) 이중 안전장치. |
| 3 | output 에 `SELFTEST_PASS` 또는 `DONE` marker 포함 필수 | trivially `exit(0)` 하는 무의미한 module 차단. 실제 selftest 실행 증거 요구. |

코드 (line 334-381):

```hexa
fn _verify_module_selftest(module_abs: string) -> array {
    if !_fexists(module_abs) {
        return [false, "module file not found: " + module_abs]
    }
    if !_ends_with(module_abs, ".hexa") {
        return [false, "module file extension must be .hexa (got: " + module_abs + ")"]
    }
    // ... wrap + exec ...
    if _has_substring(out, "unknown subcommand") {
        return [false, "module selftest leak: ..."]
    }
    if rc_str != "0" { return [false, "module selftest exit=" + rc_str + " ..."] }
    if !_has_substring(out, "SELFTEST_PASS") && !_has_substring(out, "DONE") {
        return [false, "module selftest exit=0 but missing SELFTEST_PASS/DONE marker; ..."]
    }
    return [true, "module selftest PASS (marker present)"]
}
```

Helper 추가: `_has_substring(hay, needle) -> bool`, `_ends_with(hay, suffix) -> bool` (hexa stdlib 의 `contains`/`endsWith` 부재 회피).

---

## §3. Selftest fixture 확장 — 4 → 7 단

`_selftest()` 에 negative fixture 3 종 추가:

| step | fixture | expected exit | gate layer tested |
|---|---|---|---|
| S0 | `--module-path` 누락 | 3 | argv validation |
| S1 | nonexistent module | 1 | `_fexists` |
| **S1b (new)** | `.md` extant file (075 leak case) | 1 | layer 1 (.hexa enforcement) |
| **S1c (new)** | `.hexa` with selftest exit 1 | 1 | rc check |
| **S1d (new)** | `.hexa` exit 0 but no marker | 1 | layer 3 (marker enforcement) |
| S2 | `.hexa` selftest exit 0 + `SELFTEST_PASS` | 0 | full gate PASS |
| S3 | S2 idempotent re-run | 0 | already-archived noop |

실행 결과:

```
$ hexa tool/proposal_archive.hexa --selftest
── proposal_archive selftest ──
S0 missing-arg + S1 missing-module + S1b leak-guard(.md) + S1c fail-selftest + S1d no-marker + S2 archive + S3 idempotent → 7/7 PASS
── selftest result: 7/7 PASS ──
EXIT=0
```

---

## §4. 075 archive revert (raw#12 honesty)

**행동**:
1. `git show 4d2884af:state/proposals/approved/20260422-075_*.json` → approved/ 복원.
2. `state/proposals/archived/20260422-075_*.json` 삭제.

**확인** — 새 gate 로 075 재시도:
```
$ hexa tool/proposal_archive.hexa --id 20260422-075 \
       --module-path docs/alm_an11_a_weight_emergent_r6_evidence_20260425.md
proposal_archive: module verification FAILED — module file extension must be .hexa (got: /Users/ghost/core/anima/docs/alm_an11_a_weight_emergent_r6_evidence_20260425.md)
EXIT=1
```

075 는 진정한 hexa-runtime selftest harness 가 없으므로 이번 archive 는 **불가능**. 적절한 진단.

**State**:
- `state/proposals/approved/`: 15 cards (075 복귀)
- `state/proposals/archived/`: 0 cards

---

## §5. 11 traditional cards — 동일하게 차단 유지

`tool/proposal_<id>.hexa` 가 disk 에 부재한 11 cards (001/002/016/017/038/039/040/044/047/052/056) 는 layer 1 (`_fexists`) 에서 이미 FAIL 했었음. 새 gate 에서도 동일하게 FAIL. 변화 없음.

`074` (no module path) → argv layer 에서 reject, 변화 없음.

`076`, `083` → module-path 가 `.json` 이라 새 gate 의 layer 1 에서 reject (이전엔 unknown subcommand leak 으로 우연히 PASS 가능했음).

**결론**: 새 gate 하에서 archive 가능한 approved 카드는 **현재 0**. 진정한 archive 를 위해 user 가 `.hexa` runtime module + `--selftest` harness 작성 필요.

---

## §6. Brutally honest verdict

- **이전 archived = 1 (075)**: gate leak 으로 발생한 false positive. 이번 fix 로 revert.
- **현재 archived = 0**: 정직한 baseline. 진정한 weakest evidence link 노출.
- **Gate 정합성**: 7/7 selftest, layer 1+2+3 검증.
- **남은 작업**: archived ≥ 1 충족 위한 user-driven module synthesis. 0-cost loop 권한 외 (POLICY R4).

---

## §7. 참조

- 패치: `tool/proposal_archive.hexa` (`_verify_module_selftest`, `_selftest`)
- Leak 진단 doc: `docs/anima_evolution_archive_attempt_20260425.md` §3
- Revert 대상 commit: `ef8c8713` (075 archive)
- Pre-archive 075 source: commit `4d2884af`
