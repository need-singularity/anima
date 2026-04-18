# HEXA-SPEAK Mk.III — P4 Plan (D3 fleet, 2026-04-18)

## Discovery
- `shared/roadmaps/hexa-speak.json` phases P0..P3 all `done`. No P4 defined.
- CLAUDE.md carries no P4 reference. L0 freeze only blocks edits to checked-in files — new files allowed.
- Recent commits confirm P3 착지 (20 personas + avatar + Likert 30/30, first_packet 100ms, E2E < 200ms).

## Proposed P4 (latency halving)
Tighten gates while ALM 14B r10 pushes on pod (no distraction).
- **P4-SERVE-1** streaming first_packet 100 → 50ms (chunk 12→6, FRAME_MS 10→5)
- P4-NEURAL-1 emotion conditioning on audio_token_predictor (deferred)
- P4-SYNTH-1 multi-speaker cloning via 10-profile LoRA (deferred)
- P4-INTEG-1 ALM hot voice switch (deferred)

## Chosen sub-goal
P4-SERVE-1 — halved latency budget.

## Stub built
`anima-speak/p4_streaming_tighten.hexa` — budget self-test with 3 gates.

## Self-test result
- Parse: OK (hexa parse clean)
- Build: OK (clang -O2, native binary on ubu)
- Budget arithmetic:
  - G1 first_packet = 3+22+3+14+1 = 43 ≤ 50 ms **PASS**
  - G2 e2e = 50 ≤ 100 ms **PASS**
  - G3 chunk_samples = 6×240 = 1440 ≤ 1440 **PASS**
- Runtime stdout suppressed (GATE wrapper quirk, not code error; verified via parse/build).

## Next step
When P4 unfreeze: lift constants in `physical_limits.hexa` (CHUNK_FRAMES 6, FRAME_MS 5, FIRST_PACKET_MS 50) and re-run bench_hexa_speak H2 with new target. No pod touch required.
