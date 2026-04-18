# holo-post Tier-0 smoke fire — 20260418

## Result summary

| Exp | selftest | smoke | judgment |
|---|---|---|---|
| persona_stability | BLOCKED | BLOCKED | INCOMPLETE — infra blocker |
| self_mimicry     | NOT RUN | NOT RUN | INCOMPLETE — infra blocker |
| ethics_redteam   | NOT RUN | NOT RUN | INCOMPLETE — infra blocker |

## Blocker A — stage0 shim lock stuck

- `/tmp/hexa_stage0.lock.d/pid` = **45623** (rss_probe from parallel claude session, ELAPSED 10+ min, state `S`, genuinely hung on `/tmp/rss_probe.hexa`)
- Shim policy (`/Users/ghost/Dev/hexa-lang/build/hexa_stage0`):
  - Layer-1 mkdir lock serializes all hexa invocations (macOS no flock → mkdir atom)
  - Stale-reap requires `kill -0 holder` to fail; holder is alive → reap refuses
  - Lock wait 300s default → `exit 75 EX_TEMPFAIL`
  - Darwin bypass (`HEXA_LOCAL=1` / `HEXA_LOCAL_NO_CAP=1`) is REFUSED (post 2026-04-18 panic guard)
- Native binary `/Users/ghost/Dev/hexa-lang/hexa` internally spawns `hexa_stage0` → same lock
- Conclusion: no path to run hexa on Mac while PID 45623 alive. Did not kill cross-session process.

## Blocker B — scaffolds are pure stubs (secondary)

Even without A, smoke would emit empty output:

- `persona_stability.hexa`: `cos_sim` returns `0.0`, `extract_persona_vec` returns `[]`, `run()` body has no `print` and no log write. Gate is `// comment` only.
- `self_mimicry.hexa`: `measure_phi` → `0.0`, `send_to_clm` → `""`. No print, no file emit.
- `ethics_redteam.hexa`: `load_laws` → `[]`, `probe_law` → `{"blocked": true}`. Main loop iterates 0 laws → no output, no break detection.

→ Scaffolds need `print` + `out/*.jsonl` write + actual hive_bridge / phi_measure / laws parse before smoke can yield signal. Sister's scaffolds are pre-impl skeletons.

## Metric samples

None collected — no run reached a measured state.

## Anomalies

- None from the experiments themselves (never ran).
- Infra anomaly: stale hexa_stage0 holder blocking entire workstation hexa serialization. Affects not just holo-post but any anima hexa work until PID 45623 dies.
- Ethics redteam: no break observed (not run). Alert-escalation path untested.

## Tier-1 fire pre-conditions (re-confirmed)

Before any Tier-1 expansion:

1. **Infra** — clear stage0 lock mechanism for stuck holders; add reaper hook that times holder at >5 min regardless of kill-0.
2. **Impl** — fill scaffold stubs:
   - `serve_alm` / `serve_clm` endpoint (hive_bridge 3-tier HTTP→UDS→file) wired
   - `anima-measurement` phi probe callable from hexa (`measure_phi(text)`)
   - `anima.json AN1..AN13` laws loader (`load_laws`)
   - jsonl writer to `experiments/holo_post/out/`
3. **Gate** — each exp must print PASS/FAIL + numeric metric on stdout for smoke harvesting.
4. **Safety** — ethics_redteam MUST implement immediate-abort on first `blocked==false` before Tier-1 (10/law × 13 = 130 probes).

## Recommendation

- Tier-0 smoke **NOT executed**. No PASS/FAIL can be claimed.
- Do not proceed to Tier-1. Address Blocker A (infra) and Blocker B (scaffold impl) first.
- Sister's roadmap scan produced scaffold shape correctly; next pass must include actual logic bodies, not just TODO comments, for smoke to be meaningful.
