---
purpose: Progressive disclosure architecture for context efficiency
priority: medium
category: efficiency
last-updated: 2026-02-07
---

# Progressive Disclosure for Context Efficiency

## Three-Layer Architecture

| Layer | Budget | Content | Loading |
|-------|--------|---------|---------|
| L1 | ~500 tokens | `CLAUDE.md` | Every turn |
| L2 | ~500/file | `memory/*.md` | On demand |
| L3 | Unlimited | `skills/*/references/` | When needed |

### Layer 1: Always-Loaded (CLAUDE.md)

- Quick start essentials only
- References to deeper docs
- Version index
- Quick commands
- Project structure overview

**Target**: 8KB compressed = 100% pass rate

### Layer 2: On-Demand (memory/)

- Reference documentation
- Patterns and anti-patterns
- Tool selection guides
- Decision trees

**Loading**: Read when relevant to task

### Layer 3: Deep Reference (references/)

- Full API documentation
- Schema definitions
- Examples and templates
- Historical context

**Loading**: Only when explicitly needed

---

## lib/ Directory (Zero Cost)

Shell utilities in `.claude/lib/` are **sourced at runtime** = 0 context tokens.

```bash
# Zero context cost - sourced when executed
source .claude/lib/test_utils.sh
run_pytest_parallel "unit"

source .claude/lib/bulk_edit_utils.sh
rename_symbol "OldClass" "NewClass" py
```

### Available Utilities

| File | Functions |
|------|-----------|
| `test_utils.sh` | `run_pytest_parallel`, `run_npm_test_parallel`, `run_unit_tests` |
| `bulk_edit_utils.sh` | `rename_symbol`, `update_imports`, `bulk_replace` |

---

## Key Metrics

| Metric | Target | Anti-Pattern |
|--------|--------|--------------|
| CLAUDE.md size | < 8KB | 40KB bloated monolith |
| Rule files | < 200 lines each | Giant rule files |
| Memory access | Read when needed | Always loading everything |
| lib/ usage | Source at runtime | Inline shell functions |

---

## Placement Guidelines

| Content Type | Location | Example |
|--------------|----------|---------|
| Always needed | `CLAUDE.md` | Quick commands |
| Imperative (MUST/NEVER) | `rules/` | Test parallelism, env vars |
| Reference (how-to) | `memory/` | Tool patterns, anti-patterns |
| Deep detail | `references/` | Full API docs, schemas |
| Runtime utilities | `lib/` | Shell functions |

---

## Rule of Thumb

> If content isn't needed 80%+ of sessions, it belongs in `memory/` or `references/`, not `rules/`.

---

## Context Optimization Checklist

1. **Check size**: Is CLAUDE.md under 8KB?
2. **Check rules**: Are rules imperative, not reference?
3. **Check memory**: Is memory read-on-demand?
4. **Check lib**: Are utilities runtime-sourced?
5. **Check duplication**: Is content duplicated across layers?

---

**Key Insight**: 8KB compressed docs = 100% pass rate vs 40KB bloat with failures.
