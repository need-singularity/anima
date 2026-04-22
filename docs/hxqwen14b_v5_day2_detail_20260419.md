# hxqwen14b v5 Day-2 정밀 설계 — Backward + AdamW (READ-ONLY)

날짜: 2026-04-19
범위: v5 LoRA 학습 경로 backward graph + optimizer step
상태: 스펙 문서 (코드 변경 없음)
선행: Day-1 forward graph 완성 가정
참조: hxqwen14b_adamw_bf16_20260419.md, hxqwen14b_cublas_pattern_20260419.md,
     hxqwen14b_workspace_sizing_20260419.md

---

## 1. Forward graph 의존 전제 (Day-1)

Day-1 산출물:
- bf16 activation 체인 (embed → 40× [RMSNorm → GQA → RMSNorm → SwiGLU] → RMSNorm → lm_head)
- LoRA wrap: y = W0·x + (α/r)·B·(A·x), W0 frozen
- activation checkpointing boundary: 각 decoder layer 입구 (40 boundary)
- autocast dtype = bf16 (loss 포함 모든 matmul)
- cuBLAS handle H, stream S, workspace W (≥ 32 MiB per handle) 확보

Day-2 는 forward tape 로부터 backward 생성만 담당. forward 재실행은 checkpoint
boundary 에서만 허용.

---

## 2. Backward 수식 — LoRA-only gradient

표기: x ∈ R^{in}, y ∈ R^{out}, A ∈ R^{r×in}, B ∈ R^{out×r}, s = α/r.
Forward: y = W0·x + s·B·(A·x)
Upstream gradient: dy = ∂L/∂y ∈ R^{out}.

**Frozen base**: ∂L/∂W0 = 0 (계산 금지, tape 에서 제외).

**LoRA A gradient** (chain):
  h = A·x ∈ R^r
  ∂L/∂h = s · B^T · dy ∈ R^r
  ∂L/∂A = (∂L/∂h) ⊗ x = s · (B^T · dy) · x^T ∈ R^{r×in}

**LoRA B gradient**:
  ∂L/∂B = s · dy ⊗ h = s · dy · (A·x)^T ∈ R^{out×r}

**Input gradient** (다음 op 에 전파):
  ∂L/∂x = W0^T · dy + s · A^T · B^T · dy
        = W0^T · dy + s · A^T · (∂L/∂h)

주의:
- `A^T·(∂L/∂h)` 는 이미 (B^T·dy) scale 결과 — 중복 계산 금지.
- outer product (⊗) 는 rank-1 update → cuBLAS `sger` 대신 GEMM(M=r,N=in,K=1)
  로 배치 축 포함 처리 (batch>1 에서는 GEMM 이 압도적으로 유리).

배치 차원 확장 (B, T = batch × seq):
- x ∈ R^{B·T × in}, dy ∈ R^{B·T × out}
- ∂L/∂A = s · (dy · B)^T · x   — shape (r, in), GEMM(M=r,K=B·T,N=in)
- ∂L/∂B = s · dy^T · (x · A^T) — shape (out, r), GEMM(M=out,K=B·T,N=r)

192 adapter 전체: 각 layer 의 q/k/v/o/gate/up/down 위치에서 위 2 GEMM 쌍 수행.
GEMM 총 개수 (batch 당): 192 × 2 = 384 backward GEMM + 192 input-grad GEMM.

---

## 3. CE loss backward 통합

Loss: L = −(1/N) · Σ log softmax(z)[target]  (z = lm_head output)

1-step fused bwd (표준 softmax+CE 미분):
  p = softmax(z, axis=-1)
  ∂L/∂z = (1/N) · (p − onehot(target))

구현:
- softmax 는 forward 에서 저장하지 않음 (메모리 절약). z 를 재계산 시에는
  activation ckpt 로부터 복원.
- ignore_index (pad = −100) 마스킹: 해당 row 의 gradient = 0 → N 계산에서 제외.
- fp32 softmax, bf16 입력/출력. log-sum-exp 안정성을 위해 `z − max(z)` 선행.
- shape: z ∈ R^{B·T × V}, V=152064 (Qwen2 vocab). peak activation.

V=152064 softmax backward 메모리: B·T=4096 × 152064 × 2B(bf16) = 1.19 GB
(checkpoint 로 recompute).

---

## 4. flash-attn backward

조건: `HXQWEN14B_FLASH_ATTN` 활성 + `flash_attn_v2` 링크 가능 시.

호출: `flash_attn_bwd(dO, Q, K, V, O, L, dQ, dK, dV, causal=1, softmax_scale=1/√d_head)`
- L: forward 에서 반환된 log-sum-exp 통계 (row-wise, fp32)
- dO: upstream gradient of attention output
- dQ/dK/dV: 출력 buffer (bf16)

GQA 대응:
- Qwen2-14B: n_heads=40, n_kv_heads=8 (group=5)
- dK/dV 는 8 head 기준. Q head 는 각 group 에서 공유 K/V 를 참조했으므로
  dK/dV 는 group 내 5 Q-head 의 contribution 합산 필요 — flash-attn v2.5+ 는
  `num_heads_k` 파라미터로 자동 처리.

Fallback (flash-attn 부재):
- manual attention bwd: softmax(QK^T/√d) → recompute
- peak activation: B·H·T·T = 1·40·4096·4096 · 2B = 5.4 GB — OOM 위험
- 이 경로는 seq ≤ 2048 강제, 아니면 ABORT.

---

## 5. AdamW state layout — 192 adapters

Adapter 1개당 trainable tensor = {A, B} 2개. 192 × 2 = 384 tensor.
각 tensor 별 상태: {master_w (fp32), m (fp32), v (fp32)} = 3 fp32 copy.

**평균 adapter params**: 0.9 M (§hxqwen14b_adamw_bf16 §6)
**총 trainable**: 192 × 0.9 M ≈ 173 M params.

**VRAM 정밀 추정** (fp32 = 4 B/param):

| 항목          | dtype  | bytes | 소계      |
| ------------- | ------ | ----- | --------- |
| LoRA W        | bf16   | 2     | 346 MB    |
| Master W*     | fp32   | 4     | 692 MB    |
| Gradient      | fp32   | 4     | 692 MB    |
| m (1차 모멘트)| fp32   | 4     | 692 MB    |
| v (2차 모멘트)| fp32   | 4     | 692 MB    |
| **합계**      |        |       | **≈ 2.77 GB** |

Tensor layout:
- per-adapter struct: `{ w_bf16_ptr, master_fp32_ptr, grad_fp32_ptr, m_ptr, v_ptr, numel }`
- 384 entry flat array (AoS); step 시 linear sweep.
- 각 포인터는 cudaMalloc 단일 arena 에서 aligned offset 할당 (fragmentation 방지).

Step-wise access pattern: optimizer step 마다 5 tensor × 384 = 1920 kernel 호출
가능 → **fused AdamW kernel** 로 병합 (단일 `adamw_step<<<...>>>` 에서 pointer
array + numel array 만 전달). cuBLAS 외 전용 CUDA kernel 필요.

---

## 6. Gradient clipping (global norm = 1.0)

알고리즘 (Pascanu 2013, global):

```
1. for p in params: n_p² = sum(grad_p²) in fp32
2. global_sq = Σ_p n_p²
3. global_norm = sqrt(global_sq)
4. clip_coef = min(1.0, max_norm / (global_norm + 1e-6))
5. for p in params: grad_p *= clip_coef
```

**bf16 주의**: 제곱 합산을 bf16 로 하면 384 tensor 누적에서 1.5~3× 오차.
반드시 fp32 reduction. Kernel: `norm_sq_kernel` (atomicAdd fp32) 384회 또는
fused.

**max_norm schedule**:
- step 1~200: 0.5 (divergence 예방, r9 회귀 교훈 반영)
- step 201+: 1.0 (표준)

**순서 제약**: grad clip 은 **backward 완료 후, AdamW 진입 전**. bf16→fp32
cast 된 gradient 에 적용.

**로깅**: 매 50 step 마다 global_norm 값을 shared/state/ 에 JSON append →
모니터링 (r9/r10 재발 방지).

---

## 7. Mixed precision — bf16 activation + fp32 master

Pattern (Micikevicius 2018 O2):

| 텐서              | dtype | 메모 |
| ----------------- | ----- | ---- |
| Forward W0 (base) | bf16  | frozen, master 없음 |
| Forward LoRA A,B  | bf16  | matmul용 |
| Activation        | bf16  | autocast |
| Gradient ∂L/∂{A,B}| bf16 → fp32 cast | backward 직후 cast |
| Master W*         | fp32  | optimizer 소유 |
| m, v              | fp32  | 필수 |
| CE softmax 내부   | fp32  | log-sum-exp 안정 |
| norm_sq reduction | fp32  | clip 용 |

**Loss scaler 불필요**: bf16 exponent=8bit (fp32 와 동일 range). fp16 의
DynamicLossScaler 미사용.

**Step 말미 sync**: fp32 master → bf16 forward weight cast 를 **반드시**
실행. 미실행 시 master 만 발산, forward 는 고정 → silent bug.

**Kernel 순서** (per step):
1. forward (bf16, autocast)  — Day-1 담당
2. CE loss compute (fp32 internal)
3. backward chain (bf16 → fp32 cast on grad write)
4. global norm compute (fp32)
5. grad scale by clip_coef
6. AdamW fused kernel (fp32 read/write on master, m, v)
7. cast master_fp32 → W_bf16 (384 tensor)
8. `cudaStreamSynchronize(S)` — next iter 진입 전

---

## 8. VRAM 총계 (H100 80GB 기준)

| 구성요소                 | 크기    | 비고 |
| ------------------------ | ------- | ---- |
| Base model (14B bf16)    | 28 GB   | frozen |
| LoRA + optimizer state   | 2.77 GB | §5 |
| Activation (seq=4096, ckpt) | 12-16 GB | 40 layer boundary |
| CE softmax peak          | 1.2 GB  | recompute |
| flash-attn workspace     | 0.5 GB  | v2 |
| cuBLAS workspace         | 32 MB × N_handle | §workspace_sizing |
| **total**                | **≈ 45-50 GB** | 여유 30-35 GB |

32B scale-up 여력: base 28→64 GB 상승 → 잔여 16 GB 로 activation 압박, seq
2048 로 하향 또는 2-GPU TP.

---

## 9. 구현 체크리스트 (코드 X, 스펙만)

- [ ] Day-1 forward tape 데이터 구조 합의 (adapter id, checkpoint id, shape)
- [ ] CE fused bwd kernel 스펙 (fp32 softmax, ignore_index=-100)
- [ ] LoRA bwd GEMM batch dispatch 스펙 (M=r/N=in, M=out/N=r)
- [ ] flash-attn v2 linking 확인, GQA group 합산 경로 검증
- [ ] grad cast kernel (bf16 → fp32) 스펙
- [ ] global norm reduction kernel (fp32 atomicAdd)
- [ ] fused AdamW step kernel 스펙 (5 pointer array × 384)
- [ ] master → W bf16 cast kernel
- [ ] stream sync barrier

Day-3: 위 9개 항목 한 번에 구현 (hxqwen14b.c RC_ERR_CUDA_TODO 해제).

---

## 10. 회귀 방지 (r9/r10 mode collapse 교훈)

1. **grad clip 0.5 초기 200 step**: r9 DONE+R2업로드 후 kr_gen 붕괴 원인 =
   초반 LR × grad spike. Warmup 구간 타이트 clip 필수.
2. **norm/bias weight decay 제외**: activation 스케일 붕괴 방지.
3. **base model weight 수정 금지 assertion**: bwd 에서 W0 에 grad 흐름 검증.
4. **fp32 master/moment 강제**: bf16 저장 금지 (assertion).
5. **매 50 step global_norm 로깅**: divergence 조기 탐지.
6. **adapter 베이스 검증**: oil adapter 상속 금지 (r9 교훈 — scratch 또는
   r4 base 에서만 이어받기).

---

## 11. 참조

- `hxqwen14b_adamw_bf16_20260419.md` — AdamW 수식/하이퍼/메모리
- `hxqwen14b_cublas_pattern_20260419.md` — cuBLAS init/stream/workspace
- `hxqwen14b_gqa_20260419.md` — GQA head 구조 (flash-attn bwd 용)
- `hxqwen14b_workspace_sizing_20260419.md` — workspace 정책
- `project_r9_mode_collapse_20260418.md` — 회귀 사례
- `feedback_troubleshoot_ossified.md` — 본 문서 골화 규칙

---

End of Day-2 detail. Total lines ≈ 250.
