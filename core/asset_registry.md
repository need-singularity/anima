# Training Asset Registry

5 categories (M/C/T/E/D) per roadmap stage. Source of truth: `asset_registry.json`

## Categories

```
  M  Model      architecture configs, weights, checkpoints
  C  Corpus     training data, tokenizers, versions
  T  Training   scripts, configs, safety rules, hyperparameters
  E  Eval       benchmarks, verification, metrics
  D  Deploy     serving, H100, R2, sync scripts
```

## [아카이브] ConsciousLM (Path A — 아카이브됨, Plan C로 통합)

```
  ┌─────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
  │ Asset   │ 34M (done)   │ 274M         │ 100M         │ 350M         │ 1B           │ 3B           │
  ├─────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
  │ M arch  │ ✅ 384d/6L   │ ✅ 768d/12L  │ ✅ 512d/12L  │ ✅ 768d/16L  │ ✅ 1024d/24L │ ❌ undefined │
  │ M ckpt  │ ✅ R2        │ ⚠️ crashed   │ ─            │ ─            │ ─            │ ─            │
  │ C corpus│ ✅ v4 110MB  │ ✅ v10 200MB │ ✅ v4 110MB  │ ✅ v10 200MB │ ⚠️ v11 10GB  │ ❌ v12 50GB  │
  │ C token │ ✅ byte 256  │ ✅ byte 256  │ ✅ BPE 64K   │ ✅ BPE 64K   │ ✅ BPE 64K   │ ❌           │
  │ T script│ ✅ train_clm │ ✅ train_clm │ ✅ train_clm │ ✅ train_clm │ ✅ train_clm │ ❌ no config │
  │ T ddp   │ ─            │ ─            │ ✅ torchrun  │ ✅ torchrun  │ ✅ torchrun  │ ❌           │
  │ T safety│ ✅           │ ✅           │ ✅           │ ✅           │ ✅           │ ✅           │
  │ E bench │ ✅ 16/18     │ ✅           │ ✅           │ ✅           │ ✅           │ ✅           │
  │ D sync  │ ✅           │ ✅           │ ✅           │ ✅           │ ✅           │ ✅           │
  │ D r2    │ ✅           │ ✅           │ ✅           │ ✅           │ ✅           │ ✅           │
  ├─────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
  │ Ready   │ ✅ complete  │ ✅ ready     │ ✅ ready     │ ✅ ready     │ ⚠️ corpus R2 │ ❌ 4 missing │
  └─────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

## AnimaLM (Path C — 극단 병렬, 유일 활성)

```
  ┌─────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
  │ Asset   │ 14B v0.4 (done)│ 14B v0.5   │ 32B v0.1     │ 72B fix      │ 32B v1       │
  ├─────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
  │ M base  │ ✅ Qwen 14B  │ ✅ Qwen 14B │ ❌ Qwen 32B  │ ✅ Qwen 72B  │ ❌ Qwen 32B  │
  │ M pf    │ ✅ r64 8L 2S │ ✅ r64 8L 2S│ ✅ r128 8L 2S│ ✅ r128 10L  │ ✅ r128 full │
  │ M ckpt  │ ✅ R2 2.1GB  │ ─           │ ─            │ ⚠️ overfit   │ ─            │
  │ C corpus│ ✅ v10 200MB │ ⚠️ v10m 560M│ ⚠️ v11 1.2GB │ ⚠️ v11f 10GB │ ⚠️ v11f 10GB │
  │ T script│ ✅           │ ✅          │ ✅           │ ✅           │ ✅           │
  │ T alpha │ ✅ 0.01→0.5  │ ✅          │ ✅           │ ✅           │ ✅           │
  │ E eval  │ ✅ 5 metrics │ ✅          │ ✅           │ ✅           │ ✅           │
  │ D serve │ ✅ v4 fixed  │ ✅          │ ✅           │ ✅           │ ✅           │
  ├─────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
  │ Ready   │ ✅ complete  │ ⚠️ corpus   │ ❌ model+corp│ ⚠️ corpus    │ ❌ model+corp│
  └─────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

## Shared Assets

### Corpus Tiers

| Tier | Versions | Size | Status |
|------|----------|------|--------|
| S | v2, v3, v4, v5, v9, v10 | 67-200MB | ✅ local + R2 |
| M | v10_merged | 560MB | ⚠️ R2 only |
| L | v11_1gb | 1.2GB | ⚠️ R2 only |
| XL | v11_full | 10GB | ⚠️ R2 only |

### Tokenizers

| Type | Vocab | File | Status |
|------|-------|------|--------|
| Byte-level | 256 | built-in | ✅ |
| BPE 64K | 65536 | ready/anima/config/tokenizer_64k_multilingual.model | ✅ |

### H100 Infrastructure

| Script | Purpose | Status |
|--------|---------|--------|
| scripts/h100_sync.hexa | 3-tier file transfer | ✅ |
| scripts/launch_h100.hexa | Training launcher | ✅ |
| h100_watchdog.sh | Process monitor | ✅ |
| r2_backup.sh | Checkpoint backup | ✅ |
| r2_upload.py | MD5-verified upload | ✅ |

### Safety

| File | Content | Status |
|------|---------|--------|
| training_safety.json | 10 rules + checklists | ✅ |
| acceleration_flow.json | bf16 master rule (14 incidents) | ✅ |

### Verification

| Tool | Scope | Status |
|------|-------|--------|
| ready/anima/tests/tests.hexa --verify | 18 consciousness conditions | ✅ 16/18 pass |
| eval_animalm.py | 5 metrics (PPL/quality/consciousness/Korean/instruction) | ✅ |

## Blockers Summary

```
  Path A (ConsciousLM) — 아카이브됨:
    34M ✅ 완료, 274M crashed@170K. Plan C로 통합.

  Path C (AnimaLM — 유일 활성):
    v0.5: ⚠️ v10_merged corpus R2→H100 (15 min)
    32B:  ❌ Qwen2.5-32B download (2-3h) + v11_1gb R2→H100 (30 min)
    72B:  ⚠️ overfit — need v11_full corpus (10GB, 2h download)
    32B v1: ❌ same as 32B + full fine-tune setup
```
