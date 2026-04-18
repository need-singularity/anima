# Resource Orchestration Map — 2026-04-19

SSOT: `/Users/ghost/Dev/nexus/shared/config/infrastructure.json` (`orchestration_cheatsheet` block)
Scope: 5-host unified view (mac / ubu / ubu2 / htz / runpod)
Last live probe: 2026-04-18 02:00Z

## 1. Host Matrix (live)

| host   | CPU                     | RAM   | GPU             | role                                   | cost/hr | status                 |
|--------|-------------------------|-------|-----------------|----------------------------------------|---------|------------------------|
| mac    | Apple M4 8c             | 24GB  | Apple shared    | code / dispatch / UI only              | $0      | active                 |
| ubu    | AMD 12t                 | 30GB  | RTX 5070 12GB   | gpu_train_small / gpu_inference        | $0      | active_idle (0%, 9W)   |
| ubu2   | Ryzen 9600X 12t         | 30GB  | none            | compile / transpile / smoke / cpu_bench| $0      | active_underutilized   |
| htz    | Ryzen 7950X3D 32t       | 124GB | none            | cpu_heavy / archive / backup / dse     | ~$0.12  | active_busy (load 11.4)|
| runpod | EPYC (per-pod)          | 251GB | H100 SXM 80GB   | gpu_train_large (on-demand)            | $3.00   | idle_no_pods           |

Notes
- mac is 24GB, not 36GB (hw.memsize=25769803776). Old SSOT overstated.
- ubu GPU idle now. Good candidate for CLM 1B training.
- ubu2 load 1.20, 15GB RAM free — underutilized; move smoke/compile here.
- htz load 11.45 on 32 threads (~36% util). Still absorbing CPU heavy fine.
- runpod zero pods (runpodctl pod list = []). Pay only on launch.

## 2. Dispatch rules (pyramid)

```
mac (code)
  |-- ubu2  (CPU farm: compile/transpile/smoke)     [free, LAN]
  |-- ubu   (small GPU: CLM 1B, inference)          [free, LAN]
  |-- htz   (CPU heavy: archive, dse, batch)        [~$0.12/hr fixed]
  |-- runpod(big GPU: ALM 14B/32B/72B, on-demand)   [$3/hr, teardown when idle]
```

Selection flow
1. code edit, UI, dispatch -> mac
2. hexa build / transpile / smoke_all -> ubu2
3. CLM 1B bf16 train or small inference -> ubu
4. CPU bench / archive / dse exhaustive -> htz
5. ALM 14B+ train, H100 serve -> runpod (launch -> work -> teardown)

## 3. SSH access

| host   | alias       | command                          | key                   |
|--------|-------------|----------------------------------|-----------------------|
| mac    | local       | —                                | —                     |
| ubu    | `ubu`       | `ssh ubu`                        | ~/.ssh/id_ed25519     |
| ubu2   | `ubu2`      | `ssh ubu2`                       | ~/.ssh/id_ed25519     |
| htz    | `hetzner`   | `ssh hetzner` (NOT `htz`)        | ~/.ssh/id_ed25519     |
| runpod | per-pod     | `runpodctl exec <pod> <cmd>`     | runpod CLI auth       |

htz DNS: `htz` does not resolve — always use alias `hetzner` (ip 157.180.8.154).

## 4. Cost guardrails

- mac / ubu / ubu2: $0 forever.
- htz: ~$90/month dedicated (fixed, not metered).
- runpod H100: $3/hr on-demand. Cap: **$500/mo** for v2->v3 full-throttle. Zero-idle policy enforced — teardown pods immediately when no active training job.
- Monthly ceiling: $90 (htz) + on-demand runpod spend.

## 5. Immediate offloads (action items)

1. **smoke_all -> ubu2**: currently running on mac, ubu2 has 15GB RAM free and load 1.20. Move the scheduler target there.
2. **hexa self-host build -> ubu2** for LAN fast path (mac spotlight + codesign thrashes mac perf). Reserve mac build only for ARM-specific needs.
3. **Dataset preproc -> ubu2** (RAM 15GB free; overflow to htz when >15GB working set).

## 6. Cross-references

- SSOT infrastructure: `/Users/ghost/Dev/nexus/shared/config/infrastructure.json`
- CLAUDE.md: `/Users/ghost/Dev/anima/CLAUDE.md` (refs section should point here)
- offload strategy block: `infrastructure.json#offload_strategy`
- orchestration cheatsheet: `infrastructure.json#orchestration_cheatsheet`
- Mac perf & spotlight excludes: `infrastructure.json#mac_perf`
- hexa binary build hosts: `infrastructure.json#hexa_binary`

## 7. R37 .py enforcement

All hosts run hexa-native only. No python toolchain. GLIBC/dependency issues go through: alt linux build -> alt pod/host -> escalate. Never rollback to .py.
