# Documentation Testing Strategy

## Overview

This document explains the comprehensive TDD-based documentation testing strategy that ensures documentation quality, prevents regressions, and maintains consistency across all 373+ documentation files.

**Last Updated**: 2025-11-07
**Status**: Production
**Test Coverage**: 23 automated tests (22 passed, 1 skipped)

---

## Testing Philosophy

### Test-Driven Documentation (TDD)

We follow Test-Driven Development principles for documentation:

1. **Write Tests First** - Define what "good documentation" means in code
2. **Fail Initially** - Tests fail when documentation has issues
3. **Fix & Pass** - Fix documentation until all tests pass
4. **Prevent Regression** - Tests run automatically in CI/CD to prevent future issues

### Benefits

- **Automated Quality Assurance**: No manual review needed for syntax/structure
- **Regression Prevention**: Once fixed, issues can never reoccur
- **Consistent Standards**: All documentation follows the same rules
- **Fast Feedback**: Developers know immediately if docs are broken
- **Documentation as Code**: Documentation quality enforced like code quality

---

## Test Suites

We maintain **two complementary test suites** that together provide comprehensive coverage:

### 1. Meta Documentation Validation (`tests/meta/test_documentation_validation.py`)

**Purpose**: Prevents MDX parsing errors and validates Mintlify-specific requirements

**Tests (10 total)**:

#### TestMDXParsing
- `test_no_unescaped_less_than_digits()` - Prevents `<100ms` causing MDX parse errors
- `test_no_unescaped_email_addresses()` - Prevents `<email@example.com>` issues

#### TestMintlifyNavigation
- `test_docs_json_valid()` - Validates docs.json JSON syntax
- `test_all_navigation_files_exist()` - All navigation links point to real files
- `test_no_orphaned_documentation_files()` - No MDX files exist without navigation entries

#### TestADRConsistency
- `test_adr_numbering_sequential()` - ADR numbers are sequential (no gaps)
- `test_adr_sync_between_directories()` - ADRs synced between `adr/` and `docs/architecture/`

#### TestFrontmatter
- `test_mdx_files_have_frontmatter()` - All MDX files have YAML frontmatter
- `test_frontmatter_required_fields()` - Required fields present (title, description, icon, etc.)

#### TestLinkIntegrity
- `test_no_broken_internal_links_to_docs()` - Internal links resolve correctly

**Triggered by**: Changes to `.md`, `.mdx`, `.json` files

---

### 2. Documentation Integrity Tests (`tests/test_documentation_integrity.py`)

**Purpose**: Ensures documentation completeness, accuracy, and proper structure

**Tests (13 total, 1 skipped)**:

#### TestADRSynchronization
- `test_adr_count_matches()` - Same number of ADRs in `adr/` and `docs/architecture/`
- `test_all_source_adrs_have_mdx_versions()` - Every `.md` ADR has a `.mdx` version
- `test_no_orphaned_adr_mdx_files()` - No `.mdx` ADRs without `.md` source

#### TestDocsJsonIntegrity
- `test_docs_json_is_valid_json()` - docs.json parses correctly
- `test_all_navigation_files_exist()` - All navigation references resolve

#### TestMDXSyntax
- `test_no_html_comments_in_mdx_files()` - HTML comments not allowed (use JSX `{/* */}`)
- `test_jsx_comments_are_properly_closed()` - All `{/*` have matching `*/}`
- `test_no_unescaped_comparison_operators()` - Comparison operators escaped (skipped - informational)

#### TestArchitectureOverview
- `test_architecture_overview_adr_count_is_current()` - Overview shows correct ADR count

#### TestMermaidDiagrams
- `test_all_mermaid_diagrams_have_closing_markers()` - All ` ```mermaid ` blocks properly closed

#### TestDocumentationCompleteness
- `test_no_suspiciously_small_documentation_files()` - No stub files (<15 lines)
- `test_monitoring_subdirectories_have_readmes()` - Monitoring dirs have READMEs
- `test_monitoring_readmes_are_comprehensive()` - READMEs are >50 lines

**Triggered by**: Changes to `.md`, `.mdx`, `.json` files, or `monitoring/*/README.md`

---

## Pre-Commit Integration

### Hooks

Both test suites run automatically via pre-commit hooks:

```yaml
# Hook 1: Meta Validation
- id: validate-documentation-quality
  name: Validate Documentation Quality (MDX Parsing, Links, ADRs)
  entry: python -m pytest tests/meta/test_documentation_validation.py -v --tb=short
  files: \.(md|mdx|json)$

# Hook 2: Integrity Validation
- id: validate-documentation-integrity
  name: Validate Documentation Integrity (ADRs, Monitoring, Mermaid)
  entry: python -m pytest tests/test_documentation_integrity.py -v --tb=short
  files: \.(md|mdx|json)$|^monitoring/.*README\.md$
```

### When Hooks Run

- **Pre-commit**: When committing documentation changes
- **Pre-push**: Before pushing to remote (via CI/CD regression tests)
- **CI/CD Pipeline**: On every pull request

### Bypass (Emergency Only)

```bash
# Skip documentation hooks (use sparingly!)
SKIP=validate-documentation-quality,validate-documentation-integrity git commit -m "..."
```

---

## Coverage Matrix

| Area | Meta Tests | Integrity Tests | Total |
|------|-----------|----------------|-------|
| MDX Syntax | 2 | 3 | 5 |
| Navigation | 2 | 1 | 3 |
| ADR Consistency | 2 | 4 | 6 |
| Frontmatter | 2 | 0 | 2 |
| Link Integrity | 1 | 0 | 1 |
| Mermaid Diagrams | 0 | 1 | 1 |
| Completeness | 0 | 3 | 3 |
| Architecture Accuracy | 0 | 1 | 1 |
| **Total** | **10** | **13** | **23** |

**Overall Coverage**: 100% of critical documentation aspects

---

## Mintlify CLI Validation

In addition to automated tests, we use Mintlify's CLI tools for manual validation:

### Broken Links Check

```bash
cd docs && mintlify broken-links
```

**Expected Output**:
- 0 real broken links
- 10 placeholder links in template files (acceptable)

### Accessibility Check

```bash
mintlify a11y
```

**Current Status**:
- ✅ WCAG AA compliant (6.07:1 contrast ratio)
- ✅ 235 MDX files validated
- ✅ All images have alt attributes

### Local Preview

```bash
cd docs && mintlify dev
```

Runs local development server to preview documentation changes.

---

## Test Execution

### Run All Documentation Tests

```bash
# Both test suites
uv run pytest tests/meta/test_documentation_validation.py tests/test_documentation_integrity.py -v

# Expected: 22 passed, 1 skipped
```

### Run Individual Suites

```bash
# Meta validation only
uv run pytest tests/meta/test_documentation_validation.py -v

# Integrity tests only
uv run pytest tests/test_documentation_integrity.py -v
```

### Run Specific Test

```bash
# Test ADR synchronization
uv run pytest tests/test_documentation_integrity.py::TestADRSynchronization -v

# Test MDX parsing
uv run pytest tests/meta/test_documentation_validation.py::TestMDXParsing -v
```

### Fast Failure Mode

```bash
# Stop on first failure
uv run pytest tests/meta tests/test_documentation_integrity.py -x
```

---

## Common Issues & Fixes

### Issue: HTML Comments in MDX

**Error**: `HTML comments not allowed in MDX`

**Fix**: Replace HTML comments with JSX comments:

```mdx
<!-- Bad: HTML comment -->
{/* Good: JSX comment */}
```

### Issue: Unescaped Comparison Operators

**Error**: `Unescaped '<100' - wrap in backticks`

**Fix**: Wrap in backticks or use HTML entities:

```mdx
Bad: Response time <100ms
Good: Response time `<100ms`
Good: Response time &lt;100ms
```

### Issue: Missing ADR in Mintlify

**Error**: `ADRs in adr/ missing from docs/architecture/: ['adr-0050-...']`

**Fix**:
1. Convert `.md` to `.mdx` with proper frontmatter
2. Add to `docs/architecture/`
3. Update `docs/docs.json` navigation

### Issue: Outdated Architecture Overview

**Error**: `Architecture overview shows 43 ADRs but there are actually 49`

**Fix**: Update `docs/architecture/overview.mdx` ADR count

### Issue: Unclosed Mermaid Diagram

**Error**: `Unclosed Mermaid diagrams: file.mdx (open: 2, closed: 1)`

**Fix**: Ensure all ` ```mermaid ` blocks have closing ` ``` `

### Issue: Stub Documentation File

**Error**: `Suspiciously small MDX files: guide.mdx (8 lines)`

**Fix**: Either expand the guide or remove the stub file

---

## Maintenance

### Adding New Tests

When adding documentation quality checks:

1. **Choose the right suite**:
   - Mintlify-specific → `tests/meta/test_documentation_validation.py`
   - Content/structure → `tests/test_documentation_integrity.py`

2. **Follow TDD**:
   ```python
   # 1. RED: Write failing test
   def test_new_documentation_requirement(self):
       assert False, "New requirement not met"

   # 2. GREEN: Fix documentation
   # (make changes to docs)

   # 3. REFACTOR: Improve test
   def test_new_documentation_requirement(self):
       # Comprehensive check
       assert requirement_met()
   ```

3. **Update this document** with new test descriptions

### Updating Test Thresholds

Some tests have configurable thresholds:

```python
# Comprehensive README minimum lines
MIN_README_LINES = 50  # Increase if READMEs should be longer

# Small file threshold
MIN_FILE_LINES = 15  # Adjust based on acceptable stub size
```

### Reviewing Test Results

Monitor test pass rates:

```bash
# Generate test report
uv run pytest tests/meta tests/test_documentation_integrity.py \
  --junitxml=test-results/documentation-tests.xml

# View coverage
uv run pytest tests/meta tests/test_documentation_integrity.py \
  --cov=docs --cov-report=html
```

---

## Metrics & KPIs

### Documentation Health Metrics

- **Total Documentation Files**: 373
- **Test Coverage**: 23 automated tests
- **Pre-commit Hooks**: 2 documentation validation hooks
- **Mintlify MDX Files**: 235
- **ADRs**: 49 (100% synced)
- **Mermaid Diagrams**: 49 (all validated)
- **Broken Links**: 0

### Quality Gates

All commits must pass:
- ✅ 22/23 documentation tests (1 skipped is acceptable)
- ✅ 0 real broken links
- ✅ WCAG AA accessibility compliance
- ✅ All navigation links resolve
- ✅ All Mermaid diagrams properly closed
- ✅ No HTML comments in MDX files

---

## Future Enhancements

### Planned Improvements

1. **External Link Validation**
   - Periodically check external URLs (GitHub, docs sites)
   - Report broken external links (non-blocking)

2. **Content Freshness**
   - Flag documentation not updated in >6 months
   - Suggest review of stale content

3. **Screenshot Validation**
   - Ensure screenshots are up-to-date
   - Validate referenced images exist

4. **Spell Checking**
   - Integrate spell checker for technical terms
   - Custom dictionary for project-specific terms

5. **Readability Metrics**
   - Calculate Flesch reading ease score
   - Suggest simplification for complex sections

---

## References

- **Test Files**:
  - `tests/meta/test_documentation_validation.py`
  - `tests/test_documentation_integrity.py`
- **Pre-commit Config**: `.pre-commit-config.yaml`
- **Mintlify Docs**: `docs/`
- **Source ADRs**: `adr/`
- **Audit Reports**: `docs-internal/audits/`

---

## Changelog

### 2025-11-07
- Added `test_documentation_integrity.py` suite (13 tests)
- Added monitoring README validation tests
- Added Mermaid diagram validation
- Updated pre-commit hooks to include both test suites
- Created this documentation testing strategy document

### 2025-11-06
- Initial `test_documentation_validation.py` suite (10 tests)
- Added MDX parsing validation
- Added frontmatter validation
- Added ADR consistency checks

---

## Contact

For questions about documentation testing:
- See: `docs-internal/audits/` for audit history
- Review: Pre-commit hook output for specific failures
- Check: Test file comments for detailed explanations
