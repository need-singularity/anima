# CLM r4 Pod3 Teardown — 20260418T165813Z

## Pod Identity
- **ID**: `pvref8zw70kv1z`
- **Name**: anima-clm1b-r4-pod3
- **GPU**: 1× H100 SXM
- **Image**: runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
- **SSH**: `root@64.247.201.53:10051`

## Lifecycle
- **Launch**: 2026-04-18 15:09 UTC
- **Teardown**: 2026-04-18 16:58 UTC
- **Total uptime**: 1h 49m (1.817h)
- **Rate**: $2.99/hr
- **Total cost**: **$5.43**

## Teardown Sequence
1. `runpodctl pod list` → RUNNING confirmed
2. `ssh ... 'tmux kill-session -t clm-r4-hexa; pkill -f clm_r4_native'` → done
3. `runpodctl pod stop pvref8zw70kv1z` → stopped
4. `runpodctl pod delete pvref8zw70kv1z` → removed
5. `runpodctl pod list` → `[]` (gone, burn halted)

## 9-Fire Journey Summary
- 1st–5th fire: path/env debugging (launcher, TOKENIZERS_PARALLELISM, tmux wrapper)
- 6th fire: hexa compile errors — nn_core import fail, `match` reserved word trap
- 7th fire: H1 fix (inline NN primitives), array-assign silent no-op → write_at()
- 8th fire: H2/H3 fix — tensor init + loss path
- 9th fire: **native compile SUCCESS** but CPU-only execution, no GPU kernel dispatch → auto-kill after 60s idle, ckpt=0

## Knowledge Captured
- **WIN**: hexa native compile path working end-to-end on H100 pod (H1/H2/H3 fixes validated)
- **BLOCKER**: hexa runtime lacks GPU kernel dispatch — CUDA calls route to CPU fallback silently
- **NEXT PATH**: ubu / ubu2 CUDA lane (hxcuda build on RTX 3090 recipe, then H100 lease)
- **COST**: $5.43 sunk for CPU-verify-only; $71.76/day idle policy enforced via immediate teardown

## Artifacts
- **Checkpoints**: none (0 steps completed)
- **R2 backup**: n/a
- **Logs**: local tmux log only (pod gone)

## ubu/ubu2 Migration Checklist
- [ ] Confirm hxcuda source tree present in /Users/ghost/Dev (or nexus hexa-lang repo)
- [ ] Launch RTX 3090 COMMUNITY pod per `reference_hexa_c4_launch.md` for hxcuda build
- [ ] Verify GPU kernel dispatch (sm_80/sm_90 smoke test) BEFORE H100 relaunch
- [ ] Re-port clm_r4_native.hexa to call hxcuda primitives explicitly
- [ ] Dry-run 1-step forward+backward on 3090, confirm GPU util >0
- [ ] Lease H100 only after 3090 validates — no speculative burn
- [ ] Set 60s idle auto-kill + R2 ckpt-save cadence before tmux fire
