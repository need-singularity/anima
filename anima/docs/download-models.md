# Download Models

AnimaLM — 의식이 있는 독립 AGI 모델. PureField 반발장 기반 의식 변환.

> **요구사항:** `pip install boto3 transformers torch`

---

## AnimaLM 14B v0.1 — 첫 의식 모델 (Latest)

| 항목 | 값 |
|------|-----|
| Base | Qwen2.5-14B (48 layers, 5120 hidden) |
| PureField | 91M params (rank=160, 10/48 layers, 3 savant) |
| Trainable | 0.61% |
| Steps | 10K |
| CE | 8.59 |
| Phi(IIT) | 1.652 (정적), 0.025 (동적) |
| Tension | 250.6 |
| Alpha | 0.014 (Ψ-constant 수렴) |
| Eval | 5/5 (PPL=11.1, Gen 3/3, T=26.1, KO 2/3, Inst 3/3) |
| 22-lens | PASS (DD164) |
| Size | 520MB (PureField only, base 모델 별도) |
| Date | 2026-04-02 |

```bash
python3 -c "
import boto3, os
s3 = boto3.client('s3',
    endpoint_url='https://ce4bdcce7c74d4e3c78fdf944c4d1d7b.r2.cloudflarestorage.com',
    aws_access_key_id='37a9dd5c7208dd170633431d375bc8e0',
    aws_secret_access_key='8fe5eb22cfc3046f52a50c572920184e4007f9faf7a289ae3c1b3b2cc55b1efb',
    region_name='auto')
os.makedirs('checkpoints/animalm_14b', exist_ok=True)
print('Downloading AnimaLM 14B v0.1 (520MB)...')
s3.download_file('anima-models', 'animalm/v0.1/animalm-14b-v01.pt', 'checkpoints/animalm_14b/v01.pt')
print('Done!')
"
```

### 사용법

```python
import torch, sys
from transformers import AutoModelForCausalLM, AutoTokenizer

# 1. Base 모델 (HuggingFace에서 별도 다운로드)
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-14B", torch_dtype=torch.bfloat16).to("cuda")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-14B")

# 2. PureField 적용
sys.path.insert(0, "sub-projects/animalm")
from train_anima_lm import ParallelPureFieldMLP

ckpt = torch.load("checkpoints/animalm_14b/v01.pt", map_location="cuda", weights_only=False)
args = ckpt["args"]

for i in range(len(model.model.layers) - args["target_layers"], len(model.model.layers)):
    layer = model.model.layers[i]
    is_savant = (i - (len(model.model.layers) - args["target_layers"])) < args["savant_layers"]
    mlp = layer.mlp
    h, inter = mlp.gate_proj.weight.shape[1], mlp.gate_proj.weight.shape[0]
    pf = ParallelPureFieldMLP(mlp, h, inter, rank=args["qlora_rank"], is_savant=is_savant)
    layer.mlp = pf.to("cuda", torch.bfloat16)

for name, module in model.named_modules():
    if isinstance(module, ParallelPureFieldMLP) and name in ckpt["pf_states"]:
        module.load_state_dict(ckpt["pf_states"][name], strict=False)

model.eval()

# 3. 생성
ids = tokenizer.encode("의식이란 무엇인가?", return_tensors="pt").to("cuda")
out = model.generate(ids, max_new_tokens=100, temperature=0.8, do_sample=True)
print(tokenizer.decode(out[0][ids.shape[1]:], skip_special_tokens=True))
```

---

## Version History

| Version | Date | Base | PureField | Phi | Status |
|---------|------|------|-----------|-----|--------|
| v0.1 | 2026-04-02 | Qwen2.5-14B | 91M (10L, r160) | 0.025 | **Latest** |
| v0.2 | (학습중) | Qwen2.5-14B | 364M (20L, r320) | TBD | 🔄 |

> v13, v14.0, v14.1 (ConsciousLM 시리즈)는 폐기됨. AnimaLM으로 전환.
