# Migration Checklist & Plan

Reference material for module migration. Loaded on demand from SKILL.md.

---

## Module-by-Module Breakdown

**Strict Status by Module**:
```
===================================================================
  MYPY STRICT ROLLOUT PROGRESS
===================================================================

  Module                     Status      Errors  Complexity  Priority
  ------------------------------------------------------------------
  Core Modules (3/11 strict)
  +- core/config.py          STRICT      0       Low         done
  +- core/feature_flags.py   STRICT      0       Low         done
  +- core/agent.py           STRICT      0       Medium      done
  +- core/llm_factory.py     NOT STRICT  12      Medium      NEXT
  +- core/state.py           NOT STRICT  8       Low         high

  Auth Modules (0/4 strict)
  +- auth/middleware.py       NOT STRICT  9       Medium      high
  +- auth/jwt.py              NOT STRICT  5       Low         high
  +- auth/rbac.py             NOT STRICT  15      High        medium
  +- auth/keycloak.py         NOT STRICT  11      High        medium

  Session Modules (0/3 strict)
  +- session/store.py         NOT STRICT  7       Medium      medium
  +- session/distributed.py   NOT STRICT  18      High        low
  +- session/checkpointing.py NOT STRICT  6       Medium      low

  Tool Modules (0/8 strict)
  +- tools/catalog.py         NOT STRICT  4       Low         medium
  +- tools/calculator.py      NOT STRICT  2       Low         EASY
  +- tools/filesystem.py      NOT STRICT  8       Medium      low
  +- ... (5 more)             NOT STRICT  ~15     Varies      low

  MCP Modules (0/6 strict)
  +- mcp/stdio_server.py      NOT STRICT  10      High        low
  +- mcp/protocol.py          NOT STRICT  14      High        low
  +- ... (4 more)             NOT STRICT  ~12     Varies      low

  Observability (0/5 strict)
  +- observability/telemetry  NOT STRICT  6       Medium      low
  +- observability/logging    NOT STRICT  4       Low         EASY
  +- ... (3 more)             NOT STRICT  ~8      Varies      low

  ------------------------------------------------------------------
  TOTALS
    Strict:    3 modules (27%)
    Pending:   8 modules (73%)
    Total Errors: 154 errors across 8 modules
  ------------------------------------------------------------------
```

---

## Prioritized Migration Plan

**Recommended Migration Order** (based on complexity + impact):

```
===================================================================
  MYPY STRICT MIGRATION PLAN
===================================================================

  Sprint 1 (Week 1) - Easy Wins
  ================================================================
  Goal: Migrate 2 simple modules (+18% progress)

  1. tools/calculator.py (2 errors, 30 min)
     - Add return types to functions
     - Add parameter types
     Command: uv run --frozen mypy tools/calculator.py --strict

  2. observability/logging.py (4 errors, 45 min)
     - Annotate logger initialization
     - Type log message handling
     Command: uv run --frozen mypy observability/logging.py --strict

  Expected: 5/11 strict (45%)
  Time: ~1.5 hours

  Sprint 2 (Week 2-3) - Medium Complexity
  ================================================================
  Goal: Migrate 3 medium modules (+27% progress)

  3. core/state.py (8 errors, 1-2 hours)
     - Add types to state dataclasses
     - Type LangGraph state handling
     - Add Generic type parameters

  4. auth/jwt.py (5 errors, 1 hour)
     - Type JWT payload structure
     - Add return types to encoding/decoding

  5. session/store.py (7 errors, 1-2 hours)
     - Type Redis operations
     - Add Session type annotations

  Expected: 8/11 strict (73%)
  Time: ~4-5 hours

  Sprint 3 (Week 4-5) - Complex Modules
  ================================================================
  Goal: Migrate 3 complex modules (+27% progress)

  6. core/llm_factory.py (12 errors, 2-3 hours)
     - Type LiteLLM integration
     - Add Generic types for LLM responses
     - Handle provider-specific types

  7. auth/middleware.py (9 errors, 2 hours)
     - Type FastAPI middleware
     - Type authentication flow

  8. auth/rbac.py (15 errors, 3-4 hours)
     - Type OpenFGA integration
     - Add permission type structures

  Expected: 11/11 strict (100%)
  Time: ~8-10 hours

  ------------------------------------------------------------------
  Total Timeline: 5 sprints (~5 weeks)
  Total Time: 13-16 hours
  Success Rate: High (incremental, tested approach)
  ------------------------------------------------------------------
```

---

## Module Migration Checklist

For the next module to migrate, provide a detailed checklist.

**Example: Migrating `core/llm_factory.py`**:
```
+------------------------------------------------------------------+
| MIGRATION CHECKLIST: core/llm_factory.py                          |
+------------------------------------------------------------------+
| Current Errors: 12                                                |
| Estimated Time: 2-3 hours                                         |
| Complexity: Medium                                                |
+------------------------------------------------------------------+

Pre-Migration:
  [ ] Run mypy to get baseline errors
    Command: uv run --frozen mypy src/mcp_server_langgraph/core/llm_factory.py --strict --show-error-codes

  [ ] Backup current file (git commit)
    Command: git commit -am "Pre-mypy strict: llm_factory.py"

Step 1: Add Import for Types
  [ ] Add typing imports:
    from typing import Any, Optional, Union, Type, Generic, TypeVar

  [ ] Add third-party type stubs if needed:
    uv add --dev types-redis types-requests

Step 2: Fix Function Signatures
  [ ] Add return types to all functions
    Example: def create_llm() -> LLMFactory:

  [ ] Add parameter types
    Example: def __init__(self, provider: str, model: str) -> None:

  [ ] Handle Optional parameters
    Example: fallback: Optional[List[str]] = None

Step 3: Fix Generic Types
  [ ] Add type parameters to generic classes
    Example: class LLMFactory(Generic[T]):

  [ ] Specify LiteLLM return types
    Example: response: ChatCompletion = await llm.ainvoke(...)

Step 4: Fix Type Mismatches
  [ ] Add type assertions where needed
    Example: assert isinstance(result, AIMessage)

  [ ] Use type guards for unions
    Example: if isinstance(value, str): ...

  [ ] Handle Any types cautiously
    Try to narrow to specific types when possible

Step 5: Enable Strict Mode
  [ ] Add override to pyproject.toml:
    [[tool.mypy.overrides]]
    module = "mcp_server_langgraph.core.llm_factory"
    strict = true

  [ ] Run mypy to verify:
    uv run --frozen mypy src/mcp_server_langgraph/core/llm_factory.py --strict

Step 6: Test & Verify
  [ ] Run existing tests:
    uv run --frozen pytest tests/ -k llm_factory -v

  [ ] Verify no regressions:
    uv run --frozen pytest tests/ --cov=src/mcp_server_langgraph/core/llm_factory.py

  [ ] Check overall mypy status:
    /type-safety-status

Post-Migration:
  [ ] Commit changes:
    git commit -am "feat(types): enable strict mypy for llm_factory.py"

  [ ] Update progress tracker
  [ ] One more module strict!
```

---

## Success Criteria

- 0 mypy errors with --strict flag
- All existing tests pass
- No coverage regression
- Code more readable with types
