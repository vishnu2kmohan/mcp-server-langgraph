---
description: Track mypy strict type checking rollout progress. Use when monitoring type safety migration, planning next module to convert, or reviewing type error patterns.
allowed-tools:
  - Bash(uv:*)
  - Read
  - Glob
  - Grep
---
# Type Safety Status

This command has been migrated to a skill with progressive disclosure.

**Skill location**: `.claude/skills/type-safety-status/SKILL.md`

Run the skill: `/type-safety-status`

## Skill Structure

```
.claude/skills/type-safety-status/
  SKILL.md                          # Core instructions (~110 lines)
  references/
    mypy-patterns.md                # Error analysis, common type patterns, error handling
    migration-checklist.md          # Module breakdown, migration plan, checklist, success criteria
```
