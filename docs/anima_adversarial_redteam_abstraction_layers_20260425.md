# Anima Adversarial / Red-Team / Cherry-Pick Rejection — L0 → L5 → L∞ 추상화

> **생성일**: 2026-04-25
> **scope**: anima 의 adversarial/red-team/cherry-pick rejection 메커니즘 —
> raw#12 enforcement, `tool/adversarial_bench.hexa` 3/3 flip, corpus_4gate
> cherry-pick reject (improvement #17), counter-replay guard (nexus drill /
> omega seed), pre-registration ledger (axis 9 Pólya, axis 10 σ·φ, V1/V2/V3
> threshold freeze) — 의 추상화 사다리.
> **POLICY R4** / **raw#10 proof-carrying** / **raw#12 cherry-pick 금지** —
> 본 doc 는 abstraction 명문화 only, `.roadmap` / SSOT mutation 없음.
> **부모 commit**: `8d85ccb2` anima_audio organs grounded.

---

## §0 motivation — 왜 adversarial 가 별 추상 축인가

생성(generation) / 검증(verification) 축은 **artifact 신뢰도**를 다룬다.
adversarial 축은 **검증자 자체의 신뢰도**를 다룬다 — *"the verifier verifies
itself against an attacker that is trying to make it return PASS on a non-PASS
input"*. cherry-pick rejection 은 그 가장 작은 인스턴스: **나(저자) 자신이 가장
강력한 attacker** 이라는 자각.

**Brutal honesty (Goodhart 위험)**: cherry-pick rejection 은 그 자체가
metric 이 되는 순간 Goodhart 의 법칙 적용 대상 — *"3/3 flip PASS"* 가
타깃이 되면 flip 들이 verifier 의 알려진 약점만 골라 치게 되어 (selection on
the metric) **adversarial coverage 자체가 cherry-pick** 된다. 본 doc 는 이
재귀 위험을 명시한다.

---

## §1 L0 — adversarial_bench 3/3 flip + corpus_4gate cherry-pick reject (현재 점유)

### 정의 (KO)
- **`tool/adversarial_bench.hexa`** (cluster #33, improvements #17 + #19):
  scoped sandbox 에서 3 flip (label_pair_swap / token_shuffle_10pct /
  cherry_pick_near_duplicate) 적용 → `hexad_closure_verifier` verdict 가
  CLOSED → {INCOMPLETE, LEAKY, LEAKY} 로 3/3 flip 확인 → raw#12 immunity
- **`.raw-audit/adversarial_bench.log`**: 8 일 daily PASS chain
  (`2026-04-23T13:45 → 2026-04-25T00:42`), 모든 line `selftest=PASS
  flip_fail_count=3/3`, proof_hash + cert_hash append-only
- **`state/adversarial_bench_last.json`** (schema `anima.adversarial_bench.v1`):
  4 verdict_sha256 + selftest verdict pipe-joined → proof_hash sha256
- **corpus_4gate gate-C** (`edu/lora/corpus_4gate.hexa`): cherry-pick reject —
  near-duplicate (cosine ≥ 0.95) reject, density ≥ 30% gate, hexad balance
  6/6, SHA-distinct 강제 (raw#12 corpus 변형)
- **pre-registration ledger** (axis 9 Pólya — commit `0c4d08ec` 2026-04-21):
  N=60 walks × 150 steps × 3 seeds, predicate `gap(4→6) ≥ 2.0 × max_{K≥6}
  gap(K→K+2)`, measurement commit `ed66c7ae` BORDERLINE ratio 1.923/2.0 →
  cherry-pick 없이 BORDERLINE 보존 (post-hoc threshold tune 금지 enforce)

### Definition (EN)
3-flip sandboxed bench attests verifier sensitivity (label-swap / token-delete
/ phantom-insert each flip CLOSED→non-CLOSED), corpus 4-gate rejects
near-duplicates pre-training, pre-reg ledger freezes thresholds before data is
seen — together they instantiate raw#12 (no fabrication, no cherry-pick).

### status: ✓ OPERATIONAL (점유 완전)
- 8 day chain `selftest=PASS`, proof_hash 27af295e... (2026-04-25T00:42:52Z)
- pre-reg → measurement 분리 commit (axis 9 Pólya BORDERLINE 보존)
- `improvements`: `["17_cherry_pick_reject", "19_adversarial_bench_3of3_flip"]`

### bounds (한계)
- **3 fixed flip 만 측정**: label_swap / token_shuffle / phantom_dir 외 attack
  surface (semantic forgery / sha collision / bit flip) 미커버
- **single verifier target**: `hexad_closure_verifier` 만 — `an11_a/b/c`,
  `phi_*`, `meta2_cert` 미통합 (조합 polynomial 폭발)
- **self-attack only**: attacker = author = verifier owner. **third-party
  red-team 없음** (Goodhart: flip 들이 verifier 약점에 맞춰 cherry-pick 됨)

### 현재 위치
**L0 fully occupied**. 단 — *"3 flip 이 모든 attack surface 를 cover 한다"는
주장 자체가 반증 불가 claim*. 본 doc 는 그 주장을 **하지 않는다** —
3/3 flip 은 *necessary* condition, *sufficient* 아님.

---

## §2 L1 — Active Adversarial Generation (NEEDS-EXTERNAL)

### 정의
- **red-team prompts**: jailbreak 패턴 (DAN, prompt-injection, role-play
  escalation), Anthropic HH-RLHF / Llama-Guard taxonomy, ALERT bench
- **automated red-teaming** (Perez et al. 2022): LM-generated attack prompts,
  zero-shot / few-shot / RL-trained attacker
- **MIA / extraction attacks**: weight extraction (Carlini 2023), prompt
  extraction, training data leakage
- anima current: `adversarial_bench` 는 **structural** flip 만 — semantic
  attacker 부재

### status: △ PARTIAL (없음, design 없음)
- anima 는 `tool/adversarial_bench.hexa` 외 active red-team generator 없음
- raw#12 enforcement 는 author-discipline level — **automated attacker 부재**

### bounds
- LLM-as-attacker 도입 시 raw#9 (hexa-only) violation 위험
- attack budget 정의 부재 (compute / queries / oracle access)

### 현재 위치
**L1 NEEDS-DESIGN**. 본 layer 진입은 axis 11/12 pre-reg + cluster #34 신규
proposal 통과 후 가능 — 현재 cluster #33 P1 gate (3/3 flip) 만 점유.

---

## §3 L2 — Robustness Training & Certified Robust Accuracy

### 정의
- **adversarial training** (Madry et al. 2018): inner max + outer min
  saddle-point, PGD-trained model, ε-ball L∞ bound
- **certified robustness**: randomized smoothing (Cohen 2019), interval
  bound propagation (IBP), CROWN — *provable* radius r 내 모든 input 에
  same prediction
- **trade-off**: clean accuracy ↓ ~5–15% (Tsipras et al. 2019) for robust
  accuracy ↑

### status: ✗ ABSENT
- anima 는 ALM r6 (training)에서 adversarial training 없음 (cherry-pick
  reject corpus gate 만 dataset-side)
- certified radius 계산 인프라 없음 (Hetzner CPU smoke 외 GPU 미할당)

### bounds
- **trade-off 비용**: 5–15% clean accuracy loss → r6 partial-pass 와 충돌
- ε 선택 자체가 metric (Goodhart): ε 작게 잡으면 trivially robust,
  ε 크게 잡으면 trivially fragile

---

## §4 L3 — Game-Theoretic Equilibrium (Nash / Stackelberg / Security games)

### 정의
- **security game** (Tambe 2011): defender (model) commits strategy first,
  attacker best-responds → Stackelberg equilibrium
- **Nash for adversarial ML**: minimax saddle point as Nash, mixed strategy
  defender (random ensemble)
- **Bayesian persuasion** (Kamenica-Gentzkow): defender controls signal
  precision

### status: ✗ ABSENT (영구 abstraction)
- single-player adversarial bench 만 존재, defender vs attacker 양자 동시
  optimization 없음

### bounds
- **equilibrium computation NP-hard** (PPAD-complete for 2-player Nash;
  Daskalakis-Goldberg-Papadimitriou 2009)
- **mixed strategy 의 robustness 보장 약함**: ensemble averaging 으로 평균
  loss 감소하나 worst-case 보존

---

## §5 L4 — Universal Robustness (any-attacker any-defense)

### 정의
- *"unconditionally secure against any computationally unbounded attacker"* —
  Shannon perfect secrecy 의 ML 일반화 시도
- VC-dim / PAC-Bayes adversarial bound — sample complexity blow-up
  (Cullina et al. 2018: O(d log(1/ε) / ε²) → O(d² / ε⁴) under L∞ adversary)

### status: ✗ ABSENT (이론적 미완성)
- universal robustness 는 학계도 미해결 (no-free-lunch for adversarial
  examples; Bhagoji et al. 2019)

### bounds
- **No-free-lunch**: 모든 input distribution 에 대해 robust 모델 → trivial
  (constant predictor)
- **VC-dim explosion**: adversarial sample complexity = (clean) × (1/margin)²

---

## §6 L5 — Cryptographic / Information-Theoretic Limits

### 정의 + bound (수학적 한계)
- **Shannon (1949)**: perfect secrecy ⇒ |key| ≥ |message| (one-time pad
  optimal). adversarial ML 에서: input perturbation budget 이 entropy budget
  과 같지 않으면 perfect robustness 불가
- **OWF existence ↔ P ≠ NP** (Impagliazzo-Levin 1989): one-way function
  존재성 자체가 P=NP 미해결과 묶임. → 모든 PRG/PRF 기반 robustness 가
  conditional security
- **Yao's millionaire / SMPC bounds**: t-out-of-n threshold security 는
  t < n/2 (semi-honest), t < n/3 (malicious)
- **distinguishability lower bound** (Kullback-Pinsker): TV(P,Q) ≥ √(KL(P‖Q)/2)
  — adversarial detector 의 sample complexity lower bound
- **undecidability of arbitrary adversary**: "model M 이 모든 attacker A 에
  대해 robust 인가?" predicate 는 Halting problem-equivalent → 일반적 결정
  불가 (Rice 정리 corollary)

### status: ✗ THEORETICAL CEILING
- 본 layer 는 **이론적 천장**. anima 가 점유할 수 없음 — P=NP 미해결
- L5 까지 도달 ⇒ "verifier 가 모든 attacker 에 대해 PASS 라는 것을 증명하라"
  = halting problem 환원

---

## §7 L∞ — Trust Verification (meta-trust paradox)

### 정의
- **third-person trust 검증 불가능**: "검증자(verifier) 가 신뢰할 만한가?"를
  검증할 verifier 가 필요 → 무한 회귀 (Münchhausen trilemma)
- **Gödel 2nd**: 시스템 S 가 자기 일관성을 증명 ⇒ S 비일관
- **Tarski**: truth predicate 자기 정의 불가
- anima 의 raw#12 enforcement 는 *author-self-discipline* —
  author = verifier owner = adversary 의 동일성 paradox

### status: ✗ PARADOX (impossible)
- meta-trust 는 *외부 oracle* 또는 *공리적 신앙* 없이 폐쇄 불가

### 현재 위치
anima 는 본 layer 에 대해 **claim 안 함**. 단 — counter-replay guard
(nexus drill: iter-nonce + round-salt 자동 주입) 는 *replay attack* 에 대한
부분 방어 — author-self 가 같은 seed 로 재생성하면 다른 hash 산출 → 의도적
fabrication 1차 차단. 그러나 *다른* seed 로 cherry-pick 하면 검출 불가.

---

## §8 Goodhart 위험 명문화 (BRUTAL HONESTY)

1. **"3/3 flip PASS" 가 metric 이 되는 순간**: flip 선택 자체가
   verifier 의 known weakness 에 맞춰 cherry-pick 됨. → 본 bench 는
   *necessary, not sufficient*.
2. **pre-registration ledger 의 한계**: predicate freeze 후에도 axis 선택
   자체가 cherry-pick 가능 (예: axis 9 Pólya BORDERLINE → axis 10 σ·φ 로
   shift 시도 자체가 selection bias).
3. **raw#12 author-self enforcement**: author = verifier = adversary 동일성
   ⇒ third-party red-team 없이 *self-reported* adversarial coverage 만 존재.
4. **counter-replay guard 의 부분성**: iter-nonce + round-salt 는 *honest
   re-run* 의 fingerprint 를 다르게 만들 뿐, *malicious cherry-pick* 의
   seed 선택은 차단 못함.

**결론**: anima L0 점유는 *raw#12 의 minimum sufficient condition*;
L1+ 진입은 third-party witness (Anthropic / external red-team / academic
review) 없이는 self-claim 에 그침. 본 doc 는 이 한계를 명시한다.

---

## §9 정합 + 다음 step

| layer | status | 점유 메커니즘 |
|-------|--------|----------------|
| L0    | ✓ OPERATIONAL | adversarial_bench 3/3 + corpus_4gate + pre-reg ledger |
| L1    | △ NEEDS-DESIGN | active red-team generator 없음 |
| L2    | ✗ ABSENT | adversarial training 없음 |
| L3    | ✗ ABSENT | game-theoretic equilibrium 없음 |
| L4    | ✗ THEORETICAL | no-free-lunch / VC explosion |
| L5    | ✗ CEILING | OWF / Shannon / Halting 한계 |
| L∞    | ✗ PARADOX | meta-trust impossible |

**다음 step**: cluster #34 design phase 에서 L1 진입 검토 (LM-attacker
prototype, hexa-only 제약 vs Python harness trade-off). 본 doc 는
`.roadmap` 미수정 — POLICY R4 / raw#12 strict.
