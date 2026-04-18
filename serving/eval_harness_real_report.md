# eval_harness real rewrite (G6)

## Change
`serving/eval_harness.hexa` was a synthetic logistic stub
(A3: `macro_acc = logistic(step/500)` on hard-coded refs — identical
numbers for r4 vs r9). Old file preserved as
`eval_harness_synthetic.hexa` (smoke tests still use it).
New harness drives `/generate` per `reference_alm_serve_api.md`
(uses `text` key, no hot swap). No in-process weight load
(blocked by `feedback_py_ban_total`).

## Coverage
- KoBEST n=20 (inline): BoolQ x5, COPA x5, SentiNeg x5, WiC x5.
  Closed answers, max_tokens=32, temperature=0 → deterministic.
- HAE-RAE: stub-pending. HF `HAERAE-HUB/HAE_RAE_BENCH` needs Python loader.
- MMLU-Ko: stub-pending. HF `HAERAE-HUB/KMMLU` needs Python loader.

## Safety
- Endpoint probe before eval. Unreachable → emits
  `deferred:true, deferred_reason:"endpoint_unreachable"`, exit 2.
  Never silently 0 (honours `feedback_closed_loop_verify`).
- `--ckpt-path r2:...` → `rclone copy` to `/tmp/eval_adapter_<step>/`.
  Operator must restart `serve_alm_14b.hexa` — no hot swap.

## Self-test (verified)
`hexa run serving/eval_harness.hexa --selftest` →
3 mocks (correct/wrong/partial) = 2/3 = 0.6667. PASS.

## Next action
Export HF HAE-RAE + MMLU-Ko to R2 (`r2:anima-corpus/haerae.jsonl`,
`kmmlu.jsonl`) via one-time Python job, then extend harness with
`build_haerae()` / `build_mmluko()` reading via `rclone cat`.
Keeps runtime Python-free.
