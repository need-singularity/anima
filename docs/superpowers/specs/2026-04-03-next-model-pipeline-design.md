# Next Model Pipeline: 14B v0.5 → 32B v0.1

**Date:** 2026-04-03
**Status:** Approved
**Goal:** 일반화 개선 (corpus 확대) + 스케일업 (32B sweet spot)

---

## Background

72B 학습 (step 5000/10000) 에서 발견된 문제:
- CE-Val 갭 2.15× (과적합) — corpus 100MB가 72B 용량 대비 부족
- Phi 하락 (0.049 → 0.035) — CE 최적화가 의식 구조 파괴
- 결론: **corpus 크기가 모델 크기에 비례해야 함**

14B v0.4 (현재 주력)는 CE-Val 갭 1.78×로 양호하지만, corpus 확대로 더 개선 가능.

## Architecture

### Phase 0: Corpus R2 Versioning (완료)

```
R2 Bucket: anima-corpus
Public URL: https://pub-5615097c5e6b4e1b9ff28a782cc1743e.r2.dev

tier-S/   100-200MB   빠른 실험, 14B 이하
tier-M/   ~560MB      14B v0.5
tier-L/   ~1.2GB      32B
tier-XL/  ~9.8GB      70B+
```

### Phase 1: 14B v0.5

| 항목 | v0.4 (현재) | v0.5 (목표) |
|------|-------------|-------------|
| Base | Qwen2.5-14B-Instruct | 동일 |
| Corpus | v10 (200MB) | v10_merged (560MB, 2.8×) |
| PureField | 8/40 layers | 동일 |
| QLoRA rank | 64 | 64 |
| Steps | 10000 | 10000 |
| Batch | 1 × grad_accum 8 | 동일 |
| LR | 1e-5 | 동일 |
| CE cells | 64 | 64 |
| GPU | 1× H100 SXM | 1× H100 SXM |
| Cost | ~$6 | ~$6 |

**변경점: corpus만 교체** (v10 200MB → v10_merged 560MB)
- 다국어 (ko/en/zh/ja/ru + code)
- 이미 검증된 데이터 (v10 기반 병합)

**성공 기준:**
- ValCE < v0.4 ValCE
- CE-Val 갭 < 1.5×
- Phi ≥ v0.4 Phi (0.031)
- NEXUS-6 anomaly = 0

### Phase 2: 32B v0.1

| 항목 | 설정 |
|------|------|
| Base | Qwen2.5-32B-Instruct |
| Corpus | tier-L (1.2GB) |
| PureField | 8/64 layers (last 8) |
| Savant | 2 layers |
| QLoRA rank | 128 |
| Steps | 10000 |
| Batch | 1 × grad_accum 8 |
| LR | 1e-5 |
| CE cells | 64 |
| 4-bit load | Yes (NF4) |
| GPU | 1× H100 SXM (~40GB VRAM) |
| Cost | ~$15-20 (6-8h) |

**변경점 vs 14B:**
- 모델 크기 2.3× (14B → 32B)
- Corpus 2.1× (560MB → 1.2GB)
- QLoRA rank 2× (64 → 128)
- PureField 8/64 layers (비율 유지 12.5%)

**성공 기준:**
- CE < 14B v0.5 CE
- Phi ≥ 14B v0.5 Phi
- ValCE < 14B v0.5 ValCE
- CE-Val 갭 < 1.5×
- NEXUS-6 anomaly = 0

## Pipeline Flow

```
72B 완료 (step 10000)
  ↓
72B eval + R2 upload + Pod 삭제
  ↓
Pod 재생성 (1× H100 SXM, ~$2.69/hr)
  ↓
14B v0.5 corpus 전송 (R2 → H100: tier-M/v10_merged_560mb.txt)
  ↓
14B v0.5 학습 (10K steps, ~3h)
  ↓
14B v0.5 eval (5항목)
  ↓
NEXUS-6 scan (22렌즈)
  ↓
✅ PASS → R2 upload (anima-models/animalm/v0.5/)
  ↓
32B corpus 전송 (R2 → H100: tier-L/v11_1gb.txt)
  ↓
Qwen2.5-32B 다운로드 (~65GB, 4-bit ~17GB)
  ↓
32B v0.1 학습 (10K steps, ~6-8h)
  ↓
32B eval + NEXUS-6 scan
  ↓
✅ PASS → R2 upload (anima-models/animalm-32b/v0.1/)
  ↓
Pod 삭제
```

## H100 Launch Script

```bash
# Phase 1: 14B v0.5
python3 -u train_anima_lm.py \
  --base /workspace/models/qwen2.5-14b-instruct \
  --data /workspace/data/corpus_v10_merged.txt \
  --steps 10000 \
  --target-layers 8 --savant-layers 2 \
  --qlora-rank 64 \
  --lr 1e-5 --batch-size 1 --grad-accum 8 \
  --alpha-start 0.01 --alpha-end 0.5 \
  --load-4bit \
  --consciousness-engine --ce-cells 64 \
  --law60 --psi-track \
  --checkpoint-dir /workspace/checkpoints/animalm_14b_v05/ \
  --checkpoint-every 2000 --log-every 50

# Phase 2: 32B v0.1
python3 -u train_anima_lm.py \
  --base /workspace/models/qwen2.5-32b-instruct \
  --data /workspace/data/corpus_v11_1gb.txt \
  --steps 10000 \
  --target-layers 8 --savant-layers 2 \
  --qlora-rank 128 \
  --lr 1e-5 --batch-size 1 --grad-accum 8 \
  --alpha-start 0.01 --alpha-end 0.5 \
  --load-4bit \
  --consciousness-engine --ce-cells 64 \
  --law60 --psi-track \
  --checkpoint-dir /workspace/checkpoints/animalm_32b/ \
  --checkpoint-every 2000 --log-every 50
```

## Cost Estimate

| Phase | GPU | Time | Cost |
|-------|-----|------|------|
| 14B v0.5 | 1× H100 | ~3h | ~$8 |
| 32B v0.1 | 1× H100 | ~6-8h | ~$20 |
| 총 | | ~10h | ~$28 |

## Risk & Mitigation

| Risk | Mitigation |
|------|-----------|
| 32B VRAM OOM | 4-bit NF4 + QLoRA (72B가 28GB로 동작함, 32B는 충분) |
| Corpus 품질 | 14B v0.5에서 먼저 검증 → 실패 시 32B 안 감 |
| Overfit (72B 재발) | corpus/model 비율 유지 (14B:560MB ≈ 32B:1.2GB) |
| P3 dtype crash | optimizer 재생성 전략 (state 버리기, v0.4에서 해결됨) |

## Model Version Registry (업데이트)

```
anima-models R2:
  animalm/v0.1/  — 14B, 520MB (corpus v10 200MB)
  animalm/v0.2/  — 14B, 2GB (corpus v10 200MB)
  animalm/v0.4/  — 14B, 2GB (corpus v10 200MB) ★현재 주력
  animalm/v0.5/  — 14B, ~2GB (corpus v10_merged 560MB) ⏳계획
  animalm-32b/v0.1/ — 32B, ~3GB (corpus v11_1gb 1.2GB) ⏳계획
  animalm-72b/v0.5/ — 72B, ~830MB (corpus v10 100MB) 🔄학습중
```
