#!/bin/bash
# =============================================================================
# Sharded Test Runner for OOM Prevention
# =============================================================================
# This script runs tests in shards using Vitest's native --shard feature
# to prevent OOM errors when running the full test suite.
#
# Usage:
#   ./scripts/run-tests-sharded.sh                  # Run all shards sequentially (100 shards)
#   ./scripts/run-tests-sharded.sh --parallel       # RECOMMENDED: Run shards in parallel (~5-10min)
#   ./scripts/run-tests-sharded.sh --fast           # Fast mode: 50 shards for quick iteration
#   ./scripts/run-tests-sharded.sh --shard 1        # Run specific shard (1-100)
#   ./scripts/run-tests-sharded.sh --count 50       # Custom shard count
#   ./scripts/run-tests-sharded.sh --parallel 4     # Run 4 shards in parallel
#
# Parallel Mode:
#   --parallel [N]    Run N shards concurrently (default: auto-detect based on memory)
#                     Auto-detect formula: min(free_memory_gb * 0.8 / 4, cpu_count / 2, 8)
#                     This ensures each shard has 4GB+ memory headroom
#
# Why sharding?
# - jsdom + React Testing Library consumes ~300-500MB per test file
# - Vitest workers accumulate memory over time due to module cache
# - Running 400+ tests at once can consume 16GB+ and OOM
# - Sharding restarts Node.js between shards, clearing all memory
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Shard Count Calculation
# =============================================================================
# Memory budget: 4GB heap per shard (safe for most systems)
# Memory per test file: ~300-500MB (jsdom + React Testing Library + MSW)
# Safe files per shard: 4GB / 400MB = ~10 files
# With 626 test files, need ~63 shards minimum
#
# Using 100 shards as default (optimized from 200):
# - 626 files / 100 shards = ~6 files per shard
# - 6 files × 400MB = 2.4GB per shard (safe for 4GB limit)
# - Still accounts for heavy tests that use 800MB+ each
#
# Presets:
#   --count 100  - Default: balanced speed/safety (~25min sequential)
#   --count 50   - Fast: for quick iteration (~12min sequential)
#   --count 200  - Safe: for memory-constrained systems (~50min sequential)
#   --parallel   - Recommended: auto-concurrent execution (~5-10min)
#
# Known heavy tests (800MB+ each):
# - session-hooks-integration.test.ts
# - StudioShellLayout.*.test.tsx
# - useMCPConnection.test.ts
# - AlertDetailPanel.test.tsx
# - CanvasShortcutsMenu.test.tsx
#
# Trade-off: 100 shards × 15s overhead = ~25min sequential
# Recommended: Use --parallel for fastest execution (~5-10min)
SHARD_COUNT=100

run_shard() {
    local shard_num=$1
    local total_shards=$2
    local max_retries=2
    local retry=0

    while [ $retry -le $max_retries ]; do
        if [ $retry -gt 0 ]; then
            echo -e "${YELLOW}=== Retrying Shard $shard_num/$total_shards (attempt $((retry + 1))/$((max_retries + 1))) ===${NC}"
            # Increase heap for retry attempts (OOM mitigation)
            local heap_size=$((4096 + retry * 2048))
        else
            echo -e "${YELLOW}=== Running Shard $shard_num/$total_shards ===${NC}"
            local heap_size=4096
        fi

        # Run with single fork and adaptive heap to prevent OOM
        VITEST_HEAP_SIZE=$heap_size VITEST_MAX_FORKS=1 \
            NODE_OPTIONS="--max-old-space-size=$heap_size --expose-gc" \
            npm run test:single -- --shard="$shard_num/$total_shards" 2>&1 && {
            echo -e "${GREEN}Shard $shard_num/$total_shards completed${NC}"
            echo ""
            return 0
        }

        retry=$((retry + 1))
        if [ $retry -le $max_retries ]; then
            echo -e "${YELLOW}Shard failed, will retry with more heap...${NC}"
            sleep 2
        fi
    done

    echo -e "${RED}Shard $shard_num/$total_shards failed after $((max_retries + 1)) attempts${NC}"
    return 1
}

# =============================================================================
# Parallel Execution
# =============================================================================

# Calculate optimal parallel concurrency based on available resources
get_optimal_concurrency() {
    # Get free memory in GB
    local free_mem_kb
    if command -v free &> /dev/null; then
        free_mem_kb=$(free -k | awk '/^Mem:/ {print $7}')
    elif [[ "$(uname)" == "Darwin" ]]; then
        # macOS uses vm_stat
        local pages_free=$(vm_stat | awk '/Pages free/ {print $3}' | tr -d '.')
        free_mem_kb=$((pages_free * 4))  # 4KB pages
    else
        free_mem_kb=8000000  # Default 8GB assumption
    fi
    local free_mem_gb=$((free_mem_kb / 1024 / 1024))

    # Get CPU count
    local cpu_count
    if command -v nproc &> /dev/null; then
        cpu_count=$(nproc)
    else
        cpu_count=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
    fi

    # Calculate limits
    # Memory limit: Use 80% of free memory, 4GB per concurrent shard
    local mem_limit=$((free_mem_gb * 80 / 100 / 4))
    [[ $mem_limit -lt 1 ]] && mem_limit=1

    # CPU limit: Use half of CPUs (shards are I/O bound, not CPU bound)
    local cpu_limit=$((cpu_count / 2))
    [[ $cpu_limit -lt 1 ]] && cpu_limit=1

    # Hard cap at 8 to prevent overwhelming the system
    local hard_limit=8

    # Return minimum of all limits
    local optimal=$mem_limit
    [[ $cpu_limit -lt $optimal ]] && optimal=$cpu_limit
    [[ $hard_limit -lt $optimal ]] && optimal=$hard_limit

    echo "$optimal"
}

# Run a single shard for parallel mode (outputs to file, returns exit code)
run_shard_parallel() {
    local shard_num=$1
    local total_shards=$2
    local log_file=$3

    # Clear inherited traps - this runs in a subshell and shouldn't trigger parent's cleanup
    trap - EXIT INT TERM

    # Run shard and capture output
    run_shard "$shard_num" "$total_shards" > "$log_file" 2>&1
    return $?
}

# Run all shards in parallel with job control
run_shards_parallel() {
    local total_shards=$1
    local concurrency=$2

    echo -e "${BLUE}=== Running $total_shards shards with concurrency=$concurrency ===${NC}"
    echo ""

    # Disable set -e for this function - we do our own error handling
    set +e

    # Create temp directory for logs
    local log_dir
    log_dir=$(mktemp -d)

    # Track running jobs and their shard numbers
    declare -A running_jobs  # job_pid -> shard_num
    declare -A exit_codes    # pid -> exit_code
    local failed_shards=()
    local completed=0
    local next_shard=1

    # Cleanup function to kill children and cleanup temp dir
    cleanup() {
        local exit_code=$?
        echo -e "\n${YELLOW}Cleaning up...${NC}"
        # Kill any remaining child processes
        for pid in "${!running_jobs[@]}"; do
            kill "$pid" 2>/dev/null || true
        done
        # Wait for them to actually exit
        wait 2>/dev/null || true
        # Remove temp dir (unless we had failures)
        if [[ ${#failed_shards[@]} -eq 0 ]]; then
            rm -rf "$log_dir"
        fi
        exit $exit_code
    }
    trap cleanup EXIT INT TERM

    # Start initial batch
    while [[ ${#running_jobs[@]} -lt $concurrency && $next_shard -le $total_shards ]]; do
        local log_file="$log_dir/shard-$next_shard.log"
        run_shard_parallel "$next_shard" "$total_shards" "$log_file" &
        running_jobs[$!]=$next_shard
        echo -e "${YELLOW}Started shard $next_shard/$total_shards (pid $!)${NC}"
        ((next_shard++))
    done

    # Wait for jobs to complete and start new ones
    while [[ ${#running_jobs[@]} -gt 0 ]]; do
        # Wait for any job to complete using busy-wait (compatible with all bash versions)
        local finished_pid=""
        while [[ -z "$finished_pid" ]]; do
            for pid in "${!running_jobs[@]}"; do
                if ! kill -0 "$pid" 2>/dev/null; then
                    # Process has exited, get its exit code
                    wait "$pid" 2>/dev/null
                    exit_codes[$pid]=$?
                    finished_pid=$pid
                    break
                fi
            done
            [[ -z "$finished_pid" ]] && sleep 0.5
        done

        # Get exit code from stored values (set in the wait loop above)
        local exit_code=${exit_codes[$finished_pid]:-1}
        local finished_shard=${running_jobs[$finished_pid]}
        unset "running_jobs[$finished_pid]"
        unset "exit_codes[$finished_pid]"
        ((completed++))

        if [[ $exit_code -eq 0 ]]; then
            echo -e "${GREEN}✓ Shard $finished_shard completed ($completed/$total_shards)${NC}"
        else
            echo -e "${RED}✗ Shard $finished_shard failed ($completed/$total_shards)${NC}"
            failed_shards+=("$finished_shard")
            # Show last few lines of log for failed shard
            local log_file="$log_dir/shard-$finished_shard.log"
            if [[ -f "$log_file" ]]; then
                echo -e "${RED}--- Last 10 lines of shard $finished_shard log ---${NC}"
                tail -10 "$log_file"
                echo -e "${RED}--- End of log ---${NC}"
            fi
        fi

        # Start next shard if available
        if [[ $next_shard -le $total_shards ]]; then
            local log_file="$log_dir/shard-$next_shard.log"
            run_shard_parallel "$next_shard" "$total_shards" "$log_file" &
            running_jobs[$!]=$next_shard
            echo -e "${YELLOW}Started shard $next_shard/$total_shards (pid $!)${NC}"
            ((next_shard++))
        fi
    done

    echo ""
    echo "=== Parallel Test Summary ==="
    if [[ ${#failed_shards[@]} -eq 0 ]]; then
        echo -e "${GREEN}All $total_shards shards passed!${NC}"
        return 0
    else
        echo -e "${RED}Failed shards (${#failed_shards[@]}/$total_shards): ${failed_shards[*]}${NC}"
        echo -e "${YELLOW}Full logs available in: $log_dir${NC}"
        trap - EXIT  # Don't clean up logs on failure
        return 1
    fi
}

# =============================================================================
# Argument Parsing
# =============================================================================

# Parse arguments
SPECIFIC_SHARD=""
PARALLEL_MODE=""
PARALLEL_CONCURRENCY=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --shard)
            SPECIFIC_SHARD="$2"
            shift 2
            ;;
        --count)
            SHARD_COUNT="$2"
            shift 2
            ;;
        --fast)
            # Fast mode: 50 shards for quick iteration (~12min sequential, ~3-5min parallel)
            SHARD_COUNT=50
            shift
            ;;
        --safe)
            # Safe mode: 200 shards for memory-constrained systems
            SHARD_COUNT=200
            shift
            ;;
        --parallel|-j)
            PARALLEL_MODE="true"
            # Check if next arg is a number (optional concurrency)
            if [[ "${2:-}" =~ ^[0-9]+$ ]]; then
                PARALLEL_CONCURRENCY="$2"
                shift
            fi
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --parallel [N]   RECOMMENDED: Run shards in parallel (~5-10min)"
            echo "  --fast           Fast mode: 50 shards for quick iteration"
            echo "  --safe           Safe mode: 200 shards for memory-constrained systems"
            echo "  --shard N        Run only shard N"
            echo "  --count N        Use N total shards (default: $SHARD_COUNT)"
            echo "  -j [N]           Alias for --parallel"
            echo "  --help, -h       Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 --parallel              # Fastest: parallel with auto-concurrency"
            echo "  $0 --fast --parallel       # Fast + parallel (~3-5min)"
            echo "  $0 --parallel 4            # 4 concurrent shards"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--shard N] [--count N] [--parallel [N]] [--help]"
            exit 1
            ;;
    esac
done

echo "=== Frontend Test Suite (Sharded for OOM Prevention) ==="
echo "Using $SHARD_COUNT shards with Vitest native sharding"
echo ""

# Run specific shard or all shards
if [ -n "$SPECIFIC_SHARD" ]; then
    if [ "$SPECIFIC_SHARD" -lt 1 ] || [ "$SPECIFIC_SHARD" -gt "$SHARD_COUNT" ]; then
        echo "Invalid shard number: $SPECIFIC_SHARD (valid: 1-$SHARD_COUNT)"
        exit 1
    fi
    run_shard "$SPECIFIC_SHARD" "$SHARD_COUNT"
elif [ -n "$PARALLEL_MODE" ]; then
    # Parallel execution mode
    if [ -z "$PARALLEL_CONCURRENCY" ]; then
        PARALLEL_CONCURRENCY=$(get_optimal_concurrency)
        echo -e "${BLUE}Auto-detected concurrency: $PARALLEL_CONCURRENCY${NC}"
    fi
    run_shards_parallel "$SHARD_COUNT" "$PARALLEL_CONCURRENCY"
else
    # Run all shards sequentially (default)
    FAILED_SHARDS=()

    for i in $(seq 1 $SHARD_COUNT); do
        if ! run_shard $i $SHARD_COUNT; then
            FAILED_SHARDS+=("$i")
        fi
    done

    echo "=== Test Summary ==="
    if [ ${#FAILED_SHARDS[@]} -eq 0 ]; then
        echo -e "${GREEN}All $SHARD_COUNT shards passed!${NC}"
        exit 0
    else
        echo -e "${RED}Failed shards: ${FAILED_SHARDS[*]}${NC}"
        exit 1
    fi
fi
