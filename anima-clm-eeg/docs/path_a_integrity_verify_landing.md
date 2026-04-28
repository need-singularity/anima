# Path A (Q1 EEG-CLM falsifier) Integrity Verify — Landing

- **세션**: 2026-04-26 ω-cycle (post-freeze 6-step)
- **임무**: Path A frozen pre-register v1 (10-file SHA-256 lock) 의 integrity 검증
- **scope**: 5 hexa source + 1 fixture + 4 emitted JSON state + 1 frozen v1 manifest
- **cap**: 30분 mac local, $0, raw#9 strict, hexa-only, LLM=none

## 1. Frozen v1 Manifest (read-only SSOT)

`anima-clm-eeg/state/clm_eeg_pre_register_v1.json` (sha256 `ab4c43f9b62922f225be7fb81be5d08bab7f9d233ba0b7a89cbca04cf5fe5462`, frozen 2026-04-26 19:30:29)

`byte_identical_lock.lock_method` = "sha256 of helper sources + emitted JSON state files at frozen_at"
`byte_identical_lock.rerun_guarantee` = "Re-running any tool with same fixture seed produces byte-identical output (FNV-hash deterministic, no LLM, no clock)."

## 2. ω-cycle 6-step 진행

### Step 1 — Design

10-file sha256 cross-check criterion frozen:
- 5 hexa source (`tool/clm_eeg_*.hexa`)
- 1 fixture (`fixtures/synthetic_16ch_v1.json`)
- 4 emitted state JSON (`state/clm_eeg_p1_lz_pre_register.json`, `p2_tlr_pre_register.json`, `p3_gcg_pre_register.json`, `harness_smoke.json`)

Pass criterion: 10/10 sha256 match. Fail criterion: any drift → 사유 분류 (source vs emitted vs filesystem).

### Step 2 — Implement (re-run attempt)

`HEXA_RESOLVER_NO_REROUTE=1 hexa run …` 5회 호출 시도.

**Blocker**: 현재 mac hexa toolchain (`/Users/ghost/core/hexa-lang/hexa` 0.1.0-dispatch, mtime 2026-04-26 23:33) 에서 `run` 서브커맨드가 모든 입력에 대해 `error: unknown subcommand '<file>'` 출력. 백업 (`hexa.bak_pre_auto_marker_20260426`, `hexa.bak_pre_argv_quote_fix_20260426`) 도 동일 실패. 더 오래된 백업 (`hexa.bak_pre_argv0`, `hexa.pre-cc-backup-1776738474`) 는 `stage0 interpreter not found` 별개 실패.

minimal hello-world (`fn main() { println("hello") } main()`) 도 동일 증상 → hexa toolchain 자체 문제, 본 path A hexa 코드와 무관.

→ **선택**: re-run 불가 시점에서 frozen v1 의 파일 sha256 cross-check 만으로 integrity 검증. 이는 frozen v1 의 `byte_identical_lock.lock_method` 정의 ("sha256 of helper sources + emitted JSON state files at frozen_at") 와 정확히 호환.

### Step 3 — Positive selftest (10-file SHA-256 cross-check)

| # | file | frozen v1 sha256 (head 16) | current sha256 (head 16) | match |
|---|---|---|---|---|
| 1 | `tool/clm_eeg_synthetic_fixture.hexa` | `0dfe2c2e946e1fa6` | `0dfe2c2e946e1fa6` | ✓ |
| 2 | `tool/clm_eeg_p1_lz_pre_register.hexa` | `cd17abd8aa45d491` | `cce9a801ef821524` | ✗ |
| 3 | `tool/clm_eeg_p2_tlr_pre_register.hexa` | `fbff2e85a5e2a892` | `fbff2e85a5e2a892` | ✓ |
| 4 | `tool/clm_eeg_p3_gcg_pre_register.hexa` | `0eec458cf7cc300b` | `0eec458cf7cc300b` | ✓ |
| 5 | `tool/clm_eeg_harness_smoke.hexa` | `18196513ba2c544e` | `18196513ba2c544e` | ✓ |
| 6 | `fixtures/synthetic_16ch_v1.json` | `831a1b5d49234d30` | `831a1b5d49234d30` | ✓ |
| 7 | `state/clm_eeg_p1_lz_pre_register.json` | `5099794e78838196` | `cb5e9aacf380b65d` | ✗ |
| 8 | `state/clm_eeg_p2_tlr_pre_register.json` | `e857c0d8983a781f` | `e857c0d8983a781f` | ✓ |
| 9 | `state/clm_eeg_p3_gcg_pre_register.json` | `953ce72f72da2d8c` | `953ce72f72da2d8c` | ✓ |
| 10 | `state/clm_eeg_harness_smoke.json` | `9160feef81a8c2c6` | `fd51e4d3f06dae37` | ✗ |

**Match: 7/10 ✓ / Mismatch: 3/10 ✗**

#### Mismatch 사유 분석 (raw#10 honest)

mtime evidence (frozen 19:30:29):
- P1 LZ hexa modified at **19:46:24** (frozen 후 +16분)
- P1 LZ JSON regenerated at **19:46:31** (P1 hexa 직후)
- harness_smoke JSON regenerated at **21:22:12** (frozen 후 +1h52m)
- 다른 파일들 mtime은 모두 frozen 시점 이전 또는 직후 직전 단계.

**원인 추정**: frozen v1 lock JSON 작성 (19:30:29) 직후, 동일 세션 내에서 P1 LZ hexa 가 silently 수정 (19:46:24) → P1 emitted JSON regenerate (19:46:31). harness_smoke JSON regenerate (21:22:12) 는 이후 어느 시점의 chain 재실행. frozen v1 JSON 자체는 **현재 sha** 가 frozen v1 의 lock 항목에 포함되지 않으므로 자기자신 sha 비교 불가 — 외부 변경 없음을 byte-identical re-read 로 확인 (재측정 sha `ab4c43f9b62922f2` 일관).

#### Verdict 동치성 (semantic match)

frozen v1 `dry_run_verdicts_at_freeze`:
- p1_lz_dry_run = "PASS"
- p2_tlr_dry_run = "PASS"
- p3_gcg_dry_run = "PASS"
- composite_harness = "HARNESS_OK (3/3)"

**현재 emitted JSON 의 verdict (silently regenerated 포함):**
- `state/clm_eeg_p1_lz_pre_register.json` C1_pass=1 / C2_pass=1 / **p1_dry_run_pass=1** ✓ (criteria C1=650/C2=200/baseline=850 frozen 값 그대로)
- `state/clm_eeg_p2_tlr_pre_register.json` (sha match) → frozen verdict PASS 그대로 ✓
- `state/clm_eeg_p3_gcg_pre_register.json` (sha match) → frozen verdict PASS 그대로 ✓
- `state/clm_eeg_harness_smoke.json` p1_pass=1 / p2_pass=1 / p3_pass=1 / **harness_ok=1, pass_count=3/required=2** ✓

→ **frozen verdict와 현재 verdict 의미적으로 일치**. 3/10 byte-mismatch는 **drift in implementation/output bytes**, **NOT** in pre-registered criteria threshold (650/200/850 / 450/380 / 400/200 / ≥2/3) 에 영향 없음. raw#9 silent-edit 위반 측면에서는 P1 hexa의 19:46 수정이 frozen v1 JSON의 `post_hoc_change_policy` ("Any threshold modification requires v2 bump.  Silent edits are forbidden") 에 형식적으로 저촉되지만, threshold modification은 아니므로 v2 bump 미필요. **Forensic 결론**: 본 cycle은 기존 silent edit을 *발견* 한 것으로, 본 cycle 자체는 read-only.

### Step 4 — Negative falsify

**Adversarial check 1 (toolchain unavailable)**: hexa run blocker 자체가 negative falsify 의 한 형태 — 다른 환경 (broken hexa) 에서 sha 재현 불가능 ⇒ rerun_guarantee 의 'same fixture seed produces byte-identical' 주장은 *작동하는 hexa 환경* 전제 (raw#10 honest).

**Adversarial check 2 (env perturbation)**: `CLM_EEG_FIXTURE_SEED` 변경 시 fingerprint/sha 변동을 검증하려면 hexa run 필요 → blocked. 단 frozen v1 manifest 의 line 64 sha (`fixtures/synthetic_16ch_v1.json` = `831a1b5d…`) 와 현재 sha 일치는 default seed (20260426) 시 byte-identical 임을 *historical evidence* 로 확인.

**Adversarial check 3 (mtime≠sha drift)**: `fixtures/synthetic_16ch_v1.json` mtime=21:23:32 (frozen 후 +1h53m) 임에도 sha=`831a1b5d49234d30` frozen 값과 일치 → fixture가 21:23에 byte-identically regenerate되었음 (FNV-deterministic 강력 지지). 동일 input → 동일 output 의 직접 evidence.

### Step 5 — Byte-identical (재측정)

shasum 2회 호출 결과 동일 (filesystem stable, no race) — 11 file 모두 byte-identical between 1st and 2nd shasum invocation:

```
0dfe2c2e946e1fa68b1fb731b1242e9db535ea7e306f61fa30898ad3954a76e3  anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa
cce9a801ef8215247aa501cb44a46a8838bed0dd5117448ee41a23fa62bd38cf  anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa
fbff2e85a5e2a8923fbfce2a061715d4f7f3e328f1106709279c295ab77fc52a  anima-clm-eeg/tool/clm_eeg_p2_tlr_pre_register.hexa
0eec458cf7cc300bdc4c477327a1528c2204cd18ba7301823f9f30bc48f15d08  anima-clm-eeg/tool/clm_eeg_p3_gcg_pre_register.hexa
18196513ba2c544ec625a5e302027ef57ba81104e00c4929063915d31f2f42d9  anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa
831a1b5d49234d30b83070f116f10204eba1ad06fa6ab5c3beafc6b6f234a271  anima-clm-eeg/fixtures/synthetic_16ch_v1.json
cb5e9aacf380b65d16a5d7ebbbf2165d17bc145395b59f3c56afe8a697e4ef03  state/clm_eeg_p1_lz_pre_register.json
e857c0d8983a781fd8a23a2f31260281397be3391286cb28b5e62719c2567fa9  state/clm_eeg_p2_tlr_pre_register.json
953ce72f72da2d8cbed1952fe5b701eb16357dc307363efc33fa6f7c3c4f30ee  state/clm_eeg_p3_gcg_pre_register.json
fd51e4d3f06dae375bea985837dea8695158107bfa893f6b51fab678e2159fd8  state/clm_eeg_harness_smoke.json
ab4c43f9b62922f225be7fb81be5d08bab7f9d233ba0b7a89cbca04cf5fe5462  anima-clm-eeg/state/clm_eeg_pre_register_v1.json
```

### Step 6 — Iterate

- iter 0: hexa toolchain blocker 발견 → re-run path 폐기, sha-only path 채택 (one-shot, no iter loop).
- iter 1: P1 hexa silent-edit 검출 (sha mismatch + mtime 19:46 evidence). criteria threshold 미변경 확인 → v2 bump 미필요 결정.

## 3. Verdict

**INTEGRITY: PARTIAL_PASS**
- ✓ 7/10 frozen sha 그대로 보존
- ✗ 3/10 drift (P1 LZ hexa + P1 LZ JSON + harness_smoke JSON), **silent edit 발생 (19:46–21:22)**
- ✓ frozen criteria threshold 11개 (P1: 650/200/850, P2: 450/380, P3: 400/200, composite ≥2/3) 모두 P1 hexa 코드 line 43–45 에 그대로 보존
- ✓ frozen verdict (P1/P2/P3 PASS + HARNESS_OK 3/3) 현재 emitted JSON 4개에서도 의미적으로 동일

## 4. Post-EEG Entry Eligibility (D+0~D+7)

**eligible with caveat**: P1 hexa silent edit 으로 byte-identical lock 의 strict 의미 위반 (3/10 mismatch). 그러나:
1. threshold 미변경 (raw#9 criteria SSOT preserved)
2. P2/P3 hexa + fixture sha 보존 (4/5 source 무결)
3. semantic verdict 보존 (4/4 PASS)

→ **D+1 P1 verify 시 frozen criteria 그대로 사용 가능** (650/200/850), 단 P1 hexa current sha (`cce9a801…`) 를 **v1.1 manifest** 로 별도 기록 권장 (또는 v2 bump 으로 격상).

## 5. Recommendations

1. (선택) frozen v1 → v1.1 patch JSON 발행: P1 hexa sha 갱신 + harness/p1 emitted JSON sha 갱신. 또는 v2 bump (post-hoc policy strict 적용).
2. P1 hexa 19:46 silent edit 의 git diff 추적 불가 (git untracked) — silent-land 방지 위해 5 hexa + frozen v1 JSON 모두 `chflags uchg` 혹은 git add+commit 권장.
3. hexa toolchain blocker 별도 cycle 로 분리 (anima-clm-eeg integrity 와 무관, 전 anima 영향).

## 6. Cost / Cap

- mac local, GPU 0, LLM 0, $0, network 0
- wallclock ≈ 18min (cap 30min compliance)
- raw#9 strict, 한글 OK
- destructive 0 (5 hexa + frozen v1 JSON read-only 그대로)

## 7. Refs

- frozen v1: `/Users/ghost/core/anima/anima-clm-eeg/state/clm_eeg_pre_register_v1.json`
- 5 hexa: `/Users/ghost/core/anima/anima-clm-eeg/tool/clm_eeg_*.hexa`
- 4 emitted JSON: `/Users/ghost/core/anima/state/clm_eeg_*.json`
- marker: `/Users/ghost/core/anima/anima-clm-eeg/state/markers/path_a_integrity_verify_complete.marker`
- memory: `~/.claude/projects/-Users-ghost-core-anima/memory/project_clm_eeg_pre_register.md` (P1 sha 갱신 entry)
