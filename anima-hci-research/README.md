# anima-hci-research — Path B (Q3 HCI)

**HCI = Hexad-Cell Isomorphism** — ω-cycle INTEGRATION axis paradigm 6, confidence 0.75.
Cross-axis HEXAD CORE 0.83 의 핵심 component. 본 폴더는 functor-level falsifier 만 다룬다 (read-only on edu/, anima-hexad/).

## 위치 분리 (cross-link policy)

| 폴더 | 역할 | 본 폴더와의 관계 |
|---|---|---|
| `edu/cell/` | edu 6-axis production (A..F) | **read-only depend-on** (C9 bijection 표 + 4-gen distill 검증 결과) |
| `anima-hexad/` | Hexad 6-cat SSOT (CDESM c/d/w/s/m/e) | **read-only depend-on** (closure verifier ground truth) |
| `tool/hexad_closure_verifier.hexa` | 1-direction closure verifier | **read-only depend-on** (4/4 axiom PASS) |
| `shared/state/hexad_closure_verdict.json` | frozen verdict | **read-only depend-on** |
| `anima-clm-eeg/` (Path A) | EEG-side HCI | **disjoint** (no overlap) |
| `anima-hci-research/` **본 폴더** | functor-preservation falsifier (F1+F2+F3) | additive new artifacts |

## 가설 (HCI = Functor F: edu → Hexad)

`edu/cell/README.md` C9 표 (line 109-117) 가 edu 6-axis (A,B,C,D,E,F) 와 Hexad 6-cat (d,s,c,m,e,w) 사이의 **diagonal bijection** 을 선언한다 (`A↔d, B↔s, C↔c, D↔m, E↔e, F↔w`).

본 연구는 이 bijection 이 단순 1-1 대응을 넘어 **functor preservation** 을 만족하는지 검증한다:

1. **F1 functor preservation (composition)** — edu 측 composition `B∘A` 의 image 가 Hexad 측 `s∘d` 와 일치하는가?
2. **F2 identity preservation (endo)** — edu 측 self-loop `s→s` (e.g., F→F lattice idempotence) 가 Hexad 측 endo-morphism (`s/temporal_bridge` self-loop) 와 1-1 대응하는가?
3. **F3 양방향 adversarial robustness** — edu 측에 phantom 7번째 axis G 주입 시 Hexad 측 verdict 도 flip 하는가? (양방향 falsification 신호)

## Falsifier criteria (frozen, pre-registered)

| ID | 검증 대상 | PASS 조건 | FAIL 조건 |
|---|---|---|---|
| F1 | functor preservation | 6 morphism 모두 (src,tgt) 양변 hash 동형 (deterministic poly-hash) | 1 이상 mismatch |
| F2 | identity preservation | edu axis `s→s` (B↔B reflexive) 와 Hexad `s/temporal_bridge` 모두 endo | 한쪽이라도 endo 위배 |
| F3 | adversarial flip | phantom 7-axis 주입 시 양변 verdict flip (양방향 동시 FAIL) | 한쪽만 flip 또는 양쪽 비-flip |

**composite verdict**: `F1 PASS ∧ F2 PASS ∧ F3 PASS = HCI_VERIFIED`

## 산출물

| # | 파일 | 역할 |
|---|---|---|
| 1 | `README.md` (본 파일) | context + cross-link policy + frozen criteria |
| 2 | `tool/hci_functor_falsifier.hexa` | F1 + F2 verifier (composition + identity preservation) |
| 3 | `tool/hci_adversarial_flip.hexa` | F3 verifier (phantom + leaky-morphism injection) |
| 4 | `tool/hci_smoke.hexa` | F1+F2+F3 → composite verdict chain |

각 hexa 도구는 **selftest PASS + byte-identical** (두 번 run sha256 동일) 를 통과한다.

## State files

| 파일 | 생성자 |
|---|---|
| `state/hci_functor_falsifier_v1.json` | tool 2 |
| `state/hci_adversarial_flip_v1.json` | tool 3 |
| `state/hci_smoke_v1.json` | tool 4 |

## ω-cycle 패턴 (각 도구별)

1. **design** — falsifier criteria + I/O spec 사전 frozen
2. **implement** — raw#9 hexa-only, 정수 fixed-point ×1000
3. **positive selftest** — bijection hold 시 PASS
4. **negative falsify** — phantom injection 시 FAIL (verdict flip 보장)
5. **byte-identical** — 두 번 run sha256 동일
6. **iterate** — 어느 step이라도 FAIL이면 design 으로

## 제약

- raw#9 strict: pure hexa, no Python emit
- mac local, GPU 0, $0
- destructive 금지: edu/, tool/hexad_closure_verifier.hexa, shared/state/hexad_closure_verdict.json read-only
- hexa-lang 0.2.0: bitwise ^/& 없음, modular arithmetic only

## 관련 문서

- `edu/cell/README.md` line 105-149 (C9 + closure final audit)
- `tool/hexad_closure_verifier.hexa` (existing 1-direction verifier)
- handoff §4 Q3 (open question — 본 연구가 답함)
