#!/bin/bash
LOGFILE="validation_audit.log"
echo "Starting validation audit at $(date)" > "$LOGFILE"

# Function to log and run
run_step() {
    NAME="$1"
    CMD="$2"
    echo "--- START: $NAME ---" >> "$LOGFILE"
    echo "Command: $CMD" >> "$LOGFILE"
    # We use eval to handle complex command strings, but carefully.
    # Output is redirected to logfile.
    eval "$CMD" >> "$LOGFILE" 2>&1
    RET=$?
    if [ $RET -eq 0 ]; then
        echo "--- SUCCESS: $NAME ---" >> "$LOGFILE"
    else
        echo "--- FAILURE: $NAME (Exit Code: $RET) ---" >> "$LOGFILE"
    fi
    echo "" >> "$LOGFILE"
}

# Phase 1
run_step "Lockfile Check" "uv lock --check"
run_step "Dependency Check" "uv pip check"
run_step "Workflow Syntax" "OTEL_SDK_DISABLED=true uv run --frozen pytest tests/meta/ci/test_workflow_syntax.py tests/meta/ci/test_workflow_security.py tests/meta/ci/test_workflow_dependencies.py tests/meta/infrastructure/test_docker_paths.py -v --tb=short"

# Phase 2
# Use --frozen to ensure lockfile-pinned versions (prevents version drift)
run_step "MyPy" "uv run --frozen mypy src/mcp_server_langgraph --no-error-summary"

# Phase 3
# Replicating scripts/run_pre_push_tests.py but WITHOUT -x
run_step "Pre-push Tests (No fail-fast)" "OTEL_SDK_DISABLED=true HYPOTHESIS_PROFILE=ci uv run --frozen pytest -n auto --testmon --tb=short -m '(unit or api or property) and not llm' tests/"

# Integration tests
run_step "Integration Tests" "./scripts/test-integration.sh"

# Phase 4
run_step "Pre-commit Hooks" "pre-commit run --all-files --hook-stage pre-push --show-diff-on-failure"

echo "Audit complete at $(date)" >> "$LOGFILE"
