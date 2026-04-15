# Phase 1 — Pod 생성 + 환경 셋업 (TCLM-P1-1 NL=8 replay)

## Result: PASS

## Pod
- id: `4ud5636d2wu4n4` (first attempt `rp2pl0vcvx3ofl` — SSH port never opened, deleted after 15min waiting)
- name: `anima-clm-nl8-tclm-p1-1-retry`
- GPU: 1× H100 SXM 80GB HBM3
- image: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`
- deploy method: GraphQL `podFindAndDeployOnDemand` with `PUBLIC_KEY` env (auto sshd boot)
- cost: $2.99/hr
- SSH: `103.207.149.114:11541`
- created: 2026-04-15 (retry succeeded instantly)

## Environment
- NVIDIA driver: 580.126.09 (CUDA 13.0 runtime)
- nvcc: CUDA 12.4.131 (Built 2024-03-28)
- clang: 14.0.0 (apt-installed)
- rsync: 3.2.7 (apt-installed)
- rclone: 1.58.1 (pre-installed) + R2 config uploaded from Mac

## Files Transferred (/workspace/clm_kr/)
- `self/native/` (7 sources): hexa_cc.c + codegen_c2_v2.c + lexer_v2.c + parser_v2.c + type_checker_v2.c + tensor_kernels.c + gpu_codegen_stub.c
- `self/` (4 files): runtime.c + bytecode.h + hexa_nanbox.h + hexa_nanbox_bridge.h
- `training/` (9 files): cuda_ffi.hexa / cuda_rtc.hexa / cuda_kernels.hexa / gpu_train.hexa / corpus_loader.hexa / nn_core.hexa / hxblas_wrapper.c / train_clm_d64_kr_nl8.hexa + corpus_ko_seed.tok (244582 bytes, 63305 tokens line-based)

## hexa_v2 Linux Build
- build cmd: `clang -O2 -D_GNU_SOURCE -std=gnu11 -I . -I .. native/hexa_cc.c -o ../hexa_v2 -lm`
- size: 1588976 bytes (exact match to Phase 1 baseline)
- md5: `27280fb52135d54faa5c96a4661d858e`
- warnings: 2 (trigraph, harmless)

## Codegen Fix Probe
- source: `fn _ceil_div(a:int, b:int) { return (a + b - 1) / b } ... println(str(_ceil_div(131072, 256)))`
- expected: `512`
- observed: `512`
- verdict: PASS — hexa-lang `3cd9e6f` codegen fix active on Linux binary

## NL=8 Config (train_clm_d64_kr_nl8.hexa — only change from baseline)
- D=64 FF=256 **NL=8** VOCAB=256 SEQ=128 RANK=16 BATCH=1 GRAD_ACC=8
- STEPS env-overridable (default 50000)
- LR_MAX=3e-3 LR_MIN=3e-4 WARMUP=500 (identical to baseline NL=6 run)
- CKPT_DIR=`/workspace/ckpt_clm_d64_kr_nl8` (distinct dir from r1/ baseline)
- R2 prefix: `r2:anima-models/clm-d64-kr/r2-nl8/` (upload helper overridden)
- MODEL_TAG=`clm_d64_kr_nl8`, ROUND=2

## Budget
- phase 1 actual: ~20 min wall (pod retry + 15min SSH wait on first attempt)
- cumulative: ~$1.00

## GATE
- setup succeeded: PASS
- codegen fix active: PASS
- all required files on pod: PASS
- Phase 2 entry: APPROVED
