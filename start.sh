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

# Start Anima (foreground, unbuffered)
cd /workspace/anima
exec python3 -u anima_unified.py --web --max-cells 64
