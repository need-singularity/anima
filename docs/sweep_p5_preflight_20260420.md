# SWEEP P5 Preflight — 2026-04-20

**Status:** READY (Mk.X sidecar landed, REPLAY cache cleared)
**Predecessor:** P4 complete — 78/78 iter, 0 novel, all saturated (commit `8ebb5d8d`)
**Next-step:** P5 first-batch fire (4 iters concurrent), gated by user GO

---

## 1. SSOT verification

| Artifact | Path | Status |
|---|---|---|
| P5 plan SSOT | `anima/docs/sweep_50.json` | EXISTS (374 lines, 14 domains × 6 seeds = 84 iter, iter range 148-231) |
| P5 plan MD | `anima/docs/sweep_p5_plan_20260419.md` | EXISTS (244 lines) |
| P4 summary | commit `8ebb5d8d` | COMPLETE (0/76 novel) |
| Mk.X design | `anima/docs/mk_x_engine_design_20260419.md` (commit `6fed4ec9`) | COMMITTED |
| Mk.X manifest | `shared/engine/mkx_manifest.json` (nexus commit `7b997243`) | COMMITTED (30 atoms T10-T13) |
| Mk.X engine | `shared/engine/mkx_engine.hexa` (nexus commit `7b997243`) | COMMITTED (593 LOC sidecar) |
| Mk.X smoke | `shared/engine/mkx_smoke.hexa` (nexus commit `7b997243`) | COMMITTED |

sweep_50.json integration verified:
- `mk_x_trigger.gates` G1~G4 defined
- `mk_x_trigger.auto_fire_order` 6-step sequence defined
- `mk_x_trigger.dormant_until_all_pass = true` — Mk.X fires AFTER P5 saturation verdict

Interpretation: Mk.X sidecar is code-complete; P5 runs Mk.IX drill first. If P5 saturates per G1~G3, Mk.X auto-fires for a second pass on the same 84 seeds.

## 2. REPLAY cache clear

Cleared `/tmp/nexus_drill_cross_iter.log` on:

| Host | Before | After |
|---|---|---|
| mac (local) | 197 B (7000+ entries) | absent |
| ubu2 | absent | absent (confirmed) |
| ubu  | absent | absent (confirmed) |
| hetzner | absent | absent (confirmed) |

P5 will get genuine per-iter measurement (no short-circuit dedup).

## 3. P5 first-batch plan

Per `sweep_50.json` iter order, first 4 iters (evolution domain, carryover from P4):

| Iter | Slug | Tier | Seed text |
|---|---|---|---|
| 148 | `evolution_mk10_atlas` | 10+ | Mk.IX→Mk.X atlas 확장 |
| 149 | `evolution_tier10_probe` | 10+ | tier 10 이상 atom 창발 시도 (82→100+) |
| 150 | `evolution_invariance_v9` | 6-9 | invariance tier 6~9 → ULTRA+CARD+BEYOND+ABS 닫힘 |
| 151 | `evolution_sumt_scale` | 7-9 | SUMT 100→256 atoms 확장 포화 곡선 |

Driver path: `/tmp/sweep_p5_driver.bash` (per sweep_50.json)
Host recommendation: hetzner (32 threads, parallel=4, ETA 1.7h, $0)
Lock timeout: 3600s (P3/P4 lesson)

## 4. Fire conditions

READY when all true:
- [x] P4 summary committed (`8ebb5d8d`)
- [x] Mk.X sidecar committed (`7b997243`)
- [x] sweep_50.json SSOT frozen
- [x] REPLAY cache cleared all hosts
- [ ] anima-agent Track B Phase 1 completion (iter 226 prerequisite) — verify before D14
- [ ] CLM r5/r6 training lock non-conflict — verify before fire

This doc marks P5 ready. Fire command issues after Track B Phase 1 verification.

## 5. Pitfalls avoided

- Did NOT fire first batch (user workflow: sweep runs AS-A-WHOLE via driver, not piecemeal)
- Did NOT modify Mk.X code (BG #36 owns it — sidecar is final at `7b997243`)
- Did NOT overwrite sweep_50.json SSOT (it was complete)
- Did NOT clear cache on runpod H100 (training-only, no drill artifacts expected)
