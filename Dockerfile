FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

# 시스템 패키지
RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl openssh-server build-essential \
    libportaudio2 portaudio19-dev \
    libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# SSH for RunPod
RUN mkdir -p /var/run/sshd && \
    echo 'root:root' | chpasswd && \
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Python 패키지
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# cloudflared
RUN curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared

# Anima 코드
WORKDIR /workspace/anima
COPY . .

# 체크포인트 디렉토리
RUN mkdir -p checkpoints/clm_v2

# 기본 포트: 8888 (RunPod HTTP proxy 호환)
ENV ANIMA_PORT=8888
EXPOSE 22 8888

# RunPod start script: SSH + Anima
COPY start.sh /start.sh
RUN chmod +x /start.sh
CMD ["/start.sh"]
