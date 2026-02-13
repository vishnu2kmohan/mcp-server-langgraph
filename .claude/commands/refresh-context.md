---
description: Refresh Claude Code context files from current repository state. Use when context feels stale or after significant repository changes.
allowed-tools:
  - Bash(git:*)
  - Bash(uv:*)
  - Read
  - Glob
  - Grep
  - Write
---
# Refresh Context Files

**Usage**: `/refresh-context` or `/refresh-context --full`

**Purpose**: Manually refresh Claude Code context files from current repository state

---

## 📋 What This Command Does

Refreshes context files in `.claude/context/` by analyzing current repository state:

1. **recent-work.md**: Updates from git commit history (last 15 commits)
2. **Repository stats**: Current file counts, test counts, branch info
3. **Recent file activity**: Files changed in last 7 days
4. **Commit categorization**: Automatic categorization by type

---

## 🚀 Execution

### Step 1: Run Update Script

```bash
# Quick refresh (recent-work.md only - FAST)
uv run --frozen python scripts/workflow/update-context-files.py --recent-work

# View what changed
git diff .claude/context/recent-work.md
```

### Step 2: Verify Update

Check that recent-work.md was updated:

```bash
# Check last updated timestamp
head -10 .claude/context/recent-work.md

# View recent commits section
grep -A 20 "Recent Commits" .claude/context/recent-work.md
```

### Step 3: Report Status

Provide user with summary:

```
- ✅ Context Refreshed

Updated:
- recent-work.md: Last 15 commits, 7 days of file activity
- Repository stats: X commits, Y files, Z tests
- Hot spots identified: [top directories]

Last commit: [hash] - [message]
Branch: [current branch]

Context is now up-to-date with repository state.
```

---

## 🔧 Options

### Quick Refresh (Default)

Updates only recent-work.md (fast, ~2-5 seconds):

```bash
uv run --frozen python scripts/workflow/update-context-files.py --recent-work
```

### Full Refresh (Slower)

Note: testing-patterns.md and code-patterns.md updates are not yet automated (too complex).
Only recent-work.md is auto-updated currently.

Future expansion will include:
- Testing patterns extraction
- Code patterns analysis
- ADR indexing

---

## 📊 What Gets Updated

### recent-work.md

**Repository Overview**:
- Total commits
- Contributors count
- Current branch
- Source/test file counts
- Total test count

**Recent Commits** (Last 15):
- Categorized by type (feat, fix, docs, test, etc.)
- With author and date
- Full commit message

**Recently Modified Files** (Last 7 Days):
- Top 15 files by change frequency
- Sorted by modification count

**Quick Context**:
- Auto-generated insights from commit patterns
- Hot spot directories identified
- Suggested next steps

---

## ⚡ Performance

- **Quick refresh**: ~2-5 seconds
- **Auto-runs**: After every commit (via git hook)
- **No manual work**: Fully automated

---

## 🔄 Auto-Update

Context files automatically update via git hook after commits.

To verify git hook is installed:

```bash
cat .git/hooks/post-commit
```

Should contain:
```bash
#!/bin/bash
uv run --frozen python scripts/workflow/update-context-files.py --recent-work --quiet
```

To reinstall hook if missing:

```bash
uv run --frozen python scripts/workflow/update-context-files.py --create-hook
```

---

## 💡 When to Use

**Auto-refresh** (via git hook):
- After every commit ✅
- After merge ✅
- After rebase ✅

**Manual refresh** (use this command):
- Starting new Claude Code session
- After pulling changes from remote
- When context feels stale
- Before starting a sprint

**Not needed**:
- During active coding (auto-updates handle it)
- Multiple times per session (once is enough)

---

## 🎯 Benefits

**Before**:
- Manual git log reading (5-10 minutes)
- Remembering recent changes
- Checking file activity manually
- Context becomes stale

**After**:
- Instant context (2 seconds)
- Auto-updated after commits
- Always fresh data
- Zero manual effort

---

## 📝 Example Output

```
User: /refresh-context

Claude:
Refreshing context from repository state...

Running: python scripts/workflow/update-context-files.py --recent-work

- ✅ Context Refreshed Successfully!

Updated Files:
- .claude/context/recent-work.md

Repository Stats:
- Total commits: 256
- Current branch: main
- Source files: 89 Python files
- Test files: 43 Python files
- Total tests: 437 tests

Recent Activity:
- Last 15 commits analyzed
- 25 files modified in last 7 days
- Hot spots: src/monitoring/, tests/integration/

Top Recent Commits:
- feat(workflow): comprehensive Claude Code workflow optimization
- fix(ci): fix GitHub workflow syntax
- feat(ci): add Dependabot auto-merge workflow

Context is ready for your session!
```

---

## 🔗 Related Commands

- `/start-sprint` - Uses fresh context for sprint planning
- `/progress-update` - Generates progress using git stats
- `/todo-status` - Shows TODO burndown

---

## 🛠️ Troubleshooting

### Issue: Script not found

```bash
# Check if script exists
ls -la scripts/workflow/update-context-files.py

# If missing, script may not be committed yet
```

### Issue: Permission denied

```bash
# Make script executable (Unix/macOS only - Windows uses file associations)
chmod +x scripts/workflow/update-context-files.py

# On Windows, run scripts via Python directly:
# python scripts/workflow/update-context-files.py
```

### Issue: Git hook not working

```bash
# Reinstall hook
uv run --frozen python scripts/workflow/update-context-files.py --create-hook

# Test manual update
uv run --frozen python scripts/workflow/update-context-files.py --recent-work
```

---

## 📚 Technical Details

**Script**: `scripts/workflow/update-context-files.py`
**Languages**: Python 3.10+
**Dependencies**: Git, uv (for test collection)
**Performance**: O(n) where n = number of commits
**Storage**: Updates 1 file (~5-10 KB)

**Git Commands Used**:
```bash
git log --format=... -n 15     # Recent commits
git log --since=7.days --name-only  # File activity
git rev-list --count HEAD      # Total commits
git ls-files src/ tests/       # File counts
```

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**Auto-update**: Enabled via git hook
