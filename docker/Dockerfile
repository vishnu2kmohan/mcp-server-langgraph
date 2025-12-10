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
#   - Uses `uv sync --frozen` for consistency with local/CI (same as Makefile)
#   - Distroless runtime (no shell, minimal attack surface)
#   - Layer ordering optimized for cache hits
#   - BuildKit cache mounts throughout
#   - 62% smaller base image (530MB → 200MB)
#   - 94% smaller test image (13.3GB → 800MB)
#
# OPENSHIFT COMPATIBILITY:
#   - Uses numeric UID (1001) in USER directive
#   - Files owned by UID:0 (root group) for arbitrary UID support
#   - Group permissions set with g=u for OpenShift restricted SCC
#   - See: https://developers.redhat.com/blog/2020/10/26/adapting-docker-and-kubernetes-containers-to-run-on-red-hat-openshift-container-platform
#
# REFERENCES:
#   - https://docs.astral.sh/uv/guides/integration/docker/
#   - https://hynek.me/articles/docker-uv/
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

# UV environment variables for optimal Docker builds
# See: https://docs.astral.sh/uv/guides/integration/docker/
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Copy dependency files FIRST (changes rarely)
COPY pyproject.toml uv.lock ./

# ==============================================================================
# STAGE: build-base
# Build base variant packages (production, minimal dependencies)
# ==============================================================================
FROM base-builder AS build-base

# Copy source code (changes frequently, after dependencies)
COPY src/ ./src/

# Install dependencies using uv sync --frozen (same as local/CI)
# --frozen: Use lockfile exactly, fail if out of sync
# --no-dev: Exclude development dependencies
# --no-editable: Non-editable install for production
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-cache-base,sharing=private \
    uv sync --frozen --no-dev --no-editable \
    --no-extra embeddings-local \
    --no-extra embeddings \
    --no-extra secrets \
    --no-extra all

# ==============================================================================
# STAGE: build-full
# Build full variant packages (production, with local embeddings)
# Note: Excludes infisical-python (secrets extra) due to platform wheel availability
# Application falls back to environment variables when infisical is not available
# ==============================================================================
FROM base-builder AS build-full

COPY src/ ./src/

# Install full dependencies (includes PyTorch, sentence-transformers)
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-cache-full,sharing=private \
    uv sync --frozen --no-dev --no-editable \
    --extra embeddings-local \
    --no-extra secrets

# ==============================================================================
# STAGE: build-test
# Build test variant packages (development dependencies)
# ==============================================================================
FROM base-builder AS build-test

COPY src/ ./src/
COPY tests/ ./tests/

# Install test dependencies (dev extras)
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-cache-test-main,sharing=private \
    uv sync --frozen --extra dev \
    --no-extra embeddings-local \
    --no-extra embeddings \
    --no-extra all

# ==============================================================================
# STAGE: runtime-distroless
# Python 3.12 slim runtime (compatible with our build stage)
# Note: Switched from distroless due to Python 3.11 vs 3.12 incompatibility
#
# OPENSHIFT COMPATIBILITY:
#   - User created with GID 0 (root group) for arbitrary UID support
#   - Numeric UID used in USER directive
#   - /app owned by 1001:0 with g=u permissions
#   - USER directive set in final stages after file copies
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim AS runtime-distroless

# Create user with GID 0 (root group) for OpenShift arbitrary UID support
# OpenShift runs containers with arbitrary UIDs in GID 0
RUN useradd -u 1001 -g 0 -d /app -s /sbin/nologin appuser && \
    mkdir -p /app && chown 1001:0 /app && chmod g=u /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/app/.local/bin:$PATH \
    PORT=8000 \
    HOME=/app

WORKDIR /app

# NOTE: USER directive moved to final stages after file copies
# This allows COPY --chown to work, then we set permissions and drop privileges

# ==============================================================================
# STAGE: runtime-slim
# Slim Python runtime (for test variant, needs shell)
#
# OPENSHIFT COMPATIBILITY:
#   - User created with GID 0 (root group) for arbitrary UID support
#   - /app owned by 1001:0 with g=u permissions
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim AS runtime-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TESTING=true \
    HOME=/app

WORKDIR /app

# Install runtime dependencies for tests (curl for health checks)
# Create user with GID 0 for OpenShift arbitrary UID support
RUN --mount=type=cache,target=/var/cache/apt,id=apt-cache-runtime-slim,sharing=private \
    --mount=type=cache,target=/var/lib/apt,id=apt-lib-runtime-slim,sharing=private \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -u 1001 -g 0 -d /app -s /bin/bash appuser \
    && chown 1001:0 /app && chmod g=u /app

# ==============================================================================
# FINAL STAGE: base variant (distroless)
# ==============================================================================
FROM runtime-distroless AS final-base

# Copy virtual environment from build stage
# Use 1001:0 ownership for OpenShift arbitrary UID support
COPY --from=build-base --chown=1001:0 /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

# Copy application code with OpenShift-compatible ownership
COPY --chown=1001:0 src/ ./src/
COPY --chown=1001:0 pyproject.toml ./

# Drop privileges - use numeric UID for OpenShift compatibility
# Note: --chown=1001:0 already sets correct ownership, no need for recursive chmod
USER 1001

# Metadata
LABEL org.opencontainers.image.title="MCP Server LangGraph (Base)"
LABEL org.opencontainers.image.description="Lightweight MCP server with API-based embeddings"
LABEL org.opencontainers.image.variant="base"
LABEL org.opencontainers.image.size="~200MB"
LABEL io.openshift.tags="mcp,langgraph,llm,agent"
LABEL io.k8s.description="MCP server with LangGraph for AI agent orchestration"

EXPOSE 8000

# Use Python from venv
CMD ["python", "-m", "mcp_server_langgraph.mcp.server_streamable"]

# ==============================================================================
# FINAL STAGE: full variant (distroless)
# ==============================================================================
FROM runtime-distroless AS final-full

# Copy virtual environment from build stage
# Use 1001:0 ownership for OpenShift arbitrary UID support
COPY --from=build-full --chown=1001:0 /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

# Copy application code with OpenShift-compatible ownership
COPY --chown=1001:0 src/ ./src/
COPY --chown=1001:0 pyproject.toml ./

# Drop privileges - use numeric UID for OpenShift compatibility
# Note: --chown=1001:0 already sets correct ownership, no need for recursive chmod
USER 1001

# Metadata
LABEL org.opencontainers.image.title="MCP Server LangGraph (Full)"
LABEL org.opencontainers.image.description="Complete MCP server with local embeddings support"
LABEL org.opencontainers.image.variant="full"
LABEL org.opencontainers.image.size="~1.2GB"
LABEL io.openshift.tags="mcp,langgraph,llm,agent,embeddings"
LABEL io.k8s.description="MCP server with LangGraph and local embeddings support"

EXPOSE 8000

# Use Python from venv
CMD ["python", "-m", "mcp_server_langgraph.mcp.server_streamable"]

# ==============================================================================
# FINAL STAGE: test variant (slim, with shell)
# ==============================================================================
FROM runtime-slim AS final-test

# Copy virtual environment from builder
# Use 1001:0 ownership for OpenShift arbitrary UID support
COPY --from=build-test --chown=1001:0 /app/.venv /app/.venv

# Copy application and test code with OpenShift-compatible ownership
COPY --chown=1001:0 src/ ./src/
COPY --chown=1001:0 tests/ ./tests/
COPY --chown=1001:0 pyproject.toml ./

# Copy additional directories required by tests
# NOTE: Per ADR-0053, scripts/ and deployments/ are NOT copied to the Docker image.
# Meta-tests that require these directories run on the host, not in the container.
# Only adr/ is copied for documentation purposes.
COPY --chown=1001:0 adr/ ./adr/

# Drop privileges - use numeric UID for OpenShift compatibility
# Note: --chown=1001:0 already sets correct ownership, no need for recursive chmod
USER 1001

# Set PATH to use virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Disable observability during tests
ENV ENABLE_TRACING=false \
    ENABLE_METRICS=false \
    ENABLE_CONSOLE_EXPORT=false

# Metadata
LABEL org.opencontainers.image.title="MCP Server LangGraph (Test)"
LABEL org.opencontainers.image.description="Test runner with dev dependencies"
LABEL org.opencontainers.image.variant="test"
LABEL org.opencontainers.image.size="~800MB"
LABEL io.openshift.tags="mcp,langgraph,test"
LABEL io.k8s.description="Test runner for MCP server with dev dependencies"

# Default command runs integration tests
CMD ["/app/.venv/bin/pytest", "-m", "integration", "-v", "--tb=short"]

# No health check for test variant
HEALTHCHECK NONE
