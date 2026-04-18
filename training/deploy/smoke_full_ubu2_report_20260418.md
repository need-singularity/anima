# anima 전체 .hexa smoke — ubu2 AMD farm batch

- Date: 2026-04-18 (UTC 17:06~17:15)
- Host: ubu2 (summer@192.168.50.60), AMD Ryzen 5 9600X 6c/12t, Linux 6.17
- Runner: `/tmp/hexa_v2_linux` (1.5MB) + clang -c
- Parallelism: xargs -P 6
- Wall time: ~9 min (incl. 1 hang kill)
- Mac CPU load from this task: 0% (pure offload)
- TSV: `training/deploy/smoke_full_ubu2_20260418T171520Z.tsv`

## Summary

| Metric | Value |
|---|---|
| Total .hexa scanned | 1638 |
| PASS | 1287 (78.57%) |
| FAIL_T (transpile) | 4 |
| FAIL_C (clang compile) | 347 (21.18%) |
| vs sister c0c1dc77 (78.9%) | -0.33pp (flat) |
| ubu2 peak load avg (1m) | 4.12 — healthy, no Mac cost |

Regression vs sister is negligible. Full scope (1638) now includes previously untested subtrees (anima-agent/, models/golden-moe/, models/animalm/) which are the primary FAIL_C clusters.

## FAIL_T (4 files)

| File | Reason |
|---|---|
| `experiments/consciousness/consciousness_pci.hexa` | [codegen_c2] unhandled method call: `log` |
| `experiments/consciousness/zombie_engine.hexa` | index 1 out of bounds (len 1) |
| `anima-core/verification/cvf.hexa` | index 1 out of bounds (len 1) |
| `serving/orch_or_sampler.hexa` | **HANG** — killed after >10min (transpiler infinite loop) |

`orch_or_sampler.hexa` is a new blocker not seen before — transpiler hang.

## Top FAIL_C causes (undeclared identifiers)

| Count | Symbol | Category |
|---|---|---|
| 15 | `var` | hexa-lang — keyword-as-ident leak |
| 13 | `json_parse` | runtime builtin missing |
| 10 | `u_floor` | UV micro-arith primitive |
| 10 | `shell` | runtime builtin (shell exec) |
| 9 | expected `(` | codegen syntax bug |
| 8 | `split` | runtime builtin |
| 7 | `python` | (py-call stubs — can stay broken, R37) |
| 7 | `cudaDeviceSynchronize` | CUDA (expected, not linking nvcc) |
| 5 | `xavier_init` | NN primitive |
| 5 | `u_y1` | UV primitive |
| 5 | `new_manifest` | runtime builtin |
| 5 | `LLMAdapter` (undecl fn) | module forward-decl |
| 5 | conflicting `abort` | stdlib collision |
| 4 | `tensor_zeros`, `q_hadamard`, `get_args`, `append`, `GpuClmConfig` | runtime/NN primitives |

## FAIL_C by top-level directory

| dir | FAIL_C | PASS | FAIL rate |
|---|---|---|---|
| training | 69 | 216 | 24% |
| anima-agent | 66 | 83 | 44% |
| serving | 44 | 48 | 48% |
| models | 27 | 50 | 35% |
| experiments | 25 | 184 | 12% |
| scripts | 22 | 44 | 33% |
| anima-engines | 18 | 147 | 11% |
| anima-hexad | 16 | ? | — |
| modules | 11 | ? | — |
| anima-speak | 10 | ? | — |

`anima-agent/` and `serving/` are the worst — likely share missing `json_parse`, `shell`, `LLMAdapter` intrinsics.

## Hotpath status

| File | Status | Note |
|---|---|---|
| `training/train_clm.hexa` | PASS | |
| `training/train_clm_kr.hexa` | FAIL_C | cudaDeviceSynchronize (CUDA, expected) |
| `training/train_clm_gpu.hexa` | FAIL_C | cudaDeviceSynchronize |
| `training/train_clm_gpu_v2.hexa` | FAIL_C | GpuClmConfig fwd-decl |
| `training/train_clm_emergent.hexa` | FAIL_C | conflicting `fmax` |
| `serving/serve_clm.hexa` | **FAIL_C** | `argv` undeclared — codegen bug, **blocker** |
| `serving/serve_clm_test.hexa` | PASS | |
| `serving/serve_alm.hexa` | PASS | |
| `modules/hive_bridge.hexa` | FAIL_C | conflicting `send` (libc collision) |

Live hotpath `serve_clm.hexa` fails on undeclared `argv` at line 1653 — transpiler lost `argc/argv` symbol. **New blocker**.

## Sister handoff escalation (delta from c0c1dc77 handoff)

New items for hexa-lang team:

1. **HANG — `orch_or_sampler.hexa`** (transpiler infinite loop). Reproducer: `/tmp/hexa_v2_linux serving/orch_or_sampler.hexa /tmp/out.c` never returns.
2. **`argv` undeclared in serve_clm.hexa** — codegen drops main()'s argv symbol; blocks live serving path.
3. **`var` leaked as identifier (15x)** — hexa-lang keyword not reserving in codegen.
4. **`send` / `abort` / `fmax` conflicting types** — transpiler emits builtin signatures that clash with libc. Needs `static` or renamed C symbols.
5. **`__hexa_sl_0` unknown type** — string-literal compile-time type not emitted (models/golden-moe).
6. **`HexaVal` vs `exaVal` / `ral` / `weakening` unknown types** — codegen token truncation in certain contexts.

anima-side workaround-eligible (not sister issue):
- `cudaDeviceSynchronize`, `GpuClmConfig`, nvcc intrinsics — need nvcc stage, not clang. Expected FAIL on AMD ubu2.
- `python` refs — R37 forbids; dead code to purge from anima.

## Artifacts

- TSV: `/Users/ghost/Dev/anima/training/deploy/smoke_full_ubu2_20260418T171520Z.tsv`
- This report: `/Users/ghost/Dev/anima/training/deploy/smoke_full_ubu2_report_20260418.md`
- ubu2 workdir: `/tmp/anima_full/` + `/tmp/smoke_c/` (to clean after sign-off)
