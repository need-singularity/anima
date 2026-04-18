# Wake-up Checklist — 2026-04-19

안녕하세요. 야간 세션 결과입니다. 3분 안에 어디서 재개할지 판단 가능하도록 설계.

---

## 0. 첫 30초 — 현황 스냅샷

```bash
cd /Users/ghost/Dev/anima && git log --oneline -20
cd /Users/ghost/Dev/nexus && git log --oneline -10
runpodctl get pod                         # H100 zero-idle 확인
```

Session summary: `/Users/ghost/Dev/anima/docs/session_20260418_19_overnight_summary.md`

---

## 🔴 CRITICAL — 사용자 결정 필요 (3건)

### C1. `launch.hexa` cvf 호출 제거 여부
- 현황: `anima-core/verification/cvf.hexa` 수정됨 (modified)
- 질문: launch.hexa 의 cvf 의존 자체를 제거할지 vs cvf stub 유지할지
- 결정 후: commit sweep v3 진행 가능

### C2. `--no-verify` commit 이력 검토
- 세션 중 `--no-verify` 사용 금지 준수 여부 — git log 에서 확인
- 필요 시 commit 재작성 (단, amend 금지 — 새 커밋으로)

### C3. hxblas_cuda shim 경로 결정
- 3가지 옵션:
  - (a) sister repo 완성 대기
  - (b) option B (pure-hexa scalar fallback, 이미 `896ca10d` 에 merge)
  - (c) runpod 재fire 로 CUDA 직접 검증
- 현재 (b) 가 landed — 확정 시 sister wait 해제

---

## 🟡 READY — 즉시 fire 가능 (8건)

### R1. ALM r11 branch_select fire
- File: `training/alm_r11_branch_select.hexa` (untracked)
- 선행: r10 DONE 확인 (`alm_r10_fire_log_20260418T125201Z.md` 종결 체크)

### R2. CLM 8th fire train_clm smoke
- 전제: scale_smoke 완성 여부 확인 필요
- MFS quota 주의 (old ckpt 삭제)

### R3. Physics Tier-2 HW audit
- Tier-1 4/4 PASS (`experiments/physics_tier1_20260419.md`) 후속
- Tier-2 = HW-involved (ESP32/FPGA/양자 회로)

### R4. Commit sweep v4 — 8+ untracked artifacts
```
training/alm_r11_branch_select.hexa
training/corpus_yt_ko/
training/deploy/clm_r4_bundler_relaunch*
training/deploy/ubu_cuda_smoke_20260419.md
anima-speak/docs/improvement_plan_20260419.md
experiments/holo_post/results/*.jsonl (6개)
experiments/physics_*.md (2개)
docs/htz_governor_tuning_20260419.md
```

### R5. Sister handoff review + merge
- nexus `1fde653a` (handoff CRITICAL regression 섹션) 확인
- merge 여부 결정

### R6. r11 launch retry storm 검토
- `alm_r11_{a,b,c}_launch_*` 10+ 로그 — 실패 패턴 파악 후 fix

### R7. CLM r4 pod2 relaunch 11회 실패 원인 분석
- `clm_r4_pod2_relaunch_20260418T15*.log` 11개 연속 실패
- MFS quota vs binary install 문제 구분

### R8. Holo-post ethics_redteam 결과 분석
- 6개 jsonl (`experiments/holo_post/results/ethics_redteam_*.jsonl`)
- 패턴/regression 여부

---

## 🟢 INFO — 참고용

- smoke rate 78.57% → 재smoke 후 current 확인 필요 (`d3c649a8`)
- Infra 5-host 사용 가능: htz + ubu + ubu2 + darwin + (pod)
- Φ 16D normalization 완료 — `docs/phi_16d_normalization_20260418.md`
- BLAS 14 files portable (scalar fallback) — CUDA 없이 동작
- Telegram bridge 14 extern fn strip 완료
- anima-speak bf16 NEON bench landed
- MEMORY.md 추가 후보 3건: launch.hexa cvf 패턴 / r11 retry storm / Physics Tier-1 baseline
- 로드맵: seed-freeze 플래그 ON 유지 중
- anima HEAD: `d3c649a8`, nexus HEAD: `259b6875`

---

## First-action script (copy-paste)

```bash
# 1. 현황
cd /Users/ghost/Dev/anima && git log --oneline -20
cd /Users/ghost/Dev/nexus && git log --oneline -10

# 2. Pod idle 확인
runpodctl get pod

# 3. 문서 열기
open /Users/ghost/Dev/anima/docs/session_20260418_19_overnight_summary.md
open /Users/ghost/Dev/anima/docs/wakeup_checklist_20260419.md

# 4. CRITICAL 3건 결정 → READY 1~3 순차 fire
```

추천 순서: **C1 → C3 → R4 (sweep) → R1 (ALM r11) → R3 (Physics Tier-2)**.
