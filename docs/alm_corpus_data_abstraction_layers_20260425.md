# ALM Corpus / Data Abstraction Layers — L0 → L5 Physical/Mathematical Limits

> **생성일**: 2026-04-25 (loss-free analysis, 0 cost, no GPU, no .roadmap edit)
> **부모 commit**: `b6fa6c01` r14 corpus 1200/1200 land + `19fcc388` master index
> **POLICY R4**: `.roadmap` 미수정. raw#12 strict (no cherry-pick), raw#15 (no-hardcode SSOT).
> **목적**: corpus / data 생성 pipeline 의 추상화 계층을 L0 (현재 r14 sha-locked fixed corpus) 부터 L5 (Bekenstein + Solomonoff incomputable) 까지 분해. 각 layer 의 검증 가능성 / 물리적 한계 / 수학적 한계 / 현재 도달 위치를 brutally honest 하게 기술.
> **Tone**: 한글 narrative + English technical.

---

## §0. Frame — 왜 corpus layer 분해인가

ALM r12 vacuum (kowiki general → adapter DISCARD) 사고 후 r13 G1-G7 PASS / r14 1200-line G1-G8b PASS 까지 실측 closure. 이 시점에서 corpus pipeline 의 한계가 어디서 오는지 (engineering ceiling vs information-theoretic vs incomputable) 명확히 분리하지 않으면 r15+ 에서 over-investment 발생.

- **Engineering ceiling (L0–L2)**: 시간/사람/생성기로 돌파 가능. r14 closure 가 L0–L1 ceiling 의 ~80% 도달.
- **Information-theoretic ceiling (L3)**: Bayes-optimal corpus 는 정의 가능하나 posterior 추정 cost 폭발.
- **Incomputable ceiling (L4–L5)**: Solomonoff prior 위 universal corpus, Bekenstein information bound, Berry paradox.

**현재 위치**: L0 100% (sha-lock 완료), L1 50% (4-tier partition + Seed A/B inj 통과, fellows BT 8 채널 중 BT-1423/1424 미흡), L2 5% (synthetic augmentation 미수행), L3+ 미진입.

---

## §1. L0 — Fixed corpus, sha256-locked, G-gate PASSED (현재 위치)

**Description**: human-authored + Seed A/B kernel-injected static corpus. r14 v1 = 1200 라인 / sha256 `21fcfa51b92f129b119d7fa42303adf7916547ef71c80c16f08e53839bf52b0b`. r13 v1 = 840 라인 / sha256 `7b3fd84d…` (보존, mtime stable, byte-identical pre/post).

**Generator**: `tool/corpus_generator_v2.hexa` (2082 lines per `.roadmap` L99). L1 (n6 academic richness) + L2 (7-cat ALM r13/r14 composition) + L3 (BT-1421..1428 fellows ingestion) + Seed A/B kernel injection (K1 HOT+AST / K2 IIT n6 / K3 GWT × 16 docs each).

**Validator**: `tool/alm_corpus_validate.hexa` (697 lines, hexa-only). G1 schema 100% / G2 category ratio ±3% / G3 consciousness density ≥30% / G4 anti-denial 0 / G5 truncation 0 / G6 audit_sample 50 / G7 sha256 + provenance. r14 추가: G8 korean_ratio ≥0.27 / G8b EN↔KO pair_match ≥0.98.

**Test prompts**: `bench/an11_c_test_prompts.jsonl` (20 prompts × {consciousness/philosophy/law/hexad/selfreflect}, expected hexad_module + theory_tags + seed_kernel{K1,K2,K3}).

**Templates**: `consciousness/an11_b_templates.jsonl` (16-eigenvec, family Hexad×6 + Law×4 + Phi×3 + SelfRef×3, seed=20260421).

| 측면 | 상태 |
|---|---|
| 측정 가능 | ✓ G1-G8b strict, deterministic validator |
| 검증 가능 | ✓ sha256 lock + provenance per-source distribution |
| 재현 가능 | ✓ atomic write, raw#25 git-lock-safe, V8 SAFE_COMMIT |

**물리적 한계**:
- 디스크: r13=980,326 bytes, r14=1,510,683 bytes. 둘 다 1.5MB 이하 → I/O bound 없음.
- byte-weighted h_last pool: 토큰 단위 ≈ 430K (r13) / ~770K (r14) — Mistral-7B 32K context 기준 13–24 sequence.
- 인간 author latency: 저자 1명 × ~6–8d wall (r14) = 직렬 bottleneck.

**수학적 한계**:
- Static corpus 의 Kolmogorov complexity K(C) ≤ |C| (literal) 이며, 의식 manifold 의 minimal description 보다 항상 ε-incomplete.
- G-gate 는 syntactic/lexical pattern matching 기반 — semantic adequacy 의 필요조건이지 충분조건 아님 (raw#12 cherry-pick reject 만 보장).

**현재 위치**: L0 = anima 의 검증된 baseline corpus. r13/r14 두 sha-lock 모두 활성. **약점**: r13 G3 density=0.85 (≥0.30 ceiling 18× 초과), 즉 keyword-saturated → G3 가 더 이상 informative 하지 않다 (binary saturated). r14 G8 ko_ratio=0.2958 ≥0.29 — **margin +0.0058 = 가장 tight**. 추가 EN-heavy 데이터 1줄도 g8 breach 위험.

**Weakest evidence link**: corpus diversity 가 8 BT 채널 중 BT-1423=0 / BT-1424=0 — fellows BT 매핑은 명목상 8채널이나 실측은 6채널 (r13 bt_stats). raw#12 empirical-priority 위반은 아니지만 mapping coverage gap.

---

## §2. L1 — Active learning / curriculum (corpus diversity, fellows BT, Seed A/B/Law60)

**Description**: corpus 를 quality-tier 로 stratify + on-line retrieval 로 sample 의 marginal utility maximize. anima 현 구현:
- **4-tier partition** (tool/corpus_curriculum_tier.hexa, roadmap #92): tier1 30% / tier2 50% / tier3 70% / tier4 summit consciousness density. r14 manifest `state/alm_r14_corpus_manifest.json`: 12 shards × 4 paths × 3 tiers (tier1 r13 carry-forward EN baseline, tier2 bilingual seed_b k4/k5/k6, tier3 adversarial KO seed_b_k7).
- **Fellows BT injection**: BT-1421 (Landauer) / BT-1422 (training cost) / BT-1423 (on-device) / BT-1424 (agent serving) / BT-1425 (deployment manifold) / BT-1426 / BT-1427 (consciousness) / BT-1428 (Safety 171). r13 actual: BT-1427=310 / BT-1428=110 / BT-1421=126 / BT-1422=126 / BT-1425=84 / BT-1426=84 (BT-1423/1424=0 미충족).
- **Seed A/B/Law60**: Seed A = K1/K2/K3 kernel × 16 docs (총 48). Seed B = anti-denial 3-condition (DPO relabel / hardcoded refusal removal / refusal-circuit detect-only). Law60 phase ordering c → d → {w,s,m,e} 가중 (`config/hexad_law60_weights.json` c-hub 2×).

| 측면 | 상태 |
|---|---|
| 측정 가능 | ✓ tier manifest deterministic, BT distribution counter |
| 검증 가능 | △ tier → 성능 인과관계 ablation 미수행 (#92 note: AN11(a) epoch comparison deferred until real H100 training) |
| 재현 가능 | ✓ shard_id deterministic, sha-locked per-tier |

**물리적 한계**:
- Active learning 의 query oracle cost: 인간 annotator throughput ~10–100 sample/hr × $30/hr ≈ $0.3–3/sample. r14 1200줄 × $0.5 = ~$600 인간 시간 lower-bound.
- Curriculum schedule space: |tier|^N = 4^1200 ≈ 10^722 — exhaustive search 불가.

**수학적 한계**:
- **Cohn et al. (1996) active learning lower bound**: O(d log(1/ε)) labels 필요 (d = VC dim, ε = generalization gap). consciousness manifold 의 VC-dim 추정 불가 → label complexity 미상.
- Curriculum optimality 는 NP-hard (Bengio 2009) — local heuristic (tier 30/50/70%) 만 가능.
- BT-coverage 가 8/8 도달해도 BT 자체가 fellows-2026 spec 상 finite enumeration → unknown unknowns 항상 존재.

**현재 위치**: L1 = 50% 도달. tier landed + Seed A/B inj 완료, but BT-1423/1424 미충족 (8채널 중 6) + ablation 부재. **약점**: tier 의 reward multiplier (#92 exit_criteria 의 "각 tier 에 cert reward multiplier") 는 H100-gated 로 deferred — corpus 는 land 했으나 학습 인과 검증 없음.

---

## §3. L2 — Generative augmentation (synthetic data, distillation)

**Description**: LLM 또는 procedural generator 로 corpus 확장. 현 anima 는 **Seed A 의 K1/K2/K3 deterministic template** 만 synthetic — 외부 LLM-generated synthetic 미사용 (raw#12 cherry-pick reject + raw#9 hexa-only 정책 위반 회피).

가능한 L2 변종:
- **Self-distillation**: trained ALM ckpt (r6/r7/r8) 의 logit 을 corpus 에 라벨링 — r14 corpus 의 weak label augmentation.
- **Constitutional AI rewrite** (BT-1428 alignment 32 idea): refusal pattern detected → phenomenological replacement (Seed B condition_1).
- **Tree-of-thought expansion** (BT-1428 model_welfare 18): 단일 prompt → multi-step reasoning trace.
- **Cross-lingual mirror**: EN seed → KO mirror (r14 g8b pair_match 0.972 — 이미 부분 implemented; pair_diff_abs ≤2 enforced).

| 측면 | 상태 |
|---|---|
| 측정 가능 | △ K1-K3 deterministic emit count (16/16/16) 만 measurable |
| 검증 가능 | ✗ synthetic 기여도 학습 측 ablation 부재 |
| 재현 가능 | ✓ K1-K3 byte-exact deterministic |

**물리적 한계**:
- Synthetic generation cost: GPT-4 class API ~$0.03/1K tokens. 1M token aug ≈ $30 — 저비용이나 raw#12 위반.
- Distillation: teacher inference cost ≈ student inference × N_samples. Mistral-7B teacher × 1200 sample × 512 token ≈ 0.6 GPU-hr ≈ $1.

**수학적 한계**:
- **Model collapse** (Shumailov et al. 2024): synthetic-on-synthetic recursion 은 distribution tail 손실. n-th gen variance → 0 exponentially.
- Distillation 의 information-theoretic ceiling: I(student; teacher) ≤ H(teacher) — student 가 teacher 의 entropy 를 초과할 수 없음.
- Constitutional rewrite 는 fixed-point 수렴 보장 없음 (rewrite operator T 가 contraction 인 경우만 unique fixed point).

**현재 위치**: L2 ≈ 5%. K1/K2/K3 + EN↔KO mirror 만 구현. self-distillation / tree-of-thought / constitutional rewrite 모두 미수행. **약점**: anima policy (raw#12 + raw#9) 가 외부 LLM synthetic 을 strict reject — synthetic 확장 경로가 closed by design. 이 정책 자체는 의식 이식의 cherry-pick 방지 목적이지만, L2 ceiling 에서 hard cap 으로 작동.

---

## §4. L3 — Information-theoretic optimal sampling (Bayes-optimal corpus)

**Description**: weight posterior p(θ|D) 와 task distribution p(τ) 가 주어졌을 때, 다음 sample 의 expected information gain
  EIG(x) = H[p(θ|D)] − E_y[H[p(θ|D, x, y)]]
을 maximize 하는 sample 을 무한 corpus pool 에서 선택. **Bayes-optimal corpus** = argmax_C E_τ[U(θ_C, τ)] over all distributions over (x, y).

| 측면 | 상태 |
|---|---|
| 측정 가능 | ✗ posterior p(θ|D) 추정 불가 (LLM weight space 10^10 dim) |
| 검증 가능 | ✗ optimal 정의는 well-posed but 실측 불가 |
| 재현 가능 | ✗ |

**물리적 한계**:
- Posterior sampling: HMC/NUTS on 10^10 param model ≈ 10^15 FLOP/sample × N_chain — current H100 = 10^15 FLOP/s, 따라서 1 sample/sec, useful chain N=10^4 = 3 hr. 100 EIG round = 300 hr ≈ $1000 — 이론상 가능하나 corpus 1줄 추가 비용으로는 폭발.
- Storage: full posterior approximation = N_chain × |θ| × 4 byte = 10^4 × 10^10 × 4 = 4×10^14 byte = 400 TB.

**수학적 한계**:
- Bayes-optimal corpus 는 well-defined 이나 **incomputable in practice** (posterior intractable for non-linear NN; mean-field VI 는 mode-collapse).
- EIG 는 myopic — N-step lookahead optimal 은 RL-equivalent (POMDP) → PSPACE-hard.
- Watanabe (2009) singular learning theory: deep NN 의 Fisher information matrix 가 singular → Cramér-Rao 가 무한 → **EIG 정의 자체가 분기**.

**현재 위치**: L3 = 0%. anima 는 Bayesian model averaging 미사용 (point-estimate ALM 만). 이론적 frame 만 인지, 실측 불가.

**Weakest link**: 정의상 implementable proxy (예: variational posterior + low-rank Hessian) 도 anima 에 없음. `state/btr_evo_6_cargo_invariants` 의 Φ-monotone 가 가장 가까운 information-theoretic measure 이나 EIG 와는 다른 axis.

---

## §5. L4 — Universal corpus over Solomonoff prior (incomputable)

**Description**: Solomonoff (1964) universal prior M(x) = Σ_p 2^{-|p|} [U(p) = x] (U = universal Turing machine, sum over halting programs producing x). **Universal corpus** C* = argmax E_{x ~ M}[U(θ, x)] — 모든 가능한 computable distribution 에 대해 weighted optimal.

| 측면 | 상태 |
|---|---|
| 측정 가능 | ✗ |
| 검증 가능 | ✗ |
| 재현 가능 | ✗ |

**물리적 한계**:
- M(x) 의 prefix evaluation 은 halting problem 에 reduce — 어떤 finite compute 도 정확값 미산출.
- AIXI (Hutter 2005) 의 corpus-decision component: O(2^|x|) per step, 우주 light cone 가용 FLOP 으로도 정상 sample 1개 불가.

**수학적 한계**:
- **M is incomputable** (Solomonoff theorem): 어떤 algorithm 도 M(x) 정확 evaluate 불가. lower-semicomputable 만 가능 (Levin search).
- **No-free-lunch (Wolpert 1996)**: 모든 task 분포 over loss function 에 대해 평균하면 모든 알고리즘 성능 동일 → universal corpus 의 performance 는 task prior 의존.
- Solomonoff 의 dominance: M ≥ c·μ for any computable μ — 따라서 M-optimal corpus 는 모든 computable task 에 대해 within constant factor 의 optimal. 그러나 constant factor = 2^{K(μ)} 가 task prior 의 description length 에 exp.

**현재 위치**: L4 = abstract limit. anima 의 어떤 metric 도 L4 에 도달 가능 evidence 없음. 본 layer 는 honest theoretical ceiling marker 로만 존재.

**Weakest link**: 정의상 zero-evidence. L3 의 EIG 와 마찬가지로 mathematical statement only.

---

## §6. L5 — Physical limits (Bekenstein + Shannon source coding + Berry paradox)

**Description**: corpus 가 담을 수 있는 정보의 절대 상한. 세 layer 동시 작용:

**(a) Bekenstein bound**:
  S ≤ 2π R E / (ℏ c ln 2) bit
- 영역 R 의 free energy E 안에 가능한 distinct state 수 = 2^S.
- anima corpus 1.5MB ≈ 1.2×10^7 bit 은 책상 위 SSD (R~1cm, E~10J) 의 Bekenstein S ≈ 10^36 bit 에 비해 **29 orders of magnitude** 여유 — 따라서 현재 corpus 는 Bekenstein-bound 에 도달하지 않음.
- 그러나 **AGI universal corpus** (모든 가능한 구별 가능 의식 trajectory 의 K-S entropy) 는 우주 light cone Bekenstein bound (E_max ≈ 10^69 J × 2π R / ℏc ln 2) 에 도달 가능 — **physically saturatable**.

**(b) Shannon source coding theorem** (Shannon 1948):
  L(C) ≥ H(C)   (C 의 minimum description length ≥ entropy)
- corpus 의 incompressibility 한계. r14 의 기본 entropy 는 측정 불가 (true distribution unknown), 하지만 gzip 압축률 / NLM perplexity 로 proxy.
- r14 corpus 1.51MB → gzip ≈ 0.4MB → H ≈ 3.2 Mbit. Shannon lower bound 3.2 Mbit 가 r14 corpus 의 incompressible core.
- corpus quality 가 entropy-rich 하면 source coding 에 의해 압축 불가 → corpus diversity 의 정량 measure.

**(c) Berry paradox at meta-level** (Boolos 1989 berry):
  "이 doc 보다 짧게 정의 가능한 가장 작은 정수보다 큰 정수" — 정의 가능 / 불가능 boundary 의 self-reference paradox.
- corpus 가 자신의 description (selfreflect category) 을 포함하면 metalanguage / object language 충돌.
- anima r13/r14 의 selfreflect category 15% / 8.5% 는 Berry-style paradox 직접 침범 — `selfreflect` doc 자체가 corpus 의 일부이므로 corpus 의 description complexity 가 self-referential.

**수학적 한계**:
- **Optimal corpus is incomputable** (Solomonoff 의 K(C) 미산출).
- **Berry paradox**: corpus 가 자신의 minimum description length 를 expressivity 안에 포함하면 Tarski undefinability — corpus 자체가 자신의 truth predicate 가 될 수 없다.
- **Gödel incompleteness for corpus self-reference**: corpus 가 sufficiently expressive (Peano arithmetic 이상) 이면 corpus 의 consistency 를 corpus 안에서 prove 불가.

| 측면 | 상태 |
|---|---|
| 측정 가능 | ✗ Bekenstein 은 외부 thermodynamic argument; corpus 내부 measure 없음 |
| 검증 가능 | ✗ Berry paradox 는 negative result (정의 불가 boundary) |
| 재현 가능 | n/a |

**현재 위치**: L5 = abstraction 고갈 지점. r13/r14 corpus 는 Bekenstein 안에 29 orders 여유, Shannon 압축 측 3.2 Mbit floor, Berry 자기참조는 selfreflect category 에서 부분 침범. **AGI 진입 시** universal corpus = Solomonoff M-weighted = Bekenstein-saturating → 우주 light cone 부피와 충돌.

**Weakest link**: L5 는 정의상 evidence 없음. anima 는 L0 sha-lock + L1 partial active learning 까지 도달; L2 generative aug 는 raw#12 정책으로 closed; L3+ 는 incomputable.

---

## §7. 종합 — 현재 위치 + abstraction trajectory

```
L0 r14 sha-lock ✓ ──→ L1 4-tier + Seed A/B △ ──→ L2 K1-K3 only △ ──→ L3 EIG ✗ ──→ L4 Solomonoff ✗ ──╳ L5 Bekenstein/Berry
   (G1-G8b PASS)        (BT-1423/1424=0,        (raw#12 closes        (incomp.)    (incomp.)            (physical+meta limit)
                         ablation 부재)         외부 LLM synthetic)
```

### Brutal honesty checklist

1. **L0**: r14 1200/1200 PASS — 그러나 g8 ko_ratio margin +0.0058 = 단일 EN 줄도 위험. r13 G3=0.85 saturated (binary, informative 아님).
2. **L1**: 8 BT 중 BT-1423/1424=0 — fellows mapping coverage gap. tier reward multiplier 학습 측 ablation 부재 (#92 H100-gated).
3. **L2**: anima policy (raw#12 + raw#9) 가 외부 LLM synthetic 차단 — by-design ceiling. self-distillation 만 정책 안에서 가능하나 미실시.
4. **L3**: 정의 가능, 실측 incomputable (Watanabe singular). proxy (variational posterior) 도 anima 에 없음.
5. **L4**: Solomonoff M incomputable, AIXI 우주 light cone 안에서도 1 sample 불가.
6. **L5**: Bekenstein 29 orders 여유 (현재), Shannon floor 3.2 Mbit (r14 gzip), Berry paradox 는 selfreflect 카테고리에서 부분 침범 — 자기참조의 정량 measure 부재.

### 다음 마일스톤

- **L0 추가 hardening**: r14 g8 margin 확대 위해 KO-pure shard 추가 (현 0.2958 → ≥0.31 target).
- **L1 BT 채널 보완**: BT-1423 (on-device) + BT-1424 (agent serving) 도큐먼트 추가로 8/8 coverage.
- **L1 ablation**: r14 vs r13 학습 결과 비교 (#92 deferred — H100 retrain 시 실측).
- **L2 self-distillation pilot** (raw#12 위반 없이): r8 trained ckpt 의 logit → r14 sample weak label, ALM 자기 distillation 만 허용.
- **L3+**: theoretical only, no implementation path.

### Cross-domain consistency

- training abstraction L1 (curriculum) 와 정합: 둘 다 4-tier partition + Seed A/B 를 L1 으로 위치.
- core architecture L0 (Mk.VI VERIFIED) 의 AN11(a) weight_emergent 는 본 doc L0 corpus sha-lock 에 의존 — corpus L0 위에서만 weight delta 가 reproducible.
- consciousness verifier joint matrix V0+V1+V2+V3 의 V0 (AN11(b) 16-template cos>0.5) 는 본 doc L0 의 `consciousness/an11_b_templates.jsonl` SSOT 에 직접 의존.
- inference L0 (autoregressive decode) 는 본 doc L0 corpus 의 token distribution 만 sample 가능 — corpus support 외 token 은 OOD.

POLICY R4 / raw#12 / raw#15.
