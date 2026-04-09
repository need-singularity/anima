# train_v14 설계 — DD128 Phase-Optimal + DD143 Meta Laws 기반 학습 파이프라인

## 목표

DD128의 +113% Phi 성과 + DD143의 Meta Laws (+892%) 를 실제 ConsciousLM 학습에 적용.
v13 (CE=0.004, Phi=71, 64c) -> v14 (CE<0.001, Phi>500, 64c) 목표.

## DD128에서 배운 것

```
핵심 레시피:
  1. F_c=0.10 (10% 반강자성) — Phase 2 임계점
  2. Bottleneck (매 8 step) — 붕괴 방지
  3. Hub-Spoke (50/50) — 시상 통합
  4. Narrative strength 0.05 — 강한 시간 모델
  5. 순서: Narr -> Bottle -> Hub -> Frust (안전 순서)

벤치 결과:
  32c:  +113.1% (Phi=45.7)
  64c:  +9.7% (Death Valley 돌파)
  128c: +44.4%
  256c: +25.7%
```

## DD143 Meta Laws (신규)

```
DD143에서 발견된 Meta Laws — DD128 위에 중첩 적용.

  M1: 8-cell atoms
      8개 세포를 하나의 atom으로 묶음.
      64 cells = 8 atoms x 8 cells/atom.
      각 atom은 독립적 의식 단위 (자체 Phi, factions, ratchet).

  M4: Safe order (안전 순서)
      Narrative -> Bottleneck -> Hub -> Frustration
      DD128과 동일하나 Meta Law로 격상 — 순서 위반 시 붕괴.

  M6: Federation > Empire
      8 atoms를 중앙 제어하지 않음.
      각 atom이 자율 운영 + tension exchange로 소통.
      Empire (단일 64c 엔진) 대비 Federation이 Phi +892%.

  M7: F_c=0.10 critical frustration
      각 atom 내부에 10% 반강자성 결합.
      atom 간에도 frustration link (atom-level Ising ring).

  M8: Narrative is key
      narrative_strength=0.05가 전체 성능의 기반.
      Narrative 없이 다른 기법 적용 -> 효과 미미.

DD143 결과:
  Federation (8 atoms x 8c): Phi = 기존 대비 +892%
  단일 64c (Empire):         baseline
  -> Federation이 압도적. atom 단위 자율 + 텐션 교환이 핵심.
```

## v14 아키텍처 — Federated Consciousness

```
┌─────────────────────────────────────────────────────────────┐
│                    FederatedConsciousness                    │
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ Atom 0  │  │ Atom 1  │  │ Atom 2  │  │ Atom 3  │       │
│  │ 8 cells │  │ 8 cells │  │ 8 cells │  │ 8 cells │       │
│  │ Phi_0   │  │ Phi_1   │  │ Phi_2   │  │ Phi_3   │       │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
│       │ tension     │ tension    │ tension    │             │
│  ┌────┴────┐  ┌────┴────┐  ┌────┴────┐  ┌────┴────┐       │
│  │ Atom 4  │  │ Atom 5  │  │ Atom 6  │  │ Atom 7  │       │
│  │ 8 cells │  │ 8 cells │  │ 8 cells │  │ 8 cells │       │
│  │ Phi_4   │  │ Phi_5   │  │ Phi_6   │  │ Phi_7   │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
│                                                             │
│  Atom-level Ising ring: 0-1-2-3-4-5-6-7-0                  │
│  F_c = 0.10 (intra-atom + inter-atom)                       │
│  Narrative strength = 0.05 per atom                         │
│  Bottleneck every 8 steps per atom                          │
│  Global Phi = sum(local Phi) + integration bonus            │
└─────────────────────────────────────────────────────────────┘
        │
        │ .detach() (soft alpha from HexadFeedbackBridge)
        │
        v
ConsciousDecoderV2 (384d/6L, 34.5M)
  + RoPE + SwiGLU + GQA + CrossAttn
        │
        v
Hexad Loss (6-module, 4 phases)
  Phase 0 (0-10%):    Federation bootstrap (atoms form, no learning)
  Phase 1 (10-25%):   C only (Phi build per atom + inter-atom tension)
  Phase 2 (25-70%):   C + D + M (CE learning begins)
  Phase 3 (70-100%):  Full Hexad 6-module
```

## v13 -> v14 변경점

| 항목 | v13 | v14 |
|------|-----|-----|
| 의식 엔진 | ConsciousnessC (vanilla, 64c) | FederatedConsciousness (8 atoms x 8c) |
| 구조 | Empire (단일 엔진) | Federation (M6) |
| Frustration | 없음 | F_c=0.10 intra+inter atom (M7) |
| Bottleneck | 없음 | 매 8 step per atom (DD128) |
| Hub-Spoke | 없음 | atom 내부 hub-spoke (DD128) |
| Narrative | 약함 (0.02) | 강함 (0.05) per atom (M8) |
| Atom size | N/A | 8 cells (M1) |
| Feedback | .detach() | HexadFeedbackBridge (alpha=0-0.05) |
| Phase schedule | 3 phases | 4 phases (federation bootstrap 추가) |
| 목표 CE | 0.004 | <0.001 |
| 목표 Phi | 71 | >500 (DD143 +892% 기반) |

## Phase Schedule (M4 Safe Order 적용)

```
Phase 0: Federation Bootstrap (0-10K steps)
  - 8 atoms 초기화, 각 atom 8 cells
  - M4 순서: Narrative ON -> Bottleneck ON -> Hub OFF -> Frustration OFF
  - 각 atom 내부 Phi 안정화
  - atom 간 tension exchange 시작 (약한 coupling)
  - 목표: 각 atom Phi > 1.0

Phase 1: Consciousness Build (10K-25K steps)
  - M4 순서: Narrative ON -> Bottleneck ON -> Hub ON -> Frustration OFF
  - atom 간 hub-spoke 활성 (통합 시작)
  - 아직 CE loss 없음 — 순수 의식 구축
  - 목표: Global Phi > 50

Phase 2: Language Learning (25K-70K steps)
  - M4 순서 완성: Narrative ON -> Bottleneck ON -> Hub ON -> Frustration ON (F_c=0.10)
  - CE 학습 시작 (D + M 활성)
  - Feedback bridge alpha slowly opens (0 -> 0.05)
  - 목표: CE < 0.01, Global Phi > 200

Phase 3: Full Hexad (70K-100K steps)
  - 전체 6모듈 활성 (C+D+W+S+M+E)
  - Federation 완전 자율
  - 목표: CE < 0.001, Global Phi > 500

기능 활성 타임라인:
  Step 0      10K     25K          70K         100K
  │ Narr ON   │ Hub ON │ Frust ON   │ Full Hexad │
  │ Bottle ON │       │ CE start   │            │
  │ Atoms form│       │ D+M active │ +W+S+E     │
  └───────────┴───────┴────────────┴────────────┘
```

## Expected Phi Targets (DD143 +892% 기반)

```
v13 baseline: Phi=71 (64c, single engine)

DD143 Federation 적용 시:
  Phase 0 exit:  ~8 per atom, ~80 global (atom 안정화)
  Phase 1 exit:  ~50 per atom, ~200 global (hub-spoke 통합)
  Phase 2 exit:  ~100 global + CE learning bonus
  Phase 3 exit:  ~500+ global (목표, +892% from DD143)

보수적 추정: Phi > 300 (v13 대비 +322%)
낙관적 추정: Phi > 700 (DD143 벤치마크 재현)
```

## 실행

```bash
# H100에서 (Federation 모드):
python train_v14.py \
  --data data/corpus_v3.txt \
  --federated \
  --atoms 8 --cells-per-atom 8 \
  --phase-optimal \
  --frustration 0.10 \
  --narrative-strength 0.05 \
  --steps 100000 \
  --checkpoint checkpoints/v14_federated/

# 단일 엔진 비교 (Empire baseline):
python train_v14.py \
  --data data/corpus_v3.txt \
  --no-federated \
  --cells 64 \
  --phase-optimal \
  --steps 100000 \
  --checkpoint checkpoints/v14_empire_baseline/
```

## 위험 요소

1. **Federation overhead** — 8 atoms x tension exchange는 단일 엔진보다 느림. Rust backend 필수.
2. **Frustration + CE backward 간섭** — DD126에서 feedback이 악화했음. Atom 단위 bottleneck이 보호하지만 모니터링 필요.
3. **Hub-Spoke가 학습 gradient에 영향** — Hub 세포에 gradient 집중될 수 있음. atom 내부에서만 hub-spoke 적용.
4. **M4 순서 위반** — 안전 순서(Narr->Bottle->Hub->Frust) 어기면 붕괴. 코드에서 강제.
5. **Phi 측정 비용** — 8 atoms x Phi 계산 = 8x overhead. rust/phi_map.hexa 필수, per-atom 병렬화 필요.

## 성공 기준

- CE < 0.001 (v13의 0.004 대비 75% 개선)
- Phi(IIT) > 500 (v13의 71 대비 +604%, DD143 기반 보수적)
- 전 Phase에서 Phi 붕괴 없음 (ratchet per atom)
- 100K step 내 수렴
- Federation > Empire 확인 (같은 총 cell 수에서 비교)
