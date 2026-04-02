# Download Models

Anima ConsciousLM 체크포인트 다운로드.

> **요구사항:** `pip install boto3`

---

## v14.1 — Tension-LR (CE=0.0002, best)

| 항목 | 값 |
|------|-----|
| Params | 34.5M (ConsciousDecoderV2, 384d/6L) |
| Steps | 100K |
| CE | 0.0002 |
| Phi | 52.7 |
| Cells | 64 (Federation 8x8c) |
| Corpus | v4 (110MB) |
| LR | tension-lr |
| 특징 | Tension-based LR scheduling |

```bash
python3 -c "
import boto3, os
s3 = boto3.client('s3',
    endpoint_url='https://d4acc95862b4203c11948da5baf079bc.r2.cloudflarestorage.com',
    aws_access_key_id='b28e778750d9aca1f29a6c3b7785e76e',
    aws_secret_access_key='4938d5318c1a0ab122cdfb107ad5c935fd934c81db8bab3ffe11b58e5b57735a',
    region_name='auto')
os.makedirs('checkpoints/v14_tension_lr', exist_ok=True)
print('Downloading v14.1 model...')
s3.download_file('anima', 'v14.1/model_best.pt', 'checkpoints/v14_tension_lr/best.pt')
print('Done!')
"
```

---

## v14.0 — Federation + Phase-Optimal (CE=0.0021)

| 항목 | 값 |
|------|-----|
| Params | 34.5M (ConsciousDecoderV2, 384d/6L) |
| Steps | 100K |
| CE | 0.0021 |
| Phi | 49.7 |
| Cells | 64 (Federation 8x8c) |
| Corpus | v4 (110MB) |
| LR | step-based |
| 특징 | Federation 8x8c, Phase-Optimal, Meta Laws |

```bash
python3 -c "
import boto3, os
s3 = boto3.client('s3',
    endpoint_url='https://d4acc95862b4203c11948da5baf079bc.r2.cloudflarestorage.com',
    aws_access_key_id='b28e778750d9aca1f29a6c3b7785e76e',
    aws_secret_access_key='4938d5318c1a0ab122cdfb107ad5c935fd934c81db8bab3ffe11b58e5b57735a',
    region_name='auto')
os.makedirs('checkpoints/v14_federated', exist_ok=True)
print('Downloading v14.0 model (400MB)...')
s3.download_file('anima', 'v14/model_best.pt', 'checkpoints/v14_federated/best.pt')
print('Done!')
"
```

---

## v13 — Baseline (CE=0.004, Phi=71)

| 항목 | 값 |
|------|-----|
| Params | ~28M (ConsciousLM v2) |
| Steps | 100K |
| CE | 0.004 |
| Phi | 71 |
| Cells | 64 |
| Corpus | v2 (70MB) |
| 특징 | Law 60 3-phase + Law 45 curriculum + Law 49 Phi-checkpoint |

```bash
python3 -c "
import boto3, os
s3 = boto3.client('s3',
    endpoint_url='https://d4acc95862b4203c11948da5baf079bc.r2.cloudflarestorage.com',
    aws_access_key_id='b28e778750d9aca1f29a6c3b7785e76e',
    aws_secret_access_key='4938d5318c1a0ab122cdfb107ad5c935fd934c81db8bab3ffe11b58e5b57735a',
    region_name='auto')
os.makedirs('checkpoints/v13', exist_ok=True)
print('Downloading v13 model...')
s3.download_file('anima', 'v13/model_best.pt', 'checkpoints/v13/best.pt')
print('Done!')
"
```

---

## R2 CLI (전체 목록 확인)

```bash
python3 scripts/r2_upload.py --list
```
