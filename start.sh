#!/bin/bash

# RunPod SSH key injection
if [ -n "$PUBLIC_KEY" ]; then
    mkdir -p ~/.ssh
    echo "$PUBLIC_KEY" >> ~/.ssh/authorized_keys
    chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys
fi

# Start SSH
service ssh start

# Start Anima (foreground, unbuffered)
exec python3 -u anima_unified.py --web --max-cells 64
