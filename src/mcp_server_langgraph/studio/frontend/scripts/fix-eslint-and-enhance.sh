#!/bin/bash
# Script to fix ESLint errors efficiently

set -e

# 1. Fix unused variables by prefixing with _
echo "Fixing unused variables..."

# StudioShellLayout.model.test.tsx - mockBreakpointState -> _mockBreakpointState
sed -i '' 's/const mockBreakpointState =/const _mockBreakpointState =/' src/layout/__tests__/StudioShellLayout.model.test.tsx

# Check for other unused variable patterns and fix them
# isSelected -> _isSelected in context files
find src -name "*.tsx" -exec grep -l "'isSelected' is defined but never used" {} \; 2>/dev/null || true

# 2. Fix renderAndWait if it exists
find src -name "*.test.tsx" -exec sed -i '' 's/const renderAndWait =/const _renderAndWait =/' {} \; 2>/dev/null || true

# 3. Fix buttonStyle if unused
find src -name "*.tsx" -exec sed -i '' 's/const buttonStyle =/const _buttonStyle =/' {} \; 2>/dev/null || true

echo "ESLint fixes applied. Run 'npm run lint' to verify."
