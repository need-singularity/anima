# ubu CUDA smoke — 20260419

## 환경
- ubu: RTX 5070 12GB, SM 12.0 (Blackwell), driver 580.126.09
- CUDA: `/usr/local/cuda-12.8/bin/nvcc` V12.8.93
- cuDNN: 9.21.0
- hexa-lang: `/Users/ghost/Dev/hexa-lang` (mount-share, uid 501)
- hexa linux: `/home/aiden/bin/hexa`

## CUDA source 탐색

| 파일 | 경로 | 노출 symbol |
|---|---|---|
| hxcuda_fused.cu | self/native/ | hxcuda_matmul_bf16, hxcuda_fused_lmhead_fwd/bwd, hxcuda_softmax_bwd, hxcuda_ce_loss_bwd, hxcuda_sync, hxcuda_device_info, hxcuda_version |
| hxcuda_stft.cu | self/native/ | hxcuda_stft_bf16, hxcuda_istft_bf16 |
| hxcuda_conv1d.cu | self/native/ | hxcuda_conv1d_bf16, hxcuda_conv1d_selftest |
| **hxblas_cuda.cu** | — | **없음** |
| **hxlmhead_cuda.cu** | — | **없음** |

## 빌드 결과 — libhxcuda.so (sm_120)

```
nvcc -arch=sm_120 -O2 --shared -Xcompiler -fPIC \
  hxcuda_fused.cu hxcuda_stft.cu hxcuda_conv1d.cu \
  -lcufft -o /tmp/libhxcuda.so
```

- 빌드 성공 (warning 2개, name linkage sdata — non-fatal)
- 크기: 1,149,560 bytes
- 설치: `/usr/local/lib/libhxcuda.so` (root:root, ldconfig OK)
- symbol 검증: `hxcuda_*` 20개 T-symbol 확인

## GPU smoke — 실행 불가 (ABI mismatch)

`/tmp/clm_r4_cpu` 바이너리가 dlsym 하는 symbol:
```
__ffi_sym_hxblas_sgemm
__ffi_sym_hxblas_attn_softmax_causal
RPATH: /Users/ghost/Dev/anima/training/build/libhxblas.dylib
       /Users/ghost/Dev/hexa-lang/self/native/build/libhxlmhead.dylib
```

libhxcuda.so 는 `hxcuda_matmul_bf16` / `hxcuda_fused_lmhead_fwd` ABI — **완전히 다른 symbol set**. hxblas_*/hxlmhead_* shim 이 존재하지 않아 drop-in 교체 불가.

GPU 경로 활성화를 위한 3개 경로:

1. **Sister hexa-lang 작업 (권장)**: `train_clm.hexa` 에 `hxcuda_matmul_bf16` FFI binding 추가 + GPU dispatch 분기 (`HXBLAS_BACKEND=cuda` env 로 선택). train_clm 재컴파일 필요.
2. **hxblas_cuda.cu shim 작성**: hxblas_sgemm/hxblas_attn_softmax_causal 시그니처 유지, 내부 cublas 호출 — **R37 deny list (.cu 생성 금지)** 로 이 agent 에서 불가. 
3. **hexa-lang GPU codegen path**: `build_train_gpu_c.hexa` 존재 — 별도 GPU 빌드 경로 조사 필요.

## 측정
- step/sec (GPU): 미측정 (smoke 불가)
- step/sec (CPU 현행, 참조): 이전 run 기준 ~0.X step/s

## 다음 단계

1. **Sister hexa-lang 작업 요청** (우선):
   - `hxblas_cuda.cu` shim 추가 (hxblas_sgemm → cublasSgemm, hxblas_attn_softmax_causal → custom kernel)
   - `hxlmhead_cuda.cu` shim (hxlmhead_fwd/bwd → cublas route)
   - 또는 `train_clm.hexa` 가 `HXBLAS_BACKEND` 분기로 hxcuda_* 직접 호출
2. **대안 — build_train_gpu_c.hexa 조사**: hexa-lang 에 이미 GPU 학습 빌드 스크립트 존재. 이 경로가 hxcuda_* ABI 로 컴파일하는지 확인 → ubu 에서 train_clm GPU 바이너리 재빌드 시도
3. **anima GPU 학습 가능 여부 (현재)**: 
   - libhxcuda.so 는 준비 완료 (sm_120)
   - train_clm 바이너리가 hxcuda_* 호출로 변경되기 전까지는 CPU-only
   - ETA: sister 작업 반나절~1일 예상

## Artifacts
- `/tmp/libhxcuda.so` (ubu, aiden owned, 1.1MB, sm_120)
- `/usr/local/lib/libhxcuda.so` (ubu, root, installed + ldconfig)
- 소스 stage: `/tmp/hxcuda_{fused,stft,conv1d}.cu` (ubu)
