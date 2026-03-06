#!/usr/bin/env bash
#
# Migrate legacy Tailwind neutral colors to Radix semantic colors
#
# Radix 1-12 Scale:
#   1-2:   App backgrounds
#   3-5:   Interactive backgrounds (hover, active)
#   6-8:   Borders
#   9-10:  Solid colors (buttons, badges)
#   11-12: Text (secondary, primary)
#
# Usage: ./scripts/migrate-legacy-neutrals.sh [--dry-run]

set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "DRY RUN MODE - No files will be modified"
fi

# Find all TSX files in src, excluding tests and stories
FILES=$(find src -name "*.tsx" -type f \
    ! -path "*node_modules*" \
    ! -name "*.test.tsx" \
    ! -name "*.stories.tsx")

echo "=== Migrating Legacy Neutral Patterns to Radix ==="
echo "Files to process: $(echo "$FILES" | wc -l | tr -d ' ')"
echo ""

# Create sed commands file for atomic replacements
# Using extended regex (-E) for cleaner patterns
SED_COMMANDS=$(cat << 'EOF'
# =============================================================================
# TEXT COLORS: neutral-XXX → Radix 1-12 scale
# =============================================================================
# High contrast text (900 → 12)
s/text-neutral-900/text-neutral-12/g
s/text-neutral-800/text-neutral-12/g

# Secondary text (700, 600 → 11)
s/text-neutral-700/text-neutral-11/g
s/text-neutral-600/text-neutral-11/g

# Muted text (500, 400 → 10, 9)
s/text-neutral-500/text-neutral-10/g
s/text-neutral-400/text-neutral-9/g

# Very muted text (300, 200, 100 → 9, 8)
s/text-neutral-300/text-neutral-9/g
s/text-neutral-200/text-neutral-9/g
s/text-neutral-100/text-neutral-9/g

# =============================================================================
# BACKGROUND COLORS: neutral-XXX → Radix 1-12 scale
# =============================================================================
# Dark backgrounds (900, 950 → 2)
s/bg-neutral-950/bg-neutral-2/g
s/bg-neutral-900/bg-neutral-2/g

# Medium-dark backgrounds (800, 700 → 3, 4)
s/bg-neutral-800/bg-neutral-3/g
s/bg-neutral-700/bg-neutral-4/g

# Medium backgrounds (600, 500 → 5)
s/bg-neutral-600/bg-neutral-5/g
s/bg-neutral-500/bg-neutral-5/g

# Light backgrounds (400, 300 → 4, 3)
s/bg-neutral-400/bg-neutral-4/g
s/bg-neutral-300/bg-neutral-3/g

# Very light backgrounds (200, 100, 50 → 3, 2, 1)
s/bg-neutral-200/bg-neutral-3/g
s/bg-neutral-100/bg-neutral-2/g
s/bg-neutral-50/bg-neutral-1/g

# =============================================================================
# BORDER COLORS: neutral-XXX → Radix 6-8 scale
# =============================================================================
# Strong borders (800, 700 → 7)
s/border-neutral-800/border-neutral-7/g
s/border-neutral-700/border-neutral-7/g

# Default borders (600, 500 → 6)
s/border-neutral-600/border-neutral-6/g
s/border-neutral-500/border-neutral-6/g

# Subtle borders (400, 300 → 6, 5)
s/border-neutral-400/border-neutral-6/g
s/border-neutral-300/border-neutral-5/g

# Very subtle borders (200, 100 → 5)
s/border-neutral-200/border-neutral-5/g
s/border-neutral-100/border-neutral-5/g

# =============================================================================
# HOVER BACKGROUNDS: preserve hover: prefix
# =============================================================================
s/hover:bg-neutral-900/hover:bg-neutral-3/g
s/hover:bg-neutral-800/hover:bg-neutral-4/g
s/hover:bg-neutral-700/hover:bg-neutral-5/g
s/hover:bg-neutral-600/hover:bg-neutral-5/g
s/hover:bg-neutral-500/hover:bg-neutral-5/g
s/hover:bg-neutral-400/hover:bg-neutral-4/g
s/hover:bg-neutral-300/hover:bg-neutral-4/g
s/hover:bg-neutral-200/hover:bg-neutral-4/g
s/hover:bg-neutral-100/hover:bg-neutral-3/g
s/hover:bg-neutral-50/hover:bg-neutral-3/g

# =============================================================================
# FOCUS BACKGROUNDS/BORDERS
# =============================================================================
s/focus:bg-neutral-700/focus:bg-neutral-4/g
s/focus:bg-neutral-100/focus:bg-neutral-3/g
s/focus:bg-neutral-50/focus:bg-neutral-3/g
s/focus:border-neutral-500/focus:border-neutral-8/g
s/focus:border-neutral-400/focus:border-neutral-7/g

# =============================================================================
# PLACEHOLDER COLORS
# =============================================================================
s/placeholder-neutral-500/placeholder-neutral-9/g
s/placeholder-neutral-400/placeholder-neutral-9/g
s/placeholder:text-neutral-500/placeholder:text-neutral-9/g
s/placeholder:text-neutral-400/placeholder:text-neutral-9/g

# =============================================================================
# DIVIDE COLORS (for flex/grid dividers)
# =============================================================================
s/divide-neutral-200/divide-neutral-5/g
s/divide-neutral-300/divide-neutral-6/g
s/divide-neutral-700/divide-neutral-6/g

# =============================================================================
# RING COLORS
# =============================================================================
s/ring-neutral-500/ring-neutral-8/g
s/ring-neutral-400/ring-neutral-7/g
s/ring-neutral-300/ring-neutral-6/g
s/ring-neutral-200/ring-neutral-5/g

# =============================================================================
# SPECIAL: bg-white → bg-neutral-1 (for dark mode support)
# =============================================================================
s/bg-white([^a-z])/bg-neutral-1\1/g
EOF
)

# Count patterns before
# shellcheck disable=SC2086
BEFORE_COUNT=$(grep -rE '(text|bg|border)-neutral-(100|200|300|400|500|600|700|800|900)' $FILES 2>/dev/null | wc -l | tr -d ' ')
echo "Legacy patterns found: $BEFORE_COUNT"

if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo "Would apply the following transformations:"
    echo "$SED_COMMANDS" | grep -v '^#' | grep -v '^$' | head -20
    echo "... and $(echo "$SED_COMMANDS" | grep -v '^#' | grep -vc '^$' | tr -d ' ') more"
    exit 0
fi

# Apply sed commands to each file
echo "Applying migrations..."
for file in $FILES; do
    # Use a temp file for atomic writes
    # shellcheck disable=SC2034
    TEMP_FILE=$(mktemp)

    # Apply all sed commands
    echo "$SED_COMMANDS" | grep -v '^#' | grep -v '^$' | while read -r cmd; do
        if [[ -n "$cmd" ]]; then
            sed -E -i.bak "$cmd" "$file" 2>/dev/null || true
        fi
    done

    # Clean up backup files
    rm -f "${file}.bak" 2>/dev/null || true
done

# Count patterns after
# shellcheck disable=SC2086
AFTER_COUNT=$(grep -rE '(text|bg|border)-neutral-(100|200|300|400|500|600|700|800|900)' $FILES 2>/dev/null | wc -l | tr -d ' ')

echo ""
echo "=== Migration Complete ==="
echo "Before: $BEFORE_COUNT patterns"
echo "After:  $AFTER_COUNT patterns"
echo "Fixed:  $((BEFORE_COUNT - AFTER_COUNT)) patterns"
echo ""
echo "Next steps:"
echo "1. Run: npm run lint"
echo "2. Run: npm run build"
echo "3. Visual test dark/light mode"
