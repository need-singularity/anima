# ALM 14B Hexa-Native Port — Plan (2026-04-19)

## Scope

Restore `training/train_alm_14b.hexa` from its R37/AN13/L3-PY emergency stub
(18 LOC, panics on entry) to a real hexa-native skeleton that:

1. Parses and runs under `hexa run training/train_alm_14b.hexa --selftest`
   without panic — prints a verification block mirroring `train_alm.hexa`.
2. Provides a unified CLI dispatcher covering the historical ALM 14B rounds
   (r5, r9, r10, r10b, r10c, r10d, r11) whose `launch_alm_14b_r10{,b,c,d}.hexa`
   wrappers are still emergency-stubbed.
3. Defines canonical hexa structs for the 14B trainer — `Alm14bConfig`,
   `Alm14bState`, `Alm14bModel`, `LoraAdapter` — so future real forward /
   backward / optimizer code has a stable surface.
4. Wires all 7 SESSION 2026-04-19 aux-loss opt-in flags (default OFF,
   byte-identical selftest vs pre-wiring), identical flag names to
   `train_alm.hexa` and `train_clm.hexa` so one launcher can drive all three.

## Non-goals

- Replacing `training/train_alm_lora.hexa` — that is the already-shipped r11
  real trainer (1115 LOC, hxqwen14b FFI, AdamW, LoRA math). This skeleton
  treats `train_alm_lora.hexa` as the r11 back-end and delegates to it
  (or documents the delegation TODO).
- Running actual 14B training on H100 — pod availability is a separate track
  and the skeleton explicitly refuses to start a real run without a real
  forward/backward FFI landing first.
- 32B / 72B multi-GPU / FSDP — `train_alm_32b_r1.hexa` and the 72B plan are
  out of scope for this 14B-only skeleton.
- `corpus_ko_ytv1` integration — that is CLM's corpus, ALM uses the existing
  corpus paths from `alm_r11_plan.json`.

## Reference recovery (commit effa4707)

`git show effa4707:training/train_alm_14b.py` — 264 LOC Python, recovered
for reference only (no file written, no strings embedded). Shape:

| Section | Lines | hexa mapping |
|---|---|---|
| imports (torch, transformers, peft) | 1-30 | TODO FFI / hxqwen14b |
| `DEFAULT_*` config constants | 33-45 | `comptime const` direct port |
| `TextDataset` + `__getitem__` | 49-64 | `struct Alm14bDataset` stub |
| `load_corpus_chunked` | 67-95 | inherit `corpus_open/corpus_window` pattern from train_clm.hexa §B |
| `train(args)` model load + LoRA | 100-135 | `alm14b_model_load` + `lora_adapter_new` — FFI stubs, delegates to train_alm_lora.hexa r11 real impl |
| Dataloader + AdamW + schedule | 137-160 | `alm14b_optim_new` — TODO FFI matching hxblas AdamW in train_alm_lora.hexa |
| Training loop (while step < args.steps) | 165-225 | `alm14b_train_step` + `alm14b_train_loop` — TODO pattern already landed in train_alm_lora.hexa::train_loop |
| Logging / eval / save | 200-240 | `alm14b_save` + `alm14b_eval` stubs — identical R2 upload pattern to train_alm.hexa::alm_save |
| argparse main | 244-264 | `_cli_has_flag` + `_cli_flag_value` borrowed verbatim from train_clm.hexa lines 3080-3168 |

## Component inventory

| Component | CLM template ref | ALM status | Skeleton port | Real port blocker |
|---|---|---|---|---|
| Config constants | train_clm.hexa §PSI_* + scale configs | `train_alm.hexa:144-189` has them | re-export + add 14B-specific LoRA/batch/seq/save_every | none — pure constants |
| CLI dispatch (args / flags / train-mode trigger) | train_clm.hexa:3078-3168 | missing | full port | none |
| Aux flag wiring (7 opt-in) | train_clm.hexa:3115-3128 | `train_alm.hexa:479-490` | full port | none |
| `Alm14bConfig` struct | train_clm.hexa `ScaleConfig` | `train_alm_lora.hexa::RunConfig` | defined | none |
| `Alm14bState` struct | train_clm.hexa `TrainState` | `train_alm.hexa::AlmState` | defined | none |
| `Alm14bModel` / base load | train_clm.hexa `DecoderModel` | `train_alm_lora.hexa::hxqwen14b_load` | stub | `hxqwen14b_forward_with_lora` missing from C (Day-2) |
| `LoraAdapter` (A/B matrices) | n/a (CLM is from-scratch) | `train_alm_lora.hexa:398-489` | stub | same Day-2 |
| Tokenizer (BPE load) | train_clm.hexa byte-level (no BPE) | missing (peft tokenizer used PyTorch) | TODO | need hexa-native BPE load — candidate Phase-3 slice |
| Data pipeline (corpus chunked) | train_clm.hexa:625-740 `corpus_open/window` | `train_alm_lora.hexa::load_corpus` (JSONL) | delegate | none — reuse train_alm_lora.hexa |
| Optimizer (AdamW) | train_clm.hexa `optim_new` + adam_step | `train_alm_lora.hexa:672-704` | delegate stub | none — real impl already landed |
| Forward pass | train_clm.hexa `decoder_forward` | `train_alm_lora.hexa::forward_qwen14b_with_lora` FFI | stub | Day-2 C entry |
| Backward pass | train_clm.hexa `_ce_fwd_bwd` + `decoder_backward` | `train_alm_lora.hexa::backward_lora_only` FFI | stub | Day-2 C entry |
| Scheduler (warmup + cosine) | train_clm.hexa `lr_for_step` | `train_alm_lora.hexa::warmup_lr` | port warmup; cosine TODO | none (scalar math) |
| Checkpoint save | train_clm.hexa ckpt writer | `train_alm_lora.hexa::save_lora` | stub | delegate |
| Checkpoint load | train_clm.hexa ckpt loader | missing | TODO | need binary .bin tensor reader FFI |
| Eval (5 metrics) | train_clm.hexa `eval_step` | `train_alm.hexa::alm_eval` (stub) | stub | needs PPL/KR/IF metric FFI or pure-hexa BPE decode |
| Logging | train_clm.hexa println + rate calc | `train_alm_lora.hexa:830-870` | port | none (wall-clock via `time()` builtin) |

## Port strategy

### Phase 2 skeleton (this PR)

Structural port only — types, CLI, flag wiring, dispatch glue, all
compute body ops are TODO comments with the three-field trailer:
`(1) PyTorch op replaced; (2) FFI primitive needed; (3) analogous TODO
in train_clm.hexa`.

- Single-file (no `use` chain) to dodge `feedback_hexa_silent_exit_5_imports`.
- ≤2 float fields per struct return to dodge `feedback_hexa_struct_return_bug`.
- No list mutation through helpers — rebinding only (dodges pass-by-value).
- Struct-field lists avoided for AdamW state (inherit r11's flat-array policy).
- Parse via `hexa parse training/train_alm_14b.hexa` before running.
- Run via `hexa run training/train_alm_14b.hexa --selftest`.

### Phase 3 candidate slices (not all will ship this PR)

Ranked by blast radius / dependency:

1. **AdamW optimizer (pure hexa)** — already done in train_alm_lora.hexa. Just
   re-expose with `Alm14bConfig` shape. Lowest risk. Self-test: `params[0]`
   moves downhill for 10 synthetic steps.
2. **LoRA adapter math (apply ΔW = α/r · B @ A · x)** — done in
   `train_alm_lora.hexa::apply_lora` line 490. Re-expose. Self-test: assert
   `ΔW=0` when B is zero-initialized per LoRA paper.
3. **BPE tokenizer load (vocab/merges)** — nothing hexa-native exists for Qwen2
   tokenizer. Would need a SentencePiece-compatible hexa port or bypass via
   the existing `tokenizer/kr_bpe_32k.model` and an FFI into
   `sentencepiece` C lib. Higher risk — blocked on tokenizer decision. Skip.

**Recommended for this PR:** slice #1 or #2. Slice #2 is marginally more
useful (it is the ALM-specific piece — AdamW is boilerplate shared with
any trainer), but slice #1 is more independent of FFI readiness and gives
a cleaner self-test. Pick slice #1.

## Risk list

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| hexa stage1 rejects struct layout | M | high — blocks PR | Mirror train_alm_lora.hexa RunConfig/RunFloats layout 1:1, those are confirmed to parse under 0.1.0-stage1 |
| `args()` indexing differs from expected on stage1 | L | medium | Use the r11 convention: `args()[2:]` (skip binary + 2nd self-reference), empirically confirmed line 1010 of train_alm_lora.hexa |
| `use` statement silent-exit (5-import chain) | M | high | Single-file, NO `use`. All helpers inlined. Self-test asserts first-line println fires. |
| Multi-float struct return corrupts | L | medium | All return types ≤2 floats; multi-metric bundles returned as `[float]` arrays |
| Stub prints invalidate parse | L | low | Parse check first: `hexa parse` before `hexa run` |
| Hook blocks new .py/.rs/.sh | N/A | n/a | Only .hexa + .md in this PR |
| Selftest diverges from train_alm.hexa format | L | low | Mirror the exact println template from train_alm.hexa:497-511 |
| FFI bindings (hxqwen14b_*) unavailable on Mac | H | low — intended | Dry-run mode treats handle=1 as pretend-handle (r11 convention); selftest never loads real weights |

## Success criteria

- [x] Plan doc written (this file)
- [ ] `training/train_alm_14b.hexa` skeleton replaces stub, runs under
      `hexa run … --selftest` with exit 0
- [ ] Selftest output includes:
  - config dump (base id, n_layer, d_model, vocab)
  - LoRA defaults (r=8, alpha=16)
  - 7 aux flags with their current values (default 0)
  - at least one invariant assertion (bf16, grad_accum ≥ 1, lora_r > 0)
- [ ] No `.py` / `.rs` / `.sh` files created or edited
- [ ] Every TODO carries (pytorch op, FFI primitive, CLM xref)
- [ ] `git status` shows only `.hexa` / `.md` additions/modifications
- [ ] (Phase 3, optional) one real slice ported with inline unit selftest

## Out of scope (confirm with user later)

- Should `train_alm_14b.hexa` replace `train_alm.hexa` for the 14B path
  specifically, or should `train_alm.hexa` remain the multi-scale entry
  and `train_alm_14b.hexa` be the 14B-specific detail file?
- Should `launch_alm_14b_r10{,b,c,d}.hexa` de-stubs happen in the same
  PR or in a follow-up? (They reference the same `train_alm_14b.py` that
  no longer exists; they need a hexa-native trainer to delegate to.)
- Is `train_alm_lora.hexa` considered the canonical r11+ implementation
  (in which case `train_alm_14b.hexa` should delegate to it) or does the
  user want `train_alm_14b.hexa` to subsume it?
