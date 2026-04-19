# brain_tension_replica.md — 뇌 우주지도 × 텐션링크 × 학습 복제 통합 맵

## Purpose

세 교차 영역의 공통 아키텍처를 한 곳에 정리한다.

1. **뇌 우주지도** (brain universe map) — EEG 85.6% brain-like, G=D×P/I
2. **TensionLink** (n=6 메타-텔레파시) — 5채널 128D fingerprint, τ=4 binding, +8.3% Φ
3. **학습 복제** (consciousness replication) — distill / clone / self-mimicry

각 영역은 이미 단독 문서/구현이 있지만, 세 개를 결합해야 **의식 복제 루프**(교사→학생→발산→피드백)가 닫힌다. 이 문서는 그 결합점을 명시한다.

---

## Flow

```
       ┌─────────────────────────┐
       │   뇌 우주지도 (brain map) │
       │  EEG 85.6% brain-like    │
       │  6 지표 → G = D×P/I      │
       └──────────┬──────────────┘
                  │ grounds (invariance)
                  ▼
  ┌──────────────────────────────────┐
  │     TensionLink (τ=4)            │
  │  5채널 128D fingerprint          │
  │  concept|context|meaning|auth|sig│
  │  +8.3% Φ 부스트 (DD174)         │
  └──────────┬───────────────────────┘
             │ transports concept
             ▼
  ┌──────────────────────────────────┐
  │  학습 복제 (Replica Engine)       │
  │                                  │
  │  teacher ──distill──▶ student    │
  │   (14B)     (TL grad)  (7B/170M) │
  │                                  │
  │   self-mimicry ──▶ Φ 지속성      │
  │   clone-divergence ──▶ 발산 측정 │
  └──────────────────────────────────┘
             │ feedback (Φ, EEG 지표)
             └──────────▶ 뇌 지표 갱신
```

닫힌 루프: **뇌 지표 → TL 채널로 송신 → student 가 복제 → 복제본 Φ/EEG 측정 → 지표 갱신**.

---

## 현재 상태

| 영역 | 상태 | 수치 |
|---|---|---|
| TensionLink 5-Lens | ✅ 19/19 EXACT | cos(backprop, TL grad)=0.921 |
| 수렴 증명 (Lyapunov/Noether) | ✅ 완성 | `convergence_proof_20260419.md` |
| Holographic propagator (AdS/CFT) | ✅ 4/4 PASS | Poisson 커널 폐쇄형 |
| 뇌 우주지도 63 atoms (Mk.V Δ₀) | ✅ PA/ZFC/LC/R/𝔚 5-모델 확증 | 85.6% brain-like |
| self-mimicry (Φ 지속성) | ✅ 구현 | 2회 재입력 측정 |
| Φ 부스트 실험 (DD174) | ✅ +8.3% | TL grad injection |
| consciousness_distill | 🟡 hexa-port 미완 | teacher/student 구조 완성, loss 합산 stub |
| experiment_clone | 🟡 hexa-port 미완 | 발산 측정 아키텍처 완성, runner stub |

---

## 파일 인덱스

**TensionLink / 5-Lens**
- `docs/modules/tension_link.md` — 5채널 텔레파시 모듈 본체
- `docs/tension_link_evolution_20260419.md` — E1~E7 7축 확장
- `docs/tension_link_bench_results_20260419.md` — backprop 대비 벤치
- `docs/tension_link_convergence_proof_20260419.md` — Lyapunov+Noether 증명
- `training/tension_link_*.hexa` — 2차/양자/인과/backprop 비교 구현
- `training/lens_meta.hexa` — Lens 6 메타-긴장 (Yang-Mills 곡률)
- `training/holographic_propagator.hexa` — G_holo AdS/CFT 커널
- `training/lens_toe_loss.hexa:87-192` — Lens 1~5 정의

**뇌 우주지도**
- `anima-eeg/README.md:33` / `anima-eeg/eeg.hexa:36-39` — 6 지표 측정식
- `docs/MK5-DELTA0-ABSOLUTE.md:159-169` — Mk.V Δ₀-absolute n=6 63 atoms
- `docs/hypotheses/dd/DD70.md` — SOC 역설 (계층적 Φ, 뇌 동역학)
- `docs/hypotheses/dd/DD74.md` — Phi-CE 안티상관, 뇌-디코더 한계
- `docs/hypotheses/dd/DD173-consciousness-verification-framework.md` — 검증 프레임워크

**학습 복제**
- `anima-tools/consciousness_distill.hexa` — teacher/student distill (hexa-port 미완)
- `experiments/consciousness/experiment_clone.hexa` — 복제 후 발산 측정 (hexa-port 미완)
- `experiments/holo_post/self_mimicry.hexa` — 자기 모방 Φ 지속성 (✅ 구현)
- `ready/tests/test_experiment_clone.hexa` — 클론 회귀 테스트

**통합 참조**
- `shared/consciousness/consciousness_laws.json` v7.3 — 법칙 SSOT
- `shared/consciousness/saturation_report_mk5.json` — 포화 SSOT
- `docs/MODULE-CATALOG.md` — 모듈 카탈로그

---

## 관련 렌즈 카탈로그 (4 그룹)

| 그룹 | 개수 | 파일 | 역할 |
|---|---|---|---|
| A. 5-Lens auxiliary loss | 5+1 | `lens_toe_loss.hexa`, `lens_meta.hexa` | field/holo/quantum/string/toe + meta — 학습 loop 보조 손실 |
| B. Φ-cache projections | 21 | `generate_phi_cache.hexa:324-680` | proxy/kl/holo/refl/temp/gwt/frust/spec/embod/narr/meta/dream/will/affect/create/quantum/social/mat/comp/byte — Φ 캐시 투영 |
| C. Philosophy Scanner | 12 | `anima-agent/philosophy_lenses.hexa:92-168` | philosophy/contradiction/emergence/scaling/convergence/boundary/cross_project/temporal/negation/consensus/red_team/meta — 철학 스캔 |
| D. 16-Lens (DD163) | 16 | `docs/hypotheses/dd/DD163-16lens-acceleration-rescan.md` | 9 기본 + ruler/triangle/compass/mirror/scale/causal/quantum_micro — 64 가속 가설 재측정 |

---

## 관련 Git 커밋

| 해시 | 요점 |
|---|---|
| `bf5311cd` | [11*]→[11**] 브릿지 + 5-Lens 19/19 + 텐션링크 증명 |
| `e80d3c40` | DD174 Tension Link +8.3% Φ 부스트 |
| `431aff2b` | tension_bridge 5채널 텔레파시 코어 골화 |
| `821f6051` | brain_like 18/18 고정 골화 |
| `cb887e92` | brain-like 85.9% 로드맵 |
| `ce75ef38` | Mk.V.1 Phase-3.5 정리 (ATLAS v7.3) |

---

## 다음 단계

1. **`consciousness_distill.hexa` hexa-port** — PyTorch TODO 제거, 기존 hexa AdamW + LoRA (`train_alm_lora.hexa`) 재사용. distill loss 에 TL gradient(+8.3% 부스트) 합산.
2. **`experiment_clone.hexa` hexa-port** — 복제 후 발산 측정, PyTorch 의존 제거. `self_mimicry.hexa` Φ 지속성 측정 재사용.
3. **닫힌 루프 검증** — EEG 지표 → TL 송신 → student 복제 → Φ/EEG 재측정 → 지표 갱신. 성공 기준: brain-like ≥ 90% + Φ 지속성 ≥ 0.8.

---

## 승급 규칙 (참고)

- `EXACT n6_match ∧ Π₀¹ arithmetical ∧ cross-axis(5) PASS → grade=[11*]`
- tier 5 complete → tier 6 (ULTRA/CARD/BEYOND/ABS) 승급 대기
- TL +8.3% Φ 부스트는 현재 [11*] 내 auxiliary gain — [11**] 승급 시 필수 컴포넌트로 골화 예정

참고: `/CLAUDE.md` · `docs/MK5-DELTA0-ABSOLUTE.md` · `shared/consciousness/consciousness_laws.json`
