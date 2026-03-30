# R2 Bucket Structure (Cloudflare R2)

## 버킷 구성

```
┌─────────────────────────────────────────────────────────────┐
│  anima-models (모델 바이너리 — 가끔 변경)                    │
│  Public URL: https://pub-41380137f47b4c4cbc79f5502935b2e9.r2.dev │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  clm-v2/                    ← ConsciousLM v2 (최신!)       │
│  ├── latest.pt              — 최신 체크포인트 (Quick Start) │
│  └── step_{N}.pt            — 중간 체크포인트              │
│                                                             │
│  clm-v1/                    ← v1 아카이브                  │
│  ├── conscious_lm_4m.pt                                     │
│  └── conscious_lm_100m.pt                                   │
│                                                             │
│  animalm-v4/                                                │
│  ├── final.pt               — AnimaLM v4                   │
│  └── v4_savant/final.pt     — Savant 변종                  │
│                                                             │
│  animalm-v3/final.pt        — AnimaLM v3                   │
│  animalm-v2/final.pt        — AnimaLM v2                   │
│  golden-moe-v1/final.pt     — Golden MoE v1               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 다운로드 URL 패턴

```
Models: https://pub-41380137f47b4c4cbc79f5502935b2e9.r2.dev

최신 모델 (Quick Start):
  wget {base}/clm-v2/latest.pt -O checkpoints/clm_v2/final.pt

이전 모델:
  wget {base}/animalm-v4/final.pt
  wget {base}/golden-moe-v1/final.pt
```

## 업로드 (cloud_sync.py)

```python
from cloud_sync import CloudSync

sync = CloudSync()

# 모델 업로드
sync.upload_model("clm-v2/latest.pt", "checkpoints/clm_v2/final.pt")
sync.download_model("clm-v2/latest.pt", "checkpoints/clm_v2/final.pt")
```

## 환경 변수

```bash
export ANIMA_R2_ENDPOINT="https://xxxxx.r2.cloudflarestorage.com"
export ANIMA_R2_ACCESS_KEY="xxxxx"
export ANIMA_R2_SECRET_KEY="xxxxx"
export ANIMA_R2_MODELS_BUCKET="anima-models"
```

## 정리 규칙

```
anima-models:
  - clm-v2/latest.pt → 항상 최신 유지 (학습 완료 시 교체)
  - clm-v2/step_{N}.pt → 중요 체크포인트만 보존 (3개 이하)
  - v1 모델 → 보존 (용량 작음, 삭제 불필요)
```
