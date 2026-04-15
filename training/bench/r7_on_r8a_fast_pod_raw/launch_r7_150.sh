#!/bin/bash
# r7 stack on fast pod: unsloth only, dropout=0.05, NO liger, NO compile unblock
set -e
unset ALM_COMPILE_UNBLOCK
export HF_HOME=/root/.cache/huggingface
export TRANSFORMERS_VERBOSITY=warning
export TOKENIZERS_PARALLELISM=false
# Guard r2 upload stub
export PATH=/tmp/noop:$PATH
mkdir -p /tmp/noop
cat > /tmp/noop/rclone <<'RCLONE'
#!/bin/bash
echo '[rclone-stub] skipped'
exit 0
RCLONE
chmod +x /tmp/noop/rclone

cd /workspace
python -u /workspace/train_alm_14b_r8a.py     --base Qwen/Qwen2.5-14B-Instruct     --corpus /workspace/corpus.txt     --steps 150     --batch 8     --seq 1024     --grad-accum 1     --lora-dropout 0.05     --unsloth     --ckpt-dir /workspace/ckpt_alm_14b_r7stack_150     --save-every 1000     --eval-every 10000     --smoke     --round 1 2>&1 | tee /workspace/train_alm_14b_r7stack_150.log
