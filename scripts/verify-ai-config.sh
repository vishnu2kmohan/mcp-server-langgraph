#!/usr/bin/env bash
# verify-ai-config.sh - Verify AI agent configuration files
#
# This script runs comprehensive validation checks on all AI config files
# to ensure they follow the AGENTS.md standard and Vercel/GitHub best practices.
#
# Usage: ./scripts/verify-ai-config.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++)) || true
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((ERRORS++)) || true
}

cd "$PROJECT_ROOT"

echo "========================================="
echo "AI Configuration Verification"
echo "========================================="
echo ""

# === Format Validation ===
echo "=== Format Validation ==="
echo ""

# Check files under .claude/ exist
log_info "Checking .claude/ referenced files..."

# Extract file references from .claude/CLAUDE.md and check they exist
for ref in memory/python-environment-usage.md memory/validation-strategy.md memory/make-targets.md \
           context/recent-work.md context/testing-patterns.md context/pytest-markers.md \
           templates/adr-template.md commands/README.md; do
    if [[ -f ".claude/$ref" ]]; then
        log_success ".claude/$ref exists"
    else
        log_warn ".claude/$ref not found"
    fi
done

echo ""

# Check project root files
log_info "Checking project root files..."
for f in ".ai/CORE.md" "AGENTS.md" ".cursorrules" ".github/copilot-instructions.md"; do
    if [[ -f "$f" ]]; then
        log_success "$f exists"
    else
        log_error "$f not found"
    fi
done

echo ""

# Line length check (120 char limit per GitHub recommendation)
log_info "Checking line lengths (120 char limit)..."
for f in ".claude/CLAUDE.md" "AGENTS.md" ".ai/CORE.md"; do
    if [[ -f "$f" ]]; then
        long_lines=$(awk 'length > 120 {count++} END {print count+0}' "$f")
        if [[ "$long_lines" -gt 0 ]]; then
            log_warn "$f has $long_lines lines > 120 chars"
        else
            log_success "$f passes line length check"
        fi
    fi
done

echo ""

# ASCII check
log_info "Checking for non-ASCII characters..."
for f in ".claude/CLAUDE.md" "AGENTS.md" ".ai/CORE.md"; do
    if [[ -f "$f" ]]; then
        # Allow arrows and common unicode but warn about unusual chars
        non_ascii=$(grep -Pn '[^\x00-\x7F]' "$f" 2>/dev/null | head -3 || true)
        if [[ -n "$non_ascii" ]]; then
            log_warn "$f contains non-ASCII characters (acceptable if intentional):"
            echo "$non_ascii" | head -3
        else
            log_success "$f is ASCII-only"
        fi
    fi
done

echo ""

# YAML frontmatter in AGENTS.md
log_info "Checking YAML frontmatter..."
if head -1 AGENTS.md | grep -q '^---$'; then
    log_success "AGENTS.md has YAML frontmatter"
else
    log_error "AGENTS.md missing YAML frontmatter"
fi

echo ""

# === Content Validation ===
echo "=== Content Validation ==="
echo ""

# Check for documentation-first guidance
log_info "Checking for documentation-first guidance..."
for f in "AGENTS.md" ".ai/CORE.md"; do
    if [[ -f "$f" ]]; then
        if grep -qi 'documentation-first\|retrieval-led' "$f"; then
            log_success "$f has documentation-first guidance"
        else
            log_warn "$f missing documentation-first guidance"
        fi
    fi
done

echo ""

# Check for TDD requirement
log_info "Checking for TDD requirement..."
for f in ".claude/CLAUDE.md" "AGENTS.md" ".ai/CORE.md"; do
    if [[ -f "$f" ]]; then
        if grep -qi 'TDD\|test.*first\|tests.*first' "$f"; then
            log_success "$f mentions TDD requirement"
        else
            log_warn "$f missing TDD requirement"
        fi
    fi
done

echo ""

# Check for .venv requirement
log_info "Checking for .venv requirement..."
for f in ".claude/CLAUDE.md" "AGENTS.md" ".ai/CORE.md"; do
    if [[ -f "$f" ]]; then
        if grep -q '\.venv\|uv run' "$f"; then
            log_success "$f mentions .venv requirement"
        else
            log_warn "$f missing .venv requirement"
        fi
    fi
done

echo ""

# Check for boundaries section
log_info "Checking for boundaries (always/ask/never)..."
if grep -qi 'never\|always.*do\|ask.*first\|boundaries' AGENTS.md; then
    log_success "AGENTS.md has boundaries section"
else
    log_warn "AGENTS.md missing boundaries section"
fi

echo ""

# === Cross-Agent Sync ===
echo "=== Cross-Agent Sync ==="
echo ""

# Check .cursorrules references AGENTS.md
log_info "Checking cross-agent references..."
if grep -q 'AGENTS.md\|\.ai/CORE\.md' .cursorrules; then
    log_success ".cursorrules references AGENTS.md or CORE.md"
else
    log_warn ".cursorrules missing AGENTS.md reference"
fi

if grep -q 'AGENTS.md\|\.ai/CORE\.md' .github/copilot-instructions.md; then
    log_success ".github/copilot-instructions.md references AGENTS.md or CORE.md"
else
    log_warn ".github/copilot-instructions.md missing AGENTS.md reference"
fi

echo ""

# === Size Validation ===
echo "=== Size Validation ==="
echo ""

log_info "Checking file sizes..."
for f in ".claude/CLAUDE.md:10240" "AGENTS.md:8192" ".ai/CORE.md:8192"; do
    file="${f%:*}"
    limit="${f#*:}"
    if [[ -f "$file" ]]; then
        size=$(wc -c < "$file")
        if [[ "$size" -le "$limit" ]]; then
            log_success "$file: $size bytes (limit: $limit)"
        else
            log_warn "$file: $size bytes exceeds limit of $limit"
        fi
    fi
done

echo ""

# === Summary ===
echo "========================================="
echo "Verification Summary"
echo "========================================="
echo ""

if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
    log_success "All checks passed!"
    exit 0
elif [[ $ERRORS -eq 0 ]]; then
    log_warn "$WARNINGS warning(s) found (non-blocking)"
    exit 0
else
    log_error "$ERRORS error(s), $WARNINGS warning(s) found"
    exit 1
fi
