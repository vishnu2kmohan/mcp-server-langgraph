# ==============================================================================
# Variables
# ==============================================================================
# Use UV_RUN for all Python commands with --frozen for reproducible builds
# The --frozen flag ensures:
# 1. Lockfile is not modified during execution
# 2. Fails if lockfile is out of sync with pyproject.toml
# 3. Consistent behavior between local development and CI
# Regression Prevention (2025-11-16): test-regression needs dev dependencies
# (schemathesis, freezegun, kubernetes, toml, black, psutil, flake8, isort)
UV_RUN := uv run --frozen
PYTEST := $(UV_RUN) pytest
DOCKER_COMPOSE := docker compose
COV_SRC := src/mcp_server_langgraph
COV_OPTIONS := --cov=$(COV_SRC)
