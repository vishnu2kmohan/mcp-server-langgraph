# Deprecated Documentation Validators (Archived 2025-11-15)

This directory contains Python validators that were deprecated as part of the documentation validation simplification project.

## Migration Summary

**Date**: 2025-11-15
**Reason**: Consolidation to Mintlify CLI as PRIMARY validator for Mintlify documentation (docs/)
**Impact**: 69% reduction in validators (13 → 4), 91-93% faster validation

## Deprecated Validators

### 1. link_validator.py.deprecated
**Original Purpose**: Validate internal links in MDX files
**Functionality**:
- Checked broken internal links (relative paths)
- Detected malformed URLs
- Validated anchor targets exist
- Skipped external link validation (expensive)

**Replaced By**: `mintlify broken-links` (CI) + `check-doc-links` (pre-push)
- Mintlify CLI provides superior link validation including anchor links
- check-doc-links handles ADR cross-references and GitHub links

**Tests**: `tests/unit/documentation/test_link_validator.py` (preserved for reference)

---

### 2. navigation_validator.py.deprecated
**Original Purpose**: Validate documentation navigation consistency
**Functionality**:
- All files referenced in docs.json exist
- All production MDX files are in navigation (no orphans)
- No duplicate page references
- Navigation JSON structure is valid

**Replaced By**: `mintlify broken-links` (CI)
- Mintlify CLI natively validates docs.json navigation structure
- Detects orphaned pages automatically
- Validates all navigation references

**Tests**: `tests/unit/documentation/test_navigation_validator.py` (preserved for reference)

---

### 3. image_validator.py.deprecated
**Original Purpose**: Validate image references in documentation
**Functionality**:
- All local images exist
- Relative paths resolve correctly
- Supported formats (png, jpg, jpeg, svg, gif, webp)
- External images (http/https) ignored

**Replaced By**: `mintlify broken-links` (CI)
- Mintlify CLI validates all image references as part of comprehensive documentation check
- Detects missing images and broken image paths

**Tests**: `tests/unit/documentation/test_image_validator.py` (10 tests ✅, preserved for reference)

---

### 4. frontmatter_validator.py.deprecated
**Original Purpose**: Validate MDX frontmatter (title, description)
**Functionality**:
- Required fields: title, description
- Valid YAML syntax
- Non-empty field values
- Excludes template files

**Replaced By**: `mintlify broken-links` (CI) + `validate-mintlify-docs` (pre-push)
- Mintlify CLI validates frontmatter completeness
- validate-mintlify-docs provides extended frontmatter validation (icon, quote style, Mermaid diagrams)

**Tests**: `tests/unit/documentation/test_frontmatter_validator.py` (preserved for reference)

---

### 5. check_internal_links.py.deprecated
**Original Purpose**: Internal link validator (duplicate of link_validator.py)
**Functionality**: Same as link_validator.py

**Replaced By**: `mintlify broken-links` (CI) + `check-doc-links` (pre-push)

---

## What Validators Were Retained?

### Pre-push Validators (Still Active)
1. **validate-mintlify-docs** (pre-push) - Extended Mintlify validation
   - Frontmatter quote style
   - Icon consistency
   - Mermaid diagram syntax
   - Filename conventions

2. **validate-docs-navigation** (pre-push) - Orphaned file detection
   - Kept for local pre-push validation
   - Complements Mintlify CLI

3. **check-doc-links** (pre-push) - ADR cross-references
   - Validates ADR cross-references
   - Checks GitHub links
   - Focuses on documentation outside docs/

4. **validate-documentation-integrity** (pre-push, pytest) - ADR sync, Mermaid
   - ADR synchronization between /adr and /docs/architecture
   - Mermaid diagram structure validation
   - Monitoring README completeness

5. **validate-documentation-structure** (pre-push, pytest) - Comprehensive structure
   - Orphaned files
   - ADR numbering
   - TODO/FIXME markers
   - Badges
   - Links
   - Version consistency

### Pre-commit Validators (Still Active)
1. **fix-mdx-syntax** (pre-commit) - Auto-fix MDX syntax errors
2. **validate-mdx-extensions** (pre-commit) - Enforce .mdx extension

### Manual Validators (Still Active)
1. **mintlify-broken-links-check** (manual/CI) - PRIMARY validator
2. **audit-todo-fixme-markers** (manual) - Informational only

### CI-Only Validators (New Primary)
1. **Mintlify CLI broken-links** - Now runs automatically in CI as PRIMARY validator

---

## Performance Improvements

| Metric | Before (Python Validators) | After (Mintlify CLI) | Improvement |
|--------|---------------------------|----------------------|-------------|
| **Validation Time** | 105-155 seconds | 8-12 seconds | **91-93% faster** |
| **Validator Count** | 13 validators | 4 validators | **69% reduction** |
| **Lines of Code** | ~3,500 lines | ~800 lines | **77% reduction** |
| **Maintenance Burden** | High (13 scripts) | Low (4 scripts) | **69% less work** |

---

## Migration Timeline

**Week 1**: Consolidate GitHub Actions workflows
- Merged docs-validation.yml + docs-validation.yaml
- Made Mintlify primary validator
- Kept Python validators running in parallel (validation phase)

**Week 2**: Verify coverage
- Compared Mintlify vs Python validator results on same PRs
- Documented edge cases
- Ensured no regression

**Week 3**: Remove duplicate hooks
- Removed validate-documentation-links
- Removed validate-mdx-frontmatter
- Removed validate-documentation-images
- Removed validate-documentation-quality
- Updated documentation

**Week 4**: Archive validators
- Moved to scripts/validators/archive/
- Renamed with .deprecated suffix
- Created this README

---

## How to Use Deprecated Validators (If Needed)

If you need to run these validators for any reason (e.g., debugging, comparison):

```bash
# Restore validator temporarily
cd scripts/validators/archive
cp link_validator.py.deprecated ../link_validator.py

# Run validator
python ../link_validator.py --docs-dir docs

# Remove when done
rm ../link_validator.py
```

**Note**: These validators are NO LONGER maintained. Use Mintlify CLI for comprehensive validation.

---

## References

- **Migration Documentation**: `docs-internal/DOCS_VALIDATION_SIMPLIFICATION.md`
- **CI Workflow**: `.github/workflows/docs-validation.yaml`
- **Pre-commit Config**: `.pre-commit-config.yaml`
- **Makefile Targets**: `Makefile` (docs-validate, docs-validate-mintlify)
- **Tests**: `tests/unit/documentation/` (preserved for reference)

---

## Questions?

See the migration documentation or contact the project maintainers.

**Archived**: 2025-11-15
**Reason**: Superseded by Mintlify CLI (PRIMARY validator)
**Status**: Deprecated, no longer maintained
