#!/usr/bin/env bash
# Verify all AI tool configs reference .ai/CORE.md and aren't stale
#
# Usage:
#   bash .ai/check-sync.sh          # Check all configs
#   bash .ai/check-sync.sh --fix    # Regenerate stale files

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ERRORS=0

# Verify all tool configs reference CORE.md
for f in .claude/CLAUDE.md .cursorrules .github/copilot-instructions.md .gemini/GEMINI.md .codex/instructions.md; do
  filepath="$PROJECT_ROOT/$f"
  if [[ -f "$filepath" ]]; then
    if ! grep -Eq '\.ai/CORE\.md|CORE\.md' "$filepath"; then
      echo "WARNING: $f does not reference .ai/CORE.md" >&2
      ((ERRORS++))
    fi
  else
    echo "INFO: $f not found (skipping)" >&2
  fi
done

# Verify AGENTS.md is current (if build script exists)
if [[ -x "$SCRIPT_DIR/build-agents.sh" ]]; then
  if ! bash "$SCRIPT_DIR/build-agents.sh" --check 2>/dev/null; then
    echo "WARNING: AGENTS.md is stale" >&2
    if [[ "${1:-}" == "--fix" ]]; then
      bash "$SCRIPT_DIR/build-agents.sh"
      echo "FIXED: AGENTS.md regenerated"
    else
      ((ERRORS++))
    fi
  fi
fi

if [[ $ERRORS -gt 0 ]]; then
  echo "FAIL: $ERRORS issue(s) found" >&2
  exit 1
fi

echo "OK: All AI configs are in sync"
exit 0
