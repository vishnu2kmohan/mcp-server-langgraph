#!/bin/bash
# =============================================================================
# MyPy Daemon Wrapper for Pre-Push Hook
# =============================================================================
# Uses dmypy (MyPy daemon) locally for incremental type checking (~1-3s warm).
# Falls back to standard mypy in CI (daemon doesn't persist across jobs).
#
# Usage:
#   bash scripts/hooks/dmypy_check.sh          # Auto-detect CI/local
#   CI=true bash scripts/hooks/dmypy_check.sh   # Force CI mode (standard mypy)
#
# Stale lockfile recovery:
#   If dmypy start fails (stale .dmypy.json), kills the daemon and retries.
#   Manual reset: uv run --frozen dmypy kill
#
# =============================================================================

set -e

# CI: Use standard mypy (no daemon persistence across jobs)
# Local: Use dmypy for incremental checking
if [[ "${CI:-}" == "true" || "${GITHUB_ACTIONS:-}" == "true" ]]; then
    uv run --frozen mypy src/mcp_server_langgraph \
        --config-file=pyproject.toml --show-error-codes --pretty
    exit $?
fi

# Start daemon if not running, then incremental check
# Handle stale lockfile: kill existing daemon first if start fails
# NOTE: All mypy flags must be passed to 'dmypy start', NOT 'dmypy check'.
# 'dmypy check' only accepts file/directory positional args — anything after
# '--' is treated as a filename, causing 'can't read file' errors.
if ! uv run --frozen dmypy status >/dev/null 2>&1; then
    if ! uv run --frozen dmypy start -- \
        --config-file=pyproject.toml --show-error-codes --pretty 2>/dev/null; then
        echo "dmypy start failed (stale lockfile?), killing and retrying..."
        uv run --frozen dmypy kill 2>/dev/null || true
        uv run --frozen dmypy start -- \
            --config-file=pyproject.toml --show-error-codes --pretty
    fi
fi

uv run --frozen dmypy check src/mcp_server_langgraph
