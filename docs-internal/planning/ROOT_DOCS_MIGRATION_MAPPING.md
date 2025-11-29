# Root Documentation Migration Mapping

**Date**: 2025-11-20
**Purpose**: Organize root-level .md files into appropriate docs/ subdirectories

---

## Files to KEEP at Root (Essential Top-Level)

These files are standard repository documentation and should remain at root:

1. ✅ **README.md** - Main project README (KEEP)
2. ✅ **CHANGELOG.md** - Version history (KEEP)
3. ✅ **CONTRIBUTING.md** - Contribution guidelines (KEEP)
4. ✅ **CODE_OF_CONDUCT.md** - Community standards (KEEP)
5. ✅ **SECURITY.md** - Security policy (KEEP)

**Total to keep**: 5 files

---

## Files to MIGRATE to docs/ (Public Documentation)

### Category: Development Guides → docs/development/

| Current Location | New Location | Reason |
|-----------------|--------------|---------|
| `DEVELOPER_ONBOARDING.md` | `docs/development/onboarding.mdx` | Developer guide belongs in docs |
| `NAMING-CONVENTIONS.md` | `docs/development/naming-conventions.mdx` | Development standards |
| `MDX_SYNTAX_GUIDE.md` | `docs/contributing/mdx-syntax-guide.mdx` | Documentation authoring guide |
| `AGENTS.md` | `docs/guides/agent-architecture.mdx` | Technical guide |

### Category: Testing & Quality → docs/testing/

| Current Location | New Location | Reason |
|-----------------|--------------|---------|
| `TESTING.md` | `docs/testing/overview.mdx` | Testing strategy overview |
| `HYPOTHESIS_PROFILES.md` | `docs/testing/hypothesis-profiles.mdx` | Testing configuration |

### Category: Deployment → docs/deployment/

| Current Location | New Location | Reason |
|-----------------|--------------|---------|
| `INFRASTRUCTURE-DEPLOYMENT-CHECKLIST.md` | `docs/deployment/deployment-checklist.mdx` | Deployment procedure |
| `SECRETS.md` | `docs/deployment/secrets-management.mdx` | Secrets configuration (check for duplicates) |

### Category: Architecture → docs/architecture/

| Current Location | New Location | Reason |
|-----------------|--------------|---------|
| `REPOSITORY_STRUCTURE.md` | `docs/architecture/repository-structure.mdx` | Architecture documentation |

### Category: Project Management → docs/project/

| Current Location | New Location | Reason |
|-----------------|--------------|---------|
| `ROADMAP.md` | `docs/project/roadmap.mdx` | Project roadmap |
| `MIGRATION.md` | `docs/project/migration-guides.mdx` | Migration guides |

### Category: Quick Reference → docs/

| Current Location | New Location | Reason |
|-----------------|--------------|---------|
| `QUICK_REFERENCE.md` | `docs/quick-reference.mdx` | Quick reference guide |

**Total to migrate**: 12 files

---

## Files to MOVE to docs-internal/ (Internal Documentation)

These are audit reports, planning documents, and internal analysis that should be in docs-internal/:

| Current Location | New Location | Reason |
|-----------------|--------------|---------|
| `ACTION_PLAN_NEXT_STEPS.md` | `docs-internal/planning/action-plan-next-steps.md` | Internal planning |
| `CLAUDE_AGENTS_AUDIT.md` | `docs-internal/audits/claude-agents-audit.md` | Audit report |
| `CODEX_FINDINGS_VALIDATION_REPORT.md` | `docs-internal/audits/codex-findings-validation-report.md` | Audit report |
| `cost-report.md` | `docs-internal/reports/cost-report.md` | Internal report |
| `PHASE3_TYPE_SAFETY_PLAN.md` | `docs-internal/planning/phase3-type-safety-plan.md` | Planning document |
| `PYTEST_XDIST_STATE_POLLUTION_SCAN_REPORT.md` | `docs-internal/reports/pytest-xdist-state-pollution-scan-report.md` | Test analysis |
| `REAL_ISSUES_TO_FIX.md` | `docs-internal/planning/real-issues-to-fix.md` | Internal tracking |
| `SKIPPED_TESTS_DOCUMENTATION.md` | `docs-internal/testing/skipped-tests-documentation.md` | Test documentation |
| `TEST_SUITE_REPORT.md` | `docs-internal/reports/test-suite-report.md` | Test report |
| `DOCUMENTATION_AUDIT_CHECKLIST.md` | `docs-internal/audits/documentation-audit-checklist-2025-11-16.md` | Old audit (archive) |
| `DOCUMENTATION_AUDIT_CHECKLIST_2025-11-20.md` | `DOCUMENTATION_AUDIT_CHECKLIST.md` | Rename to standard name at root |
| `DOCUMENTATION_AUDIT_REMEDIATION_REPORT.md` | `docs-internal/audits/documentation-audit-remediation-report-2025-11-20.md` | Current audit |
| `DOCUMENTATION_IMPROVEMENT_ROADMAP.md` | `docs-internal/planning/documentation-improvement-roadmap-2025-11-20.md` | Planning document |

**Total to move to docs-internal/**: 13 files

---

## Summary

| Action | Count | Files |
|--------|-------|-------|
| **KEEP at root** | 5 | README, CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY |
| **MIGRATE to docs/** | 12 | Development, testing, deployment, architecture, project docs |
| **MOVE to docs-internal/** | 13 | Audits, reports, planning documents |
| **TOTAL** | 30 | All root .md files |

---

## Migration Steps

### Step 1: Create directory structure
```bash
mkdir -p docs/development
mkdir -p docs/testing
mkdir -p docs/deployment
mkdir -p docs/architecture
mkdir -p docs/project
mkdir -p docs/contributing
mkdir -p docs-internal/planning
mkdir -p docs-internal/audits
mkdir -p docs-internal/reports
mkdir -p docs-internal/testing
```

### Step 2: Migrate files to docs/ (with MDX conversion)
For each file in "MIGRATE to docs/" category:
1. Convert .md to .mdx
2. Add frontmatter (title, description, icon, contentType, SEO fields)
3. Update internal links to use Mintlify format
4. Move to new location
5. Update docs.json navigation

### Step 3: Move files to docs-internal/ (no conversion needed)
For each file in "MOVE to docs-internal/" category:
1. Move to new location (keep as .md)
2. Update any references in other documentation

### Step 4: Update references
1. Search for references to moved files
2. Update links in README.md
3. Update links in CONTRIBUTING.md
4. Update links in other documentation

### Step 5: Validate
1. Run frontmatter validator
2. Run broken links check
3. Run all validators
4. Test Mintlify build

---

## Detailed File Analysis

### Files to Migrate to docs/

#### 1. DEVELOPER_ONBOARDING.md → docs/development/onboarding.mdx
**Content**: Developer setup guide, prerequisites, environment setup
**Icon**: `rocket` or `user-plus`
**ContentType**: `how-to`
**Navigation**: Development > Getting Started > Developer Onboarding

#### 2. NAMING-CONVENTIONS.md → docs/development/naming-conventions.mdx
**Content**: Naming standards for files, variables, functions
**Icon**: `tag`
**ContentType**: `reference`
**Navigation**: Development > Standards > Naming Conventions

#### 3. MDX_SYNTAX_GUIDE.md → docs/contributing/mdx-syntax-guide.mdx
**Content**: Guide for writing MDX documentation
**Icon**: `book-open`
**ContentType**: `how-to`
**Navigation**: Contributing > Documentation > MDX Syntax Guide

#### 4. AGENTS.md → docs/guides/agent-architecture.mdx
**Content**: Agent architecture using LangGraph and Pydantic AI
**Icon**: `brain`
**ContentType**: `explanation`
**Navigation**: Guides > Agent Architecture

#### 5. TESTING.md → docs/testing/overview.mdx
**Content**: Testing strategy, TDD principles, test organization
**Icon**: `flask`
**ContentType**: `explanation`
**Navigation**: Testing > Overview

#### 6. HYPOTHESIS_PROFILES.md → docs/testing/hypothesis-profiles.mdx
**Content**: Property-based testing configuration
**Icon**: `settings`
**ContentType**: `reference`
**Navigation**: Testing > Configuration > Hypothesis Profiles

#### 7. INFRASTRUCTURE-DEPLOYMENT-CHECKLIST.md → docs/deployment/deployment-checklist.mdx
**Content**: Deployment checklist and procedures
**Icon**: `checklist`
**ContentType**: `how-to`
**Navigation**: Deployment > Deployment Checklist

#### 8. SECRETS.md → docs/deployment/secrets-management.mdx
**Content**: Secrets management guide
**Icon**: `key`
**ContentType**: `how-to`
**Navigation**: Deployment > Secrets Management
**Note**: Check if this duplicates existing docs/deployment/secrets-management.mdx

#### 9. REPOSITORY_STRUCTURE.md → docs/architecture/repository-structure.mdx
**Content**: Repository organization and structure
**Icon**: `folder-tree`
**ContentType**: `reference`
**Navigation**: Architecture > Repository Structure

#### 10. ROADMAP.md → docs/project/roadmap.mdx
**Content**: Project roadmap and future plans
**Icon**: `map`
**ContentType**: `explanation`
**Navigation**: Project > Roadmap

#### 11. MIGRATION.md → docs/project/migration-guides.mdx
**Content**: Migration guides for version upgrades
**Icon**: `arrow-right`
**ContentType**: `how-to`
**Navigation**: Project > Migration Guides

#### 12. QUICK_REFERENCE.md → docs/quick-reference.mdx
**Content**: Quick reference guide
**Icon**: `zap`
**ContentType**: `reference`
**Navigation**: Quick Reference (top-level)

---

## Navigation Updates Required

After migration, update `docs/docs.json` to add these navigation entries:

### Development Section
```json
{
  "group": "Development",
  "pages": [
    "development/onboarding",
    "development/naming-conventions"
  ]
}
```

### Testing Section
```json
{
  "group": "Testing",
  "pages": [
    "testing/overview",
    "testing/hypothesis-profiles"
  ]
}
```

### Contributing Section
```json
{
  "group": "Contributing",
  "pages": [
    "contributing/mdx-syntax-guide"
  ]
}
```

### Other Updates
- Add "guides/agent-architecture" to Guides section
- Add "deployment/deployment-checklist" to Deployment section
- Check for "deployment/secrets-management" duplicate
- Add "architecture/repository-structure" to Architecture section
- Add "project/roadmap" and "project/migration-guides" to new Project section
- Add "quick-reference" as top-level or in main Documentation section

---

## Risk Assessment

### Low Risk Migrations
- Files with no/few references: HYPOTHESIS_PROFILES, NAMING-CONVENTIONS
- Internal docs moved to docs-internal/: All audit/report files

### Medium Risk Migrations
- Frequently referenced: TESTING.md, DEVELOPER_ONBOARDING.md
- Need careful link updates in README.md and CONTRIBUTING.md

### High Risk Migrations
- SECRETS.md - May duplicate existing documentation
- QUICK_REFERENCE.md - Likely referenced in multiple places

### Mitigation
1. Search for references before moving each file
2. Create redirects or update all references
3. Test all validators after migration
4. Validate Mintlify build succeeds

---

## Next Actions

1. **Create this migration plan** - ✅ DONE
2. **Create directory structure** - Next
3. **Migrate files one category at a time** - After directories created
4. **Update navigation** - After files migrated
5. **Validate all changes** - Final step

---

**Migration Plan Status**: READY
**Estimated Time**: 2-3 hours
**Priority**: P1 (Short-term improvement)
