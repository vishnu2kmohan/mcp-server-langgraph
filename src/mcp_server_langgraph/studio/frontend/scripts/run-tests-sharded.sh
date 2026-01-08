#!/bin/bash
# =============================================================================
# Sharded Test Runner for OOM Prevention
# =============================================================================
# This script runs tests in shards using Vitest's native --shard feature
# to prevent OOM errors when running the full test suite.
#
# Usage:
#   ./scripts/run-tests-sharded.sh           # Run all 8 shards sequentially
#   ./scripts/run-tests-sharded.sh --shard 1 # Run specific shard (1-8)
#   ./scripts/run-tests-sharded.sh --count 4 # Use 4 shards instead of 8
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
NC='\033[0m' # No Color

# =============================================================================
# Shard Count Calculation
# =============================================================================
# Memory budget: 4GB heap per shard (safe for most systems)
# Memory per test file: ~300-500MB (jsdom + React Testing Library + MSW)
# Safe files per shard: 4GB / 400MB = ~10 files
# With 622 test files, need ~62 shards minimum
#
# Using 200 shards for maximum memory safety:
# - 622 files / 200 shards = ~3 files per shard
# - 3 files × 400MB = 1.2GB per shard (very safe for 4GB limit)
# - Accounts for outlier tests that use 800MB+ each
#
# Known heavy tests (800MB+ each):
# - session-hooks-integration.test.ts
# - StudioShellLayout.*.test.tsx
# - useMCPConnection.test.ts
# - AlertDetailPanel.test.tsx
# - CanvasShortcutsMenu.test.tsx
#
# Trade-off: 200 shards × 15s overhead = ~50min total vs 10min parallel
SHARD_COUNT=200

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

# Parse arguments
SPECIFIC_SHARD=""
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
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--shard N] [--count N]"
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
else
    # Run all shards sequentially
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
