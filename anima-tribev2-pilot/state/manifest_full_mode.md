# Pilot-T1 full-mode manifest (GPU pod / Colab)

frozen at 2026-04-26 — anima ω-cycle Pilot-T1 iter 2 deferral.

## Why mac local cannot run full mode (current)

1. **whisperx torchaudio API mismatch** — `torchaudio.list_audio_backends()` removed in newer torchaudio,
   used by `pyannote.audio` which whisperx imports. uvx-isolated whisperx env (python 3.14) hits this.
2. **venv distutils-precedence shim race** — homebrew python 3.12 venv post-install left `numpy/__init__.py`
   missing after setuptools downgrade; one re-install round-trip fixed it but the path is fragile.
3. **mac CPU forward time** — even if whisperx works, llama-3.2-3B + V-JEPA2-vitg + Wav2VecBert
   forward on M-series CPU is ≫ 60 min for 64 prompts.

## What works on mac local (verified 2026-04-26)

- `pip3 index versions neuralset` → `0.1.0, 0.0.3, 0.0.2, 0.0.1` ✓
- `pip3 index versions neuraltrain` → `0.1.0, 0.0.3, 0.0.2, 0.0.1` ✓
- `pip install -e references/tribev2` → completes (after distutils shim fixup)
- `from tribev2.demo_utils import TribeModel` → import OK
- `TribeModel.from_pretrained("facebook/tribev2", cache_folder=...)` → reaches HF download stage
- 4-family prompt extraction from `corpus_alm_r14_v1.jsonl` → 16 each (Law/Phi/SelfRef/Hexad)
- Stub e2e pipeline → 4 × 20484 cortical maps + r-matrix → JSON verdict, deterministic.

## Recommended path A — Colab (cheapest, gated Llama OK)

```
# Cell 1
!pip install "tribev2[plotting] @ git+https://github.com/facebookresearch/tribev2.git"

# Cell 2 — Cache HF token
from huggingface_hub import notebook_login
notebook_login()  # use anima HF account with Llama-3.2 access granted

# Cell 3 — Run pilot
!git clone https://github.com/<anima-mirror>/anima-tribev2-pilot.git
%cd anima-tribev2-pilot
!python scripts/pilot_t1_inference.py --mode=full --n-per-family=16
```

Estimated: 1× T4/L4 GPU, ~30-45 min wall-clock for 64 prompts.

## Recommended path B — anima H100 spot pod ($0.5 cap)

1. `bin/launch_pod_h100.sh` (anima standard launcher)
2. inside pod: same install + run as Colab
3. expected: ≤10 min wall-clock for 64 prompts on H100.

Cost estimate at $2.50/hr H100 spot: $0.5 covers ~12 minutes. 64 prompts fits if model load < 8min.

## Required HF gated access

- `meta-llama/Llama-3.2-3B` — must request access at https://huggingface.co/meta-llama/Llama-3.2-3B
  before running. Cache local token at `~/.cache/huggingface/token` (anima already has token cached
  per environment check).

## Falsifiability preserved

The stub-mode result (`state/pilot_t1_result.json`) records `T1_INCONCLUSIVE_STUB` with 0.011 max
inter-family r. This is **NOT a falsification** of H0 — it's an e2e pipeline integrity check.
H0 evaluation requires full-mode (path A or B above) producing real TRIBE forward predictions.

## Sub-criterion verdicts already locked

| sub-criterion | verdict | evidence |
|---|---|---|
| neuralset 0.0.2 PyPI | PASS | `state/dependency_check_verdict.json` |
| neuraltrain 0.0.2 PyPI | PASS | `state/dependency_check_verdict.json` |
| `tribev2` editable install | PASS | mac venv (verified once, see deps_check.log iter 1) |
| `from tribev2.demo_utils import TribeModel` | PASS | mac venv import smoke |
| 4-family prompt extraction | PASS | 16 each from `corpus_alm_r14_v1.jsonl` |
| Stub pipeline e2e | PASS | byte-identical re-run verified |
| Full TRIBE forward + cortical maps | DEFERRED | path A/B above |
| H0 PASS/FAIL/INCONCLUSIVE verdict | DEFERRED | requires full forward |

## Pilot-T2 (8th axis registration) gate

Pilot-T2 (`paradigm v11 8th axis = TRIBE v2 stimulus-driven cortical correlation`) requires
Pilot-T1 PASS. Until full-mode runs, T2 stays parked.
