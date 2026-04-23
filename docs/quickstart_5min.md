# anima — 5-minute quickstart

> Get from a clean machine to your first cert verdict in **five minutes**.
> Author-maintained walkthrough (NOT auto-generated). Last reviewed: 2026-04-22.

This walks you through:

1. Installing the `hexa` toolchain (the only runtime anima depends on).
2. Cloning anima.
3. Running `tool/cert_gate.hexa` — a deterministic reward-shaping gate that
   loads the full `.meta2-cert/` stack and emits a single verdict JSON.
4. Reading the verdict.

There is **no Python**, **no GPU**, and **no model download** required for
this quickstart. Total wall-clock budget on a modern laptop: ~5 minutes
(2 min install, 30 s clone, 1 min run, ~1 min reading the result).

---

## 0. Prerequisites (30 s)

- macOS, Linux, or WSL2.
- `git`, `curl`, `bash`, `awk`, `shasum` (preinstalled on macOS / standard
  Linux distros).
- ~200 MB free disk for the anima checkout.

---

## 1. Install hexa (90 s)

`hexa` is the small interpreter every anima tool runs on. It lives in a
sibling repo and builds in seconds.

```bash
cd ~                              # or wherever you keep source
mkdir -p core && cd core
git clone https://github.com/anima/hexa-lang.git
cd hexa-lang
./build.sh                        # or `make` — single binary at ./bin/hexa
export PATH="$PWD/bin:$PATH"
hexa --version                    # sanity check
```

If `./build.sh` is missing, the repo's README documents the alternate
`make build` path. You should see a version string ending in a short SHA.

---

## 2. Clone anima (30 s)

```bash
cd ~/core
git clone https://github.com/anima/anima.git
cd anima
```

The repo is checkout-only — no `pip install`, no `npm install`, no model
weights. Everything you need to verify a cert is already in `.meta2-cert/`
and `state/`.

---

## 3. Run your first cert (~60 s)

The `cert_gate` tool is the canonical entry point. It loads ~10 breakthrough
certificates plus ~20 state verdict files, computes a deterministic
`reward_mult` ∈ [0.0, 1.5], and writes a proof-carrying JSON to
`state/cert_gate_result.json`.

```bash
hexa run tool/cert_gate.hexa --selftest
```

Expected tail of the output:

```
  count_ok_cert  (>=10)  = true   (got=10)
  count_ok_state (>=20)  = true   (got=22)
  reward_ok      (>=1.0) = true   (got=1.25)
  triplet_ok             = true

  [out] state/cert_gate_result.json
  [PASS] selftest 100% — Phase Gate Day 1 #22 green
```

If you see `[PASS]`, the entire stack — Mk.VIII triplet, AN11 factor,
Hexad factor, and the auxiliary signal — verified deterministically on
your machine. The same input produces a byte-identical `reward_mult`
on every re-run.

---

## 4. Read the verdict (60 s)

```bash
cat state/cert_gate_result.json | head -40
```

Key fields:

| field | meaning |
| ----- | ------- |
| `verdict` | one of `FULL_REWARD`, `BASE_OR_ABOVE`, `SOFT_SUPPRESS`, `FLOOR`, `REJECT_BELOW_FLOOR` |
| `reward_mult` | scalar gradient multiplier in [0.0, 1.5] |
| `core_sat` | mean of (an11_sat, hexad_sat, mk8_sat) — proves admissibility |
| `selftest.byte_identical` | `true` iff two consecutive runs produce the same scalar |
| `factors.*.sources[]` | per-source verdicts — your audit trail |

The JSON is your **proof artifact**. Commit it, diff it across runs, or
feed it to a downstream trainer — the schema is stable
(`anima.cert_gate.v1`).

---

## 5. Where to go next

- `hexa run tool/auto_tool_index.hexa` — generate a fresh index of every
  tool/*.hexa with one-line descriptions (writes `docs/tool_index_auto.md`).
- `hexa run tool/cert_graph_gen.hexa` — render the cert relationship graph
  (writes `docs/cert_graph.md` + `state/cert_graph.json`).
- `hexa run tool/api_surface_extract.hexa` — emit per-tool API surface docs
  to `docs/api/`.
- `hexa run tool/roadmap_diff_viz.hexa` — visualize per-commit `.roadmap`
  status changes (writes `docs/roadmap_diff_viz.md`).
- `tool/cert_gate.hexa --help` — full CLI reference for the cert gate.
- `.roadmap` — the SSOT phase/track/milestone registry; never hand-edit.
- `docs/TOC.md` — auto-generated table of contents for everything in `docs/`.

---

## Troubleshooting

- **`hexa: command not found`** — `PATH` did not pick up `hexa-lang/bin`.
  Re-run the `export PATH=...` line, or move the binary to `/usr/local/bin`.
- **`SETUP_ERROR — docs dir missing`** — you ran a tool from outside the
  repo root. `cd` into the anima checkout first.
- **`count_ok_cert (>=10) = false`** — the `.meta2-cert/` directory is
  partial. Re-fetch with `git pull` (or `git lfs pull` if LFS is in use).
- **selftest passes but `byte_identical=false`** — your shell's `LC_ALL`
  is non-C and a sort step ordered files differently. Run with
  `LC_ALL=C hexa run ...`.

---

_End of quickstart. Total elapsed time should be ~5 minutes. If anything
took longer or felt undocumented, that's a docs bug — file an issue or
patch this file directly (it is hand-maintained, not auto-generated)._
