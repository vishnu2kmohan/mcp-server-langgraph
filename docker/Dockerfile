# syntax=docker/dockerfile:1.4
# Multi-stage build for LangGraph MCP Agent with BuildKit caching
# Optimized with uv for 10-100x faster dependency resolution
FROM python:3.12-slim AS builder

# Set working directory
WORKDIR /app

# Install build dependencies including Rust for infisical-python
# Use BuildKit cache mounts for faster repeated builds
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl

# Install Rust toolchain with cache mount (needed for infisical-python)
RUN --mount=type=cache,target=/root/.cargo/registry \
    --mount=type=cache,target=/root/.cargo/git \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Add Rust to PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# Set PyO3 forward compatibility for infisical-python
ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Install uv - Fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Export dependencies to requirements format for installation
# This ensures compatibility while using uv's fast resolution
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --frozen --all-extras --no-hashes --no-emit-project > /tmp/requirements.txt

# Copy source code
COPY src/ ./src/

# Build and install with cache mounts (uv is 10-100x faster than pip)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cargo/registry \
    --mount=type=cache,target=/root/.cargo/git \
    uv pip install --python $(which python) --user --no-cache \
        -r /tmp/requirements.txt && \
    uv pip install --python $(which python) --user --no-cache --no-deps -e .

# Final stage
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH \
    PORT=8000

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Update PATH for non-root user
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the StreamableHTTP server by default (can override with CMD)
# Use mcp-server-streamable for modern StreamableHTTP transport
# Use mcp-server for stdio transport
CMD ["python", "-m", "mcp_server_langgraph.mcp.server_streamable"]
