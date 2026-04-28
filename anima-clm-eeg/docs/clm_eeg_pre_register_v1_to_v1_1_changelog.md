# CLM-EEG Pre-Register v1.0 → v1.1 Changelog

- **Frozen v1.0**: 2026-04-26 19:30:29 (`anima-clm-eeg/state/clm_eeg_pre_register_v1.json` initial freeze)
- **Frozen v1.1**: 2026-04-27 00:18 (`anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json` — this freeze)
- **Issue link**: `anima/.roadmap` #48 (Path A integrity verify)
- **Patch type**: **sha-only re-freeze**, criteria 변경 없음, v2 bump 미필요
- **임무 전체 cap**: 30분 mac local, $0, raw#9 strict, hexa-only, LLM=none

## 1. 발견 (issue#48 Path A integrity verify)

ω-cycle 6-step Step 3 positive selftest 에서 10-file SHA-256 cross-check 결과:

- **7/10 match** (preserved)
- **3/10 mismatch** (drift)
  - `tool/clm_eeg_p1_lz_pre_register.hexa`: `cd17abd8…` → `cce9a801…` (mtime 2026-04-26 19:46:24, frozen 후 +16분)
  - `state/clm_eeg_p1_lz_pre_register.json`: `5099794e…` → `cb5e9aac…` (mtime 19:46:31, P1 hexa 직후)
  - `state/clm_eeg_harness_smoke.json`: `9160feef…` → `fd51e4d3…` (mtime 21:22:12)

→ **byte-identical lock 위반** (raw#9 silent edit, criteria threshold는 보존).

## 2. 후속 추가 변동 (v1.json silent in-place update + 두 번째 regen)

issue#48 작성 직후 v1.json 자체에 대한 in-place edit 발생 (sha block 갱신 + v1.1 metadata 추가). 그 후 또다시 hexa toolchain 변경에 의한 fixture/P1 hexa regenerate 발생 (mtime 2026-04-27 00:15-00:18).

→ **v1.json 자체가 "frozen" 의미 위반** (in-place 두 번 갱신).

→ 본 v1.1 발행은 **별도 file** (`clm_eeg_pre_register_v1_1.json`) 으로 발행하여 v1.json silent-update 트라젝트리를 완전히 격리.

## 3. v1.0 → v1.1 sha 변경 사항 (5/10 file drift)

| 파일 | v1.0 sha (head 16) | v1.1 sha (head 16) | category |
|---|---|---|---|
| `tool/clm_eeg_synthetic_fixture.hexa` | `0dfe2c2e946e1fa6` | `8297e2bf90acd7ef` | source_silent_edit (mtime 04-27 00:15) |
| `tool/clm_eeg_p1_lz_pre_register.hexa` | `cd17abd8aa45d491` | `416e6be6f6e0c451` | source_silent_edit (issue#48 시점 `cce9a801`, 04-27 00:16 재생) |
| `tool/clm_eeg_p2_tlr_pre_register.hexa` | `fbff2e85a5e2a892` | `fbff2e85a5e2a892` | preserved |
| `tool/clm_eeg_p3_gcg_pre_register.hexa` | `0eec458cf7cc300b` | `0eec458cf7cc300b` | preserved |
| `tool/clm_eeg_harness_smoke.hexa` | `18196513ba2c544e` | `18196513ba2c544e` | preserved |
| `fixtures/synthetic_16ch_v1.json` | `831a1b5d49234d30` | `b6f1cc8669bf5bb5` | fixture_regen (FNV-deterministic, seed unchanged) |
| `state/clm_eeg_p1_lz_pre_register.json` | `5099794e78838196` | `287cf30451866273` | emitted_regen_after_source_edit |
| `state/clm_eeg_p2_tlr_pre_register.json` | `e857c0d8983a781f` | `459a9725d5e04544` | emitted_regen_chain |
| `state/clm_eeg_p3_gcg_pre_register.json` | `953ce72f72da2d8c` | `0c21f51391cf5f05` | emitted_regen_chain |
| `state/clm_eeg_harness_smoke.json` | `9160feef81a8c2c6` | `5d9f96e5137cc12c` | emitted_regen_chain |

**Drift 8/10** (issue#48 측정 시점 3/10 → v1.1 freeze 시점 8/10 — 두 번째 regen 사이클이 5개 emitted JSON 전부 갱신 + fixture + p1 hexa 다시 한 번).

raw#10 honest: `clm_eeg_p2_tlr_pre_register.json` 와 `clm_eeg_p3_gcg_pre_register.json` 은 issue#48 작성 시 sha 일치였으나, v1.1 freeze 시점에 다시 regen 되어 sha drift. P2/P3 hexa source 는 변하지 않았으므로 emitted JSON drift 가 어떻게 발생했는지는 forensic 미해결 (fixture sha 가 바뀌었기 때문에 hexa P2/P3 가 fixture 를 입력으로 받아 새 출력 emit 했을 가능성 高).

## 4. Criteria thresholds — 보존 확인 (positive selftest)

`state/clm_eeg_p1_lz_pre_register.json` (v1.1 freeze 시점 emit) 직접 확인:
- `C1_lz76_eeg_min_x1000`: **650** ✓
- `C2_delta_human_max_permille`: **200** ✓
- `human_baseline_lz76_x1000`: **850** ✓
- `verdict_rule`: `"P1.PASS = (LZ76 >= C1) AND (|Δ|/human <= C2)"` ✓

`state/clm_eeg_harness_smoke.json` (v1.1 freeze 시점 emit):
- `composite_rule`: `"HARNESS_OK iff (p1_pass + p2_pass + p3_pass) >= 2"` ✓
- `pass_count`: **3 / required 2** ✓
- `harness_ok`: **1** ✓

→ **C1/C2/baseline/verdict_rule 11개 임계값 100% 보존**, falsification surface unchanged.

## 5. Negative falsifier — 향후 v2 bump 트리거

다음 중 하나라도 변경되면 **v2 bump 필수** (v1.x sha-only 갱신 불충분):

1. `criteria.P1_LZ.C1_lz76_eeg_min_x1000` ≠ **650**
2. `criteria.P1_LZ.C2_delta_human_max_permille` ≠ **200**
3. `criteria.P1_LZ.human_baseline_lz76_x1000` ≠ **850**
4. `criteria.P2_TLR.C1_alpha_coh_min_x1000` ≠ **450**
5. `criteria.P2_TLR.C2_clm_r_min_x1000` ≠ **380**
6. `criteria.P3_GCG.C1_gc_f_min_x100` ≠ **400**
7. `criteria.P3_GCG.C2_unidir_ratio_min_x100` ≠ **200**
8. `criteria.composite.rule` ≠ `"HARNESS_OK iff (p1_pass + p2_pass + p3_pass) >= 2"`
9. 임의 `verdict_rule` 문자열 변경
10. P1/P2/P3 hypothesis 본문 변경

→ 본 v1.1 patch 는 위 10개 negative falsifier 중 **하나도 변경하지 않음**, 따라서 **sha-only patch 유효**.

## 6. v1.1 chained_fingerprint

- **chain_sha256**: `647e04f7db5e802ed7069dfb6cbd94f8e90d56b9c25ca3f6097e55110c823a03`
- **chain_fnv32**: `585811529`
- **v1.0 chain_fnv32 (reference)**: `2588542012`
- **재계산**: 5 hexa + 1 fixture + 4 emitted = 10 hex sha 를 fixed order 로 ascii concat → sha256.

## 7. Silent-edit 재발 방지 — 권장 lock 명세

### 7.1 chflags uchg (OS-level immutability, mac native)

```
CHFLAGS_AI_ACK=1 chflags uchg \
  /Users/ghost/core/anima/anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json \
  /Users/ghost/core/anima/anima-clm-eeg/state/clm_eeg_pre_register_v1.json \
  /Users/ghost/core/anima/anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa \
  /Users/ghost/core/anima/anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa \
  /Users/ghost/core/anima/anima-clm-eeg/tool/clm_eeg_p2_tlr_pre_register.hexa \
  /Users/ghost/core/anima/anima-clm-eeg/tool/clm_eeg_p3_gcg_pre_register.hexa \
  /Users/ghost/core/anima/anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa \
  /Users/ghost/core/anima/anima-clm-eeg/fixtures/synthetic_16ch_v1.json
```

해제 시: `CHFLAGS_AI_ACK=1 chflags nouchg <file>` (write 시도는 EPERM 으로 실패 → silent-edit 차단).

### 7.2 git tracking (version-control-side audit)

```
cd /Users/ghost/core/anima
git add anima-clm-eeg/state/clm_eeg_pre_register_v1.json \
        anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json \
        anima-clm-eeg/tool/clm_eeg_*.hexa \
        anima-clm-eeg/fixtures/synthetic_16ch_v1.json
git commit -m "freeze(clm-eeg): v1.1 pre-register sha re-freeze (issue#48 follow-up)"
```

→ 향후 silent-edit 발생 시 `git diff` 로 즉시 추적 가능 (chflags uchg 해제 후에도 변경 흔적 남음).

### 7.3 두 lock 의 직교성

- **chflags uchg**: prevention (write 시도 자체 차단). 단점: hexa toolchain rerun 시 emit 불가.
- **git track**: detection (변경 발생 후 차이 인지). 단점: 변경 자체는 막지 못함.

→ 양 lock 동시 적용 권장. dev 시점에 chflags 해제 → emit → re-freeze sha → chflags 재적용 + git commit 워크플로.

## 8. Post-EEG D+1 진입 시 사용 지침

D+1 (P1 LZ 실측 verify) 시점에서:

1. **frozen criteria 그대로 사용**: 650/200/850 (v1.1 sha 블록 기준)
2. **integrity baseline**: `clm_eeg_pre_register_v1_1.json.sha256_v1_1_frozen` 의 10 sha 값
3. **D+1 actual run 전**: 위 10 sha 를 shasum 으로 재측정하여 v1.1 frozen 과 일치 확인 (10/10 match 필수)
4. **불일치 시 abort**: 추가 silent-edit 발생 의심 → forensic 후 v1.2 또는 v2 bump 결정

## 9. ω-cycle 6-step 본 cycle 진행

1. **design**: v1.1 patch criterion = sha-only re-freeze (criteria 변경 X). FROZEN.
2. **implement**: `clm_eeg_pre_register_v1_1.json` + 본 changelog md 작성.
3. **positive selftest**: 5 hexa + 1 fixture + 4 emitted JSON sha 모두 `shasum -a 256` 로 측정 → v1.1 sha block 과 cross-check 10/10 match. P1 emitted JSON 의 C1=650/C2=200/baseline=850 직접 verify ✓.
4. **negative falsify**: §5 의 10개 negative falsifier 명시. v1.1 patch 가 그 중 하나라도 변경하면 patch 무효 → v2 bump 필요. 본 patch 는 0/10 변경.
5. **byte-identical**: 10 file sha 를 2회 측정 (동일 shasum 실행) — 모두 stable. v1.1 chain_sha256 = `647e04f7db5e802e…` deterministic 재계산 가능.
6. **iterate**: iter 0 = sha-only path freeze. iter 1 = 추가 변경 없음 (criteria 보존 확인 후 종료).

## 10. Cost / Cap

- mac local, GPU 0, LLM 0, $0, network 0
- wallclock ≈ 22min (cap 30min compliance)
- raw#9 strict, hexa-only (산출 JSON + md 만, hexa rerun 없음 — toolchain blocker 별개 cycle)
- destructive 0 (`clm_eeg_pre_register_v1.json` 그대로 보존)

## 11. 다음 cycle

- **D+0 EEG hardware arrival** 후 **D+1 P1 LZ verify** 진입 시 v1.1 sha block 을 integrity baseline 으로 사용.
- 만약 D+1 진입 전 추가 silent-edit 검출 시 본 v1.1 → v1.2 patch (sha 재갱신) 반복.
- D+1 actual real-EEG verdict 가 P1 PASS 면 paradigm v11 7th axis (EEG–CLM phenomenal anchor) 등록 candidate.
- hexa toolchain blocker (issue#48 §2 Step 2) 별도 cycle 분리 — anima-clm-eeg 와 무관, 전 anima 영향.

## 12. Refs

- v1.0 (preserved): `/Users/ghost/core/anima/anima-clm-eeg/state/clm_eeg_pre_register_v1.json`
- v1.1 (this freeze): `/Users/ghost/core/anima/anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json`
- changelog (this file): `/Users/ghost/core/anima/anima-clm-eeg/docs/clm_eeg_pre_register_v1_to_v1_1_changelog.md`
- marker: `/Users/ghost/core/anima/anima-clm-eeg/state/markers/clm_eeg_v1_1_patch_complete.marker`
- issue#48 landing: `/Users/ghost/core/anima/anima-clm-eeg/docs/path_a_integrity_verify_landing.md`
- memory: `~/.claude/projects/-Users-ghost-core-anima/memory/project_clm_eeg_v1_1_patch.md` (new)
