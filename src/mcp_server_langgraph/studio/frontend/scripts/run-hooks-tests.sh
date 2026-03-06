#!/bin/bash
# =============================================================================
# Hooks Test Runner - Sharded for OOM Prevention
# =============================================================================
# Runs hooks tests in 5 shards to prevent OOM.
# With 106 hook tests, 5 shards = ~21 files each.
#
# Usage:
#   ./scripts/run-hooks-tests.sh           # Run all shards
#   ./scripts/run-hooks-tests.sh --shard 1 # Run specific shard (1-5)
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
# shellcheck disable=SC2034
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SHARD_COUNT=5
SPECIFIC_SHARD=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --shard)
            SPECIFIC_SHARD="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--shard N]"
            exit 1
            ;;
    esac
done

run_shard() {
    local shard_num=$1
    echo -e "${BLUE}=== Hooks Shard $shard_num/$SHARD_COUNT ===${NC}"

    # Use 8GB heap and single fork to prevent OOM in jsdom-heavy tests
    # The --expose-gc flag allows explicit GC calls if needed
    VITEST_MAX_FORKS=1 NODE_OPTIONS='--max-old-space-size=8192 --expose-gc' \
        npm test -- --run src/hooks/ --shard="$shard_num/$SHARD_COUNT" 2>&1 || {
        echo -e "${RED}Hooks Shard $shard_num/$SHARD_COUNT failed${NC}"
        return 1
    }

    echo -e "${GREEN}Hooks Shard $shard_num/$SHARD_COUNT completed${NC}"
    echo ""
}

echo "=== Hooks Test Suite (Sharded) ==="
echo "Running 106 hooks tests in $SHARD_COUNT shards"
echo ""

if [ -n "$SPECIFIC_SHARD" ]; then
    if [ "$SPECIFIC_SHARD" -lt 1 ] || [ "$SPECIFIC_SHARD" -gt "$SHARD_COUNT" ]; then
        echo "Invalid shard number: $SPECIFIC_SHARD (valid: 1-$SHARD_COUNT)"
        exit 1
    fi
    run_shard "$SPECIFIC_SHARD"
else
    FAILED_SHARDS=()

    for i in $(seq 1 $SHARD_COUNT); do
        # shellcheck disable=SC2086
        if ! run_shard $i; then
            FAILED_SHARDS+=("$i")
        fi
    done

    echo "=== Summary ==="
    if [ ${#FAILED_SHARDS[@]} -eq 0 ]; then
        echo -e "${GREEN}All $SHARD_COUNT hooks shards passed!${NC}"
        exit 0
    else
        echo -e "${RED}Failed shards: ${FAILED_SHARDS[*]}${NC}"
        exit 1
    fi
fi
