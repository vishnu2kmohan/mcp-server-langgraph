#!/bin/bash
# =============================================================================
# Parallel Pre-Push Lane Orchestrator
# =============================================================================
# Runs pre-push hooks in 5 parallel lanes instead of sequentially.
# Resource-adaptive: adjusts lane concurrency based on CPU/memory/environment.
#
# Lanes:
#   1. Python Tests    - run-pre-push-tests, test validators, python-version-smoke
#   2. Frontend        - build, test, typecheck, design-system
#   3. Security        - parallel-security-scan (internally parallel)
#   4. Type Check      - mypy, code validators, dependency checks
#   5. Infra & Docs    - docker-build-smoke, helm, actionlint, docs validation
#
# Usage:
#   bash scripts/hooks/parallel_pre_push.sh                      # Normal run
#   PRE_PUSH_DRY_RUN=1 bash scripts/hooks/parallel_pre_push.sh   # Dry-run
#   PRE_PUSH_SEQUENTIAL=1 bash scripts/hooks/parallel_pre_push.sh # Sequential fallback
#
# Environment variables:
#   PRE_PUSH_DRY_RUN=1       - Show configuration without running hooks
#   PRE_PUSH_SEQUENTIAL=1    - Fall back to standard sequential pre-commit
#   FROM_REF / TO_REF        - Git refs for pre-commit (auto-detected from stdin)
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# -----------------------------------------------------------------------------
# Cross-platform resource detection
# -----------------------------------------------------------------------------
get_cpu_count() {
    nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4
}

get_free_memory_gb() {
    if command -v free &>/dev/null; then
        free -g 2>/dev/null | awk '/^Mem:/ {print $7}' || echo 8
    elif [[ "$(uname)" == "Darwin" ]]; then
        local pages_free
        pages_free=$(vm_stat 2>/dev/null | awk '/Pages free/ {print $3}' | tr -d '.' || echo 0)
        echo $(( (pages_free * 4) / 1024 / 1024 ))
    else
        echo 8
    fi
}

# -----------------------------------------------------------------------------
# Resource-adaptive lane concurrency
# -----------------------------------------------------------------------------
get_max_lanes() {
    local cpu_count
    cpu_count=$(get_cpu_count)
    local free_mem_gb
    free_mem_gb=$(get_free_memory_gb)

    if [[ "${CI:-}" == "true" || "${GITHUB_ACTIONS:-}" == "true" ]]; then
        # CI (4 vCPU / 16GB): Run 2 lanes at a time
        echo 2
    elif [[ $free_mem_gb -ge 32 && $cpu_count -ge 8 ]]; then
        echo 5  # All 5 lanes in parallel (beefy machine)
    elif [[ $free_mem_gb -ge 16 && $cpu_count -ge 4 ]]; then
        echo 3  # 3 lanes at a time
    else
        echo 2  # Conservative: 2 lanes at a time
    fi
}

MAX_LANES=$(get_max_lanes)

# -----------------------------------------------------------------------------
# Lane hook definitions
# Each lane is a list of pre-commit hook IDs
# -----------------------------------------------------------------------------

# Lane 1: Python Tests (CPU + DB)
LANE_1_NAME="python-tests"
LANE_1_HOOKS=(
    run-pre-push-tests
    validate-test-collection
    detect-dead-test-code
    validate-test-fixtures
    validate-test-isolation
    check-test-memory-safety
    check-test-environment-isolation
    validate-test-ids
    python-version-smoke-test
    feature-flags-frontend-contract
    check-openapi-sync
    validate-pytest-config
)

# Lane 2: Frontend (CPU + Mem)
LANE_2_NAME="frontend"
LANE_2_HOOKS=(
    frontend-typecheck
    frontend-build
    frontend-test
    frontend-design-system-metrics
    frontend-design-system-audit
    frontend-design-system-contract
)

# Lane 3: Security (CPU - internally parallel via wrapper)
LANE_3_NAME="security"
LANE_3_HOOKS=(
    parallel-security-scan
    security-tools-check
)

# Lane 4: Type Check + Validators (CPU)
LANE_4_NAME="type-check-validators"
LANE_4_HOOKS=(
    mypy
    validate-fast
    check-subprocess-timeout
    check-banned-imports
    check-type-checking-cast
    check-unsafe-float-patterns
    check-websocket-deprecated-patterns
    uv-lock-check
    uv-pip-check
    validate-dependency-injection
    validate-grafana-dashboards
    check-grafana-dashboard-sync
    check-mimir-rules-sync
    validate-workflow-test-deps
    check-no-create-all
    check-keycloak-theme
    check-mermaid-styling
)

# Lane 5: Infra & Docs (Docker + CLI)
LANE_5_NAME="infra-docs"
LANE_5_HOOKS=(
    docker-build-smoke-test
    actionlint-workflow-validation
    validate-github-workflows-comprehensive
    validate-gke-autopilot-compliance
    check-helm-placeholders
    helm-lint
    validate-helm-chart-deps
    validate-cloud-overlays
    validate-no-placeholders
    mintlify-broken-links-check
    validate-docs
    validate-adr-index
    check-internal-links
    terraform_validate
)

ALL_LANE_NAMES=("$LANE_1_NAME" "$LANE_2_NAME" "$LANE_3_NAME" "$LANE_4_NAME" "$LANE_5_NAME")

# Collect all lane hooks into a single flat list for drift validation
ALL_LANE_HOOKS=()
ALL_LANE_HOOKS+=("${LANE_1_HOOKS[@]}" "${LANE_2_HOOKS[@]}" "${LANE_3_HOOKS[@]}" "${LANE_4_HOOKS[@]}" "${LANE_5_HOOKS[@]}")

# -----------------------------------------------------------------------------
# Hook drift detection: ensure all pre-push hooks are assigned to a lane
# Prevents new hooks from being silently skipped after .pre-commit-config.yaml
# changes. Uses uv run for PyYAML access from the project venv.
# -----------------------------------------------------------------------------
validate_lane_coverage() {
    local config_hooks
    config_hooks=$(uv run --frozen python -c "
import yaml, sys
with open('.pre-commit-config.yaml') as f:
    cfg = yaml.safe_load(f)
hooks = set()
for repo in cfg.get('repos', []):
    for hook in repo.get('hooks', []):
        stages = hook.get('stages', ['pre-commit'])
        if 'pre-push' in stages:
            hooks.add(hook['id'])
print('\n'.join(sorted(hooks)))
" 2>/dev/null) || {
        echo "WARNING: Could not parse .pre-commit-config.yaml (PyYAML unavailable?)"
        echo "  Skipping hook drift validation. Install PyYAML: uv add --dev pyyaml"
        return 0  # Graceful degradation: warn but don't block
    }

    local lane_hooks_str
    lane_hooks_str=$(printf '%s\n' "${ALL_LANE_HOOKS[@]}" | sort -u)

    local missing=()
    while IFS= read -r hook; do
        [[ -z "$hook" ]] && continue
        if ! echo "$lane_hooks_str" | grep -qxF "$hook"; then
            missing+=("$hook")
        fi
    done <<< "$config_hooks"

    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "ERROR: Pre-push hooks not assigned to any lane: ${missing[*]}"
        echo "Add them to LANE_*_HOOKS in scripts/hooks/parallel_pre_push.sh"
        return 1
    fi
    return 0
}

# -----------------------------------------------------------------------------
# Parse git push refs from stdin (pre-push hook protocol)
# Git's pre-push hook receives: <local-ref> <local-sha> <remote-ref> <remote-sha>
# IMPORTANT: Read stdin ONCE at script start; no subsequent command should
# expect stdin from git.
# -----------------------------------------------------------------------------
parse_push_refs() {
    while read -r _local_ref local_sha _remote_ref remote_sha 2>/dev/null; do
        if [[ "$local_sha" == "0000000000000000000000000000000000000000" ]]; then
            continue  # Deleting branch — nothing to check
        fi
        if [[ "$remote_sha" == "0000000000000000000000000000000000000000" ]]; then
            # New branch — check all commits against default branch
            FROM_REF=$(git merge-base HEAD origin/main 2>/dev/null || echo "HEAD~1")
        else
            FROM_REF="$remote_sha"
        fi
        TO_REF="$local_sha"
    done
    # Fallback for manual invocation without git hook context
    FROM_REF="${FROM_REF:-HEAD~1}"
    TO_REF="${TO_REF:-HEAD}"
}

# Only parse refs if not already set via env
if [[ -z "${FROM_REF:-}" || -z "${TO_REF:-}" ]]; then
    parse_push_refs
fi

# -----------------------------------------------------------------------------
# Sequential fallback
# -----------------------------------------------------------------------------
if [[ "${PRE_PUSH_SEQUENTIAL:-}" == "1" ]]; then
    if [[ "${PRE_PUSH_DRY_RUN:-}" == "1" ]]; then
        echo "=== Pre-Push Configuration (dry-run) ==="
        echo "mode=sequential (PRE_PUSH_SEQUENTIAL=1)"
        echo "command: pre-commit run --hook-stage pre-push --from-ref $FROM_REF --to-ref $TO_REF"
        exit 0
    fi
    echo "=== Sequential Pre-Push (PRE_PUSH_SEQUENTIAL=1) ==="
    exec pre-commit run --hook-stage pre-push --from-ref "$FROM_REF" --to-ref "$TO_REF"
fi

# -----------------------------------------------------------------------------
# Dry-run mode
# -----------------------------------------------------------------------------
if [[ "${PRE_PUSH_DRY_RUN:-}" == "1" ]]; then
    cpu_count=$(get_cpu_count)
    free_mem_gb=$(get_free_memory_gb)
    echo "=== Pre-Push Lane Configuration (dry-run) ==="
    echo "max_lanes=$MAX_LANES"
    echo "cpu_count=$cpu_count"
    echo "free_memory_gb=$free_mem_gb"
    echo "ci_mode=${CI:-false}"
    echo "from_ref=$FROM_REF"
    echo "to_ref=$TO_REF"
    echo ""
    for lane_name in "${ALL_LANE_NAMES[@]}"; do
        echo "Lane: $lane_name"
        # Show hook count per lane
        case "$lane_name" in
            python-tests) echo "  hooks: ${#LANE_1_HOOKS[@]}" ;;
            frontend)     echo "  hooks: ${#LANE_2_HOOKS[@]}" ;;
            security)     echo "  hooks: ${#LANE_3_HOOKS[@]}" ;;
            type-check-validators) echo "  hooks: ${#LANE_4_HOOKS[@]}" ;;
            infra-docs)   echo "  hooks: ${#LANE_5_HOOKS[@]}" ;;
        esac
    done
    echo ""
    echo "Hook drift validation:"
    if validate_lane_coverage; then
        echo "  All pre-push hooks are assigned to lanes."
    fi
    exit 0
fi

# -----------------------------------------------------------------------------
# Hook drift validation: fail early if new hooks are unassigned
# -----------------------------------------------------------------------------
validate_lane_coverage || exit 1

# -----------------------------------------------------------------------------
# Signal handling: cleanup child processes on interruption
# Logs persist at /tmp/pre-push-lanes/ for post-hoc diagnosis.
# -----------------------------------------------------------------------------
declare -a lane_pids=()
log_dir="/tmp/pre-push-lanes"
rm -rf "$log_dir"
mkdir -p "$log_dir"

cleanup() {
    for pid in "${lane_pids[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    # Logs are intentionally NOT deleted — persist for post-hoc diagnosis.
    # Convention: /tmp/{tool}-{stage}.log (see .claude/rules/context-efficiency.md)
}
trap cleanup EXIT INT TERM

# -----------------------------------------------------------------------------
# Lane runner: execute a lane's hooks via pre-commit with isolated cache
# pre-commit 4.x uses positional args: `pre-commit run HOOK_ID`
# Each hook must be run individually (no multi-hook flag).
# -----------------------------------------------------------------------------
run_lane() {
    local lane_name="$1"
    shift
    local hooks=("$@")
    local log_file="$log_dir/${lane_name}.log"

    # Isolate PRE_COMMIT_HOME per lane to prevent concurrent cache corruption
    local lane_cache="$HOME/.cache/pre-commit-lane-${lane_name}"
    mkdir -p "$lane_cache"

    # Isolate GIT_INDEX_FILE per lane to prevent concurrent index.lock contention.
    # pre-commit internally runs `git write-tree` which takes an exclusive lock on
    # the index. Without isolation, concurrent lanes deadlock on index.lock.
    local lane_index="$log_dir/.git-index-${lane_name}"
    cp "${GIT_INDEX_FILE:-$(git rev-parse --git-dir)/index}" "$lane_index" 2>/dev/null || true

    (
        echo "=== Lane: $lane_name ===" > "$log_file"
        echo "Started: $(date '+%H:%M:%S')" >> "$log_file"
        echo "Hooks: ${#hooks[@]}" >> "$log_file"
        echo "" >> "$log_file"

        local lane_exit=0
        for hook in "${hooks[@]}"; do
            echo "--- Running: $hook ---" >> "$log_file"
            GIT_INDEX_FILE="$lane_index" \
            PRE_COMMIT_HOME="$lane_cache" \
                pre-commit run "$hook" --hook-stage pre-push \
                --from-ref "$FROM_REF" --to-ref "$TO_REF" >> "$log_file" 2>&1
            local hook_exit=$?
            if [[ $hook_exit -ne 0 ]]; then
                echo "  FAILED (exit code: $hook_exit)" >> "$log_file"
                lane_exit=1
            fi
        done

        echo "" >> "$log_file"
        echo "Finished: $(date '+%H:%M:%S') (exit code: $lane_exit)" >> "$log_file"
        exit $lane_exit
    ) &
    lane_pids+=($!)
}

# -----------------------------------------------------------------------------
# Concurrency limiter for lane execution
# -----------------------------------------------------------------------------
wait_for_lane_slot() {
    while [[ ${#lane_pids[@]} -ge $MAX_LANES ]]; do
        local new_pids=()
        for pid in "${lane_pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                new_pids+=("$pid")
            fi
        done
        lane_pids=("${new_pids[@]}")
        if [[ ${#lane_pids[@]} -ge $MAX_LANES ]]; then
            sleep 1
        fi
    done
}

# -----------------------------------------------------------------------------
# Execute lanes
# -----------------------------------------------------------------------------
echo "=== Parallel Pre-Push Lane Orchestrator ==="
echo "Max concurrent lanes: $MAX_LANES"
echo "Refs: $FROM_REF..$TO_REF"
echo ""

declare -A lane_exit_codes
declare -a lane_order=()

start_time=$(date +%s)

# Frontend shard concurrency: reduce when running in parallel with other lanes.
# Default 8 accounts for Vitest internal parallelism (maxWorkers=2 per shard, so
# 8 shards × 2 workers = 16 CPU-bound processes on 16-core machine).
# When 5 lanes are active, 8 Python workers + 4 shards + mypy + security scans
# exceed available CPU and memory. Cap at 1/6 standalone limit (min 2). 8/6≈1→min 2.
FRONTEND_SHARD_MAX=${VITEST_SHARD_CONCURRENCY_MAX:-8}
if [[ $MAX_LANES -gt 1 ]]; then
    FRONTEND_SHARD_MAX=$(( FRONTEND_SHARD_MAX / 6 ))
    [[ $FRONTEND_SHARD_MAX -lt 2 ]] && FRONTEND_SHARD_MAX=2
fi

# Launch lanes with concurrency limiting
for lane_idx in 1 2 3 4 5; do
    wait_for_lane_slot

    case $lane_idx in
        1) run_lane "$LANE_1_NAME" "${LANE_1_HOOKS[@]}"; lane_order+=("$LANE_1_NAME") ;;
        2) export VITEST_SHARD_CONCURRENCY_MAX=$FRONTEND_SHARD_MAX
           run_lane "$LANE_2_NAME" "${LANE_2_HOOKS[@]}"; lane_order+=("$LANE_2_NAME") ;;
        3) run_lane "$LANE_3_NAME" "${LANE_3_HOOKS[@]}"; lane_order+=("$LANE_3_NAME") ;;
        4) run_lane "$LANE_4_NAME" "${LANE_4_HOOKS[@]}"; lane_order+=("$LANE_4_NAME") ;;
        5) run_lane "$LANE_5_NAME" "${LANE_5_HOOKS[@]}"; lane_order+=("$LANE_5_NAME") ;;
    esac

    echo "  Started lane $lane_idx: ${lane_order[-1]}"
done

echo ""
echo "Waiting for all lanes to complete..."

# Collect results (disable set -e: wait returns lane's exit code, which may be non-zero)
overall_exit=0
for i in "${!lane_order[@]}"; do
    name="${lane_order[$i]}"
    pid="${lane_pids[$i]}"
    wait "$pid" 2>/dev/null && exit_code=0 || exit_code=$?
    lane_exit_codes["$name"]=$exit_code
    if [[ $exit_code -ne 0 ]]; then
        overall_exit=1
    fi
done

end_time=$(date +%s)
elapsed=$((end_time - start_time))

# -----------------------------------------------------------------------------
# Report per-lane status
# -----------------------------------------------------------------------------
echo ""
echo "=== Pre-Push Results (${elapsed}s) ==="
for name in "${lane_order[@]}"; do
    code=${lane_exit_codes[$name]}
    if [[ $code -eq 0 ]]; then
        echo "  PASS: $name"
    else
        echo "  FAIL: $name (exit code: $code)"
        echo "  --- $name output ---"
        cat "$log_dir/${name}.log" 2>/dev/null || true
        echo "  --- end $name ---"
        echo ""
    fi
done
echo ""

echo "Lane logs: $log_dir/"
if [[ $overall_exit -eq 0 ]]; then
    echo "All pre-push lanes passed."
else
    echo "Some pre-push lanes failed. See output above or inspect: ls $log_dir/"
fi

exit $overall_exit
