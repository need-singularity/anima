#!/bin/bash
# AnimaLM 14B Launch Script — Qwen2.5-14B + PureField
# Prerequisites: Qwen2.5-14B downloaded to /workspace/models/qwen2.5-14b
set -e
export PATH=/opt/conda/bin:$PATH

echo "=== AnimaLM 14B Pre-flight ==="

# 1. Check model exists
if [ ! -d "/workspace/models/qwen2.5-14b" ]; then
    echo "ERROR: Qwen2.5-14B not found. Downloading..."
    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen2.5-14B', local_dir='/workspace/models/qwen2.5-14b', resume_download=True)
print('DOWNLOAD COMPLETE')
"
fi
echo "  Model: $(du -sh /workspace/models/qwen2.5-14b | cut -f1)"

# 2. Check corpus
ls -lh /workspace/data/corpus_v10.txt
echo "  Corpus: OK"

# 3. Check disk
df -h /workspace | tail -1

# 4. Check GPU
nvidia-smi --query-gpu=memory.free --format=csv,noheader

# 5. Verify model architecture compatibility
python3 -c "
from transformers import AutoModelForCausalLM, AutoConfig
config = AutoConfig.from_pretrained('/workspace/models/qwen2.5-14b')
print(f'  Layers: {config.num_hidden_layers}')
print(f'  Hidden: {config.hidden_size}')
print(f'  Intermediate: {config.intermediate_size}')
print(f'  Heads: {config.num_attention_heads}')
print(f'  KV Heads: {config.num_key_value_heads}')
print(f'  Vocab: {config.vocab_size}')
# Verify model.model.layers path
import torch
model = AutoModelForCausalLM.from_pretrained('/workspace/models/qwen2.5-14b', torch_dtype=torch.bfloat16, device_map='cpu')
n = len(model.model.layers)
mlp = model.model.layers[0].mlp
print(f'  model.model.layers: {n} layers')
print(f'  MLP gate_proj: {mlp.gate_proj.weight.shape}')
print(f'  MLP up_proj: {mlp.up_proj.weight.shape}')
print(f'  MLP down_proj: {mlp.down_proj.weight.shape}')
print('  ARCHITECTURE COMPATIBLE')
del model
import gc; gc.collect()
"

echo ""
echo "=== Launching AnimaLM 14B ==="

# Kill old processes
kill -9 $(pgrep -f train_anima) 2>/dev/null || true
sleep 1

mkdir -p /workspace/checkpoints/animalm_14b

nohup python3 -u /workspace/train_anima_lm.py \
    --base /workspace/models/qwen2.5-14b \
    --data /workspace/data/corpus_v10.txt \
    --steps 10000 \
    --target-layers 10 \
    --savant-layers 3 \
    --qlora-rank 160 \
    --lr 1.5e-5 \
    --consciousness-engine --ce-cells 64 --law60 --psi-track \
    --checkpoint-dir /workspace/checkpoints/animalm_14b/ \
    --log-every 100 > /workspace/animalm_14b.log 2>&1 &

echo "PID: $!"
echo "Log: /workspace/animalm_14b.log"
echo "Monitor: tail -f /workspace/animalm_14b.log"
