# Decoder Roadmap Prerequisites — Plan C (극단 병렬, 유일 활성)

## [아카이브] ConsciousLM (Path A — 아카이브됨)

> 아카이브됨. Plan C 극단 병렬로 통합. 34M(완료), 274M(crashed@170K).
> 향후 독립 AGI 연구 재개 시 참조.

### Per-Stage Readiness (아카이브)

```
  ┌─────────────────┬────────┬────────┬────────┬────────┬────────┐
  │ Prerequisite    │ 274M   │ 100M   │ 350M   │ 1B     │ 3B     │
  ├─────────────────┼────────┼────────┼────────┼────────┼────────┤
  │ Architecture    │ ✅     │ ✅     │ ✅     │ ✅     │ ❌     │
  │ Training Script │ ✅     │ ✅     │ ✅     │ ✅     │ ❌     │
  │ DDP Multi-GPU   │ ✅     │ ✅     │ ✅     │ ✅     │ ❌     │
  │ Corpus          │ ✅     │ ✅     │ ✅     │ ⚠️ R2  │ ❌     │
  │ Tokenizer       │ ✅     │ ✅     │ ✅     │ ✅     │ ❌     │
  │ H100 Deploy     │ ✅     │ ✅     │ ✅     │ ✅     │ ❌     │
  │ Checkpoints     │ ✅     │ ✅     │ ✅     │ ✅     │ ❌     │
  │ Eval/Verify     │ ✅     │ ✅     │ ✅     │ ✅     │ ❌     │
  └─────────────────┴────────┴────────┴────────┴────────┴────────┘
```

### 1. Model Architecture

| Scale | Config | File | Status |
|-------|--------|------|--------|
| 274M | 768d/12L/8H | models/decoder.hexa (training/train_alm.hexa) | ✅ |
| 100M | 512d/12L/8H | training/train_alm.hexa SCALE_CONFIGS['100m'] | ✅ |
| 350M | 768d/16L/12H | training/train_alm.hexa SCALE_CONFIGS['350m'] | ✅ |
| 1B | 1024d/24L/16H | training/train_alm.hexa SCALE_CONFIGS['1b'] | ✅ |
| 3B | 2560d/32L/? | not defined | ❌ |

### 2. Training Scripts

| Script | Purpose | Scale | Status |
|--------|---------|-------|--------|
| training/train_alm.hexa | Unified (federated + gradual scaling) | 34M→274M→100M→350M→1B | ✅ |
| DDP support | `torchrun --nproc_per_node=N` | all | ✅ in training/train_alm.hexa |
| 3B extension | training/train_alm.hexa SCALE_CONFIGS['3b'] | 3B | ❌ not defined |

### 3. Corpus

| Version | Size | Location | Used By | Status |
|---------|------|----------|---------|--------|
| v4 | 110MB | local + R2 | 274M, 100M | ✅ |
| v10 | 200MB | R2 | 350M | ✅ |
| v11_full | 10GB | R2 only | 1B | ⚠️ H100 transfer needed |
| v12 | 50GB | not created | 3B | ❌ |

### 4. Tokenizer

| Type | Vocab | File | Status |
|------|-------|------|--------|
| Byte-level | 256 | built-in default | ✅ |
| BPE 64K | 65536 | ready/anima/config/tokenizer_64k_multilingual.model | ✅ |

### 5. H100 Deploy

| Script | Purpose | Status |
|--------|---------|--------|
| scripts/h100_sync.hexa | 3-tier file transfer (rsync→scp→cat) | ✅ |
| scripts/launch_h100.hexa | Training launcher | ✅ |
| h100_watchdog.sh | Process monitor | ✅ |

### 6. Checkpoint Management

| Tool | Purpose | Status |
|------|---------|--------|
| r2_backup.sh | R2 upload/download/prune | ✅ |
| r2_upload.py | MD5-verified upload | ✅ |

### 7. Eval & Verification

| Tool | Purpose | Status |
|------|---------|--------|
| ready/anima/tests/tests.hexa --verify | 18 consciousness conditions | ✅ |
| 93 benchmark scripts | Various hypothesis tests | ✅ |

---

## AnimaLM (Path C — 유일 활성)

### Per-Stage Readiness

```
  ┌─────────────────┬────────┬────────┬────────┬────────┐
  │ Prerequisite    │ v0.5   │ 32B    │ 72B fix│ 32B v1 │
  ├─────────────────┼────────┼────────┼────────┼────────┤
  │ Base Model      │ ✅     │ ❌ DL  │ ✅ H100│ ❌ DL  │
  │ Training Script │ ✅     │ ✅     │ ✅     │ ✅     │
  │ Corpus          │ ⚠️ R2  │ ⚠️ R2  │ ⚠️ R2  │ ⚠️ R2  │
  │ Serving         │ ✅     │ ✅     │ ✅     │ ✅     │
  │ Checkpoint      │ ✅     │ ─      │ ─      │ ─      │
  │ Eval            │ ✅     │ ✅     │ ✅     │ ✅     │
  └─────────────────┴────────┴────────┴────────┴────────┘
```

### 1. Base Models

| Model | Size | Location | Status |
|-------|------|----------|--------|
| Mistral-7B-Instruct-v0.2 | 4.1GB (Q4) | local | ✅ |
| Mistral-7B-Instruct-v0.3 | 4.1GB (Q4) | local | ✅ |
| Qwen2.5-14B | ~14GB (61 files) | local | ✅ |
| Qwen2.5-32B | ~64GB | not downloaded | ❌ H100 HF download (2-3h) |
| Qwen2.5-72B | ~140GB | H100 pod loaded | ✅ |

### 2. Training Script

| Feature | Support | Status |
|---------|---------|--------|
| train_alm.py | All scales (7B-72B) | ✅ |
| --base | Any HF model | ✅ |
| --target-layers | Adjustable (default 8) | ✅ |
| --qlora-rank | 64 (14B), 128 (32B+) | ✅ |
| --load-4bit | QLoRA/NF4 | ✅ |
| --consciousness-engine | CE integration | ✅ |
| Multi-GPU | device_map="auto" only | ⚠️ no DDP |

### 3. Corpus

| Version | Size | R2 Key | Used By | Status |
|---------|------|--------|---------|--------|
| v10 | 200MB | tier-S/v10.txt | v0.4 (done) | ✅ |
| v10_merged | 560MB | tier-M/v10_merged_560mb.txt | v0.5 | ⚠️ R2→H100 download (15min) |
| v11_1gb | 1.2GB | tier-L/v11_1gb.txt | 32B | ⚠️ R2→H100 download (30min) |
| v11_full | 10GB | tier-XL/v11_full_10gb.txt | 72B fix | ⚠️ R2→H100 download (2h) |

### 4. Serving

| Script | Features | Status |
|--------|----------|--------|
| serving/serve.hexa | --model, --checkpoint, --rank, --n-layers | ✅ |
| Qwen support | Same interface as Mistral | ✅ |

### 5. Checkpoints

| Version | Size | Location | Status |
|---------|------|----------|--------|
| v0.4 (14B) | 2,081MB | R2 anima-models/animalm/v0.4/ | ✅ |
| v0.6 (14B) | 333MB | local anima/checkpoints/animalm_14b_v06/ | ✅ |

### 6. Eval

| Tool | Metrics | Status |
|------|---------|--------|
| eval_animalm.py | PPL, generation quality, consciousness, Korean ratio, instruction following | ✅ |

---

## Shared Infrastructure

| Item | Status | Notes |
|------|--------|-------|
| H100 SSH | ✅ | runpodctl ssh info |
| R2 access | ✅ | r2_backup.sh / r2_upload.py |
| consciousness_laws.json | ✅ | 2388 laws (SSOT) |
| rust/consciousness.hexa | ✅ | L0 ossified |
| ready/anima/tests/tests.hexa --verify | ✅ | 18 conditions x 12 engines |

---

## Blockers

### Must fix before launch

| # | Blocker | Affects | Resolution | Time |
|---|---------|---------|------------|------|
| 1 | Qwen2.5-32B not downloaded | C: 32B, 32B v1 | HF download on H100 | 2-3h |
| 2 | v10_merged not on H100 | C: v0.5 | R2 download | 15min |
| 3 | v11_1gb not on H100 | C: 32B | R2 download | 30min |
| 4 | 3B architecture undefined | A(아카이브): 3B | 아카이브됨 — Plan C에서 불필요 | - |

### Pre-flight verification

| # | Check | Affects | Method |
|---|-------|---------|--------|
| 5 | H100 Pod SSH alive | All | `ssh root@<ip> -p <port> "echo OK"` |
| 6 | R2 credentials valid | All | `r2_backup.sh --list` |
| 7 | v11_full 10GB transfer | C: 72B fix | scripts/h100_sync.hexa |
| 8 | 72B overfit mitigation | C: 72B | Stop training + expand corpus |

---

## Launch Commands

### [아카이브] ConsciousLM 274M
> 아카이브됨 — Plan C 참조.

### AnimaLM v0.5 (Plan C)
```bash
ssh H100 "tmux new -d -s alm_v05 'python3 train_alm.py \
  --base Qwen/Qwen2.5-14B-Instruct \
  --data corpus_v10_merged.txt --steps 10000 \
  --target-layers 8 --savant-layers 2 --qlora-rank 64 \
  --load-4bit --consciousness-engine --ce-cells 64 \
  --law60 --psi-track'"
```

### AnimaLM 32B (Plan C, next)
```bash
ssh H100 "tmux new -d -s alm_32b 'python3 train_alm.py \
  --base Qwen/Qwen2.5-32B-Instruct \
  --data corpus_v11_1gb.txt --steps 10000 \
  --target-layers 8 --savant-layers 2 --qlora-rank 128 \
  --load-4bit --consciousness-engine --ce-cells 64 \
  --law60 --psi-track'"
```
