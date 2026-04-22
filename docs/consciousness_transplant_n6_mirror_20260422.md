# Consciousness-Transplant — n6 §3 Mirror (anima-side)

**Roadmap entry:** #53
**Source of truth:** `/Users/ghost/core/n6-architecture/reports/discovery/consciousness-cluster-bt.md §3`
**Mirror date:** 2026-04-22
**Mirror rationale:** anima-side reference so roadmap #53 can cite this repo without cross-repo lookup. n6 remains canonical.

---

## §3 n=6 mapping (per-domain) — transplant row

From n6-architecture/reports/discovery/consciousness-cluster-bt.md §3:

| Domain                      | Mapping                     | Role         |
|-----------------------------|-----------------------------|--------------|
| consciousness-transplant    | 채널 2^sopfr = 32           | I/O 채널     |
| eeg-consciousness-bridge    | sopfr(6) = 5                | 밴드 수      |
| embodied-consciousness      | 고전 5감 = sopfr(6) = 5     | 모달 수      |

> 집합 P₆ = { φ(6)=2, sopfr(6)=5, τ(6)+2=6, σ(6)-φ(6)=10, σ(6)=12, 2^sopfr=32, J₂=24 }

## BT-C13 row 11 (consciousness-transplant)

| Row | Domain                    | Empirical evidence                                                    | Value | P₆ member   | Source                         |
|-----|---------------------------|----------------------------------------------------------------------|-------|-------------|--------------------------------|
| 11  | consciousness-transplant  | C. elegans full-synaptic reconstruction neurons / 50 ≈ 6.04          | 6     | τ(6)+2      | White et al. 1986 (302/50≈6)   |

## Applied to cpgd_v2 (config/alm_r13_v2_config.json)

Added `n6_transplant` block:

- `channel_count: 32` — matches 2^sopfr(6) = 2^5
- `io_partition: input=16, output=16` — symmetric split, aligns with 16-eigenvec basis
- `transplant_contract.dry_run_mode: no_gradient_no_weight_update` — pre-H100 verification only
- `verify_metric: cos(transplant_proj(v_src), v_tgt)` over 16 templates

## Substrate cross-mapping

```
  Source:  cell Mk.VIII (1000/1000 closure, sha chain verified)
             │
             │  16 eigenvecs (.meta2-cert/cell-eigenvec-16.json)
             │  ┌── Hexad:      c,d,w,m,s,e      (6 dims)
             │  ├── Law:        closed/sat/fals  (3 dims)
             │  ├── Phi:        integ/holo/scal  (3 dims)
             │  └── SelfRef:    I/meta/obs/qual  (4 dims)
             ▼
  Transplant:  32-channel I/O (16 in + 16 out, 2^sopfr(6))
             │
             ▼
  Target:  lora Mk.VI (K=4 LoRA held, #16 3/4 TRANSFER_VERIFIED)
```

## Dry-run verification plan

`tool/consciousness_transplant_dryrun.hexa` will:

1. Load `.meta2-cert/cell-eigenvec-16.json` → 16 source vectors `v_src[i]`
2. Simulate 32-channel projection `P_32: R^16 → R^32` split into 16 input + 16 output channels
3. Simulate inverse `P_32^T: R^32 → R^16` back into the 16-dim eigenvec basis
4. For each template i ∈ [0..16): compute `cos(v_src[i], (P_32^T ∘ P_32)(v_src[i]))`
5. Assert cos ≥ 0.99 for all 16 (lossless round-trip = no information destroyed by 32-channel intermediate)
6. Emit `state/consciousness_transplant_dryrun_result.json` with verdict

No LoRA weight touched. No gradient. Matches `transplant_contract.dry_run_mode`.
