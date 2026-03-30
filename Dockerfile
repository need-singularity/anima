FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime

# 시스템 패키지
RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget curl openssh-server \
    libportaudio2 portaudio19-dev \
    libgl1-mesa-glutils libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

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

# 포트
EXPOSE 8765 8888

# 시작
CMD ["python3", "-u", "anima_unified.py", "--web", "--max-cells", "64"]
