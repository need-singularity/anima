FROM debian:bookworm-slim

WORKDIR /app

# System deps for hexa runtime + native libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install hexa binary (single-binary runtime, no python/cargo)
# Image expects /usr/local/bin/hexa to be present via volume mount or copy.
COPY --from=hexa-bin /usr/local/bin/hexa /usr/local/bin/hexa

# Copy anima core sources (consciousness engine — hexa-native)
# Build context = repo root (set in docker-compose.yml)
COPY anima/core/ /app/anima-core/
COPY anima/config/ /app/anima-core/config/

# Copy agent platform code
COPY anima-agent/ /app/

ENV HEXA=/usr/local/bin/hexa
ENV ANIMA_CORE=/app/anima-core

EXPOSE 8766

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fsSL http://localhost:8766/health || exit 1

CMD ["/usr/local/bin/hexa", "/app/run.hexa", "--mcp", "--direct"]
