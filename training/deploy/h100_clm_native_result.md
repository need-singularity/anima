# CLM hexa-native CUDA — H100 deploy measurement

| 지표 | 값 |
| --- | --- |
| pod | xhq9b2c8fljdyo (216.243.220.217:17992) |
| GPU | 1x H100 SXM 80GB, CUDA 12.4, driver 580.126.09 |
| hexa_v2 Linux 빌드 | PASS (2.2MB from self/native/hexa_cc.c, patched) |
| patch #1 | hexa_cc.c:8714 tensor_from_f32_ptr 2-arg dispatch (CUDA-compose spike fix source patch propagated to C) |
| patch #2 | emitted-C regex: `<expr>; return hexa_void();` → `return <expr>;` (fn implicit-return quirk bypass) |
| patch #3 | emitted-C sed: main early `return hexa_void();` → `return 1;` (main must return int) |
| STEPS=20 transpile | PASS (5036 LOC hexa → 288KB C in 0.21s) |
| STEPS=20 compile | PASS (gcc -O2 -ldl, 817KB binary) |
| STEPS=20 실행 | PARTIAL |
| runtime (wall) | 0.94s end-to-end |
| cuda_init | PASS (cuBLAS handle, 80484 MB free, tensor cores enabled) |
| NVRTC compile | PASS (49032 bytes PTX, 12 base + 8 fused kernels) |
| rtc_get_function | PASS (20 entry points resolved) |
| init_gpu_weights | PASS (allocated + randn_fill kernels called) |
| fwd/bwd kernels | FAIL — cuLaunchKernelEx returns CUDA_ERROR_INVALID_VALUE=1 on all launches |
| kernel launch failures | 112 in 0.94s |
| GPU util (nvidia-smi dmon) | 0-1% (no kernel actually executed compute) |
| GPU mem used | ~3 GB allocated (77456/81079 MB free after alloc) |
| step 평균 (sec) | N/A (loop aborted before step log) |
| interpreter baseline (sec/step) | 0.18-3 (reference only — not re-measured) |
| native speedup | N/A (kernels did not execute) |
| 천장 도달 조건 | NOT MET |
| 판정 | progress → GAP (FFI/codegen 80% 완성, kernel-launch 파라미터 패킹만 남음) |

## 해결된 블로커
1. **briefing 스테일 정보 수정** — Mac hexa_v2 (990072 bytes) 는 briefing md5 `16d69b27...` 과 불일치. 실제 md5 `bdf61837...` (빌드 00:37). 2-arg 패치가 소스 codegen_c2.hexa:1668-1678 에만 반영되어 있고 컴파일된 바이너리에는 미반영.
2. **Linux x86_64 hexa_v2 부재** — 로컬에는 Mach-O arm64 바이너리만 존재 (build/hexa-linux-x86_64 은 2026-04-15 01:22 로 cuda 패치 이전). pod 에서 self/native/hexa_cc.c + runtime.c + 6개 native/ .c 파일을 gcc 로 재빌드.
3. **tensor_from_f32_ptr 2-arg 크래시** — `index 2 out of bounds (len 2)` 해결. hexa_cc.c:8714 에 `if len==2 return hexa_tensor_from_ptr(p, hexa_int(1), numel)` 추가.
4. **rsync 없음** — tar-pipe 로 대체.
5. **codegen 생성 main 이 int return 요구** — sed 로 `return hexa_void();` → `return 1;` (4469-4802 라인 범위).
6. **codegen 생성 fn implicit-return 미지원** — `<expr>; return hexa_void();` → `return <expr>;` 정규식 패치. 1020 바이트 감소.

## 남은 블로커 (breakthrough 전제조건)
1. **cuLaunchKernelEx INVALID_VALUE** — self/ml/cuda_rtc.hexa:448 rtc_launch_shmem. params_buf 배열 구축 (line 450-455) 또는 CUlaunchConfig struct (line 457-467) 의 바이트 레이아웃이 CUDA 12.4 기대와 불일치 추정. 가능성:
   - `args_array[i]` 가 이미 포인터 아닌 HexaVal wrapper — `ptr_addr` 이 포인터 값 아닌 tag 를 반환
   - shmem_bytes=0 이어야 하는데 hexa_int wrapping 누락
   - CUlaunchConfig 의 numAttrs 오프셋 (byte 48 이 아닌 44?) — CUDA 12.4 struct layout 재검증 필요
2. **"array[0]: container is not an array (tag=0)"** — args_array 중 하나가 빈 HexaVal 로 전달됨. init_gpu_weights 의 randn_fill 인자 구축 시 1회, training loop 중 수십회. 실제 커널 실행 전제.

## 다음 스텝 (outside this 30-min window)
- cuda_rtc.hexa:rtc_launch_shmem 에 디버그 println 삽입 → args_array 각 원소의 ptr_addr / tag 검증
- CUlaunchConfig 바이트 레이아웃을 CUDA 12.4 cuda.h 와 일치 확인 (sizeof(CUlaunchConfig) 58-byte?)
- shmem=0 경로 vs shmem>0 경로 분리 테스트로 cfg struct 인코딩 축소

## 산출물 구성
- `h100_clm_native_run.log` — 148 라인, 파이프라인 전 단계 로그
- `h100_clm_native_dmon.log` — nvidia-smi dmon 스냅샷 (SM util 0%, 컴퓨트 미실행 확인)
- `h100_clm_native_result.md` — 본 파일
- pod `/workspace/cuda_native/` 보존 — 후속 디버그용

## Budget/cost
- 실행 시간 < 25분 (pod $1.25)
- pod 삭제 안함 — 후속 세션에서 kernel-launch 이슈 30분 내 해소 가능한 상태로 유지
