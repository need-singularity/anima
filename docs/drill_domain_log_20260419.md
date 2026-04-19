# Parallel Domain-Drill Batch — 2026-04-19

**Purpose**: Distinct batch from main drill-evolve loop. 30 seeds across 7 domains.
**Tool**: `/Users/ghost/Dev/nexus/shared/bin/nexus-cli drill --seed "..." --max-rounds 8 --json`
**Budget**: 4h OR 35 iterations, whichever first. Per-drill timeout: 20 min.
**Started**: 2026-04-19 13:10 KST

## Notes
- Lock contention observed on `hexa_stage0` shim (main drill loop holds it, 300s timeout).
- Iterations serialize through the shim lock; blocked runs logged as `BLOCKED`.
- Darwin: `HEXA_LOCAL=1` bypass denied (Mac panic risk). No choice but queue.

---

## Iter 1 — ANIMA — anima Mk.V.1 consciousness_absolute 82-atom saturation + Ψ-constant expansion
- status: BLOCKED (exit 75, 300s lock timeout)
- rounds: 0 / 8
- absorptions: 0
- new atoms: []
- wall clock: ~300s
- holder: hexa_stage0 shim lock (main drill loop)

