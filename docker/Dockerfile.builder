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
# Stage 2: Python Runtime with FastAPI + SPAStaticFiles
# ==============================================================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install minimal system dependencies
# curl: health checks
# ca-certificates: HTTPS for auth providers
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv - Fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# UV environment variables for optimal Docker builds
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies (production only, no dev extras)
# --frozen: Use lockfile exactly, fail if out of sync
# --no-dev: Skip development dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/

# Copy built frontend from stage 1
# Place in builder/frontend/dist to match SPAStaticFiles path expectations
COPY --from=frontend-builder /frontend/dist ./src/mcp_server_langgraph/builder/frontend/dist/

# Create non-root user for security (DS002 compliance)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Environment configuration (12-factor: config via env vars)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose API port
EXPOSE 8001

# Health check for Kubernetes probes
# Matches /api/builder/health endpoint (no auth required)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8001/api/builder/health || exit 1

# Run the unified server
# --host 0.0.0.0: Bind to all interfaces (required for container networking)
# --port 8001: Builder API port
CMD ["uvicorn", "mcp_server_langgraph.builder.api.server:app", "--host", "0.0.0.0", "--port", "8001"]
