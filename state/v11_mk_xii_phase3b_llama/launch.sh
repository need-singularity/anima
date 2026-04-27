#!/bin/bash
# Launch wrapper for Mk.XII Phase 3b Llama 8B + 70B int4 sequential measurement
set -u
cd /workspace
ulimit -n 65536 || true
export HF_HOME=/workspace/.hf_cache
export HF_HUB_CACHE=/workspace/.hf_cache
export HF_HUB_DISABLE_XET=1
export TRANSFORMERS_VERBOSITY=warning
mkdir -p /workspace/.hf_cache /workspace/out
if [ -f /workspace/.hf_token ]; then
    export HF_TOKEN="$(cat /workspace/.hf_token)"
    export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
    echo "hf-token-loaded len=${#HF_TOKEN}"
fi
# install missing deps
python3 -m pip install --quiet --no-input \
    transformers==4.44.2 \
    accelerate==0.34.2 \
    bitsandbytes==0.43.3 \
    huggingface_hub==0.25.2 \
    psutil 2>&1 | tail -5
nohup python3 /workspace/wrapper.py >> /workspace/wrapper.stdout 2>&1 &
echo "wrapper-launched pid=$!"
disown
sleep 1
