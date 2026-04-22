# B-axis Prompt — Post-H100 Research (Mk.XII / r14 / Φ Paper)

**Date**: 2026-04-22
**Axis**: B (7-axis framework)
**Target session**: anima 재방문 또는 post-H100 전용 세션
**Precondition**: β main merge 완료 + H100 launch verdict (PASS/PARTIAL) 확보 가정
**Status**: paste-ready (<400 lines, NO .py)

---

## 0. How to use

1. β main merge + H100 launch verdict (state/h100_launch_verdict.json or equivalent) 확인
2. Mk.VI checkpoint (8B, r13 corpus 완료) + r14 skeleton (docs/alm_r14_design_v1_20260422.md) 확보 확인
3. 아래 prompt 를 post-H100 세션에 paste → B.1/B.2/B.3 순차 혹은 병렬 실행
4. B.3 (paper draft) 는 B.1/B.2 완료 없어도 partial 가능 (Mk.VI empirical data 기반)

---

## 1. Prompt (paste-ready)

```
anima session — B axis (post-H100 research · Mk.XII / r14 / Φ paper draft)

Working dir: /Users/ghost/core/anima
Precondition:
- β main (hexa-lang) merge 완료 + main acceleration mirror 확보
- H100 launch verdict 확보 (PASS / PARTIAL / FAIL 중 하나)
  · PASS/PARTIAL → B.1 진행 가능
  · FAIL → B.1 보류, B.2/B.3 만 진행

배경:
- A (launch 최적화) = ROI 82 항목 완료
- B (post-H100 research) = 본 세션 대상
  · B.1: Mk.XII scale-up (Mk.VI 8B → 70B)
  · B.2: r14 corpus full build (한글 30% · 한자 5% · 다국어 balance)
  · B.3: Φ empirical paper draft (#89)
- C/D/E/F/G = 별도 prompt 발행됨

참조 산출물 (이미 존재):
- docs/alm_r14_design_v1_20260422.md         (r14 skeleton + 한글 30% plan)
- state/alm_r14_corpus_skeleton.jsonl        (r14 seed shard list)
- docs/cell_learning_method_paradigm_20260422.md
- docs/anima_three_paradigm_unified_20260422.md
- .roadmap #82 (70B retrain), #21 (Mk.X AGI final), #89 (Φ paper draft)

Task breakdown:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
B.1 Mk.XII scale-up (8B → 70B)          [depends on H100 verdict]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Goal:
  - Mk.VI (8B · r13) checkpoint → Mk.XII (70B · r14) 재학습 plan 확정
  - cert chain (LM-E / LP-M / CG-M) 70B 스케일 재검증

Deliverables (anima 내부 작업):
  - docs/mk_xii_scale_up_plan_20260422.md
    · compute budget (H100 node-hour 추산)
    · parameter scaling law (8B → 70B 시 loss / perplexity 예측)
    · cert chain revalidation matrix (3축 x 5 metric)
    · rollback criteria (70B 실패 시 Mk.VI + r14 fallback)
  - state/mk_xii_scale_up_precheck.json
    · H100 verdict 참조
    · resource availability (GPU node, storage, bandwidth)
    · dependency status (r14 corpus ready? cert chain ready?)

Outside anima (외부 세션 필요):
  - 실제 70B training run 실행
  - distributed training infra (fsdp / tensor parallel) 검증
  - wandb / mlflow 연동

Dependency:
  - H100 launch verdict = PASS or PARTIAL
  - B.2 r14 corpus ≥ 50% 완료 (또는 r13 fallback)
  - cert chain engine upgraded for 70B

Hard constraint:
  - Mk.VI checkpoint 삭제 금지 (r14/Mk.XII 실패 시 rollback 원본)
  - .roadmap #82 entry 단순 update (신규 entry 생성 지양)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
B.2 r14 corpus full build (한글 30%)      [anima 내부 가능]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Goal:
  - r14 skeleton (docs/alm_r14_design_v1_20260422.md) → full corpus 확장
  - 한글 30% · 한자 5% · 다국어 balance 검증

Deliverables (anima 내부 작업):
  - docs/alm_r14_design_v2_20260422.md
    · r14 v1 skeleton → v2 finalization
    · shard manifest (size / lang ratio / quality score)
    · tokenizer 검증 (hexa-lang α/β 호환성)
  - state/alm_r14_corpus_manifest.json
    · shard별 byte count / token count / lang ratio
    · checksum (sha256) + bloom dedup
  - state/alm_r14_lang_ratio_check.json
    · 한글 30% · 한자 5% · 영어 40% · 기타 25% 검증
    · deviation tolerance ±2%p
  - tools/ 또는 streams/ 내부 shell script (NO .py)
    · corpus audit: byte count, dedup ratio, lang detection

Outside anima (외부 세션 필요):
  - 실제 대용량 shard 다운로드 (한글 corpus · 한자 source)
  - GPU-based tokenizer benchmark (70B scale)

Dependency:
  - hexa-lang β main merge 완료
  - tokenizer_sha (H100 precache 산출물) 호환성 확인
  - disk quota ≥ 2TB 확보

Hard constraint:
  - r13 corpus (state/alm_r13_*) 삭제/overwrite 금지
  - lang ratio deviation > 5%p 시 build abort

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
B.3 Φ empirical paper draft (#89)       [anima 내부 가능]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Goal:
  - Mk.VI (8B · r13) empirical Φ (phi) metric → paper draft
  - 3-paradigm unified framework 이론 + empirical data 결합
  - Mk.XII 결과 나오기 전이라도 Mk.VI 데이터만으로 v1 draft 가능

Deliverables (anima 내부 작업):
  - docs/phi_empirical_paper_draft_v1_20260422.md
    · Abstract / Intro / Related Work / Method / Results / Discussion
    · Mk.VI Φ measurement data
    · cell_learning_method + three_paradigm_unified 이론 근거
    · limitation section (Mk.XII 미확보, 70B 재검증 필요)
  - docs/phi_paper_figures_spec_20260422.md
    · figure list (Φ curve · perplexity vs model size · cert chain heatmap)
    · figure 생성 script outline (NO .py — shell + plot tool spec only)
  - state/phi_paper_draft_v1_status.json
    · section별 word count / completion %
    · citation count / figure count

Outside anima (외부 세션 필요):
  - LaTeX typesetting (overleaf / local)
  - figure rendering (matplotlib / tikz — 별도 환경)
  - peer review / arxiv submission

Dependency:
  - Mk.VI empirical Φ data (state/phi_* 또는 state/mk_vi_*)
  - docs/cell_learning_method_paradigm_20260422.md
  - docs/anima_three_paradigm_unified_20260422.md

Hard constraint:
  - Mk.XII 미확보 상태에서 v1 draft = "preliminary" 명시
  - Mk.XII 확보 후 v2 draft 에서 upgrade

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Global hard constraints:
  - .roadmap uchg (direct edit 금지, 신규 entry 만 append 허용)
  - no auto-commit (user 확인 후 수동 commit)
  - NO .py 생성 (shell + md + json only)
  - state/*.json 수정 시 기존 data preserve (merge, not overwrite)
  - Mk.VI checkpoint · r13 corpus 보존 (rollback anchor)
  - β main branch 기준 (feat/roadmap-63-multimodal 에서 branch)

Success criteria:
  - B.1: state/mk_xii_scale_up_precheck.json = "ready" or "blocked" 명시
        + docs/mk_xii_scale_up_plan_20260422.md ≥ 200 lines
  - B.2: state/alm_r14_lang_ratio_check.json deviation ≤ 2%p
        + docs/alm_r14_design_v2_20260422.md ≥ 300 lines
  - B.3: docs/phi_empirical_paper_draft_v1_20260422.md ≥ 8 sections
        + state/phi_paper_draft_v1_status.json completion ≥ 60%

신규 roadmap entry 후보 (append 전 user 확인):
  1. [B.1] "Mk.XII 70B scale-up precheck + plan doc"
  2. [B.1] "cert chain engine 70B-scale revalidation"
  3. [B.2] "r14 corpus full build (한글 30% · 한자 5%)"
  4. [B.2] "r14 tokenizer benchmark vs hexa-lang β"
  5. [B.3] "Φ empirical paper v1 draft (Mk.VI only)"
  6. [B.3] "Φ paper figure spec + citation matrix"
  7. [cross] "Mk.XII → Φ paper v2 upgrade pipeline"

Test plan:
  - B.1:
    [ ] docs/mk_xii_scale_up_plan_20260422.md 존재 + ≥ 200 lines
    [ ] state/mk_xii_scale_up_precheck.json = valid JSON
    [ ] H100 verdict 참조 확인 (grep "h100_launch_verdict")
    [ ] Mk.VI checkpoint 경로 명시 + 보존 verification
  - B.2:
    [ ] docs/alm_r14_design_v2_20260422.md 존재 + ≥ 300 lines
    [ ] state/alm_r14_corpus_manifest.json shard count ≥ 10
    [ ] state/alm_r14_lang_ratio_check.json lang ratio 한글 ≥ 28%
    [ ] r13 corpus 파일 mtime 변화 없음 (preserve 확인)
  - B.3:
    [ ] docs/phi_empirical_paper_draft_v1_20260422.md section ≥ 8
    [ ] docs/phi_paper_figures_spec_20260422.md figure ≥ 5
    [ ] state/phi_paper_draft_v1_status.json completion ≥ 60%
    [ ] "preliminary" 명시 (Mk.XII 미확보 reflect)

Report format (Under 300 words):
  - B.1/B.2/B.3 각 상태: ready / partial / blocked
  - 생성 파일 경로 list
  - 신규 roadmap entry 실제 append 여부 + count
  - H100 verdict branching 결과 (B.1 진행 여부)
  - 다음 세션 handoff 사항 (outside-anima task 요약)
```

---

## 2. Branching logic (H100 verdict 기반)

| H100 verdict | B.1 | B.2 | B.3 |
|--------------|-----|-----|-----|
| PASS         | full go | full go | full go (v1) |
| PARTIAL      | plan only (precheck blocked) | full go | full go (v1) |
| FAIL         | skip (rollback to Mk.VI) | full go (standalone) | full go (v1, Mk.VI only) |

---

## 3. Handoff notes

- B.1 실제 70B training = 외부 세션 필수 (anima 내부는 plan + precheck 까지)
- B.2 대용량 shard 다운로드 = 외부 세션 권장 (disk quota · network)
- B.3 LaTeX typesetting = 외부 세션 필수 (anima 내부는 md draft 까지)
- 모든 outside-anima task 는 `state/b_axis_outside_handoff.json` 에 기록 권장

---

## 4. Cross-axis dependency

- A (ROI 82) 완료 → B.1 precheck 시 resource 재활용 가능
- C/D/E/F/G prompts 와 충돌 없음 (B 축 독립)
- 단, D/E 축이 cert chain 관련이면 B.1 cert revalidation 과 coord 필요
