# Hexa-Native ALM Serve — Plan & Blocker Analysis

**Date:** 2026-04-16
**Author:** smash agent (serving migration)
**Target:** Replace `serving/serve_alm_14b.py` (Python) with `.hexa`-only serve on ALM pod `itfl66q4z768kh`.
**Status:** **Scaffold ready, real socket loop blocked on hexa runtime gap.**

---

## TL;DR

| Layer | State | Blocker |
|---|---|---|
| **Dispatch logic** (JSON route → handler) | PASS 7/7 | none — `serve_alm_native.hexa` self-test passes |
| **voice_routes / hire_routes mount** | PASS | none — imports and routes resolved in scaffold |
| **HTTP parse** (`method path body` from stdin) | PASS | none — tested via direct stdin pipe |
| **Real socket bind/accept/read/write** | **FAIL** | `hexa_stage0` binary has **no `net_listen` builtin**. `self/std_net.hexa` wrapper calls `__builtin_net_*` but stage0 C runtime never got the impl ported (original was Rust `src/std_net.rs`, deleted during self-host absorption at hexa-lang@94ffd0f). **Original rt-32-j claim was incorrect — verified 2026-04-16 merge agent.** |
| **socat bridge (per-conn SYSTEM:)** | **FAIL** | `read_stdin()` uses line-by-line `input()` loop; deadlocks on HTTP/1.1 half-open socket that never reaches EOF |
| **Qwen 14B FFI forward** | **MOCK** | `libhxqwen14b.so` not built. `hxlmhead.so` exists on Mac only; Linux build missing |

**Result:** Cannot swap `serve_alm_14b.py` on ALM pod today. Two prerequisites must land in hexa-lang first.

---

## 1. Investigation Results

### 1.1 Existing files

| File | LOC | Runnable? | Notes |
|---|---|---|---|
| `serving/http_server.hexa` | 805 | **No** — parse error | Uses `MmapHandle` type + `effect Net { ... }` syntax that `hexa_stage0` doesn't parse (reserves `handle` keyword). All `TODO[pytorch]:` stubs. |
| `serving/voice_routes.hexa` | 756 | Yes | 10 voice profiles + TTS/E2E mock pipeline. Parse-clean; 5/5 tests PASS standalone. |
| `serving/serve.hexa` | 235 | Yes (prints only) | Scaffold with `TODO[pytorch]` stubs. No socket loop. |
| `serving/serve_alm_14b.py` | 456 | **Yes (LIVE)** | Python + `torch` + `transformers` + `peft` + `http.server`. Running on ALM pod, 62 req served. |
| `serving/clm_lore_serve.hexa` | 930 | Yes (tests) | Full CLM serve logic. No socket — returns structs. |
| `serving/serve_http.hexa` | 96 | No (socat recipe) | Shells out to `socat` + `eval_serve.hexa`. Meant as CLM serving bridge; requires `eval_serve.hexa` stdin handshake. |

### 1.2 Hexa runtime capabilities (2026-04-16 `hexa_stage0`)

- `println`, `print`, `read_stdin`, `input` — work
- `to_string`, `to_int`, `to_float`, `len`, `substring`, `index_of` — work
- **`net_listen`, `net_accept`, `net_read`, `net_write`, `net_close` — NOT PRESENT**. `Runtime error: undefined function: net_listen`
- `use "voice_routes"` — works (same-dir cross-file import)
- `@link("libname") extern fn ...` — Mac-only hardcoded absolute paths

### 1.3 `self/std_net.hexa` existence

- **Exists on main** (`/Users/ghost/Dev/hexa-lang/self/std_net.hexa`) — bytes identical to worktrees
- Delegates to `__builtin_net_listen` / `__builtin_net_accept` / etc.
- **Not compiled into live `hexa_stage0`**. The C impl was in the deleted Rust `src/std_net.rs` (hexa-lang@94ffd0f self-host absorption). Need to port to `self/runtime.c` or a new `self/native/net.c` and register in stage0 builtin dispatch. (rt-32-j claim was incorrect — verified 2026-04-16.)

### 1.4 ALM pod status (untouched)

- Pod `itfl66q4z768kh` / endpoint `https://itfl66q4z768kh-8090.proxy.runpod.net`
- **LIVE** — 62 requests served, uptime 7,948s, phi=3.05, tension=195.9
- `serve_alm_14b.py` unchanged. **Not disrupted.**

### 1.5 hexa-c4 pod (`u01lnnu8ywt92p`) status

- RUNNING, RTX 3090, `$0.22/hr`
- `/workspace/hexa-lang/build/hexa_stage0` exists (Linux x86_64 build)
- `socat` installed (apt-get install confirmed)
- `/workspace/anima/` source present but stale — needs rsync sync

---

## 2. Design Decision: Option A (FFI-backed hybrid)

Three routes evaluated:

| Option | Viable now? | Dependency | Verdict |
|---|---|---|---|
| **A. hexa orchestrates + FFI to C/CUDA shim** | After `net_listen` + `libhxqwen14b.so` | 2 artifacts | **CHOSEN** |
| B. hexa shells out to python worker | **NO — violates R-NO-PYTHON** | none | REJECTED |
| C. hexa proxy to libtorch runtime | Possible but heavy | libtorch (~4GB); bf16 ABI | DEFERRED |

**Rationale for A:**
- Hexa owns routing, JSON shaping, voice/hire/avatar route mounting
- Heavy math (Qwen14B forward, KV-cache, sampling, MI-binned phi) delegated to a single C shim `libhxqwen14b.so`
- This is the exact pattern successful in `hxlmhead` / `hxblas` / `hxcuda` libs
- Once `libhxqwen14b.so` + `net_listen` land, scaffold becomes canonical serve with zero logic changes

---

## 3. Scaffold Deliverables (this commit)

### 3.1 `serving/serve_alm_native.hexa` (new, 262 LOC)

- `san_route(method, path, body, state) -> SanResponse` — pure dispatch
- Mounts `voice_routes` (4 routes), `hire_routes` (3 routes), and `/generate`, `/consciousness`, `/health`
- FFI extern stubs: `hxqwen14b_load`, `hxqwen14b_generate`, `hxqwen14b_compute_phi_holo`
- Runtime gates: `RUNTIME_HAS_NET`, `RUNTIME_HAS_FFI_QWEN` (both `false` today)
- Self-test harness `san_smoke_test()` — **7/7 PASS**:
  - T1 GET /health → 200
  - T2 GET /voice/health → 200
  - T3 GET /voice/profiles → 200 (10 profiles present)
  - T4 POST /generate {prompt:"hi"} → 200 (mock-native-serve text)
  - T5 POST /generate {} → 400 (missing prompt)
  - T6 GET /unknown → 404
  - T7 GET /hire/capabilities → 200

### 3.2 `serving/serve_alm_native_handler.hexa` (new, 175 LOC)

- Single-request handler: reads HTTP request from stdin, writes response to stdout
- Intended for socat `SYSTEM:` invocation
- **Currently blocked by hexa `read_stdin()` deadlock** on half-open TCP sockets (curl HTTP/1.1 keeps write side open until response received → `read_stdin` waits forever for EOF)
- Kept in tree as reference for future socat bridge once hexa adds `read_http_request()` builtin (bounded read)

---

## 4. Blockers (ranked)

### 4.1 CRITICAL: hexa runtime missing `net_listen`/accept/read/write/close

- **Who owns:** hexa-lang repo maintainer
- **Path:** Port C impl (was Rust `src/std_net.rs`, deleted at 94ffd0f) into `self/runtime.c` or `self/native/net.c`. Register 8 symbols (`net_listen`, `net_accept`, `net_read`, `net_write`, `net_close`, `net_connect`, `http_get`, `http_serve`) in stage0 builtin dispatch. Rebuild `hexa.real`. Original Rust logic available at hexa-lang@ef92fc6 in git history.
- **Effort estimate:** 2-3 days (C port + dispatch wiring + smoke tests)
- **Test:** `hexa run serve_alm_native.hexa` with `RUNTIME_HAS_NET=true` should bind :8090
- **NOTE:** Earlier "merge rt-32-j" path was incorrect (verified 2026-04-16 — rt-32-j is env-define-batch, unrelated to networking)

### 4.2 HIGH: `libhxqwen14b.so` not built

- **What:** Linux x86_64 shared library exposing:
  - `int hxqwen14b_load(const char* ckpt_path)` → model handle
  - `char* hxqwen14b_generate(int h, const char* prompt, int max_tokens, float temp, float top_p, int top_k)` → null-terminated UTF-8
  - `float hxqwen14b_compute_phi_holo(int h)` → last-step phi_holo
- **Dependencies:** CUDA 11.8 + cuBLAS + bf16 Tensor Core kernels; Qwen2.5-14B base weights + LoRA adapter loader (GGML or safetensors)
- **Effort estimate:** 3-5 days (companion agents per prompt: hxcuda STFT/iSTFT + neural_vocoder)
- **Alternative bridge:** link against `libhxlmhead.so` for LM-head + write a minimal C loader for Qwen decoder stack (2-3x longer but avoids new big dep)

### 4.3 MEDIUM: Cross-platform `@link` resolution

- **What:** `@link("name")` currently Mac-only absolute paths
- **Fix:** `codegen_c2.hexa` should resolve via `HEXA_TARGET` env (per `hexa_codegen_research_20260416.md` Task 1)
- **Effort estimate:** 3-5 days (already documented in codegen research)

### 4.4 LOW: `use` side-effects pollute stdout

- `use "hire_routes"` runs the file's top-level smoke tests (5/5 PASS banners printed)
- For socat/HTTP this would corrupt the response
- **Fix options:**
  - Guard test blocks with `if env("HEXA_TEST") == "1" { ... }`
  - Or add `#[cfg(test)]`-style attribute to hexa-lang
  - Or filter with awk in launcher script (works; already in `/tmp/serve_alm_native_run.sh`)

---

## 5. Recommended Sequencing

### Phase 1 — Land `net_listen` in hexa runtime (1 day, blocks everything)

1. hexa-lang maintainer ports net builtins (Rust `src/std_net.rs` at hexa-lang@ef92fc6 → C in `self/runtime.c`) + registers in stage0 builtin dispatch
2. Rebuild `hexa_stage0` (macOS + Linux)
3. Redeploy `shared/bin/hexa` wrapper resolves to rebuilt binary
4. Verify: `hexa run test_net.hexa` (from §1.2) returns `LISTEN ok`

### Phase 2 — Flip `RUNTIME_HAS_NET = true` in scaffold (1 hour)

1. Wire real socket loop at end of `serve_alm_native.hexa:main()` (loop template already in comments)
2. Smoke test on hexa-c4 pod (cheap RTX 3090):
   ```bash
   ssh hexa-c4
   rsync -av anima/ /workspace/anima/
   /workspace/hexa-lang/build/hexa_stage0 run \
     /workspace/anima/serving/serve_alm_native.hexa --port 8090 &
   curl http://localhost:8090/health  # → 200 ok
   curl http://localhost:8090/voice/profiles  # → 200 + 10 profiles
   ```
3. Verify `/health`, `/voice/profiles`, `/voice/health`, `/hire/capabilities` return 200

### Phase 3 — Build `libhxqwen14b.so` (3-5 days)

- Companion agents handling `hxcuda` STFT/iSTFT + neural vocoder set pattern
- Reuse `hxlmhead` + `hxblas` linkage
- Key kernels needed: Q/K/V projection, GQA attention, SwiGLU FFN, RMSNorm, RoPE
- Alternative: dlopen `libtorch.so` + thin C wrapper calling `torch::jit::load()` — 1-2 day path but +4GB dep

### Phase 4 — Flip `RUNTIME_HAS_FFI_QWEN = true` and deploy (1 day)

1. rsync `libhxqwen14b.so` + `serve_alm_native.hexa` to ALM pod `itfl66q4z768kh`
2. Stop `serve_alm_14b.py` (graceful: drain via `SIGTERM`, wait for request count to stabilize)
3. Start `hexa run serve_alm_native.hexa --port 8090 --checkpoint /runpod/ckpt_r9`
4. Run `hire_sim_alm_actual.py` harness against new endpoint; compare CE/phi against baseline
5. Rollback plan: `kill -9 $(pgrep hexa)` + restart `serve_alm_14b.py` (recipe in BENCHMARKS_README.md)

### Total path: 5-7 days engineering, 0 Python remaining in serving path.

---

## 6. Deployment Recipe (future — once §5 Phase 1 lands)

### 6.1 Smoke on hexa-c4 (non-disruptive)

```bash
# 1. Sync source
rsync -avz --delete /Users/ghost/Dev/anima/ \
  -e "ssh -i /Users/ghost/.runpod/ssh/RunPod-Key-Go -p 61461" \
  root@64.228.13.219:/workspace/anima/

# 2. Install deps
ssh hexa-c4 "apt-get install -y socat curl"

# 3. Start hexa serve (port 8090)
ssh hexa-c4 "cd /workspace/anima && \
  HEXA_LOCAL=1 /workspace/hexa-lang/build/hexa_stage0 run \
  serving/serve_alm_native.hexa --port 8090 &"

# 4. Verify endpoints
curl http://<hexa-c4-public>:8090/health
curl http://<hexa-c4-public>:8090/voice/profiles
curl -X POST http://<hexa-c4-public>:8090/generate \
  -H 'Content-Type: application/json' -d '{"prompt":"hello"}'
```

### 6.2 Production replacement on ALM pod

```bash
# Pre-flight
curl -sS https://itfl66q4z768kh-8090.proxy.runpod.net/health > /tmp/pre_swap.json
PRE_SERVED=$(jq .requests_served /tmp/pre_swap.json)

# Drain — stop accepting new requests, wait 60s
ssh alm-pod "pkill -SIGTERM -f serve_alm_14b.py"
sleep 60

# Start native
ssh alm-pod "cd /workspace/anima && \
  LD_LIBRARY_PATH=/workspace/lib:$LD_LIBRARY_PATH \
  HEXA_LOCAL=1 /workspace/hexa-lang/build/hexa_stage0 run \
  serving/serve_alm_native.hexa \
  --port 8090 --checkpoint /runpod/ckpt_r9 &"

# Validate
sleep 10
curl -sS https://itfl66q4z768kh-8090.proxy.runpod.net/health | jq .version
# expect: "2.0-rc-native"

# Replay 10 prompts, compare latency/CE vs pre_swap baseline
python3 training/deploy/hire_sim_alm_runner.py --endpoint $ENDPOINT --n 10 --baseline pre_swap.json
```

---

## 7. What was tested today (2026-04-16)

- `serve_alm_native.hexa` smoke: **7/7 PASS** on local `hexa_stage0`
- `http_server.hexa`: parse errors on `MmapHandle` type — not runnable
- `voice_routes.hexa`: 5/5 tests PASS standalone
- `hire_routes.hexa`: 5/5 tests PASS standalone
- Direct stdin → `serve_alm_native_handler.hexa`: HTTP/1.1 200 response well-formed
- socat TCP bridge: **timeout** — `read_stdin()` deadlock on half-open socket (blocker §4.4)
- ALM pod `itfl66q4z768kh`: **untouched**. `/health` confirms 62 req served, phi=3.05, uptime 7,948s

---

## 8. Files modified / created

- `serving/serve_alm_native.hexa` — NEW, 262 LOC, 7/7 self-test PASS
- `serving/serve_alm_native_handler.hexa` — NEW, 175 LOC, stdin/stdout handler (parked until hexa `read_http_request` builtin)
- `training/deploy/hexa_serve_native_plan_20260416.md` — THIS FILE
- `serving/serve_alm_14b.py` — **UNCHANGED** (still live on pod)

No ALM pod ops performed. No production impact.
