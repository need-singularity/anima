/* gpu_codegen_stub.c — rt#45-research scaffold
 *
 * Skeleton for the @gpu codegen backend. NO real emission — every
 * function returns a placeholder. The point of this file is to lock in
 * the C ABI between hexa_cc.c (parser/AST) and the future GPU backend
 * so the rt#45 wave-6 implementer has a fixed contract to fill in.
 *
 * Companion design: docs/rt-45-gpu-design.md
 * Roadmap entry:   shared/hexa-lang/build-toolchain.json bt#82
 *
 * This file is intentionally standalone (no hexa_cc.c headers required)
 * so it compiles with `gcc -c gpu_codegen_stub.c -o /tmp/gpu_codegen_stub.o`
 * as a smoke test.  The future implementation will replace HexaNode*
 * with the real ast node typedef from hexa_cc.c.
 */

#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -------------------------------------------------------------------------
 * Opaque types
 * -------------------------------------------------------------------------
 * In the real integration these become the actual hexa AST node and
 * string-buffer types from hexa_cc.c.  Defined as opaque structs here so
 * the stub compiles without pulling in hexa_cc.c.
 */
typedef struct HexaNode HexaNode;     /* AST node — forward decl */
typedef struct GpuStr   GpuStr;       /* growable string buffer  */

struct HexaNode {
    /* opaque — see hexa_cc.c */
    int  kind;
    void *_pad;
};

struct GpuStr {
    char  *data;
    size_t len;
    size_t cap;
};

/* -------------------------------------------------------------------------
 * GPU backend selection
 * ------------------------------------------------------------------------- */
typedef enum {
    GPU_BACKEND_NONE        = 0,
    GPU_BACKEND_PTX_DIRECT  = 1,  /* hand-rolled PTX text emit (§ 3.1) */
    GPU_BACKEND_PTX_LLVM    = 2,  /* LLVM-NVPTX (§ 3.2, preferred)     */
    GPU_BACKEND_METAL_MSL   = 3,  /* Apple Metal Shading Language       */
    GPU_BACKEND_SPIRV       = 4   /* SPIR-V (rejected for v1, § 3.3)    */
} GpuBackend;

/* Default backend — flipped at build time by the rt#45 implementer.
 * Today: NONE (research only). */
static GpuBackend g_gpu_backend = GPU_BACKEND_NONE;

void gpu_codegen_set_backend(GpuBackend b) {
    g_gpu_backend = b;
}

GpuBackend gpu_codegen_get_backend(void) {
    return g_gpu_backend;
}

/* -------------------------------------------------------------------------
 * Validation pass — § 4.2 + § 5.4
 *
 * Walks an AST node (assumed to be FnDecl with @gpu attribute) and rejects
 * anything outside the GPU subset.  Returns 1 if the function is valid,
 * 0 otherwise.  err_buf receives a human-readable diagnostic list.
 *
 * Allowlist (initial):
 *   types       : f32, f64, i32, i64, bool
 *   collections : fixed [T; N], borrowed [T]
 *   ops         : arithmetic, comparison, indexing, assignment
 *   intrinsics  : gpu_thread_id_*, gpu_block_id_*, gpu_block_dim_*,
 *                 gpu_grid_dim_*, gpu_sync, gpu_atomic_add, gpu_warp_shuffle
 *   control     : if/else, while, return
 *
 * Denylist (rejects):
 *   - String, Map, Set, dynamic List ops (.map/.filter/etc — alloc)
 *   - closures, lambda
 *   - println, file IO, system calls
 *   - dynamic dispatch / vtable / trait objects
 *   - any reference to a non-@gpu function (other than allowlisted intrinsics)
 *
 * TODO(rt#45): implement walk; today returns 1 with empty err.
 */
int validate_gpu_subset(HexaNode *fn_node, GpuStr *err_buf) {
    (void)fn_node;
    (void)err_buf;
    /* TODO(rt#45 wave 6):
     *   1. assert fn_node->kind == FnDecl
     *   2. assert "gpu" appears in fn_node attrs list
     *   3. recursive walk children: type-check params against allowlist
     *   4. walk body: reject any Call whose target is not in
     *      g_gpu_intrinsic_table or another @gpu fn
     *   5. reject any StringLit, MapLit, ListLit-with-grow ops
     *   6. on error: append "error[GPU0N]: ..." to err_buf
     */
    return 1;
}

/* -------------------------------------------------------------------------
 * PTX emission — § 3.1 / § 3.2
 *
 * Produces a PTX kernel source string for the given @gpu fn.  Caller owns
 * the returned char* and must free it.  Returns NULL on failure (use
 * validate_gpu_subset first to know why).
 *
 * TODO(rt#45): two implementations behind one signature.
 */
char *emit_ptx_kernel(HexaNode *fn_node) {
    (void)fn_node;
    /* TODO(rt#45 wave 6):
     *   if g_gpu_backend == GPU_BACKEND_PTX_DIRECT:
     *       return emit_ptx_kernel_direct(fn_node)
     *   else if g_gpu_backend == GPU_BACKEND_PTX_LLVM:
     *       return emit_ptx_kernel_via_llvm(fn_node)
     *   else: return NULL
     */
    static const char *placeholder =
        "// PTX emission not implemented — rt#45 wave 6\n"
        ".version 7.5\n"
        ".target sm_80\n"
        ".address_size 64\n"
        "// .visible .entry kernel_stub() { ret; }\n";
    char *out = (char *)malloc(strlen(placeholder) + 1);
    if (!out) return NULL;
    strcpy(out, placeholder);
    return out;
}

static char *emit_ptx_kernel_direct(HexaNode *fn_node) {
    (void)fn_node;
    /* TODO: hand-write PTX text — small AST walker, no LLVM dep.
     * Reg alloc by linear-scan over SSA names.  Documented as fallback
     * if the LLVM dep is rejected at L0 review (§ 3.5 risk 1). */
    return NULL;
}

static char *emit_ptx_kernel_via_llvm(HexaNode *fn_node) {
    (void)fn_node;
    /* TODO: emit LLVM IR as text, hand to libLLVM, target NVPTX,
     * read back PTX.  Preferred path — quality wins are 30-40% on GEMM. */
    return NULL;
}

/* -------------------------------------------------------------------------
 * Metal Shading Language emission — § 7
 *
 * Produces a .metal source string.  Not v1.  Stub here so the abstraction
 * doesn't preclude it.
 */
char *emit_metal_shader(HexaNode *fn_node) {
    (void)fn_node;
    /* TODO(future): walk AST, emit MSL.  Same validated AST as PTX path. */
    static const char *placeholder =
        "// Metal Shading Language emission not implemented (v1 = PTX only)\n"
        "#include <metal_stdlib>\n"
        "using namespace metal;\n"
        "// kernel void stub() {}\n";
    char *out = (char *)malloc(strlen(placeholder) + 1);
    if (!out) return NULL;
    strcpy(out, placeholder);
    return out;
}

/* -------------------------------------------------------------------------
 * Host-side launch shim synthesis — § 4.2 step 3
 *
 * For an @gpu kernel `fn foo(a: [f32], b: [f32]) -> [f32]`, synthesize a
 * hexa-source host wrapper:
 *
 *     fn foo_launch(grid_x, grid_y, grid_z, block_x, block_y, block_z,
 *                   a, b) {
 *         let a_dev = __cuda_memcpy_h2d(a)
 *         let b_dev = __cuda_memcpy_h2d(b)
 *         __cuda_launch("foo", grid_x, grid_y, grid_z,
 *                              block_x, block_y, block_z, a_dev, b_dev)
 *         let result = __cuda_memcpy_d2h(b_dev, len(b))
 *         __cuda_free(a_dev); __cuda_free(b_dev)
 *         return result
 *     }
 *
 * Returns hexa source text the parser will then re-ingest.
 *
 * TODO(rt#45): real impl walks fn_node->params and emits per-arg copies.
 */
char *emit_host_launch_shim(HexaNode *fn_node) {
    (void)fn_node;
    static const char *placeholder =
        "// host launch shim not implemented — rt#45 wave 6\n"
        "// fn KERNEL_launch(grid, block, ...args) { ... }\n";
    char *out = (char *)malloc(strlen(placeholder) + 1);
    if (!out) return NULL;
    strcpy(out, placeholder);
    return out;
}

/* -------------------------------------------------------------------------
 * Intrinsic table — § 5.2
 *
 * The set of pseudo-functions legal inside @gpu bodies.  Pattern-matched
 * at codegen time; never linked at runtime.
 */
typedef struct {
    const char *hexa_name;     /* what the user writes              */
    const char *ptx_pattern;   /* PTX equivalent (informational)    */
    const char *metal_pattern; /* MSL equivalent (informational)    */
} GpuIntrinsic;

static const GpuIntrinsic g_gpu_intrinsics[] = {
    { "gpu_thread_id_x",  "%tid.x",     "thread_position_in_threadgroup.x" },
    { "gpu_thread_id_y",  "%tid.y",     "thread_position_in_threadgroup.y" },
    { "gpu_thread_id_z",  "%tid.z",     "thread_position_in_threadgroup.z" },
    { "gpu_block_id_x",   "%ctaid.x",   "threadgroup_position_in_grid.x"   },
    { "gpu_block_id_y",   "%ctaid.y",   "threadgroup_position_in_grid.y"   },
    { "gpu_block_id_z",   "%ctaid.z",   "threadgroup_position_in_grid.z"   },
    { "gpu_block_dim_x",  "%ntid.x",    "threads_per_threadgroup.x"        },
    { "gpu_block_dim_y",  "%ntid.y",    "threads_per_threadgroup.y"        },
    { "gpu_block_dim_z",  "%ntid.z",    "threads_per_threadgroup.z"        },
    { "gpu_grid_dim_x",   "%nctaid.x",  "threadgroups_per_grid.x"          },
    { "gpu_sync",         "bar.sync 0", "threadgroup_barrier"              },
    { "gpu_atomic_add",   "atom.add",   "atomic_fetch_add_explicit"        },
    { "gpu_warp_shuffle", "shfl.sync",  "simd_shuffle"                     },
    { NULL, NULL, NULL }
};

int gpu_intrinsic_lookup(const char *name) {
    if (!name) return 0;
    for (int i = 0; g_gpu_intrinsics[i].hexa_name; i++) {
        if (strcmp(g_gpu_intrinsics[i].hexa_name, name) == 0) {
            return 1;
        }
    }
    return 0;
}

/* -------------------------------------------------------------------------
 * Smoke main — only compiled when GPU_CODEGEN_STUB_MAIN is defined.
 * Lets the stub double as a tiny self-test:
 *     gcc -DGPU_CODEGEN_STUB_MAIN gpu_codegen_stub.c -o /tmp/gpu_stub
 *     /tmp/gpu_stub
 * ------------------------------------------------------------------------- */
#ifdef GPU_CODEGEN_STUB_MAIN
int main(void) {
    printf("gpu_codegen_stub: backend = %d (NONE)\n", gpu_codegen_get_backend());
    printf("gpu_codegen_stub: intrinsic 'gpu_thread_id_x' known = %d\n",
           gpu_intrinsic_lookup("gpu_thread_id_x"));
    printf("gpu_codegen_stub: intrinsic 'println' known         = %d\n",
           gpu_intrinsic_lookup("println"));
    char *ptx   = emit_ptx_kernel(NULL);
    char *metal = emit_metal_shader(NULL);
    char *shim  = emit_host_launch_shim(NULL);
    printf("--- PTX placeholder ---\n%s", ptx);
    printf("--- MSL placeholder ---\n%s", metal);
    printf("--- shim placeholder ---\n%s", shim);
    free(ptx); free(metal); free(shim);
    return 0;
}
#endif
