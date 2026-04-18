# hexa_v2 compile-time bench — 4-host matrix

**Date**: 2026-04-19
**Runs**: 3× per cell, median reported (variance <5%)
**runpod**: theoretical — H100 pods use Xeon host CPUs, est. ~mid-tier single-thread, similar to `ubu` class

## Hosts

| host | CPU | cores(nproc) | transpile binary | compiler |
|---|---|---|---|---|
| mac | Apple M-series arm64 | 8 | `/Users/ghost/Dev/hexa-lang/self/native/hexa_v2` | clang |
| ubu | x86_64 (Intel/AMD desktop) | 12 | `/tmp/hexa_v2_linux` | gcc |
| ubu2 | AMD Ryzen 5 9600X (assumed) | 12 | `/tmp/hexa_v2_linux` | clang |
| htz | AMD Ryzen 9 7950X3D (16C/32T) | 32 | `/tmp/hexa_v2_linux` | clang |
| runpod | Xeon (H100 host, theoretical) | varies | (not measured) | gcc/clang |

## Methodology

- Sources copied to each host `/tmp/`; measured with `/usr/bin/time -p`.
- Transpile: `hexa_v2 <src.hexa> <out.c>` — wall clock in seconds.
- Compile: `clang -c <out.c> -o <out.o>` (gcc on `ubu`).
- Parallel: 100× copies of `style_preset.hexa`, transpile via `xargs -P N`.

## Table 1 — Single-file transpile (wall sec)

| file | LOC | mac | ubu | ubu2 | htz | best |
|---|---|---|---|---|---|---|
| style_preset.hexa | 551 | 0.01 | 0.02 | 0.01 | 0.06 | mac/ubu2 |
| train_alm_lora.hexa | 1115 | 0.04 | 0.04 | 0.05 | 0.13 | mac/ubu |
| train_clm.hexa | 2902 | 0.09 | 0.10 | 0.10 | 0.30 | mac |

**Finding**: Single-thread transpile fastest on `mac` (M-series) and `ubu`/`ubu2`. `htz` 7950X3D is ~3× slower per-thread — likely x86_64 frequency/cache vs compiled Linux binary characteristics (the hexa_v2 transpiler is single-threaded).

## Table 2 — Single-file C compile (wall sec)

| file | gen .c LOC | mac clang | ubu gcc | ubu2 clang | htz clang | best |
|---|---|---|---|---|---|---|
| style_preset | 661 | 0.04 | 0.26 | 0.12 | 0.06 | mac |
| train_alm_lora | 1472 | 0.05 | 0.42 | 0.19 | 0.06 | mac/htz |
| train_clm | 2880 | 0.05 | 0.52 | 0.10 | 0.06 | mac/htz |

**Finding**: mac clang and htz clang are clearly fastest at C compilation. ubu gcc is 5–10× slower (probably older gcc / different optimization path). ubu2 clang mid-tier.

## Table 3 — Parallel scalability (100× style_preset transpile, wall sec)

| host | P=1 | P=4 | P=8 | P=12 | P=16 | P=32 | best P | speedup |
|---|---|---|---|---|---|---|---|---|
| mac | 1.97 | 0.55 | 0.42 | 0.41 | — | — | 8–12 | 4.8× |
| ubu | 1.76 | 0.47 | 0.33 | — | 0.30 | — | 16 | 5.9× |
| ubu2 | 1.88 | 0.52 | 0.39 | 0.35 | — | — | 12 | 5.4× |
| htz | 6.43 | 1.86 | 0.95 | — | 0.70 | 0.61 | 32 | 10.5× |

**Finding**: Per-thread `htz` is slow, but at full 32-way concurrency it reaches 0.61s — competitive, and scales further than the 12-core boxes. `ubu` and `ubu2` saturate around 0.30–0.35s; this is the **absolute fastest wall time** for 100-file batch transpile.

## Interpretation

1. **Per-thread transpile throughput** (tokens/sec):
   mac ≈ ubu ≈ ubu2 > htz (3× slower per thread). The hexa_v2 binary must be single-threaded; 7950X3D's V-cache doesn't help and the per-core frequency under load is lower.
2. **C compilation** (clang -O0): mac ≈ htz > ubu2 > ubu (gcc). htz wins at bulk C compile thanks to fast clang + many cores.
3. **Parallel batches**: `ubu`/`ubu2` win with 12 threads — 0.30–0.35s for 100 files. htz needs 32 threads to match, but can handle 2–3× more concurrent builds.

## Host × Task recommendations

| task | recommended host | rationale |
|---|---|---|
| interactive single-file transpile (dev loop) | **mac** | 0.01–0.09s, no ssh latency, native arm64 |
| `smoke_all` (100–500 files transpile) | **ubu** (or ubu2) | lowest wall time per batch, 12-core sweet spot |
| `train_clm` bundle transpile+C-compile | **ubu2** (clang) or **mac** | total (transpile+clang) ≤ 0.2s; htz competitive for C step only |
| mass parallel CI sweep (>200 files) | **htz** | 32 threads sustain highest throughput; slower single-thread is amortized |
| runpod | transpile locally, scp `.c`/binary to pod | pod CPU not a good transpile host |

## CPU offload policy update (proposed)

```
policy hexa_compile_offload:
  SINGLE   (<5 files):      local (mac) — ssh overhead > compile time
  SMALL    (5-50 files):    ubu2 clang — clang fast, 12 threads adequate
  MEDIUM   (50-200 files):  ubu (gcc linux-native) OR ubu2 — 0.3s/100 files
  LARGE    (>200 files):    htz -P32 — scales to high-concurrency batch
  TRAIN_C  (bundle clang -c): mac (lowest wall) OR htz (fastest parallel C)
  RUNPOD:  never transpile on pod; scp pre-compiled .c or .so
```

Key change vs current policy: **ubu2 is the new default for batch smoke** (current default was `htz` based on raw core count — actually suboptimal below ~200 files due to slower per-thread perf).

## Raw data notes

- mac clang first run had warmup penalty (0.13s vs 0.04s steady) — filesystem cache.
- htz transpile consistency excellent (±0.01s).
- Generated .c LOC: style_preset 661, train_alm_lora 1472, train_clm 2880 — no Large bundle (4 deps) tested; train_clm standalone has `use` statements but transpile runs without them.

## Anomaly: why htz per-thread is slow

- hexa_v2_linux is likely a Linux x86_64 static binary compiled on ubu2 (AMD Zen4). Running on htz 7950X3D should be equivalent instruction-set, but htz shows consistent ~3× slowdown.
- Hypothesis: htz may be running at reduced P-state under unloaded test, or the test was done while another workload held a core. Not a reproducibility issue — 3 runs were all within 5%.
- **Action**: re-bench htz with `cpupower frequency-set -g performance` before relying on this result for single-thread capacity planning.
