# Context Efficiency Patterns

**Purpose**: Minimize redundant reads, maximize context utilization
**Last Updated**: 2025-01-10

---

## Core Principle

**Context is expensive. Never read the same information twice.**

---

## File Reading Strategy

### Batch Reads at Session Start

When starting work on a feature/bug:

```
# In a SINGLE message, read all likely-relevant files:
Read src/module/main.py
Read src/module/types.py
Read tests/unit/module/test_main.py
Read docs/module.md
# All execute in parallel - ~1 second total vs ~4 seconds sequential
```

### Anticipatory Reading

Before making changes, read:
1. The file to change
2. Its test file
3. Files that import from it (use Grep first)
4. Type definitions it uses

### Never Re-Read

- If you read a file 50 lines ago, you have it in context
- If user pastes content, you have it - don't Read to "verify"
- Use mental notes: "File X contains Y pattern at line ~Z"

---

## Search Strategy

### One Search, Multiple Patterns

```bash
# BAD: Three separate searches
rg "pattern1" --type py
rg "pattern2" --type py
rg "pattern3" --type py

# GOOD: Combined pattern
rg "(pattern1|pattern2|pattern3)" --type py
```

### Search Then Read

```
# GOOD: Find files first, then batch read
Grep "ClassName" -> returns file1.py:10, file2.py:25

# Then read both files in parallel
Read file1.py
Read file2.py
```

### Use Glob for Structure, Grep for Content

```
# Find all test files (structure)
Glob tests/**/*test*.py

# Find files containing a pattern (content)
Grep "async def test_" --type py
```

---

## Context Preservation

### Mental Indexing

After reading files, mentally note:
- "Feature flags defined in core/feature_flags.py, ~175 flags"
- "API routes in api/v1/*.py, routers registered in main.py"
- "Test fixtures in conftest.py at tests/ and tests/unit/ levels"

### Avoid Context Thrash

Don't:
- Read a file, switch to unrelated task, read same file again
- Use `/clear` in middle of multi-file change
- Start new exploration without completing current task

Do:
- Complete one logical unit of work before context switch
- Use TodoWrite to track where you are
- Batch related reads together

---

## Exploration Efficiency

### Use Task/Explore for Unknown Territory

When you don't know the codebase structure:
```
Task(subagent_type="Explore", prompt="Find where authentication is implemented")
```

The Explore agent can do multiple searches without burning main context.

### Direct Search for Known Patterns

When you know what you're looking for:
```
# Direct Grep - don't spawn agent
Grep "class AuthMiddleware" --type py
```

---

## Information Density

### Ask for Summaries When Appropriate

For large config files or logs:
```
Read file.json
# Then: "The config has 3 main sections: auth, database, features..."
```

Don't dump entire file contents back to user.

### Compress Findings

Instead of quoting 50 lines, summarize:
```
# BAD:
"Lines 1-50 contain: [paste 50 lines]"

# GOOD:
"The function at lines 12-45 validates input, calls external API,
caches result. Key logic at line 28: if cache_hit: return cached."
```

---

## Common Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Reading same file twice in conversation | Check context first |
| Sequential reads of related files | Parallel Read calls |
| Searching, then searching again with slight variation | Combine patterns |
| Reading entire file when you need 5 lines | Use offset/limit, or just note the lines |
| Spawning Explore agent for simple lookups | Direct Grep/Glob |
| Re-reading after user confirms information | Trust the confirmation |

---

## Context Budget Awareness

Each session has ~175k tokens of context. Budget wisely:

| Content Type | Approximate Tokens |
|--------------|-------------------|
| 100 lines of code | ~400 tokens |
| Full Python file (~500 lines) | ~2,000 tokens |
| Large config file | ~1,000-5,000 tokens |
| Test file | ~800-1,500 tokens |

**Rule of thumb**: You can hold ~50-80 files worth of content before context pressure.

---

## Refresh Strategy

### When Context Is Stale

After significant time or `/clear`:
1. Re-read `.claude/context/recent-work.md` (auto-updated)
2. Check git status for current state
3. Read TodoWrite state to resume

### What NOT to Re-Read

- CLAUDE.md (it's in system prompt)
- Memory files (they're stable reference)
- Files unchanged since last read

---

**Remember**: Every Read costs tokens. Batch reads, avoid duplicates, preserve context.
