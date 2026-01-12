#!/bin/bash
# Gray to Neutral Color Migration Script
#
# Migrates gray-* Tailwind classes to neutral-* for design system consistency.
# Run with --dry-run to preview changes before applying.
#
# Usage:
#   ./scripts/migrate-gray-to-neutral.sh [--dry-run] [directory]
#
# Examples:
#   ./scripts/migrate-gray-to-neutral.sh --dry-run src/components/UI
#   ./scripts/migrate-gray-to-neutral.sh src/components/UI

set -euo pipefail

# Configuration
DRY_RUN=false
TARGET_DIR="${2:-src/components/UI}"
BACKUP_DIR=".migration-backup-$(date +%Y%m%d-%H%M%S)"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  TARGET_DIR="${2:-src/components/UI}"
  echo -e "${YELLOW}DRY RUN MODE - No files will be modified${NC}"
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Gray to Neutral Migration Tool${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "Target directory: ${GREEN}${TARGET_DIR}${NC}"
echo ""

# Check if ripgrep is available
if ! command -v rg &> /dev/null; then
  echo -e "${RED}Error: ripgrep (rg) is required but not installed.${NC}"
  echo "Install with: brew install ripgrep"
  exit 1
fi

# Find files with gray-* usage
echo -e "${BLUE}Scanning for gray-* usage...${NC}"
FILES_WITH_GRAY=$(rg -l 'gray-\d+' "$TARGET_DIR" --type tsx --type ts 2>/dev/null || true)

if [[ -z "$FILES_WITH_GRAY" ]]; then
  echo -e "${GREEN}No gray-* usage found in ${TARGET_DIR}${NC}"
  exit 0
fi

# Count occurrences
TOTAL_GRAY=$(rg -c 'gray-\d+' "$TARGET_DIR" --type tsx --type ts 2>/dev/null | awk -F: '{sum += $2} END {print sum}')
echo -e "Found ${YELLOW}${TOTAL_GRAY}${NC} gray-* occurrences in:"
echo "$FILES_WITH_GRAY" | while read -r file; do
  count=$(rg -c 'gray-\d+' "$file" 2>/dev/null || echo "0")
  echo -e "  - ${file}: ${count} occurrences"
done
echo ""

# Define replacement patterns
# gray-50 through gray-950 -> neutral-50 through neutral-950
PATTERNS=(
  "gray-50:neutral-50"
  "gray-100:neutral-100"
  "gray-200:neutral-200"
  "gray-300:neutral-300"
  "gray-400:neutral-400"
  "gray-500:neutral-500"
  "gray-600:neutral-600"
  "gray-700:neutral-700"
  "gray-800:neutral-800"
  "gray-900:neutral-900"
  "gray-950:neutral-950"
)

if [[ "$DRY_RUN" == true ]]; then
  echo -e "${YELLOW}Preview of changes:${NC}"
  echo ""
  for file in $FILES_WITH_GRAY; do
    echo -e "${BLUE}File: ${file}${NC}"
    rg 'gray-\d+' "$file" --color=always -n | head -10
    echo ""
  done
  echo -e "${YELLOW}Run without --dry-run to apply changes.${NC}"
  exit 0
fi

# Create backup
echo -e "${BLUE}Creating backup in ${BACKUP_DIR}...${NC}"
mkdir -p "$BACKUP_DIR"
for file in $FILES_WITH_GRAY; do
  cp "$file" "$BACKUP_DIR/"
done

# Apply replacements
echo -e "${BLUE}Applying replacements...${NC}"
for pattern in "${PATTERNS[@]}"; do
  OLD="${pattern%%:*}"
  NEW="${pattern##*:}"

  # Use sed for replacement (macOS compatible)
  for file in $FILES_WITH_GRAY; do
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s/${OLD}/${NEW}/g" "$file"
    else
      sed -i "s/${OLD}/${NEW}/g" "$file"
    fi
  done
done

# Verify changes
echo ""
echo -e "${GREEN}Migration complete!${NC}"
echo ""
REMAINING_GRAY=$(rg -c 'gray-\d+' "$TARGET_DIR" --type tsx --type ts 2>/dev/null | awk -F: '{sum += $2} END {print sum}' || echo "0")
echo -e "Remaining gray-* usage in ${TARGET_DIR}: ${REMAINING_GRAY}"
echo -e "Backup saved to: ${BACKUP_DIR}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Review the changes: git diff"
echo "  2. Run tests: npm test"
echo "  3. Delete backup if satisfied: rm -rf ${BACKUP_DIR}"
