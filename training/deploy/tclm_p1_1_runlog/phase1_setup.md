# Phase 1 — Pod 생성 + 환경 셋업 (TCLM-P1-1)

## Result: PASS

## Pod
- id: `1808yzai60zq9m`
- name: `anima-clm-d64-kr-tclm-p1-1`
- GPU: 1× H100 SXM 80GB HBM3
- image: `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`
- cost: $2.99/hr
- SSH: `64.247.201.32:11090`
- created: 2026-04-16 (pod uptime <1m at phase start)

## Environment
- NVIDIA driver: 580.126.09 (CUDA 13.0 runtime)
- nvcc: CUDA 12.4.131 (Built 2024-03-28)
- clang: 14.0.0 (apt-installed)
- rsync: 3.2.7 (apt-installed)
- ram: 2015G total, 1842G available
- disk: 60G overlay, 60G free

## Files Transferred (/workspace/clm_kr/)
- `hexa_native/` — hexa_cc.c + 5 supporting .c sources (codegen_c2_v2, lexer_v2, parser_v2, tensor_kernels, type_checker_v2, gpu_codegen_stub)
- `hexa_self/` — runtime.c + 3 nanbox headers (bytecode.h, hexa_nanbox.h, hexa_nanbox_bridge.h)
- `cuda_ffi.hexa` `cuda_rtc.hexa` `cuda_kernels.hexa` `gpu_train.hexa` (from hexa-lang/self/ml/, current codegen-fix variant)
- `corpus_loader.hexa` `nn_core.hexa` `hxblas_wrapper.c` (from anima/training/)
- `train_clm_d64_kr.hexa` (new d=64 variant — STEPS env-overridable)
- `corpus_ko_seed.tok` — 63305 bytes Korean byte-level corpus (restored from holo_breakthrough_20260416 backup)

## hexa_v2 Linux Build
- build cmd: `clang -O2 -D_GNU_SOURCE -std=gnu11 -I . -I . native/hexa_cc.c -o ../hexa_v2 -lm`
- size: 1588976 bytes
- md5: `69ed7826e1cef4ec135ebbaa3e359768`
- warnings: 2 (trigraph, harmless)

## Codegen Fix Probe (Critical)
- source: `fn _ceil_div(a:int, b:int) { return (a + b - 1) / b } ... println(str(_ceil_div(131072, 256)))`
- expected: `512` (post-codegen-fix — untyped fn tail-return)
- observed: `512`
- verdict: PASS — hexa-lang 3cd9e6f codegen fix active on Linux binary

## d=64 Config (train_clm_d64_kr.hexa)
- D=64 FF=256 NL=6 VOCAB=256 SEQ=128 RANK=16 BATCH=1 GRAD_ACC=8
- STEPS env-overridable (default 50000; phase 2 = 20, phase 3 = 500, phase 4 = 50000)
- LR_MAX=3e-4 LR_MIN=3e-5 WARMUP=500
- R2 prefix: `r2:anima-models/clm-d64-kr`

## Budget
- phase 1 budget: 30min / $1.50
- actual: ~8 min wall + pod setup overhead → ~$0.40
- cumulative: ~$0.40

## GATE
- setup succeeded: PASS
- codegen fix active: PASS
- all required files on pod: PASS
- Phase 2 entry: APPROVED
