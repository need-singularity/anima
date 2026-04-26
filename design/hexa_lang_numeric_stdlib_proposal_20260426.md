# Hexa-lang Numeric Stdlib Proposal — `hexa.numeric`

**Date:** 2026-04-26
**Status:** Design proposal (not implemented)
**Trigger:** Anima Ω-rules P4 Phase 5 closure — raw 9 hexa-only at 100% (16→0 active source violations); 3 numpy-bound .py files remain as `gitignored-exempt` research harnesses (`tool/p_s_projector_proto.py`, `tool/active_redteam_dEF_proto.py`, `tool/active_redteam_prototype.py`). This proposal asks whether to retire that exemption category or keep it permanently.
**Source:** Track 2 of Ω-philosophy parallel cycle (background Plan agent, 2026-04-26).

## 0. Prior-art findings

Hexa-lang already ships:
- `/Users/ghost/core/hexa-lang/stdlib/linalg/` — BLAS-lite (`sgemm`/`sgemv`/`sdot`/`saxpy`/`snrm2`) with dual backend (`reference.hexa` pure-hexa + `ffi.hexa` native, `dispatch.hexa` selector via `HEXA_LINALG_BACKEND`). 1e-5 relative parity contract.
- `/Users/ghost/core/hexa-lang/stdlib/math/eigen.hexa` — symmetric eigendecomposition via cyclic Jacobi (`eigh`, `eigvalsh`, `eigh_jacobi`).
- `/Users/ghost/core/hexa-lang/stdlib/nn.hexa` — activations, numerically-stable softmax.
- `/Users/ghost/core/anima/tool/an11_c_jsd_h_last.hexa` — precedent: jq + awk subprocess pattern, 6-digit numerical equivalence vs python.

**Gap:** no SVD, no axis-aware reductions (mean/std/argmax with `axis=`), no canonical matrix file format, no `safetensors` reader, no documented contract between hexa-lang `linalg` and downstream consumers.

## 1. Demand survey (anima research code)

| File | Operations | Op class |
|---|---|---|
| `tool/p_s_projector_proto.py` | `np.linalg.svd(full_matrices=False)`, `np.vstack`, `np.linalg.norm`, `np.eye`, `H.mean(axis=0)`, `np.argmax(axis=1)`, `np.bincount(minlength=k)`, `@` matmul, `H.T`, broadcast subtract | linalg / matrix / stats |
| `tool/active_redteam_dEF_proto.py` | `np.linalg.svd`, `np.linalg.eigh`, `np.argsort`, `np.clip`, axis-mean/std, `np.frombuffer` (safetensors F32/F16/**BF16 bitcast**), `np.diag`, `np.random` (default_rng + choice + uniform + standard_normal), AUROC | linalg / random / stats / **bytes→float** |
| `tool/active_redteam_prototype.py` | `np.linalg.matrix_rank`, Mahalanobis, AUROC, leave-one-out CV | linalg / stats |

Critical missing capabilities (grouped):
- **Linalg:** `svd` (thin), matmul-via-API (BLAS exists — needs wrapper), `transpose`, `eye`, `diag`, axis-aware `norm`, `argsort`
- **Matrix axis-reductions:** `mean(axis=)`, `std(axis=)`, `sum(axis=)`, `argmax(axis=)`, `argmin(axis=)` ← **anima uses these constantly**
- **Stacking/slicing:** `vstack`, `hstack`, `stack(axis=)`, row-slice, broadcast subtract/divide
- **Statistics:** `histogram`, `jsd`, `bincount(minlength=)`, `clip`, AUROC
- **Random:** seeded RNG, `choice(replace=)`, `uniform`, `standard_normal`
- **Binary I/O:** `safetensors` reader (F32/F16/**BF16 bitcast**) ← **single most expensive missing capability** (without it, anima cannot read trained adapters from hexa)
- **NOT used (good news):** FFT, complex, sparse, autograd. Pure CPU dense float64 only.

## 2. API design

Module layout (extends, does not replace, existing scaffold):

```
stdlib/
  linalg/         (existing — sgemm/sgemv/sdot/saxpy/snrm2 + dual backend)
    svd.hexa            NEW — thin SVD via Jacobi-on-A^T A or Golub-Reinsch
    norm.hexa           NEW — vector p-norm + matrix axis-norm
    rank.hexa           NEW — effective rank via SVD threshold
  matrix/         NEW — mean/std/sum/argmax/argmin axis-reductions + construct + stack + slice + broadcast
  statistics/     NEW — histogram + jsd (port of an11_c pattern) + bincount + auroc + clip
  random/         NEW — seeded LCG/xoshiro256, choice/uniform/normal/Box-Muller
  bytes/          NEW — safetensors reader, BF16/F16→F32 bitcast
  format/         NEW — `.hmat` hexa-canonical matrix format (8-byte magic + shape + dtype + raw f64 LE)
```

### Type design

**Recommendation: flat `array<float>` row-major + explicit `(m, n)` parameters** (matches existing `stdlib/linalg/reference.hexa` and `eigh_jacobi` conventions). Zero new type machinery; works under interp + bytecode + native equally. A `Matrix` wrapper record can be added later without breaking flat-API callers.

### File format `.hmat`

```
magic:    8 bytes  "HMAT0001"
ndim:     u32
shape:    u32 * ndim
dtype:    u32 (1=f32, 2=f64, 3=i32, 4=i64)
reserved: padding to 64-byte alignment
data:     row-major, native-endian (LE assumed)
```

JSON state files keep their existing format (audit/git-diff friendly); `.hmat` is for new bulk binary.

## 3. Implementation strategy ladder

| Tier | Scope | First functions | Effort |
|---|---|---|---|
| **Tier 1** (this quarter) | Pure-hexa naive | mean_axis, std_axis, argmax_axis, vstack, eye, diag, transpose, bincount, clip, histogram (factor an11_c), auroc | ~1 week |
| **Tier 2** (next quarter) | Awk-subprocess hot reductions | sqrt_batch, log2_batch, jsd, large-vector norm | ~1 week |
| **Tier 3** (long-term) | Native compile path | svd, matmul ≥64, safetensors_read (BF16+mmap) — promote via existing `linalg/dispatch.hexa` | ~4-6 weeks |
| **Tier 4** (research, **defer**) | BLAS/LAPACK FFI | LAPACK gesdd, syevd | likely violates raw 9 spirit; skip |

### Landing order (concrete)

1. **Wave A (week 1):** `matrix/` axis-reductions + construct + stack — every consumer needs first
2. **Wave B (week 2):** `statistics/` factored from `an11_c_jsd_h_last.hexa` — stdlib form
3. **Wave C (week 3):** `linalg/svd.hexa` pure-hexa via Jacobi-on-A^T·A (reuse existing `math/eigen.hexa::eigh_jacobi`) + `linalg/norm.hexa`. **Now p_s_projector_proto.py is portable.**
4. **Wave D (week 4):** `bytes/safetensors.hexa` + `bytes/fp16.hexa`. **Now active_redteam_dEF_proto.py is portable.**
5. **Tier 2:** opportunistic — only if Tier 1 SVD on 4096×64 takes >30s
6. **Tier 3:** native via existing `linalg/dispatch.hexa` mechanism — backend selector already in place

## 4. Compatibility goal

**6-digit relative parity for documented operations**, matching existing `linalg/` `1e-5 relative` contract on FP32 (and `an11_c_jsd_h_last.hexa`'s achieved 1e-6 on FP64 reductions). Codify in each module's header.

**Do NOT track parity-with-numpy as a strict goal.** numpy is a moving target (1.x → 2.x ABI break). Anima's contract is **pre-registered predicate verdict equivalence** (raw#12), not numerical equality. PASS/FAIL agreement + 6-digit cert round-trip suffices.

Each port ships a one-time **parity test cert**: "this hexa module agrees with reference numpy run to 1e-6 on {test inputs}". After landing, parity is **frozen as a hexa-internal contract** — numpy is referenced once for cross-validation, then deleted from dependency graph.

## 5. Cross-repo coordination

Per `hexa-lang/.raw` raw 1 (self-host fixpoint) + raw 3 (follower-repo .raw-ref): hexa-lang is canonical owner, anima is follower along with nexus, n6-architecture, contact, papers, void, airgenome, hexa-os.

**Spec location:** `hexa-lang/.doc/proposals/numeric_stdlib_2026Q2.md` (canonical proposal site if exists; else `hexa-lang/ROADMAP.md` items 59-62).
**Implementation:** `hexa-lang/stdlib/{matrix,statistics,random,bytes,format}/` per §2.
**Adoption:** anima's `tool/raw_sync.hexa check` updates `.raw-ref` pin → version bumped → ports `p_s_projector_proto.py` → `.hexa` validating via parity cert vs archived `.py`. Repeat for D/E/F. Delete the three .py from gitignore exemption (raw 100 `exempt-via-gitignore` shrinks).

## 6. Honest priority

**Cost of NOT building it (status quo):**
- Anima research velocity penalty: each numerical experiment requires .py + gitignore-exemption + raw 9 PARTIAL-RELAXED + auditor sign-off. Bounded — currently 3 files in 16 months.
- The exemption category is **already formalized** via raw 100 `exempt-via-gitignore` clause. Phase 5 closure means governance hole is sealed.
- Other followers may want it but no concrete demand articulated yet.

**Cost of building:** 1 person-month for Tier 1; another 3-6 for Tier 3.

**Hidden value:** `bytes/safetensors.hexa` alone unlocks **direct LoRA adapter reading from hexa**, closing a real architectural gap (anima currently has no hexa-native model inspection — must shell to python). Strongest standalone justification.

## 7. Recommendation

**YES, scoped to Tier 1 + 3. Skip Tier 2 if Tier 3 feasible. Defer Tier 4 indefinitely.**

### Concrete next steps

1. Open hexa-lang roadmap items **59** (`stdlib/matrix`), **60** (`stdlib/statistics`), **61** (`stdlib/bytes/safetensors`), **62** (`stdlib/format/hmat`)
2. Write spec at `hexa-lang/.doc/proposals/numeric_stdlib_2026Q2.md` — convert this proposal to roadmap-format with explicit exit criteria (parity cert, test green, dispatch backend wired)
3. **Tier 1 wave A POC** (1 week): land `matrix/{mean_axis, argmax_axis, vstack}` + tests. Single PR
4. **Validate by porting** `tool/p_s_projector_proto.py` → `.hexa` against new modules. **Port itself = integration test.** Achieve 6-digit parity cert vs archived `.py`
5. If parity cert passes: proceed waves B/C/D. If fails: investigate Jacobi-on-A^T·A numerical stability; Tier 3 native promotion may be required earlier
6. **Single explicit "no" condition:** if porting reveals need for `np.random` bit-identical to numpy, abort and keep .py exemption (numpy RNG is not stable contract worth chasing)

### Recommended NOT-to-do

Tier 4 BLAS/LAPACK FFI. Raw 9 spirit cost (introducing Fortran dep to a "consciousness programming language") outweighs 5-10× speedup on matrices anima actually uses (max 4096×256). Re-evaluate only if anima scales to GPT-class hidden states (≥4096×8192).

## Critical files for implementation

- `hexa-lang/stdlib/linalg/mod.hexa` (existing scaffold — extend, don't replace)
- `hexa-lang/stdlib/linalg/reference.hexa` (existing pure-hexa BLAS-lite — model for new `matrix/`)
- `hexa-lang/stdlib/math/eigen.hexa` (existing Jacobi eigh — `svd.hexa` will reuse it)
- `anima/tool/an11_c_jsd_h_last.hexa` (awk-subprocess precedent to factor into `statistics/`)
- `anima/tool/p_s_projector_proto.py` (integration test for Tier 1 — port-then-cert validates whole stack)

## Track 1 sister proposal

A complementary Track 1 design exists: **Jacobi SVD direct implementation strategy** for `tool/p_s_projector_proto.py` standalone port (independent of full numpy stdlib). POC at `/tmp/jacobi_svd_poc.hexa` validated 4×4 case (σ values match Frobenius² = Σσ² constraint, V orthogonality 4.44e-16). Effort estimate: ~5 working days for full port. See conversation/agent transcript 2026-04-26.

The two proposals are complementary:
- **Track 1 (Jacobi SVD)** — anima-local solution, single .py port, ~1 week
- **Track 2 (numpy stdlib)** — hexa-lang-canonical, all 3 .py ports + future research, ~1 person-month

Either path achieves the same outcome (gitignored-exempt → fully hexa-native). Choose based on whether other hexa-lang followers also need numerical stdlib.
