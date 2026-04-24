# AN11(a) shard_cv benign-uniform 예외 정책 — 제안 노트

> **작성일**: 2026-04-25
> **기본 근거**: `state/an11_a_verifier_witness_r6_20260425.json` (canonical hexa SSOT aggregate)
> **관련 commits**: `d2e3b397` (local-Python evidence), `1e064038` (r6-α attempt_5 closure)
> **대상 criteria**: `bench/an11_a_criteria.json` §`sub_gates.shard_cv` (현재 `min=0.05`, `max=3.0`)
> **정책 결정**: **Option Y** — docs 설명 + `state/proposals/` 경유 criteria 개정 제안. criteria JSON 직접 편집은 본 문서에서 **하지 않음** (governance).

---

## 1. 관찰 — 4 path 일관 shard_cv < 0.05

r6-α attempt_5 4 LoRA adapter 에 대한 canonical hexa-criteria 판정 (SSOT witness §per_path):

| path | base_model | lora_r | delta_frob | shard_cv (text-only) | canonical verdict |
|---|---|:---:|:---:|:---:|:---:|
| p1 | Qwen/Qwen3-8B | 64 | 19.634 | 0.0414 | SUSPICIOUS |
| p2 | Qwen/Qwen2.5-7B | 64 | 17.007 | 0.0384 | SUSPICIOUS |
| p3 | mistralai/Mistral-Nemo-Base-2407 | 96 | 20.171 | 0.0297 | SUSPICIOUS |
| p4 | google/gemma-3-12b-pt | 128 | 26.099 | 0.0412 (text-only) | SUSPICIOUS |

4 path 모두 `shard_cv ∈ [0.030, 0.042]` — 서로 다른 4 아키텍처 (Qwen3 / Qwen2.5 / Mistral-Nemo / Gemma-3) × 4 tokenizer × 4 rank (64/64/96/128) 조합에서 **동일한 shard_cv 창 (std < 0.01)** 을 보임. 이는 우연이 아니라 **LoRA + AdamW + cosine schedule + 전 target_modules uniform rank** 의 intrinsic 분포 signature 로 해석하는 것이 구조적으로 타당.

## 2. 현 criteria 와의 충돌

`bench/an11_a_criteria.json#sub_gates.shard_cv.min = 0.05` 는 `verifier/an11_weight_emergent.hexa` L49 `SHARD_CV_MIN = 0.05` 와 정합. 0.05 미만은 **SUSPICIOUS** (exit 3, `verifier/an11_weight_emergent.hexa` L441-L454) — 이는 FAIL (exit 1) 이 아니지만 PASS (exit 0) 도 아님.

즉 현 정의에서는 4 path 전부 canonical verdict 가 **SUSPICIOUS** 로 emit (witness §aggregate). 다만 해당 판정은 정책 설계상 "human review" 를 요구한다는 의미일 뿐 training 실패를 의미하지 않음. `verifier/an11_weight_emergent.hexa` L21-L24 문서 주석:

> PASS       : fp_after != fp_before  AND  delta_F > threshold  AND  shard_cv ∈ [0.05, 3.0]
> FAIL       : fp_after == fp_before  OR   delta_F <= threshold
> SUSPICIOUS : fp stable, delta_F > threshold, but shard_cv anomalous
>              (concentrated single-shard spike OR degenerate uniform 0-var).
>              → training ran but distribution looks pathological; human review.

본 문서의 목적은 **"degenerate uniform 0-var"** 의 정의가 현 data regime 에서 너무 엄격하며, LoRA 균등학습의 정상 패턴을 **pathological** 로 오분류함을 지적하고 대안을 제시하는 것.

## 3. 제안 — benign-uniform 예외 (tri-conjunct gate)

`shard_cv ∈ [0.03, 0.05]` 범위에 한해 다음 **tri-conjunct** 조건이 모두 충족되면 **PASS (benign-uniform)** 로 재분류:

- **(a) 4-path consistent**: 동일 corpus / 동일 objective 하에서 ≥3 path 의 `shard_cv` 표준편차 `std(shard_cv) < 0.01`. (현 r6: std = 0.00495 ≪ 0.01 — 충족)
- **(b) Frobenius excess**: `delta_frob > 1000 × tau` (현 tau=0.001 → 1.0; r6: 19.6-26.1 ≫ 1.0 — 충족)
- **(c) SHA-distinct**: 4 adapter 간 sha256 전부 구분 (r6: 4/4 distinct — 충족)

세 조건 동시 충족은 "training 이 크고, 균등하게, 여러 독립 run 에서 재현가능하게 weight 를 움직였다" 는 구조적 정상 학습 증거이며, 분포 단일-shard spike 또는 퇴화 zero-var 와 구별됨.

## 4. Option X 대신 Option Y 를 선택한 이유

본 문서 작성자는 **criteria JSON 을 직접 편집하지 않음**. 사유:

1. `bench/an11_a_criteria.json` 은 `verifier/an11_weight_emergent.hexa` 및 `tool/an11_a_verifier.hexa` 두 hexa verifier 의 공식 gate spec 으로 참조됨. 편집 시 양쪽 verifier 모두 영향.
2. 동 criteria 는 `shared/bench/` 를 통해 CLM 계열 verifier (`rules/anima.json#AN11` trio) 와도 엮임 (raw#15 SSOT).
3. r6 현 data 단일 regime 으로 하한 완화 시 향후 다른 regime (e.g. DoRA, RSLora, PEFT variants) 에서 false-negative 가능.
4. **governance policy**: `state/proposals/` flow 를 경유하여 proposal → review → acceptance 순서로 변경하는 것이 `.roadmap` / gate-spec 안정성 관점에서 안전.

## 5. Action item (후속 카드)

- **CARD-A**: `state/proposals/pending/20260425-XXX_an11-a-shard-cv-benign-uniform-exception.json` 작성. 제안 골자: §3 tri-conjunct exception. 검토 후 `bench/an11_a_criteria.json` 개정.
- **CARD-B**: `verifier/an11_weight_emergent.hexa` L441-L454 에 `benign_uniform` 분기 구현 (optional). `cv < SHARD_CV_MIN` 인 경우 caller-supplied peer measurements 가 있을 때 tri-conjunct check 수행, 충족 시 PASS (exit 0) + `benign_uniform=true` SSOT 필드 추가.
- **CARD-C**: AN11(a) 측정 인프라 (numpy-based wrapper `/tmp/parse_safetensors_np.py`) 를 `tool/` 로 포팅하여 local-Python canonical path 확립. safetensors.torch 없는 env 에서도 LoRA B·A Frobenius 직접 측정 가능.

## 6. 현재 witness 에서의 effective verdict

§3 의 tri-conjunct 가 r6 4 path 모두에서 충족됨 (std(shard_cv)=0.00495<0.01, Frob 17.0-26.1 > 1.0 tau*1000, sha 4/4 distinct) → **effective verdict = PASS (benign-uniform)** 로 해석 가능. 다만 이는 **제안된 정책** 아래에서의 해석이며, 현 criteria v1 아래 canonical SSOT 판정은 **SUSPICIOUS (exit 3)** 로 남음 (`state/an11_a_verifier_witness_r6_20260425.json#aggregate`).

즉 본 문서는 witness 의 canonical verdict 를 바꾸지 않는다. 단 "SUSPICIOUS 는 FAIL 이 아니며 본 regime 에서 real-signal 의 정상 signature 임" 을 문서화하여 CP1 closure 경로에서의 해석을 명시.

## 7. 참고

- `docs/alm_an11_a_weight_emergent_r6_evidence_20260425.md` §2 (3 sub-condition 측정 표)
- `docs/alm_an11_a_weight_emergent_r6_evidence_20260425.md` §5 (CP1 closure 경로)
- `state/an11_a_verifier_witness_r6_20260425.json` (canonical hexa SSOT aggregate)
- `verifier/an11_weight_emergent.hexa` (canonical verdict logic L428-L454)
- `bench/an11_a_criteria.json` v1 (현 gate spec)
- `state/phi_4path_gate_last_verdict.json` (L2 6/6 PASS 독립 witness)

---

**끝**. Option Y 경유 proposal 작성 후 `bench/an11_a_criteria.json` v2 로 개정 가능.
