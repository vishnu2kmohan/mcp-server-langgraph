# Archived Scripts

These scripts have been deprecated and superseded by the unified `design-system.py` tool.

## Replacement

Use the unified tool instead:

```bash
# Audit all design system violations
python scripts/design-system.py audit

# Fix violations by category
python scripts/design-system.py fix --category=color
python scripts/design-system.py fix --category=component
python scripts/design-system.py fix --all

# Quick check for pre-commit
python scripts/design-system.py check

# Generate compliance report
python scripts/design-system.py report
```

## Why These Were Deprecated

The previous approach had 23 separate fix scripts, each handling a narrow concern:
- 12 color migration scripts (one per page/component area)
- 7 style/accessibility scripts
- 4 utility scripts (kept, not archived)

This fragmented approach made it difficult to:
1. Maintain consistent patterns across scripts
2. Run comprehensive audits
3. Track which fixes had been applied
4. Add new patterns

## Archived Scripts

| Script | Replaced By |
|--------|-------------|
| `fix-design-system-colors.py` | `design-system.py fix --category=color` |
| `fix-hardcoded-colors.py` | `design-system.py fix --category=color` |
| `fix-canvas-text-colors.py` | `design-system.py fix --category=color` |
| `fix-skills-page-colors.py` | `design-system.py fix --category=color` |
| `fix-projects-page-colors.py` | `design-system.py fix --category=color` |
| `fix-workflows-page-colors.py` | `design-system.py fix --category=color` |
| `fix-vectors-page-colors.py` | `design-system.py fix --category=color` |
| `fix-observability-page-colors.py` | `design-system.py fix --category=color` |
| `fix-artifacts-page-colors.py` | `design-system.py fix --category=color` |
| `fix-settings-page-colors.py` | `design-system.py fix --category=color` |
| `fix-cost-page-colors.py` | `design-system.py fix --category=color` |
| `fix-help-page-colors.py` | `design-system.py fix --category=color` |
| `fix-design-system-violations.py` | `design-system.py fix --all` |
| `fix-admin-style-compliance.py` | `design-system.py fix --all` |
| `fix-progress-bars.py` | `design-system.py fix --category=component` |
| `fix-button-variants.py` | `design-system.py fix --category=component` |
| `fix-all-button-variants.py` | `design-system.py fix --category=component` |
| `fix-accessibility-attrs.py` | `design-system.py audit --category=aria` |
| `fix-duplicate-classnames.py` | `design-system.py check` |

## Scripts NOT Archived (Still Active)

These utility scripts remain in the parent directory:
- `fix-broken-empty-strings.py` - Edge case fix for malformed strings
- `fix-msw-snake-case.py` - MSW handler migration utility
- `fix-test-fixtures.py` - Test fixture migration utility
- `fix-react-refresh-warnings.py` - React refresh dev tooling fix

## Date Archived

2025-01-17

## References

- See `docs-internal/frontend/STYLE.md` for the comprehensive style guide
- See `scripts/design-system.py --help` for full usage documentation
- See `scripts/lib/audit-patterns.ts` for pattern definitions
