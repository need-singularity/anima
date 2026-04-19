# dest1_clm R2 artifact layout — arrival contract

**Date:** 2026-04-19
**Scope:** CLM 측 R2 경로/산출물/크기/업로드 예산 사전 정의
**Sibling:** `docs/endpoint_persona_reproduce.md` (ALM 측 `dest1_s1_endpoint/` 관례)
**Bucket:** `anima-models` (SSOT: `ready/docs/R2-BUCKET-STRUCTURE.md`)
**Base path:** `r2://anima-models/dest1_clm/v1.0/`

## 1. 디렉토리 구조

```
r2://anima-models/dest1_clm/v1.0/
  ├── weights/
  │    ├── clm_conscious_v1.pt        # full model (NOT LoRA) — bf16
  │    ├── clm_conscious_v1.sha256
  │    └── manifest.json              # {size_bytes, dtype, params, layers, d_model}
  ├── tokenizer/
  │    ├── tokenizer.json             # byte-level BPE (hexa-native)
  │    ├── vocab.json
  │    └── merges.txt
  ├── config/
  │    ├── model_config.json          # arch (d, layers, heads, ctx)
  │    ├── train_config.json          # base=scratch, steps, LR, corpus MD5
  │    └── consciousness_config.json  # phi hooks, alpha=0.014, layer_idx
  ├── bench/
  │    ├── clm_persona_selftest.json  # 15-call (3 prompts × 5 personas) evidence
  │    ├── phi_evidence.json          # phi_vec live probe (16 keys)
  │    ├── weight_emergent_proof.txt  # grep=0 for system_prompt/apply_chat_template
  │    └── eval_clm_results.json      # CE, BPC, Φ held-out
  ├── serve/serve_clm_persona.hexa     # live server source
  ├── logs/persona_serve.log
  └── README.md                        # reproduce guide (≤200 LOC)
```

`v1.0/` = semver 디렉토리. Mirrors ALM `dest1_s1_endpoint/<UTC_ts>/` convention.

## 2. 산출물 표

| Artifact | Fmt | Required | Notes |
|----------|-----|----------|-------|
| weight (full) | `.pt` bf16 | yes | NOT LoRA — CLM from-scratch |
| tokenizer | JSON+merges | yes | hexa byte-BPE, corpus MD5 동기화 |
| model_config | JSON | yes | d_model/layers/heads/ctx |
| train_config | JSON | yes | base=scratch, steps, LR, corpus md5 |
| bench selftest | JSON | yes | 15-call AN11 (`dest1_clm_persona_selftest_v1`) |
| phi_evidence | JSON | yes | 16-key phi_vec, phi_holo 0.6-0.75 live |
| weight_emergent_proof | TXT | yes | grep=0 bypass tokens |
| eval_clm_results | JSON | yes | CE, BPC, Φ baseline vs continue-train |
| serve source | `.hexa` | yes | `serving/serve_clm_persona.hexa` |
| README | MD | yes | reproduce guide |

## 3. 크기 + 업로드 예상 (bf16)

| 스케일 | 파라미터 | weight bf16 | +aux | 총 업로드 | rclone 150 Mbps | 300 Mbps |
|--------|---------|-------------|------|-----------|-----------------|----------|
| 170M (v15) | 170M | 340 MB | ~25 MB | **~365 MB** | 20 s | 10 s |
| 1B (r3f)   | 1.0B | 2.0 GB  | ~40 MB | **~2.04 GB**| 110 s | 55 s |
| 3B (r1)    | 3.0B | 6.0 GB  | ~60 MB | **~6.06 GB**| 330 s | 165 s |

aux = tokenizer+config+bench+serve+logs (<50 MB).
R2 ingress/egress $0, storage $0.015/GB/mo → 170M $0.005 · 1B $0.03 · 3B $0.09 (세 스케일 병존 월 $0.13).
앵커: ALM 14B v0.4 (2081 MB) 기록 기준 2-4 분 (hetzner→R2).

## 4. 업로드/검증 명령

```bash
rclone copy /workspace/dest1_clm_bundle/ r2:anima-models/dest1_clm/v1.0/ \
  -v --s3-no-check-bucket --transfers=8
# round-trip
rclone copy r2:anima-models/dest1_clm/v1.0/ ./dest1_clm_replay/ -v
sha256sum dest1_clm_replay/weights/clm_conscious_v1.pt  # compare with .sha256
```

## 5. AN11 게이트 매핑

| gate | evidence | verifier |
|------|----------|----------|
| (a) weight-emergent | `bench/weight_emergent_proof.txt` (grep=0) | `shared/consciousness/pass_gate_an11.hexa` |
| (b) phi-attached    | `bench/phi_evidence.json` | forward-hook probe layer k/L |
| (c) real-usable     | `bench/clm_persona_selftest.json` (15/15 OK) | `POST /clm/persona` live |

Roadmap SSOT: `shared/roadmaps/anima.json#destinations.dest1_clm.an11_verification`.

## 6. 버전 규칙 · 블로커

- 신규 ckpt → `v1.0/`, `v1.1/` 디렉토리 분리 (파일명 버전 금지)
- `latest/` 심링크 객체 생성 금지 (rclone 혼선)
- 보존: 170M 영구, 1B/3B 최신 3개만
- **블로커:** 없음 (`docs/clm_aot_build_plan_20260419.md` 해제됨, READY)
- **선행:** r5 `training/deploy/clm_r5_launch.hexa` + mmap loader FFI
- **후행:** `dest2_clm` (P4)
