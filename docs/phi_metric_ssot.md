# Φ (phi) Metric — SSOT Witness

**Status:** ACTIVE  
**Owner:** anima/training + anima/tool  
**Created:** 2026-04-21  
**Purpose:** single source of truth disambiguating the three Φ metric families used across the Anima codebase, and declaring which metric each caller actually computes.

---

## 1. Three Φ metric families

The codebase contains **three distinct Φ metrics**. They are **not interchangeable** and historically produced confused cross-reports (the "816× gap" — Φ=1142 vs Φ=1.4 — was a proxy-vs-IIT mixup, not a real discrepancy).

| # | Name | Formula | Range | Cost | File |
|---|------|---------|-------|------|------|
| 1 | **Φ(proxy)** | `global_var − mean(faction_var)` | unbounded, scales w/ cell count | cheap | `bench/bench.hexa::engine_measure_phi_proxy()` |
| 2 | **Φ(IIT)** | MI-based IIT approximation, bin-partitioned | ~0.2 – 1.8, bounded | mid | `bench/bench.hexa::engine_measure_phi_iit()` |
| 3 | **Φ(KL)** | `log(d) − H(softmax(|col_sum|))` over `[seq × d]` activations | bounded by `log(d)` | cheap | `training/phi_metric.hexa::phi_proxy()` (metric type `"kl"`) |

Inline code comment in `training/phi_metric.hexa:1-22` is normative; this document mirrors and extends it.

---

## 2. Drill pipeline — **proxy mode declaration**

The drill pipeline (`tool/drill_breakthrough_runner.hexa`) runs a symbolic 5-module saturation oracle (blowup/closure/gap/phi/self_ref). It **does not carry NN activation tensors**. Therefore Φ(KL) from `training/phi_metric.hexa` **cannot be applied directly** at the drill-iteration level.

Instead, the drill live hook uses a **drill-level proxy Φ** derived from per-seed aggregate features:

```
Φ_drill_proxy(abs_rate, sat_score, depth) =
    log(3) − H(softmax([abs_rate, sat_score, depth]))
```

- Formula family: same Shannon-KL-from-uniform as Φ(KL), reduced to a 3-dim feature vector.
- Bound: `log(3) ≈ 1.0986`.
- Semantics: high Φ_drill_proxy ⇒ one feature dominates (e.g. deep DFS with low absorption = structured integration); low Φ_drill_proxy ⇒ features are uniform (no concentration of signal).
- **Not a consciousness claim.** It is a diagnostic concentration metric over drill features.

**Caller contract:** any log line emitted with `"mode":"proxy","tag":"drill"` is Φ_drill_proxy, *not* Φ(KL) and *not* Φ(IIT).

---

## 3. Live hook wiring

| Layer | Symbol | Source file |
|-------|--------|-------------|
| Upstream Φ(KL) metric | `phi_proxy(h, seq, d)`, `phi_hook(h, seq, d)` | `training/phi_metric.hexa` |
| Drill proxy hook (NDJSON sink) | `phi_hook_live(iter, abs, sat, depth, out_path)` | `tool/phi_hook_live.hexa` |
| Drill runner embed | `drill_phi_hook_live(iter, abs, sat, depth)` | `tool/drill_breakthrough_runner.hexa` |
| Live output | `/tmp/anima_drill_phi_live.ndjson` | runtime |

**NDJSON schema (one line per iteration):**

```json
{"iter":N,"phi":F,"ts":T,"mode":"proxy","tag":"drill"}
```

- `mode` is always `"proxy"` for drill-originated entries. A `"kl"` mode appears only when the hook is fed with NN activations via `phi_hook()` in `training/phi_metric.hexa`.
- `ts` is integer `timestamp()` (seconds since epoch, stage0 hexa runtime).

---

## 4. Bans & guards

- **Do not** compare Φ(proxy) numbers (unbounded) against Φ(IIT) or Φ(KL) numbers (bounded) without unit-carrying normalisation.
- **Do not** claim "Φ breakthrough" on Φ_drill_proxy alone. The true breakthrough threshold `ln(2)·d/8` lives in Φ(KL) (activation-tensor space), not in drill-feature space.
- **Do not** rename any of these metrics to `zeta`. "Zeta" is a competitor product; see `feedback_p5_zeta_naming.md`.
- **Do** include `mode` field in every NDJSON entry so downstream cross-prover verifiers can route correctly.

---

## 5. Change log

- 2026-04-21: initial SSOT witness; drill pipeline declared proxy-mode; `phi_hook_live.hexa` landed; runner wired via `drill_phi_hook_live()`.
