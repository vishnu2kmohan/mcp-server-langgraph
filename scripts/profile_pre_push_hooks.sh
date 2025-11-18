#!/usr/bin/env bash
# Profile pre-push hooks execution time
# Usage: ./scripts/profile_pre_push_hooks.sh

set -euo pipefail

echo "🔍 Profiling Pre-Push Hooks Execution Time"
echo "=========================================="
echo ""

# Get list of pre-push hooks
HOOKS=$(grep -B5 "stages:.*pre-push" .pre-commit-config.yaml | grep "^\s*-\s*id:" | sed 's/.*id: //' | sort | uniq)

TOTAL_TIME=0
declare -a HOOK_TIMES

echo "📊 Individual Hook Timings:"
echo ""

while IFS= read -r hook; do
    if [ -z "$hook" ]; then
        continue
    fi

    echo -n "Testing $hook... "
    START=$(date +%s)

    # Run hook in isolation
    if SKIP='' pre-commit run "$hook" --all-files &>/dev/null; then
        STATUS="✅"
    else
        STATUS="⚠️"
    fi

    END=$(date +%s)
    DURATION=$((END - START))
    TOTAL_TIME=$((TOTAL_TIME + DURATION))

    printf "%s %3ds\n" "$STATUS" "$DURATION"
    HOOK_TIMES+=("$DURATION:$hook")
done <<< "$HOOKS"

echo ""
echo "=========================================="
echo "📈 Summary:"
echo "  Total time: ${TOTAL_TIME}s ($(($TOTAL_TIME / 60))m $(($TOTAL_TIME % 60))s)"
echo ""
echo "🐌 Slowest hooks:"
printf '%s\n' "${HOOK_TIMES[@]}" | sort -rn | head -10 | while IFS=: read -r time hook; do
    printf "  %3ds - %s\n" "$time" "$hook"
done
