# anima-tribev2-pilot — Pilot-T1 (Mk.XI v10 ↔ TRIBE v2 cortical-vs-family)

frozen at 2026-04-26 — anima ω-cycle session, $0-0.5 budget cap.

## Purpose

Test whether the 4-family prompt set (Law / Phi / SelfRef / Hexad) used by Mk.XI v10 produces
**family-separated cortical maps** when fed to TRIBE v2 (Meta FAIR's multimodal fMRI foundation
model, text encoder = meta-llama/Llama-3.2-3B).

## Hypothesis (frozen, ANIMA_INTEGRATION_PROPOSAL.md §4)

- **H0**: 4-family prompts → family-별로 분리된 cortical map.
- **PASS** : pairwise inter-family vertex r < 0.7 (≥1 pair) AND intra-family r > 0.85.
- **FAIL** : pairwise r > 0.95 across all pairs (axis collapse, LLM family axis ⊥ brain axis).

## Layout

```
anima-tribev2-pilot/
├── README.md                           ← this file
├── scripts/
│   ├── dependency_check.sh             ← PyPI availability + optional venv install
│   └── pilot_t1_inference.py           ← stub | full mode forward + r-matrix verdict
├── state/
│   ├── dependency_check_verdict.json   ← PyPI sub-criterion verdict
│   ├── dependency_check.log
│   ├── pilot_t1_result.json            ← FROZEN final verdict + r matrices + sha256
│   ├── pilot_t1_maps.npz               ← per-family cortical maps (4 × n × 20484)
│   ├── pilot_t1_run.log
│   └── manifest_full_mode.md           ← GPU pod / Colab manifest for full-mode
└── .venv/                              ← venv (gitignored; created by --install)
```

## Cross-link policy

This pilot folder treats `references/tribev2/` (the upstream Meta FAIR clone) as **read-only**.
No edits to upstream code; all wrappers live here.

Cross-links into anima:

| anima target | role |
|---|---|
| `references/tribev2/` | upstream clone, frozen |
| `experiments/alm_r14/corpus_alm_r14_v1.jsonl` | 4-family prompt source (category: law/phi/selfref/hexad) |
| `~/.claude/projects/-Users-ghost-core-anima/memory/project_paradigm_v11_stack_complete.md` | Mk.XI v10 architecture context |
| `.roadmap` entry | registered as P5 axis-8 candidate (Pilot-T2 dep) |

## ω-cycle state

- iter 1: design + implement + sub-criterion (PyPI). PASS.
- iter 2: full-mode mac local blocked by whisperx torchaudio API mismatch + numpy/distutils
  shim race during venv install. **stub mode = e2e pipeline test only**, not authoritative for H0.
- iter 3 (deferred): GPU pod / Colab manifest in `state/manifest_full_mode.md`.

## Usage

```bash
# 1) PyPI availability (sub-criterion)
bash anima-tribev2-pilot/scripts/dependency_check.sh

# 2) Optional venv install (≈1.5 GB; not required for stub mode)
bash anima-tribev2-pilot/scripts/dependency_check.sh --install

# 3) Stub-mode pipeline test (ms, no GPU, NOT a real H0 result)
python3 anima-tribev2-pilot/scripts/pilot_t1_inference.py --mode=stub --n-per-family=16

# 4) Full-mode (requires venv + HF gated Llama-3.2-3B + uvx whisperx + GPU recommended)
anima-tribev2-pilot/.venv/bin/python anima-tribev2-pilot/scripts/pilot_t1_inference.py --mode=full --n-per-family=16
```

## Determinism

All anima-side computation is deterministic byte-identical:

- `np.random.seed(20260426)`
- per-prompt seed = `blake2b(prompt_text)` → `default_rng(seed)` standard normal
- per-family baseline = `blake2b(family) + base_seed` → cosine ridge
- corpus subset = sorted by `id`, take first `n_per_family` `_en` ids per category

Re-run `pilot_t1_inference.py --mode=stub` ⇒ all numerical fields identical (only
`elapsed_seconds` varies).

## License

CC-BY-NC-4.0 inherited from TRIBE v2 (research only, anima-compatible).
