#!/bin/bash
# Launch wrapper for gemma-27b int8/4bit alternative path 1 measurement
set -u
cd /workspace
ulimit -n 65536 || true
export HF_HUB_DISABLE_XET=1
export HF_HOME=/workspace/.hf_cache
export TRANSFORMERS_VERBOSITY=warning
mkdir -p /workspace/.hf_cache /workspace/out
if [ -f /workspace/.hf_token ]; then
    export HF_TOKEN="$(cat /workspace/.hf_token)"
    export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
fi
# install missing deps (transformers + bitsandbytes for 4bit)
python3 -m pip install --quiet --no-input transformers==4.44.2 accelerate==0.34.2 bitsandbytes==0.43.3 huggingface_hub==0.25.2 2>&1 | tail -3
# spawn wrapper detached so pod-side process survives ssh disconnect
nohup python3 /workspace/wrapper.py >> /workspace/wrapper.stdout 2>&1 &
echo "wrapper-launched pid=$!"
disown
sleep 1
