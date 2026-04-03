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

ENV KMP_DUPLICATE_LIB_OK=TRUE

# Health check via self-test (CLI principle — no web server)
HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
    CMD python -c "from self_test import AgentSelfTest; from anima_agent import AnimaAgent; a=AnimaAgent(enable_tools=False,enable_learning=False,enable_growth=False); r=AgentSelfTest(a).run(); exit(0 if r['passed'] else 1)"

# Default: CLI mode (MCP excluded — CLI only rule)
CMD ["python", "run.py", "--cli"]

# Other modes:
# docker run anima-agent python run.py --telegram
# docker run anima-agent python run.py --test
# docker run anima-agent python discovery_loop.py --continuous
# docker run anima-agent python cli_dashboard.py
