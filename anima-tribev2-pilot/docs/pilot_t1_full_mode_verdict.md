# Pilot-T1 full-mode verdict (TRIBE v2 forward, H100)

frozen 2026-04-26 — anima ω-cycle session 28 (Pilot-T1 full-mode resume).

> This document is the human-readable record. The authoritative verdict is in
> `state/pilot_t1_full_mode_result_v1.json`. Cortical maps are in
> `state/pilot_t1_maps_full_v1.npz` (key per family, shape `(16, n_vertices)`).

## Hypothesis (frozen, ANIMA_INTEGRATION_PROPOSAL.md §4)

- **H0**: 4-family prompts (Law / Phi / SelfRef / Hexad) → family-separated
  cortical map.
- **PASS**: pairwise inter-family vertex Pearson r < 0.7 in at least one
  family pair AND intra-family vertex r > 0.85 for all families.
- **FAIL**: pairwise vertex r > 0.95 across all 6 family pairs (axis collapse,
  LLM family axis ⊥ brain axis).
- **INCONCLUSIVE_FULL**: numerically valid result that satisfies neither
  PASS nor FAIL bounds.

## Run setup

- Pod: `anima-pilot-t1-v3` (id `stldy2ewplkhsj`), 1× H100 80GB SXM,
  $2.99/hr listed (active charges already accruing prior to this cycle —
  cycle-attributed cost is the delta during this re-launch only).
- Workspace: `/workspace/anima_pilot_t1/`
  - `ref/tribev2/` — frozen Meta FAIR clone (rsync→tar fallback, ~1 MB).
  - `corpus/corpus_alm_r14_v1.jsonl` — 1200 lines, 16 _en per family available.
  - `scripts/install_pod_deps.sh`, `scripts/pilot_t1_inference_full.py`.
  - `state/install.log`, `state/pilot_t1_full_mode_result_v1.json`,
    `state/pilot_t1_maps_full_v1.npz`.
- HF token mounted at `~/.cache/huggingface/token` (gated Llama-3.2-3B).

## ω-cycle iteration trace

- iter 1 (prior session): design + dependency_check (PyPI PASS).
- iter 2 (prior session): mac local stub-mode → `T1_INCONCLUSIVE_STUB`,
  byte-deterministic e2e pipeline test only (`state/pilot_t1_result.json`).
- iter 3 (this session): H100 full-mode resume. Re-used existing RUNNING pod
  rather than create new one (cost-aware: `feedback_forward_auto_approval`).

### Encountered issues + fixes

| issue | fix |
|---|---|
| awk pod-discovery filter expected table output, runpodctl emits JSON | switched to `python3 -c 'json.load'` parse |
| pod has no `rsync` binary | tar+ssh streaming fallback (~1 MB tarball) |
| local inference script repeatedly disappeared from `scripts/` between Bash invocations on mac (other-agent cleanup of untracked tribev2-pilot files suspected) | scripts staged to pod once (pod is stable); run from pod thereafter |
| install timing under launch wrapper auto-set `install_rc=0` even when `pip install` actually never ran (script not on pod) | re-pushed `install_pod_deps.sh` directly via `scp /tmp/...` and ran it explicitly with `tee state/install.log` for honest capture |

## raw#10 honest

- The pod was already RUNNING for ~2.5 days (load avg 12+). This means the
  user has been incurring idle cost regardless of this cycle. The cost cap
  in this cycle accounts only for the *delta* between this cycle's start
  and end, NOT the historical idle burn.
- TRIBE v2 demo path uses `TextToEvents` → gTTS → Whisper transcription
  before the multimodal forward. If `whisperx` install fails, the text path
  raises and the verdict becomes `T1_DEFERRED_PREDICT_BLOCKED` per family —
  the JSON records the exception trace verbatim.
- `modality_dropout=0.3` and `subject_dropout=0.1` are stochastic at forward
  time. We seed `numpy`/`torch`/`torch.cuda` with `20260426` before model
  load, but TRIBE v2 forward draws from the same pool — single deterministic
  realisation, not an ensemble.

## Result summary

```
status: blocked at first prompt — Llama-3.2-3B gated repo access denied
verdict: T1_DEFERRED_LLAMA_GATED_ACCESS_BLOCKED
inter/intra family r matrix: NOT COMPUTED (TRIBE forward never reached)
HF token: valid (account "dancinlife", write role) — but not on Llama-3.2-3B authorized list
```

### Chain that worked (proves install + GPU + non-LLM stages are fine)

| stage | result |
|---|---|
| pod discovery (RUNNING anima-pilot-t1-v3) | OK |
| tar+ssh tribev2 ref + corpus + scripts + HF token | OK |
| pip install minimal deps | OK (1m25s) |
| pip install -e tribev2 (forced torch 2.4 → 2.6) | OK |
| `from tribev2.demo_utils import TribeModel` | OK |
| spacy en_core_web_sm download | OK |
| pip install whisperx (forced torch 2.6 → 2.8 + cu128) | OK |
| `apt install ffmpeg` (post-FAIL #1, audio backend missing) | OK |
| `curl install.sh \| sh` for uv/uvx (post-FAIL #1, tribev2 invokes `subprocess.run(['uvx', 'whisperx', ...])`) | OK |
| TRIBE checkpoint download (`facebook/tribev2/best.ckpt`) | OK (~3 GB) |
| TribeModel.from_pretrained (CUDA H100) | OK |
| gTTS TTS audio generation per prompt | OK |
| uvx whisperx large-v3 PEX install (~5 GB) + first transcription | OK (~102 s for first, cached after) |
| spacy en_core_web_lg download (~400 MB) | OK |
| `model.predict(events)` text encoder load step | **FAIL** — `OSError: gated repo Llama-3.2-3B`, account "dancinlife" not authorized |

### Resolution path

The user must:

1. Visit https://huggingface.co/meta-llama/Llama-3.2-3B logged in as
   account `dancinlife` (the same account the cached HF token belongs to).
2. Click the **I Accept** gate button on the Llama 3.2 Community License.
3. Wait for Meta's automated approval (typically 1-2 business days; the
   gate is `gated:"manual"` per the HF API).
4. Re-run `bash anima-tribev2-pilot/scripts/launch_h100_pilot_t1.sh`.
   - Pod `stldy2ewplkhsj` is still running and has all the deps cached
     (Python deps, whisperx PEX, TRIBE weights, large-v3 weights, spacy
     en_core_web_lg, ffmpeg). Only the gated `Llama-3.2-3B/config.json`
     fetch needs to succeed.
   - Estimated wallclock: ~13 min (model load 2m + 64 prompt × ~10 s/prompt).
   - Estimated GPU cost: ~$0.65 at $2.99/hr.

### Why we did NOT swap to a non-gated text encoder

TRIBE v2 was *trained* with `meta-llama/Llama-3.2-3B` as its text feature
extractor at fixed layer fractions `[0, 0.2, 0.4, 0.6, 0.8, 1.0]` and
fixed hidden dim. Swapping to another LLM would require re-training the
fusion head — out of scope for a Pilot-T1 H0 evaluation (which targets
the *frozen* TRIBE v2 architecture as a black-box forward encoder).

## Cross-link policy

- `references/tribev2/` is **read-only** (frozen Meta FAIR clone).
- `state/pilot_t1_result.json` (stub mode) is **read-only**, preserved as
  pipeline-integrity baseline.
- This full-mode result is the authoritative H0 evidence (or honest
  deferral) — it does NOT overwrite the stub baseline.

## Next steps

- T1_PASS → Pilot-T2 (8th-axis registration) un-parks
  per `docs/pilot_t2_8th_axis_spec.md`.
- T1_FAIL → R33 ledger entry remains at `architectural_reference` tier
  (no measurement-level promotion); update `next_probe` field to record
  "LLM family axis ⊥ brain axis evidence captured".
- T1_INCONCLUSIVE_FULL → iterate: increase n_per_family, vary feature
  aggregation, or test single-modality (text-only) ablation.
- T1_DEFERRED_* → investigate the recorded exception in the result JSON,
  fix the install or auth chain, re-run.
