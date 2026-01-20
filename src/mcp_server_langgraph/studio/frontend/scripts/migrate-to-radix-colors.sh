#!/bin/bash
# migrate-to-radix-colors.sh
#
# Migrates legacy Tailwind dark mode patterns to Radix semantic colors.
# Radix Colors v3.0+ uses .dark class selector, so colors auto-switch.
#
# Usage: ./scripts/migrate-to-radix-colors.sh [--dry-run]

set -e

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "DRY RUN - No files will be modified"
fi

SRC_DIR="src"

# Function to run sed replacement
run_sed() {
  local pattern="$1"
  local replacement="$2"
  local description="$3"

  count=$(grep -r "$pattern" --include="*.tsx" --include="*.ts" "$SRC_DIR" 2>/dev/null | wc -l | tr -d ' ')

  if [[ "$count" -gt 0 ]]; then
    echo "  $description: $count occurrences"
    if [[ "$DRY_RUN" == "false" ]]; then
      find "$SRC_DIR" -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i '' "s/$pattern/$replacement/g" {} +
    fi
  fi
}

echo "=== Radix Colors Migration ==="
echo ""

# ===========================================================================
# BACKGROUNDS
# ===========================================================================
echo "Migrating backgrounds..."

# Pure white/black backgrounds
run_sed 'bg-white dark:bg-neutral-900' 'bg-neutral-1' 'white/900 → neutral-1'
run_sed 'bg-white dark:bg-gray-900' 'bg-neutral-1' 'white/gray-900 → neutral-1'

# Light backgrounds
run_sed 'bg-neutral-50 dark:bg-neutral-800' 'bg-neutral-2' '50/800 → neutral-2'
run_sed 'bg-neutral-100 dark:bg-neutral-800' 'bg-neutral-3' '100/800 → neutral-3'
run_sed 'bg-neutral-100 dark:bg-neutral-700' 'bg-neutral-4' '100/700 → neutral-4'
run_sed 'bg-neutral-200 dark:bg-neutral-700' 'bg-neutral-5' '200/700 → neutral-5'

# Hover backgrounds
run_sed 'hover:bg-neutral-100 dark:hover:bg-neutral-700' 'hover:bg-neutral-4' 'hover 100/700 → 4'
run_sed 'hover:bg-neutral-100 dark:hover:bg-neutral-800' 'hover:bg-neutral-3' 'hover 100/800 → 3'
run_sed 'hover:bg-neutral-50 dark:hover:bg-neutral-800' 'hover:bg-neutral-3' 'hover 50/800 → 3'
run_sed 'hover:bg-neutral-200 dark:hover:bg-neutral-600' 'hover:bg-neutral-5' 'hover 200/600 → 5'

# ===========================================================================
# BORDERS
# ===========================================================================
echo "Migrating borders..."

run_sed 'border-neutral-200 dark:border-neutral-700' 'border-neutral-6' '200/700 → neutral-6'
run_sed 'border-neutral-200 dark:border-neutral-600' 'border-neutral-6' '200/600 → neutral-6'
run_sed 'border-neutral-300 dark:border-neutral-600' 'border-neutral-6' '300/600 → neutral-6'
run_sed 'border-neutral-300 dark:border-neutral-700' 'border-neutral-7' '300/700 → neutral-7'

# ===========================================================================
# TEXT COLORS
# ===========================================================================
echo "Migrating text colors..."

# High contrast text (headings, body)
run_sed 'text-neutral-900 dark:text-neutral-100' 'text-neutral-12' '900/100 → neutral-12'
run_sed 'text-neutral-900 dark:text-white' 'text-neutral-12' '900/white → neutral-12'
run_sed 'text-neutral-900 dark:text-neutral-50' 'text-neutral-12' '900/50 → neutral-12'

# Secondary text
run_sed 'text-neutral-700 dark:text-neutral-300' 'text-neutral-11' '700/300 → neutral-11'
run_sed 'text-neutral-600 dark:text-neutral-400' 'text-neutral-11' '600/400 → neutral-11'
run_sed 'text-neutral-600 dark:text-neutral-300' 'text-neutral-11' '600/300 → neutral-11'

# Muted/placeholder text
run_sed 'text-neutral-500 dark:text-neutral-400' 'text-neutral-10' '500/400 → neutral-10'
run_sed 'text-neutral-500 dark:text-neutral-300' 'text-neutral-10' '500/300 → neutral-10'
run_sed 'text-neutral-400 dark:text-neutral-500' 'text-neutral-9' '400/500 → neutral-9'
run_sed 'text-neutral-400 dark:text-neutral-300' 'text-neutral-9' '400/300 → neutral-9'

# ===========================================================================
# PLACEHOLDERS
# ===========================================================================
echo "Migrating placeholders..."

run_sed 'placeholder-neutral-400 dark:placeholder-neutral-500' 'placeholder-neutral-9' 'placeholder 400/500 → 9'
run_sed 'placeholder-neutral-500 dark:placeholder-neutral-400' 'placeholder-neutral-9' 'placeholder 500/400 → 9'

# ===========================================================================
# CLEANUP - Remove redundant dark: when already using Radix scale
# ===========================================================================
echo "Cleaning up redundant patterns..."

# Remove dark: prefixes for Radix 1-12 scale (they auto-switch)
run_sed ' dark:bg-neutral-1' '' 'remove redundant dark:bg-neutral-1'
run_sed ' dark:bg-neutral-2' '' 'remove redundant dark:bg-neutral-2'
run_sed ' dark:bg-neutral-3' '' 'remove redundant dark:bg-neutral-3'
run_sed ' dark:text-neutral-11' '' 'remove redundant dark:text-neutral-11'
run_sed ' dark:text-neutral-12' '' 'remove redundant dark:text-neutral-12'
run_sed ' dark:border-neutral-6' '' 'remove redundant dark:border-neutral-6'

echo ""
echo "=== Migration complete ==="
echo ""
echo "Next steps:"
echo "1. Run: npm run build"
echo "2. Run: npm run lint"
echo "3. Test dark/light mode switching manually"
