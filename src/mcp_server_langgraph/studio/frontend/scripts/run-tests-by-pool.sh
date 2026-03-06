#!/bin/bash
# =============================================================================
# Pool-Based Test Runner for OOM Prevention
# =============================================================================
# This script runs tests by workspace pools defined in vitest.workspace.ts.
# Each pool runs in a separate Node.js process, preventing memory accumulation.
#
# Usage:
#   ./scripts/run-tests-by-pool.sh           # Run all pools sequentially
#   ./scripts/run-tests-by-pool.sh layout    # Run specific pool
#   ./scripts/run-tests-by-pool.sh --ci      # Run with CI optimizations
#
# Pools (defined in vitest.workspace.ts):
#   layout, hooks, store, components, canvas, ai, conversation,
#   pages, router, api, contexts, utils, other
#
# Why pools?
# - Each pool runs in isolated Node.js process
# - Memory is fully released between pools
# - Pools can run in parallel in CI via matrix jobs
# - More intuitive than numeric sharding
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
# shellcheck disable=SC2034
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Pool definitions - order optimized for memory (heaviest last)
POOLS=(
    "utils"
    "contexts"
    "api"
    "router"
    "store"
    "ai"
    "canvas"
    "conversation"
    "pages"
    "other"
    "hooks"
    "components"
    "layout"
)

# Memory allocations per pool (in MB)
declare -A POOL_MEMORY=(
    ["utils"]=4096
    ["contexts"]=4096
    ["api"]=4096
    ["router"]=4096
    ["store"]=4096
    ["ai"]=4096
    ["canvas"]=4096
    ["conversation"]=4096
    ["pages"]=4096
    ["other"]=4096
    ["hooks"]=8192
    ["components"]=8192
    ["layout"]=8192
)

# Pool to directory mapping
declare -A POOL_DIRS=(
    ["utils"]="src/utils/ src/types/ src/help/ src/persona/"
    ["contexts"]="src/contexts/"
    ["api"]="src/api/"
    ["router"]="src/router/"
    ["store"]="src/store/"
    ["ai"]="src/ai/"
    ["canvas"]="src/canvas/"
    ["conversation"]="src/conversation/"
    ["pages"]="src/pages/"
    ["other"]="src/analytics/ src/compliance/ src/devtools/ src/observability/ src/onboarding/ src/pwa/ src/security/ src/workflow/"
    ["hooks"]="src/hooks/"
    ["components"]="src/components/"
    ["layout"]="src/layout/"
)

run_pool() {
    local pool=$1
    local memory=${POOL_MEMORY[$pool]:-4096}
    local dirs=${POOL_DIRS[$pool]}

    echo -e "${BLUE}=== Running Pool: $pool (${memory}MB heap) ===${NC}"
    echo -e "  Directories: $dirs"

    # Use single fork to prevent OOM from parallel workers accumulating memory
    # jsdom + React Testing Library can consume 300-500MB per test file
    # shellcheck disable=SC2034,SC2086
    VITEST_MAX_FORKS=1 NODE_OPTIONS="--max-old-space-size=${memory} --expose-gc" \
        npm test -- --run $dirs 2>&1 || {
        echo -e "${RED}Pool '$pool' failed${NC}"
        return 1
    }

    echo -e "${GREEN}Pool '$pool' completed${NC}"
    echo ""
}

# Parse arguments
# shellcheck disable=SC2034
CI_MODE=false
SPECIFIC_POOL=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --ci)
            # shellcheck disable=SC2034
            CI_MODE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [pool_name] [--ci]"
            echo ""
            echo "Pools: ${POOLS[*]}"
            echo ""
            echo "Options:"
            echo "  --ci      Run with CI optimizations"
            echo "  --help    Show this help"
            exit 0
            ;;
        *)
            SPECIFIC_POOL="$1"
            shift
            ;;
    esac
done

echo "=== Frontend Test Suite (Pool-Based) ==="
echo "Pools defined in vitest.workspace.ts"
echo ""

# Run specific pool or all pools
if [ -n "$SPECIFIC_POOL" ]; then
    # Validate pool name
    valid=false
    for pool in "${POOLS[@]}"; do
        if [ "$pool" == "$SPECIFIC_POOL" ]; then
            valid=true
            break
        fi
    done

    if [ "$valid" = false ]; then
        echo -e "${RED}Invalid pool: $SPECIFIC_POOL${NC}"
        echo "Valid pools: ${POOLS[*]}"
        exit 1
    fi

    run_pool "$SPECIFIC_POOL"
else
    # Run all pools sequentially
    FAILED_POOLS=()
    PASSED_POOLS=()
    START_TIME=$(date +%s)

    for pool in "${POOLS[@]}"; do
        if run_pool "$pool"; then
            PASSED_POOLS+=("$pool")
        else
            FAILED_POOLS+=("$pool")
        fi
    done

    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo "=== Test Summary ==="
    echo "Duration: ${DURATION}s"
    echo -e "${GREEN}Passed: ${#PASSED_POOLS[@]} pools${NC}"

    if [ ${#FAILED_POOLS[@]} -eq 0 ]; then
        echo -e "${GREEN}All pools passed!${NC}"
        exit 0
    else
        echo -e "${RED}Failed: ${FAILED_POOLS[*]}${NC}"
        exit 1
    fi
fi
