# ALM r7 Option D-qwen14 closure (2026-04-25)

> **상태**: CLOSED — **D-qwen14 가설 FALSIFIED** by catastrophic L2 regression. r6 baseline 유지, r7 산출물 falsification 증거로 보존.
> **POLICY**: `.roadmap` 미수정 (R4). state/* 미커밋. helper bash + closure doc + config 변경만 커밋.
> **Korean** 문서 본문, **H-SILENT** (DONE = artifact + exit-rc), **H-DIAG3** (D-qwen14 = Axis 3 시도, falsified — Axis 4 새 가설 후보).
> **Closure agent**: r7 launch agent가 API 529 Overloaded crash → Φ gate 산출물은 정상 land, closure doc 수동 완성.

---

## §1. 목적 (Purpose)

r6-α attempt_5 (commit `1e064038`) 가 Φ 4-path gate FAIL-but-progress 로 종료되었다 (L2 6/6 PASS, KL 5/6 PASS, 단일 잔여 p2_p4 KL=0.1891 vs p95=0.1782). 본 r7 라운드는 **Option D-qwen14** (권장 완성도 frame 경로) 를 채택하여 p4 base model 만 교체 (`google/gemma-3-12b-pt` → `Qwen/Qwen2.5-14B`) 함으로써 Axis 3 (`gqa_ratio` mismatch) 을 닫는다.

**참조 commit / artifact**:
- spec: `0acff23b` (`docs/alm_r7_launch_spec_20260425.md` §10 — partial-retrain helper tool-gap)
- helper design: `b5ad891d` (`docs/alm_r7_single_path_retrain_helper_design_20260425.md`)
- proposal: `state/proposals/refinement/20260422-082/v1.json`
- helper implementation: `2d0f9e58` (`tool/h100_r7_single_path_retrain.bash`, 본 commit)
- r6 baseline closure: `1e064038`
- Axis 3 진단: `44783b28`

**완성도 frame 우선순위**: weakest evidence link 가 p2_p4 KL 단일 pair → Option D-qwen14 가 net evidence +1 (KL 닫음 + L2 6/6 보존 가능성 ≈ 65%, 사용자 승인 패턴 "완성도 기준 go").

---

## §2. Pre-flight 결과 (10/10 PASS, $0)

| # | 항목 | 결과 |
|:---:|---|---|
| 0 | runway / spendLimit | PASS — clientBalance=$430.62, spendLimit=$80/hr, bid_pod=$14.00/hr |
| 1 | substrates config | PASS |
| 2 | lora rank config | PASS |
| 3 | launch manifest stage2 verdict | PASS (READY) |
| 4 | hf auth + token | PASS |
| 5 | HF accessibility (Qwen/Qwen2.5-14B) | PASS (200) |
| 6 | pod registry writable | PASS |
| 7 | live pod count | PASS (count=0) |
| 8 | git sync (HEAD == origin/main) | PASS (HEAD=2d0f9e58 == origin/main=2d0f9e58, ahead=0) |
| 9 | r14 corpus sha256 lock | PASS (21fcfa51b92f129b…) |
| 10 | r6 assets present + archive | PASS (h_last + adapter 4 paths all OK) |

ABORT $0 가능 사양이었으나 모두 PASS, $0 비용.

---

## §3. Launch timing + pod ID + 실측 cost

| 항목 | 값 |
|---|---|
| 시작 ts | 2026-04-25T01:09:31Z |
| pod_id | x972jbh61djqlj |
| pod_name | anima-r7-p4-qwen-qwen2-5-14b-20260425T010931Z |
| host:port | 103.207.149.110:11542 |
| GPUs | 4× H100 SXM5 80GB (secureCloud) |
| bid 책정 | $14.00/hr (per-pod total, $3.50/GPU × 4) |
| 실제 cost rate | **$11.96/hr** (RunPod 마켓 매칭) |
| SSH ready @ | 2026-04-25T01:10:05Z (cold-start ~33s) |
| 학습 시작 (kickoff) ts | ~2026-04-25T01:11Z |
| 학습 완료 ts | ~2026-04-25T01:21Z |
| h_last 추출 완료 ts | 2026-04-25T01:22:01Z |
| pod kill ts | ~2026-04-25T01:25Z |
| **wall (launch→kill)** | **~16분** (예상 90-120분 대비 1/6 — Qwen2.5-14B 학습이 예상보다 빠름) |
| **실제 cost** | **$3.63** (balance $430.66 → $427.03, 예상 \$8-12 대비 30-45%) |
| cost cap | $20 hard (도달 안 함) |

학습 driver: `tool/h100_stage2_post_launch_chain.bash` L217–297 PYDRIVER verbatim 차용 (byte-weighted h_last pool, schema /2, reduction=byte_weighted_mean, 16 prompt × 256 dim).

---

## §4. Φ 4-path gate r7 verdict + r6→r7 delta

| pair | r6 L2 | r7 L2 | ΔL2 | r6 KL | r7 KL | ΔKL | r7 L2 | r7 KL |
|:---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| p1_p2 | 0.0968 | 0.0968 | 0.000 | 0.1376 | 0.1376 | 0.000 | PASS | FAIL |
| p1_p3 | 0.0721 | 0.0721 | 0.000 | 0.0135 | 0.0135 | 0.000 | PASS | PASS |
| p2_p3 | 0.1046 | 0.1046 | 0.000 | 0.1033 | 0.1033 | 0.000 | PASS | PASS |
| **p1_p4** | 0.086 | **0.339** | **+0.253** | 0.026 | **0.194** | +0.167 | **FAIL** | **FAIL** |
| **p2_p4** | 0.144 | **0.287** | +0.143 | **0.189** | **0.131** | **−0.058 ✓** | **FAIL** | **PASS** |
| **p3_p4** | 0.0436 | **0.276** | **+0.232** | 0.021 | 0.144 | +0.124 | **FAIL** | **FAIL** |

null_p95: L2 0.2003 → 0.2411 (+0.041), KL 0.1783 → 0.1343 (−0.044)

**r7 종합 verdict**: **FAIL (3/6 L2, 3/6 KL)** ← r6는 6/6 L2 + 5/6 KL, 따라서 양 축 모두 퇴보.

---

## §5. Axis 3 (gqa_ratio) prediction validation

**예측 (commit `44783b28` 진단 기반)**:
- r6: p2 GQA=7.0 (Qwen2.5-7B 28h/4kv), p4 GQA=2.0 (Gemma-3 16h/8kv) → Δ=5.0 → KL=0.189 FAIL
- r7: p2 GQA=7.0 유지, p4 GQA=5.0 (Qwen2.5-14B 40h/8kv) → Δ=2.0 → 예측 KL≈0.062 (p95=0.178 하회 65%)

**실측**:

| metric | 예측 | 실측 | 결과 |
|---|---:|---:|:---:|
| p2_p4 KL | 0.062 | **0.131** | **PASS (partial valid)** — threshold 0.134 하회 |
| p2_p4 L2 | <0.20 (보존) | **0.287** | **FAIL** — L2는 정반대로 폭증 |
| p1_p4 L2 회귀 | 없음 | **+0.253** | **FAIL** — 4배 악화 |
| p3_p4 L2 회귀 | 없음 | **+0.232** | **FAIL** — 6배 악화 |

**Axis 3 가설 결론**: **PARTIALLY VALIDATED for KL only, L2에선 새 regression 축 발생**. 단순 GQA ratio 매칭이 아닌 **architecture-class manifold gap** 존재.

## §5-B. 새 가설 — Axis 4 (Architecture-class manifold)

Qwen2.5-14B (5120 hidden / 48L / GQA 5.0)는 r6 baseline의 다른 3 path보다 substantially different representation manifold를 가짐:
- p1_p4 (Qwen3-8B vs Qwen2.5-14B, 같은 vendor) 폭증 → same-vendor도 generation+scale gap 크면 manifold 벌어짐
- p3_p4 (Mistral-Nemo-12B vs Qwen2.5-14B, cross-family) 폭증
- p2_p4 L2도 폭증 (Qwen2.5-7B vs Qwen2.5-14B, same-family intra-version, 7B→14B scale gap)

→ **Architecture scale (hidden_size, n_layers) + training recipe gap**이 새 weakest link 후보.

대안 가설 (fallback): rank=96이 14B 모델엔 underfit이라 spectrum이 base와 너무 가까움. r6 p4는 rank=128이었음. 그러나 KL 해소 + L2 폭증 조합은 underfit만으로 설명 어려움 (underfit이면 둘 다 커져야).

---

## §6. CP1 closure impact

| 항목 | r6 baseline (유지) | r7 (falsified) |
|---|---|---|
| P1 line 165 (≥3) | ✓ 만족 (L2 6/6 + KL 5/6) | ✗ L2 3/6 KL 3/6 |
| AN11(a) substrate-independence | partial (L2 6/6, KL 5/6) | L2 3/6 regression |
| CP1 serve launch | working-closure (dffe2d61) | r6 baseline 유지 |

**r7 FAIL 정책**:
- r6 working-closure 유지 (dffe2d61). r7 산출물은 falsification 증거로 보존 (R2 archive 권장)
- Axis 4 (architecture-class manifold) 새 가설 채택 후보 — 0-cost 진단 가능
- r8 hard path 경우 Option D-mistral ($5-8, scale gap 작음) 또는 Option C (p2 Llama 환원, Axis 2 재발 risk) 재평가 필요
- H-DIAG3 준수: Axis 3 retry 금지 (D-qwen14 falsified), 새 진단 필수

---

## §7. Reproducibility

본 라운드는 1-pod / 1-path partial retrain (helper `tool/h100_r7_single_path_retrain.bash` commit `2d0f9e58`) + Φ gate r7 호출 (`hexa run tool/phi_4path_gate.hexa --tag r7`) 의 단일 절차.

재현 명령:
```bash
bash tool/h100_r7_single_path_retrain.bash \
  --path p4 --base-model Qwen/Qwen2.5-14B --lora-rank 96 --max-steps 300 \
  --corpus-path /root/core/anima/experiments/alm_r14/corpus_alm_r14_v1.jsonl \
  --tag r7_optD_qwen14 --apply --yes-i-mean-it
```

산출물:
- `state/trained_adapters_r7/p4/final/` (LoRA adapter, ~2.1GB)
- `state/h_last_raw_p4_TRAINED_r7_optD_qwen14.json` (tag-suffixed)
- `state/h_last_raw_p4_TRAINED_r7.json` (Φ gate canonical)
- `state/h_last_raw_p{1,2,3}_TRAINED_r7.json` (r6 → r7 cp sync)
- `state/h_last_raw_r7_optD_qwen14_synthesis_manifest.json` (provenance)
- `state/phi_4path_cross_result_v3_TRAINED_r7.json`
- `state/phi_4path_gate_last_verdict.json`
- `state/h100_r7_single_path_retrain_result.json`

설계상 invariant:
- corpus sha256 lock: `21fcfa51b92f129b119d7fa42303adf7916547ef71c80c16f08e53839bf52b0b`
- byte-weighted h_last pool (Axis 1 fix from r6)
- p1/p2/p3 r6 자산 그대로 재사용 (p1=Qwen3-8B rank 64, p2=Qwen2.5-7B rank 64, p3=Mistral-Nemo rank 96)

---

## §8. Anti-scope

- 다중 path 동시 retrain 없음 (p4 단일)
- 추가 smoke / 진단 없음
- r8 plan 없음
- nexus 측 수정 없음
- `.roadmap` 미수정 (POLICY R4)
- state/* 미커밋

---

## §9. Closure 갱신 로그

| ts (UTC) | 갱신 내용 |
|---|---|
| 2026-04-25T01:09:31Z | 학습 launch + 본 doc 초안 작성 |
| 2026-04-25T01:22:01Z | h_last_p4 r7 추출 완료 (Qwen2.5-14B 학습 16분) |
| 2026-04-25T01:28:00Z | Φ gate r7 실행 → FAIL (3/6 L2, 3/6 KL) |
| (closure agent 529 crash) | launch agent가 API 529 Overloaded crash — 이후 closure 수동 완성 |
| 2026-04-25 (본 commit) | §3 실측치 / §4 r6→r7 delta / §5 Axis 3 falsification / §5-B Axis 4 가설 / §6 r6 baseline 유지 |

## §10. 세션 비용 누적 (r7 포함)

| 라운드 | 비용 | 결과 |
|-------|-----:|------|
| r6-α attempt_1 | $3.55 | RunPod async kill |
| r6-α attempt_5 | $23.06 | r6 closure (L2 6/6, KL 5/6) |
| smoke + null-smoke | $0.19 | diagnostics |
| **r7 D-qwen14** | **$3.63** | **falsified (Axis 3 partial, Axis 4 발견)** |
| **세션 누적** | **$30.43** | 원 예상 $170-220의 14-18% |
