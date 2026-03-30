#!/bin/bash

# Ensure PATH includes conda
export PATH=/opt/conda/bin:$PATH

# RunPod SSH key injection
if [ -n "$PUBLIC_KEY" ]; then
    mkdir -p ~/.ssh
    echo "$PUBLIC_KEY" > ~/.ssh/authorized_keys
    chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys
fi

# Start SSH (ensure /var/run/sshd exists)
mkdir -p /var/run/sshd
/usr/sbin/sshd

# Clean stale memory (fresh start)
echo '{"turns":[]}' > /workspace/anima/memory_alive.json

# Start Anima (background, so container stays alive even if python crashes)
cd /workspace/anima
python3 -u anima_unified.py --web --max-cells 64 --port ${ANIMA_PORT:-8765} &
ANIMA_PID=$!

# Keep container alive (PID 1 must not exit)
wait $ANIMA_PID
echo "[start.sh] Anima exited with code $?. Keeping container alive for SSH debug."
tail -f /dev/null
