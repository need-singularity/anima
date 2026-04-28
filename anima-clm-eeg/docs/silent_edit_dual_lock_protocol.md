# Silent-Edit Dual-Lock Protocol — Path A frozen v1 + v1.1 산출물

**작성일**: 2026-04-27
**대상**: Path A (CLM-EEG pre-register chain) frozen v1 + v1.1 산출물 8 file
**원인 사건**: 이전 ω-cycle #61 (P1 LZ v1.1 patch) 진행 중 5/10 file silent drift 발견 — `clm_eeg_pre_register_v1.json` 이 in-place silently edited (sha block + v1.1 metadata appended) 상태로 v1.1 freeze 진입.
**목표**: 동일 종류 silent-edit 재발을 두 직교 layer 에서 차단/탐지.

---

## 1. Lock 대상 8 file

| # | path | role |
|---|------|------|
| 1 | `anima-clm-eeg/state/clm_eeg_pre_register_v1.json` | v1.0 frozen manifest (in-place edited 사건 본체) |
| 2 | `anima-clm-eeg/state/clm_eeg_pre_register_v1_1.json` | v1.1 frozen manifest (sha-only patch SSOT) |
| 3 | `anima-clm-eeg/tool/clm_eeg_synthetic_fixture.hexa` | fixture generator (P0) |
| 4 | `anima-clm-eeg/tool/clm_eeg_p1_lz_pre_register.hexa` | P1 LZ probe (drift epicenter `cd17abd8 → 416e6be6`) |
| 5 | `anima-clm-eeg/tool/clm_eeg_p2_tlr_pre_register.hexa` | P2 TLR probe |
| 6 | `anima-clm-eeg/tool/clm_eeg_p3_gcg_pre_register.hexa` | P3 GCG probe |
| 7 | `anima-clm-eeg/tool/clm_eeg_harness_smoke.hexa` | harness smoke entrypoint |
| 8 | `anima-clm-eeg/fixtures/synthetic_16ch_v1.json` | synthetic 16ch fixture artefact |

이 8 file 은 **재freeze 대상이 아닌 한 byte-identical 유지가 frozen contract**.

---

## 2. Dual-Lock 설계: 두 직교 layer

### Layer 1 — `chflags uchg` (OS-level prevention)

- macOS HFS+/APFS user-immutable flag.
- 효과: write / truncate / unlink / rename 모두 EPERM. root 라도 `chflags nouchg` 선행 필요.
- 적용 단위: per-file, repo 외부 (file-system layer).
- 효과 범위: Claude / IDE / build script / shell `>` redirect 등 **모든 actor** 에 적용.
- **핵심**: silent-edit attempt 가 즉시 OS error 로 surface — '보이지 않는 변경' 의 가능성 자체를 제거.
- 해제: `sudo chflags nouchg <file>` (사용자 명시 의도 시에만; v2 freeze 등).

### Layer 2 — `git add` (VCS-level detection)

- git index 에 추가하여 working-tree drift 가 `git status` / `git diff` 로 surface 되도록 함.
- **#61 사건의 직접 원인**: `clm_eeg_pre_register_v1_1.json` 이 git untracked 상태로 freeze 됨 → 만약 silent-edit 가 발생해도 `git diff` 가 잡지 못함.
- 본 protocol 의 git track 단계는 commit X — 사용자 명시 승인 후 manual.
- 효과: chflags 가 (어떤 이유로) 우회/해제 후 silent-edit 발생하더라도 다음 `git status` 시점에 즉시 detection.

### 직교성 (orthogonality) 정리

| layer | semantics | failure mode that other layer covers |
|-------|-----------|--------------------------------------|
| L1 chflags | prevention (edit 시도 차단) | untracked drift detection 불가 — L2 가 cover |
| L2 git add | detection (edit 발생 후 surface) | tracked file silent-edit 자체 막지 않음 — L1 이 cover |

두 layer 는 **순차 방어** (L1 차단 → 실패 시 L1 해제 후 L2 detection) 로 작동하므로 **직교** (independent, multiplicative coverage).

---

## 3. 절차 contract

### Phase 0 — selftest (DRY_RUN, 본 cycle)

```bash
DRY_RUN=1 bash anima-clm-eeg/tool/silent_edit_dual_lock.sh.txt
```

기대 출력: 8/8 OK, plan 출력, mutation 없음, exit 0.

### Phase 1 — actual lock (사용자 명시 승인 후 manual)

```bash
DRY_RUN=0 CHFLAGS_AI_ACK=1 bash anima-clm-eeg/tool/silent_edit_dual_lock.sh.txt
```

기대: 8/8 file 에 대해 (a) chflags uchg 적용, (b) untracked → tracked, (c) commit X (manual).

### Phase 2 — manual git commit (사용자 명시 승인 후)

```bash
git status            # staged 항목 확인
git diff --cached     # 0 byte content diff (lock 자체는 metadata only)
git commit -m "lock(path-a): freeze v1+v1.1 8 산출물 (chflags uchg + git track)"
```

### Phase 3 — 재freeze 시 unlock 절차 (v2 등)

1. `sudo chflags nouchg <file>` — L1 해제
2. 의도된 edit 수행
3. `chflags uchg <file>` 재적용
4. git commit (drift surface 됨)

---

## 4. 안전망

| risk | mitigation |
|------|------------|
| script 가 8 file 중 일부에만 partial-lock | step A 에서 missing 1+ → abort exit 2 |
| user 가 의도치 않게 mutation 실행 | DRY_RUN=1 default, CHFLAGS_AI_ACK=1 명시 필요 |
| chflags 적용 실패 (permission 등) | step D 에서 `chflags ... \|\| exit 4` |
| git add 자체 실패 | step D 에서 `git add ... \|\| exit 5` |
| commit 자동 실행 | script 안에 commit 명령 없음 — 사용자 manual 만 |

---

## 5. 재발 방지 검증 기준

본 protocol 이 이전 #61 같은 silent-edit 을 차단했을지 검증:

1. **#61 v1.json in-place edit (sha 블록 + v1.1 metadata)**: chflags uchg 적용 상태였다면 write 자체가 EPERM → block.
2. **#61 v1_1.json untracked freeze**: git add 적용 상태였다면 freeze 후 첫 silent-edit 시점에 `git status` 가 modified 로 surface.
3. **5/10 drift trajectory**: 각 file 에 chflags 적용 상태였다면 regen sweep 자체가 file-system 단계에서 실패 → 사용자가 unlock 명시 필요 → 재freeze 의도가 명확해짐.

---

## 6. 산출물

| path | role |
|------|------|
| `anima-clm-eeg/tool/silent_edit_dual_lock.sh.txt` | dual-lock script (실행 X, 사용자 명시 승인 후 manual run) |
| `anima-clm-eeg/docs/silent_edit_dual_lock_protocol.md` | 본 protocol 문서 |
| `anima-clm-eeg/state/markers/silent_edit_dual_lock_complete.marker` | silent-land marker |

---

## 7. 후속 cycle 권장

- **사용자 승인 후 actual lock 실행** (`DRY_RUN=0 CHFLAGS_AI_ACK=1`).
- **확장 후보**: 다른 frozen 산출물 (e.g. anima-tribev2-pilot v1 launcher, anima-clm-eeg cross-link audit) 에 동일 dual-lock 적용.
- **검증 cycle**: lock 적용 후 1주일 monitor — 의도치 않은 EPERM (build/test pipeline 에서) 발생 여부 관찰.
- **자동화 후보**: pre-commit hook 으로 frozen file 의 chflags+tracked 상태 monitoring (현재 manual).
