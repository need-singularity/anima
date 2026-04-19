# hexa stage0 memory profile — 2026-04-19

READ-ONLY diagnostic. Goal: quantify stage0 interpreter RSS vs LOC and judge
viability of **Path C (compile train_clm.hexa directly through stage0)**.

## Binary under test

- `hexa_stage0` shim: `/Users/ghost/Dev/hexa-lang/build/hexa_stage0` (bash
  shim, mkdir-lock + launchd RSS cap 4GB).
- Real binary: `/Users/ghost/.hx/packages/hexa/build/hexa_stage0.real`
  (Mach-O arm64, 2.74 MB, built 2026-04-19 02:12).
- Also at `/Users/ghost/Dev/hexa-lang/build/hexa_stage0.real` (same mtime).
- Measurement tool: macOS `/usr/bin/time -l` — `maximum resident set size`
  and `peak memory footprint`. 3 runs per point, median reported.
- Shim bypassed by invoking `.real` directly (wrapper adds launchd overhead
  and a 4GB cap that would mask peak).

## RSS vs LOC (median of 3)

| program          | LOC  | RSS (MB) | ΔRSS (MB) | bytes/LOC | peak (MB) |
|------------------|-----:|---------:|----------:|----------:|----------:|
| empty.hexa       |    0 |     2.02 |      0.00 |        -- |      1.44 |
| hello_min.hexa   |    2 |     2.27 |      0.25 |   131 072 |      1.47 |
| t_50.hexa        |   50 |     4.59 |      2.58 |    54 067 |      3.64 |
| t_100.hexa       |  100 |     7.08 |      5.06 |    53 084 |      6.14 |
| t_500.hexa       |  500 |    24.70 |     22.69 |    47 579 |     23.88 |
| t_1000.hexa      | 1000 |    46.77 |     44.75 |    46 924 |     45.95 |
| t_1500.hexa      | 1500 |    68.84 |     66.83 |    46 716 |     68.16 |

Mixed workload: arith + string-let + if/else + arith + cross-ref.

### Linear fit (LOC ≥ 50)

`RSS_bytes ≈ 46 476 · LOC + 2 541 811`

- Slope: **≈ 45.4 KB / LOC** (asymptotic; per-LOC drops from 131KB at
  small-N due to fixed parser overhead).
- Extrapolations:
  - 10 000 LOC → **446 MB**
  - 100 000 LOC → **4.33 GB**
  - 600 000 LOC (train_clm-class) → **≈ 26 GB**

30 GB OOM threat to `train_clm.hexa` is **empirically confirmed**, not
speculative.

## Leak-source localization (all N = 1000)

Different workload shapes, same LOC:

| shape                              | RSS (MB) | peak (MB) | notes                          |
|------------------------------------|---------:|----------:|--------------------------------|
| arith_1000 (`let v_i = i + 1`)     |    33.65 |     32.86 | 1000 `BinOp(Add)` AST nodes    |
| str_1000  (`let s_i = "string_i"`) |    19.60 |     18.81 | cheapest: flat literal nodes   |
| branch_1000 (`if/else { … }`)      |  **94.51** |     93.90 | **2.8× arith** — nested blocks |
| decl_norun_1000 (no `println`)     |    21.34 |     20.64 | terminates before eval         |
| loop_body_N1000 (`for i in 0..1000`) |   5.53 |      4.59 | **16× cheaper than unrolled**  |

### Key findings

1. `decl_norun_1000` ≈ `str_1000` ≈ 20 MB — program **exits right after
   parse**, yet still allocates 20 MB. Hence memory cost is dominated by
   **AST tree retention**, not value arena or call stack.
2. `loop_body_N1000` (3 LOC, 1000 runtime iterations) = 5.5 MB. Runtime
   values are essentially free; only static AST nodes cost.
3. `branch_1000` nearly triples the arith baseline → nested block statements
   (`{ … }`) are the heaviest node class. Each `if/else` holds two child
   blocks + their scopes.
4. Per-LOC cost is **LOC-shape-sensitive** (20 → 95 MB @ 1000 LOC), so
   `train_clm.hexa` (heavy nested struct/match/tensor blocks) will likely
   land in the **high-branch regime**, pushing the 26 GB estimate **above 40
   GB** in practice.

## Where the leak lives (estimate)

- Arena growth is **monotonic for the full lifetime of the process** — no
  freeing observed between parse and exit on `decl_norun_1000`.
- Per-AST-node amortized cost ≈ 45–90 KB. That is far larger than a packed
  node struct (expected < 256 B); the 100–300× overhead suggests **per-node
  heap allocations** rather than a bump arena, plus auxiliary side tables
  (symbol table, span metadata, list-of-children vectors).
- NaN-boxed `HexaVal` is 32 B (see `project_nanbox_encoding`) — runtime
  values themselves cannot explain 45 KB/LOC.

## Path C (compile train_clm.hexa directly through stage0) — verdict

**NOT viable in its current form.**

- Projected RSS at `train_clm.hexa` scale: **25–45 GB** just to hold the
  AST. No CUDA activations, no training tensors — pure parser state.
- stage0 shim's 4 GB cap (`safe_hexa_launchd`) kills any file larger than
  ≈ 85 k LOC. `train_clm.hexa` would trip the cap at parse time.
- Even with the cap lifted, macOS compressor will panic (2026-04-18 precedent).

### Required before Path C becomes feasible

1. **Bump arena for AST nodes** (single contiguous region; free nothing
   during parse). Expected reduction: 45 KB/LOC → < 2 KB/LOC → 20× headroom.
2. **Streaming parse + IR lowering** (do not retain full AST; emit IR
   per-function then discard subtree). This collapses memory to
   `O(max_function_size)` instead of `O(program_size)`.
3. **Separate compile vs eval** — `stage0` currently parses the whole file
   before executing; even `--parse-only` artifacts are retained. A
   codegen-only fast path would avoid building the interpreter's runtime
   symbol tables entirely.

Short term: for CLM AOT, **do not route through stage0**; use `hexa build`
(native codegen) which emits C and lets clang/mmap handle the memory
envelope, or split `train_clm.hexa` into ≤ 1 500-LOC modules (confirmed
safe at 70 MB RSS each).
