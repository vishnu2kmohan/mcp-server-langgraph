# Documentation Validation - Quick Start Guide

**Last Updated**: 2025-11-12
**Status**: ✅ Production Ready
**Time to Learn**: 5 minutes

---

## 🚀 One-Minute Quick Start

```bash
# Validate all documentation (one command!)
make docs-validate

# Auto-fix MDX syntax errors
make docs-fix-mdx

# Run validation tests
make docs-test

# Done! ✅
```

That's it. Everything else is automated.

---

## 📋 Daily Workflow

### Editing Documentation

```bash
# 1. Edit
vim docs/guides/my-guide.mdx

# 2. Validate
make docs-validate

# 3. Fix (if needed)
make docs-fix-mdx

# 4. Commit
git commit -m "docs: update guide"
# Pre-commit hooks run automatically and fix issues

# 5. Push
git push
# CI validates on PR
```

**Time**: <1 minute of your time (automation does the rest)

---

## 🔧 Common Tasks

### Before Committing

```bash
make docs-validate
```

**What it does**:
- ✅ Checks MDX syntax
- ✅ Validates internal links
- ✅ Checks version consistency
- ✅ Validates Mintlify build

**Time**: ~10-15 seconds

---

### Fixing Issues

```bash
# Auto-fix MDX syntax
make docs-fix-mdx

# Check what changed
git diff docs/

# If good, commit
git add docs/
git commit -m "fix(docs): resolve MDX syntax errors"
```

**Time**: ~5 seconds + review time

---

### Running Tests

```bash
make docs-test
```

**Output**:
```text
🧪 Running documentation validation tests...
======================== 27 passed in 3.16s =========================
✅ All tests passed!
```

**Time**: 3 seconds

---

### Monthly Audit

```bash
make docs-audit
```

**Output**:
```text
📊 Running comprehensive documentation audit...
Current version: 2.8.0

Running validations...
✅ MDX syntax validation passed
✅ Internal links validation passed
⚠️  Version consistency warnings (32 files)
✅ Mintlify validation passed

See docs-internal/DOCUMENTATION_AUDIT_*.md for detailed reports
```

**Time**: ~15 seconds

---

## 🎯 Mintlify CLI Validation (CRITICAL for Docs Changes)

### Why Use Mintlify CLI?

Mintlify CLI provides the **final validation** that your documentation will work correctly in production. Python validators catch most issues, but Mintlify CLI validates:
- **Actual build process** - Ensures docs compile without errors
- **Link resolution** - Validates internal links and anchors work correctly
- **Component rendering** - Checks MDX components render properly
- **Production accuracy** - Same validation that runs on Mintlify hosting

### When to Run Mintlify Validation

**ALWAYS run before committing docs changes**:
```bash
make docs-validate-mintlify
```

**Run manually via pre-commit hook** (optional):
```bash
SKIP= pre-commit run mintlify-broken-links-check --all-files
```

**During /docs-audit** (recommended monthly):
```bash
# Via Claude Code slash command
/docs-audit
# This automatically runs Mintlify validation as part of comprehensive audit
```

### Understanding Mintlify Validation Output

```bash
$ make docs-validate-mintlify

📋 Validating Mintlify configuration...
🔗 Checking for broken links...
✅ Broken links check passed

🏗️  Validating Mintlify build...
   Note: This will start the dev server briefly to validate the build.
   The server will auto-stop after validation.
✅ Mintlify build validation passed
```

**If you see errors**:
1. Read the error message carefully
2. Check the file and line number mentioned
3. Fix the issue (usually MDX syntax or broken link)
4. Run validation again
5. Repeat until all checks pass

### Mintlify CLI vs Python Validators

| Aspect | Python Validators | Mintlify CLI |
|--------|------------------|--------------|
| **Speed** | Fast (2-8s) | Slower (15-20s) |
| **Coverage** | MDX syntax, frontmatter, basic links | Full build, all links, components |
| **When to use** | Every commit (via pre-commit) | Before push, during audit |
| **Automation** | Pre-commit hooks | Manual or /docs-audit |
| **Accuracy** | Catches 80% of issues | Catches 100% of issues |

**Best Practice**: Use Python validators frequently, Mintlify CLI before pushing.

---

## 🛠️ Installation

### Prerequisites

```bash
# Python 3.11+ (already installed if you're working on this project)
python3 --version

# Node.js (for Mintlify)
node --version

# That's it!
```

### One-Time Setup

```bash
# Install pre-commit hooks
pip install pre-commit  # or: uv tool install pre-commit
pre-commit install

# Done! Hooks will run automatically on commit
```

**Time**: 1 minute

---

## 📚 Available Commands

### Validation

| Command | Description | Time |
|---------|-------------|------|
| `make docs-validate` | Validate everything | 10-15s |
| `make docs-validate-mdx` | MDX syntax only | 2-3s |
| `make docs-validate-links` | Internal links only | 5-8s |
| `make docs-validate-version` | Version consistency | 2-3s |
| `make docs-validate-mintlify` | Mintlify broken links + build validation | 15-20s |

### Fixing

| Command | Description | Time |
|---------|-------------|------|
| `make docs-fix-mdx` | Auto-fix MDX errors | 2-3s |

### Testing

| Command | Description | Time |
|---------|-------------|------|
| `make docs-test` | Run validation tests | 3s |

### Utilities

| Command | Description | Time |
|---------|-------------|------|
| `make docs-audit` | Comprehensive audit | 15s |
| `make docs-serve` | Serve docs locally | N/A |
| `make docs-build` | Build documentation | ~1min |

---

## 🐛 Troubleshooting

### "make docs-validate" fails

```bash
# Run individual validations to identify issue
make docs-validate-mdx       # MDX syntax
make docs-validate-links     # Internal links
make docs-validate-version   # Versions
make docs-validate-mintlify  # Mintlify build

# Fix the failing one
# If MDX syntax:
make docs-fix-mdx
```

### "make docs-test" fails

```bash
# Run with verbose output
uv run pytest tests/test_mdx_validation.py -vv

# Check specific test
uv run pytest tests/test_mdx_validation.py::TestName::test_name -vv

# If tests fail, scripts may have issues
# Report to team
```

### "pre-commit hook fails"

```bash
# See what it tried to fix
git diff

# If changes look good
git add .
git commit

# If changes look bad
git checkout .
# Report issue to team
```

### "Mintlify validation fails"

```bash
# Option 1: Run comprehensive Mintlify validation (recommended)
make docs-validate-mintlify
# This runs both 'broken-links' and 'dev' build validation

# Option 2: Run individual Mintlify checks
cd docs

# Check for broken links
npx mintlify broken-links

# Validate build (starts dev server briefly)
mintlify dev
# Press Ctrl+C after verifying build succeeds

# Option 3: Manual pre-commit hook
SKIP= pre-commit run mintlify-broken-links-check --all-files

# Fix the specific file
python3 ../scripts/fix_mdx_syntax.py --file path/to/file.mdx

# Test again
npx mintlify broken-links

# Repeat until clean
```

**Common Mintlify Issues**:
- **Broken links**: Check anchor links and page references in MDX
- **Build errors**: Look for unclosed JSX tags, invalid frontmatter, or syntax errors
- **Missing pages**: Verify all navigation items in `docs.json` have corresponding files

---

## 📖 Full Documentation

**Need more details?**

- **Architecture**: `docs-internal/VALIDATION_INFRASTRUCTURE.md` (12KB)
- **Implementation**: `docs-internal/VALIDATION_IMPLEMENTATION_SUMMARY.md` (26KB)
- **Deployment**: `docs-internal/VALIDATION_DEPLOYMENT_COMPLETE.md` (17KB)
- **Scripts**: `scripts/README.md` (validation section)

**Total**: 55KB of comprehensive documentation

---

## ❓ FAQ

**Q: Do I need to run validation manually?**
A: No! Pre-commit hooks run automatically. But `make docs-validate` is useful to check before committing.

**Q: Will validation slow down my commits?**
A: No! Validation runs in <15 seconds. Worth it to catch errors.

**Q: What if I need to bypass validation?**
A: Use `git commit --no-verify` (not recommended) or `SKIP=fix-mdx-syntax git commit`

**Q: What if the auto-fix breaks something?**
A: Very unlikely (27 tests validate behavior), but if it happens: `git checkout docs/file.mdx` and report issue.

**Q: How do I add new validation rules?**
A: See `VALIDATION_INFRASTRUCTURE.md` - Section "Adding New Validation"

---

## 🎯 Success Checklist

When you see these, validation is working:

- [ ] `make docs-validate` runs in <15 seconds
- [ ] `make docs-test` shows "27 passed"
- [ ] `pre-commit run --all-files` includes fix-mdx-syntax
- [ ] GitHub PRs have "Documentation Validation" checks
- [ ] PR comments show validation status table

If all checked: ✅ **System working perfectly!**

---

## 💪 Power User Tips

### Validate Only Changed Files

```bash
# Pre-commit automatically does this
git add docs/changed-file.mdx
git commit
# Only validates changed file (fast!)
```

### Batch Fix All MDX Files

```bash
# Use with caution - review changes after
make docs-fix-mdx

# Review every change
git diff docs/

# If looks good
git add docs/
git commit -m "fix(docs): resolve all MDX syntax errors"
```

### Check Specific File

```bash
# MDX syntax
python3 scripts/fix_mdx_syntax.py --file docs/my-file.mdx --dry-run

# Links
python3 scripts/check_internal_links.py --file docs/my-file.mdx

# Both
make docs-validate
# Then check output for your file
```

---

## 🔗 Related Resources

- **Testing Guide**: `TESTING.md`
- **Development Setup**: `DEVELOPER_ONBOARDING.md`
- **Contributing**: `CONTRIBUTING.md`
- **Makefile Help**: `make help`

---

**Questions?** See full documentation in `docs-internal/VALIDATION_INFRASTRUCTURE.md`

**Issues?** Create GitHub issue with label: `documentation`

---

🎉 **Happy documenting!** The validation infrastructure has your back. 🎉
