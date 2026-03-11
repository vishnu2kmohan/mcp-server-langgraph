#!/bin/bash
# =============================================================================
# Parallel Security Scan Wrapper
# =============================================================================
# Runs all security scanning tools concurrently as background jobs.
# Resource-adaptive: adjusts concurrency based on CPU/memory and environment.
#
# Tools: bandit, trivy (k8s, helm, helm-full, terraform), semgrep
#
# Usage:
#   bash scripts/hooks/parallel_security_scan.sh           # Normal run
#   SECURITY_SCAN_DRY_RUN=1 bash scripts/hooks/parallel_security_scan.sh  # Dry-run
#
# Environment variables:
#   SKIP_BANDIT=1       - Skip bandit (local only, ignored in CI)
#   SKIP_TRIVY=1        - Skip all trivy scans (local only, ignored in CI)
#   SKIP_SEMGREP=1      - Skip semgrep (local only, ignored in CI)
#   SECURITY_SCAN_DRY_RUN=1 - Show config without running scans
# =============================================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# -----------------------------------------------------------------------------
# Cross-platform resource detection
# -----------------------------------------------------------------------------
get_cpu_count() {
    nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4
}

# -----------------------------------------------------------------------------
# Resource-adaptive concurrency
# -----------------------------------------------------------------------------
cpu_count=$(get_cpu_count)

if [[ "${CI:-}" == "true" || "${GITHUB_ACTIONS:-}" == "true" ]]; then
    MAX_CONCURRENT=2  # CI: 16GB shared with other processes
    # Ignore SKIP_* env vars in CI to prevent silent security bypass
    unset SKIP_BANDIT SKIP_TRIVY SKIP_SEMGREP 2>/dev/null || true
else
    MAX_CONCURRENT=$((cpu_count > 6 ? 6 : cpu_count))  # Local: up to 6
fi

# -----------------------------------------------------------------------------
# Dry-run mode
# -----------------------------------------------------------------------------
if [[ "${SECURITY_SCAN_DRY_RUN:-}" == "1" ]]; then
    echo "=== Security Scan Configuration (dry-run) ==="
    echo "max_concurrent=$MAX_CONCURRENT"
    echo "cpu_count=$cpu_count"
    echo "ci_mode=${CI:-false}"
    echo "skip_bandit=${SKIP_BANDIT:-0}"
    echo "skip_trivy=${SKIP_TRIVY:-0}"
    echo "skip_semgrep=${SKIP_SEMGREP:-0}"
    echo "tools: bandit, trivy-k8s, trivy-helm, trivy-helm-full, trivy-terraform, semgrep"
    exit 0
fi

# -----------------------------------------------------------------------------
# Signal handling: cleanup child processes on interruption
# -----------------------------------------------------------------------------
declare -a active_pids=()
log_dir=$(mktemp -d)

cleanup() {
    for pid in "${all_pids[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    wait 2>/dev/null || true
    rm -rf "$log_dir"
}
trap cleanup EXIT INT TERM

# -----------------------------------------------------------------------------
# Tool runner: execute a scan in the background
# -----------------------------------------------------------------------------
declare -A tool_exit_codes
declare -A tool_pids
declare -a tool_names=()
declare -a all_pids=()

run_tool() {
    local name="$1"
    shift
    local log_file="$log_dir/${name}.log"
    tool_names+=("$name")

    (
        "$@" > "$log_file" 2>&1
    ) &
    local pid=$!
    tool_pids["$name"]=$pid
    active_pids+=("$pid")
    all_pids+=("$pid")
}

# -----------------------------------------------------------------------------
# Concurrency limiter: wait for a slot when at max_concurrent
# -----------------------------------------------------------------------------
wait_for_slot() {
    while [[ ${#active_pids[@]} -ge $MAX_CONCURRENT ]]; do
        local new_pids=()
        for pid in "${active_pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then
                new_pids+=("$pid")
            fi
        done
        active_pids=("${new_pids[@]}")
        if [[ ${#active_pids[@]} -ge $MAX_CONCURRENT ]]; then
            sleep 0.5
        fi
    done
}

# -----------------------------------------------------------------------------
# Security scan tools
# -----------------------------------------------------------------------------
echo "=== Parallel Security Scan ==="
echo "Concurrency: $MAX_CONCURRENT (CPUs: $cpu_count)"
echo ""

# 1. Bandit
if [[ "${SKIP_BANDIT:-0}" != "1" ]]; then
    wait_for_slot
    run_tool "bandit" bash -c "
        cd '$REPO_ROOT' && \
        if command -v bandit &>/dev/null; then
            bandit -lll --skip B608 -r src/ 2>&1
        elif [ -x .venv/bin/bandit ]; then
            .venv/bin/bandit -lll --skip B608 -r src/ 2>&1
        else
            echo 'ERROR: bandit not found'
            exit 1
        fi
    "
    echo "  Started: bandit"
else
    echo "  Skipped: bandit (SKIP_BANDIT=1)"
fi

# 2. Trivy - K8s manifests
if [[ "${SKIP_TRIVY:-0}" != "1" ]]; then
    wait_for_slot
    run_tool "trivy-k8s" bash -c "
        cd '$REPO_ROOT' && \
        if ! command -v trivy &>/dev/null; then
            echo 'ERROR: trivy not found'
            exit 1
        fi
        trivy config deployments --severity CRITICAL,HIGH --skip-dirs '**/charts' --exit-code 1 --quiet 2>&1
    "
    echo "  Started: trivy-k8s"

    # 3. Trivy - Helm charts
    wait_for_slot
    run_tool "trivy-helm" bash -c "
        cd '$REPO_ROOT/deployments/helm/mcp-server-langgraph' && \
        if ! command -v trivy &>/dev/null; then
            echo 'ERROR: trivy not found'
            exit 1
        fi
        trivy config . --severity CRITICAL,HIGH --exit-code 1 --quiet --skip-dirs charts 2>&1
    "
    echo "  Started: trivy-helm"

    # 4. Trivy - Helm full scan (with subcharts)
    wait_for_slot
    run_tool "trivy-helm-full" bash -c "
        cd '$REPO_ROOT' && \
        if [ -x scripts/security/scan_helm_templates.sh ]; then
            bash scripts/security/scan_helm_templates.sh 2>&1
        else
            echo 'ERROR: scripts/security/scan_helm_templates.sh not found'
            exit 1
        fi
    "
    echo "  Started: trivy-helm-full"
else
    echo "  Skipped: trivy-k8s, trivy-helm, trivy-helm-full (SKIP_TRIVY=1)"
fi

# 5. Trivy - Terraform IaC security scan (replaces checkov)
if [[ "${SKIP_TRIVY:-0}" != "1" ]]; then
    wait_for_slot
    run_tool "trivy-terraform" bash -c "
        cd '$REPO_ROOT' && \
        if ! command -v trivy &>/dev/null; then
            echo 'ERROR: trivy not found'
            exit 1
        fi
        trivy config terraform/ --severity CRITICAL,HIGH --exit-code 1 --quiet \
            --ignorefile terraform/.trivyignore 2>&1
    "
    echo "  Started: trivy-terraform"
else
    echo "  Skipped: trivy-terraform (SKIP_TRIVY=1)"
fi

# 6. Semgrep
if [[ "${SKIP_SEMGREP:-0}" != "1" ]]; then
    wait_for_slot
    run_tool "semgrep" bash -c "
        cd '$REPO_ROOT' && \
        if [ -x '.venv/bin/semgrep' ]; then
            SEMGREP='.venv/bin/semgrep'
        elif command -v semgrep &>/dev/null; then
            SEMGREP='semgrep'
        else
            echo 'ERROR: semgrep not found'
            exit 1
        fi
        \$SEMGREP scan --config auto --error --severity ERROR --quiet src/ scripts/ 2>&1
    "
    echo "  Started: semgrep"
else
    echo "  Skipped: semgrep (SKIP_SEMGREP=1)"
fi

echo ""
echo "Waiting for scans to complete..."

# -----------------------------------------------------------------------------
# Collect results
# -----------------------------------------------------------------------------
overall_exit=0

for name in "${tool_names[@]}"; do
    pid="${tool_pids[$name]}"
    if wait "$pid" 2>/dev/null; then
        exit_code=0
    else
        exit_code=$?
    fi
    tool_exit_codes["$name"]=$exit_code
    if [[ $exit_code -ne 0 ]]; then
        overall_exit=1
    fi
done

# -----------------------------------------------------------------------------
# Report per-tool status
# -----------------------------------------------------------------------------
echo ""
echo "=== Security Scan Results ==="
for name in "${tool_names[@]}"; do
    code=${tool_exit_codes[$name]}
    if [[ $code -eq 0 ]]; then
        echo "  PASS: $name"
    else
        echo "  FAIL: $name (exit code: $code)"
        echo "  --- $name output ---"
        cat "$log_dir/${name}.log" 2>/dev/null || true
        echo "  --- end $name ---"
    fi
done
echo ""

if [[ $overall_exit -eq 0 ]]; then
    echo "All security scans passed."
else
    echo "Some security scans failed. See output above."
fi

exit $overall_exit
