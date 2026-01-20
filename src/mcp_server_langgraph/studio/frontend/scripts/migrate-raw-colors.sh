#!/usr/bin/env bash
#
# Color Migration Script
#
# Finds raw Tailwind color classes and suggests semantic replacements.
# Use --fix to automatically apply common migrations.
#
# Usage:
#   ./scripts/migrate-raw-colors.sh          # Audit mode (report only)
#   ./scripts/migrate-raw-colors.sh --fix    # Apply common fixes
#
# Semantic Color Mappings:
#   violet-*  -> insight-*  (AI features)
#   indigo-*  -> primary-*  (Primary actions)
#   blue-*    -> primary-*  (Primary actions)
#   emerald-* -> success-*  (Success states)
#   green-*   -> success-*  (Success states)
#   red-*     -> error-*    (Error states)
#   rose-*    -> error-*    (Error states)
#   amber-*   -> warning-*  (Warning states)
#   yellow-*  -> warning-*  (Warning states)
#   cyan-*    -> info-*     (Informational)
#   teal-*    -> info-*     (Informational)
#   gray-*    -> neutral-*  (General UI)
#   slate-*   -> neutral-*  (General UI)
#   zinc-*    -> neutral-*  (General UI)
#   stone-*   -> neutral-*  (General UI)
#
# Exceptions (do not migrate):
#   - NodePalette.tsx: Categorical node type colors
#   - Chart/visualization components: Programmatic SVG colors
#   - Test files with color assertions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${SCRIPT_DIR}/../src"

# Color mapping: raw -> semantic
declare -A COLOR_MAP=(
    ["violet"]="insight"
    ["indigo"]="primary"
    ["blue"]="primary"
    ["emerald"]="success"
    ["green"]="success"
    ["red"]="error"
    ["rose"]="error"
    ["amber"]="warning"
    ["yellow"]="warning"
    ["cyan"]="info"
    ["teal"]="info"
    ["gray"]="neutral"
    ["slate"]="neutral"
    ["zinc"]="neutral"
    ["stone"]="neutral"
)

# Files/patterns to exclude from automatic fixes
EXCLUDE_PATTERNS=(
    "NodePalette.tsx"           # Categorical node colors
    "TraceNode.tsx"             # Trace visualization
    "TraceCanvas.tsx"           # Trace visualization
    "ChartArtifact.tsx"         # Chart colors
    "InteractiveChart.tsx"      # Chart colors
    "ConnectionTemplateSelector.tsx"  # Template colors
    "*.test.tsx"                # Test files
    "*.stories.tsx"             # Storybook files
    "tokens.ts"                 # Design tokens (defines raw values)
)

# Build exclude pattern for rg
build_exclude_args() {
    local exclude_args=""
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        exclude_args+=" --glob '!${pattern}'"
    done
    echo "$exclude_args"
}

# Audit mode: report all raw color usage
audit_colors() {
    echo "=== RAW COLOR AUDIT ==="
    echo ""
    echo "Scanning for raw Tailwind color classes..."
    echo ""

    cd "$SRC_DIR"

    # Count by color type
    echo "=== Usage by Color Type ==="
    rg -o '\b(blue|red|green|yellow|purple|orange|pink|cyan|teal|indigo|amber|lime|emerald|rose|fuchsia|violet|sky|slate|zinc|stone)-[0-9]{2,3}\b' \
        --glob '*.tsx' --glob '*.ts' 2>/dev/null | \
        cut -d: -f2 | cut -d- -f1 | sort | uniq -c | sort -rn || echo "No raw colors found."

    echo ""
    echo "=== Files with Raw Colors ==="
    rg -c '\b(blue|red|green|yellow|purple|orange|pink|cyan|teal|indigo|amber|lime|emerald|rose|fuchsia|violet|sky|slate|zinc|stone)-[0-9]{2,3}\b' \
        --glob '*.tsx' --glob '*.ts' 2>/dev/null | sort -t: -k2 -nr | head -20 || echo "No files found."

    echo ""
    echo "=== Suggested Migrations ==="
    for raw in "${!COLOR_MAP[@]}"; do
        local semantic="${COLOR_MAP[$raw]}"
        local count
        count=$(rg -c "\b${raw}-[0-9]{2,3}\b" --glob '*.tsx' --glob '*.ts' 2>/dev/null | \
                awk -F: '{sum += $2} END {print sum}' || echo "0")
        if [[ "$count" -gt 0 ]]; then
            echo "  ${raw}-* -> ${semantic}-* : ${count} instances"
        fi
    done

    echo ""
    echo "Run with --fix to apply common migrations."
    echo "Excluded files: ${EXCLUDE_PATTERNS[*]}"
}

# Fix mode: apply common migrations
fix_colors() {
    echo "=== APPLYING COLOR MIGRATIONS ==="
    echo ""

    cd "$SRC_DIR"

    # Build list of files to process (excluding exceptions)
    local files_to_process
    files_to_process=$(rg -l '\b(violet|indigo)-[0-9]{2,3}\b' --glob '*.tsx' --glob '*.ts' 2>/dev/null | \
        grep -v -E "(NodePalette|TraceNode|TraceCanvas|ChartArtifact|InteractiveChart|ConnectionTemplateSelector|\.test\.|\.stories\.)" || true)

    if [[ -z "$files_to_process" ]]; then
        echo "No files to migrate (after exclusions)."
        return 0
    fi

    # Apply high-priority migrations
    echo "Migrating violet-* -> insight-* ..."
    echo "$files_to_process" | xargs -I{} sed -i '' 's/violet-/insight-/g' {} 2>/dev/null || true

    echo "Migrating indigo-* -> primary-* ..."
    echo "$files_to_process" | xargs -I{} sed -i '' 's/indigo-/primary-/g' {} 2>/dev/null || true

    echo ""
    echo "Migration complete. Please review changes with: git diff"
    echo ""
    echo "Remaining raw colors (may be intentional):"
    rg -c '\b(blue|red|green|yellow|purple|orange|pink|cyan|teal|amber|lime|emerald|rose|fuchsia|sky|slate|zinc|stone)-[0-9]{2,3}\b' \
        --glob '*.tsx' --glob '*.ts' 2>/dev/null | sort -t: -k2 -nr | head -10 || echo "None found."
}

# Main
case "${1:-}" in
    --fix)
        fix_colors
        ;;
    --help|-h)
        echo "Usage: $0 [--fix]"
        echo ""
        echo "Options:"
        echo "  (none)  Audit mode - report raw color usage"
        echo "  --fix   Apply common color migrations"
        echo "  --help  Show this help message"
        ;;
    *)
        audit_colors
        ;;
esac
