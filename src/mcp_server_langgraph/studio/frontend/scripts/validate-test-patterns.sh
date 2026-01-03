#!/bin/bash
# =============================================================================
# Validate Frontend Test Patterns
# =============================================================================
# Checks for problematic patterns in test files that can cause flaky tests
# or test failures.
#
# Patterns checked:
# 1. delete window.location - Breaks keyboard events when used with dispatchEvent
# 2. currentSessionId in session slice tests - sessionSlice uses currentSession
#
# Usage:
#   ./scripts/validate-test-patterns.sh           # Check all test files
#   ./scripts/validate-test-patterns.sh file.tsx  # Check specific file
#
# Exit codes:
#   0 - No issues found
#   1 - Pattern violations found
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

ERRORS=0
WARNINGS=0

# Get files to check
if [ $# -gt 0 ]; then
    FILES="$@"
else
    FILES=$(find src -name "*.test.tsx" -o -name "*.test.ts")
fi

echo "=== Frontend Test Pattern Validation ==="
echo ""

# Pattern 1: delete window.location (unless marked safe)
# This pattern breaks window.dispatchEvent() for keyboard events
echo "Checking for 'delete window.location' pattern..."
for file in $FILES; do
    # Get line numbers with delete window.location (excluding comment lines)
    LINE_NUMS=$(grep -n "delete window.location" "$file" 2>/dev/null | \
        grep -v ":[[:space:]]*\*" | \
        grep -v ":[[:space:]]*//" | \
        grep -v "BAD:" | \
        grep -v "NEVER use" | \
        cut -d: -f1 || true)

    for line in $LINE_NUMS; do
        # Check if the line itself or any of the 3 lines before have keyboard-safe
        START=$((line - 3))
        if [ $START -lt 1 ]; then START=1; fi
        CONTEXT=$(sed -n "${START},${line}p" "$file" 2>/dev/null)
        if echo "$CONTEXT" | grep -q "keyboard-safe:\|// safe:"; then
            continue  # Skip - has safe marker
        fi

        # This is a violation
        echo -e "${YELLOW}WARNING:${NC} $file:$line"
        sed -n "${line}p" "$file"
        echo -e "  ${YELLOW}→ This breaks keyboard events. Use userEvent.keyboard() instead.${NC}"
        echo -e "  ${YELLOW}→ Or add '// keyboard-safe:' comment above if safe.${NC}"
        echo ""
        ((WARNINGS++))
    done
done

# Pattern 2: currentSessionId in session slice tests
# sessionSlice uses currentSession (full object), not currentSessionId
echo "Checking for 'currentSessionId' in session slice tests..."
for file in $FILES; do
    # Only check if file deals with session slice
    if grep -q "session:" "$file" 2>/dev/null || grep -q "sessionSlice" "$file" 2>/dev/null; then
        # Look for currentSessionId: pattern (not currentSessionId variable references)
        # Exclude comment lines (starting with * or //) and intentional langGraph usage
        MATCHES=$(grep -n "currentSessionId:" "$file" 2>/dev/null | \
            grep -v ":[[:space:]]*\*" | \
            grep -v ":[[:space:]]*//" | \
            grep -v "// lang-graph:" | \
            grep -v "langGraph" || true)

        if [ -n "$MATCHES" ]; then
            echo -e "${YELLOW}WARNING:${NC} $file"
            echo "$MATCHES"
            echo -e "  ${YELLOW}→ sessionSlice uses 'currentSession' (object), not 'currentSessionId' (string).${NC}"
            echo -e "  ${YELLOW}→ langGraphSlice uses 'currentSessionId'. Add '// lang-graph:' if intentional.${NC}"
            echo ""
            ((WARNINGS++))
        fi
    fi
done

# Pattern 3: vi.fn() in vi.mock() without vi.hoisted()
# This causes "Cannot access before initialization" errors
echo "Checking for mock initialization order issues..."
for file in $FILES; do
    # Look for vi.mock with inline vi.fn that references a const
    if grep -E "const mock\w+ = vi\.fn" "$file" 2>/dev/null | head -1 > /dev/null; then
        # Check if vi.hoisted is used
        if ! grep -q "vi.hoisted" "$file" 2>/dev/null; then
            # Check if the mock is used inside a vi.mock factory
            MOCK_VAR=$(grep -oE "const mock\w+ = vi\.fn" "$file" 2>/dev/null | head -1 | sed 's/const //' | cut -d' ' -f1)
            if [ -n "$MOCK_VAR" ] && grep -q "vi.mock.*$MOCK_VAR" "$file" 2>/dev/null; then
                echo -e "${YELLOW}INFO:${NC} $file may need vi.hoisted() for mock: $MOCK_VAR"
                ((WARNINGS++))
            fi
        fi
    fi
done

echo ""
echo "=== Summary ==="
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}Errors: $ERRORS${NC}"
fi
if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
fi
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}No pattern violations found!${NC}"
fi

# Exit with error if any errors found
if [ $ERRORS -gt 0 ]; then
    exit 1
fi

exit 0
