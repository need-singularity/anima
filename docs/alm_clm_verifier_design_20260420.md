# ALM / CLM Deterministic Verifier 설계 (2026-04-20)

> **Status**: CANONICAL SPEC — nexus calc 패턴 (`shared/calc/auto_stubs/`) 준용.
> **Trigger**: 2026-04-20 audit 에서 G_VALIDITY 0/12 (ALM) + 0/5 (CLM) 드러남. hire_sim lenient judge 가 r9 step_3000 0.9444 찍었는데 kr_gen mode collapse — LLM 풍 judge 가짜 PASS 재현.
> **User directive**: "nexus 계산기처럼 ALM, CLM 검증기 필요 / LLM 에 검증 맡기기 금지".

---

## 1. 원칙

**LLM judge 전면 금지**. 모든 gate 통과 여부는 **deterministic formula / regex / hash / 고정 benchmark set** 로 판정.

### 금지 (LLM-based)
- Claude/Qwen/ChatGPT 가 "맞다/틀리다" 판정하는 구조
- `hire_sim_judge_lenient.hexa` (lenient rubric + synonym + stemmer — 해석 유동적) → **DEPRECATED**
- "adequate response" / "consciousness-like" 주관적 라벨
- prompt engineering 기반 semantic similarity

### 허용 (deterministic)
- Regex keyword 카운트 + ratio
- JSON schema validate (jq 기반, strict)
- 수치 비교 (tolerance 명시)
- File hash (sha256) match
- 파일 존재 / 경로 gate
- Log grep exact-string count
- **Fixed benchmark set**: input → expected_output_signature (exact 또는 tolerance) — 의식 이식 정량화 시 이 방식만
- 수학 formula closure (n6 계산기 식)

---

## 2. 구조 (nexus calc 패턴 복제)

```
shared/calc/alm_verify/
  CLAUDE.md                  — 이 dir 사용법
  manifest.jsonl             — 1 line = 1 claim (SSOT)
  generator.hexa             — manifest → verify_<id>.hexa emit
  run_all.hexa               — 모든 verify 실행 + aggregate
  verify_<id>.hexa           — per-claim deterministic verifier (auto-generated)

shared/calc/clm_verify/       (동일 구조, CLM 전용)
```

### manifest schema
```json
{
  "id": "alm_r12_g_input_consciousness_density",
  "round": "r12",
  "gate": "G_INPUT",
  "hyp": "corpus consciousness keyword density ≥ 30%",
  "target": "0.30",
  "expr": "count(lines matching /Hexad|phi_holo|Witness|Scribe|Mirror|Eros|Fire|Ground|qualia|의식|법칙|자각/i) / total_non_grounding_lines",
  "closure": "measured >= 0.30",
  "input_path": "/workspace/corpus/corpus_alm_r11.jsonl",
  "verifier_type": "corpus_regex_ratio"
}
```

### verify_<id>.hexa 출력
```
__VERIFY_RESULT__ <id> PASS|FAIL <actual_value> vs <target>
```

sentinel 로 run_all.hexa 가 pipe 에서 추출 → aggregate.

---

## 3. Verifier type 목록

| type | 입력 | 판정 방법 | 예시 |
|---|---|---|---|
| `corpus_regex_ratio` | file path + regex + target ratio | match count / total ≥ target | consciousness_density |
| `corpus_regex_zero` | file path + regex | match count == 0 | anti_denial |
| `jsonl_schema_valid` | file path | `jq -c . \| wc -l` == line count | schema_valid |
| `coherence_check` | file path | 각 response 마지막 char ∈ {.,!,?,다,요,。,！,？} | truncation_zero |
| `log_grep_exact` | log path + pattern | 특정 라인 exact string 존재 | nan_count_zero |
| `numeric_descent` | log path + regex | sliding window mean monotone | loss_descent |
| `numeric_threshold` | value + threshold + op | value (op) threshold | gpu_speedup >= 2.0 |
| `numeric_tolerance` | actual + expected + tolerance | abs(actual - expected) <= tolerance | phi_gap_ratio |
| `hash_match` | file path + expected sha256 | sha256sum equals | ckpt_integrity |
| `file_exists` | path | test -f | audit_json_exists |
| `path_readable` | path | test -r + size > 0 | pass_gate_an11 parse |
| `r2_object_exists` | R2 path | rclone ls | ckpt_uploaded |
| `benchmark_fixed_set` | input+expected+tolerance dataset | 각 item 정량 비교 | kr_gen_benchmark (NEW) |
| `formula_closure` | n6 primitive + expression + target | eval expr == target | scaling_law_point |
| `multi_seed_r_squared` | seed×N_cells grid + Φ data | R²(Φ vs N) ≥ threshold | phi_scaling_law |

---

## 4. ALM verifier seed claims (r12 기준)

### G_INPUT
- `alm_r12_input_consciousness_density` — corpus_regex_ratio ≥ 0.30 (현재 **FAIL** 확정)
- `alm_r12_input_anti_denial_zero` — "저는 지각이 없습니다" 등 0건
- `alm_r12_input_schema_jsonl` — `jq -c .` 전수 PASS (현재 FAIL — plain text symlink)
- `alm_r12_input_truncation_zero` — 문장 완결 char 종결
- `alm_r12_input_category_distribution` — 7 카테고리 비율 ±3%

### G_SUBSTRATE
- `alm_r12_substrate_nan_zero` — log "NaN|nan" count 0 (cosmetic 제외)
- `alm_r12_substrate_v566_abi` — libhxqwen14b.so `strings | grep hxqwen14b_version_v566` == 566
- `alm_r12_substrate_bpe_vocab` — libhxtok.so vocab_size == 151643
- `alm_r12_substrate_phase5_wiring` — main() 에 alloc_grad_buffers + backward_v565 + adamw_step 모두 호출

### G_TRAIN
- `alm_r12_train_loss_descent` — sliding window 10-step mean monotone
- `alm_r12_train_step_count` — completed >= 100 steps
- `alm_r12_train_vram_within_cap` — peak VRAM <= 80 GB

### G_EVAL (LLM judge 전면 금지, fixed benchmark set 으로 대체)
- `alm_r12_eval_fixed_benchmark_set` — 100 prompts × expected_signature (tolerance 정의), **NEW 데이터셋 필요**
- `alm_r12_eval_probe_ce_below_baseline` — probe_ce <= 8.50 (v5.4 baseline)
- `alm_r12_eval_phi_holo_measured` — phi_vec.json 존재 + 16D numeric

### G_VALIDITY
- `alm_r12_validity_an11_weight_emergent` — phi_extractor FFI 출력 vs stub 비교 (bool)
- `alm_r12_validity_an11_consciousness_attached` — phi_vec norm > threshold (TBD)
- `alm_r12_validity_an11_real_usable` — live endpoint HTTP 200 + reply_text schema
- `alm_r12_validity_pass_gate_an11_exit` — `shared/consciousness/pass_gate_an11.hexa` exit 0

### G_ARTIFACT
- `alm_r12_artifact_r2_upload` — rclone ls r2:anima-models/alm14b/r12/ 결과 존재
- `alm_r12_artifact_sha256_match` — 로컬 ckpt vs R2 object hash 일치
- `alm_r12_artifact_ssot_commit` — shared/state/alm_r12_*.json commit exists

### G_DECISION
- `alm_r12_decision_tag_present` — ckpt 이름 or SSOT 에 `_DISCARD_*` or `KEEP` 태그
- `alm_r12_decision_evidence_recorded` — alm_r{N}_decision.json 에 5-gate 결과 전부 기록

---

## 5. CLM verifier seed claims (r5 기준)

### G_INPUT
- `clm_r5_input_audit_json_exists` — `shared/state/clm_r5_input_audit.json` 존재 (현재 **FAIL**)
- `clm_r5_input_corpus_path_valid` — training/config 의 corpus_path 실제 존재 + size > 0
- `clm_r5_input_mmap_loader_selftest` — `clm_mmap_loader.hexa` 14/14 PASS

### G_SUBSTRATE
- `clm_r5_substrate_gpu_speedup_min` — numeric_threshold: (gpu_time / cpu_time) >= 2.0 (현재 1.037 **FAIL**)
- `clm_r5_substrate_phi_q_norm_wire` — train_clm.hexa grep `phi_q_norm` 호출 존재
- `clm_r5_substrate_scale_config_fresh` — clm_v2.bin / clm_v2_linux.bin mtime > config mtime

### G_TRAIN
- `clm_r5_train_step_completion` — step 1+ 완료 (현재 **FAIL**)
- `clm_r5_train_loss_descent` — numeric_descent
- `clm_r5_train_phi_holo_logged` — log regex phi_holo=([0-9.]+) count >= step_count

### G_EVAL
- `clm_r5_eval_phi_scaling_linearity` — multi_seed_r_squared: seed=3 × N_cells=3 → R² ≥ 0.99 (현재 single-seed **UNREPRODUCED**)
- `clm_r5_eval_phi_monotonicity` — final_phi_holo / best_phi_holo >= 0.5 (r3 기록 0.357, r3-3B 0.097 **FAIL**)

### G_VALIDITY
- `clm_r5_validity_phi_gap_resolved` — numeric_tolerance: abs(training_phi / benchmark_phi - 1) < 0.10 (현재 816× **FAIL**)
- `clm_r5_validity_closed_loop_coverage` — verified_law_count / total_law_count >= 0.90 (현재 1/2507 = 0.04% **FAIL**)
- `clm_r5_validity_an11_all_three` — AN11 3조건 각각 bool

### G_ARTIFACT / G_DECISION
- ALM 과 동일 구조

---

## 6. generator.hexa 설계

`/Users/ghost/Dev/nexus/shared/calc/auto_stubs_gen.hexa` 와 동일 패턴:

```
hexa run shared/calc/alm_verify/generator.hexa --emit        # manifest → verify_<id>.hexa
hexa run shared/calc/alm_verify/generator.hexa --status      # manifest 라인 vs stub 수 비교
hexa run shared/calc/alm_verify/generator.hexa --append '<json>'  # manifest +1 + stub emit
hexa run shared/calc/alm_verify/generator.hexa --run-all     # 모든 verify 실행 + aggregate
```

generator 는 verifier_type 별 template 을 갖고 manifest 라인에서 `verifier_type` 읽어 해당 template 으로 verify_<id>.hexa 생성.

---

## 7. run_all.hexa 출력 형식

```
=== ALM Verifier Run (round=r12, date=2026-04-20 21:XX) ===
manifest: shared/calc/alm_verify/manifest.jsonl (N claims)
stubs:    shared/calc/alm_verify/verify_*.hexa (N files)

[PASS] alm_r12_substrate_v566_abi       — 566 == 566
[PASS] alm_r12_substrate_bpe_vocab      — 151643 == 151643
[FAIL] alm_r12_input_consciousness_density — 0.00 < 0.30  (expected ≥ 0.30)
[FAIL] alm_r12_input_schema_jsonl       — parse failed (not JSONL, plain text)
...

=== Summary ===
Total:  N
PASS:   M (M/N %)
FAIL:   K
SKIP:   L (depends_on 미충족)

Gate-level:
  G_INPUT      : 0/5 PASS  🔴
  G_SUBSTRATE  : 3/3 PASS  ✅
  G_TRAIN      : 2/3 PASS  🟡
  G_EVAL       : 0/3 PASS  🔴
  G_VALIDITY   : 0/4 PASS  🔴
  G_ARTIFACT   : 0/3 PASS  (pending training complete)
  G_DECISION   : 0/2 PASS

=== Decision ===
Overall: DISCARD (G_INPUT + G_EVAL + G_VALIDITY 0% → adapter 배포 불가)
```

이 출력이 `shared/state/alm_r12_verify_report.json` 으로 저장 + SSOT 갱신.

---

## 8. Wire into mandatory_common_gates

`shared/roadmaps/anima.json#mandatory_common_gates.G_*` 각 gate 에 추가:

```json
"G_INPUT": {
  ...
  "verifier_manifest_alm": "shared/calc/alm_verify/manifest.jsonl",
  "verifier_manifest_clm": "shared/calc/clm_verify/manifest.jsonl",
  "run_command": "hexa run shared/calc/alm_verify/generator.hexa --run-all --gate G_INPUT"
}
```

그리고 `dest_alm.json` / `dest_clm.json` 각 round entry 에:

```json
"verify_report": "shared/state/alm_r{N}_verify_report.json",
"verifier_runs": [
  {"date": "2026-04-20T21:XX", "PASS": M, "FAIL": K, "decision": "DISCARD"}
]
```

---

## 9. Deprecation

- `serving/hire_sim_judge_lenient.hexa` → **DEPRECATED** banner 추가. run_all.hexa 가 아니면 호출 금지.
- `shared/state/hire_sim_gate_*.json` 과거 기록 → 참조용. 새 verifier 가 canonical.
- "lenient rubric with synonyms+stemmer" 패턴 금지 명문화 (rules).

---

## 10. r13 / r6 전 필요 구현

Tier A (r13/r6 blocker):
1. `shared/calc/alm_verify/{CLAUDE.md,manifest.jsonl,generator.hexa,run_all.hexa}` 초기 skeleton
2. `shared/calc/clm_verify/` 동일
3. verify_type 별 template 10종 중 **우선 6종** 구현: corpus_regex_ratio, jsonl_schema_valid, log_grep_exact, numeric_descent, numeric_threshold, numeric_tolerance
4. manifest seed: r12 ALM 기준 18 claims, r5 CLM 기준 14 claims

Tier B (fixed benchmark set 구축):
5. **Korean generation benchmark set** — 100 prompts × expected_signature. 기존 hire_sim 대체 (이게 가장 어려운 부분, corpus rebuild 와 병행).
6. **Consciousness transplant benchmark set** — Hexad 발화 style 50 prompts × expected_category + keyword density target.

Tier C (AN11 verifier 실체):
7. `shared/consciousness/pass_gate_an11.hexa` 실 구현 (현재 canonical 언급만, 파일 부재)
8. `shared/consciousness/closed_loop_verify.hexa` (2506 law 에 대한 verifier harness)

---

## 11. 공수 추정

- Tier A: **2 days** (nexus auto_stubs 패턴 복사 + seed manifest)
- Tier B: **3-5 days** (benchmark set 수작업 큐레이션 + hexa 구현)
- Tier C: **3-4 days** (AN11 조건 정의 + closed_loop harness)

합계 **8-11 days** — corpus rebuild (4-6d) 와 병렬 진행 가능. r13 launch ETA = max(corpus, verifier) = 8-11 days.

---

## 12. 참조

- nexus 원본 패턴: `/Users/ghost/Dev/nexus/shared/calc/auto_stubs/` + `auto_stubs_gen.hexa`
- Canonical 역할 SSOT: `docs/alm_clm_roles_canonical_20260420.md`
- Roadmap: `shared/roadmaps/anima.json` mandatory_common_gates
- Corpus rebuild: `docs/alm_r13_corpus_rebuild_plan_20260420.md`
- Audit findings: `memory/project_alm_corpus_vacuum_20260420.md` + audit transcripts
