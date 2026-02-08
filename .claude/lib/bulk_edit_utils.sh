#!/bin/bash
# Bulk edit utilities - cross-platform (perl, not sed)
# Uses null-delimited paths and escaped patterns for safety
# Usage: source .claude/lib/bulk_edit_utils.sh
set -euo pipefail

# Validate pattern doesn't contain dangerous characters
_validate_pattern() {
    local pattern="$1"
    # Reject empty patterns — rg matches every line, Perl replaces everything
    if [[ -z "$pattern" ]]; then
        echo "ERROR: Pattern must be non-empty" >&2
        return 1
    fi
    # Reject patterns with shell metacharacters that could cause injection
    if [[ "$pattern" =~ [\`\$\(\)\{\}\;\&\|] ]]; then
        echo "ERROR: Pattern contains unsafe characters: $pattern" >&2
        return 1
    fi
}

# Escape string for use in Perl replacement (handles backrefs and special chars)
# Uses perl instead of sed for cross-platform compatibility
_escape_replacement() {
    local str="$1"
    # Escape backslashes, dollar signs, and at signs for Perl replacement string
    printf '%s' "$str" | perl -pe 's/\\/\\\\/g; s/\$/\\\$/g; s/\@/\\@/g'
}

# Rename a symbol across the codebase
# Args:
#   $1 - old symbol name
#   $2 - new symbol name
#   $3 - file type (default: py)
rename_symbol() {
    local old="$1" new="$2" type="${3:-py}"

    # Validate inputs
    _validate_pattern "$old" || return 1
    _validate_pattern "$new" || return 1

    # Check for required tools
    command -v rg >/dev/null 2>&1 || { echo "ERROR: rg (ripgrep) not found" >&2; return 1; }
    command -v perl >/dev/null 2>&1 || { echo "ERROR: perl not found" >&2; return 1; }

    # Escape replacement for safe Perl substitution
    local escaped_new
    escaped_new=$(_escape_replacement "$new")

    # Use -e to prevent option injection if pattern starts with '-'
    # Use null-delimited output and \Q..\E for literal matching
    # Guard: skip if no files match (prevents xargs hanging on BSD with no input)
    rg -q -e "$old" --type "$type" || return 0
    rg -l0 -e "$old" --type "$type" | xargs -0 perl -pi -e "s/\\Q${old}\\E/${escaped_new}/g"
}

# Update import statements across the codebase
# Args:
#   $1 - old module path
#   $2 - new module path
update_imports() {
    local old_module="$1" new_module="$2"

    # Validate inputs
    _validate_pattern "$old_module" || return 1
    _validate_pattern "$new_module" || return 1

    # Check for required tools
    command -v rg >/dev/null 2>&1 || { echo "ERROR: rg (ripgrep) not found" >&2; return 1; }
    command -v perl >/dev/null 2>&1 || { echo "ERROR: perl not found" >&2; return 1; }

    # Escape replacement for safe Perl substitution
    local escaped_new
    escaped_new=$(_escape_replacement "$new_module")

    # Use -e to prevent option injection
    # Use null-delimited output and \Q..\E for literal matching
    # Guard: skip if no files match (prevents xargs hanging on BSD with no input)
    rg -q -e "from $old_module" --type py || return 0
    rg -l0 -e "from $old_module" --type py | xargs -0 perl -pi -e "s/from \\Q${old_module}\\E/from ${escaped_new}/g"
}

# Replace a pattern across files of a specific type
# Args:
#   $1 - pattern to find
#   $2 - replacement string
#   $3 - file type (default: py)
bulk_replace() {
    local pattern="$1" replacement="$2" type="${3:-py}"

    # Validate inputs
    _validate_pattern "$pattern" || return 1
    _validate_pattern "$replacement" || return 1

    # Check for required tools
    command -v rg >/dev/null 2>&1 || { echo "ERROR: rg (ripgrep) not found" >&2; return 1; }
    command -v perl >/dev/null 2>&1 || { echo "ERROR: perl not found" >&2; return 1; }

    local escaped_replacement
    escaped_replacement=$(_escape_replacement "$replacement")

    # Guard: skip if no files match (prevents xargs hanging on BSD with no input)
    rg -q -e "$pattern" --type "$type" || return 0
    rg -l0 -e "$pattern" --type "$type" | xargs -0 perl -pi -e "s/\\Q${pattern}\\E/${escaped_replacement}/g"
}
