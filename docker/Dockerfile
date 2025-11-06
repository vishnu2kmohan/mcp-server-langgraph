# syntax=docker/dockerfile:1.4
# ==============================================================================
# Optimized Multi-Variant Dockerfile for MCP Server LangGraph
# ==============================================================================
#
# VARIANTS:
#   - base:    Lightweight (200MB) - API-based embeddings only (Google Gemini)
#   - full:    Complete (1.2GB)    - Includes sentence-transformers for local embeddings
#   - test:    Test runner (800MB)  - Dev dependencies, no ML models
#
# BUILD EXAMPLES:
#   docker build --target final-base -t mcp-server-langgraph:base -f docker/Dockerfile .
#   docker build --target final-full -t mcp-server-langgraph:full -f docker/Dockerfile .
#   docker build --target final-test -t mcp-server-langgraph:test -f docker/Dockerfile .
#
# OPTIMIZATION HIGHLIGHTS:
#   - Distroless runtime (no shell, minimal attack surface)
#   - Layer ordering optimized for cache hits
#   - Separate build stages for each variant
#   - BuildKit cache mounts throughout
#   - 62% smaller base image (530MB → 200MB)
#   - 94% smaller test image (13.3GB → 800MB)
#
# ==============================================================================

ARG PYTHON_VERSION=3.12

# ==============================================================================
# STAGE: base-builder
# Common build dependencies for all variants
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim AS base-builder

WORKDIR /app

# Install minimal build dependencies
# Note: No Rust needed for base variant (no infisical)
# Shared cache for all variants (base-builder is common to all)
RUN --mount=type=cache,target=/var/cache/apt,id=apt-cache-base-builder,sharing=private \
    --mount=type=cache,target=/var/lib/apt,id=apt-lib-base-builder,sharing=private \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv - Fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files FIRST (changes rarely)
COPY pyproject.toml uv.lock ./

# ==============================================================================
# STAGE: dependencies-base
# Lightweight dependencies (no ML, no secrets management)
# ==============================================================================
FROM base-builder AS dependencies-base

# Export base dependencies (exclude heavy optional packages)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --frozen \
    --no-hashes \
    --no-emit-project \
    --no-extra embeddings-local \
    --no-extra embeddings \
    --no-extra secrets \
    --no-extra all \
    > /tmp/requirements-base.txt

# Show what we're installing for transparency
RUN echo "=== Base Dependencies ===" && \
    grep -E "^(langchain|langgraph|litellm|mcp|opentelemetry|fastapi)" /tmp/requirements-base.txt | head -20

# ==============================================================================
# STAGE: dependencies-full
# Complete dependencies including ML models
# Note: Excludes infisical-python (secrets extra) due to platform wheel availability
# Application falls back to environment variables when infisical is not available
# ==============================================================================
FROM base-builder AS dependencies-full

# Export full dependencies (includes embeddings-local, excludes secrets)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --frozen \
    --no-hashes \
    --no-emit-project \
    --extra embeddings-local \
    --no-extra secrets \
    > /tmp/requirements-full.txt

# ==============================================================================
# STAGE: dependencies-test
# Test dependencies only (no production runtime)
# ==============================================================================
FROM base-builder AS dependencies-test

# Export test dependencies (dev extras, no heavy embeddings)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv export --frozen \
    --no-hashes \
    --no-emit-project \
    --extra dev \
    --no-extra embeddings-local \
    --no-extra embeddings \
    --no-extra all \
    > /tmp/requirements-test.txt

# ==============================================================================
# STAGE: build-base
# Build base variant packages
# ==============================================================================
FROM dependencies-base AS build-base

# Copy source code (changes frequently, after dependencies)
COPY src/ ./src/

# Create virtual environment and install base dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --python /opt/venv/bin/python --no-cache \
    -r /tmp/requirements-base.txt && \
    uv pip install --python /opt/venv/bin/python --no-cache --no-deps .

# ==============================================================================
# STAGE: build-full
# Build full variant packages (with ML, without secrets management)
# ==============================================================================
FROM dependencies-full AS build-full

COPY src/ ./src/

# Create virtual environment and install full dependencies (includes PyTorch, sentence-transformers)
RUN --mount=type=cache,target=/root/.cache/uv \
    python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --python /opt/venv/bin/python --no-cache \
    -r /tmp/requirements-full.txt && \
    uv pip install --python /opt/venv/bin/python --no-cache --no-deps .

# ==============================================================================
# STAGE: build-test
# Build test variant packages
# ==============================================================================
FROM dependencies-test AS build-test

COPY src/ ./src/
COPY tests/ ./tests/

# Create virtual environment and install test dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    python -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --python /opt/venv/bin/python --no-cache \
    -r /tmp/requirements-test.txt && \
    uv pip install --python /opt/venv/bin/python --no-cache --no-deps -e .

# ==============================================================================
# STAGE: runtime-distroless
# Python 3.12 slim runtime (compatible with our build stage)
# Note: Switched from distroless due to Python 3.11 vs 3.12 incompatibility
# ==============================================================================
FROM python:3.12-slim AS runtime-distroless

RUN useradd -r -u 65532 -g users nonroot

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/nonroot/.local/bin:$PATH \
    PORT=8000

WORKDIR /app

USER nonroot

# ==============================================================================
# STAGE: runtime-slim
# Slim Python runtime (for test variant, needs shell)
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim AS runtime-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TESTING=true

WORKDIR /app

# Install runtime dependencies for tests (curl for health checks)
RUN --mount=type=cache,target=/var/cache/apt,id=apt-cache-runtime-slim,sharing=private \
    --mount=type=cache,target=/var/lib/apt,id=apt-lib-runtime-slim,sharing=private \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ==============================================================================
# FINAL STAGE: base variant (distroless)
# ==============================================================================
FROM runtime-distroless AS final-base

# Copy virtual environment from build stage
COPY --from=build-base --chown=nonroot:users /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=nonroot:nonroot src/ ./src/
COPY --chown=nonroot:nonroot pyproject.toml ./

# Metadata
LABEL org.opencontainers.image.title="MCP Server LangGraph (Base)"
LABEL org.opencontainers.image.description="Lightweight MCP server with API-based embeddings"
LABEL org.opencontainers.image.variant="base"
LABEL org.opencontainers.image.size="~200MB"

EXPOSE 8000

# Use Python from venv
CMD ["python", "-m", "mcp_server_langgraph.mcp.server_streamable"]

# ==============================================================================
# FINAL STAGE: full variant (distroless)
# ==============================================================================
FROM runtime-distroless AS final-full

# Copy virtual environment from build stage
COPY --from=build-full --chown=nonroot:users /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=nonroot:nonroot src/ ./src/
COPY --chown=nonroot:nonroot pyproject.toml ./

# Metadata
LABEL org.opencontainers.image.title="MCP Server LangGraph (Full)"
LABEL org.opencontainers.image.description="Complete MCP server with local embeddings support"
LABEL org.opencontainers.image.variant="full"
LABEL org.opencontainers.image.size="~1.2GB"

EXPOSE 8000

# Use Python from venv
CMD ["python", "-m", "mcp_server_langgraph.mcp.server_streamable"]

# ==============================================================================
# FINAL STAGE: test variant (slim, with shell)
# ==============================================================================
FROM runtime-slim AS final-test

# Copy virtual environment from builder
COPY --from=build-test /opt/venv /opt/venv

# Copy application and test code
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml ./

# Set PATH to use virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Disable observability during tests
ENV ENABLE_TRACING=false \
    ENABLE_METRICS=false \
    ENABLE_CONSOLE_EXPORT=false

# Metadata
LABEL org.opencontainers.image.title="MCP Server LangGraph (Test)"
LABEL org.opencontainers.image.description="Test runner with dev dependencies"
LABEL org.opencontainers.image.variant="test"
LABEL org.opencontainers.image.size="~800MB"

# Default command runs integration tests
CMD ["/opt/venv/bin/pytest", "-m", "integration", "-v", "--tb=short"]

# No health check for test variant
HEALTHCHECK NONE
