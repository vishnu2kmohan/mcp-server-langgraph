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

# Default shard count - 200 shards for ~2-3 test files per shard
# With 481 test files, 200 shards = ~2.4 files each
# This prevents OOM by keeping memory under 4GB per shard
# Increased from 80 to 200 due to severe memory accumulation in jsdom
SHARD_COUNT=200

run_shard() {
    local shard_num=$1
    local total_shards=$2
    echo -e "${YELLOW}=== Running Shard $shard_num/$total_shards ===${NC}"

    # Run with single fork to prevent OOM, using vitest native sharding
    VITEST_MAX_FORKS=1 npm test -- --run --shard="$shard_num/$total_shards" 2>&1 || {
        echo -e "${RED}Shard $shard_num/$total_shards failed${NC}"
        return 1
    }

    echo -e "${GREEN}Shard $shard_num/$total_shards completed${NC}"
    echo ""
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
