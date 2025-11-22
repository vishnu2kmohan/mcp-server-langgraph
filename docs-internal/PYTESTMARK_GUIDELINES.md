# Pytestmark Placement Guidelines

## Critical Rule: pytestmark MUST Appear After All Imports

**Last Updated:** 2025-11-20
**Status:** ENFORCED (Pre-commit hook + Meta-test)
**Severity:** CRITICAL (Causes SyntaxError if violated)

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Why This Rule Exists](#why-this-rule-exists)
3. [Correct Placement Examples](#correct-placement-examples)
4. [Incorrect Placement Examples](#incorrect-placement-examples)
5. [Automated Enforcement](#automated-enforcement)
6. [Troubleshooting](#troubleshooting)
7. [References](#references)

---

## Quick Reference

### ✅ CORRECT Placement

```python
"""Test module docstring."""

import gc
import pytest
from pathlib import Path
from unittest.mock import AsyncMock

# pytestmark AFTER all imports
pytestmark = pytest.mark.unit


class TestSomething:
    # Test code...
```

### ❌ INCORRECT Placement (Causes SyntaxError)

```python
"""Test module docstring."""

import pytest

# ❌ pytestmark inside import block
pytestmark = pytest.mark.unit

import gc  # ❌ SyntaxError: imports must be at top
from pathlib import Path  # ❌ This also fails
```

---

## Why This Rule Exists

### Python's Import Requirement

Python requires **all import statements** to appear at the **top of the module** (after docstrings and module-level comments). Placing any non-import statement (like `pytestmark` assignment) **between** or **inside** imports violates Python's syntax rules and causes a **SyntaxError**.

### Historical Context

During pytest marker rollout (commit `a57fcc95`, 2025-11-20), OpenAI Codex identified that manually-added `pytestmark` declarations could be incorrectly placed inside import blocks. While the automated script `scripts/fix_missing_pytestmarks.py` correctly places `pytestmark` AFTER imports using AST analysis, there was no validation to catch manual misplacements.

This guideline, along with automated enforcement, prevents this issue from recurring.

---

## Correct Placement Examples

### Example 1: Simple Test File

```python
"""Unit tests for authentication."""

import pytest
from mcp_server_langgraph.auth import User

pytestmark = pytest.mark.unit


def test_user_creation():
    user = User(username="test")
    assert user.username == "test"
```

**Why it works:** `pytestmark` appears on line 6, **after** all imports (lines 3-4).

---

### Example 2: File with Multiple Imports

```python
"""Integration tests for API endpoints."""

import gc
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from mcp_server_langgraph.api.health import router
from mcp_server_langgraph.core.config import Settings

# pytestmark appears AFTER all imports
pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_health_endpoint():
    # Test code...
```

**Why it works:** `pytestmark` on line 12 appears **after** the last import on line 9.

---

### Example 3: File with sys.path Manipulation

```python
"""Test file that modifies sys.path."""

import gc
import sys
from pathlib import Path

import pytest

# sys.path modification (non-import statement)
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

from some_script import helper  # noqa: E402

# pytestmark appears AFTER ALL statements (including late imports)
pytestmark = pytest.mark.unit


def test_helper():
    # Test code...
```

**Why it works:** `pytestmark` on line 15 appears **after** the late import on line 12 (note the `# noqa: E402` which allows import-not-at-top for this special case).

---

## Incorrect Placement Examples

### Example 1: pytestmark Before Imports (WRONG!)

```python
"""Test file with incorrect placement."""

import pytest

# ❌ pytestmark before other imports
pytestmark = pytest.mark.unit

import gc  # ❌ SyntaxError!
from pathlib import Path  # ❌ Also fails
```

**Error:**
```
SyntaxError: import statement after assignment
```

**Why it fails:** Python sees `pytestmark = ...` (line 6) before `import gc` (line 8), violating the "imports at top" rule.

---

### Example 2: pytestmark Inside Import Block (WRONG!)

```python
"""Test file with pytestmark inside import parentheses."""

import pytest

from mcp_server_langgraph.core.exceptions import (
pytestmark = pytest.mark.unit  # ❌ WRONG! Inside import block!
    AuthenticationError,
    AuthorizationError,
)
```

**Error:**
```
SyntaxError: invalid syntax
```

**Why it fails:** Inside `from ... import (...)`, Python expects **import names** (like `AuthenticationError`), not variable assignments.

---

### Example 3: pytestmark Between Import Groups (WRONG!)

```python
"""Test file with pytestmark between import groups."""

import pytest
import gc

pytestmark = pytest.mark.unit  # ❌ Still more imports below!

from pathlib import Path  # ❌ SyntaxError!
from unittest.mock import AsyncMock  # ❌ Also fails
```

**Error:**
```
SyntaxError: import statement after assignment
```

**Why it fails:** `pytestmark` appears before the `from pathlib import Path` statement, breaking the "imports at top" rule.

---

## Automated Enforcement

### 1. Pre-Commit Hook

**Hook ID:** `validate-pytest-markers`
**Script:** `scripts/validate_pytest_markers.py`
**Triggers:** When test files (`.py`) or `pyproject.toml` are modified

The pre-commit hook will **automatically block commits** with misplaced `pytestmark` declarations:

```bash
$ git commit -m "Add test"
Validate Pytest Markers & Placement..........................................Failed
❌ Found 1 pytestmark placement error:
   - tests/test_example.py:17 (pytestmark before import at line 23)

📝 To fix, move pytestmark AFTER all import statements:
   ❌ WRONG:
      import pytest
      pytestmark = pytest.mark.unit  # Before other imports!
      from pathlib import Path

   ✅ CORRECT:
      import pytest
      from pathlib import Path

      pytestmark = pytest.mark.unit  # After all imports
```

---

### 2. Meta-Test

**Test File:** `tests/meta/test_pytestmark_placement.py`
**Test Function:** `test_pytestmark_appears_after_all_imports()`

This meta-test scans **all test files** and validates `pytestmark` placement using **AST (Abstract Syntax Tree) parsing**:

```bash
$ pytest tests/meta/test_pytestmark_placement.py -v

tests/meta/test_pytestmark_placement.py::TestPytestmarkPlacement::test_pytestmark_appears_after_all_imports PASSED
```

If violations exist, the test **fails** with detailed error messages:

```
FAILED - AssertionError:
================================================================================
❌ PYTESTMARK PLACEMENT VIOLATIONS DETECTED
================================================================================

Found 1 file(s) with pytestmark inside import blocks:

  1. tests/test_example.py:17 (pytestmark before import at line 23)

[... detailed error message with fix instructions ...]
```

---

### 3. Manual Validation

You can manually run the validator at any time:

```bash
$ python scripts/validate_pytest_markers.py

🔍 Validating pytest markers...
✅ All 36 used markers are registered
✅ All test files have pytestmark declarations
✅ All pytestmark declarations are correctly placed
   Registered: 43 markers
   Used: 36 markers
```

---

## Troubleshooting

### Error: "pytestmark before import at line X"

**Problem:** You placed `pytestmark` before some import statements.

**Solution:**
1. Find the **last import** in your file (e.g., line 23)
2. Move `pytestmark` to **after** that line (e.g., line 25)
3. Add a blank line for readability

**Example fix:**

```diff
  import pytest
  import gc
- pytestmark = pytest.mark.unit
  from pathlib import Path
+
+ pytestmark = pytest.mark.unit
```

---

### Error: "PARSE_ERROR (cannot parse: ...)"

**Problem:** Your file has syntax errors preventing AST parsing.

**Solution:**
1. Check for syntax errors using Python: `python -m py_compile tests/your_file.py`
2. Common causes:
   - Mismatched parentheses in imports
   - `pytestmark` inside `from ... import (...)` block
   - Missing commas in import lists

**Example fix:**

```diff
  from module import (
-     pytestmark = pytest.mark.unit
      Symbol1,
      Symbol2,
  )
+
+ pytestmark = pytest.mark.unit
```

---

### Question: "Can I have pytestmark at class level?"

**Answer:** Yes! Class-level `pytestmark` is fine:

```python
import pytest

pytestmark = pytest.mark.unit  # Module-level (must be after imports)


class TestExample:
    pytestmark = pytest.mark.slow  # Class-level (no restriction)

    def test_something(self):
        pass
```

**This guideline only applies to MODULE-LEVEL `pytestmark`**, not class-level or function-level markers.

---

### Question: "What about conditional imports?"

**Answer:** Place `pytestmark` **after ALL imports**, including conditional ones:

```python
import pytest

# Conditional import
try:
    from freezegun import freeze_time
except ImportError:
    pytest.skip("freezegun not installed", allow_module_level=True)

# pytestmark AFTER conditional import block
pytestmark = pytest.mark.unit


def test_with_freezegun():
    # ...
```

---

## References

### Related Files

- **Validator Script:** [`scripts/validate_pytest_markers.py`](../scripts/validate_pytest_markers.py)
- **Meta-Test:** [`tests/meta/test_pytestmark_placement.py`](meta/test_pytestmark_placement.py)
- **Pre-Commit Config:** [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) (line 742)
- **Auto-Fix Script:** [`scripts/fix_missing_pytestmarks.py`](../scripts/fix_missing_pytestmarks.py) (lines 108-129)


### Git History

- **Commit `a57fcc95`** (2025-11-20): "fix(test): add missing pytestmark declarations to 239 test files"
  - Added `pytestmark` to 163 files using automated script
  - Script correctly placed `pytestmark` after imports using AST analysis

### OpenAI Codex Findings

- **Report Date:** 2025-11-20
- **Finding:** 16 files identified with `pytestmark` inside import blocks
- **Status:** Validated (most were false positives, 1 real violation fixed)

---

## Summary

**Golden Rule:** `pytestmark` must appear **AFTER** all module-level import statements.

**Enforcement:** Pre-commit hook + Meta-test (100% coverage)

**Detection:** AST-based parsing (more reliable than regex)

**Documentation:** This file (PYTESTMARK_GUIDELINES.md)

**Prevention:** Automated script (`fix_missing_pytestmarks.py`) always places correctly

---

**Questions or issues?** See [TESTING.md](TESTING.md) or open a GitHub issue.
