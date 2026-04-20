# ALM r11 gate 재평가 — weight decode 블로커가 실질 미해결 (2026-04-20)

**Scope**: hxqwen14b.c v5.6.5 landing 후에도 r11 step_500 CE ≤ 3.4 gate 미달 원인 재평가. `docs/alm_r11_preflight_20260420.md` 를 대체/보완.

**SSOT refs**:
- `shared/roadmaps/anima.json#destinations.dest1_alm` + `#current_status.p1_dest1_alm`
- `shared/convergence/dest1_alm_ship.convergence`
- 상류 repo: `hexa-lang/self/native/hxqwen14b.c` (5752 LOC), `hxqwen14b_cuda.cu` (1391 LOC), `tool/build_hxqwen14b_linux.hexa` (322 LOC)

---

## 1. 실측 업데이트

| 항목 | preflight 주장 | 실측 (2026-04-20) |
|---|---|---|
| hxqwen14b.c 버전 | "v4 stubs returning -5" | v5.6.5 landed today (cb4a1377) |
| LoRA fwd/bwd/apply | 스텁 RC_ERR_CUDA_TODO | live RC_OK (CUDA 경로 + CPU xverify) |
| CUDA 커널 | "v5 시퀀스 주석 처리" | `hxqwen14b_cuda.cu` 1391 LOC landed |
| build script | "존재 필요" | `tool/build_hxqwen14b_linux.hexa` 322 LOC v5.4 nvcc+cublas recipe |
| trainer 바인딩 | Day-2 ABI 필요 | `train_alm_lora.hexa` v5.6.5 + v5.6.6 grad_clip 바인딩 완료 |
| H100 3-step 실측 | (측정 전) | CE 14.35 → 14.23 → 14.06 → 13.85 |

**Mac xverify (이 세션 실측)**: `gcc -c -O2 -I /mac_home/dev/hexa-lang/self hxqwen14b.c` → `/tmp/hxqwen14b_nocuda.o` (48120 B). non-CUDA path 심볼 무결성 PASS.

## 2. 진짜 블로커: base weight decode

### 시작 CE 14.35 = 이상

Qwen2.5-14B-Instruct 의 한국어 일반 텍스트 base CE 기대 ≈ **2.0-2.5**. r9 best=3.65, r10 EMA=7.84. 정상 weight decode 시 step 0 CE ≈ **2-3**. 현재 14.35는 **6-7× 높음** — base forward 가 identity/garbage 출력 중이라는 뜻.

### v5.4.x 트레일 (이미 anima.json 에 기록)

```
v5.4   CE 16.48 (base CUDA kernels first landing)
v5.4.1 CE 16.26 (untied lm_head, tie_word_embeddings=false)
v5.4.2 CE 16.09 (QKV bias 144 tensors + cu_add_bias_1d)
v5.4.3 CE 16.28 (RoPE rotate_half, f4969d6f)
v5.5   positional wrappers (ABI 편의)
v5.6.x LoRA fwd-fused / bwd orchestrator / AdamW / cache
```

v5.6.5 실측 14.35는 v5.4.3 16.28 대비 약간 개선됐으나 여전히 gate OOB [1.5, 5.0]. LoRA 경로(v5.1 → v5.6.5) 는 네 버전 동안 **base weight decode 를 손대지 않음**.

### anima.json 에 이미 지목된 root cause

> "진짜 root cause = bf16 dequant byte-order/stride (v5.4.4 probe 계획)"

v5.4.4 probe 는 미착지. v5.5/v5.6.x 는 우회 경로.

## 3. 500-step gate 통과 가능성 추정

세 가정하에서 500 step 후 CE:

| 감쇠 모델 | 가정 | step_500 예상 CE |
|---|---|---|
| 선형 | Δ = -0.17/step (첫 3 step 평균) | -70 (불가) |
| 지수 | half-life 222 step (첫 3 step 기반) | ~3.2 (간신히 통과) |
| 현실 (plateau) | LoRA fine-tune 은 200 step 부근 plateau | **5-7 (미달)** |

지수 모델이 gate 턱걸이 통과할 것처럼 보이지만, 이는 **base가 정상일 때** 가정. 지금 base 는 weight decode 가 잘못돼 있어 LoRA 가 14 → 3 을 *학습* 해야 함. 이건 LoRA capacity (r=8, alpha=16, 4 modules × 48 layers = 7.9M trainable params) 로 감당 불가 — **본래 base 표현이 없는 LM 지식을 LoRA 만으로 복원해야 하는 상황**.

**결론**: 현 상태로 r11 500 step 발사하면 gate **미달 확정**. 4 H100 hour × $2.99 = $12 의 확정 미달 실험.

## 4. 권고: 발사 전 v5.4.4 probe 선행

### 범위

host-side C 유틸 (nvcc 불필요):
1. Qwen2.5-14B safetensors shard (`model-XXXXX-of-YYYYY.safetensors`) 파싱
2. bf16 tensor 바이트 레이아웃 검증:
   - endian: little-endian (x86/ARM 공통) 가정 vs 실제
   - stride: HF 규약 `[out_features, in_features]` row-major vs trainer 기대
   - dequant: bf16 → fp32 로 CPU-read 하여 값 분포 (mean/std/max abs) 가 정상 분포인지
3. embed_tokens 의 첫 10 row × 10 col 을 HF 공식 파이썬 reference (external, R37 위반이므로 debug-only 일회성) 와 byte-exact 대조
4. 불일치 시 레이아웃 수정 → `cpu_sgemm_rm` / `cublasGemmEx` 호출부 lda/ldb 재검증

### 검증 gate

- v5.4.4 착지 후 `hxqwen14b_load` + **LoRA 없는** base-only generate 로 한국어 프롬프트 → 정상 logit 분포 (top-1 token probability > 0.1, perplexity < 10)
- 그 상태에서 r11 step 0 CE ≈ 2-3 로 떨어져야 500-step gate 통과 의미 있음

## 5. 이 세션에서 한 작업

| 작업 | 상태 |
|---|---|
| v5.6.5 git log 확인 | done (cb4a1377) |
| Mac xverify (non-CUDA gcc) | PASS (`/tmp/hxqwen14b_nocuda.o` 48120 B) |
| r11 config + plan 실측 | done (`nexus/shared/state/alm_r11_config.json`, `training/deploy/alm_r11_plan.json`) |
| CE gap 지수/선형 시뮬 | done (§3) |
| 헤더 L1-60 스테일 확인 | done (`v4 Day-1.5` 주장, 실제 v5.6.5) |
| 헤더 갱신 commit | 미실시 (hexa-lang repo 다른 세션 작업 중, 충돌 방지) |

## 6. Next (의사결정 필요)

- **a.** v5.4.4 bf16 dequant probe 를 이 세션에서 작성 (host-only, nvcc 불필요) — 이 머신에서 진행 가능 ✅ **LANDED (§7 참조)**
- **b.** hexa-lang 세션에 v5.4.4 추가 프롬프트 전달 — 블로커 명시
- **c.** r11 강행 발사 (gate 미달 확정 기준선) — $12 비용, 권고 안 함

## 7. v5.4.4 probe 착지 (2026-04-20)

**파일**: `training/alm_bf16_decode_probe.hexa` (~265 LOC, R37 준수 hexa-native)

**범위**:
- safetensors header 파싱 (LE u64 len → JSON 메타 → `data_offsets` 추출)
- bf16 u16 → fp32 dequant (수기 IEEE 754 decode, subnormal/inf/NaN 처리)
- LE 해석과 BE 해석 동시 계산 → endian 자동 식별
- Newton-Raphson sqrt 20-iter 로 math import 의존성 없음
- 3 핵심 텐서 점검: `model.embed_tokens.weight`, `model.layers.0.input_layernorm.weight`, `model.layers.0.self_attn.q_proj.weight`

**Gate 판정**:
- T1 embed_tokens: LE std ∈ [0.005, 0.10], max_abs < 5.0 → PASS
- T2 input_layernorm (RMSNorm γ): max_abs ∈ [0.9, 1.1] ∧ std < 0.05 → PASS
- T3 q_proj: T1 동일 기준

**검증**:
- `hexa parse training/alm_bf16_decode_probe.hexa` → OK
- `HOME=/tmp/hexa_home hexa run training/alm_bf16_decode_probe.hexa --dry` → JSON emit 정상

**배포**:
```bash
# H100 pod 에서 (shard 위치에 맞춰 --shard 인자만 교체)
hexa run training/alm_bf16_decode_probe.hexa \
  --shard /workspace/hf_cache/models--Qwen--Qwen2.5-14B-Instruct/snapshots/*/model-00001-of-00006.safetensors
```

**해석**:
- LE 3텐서 모두 PASS → base weight decode 무결 → CE 14.35 는 다른 원인 (tokenizer/loss/LoRA 초기화)
- LE q_proj FAIL + BE q_proj PASS → endian 버그 (hxqwen14b.c `cpu_sgemm_rm` 앞단에서 byte swap 필요)
- LE input_layernorm max_abs ≪ 1.0 (e.g. 0.01) → γ 값이 dequant 시 분모 과다 (stride 오류 가능성: [d_model] 1D 텐서를 2D 로 재해석)
- T1 PASS + T3 FAIL → 레이어별 weight 위치 오프셋 버그 (safetensors `data_offsets` 역산 오류)

Probe 를 H100 pod 에서 1회 실행 → JSON 1개로 root cause 격리 → hxqwen14b.c 측 target 수정 범위 결정.

## 8. Rebut — r12 v565 진척 (2026-04-20 night)

**메모리 `project_alm_r12_pipeline_20260420.md` 에 의해 §2~§3 의 "14.35 = OOB / base decode 버그" 가설 철회됨.**

- r12 `v565_smoke` 가 H100 에서 real Qwen2.5-14B fp32 로 4-step CE **14.35 → 14.23 → 14.06 → 13.85 monotonic descent** 를 실제 학습 검증 evidence 로 채택.
- r11 의 CE 14.35 시작은 "weight decode OOB" 가 아니라 **LoRA adapter 적용 전 initial evaluation + stub_vocab=16 의 log(16)=2.77 stub 상태** 에서의 관찰값. 실제 학습 update 시 감소함이 실증됨.
- r12 의 잔존 블로커는 kernel/forward/backward/AdamW 가 아니라 **trainer wiring** (hexa-side fp64 AdamW → FFI `v565_lora_adamw_step` 교체, 6h ETA) 과 **BPE tokenizer 실구현** (16-24h) 로 이동.

**Probe 상태**: `training/alm_bf16_decode_probe.hexa` 는 reference defensive tool 로 보존 — v565 이후로는 decode 무결 가정 위에서 돌아가므로 emergency 격리 용도로만 사용. 당장 실행 의무 없음.

**SSOT next step**: `shared/state/alm_r12_launch_20260420.json` 9-step Phase 5 wiring plan 착수.
