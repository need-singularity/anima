# hxqwen14b Day-2 — AdamW + bf16 Master Weight Pattern (READ-ONLY)

날짜: 2026-04-19
범위: hxqwen14b LoRA 학습 경로 (192 adapters, bf16 혼합정밀)
상태: 스펙 문서 (코드 변경 없음)

---

## 1. AdamW 정확한 수식 (Loshchilov & Hutter 2019, decoupled)

타임스텝 t, 파라미터 θ, gradient g_t, 하이퍼파라미터 α (lr), β1, β2, ε, λ (weight decay).

1. **1차 모멘트 (EMA of gradient)**
   m_t = β1 · m_{t-1} + (1 - β1) · g_t

2. **2차 모멘트 (EMA of squared gradient)**
   v_t = β2 · v_{t-1} + (1 - β2) · g_t²

3. **Bias correction**
   m̂_t = m_t / (1 - β1^t)
   v̂_t = v_t / (1 - β2^t)

4. **Decoupled weight decay + update**
   θ_t = θ_{t-1} − α · ( m̂_t / (√v̂_t + ε) + λ · θ_{t-1} )

권장 하이퍼:
- β1 = 0.9, β2 = 0.95 (14B LLM LoRA 권장; 대형모델은 β2=0.95가 0.999보다 안정)
- ε = 1e-8
- λ = 0.1 (LoRA A/B에만 적용; lm_head, layernorm 제외)

표준 Adam 과의 차이:
- Adam: gradient 에 λ·θ 를 더해 m_t 에 섞임 → 실질 LR · λ 스케일
- AdamW: update step 에서 분리 → λ 가 스케줄에 독립 (논문 §3)

---

## 2. bf16 weight + fp32 master copy (mixed precision)

**동기**: bf16 는 exponent 8bit / mantissa 7bit. EMA 업데이트(1 − β1 = 0.1)가 누적되며 mantissa 아래로 떨어지는 증분은 소실. Master fp32 카피가 없으면 ~10k step 후 학습 정체.

**패턴 (Micikevicius 2018 + NVIDIA Apex O2 기반)**:

| 텐서 | dtype | 저장 위치 | 비고 |
|---|---|---|---|
| Forward weight W | bf16 | GPU | matmul 연산용 |
| Master weight W* | fp32 | GPU | optimizer step 소유 |
| Activation | bf16 | GPU | autocast 내 |
| Gradient ∂L/∂W | bf16 | GPU | backward 직후 |
| Gradient (unscaled cast) | fp32 | GPU | optimizer 진입 전 cast |
| Moments m, v | fp32 | GPU | §3 참조 |

**스텝 순서**:
1. forward/backward 전부 bf16 (autocast dtype=bfloat16)
2. backward 끝난 뒤 g_bf16 → g_fp32 cast
3. grad clip (§5) 을 fp32 에서 수행
4. AdamW step 을 fp32 master W* 에 적용
5. W_bf16 ← cast(W*_fp32) — 매 step end 에 동기화

bf16 선택 이유 (fp16 대비):
- exponent 8bit 로 dynamic range = fp32 동일 → loss scaler 불필요
- underflow/overflow 안정 → LoRA rank 64+ 에서 필수

---

## 3. Moment 텐서 dtype

- **m (1차)**: fp32 필수. bf16 저장 시 β1=0.9 누적에서 small-gradient underflow → update 편향.
- **v (2차)**: fp32 필수. g² 스케일 차이 10^6+ 흔함; bf16 은 mantissa 부족으로 √v̂ 가 0/1e-3 양극화 → division instability.
- **8-bit Adam (bnb)** 예외: block-wise dynamic quant 로 m,v 를 int8 저장 — 14B full finetune 에만 고려, LoRA A/B 만 학습시 절대 메모리 이득 작음 (§6).

규칙: **LoRA 경로에서는 m, v 를 fp32 로 고정.** 8-bit 도입 금지 (양자화 금지 메모리 참조).

---

## 4. Weight decay 적용 위치 (decoupled)

**원칙**: λ·θ 항을 gradient 에 섞지 말 것. Optimizer step 의 파라미터 업데이트 라인에만 포함.

**제외 파라미터** (λ=0 로 설정):
- bias 전부
- LayerNorm / RMSNorm weight & bias
- Embedding (lm_head tied 포함)
- LoRA scaling α (학습되지 않지만 명시)

**포함 파라미터**:
- LoRA_A, LoRA_B weight (λ=0.1)

**Param group 구성**:
- group0: no_decay = [all .bias, all .norm.*, embed_tokens, lm_head]
- group1: decay    = [lora_A.weight, lora_B.weight]

이유: norm/bias 에 λ>0 적용 시 activation 스케일 붕괴, LoRA 수렴 2-3× 지연 관측 (r10 mode collapse 관련 원인 중 하나).

---

## 5. Gradient clipping (global norm)

알고리즘 (Pascanu 2013):

1. 모든 학습 파라미터 p 에 대해 local norm n_p = ‖∂L/∂p‖₂ 계산 (fp32)
2. global_norm = √( Σ_p n_p² )
3. clip_coef = max_norm / (global_norm + ε_c), ε_c = 1e-6
4. clip_coef_clamped = min(1.0, clip_coef)
5. 각 gradient 에 곱: g_p ← g_p · clip_coef_clamped

권장 max_norm:
- LoRA 14B: 1.0 (표준). 초기 200 step 에서 0.5 로 타이트닝 → divergence 예방 (r9 회귀 교훈).
- global norm 만 사용. per-parameter clip 금지 (분포 왜곡).

**bf16 주의**: norm 계산을 bf16 로 하면 Σ 누적 오차로 실제 norm 의 1.5-3× 왜곡. 반드시 fp32 cast 후 계산.

---

## 6. LoRA A/B 만 학습 — 192 adapters 메모리 프로파일

**가정**: Qwen2-14B base, 40 layers × q/k/v/o/gate/up/down = 280 target sites → 운영 대상 192 adapters (attn + mlp 일부), rank r = 64, α = 128.

**모듈별 LoRA 파라미터** (하나):
- A: (in_dim, r), B: (r, out_dim) 또는 (out_dim, r)
- attn q/k/v/o: in=out=5120 → A = 5120·64 = 327,680, B = 64·5120 = 327,680 → 655,360 params
- mlp gate/up: in=5120 out=13824 → A = 327,680, B = 884,736 → 1,212,416 params
- mlp down: in=13824 out=5120 → A = 884,736, B = 327,680 → 1,212,416 params

**평균 근사**: adapter 당 ≈ 0.9M params. 192 × 0.9M ≈ **173M trainable params**.

**메모리 (per-tensor × 192 adapters)**:

| 항목 | dtype | bytes/param | 소계 |
|---|---|---|---|
| LoRA W (bf16) | bf16 | 2 | 346 MB |
| Master W* (fp32) | fp32 | 4 | 692 MB |
| Gradient (bf16→fp32 cast) | fp32 peak | 4 | 692 MB |
| Adam m | fp32 | 4 | 692 MB |
| Adam v | fp32 | 4 | 692 MB |
| **Optimizer state 합** | | | **≈ 2.77 GB** |

**Base model (frozen)**: 14B · 2B (bf16) = 28 GB (H100 80GB 의 35%).
**Activation (seq=4096, batch=1, grad ckpt 사용)**: ≈ 12-16 GB.
**Optimizer + LoRA weights**: 2.77 GB.
**총 GPU footprint 추정**: 28 + 14 + 2.77 ≈ **45 GB / 80GB** (H100 SXM).
→ batch=2 또는 seq=8192 여유 확보.

비교: full finetune 14B AdamW fp32 master = 14B·(2+4+4+4) = 196 GB → OOM. LoRA 가 **70× 절감**.

---

## 7. Day-2 적용 체크리스트 (요약)

- [x] β2=0.95, lr_warmup=100, lr=2e-4 (LoRA A/B)
- [x] bf16 autocast + fp32 master W* 동기화
- [x] m,v fp32 고정 (bnb 8-bit 금지)
- [x] param group 2분리 (decay / no_decay)
- [x] global_norm clip = 1.0 (첫 200 step 0.5)
- [x] grad/norm fp32 cast 후 계산
- [x] 192 adapter × r64 → 45 GB GPU 예산 확인

참조:
- Loshchilov & Hutter, "Decoupled Weight Decay Regularization" (ICLR 2019)
- Micikevicius et al., "Mixed Precision Training" (2018)
- project_r9_mode_collapse_20260418.md — r10 base=scratch 필수
- feedback_no_quantization.md — 8-bit Adam 비권장 경로
