#!/bin/bash
# =============================================================================
# Storage Usage Checker & Migration Helper
# =============================================================================
#
# This script checks for direct localStorage usage in the codebase and helps
# migrate to the unified storage utility.
#
# Usage:
#   ./scripts/check-storage-usage.sh [command]
#
# Commands:
#   report    - Generate detailed report of localStorage usage (default)
#   check     - Quick check for violations (CI-friendly)
#   migrate   - Show migration suggestions for each file
#   stats     - Show storage key statistics
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SRC_DIR="$PROJECT_DIR/src"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# =============================================================================
# Helper Functions
# =============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}=== $1 ===${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# =============================================================================
# Report Command
# =============================================================================

generate_report() {
    print_header "localStorage Usage Report"

    echo "Generated: $(date)"
    echo "Project: mcp-server-langgraph/studio/frontend"
    echo ""

    # Check production files (excluding tests and storage.ts)
    print_header "Production Files Analysis"

    PROD_VIOLATIONS=$(grep -rn "localStorage\." "$SRC_DIR" \
        --include="*.ts" --include="*.tsx" \
        | grep -v "\.test\." \
        | grep -v "\.spec\." \
        | grep -v "storage\.ts" \
        | grep -v "node_modules" \
        || true)

    if [ -z "$PROD_VIOLATIONS" ]; then
        print_success "No direct localStorage usage in production files!"
        echo ""
        echo "All production code correctly uses the storage utility."
    else
        print_error "Found direct localStorage usage in production files:"
        echo ""
        echo "$PROD_VIOLATIONS"
    fi

    # Storage utility analysis
    print_header "Storage Utility (utils/storage.ts)"

    STORAGE_USAGES=$(grep -c "localStorage\." "$SRC_DIR/utils/storage.ts" || echo "0")
    echo "localStorage references in storage utility: $STORAGE_USAGES"
    echo "(These are expected - storage.ts wraps localStorage)"

    # Test files analysis
    print_header "Test Files Analysis"

    TEST_USAGES=$(grep -rn "localStorage" "$SRC_DIR" \
        --include="*.test.ts" --include="*.test.tsx" \
        --include="*.spec.ts" --include="*.spec.tsx" \
        | wc -l || echo "0")

    echo "localStorage references in test files: $TEST_USAGES"
    echo "(These are expected - tests mock localStorage)"

    # STORAGE_KEYS analysis
    print_header "STORAGE_KEYS Registry"

    echo "Defined keys in utils/storage.ts:"
    grep -A 30 "export const STORAGE_KEYS" "$SRC_DIR/utils/storage.ts" \
        | grep -E "^\s+[A-Z_]+:" \
        | sed 's/^/  /' \
        || echo "  (Could not parse STORAGE_KEYS)"

    print_header "Summary"

    if [ -z "$PROD_VIOLATIONS" ]; then
        print_success "Migration Complete!"
        echo ""
        echo "All production files use the storage utility."
        echo "ESLint rule 'no-restricted-globals' enforces this going forward."
    else
        print_warning "Migration Incomplete"
        echo ""
        echo "Some production files still use localStorage directly."
        echo "Run './scripts/check-storage-usage.sh migrate' for suggestions."
    fi
}

# =============================================================================
# Check Command (CI-friendly)
# =============================================================================

check_violations() {
    VIOLATIONS=$(grep -rn "localStorage\." "$SRC_DIR" \
        --include="*.ts" --include="*.tsx" \
        | grep -v "\.test\." \
        | grep -v "\.spec\." \
        | grep -v "storage\.ts" \
        | grep -v "node_modules" \
        || true)

    if [ -z "$VIOLATIONS" ]; then
        print_success "No localStorage violations found"
        exit 0
    else
        print_error "Found localStorage violations:"
        echo "$VIOLATIONS"
        exit 1
    fi
}

# =============================================================================
# Migrate Command
# =============================================================================

show_migration_suggestions() {
    print_header "Migration Suggestions"

    echo "For each file with direct localStorage usage, here are the recommended changes:"
    echo ""

    cat << 'EOF'
## Common Migrations

### 1. Simple get/set operations:

BEFORE:
  const value = localStorage.getItem("my-key");
  localStorage.setItem("my-key", JSON.stringify(data));
  localStorage.removeItem("my-key");

AFTER:
  import { storage } from "../utils/storage";

  const value = storage.get<MyType>("my-key");
  storage.set("my-key", data);
  storage.remove("my-key");

### 2. Auth token operations:

BEFORE:
  const token = localStorage.getItem("access_token") || localStorage.getItem("auth_token");
  localStorage.setItem("access_token", token);
  localStorage.removeItem("access_token");

AFTER:
  import { getAuthToken, setAuthTokens, clearAuthTokens } from "../utils/storage";

  const token = getAuthToken();
  setAuthTokens(accessToken, refreshToken);
  clearAuthTokens();

### 3. Object storage with validation:

BEFORE:
  const stored = localStorage.getItem("preferences");
  if (stored) {
    try {
      const data = JSON.parse(stored);
      // use data
    } catch { /* handle error */ }
  }

AFTER:
  import { storage, STORAGE_KEYS } from "../utils/storage";

  const data = storage.get<PreferencesType>(STORAGE_KEYS.PREFERENCES, {
    expectObject: true,
    validator: isValidPreferences,
  });

### 4. Add new keys to STORAGE_KEYS:

If you have a new storage key, add it to STORAGE_KEYS in utils/storage.ts:

  export const STORAGE_KEYS = {
    // ... existing keys ...
    MY_NEW_KEY: "studio-my-new-key",
  } as const;

### 5. Listing/iterating keys:

BEFORE:
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    // ...
  }

AFTER:
  import { storage } from "../utils/storage";

  const keys = storage.keys(); // Returns all studio-* keys
  for (const key of keys) {
    // ...
  }

EOF
}

# =============================================================================
# Stats Command
# =============================================================================

show_stats() {
    print_header "Storage Key Statistics"

    echo "Analyzing usage of STORAGE_KEYS across the codebase..."
    echo ""

    # Extract all STORAGE_KEYS
    KEYS=$(grep -oE "STORAGE_KEYS\.[A-Z_]+" "$SRC_DIR" -r --include="*.ts" --include="*.tsx" \
        | grep -v "node_modules" \
        | cut -d: -f2 \
        | sort \
        | uniq -c \
        | sort -rn)

    if [ -z "$KEYS" ]; then
        echo "No STORAGE_KEYS usage found."
    else
        echo "STORAGE_KEYS usage (sorted by frequency):"
        echo ""
        echo "$KEYS" | while read count key; do
            printf "  %3d  %s\n" "$count" "$key"
        done
    fi

    echo ""
    print_header "Storage Utility Function Usage"

    echo "Analyzing usage of storage utility functions..."
    echo ""

    for func in "storage.get" "storage.set" "storage.remove" "storage.keys" "storage.clear" "getAuthToken" "setAuthTokens" "clearAuthTokens"; do
        count=$(grep -r "$func" "$SRC_DIR" --include="*.ts" --include="*.tsx" \
            | grep -v "node_modules" \
            | grep -v "storage\.ts" \
            | wc -l || echo "0")
        printf "  %3d  %s()\n" "$count" "$func"
    done
}

# =============================================================================
# Main
# =============================================================================

COMMAND="${1:-report}"

case "$COMMAND" in
    report)
        generate_report
        ;;
    check)
        check_violations
        ;;
    migrate)
        show_migration_suggestions
        ;;
    stats)
        show_stats
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo ""
        echo "Usage: $0 [report|check|migrate|stats]"
        exit 1
        ;;
esac
