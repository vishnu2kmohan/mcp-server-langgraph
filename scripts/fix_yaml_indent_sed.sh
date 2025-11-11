#!/bin/bash
#
# Fix YAML indentation issues using sed.
#
# The pattern: List items and their properties are 2 spaces under-indented.
# Strategy: Process files line-by-line, tracking context and fixing indentation.
#

set -euo pipefail

# Process a single YAML file
fix_yaml_file() {
    local file="$1"
    local tmpfile="${file}.tmp"

    echo "Processing: $file"

    # Use Python for more reliable indentation fixing
    python3 -c "
import sys

def fix_indentation(lines):
    '''Fix YAML indentation issues.'''
    fixed = []
    prev_line_ends_with_colon = False
    in_list = False
    list_indent = 0

    for i, line in enumerate(lines):
        stripped = line.lstrip()

        # Skip empty lines, comments, document markers
        if not stripped or stripped.startswith('#') or stripped in ['---', '...']:
            fixed.append(line)
            prev_line_ends_with_colon = False
            continue

        current_indent = len(line) - len(stripped)

        # Track if previous line was a key (ends with :)
        if i > 0:
            prev_stripped = lines[i-1].strip()
            if prev_stripped and not prev_stripped.startswith('#'):
                prev_line_ends_with_colon = prev_stripped.endswith(':')
                if prev_stripped.endswith(':'):
                    list_indent = len(lines[i-1]) - len(lines[i-1].lstrip())

        # Check if current line is a list item
        if stripped.startswith('- '):
            # If previous line ended with ':', this list item should be indented 2 more
            if prev_line_ends_with_colon and current_indent == list_indent:
                line = '  ' + line
                in_list = True
            fixed.append(line)
            prev_line_ends_with_colon = False
        else:
            # Check if this is a property of a list item
            # (non-list line following a list item at same or less indent)
            if in_list and i > 0:
                prev_stripped = lines[i-1].strip()
                if prev_stripped.startswith('- '):
                    prev_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                    # Properties should be aligned with first property after '- '
                    # which is at prev_indent + 2
                    expected_indent = prev_indent + 2
                    if current_indent < expected_indent:
                        spaces_to_add = expected_indent - current_indent
                        line = (' ' * spaces_to_add) + line

            fixed.append(line)
            prev_line_ends_with_colon = False

    return fixed

# Read input file
with open('$file', 'r') as f:
    lines = f.readlines()

# Fix indentation
fixed_lines = fix_indentation(lines)

# Write output
with open('$tmpfile', 'w') as f:
    f.writelines(fixed_lines)
"

    if [ $? -eq 0 ] && [ -f "$tmpfile" ]; then
        mv "$tmpfile" "$file"
        echo "  ✅ Fixed"
        return 0
    else
        echo "  ❌ Error"
        rm -f "$tmpfile"
        return 1
    fi
}

# Files to fix
FILES=(
    "deployments/base/deployment.yaml"
    "deployments/base/redis-session-deployment.yaml"
    "deployments/base/postgres-statefulset.yaml"
    "deployments/base/role.yaml"
    "deployments/base/keycloak-deployment.yaml"
    "deployments/base/openfga-deployment.yaml"
    "deployments/base/service.yaml"
    "deployments/base/hpa.yaml"
    "deployments/base/keycloak-service.yaml"
    "deployments/base/redis-session-service.yaml"
    "deployments/optimized/deployment.yaml"
    "deployments/optimized/postgres-statefulset.yaml"
    "deployments/optimized/hpa.yaml"
    "deployments/optimized/redis-session-deployment.yaml"
    "deployments/cloudrun/service.yaml"
    "deployments/kubernetes/skaffold.yaml"
    "deployments/kubernetes/kong/kong-ingress.yaml"
    "deployments/kubernetes/kong/kong-apikey-jwt-plugin.yaml"
    "deployments/kubernetes/kong/kong-jwks-updater-cronjob.yaml"
    "deployments/kubernetes/kong/redis-deployment.yaml"
    "deployments/components/gcp-cloud-sql-proxy/cloud-sql-proxy-sidecar.yaml"
)

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "Fixing YAML indentation in ${#FILES[@]} files..."
echo

FIXED=0
ERRORS=0

for file in "${FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "⚠️  Not found: $file"
        ((ERRORS++))
        continue
    fi

    if fix_yaml_file "$file"; then
        ((FIXED++))
    else
        ((ERRORS++))
    fi
done

echo
echo "📊 Summary:"
echo "  ✅ Fixed: $FIXED"
echo "  ❌ Errors: $ERRORS"
echo "  📁 Total: ${#FILES[@]}"

exit 0
