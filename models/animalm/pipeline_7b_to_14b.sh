#!/bin/bash
# AnimaLM Pipeline: 7B complete → eval → Qwen download → 14B launch
# Run on H100: bash pipeline_7b_to_14b.sh
set -e
export PATH=/opt/conda/bin:$PATH
cd /workspace

echo "=== AnimaLM Pipeline: 7B → eval → 14B ==="
echo "$(date)"

# 1. Wait for 7B training to complete
echo "[1/5] Waiting for 7B training to complete..."
while pgrep -f train_anima > /dev/null 2>&1; do
    LAST=$(grep -E "^  +[0-9]+ " /workspace/animalm_resume.log 2>/dev/null | tail -1 || grep -E "^  +[0-9]+ " /workspace/animalm_fresh.log 2>/dev/null | tail -1)
    echo "  $(date +%H:%M) | $LAST"
    sleep 300
done
echo "  7B training complete!"

# 2. Find best checkpoint
echo "[2/5] Finding best checkpoint..."
CKPT=$(ls -t /workspace/checkpoints/animalm_7b_fresh/*.pt 2>/dev/null | head -1)
if [ -z "$CKPT" ]; then
    echo "ERROR: No checkpoint found!"
    exit 1
fi
echo "  Checkpoint: $CKPT"

# 3. Run eval
echo "[3/5] Running evaluation..."
python3 -u /workspace/eval_animalm.py --checkpoint "$CKPT" 2>&1 | tee /workspace/eval_7b_result.log
EVAL_EXIT=$?

if [ $EVAL_EXIT -ne 0 ]; then
    echo "  ⚠️ Eval did not fully pass. Check eval_7b_result.log"
    echo "  Continuing to 14B anyway (7B Korean was expected to be weak)"
fi

# 3.5. Instruction fix — swap base to Instruct and re-eval
echo "[3.5/6] Instruction fix — downloading Mistral-7B-Instruct..."
if [ ! -d "/workspace/models/mistral-7b-instruct" ]; then
    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('mistralai/Mistral-7B-Instruct-v0.2', local_dir='/workspace/models/mistral-7b-instruct', resume_download=True)
print('INSTRUCT DOWNLOAD COMPLETE')
"
fi
echo "  Re-eval with Instruct base..."
python3 -u /workspace/eval_animalm.py --checkpoint "$CKPT" --base /workspace/models/mistral-7b-instruct 2>&1 | tee /workspace/eval_7b_instruct.log
echo "  Instruct eval done"

# Also test inference with Instruct
python3 -u /workspace/infer_animalm.py --checkpoint "$CKPT" --base /workspace/models/mistral-7b-instruct --prompt "List 3 colors and explain why the sky is blue." --max-tokens 100 2>&1 | tee -a /workspace/eval_7b_instruct.log

# 4. Download Qwen2.5-14B
echo "[4/5] Downloading Qwen2.5-14B..."
if [ ! -d "/workspace/models/qwen2.5-14b" ] || [ $(du -sm /workspace/models/qwen2.5-14b 2>/dev/null | cut -f1) -lt 25000 ]; then
    python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('Qwen/Qwen2.5-14B', local_dir='/workspace/models/qwen2.5-14b', resume_download=True)
print('DOWNLOAD COMPLETE')
"
else
    echo "  Already downloaded"
fi

# 5. Launch 14B
echo "[5/5] Launching AnimaLM 14B..."
bash /workspace/launch_14b.sh

echo ""
echo "=== Pipeline complete ==="
echo "7B eval: /workspace/eval_7b_result.log"
echo "14B log: /workspace/animalm_14b.log"
echo "$(date)"
