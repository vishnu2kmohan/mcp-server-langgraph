---
purpose: Fast decision frameworks for common tool and workflow choices
priority: high
category: decision-trees
last-updated: 2026-02-05
---

# Quick Decision Trees

---

## Tool Selection

```
Need to find files?
├── By name/pattern → Glob
├── By content → Grep
└── Unknown structure → Task(Explore)

Need to read files?
├── 1 file → Read
├── 2-4 files → Parallel Read calls (single message)
└── 5+ files → Consider: do I need all of them?

Need to make changes?
├── 1-2 files, different changes → Edit
├── 3+ files, same pattern → Script (rg | xargs sed)
├── Complex logic → Python script
└── New file needed → Write (but prefer Edit existing)

Need to run command?
├── Git operation → Bash
├── Tests → Bash (uv run pytest)
├── File search → Glob/Grep (NOT bash find/grep)
└── Package management → Bash (uv add/run)
```

---

## Script vs Tool Calls

```
How many files need the same change?
├── 1-2 files → Edit tool
├── 3-5 files → Probably script
└── 6+ files → Definitely script

Is the change pattern-based (regex)?
├── Yes → rg | xargs sed
└── No, needs logic → Python script

Is order important?
├── Yes → Sequential Bash with &&
└── No → Parallel tool calls
```

---

## Agent Selection

```
What's the task?
├── Code exploration/search → Task(Explore)
├── Multi-step implementation → Task(Plan) first
├── Git operations → Bash directly
├── Simple lookup → Grep/Glob directly
└── Complex research → Task(general-purpose)

How deep is the search?
├── Know exact pattern → Grep directly
├── Know file pattern → Glob directly
├── Need to understand structure → Task(Explore, "quick")
├── Need comprehensive analysis → Task(Explore, "very thorough")
```

---

## Test Approach

```
Writing new code?
├── Yes → TDD: Write test FIRST
└── Fixing bug → Write failing test that reproduces bug FIRST

What test type?
├── Single function/class → @pytest.mark.unit
├── Multiple components together → @pytest.mark.integration
├── External services (DB, API) → @pytest.mark.requires_infrastructure
├── Slow (>1s) → @pytest.mark.slow

How to run?
├── Quick check → uv run pytest -x (stop on first failure)
├── Last failed → uv run pytest --lf
├── Unit only → uv run pytest -m unit
├── Full suite → uv run pytest
```

---

## Error Handling

```
Test failed?
├── Is it my change? → Fix the issue
├── Pre-existing failure? → Note it, continue
└── Flaky test? → Run again, investigate if persists

Type error?
├── Missing import → Add import
├── Wrong type → Fix the type
├── Complex generic → Check if type:ignore is appropriate
└── Third-party library → Check stub availability

Lint error?
├── Formatting → uv run ruff format
├── Code quality → uv run ruff check --fix
├── Can't auto-fix → Manual fix following ruff suggestion
```

---

## Commit Strategy

```
User asked to commit?
├── Yes → Proceed with commit workflow
└── No → DO NOT commit automatically

What to include in commit?
├── Staged changes only → git commit
├── All tracked changes → git add . && git commit
├── Specific files → git add <files> && git commit

Commit message style?
├── Check recent commits → git log --oneline -10
├── Follow existing convention → Usually conventional commits
└── Include Co-Authored-By → Always (Claude Code requirement)
```

---

## Context Management

```
Starting new task?
├── Related to current work → Continue in context
├── Unrelated task → Suggest /clear first
└── Need fresh start → /clear then reload essentials

Context feeling full?
├── Still working on same thing → Continue
├── Finished major task → Suggest /clear
└── User asks about something new → Complete current, then /clear
```

---

## Plan Mode

```
Should I enter plan mode?
├── Simple, obvious fix → No, just do it
├── Multi-file change → Yes, plan first
├── Architectural decision → Yes, definitely
├── User said "just do it" → No, proceed
└── Unsure about approach → Yes, plan and ask
```

---

## Bulk Operation Recipes

> **Cross-Platform Note**: Use `perl -pi -e` instead of `sed -i` for portable in-place editing.
> Python alternatives provided for Windows compatibility.

```
Rename symbol across codebase (cross-platform):
rg -l "OldName" --type py | xargs perl -pi -e 's/OldName/NewName/g'

Add import to files using symbol (Python for reliability):
uv run --frozen python3 -c "
from pathlib import Path
for f in Path('.').rglob('*.py'):
    c = f.read_text()
    if 'Symbol' in c and 'import foo' not in c:
        f.write_text('import foo\n' + c)
"

Update version in multiple files:
rg -l "1.2.3" | xargs perl -pi -e 's/1.2.3/1.2.4/g'

Find and update test markers:
rg -l "@pytest.mark.old" tests/ | xargs perl -pi -e 's/\@pytest.mark.old/\@pytest.mark.new/g'

Rename files matching pattern:
fd "old_name" --type f -x mv {} {//}/new_name

Remove lines matching pattern:
rg -l "pattern_to_remove" | xargs perl -pi -e '/pattern_to_remove/ && next; print'
```

---

## Quick Checks

```
Before making changes:
□ Did I read the file first?
□ Did I check for tests?
□ Is this the minimal change?
□ Am I following existing patterns?

Before committing:
□ Did user ask me to commit?
□ Are tests passing?
□ Is lint clean?
□ Is the message clear?

Before suggesting /clear:
□ Is current task complete?
□ Is there uncommitted work?
□ Did I update todos?
```

---

**Principle**: When in doubt, choose the simpler path. Complexity should be justified.
