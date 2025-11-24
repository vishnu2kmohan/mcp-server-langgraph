# Scripts Archive

This directory contains scripts that are no longer actively used but are preserved for historical reference and potential future use.

**Last Updated**: 2025-11-24
**Total Archived Scripts**: 54

---

## Directory Structure

### `completed/` (34 scripts)

**Purpose**: One-time fix and migration scripts that have completed their purpose.

**Categories**:
- **Code Migrations**: Scripts that added missing features, decorators, or patterns
- **Documentation Fixes**: Scripts that fixed MDX syntax, frontmatter, or styling
- **Test Improvements**: Scripts that added memory safety, xdist markers, or timeouts
- **Syntax Fixes**: Scripts that fixed YAML indentation, import issues, or deprecations

**Naming Patterns**:
- `add_*.py` - Scripts that added missing features (e.g., `add_gc_import.py`, `add_xdist_group_markers.py`)
- `fix_*.py` - Scripts that fixed specific issues (e.g., `fix_yaml_indentation.py`, `fix_memory_safety.py`)

**When to Archive Here**:
- Script was used for a one-time bulk code modification
- The changes have been committed and verified
- The script is no longer needed for regular operations
- Keeping for historical reference and potential pattern reuse

**Examples**:
- `add_memory_safety_to_tests.py` - Added memory safety patterns to all test files
- `fix_mdx_angle_brackets.py` - Fixed MDX angle bracket escaping issues
- `add_xdist_group_markers.py` - Added pytest-xdist group markers to test classes

---

### `unused/` (20 scripts)

**Purpose**: Scripts that were created but never integrated into active workflows or became obsolete.

**Categories**:
- **Deprecated Validators**: Replaced by Mintlify or newer validators
- **Experimental Tools**: Proof-of-concept scripts that didn't make it to production
- **Superseded Utilities**: Replaced by better implementations

**When to Archive Here**:
- Script was never integrated into hooks, Makefile, or workflows
- Functionality has been superseded by newer tools
- No longer relevant to current development practices

---

## Archival Process

### When to Archive a Script

Archive a script when it meets ANY of these criteria:

1. **Completed Purpose** (→ `completed/`)
   - One-time migration or bulk fix completed
   - Changes committed and stable
   - No ongoing need for the script

2. **Replaced by Better Tool** (→ `unused/`)
   - Functionality now handled by Mintlify, pre-commit, or other tools
   - Newer implementation exists with better features

3. **Never Actively Used** (→ `unused/`)
   - Created but never integrated into development workflow
   - Not referenced in hooks, Makefile, or GitHub Actions

### How to Archive

```bash
# For completed one-time scripts
git mv scripts/path/to/script.py scripts/archive/completed/

# For unused/deprecated scripts
git mv scripts/path/to/script.py scripts/archive/unused/

# Update inventory
uv run python scripts/generate_script_inventory.py

# Commit with explanation
git commit -m "chore(scripts): archive completed migration script

Script completed its purpose: [explanation]
Archiving for historical reference only.
"
```

### Do NOT Archive

**Keep these types of scripts ACTIVE**:
- ✅ Used in `.pre-commit-config.yaml` hooks
- ✅ Used in `Makefile` targets
- ✅ Used in `.github/workflows/*.yaml` workflows
- ✅ Development utilities still useful (profiling, analysis)
- ✅ Infrastructure setup scripts (even if infrequent)

---

## Archival History

### 2025-11-17 (Initial Cleanup)
- **Archived**: 31 one-time fix scripts to `completed/`
- **Deleted**: 7 deprecated validators
- **Moved**: 4 development tools to `scripts/dev/`
- **Total Impact**: 42 scripts reorganized

### 2025-11-24 (Phase 5.2)
- **Archived**: 2 additional documentation migration scripts
  - `add_missing_frontmatter.py`
  - `add_seo_fields.py`
- **Current State**: 54 archived scripts total

---

## Maintenance

**Audit Frequency**: Quarterly (every 3 months)
**Next Audit**: 2026-02-24
**Process**:
1. Run `uv run python scripts/generate_script_inventory.py`
2. Review scripts marked as "unused" in inventory
3. Archive completed one-time scripts to `archive/completed/`
4. Archive obsolete utilities to `archive/unused/`
5. Update this README

---

## Recovery

To restore an archived script:

```bash
# Move back to active location
git mv scripts/archive/completed/script.py scripts/path/to/script.py

# Update inventory
uv run python scripts/generate_script_inventory.py

# Integrate into workflow (choose one or more)
# - Add to .pre-commit-config.yaml
# - Add to Makefile
# - Add to .github/workflows/*.yaml

# Commit
git commit -m "chore(scripts): restore script.py for active use"
```

---

## Statistics

| Metric | Count |
|--------|-------|
| **Total Active Scripts** | 138 |
| **Total Archived Scripts** | 54 |
| **Completion Percentage** | 39% of one-time scripts archived |

**Archive Breakdown**:
- Completed migrations: 34 scripts (63%)
- Unused/deprecated: 20 scripts (37%)

---

**See Also**:
- [scripts/SCRIPT_INVENTORY.md](../SCRIPT_INVENTORY.md) - Complete script categorization
- [scripts/README.md](../README.md) - Active scripts documentation
- [docs-internal/CODEX_FINDINGS_REMEDIATION_REPORT.md](../../docs-internal/CODEX_FINDINGS_REMEDIATION_REPORT.md) - Remediation context

---

**Generated**: 2025-11-24
**Maintained By**: Infrastructure Team
