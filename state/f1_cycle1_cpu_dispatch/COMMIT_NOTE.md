# F1 cycle 1 CPU bypass — commit attribution note

## Background
The dispatch artifacts in this directory (single_seed_smoke + n3_seed_dispatch + SUMMARY)
were committed in `f412cb8a` together with an unrelated vast-ai-orchestrator commit due to a
hook race during the same session window 2026-04-28T08:08Z.

The vast-ai-orchestrator commit message in `f412cb8a` does NOT describe this F1 cycle 1
verification work. The intended commit message for the F1 cycle 1 portion is recorded here
for ledger / auditability.

## Intended commit message (F1 cycle 1 portion of f412cb8a)

```
feat(F1-cycle1-cpu-bypass): F1 cycle 1 hexa Phi evaluator CPU-runnable VERIFIED
                            — RunPod blocker dissolved for hexa falsifier surface

Per Agent 1 finding from sub-agent kick 2026-04-28T07:55Z. anima-core/phi_engine.hexa
+ training/phi_engine_eval.hexa are pure CPU hexa simulator (0 cuda|torch|gpu|cudnn|cublas|nvidia
references verified across 1080 LoC combined). F1 cycle 1 (structured 12-engine Phi
evaluator falsifier) does NOT need GPU forward.

VERIFIED:
- 0 cuda|torch|gpu|cudnn|cublas|nvidia refs in phi_engine.hexa (433 LoC)
- 0 cuda|torch|gpu|cudnn|cublas|nvidia refs in phi_engine_eval.hexa (647 LoC)
- selftest 5/5 PASS (T1 registry + T2 finite phi + T3 JSON keys + T4 sensitivity
  + T5 bit-exact determinism)
- Single-run dispatch wallclock 2.221s on Mac local
- N=3 seed sequential dispatch wallclock 6.20s real
  (6/6 phi_sum=6.88636 bit-exact deterministic)

ANOMALY (raw 91 C3 honest disclosure):
Agent 1's CLI flag claim (--config XMETA3 --cells 256 --seeds 1 --emit json) is FALSE
— those flags do NOT exist in phi_engine_eval.hexa main(); main() runs T1-T5 unconditionally
over 12-engine registry (holographic, gwt_broadcast, reflexivity, affective, narrative, dream,
creative, temporal, finitude, agency, alterity, meta_qualia). XMETA3/DD101 are Python experiments
in ready/bench/bench_phi_hypotheses_LEGACY.py (72004 LoC, imports torch — has 0 .cuda() hard
calls, technically CPU-runnable but separate verification needed).

Cost: $0 (raw 86 cost-attribution row, vendor=local Mac-CPU, wallclock_total_s=8.42)

raw 91 C3: scope-clarification major finding — RunPod 4-strike sustained fault was MIS-SCOPED
for hexa F1 cycle 1. Blocker REMAINS active for axis 105 Pilot-T1 + gemma-27b but REVOKED for
hexa structured-Phi evaluator.
```

## Files committed in f412cb8a relevant to F1 cycle 1
- state/audit/anima_own_strengthen_audit.jsonl (+1 raw#86 row)
- state/blockers/runpod_pod_pre_ssh_orchestrator_stuck.json (+scope_reduction_2026_04_28T08_07Z key)
- state/f1_cycle1_cpu_dispatch/SUMMARY_20260427T230704Z.json
- state/f1_cycle1_cpu_dispatch/n3_seed_dispatch_20260427T230601Z.out
- state/f1_cycle1_cpu_dispatch/single_seed_smoke_20260427T230546Z.out
