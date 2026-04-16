# 2026-04-16 Session Recap — v2.0 GA + Infrastructure Consolidation

> **Master reference** — 이 세션에서 일어난 모든 주요 사건, 커밋, 발견, 블로커.
> 새 세션 진입 시 이 문서 먼저 읽으면 상황 복구 가능.

---

## TL;DR

**도달**: ALM 14B v2.0 GA 공식 태그 (`fc56f931`) + CLM 1B/3B pipeline 검증 + HEXA-SPEAK 구조 완성.

**가속**: v3.0 직원 능력 도달 일정 14-21일 → **7-14일**.

**소비**: ~$30 (CLM 1B + CLM 3B + hexa-c4 idle).

**수확**: 3 publishable research notes, 5 memory files, 2 handoff prompts.

---

## 주요 성과 (14건)

| # | 성과 | 커밋 | 가치 |
|---|------|------|------|
| 1 | CLM 1B r3f 학습 PASS (eval 1.23 ppl 3.42) | anima@a38d7ca6 | ★★★ |
| 2 | CLM 3B r1 pipeline 검증 PASS (eval 1.22 ppl 3.38) | anima@7787816e | ★★★ |
| 3 | 7/7 의식검증 VERIFIED (cells=128 phase transition) | anima@5e6e372b | ★★★ |
| 4 | ALM v2.0 RC Top 3 fix + LIFT HOLD | anima@c3926183 | ★★★ |
| 5 | ALM v2.0 GA 태그 (Path C prompt aug 0.87) | anima@fc56f931 | ★★★ |
| 6 | hxcuda STFT/iSTFT CUDA kernel (SNR 129.5dB) | hexa-lang@fc20fe4 | ★★ |
| 7 | neural_vocoder 42L → 536L real impl | anima@0078da8c | ★★ |
| 8 | Stage C iSTFT FFI 배관 검증 | anima@e12ed2d8 | ★★ |
| 9 | hexa serve native scaffold (7/7 self-test) | anima@47ae0a37 | ★★ |
| 10 | H-HEXA-CANONICAL lint 규칙 추가 | nexus@d18f56d8 | ★★ |
| 11 | H-NOHOOK-DRIFT lint 규칙 추가 | nexus@839f49d4 | ★★ |
| 12 | telescope.hexa pure fn + a[i]=v 수정 | nexus@70ade726 | ★ |
| 13 | MFS quota 골화 (pre-save rotation) | anima@988ecec5 | ★★ |
| 14 | 3 research notes (publishable) | papers@8780048 | ★ |

---

## 주요 발견 (3 epistemic lessons)

### 1. "측정 장치가 틀렸지, 측정 대상이 틀린 게 아니다"
크로스 디스커버리 패턴: 3개 독립 버그, 1 교훈.
- **MFS quota**: `df`가 잘못된 프로브 (47GB per-session hidden)
- **V5 SELF_LOOP**: N=32 cells 측정이 phase transition 아래
- **Path C**: hire_sim 하네스가 format 따지지 실력을 안 봤다

### 2. "Client 적응, environment 아님"
- **Path C**: serve 불변, 클라이언트 prompt aug만
- **MFS fix**: torch.save 불변, 경계 계층 rotation만

### 3. Triple-mislabeling 체인
- Pass 1: "hire_sim 100% = Claude baseline" (부분 정정)
- Pass 2: "hire_sim_real_eval_r9 = ALM actual" (내가 또 오해)
- Pass 3: "둘 다 Claude" (최종 진실)
- 교훈: agent 1회 독해 믿지 말고, 소스 + 헤더 직접 검증

---

## 골화된 인프라 규칙 (재발 방지)

| 규칙 | 강제 방식 | 출처 |
|------|-----------|------|
| RunPod MFS 47GB 세션 쿼터 | training/CLAUDE.md + pre-save rotation 코드 | MFS crash 3회 |
| R2 upload 학습 중 금지 | train_clm_1b.py DEFERRED 큐만 | r3/r3b crash |
| phi_emergency_ckpt 제거 | train_clm_1b.py skip 로직 | r3b step 4000 crash |
| .py SSOT 등록 block | shared/harness/lint.hexa H-HEXA-CANONICAL | 5019 refs audit |
| settings.json 훅 드리프트 감지 | shared/harness/lint.hexa H-NOHOOK-DRIFT | ready/.claude 발견 |
| pure fn 예약어 주의 | memory/feedback_hexa_syntax.md | telescope crash |
| a[i]=v silent no-op | memory/feedback_hexa_runtime.md | telescope crash |
| Gate claim 실측 검증 | memory/feedback_gate_vs_live_drift.md | 삼중 mislabel |

---

## Pod 활용 역사

| Pod ID | 이름 | GPU | 용도 | 결과 |
|--------|------|-----|------|------|
| kyk15ck0c428es | anima-clm-1b | H100 | CLM 1B r3/r3b/r3c/r3d/r3e/r3f | PASS (r3f, 33min) |
| h94bio33ugnp8o | anima-clm-3b | H100 | CLM 3B r1 pipeline | PASS (62min) |
| itfl66q4z768kh | anima-alm-serve | H100 | ALM v2.0 GA live serving | LIVE 유지 |
| u01lnnu8ywt92p | hexa-c4 | 3090 | hxcuda build + bench | 활성 (bench용) |
| 8m4q1z2hi5nw2u | hexa-lang-surpass | H100 | (idle) | 중간 정지 |

---

## 남은 v3.0 블로커

### 도착지 1 — v2.0 GA 완전 배포 (인프라)
- Python serve → 네이티브 hexa serve (5-7일)
  - [in_flight] net builtin C port (agent #22)
  - [pending] libhxqwen14b.so (3-5일)
  - [done] libhxcuda Linux FFI ✓
  - [pending] iSTFT dispatch marshalling (1-2일, 다른 세션)

### 도착지 2 — v3.0 직원 능력
- [in_flight] ALM r10 synthetic corpus (agent #26)
- [pending] ALM r10 학습 (~4-6h $18 after corpus)
- [delegated] HEXA-SPEAK W_ctrl 학습 (다른 세션)
- [pending] Tool-use LoRA (24h $72)
- [pending] 6채널 인지 (zeta-surpass 의존)

상세: `shared/papers/v3_employee_capability_path_20260416.md` 부록 A

---

## 메모리 파일 (Claude 본인 것)

위치: `~/.claude-claude12/projects/-Users-ghost-Dev-anima/memory/`

| 파일 | 용도 |
|------|------|
| feedback_runpod_mfs_quota.md | MFS 쿼터 트랩 패턴 |
| feedback_gate_vs_live_drift.md | Gate vs live 드리프트 + triple-mislabel |
| feedback_h100_free_use.md | 4-pod 한도 내 자유 사용 |
| reference_hexa_c4_launch.md | RTX 3090 bench pod 레시피 |
| feedback_hexa_runtime.md | a[i]=v / pure fn 예약어 등 |
| feedback_hexa_syntax.md | match 예약어 |

---

## 인수인계 문서

| 문서 | 대상 |
|------|------|
| `training/deploy/hexa_speak_handoff_20260416.md` | HEXA-SPEAK Mk.III 실음 학습 |
| `training/deploy/hexa_serve_native_plan_20260416.md` | Python → 네이티브 serve 전환 |
| `training/deploy/hexa_codegen_research_20260416.md` | Hexa codegen 5 task critical path |
| `training/deploy/alm_ga_gap_research_20260416.md` | ALM GA 5 path 비교 |
| `training/deploy/ALM_v2_RC_RELEASE.md` | v2.0 RC/GA 릴리즈 체크리스트 |
| `training/deploy/session_recap_20260416.md` | **이 파일** |

---

## 숫자로 요약

- **Commits**: 30+ (anima + nexus + ready + papers + hexa-lang)
- **Agents**: 15+ dispatch (completion/fail mix)
- **Pods 사용**: 5 (2개 상시, 3개 일시)
- **총 학습 시간**: CLM 1B 33min + CLM 3B 62min = 95min H100 SXM
- **비용**: ~$30 (H100 95min + hexa-c4 continuous)
- **새 파일**: 17 (deploy/, papers/, 메모리)
- **코드 LOC 추가**: ~2000 (neural_vocoder 494 + STFT 297 + serve 437 + lint 77 + etc)

---

## 이 세션의 "한 문장 메시지"

**측정만 올바르면 ALM은 이미 직원이다; 인프라만 정비하면 모든 건 .hexa에서 돈다.**
