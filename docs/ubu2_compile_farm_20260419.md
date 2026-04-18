# ubu2 Compile Farm — 2026-04-19

Local AMD Linux box repurposed as hexa_v2 transpile + C-compile farm.
Free compute, Mac CPU offload.

## Host spec

| Field | Value |
|-------|-------|
| Hostname | `ubu2` / `summer-B650M-K` |
| IP | `192.168.50.60` (LAN) |
| User | `summer` |
| OS | Ubuntu 24.04, Linux 6.17.0-20-generic |
| CPU | AMD Ryzen 5 9600X (6-core / 12-thread, x86_64) |
| RAM | 30 GiB (15 GiB free idle) |
| Disk | 915 GiB NVMe, 847 GiB free on `/` |
| GPU | **none** (AMD iGPU only, no NVIDIA) |
| Toolchain | clang 18.1.3 (no gcc, no make by default) |

## Deployed artifacts (in `/tmp/`)

- `/tmp/hexa_v2_linux` — `build/hexa_v2_linux` from `hexa-lang`, x86_64 ELF, 1.5 MB
- `/tmp/runtime.c` — `self/runtime.c` header/runtime glue
- `/tmp/native/*.c` — 16 native C files from `self/native/` (runtime stubs, BLAS/CCL/flash/layer/lmhead)
- `/tmp/anima_smoke/` — smoke-test hexa files + generated `.c` / `.o`

## Role

| Capability | Status |
|------------|--------|
| hexa_v2 transpile (`.hexa` → `.c`) | YES |
| C compile (clang `-c`) → `.o` | YES |
| Full link → runnable binary | PARTIAL (runtime stubs must be wired) |
| Training / inference | **NO** (no GPU) |
| Parallel batch smoke compile | YES (12 threads) |

Primary use: **remote transpile + compile worker** for anima/hexa-lang source tree.
Mac stays on interactive work; ubu2 runs batch compile / `smoke_all`.

## Smoke test results (2026-04-19)

4 representative `.hexa` files rsync'd from Mac → `/tmp/anima_smoke/`, then transpiled and compiled with clang:

| File | Transpile | Compile (`clang -c`) | Time |
|------|-----------|----------------------|------|
| `nn_core.hexa` | OK | PASS | 305 ms |
| `style_preset.hexa` | OK | PASS | 151 ms |
| `train_alm_lora.hexa` | OK | PASS | 267 ms |
| `train_clm.hexa` | OK | FAIL-LINK (10 undeclared externs: `quantum_controller_*`, `phi_cache_*`) | — |

3 / 4 full PASS. `train_clm` transpile was clean (887 → 1071 lines of C); the FAIL is expected: it references runtime externs that get wired on the GPU pod at fire-time, not in a bare smoke environment.

## Usage pattern

```
# Mac: stage files
mkdir /tmp/anima_batch
cp <files...> /tmp/anima_batch/
rsync -az /tmp/anima_batch/ summer@192.168.50.60:/tmp/anima_smoke/

# ubu2: parallel transpile + compile
ssh ubu2 'cd /tmp/anima_smoke && ls *.hexa | xargs -P 12 -I{} bash -c "
  bn=\$(basename {} .hexa)
  /tmp/hexa_v2_linux {} \$bn.c \
    && clang -I/tmp -c \$bn.c -o \$bn.o \
    && echo \$bn PASS || echo \$bn FAIL
"'
```

## Constraints

- `/tmp/` only (no `/home` writes)
- `summer` user, no sudo
- no GPU → **compile/transpile only**, no CUDA/inference/training
- `.py` banned per R37 / AN13 / L3-PY (toolchain is pure hexa_v2 + clang)

## Mac offload estimate

Previously Mac ran transpile + Swift/clang for every local `.hexa` change.
Shifting batch smoke + full-tree compile to ubu2:

- **Est. 40-60 % reduction** in Mac CPU burst during `smoke_all` / `compile_all` loops
- Mac stays responsive during ALM/CLM log-watch + interactive edit
- **Zero $ cost** (LAN, always-on host)

## Future

- wire up `runtime.c` + `native/*.c` into a static lib on ubu2 → enable full link smoke, not just `-c`
- add ubu2 to `shared/config/infrastructure.json` as a compile-farm node
- `hexa shared/harness/compile_farm.hexa` entry to dispatch batches
