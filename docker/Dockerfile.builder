# Unified Builder Dockerfile
# ==========================
# Multi-stage build for Visual Workflow Builder
# Combines React frontend + FastAPI backend in a single container
#
# ARCHITECTURE:
#   - FastAPI serves API endpoints at /api/builder/*
#   - SPAStaticFiles serves React SPA at / with client-side routing support
#   - Health endpoint at /api/builder/health (unauthenticated for K8s probes)
#
# AUTH INTEGRATION:
#   - Keycloak for authentication (federated OIDC/OAuth2/SAML, LDAP/AD)
#   - OpenFGA for fine-grained authorization (ReBAC)
#
# OPENSHIFT COMPATIBILITY:
#   - Uses numeric UID (1001) in USER directive
#   - Files owned by UID:0 (root group) for arbitrary UID support
#   - Group permissions set with g=u for OpenShift restricted SCC
#   - See: https://developers.redhat.com/blog/2020/10/26/adapting-docker-and-kubernetes-containers-to-run-on-red-hat-openshift-container-platform
#
# USAGE:
#   docker build -f docker/Dockerfile.builder -t builder .
#   docker run -p 8001:8001 \
#     -e ENVIRONMENT=production \
#     -e KEYCLOAK_SERVER_URL=http://keycloak:8080 \
#     -e OPENFGA_API_URL=http://openfga:8080 \
#     builder
#
# PORTS:
#   8001 - FastAPI (API + SPA)
#
# REFERENCES:
#   - https://docs.astral.sh/uv/guides/integration/docker/
#   - https://hynek.me/articles/docker-uv/
#   - 12-factor app: https://12factor.net/

ARG PYTHON_VERSION=3.12

# ==============================================================================
# Stage 1: Build React Frontend
# ==============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy package files for dependency caching
COPY src/mcp_server_langgraph/builder/frontend/package*.json ./

# Install dependencies (prefer offline, skip audit for faster builds)
RUN npm ci --prefer-offline --no-audit

# Copy frontend source code
COPY src/mcp_server_langgraph/builder/frontend/ ./

# Build the production bundle
# Note: Vite outputs to ./dist by default
RUN npm run build

# ==============================================================================
# Stage 2: Python Builder - Install dependencies in isolated stage
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim AS python-builder

WORKDIR /app

# Install uv - Fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# UV environment variables for optimal Docker builds
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Copy dependency files and source code
# NOTE: uv sync needs src/ because pyproject.toml uses "packages = [..., from = 'src']"
COPY pyproject.toml uv.lock ./
COPY src/ ./src/

# Install Python dependencies (production only, no dev extras)
# --frozen: Use lockfile exactly, fail if out of sync
# --no-dev: Skip development dependencies
RUN --mount=type=cache,target=/root/.cache/uv,id=uv-cache-builder,sharing=private \
    uv sync --frozen --no-dev

# ==============================================================================
# Stage 3: Runtime - Minimal runtime image
# ==============================================================================
FROM python:${PYTHON_VERSION}-slim AS runtime

WORKDIR /app

# Install minimal system dependencies and create user BEFORE copying files
# This avoids expensive post-copy chown layer duplication
RUN --mount=type=cache,target=/var/cache/apt,id=apt-cache-builder,sharing=private \
    --mount=type=cache,target=/var/lib/apt,id=apt-lib-builder,sharing=private \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -u 1001 -g 0 -d /app -s /sbin/nologin appuser \
    && mkdir -p /app && chown 1001:0 /app && chmod g=u /app

# Copy virtual environment from builder with correct ownership
# Using --chown avoids expensive post-copy chown layer
COPY --from=python-builder --chown=1001:0 /app/.venv /app/.venv

# Copy source code with correct ownership
COPY --chown=1001:0 src/ ./src/
COPY --chown=1001:0 pyproject.toml ./

# Copy built frontend from stage 1
# Place in builder/frontend/dist to match SPAStaticFiles path expectations
COPY --from=frontend-builder --chown=1001:0 /frontend/dist ./src/mcp_server_langgraph/builder/frontend/dist/

# Drop privileges - use numeric UID for OpenShift compatibility
USER 1001

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Environment configuration (12-factor: config via env vars)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/app

# Expose API port
EXPOSE 8001

# Health check for Kubernetes probes
# Matches /api/builder/health endpoint (no auth required)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8001/api/builder/health || exit 1

# OpenShift / Kubernetes labels
LABEL io.openshift.tags="mcp,langgraph,builder,react"
LABEL io.k8s.description="Visual Workflow Builder for MCP Server LangGraph"

# Run the unified server
# --host 0.0.0.0: Bind to all interfaces (required for container networking)
# --port 8001: Builder API port
CMD ["uvicorn", "mcp_server_langgraph.builder.api.server:app", "--host", "0.0.0.0", "--port", "8001"]
