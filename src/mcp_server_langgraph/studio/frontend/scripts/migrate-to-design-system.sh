#!/bin/bash
#
# Design System Migration Script
#
# Migrates raw HTML elements to design system components using AST transforms.
#
# Usage:
#   ./scripts/migrate-to-design-system.sh [options] [target]
#
# Options:
#   --buttons     Migrate <button> → <Button>
#   --inputs      Migrate <input>/<select>/<textarea> → Input/Select/Textarea
#   --all         Run all migrations
#   --dry-run     Preview changes without modifying files
#   --check       Show files that need migration (no changes)
#
# Target:
#   Path to file or directory. Defaults to src/
#
# Examples:
#   ./scripts/migrate-to-design-system.sh --buttons src/pages/
#   ./scripts/migrate-to-design-system.sh --all --dry-run
#   ./scripts/migrate-to-design-system.sh --check
#

set -e

# Colors for output
# shellcheck disable=SC2034  # RED kept for color palette completeness
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
MIGRATE_BUTTONS=false
MIGRATE_INPUTS=false
DRY_RUN=false
CHECK_ONLY=false
TARGET="src/"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --buttons)
      MIGRATE_BUTTONS=true
      shift
      ;;
    --inputs)
      MIGRATE_INPUTS=true
      shift
      ;;
    --all)
      MIGRATE_BUTTONS=true
      MIGRATE_INPUTS=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --check)
      CHECK_ONLY=true
      shift
      ;;
    -h|--help)
      head -30 "$0" | tail -28
      exit 0
      ;;
    *)
      TARGET="$1"
      shift
      ;;
  esac
done

# If no migration type selected, default to --all
if [[ "$MIGRATE_BUTTONS" == "false" && "$MIGRATE_INPUTS" == "false" && "$CHECK_ONLY" == "false" ]]; then
  MIGRATE_BUTTONS=true
  MIGRATE_INPUTS=true
fi

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}   Design System Migration Tool${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check mode: just report what needs migration
if [[ "$CHECK_ONLY" == "true" ]]; then
  echo -e "${YELLOW}Checking files that need migration...${NC}"
  echo ""

  echo -e "${BLUE}Files with raw <button> elements (excluding tests):${NC}"
  rg -c '<button' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | sort -t: -k2 -rn | head -20 || echo "  None found"
  echo ""

  echo -e "${BLUE}Files with raw <input> elements (excluding tests):${NC}"
  rg -c '<input' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | sort -t: -k2 -rn | head -20 || echo "  None found"
  echo ""

  echo -e "${BLUE}Files with raw <select> elements (excluding tests):${NC}"
  rg -c '<select' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | sort -t: -k2 -rn | head -20 || echo "  None found"
  echo ""

  echo -e "${BLUE}Files with raw <textarea> elements (excluding tests):${NC}"
  rg -c '<textarea' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | sort -t: -k2 -rn | head -20 || echo "  None found"

  exit 0
fi

# Build jscodeshift options
# Use babel parser with typescript plugin for proper TSX support
JSCODESHIFT_OPTS="--parser=tsx --extensions=tsx"
if [[ "$DRY_RUN" == "true" ]]; then
  JSCODESHIFT_OPTS="$JSCODESHIFT_OPTS --dry"
  echo -e "${YELLOW}DRY RUN MODE - No files will be modified${NC}"
  echo ""
fi

# Find files to process (exclude test files)
find_source_files() {
  find "$TARGET" -name '*.tsx' \
    ! -name '*.test.tsx' \
    ! -name '*.spec.tsx' \
    ! -path '*/test/*' \
    ! -path '*/__tests__/*' \
    ! -path '*/stories/*' \
    2>/dev/null
}

# Run button migration
if [[ "$MIGRATE_BUTTONS" == "true" ]]; then
  echo -e "${GREEN}[1/2] Migrating buttons...${NC}"

  # Count before
  BEFORE=$(rg -c '<button' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')

  # Run codemod
  FILES=$(find_source_files | xargs rg -l '<button' 2>/dev/null || true)
  if [[ -n "$FILES" ]]; then
    echo "$FILES" | xargs npx jscodeshift $JSCODESHIFT_OPTS -t scripts/codemods/migrate-buttons.ts 2>&1 | grep -v "^Processing" || true
  else
    echo "  No files with raw buttons found"
  fi

  if [[ "$DRY_RUN" == "false" ]]; then
    AFTER=$(rg -c '<button' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
    echo -e "  ${BLUE}Buttons: $BEFORE → $AFTER (migrated $((BEFORE - AFTER)))${NC}"
  fi
  echo ""
fi

# Run input migration
if [[ "$MIGRATE_INPUTS" == "true" ]]; then
  echo -e "${GREEN}[2/2] Migrating inputs/selects/textareas...${NC}"

  # Count before
  INPUT_BEFORE=$(rg -c '<input' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
  SELECT_BEFORE=$(rg -c '<select' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
  TEXTAREA_BEFORE=$(rg -c '<textarea' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')

  # Run codemod
  FILES=$(find_source_files | xargs rg -l '<input\|<select\|<textarea' 2>/dev/null || true)
  if [[ -n "$FILES" ]]; then
    echo "$FILES" | xargs npx jscodeshift $JSCODESHIFT_OPTS -t scripts/codemods/migrate-inputs.ts 2>&1 | grep -v "^Processing" || true
  else
    echo "  No files with raw form elements found"
  fi

  if [[ "$DRY_RUN" == "false" ]]; then
    INPUT_AFTER=$(rg -c '<input' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
    SELECT_AFTER=$(rg -c '<select' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
    TEXTAREA_AFTER=$(rg -c '<textarea' "$TARGET" --glob '*.tsx' --glob '!*.test.*' --glob '!*.spec.*' 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
    echo -e "  ${BLUE}Inputs:    $INPUT_BEFORE → $INPUT_AFTER (migrated $((INPUT_BEFORE - INPUT_AFTER)))${NC}"
    echo -e "  ${BLUE}Selects:   $SELECT_BEFORE → $SELECT_AFTER (migrated $((SELECT_BEFORE - SELECT_AFTER)))${NC}"
    echo -e "  ${BLUE}Textareas: $TEXTAREA_BEFORE → $TEXTAREA_AFTER (migrated $((TEXTAREA_BEFORE - TEXTAREA_AFTER)))${NC}"
  fi
  echo ""
fi

echo -e "${BLUE}================================================${NC}"

if [[ "$DRY_RUN" == "true" ]]; then
  echo -e "${YELLOW}Dry run complete. Run without --dry-run to apply changes.${NC}"
else
  echo -e "${GREEN}Migration complete!${NC}"
  echo ""
  echo "Next steps:"
  echo "  1. Run tests: npm test"
  echo "  2. Run lint:  npm run lint"
  echo "  3. Review changes: git diff"
fi
