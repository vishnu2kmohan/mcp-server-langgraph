---
description: You are tasked with tracking the mypy strict type checking rollout progress for the mcp-server-langg
---
# Type Safety Status Tracker

You are tasked with tracking the mypy strict type checking rollout progress for the mcp-server-langgraph project. This command helps manage the gradual migration to full type safety.

## Project Type Safety Context

**Current Status**: 3/11 core modules with strict mypy
**Target**: 11/11 modules with strict type checking
**Strategy**: Gradual rollout, module by module
**Tool**: mypy with strict mode

**Strict Mode Benefits**:
- Catch type errors before runtime
- Better IDE autocomplete
- Self-documenting code
- Easier refactoring

## Your Task

### Step 1: Analyze Current mypy Configuration

1. **Read mypy configuration**:
   ```bash
   # Check mypy config
   cat pyproject.toml | grep -A 20 "\[tool.mypy\]"
   ```

2. **Identify strict modules**:
   Look for `[[tool.mypy.overrides]]` sections with `strict = true`

3. **Count total modules**:
   ```bash
   find src/mcp_server_langgraph -name "*.py" -type f | wc -l
   ```

### Step 2: Run mypy Analysis

1. **Run mypy on all code**:
   ```bash
   uv run --frozen mypy src/mcp_server_langgraph --show-error-codes --pretty
   ```

2. **Parse mypy output**:
   - Count total errors
   - Group by error code
   - Group by file
   - Identify patterns

3. **Run mypy with strict on non-strict modules**:
   ```bash
   uv run --frozen mypy src/mcp_server_langgraph/<module>.py --strict --show-error-codes
   ```

### Step 3: Generate Type Safety Dashboard

**Dashboard Format**:
```
╔══════════════════════════════════════════════════════════════════╗
║              TYPE SAFETY STATUS                                  ║
║              mcp-server-langgraph                                ║
╠══════════════════════════════════════════════════════════════════╣
║  Strict Modules:     3/11  [███░░░░░░░░░░░░░░░░░░░]  27%        ║
║  Target:            11/11  [████████████████████████]  100%      ║
║  Progress:            +8   [⚠️  8 modules remaining]             ║
║  mypy Errors:         47   [🔴 Need fixing before strict]        ║
║  Error Types:          9   [Most common: type-arg, no-untyped]  ║
╠══════════════════════════════════════════════════════════════════╣
║  Trend:               📈   [+1 module/sprint]                    ║
║  ETA to Full Strict: 8wk   [At current pace]                    ║
╚══════════════════════════════════════════════════════════════════╝
```

### Step 4: Module-by-Module Breakdown

**Strict Status by Module**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MYPY STRICT ROLLOUT PROGRESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Module                     Status      Errors  Complexity  Priority
  ──────────────────────────────────────────────────────────────────
  📦 Core Modules (3/11 strict)
  ├─ core/config.py          ✅ STRICT   0       Low         ✓
  ├─ core/feature_flags.py   ✅ STRICT   0       Low         ✓
  ├─ core/agent.py           ✅ STRICT   0       Medium      ✓
  ├─ core/llm_factory.py     ⚠️  NOT     12      Medium      🔥 NEXT
  └─ core/state.py           ⚠️  NOT     8       Low         ⚠️

  🔐 Auth Modules (0/4 strict)
  ├─ auth/middleware.py      ⚠️  NOT     9       Medium      🔥
  ├─ auth/jwt.py             ⚠️  NOT     5       Low         ⚠️
  ├─ auth/rbac.py            ⚠️  NOT     15      High        ⚠️
  └─ auth/keycloak.py        ⚠️  NOT     11      High        ⚠️

  💾 Session Modules (0/3 strict)
  ├─ session/store.py        ⚠️  NOT     7       Medium      ⚠️
  ├─ session/distributed.py  ⚠️  NOT     18      High        ℹ️
  └─ session/checkpointing.py⚠️  NOT     6       Medium      ℹ️

  🔧 Tool Modules (0/8 strict)
  ├─ tools/catalog.py        ⚠️  NOT     4       Low         ⚠️
  ├─ tools/calculator.py     ⚠️  NOT     2       Low         ✓ EASY
  ├─ tools/filesystem.py     ⚠️  NOT     8       Medium      ℹ️
  └─ ... (5 more)            ⚠️  NOT     ~15     Varies      ℹ️

  🌐 MCP Modules (0/6 strict)
  ├─ mcp/stdio_server.py     ⚠️  NOT     10      High        ℹ️
  ├─ mcp/protocol.py         ⚠️  NOT     14      High        ℹ️
  └─ ... (4 more)            ⚠️  NOT     ~12     Varies      ℹ️

  📊 Observability (0/5 strict)
  ├─ observability/telemetry ⚠️  NOT     6       Medium      ℹ️
  ├─ observability/logging   ⚠️  NOT     4       Low         ✓ EASY
  └─ ... (3 more)            ⚠️  NOT     ~8      Varies      ℹ️

  ──────────────────────────────────────────────────────────────────
  TOTALS
    ✅ Strict:    3 modules (27%)
    ⚠️  Pending:  8 modules (73%)
    Total Errors: 154 errors across 8 modules
  ──────────────────────────────────────────────────────────────────
```

### Step 5: Error Analysis

**Most Common mypy Errors**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MYPY ERROR BREAKDOWN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Error Code          Count   %      Description
  ──────────────────────────────────────────────────────────────────
  type-arg            38      25%    Missing type arguments (Generic[T])
  no-untyped-def      29      19%    Function missing type annotations
  no-untyped-call     24      16%    Calling untyped function
  return-value        18      12%    Return type mismatch
  arg-type            15      10%    Argument type mismatch
  assignment          12      8%     Assignment type mismatch
  var-annotated       9       6%     Variable needs type annotation
  misc                6       4%     Miscellaneous type errors
  union-attr          3       2%     Union attribute access
  ──────────────────────────────────────────────────────────────────
  TOTAL               154     100%
  ──────────────────────────────────────────────────────────────────

  Top 3 Fixes Needed:
  1. Add type parameters to generic classes/functions [type-arg]
  2. Add function signatures with types [no-untyped-def]
  3. Fix calls to untyped functions [no-untyped-call]
```

### Step 6: Prioritized Migration Plan

**Recommended Migration Order** (based on complexity + impact):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MYPY STRICT MIGRATION PLAN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Sprint 1 (Week 1) - Easy Wins
  ════════════════════════════════════════════════════════════════
  Goal: Migrate 2 simple modules (+18% progress)

  1. ✓ tools/calculator.py (2 errors, 30 min)
     - Add return types to functions
     - Add parameter types
     Command: uv run --frozen mypy tools/calculator.py --strict

  2. ✓ observability/logging.py (4 errors, 45 min)
     - Annotate logger initialization
     - Type log message handling
     Command: uv run --frozen mypy observability/logging.py --strict

  Expected: 5/11 strict (45%)
  Time: ~1.5 hours

  Sprint 2 (Week 2-3) - Medium Complexity
  ════════════════════════════════════════════════════════════════
  Goal: Migrate 3 medium modules (+27% progress)

  3. ⚠️ core/state.py (8 errors, 1-2 hours)
     - Add types to state dataclasses
     - Type LangGraph state handling
     - Add Generic type parameters

  4. ⚠️ auth/jwt.py (5 errors, 1 hour)
     - Type JWT payload structure
     - Add return types to encoding/decoding

  5. ⚠️ session/store.py (7 errors, 1-2 hours)
     - Type Redis operations
     - Add Session type annotations

  Expected: 8/11 strict (73%)
  Time: ~4-5 hours

  Sprint 3 (Week 4-5) - Complex Modules
  ════════════════════════════════════════════════════════════════
  Goal: Migrate 3 complex modules (+27% progress)

  6. 🔥 core/llm_factory.py (12 errors, 2-3 hours)
     - Type LiteLLM integration
     - Add Generic types for LLM responses
     - Handle provider-specific types

  7. ⚠️ auth/middleware.py (9 errors, 2 hours)
     - Type FastAPI middleware
     - Type authentication flow

  8. ℹ️ auth/rbac.py (15 errors, 3-4 hours)
     - Type OpenFGA integration
     - Add permission type structures

  Expected: 11/11 strict (100%) ✓
  Time: ~8-10 hours

  ────────────────────────────────────────────────────────────────
  Total Timeline: 5 sprints (~5 weeks)
  Total Time: 13-16 hours
  Success Rate: High (incremental, tested approach)
  ────────────────────────────────────────────────────────────────
```

### Step 7: Module Migration Checklist

For the next module to migrate, provide a detailed checklist:

**Example: Migrating `core/llm_factory.py`**:
```
┌──────────────────────────────────────────────────────────────────┐
│ MIGRATION CHECKLIST: core/llm_factory.py                        │
├──────────────────────────────────────────────────────────────────┤
│ Current Errors: 12                                               │
│ Estimated Time: 2-3 hours                                        │
│ Complexity: Medium                                               │
└──────────────────────────────────────────────────────────────────┘

Pre-Migration:
  ☐ Run mypy to get baseline errors
    Command: uv run --frozen mypy src/mcp_server_langgraph/core/llm_factory.py --strict --show-error-codes

  ☐ Backup current file (git commit)
    Command: git commit -am "Pre-mypy strict: llm_factory.py"

Step 1: Add Import for Types
  ☐ Add typing imports:
    from typing import Any, Optional, Union, Type, Generic, TypeVar

  ☐ Add third-party type stubs if needed:
    uv add --dev types-redis types-requests

Step 2: Fix Function Signatures
  ☐ Add return types to all functions
    Example: def create_llm() -> LLMFactory:

  ☐ Add parameter types
    Example: def __init__(self, provider: str, model: str) -> None:

  ☐ Handle Optional parameters
    Example: fallback: Optional[List[str]] = None

Step 3: Fix Generic Types
  ☐ Add type parameters to generic classes
    Example: class LLMFactory(Generic[T]):

  ☐ Specify LiteLLM return types
    Example: response: ChatCompletion = await llm.ainvoke(...)

Step 4: Fix Type Mismatches
  ☐ Add type assertions where needed
    Example: assert isinstance(result, AIMessage)

  ☐ Use type guards for unions
    Example: if isinstance(value, str): ...

  ☐ Handle Any types cautiously
    Try to narrow to specific types when possible

Step 5: Enable Strict Mode
  ☐ Add override to pyproject.toml:
    [[tool.mypy.overrides]]
    module = "mcp_server_langgraph.core.llm_factory"
    strict = true

  ☐ Run mypy to verify:
    uv run --frozen mypy src/mcp_server_langgraph/core/llm_factory.py --strict

Step 6: Test & Verify
  ☐ Run existing tests:
    uv run --frozen pytest tests/ -k llm_factory -v

  ☐ Verify no regressions:
    uv run --frozen pytest tests/ --cov=src/mcp_server_langgraph/core/llm_factory.py

  ☐ Check overall mypy status:
    /type-safety-status

Post-Migration:
  ☐ Commit changes:
    git commit -am "feat(types): enable strict mypy for llm_factory.py"

  ☐ Update progress tracker
  ☐ Celebrate! 🎉 One more module strict!

Success Criteria:
  ✅ 0 mypy errors with --strict flag
  ✅ All existing tests pass
  ✅ No coverage regression
  ✅ Code more readable with types
```

### Step 8: Quick Reference

**Common Type Patterns**:
```python
# AsyncIO functions
async def fetch_data() -> dict[str, Any]: ...

# Optional parameters
def process(value: str, timeout: Optional[int] = None) -> bool: ...

# Union types
def handle(item: str | int) -> None: ...

# Generic classes
T = TypeVar('T')
class Store(Generic[T]):
    def get(self, key: str) -> Optional[T]: ...

# Protocol compliance
from typing import Protocol
class HasName(Protocol):
    name: str

# Type guards
def is_string(value: Any) -> TypeGuard[str]:
    return isinstance(value, str)

# Callable types
from collections.abc import Callable
def apply(func: Callable[[int], str], value: int) -> str: ...
```

### Commands to Run

```bash
# Check current strict module status
grep -A 2 "tool.mypy.overrides" pyproject.toml | grep "strict = true" | wc -l

# Run mypy on all code
uv run --frozen mypy src/mcp_server_langgraph --show-error-codes --pretty

# Test strict mode on specific module
uv run --frozen mypy src/mcp_server_langgraph/<module>.py --strict --show-error-codes

# Check which errors are most common (cross-platform: grep -oE instead of grep -oP)
uv run --frozen mypy src/ --show-error-codes 2>&1 | grep -oE '\[[^]]+\]' | sort | uniq -c | sort -rn

# Verify migration successful
uv run --frozen pytest tests/ -v && uv run --frozen mypy src/mcp_server_langgraph --strict
```

## Error Handling

- If mypy not installed, suggest: `uv add --dev mypy`
- If pyproject.toml not found, warn and provide manual config
- If no modules are strict yet, encourage starting with easiest module
- If all modules strict, celebrate completion!

## Integration with Other Commands

- `/lint` - Run all linters including mypy
- `/validate` - Full validation including type checking
- `/progress-update` - Include type safety in sprint progress

## Notes

- **Gradual is better** than trying to fix everything at once
- **Test after each migration** to catch regressions early
- **Commit frequently** during migration
- **Don't use Any everywhere** - that defeats the purpose
- **Type stubs** may be needed for third-party libraries

---

**Success Criteria**:
- ✅ Current strict status displayed
- ✅ Remaining modules identified
- ✅ Migration plan with priorities
- ✅ Error breakdown and common patterns
- ✅ Detailed checklist for next module
- ✅ Commands to run for migration
