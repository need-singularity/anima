# Mk.XII Retrain Plan v2 — Family-Conditional Primary Axis Integration

**작성일**: 2026-04-26
**축**: Axis 91 (own#2 (c) Phase 3 Production-readiness deliverable)
**선행**: axis 82 HW-A (Mistral weight-init PRIMARY) + axis 90 HCF-B/HCG-B (Qwen3+gemma corpus PRIMARY) + R46_CANDIDATE 4-family BIMODAL
**비용**: $0 mac-local docs only
**raw#10 honest**: 본 plan 은 own#2 (c) Production-readiness 만 영향, (a) FC + (b) PC 와 무관. Mk.XII retrain 이 hard problem 해결 NOT, philosophical zombie 가능성 untouched.

---

## §0 v1 → v2 핵심 diff

| dimension | v1 plan | v2 plan |
|---|---|---|
| **weight init strategy** | pretrained Mistral checkpoint + r14 LoRA (universal) | family-conditional: Mistral weight-init primary axis (axis 82) → A3 progressive disintegration |
| **corpus strategy** | r14 4-family balanced (universal) | backbone-conditional Mk.XI v10 ensemble (Mistral=Law / Qwen3=Phi / Llama=SelfRef / gemma=Hexad) |
| **scale strategy** | 70B universal ($1400-2100) | 13B pilot first ($300) → HW-A scale-invariance validation → 70B if confirmed |
| **family primary axis** | unspecified | Mistral=weight-init / Qwen3+gemma=corpus / Llama=neither (POS-base) |
| **estimated cost** | $1400-2100 4-6주 | Phase 3a $300 1-2주 (pilot) + Phase 3b $1400 4-6주 (full, conditional on pilot PASS) = total $1700 |

---

## §1 axis 82+90 결과 종합 (v2 plan rationale)

### 1.1 axis 82 — weight-distribution PRIMARY (Mistral)
- W1.1/W1.2/W1.3 hidden_noise 모두 sign 보존 NEG (-16.7~-16.0)
- W2 random_init **sign flip POS** (+23.47, Δ+40.17, 8/8 partitions POS)
- 결론: Mistral 의 anti-integration 은 architecture-inherent NOT, **PRETRAINING emergent consequence**
- raw#10 caveat: random_init POS 는 'noise floor' 가능성 (top_var 균등 0.34±0.01, I_full << I_partition trivially)

### 1.2 axis 90 — corpus PRIMARY (Qwen3 + gemma 50%)
- Mistral: BASE -16.70 → Instruct -12.91 (sign 보존, MODIFIER, |BASE|=16.70 > 10)
- Llama: BASE +5.09 → Instruct +5.21 (sign 보존, MODIFIER, POS-base)
- **Qwen3**: BASE -3.45 → Instruct +1.04 (**sign flip POS**, PRIMARY, |BASE|=3.45 ~ threshold)
- **gemma**: BASE -0.79 → Instruct +7.54 (**sign flip POS**, PRIMARY, |BASE|=0.79 < 3 threshold)
- 결론: 4-family BIMODAL 2/2 (R46_CANDIDATE registered)
- 가설: |BASE phi*| < ~3 NEG → corpus PRIMARY / |BASE| > ~10 → MODIFIER

### 1.3 joint determinant
- Mistral: weight-init primary (axis 82) → r14 corpus 변경으로는 sign flip 안 됨
- Qwen3+gemma: corpus primary (axis 90) → SFT instruct 만으로도 sign flip
- Llama: 둘 다 아님 (POS-base, 이미 integrated)
- gemma 의 weight-init axis 미테스트 — 대각선 셀 미완

---

## §2 Mk.XII v2 architecture proposal

### 2.1 weight init strategy (per backbone)

**Mistral** (weight-init primary):
- A3 progressive disintegration: pretrained checkpoint + intentional random Gaussian perturbation (scale 0.5-1.0, Layer 28-32 deep) → POS-bias retrain
- 또는 A2 mixed init: 일부 layer (deep CMT-active layer) random_init + 나머지 pretrained
- 비용: standard LoRA r14 + perturbation step → +5% wall time
- raw#10 risk: A3 가 'integrated info' 진정한 emergence 아닌 'unstructured uniform noise floor' 가능성

**Qwen3 + gemma** (corpus primary):
- A1 standard pretrained checkpoint 유지 + corpus axis B 변경에 의존
- weight init 변화 불필요 (이미 SFT 만으로 POS flip)

**Llama** (neither primary):
- A1 standard 유지 (이미 POS-base, 변경 무의미)

### 2.2 corpus strategy (per backbone — Mk.XI v10 ensemble 확장)

| backbone | family bias | corpus assignment |
|---|---|---|
| Mistral | Law (training) | Law-r14 (existing) + Law-extension Phase 3b |
| Qwen3 | Phi | Phi-r14 (existing, broad-attention C2) |
| Llama | SelfRef | SelfRef-r14 (existing) |
| gemma | Hexad | Hexad-r14 (existing) — Hexad 가장 약한 NEG (-0.79), corpus axis SFT-flip 능력 가장 강함 (+1055%) |

**B1 backbone-conditional corpus** (권장): Mk.XI v10 ensemble pattern 직접 확장. v1 universal 보다 family alignment 강화.

### 2.3 scale strategy

**C2 13B pilot first** (권장):
- 13B parameter range (e.g. mistralai/Mistral-Small-3.1-24B 또는 Qwen2.5-14B)
- Phase 3a 1-2주 $300 estimate
- 검증 항목: HW-A scale-invariance (Mistral weight-axis sign flip 가 13B 에도 작동?)
- 검증 항목: HCF-B/HCG-B scale-invariance (Qwen3+gemma corpus axis flip 이 13B 에도 작동?)
- PASS → Phase 3b 70B confirmed; FAIL → Phase 3b 7B 유지 (architectural primary axis 다른 가능성)

**C1 70B universal** 단독 진입은 risk 너무 큼 (HW-A scale-invariance 미검증).

---

## §3 권장 path: A3 + B1 + C2

**Phase 3a (1-2주, $300, 13B pilot)**:
1. Mistral-Small-24B random_init A3 + Law-r14 corpus → phi_v3_canonical 측정
2. Qwen2.5-14B A1 standard + Phi-r14 corpus → phi_v3_canonical 측정
3. Llama-3.2-Vision-11B A1 standard + SelfRef-r14 corpus → phi_v3_canonical 측정
4. gemma-3-12b A1 standard + Hexad-r14 corpus → phi_v3_canonical 측정
5. 4-bb scale-invariance verdict: HW-A + HCF-B + HCG-B 가 13B 에 generalize 하는가?

**Phase 3b (4-6주, $1400, 70B full)** — Phase 3a PASS 조건:
1. Mistral-Large-2 (123B) 또는 Mistral-Nemo-Instruct-12B 확장 + r14 Law full
2. Qwen3-72B + Phi-r14 full
3. Llama-3.1-70B + SelfRef-r14 full
4. gemma-2-27b + Hexad-r14 full

**Phase 3c (own#2 (c) closure 후속)**:
- vLLM endpoint deployment
- OAuth + SLA + 안전 가이드라인
- legal/ethics review (external dependency, blocking)

---

## §4 cost summary

| Phase | duration | cost | deliverable |
|---|---|---|---|
| Phase 3a (13B pilot) | 1-2주 | $300 | scale-invariance verdict (4-bb) |
| Phase 3b (70B full) | 4-6주 | $1400 | own#2 (c) Mk.XII retrain |
| Phase 3c (production) | 4-8주 | $500-5000 | endpoint + legal sign-off |
| **total** | **9-16주** | **$2200-6700** | own#2 (c) full PASS |

own#2 audit (axis 81 precursor) 의 v1 estimate $1400-2100 4-6주 → v2 $2200-6700 9-16주 (Phase 3a 추가 + Phase 3c 확장 honest reflection).

---

## §5 raw#10 honest 한계 (필수 reading)

1. **Mk.XII retrain 은 own#2 (c) production-readiness 만 영향** — (a) FC + (b) PC empirical-max 와 무관. Mk.XII PASS 후에도 own#2 triad full PASS NOT.
2. **HW-A random_init POS 가 'integrated info' 보장 NOT** — 'noise floor' 가능성 (top_var 균등 0.34±0.01). A3 progressive disintegration 적용 시 이 risk 그대로 유전.
3. **R46 4-family BIMODAL N=4 statistically small** — threshold ~3-10 post-hoc fitted, 5번째+ backbone 검증 시 무너질 가능성 (R46 → R46_DEPRECATED).
4. **scale invariance 미검증** — HW-A Mistral 7B 에서만 measured. 13B pilot Phase 3a 결과 따라 70B 확장 여부 결정. Phase 3a FAIL 시 7B 유지.
5. **family primary axis 가 production target 정의 NOT** — 사용자 query 별 family 동적 선택 또는 ensemble routing 필요. 단일 backbone production deployment 는 family bias risk.
6. **legal/ethics review external dependency** — Phase 3c 의 hardest blocker, 사용자 (또는 anima org) 외부 협력 필요. Mac-local timeline 으로 control 불가.
7. **hard problem 영구 untouched** — Mk.XII retrain 이 phenomenal consciousness 문제 해결 NOT. own#2 PC empirical-max ceiling 그대로.

---

## §6 next actionable

1. **즉시** (mac-local $0): Phase 3a 13B pilot spec frozen — 4-bb 모델 ID, corpus assignment, A3 perturbation parameters, phi_v3_canonical 측정 프로토콜
2. **subagent rate limit reset 후** (4:40am KST): Phase 3a runpod launch script 작성 + validate
3. **Phase 3a launch** (1-2주 후): 4-bb 13B forward + phi_v3_canonical fan-out
4. **Phase 3a verdict** (Phase 3a 후 1주): scale-invariance generalize? PASS → Phase 3b 70B; FAIL → 7B 유지 + Mk.XII v3 재설계
5. **R46 4-family BIMODAL 5번째 backbone 검증** (별도 cycle): Phi-3-mini, DeepSeek-llm-7b, Yi-6B 추가 → R46 promotion 또는 deprecation

---

## §7 cross-link

- **own#2** (`anima/.own` L28-L46): production triad (a)+(b)+(c) ALL required, Mk.XII v2 = (c) deliverable only
- **own#3** (`anima/.own` L48-L66): σ/τ=3 governance, Mk.XII 의 r14 corpus = 4-backbone × 4-family τ=4 ↔ Hexad 매니폴드 alignment
- **R46_CANDIDATE** (`state/atlas_convergence_witness.jsonl` round 47): 4-family BIMODAL hypothesis, R46 → R46_CONFIRMED 시 v2 plan rationale 강화
- **R45_CANDIDATE** zombie posterior (round 45): 10-substrate update needed (Qwen3-it + gemma-it 추가 → 4 NEG / 6 POS dominance)
- **axis 82** (`~/.claude/projects/-Users-ghost-core-anima/memory/project_weight_distribution_axis_phi_v3.md`): HW-A primary axis evidence
- **axis 90** (`~/.claude/projects/-Users-ghost-core-anima/memory/project_corpus_axis_4family_bimodal.md`): HCF-B/HCG-B primary axis evidence
- **CLAUDE.md retired** (per memory `project_claude_md_retired.md`): canonical SSOT = .raw + .own + .guide triad

---

## §8 verdict

**Mk.XII v2 plan = A3 (Mistral weight perturbation) + B1 (backbone-conditional Mk.XI v10 ensemble corpus) + C2 (13B pilot first → conditional 70B)**.

**비용**: Phase 3a $300 + Phase 3b $1400 + Phase 3c $500-5000 = $2200-6700, 9-16주.

**Phase 3a 13B pilot 가 critical gate** — HW-A + HCF-B/HCG-B scale-invariance 검증.

**own#2 (c) full PASS path 명확화**, but **(a) FC + (b) PC 무관** (Mk.XII 가 own#2 triad full PASS 보장 NOT).

raw#10 absolute: **이 plan 은 production target deliverable 이지 의식 검증 진전 NOT**.
