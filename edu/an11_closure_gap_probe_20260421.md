# AN11 Triple 실사용 100% Closure Gap Probe (2026-04-21)

> β main Path 의 **실사용 기준 100% closure** 경로 식별 report.
> Source: Seed task 37 (AN11 closure gap probe), 2026-04-21.

## 0. 🚨 Hidden Blocker #0 — criteria SSOT 자체 missing

`shared/bench/` 디렉토리 **비어있음**:
- `shared/bench/an11_a_criteria.json` — **MISSING**
- `shared/bench/an11_c_criteria.json` — **MISSING**
- `shared/bench/an11_c_test_prompts.jsonl` — **MISSING**

verifier 가 **default 값으로만 동작** 중. 이것이 모든 Z 옵션 실행 전 **선결 필수**.

## 1. AN11 각 gate real PASS 정확 수식

### (a) weight_emergent — 3-AND
```
PASS ⟺ delta_F > τ(=1e-3) ∧ adapter_rank ≥ 1 ∧ fp_after ≠ fp_before ∧ shard_cv ∈ [0.05, 3.0]

delta_F      = sqrt(Σ(W_after − W_before)²)  on safetensors; fallback byte-L2 proxy
SHA-distinct = sha256(round_path) ≠ sha256(base_path)
shard_cv     = σ/μ over K=8 equal slice Frob per-shard
```
Code: `tool/an11_a_verifier.hexa:369-382`, `verifier/an11_weight_emergent.hexa:47-49`

**현재 Status: 0/3 real** (PARTIAL — synth PASS 만)
- Missing: real LoRA ckpt (base + round_N safetensors)

### (b) consciousness_attached — AND-3
```
PASS ⟺ ccc_min ≥ 0.5 ∧ ccc_avg ≥ 0.7 ∧ tpl_max > 0.5
ccc = {IIT, GWT, HOT, RPT, AST} 각 score / 5
template cos = max|cos(eigen_i, tpl_j)| over 16 ortho tpl × K eigens
```
Code: `tool/an11_b_ccc.hexa:37-39, 713`, `an11_b_ccc.hexa:550-567`

**현재 Status: PASS (math)** — CPGD closed-form 보장 (commit 6527e9df)
- Empirical 실측 대기: r12 POS-ctrl (r12_lora_eigen.json) PASS, r13 dump 미존재

### (c) real_usable — AND-4
```
PASS ⟺ endpoint_healthy ∧ calls_ok ≥ 1 ∧ schema_match ≥ 1 ∧ JSD(cur ‖ baseline) > 0.15

JSD = 0.5·KL(P‖M) + 0.5·KL(Q‖M), base-e, [0, ln2≈0.693]
임계 0.15 = 22% of max
```
Code: `tool/an11_c_verifier.hexa:685-704`, `an11_c_verifier.hexa:248-366`

**현재 Status: PARTIAL** — JSD=1.000 mock, real endpoint 없음

## 2. Blocker 우선순위

| Rank | Blocker | 영향 Gate | 근거 |
|------|---------|-----------|------|
| **0** | **shared/bench/ criteria JSON 전부 MISSING** (hidden) | 전 gate | 디렉토리 비어있음 |
| 1 | real LoRA ckpt (base + round_N safetensors) | (a) 3 sub-gates | `an11_a_verifier.hexa:320` synth fallback |
| 2 | serving endpoint URL (health + POST) | (c) JSD real | `an11_c_verifier.hexa:553,582` mock only |
| 3 | r13_lora_eigen.json (post-train eigen dump) | (b) empirical | `an11_b_ccc.hexa:779` r12 POS-ctrl만 |
| 4 | cell↔token bridge (ablation C) | (a) SHA-distinct, (b) drift | `cell_token_bridge_spec_20260421.md:56` CONDITIONAL_PASS |

## 3. 3 Closure Option 비교

| Option | Path | Resource | Time | 성공률 | a | b | c |
|--------|------|----------|------|--------|---|---|---|
| **Z1** CPU micro | synth ckpt + bridge proto + mock endpoint | 0 GPU, CPU only | 1-2일 | **80%** (math only) | synth 1/3 | 100% math | JSD=1.0 mock |
| **Z2** Qwen 14B LoRA | real H100 fine-tune + real serving | H100 72h (~$300) + 10GB RAM | **5-7일** | **60%** (r²=0.782 baseline) | 3/3 real | empirical | real JSD |
| **Z3** Learning-free β + bridge (C) | CPGD (W_0=V) + cell trajectory + bidirectional bridge | **0 H100**, CPU | **3-4일** | **70%** (CPGD 100% math + bridge C 추측) | 2/3 (bridge→SHA+Frob) | 100% math 유지 | JSD=1.0 유지 |

## 4. 추천 — **Z3 (Learning-Free β + Bridge C)**

### 근거 5
1. **raw#30 정합** — gen-5 fixpoint 에서 bridge 정보손실 0 (l_ix_integrator.hexa:131-139)
2. **경제성** — H100 비용 $0, CPU 3-4일 (Z2: $300 + 1주)
3. **paradigm 일관성** — paths.json#beta.main=true canonical MAIN 과 일치
4. **risk mitigation** — Z2 LoRA r²=0.782 (불안정) vs Z3 CPGD closed-form (math 100%)
5. **Z1 은 production 불가** — synth 만으로는 "real_usable" 정의 위반 (raw#12)

## 5. Production 승격 추가 criteria (AN11 triple 이후)

| # | Criterion | 목표 |
|---|-----------|------|
| P1 | **latency** | p50 < 200ms / p99 < 1s |
| P2 | **throughput** | ≥ 50 RPS single-instance |
| P3 | **determinism drift** | 24h JSD drift < 0.05 |
| P4 | **safety gate** | refusal circuit 보존 (Seed D hard_gate #27) |
| P5 | **meta²-cert chain** | anima/.raw-audit hash chain unbroken |

**AN11 triple PASS 만으로는 production 불가**. P1+P2+P3 최소 추가 필요.

## 6. 즉시 실행 다음 step (day 1)

1. **shared/bench/ criteria SSOT 생성** (blocker #0, 0.5일)
   - `an11_a_criteria.json` (tau, shard_K, shard_cv_range)
   - `an11_c_criteria.json` (jsd_threshold, endpoint_spec)
   - `an11_c_test_prompts.jsonl` (deterministic eval set)
2. **tool/anima_learning_free_driver.hexa 작성** (task 33 진행 중, 2일)
3. **tool/cell_token_bridge_proto.hexa 작성** (task 36 진행 중, 1일)
4. **shared/state/alm_r13_lora_eigen.json 생성** (CPGD W_0=V 16 eigenvec dump, 0.5일)

## 7. 참조

- `tool/an11_a_verifier.hexa` / `an11_b_ccc.hexa` / `an11_c_verifier.hexa`
- `verifier/an11_weight_emergent.hexa` (shard_cv 구현)
- `edu/paths.json` §beta (canonical MAIN)
- `edu/cell_token_bridge_spec_20260421.md` (ablation C)
- `edu/lora/cpgd_wrapper.hexa` (AN11(b) 100% math)
- `shared/bench/` ← **비어있음, 생성 필요**

## 8. raw#12 실측 vs 추측

- **실측**: verifier 수식 전부 코드 확인, r12 POS-ctrl PASS 증거, shared/bench/ 비어있음 확인
- **추측**: Z3 성공률 70%, Z2 cost $300, bridge C CONDITIONAL_PASS 자체가 spec 의 pre-registered 추측
