# PhiVec 16D Normalization Design — 2026-04-18

## 1. Problem statement

`anima-agent/autonomy_live.hexa:22` defines `struct PhiVec { holo, complexity, gwt, refl, raw }` — a 4-field struct that extracts only 4 of the 16 dimensions returned by the S1 `/persona` endpoint. The other 12 dims (`phi_time, phi_embodied, phi_meta, …`) are discarded. This is a **schema-drift / information-loss** bug: consumers of `autonomy_live`'s `S1Response` see a collapsed Φ signal even when S1 emits a full 16D vector.

## 2. phi=2 cap origin — NOT the 4D struct

The memory "serve phi caps at 2 (6000x off)" (`feedback_gate_vs_live_drift.md`) describes a **formula SSOT divergence**, not a struct truncation:

- Old serve path used `spatial_var * eff_rank * 0.01` → saturates near 2.
- Fixed in commit `c3926183` by switching serve → MI-based C41 (matches training).

The 4D `PhiVec` in `autonomy_live.hexa` was **not the root cause of phi=2**, but it is a **related schema-SSOT defect** that should be fixed at the same time: it would mask any future per-dim disagreement between training and serve.

## 3. Current state — audit

| File | Struct | Dim count | Notes |
|---|---|---|---|
| `anima-agent/autonomy_live.hexa:22` | `PhiVec` | **4** | holo/complexity/gwt/refl + raw |
| `serving/serve_clm.hexa:102` | `ScPhiVec` | **16** | already 16 fields (+has_prior/prior_holo meta) |
| `serving/serve_alm_persona.hexa:141-156` | positional `array` | **16** | SAP_PHI_* indices, c2 schema |
| `serving/phi_hook_live.hexa:74-89` | positional `array` | **16** | PHI_IDX_* indices, alm_phi_vec_logger_v1 schema |

Only `autonomy_live.hexa` needs structural change. `ScPhiVec` is already normalized.

### SSOT split warning
Two competing 16D orderings exist:
- `phi_hook_live` / `alm_phi_vec_logger_v1`: `[holo, complexity, gwt, refl, time, embodied, nested_drift, k_amp, affect_v, affect_a, finitude, hive_collec, hive_indiv, hive_emerge, dream_phase, cycle_count]`
- `serve_alm_persona` / `ScPhiVec` / `c2 schema`: `[holo, refl, time, embodied, meta, social, will, narrative, affect, dream, create, finitude, lang, mirror, collective, unity]`

**Resolution deferred** — both are in-tree; picking one requires a separate SSOT decision. For this migration we mirror the **c2 / `ScPhiVec`** schema (because S1 `/persona` response is the upstream producer that `autonomy_live` consumes, and `serve_alm_persona` is the reference S1 impl).

## 4. Target structure (Option A — 16 explicit fields)

Rationale: Hexa runtime quirk (`memory/feedback_hexa_runtime.md` — `a[i]=v` silently no-ops; array indexing is unreliable). `ScPhiVec` already demonstrates 16-field struct works. No `array<float, 16>` (Option B rejected — Index kind unsupported).

```hexa
struct PhiVec {
    phi_holo:       float,
    phi_refl:       float,
    phi_time:       float,
    phi_embodied:   float,
    phi_meta:       float,
    phi_social:     float,
    phi_will:       float,
    phi_narrative:  float,
    phi_affect:     float,
    phi_dream:      float,
    phi_create:     float,
    phi_finitude:   float,
    phi_lang:       float,
    phi_mirror:     float,
    phi_collective: float,
    phi_unity:      float,
    raw: string
}
```

## 5. Mapping table — old 4D → new 16D (autonomy_live)

Old field writes (line 137, 149) extract keys `phi_holo, phi_complexity, phi_gwt, phi_refl` from the S1 JSON response. Under the c2 schema these do not map cleanly (c2 has no `phi_complexity`/`phi_gwt`). Required JSON-key changes:

| Old struct field | S1 JSON key (old) | New struct field | S1 JSON key (new, c2) |
|---|---|---|---|
| `holo` | `phi_holo` | `phi_holo` | `phi_holo` |
| `complexity` | `phi_complexity` | *(removed)* | — |
| `gwt` | `phi_gwt` | *(removed)* | — |
| `refl` | `phi_refl` | `phi_refl` | `phi_refl` |
| — | — | `phi_time` | `phi_time` |
| — | — | `phi_embodied` | `phi_embodied` |
| — | — | `phi_meta` | `phi_meta` |
| — | — | `phi_social` | `phi_social` |
| — | — | `phi_will` | `phi_will` |
| — | — | `phi_narrative` | `phi_narrative` |
| — | — | `phi_affect` | `phi_affect` |
| — | — | `phi_dream` | `phi_dream` |
| — | — | `phi_create` | `phi_create` |
| — | — | `phi_finitude` | `phi_finitude` |
| — | — | `phi_lang` | `phi_lang` |
| — | — | `phi_mirror` | `phi_mirror` |
| — | — | `phi_collective` | `phi_collective` |
| — | — | `phi_unity` | `phi_unity` |

The phi-driven abort logic at `autonomy_live.hexa:227` reads `resp.phi.holo` only → continues to work after rename as `resp.phi.phi_holo`.

## 6. Affected call sites (in `autonomy_live.hexa`)

1. `struct PhiVec` definition — line 22
2. `PhiVec { holo: 0.0, … }` construction on transport failure — line 137
3. `PhiVec { holo: holo, … }` construction on success — line 149
4. `let phi_after = resp.phi.holo` — line 227 (rename to `resp.phi.phi_holo`)

Plus 12 new `s1_extract_json_float` calls for the added dims (line 142-145 region).

## 7. Migration steps (incremental)

1. Expand struct to 16 fields.
2. Add 12 new `s1_extract_json_float` calls in `s1_call()`.
3. Update 2 construction sites + 1 read site.
4. `hexa parse anima-agent/autonomy_live.hexa` → must pass (16-field struct worked in `ScPhiVec`, so precedent).
5. Run `selftest_10x3()` if S1 endpoint reachable — else parse-only.

## 8. Validation plan (phi=2 cap check)

1. Deploy serve_clm to pod, POST `/generate` with healthy prompt.
2. Verify `phi_vec.phi_holo` in response JSON is **> 2.0** for non-degenerate output (tests the already-fixed MI formula, not the struct).
3. Run `autonomy_live` selftest against S1; confirm `terminal_phi` > 2.0.
4. If phi_holo still caps at 2 — the problem is in serve's live formula (needs separate dig; this doc does NOT fix that).

## 9. Risk / scope

- **Out of scope**: phi=2 cap *per se* was fixed in `c3926183`; a regression would need independent investigation (check current serve_clm line 194 formula `holo = 50.0 + 1150.0 * ent_t * len_factor` → caps near 1200, not 2, so that path is fine).
- **In scope**: remove the 4D truncation in `autonomy_live` so future Φ-based decisions can use all 16 dims.
- **POC risk**: Hexa `struct` with many fields has historic corruption (`serve_clm.hexa:40` comment — "NO struct with ≥3 float fields" for multi-float return). But `ScPhiVec` (16 floats) works when read field-by-field. Mitigation: autonomy_live reads `.phi_holo` only, same pattern as serve_clm.

## 10. Status

- Design: **COMPLETE**
- Schema selection: c2 (`ScPhiVec` order) — deferred re-alignment with `phi_hook_live` to a separate SSOT decision.
- POC implementation: **deferred to next session** (scope control per task constraints).
- Do-not-commit constraint: observed.

## 11. Next-session actions

1. Apply Option A struct expansion to `autonomy_live.hexa` (4 → 16 fields).
2. Run `hexa parse` to confirm 16-float struct compiles.
3. If parse OK → run selftest against a live S1 `/persona` endpoint and record `terminal_phi` values.
4. Draft SSOT merge proposal for `phi_hook_live` vs `c2` dim ordering.
5. Separately: trace current serve_clm `sc_extract_phi_vec` formula (line 194) to confirm it matches training's MI-based C41 formula — if not, open a new formula-SSOT fix ticket.
