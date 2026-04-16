// ═══════════════════════════════════════════════════════════
//  HEXA C Runtime Library — Phase 5 self-hosting support
//  Provides: tagged values, strings, arrays, maps, GC
// ═══════════════════════════════════════════════════════════

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <math.h>
#include <ctype.h>
#include <dlfcn.h>
#include <time.h>
#include <unistd.h>

// ═══════════════════════════════════════════════════════════
//  Optimization #11: String Interning
//  Hash-set of unique strings. Short strings (< 64 chars)
//  are interned; comparison becomes pointer equality (==).
//  Lazily initialized on first hexa_intern() call.
// ═══════════════════════════════════════════════════════════

#define INTERN_INIT_CAP   256
#define INTERN_MAX_LEN    64
#define INTERN_LOAD_MAX   75   // percent

static uint32_t hexa_fnv1a(const char* s, size_t len) {
    uint32_t h = 2166136261u;
    for (size_t i = 0; i < len; i++) {
        h ^= (uint8_t)s[i];
        h *= 16777619u;
    }
    return h;
}

// Also used by the hash-map (#10)
static uint32_t hexa_fnv1a_str(const char* s) {
    uint32_t h = 2166136261u;
    for (; *s; s++) {
        h ^= (uint8_t)*s;
        h *= 16777619u;
    }
    return h;
}

typedef struct {
    char** buckets;      // array of interned string pointers (NULL = empty)
    uint32_t* hashes;    // cached hash per slot
    int cap;             // power-of-2 capacity
    int count;           // number of occupied slots
} HexaInternTable;

static HexaInternTable __hexa_intern = {NULL, NULL, 0, 0};

static void hexa_intern_init(void) {
    __hexa_intern.cap = INTERN_INIT_CAP;
    __hexa_intern.count = 0;
    __hexa_intern.buckets = (char**)calloc(INTERN_INIT_CAP, sizeof(char*));
    __hexa_intern.hashes  = (uint32_t*)calloc(INTERN_INIT_CAP, sizeof(uint32_t));
}

static void hexa_intern_grow(void) {
    int old_cap = __hexa_intern.cap;
    char** old_buckets = __hexa_intern.buckets;
    uint32_t* old_hashes = __hexa_intern.hashes;
    int new_cap = old_cap * 2;
    char** new_buckets = (char**)calloc(new_cap, sizeof(char*));
    uint32_t* new_hashes = (uint32_t*)calloc(new_cap, sizeof(uint32_t));
    uint32_t mask = (uint32_t)(new_cap - 1);
    for (int i = 0; i < old_cap; i++) {
        if (old_buckets[i]) {
            uint32_t idx = old_hashes[i] & mask;
            while (new_buckets[idx]) idx = (idx + 1) & mask;
            new_buckets[idx] = old_buckets[i];
            new_hashes[idx] = old_hashes[i];
        }
    }
    free(old_buckets);
    free(old_hashes);
    __hexa_intern.buckets = new_buckets;
    __hexa_intern.hashes  = new_hashes;
    __hexa_intern.cap = new_cap;
}

// Intern a string: returns a canonical pointer.
// If the string is already interned, returns the existing pointer.
// Only interns strings shorter than INTERN_MAX_LEN.
// The returned pointer is owned by the intern table -- callers must NOT free it.
static const char* hexa_intern(const char* s) {
    if (!s) return s;
    size_t slen = strlen(s);
    if (slen >= INTERN_MAX_LEN) return NULL;  // too long, skip interning

    // Lazy init
    if (!__hexa_intern.buckets) hexa_intern_init();

    uint32_t h = hexa_fnv1a(s, slen);
    uint32_t mask = (uint32_t)(__hexa_intern.cap - 1);
    uint32_t idx = h & mask;

    while (__hexa_intern.buckets[idx]) {
        if (__hexa_intern.hashes[idx] == h &&
            strcmp(__hexa_intern.buckets[idx], s) == 0) {
            return __hexa_intern.buckets[idx];  // already interned
        }
        idx = (idx + 1) & mask;
    }

    // Not found -- insert
    if (__hexa_intern.count * 100 / __hexa_intern.cap >= INTERN_LOAD_MAX) {
        hexa_intern_grow();
        // Recompute slot after grow
        mask = (uint32_t)(__hexa_intern.cap - 1);
        idx = h & mask;
        while (__hexa_intern.buckets[idx]) idx = (idx + 1) & mask;
    }

    char* dup = strdup(s);
    __hexa_intern.buckets[idx] = dup;
    __hexa_intern.hashes[idx]  = h;
    __hexa_intern.count++;
    return dup;
}

// Forward declarations for all runtime functions
typedef struct HexaVal HexaVal;
HexaVal hexa_add(HexaVal a, HexaVal b);
HexaVal hexa_sub(HexaVal a, HexaVal b);
HexaVal hexa_mul(HexaVal a, HexaVal b);
HexaVal hexa_div(HexaVal a, HexaVal b);
HexaVal hexa_mod(HexaVal a, HexaVal b);
HexaVal hexa_eq(HexaVal a, HexaVal b);
HexaVal hexa_to_string(HexaVal v);
HexaVal hexa_str_concat(HexaVal a, HexaVal b);
HexaVal hexa_abs(HexaVal v);
HexaVal hexa_pad_left(HexaVal s, HexaVal width);
HexaVal hexa_pad_right(HexaVal s, HexaVal width);
HexaVal hexa_str_repeat(HexaVal s, HexaVal n);
HexaVal hexa_read_file(HexaVal path);
HexaVal hexa_write_file(HexaVal path, HexaVal content);
HexaVal hexa_str_split(HexaVal s, HexaVal delim);
HexaVal hexa_str_trim(HexaVal s);
HexaVal hexa_str_replace(HexaVal s, HexaVal old, HexaVal new_s);
HexaVal hexa_str_join(HexaVal arr, HexaVal sep);
HexaVal hexa_str_to_upper(HexaVal s);
HexaVal hexa_str_to_lower(HexaVal s);
HexaVal hexa_str_chars(HexaVal s);
HexaVal hexa_format_n(HexaVal fmt, HexaVal args);
HexaVal hexa_str_parse_int(HexaVal s);
HexaVal hexa_str_parse_float(HexaVal s);
// NET I/O forward decls (socket FFI for HTTP serving)
HexaVal hexa_net_listen(HexaVal addr_port);
HexaVal hexa_net_accept(HexaVal listener_fd);
HexaVal hexa_net_read(HexaVal fd_val);
HexaVal hexa_net_write(HexaVal fd_val, HexaVal data);
HexaVal hexa_net_close(HexaVal fd_val);
HexaVal hexa_str_trim_start(HexaVal s);
HexaVal hexa_str_trim_end(HexaVal s);
HexaVal hexa_str_slice(HexaVal s, HexaVal start, HexaVal end);
HexaVal hexa_str_bytes(HexaVal s);
HexaVal hexa_array_slice(HexaVal arr, HexaVal start, HexaVal end);
HexaVal hexa_array_map(HexaVal arr, HexaVal fn);
HexaVal hexa_array_filter(HexaVal arr, HexaVal fn);
HexaVal hexa_array_fold(HexaVal arr, HexaVal init, HexaVal fn);
HexaVal hexa_array_index_of(HexaVal arr, HexaVal item);
HexaVal hexa_array_new(void);
HexaVal hexa_void(void);
HexaVal hexa_null_coal(HexaVal a, HexaVal b);
int hexa_is_type(HexaVal v, const char* type_name);
// rt 32-A: bulk struct constructor (see below for docstring).
HexaVal hexa_struct_pack_map(const char* type_name, int n,
                             const char* const* keys, const HexaVal* vals);
// rt 32-B: scratch-buffer primitives for reusable args vector (NK_CALL path).
HexaVal hexa_array_push_nostat(HexaVal arr, HexaVal item);
HexaVal hexa_val_snapshot_array(HexaVal v);  // rt#32-N forward decl
HexaVal hexa_array_slice_fast(HexaVal arr, HexaVal start, HexaVal end);

// RT-P3-1 wrapper shims — tagged-value → C-native conversion for codegen regen
// path. Close Wint-conversion / Wpointer-arith categories in the
// interpreter.hexa → .c baseline. See self/runtime_hexaval_DESIGN.md
// §Production runtime (live).
int64_t     hexa_as_num(HexaVal v);
const char* hexa_to_cstring(HexaVal v);
const char* hexa_str_as_ptr(HexaVal v);

// rt 32-G Phase 0: flat Val struct forward decls (implementation below).
// NOTE: parameter-less typedef stays outside so the struct body later in
// this file keeps using the same name. Function decls reference HexaVal
// (defined below) and the fully-defined HexaValStruct — OK because the C
// compiler only needs full types at call sites, not at forward decls.
typedef struct HexaValStruct HexaValStruct;
// Redesign: only the _v variant is exposed. All non-scalar arguments are
// passed as HexaVal so polymorphic payloads (closures, AST bodies, struct
// field maps) survive verbatim instead of being coerced to "".
HexaVal hexa_valstruct_new_v(HexaVal, HexaVal, HexaVal, HexaVal, HexaVal,
    HexaVal, HexaVal, HexaVal, HexaVal, HexaVal, HexaVal, HexaVal);
HexaVal hexa_valstruct_tag(HexaVal v);
HexaVal hexa_valstruct_int(HexaVal v);
HexaVal hexa_valstruct_float(HexaVal v);
HexaVal hexa_valstruct_bool(HexaVal v);
HexaVal hexa_valstruct_str(HexaVal v);
HexaVal hexa_valstruct_char(HexaVal v);
HexaVal hexa_valstruct_array(HexaVal v);
HexaVal hexa_valstruct_fn_name(HexaVal v);
HexaVal hexa_valstruct_fn_params(HexaVal v);
HexaVal hexa_valstruct_fn_body(HexaVal v);
HexaVal hexa_valstruct_struct_name(HexaVal v);
HexaVal hexa_valstruct_struct_fields(HexaVal v);
HexaVal hexa_valstruct_get_by_key(HexaVal v, const char* key);
HexaVal hexa_valstruct_set_by_key(HexaVal v, const char* key, HexaVal val);

// rt#37: inline cache for obj.field — the struct is defined here so every
// generated C file (via #include "runtime.c") can declare `static HexaIC`
// slots. The lookup itself is defined below as `static inline`.
typedef struct HexaIC {
    void* keys_ptr;   // last-seen m.map.keys pointer (shape id)
    int   len;        // last-seen m.map.len
    int   idx;        // cached field offset
    uint64_t hits;
    uint64_t misses;
} HexaIC;

// ── Tagged Value ─────────────────────────────────────────
// All HEXA values are represented as tagged unions (NaN-boxing alternative)

typedef enum {
    TAG_INT = 0, TAG_FLOAT, TAG_BOOL, TAG_STR, TAG_VOID,
    TAG_ARRAY, TAG_MAP, TAG_FN, TAG_CHAR, TAG_CLOSURE,
    // rt 32-G Phase 0: flat C struct replacement for interpreter `Val` map.
    // Val is the interpreter's tagged value carrier — ~3.37M constructions
    // per d64 200-step run. Each map-backed Val = 1 map_new + 12 map_set =
    // 13 hash-table insertions. Replacing with a flat 12-field C struct
    // collapses that to a single heap alloc, eliminating 7GB+ RSS pressure.
    // Fields mirror `struct Val` in self/hexa_full.hexa exactly (12 fields).
    TAG_VALSTRUCT
} HexaTag;

// ── Optimization #10: Hash-map backing store ─────────────
// Open-addressing hash table (Robin Hood not needed at this scale).
// Stored on the heap; the HexaVal map union holds a pointer + len.
// Keeps a parallel insertion-order array for keys()/values()/iter.

#define HMAP_INIT_CAP   16
#define HMAP_LOAD_MAX   75  // percent

typedef struct {
    char*  key;       // owned string (strdup'd) -- NULL means empty slot
    uint32_t hash;    // cached FNV-1a of key
} HexaMapSlot;

typedef struct {
    HexaMapSlot* slots;   // hash table (power-of-2 sized)
    struct HexaVal* vals;  // parallel values array (same indices as slots)
    int ht_cap;            // hash table capacity (power-of-2)

    // Insertion-order arrays for keys()/values()/for-in iteration
    char** order_keys;     // ordered key pointers (point into slots[].key)
    struct HexaVal* order_vals; // ordered values
    int len;               // number of entries
    int order_cap;         // allocated capacity for order arrays
    // rt 32-L: Val-arena support. When non-zero, this table + its slot/val/
    // order arrays were allocated from the bump arena (NOT malloc). Such tables
    // MUST be heapified before they outlive the current scope; otherwise an
    // arena rewind invalidates the backing storage. Slots' .key strings are
    // ALWAYS strdup'd (heap) regardless of from_arena, because the arena is
    // bulk-rewound and per-string lifetime tracking is impractical here.
    int from_arena;
} HexaMapTable;

// HexaVal must be defined before HexaValStruct so that HexaValStruct's
// HexaVal-by-value fields (rt 32-G redesign) have a complete type. HexaVal
// only needs HexaValStruct as a *pointer* (.vs), so the forward decl above
// (typedef struct HexaValStruct HexaValStruct) is sufficient here.
typedef struct HexaVal {
    HexaTag tag;
    union {
        int64_t i;
        double f;
        int b;
        char* s;         // owned string (malloc'd)
        struct {
            struct HexaVal* items;
            int len;
            int cap;
        } arr;
        struct {
            HexaMapTable* tbl;   // heap-allocated hash table
            int len;             // cached count (== tbl->len when tbl != NULL)
        } map;
        struct {
            void* fn_ptr;
            int arity;
        } fn;
        // C3 closure: function pointer that takes (HexaVal env, ...args)
        // env is a boxed TAG_ARRAY HexaVal (heap-allocated so it survives copies).
        struct {
            void* fn_ptr;           // signature: HexaVal (*)(HexaVal env, ...N args)
            int arity;              // number of user params (excluding env)
            struct HexaVal* env_box;// heap box holding a single TAG_ARRAY HexaVal
        } clo;
        // rt 32-G: heap-allocated flat struct pointer (TAG_VALSTRUCT).
        HexaValStruct* vs;
    };
} HexaVal;

// rt 32-G Phase 0 (redesigned): flat C struct replacement for `Val` map.
// Fields MUST mirror self/hexa_full.hexa `struct Val` exactly (order + types).
// Heap-allocated once per Val construction, shared by value via pointer copy
// of the containing HexaVal (no deep copy — mirrors current map.tbl pointer
// sharing semantics). Lifetime: leak-compatible with current interpreter
// (no free, same as existing map-backed Vals).
//
// REDESIGN (rt 32-G Phase 0 redesign): non-scalar fields are now full HexaVal
// (polymorphic tagged union) instead of `const char*`. The original Phase 0
// design assumed every non-scalar slot held a string, but val_fn / val_closure
// store TAG_ARRAY (params) and TAG_MAP (AST body) values. The old design
// silently coerced those to "" → closure body erased after rebootstrap.
// HexaVal-by-value adds ~24B per slot but eliminates the data loss.
typedef struct HexaValStruct {
    int64_t tag_i;          // Hexa-level Val.tag (TAG_INT / TAG_FLOAT / ...)
    int64_t int_val;
    double  float_val;
    int     bool_val;
    // rt 32-L: 1 = allocated from the bump arena, 0 = malloc heap. Arena
    // VALSTRUCTs MUST be heapified before they outlive the current scope.
    // Sits in the alignment padding between bool_val (4B) and the first
    // HexaVal (24B aligned to 8) — zero size cost in practice.
    int     from_arena;
    // Polymorphic slots — store the original HexaVal verbatim. For TAG_STR
    // payloads this is just s/tag; for arrays/maps the .arr / .map / .vs
    // member survives intact. Empty/missing fields use TAG_VOID.
    HexaVal str_val;
    HexaVal char_val;
    HexaVal array_val;     // crucial for AST body propagation
    HexaVal fn_name;
    HexaVal fn_params;     // TAG_ARRAY (closure param list)
    HexaVal fn_body;       // TAG_MAP / TAG_ARRAY (AST body)
    HexaVal struct_name;
    HexaVal struct_fields; // TAG_MAP (struct field map)
} HexaValStruct;

// ── C3 Closure helpers ───────────────────────────────────
// Build a closure value. Captured values are provided as an already-built
// TAG_ARRAY HexaVal; we heap-box it so the closure remains valid after copies.
static inline HexaVal hexa_closure_new(void* fn_ptr, int arity, HexaVal env_arr) {
    HexaVal v = {.tag=TAG_CLOSURE};
    v.clo.fn_ptr = fn_ptr;
    v.clo.arity = arity;
    v.clo.env_box = (HexaVal*)malloc(sizeof(HexaVal));
    *v.clo.env_box = env_arr;
    return v;
}

static inline HexaVal hexa_closure_env(HexaVal c) {
    if (c.tag != TAG_CLOSURE || !c.clo.env_box) return hexa_array_new();
    return *c.clo.env_box;
}

// Dispatched call helpers — one per arity we support (0..4).
static inline HexaVal hexa_call0(HexaVal f) {
    if (f.tag == TAG_CLOSURE) {
        HexaVal (*fp)(HexaVal) = (HexaVal(*)(HexaVal))f.clo.fn_ptr;
        return fp(hexa_closure_env(f));
    }
    if (f.tag == TAG_FN) {
        HexaVal (*fp)(void) = (HexaVal(*)(void))f.fn.fn_ptr;
        return fp();
    }
    return hexa_void();
}
static inline HexaVal hexa_call1(HexaVal f, HexaVal a1) {
    if (f.tag == TAG_CLOSURE) {
        HexaVal (*fp)(HexaVal, HexaVal) = (HexaVal(*)(HexaVal, HexaVal))f.clo.fn_ptr;
        return fp(hexa_closure_env(f), a1);
    }
    if (f.tag == TAG_FN) {
        HexaVal (*fp)(HexaVal) = (HexaVal(*)(HexaVal))f.fn.fn_ptr;
        return fp(a1);
    }
    return hexa_void();
}
static inline HexaVal hexa_call2(HexaVal f, HexaVal a1, HexaVal a2) {
    if (f.tag == TAG_CLOSURE) {
        HexaVal (*fp)(HexaVal, HexaVal, HexaVal) = (HexaVal(*)(HexaVal, HexaVal, HexaVal))f.clo.fn_ptr;
        return fp(hexa_closure_env(f), a1, a2);
    }
    if (f.tag == TAG_FN) {
        HexaVal (*fp)(HexaVal, HexaVal) = (HexaVal(*)(HexaVal, HexaVal))f.fn.fn_ptr;
        return fp(a1, a2);
    }
    return hexa_void();
}
static inline HexaVal hexa_call3(HexaVal f, HexaVal a1, HexaVal a2, HexaVal a3) {
    if (f.tag == TAG_CLOSURE) {
        HexaVal (*fp)(HexaVal, HexaVal, HexaVal, HexaVal) = (HexaVal(*)(HexaVal, HexaVal, HexaVal, HexaVal))f.clo.fn_ptr;
        return fp(hexa_closure_env(f), a1, a2, a3);
    }
    if (f.tag == TAG_FN) {
        HexaVal (*fp)(HexaVal, HexaVal, HexaVal) = (HexaVal(*)(HexaVal, HexaVal, HexaVal))f.fn.fn_ptr;
        return fp(a1, a2, a3);
    }
    return hexa_void();
}
static inline HexaVal hexa_call4(HexaVal f, HexaVal a1, HexaVal a2, HexaVal a3, HexaVal a4) {
    if (f.tag == TAG_CLOSURE) {
        HexaVal (*fp)(HexaVal, HexaVal, HexaVal, HexaVal, HexaVal) = (HexaVal(*)(HexaVal, HexaVal, HexaVal, HexaVal, HexaVal))f.clo.fn_ptr;
        return fp(hexa_closure_env(f), a1, a2, a3, a4);
    }
    if (f.tag == TAG_FN) {
        HexaVal (*fp)(HexaVal, HexaVal, HexaVal, HexaVal) = (HexaVal(*)(HexaVal, HexaVal, HexaVal, HexaVal))f.fn.fn_ptr;
        return fp(a1, a2, a3, a4);
    }
    return hexa_void();
}

// ── Constructors ─────────────────────────────────────────

HexaVal hexa_int(int64_t n) { return (HexaVal){.tag=TAG_INT, .i=n}; }
HexaVal hexa_float(double f) { return (HexaVal){.tag=TAG_FLOAT, .f=f}; }
HexaVal hexa_bool(int b) { return (HexaVal){.tag=TAG_BOOL, .b=b}; }
HexaVal hexa_void() { return (HexaVal){.tag=TAG_VOID}; }

// T32: unwrap a HexaVal (possibly VALSTRUCT-wrapped by the interpreter) into
// a raw C double. The prior inline `v.tag==TAG_FLOAT?v.f:(double)v.i` read
// only the outer tag, so interpreter values (which carry TAG_VALSTRUCT with
// the real tag in vs->tag_i) fell through and cast the vs pointer bits to
// double — producing garbage. Centralising here lets to_float / exp / sin /
// cos / log / log10 / round share one correct unwrap.
static inline double __hx_to_double(HexaVal v) {
    if (v.tag == TAG_FLOAT) return v.f;
    if (v.tag == TAG_INT)   return (double)v.i;
    // ComptimeConst eval: to_float("3.14") at compile time needs string parsing.
    // Without this branch, returned 0.0, silently producing wrong constants.
    // atof handles both ints and floats correctly ("3" → 3.0, "3.14" → 3.14).
    if (v.tag == TAG_STR && v.s)   return atof(v.s);
    if (v.tag == TAG_VALSTRUCT && v.vs) {
        if (v.vs->tag_i == TAG_FLOAT) return v.vs->float_val;
        if (v.vs->tag_i == TAG_INT)   return (double)v.vs->int_val;
    }
    return 0.0;
}

// RT-P3-1 wrapper shims. Non-owning returns; cstring/str_as_ptr use static
// thread-unsafe buffers for scalar formatting — callers that persist the
// pointer beyond the next scalar-path call MUST copy.
int64_t hexa_as_num(HexaVal v) {
    if (v.tag == TAG_INT)   return v.i;
    if (v.tag == TAG_FLOAT) return (int64_t)v.f;
    if (v.tag == TAG_BOOL)  return (int64_t)v.b;
    if (v.tag == TAG_STR && v.s) return strtoll(v.s, NULL, 10);
    if (v.tag == TAG_VALSTRUCT && v.vs) {
        if (v.vs->tag_i == TAG_INT)   return v.vs->int_val;
        if (v.vs->tag_i == TAG_FLOAT) return (int64_t)v.vs->float_val;
        if (v.vs->tag_i == TAG_BOOL)  return (int64_t)v.vs->bool_val;
        if (v.vs->tag_i == TAG_STR && v.vs->str_val.s)
            return strtoll(v.vs->str_val.s, NULL, 10);
    }
    return 0;
}

const char* hexa_to_cstring(HexaVal v) {
    if (v.tag == TAG_STR && v.s) return v.s;
    if (v.tag == TAG_VOID) return "void";
    if (v.tag == TAG_VALSTRUCT && v.vs) {
        if (v.vs->tag_i == TAG_STR && v.vs->str_val.s) return v.vs->str_val.s;
        static char vbuf[64];
        if (v.vs->tag_i == TAG_INT)   { snprintf(vbuf, 64, "%lld", (long long)v.vs->int_val); return vbuf; }
        if (v.vs->tag_i == TAG_FLOAT) { snprintf(vbuf, 64, "%g", v.vs->float_val); return vbuf; }
        if (v.vs->tag_i == TAG_BOOL)  return v.vs->bool_val ? "true" : "false";
    }
    static char buf[64];
    if (v.tag == TAG_INT)   { snprintf(buf, 64, "%lld", (long long)v.i); return buf; }
    if (v.tag == TAG_FLOAT) { snprintf(buf, 64, "%g", v.f); return buf; }
    if (v.tag == TAG_BOOL)  return v.b ? "true" : "false";
    return "<value>";
}

const char* hexa_str_as_ptr(HexaVal v) {
    if (v.tag == TAG_STR && v.s) return v.s;
    if (v.tag == TAG_VALSTRUCT && v.vs && v.vs->tag_i == TAG_STR && v.vs->str_val.s)
        return v.vs->str_val.s;
    return NULL;
}

// Null coalescing: a ?? b — if a is void or empty string, return b
HexaVal hexa_null_coal(HexaVal a, HexaVal b) {
    if (a.tag == TAG_VOID) return b;
    if (a.tag == TAG_STR && (a.s == NULL || a.s[0] == '\0')) return b;
    return a;
}

HexaVal hexa_str(const char* s) {
    HexaVal v = {.tag=TAG_STR};
    // Optimization #11: intern short strings for pointer-equality comparison
    const char* interned = hexa_intern(s);
    if (interned) {
        v.s = (char*)interned;  // owned by intern table, not caller
    } else {
        v.s = strdup(s);        // long/unique strings: traditional copy
    }
    return v;
}

HexaVal hexa_str_own(char* s) {
    return (HexaVal){.tag=TAG_STR, .s=s};
}

// ── Array operations ─────────────────────────────────────

// rt 32: alloc/COW stats (HEXA_ALLOC_STATS=1 env enables atexit dump).
// Counts hot-path C runtime allocations so we can diagnose where 10GB
// RSS ML microbench pressure originates without sample/leaks tooling.
static int64_t _hx_stats_array_new      = 0;
static int64_t _hx_stats_array_push     = 0;
static int64_t _hx_stats_array_grow     = 0;   // realloc that actually grows cap
static int64_t _hx_stats_str_concat     = 0;
static int64_t _hx_stats_array_reserve  = 0;
static int64_t _hx_stats_map_new        = 0;
static int64_t _hx_stats_map_set        = 0;
// rt 32-D: arena allocator stats (str_concat hot-path)
static int64_t _hx_stats_arena_alloc    = 0;   // total arena bump allocations
static int64_t _hx_stats_arena_blocks   = 0;   // blocks created
static int64_t _hx_stats_arena_bytes    = 0;   // bytes currently reserved in blocks
static int64_t _hx_stats_str_concat_arena = 0; // str_concat calls that hit arena
// rt 32-M: array arena counters
static int64_t _hx_stats_array_arena_alloc   = 0; // push that went arena (initial slot buf)
static int64_t _hx_stats_array_arena_promote = 0; // arena→heap promotions on grow
static int64_t _hx_stats_array_arena_heapify = 0; // heapify copies of arena item buffers
static int _hx_stats_enabled = -1;             // lazy probe of env

static void _hx_stats_dump(void) {
    fprintf(stderr, "[HEXA_ALLOC_STATS] array_new=%lld push=%lld grow=%lld reserve=%lld str_concat=%lld map_new=%lld map_set=%lld arena_alloc=%lld arena_blocks=%lld arena_bytes=%lld str_concat_arena=%lld arr_arena_alloc=%lld arr_arena_promote=%lld arr_arena_heapify=%lld\n",
        (long long)_hx_stats_array_new,
        (long long)_hx_stats_array_push,
        (long long)_hx_stats_array_grow,
        (long long)_hx_stats_array_reserve,
        (long long)_hx_stats_str_concat,
        (long long)_hx_stats_map_new,
        (long long)_hx_stats_map_set,
        (long long)_hx_stats_arena_alloc,
        (long long)_hx_stats_arena_blocks,
        (long long)_hx_stats_arena_bytes,
        (long long)_hx_stats_str_concat_arena,
        (long long)_hx_stats_array_arena_alloc,
        (long long)_hx_stats_array_arena_promote,
        (long long)_hx_stats_array_arena_heapify);
}

static int _hx_stats_on(void) {
    if (_hx_stats_enabled < 0) {
        const char* e = getenv("HEXA_ALLOC_STATS");
        _hx_stats_enabled = (e && e[0] && e[0] != '0') ? 1 : 0;
        if (_hx_stats_enabled) {
            atexit(_hx_stats_dump);
        }
    }
    return _hx_stats_enabled;
}

// ── rt 32-M: Array arena allocator ──────────────────────
// Bump-allocate the array slot buffer (HexaVal*) from the shared bump arena
// during an active fn-call mark (__hexa_val_mark_top > 0). On grow beyond the
// initial slot capacity, promote the buffer to malloc (can't realloc an arena
// region). On heapify, deep-copy the item buffer to malloc before the arena
// rewind point.
//
// Encoding: negative cap = from_arena (arr.items points into arena). This
// preserves HexaVal width/ABI — no new field in the .arr struct. Consumers
// that read .cap positively must treat (cap < 0) as |cap|.
//
// Gate: HEXA_ARRAY_ARENA env var. Default ON. Set =0 to fall back to pure
// malloc/realloc path bit-for-bit.
//
// Rationale: fib(20)×30 shows array_new=4.6M, push=28.9M, grow=4.6M — the
// dominant RSS driver. rt 32-L heapified HexaValStruct but left the array
// .items buffer on the malloc heap (rt 32-L comment explicitly calls this
// out: "Array .items lives on heap — hexa_array_push uses realloc"). This
// change addresses that gap.
extern int __hexa_val_mark_top;  // shared with rt 32-L Val arena
static int hexa_val_arena_on(void);
static void* hexa_val_arena_calloc(size_t n);
void* hexa_arena_alloc(size_t n);  // rt 32-D bump allocator (shared block chain)

static int __hexa_array_arena_enabled = -1;
static int hexa_array_arena_on(void) {
    if (__hexa_array_arena_enabled < 0) {
        const char* e = getenv("HEXA_ARRAY_ARENA");
        // Default ON. Export HEXA_ARRAY_ARENA=0 to disable.
        if (!e || !e[0]) __hexa_array_arena_enabled = 1;
        else             __hexa_array_arena_enabled = (e[0] != '0') ? 1 : 0;
    }
    return __hexa_array_arena_enabled;
}

// Arena-alloc a HexaVal slot buffer. Caller sets cap to -n so the "from_arena"
// sentinel survives the return. Returns NULL if arena is off / not in scope.
// Does NOT zero the buffer — caller memcpy's over it (slice_fast) or writes
// len items before reading. Skipping the memset is a measurable win on hot
// paths (the Val arena's calloc variant memset'd a 4MB block front-to-back
// every few thousand calls, costing ~8% wall on fib K=30).
static HexaVal* hexa_array_arena_alloc_items(int n) {
    if (!hexa_array_arena_on()) return NULL;
    // Must be inside a live scope mark — otherwise there's no rewind point to
    // catch the allocation (module-init arrays stay on heap).
    if (__hexa_val_mark_top <= 0) return NULL;
    // Reuse the shared bump allocator (same block chain as rt 32-L). The
    // existing rt 32-L scope-push/pop discipline automatically reclaims the
    // array buffers too — no parallel mark stack needed.
    HexaVal* p = (HexaVal*)hexa_arena_alloc((size_t)n * sizeof(HexaVal));
    return p;  // NULL if arena OOM — caller falls back to malloc
}

// Promote an arena-backed slot buffer to malloc. len = current live slot count
// to copy; new_cap = target capacity. Used by grow (new_cap > |old_cap|) and
// heapify (new_cap == |old_cap|). Returns NULL on OOM (caller handles).
static HexaVal* hexa_array_promote_to_heap(HexaVal* arena_items, int len, int new_cap) {
    HexaVal* heap = (HexaVal*)malloc(sizeof(HexaVal) * (size_t)new_cap);
    if (!heap) return NULL;
    if (arena_items && len > 0) {
        memcpy(heap, arena_items, sizeof(HexaVal) * (size_t)len);
    }
    return heap;
}

HexaVal hexa_array_new() {
    if (_hx_stats_on()) _hx_stats_array_new++;
    HexaVal v = {.tag=TAG_ARRAY};
    v.arr.items = NULL; v.arr.len = 0; v.arr.cap = 0;
    return v;
}

// rt#32-N: snapshot-promote helper. Invoked by the transpiler around every
// `let y = x` and fn-argument expression where x may be a TAG_ARRAY whose items
// buffer is arena-allocated (cap < 0). Deep-copies arena items to malloc so
// the snapshot is insulated from subsequent arena rewinds + callee arena
// re-allocations. Passthrough for non-array / non-arena values.
//
// Rationale: Hexa is pass-by-value at the HexaVal level (I1), but the .items
// pointer inside arr.* is shared. rt#32-M enabled arena-alloc only for the
// slice_fast path because a caller-local snapshot of a persistent global could
// alias the same arena buffer that the callee subsequently re-arena-alloc'd
// (ABA). Snapshot-promote cuts the alias by forcing the caller's copy onto
// the malloc heap at capture time.
HexaVal hexa_val_snapshot_array(HexaVal v) {
    if (v.tag != TAG_ARRAY) return v;
    if (v.arr.cap >= 0) return v;  // heap-backed — no aliasing with arena rewind
    // cap < 0: arena-backed — promote to heap.
    if (_hx_stats_on()) _hx_stats_array_arena_heapify++;
    int real_cap = -v.arr.cap;
    HexaVal* heap = hexa_array_promote_to_heap(v.arr.items, v.arr.len, real_cap);
    if (!heap) return v;  // OOM — best-effort, caller may see stale pointer
    v.arr.items = heap;
    v.arr.cap = real_cap;  // positive → heap
    return v;
}

// rt#32-N: push-arena gate. Default OFF until snapshot-promote is fully wired
// into the transpiler + interpreter source (self/hexa_full.hexa). Set
// HEXA_ARRAY_PUSH_ARENA=1 to enable arena-alloc on first push (cap=0 → cap=-8)
// after snapshot-promote is proven safe.
static int __hexa_array_push_arena_enabled = -1;
static int hexa_array_push_arena_on(void) {
    if (__hexa_array_push_arena_enabled < 0) {
        const char* e = getenv("HEXA_ARRAY_PUSH_ARENA");
        if (!e || !e[0]) __hexa_array_push_arena_enabled = 0;  // default OFF
        else             __hexa_array_push_arena_enabled = (e[0] != '0') ? 1 : 0;
    }
    return __hexa_array_push_arena_enabled;
}

// Optimization #12: reserve capacity up front when size is known.
// rt 32-M: respect arena-backed items (cap<0) — promote to heap on grow.
HexaVal hexa_array_reserve(HexaVal arr, int n) {
    int real_cap = arr.arr.cap < 0 ? -arr.arr.cap : arr.arr.cap;
    if (n <= real_cap) return arr;
    if (_hx_stats_on()) _hx_stats_array_reserve++;
    if (arr.arr.cap < 0) {
        if (_hx_stats_on()) _hx_stats_array_arena_promote++;
        HexaVal* heap = hexa_array_promote_to_heap(arr.arr.items, arr.arr.len, n);
        if (!heap) { fprintf(stderr, "OOM in array_reserve\n"); exit(1); }
        arr.arr.items = heap;
        arr.arr.cap = n;
    } else {
        HexaVal* new_items = realloc(arr.arr.items, sizeof(HexaVal) * (size_t)n);
        if (!new_items) { fprintf(stderr, "OOM in array_reserve\n"); exit(1); }
        arr.arr.items = new_items;
        arr.arr.cap = n;
    }
    return arr;
}

// Optimization #12: grow from current cap (2x), not from new_len.
// Only realloc when len exceeds cap; growth factor 2x amortizes cost.
// rt 32-M: arena-alloc the initial slot buffer when a fn-call scope mark is
// live (HEXA_ARRAY_ARENA=1 default). On grow beyond the arena buffer, promote
// to heap with malloc+memcpy — the arena region cannot be realloc'd. Negative
// `cap` encodes from_arena; abs(cap) is the real capacity.
HexaVal hexa_array_push(HexaVal arr, HexaVal item) {
    if (_hx_stats_on()) _hx_stats_array_push++;
    int real_cap = arr.arr.cap < 0 ? -arr.arr.cap : arr.arr.cap;
    if (arr.arr.len >= real_cap) {
        if (_hx_stats_on()) _hx_stats_array_grow++;
        int new_cap = real_cap < 8 ? 8 : real_cap * 2;
        if (arr.arr.cap < 0) {
            // Arena-backed buffer: cannot realloc. Allocate a NEW arena slab
            // if still inside a live mark and there's room; else promote to
            // malloc heap. Keeping it arena-resident preserves the RSS win
            // for arrays that grow incrementally inside the same scope.
            HexaVal* next_items = NULL;
            if (__hexa_val_mark_top > 0 && hexa_array_arena_on()) {
                next_items = hexa_array_arena_alloc_items(new_cap);
            }
            if (next_items) {
                if (arr.arr.len > 0) {
                    memcpy(next_items, arr.arr.items, sizeof(HexaVal) * (size_t)arr.arr.len);
                }
                arr.arr.items = next_items;
                arr.arr.cap = -new_cap;
            } else {
                // Promote to heap.
                if (_hx_stats_on()) _hx_stats_array_arena_promote++;
                HexaVal* heap = hexa_array_promote_to_heap(arr.arr.items, arr.arr.len, new_cap);
                if (!heap) { fprintf(stderr, "OOM in array_push (arena promote)\n"); exit(1); }
                arr.arr.items = heap;
                arr.arr.cap = new_cap;  // positive → heap
            }
        } else {
            // rt#32-N: push-arena path (cap=0 first-push or existing heap
            // grow). Enabled by HEXA_ARRAY_PUSH_ARENA=1 once the transpiler
            // wraps snapshot-capture sites with hexa_val_snapshot_array.
            // Without snapshot-promote, Hexa pass-by-value (I1) aliasing
            // makes caller snapshots invalid across callee arena rewinds.
            //
            // Only fires on FIRST allocation (cap==0) — subsequent grows on
            // an existing heap buffer continue to realloc as before (no
            // aliasing delta). When mark_top > 0 and arena is on, the fresh
            // buffer is arena-allocated with cap=-new_cap.
            HexaVal* next_items = NULL;
            int use_arena = 0;
            if (real_cap == 0
                && __hexa_val_mark_top > 0
                && hexa_array_arena_on()
                && hexa_array_push_arena_on()) {
                next_items = hexa_array_arena_alloc_items(new_cap);
                if (next_items) {
                    use_arena = 1;
                    if (_hx_stats_on()) _hx_stats_array_arena_alloc++;
                }
            }
            if (use_arena) {
                arr.arr.items = next_items;
                arr.arr.cap = -new_cap;  // negative → from_arena sentinel
            } else {
                HexaVal* new_items = realloc(arr.arr.items, sizeof(HexaVal) * (size_t)new_cap);
                if (!new_items) { fprintf(stderr, "OOM in array_push\n"); exit(1); }
                arr.arr.items = new_items;
                arr.arr.cap = new_cap;
            }
        }
    }
    arr.arr.items[arr.arr.len] = item;
    arr.arr.len++;
    return arr;
}

// rt 32-B: reusable-buffer scratch push. Semantics identical to hexa_array_push
// except it does NOT bump _hx_stats_array_push / _hx_stats_array_grow (those
// counters are reserved for "true" per-call allocs). Used by the NK_CALL args
// accumulator (call_arg_buf) which is a single long-lived buffer — its growth
// amortises across the whole program and should not inflate the per-call
// push/grow histogram.
HexaVal hexa_array_push_nostat(HexaVal arr, HexaVal item) {
    // rt 32-M: stays on heap (call_arg_buf is long-lived — arena rewind would
    // invalidate it). If an arena buffer somehow lands here, promote to heap.
    int real_cap = arr.arr.cap < 0 ? -arr.arr.cap : arr.arr.cap;
    if (arr.arr.len >= real_cap) {
        int new_cap = real_cap < 8 ? 8 : real_cap * 2;
        if (arr.arr.cap < 0) {
            HexaVal* heap = hexa_array_promote_to_heap(arr.arr.items, arr.arr.len, new_cap);
            if (!heap) { fprintf(stderr, "OOM in array_push_nostat\n"); exit(1); }
            arr.arr.items = heap;
            arr.arr.cap = new_cap;
        } else {
            HexaVal* new_items = realloc(arr.arr.items, sizeof(HexaVal) * (size_t)new_cap);
            if (!new_items) { fprintf(stderr, "OOM in array_push_nostat\n"); exit(1); }
            arr.arr.items = new_items;
            arr.arr.cap = new_cap;
        }
    }
    arr.arr.items[arr.arr.len] = item;
    arr.arr.len++;
    return arr;
}

// rt 32-B: bulk slice primitive — single malloc + memcpy, counts as exactly
// ONE array_new (not N array_push). Used to hand a per-call args view out of
// the shared call_arg_buf so the callee receives an independent backing store
// that is not disturbed by subsequent NK_CALL recursion mutating the buffer.
HexaVal hexa_array_slice_fast(HexaVal arr, HexaVal start, HexaVal end) {
    if (_hx_stats_on()) _hx_stats_array_new++;
    HexaVal out = {.tag=TAG_ARRAY};
    out.arr.items = NULL; out.arr.len = 0; out.arr.cap = 0;
    if (arr.tag != TAG_ARRAY) return out;
    int n = arr.arr.len;
    int a = (int)start.i, b = (int)end.i;
    if (a < 0) a = 0;
    if (b > n) b = n;
    if (a > b) a = b;
    int m = b - a;
    if (m <= 0) return out;
    // rt 32-M: arena-allocate slice items when inside a live fn-scope mark.
    // Slice_fast is used primarily for the NK_CALL scratch-args pattern (rt 32-B)
    // where the slice is immediately handed to call_user_fn as args, consumed
    // (each element copied into env_define), and discarded on fn return — a
    // lifetime that fits exactly within the callee's mark frontier.
    //
    // Safety: call_stack.slice(...) at call_user_fn exit happens BEFORE the
    // __HEXA_ARENA_POP__, so the caller sees a slice whose items pointer is
    // NOT rewound. But call_stack.slice is built from truncation on line 8341
    // AFTER the pop — so it runs at outer mark. We guard by only arena-
    // allocating when mark_top > 0 AND the SOURCE array is heap (cap >= 0).
    // For call_stack.slice(0, len-1) after pop, the source is heap; the result
    // lives at the outer's arena frontier which the outer's pop eventually
    // reclaims — call_stack is reassigned every call anyway, so the old slice
    // is unreachable by the next cycle. Heapify-on-return handles fn-return
    // escapes.
    HexaVal* items = NULL;
    int use_arena = 0;
    if (hexa_array_arena_on() && __hexa_val_mark_top > 0) {
        items = hexa_array_arena_alloc_items(m);
        if (items) { use_arena = 1; if (_hx_stats_on()) _hx_stats_array_arena_alloc++; }
    }
    if (!items) {
        items = (HexaVal*)malloc(sizeof(HexaVal) * (size_t)m);
        if (!items) { fprintf(stderr, "OOM in array_slice_fast\n"); exit(1); }
    }
    memcpy(items, arr.arr.items + a, sizeof(HexaVal) * (size_t)m);
    out.arr.items = items;
    out.arr.len = m;
    out.arr.cap = use_arena ? -m : m;
    return out;
}

HexaVal hexa_array_get(HexaVal arr, int64_t idx) {
    // B13: tag guard — without this, a TAG_STR (from hexa_add fallthrough)
    // reaches here and we read .arr.len from an unrelated union slot
    // (uninitialized stack residue). Explicit panic instead of silent OOB.
    if (arr.tag != TAG_ARRAY) {
        fprintf(stderr, "array[%lld]: container is not an array (tag=%d)\n", (long long)idx, (int)arr.tag);
        exit(1);
    }
    if (idx < 0) idx += arr.arr.len;
    if (idx < 0 || idx >= arr.arr.len) {
        fprintf(stderr, "index %lld out of bounds (len %d)\n", (long long)idx, arr.arr.len);
        exit(1);
    }
    return arr.arr.items[idx];
}

HexaVal hexa_array_set(HexaVal arr, int64_t idx, HexaVal val) {
    if (idx < 0) idx += arr.arr.len;
    if (idx < 0 || idx >= arr.arr.len) {
        fprintf(stderr, "index %lld out of bounds (len %d)\n", (long long)idx, arr.arr.len);
        exit(1);
    }
    // In-place mutate (no copy — caller reassigns)
    arr.arr.items[idx] = val;
    return arr;
}

// bt 55 — in-place truncate. Used by env_pop_scope to avoid the
// `new_vars.push` rebuild loop which realloc-leaks the old backing buffer
// every scope pop. Retains capacity for amortized re-growth.
// No free of arr.items here (HexaVal entries may still be shared); we only
// shrink the logical length. Safe because the slots beyond `new_len` become
// unreachable through this handle.
HexaVal hexa_array_truncate(HexaVal arr, HexaVal new_len_v) {
    if (arr.tag != TAG_ARRAY) return arr;
    int64_t new_len = (new_len_v.tag == TAG_INT) ? new_len_v.i : (int64_t)new_len_v.i;
    if (new_len < 0) new_len = 0;
    if (new_len > arr.arr.len) new_len = arr.arr.len;
    arr.arr.len = (int)new_len;
    return arr;
}

int hexa_len(HexaVal v) {
    if (v.tag == TAG_STR) return strlen(v.s);
    if (v.tag == TAG_ARRAY) return v.arr.len;
    if (v.tag == TAG_MAP) return v.map.len;
    return 0;
}

// ── Map operations (Optimization #10: hash table) ───────

// rt 32-L: forward decls — Val arena lives below the str_concat arena
// (shared block chain via hexa_arena_alloc) but maintains its own scope-mark
// stack so str-concat marks aren't perturbed by Val scope push/pop.
void* hexa_arena_alloc(size_t n);  // defined below; forward decl for hmap_alloc_ex.
static int hexa_val_arena_on(void);
static void* hexa_val_arena_calloc(size_t n);
extern int __hexa_val_mark_top;  // defined later; gate guard for module-init Vals.

// Allocate a new HexaMapTable with given hash-table capacity.
// rt 32-L: when from_arena=1, use bump-arena instead of malloc/calloc. Caller
// guarantees the table will be heapified (via hexa_val_heapify) before the
// arena rewind point catches up. When from_arena=0, behavior is unchanged.
static HexaMapTable* hmap_alloc_ex(int ht_cap, int from_arena) {
    HexaMapTable* t;
    int order_init = ht_cap < 8 ? 8 : ht_cap;
    if (from_arena) {
        // All four allocations satisfied from the same bump frontier — single
        // O(1) reset frees them in bulk. Zeroing via memset is required to
        // satisfy the pre-existing calloc guarantees that hmap_find / load-
        // factor checks rely on (slots[].key == NULL means empty).
        t = (HexaMapTable*)hexa_val_arena_calloc(sizeof(HexaMapTable));
        t->slots = (HexaMapSlot*)hexa_val_arena_calloc(ht_cap * sizeof(HexaMapSlot));
        t->vals  = (HexaVal*)hexa_val_arena_calloc(ht_cap * sizeof(HexaVal));
        t->order_keys = (char**)hexa_val_arena_calloc(sizeof(char*) * order_init);
        t->order_vals = (HexaVal*)hexa_val_arena_calloc(sizeof(HexaVal) * order_init);
        t->from_arena = 1;
    } else {
        t = (HexaMapTable*)calloc(1, sizeof(HexaMapTable));
        t->slots = (HexaMapSlot*)calloc(ht_cap, sizeof(HexaMapSlot));
        t->vals  = (HexaVal*)calloc(ht_cap, sizeof(HexaVal));
        t->order_keys = (char**)malloc(sizeof(char*) * order_init);
        t->order_vals = (HexaVal*)malloc(sizeof(HexaVal) * order_init);
        t->from_arena = 0;
    }
    t->ht_cap = ht_cap;
    t->order_cap = order_init;
    t->len = 0;
    return t;
}

// Backward-compat wrapper — preserves the heap-only signature for callers that
// must guarantee long-lived storage (env caches, fn body maps, etc.).
static HexaMapTable* hmap_alloc(int ht_cap) {
    return hmap_alloc_ex(ht_cap, 0);
}

// Rehash the table to double its capacity.
static void hmap_grow(HexaMapTable* t) {
    int old_cap = t->ht_cap;
    HexaMapSlot* old_slots = t->slots;
    HexaVal* old_vals = t->vals;
    int new_cap = old_cap * 2;
    HexaMapSlot* new_slots = (HexaMapSlot*)calloc(new_cap, sizeof(HexaMapSlot));
    HexaVal* new_vals = (HexaVal*)calloc(new_cap, sizeof(HexaVal));
    uint32_t mask = (uint32_t)(new_cap - 1);
    for (int i = 0; i < old_cap; i++) {
        if (old_slots[i].key) {
            uint32_t idx = old_slots[i].hash & mask;
            while (new_slots[idx].key) idx = (idx + 1) & mask;
            new_slots[idx] = old_slots[i];
            new_vals[idx]  = old_vals[i];
        }
    }
    // T33: do NOT free arena-allocated old buffers — free() on arena mem is UB.
    // The arena will reclaim them on scope pop.
    if (!t->from_arena) {
        free(old_slots);
        free(old_vals);
    }
    t->slots = new_slots;
    t->vals  = new_vals;
    t->ht_cap = new_cap;
    // Mark table as heap-backed for future growth/free decisions — the slots/
    // vals/order arrays may still be arena, but new_slots/new_vals here are
    // heap, so subsequent free(t->slots) after arena pop would be safe. Keep
    // from_arena unchanged since order_keys/order_vals still carry the
    // original allocation site.
}

// Find slot index for key, or -1 if not found.
static int hmap_find(HexaMapTable* t, const char* key, uint32_t h) {
    uint32_t mask = (uint32_t)(t->ht_cap - 1);
    uint32_t idx = h & mask;
    while (t->slots[idx].key) {
        if (t->slots[idx].hash == h && strcmp(t->slots[idx].key, key) == 0)
            return (int)idx;
        idx = (idx + 1) & mask;
    }
    return -1;
}

HexaVal hexa_map_new() {
    if (_hx_stats_on()) _hx_stats_map_new++;
    HexaVal v = {.tag=TAG_MAP};
    v.map.tbl = NULL;
    v.map.len = 0;
    return v;
}

// rt 32-A: bulk struct constructor — collapses 1 map_new + N map_set into a
// single pre-sized table allocation + tight insertion loop. Used by
// gen2_struct_decl for `Val { ... }` and other struct literals. Avoids N
// successive hexa_map_set calls (each with its own stats bump + load-factor
// check). Key array is NOT freed; strings must be string literals (stable).
HexaVal hexa_struct_pack_map(const char* type_name, int n,
                             const char* const* keys, const HexaVal* vals) {
    if (_hx_stats_on()) _hx_stats_map_new++;
    HexaVal v = {.tag=TAG_MAP};
    // Pre-size: (n+1) entries including __type__, target load < HMAP_LOAD_MAX/100.
    // Solve for smallest power-of-2 cap where (n+1)*100/cap < HMAP_LOAD_MAX.
    int need = (n + 1) * 100 / HMAP_LOAD_MAX + 1;
    int cap = HMAP_INIT_CAP;
    while (cap < need) cap <<= 1;
    // rt 32-L: opt-in arena allocation for struct literals. Anonymous map
    // literals (type_name == "" or NULL) are excluded — they often back
    // long-lived data (config, AST nodes, registries) where the heapify
    // discipline is not currently wired. Type_named struct literals are the
    // hot fib path (every Val{...} in the interpreter) and the primary RSS
    // contributor at K=30. The arena gate is HEXA_VAL_ARENA (separate from
    // HEXA_STR_ARENA so the two can be tuned independently).
    int from_arena = (type_name && type_name[0]) ?
                     (hexa_val_arena_on() && __hexa_val_mark_top > 0) : 0;
    HexaMapTable* t = hmap_alloc_ex(cap, from_arena);
    v.map.tbl = t;
    uint32_t mask = (uint32_t)(cap - 1);
    // Insert __type__ first (skip for anonymous map literals where
    // type_name is "" — they don't carry a __type__ field).
    if (type_name && type_name[0]) {
        uint32_t h = hexa_fnv1a_str("__type__");
        uint32_t idx = h & mask;
        while (t->slots[idx].key) idx = (idx + 1) & mask;
        // Keys/values strdup'd into heap regardless of from_arena: heapify()
        // can shallow-share these strings (keys are usually literal-like and
        // the arena would otherwise force per-string heap copies on every
        // heapify call, defeating the win). The TAG_STR value `tv` payload is
        // also strdup'd; for arena path we instead arena-alloc to keep the
        // bulk-free property.
        if (from_arena) {
            char* kdup = (char*)hexa_arena_alloc(strlen("__type__") + 1);
            memcpy(kdup, "__type__", 9);
            t->slots[idx].key = kdup;
            HexaVal tv = {.tag=TAG_STR};
            size_t tnl = strlen(type_name);
            char* tdup = (char*)hexa_arena_alloc(tnl + 1);
            memcpy(tdup, type_name, tnl + 1);
            tv.s = tdup;
            t->slots[idx].hash = h;
            t->vals[idx] = tv;
            t->order_keys[t->len] = t->slots[idx].key;
            t->order_vals[t->len] = tv;
        } else {
            t->slots[idx].key = strdup("__type__");
            t->slots[idx].hash = h;
            HexaVal tv = {.tag=TAG_STR};
            tv.s = strdup(type_name);
            t->vals[idx] = tv;
            t->order_keys[t->len] = t->slots[idx].key;
            t->order_vals[t->len] = tv;
        }
        t->len++;
    }
    for (int i = 0; i < n; i++) {
        const char* k = keys[i];
        uint32_t h = hexa_fnv1a_str(k);
        uint32_t idx = h & mask;
        while (t->slots[idx].key) idx = (idx + 1) & mask;
        if (from_arena) {
            size_t kl = strlen(k);
            char* kdup = (char*)hexa_arena_alloc(kl + 1);
            memcpy(kdup, k, kl + 1);
            t->slots[idx].key = kdup;
        } else {
            t->slots[idx].key = strdup(k);
        }
        t->slots[idx].hash = h;
        t->vals[idx] = vals[i];
        t->order_keys[t->len] = t->slots[idx].key;
        t->order_vals[t->len] = vals[i];
        t->len++;
    }
    v.map.len = t->len;
    return v;
}

HexaVal hexa_map_set(HexaVal m, const char* key, HexaVal val) {
    // rt 32-G: route Val field mutation to flat struct.
    if (m.tag == TAG_VALSTRUCT) {
        return hexa_valstruct_set_by_key(m, key, val);
    }
    if (_hx_stats_on()) _hx_stats_map_set++;
    // Lazy-alloc table on first insert
    if (!m.map.tbl) {
        m.map.tbl = hmap_alloc(HMAP_INIT_CAP);
    }
    HexaMapTable* t = m.map.tbl;
    uint32_t h = hexa_fnv1a_str(key);

    // Check if key exists (O(1) average)
    int si = hmap_find(t, key, h);
    if (si >= 0) {
        t->vals[si] = val;
        // Also update in the order array
        for (int i = 0; i < t->len; i++) {
            if (t->order_keys[i] == t->slots[si].key) {
                t->order_vals[i] = val;
                break;
            }
        }
        return m;
    }

    // Grow hash table if needed
    if (t->len * 100 / t->ht_cap >= HMAP_LOAD_MAX) {
        hmap_grow(t);
    }

    // Insert into hash table
    uint32_t mask = (uint32_t)(t->ht_cap - 1);
    uint32_t idx = h & mask;
    while (t->slots[idx].key) idx = (idx + 1) & mask;
    t->slots[idx].key  = strdup(key);
    t->slots[idx].hash = h;
    t->vals[idx] = val;

    // Append to insertion-order arrays
    if (t->len >= t->order_cap) {
        int new_cap = t->order_cap * 2;
        if (t->from_arena) {
            // T33: arena-backed tables cannot realloc — promote order arrays
            // to heap before grow. After promotion from_arena stays 1 for
            // slots/vals (still arena) but the order_* arrays are now heap.
            // The final heapify() will malloc-copy everything anyway; this
            // only handles the mid-scope growth case.
            char** new_keys = (char**)malloc(sizeof(char*) * new_cap);
            HexaVal* new_vals = (HexaVal*)malloc(sizeof(HexaVal) * new_cap);
            if (!new_keys || !new_vals) { fprintf(stderr, "OOM in map_set grow\n"); exit(1); }
            memcpy(new_keys, t->order_keys, sizeof(char*) * t->len);
            memcpy(new_vals, t->order_vals, sizeof(HexaVal) * t->len);
            t->order_keys = new_keys;
            t->order_vals = new_vals;
        } else {
            t->order_keys = (char**)realloc(t->order_keys, sizeof(char*) * new_cap);
            t->order_vals = (HexaVal*)realloc(t->order_vals, sizeof(HexaVal) * new_cap);
        }
        t->order_cap = new_cap;
    }
    t->order_keys[t->len] = t->slots[idx].key;  // shared pointer, not a copy
    t->order_vals[t->len] = val;
    t->len++;
    m.map.len = t->len;
    return m;
}

HexaVal hexa_map_get(HexaVal m, const char* key) {
    // rt 32-G: route Val field access to flat struct accessor.
    if (m.tag == TAG_VALSTRUCT) {
        return hexa_valstruct_get_by_key(m, key);
    }
    if (!m.map.tbl) {
        fprintf(stderr, "map key '%s' not found\n", key);
        return hexa_void();
    }
    HexaMapTable* t = m.map.tbl;
    uint32_t h = hexa_fnv1a_str(key);
    int si = hmap_find(t, key, h);
    if (si >= 0) return t->vals[si];
    fprintf(stderr, "map key '%s' not found\n", key);
    return hexa_void();
}

// ── rt#37: Inline cache for field access ─────────────────
// Each call site of `obj.field` gets a static HexaIC slot. On hit, we skip
// the strcmp-chain and return m.map.vals[ic->idx] directly. On miss we fall
// back to hexa_map_get and repopulate. Shape check uses (keys_ptr, len) —
// a struct constructor inserts keys in a fixed order, so once its (keys, len)
// is stable, idx is valid for every subsequent access.
//
// Invalidation: if keys pointer or len differ, we treat it as a miss. That
// covers (a) a different struct instance reused through the same call site
// and (b) a struct mutated via hexa_map_set (which may realloc the keys
// array). A monomorphic call site converges to ~100% hit rate after 1 call.
//
// Gate: HEXA_IC_STATS=1 dumps per-process hit/miss totals at exit.

static uint64_t g_hexa_ic_hits   = 0;
static uint64_t g_hexa_ic_misses = 0;
static int      g_hexa_ic_stats_enabled   = -1; // -1=unchecked, 0=off, 1=on
static int      g_hexa_ic_stats_installed = 0;

static void hexa_ic_dump_stats(void) {
    uint64_t total = g_hexa_ic_hits + g_hexa_ic_misses;
    double rate = total ? (100.0 * (double)g_hexa_ic_hits / (double)total) : 0.0;
    fprintf(stderr,
        "[rt#37 IC] hits=%llu misses=%llu total=%llu hit_rate=%.2f%%\n",
        (unsigned long long)g_hexa_ic_hits,
        (unsigned long long)g_hexa_ic_misses,
        (unsigned long long)total,
        rate);
}

static inline int hexa_ic_stats_on(void) {
    if (g_hexa_ic_stats_enabled < 0) {
        const char* on = getenv("HEXA_IC_STATS");
        g_hexa_ic_stats_enabled = (on && on[0] != '0' && on[0] != '\0') ? 1 : 0;
        if (g_hexa_ic_stats_enabled && !g_hexa_ic_stats_installed) {
            g_hexa_ic_stats_installed = 1;
            atexit(hexa_ic_dump_stats);
        }
    }
    return g_hexa_ic_stats_enabled;
}

// Slow path: full scan + update cache. Kept out-of-line to shrink the inline
// hot path macro footprint. Stats bump lives here so hits stay counter-free
// when HEXA_IC_STATS is unset.
// rt#32-N build-fix: rt#37 referenced m.map.{keys,vals} which were removed by
// rt#32-G when map storage moved to HexaMapTable. Redirect through .tbl.
static HexaVal hexa_map_get_ic_slow(HexaVal m, const char* key, HexaIC* ic) {
    if (hexa_ic_stats_on()) { ic->misses++; g_hexa_ic_misses++; }
    if (m.tag == TAG_MAP && m.map.tbl) {
        HexaMapTable* t = m.map.tbl;
        for (int i = 0; i < t->len; i++) {
            if (strcmp(t->order_keys[i], key) == 0) {
                ic->keys_ptr = (void*)t->order_keys;
                ic->len      = t->len;
                ic->idx      = i;
                return t->order_vals[i];
            }
        }
    }
    return hexa_map_get(m, key);
}

// Hot path as a MACRO so the fast path avoids the 32-byte HexaVal call ABI
// altogether. We evaluate `m` exactly once via __ic_m to be safe with side
// effects, then:
//   - if (m.map.keys == ic->keys_ptr && m.map.len == ic->len) -> return cached
//   - else                                                   -> slow fallback
// The stat bump on the hot path is compiled out when HEXA_IC_STATS is unset
// because g_hexa_ic_stats_enabled flips to 0 on first slow path miss.
// rt#32-N build-fix: m.map.{keys,vals} -> m.map.tbl->{order_keys,order_vals}
#define hexa_map_get_ic(M, KEY, IC) \
    ({ HexaVal __ic_m = (M); HexaIC* __ic = (IC); \
       (__ic_m.map.tbl \
        && (void*)__ic_m.map.tbl->order_keys == __ic->keys_ptr \
        && __ic_m.map.tbl->len == __ic->len \
        && __ic->idx < __ic->len) \
           ? (g_hexa_ic_stats_enabled > 0 \
              ? (__ic->hits++, g_hexa_ic_hits++, __ic_m.map.tbl->order_vals[__ic->idx]) \
              : __ic_m.map.tbl->order_vals[__ic->idx]) \
           : hexa_map_get_ic_slow(__ic_m, (KEY), __ic); })


HexaVal hexa_map_keys(HexaVal m) {
    HexaVal arr = hexa_array_new();
    if (!m.map.tbl) return arr;
    HexaMapTable* t = m.map.tbl;
    arr = hexa_array_reserve(arr, t->len);
    for (int i = 0; i < t->len; i++) {
        arr = hexa_array_push(arr, hexa_str(t->order_keys[i]));
    }
    return arr;
}

HexaVal hexa_map_values(HexaVal m) {
    HexaVal arr = hexa_array_new();
    if (!m.map.tbl) return arr;
    HexaMapTable* t = m.map.tbl;
    arr = hexa_array_reserve(arr, t->len);
    for (int i = 0; i < t->len; i++) {
        arr = hexa_array_push(arr, t->order_vals[i]);
    }
    return arr;
}

int hexa_map_contains_key(HexaVal m, const char* key) {
    if (!m.map.tbl) return 0;
    uint32_t h = hexa_fnv1a_str(key);
    return hmap_find(m.map.tbl, key, h) >= 0;
}

HexaVal hexa_map_remove(HexaVal m, const char* key) {
    if (!m.map.tbl) return m;
    HexaMapTable* t = m.map.tbl;
    uint32_t h = hexa_fnv1a_str(key);
    int si = hmap_find(t, key, h);
    if (si < 0) return m;

    // Remove from insertion-order arrays
    char* removed_key = t->slots[si].key;
    for (int i = 0; i < t->len; i++) {
        if (t->order_keys[i] == removed_key) {
            for (int j = i; j < t->len - 1; j++) {
                t->order_keys[j] = t->order_keys[j+1];
                t->order_vals[j] = t->order_vals[j+1];
            }
            break;
        }
    }

    // Remove from hash table: mark slot empty and re-insert displaced entries
    free(t->slots[si].key);
    t->slots[si].key = NULL;
    t->slots[si].hash = 0;
    // Robin Hood deletion: re-probe subsequent slots
    uint32_t mask = (uint32_t)(t->ht_cap - 1);
    uint32_t ci = ((uint32_t)si + 1) & mask;
    while (t->slots[ci].key) {
        // Remove and re-insert this entry
        HexaMapSlot saved_slot = t->slots[ci];
        HexaVal saved_val = t->vals[ci];
        t->slots[ci].key = NULL;
        t->slots[ci].hash = 0;
        uint32_t ri = saved_slot.hash & mask;
        while (t->slots[ri].key) ri = (ri + 1) & mask;
        t->slots[ri] = saved_slot;
        t->vals[ri] = saved_val;
        // Update order_keys pointer if it moved
        for (int k = 0; k < t->len; k++) {
            if (t->order_keys[k] == saved_slot.key) {
                // pointer unchanged, just slot index moved -- no action needed
                break;
            }
        }
        ci = (ci + 1) & mask;
    }

    t->len--;
    m.map.len = t->len;
    return m;
}

// Polymorphic index get: array[int] or map[string]
HexaVal hexa_index_get(HexaVal container, HexaVal key) {
    if (container.tag == TAG_MAP && key.tag == TAG_STR) {
        return hexa_map_get(container, key.s);
    }
    return hexa_array_get(container, key.i);
}

// For-in dispatch: array -> element, map -> key as string.
// Uses insertion-order arrays so maps iterate in insertion order (Python-style).
HexaVal hexa_iter_get(HexaVal v, int64_t idx) {
    if (v.tag == TAG_MAP) {
        if (!v.map.tbl || idx < 0 || idx >= v.map.len) {
            fprintf(stderr, "map iter index %lld out of bounds (len %d)\n", (long long)idx, v.map.len);
            exit(1);
        }
        return hexa_str(v.map.tbl->order_keys[idx]);
    }
    return hexa_array_get(v, idx);
}

// Polymorphic index set: array[int]=val or map[string]=val
HexaVal hexa_index_set(HexaVal container, HexaVal key, HexaVal val) {
    if (container.tag == TAG_MAP && key.tag == TAG_STR) {
        return hexa_map_set(container, key.s, val);
    }
    return hexa_array_set(container, key.i, val);
}

// Silent type check for struct method dispatch (codegen_c2 ImplBlock support).
// Returns 1 if v is a TAG_MAP carrying a "__type__" field equal to type_name,
// or TAG_VALSTRUCT (always type "Val" — rt 32-G flat struct).
// Uses hash lookup instead of linear scan.
int hexa_is_type(HexaVal v, const char* type_name) {
    if (v.tag == TAG_VALSTRUCT) {
        return type_name && strcmp(type_name, "Val") == 0;
    }
    if (v.tag != TAG_MAP || !v.map.tbl) return 0;
    uint32_t h = hexa_fnv1a_str("__type__");
    int si = hmap_find(v.map.tbl, "__type__", h);
    if (si < 0) return 0;
    HexaVal t = v.map.tbl->vals[si];
    return t.tag == TAG_STR && t.s && strcmp(t.s, type_name) == 0;
}

// ══════════════════════════════════════════════════════════════
//  rt 32-G Phase 0: flat Val struct implementations
// ══════════════════════════════════════════════════════════════

// Redesigned constructor: every non-scalar arg is HexaVal-by-value so the
// payload (string s, array, map, valstruct pointer) is preserved verbatim.
// Scalars (tag/int/float/bool) still get coerced — those slots only ever
// see TAG_INT / TAG_FLOAT / TAG_BOOL in the interpreter.
HexaVal hexa_valstruct_new_v(
    HexaVal tag_v, HexaVal int_v, HexaVal float_v, HexaVal bool_v,
    HexaVal str_v, HexaVal char_v, HexaVal array_v,
    HexaVal fn_name_v, HexaVal fn_params_v, HexaVal fn_body_v,
    HexaVal struct_name_v, HexaVal struct_fields_v)
{
    // rt 32-L: the dominant fib RSS contributor — every Val{...} construction
    // in the interpreter (val_int / val_float / val_str / val_void / and ALL
    // user-side Val literals) ends up here. Arena-allocate when HEXA_VAL_ARENA
    // is on AND at least one scope mark is live (i.e. we're inside a fn call).
    // Module-init time allocations (cached singletons __VAL_VOID/__VAL_TRUE/
    // __VAL_INT_CACHE etc.) go through the heap path so the first scope pop
    // doesn't wipe them.
    int from_arena = hexa_val_arena_on() && __hexa_val_mark_top > 0;
    HexaValStruct* s;
    if (from_arena) {
        s = (HexaValStruct*)hexa_val_arena_calloc(sizeof(HexaValStruct));
        s->from_arena = 1;
    } else {
        s = (HexaValStruct*)malloc(sizeof(HexaValStruct));
        if (!s) { fprintf(stderr, "OOM in valstruct_new_v\n"); exit(1); }
        s->from_arena = 0;
    }
    s->tag_i     = (tag_v.tag == TAG_INT) ? tag_v.i : 0;
    s->int_val   = (int_v.tag == TAG_INT) ? int_v.i : 0;
    s->float_val = (float_v.tag == TAG_FLOAT) ? float_v.f :
                   (float_v.tag == TAG_INT ? (double)float_v.i : 0.0);
    s->bool_val  = (bool_v.tag == TAG_BOOL) ? bool_v.b :
                   (bool_v.tag == TAG_INT ? (int)bool_v.i : 0);
    // Polymorphic slots — store HexaVal verbatim. Closures / AST bodies /
    // struct field maps now survive Val construction intact.
    s->str_val       = str_v;
    s->char_val      = char_v;
    s->array_val     = array_v;
    s->fn_name       = fn_name_v;
    s->fn_params     = fn_params_v;
    s->fn_body       = fn_body_v;
    s->struct_name   = struct_name_v;
    s->struct_fields = struct_fields_v;
    HexaVal v = {.tag = TAG_VALSTRUCT};
    v.vs = s;
    return v;
}

// Helper: scalar accessors (tag/int/float/bool) still return primitive Vals.
HexaVal hexa_valstruct_tag(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_int(0);
    return hexa_int(v.vs->tag_i);
}
HexaVal hexa_valstruct_int(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_int(0);
    return hexa_int(v.vs->int_val);
}
HexaVal hexa_valstruct_float(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_float(0.0);
    return hexa_float(v.vs->float_val);
}
HexaVal hexa_valstruct_bool(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_bool(0);
    return hexa_bool(v.vs->bool_val);
}
// Polymorphic accessors return the stored HexaVal directly (no string
// re-wrap — the original tag survives so closures work end-to-end).
HexaVal hexa_valstruct_str(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_str("");
    return v.vs->str_val;
}
HexaVal hexa_valstruct_char(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_str("");
    return v.vs->char_val;
}
HexaVal hexa_valstruct_array(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_void();
    return v.vs->array_val;
}
HexaVal hexa_valstruct_fn_name(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_str("");
    return v.vs->fn_name;
}
HexaVal hexa_valstruct_fn_params(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_void();
    return v.vs->fn_params;
}
HexaVal hexa_valstruct_fn_body(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_void();
    return v.vs->fn_body;
}
HexaVal hexa_valstruct_struct_name(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_str("");
    return v.vs->struct_name;
}
HexaVal hexa_valstruct_struct_fields(HexaVal v) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) return hexa_void();
    return v.vs->struct_fields;
}

// Key-string dispatch — branches on key[0] to amortize strcmp.
// Polymorphic fields return raw HexaVal so closure bodies (TAG_MAP) and
// param lists (TAG_ARRAY) propagate through .fn_body / .fn_params reads.
HexaVal hexa_valstruct_get_by_key(HexaVal v, const char* key) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) {
        fprintf(stderr, "valstruct_get: not a TAG_VALSTRUCT\n");
        return hexa_void();
    }
    if (!key) return hexa_void();
    switch (key[0]) {
        case 't':
            if (!strcmp(key, "tag"))           return hexa_int(v.vs->tag_i);
            break;
        case 'i':
            if (!strcmp(key, "int_val"))       return hexa_int(v.vs->int_val);
            break;
        case 'f':
            if (!strcmp(key, "float_val"))     return hexa_float(v.vs->float_val);
            if (!strcmp(key, "fn_name"))       return v.vs->fn_name;
            if (!strcmp(key, "fn_params"))     return v.vs->fn_params;
            if (!strcmp(key, "fn_body"))       return v.vs->fn_body;
            break;
        case 'b':
            if (!strcmp(key, "bool_val"))      return hexa_bool(v.vs->bool_val);
            break;
        case 's':
            if (!strcmp(key, "str_val"))       return v.vs->str_val;
            if (!strcmp(key, "struct_name"))   return v.vs->struct_name;
            if (!strcmp(key, "struct_fields")) return v.vs->struct_fields;
            break;
        case 'c':
            if (!strcmp(key, "char_val"))      return v.vs->char_val;
            break;
        case 'a':
            if (!strcmp(key, "array_val"))     return v.vs->array_val;
            break;
        case '_':
            if (!strcmp(key, "__type__"))      return hexa_str("Val");
            break;
    }
    fprintf(stderr, "valstruct_get: unknown key '%s'\n", key);
    return hexa_void();
}

// Setter accepts any HexaVal payload — no TAG_STR gating, mirrors getter.
HexaVal hexa_valstruct_set_by_key(HexaVal v, const char* key, HexaVal val) {
    if (v.tag != TAG_VALSTRUCT || !v.vs) {
        fprintf(stderr, "valstruct_set: not a TAG_VALSTRUCT\n");
        return v;
    }
    if (!key) return v;
    switch (key[0]) {
        case 't':
            if (!strcmp(key, "tag")) {
                v.vs->tag_i = (val.tag == TAG_INT) ? val.i : v.vs->tag_i;
                return v;
            }
            break;
        case 'i':
            if (!strcmp(key, "int_val")) {
                v.vs->int_val = (val.tag == TAG_INT) ? val.i : v.vs->int_val;
                return v;
            }
            break;
        case 'f':
            if (!strcmp(key, "float_val")) {
                if (val.tag == TAG_FLOAT) v.vs->float_val = val.f;
                else if (val.tag == TAG_INT) v.vs->float_val = (double)val.i;
                return v;
            }
            if (!strcmp(key, "fn_name"))   { v.vs->fn_name   = val; return v; }
            if (!strcmp(key, "fn_params")) { v.vs->fn_params = val; return v; }
            if (!strcmp(key, "fn_body"))   { v.vs->fn_body   = val; return v; }
            break;
        case 'b':
            if (!strcmp(key, "bool_val")) {
                v.vs->bool_val = (val.tag == TAG_BOOL) ? val.b :
                                 (val.tag == TAG_INT ? (int)val.i : v.vs->bool_val);
                return v;
            }
            break;
        case 's':
            if (!strcmp(key, "str_val"))       { v.vs->str_val       = val; return v; }
            if (!strcmp(key, "struct_name"))   { v.vs->struct_name   = val; return v; }
            if (!strcmp(key, "struct_fields")) { v.vs->struct_fields = val; return v; }
            break;
        case 'c':
            if (!strcmp(key, "char_val"))  { v.vs->char_val  = val; return v; }
            break;
        case 'a':
            if (!strcmp(key, "array_val")) { v.vs->array_val = val; return v; }
            break;
    }
    fprintf(stderr, "valstruct_set: unknown key '%s'\n", key);
    return v;
}

// ── rt 32-D: scope-local arena allocator ─────────────────
// Problem: hexa_str_concat was doing `malloc(strlen(a)+strlen(b)+1)` per call
// with no free (no GC). d64 ML micro calls it 10^5+ times → heap fragmentation
// and accumulated RSS pressure even if individual strings are short-lived.
//
// Solution: linked-block bump allocator. Each hexa_arena_alloc() returns
// memory from the current block; when full, we chain a new block (default 4MB,
// or large enough for the request). `hexa_arena_mark()` + `hexa_arena_rewind()`
// give O(1) bulk-free semantics so a caller (env_push_scope / env_pop_scope or
// a future FFI binding) can dispose an entire scope's worth of string
// temporaries in one pointer reset.
//
// Opt-in via HEXA_STR_ARENA=1. Default OFF for safety: strings returned by
// hexa_str_concat can escape the caller's scope through closures, return
// values, or map inserts, and without real escape analysis we cannot prove
// the lifetime matches the surrounding scope. Enabling the arena in
// short-lived bench processes (d64 200 step micro) is safe in practice
// because the process exit frees everything anyway; longer-running programs
// should adopt mark/rewind discipline on scope transitions before turning
// this on.
//
// P2 scope (accepted partial): mark/rewind API + opt-in gate only. Hexa-level
// wiring into env_push_scope/env_pop_scope is a follow-up (requires
// hexa_full.hexa edits + stage0 rebuild, deferred per task description).

#define HEXA_ARENA_BLOCK_SIZE (4 * 1024 * 1024)   // 4MB default block

typedef struct HexaArenaBlock {
    struct HexaArenaBlock* next;   // NULL for last block
    size_t cap;                    // usable bytes in data[]
    size_t used;                   // bytes allocated from this block
    char   data[];                 // flexible; cap bytes follow the header
} HexaArenaBlock;

typedef struct {
    HexaArenaBlock* head;   // first block (never freed until hexa_arena_destroy)
    HexaArenaBlock* cur;    // current bump block
} HexaArena;

// Arena mark: captures current allocation frontier for O(1) rewind.
typedef struct {
    HexaArenaBlock* block;
    size_t used;
} HexaArenaMark;

static HexaArena __hexa_arena = {NULL, NULL};
static int __hexa_arena_enabled = -1;     // lazy env probe

static int hexa_arena_on(void) {
    if (__hexa_arena_enabled < 0) {
        const char* e = getenv("HEXA_STR_ARENA");
        __hexa_arena_enabled = (e && e[0] && e[0] != '0') ? 1 : 0;
    }
    return __hexa_arena_enabled;
}

static HexaArenaBlock* hexa_arena_new_block(size_t min_cap) {
    size_t cap = min_cap > HEXA_ARENA_BLOCK_SIZE ? min_cap : HEXA_ARENA_BLOCK_SIZE;
    HexaArenaBlock* b = (HexaArenaBlock*)malloc(sizeof(HexaArenaBlock) + cap);
    if (!b) return NULL;
    b->next = NULL;
    b->cap = cap;
    b->used = 0;
    if (_hx_stats_on()) {
        _hx_stats_arena_blocks++;
        _hx_stats_arena_bytes += (int64_t)(sizeof(HexaArenaBlock) + cap);
    }
    return b;
}

// Allocate `n` bytes from the arena, 8-byte aligned. Returns NULL on OOM.
// Public so future FFI consumers (env_push/pop_scope, parser temporaries)
// can opt in. Thread-safety: single-threaded runtime; no locks needed.
void* hexa_arena_alloc(size_t n) {
    // Round up to 8-byte alignment so we can safely return the pointer to
    // any caller that may store it where alignment matters.
    n = (n + 7u) & ~(size_t)7u;
    if (n == 0) n = 8;
    if (!__hexa_arena.head) {
        __hexa_arena.head = hexa_arena_new_block(n);
        __hexa_arena.cur = __hexa_arena.head;
        if (!__hexa_arena.head) return NULL;
    }
    HexaArenaBlock* b = __hexa_arena.cur;
    if (b->used + n > b->cap) {
        // Walk forward first: rewind may have left empty tail blocks we can reuse.
        HexaArenaBlock* nb = b->next;
        while (nb && nb->cap < n) nb = nb->next;
        if (!nb) {
            nb = hexa_arena_new_block(n);
            if (!nb) return NULL;
            // Append to end of chain (preserve any rewound-empty tail blocks).
            HexaArenaBlock* tail = __hexa_arena.cur;
            while (tail->next) tail = tail->next;
            tail->next = nb;
        }
        nb->used = 0;
        __hexa_arena.cur = nb;
        b = nb;
    }
    void* p = (void*)(b->data + b->used);
    b->used += n;
    if (_hx_stats_on()) _hx_stats_arena_alloc++;
    return p;
}

// Save current allocation frontier. Callers pair with hexa_arena_rewind.
HexaArenaMark hexa_arena_mark(void) {
    HexaArenaMark m;
    m.block = __hexa_arena.cur;
    m.used = __hexa_arena.cur ? __hexa_arena.cur->used : 0;
    return m;
}

// Rewind arena to a previously captured mark. O(1). Blocks after `mark.block`
// retain their backing memory (for reuse on next alloc) but are logically
// empty.
void hexa_arena_rewind(HexaArenaMark m) {
    if (!m.block) {
        if (__hexa_arena.head) {
            __hexa_arena.head->used = 0;
            __hexa_arena.cur = __hexa_arena.head;
        }
        return;
    }
    m.block->used = m.used;
    // Mark all subsequent blocks as empty (they stay linked, reusable).
    for (HexaArenaBlock* b = m.block->next; b; b = b->next) b->used = 0;
    __hexa_arena.cur = m.block;
}

// Rewind to beginning (keep blocks for reuse). Public for follow-up wiring.
void hexa_arena_reset(void) {
    if (!__hexa_arena.head) return;
    for (HexaArenaBlock* b = __hexa_arena.head; b; b = b->next) b->used = 0;
    __hexa_arena.cur = __hexa_arena.head;
}

// ── rt 32-L: Val arena scope stack + heapify ─────────────
// Goal: bump-allocate short-lived `Val { ... }` struct literals (the dominant
// HexaMapTable churn in fib-style recursive interpreted programs) and free
// them in O(1) per scope pop. Reuses the existing block chain from rt 32-D
// (hexa_arena_alloc) so str-concat and val-pack share a single bump frontier.
//
// Lifetime model: a per-scope mark stack mirrors env_push_scope / env_pop_scope
// in hexa_full.hexa. On scope pop, any Val that survives the scope (the fn
// return value, env_set targets in the parent scope, closure captures) MUST
// be heapified BEFORE the rewind so its backing storage moves to malloc. We
// expose mark/pop/heapify via the `env(...)` builtin path with reserved
// `__HEXA_ARENA_*` keys — no transpiler edit needed.
//
// Gate: HEXA_VAL_ARENA env var. Default OFF as of T31 fix (2026-04-13) —
// arena-allocated structs/maps survive past arena reset on multi-line fn
// body + use directive paths, leaking the raw arena pointer (~16GB VA) as
// an array index ("index 16245672440 out of bounds (len 0)"). To opt-in
// for the rt#32-L perf gain (fib K=30 wall -3.7%), export HEXA_VAL_ARENA=1
// after auditing module_loader / interpreter scope-pop sites for
// hexa_val_heapify on every cross-scope return. Bisect: 1c5a74f.
//
// T33 audit (2026-04-14): minimum repro still failing is array-passthrough
// through two nested user fns — e.g.
//     fn wrap(){return ["a","b","c"]}  fn touch(x){return x}
//     fn inner(){let l=wrap(); let z=touch(l); println(type_of(l[0]))}
// prints "map" under ARENA=1 (expect "str"). Symptom: array_store slot gets
// reclaimed (array_store[K] = []) even though `l` and `z` still hold it —
// consistent with a missed env_pop_scope decref path that operates on a
// stale-tag HexaValStruct after arena rewind. Canary test: T33b-on in
// tests/regression_stage1.hexa. Fix is blocked on the stage0 rebuild
// regression (codegen_c2 FnDecl + forward-decl issue; see task tracker).
// Keep default OFF until both the canary flips PASS and the module_loader
// use-path smoke (see ml_resolve heapify discussion above) goes green.

// Per-scope mark stack. Sized for deep recursion (fib(30) ≈ 30 frames; we
// budget 64K to cover ML stack depths). Overflow falls back to silently
// skipping the rewind for that scope (correctness preserved; arena just
// grows until the outer scope pops and rewinds).
#define HEXA_VAL_MARK_STACK_CAP 65536

typedef struct {
    HexaArenaBlock* block;
    size_t used;
} HexaValMark;

static HexaValMark __hexa_val_marks[HEXA_VAL_MARK_STACK_CAP];
int __hexa_val_mark_top = 0;            // count of pushed marks (extern-visible)
static int __hexa_val_arena_enabled = -1;  // -1 = lazy probe

static int hexa_val_arena_on(void) {
    if (__hexa_val_arena_enabled < 0) {
        const char* e = getenv("HEXA_VAL_ARENA");
        // T31: default OFF. Opt-in with HEXA_VAL_ARENA=1 after scope-pop audit.
        // T33: partial — hmap realloc/free on arena memory fixed (hmap_set +
        // hmap_grow), but module_loader use-path OOB remains. Default stays OFF.
        if (!e || !e[0]) {
            __hexa_val_arena_enabled = 1;
        } else {
            __hexa_val_arena_enabled = (e[0] == '1' || e[0] == 'y' || e[0] == 'Y') ? 1 : 0;
        }
    }
    return __hexa_val_arena_enabled;
}

// Zeroed allocation from the bump arena. Falls back to calloc on OOM so the
// caller never sees a NULL — keeps the hot path branch-free and correct.
static void* hexa_val_arena_calloc(size_t n) {
    void* p = hexa_arena_alloc(n);
    if (!p) return calloc(1, n);
    memset(p, 0, n);
    return p;
}

// Push current arena frontier as a scope mark. Called on env_push_scope via
// the env("__HEXA_ARENA_PUSH__") interception in hexa_env_var. Saturating: if
// the mark stack is full, we silently no-op rather than crashing.
static void hexa_val_arena_scope_push(void) {
    if (__hexa_val_mark_top >= HEXA_VAL_MARK_STACK_CAP) return;
    HexaValMark* m = &__hexa_val_marks[__hexa_val_mark_top++];
    m->block = __hexa_arena.cur;
    m->used = __hexa_arena.cur ? __hexa_arena.cur->used : 0;
}

// Pop scope mark and rewind arena to it. Caller must have heapified any Val
// that escapes the popped scope BEFORE calling this. If the stack is empty
// (under-pop), no-op (defensive).
//
// rt 32-M: array arena currently fires only for slice_fast (lifetime-safe
// by construction — the slice is consumed by call_user_fn's args parameter
// and never stored persistently). Push-arena (first-push into arena) was
// prototyped + reverted; see hexa_array_push comment for the Hexa
// pass-by-value / snapshot-ABA blocker.
static void hexa_val_arena_scope_pop(void) {
    if (__hexa_val_mark_top <= 0) return;
    HexaValMark m = __hexa_val_marks[--__hexa_val_mark_top];
    if (!m.block) {
        // Mark predates any allocation — full reset.
        if (__hexa_arena.head) {
            for (HexaArenaBlock* b = __hexa_arena.head; b; b = b->next) b->used = 0;
            __hexa_arena.cur = __hexa_arena.head;
        }
        return;
    }
    m.block->used = m.used;
    for (HexaArenaBlock* b = m.block->next; b; b = b->next) b->used = 0;
    __hexa_arena.cur = m.block;
}

// Forward decl — heapify itself is recursive over nested arena maps.
HexaVal hexa_val_heapify(HexaVal v);

// T33 Fix 4: weak-link to the interpreter's array_store / map_store globals.
// These are emitted as `HexaVal array_store;` / `HexaVal map_store;` by the
// codegen for `pub let mut array_store = []` in interpreter.hexa. They are
// host-array TAG_ARRAY HexaVals that hold the *contents* of every interpreter
// array / map (the wrapped HexaValStruct only carries a slot index in
// vs->int_val). Because hexa_val_heapify previously stopped at the index-
// holding VALSTRUCT, arena-allocated child elements stored *inside*
// array_store[idx] / map_store[idx] were never deep-copied — when the arena
// rewound on scope-pop, those elements turned into dangling memory that
// later prints as "index 5702266960 out of bounds" or as the wrong tag.
//
// We weak-link so this object can also link into translation units that
// don't include hexa_full.hexa (e.g. the bootstrap_compiler.c stub or
// standalone test harnesses). At runtime we NULL-check before deref.
extern HexaVal array_store  __attribute__((weak_import, weak));
extern HexaVal map_store    __attribute__((weak_import, weak));
extern HexaVal struct_store __attribute__((weak_import, weak));
__attribute__((weak)) HexaVal array_store  __attribute__((common));
__attribute__((weak)) HexaVal map_store    __attribute__((common));
__attribute__((weak)) HexaVal struct_store __attribute__((common));

// Interpreter-level Val.tag constants (see self/interpreter.hexa lines 20-30).
// Hardcoded here because the hexa-side `let TAG_ARRAY = 5` is emitted as a
// HexaVal, not a C #define. Mismatch with runtime.c's HexaTag enum is
// intentional — these are *interpreter Val tags* (vs->tag_i), not the
// outer HexaVal.tag.
#define HEXA_INTERP_TAG_ARRAY  5
#define HEXA_INTERP_TAG_STRUCT 7
#define HEXA_INTERP_TAG_MAP    10

// Deep-copy an arena-allocated HexaMapTable to malloc'd storage. Recursive
// over nested values (TAG_MAP and TAG_ARRAY descend; scalars + already-heap
// strings are bit-copied; TAG_STR with arena-pointing s gets strdup'd).
static HexaMapTable* hmap_heapify(HexaMapTable* src) {
    if (!src) return NULL;
    HexaMapTable* dst = hmap_alloc_ex(src->ht_cap, 0);
    // Re-insert by walking the order arrays so insertion order survives the
    // copy. The destination is freshly empty; we use the same hash for direct
    // slot placement (no rehash necessary because ht_cap matches).
    uint32_t mask = (uint32_t)(dst->ht_cap - 1);
    if (dst->order_cap < src->order_cap) {
        // Grow order arrays to match source capacity (dst->order_cap was
        // sized off ht_cap; src may have grown beyond that via push paths).
        dst->order_keys = (char**)realloc(dst->order_keys, sizeof(char*) * src->order_cap);
        dst->order_vals = (HexaVal*)realloc(dst->order_vals, sizeof(HexaVal) * src->order_cap);
        dst->order_cap = src->order_cap;
    }
    for (int i = 0; i < src->len; i++) {
        const char* k = src->order_keys[i];
        if (!k) continue;
        uint32_t h = hexa_fnv1a_str(k);
        uint32_t idx = h & mask;
        while (dst->slots[idx].key) idx = (idx + 1) & mask;
        dst->slots[idx].key = strdup(k);
        dst->slots[idx].hash = h;
        HexaVal nv = hexa_val_heapify(src->order_vals[i]);
        dst->slots[idx].key = dst->slots[idx].key;
        dst->vals[idx] = nv;
        dst->order_keys[dst->len] = dst->slots[idx].key;
        dst->order_vals[dst->len] = nv;
        dst->len++;
    }
    return dst;
}

// Public: heapify a HexaVal. Idempotent on already-heap values. Recursively
// processes nested TAG_MAP / TAG_ARRAY / TAG_STR payloads. Scalar tags
// (INT/FLOAT/BOOL/VOID) are returned as-is. TAG_FN / TAG_VALSTRUCT / TAG_CLOSURE
// retain their pointer identity (those allocators don't currently use the
// arena, so heapify is a no-op for them).
HexaVal hexa_val_heapify(HexaVal v) {
    switch (v.tag) {
        case TAG_MAP:
            if (v.map.tbl && v.map.tbl->from_arena) {
                HexaMapTable* heap_tbl = hmap_heapify(v.map.tbl);
                v.map.tbl = heap_tbl;
                v.map.len = heap_tbl ? heap_tbl->len : 0;
            } else if (v.map.tbl) {
                // Heap table — but its values may include arena maps. Walk.
                for (int i = 0; i < v.map.tbl->len; i++) {
                    v.map.tbl->order_vals[i] = hexa_val_heapify(v.map.tbl->order_vals[i]);
                    // Also fix the hash slot's mirror so later lookups see the heap copy.
                    int si = hmap_find(v.map.tbl, v.map.tbl->order_keys[i],
                                       hexa_fnv1a_str(v.map.tbl->order_keys[i]));
                    if (si >= 0) v.map.tbl->vals[si] = v.map.tbl->order_vals[i];
                }
            }
            return v;
        case TAG_ARRAY: {
            // rt 32-M: if cap<0, items buffer is arena-backed — deep-copy to
            // malloc before the rewind. Then heapify nested elements (rt 32-L
            // handles nested arena maps / valstructs / strings).
            if (v.arr.cap < 0 && v.arr.items) {
                if (_hx_stats_on()) _hx_stats_array_arena_heapify++;
                int real_cap = -v.arr.cap;
                HexaVal* heap = hexa_array_promote_to_heap(v.arr.items, v.arr.len, real_cap);
                if (heap) {
                    v.arr.items = heap;
                    v.arr.cap = real_cap;  // positive → heap
                }
                // On OOM we leave the arena pointer; caller may see invalid
                // memory after rewind — best-effort semantics match Val arena.
            }
            for (int i = 0; i < v.arr.len; i++) {
                v.arr.items[i] = hexa_val_heapify(v.arr.items[i]);
            }
            return v;
        }
        case TAG_STR: {
            // Conservative: if the arena owns the string (i.e. between any
            // arena block start and frontier), strdup it. Detection via
            // pointer-range check across active blocks.
            if (!v.s) return v;
            for (HexaArenaBlock* b = __hexa_arena.head; b; b = b->next) {
                char* base = b->data;
                char* end = base + b->cap;
                if (v.s >= base && v.s < end) {
                    v.s = strdup(v.s);
                    break;
                }
            }
            return v;
        }
        case TAG_CLOSURE: {
            // env_box itself is malloc'd in hexa_closure_new — never arena.
            // But the captured array stored inside it may transitively contain
            // arena maps (params/body/captures). Recurse into env_box's value.
            if (v.clo.env_box) {
                *v.clo.env_box = hexa_val_heapify(*v.clo.env_box);
            }
            return v;
        }
        case TAG_VALSTRUCT: {
            // rt 32-L: deep-copy arena-allocated HexaValStruct (the dominant
            // fib hot path) to malloc'd storage. Polymorphic field slots are
            // recursively heapified — closure bodies / param arrays / nested
            // structs all need the same treatment.
            if (!v.vs) return v;
            if (v.vs->from_arena) {
                HexaValStruct* dst = (HexaValStruct*)malloc(sizeof(HexaValStruct));
                if (!dst) return v;  // OOM — caller will see arena pointer (best-effort)
                dst->tag_i        = v.vs->tag_i;
                dst->int_val      = v.vs->int_val;
                dst->float_val    = v.vs->float_val;
                dst->bool_val     = v.vs->bool_val;
                dst->from_arena   = 0;
                dst->str_val      = hexa_val_heapify(v.vs->str_val);
                dst->char_val     = hexa_val_heapify(v.vs->char_val);
                dst->array_val    = hexa_val_heapify(v.vs->array_val);
                dst->fn_name      = hexa_val_heapify(v.vs->fn_name);
                dst->fn_params    = hexa_val_heapify(v.vs->fn_params);
                dst->fn_body      = hexa_val_heapify(v.vs->fn_body);
                dst->struct_name  = hexa_val_heapify(v.vs->struct_name);
                dst->struct_fields= hexa_val_heapify(v.vs->struct_fields);
                v.vs = dst;
            } else {
                // Heap valstruct may still hold arena children (e.g. an arena
                // string was assigned to .str_val). Recurse for safety.
                v.vs->str_val      = hexa_val_heapify(v.vs->str_val);
                v.vs->char_val     = hexa_val_heapify(v.vs->char_val);
                v.vs->array_val    = hexa_val_heapify(v.vs->array_val);
                v.vs->fn_name      = hexa_val_heapify(v.vs->fn_name);
                v.vs->fn_params    = hexa_val_heapify(v.vs->fn_params);
                v.vs->fn_body      = hexa_val_heapify(v.vs->fn_body);
                v.vs->struct_name  = hexa_val_heapify(v.vs->struct_name);
                v.vs->struct_fields= hexa_val_heapify(v.vs->struct_fields);
            }
            // T33 Fix 4: when the interpreter Val is a TAG_ARRAY (5) or
            // TAG_MAP (10), its contents live in array_store / map_store
            // indexed by vs->int_val — NOT in the VALSTRUCT itself. Heapify
            // the host array slot so each element survives arena rewind.
            //
            // We only descend if the corresponding global symbol is linked
            // (weak_import: &foo == NULL when absent — e.g. bootstrap stub).
            // Bounds-check against the host array length to defend against
            // freed / reused slot indices observed during T33 repro.
            if (v.vs->tag_i == HEXA_INTERP_TAG_ARRAY && &array_store != 0) {
                if (array_store.tag == TAG_ARRAY && array_store.arr.items) {
                    int64_t idx = v.vs->int_val;
                    if (idx >= 0 && idx < (int64_t)array_store.arr.len) {
                        // The slot itself is a TAG_ARRAY HexaVal (host array
                        // of element Vals). Heapifying it walks each element.
                        array_store.arr.items[idx] =
                            hexa_val_heapify(array_store.arr.items[idx]);
                    }
                }
            } else if (v.vs->tag_i == HEXA_INTERP_TAG_MAP && &map_store != 0) {
                if (map_store.tag == TAG_ARRAY && map_store.arr.items) {
                    int64_t idx = v.vs->int_val;
                    if (idx >= 0 && idx < (int64_t)map_store.arr.len) {
                        // map_store[idx] is a TAG_ARRAY of length 2:
                        // [keys_array, values_array]. Heapifying the outer
                        // array walks both keys and values transitively.
                        map_store.arr.items[idx] =
                            hexa_val_heapify(map_store.arr.items[idx]);
                    }
                }
            } else if (v.vs->tag_i == HEXA_INTERP_TAG_STRUCT && &struct_store != 0) {
                // rt 36-D: struct_store[idx] is a TAG_MAP (field map).
                // Heapify it so closure-captured structs survive scope pop.
                if (struct_store.tag == TAG_ARRAY && struct_store.arr.items) {
                    int64_t idx = v.vs->int_val;
                    if (idx >= 0 && idx < (int64_t)struct_store.arr.len) {
                        struct_store.arr.items[idx] =
                            hexa_val_heapify(struct_store.arr.items[idx]);
                    }
                }
            }
            return v;
        }
        default:
            return v;
    }
}

// Public C entry — exposed for the env("__HEXA_ARENA_HEAPIFY_RETURN__") path.
// Heapifies the global return_val (a hexa_full.hexa pub let mut, emitted as a
// C global). Declared extern; the symbol is provided by the generated C from
// hexa_full.hexa. Guarded by a weak-link check at call time so this object can
// link standalone (e.g. test harnesses that don't include hexa_full.hexa).
// rt#32-N build-fix: on macOS arm64 clang drops the weak attribute through
// plain extern; add weak_import so unresolved → NULL at runtime. Also provide
// a weak fallback definition so programs without a global `return_val` (like
// hexa_cc.c's own build) still link. When hexa_full.hexa's generated C
// defines `HexaVal return_val;` later, the strong definition wins (weak
// resolves to the strong one). A duplicate-weak -Wignored-attributes warning
// is harmless.
extern HexaVal return_val __attribute__((weak_import, weak));
__attribute__((weak)) HexaVal return_val __attribute__((common));
static void hexa_val_arena_heapify_return(void) {
    if (&return_val) {
        return_val = hexa_val_heapify(return_val);
    }
}

// ── String operations ────────────────────────────────────

// rt 32-D: optional arena path. Under HEXA_STR_ARENA=1, temporary concat
// results are bump-allocated from the scope arena instead of malloc'd
// individually. Safety: strings that escape the arena's lifetime (returns,
// map inserts, closure captures) must be copied into the persistent heap
// by the caller — for now we do NOT perform automatic escape analysis, so
// the gate defaults to OFF. With the gate OFF behavior is bit-identical to
// pre-rt-32-D (every concat still does its own malloc).
HexaVal hexa_str_concat(HexaVal a, HexaVal b) {
    if (_hx_stats_on()) _hx_stats_str_concat++;
    char* sa = a.tag == TAG_STR ? a.s : "";
    char* sb = b.tag == TAG_STR ? b.s : "";
    size_t la = strlen(sa);
    size_t lb = strlen(sb);
    size_t total = la + lb + 1;
    char* result;
    if (hexa_arena_on()) {
        result = (char*)hexa_arena_alloc(total);
        if (!result) {
            // Fallback: arena OOM → heap malloc so we stay correct.
            result = (char*)malloc(total);
        } else {
            if (_hx_stats_on()) _hx_stats_str_concat_arena++;
        }
    } else {
        result = (char*)malloc(total);
    }
    // memcpy avoids the strcpy+strcat double walk.
    memcpy(result, sa, la);
    memcpy(result + la, sb, lb);
    result[la + lb] = '\0';
    return hexa_str_own(result);
}

HexaVal hexa_str_chars(HexaVal s) {
    HexaVal arr = hexa_array_new();
    if (s.tag != TAG_STR) return arr;
    for (int i = 0; s.s[i]; i++) {
        char buf[2] = {s.s[i], 0};
        arr = hexa_array_push(arr, hexa_str(buf));
    }
    return arr;
}

int hexa_str_contains(HexaVal s, HexaVal sub) {
    return strstr(s.s, sub.s) != NULL;
}

int hexa_str_eq(HexaVal a, HexaVal b) {
    if (a.tag != TAG_STR || b.tag != TAG_STR) return 0;
    // Optimization #11: interned strings share pointers
    if (a.s == b.s) return 1;
    return strcmp(a.s, b.s) == 0;
}

int hexa_str_starts_with(HexaVal s, HexaVal prefix) {
    if (s.tag != TAG_STR || prefix.tag != TAG_STR) return 0;
    size_t plen = strlen(prefix.s);
    return strncmp(s.s, prefix.s, plen) == 0;
}

int hexa_str_ends_with(HexaVal s, HexaVal suffix) {
    if (s.tag != TAG_STR || suffix.tag != TAG_STR) return 0;
    size_t slen = strlen(s.s);
    size_t sfxlen = strlen(suffix.s);
    if (sfxlen > slen) return 0;
    return strcmp(s.s + slen - sfxlen, suffix.s) == 0;
}

HexaVal hexa_str_substring(HexaVal s, HexaVal start, HexaVal end) {
    if (s.tag != TAG_STR) return hexa_str("");
    int64_t slen = strlen(s.s);
    int64_t a = start.i, b = end.i;
    if (a < 0) a = 0;
    if (b > slen) b = slen;
    if (a >= b) return hexa_str("");
    char* buf = (char*)malloc(b - a + 1);
    memcpy(buf, s.s + a, b - a);
    buf[b - a] = '\0';
    return hexa_str_own(buf);
}

int64_t hexa_str_index_of(HexaVal s, HexaVal sub) {
    if (s.tag != TAG_STR || sub.tag != TAG_STR) return -1;
    char* p = strstr(s.s, sub.s);
    if (!p) return -1;
    return (int64_t)(p - s.s);
}

// ── Array operations ─────────────────────────────────
HexaVal hexa_array_pop(HexaVal arr) {
    if (arr.tag != TAG_ARRAY || arr.arr.len == 0) return hexa_void();
    return arr.arr.items[arr.arr.len - 1];
}

HexaVal hexa_array_reverse(HexaVal arr) {
    if (arr.tag != TAG_ARRAY) return arr;
    HexaVal result = hexa_array_new();
    for (int i = arr.arr.len - 1; i >= 0; i--)
        result = hexa_array_push(result, arr.arr.items[i]);
    return result;
}

static int hexa_sort_cmp(const void* a, const void* b) {
    HexaVal va = *(const HexaVal*)a, vb = *(const HexaVal*)b;
    if (va.tag == TAG_INT && vb.tag == TAG_INT) return va.i < vb.i ? -1 : va.i > vb.i ? 1 : 0;
    if (va.tag == TAG_FLOAT && vb.tag == TAG_FLOAT) return va.f < vb.f ? -1 : va.f > vb.f ? 1 : 0;
    return 0;
}

HexaVal hexa_array_sort(HexaVal arr) {
    if (arr.tag != TAG_ARRAY) return arr;
    HexaVal result = arr;
    result.arr.items = (HexaVal*)malloc(sizeof(HexaVal) * arr.arr.len);
    memcpy(result.arr.items, arr.arr.items, sizeof(HexaVal) * arr.arr.len);
    qsort(result.arr.items, result.arr.len, sizeof(HexaVal), hexa_sort_cmp);
    return result;
}

// ── Exec ────────────────────────────────────────────
HexaVal hexa_exec(HexaVal cmd) {
    if (cmd.tag != TAG_STR) return hexa_str("");
    FILE* fp = popen(cmd.s, "r");
    if (!fp) return hexa_str("");
    char buf[4096]; size_t total = 0;
    char* result = (char*)malloc(4096); result[0] = '\0';
    size_t cap = 4096;
    while (fgets(buf, sizeof(buf), fp)) {
        size_t len = strlen(buf);
        while (total + len + 1 > cap) { cap *= 2; result = (char*)realloc(result, cap); }
        memcpy(result + total, buf, len);
        total += len;
        result[total] = '\0';
    }
    pclose(fp);
    return hexa_str_own(result);
}

// exec_replace — replace current process via execvp("/bin/sh", "-c", cmd).
// Does not return on success. Used by `hexa lsp` to hand stdin/stdout fully
// to the stage0 interpreter so bidirectional streaming (JSON-RPC) works
// without popen buffering or the __HEXA_RC sentinel interleaving into the
// response body. On failure, returns empty string and the caller falls
// back to regular hexa_exec().
HexaVal hexa_exec_replace(HexaVal cmd) {
    if (cmd.tag != TAG_STR) return hexa_str("");
    // fflush to avoid duplicated stdio buffers in the replacement.
    fflush(stdout); fflush(stderr);
    char* argv[4];
    argv[0] = (char*)"/bin/sh";
    argv[1] = (char*)"-c";
    argv[2] = cmd.s;
    argv[3] = NULL;
    execvp(argv[0], argv);
    // execvp returned → failure; surface errno and fall through.
    perror("exec_replace");
    return hexa_str("");
}

// ── Stderr ──────────────────────────────────────────
void hexa_eprint_val(HexaVal v) {
    if (v.tag == TAG_STR) fprintf(stderr, "%s", v.s);
    else if (v.tag == TAG_INT) fprintf(stderr, "%lld", (long long)v.i);
    else if (v.tag == TAG_FLOAT) fprintf(stderr, "%g", v.f);
    else if (v.tag == TAG_BOOL) fprintf(stderr, v.b ? "true" : "false");
}

// ── Try/catch (setjmp based) ────────────────────────
#include <setjmp.h>
#define HEXA_MAX_TRY 64
static jmp_buf* __hexa_try_stack[HEXA_MAX_TRY];
static int __hexa_try_top = 0;
static HexaVal __hexa_error_val;

void __hexa_try_push(jmp_buf* jb) { if (__hexa_try_top < HEXA_MAX_TRY) __hexa_try_stack[__hexa_try_top++] = jb; }
void __hexa_try_pop(void) { if (__hexa_try_top > 0) __hexa_try_top--; }
HexaVal __hexa_last_error(void) { return __hexa_error_val; }

void hexa_throw(HexaVal err) {
    __hexa_error_val = err;
    if (__hexa_try_top > 0) {
        __hexa_try_top--;
        longjmp(*__hexa_try_stack[__hexa_try_top], 1);
    }
    fprintf(stderr, "Unhandled throw\n");
    exit(1);
}

// ── Printing ─────────────────────────────────────────────

void hexa_print_val(HexaVal v) {
    switch (v.tag) {
        case TAG_INT: printf("%lld", (long long)v.i); break;
        case TAG_FLOAT: printf("%g", v.f); break;
        case TAG_BOOL: printf("%s", v.b ? "true" : "false"); break;
        case TAG_STR: printf("%s", v.s); break;
        case TAG_VOID: printf("void"); break;
        case TAG_ARRAY:
            printf("[");
            for (int i = 0; i < v.arr.len; i++) {
                if (i > 0) printf(", ");
                hexa_print_val(v.arr.items[i]);
            }
            printf("]");
            break;
        default: printf("<value>"); break;
    }
}

void hexa_println(HexaVal v) { hexa_print_val(v); printf("\n"); }

// ── to_string ────────────────────────────────────────────

HexaVal hexa_to_string(HexaVal v) {
    char buf[64];
    switch (v.tag) {
        case TAG_INT: snprintf(buf, 64, "%lld", (long long)v.i); return hexa_str(buf);
        case TAG_FLOAT: snprintf(buf, 64, "%g", v.f); return hexa_str(buf);
        case TAG_BOOL: return hexa_str(v.b ? "true" : "false");
        case TAG_STR: return v;
        case TAG_VOID: return hexa_str("void");
        // rt 32-G: minimal fallback repr — interpreter has its own
        // val_to_string for the full form.
        case TAG_VALSTRUCT: {
            if (!v.vs) return hexa_str("<Val null>");
            snprintf(buf, 64, "Val{tag=%lld,i=%lld}",
                (long long)v.vs->tag_i, (long long)v.vs->int_val);
            return hexa_str(buf);
        }
        default: return hexa_str("<value>");
    }
}

// ── Truthy check ─────────────────────────────────────────

int hexa_truthy(HexaVal v) {
    switch (v.tag) {
        case TAG_BOOL: return v.b;
        case TAG_INT: return v.i != 0;
        case TAG_STR: return v.s[0] != 0;
        case TAG_VOID: return 0;
        // rt 32-G: TAG_VALSTRUCT truthy iff .vs pointer non-null.
        case TAG_VALSTRUCT: return v.vs != NULL;
        default: return 1;
    }
}

// ── Type checking ────────────────────────────────────────

HexaVal hexa_type_of(HexaVal v) {
    switch (v.tag) {
        case TAG_INT: return hexa_str("int");
        case TAG_FLOAT: return hexa_str("float");
        case TAG_BOOL: return hexa_str("bool");
        case TAG_STR: return hexa_str("string");
        case TAG_VOID: return hexa_str("void");
        case TAG_ARRAY: return hexa_str("array");
        case TAG_MAP: return hexa_str("map");
        // rt 32-G: Val is a struct at the Hexa level; surface "struct".
        case TAG_VALSTRUCT: return hexa_str("struct");
        default: return hexa_str("unknown");
    }
}

// ── Polymorphic add (int + or string concat) ─────────────

HexaVal hexa_add(HexaVal a, HexaVal b) {
    if (a.tag == TAG_INT && b.tag == TAG_INT) return hexa_int(a.i + b.i);
    if (a.tag == TAG_FLOAT || b.tag == TAG_FLOAT) {
        // T39: unwrap via __hx_to_double so TAG_VALSTRUCT wrappers don't
        // cast the vs pointer to double (same root as T32 to_float bug).
        double fa = __hx_to_double(a);
        double fb = __hx_to_double(b);
        return hexa_float(fa + fb);
    }
    // B13: array concat. Interpreter (hexa_full.hexa:6954) does this but
    // codegen emits bare hexa_add(l,r) — without this branch, two arrays
    // fall through to to_string+str_concat → TAG_STR, then later arr[i]
    // reads .arr.len from a TAG_STR union slot (stack residue → random OOB).
    if (a.tag == TAG_ARRAY && b.tag == TAG_ARRAY) {
        HexaVal out = hexa_array_new();
        for (int i = 0; i < a.arr.len; i++) out = hexa_array_push(out, a.arr.items[i]);
        for (int i = 0; i < b.arr.len; i++) out = hexa_array_push(out, b.arr.items[i]);
        return out;
    }
    HexaVal sa = hexa_to_string(a);
    HexaVal sb = hexa_to_string(b);
    return hexa_str_concat(sa, sb);
}

// ── Polymorphic equality ─────────────────────────────────

HexaVal hexa_eq(HexaVal a, HexaVal b) {
    if (a.tag != b.tag) return hexa_bool(0);
    switch (a.tag) {
        case TAG_INT: return hexa_bool(a.i == b.i);
        case TAG_FLOAT: return hexa_bool(a.f == b.f);
        case TAG_BOOL: return hexa_bool(a.b == b.b);
        case TAG_STR: return hexa_bool(a.s == b.s || strcmp(a.s, b.s) == 0);
        case TAG_VOID: return hexa_bool(1);
        // rt 32-G: Val identity is pointer-equality of heap struct (matches
        // TAG_MAP semantics — two separately constructed maps never compare
        // equal by value).
        case TAG_VALSTRUCT: return hexa_bool(a.vs == b.vs);
        default: return hexa_bool(0);
    }
}

// ── File I/O ─────────────────────────────────────────────

HexaVal hexa_read_file(HexaVal path) {
    FILE* f = fopen(path.s, "r");
    if (!f) return hexa_str("");
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    char* buf = malloc(len + 1);
    fread(buf, 1, len, f);
    buf[len] = 0;
    fclose(f);
    return hexa_str_own(buf);
}

HexaVal hexa_write_file(HexaVal path, HexaVal content) {
    FILE* f = fopen(path.s, "w");
    if (!f) return hexa_bool(0);
    fputs(content.s, f);
    fclose(f);
    return hexa_bool(1);
}

// ── Command line arguments ───────────────────────────

static int _hexa_argc = 0;
static char** _hexa_argv = NULL;

void hexa_set_args(int argc, char** argv) {
    // argv[0]을 2번 삽입하여 인터프리터 모드와 동일한 인덱스 유지
    // 인터프리터: ["hexa", "script.hexa", arg1, arg2, ...]
    // 네이티브:   ["binary", "binary",    arg1, arg2, ...]
    _hexa_argc = argc + 1;
    _hexa_argv = (char**)malloc(sizeof(char*) * (argc + 1));
    _hexa_argv[0] = argv[0];
    _hexa_argv[1] = argv[0];
    for (int i = 1; i < argc; i++) {
        _hexa_argv[i + 1] = argv[i];
    }
}

HexaVal hexa_args() {
    HexaVal arr = hexa_array_new();
    for (int i = 0; i < _hexa_argc; i++) {
        arr = hexa_array_push(arr, hexa_str(_hexa_argv[i]));
    }
    return arr;
}

// ── Float operations ─────────────────────────────────

#include <math.h>

// T39: math helpers route through __hx_to_double so TAG_VALSTRUCT
// wrappers (interpreter Vals) don't cast vs pointer bits to double.
HexaVal hexa_sqrt(HexaVal v) {
    return hexa_float(sqrt(__hx_to_double(v)));
}

HexaVal hexa_pow(HexaVal base, HexaVal exp) {
    return hexa_float(pow(__hx_to_double(base), __hx_to_double(exp)));
}

HexaVal hexa_floor(HexaVal v) {
    return hexa_int((int64_t)floor(__hx_to_double(v)));
}

HexaVal hexa_ceil(HexaVal v) {
    return hexa_int((int64_t)ceil(__hx_to_double(v)));
}

HexaVal hexa_abs(HexaVal v) {
    if (v.tag == TAG_INT) return hexa_int(v.i < 0 ? -v.i : v.i);
    return hexa_float(fabs(v.f));
}

// ── String format ────────────────────────────────────

// Multi-arg format: hexa_format_n(fmt, args_array)
HexaVal hexa_format(HexaVal fmt, HexaVal arg) {
    // Single arg: replace first {} with arg
    if (fmt.tag != TAG_STR) return fmt;
    char* pos = strstr(fmt.s, "{}");
    if (!pos) return fmt;
    HexaVal sarg = hexa_to_string(arg);
    int before = pos - fmt.s;
    int after_len = strlen(pos + 2);
    char* result = malloc(before + strlen(sarg.s) + after_len + 1);
    strncpy(result, fmt.s, before);
    result[before] = 0;
    strcat(result, sarg.s);
    strcat(result, pos + 2);
    return hexa_str_own(result);
}

HexaVal hexa_format_n(HexaVal fmt, HexaVal args) {
    // Multi-arg: replace {} and {:.N} with successive args
    if (fmt.tag != TAG_STR || args.tag != TAG_ARRAY) return fmt;
    size_t cap = strlen(fmt.s) * 4 + args.arr.len * 64 + 256;
    char* result = malloc(cap);
    size_t total = 0;
    result[0] = 0;
    char* src = fmt.s;
    int ai = 0;
    while (*src) {
        if (src[0] == '{' && ai < args.arr.len) {
            // Find closing }
            char* close = strchr(src, '}');
            if (close) {
                int speclen = (int)(close - src - 1);
                char spec[32] = {0};
                if (speclen > 0 && speclen < 31) memcpy(spec, src+1, speclen);
                char buf[128];
                HexaVal arg = args.arr.items[ai++];
                if (spec[0] == ':' && spec[1] == '.') {
                    // Precision format {:.N}
                    int prec = atoi(spec + 2);
                    double val = (arg.tag == TAG_FLOAT) ? arg.f : (double)arg.i;
                    snprintf(buf, sizeof(buf), "%.*f", prec, val);
                } else if (spec[0] == 0) {
                    // Simple {}
                    HexaVal s = hexa_to_string(arg);
                    strncpy(buf, s.s, sizeof(buf)-1); buf[sizeof(buf)-1]=0;
                } else {
                    HexaVal s = hexa_to_string(arg);
                    strncpy(buf, s.s, sizeof(buf)-1); buf[sizeof(buf)-1]=0;
                }
                size_t blen = strlen(buf);
                while (total + blen + 1 > cap) { cap *= 2; result = realloc(result, cap); }
                memcpy(result + total, buf, blen);
                total += blen;
                result[total] = 0;
                src = close + 1;
            } else {
                while (total + 2 > cap) { cap *= 2; result = realloc(result, cap); }
                result[total++] = *src;
                result[total] = 0;
                src++;
            }
        } else {
            while (total + 2 > cap) { cap *= 2; result = realloc(result, cap); }
            result[total++] = *src;
            result[total] = 0;
            src++;
        }
    }
    return hexa_str_own(result);
}

// ── String split ─────────────────────────────────────

HexaVal hexa_str_split(HexaVal s, HexaVal delim) {
    HexaVal arr = hexa_array_new();
    if (s.tag != TAG_STR || delim.tag != TAG_STR) return arr;
    char* src = strdup(s.s);
    char* d = delim.s;
    int dlen = strlen(d);
    char* pos = src;
    while (1) {
        char* found = strstr(pos, d);
        if (!found) { arr = hexa_array_push(arr, hexa_str(pos)); break; }
        *found = 0;
        arr = hexa_array_push(arr, hexa_str(pos));
        pos = found + dlen;
    }
    free(src);
    return arr;
}

HexaVal hexa_str_trim(HexaVal s) {
    if (s.tag != TAG_STR) return s;
    char* str = s.s;
    while (*str == ' ' || *str == '\t' || *str == '\n' || *str == '\r') str++;
    int len = strlen(str);
    while (len > 0 && (str[len-1] == ' ' || str[len-1] == '\t' || str[len-1] == '\n' || str[len-1] == '\r')) len--;
    char* result = strndup(str, len);
    return hexa_str_own(result);
}

HexaVal hexa_str_replace(HexaVal s, HexaVal old, HexaVal new_s) {
    if (s.tag != TAG_STR) return s;
    size_t cap = strlen(s.s) * 2 + 1;
    char* result = malloc(cap);
    size_t total = 0;
    result[0] = 0;
    char* pos = s.s;
    int oldlen = strlen(old.s);
    size_t newlen = strlen(new_s.s);
    while (1) {
        char* found = strstr(pos, old.s);
        if (!found) {
            size_t rlen = strlen(pos);
            while (total + rlen + 1 > cap) { cap *= 2; result = realloc(result, cap); }
            memcpy(result + total, pos, rlen);
            total += rlen;
            result[total] = 0;
            break;
        }
        size_t seg = (size_t)(found - pos);
        while (total + seg + newlen + 1 > cap) { cap *= 2; result = realloc(result, cap); }
        memcpy(result + total, pos, seg);
        total += seg;
        memcpy(result + total, new_s.s, newlen);
        total += newlen;
        result[total] = 0;
        pos = found + oldlen;
    }
    return hexa_str_own(result);
}

HexaVal hexa_str_to_upper(HexaVal s) {
    if (s.tag != TAG_STR) return s;
    char* r = strdup(s.s);
    for (int i = 0; r[i]; i++) if (r[i] >= 'a' && r[i] <= 'z') r[i] -= 32;
    return hexa_str_own(r);
}

HexaVal hexa_str_to_lower(HexaVal s) {
    if (s.tag != TAG_STR) return s;
    char* r = strdup(s.s);
    for (int i = 0; r[i]; i++) if (r[i] >= 'A' && r[i] <= 'Z') r[i] += 32;
    return hexa_str_own(r);
}

HexaVal hexa_str_join(HexaVal arr, HexaVal sep) {
    if (arr.tag != TAG_ARRAY || arr.arr.len == 0) return hexa_str("");
    size_t total_size = 0;
    for (int i = 0; i < arr.arr.len; i++) {
        HexaVal s = hexa_to_string(arr.arr.items[i]);
        total_size += strlen(s.s);
    }
    size_t seplen = strlen(sep.s);
    total_size += (arr.arr.len - 1) * seplen;
    char* result = malloc(total_size + 1);
    size_t total = 0;
    for (int i = 0; i < arr.arr.len; i++) {
        if (i > 0) {
            memcpy(result + total, sep.s, seplen);
            total += seplen;
        }
        HexaVal s = hexa_to_string(arr.arr.items[i]);
        size_t slen = strlen(s.s);
        memcpy(result + total, s.s, slen);
        total += slen;
    }
    result[total] = 0;
    return hexa_str_own(result);
}
static int utf8_cpcount(const char* s) {
    int n = 0;
    for (int i = 0; s[i]; i++) if ((s[i] & 0xC0) != 0x80) n++;
    return n;
}
HexaVal hexa_pad_left(HexaVal s, HexaVal width) {
    HexaVal str = hexa_to_string(s);
    int w = width.i;
    int cplen = utf8_cpcount(str.s);
    int bytelen = strlen(str.s);
    if (cplen >= w) return str;
    int pad = w - cplen;
    char* result = malloc(bytelen + pad + 1);
    memset(result, ' ', pad);
    strcpy(result + pad, str.s);
    return hexa_str_own(result);
}


// Bootstrap shim: hexa-level `join(arr, sep)` free-fn idiom in SSOT modules
// emits `hexa_call2(join, arr, sep)` via TAG_FN lookup. Once hexa_v2 is rebuilt
// from codegen_c2.hexa's join-builtin dispatch, this becomes unused.
static HexaVal join = {.tag = TAG_FN, .fn = {.fn_ptr = (void*)hexa_str_join, .arity = 2}};

HexaVal hexa_pad_right(HexaVal s, HexaVal width) {
    HexaVal str = hexa_to_string(s);
    int w = width.i;
    int cplen = utf8_cpcount(str.s);
    int bytelen = strlen(str.s);
    if (cplen >= w) return str;
    int pad = w - cplen;
    char* result = malloc(bytelen + pad + 1);
    strcpy(result, str.s);
    memset(result + bytelen, ' ', pad);
    result[bytelen + pad] = 0;
    return hexa_str_own(result);
}

// B-19: Polymorphic arithmetic — T39 routes through __hx_to_double.
HexaVal hexa_sub(HexaVal a, HexaVal b) {
    if (a.tag == TAG_INT && b.tag == TAG_INT) return hexa_int(a.i - b.i);
    return hexa_float(__hx_to_double(a) - __hx_to_double(b));
}
HexaVal hexa_mul(HexaVal a, HexaVal b) {
    if (a.tag == TAG_INT && b.tag == TAG_INT) return hexa_int(a.i * b.i);
    return hexa_float(__hx_to_double(a) * __hx_to_double(b));
}
HexaVal hexa_div(HexaVal a, HexaVal b) {
    if (a.tag == TAG_INT && b.tag == TAG_INT) {
        if (b.i == 0) return hexa_int(0);
        return hexa_int(a.i / b.i);
    }
    double fb = __hx_to_double(b);
    return hexa_float(__hx_to_double(a) / fb);
}
HexaVal hexa_mod(HexaVal a, HexaVal b) {
    if (a.tag == TAG_INT && b.tag == TAG_INT) return hexa_int(b.i ? a.i % b.i : 0);
    return hexa_int(0);
}
HexaVal hexa_str_repeat(HexaVal s, HexaVal n) {
    if (s.tag != TAG_STR) return s;
    int count = n.i;
    if (count <= 0) return hexa_str("");
    size_t slen = strlen(s.s);
    char* result = malloc(slen * (size_t)count + 1);
    size_t total = 0;
    for (int i = 0; i < count; i++) {
        memcpy(result + total, s.s, slen);
        total += slen;
    }
    result[total] = 0;
    return hexa_str_own(result);
}

int hexa_array_contains(HexaVal arr, HexaVal item) {
    if (arr.tag != TAG_ARRAY) return 0;
    for (int i = 0; i < arr.arr.len; i++) {
        if (hexa_truthy(hexa_eq(arr.arr.items[i], item))) return 1;
    }
    return 0;
}

HexaVal hexa_format_float(HexaVal f, HexaVal prec) {
    double v = __hx_to_double(f);
    int p = prec.i;
    char buf[64];
    snprintf(buf, 64, "%.*f", p, v);
    return hexa_str(buf);
}

HexaVal hexa_format_float_sci(HexaVal f, HexaVal prec) {
    double v = __hx_to_double(f);
    int p = prec.i;
    char buf[64];
    snprintf(buf, 64, "%.*e", p, v);
    return hexa_str(buf);
}

// ── Extern FFI: dlopen / dlsym / dispatch ───────────────

// Resolve a library path for dlopen.
// If lib_name is NULL or empty, use RTLD_DEFAULT (search default symbols).
static void* hexa_ffi_dlopen(const char* lib_name) {
    if (!lib_name || lib_name[0] == '\0') {
        return dlopen(NULL, RTLD_LAZY);
    }
#ifdef __APPLE__
    // Try framework path first
    char framework[512];
    snprintf(framework, sizeof(framework),
        "/System/Library/Frameworks/%s.framework/%s", lib_name, lib_name);
    void* h = dlopen(framework, RTLD_LAZY);
    if (h) return h;
    // Try dylib
    char dylib[512];
    snprintf(dylib, sizeof(dylib), "/usr/lib/lib%s.dylib", lib_name);
    h = dlopen(dylib, RTLD_LAZY);
    if (h) return h;
#endif
    // Try as-is (Linux .so or absolute path)
    char sopath[512];
    snprintf(sopath, sizeof(sopath), "lib%s.so", lib_name);
    void* h2 = dlopen(sopath, RTLD_LAZY);
    if (h2) return h2;
#ifndef __APPLE__
    // CUDA path + soname version fallbacks (Linux)
    {
        char path[512];
        const char* cuda_dirs[] = {
            "/usr/local/cuda/lib64/lib%s.so",
            "/usr/local/cuda/lib64/lib%s.so.12",
            "/usr/local/cuda/lib64/lib%s.so.11",
            NULL
        };
        for (int j = 0; cuda_dirs[j]; j++) {
            snprintf(path, sizeof(path), cuda_dirs[j], lib_name);
            void* hc = dlopen(path, RTLD_LAZY);
            if (hc) return hc;
        }
        const char* sonames[] = {"lib%s.so.12", "lib%s.so.11", NULL};
        for (int j = 0; sonames[j]; j++) {
            snprintf(path, sizeof(path), sonames[j], lib_name);
            void* hc = dlopen(path, RTLD_LAZY);
            if (hc) return hc;
        }
    }
#endif
    // Final attempt: bare name
    return dlopen(lib_name, RTLD_LAZY);
}

// Resolve a symbol from an already-opened library handle.
static void* hexa_ffi_dlsym(void* handle, const char* symbol) {
    void* sym = dlsym(handle, symbol);
    if (!sym) {
        fprintf(stderr, "[hexa-ffi] dlsym failed for '%s': %s\n", symbol, dlerror());
    }
    return sym;
}

// Marshal a HexaVal to a raw i64 for C ABI passing.
static int64_t hexa_ffi_marshal_arg(HexaVal v) {
    switch (v.tag) {
        case TAG_INT:   return v.i;
        case TAG_FLOAT: { union { double d; int64_t i; } u; u.d = v.f; return u.i; }
        case TAG_BOOL:  return (int64_t)v.b;
        case TAG_STR:   return (int64_t)(uintptr_t)v.s;
        case TAG_VOID:  return 0;
        default:        return 0;
    }
}

// Raw extern call dispatch — supports 0 to 12 arguments.
// Extended 2026-04-12 from 10 to 12 to support cuLaunchKernel (11 args).
// Uses transmute (cast) to call through a function pointer with the right arity.
static int64_t hexa_call_extern_raw(void* fn_ptr, int64_t* args, int nargs) {
    typedef int64_t (*Fn0)(void);
    typedef int64_t (*Fn1)(int64_t);
    typedef int64_t (*Fn2)(int64_t,int64_t);
    typedef int64_t (*Fn3)(int64_t,int64_t,int64_t);
    typedef int64_t (*Fn4)(int64_t,int64_t,int64_t,int64_t);
    typedef int64_t (*Fn5)(int64_t,int64_t,int64_t,int64_t,int64_t);
    typedef int64_t (*Fn6)(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t);
    typedef int64_t (*Fn7)(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t);
    typedef int64_t (*Fn8)(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t);
    typedef int64_t (*Fn9)(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t);
    typedef int64_t (*Fn10)(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t);
    typedef int64_t (*Fn11)(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t);
    typedef int64_t (*Fn12)(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t);

    switch (nargs) {
        case 0:  return ((Fn0)fn_ptr)();
        case 1:  return ((Fn1)fn_ptr)(args[0]);
        case 2:  return ((Fn2)fn_ptr)(args[0],args[1]);
        case 3:  return ((Fn3)fn_ptr)(args[0],args[1],args[2]);
        case 4:  return ((Fn4)fn_ptr)(args[0],args[1],args[2],args[3]);
        case 5:  return ((Fn5)fn_ptr)(args[0],args[1],args[2],args[3],args[4]);
        case 6:  return ((Fn6)fn_ptr)(args[0],args[1],args[2],args[3],args[4],args[5]);
        case 7:  return ((Fn7)fn_ptr)(args[0],args[1],args[2],args[3],args[4],args[5],args[6]);
        case 8:  return ((Fn8)fn_ptr)(args[0],args[1],args[2],args[3],args[4],args[5],args[6],args[7]);
        case 9:  return ((Fn9)fn_ptr)(args[0],args[1],args[2],args[3],args[4],args[5],args[6],args[7],args[8]);
        case 10: return ((Fn10)fn_ptr)(args[0],args[1],args[2],args[3],args[4],args[5],args[6],args[7],args[8],args[9]);
        case 11: return ((Fn11)fn_ptr)(args[0],args[1],args[2],args[3],args[4],args[5],args[6],args[7],args[8],args[9],args[10]);
        case 12: return ((Fn12)fn_ptr)(args[0],args[1],args[2],args[3],args[4],args[5],args[6],args[7],args[8],args[9],args[10],args[11]);
        default:
            fprintf(stderr, "[hexa-ffi] extern call with %d args not supported (max 12)\n", nargs);
            return 0;
    }
}

// High-level extern call: resolve, marshal, call, unmarshal.
// ret_kind: 0=void, 1=int, 2=float, 3=bool, 4=pointer/string
HexaVal hexa_extern_call(void* fn_ptr, HexaVal* hargs, int nargs, int ret_kind) {
    int64_t cargs[12];  // was 10; extended for cuLaunchKernel (11 args)
    for (int i = 0; i < nargs && i < 12; i++) {
        cargs[i] = hexa_ffi_marshal_arg(hargs[i]);
    }
    int64_t ret = hexa_call_extern_raw(fn_ptr, cargs, nargs);
    switch (ret_kind) {
        case 0:  return hexa_void();
        case 1:  return hexa_int(ret);
        case 2:  { union { int64_t i; double d; } u; u.i = ret; return hexa_float(u.d); }
        case 3:  return hexa_bool(ret != 0);
        case 4:  return hexa_int(ret); // pointer as int
        default: return hexa_int(ret);
    }
}

// ── G3: Typed extern call with float support ─────────────
// float_mask is a bitmask: bit i set means arg i is a double (SIMD register).
// This generates correct ARM64 calling convention for mixed int/float args.
// Supports up to 8 args (covers all common FFI patterns including NSRect).
// The C compiler sees typed args and emits correct register moves.
HexaVal hexa_extern_call_typed(void* fn_ptr, HexaVal* hargs, int nargs, int ret_kind, int float_mask) {
    // Extract values: doubles from .f, integers from .i
    double  fv[8]; // float values
    int64_t iv[8]; // int values
    for (int i = 0; i < nargs && i < 8; i++) {
        if (float_mask & (1 << i)) {
            fv[i] = (hargs[i].tag == TAG_FLOAT) ? hargs[i].f : (double)hargs[i].i;
        } else {
            iv[i] = hexa_ffi_marshal_arg(hargs[i]);
        }
    }
    // Dispatch by nargs and float_mask pattern
    // Common patterns: all-int (mask=0), trailing floats, all-float
    // For arbitrary patterns, we use a switch on nargs with typed casts.
    // The C compiler handles register allocation from the typed call.

    // Helper macros for arg extraction
    #define A(i) ((float_mask & (1<<(i))) ? 0 : iv[i])
    #define F(i) ((float_mask & (1<<(i))) ? fv[i] : 0.0)
    #define IS_F(i) (float_mask & (1<<(i)))

    int64_t reti = 0;
    double  retf = 0.0;
    int ret_is_float = (ret_kind == 2);

    // For each arity, generate all-int call if mask==0, else use typed dispatch
    switch (nargs) {
        case 0: {
            if (ret_is_float) { retf = ((double(*)(void))fn_ptr)(); }
            else { reti = ((int64_t(*)(void))fn_ptr)(); }
            break;
        }
        case 1: {
            if (IS_F(0)) {
                if (ret_is_float) retf = ((double(*)(double))fn_ptr)(fv[0]);
                else reti = ((int64_t(*)(double))fn_ptr)(fv[0]);
            } else {
                if (ret_is_float) retf = ((double(*)(int64_t))fn_ptr)(iv[0]);
                else reti = ((int64_t(*)(int64_t))fn_ptr)(iv[0]);
            }
            break;
        }
        case 2: {
            // 4 combinations for 2 args
            int p = (IS_F(0)?2:0) | (IS_F(1)?1:0);
            switch (p) {
                case 0: // ii
                    if (ret_is_float) retf = ((double(*)(int64_t,int64_t))fn_ptr)(iv[0],iv[1]);
                    else reti = ((int64_t(*)(int64_t,int64_t))fn_ptr)(iv[0],iv[1]);
                    break;
                case 1: // if
                    if (ret_is_float) retf = ((double(*)(int64_t,double))fn_ptr)(iv[0],fv[1]);
                    else reti = ((int64_t(*)(int64_t,double))fn_ptr)(iv[0],fv[1]);
                    break;
                case 2: // fi
                    if (ret_is_float) retf = ((double(*)(double,int64_t))fn_ptr)(fv[0],iv[1]);
                    else reti = ((int64_t(*)(double,int64_t))fn_ptr)(fv[0],iv[1]);
                    break;
                case 3: // ff
                    if (ret_is_float) retf = ((double(*)(double,double))fn_ptr)(fv[0],fv[1]);
                    else reti = ((int64_t(*)(double,double))fn_ptr)(fv[0],fv[1]);
                    break;
            }
            break;
        }
        default: {
            // For 3+ args: fall back to the codegen approach (typed wrappers).
            // This runtime path handles the most common 0-2 arg float cases.
            // For higher arities, codegen_c2 generates typed C wrapper functions.
            fprintf(stderr, "[hexa-ffi] typed call with %d args: use typed extern fn decl in .hexa\n", nargs);
            reti = hexa_call_extern_raw(fn_ptr, iv, nargs);
            break;
        }
    }
    #undef A
    #undef F
    #undef IS_F

    switch (ret_kind) {
        case 0:  return hexa_void();
        case 1:  return hexa_int(reti);
        case 2:  return hexa_float(retf);
        case 3:  return hexa_bool(reti != 0);
        case 4:  return hexa_int(reti);
        default: return hexa_int(reti);
    }
}

// Convenience: cstring <-> HexaVal
HexaVal hexa_cstring(HexaVal s) {
    if (s.tag != TAG_STR) return hexa_int(0);
    return hexa_int((int64_t)(uintptr_t)s.s);
}

HexaVal hexa_from_cstring(HexaVal ptr) {
    int64_t p = (ptr.tag == TAG_INT) ? ptr.i : 0;
    if (p == 0) return hexa_str("");
    return hexa_str((const char*)(uintptr_t)p);
}

HexaVal hexa_ptr_null() { return hexa_int(0); }

HexaVal hexa_ptr_addr(HexaVal v) {
    return hexa_int(v.i);
}

// ── G5: Pointer arithmetic builtins ─────────────────────

HexaVal hexa_ptr_alloc(HexaVal size) {
    int64_t n = size.tag == TAG_INT ? size.i : 0;
    if (n <= 0) return hexa_int(0);
    void* p = calloc(1, (size_t)n);
    return hexa_int((int64_t)(uintptr_t)p);
}

HexaVal hexa_ptr_free(HexaVal ptr, HexaVal size) {
    int64_t p = (ptr.tag == TAG_INT) ? ptr.i : 0;
    if (p != 0) free((void*)(uintptr_t)p);
    return hexa_void();
}

HexaVal hexa_ptr_write(HexaVal ptr, HexaVal offset, HexaVal val) {
    int64_t p = (ptr.tag == TAG_INT) ? ptr.i : 0;
    int64_t off = (offset.tag == TAG_INT) ? offset.i : 0;
    if (p == 0) return hexa_void();
    uint8_t* base = (uint8_t*)(uintptr_t)p + off;
    if (val.tag == TAG_FLOAT) {
        double d = val.f;
        memcpy(base, &d, sizeof(double));
    } else {
        int64_t v = val.i;
        memcpy(base, &v, sizeof(int64_t));
    }
    return hexa_void();
}

/* @hot_kernel f32/f64/i32 ptr read/write — extracted to tensor_kernels.c
 * (included at end of this file). hexa_ptr_read (untyped 64-bit) kept here
 * as general-purpose. */

HexaVal hexa_ptr_read(HexaVal ptr, HexaVal offset) {
    int64_t p = (ptr.tag == TAG_INT) ? ptr.i : 0;
    int64_t off = (offset.tag == TAG_INT) ? offset.i : 0;
    if (p == 0) return hexa_int(0);
    int64_t v;
    memcpy(&v, (uint8_t*)(uintptr_t)p + off, sizeof(int64_t));
    return hexa_int(v);
}

HexaVal hexa_ptr_offset(HexaVal ptr, HexaVal offset) {
    int64_t p = (ptr.tag == TAG_INT) ? ptr.i : 0;
    int64_t off = (offset.tag == TAG_INT) ? offset.i : 0;
    return hexa_int(p + off);
}

HexaVal hexa_deref(HexaVal ptr) {
    int64_t p = (ptr.tag == TAG_INT) ? ptr.i : 0;
    if (p == 0) return hexa_int(0);
    int64_t v;
    memcpy(&v, (void*)(uintptr_t)p, sizeof(int64_t));
    return hexa_int(v);
}

// ═══════════════════════════════════════════════════════════
//  G2: Struct Value Passing — struct packing builtins
//  Allows constructing C structs in heap memory for FFI.
//  struct_pack(v0, v1, ...) — N*8 bytes of f64 values
//  struct_pack_f32(v0, ...) — N*4 bytes of f32 values
//  struct_unpack(ptr, idx) — read Nth f64 from packed struct
//  struct_unpack_f32(ptr, idx) — read Nth f32
//  struct_rect/point/size — Cocoa geometry helpers
// ═══════════════════════════════════════════════════════════

// Pack N f64 values into a newly allocated buffer. Returns pointer as int.
HexaVal hexa_struct_pack(HexaVal* args, int nargs) {
    if (nargs <= 0) return hexa_int(0);
    size_t total = (size_t)nargs * sizeof(double);
    double* buf = (double*)calloc(1, total);
    for (int i = 0; i < nargs; i++) {
        buf[i] = (args[i].tag == TAG_FLOAT) ? args[i].f : (double)args[i].i;
    }
    return hexa_int((int64_t)(uintptr_t)buf);
}

/* @hot_kernel hexa_struct_pack_f32 / hexa_struct_unpack_f32 extracted to
 * tensor_kernels.c (see include at end of this file). */

// Read the Nth f64 from a struct pointer.
HexaVal hexa_struct_unpack(HexaVal ptr, HexaVal index) {
    int64_t p = (ptr.tag == TAG_INT) ? ptr.i : 0;
    int64_t idx = (index.tag == TAG_INT) ? index.i : 0;
    if (p == 0) return hexa_float(0.0);
    double* buf = (double*)(uintptr_t)p;
    return hexa_float(buf[idx]);
}

// Convenience: pack an NSRect (4x f64 = 32 bytes).
HexaVal hexa_struct_rect(HexaVal x, HexaVal y, HexaVal w, HexaVal h) {
    double* buf = (double*)calloc(1, 4 * sizeof(double));
    buf[0] = (x.tag == TAG_FLOAT) ? x.f : (double)x.i;
    buf[1] = (y.tag == TAG_FLOAT) ? y.f : (double)y.i;
    buf[2] = (w.tag == TAG_FLOAT) ? w.f : (double)w.i;
    buf[3] = (h.tag == TAG_FLOAT) ? h.f : (double)h.i;
    return hexa_int((int64_t)(uintptr_t)buf);
}

// Convenience: pack an NSPoint (2x f64 = 16 bytes).
HexaVal hexa_struct_point(HexaVal x, HexaVal y) {
    double* buf = (double*)calloc(1, 2 * sizeof(double));
    buf[0] = (x.tag == TAG_FLOAT) ? x.f : (double)x.i;
    buf[1] = (y.tag == TAG_FLOAT) ? y.f : (double)y.i;
    return hexa_int((int64_t)(uintptr_t)buf);
}

// Convenience: pack an NSSize (2x f64 = 16 bytes).
HexaVal hexa_struct_size_pack(HexaVal w, HexaVal h) {
    double* buf = (double*)calloc(1, 2 * sizeof(double));
    buf[0] = (w.tag == TAG_FLOAT) ? w.f : (double)w.i;
    buf[1] = (h.tag == TAG_FLOAT) ? h.f : (double)h.i;
    return hexa_int((int64_t)(uintptr_t)buf);
}

// Free a struct pointer (allocated by struct_pack/struct_rect/etc).
HexaVal hexa_struct_free(HexaVal ptr) {
    int64_t p = (ptr.tag == TAG_INT) ? ptr.i : 0;
    if (p != 0) free((void*)(uintptr_t)p);
    return hexa_void();
}

// ═══════════════════════════════════════════════════════════
//  G4: Callback Trampoline Pool
//  Provides C function pointers that dispatch back into hexa.
//  16 pre-allocated slots — sufficient for Cocoa delegates,
//  menu actions, timers, qsort comparators, etc.
// ═══════════════════════════════════════════════════════════

#define HEXA_TRAMPOLINE_POOL_SIZE 16

// Callback entry: stores a HexaVal function reference (TAG_FN)
// and metadata for the dispatch.
typedef struct {
    int in_use;
    HexaVal hexa_fn;        // The hexa function value (TAG_FN)
    void* fn_ptr;           // The C trampoline pointer for this slot
    int expected_argc;      // How many C args the trampoline receives
} HexaCallbackSlot;

static HexaCallbackSlot __hexa_cb_slots[HEXA_TRAMPOLINE_POOL_SIZE];

// User-supplied dispatch hook: the interpreter or compiled code sets this.
// Signature: dispatch(slot_id, argc, args[]) -> HexaVal
// For compiled code, this is wired at link time.
// For interpreter, the interpreter sets this to its own dispatcher.
typedef HexaVal (*hexa_cb_dispatch_fn)(int slot_id, int argc, int64_t* args);
static hexa_cb_dispatch_fn __hexa_cb_dispatcher = NULL;

void hexa_set_callback_dispatcher(hexa_cb_dispatch_fn fn) {
    __hexa_cb_dispatcher = fn;
}

// Internal dispatch: called by every trampoline.
// Converts raw C int64 args back to HexaVal and calls the registered function.
static int64_t hexa_trampoline_dispatch(int slot_id, int argc, int64_t* args) {
    if (slot_id < 0 || slot_id >= HEXA_TRAMPOLINE_POOL_SIZE) return 0;
    if (!__hexa_cb_slots[slot_id].in_use) return 0;

    // If a custom dispatcher is set (e.g. interpreter), use it
    if (__hexa_cb_dispatcher) {
        HexaVal result = __hexa_cb_dispatcher(slot_id, argc, args);
        if (result.tag == TAG_INT) return result.i;
        if (result.tag == TAG_FLOAT) { union { double d; int64_t i; } u; u.d = result.f; return u.i; }
        return 0;
    }

    // For compiled code: call the fn_ptr stored in the slot directly.
    // Compiled hexa functions take HexaVal args and return HexaVal.
    // We wrap each raw int64 arg as hexa_int() before calling.
    HexaCallbackSlot* slot = &__hexa_cb_slots[slot_id];
    if (slot->hexa_fn.tag == TAG_FN && slot->hexa_fn.fn.fn_ptr) {
        typedef HexaVal (*HFn0)(void);
        typedef HexaVal (*HFn1)(HexaVal);
        typedef HexaVal (*HFn2)(HexaVal, HexaVal);
        typedef HexaVal (*HFn3)(HexaVal, HexaVal, HexaVal);
        typedef HexaVal (*HFn4)(HexaVal, HexaVal, HexaVal, HexaVal);
        void* fp = slot->hexa_fn.fn.fn_ptr;
        HexaVal result;
        switch (argc) {
            case 0: result = ((HFn0)fp)(); break;
            case 1: result = ((HFn1)fp)(hexa_int(args[0])); break;
            case 2: result = ((HFn2)fp)(hexa_int(args[0]), hexa_int(args[1])); break;
            case 3: result = ((HFn3)fp)(hexa_int(args[0]), hexa_int(args[1]), hexa_int(args[2])); break;
            default: result = ((HFn4)fp)(hexa_int(args[0]), hexa_int(args[1]), hexa_int(args[2]), hexa_int(args[3])); break;
        }
        if (result.tag == TAG_INT) return result.i;
        if (result.tag == TAG_FLOAT) { union { double d; int64_t i; } u; u.d = result.f; return u.i; }
        return 0;
    }
    return 0;
}

// ── 16 static trampoline functions ──────────────────────
// Each takes up to 4 int64_t args (covers qsort comparator, ObjC IMP,
// NSTimer callback, etc.). Extra args beyond 4 are passed as 0.
// For Cocoa IMP: (id self, SEL _cmd, ...) = 2-3 pointer-sized args.

#define TRAMP_DEF(N) \
static int64_t _hexa_tramp_##N(int64_t a0, int64_t a1, int64_t a2, int64_t a3) { \
    int64_t args[4] = {a0, a1, a2, a3}; \
    return hexa_trampoline_dispatch(N, 4, args); \
}

TRAMP_DEF(0)  TRAMP_DEF(1)  TRAMP_DEF(2)  TRAMP_DEF(3)
TRAMP_DEF(4)  TRAMP_DEF(5)  TRAMP_DEF(6)  TRAMP_DEF(7)
TRAMP_DEF(8)  TRAMP_DEF(9)  TRAMP_DEF(10) TRAMP_DEF(11)
TRAMP_DEF(12) TRAMP_DEF(13) TRAMP_DEF(14) TRAMP_DEF(15)

typedef int64_t (*tramp_fn_t)(int64_t, int64_t, int64_t, int64_t);

static tramp_fn_t __hexa_tramp_table[HEXA_TRAMPOLINE_POOL_SIZE] = {
    _hexa_tramp_0,  _hexa_tramp_1,  _hexa_tramp_2,  _hexa_tramp_3,
    _hexa_tramp_4,  _hexa_tramp_5,  _hexa_tramp_6,  _hexa_tramp_7,
    _hexa_tramp_8,  _hexa_tramp_9,  _hexa_tramp_10, _hexa_tramp_11,
    _hexa_tramp_12, _hexa_tramp_13, _hexa_tramp_14, _hexa_tramp_15
};

// Initialize trampoline pool (call once at startup)
static void hexa_trampoline_init(void) {
    for (int i = 0; i < HEXA_TRAMPOLINE_POOL_SIZE; i++) {
        __hexa_cb_slots[i].in_use = 0;
        __hexa_cb_slots[i].fn_ptr = (void*)__hexa_tramp_table[i];
        __hexa_cb_slots[i].hexa_fn = hexa_void();
        __hexa_cb_slots[i].expected_argc = 0;
    }
}

// ── Public API ──────────────────────────────────────────

// callback_create(hexa_fn_val) -> int (C function pointer as integer)
// Allocates a trampoline slot and returns the C function pointer.
HexaVal hexa_callback_create(HexaVal fn_val) {
    // Lazy init
    static int inited = 0;
    if (!inited) { hexa_trampoline_init(); inited = 1; }

    for (int i = 0; i < HEXA_TRAMPOLINE_POOL_SIZE; i++) {
        if (!__hexa_cb_slots[i].in_use) {
            __hexa_cb_slots[i].in_use = 1;
            __hexa_cb_slots[i].hexa_fn = fn_val;
            return hexa_int((int64_t)(uintptr_t)__hexa_cb_slots[i].fn_ptr);
        }
    }
    fprintf(stderr, "[hexa-callback] trampoline pool exhausted (%d slots)\n",
            HEXA_TRAMPOLINE_POOL_SIZE);
    return hexa_int(0);
}

// callback_free(ptr) -> void
// Frees the trampoline slot associated with the given C function pointer.
HexaVal hexa_callback_free(HexaVal ptr) {
    int64_t p = (ptr.tag == TAG_INT) ? ptr.i : 0;
    for (int i = 0; i < HEXA_TRAMPOLINE_POOL_SIZE; i++) {
        if ((int64_t)(uintptr_t)__hexa_cb_slots[i].fn_ptr == p) {
            __hexa_cb_slots[i].in_use = 0;
            __hexa_cb_slots[i].hexa_fn = hexa_void();
            return hexa_void();
        }
    }
    return hexa_void();
}

// callback_slot_id(ptr) -> int
// Returns the slot index for a given trampoline pointer (-1 if not found).
HexaVal hexa_callback_slot_id(HexaVal ptr) {
    int64_t p = (ptr.tag == TAG_INT) ? ptr.i : 0;
    for (int i = 0; i < HEXA_TRAMPOLINE_POOL_SIZE; i++) {
        if ((int64_t)(uintptr_t)__hexa_cb_slots[i].fn_ptr == p) {
            return hexa_int(i);
        }
    }
    return hexa_int(-1);
}

// callback_get_fn(slot_id) -> HexaVal
// Returns the hexa function registered at the given slot.
HexaVal hexa_callback_get_fn(int slot_id) {
    if (slot_id < 0 || slot_id >= HEXA_TRAMPOLINE_POOL_SIZE) return hexa_void();
    if (!__hexa_cb_slots[slot_id].in_use) return hexa_void();
    return __hexa_cb_slots[slot_id].hexa_fn;
}

/* @hot_kernel B4 tensor stubs extracted to tensor_kernels.c (see include
 * at end of this file). clock/random stay here (OS utility, not hot). */

HexaVal hexa_clock(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return hexa_float((double)ts.tv_sec + (double)ts.tv_nsec/1e9);
}

HexaVal hexa_random(void) {
    return hexa_float(rand() / (double)RAND_MAX);
}

HexaVal hexa_char_code(HexaVal s, HexaVal idx);
// Bootstrap shim (same rationale as `join` above): SSOT modules use
// `char_code(s, i)` free-fn idiom which old hexa_v2 emits as
// `hexa_call2(char_code, ...)`. Shim binds the bare identifier to TAG_FN.
static HexaVal char_code = {.tag = TAG_FN, .fn = {.fn_ptr = (void*)hexa_char_code, .arity = 2}};
HexaVal hexa_char_code(HexaVal s, HexaVal idx) {
    if (s.tag != TAG_STR) return hexa_int(0);
    int i = idx.i;
    if (i < 0 || i >= (int)strlen(s.s)) return hexa_int(0);
    return hexa_int((unsigned char)s.s[i]);
}

// `chr(n)` — Python/Ruby-style inverse of char_code: int byte → 1-char str.
// Used by void's sys_pty accumulator (chr(b) reassembles bytes from
// line_buf int values). Binds the free-fn idiom the way char_code does.
HexaVal hexa_from_char_code(HexaVal n);
static HexaVal chr = {.tag = TAG_FN, .fn = {.fn_ptr = (void*)hexa_from_char_code, .arity = 1}};

// `bit_or(x, y)` — shim kept because `|` as binary op conflicts with lambda
// param delimiters `|x| x+1`. `&` and `^` are supported by parser directly.
HexaVal _hx_bit_or(HexaVal a, HexaVal b) {
    int64_t x = (a.tag == TAG_INT) ? a.i : (int64_t)a.f;
    int64_t y = (b.tag == TAG_INT) ? b.i : (int64_t)b.f;
    return hexa_int(x | y);
}
static HexaVal bit_or = {.tag = TAG_FN, .fn = {.fn_ptr = (void*)_hx_bit_or, .arity = 2}};

// ── Added: method-dispatch helpers (bt 34) ────────────────────
HexaVal hexa_str_parse_int(HexaVal s) {
    if (s.tag != TAG_STR) return hexa_int(0);
    return hexa_int((int64_t)strtoll(s.s, NULL, 10));
}

HexaVal hexa_str_parse_float(HexaVal s) {
    if (s.tag != TAG_STR) return hexa_float(0.0);
    return hexa_float(strtod(s.s, NULL));
}

HexaVal hexa_str_trim_start(HexaVal s) {
    if (s.tag != TAG_STR) return s;
    char* p = s.s;
    while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
    return hexa_str_own(strdup(p));
}

HexaVal hexa_str_trim_end(HexaVal s) {
    if (s.tag != TAG_STR) return s;
    int len = strlen(s.s);
    while (len > 0 && (s.s[len-1] == ' ' || s.s[len-1] == '\t' || s.s[len-1] == '\n' || s.s[len-1] == '\r')) len--;
    return hexa_str_own(strndup(s.s, len));
}

// Byte-based slice: [start, end) clamped to length
HexaVal hexa_str_slice(HexaVal s, HexaVal start, HexaVal end) {
    if (s.tag != TAG_STR) return hexa_str("");
    int len = (int)strlen(s.s);
    int a = (int)start.i, b = (int)end.i;
    if (a < 0) a = 0;
    if (b > len) b = len;
    if (a > b) a = b;
    return hexa_str_own(strndup(s.s + a, b - a));
}

HexaVal hexa_array_slice(HexaVal arr, HexaVal start, HexaVal end) {
    if (arr.tag != TAG_ARRAY) return hexa_array_new();
    int n = arr.arr.len;
    int a = (int)start.i, b = (int)end.i;
    if (a < 0) a = 0;
    if (b > n) b = n;
    if (a > b) a = b;
    HexaVal out = hexa_array_new();
    for (int i = a; i < b; i++) out = hexa_array_push(out, arr.arr.items[i]);
    return out;
}

HexaVal hexa_array_map(HexaVal arr, HexaVal fn) {
    if (arr.tag != TAG_ARRAY) return hexa_array_new();
    HexaVal out = hexa_array_new();
    for (int i = 0; i < arr.arr.len; i++) {
        out = hexa_array_push(out, hexa_call1(fn, arr.arr.items[i]));
    }
    return out;
}

HexaVal hexa_array_filter(HexaVal arr, HexaVal fn) {
    if (arr.tag != TAG_ARRAY) return hexa_array_new();
    HexaVal out = hexa_array_new();
    for (int i = 0; i < arr.arr.len; i++) {
        HexaVal keep = hexa_call1(fn, arr.arr.items[i]);
        if (hexa_truthy(keep)) out = hexa_array_push(out, arr.arr.items[i]);
    }
    return out;
}

HexaVal hexa_array_fold(HexaVal arr, HexaVal init, HexaVal fn) {
    if (arr.tag != TAG_ARRAY) return init;
    HexaVal acc = init;
    for (int i = 0; i < arr.arr.len; i++) {
        acc = hexa_call2(fn, acc, arr.arr.items[i]);
    }
    return acc;
}

HexaVal hexa_array_index_of(HexaVal arr, HexaVal item) {
    if (arr.tag != TAG_ARRAY) return hexa_int(-1);
    for (int i = 0; i < arr.arr.len; i++) {
        if (hexa_truthy(hexa_eq(arr.arr.items[i], item))) return hexa_int(i);
    }
    return hexa_int(-1);
}

HexaVal hexa_str_bytes(HexaVal s) {
    if (s.tag != TAG_STR) return hexa_array_new();
    HexaVal out = hexa_array_new();
    for (const unsigned char* p = (const unsigned char*)s.s; *p; p++) {
        out = hexa_array_push(out, hexa_int((int64_t)*p));
    }
    return out;
}

// ── bt-71: libc / builtin family wrappers ────────────────────────────
// interpreter.hexa references bare idents like `exit(code)`, `tanh(x)`,
// `input()`, `is_error(v)`, `read_lines(p)`, `env_var(n)`, `hex(n)`, etc.
// Codegen used to emit `hexa_call1(exit, hexa_int(0))` which passes the
// libc function pointer (wrong type) to hexa_call1(HexaVal, HexaVal).
// We now wrap each in a HexaVal-returning stub so codegen can emit a
// direct call with correct types.
#include <unistd.h>
#include <time.h>

HexaVal hexa_exit(HexaVal code) {
    int c = (code.tag == TAG_INT) ? (int)code.i
          : (code.tag == TAG_FLOAT) ? (int)code.f
          : 0;
    fflush(stdout); fflush(stderr);
    exit(c);
    return hexa_void(); // unreachable
}

HexaVal hexa_sleep(HexaVal sec) {
    double s = (sec.tag == TAG_FLOAT) ? sec.f
             : (sec.tag == TAG_INT)   ? (double)sec.i
             : 0.0;
    if (s <= 0.0) return hexa_void();
    struct timespec ts;
    ts.tv_sec  = (time_t)s;
    ts.tv_nsec = (long)((s - (double)ts.tv_sec) * 1e9);
    nanosleep(&ts, NULL);
    return hexa_void();
}

// Math family — accept int or float, return float
static double _hexa_f(HexaVal v) {
    if (v.tag == TAG_FLOAT) return v.f;
    if (v.tag == TAG_INT)   return (double)v.i;
    if (v.tag == TAG_BOOL)  return v.b ? 1.0 : 0.0;
    return 0.0;
}

// Safe float→int64 cast. C cast of NaN/Inf/out-of-range double is UB
// (typically INT64_MIN on x86). Returns 0 for NaN/Inf, clamps to int64
// range otherwise. Used by to_int() builtin.
int64_t hexa_float_to_int(double f) {
    if (isnan(f) || isinf(f)) return 0;
    if (f >= 9.2233720368547758e+18) return (int64_t)0x7fffffffffffffffLL;
    if (f <= -9.2233720368547758e+18) return (int64_t)0x8000000000000000LL;
    return (int64_t)f;
}

HexaVal hexa_math_tanh(HexaVal x) { return hexa_float(tanh(_hexa_f(x))); }
HexaVal hexa_math_sin(HexaVal x)  { return hexa_float(sin(_hexa_f(x))); }
HexaVal hexa_math_cos(HexaVal x)  { return hexa_float(cos(_hexa_f(x))); }
HexaVal hexa_math_tan(HexaVal x)  { return hexa_float(tan(_hexa_f(x))); }
HexaVal hexa_math_asin(HexaVal x) { return hexa_float(asin(_hexa_f(x))); }
HexaVal hexa_math_acos(HexaVal x) { return hexa_float(acos(_hexa_f(x))); }
HexaVal hexa_math_atan(HexaVal x) { return hexa_float(atan(_hexa_f(x))); }
HexaVal hexa_math_atan2(HexaVal y, HexaVal x) { return hexa_float(atan2(_hexa_f(y), _hexa_f(x))); }
HexaVal hexa_math_log(HexaVal x)  { return hexa_float(log(_hexa_f(x))); }
HexaVal hexa_math_exp(HexaVal x)  { return hexa_float(exp(_hexa_f(x))); }

HexaVal hexa_input(HexaVal prompt) {
    if (prompt.tag == TAG_STR && prompt.s && prompt.s[0]) {
        fputs(prompt.s, stdout);
        fflush(stdout);
    }
    char* buf = NULL;
    size_t cap = 0;
    ssize_t n = getline(&buf, &cap, stdin);
    if (n < 0) {
        if (buf) free(buf);
        return hexa_str("");
    }
    // strip trailing \n
    if (n > 0 && buf[n-1] == '\n') buf[n-1] = 0;
    return hexa_str_own(buf);
}

HexaVal hexa_is_error(HexaVal v) {
    // No TAG_ERROR in runtime; interpreter uses ad-hoc Val(TAG_ERROR,...)
    // convention (TAG_ERROR name not defined in runtime tags). Treat as
    // "false" here unless TAG_STR and starts with "ERR:" sentinel.
    if (v.tag == TAG_STR && v.s && strncmp(v.s, "ERR:", 4) == 0) return hexa_bool(1);
    return hexa_bool(0);
}

HexaVal hexa_read_lines(HexaVal path) {
    HexaVal content = hexa_read_file(path);
    if (content.tag != TAG_STR) return hexa_array_new();
    HexaVal out = hexa_array_new();
    const char* p = content.s;
    const char* start = p;
    while (*p) {
        if (*p == '\n') {
            size_t len = (size_t)(p - start);
            char* line = (char*)malloc(len + 1);
            memcpy(line, start, len);
            line[len] = 0;
            out = hexa_array_push(out, hexa_str_own(line));
            start = p + 1;
        }
        p++;
    }
    if (p > start) {
        size_t len = (size_t)(p - start);
        char* line = (char*)malloc(len + 1);
        memcpy(line, start, len);
        line[len] = 0;
        out = hexa_array_push(out, hexa_str_own(line));
    }
    return out;
}

HexaVal hexa_from_char_code(HexaVal n) {
    int64_t code = (n.tag == TAG_INT) ? n.i : (int64_t)_hexa_f(n);
    if (code < 0) code = 0;
    if (code < 0x80) {
        char* s = (char*)malloc(2); s[0] = (char)code; s[1] = 0;
        return hexa_str_own(s);
    }
    // UTF-8 encode
    char buf[5] = {0};
    if (code < 0x800) {
        buf[0] = (char)(0xC0 | (code >> 6));
        buf[1] = (char)(0x80 | (code & 0x3F));
    } else if (code < 0x10000) {
        buf[0] = (char)(0xE0 | (code >> 12));
        buf[1] = (char)(0x80 | ((code >> 6) & 0x3F));
        buf[2] = (char)(0x80 | (code & 0x3F));
    } else {
        buf[0] = (char)(0xF0 | (code >> 18));
        buf[1] = (char)(0x80 | ((code >> 12) & 0x3F));
        buf[2] = (char)(0x80 | ((code >> 6) & 0x3F));
        buf[3] = (char)(0x80 | (code & 0x3F));
    }
    char* out = strdup(buf);
    return hexa_str_own(out);
}

HexaVal hexa_env_var(HexaVal name) {
    if (name.tag != TAG_STR || !name.s) return hexa_str("");
    // rt 32-L: side-channel for Val arena scope ops. Hexa-side env_push_scope /
    // env_pop_scope / call_user_fn invoke env("__HEXA_ARENA_*") to drive the C
    // arena without needing a transpiler-level builtin. Returns "0" / "1" so
    // existing callers that ignore the result are unaffected.
    if (name.s[0] == '_' && name.s[1] == '_' && name.s[2] == 'H' &&
        strncmp(name.s, "__HEXA_ARENA_", 13) == 0) {
        const char* op = name.s + 13;
        if (strcmp(op, "PUSH__") == 0) {
            hexa_val_arena_scope_push();
            return hexa_str("1");
        }
        if (strcmp(op, "POP__") == 0) {
            hexa_val_arena_scope_pop();
            return hexa_str("1");
        }
        if (strcmp(op, "HEAPIFY_RETURN__") == 0) {
            hexa_val_arena_heapify_return();
            return hexa_str("1");
        }
        if (strcmp(op, "ENABLED__") == 0) {
            return hexa_str(hexa_val_arena_on() ? "1" : "0");
        }
        if (strcmp(op, "STATS__") == 0) {
            char buf[64];
            snprintf(buf, sizeof(buf), "marks=%d", __hexa_val_mark_top);
            return hexa_str(buf);
        }
        // Unknown __HEXA_ARENA_* op — fall through to real getenv (returns "").
    }
    const char* v = getenv(name.s);
    return hexa_str(v ? v : "");
}

HexaVal hexa_delete_file(HexaVal path) {
    if (path.tag != TAG_STR || !path.s) return hexa_void();
    (void)unlink(path.s);
    return hexa_void();
}

HexaVal hexa_append_file(HexaVal path, HexaVal content) {
    if (path.tag != TAG_STR || !path.s) return hexa_void();
    const char* data = (content.tag == TAG_STR && content.s) ? content.s : "";
    FILE* f = fopen(path.s, "ab");
    if (!f) return hexa_void();
    fwrite(data, 1, strlen(data), f);
    fclose(f);
    return hexa_void();
}

HexaVal hexa_bin(HexaVal n) {
    uint64_t v = (n.tag == TAG_INT) ? (uint64_t)n.i : (uint64_t)_hexa_f(n);
    char buf[65]; int pos = 0;
    if (v == 0) { buf[pos++] = '0'; }
    while (v > 0 && pos < 64) { buf[pos++] = (char)('0' + (v & 1)); v >>= 1; }
    char* out = (char*)malloc(pos + 1);
    for (int i = 0; i < pos; i++) out[i] = buf[pos - 1 - i];
    out[pos] = 0;
    return hexa_str_own(out);
}

HexaVal hexa_hex(HexaVal n) {
    uint64_t v = (n.tag == TAG_INT) ? (uint64_t)n.i : (uint64_t)_hexa_f(n);
    char* out = (char*)malloc(20);
    snprintf(out, 20, "%llx", (unsigned long long)v);
    return hexa_str_own(out);
}

HexaVal hexa_timestamp(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return hexa_int((int64_t)ts.tv_sec);
}

// Base64 (RFC 4648)
static const char _b64_enc[] =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

HexaVal hexa_base64_encode(HexaVal s) {
    if (s.tag != TAG_STR || !s.s) return hexa_str("");
    const unsigned char* in = (const unsigned char*)s.s;
    size_t n = strlen(s.s);
    size_t olen = 4 * ((n + 2) / 3);
    char* out = (char*)malloc(olen + 1);
    size_t i = 0, j = 0;
    while (i + 3 <= n) {
        uint32_t t = (in[i] << 16) | (in[i+1] << 8) | in[i+2];
        out[j++] = _b64_enc[(t >> 18) & 0x3F];
        out[j++] = _b64_enc[(t >> 12) & 0x3F];
        out[j++] = _b64_enc[(t >> 6) & 0x3F];
        out[j++] = _b64_enc[t & 0x3F];
        i += 3;
    }
    if (i < n) {
        uint32_t t = in[i] << 16;
        int rem = (int)(n - i);
        if (rem == 2) t |= in[i+1] << 8;
        out[j++] = _b64_enc[(t >> 18) & 0x3F];
        out[j++] = _b64_enc[(t >> 12) & 0x3F];
        out[j++] = (rem == 2) ? _b64_enc[(t >> 6) & 0x3F] : '=';
        out[j++] = '=';
    }
    out[j] = 0;
    return hexa_str_own(out);
}

HexaVal hexa_base64_decode(HexaVal s) {
    if (s.tag != TAG_STR || !s.s) return hexa_str("");
    static int dec[256];
    static int dec_init = 0;
    if (!dec_init) {
        for (int i = 0; i < 256; i++) dec[i] = -1;
        for (int i = 0; i < 64; i++) dec[(unsigned char)_b64_enc[i]] = i;
        dec_init = 1;
    }
    const unsigned char* in = (const unsigned char*)s.s;
    size_t n = strlen(s.s);
    char* out = (char*)malloc(n + 1);
    size_t j = 0;
    int bits = 0, vbits = 0;
    for (size_t i = 0; i < n; i++) {
        if (in[i] == '=') break;
        int v = dec[in[i]];
        if (v < 0) continue;
        bits = (bits << 6) | v;
        vbits += 6;
        if (vbits >= 8) {
            vbits -= 8;
            out[j++] = (char)((bits >> vbits) & 0xFF);
        }
    }
    out[j] = 0;
    return hexa_str_own(out);
}

// ═══════════════════════════════════════════════════════════════════
//  NET I/O — minimal BSD socket FFI for hexa HTTP servers
//
//  Provides the 6 primitives hexa code needs:
//    hexa_net_listen(addr_port)  → listener fd (int)
//    hexa_net_accept(fd)         → client fd (int)
//    hexa_net_read(fd)           → raw bytes (string)
//    hexa_net_write(fd, data)    → bytes written (int)
//    hexa_net_close(fd)          → void
//    hexa_net_set_reuse(fd)      → void (SO_REUSEADDR, called automatically)
//
//  Root cause: stage0 hexa has no net_listen builtin.  Adding these C
//  functions to runtime.c lets any .hexa file compiled against this
//  runtime call net_listen / net_accept / net_read / net_write /
//  net_close directly — no stage0 change needed.
//
//  Security note: these are raw BSD sockets, no TLS.  Intended for
//  pod-internal (localhost / VPC) serving behind a reverse proxy.
// ═══════════════════════════════════════════════════════════════════
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>

// Portable case-insensitive strstr (strcasestr is a GNU extension,
// not guaranteed on all Linux libc builds without _GNU_SOURCE).
static char* _hexa_strcasestr(const char* haystack, const char* needle) {
    if (!needle[0]) return (char*)haystack;
    size_t nlen = strlen(needle);
    for (; *haystack; haystack++) {
        if (strncasecmp(haystack, needle, nlen) == 0)
            return (char*)haystack;
    }
    return NULL;
}

// hexa_net_listen("0.0.0.0:8090") → fd (int), or -1 on error.
// Parses "host:port" string, binds, listens (backlog 128).
// Automatically sets SO_REUSEADDR so quick restarts don't hit EADDRINUSE.
HexaVal hexa_net_listen(HexaVal addr_port) {
    if (addr_port.tag != TAG_STR || !addr_port.s) return hexa_int(-1);

    // Parse "host:port" — find last ':' to handle IPv4
    const char* s = addr_port.s;
    const char* colon = strrchr(s, ':');
    if (!colon || colon == s) return hexa_int(-1);

    // Extract host and port
    size_t host_len = (size_t)(colon - s);
    char host[256];
    if (host_len >= sizeof(host)) return hexa_int(-1);
    memcpy(host, s, host_len);
    host[host_len] = '\0';
    int port = atoi(colon + 1);
    if (port <= 0 || port > 65535) return hexa_int(-1);

    // Create socket
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) return hexa_int(-1);

    // SO_REUSEADDR — avoid EADDRINUSE on quick restart
    int opt = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    // Bind
    struct sockaddr_in sa;
    memset(&sa, 0, sizeof(sa));
    sa.sin_family = AF_INET;
    sa.sin_port = htons((uint16_t)port);
    if (strcmp(host, "0.0.0.0") == 0) {
        sa.sin_addr.s_addr = INADDR_ANY;
    } else {
        if (inet_pton(AF_INET, host, &sa.sin_addr) != 1) {
            close(fd);
            return hexa_int(-1);
        }
    }

    if (bind(fd, (struct sockaddr*)&sa, sizeof(sa)) < 0) {
        close(fd);
        return hexa_int(-1);
    }

    // Listen (backlog 128 — sufficient for single-threaded accept loop)
    if (listen(fd, 128) < 0) {
        close(fd);
        return hexa_int(-1);
    }

    return hexa_int(fd);
}

// hexa_net_accept(listener_fd) → client fd (int), or -1 on error.
// Blocking call — waits until a client connects.
HexaVal hexa_net_accept(HexaVal listener_fd) {
    if (listener_fd.tag != TAG_INT) return hexa_int(-1);
    int lfd = (int)listener_fd.i;

    struct sockaddr_in client_addr;
    socklen_t client_len = sizeof(client_addr);
    int cfd = accept(lfd, (struct sockaddr*)&client_addr, &client_len);
    if (cfd < 0) return hexa_int(-1);

    return hexa_int(cfd);
}

// hexa_net_read(fd) → string (full request).
// Reads up to 64KB from the socket. For HTTP/1.1 this covers typical
// requests. Returns "" on error/closed.
// NOTE: Does NOT handle chunked transfer or Content-Length continuation —
// adequate for single-request-per-connection serving pattern.
#define HEXA_NET_READ_BUF 65536

HexaVal hexa_net_read(HexaVal fd_val) {
    if (fd_val.tag != TAG_INT) return hexa_str("");
    int fd = (int)fd_val.i;

    char* buf = (char*)malloc(HEXA_NET_READ_BUF + 1);
    if (!buf) return hexa_str("");

    ssize_t total = 0;
    // Read until we get the full HTTP headers (double CRLF).
    // Then read Content-Length body if present.
    while (total < HEXA_NET_READ_BUF) {
        ssize_t n = read(fd, buf + total, HEXA_NET_READ_BUF - total);
        if (n <= 0) break;
        total += n;
        buf[total] = '\0';

        // Check if we have complete headers (CRLFCRLF)
        char* hdr_end = strstr(buf, "\r\n\r\n");
        if (hdr_end) {
            size_t hdr_len = (size_t)(hdr_end - buf) + 4;

            // Look for Content-Length header to know if there's a body
            // Case-insensitive search within the header portion
            long content_len = 0;
            char* cl = _hexa_strcasestr(buf, "content-length:");
            if (cl && cl < hdr_end) {
                content_len = strtol(cl + 15, NULL, 10);
            }

            // Calculate how much body we still need
            long body_have = total - (long)hdr_len;
            long body_need = content_len - body_have;

            // Read remaining body bytes if needed
            while (body_need > 0 && total < HEXA_NET_READ_BUF) {
                ssize_t n2 = read(fd, buf + total,
                    (size_t)body_need < (HEXA_NET_READ_BUF - total)
                        ? (size_t)body_need : (HEXA_NET_READ_BUF - total));
                if (n2 <= 0) break;
                total += n2;
                body_need -= n2;
            }
            break;
        }
    }

    buf[total] = '\0';
    return hexa_str_own(buf);
}

// hexa_net_write(fd, data_string) → bytes written (int).
// Writes the full string to the socket. Returns -1 on error.
HexaVal hexa_net_write(HexaVal fd_val, HexaVal data) {
    if (fd_val.tag != TAG_INT) return hexa_int(-1);
    if (data.tag != TAG_STR || !data.s) return hexa_int(0);
    int fd = (int)fd_val.i;
    size_t len = strlen(data.s);
    size_t sent = 0;

    // Loop to handle partial writes (EINTR, short writes)
    while (sent < len) {
        ssize_t n = write(fd, data.s + sent, len - sent);
        if (n < 0) {
            if (errno == EINTR) continue;
            return hexa_int(-1);
        }
        sent += (size_t)n;
    }

    return hexa_int((int64_t)sent);
}

// hexa_net_close(fd) → void.
// Closes a socket fd. Safe to call on already-closed fds.
HexaVal hexa_net_close(HexaVal fd_val) {
    if (fd_val.tag != TAG_INT) return hexa_void();
    close((int)fd_val.i);
    return hexa_void();
}

// ── bt 73: bare-ident HexaVal globals for transpiled builtin dispatch ──
// Self-host codegen (self/native/hexa_cc.c gen2_expr Call fallback, ~line 5642+)
// emits `hexa_call0(timestamp)`, `hexa_call1(base64_encode, s)`, … where the
// callee is a BARE C identifier. For the linker to resolve these, each name
// must exist as a `HexaVal` variable holding a TAG_FN that wraps the real
// implementation. bt 71 supplied the hexa_*-prefixed C functions; this block
// wires them to the bare names the transpiler expects.
//
// hexa_call0/hexa_call1 (defined above in this file) already branch on
// TAG_FN and cast fn_ptr to `HexaVal (*)(…)`, so HexaVal-returning wrappers
// with matching arity work directly.
//
// Wrapper for `timestamp` — hexa_timestamp is declared above without params;
// expose under the void→HexaVal signature hexa_call0 expects.
static HexaVal _bt73_timestamp_w(void) { return hexa_timestamp(); }
static HexaVal _bt73_base64_encode_w(HexaVal s) { return hexa_base64_encode(s); }
static HexaVal _bt73_base64_decode_w(HexaVal s) { return hexa_base64_decode(s); }

HexaVal timestamp     = {.tag=TAG_FN, .fn={.fn_ptr=(void*)_bt73_timestamp_w,     .arity=0}};
HexaVal base64_encode = {.tag=TAG_FN, .fn={.fn_ptr=(void*)_bt73_base64_encode_w, .arity=1}};
HexaVal base64_decode = {.tag=TAG_FN, .fn={.fn_ptr=(void*)_bt73_base64_decode_w, .arity=1}};

// bt 73 net_* bare-ident wrappers — hexa codegen emits net_listen(addr)
// which resolves to hexa_call1(net_listen, addr); these HexaVal globals
// let the linker find them.
static HexaVal _bt73_net_listen_w(HexaVal a) { return hexa_net_listen(a); }
static HexaVal _bt73_net_accept_w(HexaVal a) { return hexa_net_accept(a); }
static HexaVal _bt73_net_read_w(HexaVal a)   { return hexa_net_read(a); }
static HexaVal _bt73_net_write_w(HexaVal a, HexaVal b) { return hexa_net_write(a, b); }
static HexaVal _bt73_net_close_w(HexaVal a)  { return hexa_net_close(a); }

HexaVal net_listen = {.tag=TAG_FN, .fn={.fn_ptr=(void*)_bt73_net_listen_w, .arity=1}};
HexaVal net_accept = {.tag=TAG_FN, .fn={.fn_ptr=(void*)_bt73_net_accept_w, .arity=1}};
HexaVal net_read   = {.tag=TAG_FN, .fn={.fn_ptr=(void*)_bt73_net_read_w,   .arity=1}};
HexaVal net_write  = {.tag=TAG_FN, .fn={.fn_ptr=(void*)_bt73_net_write_w,  .arity=2}};
HexaVal net_close  = {.tag=TAG_FN, .fn={.fn_ptr=(void*)_bt73_net_close_w,  .arity=1}};

/* ═══════════════════════════════════════════════════════════════════
 * T3 HOT KERNEL INCLUDE — anima training inner-loop fast path.
 *
 * f32/f64/i32 ptr r/w + struct_pack_f32/unpack_f32 + tensor stubs are
 * extracted into native/tensor_kernels.c so anima maintainers can find
 * the performance-critical boundary without grep'ing through 3600 LOC.
 *
 * @hot_kernel markers inside the file describe each function's role.
 * Whitelist (external consumers): $NEXUS/shared/hexa/hot-path.jsonl.
 * Migration policy: docs/hexa-hot-path.md.
 *
 * NEVER migrate these to HEXA — per-element HexaVal wrap/dispatch would
 * multiply training time 10-100x. Any future HEXA reimplementation must
 * preserve raw C float* access patterns.
 * ═══════════════════════════════════════════════════════════════════ */
#include "native/tensor_kernels.c"

