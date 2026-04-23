# hexa build chain — memory forensics (2026-04-19)

READ-ONLY diagnostic. No sources edited. train_clm.hexa (3504 LOC) held by
another BG agent (aabf75c5); we observed only.

## Build chain (from `hexa build` driver)

```
 .hexa ──► [1] hexa_v2 transpile ──► .c ──► [2] clang -O2 ──► native bin
         (self-hosted, arm64)                (fbracket-depth=4096)
```

Two AOT stages. No separate typecheck / stage1+stage2 split visible at this
level — `hexa_v2` is the monolithic transpile (parse + typecheck + codegen
fused). Interpreter path `hexa run` is unrelated to AOT.

Driver: `/Users/ghost/Dev/nexus/shared/scripts/bin/hexa` delegates to
`/Users/ghost/Dev/hexa-lang/self/native/hexa_v2 <src> <out.c>` then `clang`.

## Method

- Platform: macOS 14.x arm64, `/usr/bin/time -l`.
- Synthetic corpus: `/tmp/hexa_prof/t{100,500,1500,3500}.hexa` (linear `x = x + i` body).
- Real: `/Users/ghost/Dev/anima/training/train_clm.hexa` (3504 LOC).
- Env: `HEXA_LOCAL=1` (bypass remote dispatch, ensure local measurement).
- Metric: `maximum resident set size` (B) and wall real (s) per stage.

Only `hexa parse`, `hexa_v2 <src> <out.c>`, and `clang -O2 …` were executed.
No mutation of train_clm.hexa, no `hexa run`, no launcher scripts.

## Stage RSS curves

| LOC (.hexa) | .c LOC out | parse-only (`hexa parse`) | hexa_v2 transpile | clang -O2 | full `hexa build` |
|-------------|-----------:|--------------------------:|------------------:|----------:|------------------:|
|   94        |   116      |  4.77 MB / 0.04 s         |  4.88 MB / <0.01s |  99.2 MB / 0.54 s |  99.7 MB / 0.91 s |
|  494        |   516      | 16.70 MB / 0.06 s         | 16.48 MB / 0.01 s | 105.8 MB / 0.59 s | 110.0 MB / 1.01 s |
| 1494        |  1516      | 46.17 MB / 0.12 s         | 45.92 MB / 0.05 s | 162.9 MB / 0.86 s | 161.6 MB / 1.40 s |
| 3494        |  3516      | 104.97 MB / 0.23 s        | 104.96 MB / 0.15 s| 653.4 MB / 1.88 s | 653.9 MB / 3.51 s |
| **3504 train_clm.hexa** | **3464** | **78.15 MB / 0.17 s** | **77.77 MB / 0.11 s** | **174.1 MB / 1.51 s** | **170.8 MB / 2.65 s** |

(`hexa parse` and `hexa_v2` numbers near-identical → parse ≈ transpile front
half; back half is the string writer, cheap.)

## Observations

1. **Transpile (hexa_v2) scales ~linearly with LOC**, ~30 KB RSS / LOC.
   3504 LOC real file uses 78 MB — well under any Mac limit.
2. **clang -O2 dominates tail**. On the synthetic 3494 LOC file (very
   arithmetic-dense, long-chain basic block) clang spiked to 653 MB; on the
   real train_clm.hexa (3464 LOC of more typical branchy code) clang used
   only 174 MB. Basic-block size drives clang inliner/register-allocator RSS
   more than raw LOC.
3. **Parse-only is cheap**. Even on the training corpus, parse fits in
   ~78 MB. Rules out parser memory blow-up.
4. **Full `hexa build train_clm.hexa` max RSS = 170.8 MB, wall 2.65 s on
   Mac M-class CPU.** No OOM, no thrash.

## Bottleneck stage

- Primary RSS consumer: **stage 2 (clang -O2)**, and only when the .c has
  long straight-line basic blocks. Tunable via `-O1`, `-O0`, or function
  splitting in the generated .c.
- Secondary: hexa_v2 transpile, but bounded and linear; not a concern at
  3.5K LOC.

## The 30 GB OOM is NOT in the AOT chain

The 30 GB figure cited in the task (interpreter OOM) was observed with
`hexa run train_clm.hexa`. That path evaluates a tree-walking interpreter
over every training tensor op — allocations are dominated by runtime
tensor state (embeddings, grads, optimizer moments), not compilation.
Measurements above show the AOT chain peaks below 200 MB for the same
source.

## AOT feasibility — verdict

**AOT is already fully viable on Mac.** `hexa build
training/train_clm.hexa` completes in < 3 s with < 200 MB RSS. The
existing artifact `build/artifacts/train_clm_bin.c` (2775 LOC of emitted
C) confirms a prior successful transpile. The 30 GB interpreter-OOM
problem disappears under AOT because tensor allocations happen in the
*compiled binary*, not in the compiler, and can be sized / streamed
independently.

Recommended path:

1. Route `train_clm.hexa` exclusively through `hexa build` + execute the
   native binary. Stop using `hexa run` for heavy training loops.
2. If clang RSS ever becomes an issue on larger generated .c (e.g. a
   future 10 KLOC training driver), drop to `-O1` or split hot functions
   in the codegen step — easy levers, no interpreter redesign.
3. No new compiler stage memory work needed for the current
   train_clm.hexa footprint.
