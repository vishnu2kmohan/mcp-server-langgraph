#!/bin/bash
# Test utilities - source at runtime (zero context cost)
# Usage: source .claude/lib/test_utils.sh
# shellcheck disable=SC2086  # Intentional word splitting for extra_args
set -euo pipefail

# Run pytest with parallel execution by default
# Args:
#   $1 - pytest markers (optional, e.g., "unit", "integration")
#   $2 - extra args (optional, e.g., "-v --tb=short")
run_pytest_parallel() {
    local markers="${1:-}"
    local extra_args="${2:-}"

    # Sequential mode: skip all xdist logic, run without -n flag
    if [[ "${PYTEST_SEQUENTIAL:-}" == "1" ]]; then
        echo "INFO: Running in sequential mode (PYTEST_SEQUENTIAL=1)" >&2
        if [[ -n "$markers" ]]; then
            uv run --frozen pytest -m "$markers" $extra_args
        else
            uv run --frozen pytest $extra_args
        fi
        return
    fi

    # Check for pytest-xdist availability
    if ! uv run --frozen python -c "import xdist" 2>/dev/null; then
        echo "WARNING: pytest-xdist not installed. Running sequentially." >&2
        if [[ -n "$markers" ]]; then
            uv run --frozen pytest -m "$markers" $extra_args
        else
            uv run --frozen pytest $extra_args
        fi
        return
    fi

    # Parallel mode: use -n with worker count
    local workers="${PYTEST_WORKERS:-auto}"

    if [[ -n "$markers" ]]; then
        uv run --frozen pytest -n "$workers" -m "$markers" $extra_args
    else
        uv run --frozen pytest -n "$workers" $extra_args
    fi
}

# Run npm tests with parallel worker pool
# Args:
#   $@ - extra args passed to npm test (or empty for full suite)
# Full suite: delegates to sharded runner to prevent OOM (787+ test files)
# Targeted files: uses direct vitest via npm test --pool=threads
run_npm_test_parallel() {
    local frontend_dir="src/mcp_server_langgraph/studio/frontend"

    # Verify directory exists
    if [[ ! -d "$frontend_dir" ]]; then
        echo "ERROR: Frontend directory not found: $frontend_dir" >&2
        return 1
    fi

    # Check npm availability
    command -v npm >/dev/null 2>&1 || { echo "ERROR: npm not found" >&2; return 1; }

    # Run in subshell to avoid changing caller's working directory
    (
        cd "$frontend_dir" || exit 1

        if [[ $# -eq 0 ]]; then
            # Full suite: use sharded runner to prevent OOM
            # NOTE: Use default 150 shards (not --fast/75) to stay within 4GB heap budget
            # 787 files / 150 shards = ~5 files/shard = ~2GB (safe); 75 shards = ~10.5 files = ~4.2GB (OOM risk)
            bash scripts/run-tests-sharded.sh --parallel
        else
            # Targeted files/patterns: direct vitest is safe
            npm test -- --run --pool=threads "$@"
        fi
    )
}

# Run unit tests only (parallel by default)
run_unit_tests() {
    run_pytest_parallel "unit" "${1:-}"
}

# Run integration tests only (parallel by default)
run_integration_tests() {
    run_pytest_parallel "integration" "${1:-}"
}
