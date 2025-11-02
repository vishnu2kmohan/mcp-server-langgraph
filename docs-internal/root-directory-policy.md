# Root Directory Policy

**Purpose:** Maintain a clean repository root that doesn't interfere with Mintlify documentation

## Root Directory Contents

### ✅ ALLOWED at Root

**Essential Project Files:**
- `README.md` - Main project README
- `CHANGELOG.md` - Version history
- `SECURITY.md` - Security policy
- `LICENSE` - Project license
- `CONTRIBUTING.md` - Contribution guidelines
- `CODE_OF_CONDUCT.md` - Code of conduct
- `REPOSITORY_STRUCTURE.md` - Structure documentation

**Configuration Files:**
- `pyproject.toml` - Python project config
- `.mintlifyignore` - Mintlify exclusions
- `.gitignore` - Git exclusions
- `.pre-commit-config.yaml` - Pre-commit hooks
- `requirements*.txt` - Python dependencies
- `Makefile` - Build automation

### ❌ NOT ALLOWED at Root

**Documentation Files:**
- ❌ Implementation guides → `docs-internal/`
- ❌ Technical specs → `docs-internal/` or `reference/`
- ❌ Migration guides → `docs-internal/`
- ❌ Runbooks → `runbooks/`
- ❌ Reports → `reports/`
- ❌ ADRs → `adr/`
- ❌ HTML files → `docs-internal/` or remove

**Build Artifacts:**
- ❌ `*.pyc`, `*.pyo` → Ignored by `.gitignore`
- ❌ `dist/`, `build/` → Ignored by `.gitignore`
- ❌ `*.egg-info/` → Ignored by `.gitignore`

## Mintlify Interference Prevention

### Problem
Files and directories at the root can interfere with Mintlify's document scanner, causing:
- Performance issues
- Incorrect indexing
- Confusion about what's documentation
- Scanning of irrelevant content (.venv, build artifacts)

### Solution
Use `.mintlifyignore` to exclude all non-documentation content:

```gitignore
# Python environment
.venv/
venv/

# Internal documentation
docs-internal/

# Reports and internal content
reports/
adr/
runbooks/
archive/

# Source and tests
src/
tests/

# Configuration
config/
deployments/
...
```

## Enforcement

### Pre-Commit Check (Recommended)
Add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: check-root-docs
      name: Check root directory cleanliness
      entry: ./hooks/check-root-docs.sh
      language: system
      pass_filenames: false
```

### CI/CD Check
Add to GitHub Actions workflow:

```yaml
- name: Verify root directory
  run: |
    # Count .md files at root (excluding allowed ones)
    count=$(ls -1 *.md 2>/dev/null | grep -vE "^(README|CHANGELOG|SECURITY|CONTRIBUTING|CODE_OF_CONDUCT|REPOSITORY_STRUCTURE)\.md$" | wc -l)
    if [ $count -gt 0 ]; then
      echo "ERROR: Unexpected .md files at root"
      ls -1 *.md | grep -vE "^(README|CHANGELOG|SECURITY|CONTRIBUTING|CODE_OF_CONDUCT|REPOSITORY_STRUCTURE)\.md$"
      exit 1
    fi
```

## When Moving Files

### Decision Tree

```
Is the file documentation?
├─ YES
│  ├─ User-facing (API docs, guides, tutorials)?
│  │  └─ → docs/ (as .mdx Mintlify format)
│  │
│  ├─ Internal implementation details?
│  │  └─ → docs-internal/
│  │
│  ├─ Operational procedures?
│  │  └─ → runbooks/
│  │
│  ├─ Architecture decision?
│  │  └─ → adr/
│  │
│  └─ Project report or metric?
│     └─ → reports/
│
└─ NO
   ├─ Configuration?
   │  └─ → config/ or appropriate config location
   │
   ├─ Build artifact?
   │  └─ → Add to .gitignore, don't commit
   │
   └─ Essential project file?
      └─ → OK at root (see allowed list above)
```

## Periodic Cleanup

### Monthly
- Review root directory for new files
- Move misplaced files to correct locations
- Update .mintlifyignore if needed

### Quarterly
- Archive old reports to reports/archive/
- Review docs-internal/ for outdated content
- Update REPOSITORY_STRUCTURE.md

## Common Violations and Fixes

### ❌ Implementation Guide at Root
```bash
# Wrong
./PYDANTIC_MIGRATION_COMPLETE.md

# Fix
mv PYDANTIC_MIGRATION_COMPLETE.md docs-internal/
```

### ❌ Report at Root
```bash
# Wrong
./TEST_COVERAGE_REPORT.md

# Fix
mv TEST_COVERAGE_REPORT.md reports/
```

### ❌ HTML Files at Root
```bash
# Wrong
./index.html

# Fix
mv index.html docs-internal/
# or delete if not needed
```

### ❌ Too Many .txt Files
```bash
# Wrong
./notes.txt
./scratch.txt

# Fix
mv *.txt docs-internal/
# or delete if temporary
```

## Rationale

### Why This Matters

1. **Mintlify Performance**
   - Cleaner root = faster scanning
   - Less confusion about what to index
   - Reduced memory usage

2. **Developer Experience**
   - Easy to find essential project files
   - Clear structure reduces questions
   - Onboarding is faster

3. **Professionalism**
   - Clean repository looks maintained
   - Clear organization demonstrates care
   - Easier for external contributors

4. **Maintainability**
   - Less clutter = easier navigation
   - Clear homes for different content types
   - Scales better as project grows

## Current Root Directory (2025-10-14)

```
/
├── .mintlifyignore        ✅ Essential (Mintlify config)
├── pyproject.toml         ✅ Essential (Python project)
├── README.md              ✅ Essential (Project README)
├── CHANGELOG.md           ✅ Essential (Version history)
├── SECURITY.md            ✅ Essential (Security policy)
├── REPOSITORY_STRUCTURE.md ✅ Essential (Structure docs)
├── requirements*.txt      ✅ Essential (Dependencies)
├── .gitignore             ✅ Essential (Git config)
├── .pre-commit-config.yaml ✅ Essential (Git hooks)
├── docs/
│   └── docs.json          ✅ Essential (Mintlify v4+ config)
└── (no other .md/.html files) ✅ Clean!
```

## Summary

**Goal:** Keep root directory clean and professional
**Method:** Use appropriate subdirectories for all non-essential content
**Benefit:** Better Mintlify performance, clearer structure, happier developers

---

**Policy Established:** 2025-10-14
**Review Frequency:** Quarterly
**Enforcement:** Manual (consider automating with pre-commit hooks)
