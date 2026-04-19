# hxqwen14b — cuBLAS Workspace Sizing (Hopper H100, SM_90)

Date: 2026-04-19
Scope: Day-1 acceleration — workspace byte budget for cuBLASLt init in hxqwen14b.
Mode: docs/WebFetch only. No code.

## 1. NVIDIA 권장치 (Hopper SM_90)

| Source | 권장 workspace | 비고 |
|---|---|---|
| cuBLAS 13.2 docs | 32 MiB (33,554,432 B) | SM_90 권장치. H100 native kernel이 workspace 요구 증가 |
| cuBLAS 12.0 blog | ≥ 32 MiB | "highly recommended" for cuBLASLt on H100 |
| Minimum (alloc-fail 회피) | 16 KiB | GEMM 실패 방지 하한, 성능 저하 |

핵심 규칙:
- `cublasSetStream()` 호출은 workspace를 default pool로 리셋 → stream별 핸들에 `cublasSetWorkspace()` 재설정 필수.
- `(handle, stream)` 조합마다 독립 workspace 할당 (PyTorch 내부 캐시와 동일 모델).
- `CUBLAS_WORKSPACE_CONFIG=:4096:8` = 4096 KiB × 8 슬롯 = 32 MiB, determinism + 성능 병행 (PyTorch 기본값 근사치).
- `:16:8` 은 16 KiB × 8 = 128 KiB. GEMM split-K 경로 제한, Hopper에서는 회피.

## 2. Qwen2.5-14B GEMM shape 표

Config: `hidden=5120`, `intermediate=13824`, `q_heads=40`, `kv_heads=8`, `head_dim=128`, `layers=48`.
M = batch × seq (예: micro-batch 1, seq 2048 → M=2048).

| GEMM | M | K | N | FLOP/token | workspace 민감도 |
|---|---|---|---|---|---|
| Q-proj | M | 5120 | 5120 | 26.2 M | 중 (square, split-K 약함) |
| K-proj | M | 5120 | 1024 | 5.2 M | 저 (narrow N) |
| V-proj | M | 5120 | 1024 | 5.2 M | 저 |
| O-proj | M | 5120 | 5120 | 26.2 M | 중 |
| MLP gate | M | 5120 | 13824 | 70.8 M | **고** (wide N, split-K 이득) |
| MLP up   | M | 5120 | 13824 | 70.8 M | **고** |
| MLP down | M | 13824 | 5120 | 70.8 M | **고** (wide K → split-K 의존) |

결론: MLP 3종(gate/up/down)이 workspace에서 가장 큰 이득. 32 MiB 미만이면 Hopper 전용 WGMMA split-K 후보가 탈락하여 TFLOPS 20–35% 손실 가능 (cuBLAS 12.0 blog 추정치 범위).

## 3. 단일 stream vs 4 stream 분할

가정: 1 cuBLAS handle = 1 stream. 4-way concurrency (예: compute + copy + reduce + aux).

| 구성 | per-handle workspace | 총 workspace | VRAM 비중 (80GB H100) |
|---|---|---|---|
| 단일 stream | 32 MiB | 32 MiB | 0.04% |
| 2-stream | 32 MiB × 2 | 64 MiB | 0.08% |
| 4-stream | 32 MiB × 4 | 128 MiB | 0.16% |
| 4-stream (축소) | 16 MiB × 4 | 64 MiB | 0.08% (MLP split-K 일부 탈락) |

**권고**: 4-stream 전부 32 MiB 유지. 14B 파라미터 자체 28GB(BF16) + activation + optimizer 대비 128 MiB는 무시 가능 오버헤드. 축소는 MLP split-K 손실이 크므로 금지.

Determinism이 필요한 디버그 빌드에서만 `CUBLAS_WORKSPACE_CONFIG=:4096:8` 고정. 평시 학습은 핸들별 `cublasSetWorkspace(handle_i, buf_i, 32<<20)` 직접 호출.

## 4. hxqwen14b 적용 체크리스트

1. cuBLASLt init 시 preference에 `CUBLASLT_MATMUL_PREF_MAX_WORKSPACE_BYTES = 33554432` (32 MiB) 설정.
2. stream pool 생성 시 각 stream마다 32 MiB device buffer 사전 할당 후 `cublasSetWorkspace` 바인딩.
3. `cublasSetStream` 호출 직후 반드시 `cublasSetWorkspace` 재호출 (문서 경고).
4. 4-stream 구성 총 workspace 128 MiB를 VRAM budget에 명시 기입 (28 GB 모델 + KV cache와 별도 예산).
5. 16 KiB 최소치, `:16:8` 모드는 Hopper에서 사용 금지 (alloc 회피용 fallback만).

## 5. 참고

- [cuBLAS 13.2 Introduction](https://docs.nvidia.com/cuda/cublas/)
- [cuBLAS 12.0 Hopper perf blog](https://developer.nvidia.com/blog/new-cublas-12-0-features-and-matrix-multiplication-performance-on-nvidia-hopper-gpus/)
- [PyTorch CUDA semantics — workspace pool](https://docs.pytorch.org/docs/stable/notes/cuda.html)
- [Qwen2.5-14B config.json (HF)](https://huggingface.co/Qwen/Qwen2.5-14B/blob/main/config.json)
- [NVIDIA TransformerEngine cublaslt_gemm.cu](https://github.com/NVIDIA/TransformerEngine/blob/main/transformer_engine/common/gemm/cublaslt_gemm.cu)
