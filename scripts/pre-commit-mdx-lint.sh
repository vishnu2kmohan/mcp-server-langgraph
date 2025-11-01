#!/usr/bin/env bash
#
# Pre-commit hook to validate and fix MDX files
#
# Installation:
#   ln -s ../../scripts/pre-commit-mdx-lint.sh .git/hooks/pre-commit
#
# Or add to .git/hooks/pre-commit:
#   ./scripts/pre-commit-mdx-lint.sh
#

set -e

echo "🔍 Validating MDX files..."

# Get the root directory
ROOT_DIR="$(git rev-parse --show-toplevel)"
cd "$ROOT_DIR"

# Track if any fixes were applied
FIXES_APPLIED=0

# Step 1: Fix angle brackets
echo "  → Fixing angle brackets..."
if python scripts/fix_mdx_angle_brackets.py | grep -q "modified"; then
    FIXES_APPLIED=1
    echo "    ✓ Fixed angle brackets"
fi

# Step 2: Check for stray XML tags
echo "  → Checking for stray XML tags..."
if find docs -name "*.mdx" -type f -exec grep -l '```xml$' {} \; 2>/dev/null | grep -q .; then
    echo "    ⚠ Found stray ```xml tags, fixing..."
    find docs -name "*.mdx" -type f -exec sed -i 's/```xml$/```/g' {} \;
    FIXES_APPLIED=1
    echo "    ✓ Fixed XML tags"
fi

# Step 3: Validate MDX syntax
echo "  → Validating MDX syntax..."
if ! python scripts/validate_mdx_syntax.py; then
    echo "❌ MDX validation failed!"
    echo "   Run 'python scripts/validate_mdx_syntax.py' to see errors"
    exit 1
fi

# Step 4: Stage any fixes that were applied
if [ $FIXES_APPLIED -eq 1 ]; then
    echo ""
    echo "📝 Auto-fixes were applied. Staging changes..."
    git add docs/**/*.mdx 2>/dev/null || true
    echo "   ✓ Changes staged"
fi

echo ""
echo "✅ MDX validation passed!"
exit 0
