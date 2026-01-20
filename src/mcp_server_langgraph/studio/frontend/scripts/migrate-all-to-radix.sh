#!/bin/bash
# migrate-all-to-radix.sh
#
# COMPREHENSIVE migration from legacy Tailwind dark mode patterns to Radix semantic colors.
# Radix Colors v3.0.0+ uses .dark class selector - colors auto-switch.
#
# Usage: ./scripts/migrate-all-to-radix.sh [--dry-run]
#
# Radix 1-12 Scale Reference:
#   1-2:   App backgrounds
#   3-5:   Interactive backgrounds (hover, active)
#   6-8:   Borders
#   9-10:  Solid colors (buttons, badges)
#   11-12: Text (secondary, primary)

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

  count=$(grep -rE "$pattern" --include="*.tsx" --include="*.ts" "$SRC_DIR" 2>/dev/null | wc -l | tr -d ' ')

  if [[ "$count" -gt 0 ]]; then
    echo "  $description: $count occurrences"
    if [[ "$DRY_RUN" == "false" ]]; then
      find "$SRC_DIR" -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i '' -E "s/$pattern/$replacement/g" {} +
    fi
  fi
}

echo "=== COMPREHENSIVE Radix Colors Migration ==="
echo ""

# ===========================================================================
# PHASE 1: BACKGROUND COLORS (dark:bg-*)
# ===========================================================================
echo "Phase 1: Migrating backgrounds..."

# Pure white/black backgrounds
run_sed 'bg-white dark:bg-neutral-900' 'bg-neutral-1' 'white/900 → neutral-1'
run_sed 'bg-white dark:bg-gray-900' 'bg-neutral-1' 'white/gray-900 → neutral-1'
run_sed 'bg-white dark:bg-neutral-800' 'bg-neutral-1' 'white/800 → neutral-1'

# Light backgrounds (50-200 scale)
run_sed 'bg-neutral-50 dark:bg-neutral-900' 'bg-neutral-1' '50/900 → neutral-1'
run_sed 'bg-neutral-50 dark:bg-neutral-800' 'bg-neutral-2' '50/800 → neutral-2'
run_sed 'bg-neutral-100 dark:bg-neutral-900' 'bg-neutral-2' '100/900 → neutral-2'
run_sed 'bg-neutral-100 dark:bg-neutral-800' 'bg-neutral-3' '100/800 → neutral-3'
run_sed 'bg-neutral-100 dark:bg-neutral-700' 'bg-neutral-4' '100/700 → neutral-4'
run_sed 'bg-neutral-200 dark:bg-neutral-800' 'bg-neutral-4' '200/800 → neutral-4'
run_sed 'bg-neutral-200 dark:bg-neutral-700' 'bg-neutral-5' '200/700 → neutral-5'

# Opacity-based backgrounds (semantic colors) - use | delimiter to avoid / conflicts
for color in primary success warning error info insight; do
  for opacity in 20 30 40 50; do
    count=$(grep -rE "bg-${color}-50 dark:bg-${color}-900/${opacity}" --include="*.tsx" --include="*.ts" "$SRC_DIR" 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$count" -gt 0 ]]; then
      echo "  ${color} 50/${opacity} → ${color}-3: $count occurrences"
      if [[ "$DRY_RUN" == "false" ]]; then
        find "$SRC_DIR" -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i '' "s|bg-${color}-50 dark:bg-${color}-900/${opacity}|bg-${color}-3|g" {} +
      fi
    fi
    count=$(grep -rE "bg-${color}-100 dark:bg-${color}-900/${opacity}" --include="*.tsx" --include="*.ts" "$SRC_DIR" 2>/dev/null | wc -l | tr -d ' ')
    if [[ "$count" -gt 0 ]]; then
      echo "  ${color} 100/${opacity} → ${color}-3: $count occurrences"
      if [[ "$DRY_RUN" == "false" ]]; then
        find "$SRC_DIR" -type f \( -name "*.tsx" -o -name "*.ts" \) -exec sed -i '' "s|bg-${color}-100 dark:bg-${color}-900/${opacity}|bg-${color}-3|g" {} +
      fi
    fi
  done
done

# Remove orphaned dark:bg-neutral-* (after light pattern removed)
run_sed ' dark:bg-neutral-900' '' 'remove dark:bg-neutral-900'
run_sed ' dark:bg-neutral-800' '' 'remove dark:bg-neutral-800'
run_sed ' dark:bg-neutral-700' '' 'remove dark:bg-neutral-700'

# ===========================================================================
# PHASE 2: TEXT COLORS (dark:text-*)
# ===========================================================================
echo "Phase 2: Migrating text colors..."

# High contrast text (headings, body) - neutral
run_sed 'text-neutral-900 dark:text-neutral-100' 'text-neutral-12' '900/100 → neutral-12'
run_sed 'text-neutral-900 dark:text-neutral-50' 'text-neutral-12' '900/50 → neutral-12'
run_sed 'text-neutral-900 dark:text-white' 'text-neutral-12' '900/white → neutral-12'
run_sed 'text-neutral-800 dark:text-neutral-100' 'text-neutral-12' '800/100 → neutral-12'
run_sed 'text-neutral-800 dark:text-neutral-200' 'text-neutral-12' '800/200 → neutral-12'

# Secondary text - neutral
run_sed 'text-neutral-700 dark:text-neutral-300' 'text-neutral-11' '700/300 → neutral-11'
run_sed 'text-neutral-700 dark:text-neutral-200' 'text-neutral-11' '700/200 → neutral-11'
run_sed 'text-neutral-600 dark:text-neutral-400' 'text-neutral-11' '600/400 → neutral-11'
run_sed 'text-neutral-600 dark:text-neutral-300' 'text-neutral-11' '600/300 → neutral-11'

# Muted/placeholder text - neutral
run_sed 'text-neutral-500 dark:text-neutral-400' 'text-neutral-10' '500/400 → neutral-10'
run_sed 'text-neutral-500 dark:text-neutral-300' 'text-neutral-10' '500/300 → neutral-10'
run_sed 'text-neutral-400 dark:text-neutral-500' 'text-neutral-9' '400/500 → neutral-9'
run_sed 'text-neutral-400 dark:text-neutral-300' 'text-neutral-9' '400/300 → neutral-9'

# Semantic text colors (primary, success, warning, error, info, insight)
for color in primary success warning error info insight; do
  run_sed "text-${color}-900 dark:text-${color}-100" "text-${color}-12" "${color} 900/100 → 12"
  run_sed "text-${color}-800 dark:text-${color}-200" "text-${color}-11" "${color} 800/200 → 11"
  run_sed "text-${color}-800 dark:text-${color}-300" "text-${color}-11" "${color} 800/300 → 11"
  run_sed "text-${color}-700 dark:text-${color}-300" "text-${color}-11" "${color} 700/300 → 11"
  run_sed "text-${color}-700 dark:text-${color}-400" "text-${color}-11" "${color} 700/400 → 11"
  run_sed "text-${color}-600 dark:text-${color}-400" "text-${color}-11" "${color} 600/400 → 11"
  run_sed "text-${color}-600 dark:text-${color}-300" "text-${color}-11" "${color} 600/300 → 11"
  run_sed "text-${color}-500 dark:text-${color}-400" "text-${color}-9" "${color} 500/400 → 9"
  run_sed "text-${color}-500 dark:text-${color}-300" "text-${color}-9" "${color} 500/300 → 9"
done

# Remove orphaned dark:text-* patterns
run_sed ' dark:text-neutral-100' '' 'remove dark:text-neutral-100'
run_sed ' dark:text-neutral-200' '' 'remove dark:text-neutral-200'
run_sed ' dark:text-neutral-300' '' 'remove dark:text-neutral-300'

# ===========================================================================
# PHASE 3: BORDER COLORS (dark:border-*)
# ===========================================================================
echo "Phase 3: Migrating borders..."

run_sed 'border-neutral-200 dark:border-neutral-700' 'border-neutral-6' '200/700 → neutral-6'
run_sed 'border-neutral-200 dark:border-neutral-600' 'border-neutral-6' '200/600 → neutral-6'
run_sed 'border-neutral-200 dark:border-neutral-800' 'border-neutral-6' '200/800 → neutral-6'
run_sed 'border-neutral-300 dark:border-neutral-600' 'border-neutral-6' '300/600 → neutral-6'
run_sed 'border-neutral-300 dark:border-neutral-700' 'border-neutral-7' '300/700 → neutral-7'
run_sed 'border-neutral-300 dark:border-neutral-800' 'border-neutral-7' '300/800 → neutral-7'

# Semantic border colors
for color in primary success warning error info insight; do
  run_sed "border-${color}-200 dark:border-${color}-700" "border-${color}-6" "${color} 200/700 → 6"
  run_sed "border-${color}-200 dark:border-${color}-800" "border-${color}-6" "${color} 200/800 → 6"
  run_sed "border-${color}-300 dark:border-${color}-700" "border-${color}-7" "${color} 300/700 → 7"
  run_sed "border-${color}-500 dark:border-${color}-400" "border-${color}-9" "${color} 500/400 → 9"
done

# Remove orphaned dark:border-*
run_sed ' dark:border-neutral-700' '' 'remove dark:border-neutral-700'
run_sed ' dark:border-neutral-800' '' 'remove dark:border-neutral-800'

# ===========================================================================
# PHASE 4: HOVER STATES (dark:hover:*)
# ===========================================================================
echo "Phase 4: Migrating hover states..."

# Background hovers
run_sed 'hover:bg-neutral-100 dark:hover:bg-neutral-700' 'hover:bg-neutral-4' 'hover 100/700 → 4'
run_sed 'hover:bg-neutral-100 dark:hover:bg-neutral-800' 'hover:bg-neutral-3' 'hover 100/800 → 3'
run_sed 'hover:bg-neutral-50 dark:hover:bg-neutral-800' 'hover:bg-neutral-3' 'hover 50/800 → 3'
run_sed 'hover:bg-neutral-200 dark:hover:bg-neutral-600' 'hover:bg-neutral-5' 'hover 200/600 → 5'
run_sed 'hover:bg-neutral-200 dark:hover:bg-neutral-700' 'hover:bg-neutral-5' 'hover 200/700 → 5'

# Text hovers
run_sed 'hover:text-neutral-900 dark:hover:text-neutral-100' 'hover:text-neutral-12' 'hover text 900/100 → 12'
run_sed 'hover:text-neutral-800 dark:hover:text-neutral-200' 'hover:text-neutral-12' 'hover text 800/200 → 12'
run_sed 'hover:text-neutral-700 dark:hover:text-neutral-300' 'hover:text-neutral-11' 'hover text 700/300 → 11'

# Remove orphaned dark:hover:*
run_sed ' dark:hover:bg-neutral-700' '' 'remove dark:hover:bg-neutral-700'
run_sed ' dark:hover:bg-neutral-800' '' 'remove dark:hover:bg-neutral-800'
run_sed ' dark:hover:text-neutral-300' '' 'remove dark:hover:text-neutral-300'
run_sed ' dark:hover:text-neutral-200' '' 'remove dark:hover:text-neutral-200'

# ===========================================================================
# PHASE 5: FOCUS STATES (dark:focus:*)
# ===========================================================================
echo "Phase 5: Migrating focus states..."

run_sed 'focus:border-primary-500 dark:focus:border-primary-400' 'focus:border-primary-9' 'focus border primary → 9'
run_sed 'focus:ring-primary-500 dark:focus:ring-primary-400' 'focus:ring-primary-9' 'focus ring primary → 9'
run_sed 'focus:ring-primary-500/20 dark:focus:ring-primary-400/20' 'focus:ring-primary-9/20' 'focus ring opacity → 9/20'

# ===========================================================================
# PHASE 6: PLACEHOLDERS
# ===========================================================================
echo "Phase 6: Migrating placeholders..."

run_sed 'placeholder:text-neutral-400 dark:placeholder:text-neutral-500' 'placeholder:text-neutral-9' 'placeholder 400/500 → 9'
run_sed 'placeholder:text-neutral-500 dark:placeholder:text-neutral-400' 'placeholder:text-neutral-9' 'placeholder 500/400 → 9'
run_sed 'placeholder-neutral-400 dark:placeholder-neutral-500' 'placeholder-neutral-9' 'placeholder 400/500 → 9'
run_sed 'placeholder-neutral-500 dark:placeholder-neutral-400' 'placeholder-neutral-9' 'placeholder 500/400 → 9'

# ===========================================================================
# PHASE 7: STANDALONE ORPHAN CLEANUP
# ===========================================================================
echo "Phase 7: Cleaning up standalone orphan patterns..."

# These are dark:* patterns that exist WITHOUT a light counterpart
# They should use Radix semantic colors that auto-switch

# Standalone dark:bg-* (most common orphans)
run_sed ' dark:bg-neutral-900/30' '' 'remove standalone dark:bg-neutral-900/30'
run_sed ' dark:bg-primary-900/30' '' 'remove standalone dark:bg-primary-900/30'
run_sed ' dark:bg-warning-900/20' '' 'remove standalone dark:bg-warning-900/20'
run_sed ' dark:bg-error-900/30' '' 'remove standalone dark:bg-error-900/30'

# Standalone dark:text-* (common orphans) - these usually indicate missing Radix migration
run_sed ' dark:text-primary-400' '' 'remove standalone dark:text-primary-400'
run_sed ' dark:text-error-400' '' 'remove standalone dark:text-error-400'
run_sed ' dark:text-warning-400' '' 'remove standalone dark:text-warning-400'
run_sed ' dark:text-success-400' '' 'remove standalone dark:text-success-400'
run_sed ' dark:text-insight-400' '' 'remove standalone dark:text-insight-400'

echo ""
echo "=== Migration complete ==="
echo ""
echo "Next steps:"
echo "1. Run: npm run build"
echo "2. Run: npm run lint"
echo "3. Manually review any remaining dark: patterns"
echo "4. Test dark/light mode switching visually"
