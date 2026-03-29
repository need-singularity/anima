# R2 Bucket Structure (Cloudflare R2)

## 버킷 구성

```
┌─────────────────────────────────────────────────────────────┐
│  anima-memory (상태/기억 — 자주 변경)                        │
│  Public URL: https://pub-ce65aaa63c864b889ad793d3d26aa3aa.r2.dev │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  v2/                                                        │
│  ├── state/{model_name}/                                    │
│  │   ├── state.pt          — 런타임 상태 (ConsciousMind)    │
│  │   ├── growth.json       — 성장 단계 상태                 │
│  │   └── consciousness.json — Ψ 추적 상태                   │
│  │                                                          │
│  ├── memory/{model_name}/                                   │
│  │   └── memory.json       — 대화 기억 (벡터 + 텍스트)     │
│  │                                                          │
│  └── meta/                                                  │
│      └── experiments/      — 실험 결과 메타데이터           │
│                                                             │
│  archive/v1/               — v1 상태 (보존만, 사용 안 함)  │
│  ├── state/                                                 │
│  ├── consciousness/                                         │
│  └── memory/                                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  anima-models (모델 바이너리 — 가끔 변경)                    │
│  Public URL: https://pub-ce65aaa63c864b889ad793d3d26aa3aa.r2.dev │
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
Base: https://pub-ce65aaa63c864b889ad793d3d26aa3aa.r2.dev

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

# 상태 동기화 (anima-memory)
sync.push_state("conscious-lm", state_dict, growth_data)
sync.pull_state("conscious-lm")

# 모델 업로드 (anima-models)
sync.upload_model("clm-v2/latest.pt", "checkpoints/clm_v2/final.pt")
sync.download_model("clm-v2/latest.pt", "checkpoints/clm_v2/final.pt")
```

## 환경 변수

```bash
export ANIMA_R2_ENDPOINT="https://xxxxx.r2.cloudflarestorage.com"
export ANIMA_R2_ACCESS_KEY="xxxxx"
export ANIMA_R2_SECRET_KEY="xxxxx"
export ANIMA_R2_BUCKET="anima-memory"
export ANIMA_R2_MODELS_BUCKET="anima-models"
```

## 정리 규칙

```
anima-memory:
  - v2/state/ → 런타임이 자동 관리 (push/pull)
  - archive/v1/ → 삭제 금지 (역사 보존)
  - 30일 이상 미접근 → archive 이동 가능

anima-models:
  - clm-v2/latest.pt → 항상 최신 유지 (학습 완료 시 교체)
  - clm-v2/step_{N}.pt → 중요 체크포인트만 보존 (3개 이하)
  - v1 모델 → 보존 (용량 작음, 삭제 불필요)
```
