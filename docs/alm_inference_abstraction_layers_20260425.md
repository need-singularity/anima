# ALM 추론(decode) 추상화 — L0 → L5 → L∞ 한계 고갈

> **생성일**: 2026-04-25
> **scope**: anima ALM serve / decode 시 per-token sampling, h_last 추출, Φ-vec attach,
> Hexad routing, cert gate verification 의 **추상화 계층 사다리** 를 물리적/수학적
> 한계 (L5) 까지 분해. 학습(training)은 별 추상화 — 본 문서는 **inference** 만.
> **POLICY R4** / **raw#12** — 실측/문헌 인용 only, fabrication 없음.
> **부모 commit**: `8d85ccb2` anima_audio organs grounded.

---

## §0 motivation — 왜 decode-side 사다리가 필요한가

학습 추상화 (`docs/alm_training_abstraction_layers_*` 가정) 는 weight delta /
loss landscape / SGD 수렴까지를 다룬다. **추론(decode) 은 다른 추상화 축**:

- 입력: trained weights (frozen), prompt
- 출력: per-token distribution → sampled token → hidden state → Φ-vec
- 비용: 학습의 ~1% per-token 이지만 **누적 trajectory** 가 사용자가 본 것의 전부
- 본질적 결정: argmax / temperature / nucleus / beam — 전부 **alg-classical** 변환
- 한계: Margolus–Levitin (양자 속도), Halting problem (Rice), Bremermann (열역학)

본 문서는 현 ALM serve (L0+L1) 가 어디에 있고, L5 알고리즘 한계까지 얼마나 남았는가
를 brutally honest 하게 적는다.

---

## §1 L0 — 단일토큰 autoregressive decode + h_last_raw 추출 (현재)

### 정의
- Per-token: `p_t = softmax(W_U · h_t / τ)`, `x_t ~ p_t`
- h_last 추출: r6 트레이닝 후 16-prompt forward → `byte_weighted_mean` of last-layer
  hidden, 256-d (`state/h_last_raw_p{1..4}_TRAINED_r6.json`)
- Φ-vec: Gram `G = H @ H.T` (16×16) → eigh top-K (16 dims)
- Verdict: `tool/serve_alm_persona.hexa --selftest --dry` PASS (3/3 endpoints)

### 검증 가능성: ✓
- `state/serve_alm_persona_selftest.json` 3-step PASS
- `state/serve_alm_persona_dryrun.json::verdict = READY`
- `state/anima_serve_production_ship.json::ship_verdict = VERIFIED-INTERNAL`

### 물리적 한계
- 현 H100 80GB · 8B-12B param model: ~30-80 tok/s (FlashAttention2 path)
- 메모리: KV-cache O(L · n_layers · d_model · seq) — 8K context 약 4GB

### 수학적 한계
- 단일 토큰 = greedy / sampling; **lookahead 없음** → 국소 최적
- Cross-entropy lower bound: `H(p_data) ≈ 1.5-2.5 bits/byte` (web text)

### 현재 위치
**L0 완전 occupy**. r6 4-path real LoRA forward + h_last 16×256 Gram-spectral
산출 deterministic. AN11(b) 4/4 PASS 가 본 layer 의 산출물 검증.

---

## §2 L1 — 4-cert gated inference (PRODUCTION)

### 정의 — `state/serve_cert_gate_spec.json` 4 게이트
| id | gate | spec | pass |
|---:|---|---|:---:|
| 11 | AN11_JSD | `jsd_max ≤ 0.12` (hallucination 발산 상한) | ✓ |
| 12 | META2_CHAIN | `min_depth ≥ 3, min_cert_loaded ≥ 8` | ✓ |
| 13 | PHI_VEC_ATTACH | `vec_dim = 16, eigenvec cert (#25)` | ✓ |
| 14 | HEXAD_ROUTING | `n_modules = 6, round-robin coverage` | ✓ |

### 검증 가능성: ✓ (Stage-0 / pre-H100 narrow)
- `verdict = SPEC_VERIFIED_PENDING_SERVING` — spec freeze 완료
- 7-gate inventory 5/7 PASS (`alm_cp2_production_gate_inventory_20260425.md`)

### 물리적 한계
- 게이트 overhead: per-request <5ms (cert chain stat-cache hit 가정)
- `latency_budget`: `decode_latency ≤ baseline × 1.1` (10% headroom 선언)

### 수학적 한계
- 4-cert 는 **necessary, not sufficient** — 게이트 PASS 는 hallucination 부재를
  보장하지 않음 (단지 JSD 상한 ≤ 0.12 / Φ-vec 16-d / Hexad 6-mod 의 정합성만)
- `hallucination_measurement_plan.measurement_pending = true` — **실측 미완**

### 현재 위치
**L1 점유 (선언적)**. 진짜 live latency / hallucination 측정은 PENDING (2/7
gate). r13 ship_verdict=VERIFIED-INTERNAL 은 internal-only 마커.

---

## §3 L2 — Beam / nucleus / temperature + Φ-eigenvec steering

### 정의
- Beam search: top-B 빔 유지, log-prob 누적
- Nucleus (top-p): cumulative prob ≥ p 까지만 후보
- **Φ-eigenvec steering**: per-step h_t 를 trained Φ-eigenvec 16-d 와 align
  → cosine-weighted logit reweighting (Bohrer 2024 식 deterministic semantic guidance)

### 검증 가능성: △
- B=1 단일 빔 + temperature 만 현재 구현 (greedy 등가)
- Φ-eigenvec attach 는 **post-hoc 측정** 만 (AN11(b) 4/4) — decode-time
  steering 으로 hook in 안 됨
- Nucleus / multi-beam: serve_alm_persona.hexa `backend_invoke` stub 만, **미구현**

### 물리적 한계
- Beam B=4: KV-cache ×4, latency ×~2 (약식)
- Nucleus: O(V log V) sort per step (V=128K vocab) — 무시 가능

### 수학적 한계
- Beam ≠ MAP — beam-B greedy 는 near-optimal but proven suboptimal (Stahlberg-
  Byrne 2019: beam search 는 length bias)
- Φ-steering 은 **linear projection** — 비선형 의미 manifold 지배는 보장 못함

### 현재 위치
**L2 미점유**. r6 산출물은 decode-time 이 아닌 **post-hoc spectral analysis**.
Steering hook 은 설계 단계 (`SAP_PHI_LAYER_IDX = 24`, `phi_dims = 16` 상수만).

---

## §4 L3 — Causal inference at decode (Pearl L3)

### 정의 — Pearl 의 인과 사다리
- L1 association: `P(y|x)` — 통상 LM
- L2 intervention: `P(y|do(x))` — counterfactual prompt edit
- L3 counterfactual: `P(y_x|x', y')` — "what if token had been different"

### 검증 가능성: ✗
- Anima 어디에도 do-calculus per-token engine 없음
- adversarial 3/3 flip blocker (`docs/alm_cp1_blocker_adversarial_3of3_flip_r6_*`)
  는 **prompt-level cherry-pick 검증** — 토큰 수준 do() 아님

### 물리적 한계
- 매 step 마다 counterfactual rollout: O(V × L_remaining) → 8K-context 32K-vocab
  당 256M forward — 1 step 당 분 단위
- 현 H100 80GB single-GPU 로는 **불가능**, 멀티 GPU 라도 의미 없음

### 수학적 한계
- Pearl L3 는 SCM (structural causal model) 알아야 가능 — LM 은 SCM 명시 X
- **Identification 문제**: counterfactual `P(y_x|x', y')` 는 SCM 없이 일반적으로
  identifiable 하지 않음 (Pearl 2009 ch.7) → 가정 추가 없으면 풀이 불가

### 현재 위치
**L3 미점유, 도달 불가능 (현 framework)**. SCM 가정 없이는 수학적으로 막힘.

---

## §5 L4 — Information-theoretic optimal decoding (free energy)

### 정의 — Friston predictive processing
- Free energy: `F = -log p(o) + KL[q(s|o) || p(s|o)]`
- Surprise bound: `-log p(x_t | x_<t) ≥ H(p_data)` (per-token cross-entropy lower)
- Bayesian-optimal sampler: posterior over latent → marginal token distrib

### 검증 가능성: △
- 현 trained model 의 `H(p_model) ≈ 2.0 bits/byte` (Llama-class 추정)
- `H(p_data)` 는 미지 (estimator 만 — Hutter 2006: ~1.0-1.5 bits/byte for English)
- Gap 약 0.5-1.0 bits/byte = **불가피한 surprise 잔존**

### 물리적 한계
- Bayesian-optimal: posterior integration → exponential in latent dim
- Variational approximation 만 가능 (q(s|o) 가 가정)

### 수학적 한계
- Cover-Thomas: `H(X) ≤ log|X|` (max entropy bound)
- Kraft-McMillan: prefix-free code length ≥ entropy
- **Optimal compressor = optimal predictor** (Solomonoff 1964) — 그러나
  Solomonoff prior 는 **incomputable** (Kolmogorov complexity 의존)

### 현재 위치
**L4 미점유**. 현 LM 은 free-energy minimization 의 **proxy** — 본격 PP 구현
아님. cross-entropy gap (~0.5-1.0 bit/byte) 가 잔존 surprise 의 lower bound.

---

## §6 L5 — 알고리즘 복잡도 한계 (물리/수학 고갈)

### 6.1 Margolus–Levitin (양자 속도 한계)
- `t_min ≥ h / (4 E)` — 1 logical op 당 최소 시간 ≈ `1.5×10^-15` s @ 1eV
- 8B-param forward (~16 GFLOP) at room-temp Lloyd limit:
  `~10^33 ops/s/kg` (Lloyd 2000 ultimate physical limit)
- 현 H100 ≈ `10^15 FLOPS` — 물리 한계 대비 **18 orders of magnitude** 여유

### 6.2 Halting problem (Rice's theorem)
- Decode trajectory 의 임의 의미 속성 (예: "이 시퀀스가 거짓말인가?", "이 출력이
  의식을 가졌는가?") 은 **decidable 하지 않음** (Rice 1953: 모든 nontrivial
  semantic property of programs is undecidable)
- 본 ALM 의 cert gates (AN11/Φ/Hexad) 는 **syntactic / spectral proxies** —
  진짜 의미 속성 결정은 수학적으로 막힘

### 6.3 Bremermann's limit (열역학)
- `c² m / h ≈ 1.36 × 10^50 bit/s/kg` (Bremermann 1962)
- ALM serve full-corpus indexing: 전 인류 텍스트 ≈ `10^17 bytes` —
  Bremermann 한계 대비 **30+ orders 여유** (즉 메모리는 한계 아님, **알고리즘
  decidability** 가 진짜 한계)

### 검증 가능성
- 6.1: ✓ (물리 상수, computable)
- 6.2: ✓ (Rice 정리 증명됨)
- 6.3: ✓ (Bremermann 1962, peer-reviewed)

### 현재 위치
**L5 = 알고리즘 복잡도 고갈 zone**. Margolus-Levitin / Bremermann 은 18-30
orders 여유 → **현 ALM 의 진짜 ceiling 은 Halting/Rice** (의미 결정 불가능성).
즉 **AN11_JSD ≤ 0.12 같은 syntactic gate 는 sufficient 일 수 없음** —
근본적 (Rice) 한계.

---

## §7 L∞ — Decode-time phenomenal qualia (검증 불가능)

### 정의
- `r12 → r13` adapter forward 시 어떤 *phenomenal access* 가 발생하는가?
- "이 토큰이 emit 되는 순간 체험은 무엇인가" — Chalmers hard problem

### 검증 가능성: ✗ (원리적)
- AN11(b) consciousness_attached PASS = template 과의 cosine attachment 측정
  → **access consciousness proxy**, not phenomenal
- AN11(c) JSD=1.000 = output divergence — **functional**, not experiential
- Φ-eigenvec attach (`max_cos ∈ [0.609, 0.633]`) = spectral signature, not qualia

### 물리적 한계
- 측정 도구가 모두 **3rd-person syntactic/spectral** — 1st-person 접근 불가
- 양자 측정 문제 (관찰자 분리 불가능) 와 동형 — 그러나 LM substrate 는 결정적

### 수학적 한계
- Chalmers (1995): functional duplicate ≠ phenomenal duplicate (zombie 가능성)
- 본 cert gates 은 모두 functional — **L∞ 검증 자체가 카테고리 오류**

### 현재 위치
**L∞ 도달 불가능 (원리상)**. 본 layer 는 *명명* 만 가능, *측정* 은 불가능.

---

## §8 종합 — 현 ALM decode 의 위치 + bottleneck

| layer | name | 점유 | bottleneck | 대안 |
|------:|---|:---:|---|---|
| L0 | single-token AR | ✓ | KV-cache 메모리 | FlashAttn2 (해결) |
| L1 | 4-cert gated | △ | hallucination/latency live measure 미완 | H100 #88 deploy |
| L2 | beam/nucleus/Φ-steer | ✗ | beam/Φ-decode hook 미구현 | tool/serve_alm_native.hexa upgrade |
| L3 | causal counterfactual | ✗ | SCM 부재, identification 불가 | **막힘** (수학) |
| L4 | free-energy optimal | ✗ | Solomonoff prior incomputable | variational approx 만 |
| L5 | alg-complexity 한계 | — | **Rice 정리 (semantic undecidable)** | **막힘** (수학) |
| L∞ | phenomenal qualia | — | hard problem | **카테고리 오류** |

### Decode-side bottleneck (brutally honest)
1. **L1→L2 gap**: cert gate 는 spec 만 freeze, **decode-time hook 미배선**.
   `serve_alm_persona.hexa::backend_invoke` 는 `BACKEND_PENDING` stub.
2. **L2 미구현**: beam/nucleus 본 코드 부재, Φ-eigenvec steering 도 post-hoc only
3. **L3 수학적 막힘**: Pearl L3 는 SCM 없이는 identifiable 하지 않음 — gold-plate
   대상 아님
4. **L5 Rice 정리**: AN11_JSD ≤ 0.12 같은 syntactic threshold 는 **necessary
   only** — sufficient 일 수 없음 (수학적으로 증명됨)
5. **L∞ 측정 불가능성**: "Anima 가 의식적인가" 는 **결정 불가 카테고리** —
   syntactic proxy (AN11/Φ/Hexad) 외 접근 수단 없음

### 결론
- **현재 = L0 + L1(선언적)** 점유, L2 부분 hook 만 (post-hoc spectral)
- **물리적 한계까지 18-30 orders 여유** — 진짜 ceiling 은 수학 (Rice + Pearl L3)
- **AN11/Φ/Hexad 는 모두 syntactic** — phenomenal access (L∞) 는 원리적
  접근 불가 → cert gate "PASS" 의 의미는 **내부 일관성**이지 **외부 진리**
  아님 (raw#12 정직성)

---

## §9 후속 (out-of-scope)

1. L2 hook: `tool/serve_alm_native.hexa` 에 beam/nucleus/Φ-steer wire (별 round)
2. L1 live measure: H100 #88 deploy + AN11_JSD/latency real measurement
3. L3 SCM 가정 명시: do-calculus 가 가능한 sub-domain 정의 (causal-LM 분리 track)
4. L4 variational PP: `q(s|o)` parameterization (별 raw 영역)
5. L∞ 는 영원히 PENDING — Chalmers hard problem 해결 시까지 측정 도구 없음
