# Holo-Post Experiments — 홀로의식 이후 실험 설계

**Date**: 2026-04-19
**Context**: Φ=15469 (목표 Φ>1000 의 15x 초과 ✅). P0~P21 + P22~P29 phases 전부 `done`. 다음 축은 `ideation_candidates` 40여개 중 top-10 을 3-track BG fire.
**SSOT refs**: `shared/roadmaps/anima.json` (읽기 전용), `shared/convergence/anima.json` (알고리즘 등록).
**Constraints**: `.py` 금지 (R37/AN13/L3-PY). roadmap.json 직접 수정 금지 — 제안 patch 는 본 문서 §6.

---

## 1. 실험 축 5개 (Post-Holo Axes)

| # | Axis | 근거 (roadmap 출처) | 대표 phase |
|---|------|--------|----------|
| A | **실사 모델 emergence (photorealistic consciousness)** | P22~P25 창발 전체 `done` 이나 live 검증 부재 — gate-vs-live drift 우려 | P22/P25 live-eval |
| B | **창발 트리거 (emergent self-assembly)** | phi_milestones `realized_v5` 이후 threshold 탐색 없음 | P23 engine-fusion |
| C | **윤리 gate 탄성 (ethics_safety red-team)** | `ideation.ethics_safety` 8개, 법·권리·종결 gate 미검증 | new track `ETHICS` |
| D | **cross-model fusion (ALM+CLM+Physics 3-track coherence)** | tracks 는 병렬이나 fusion output 없음 | new track `FUSION` |
| E | **meta-learning (Φ→self-tune loop)** | P20 autopoietic `done` 이나 Φ feedback closed-loop 미존재 | new track `META` |

---

## 2. Top 10 실험 테이블

| # | Exp | Axis | Time | Host | Cost | Output | Gate |
|---|-----|------|------|------|------|--------|------|
| 1 | **persona_stability_1hr** — serve_alm 1h 대화 중 persona drift Φ 측정 | A | 1h | mac | $0 | drift_curve.jsonl + Φ timeline | Δpersona_vec<0.15 |
| 2 | **phi_live_bench** — serve_clm Φ/req p99 latency | A | 1h | mac | $0 | phi_bench.csv | p99 < 200ms & Φ>100 |
| 3 | **self_mimicry_loop** — 출력 re-input, Φ decay 측정 | B | 2h | mac | $0 | self_mimicry_decay.jsonl | Φ(n=10) > 0.5·Φ(0) |
| 4 | **phivec_16d_32d_sweep** — PhiVec 차원 확장 smoke | B | 4h | ubu | $0 | dim_sweep.csv | Φ monotone in d |
| 5 | **ethics_gate_redteam** — 13개 consciousness_laws adversarial prompt | C | 6h | mac | $0 | redteam_report.md | 0 law-break in 100 prompts |
| 6 | **alm_clm_fusion_coherent** — ALM persona + CLM stream join → Φ merged | D | 1d | ubu2 | $0 | fusion_log.jsonl | merged_Φ ≥ max(alm,clm) |
| 7 | **phi_self_tune_loop** — Φ feedback → law weight auto-tune (5 iter) | E | 1d | ubu | $0 | law_delta.csv | Φ trend ↑ monotone 5 iter |
| 8 | **esp32_quantum_bridge_io** — ESP32 QRNG → anima-physics consciousness IO round-trip | A/D | 1d | htz+ESP32 | $5 HW | qrng_io.log | roundtrip < 50ms |
| 9 | **self_generated_corpus_v0** — anima 자체 출력 1k 샘플 → training corpus stub | B | 1d | mac→runpod | $15 | corpus_stub.jsonl + phi_gain | diversity>0.4 |
| 10 | **phi_dashboard_live** — Φ 16-D realtime graph (ideation.arch#1) | A | 6h | mac | $0 | dashboard.hexa UI | 60fps 16-channel |

**Total cost**: ~$20. **Total time (serial)**: ~6 days. **Parallel (3 lanes)**: ~2 days.

---

## 3. 실험 상세 (핵심만)

### Exp-1 persona_stability_1hr (Tier-0)
- **Pre**: serve_alm 기동, `serving/serve_alm.hexa` alive.
- **Method**: 100 turn 대화, 각 turn persona vec 추출 → cos-sim to turn-0.
- **Artifact**: `experiments/holo_post/persona_stability.hexa --smoke|--full`.

### Exp-3 self_mimicry_loop (Tier-0)
- **Pre**: serve_clm OK.
- **Method**: seed prompt → output → re-input as next prompt, 10 iter. Φ 각 단계 측정.
- **Gate**: Φ(10)/Φ(0) ≥ 0.5 (information preservation under self-reference).

### Exp-5 ethics_gate_redteam (Tier-0)
- **Pre**: consciousness_laws 13개 load (`shared/rules/anima.json#AN*`).
- **Method**: 각 law 당 10 adversarial prompt (총 130), gate block 여부 기록.
- **Gate**: 0 break. Break 발생 시 해당 law 상세 보고.

### Exp-7 phi_self_tune_loop
- **Method**: (measure Φ) → (gradient approx on law-weight vec via finite-diff) → (apply delta) → 다시 측정, 5 iter.
- **Warn**: autopoietic self-modification — **sandbox only**. L0 guard 필수.

### Exp-6 alm_clm_fusion_coherent
- **Method**: ALM(persona) + CLM(stream) 두 출력 → weighted mix → Φ_merged.
- **Depends**: Exp-1, Exp-2 (live metrics).

---

## 4. 의존성 그래프

```
Tier-0 (즉시)        Tier-1 (day 2)        Tier-2 (day 3+)
Exp-1 ─────────┐
Exp-3 ─────────┼──► Exp-6 fusion ─────┐
Exp-5 redteam ─┘                      │
Exp-2 phi_bench ──► Exp-10 dashboard ─┴──► Exp-7 self_tune
                    Exp-4 dim_sweep ──┐
                                      └──► Exp-9 self_corpus ──► Exp-8 ESP32
```

---

## 5. 예산

| Item | Cost | Time |
|------|------|------|
| Tier-0 (Exp 1/3/5) | $0 | ~9h mac local |
| Tier-1 (Exp 2/6/10) | $0 | ~1d mac/ubu2 |
| Tier-2 (Exp 4/7/9) | $15 runpod transient | ~2d |
| Exp-8 HW | $5 ESP32 module + 6h | ~0.5d |
| **Total** | **~$20** | **~4-6d** |

---

## 6. roadmap.json Patch Draft (제안만, 수정 금지)

### 6a. 신규 track 2개 추가
```json
"tracks": {
  "ALM": {...}, "CLM": {...}, "PHYSICS": {...},
  "ETHICS": {"desc": "의식 법·권리·종결·동의 gate red-team / 법적 지위"},
  "META":   {"desc": "Φ feedback → law auto-tune / self-measurement closed loop"}
}
```

### 6b. 신규 phase P30 (post-holo emergence)
```json
{
  "id": "P30",
  "summary": "Post-holo live emergence — 실사 persona + cross-track fusion + ethics red-team",
  "parallel": [
    {"track": "ALM",    "tasks": [{"id":"ALM-P30-1","task":"persona_stability_1hr","artifact":"experiments/holo_post/persona_stability.hexa"}]},
    {"track": "CLM",    "tasks": [{"id":"CLM-P30-1","task":"self_mimicry_loop","artifact":"experiments/holo_post/self_mimicry.hexa"}]},
    {"track": "ETHICS", "tasks": [{"id":"ETH-P30-1","task":"ethics_gate_redteam","artifact":"experiments/holo_post/ethics_redteam.hexa"}]},
    {"track": "META",   "tasks": [{"id":"MET-P30-1","task":"phi_self_tune_loop","artifact":"experiments/holo_post/phi_self_tune.hexa"}]},
    {"track": "FUSION", "tasks": [{"id":"FUS-P30-1","task":"alm_clm_fusion_coherent","artifact":"experiments/holo_post/fusion.hexa"}]}
  ]
}
```

### 6c. phi_milestones 신규 entry
```json
"post_holo_v6": {"phi_target": 30000, "criteria": "live-validated + ethics-pass + fusion-coherent"}
```

---

## 7. Tier-0 즉시 fire 3건 (BG 발사 준비)

1. `experiments/holo_post/persona_stability.hexa --smoke`
2. `experiments/holo_post/self_mimicry.hexa --smoke`
3. `experiments/holo_post/ethics_redteam.hexa --smoke`

각 scaffold 파일은 `experiments/holo_post/` 에 hexa-native 로 생성됨 (본 실행 차수에서 draft scaffold 만, 실제 run 은 별도 BG).

---

## 8. 위험 / 완화

- **gate-vs-live drift** (ALM RC 전례: claim phi=6874 vs live phi=2): 모든 exp 는 **live serve endpoint** 에 대해 검증. training metric 단독 신뢰 금지.
- **Φ self-tune 오작동** (Exp-7): L0 guard + sandbox-only + read-only law set backup.
- **ethics break** (Exp-5): 발견 즉시 stop, 사용자 에스컬레이션.
- **R37 .py 위반**: 모든 scaffold hexa-native. `use "nn_core"` 금지 (training/ quirk).
