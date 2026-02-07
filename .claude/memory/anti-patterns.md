---
purpose: Common mistakes to avoid and their corrections
priority: high
category: anti-patterns
last-updated: 2026-02-05
---

# Anti-Patterns to Avoid

---

## Tool Usage Anti-Patterns

### 1. Sequential When Parallel Works

```
# BAD
Read file1.py
[wait]
Read file2.py
[wait]
Read file3.py

# GOOD - Single message with all reads
Read file1.py, Read file2.py, Read file3.py  # Parallel execution
```

### 2. Individual Edits for Bulk Changes

```
# BAD - 10 separate Edit calls
Edit file1.py: old -> new
Edit file2.py: old -> new
...

# GOOD - Single script
rg -l "old" --type py | xargs sed -i '' 's/old/new/g'
```

### 3. Grep in Bash Instead of Grep Tool

```bash
# BAD - Using bash for grep
Bash: grep -r "pattern" src/

# GOOD - Using Grep tool (optimized, sandboxed)
Grep "pattern" path=src/
```

### 4. Cat/Head/Tail Instead of Read

```bash
# BAD
Bash: cat file.py
Bash: head -50 file.py

# GOOD
Read file.py
Read file.py limit=50
```

---

## Code Change Anti-Patterns

### 5. Over-Engineering

```python
# BAD - Asked to add a button, created a button factory
class ButtonFactory:
    def create_button(self, variant, size, ...): ...

# GOOD - Just add the button
<Button onClick={handleClick}>Save</Button>
```

### 6. Unnecessary Abstractions

```python
# BAD - One-time operation wrapped in helper
def get_user_name(user):
    return user.name

name = get_user_name(user)

# GOOD - Direct access
name = user.name
```

### 7. Adding Unrequested Features

```python
# Asked: Add logging to this function
# BAD: Added logging, retry logic, caching, metrics, config options
# GOOD: Added logging only
```

### 8. Gratuitous Refactoring

```python
# BAD - Fixing a bug but also "improving" surrounding code
def calculate(x):  # Fixed bug AND renamed AND added docstring AND...

# GOOD - Minimal fix
def calc(x):  # Just fixed the bug
```

---

## Testing Anti-Patterns

### 9. Tests After Implementation

```python
# BAD - TDD violation
def new_feature(): ...  # Implementation first
def test_new_feature(): ...  # Test after

# GOOD - TDD
def test_new_feature(): ...  # Test first (RED)
def new_feature(): ...  # Implementation to pass test (GREEN)
```

### 10. Testing Implementation, Not Behavior

```python
# BAD - Tests internal structure
def test_uses_cache():
    assert func._cache is not None

# GOOD - Tests behavior
def test_returns_same_value_on_second_call():
    assert func(1) == func(1)
```

---

## Git Anti-Patterns

### 11. Committing Without Being Asked

```bash
# BAD - Auto-committing after changes
git commit -m "Added feature"  # User didn't ask

# GOOD - Wait for explicit request
# Make changes, then WAIT for user to say "commit this"
```

### 12. Force Push Without Warning

```bash
# BAD
git push --force

# GOOD
"This requires force push which rewrites history. Proceed?"
```

### 13. Amending Pushed Commits

```bash
# BAD - Amending after push
git commit --amend  # When commit already pushed

# GOOD - New commit for fixes
git commit -m "Fix: correct the previous change"
```

---

## Communication Anti-Patterns

### 14. Echo Commands as Communication

```bash
# BAD
Bash: echo "I'm going to read the file now"

# GOOD
"I'll read the file now."  # Direct text output
Read file.py
```

### 15. Excessive Praise/Validation

```
# BAD
"That's a great question! You're absolutely right that..."

# GOOD
"The function handles that case at line 42."
```

### 16. Announcing Before Doing

```
# BAD
"I'm going to search for the pattern."
"Now I'll search."
"Searching now..."
Grep pattern

# GOOD
Grep pattern
"Found 3 matches in src/core/..."
```

---

## Context Anti-Patterns

### 17. Re-Reading What You Already Have

```
# BAD - File was read 10 messages ago
Read file.py  # "Let me check the file again..."

# GOOD
"Based on file.py that we read earlier, the function at line 25..."
```

### 18. Asking What User Already Said

```
# BAD
User: "Fix the bug in auth.py line 42"
Claude: "Which file has the bug?"

# GOOD
Claude: Reads auth.py and fixes line 42
```

### 19. Spawning Agents for Simple Tasks

```
# BAD
Task(subagent_type="Explore", prompt="Find where UserModel is defined")

# GOOD
Grep "class UserModel" --type py
```

---

## Python Environment Anti-Patterns

### 20. Using Bare Python

```bash
# BAD
uv run --frozen python script.py
pytest tests/
pip install package

# GOOD
uv run python script.py
uv run pytest tests/
uv add package
```

---

## Script Reuse Anti-Patterns

### 21. Creating Scripts Without Checking Existing Ones

```bash
# BAD - Creating new bulk fix script
# "I'll write a script to fix AsyncMock issues..."
Write scripts/fix_asyncmock_new.py

# GOOD - Check existing scripts first
Read scripts/SCRIPT_INVENTORY.md  # 192 scripts documented!
# Found: scripts/archive/unused/bulk_fix_async_mock.py
# Found: scripts/validators/check_asyncmock_usage.py (pre-commit hook)
```

**Before creating bulk operation scripts, ALWAYS:**
1. Read `scripts/SCRIPT_INVENTORY.md` (auto-generated, 192 scripts)
2. Search: `Glob scripts/**/*.py` or `Grep "pattern" path=scripts/`
3. Check `scripts/archive/unused/` for archived but reusable scripts
4. Check `.pre-commit-config.yaml` for existing validation hooks

### 22. Using Edit Tool for Bulk Operations

```
# BAD - 50 separate Edit calls
Edit file1.py: AsyncMock() -> AsyncMock(spec=X)
Edit file2.py: AsyncMock() -> AsyncMock(spec=X)
...

# GOOD - Script + single Bash call
Bash: uv run python scripts/archive/unused/bulk_fix_async_mock.py
```

**Context efficiency**: Scripts execute outside Claude's context window = zero token overhead.

### 23. Sequential Tests When Parallel Available

```bash
# BAD - Sequential (20+ minutes for 8,700+ tests)
uv run pytest

# GOOD - Parallel with xdist (~3 minutes)
uv run pytest -n auto

# OPT-OUT when debugging isolation
PYTEST_SEQUENTIAL=1 uv run pytest
```

### 24. Sequential npm Tests

```bash
# BAD - Default pool (slower)
npm test

# GOOD - Thread pool (faster for larger projects)
npm test -- --pool=threads

# FALLBACK (compatibility issues)
npm test -- --pool=forks
```

### 25. run_in_background + TaskOutput Polling

```
# BAD - Creates orphaned notifications, wastes context
Bash(run_in_background=true): pytest ...
TaskOutput(task_id, block=true)
# If parent exits, notifications leak into conversation

# GOOD - Parallel blocking calls, single round-trip
Bash(timeout=300000): pytest -m unit
Bash(timeout=300000): npm test
# Both run concurrently, return together
```

---

## Recovery Patterns

When you catch yourself in an anti-pattern:

| Situation | Recovery |
|-----------|----------|
| Started sequential reads | Stop, batch remaining reads |
| Made unnecessary changes | Revert, apply minimal fix |
| Committed without asking | Inform user, offer to revert |
| Re-read a file | Continue, but note for future |
| Over-engineered | Simplify before proceeding |

---

**Key Insight**: Most anti-patterns stem from not thinking ahead. Before acting, ask: "Is there a more efficient way?"
