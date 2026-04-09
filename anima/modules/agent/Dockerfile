FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
# (torch cpu-only for agent; full torch via base image if GPU needed)
RUN pip install --no-cache-dir \
    "torch>=2.0" \
    numpy \
    websockets \
    requests \
    scipy

# Copy anima core sources (consciousness engine imports)
# Build context = repo root (set in docker-compose.yml)
COPY anima/src/ /app/anima-src/
COPY anima/config/ /app/anima-src/config/

# Copy agent platform code
COPY anima-agent/ /app/

# Ensure anima-src is importable (path_setup.py adds subdirs to sys.path)
ENV PYTHONPATH="/app:/app/anima-src"
ENV PYTHONUNBUFFERED=1

EXPOSE 8766

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8766/health')" || exit 1

CMD ["python", "run.py", "--mcp", "--direct"]
