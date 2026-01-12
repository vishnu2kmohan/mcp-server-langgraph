---
description: Exploration-first session for understanding before implementing
allowed-tools: Read, Grep, Glob, Bash, Task, WebSearch, WebFetch
---

# Research Session: $ARGUMENTS

Conduct a thorough exploration of **$ARGUMENTS** before any implementation.

## Research-Then-Implement Pattern

This command enforces separation of concerns:
1. **This session**: Explore, understand, document findings
2. **Next session**: Implement based on documented understanding

## Phase 1: Exploration (This Session)

### 1. Understand the Scope

```
- What are we trying to understand?
- What files/modules are likely involved?
- What existing patterns should we follow?
```

### 2. Search and Read

Use parallel searches to find relevant code:
- Grep for related symbols, patterns
- Glob for file structure
- Read key files (batch reads)

### 3. Document Architecture

Note in findings:
- How the current system works
- Key files and their responsibilities
- Data flow and dependencies
- Existing patterns to follow

### 4. Identify Risks

- Breaking changes potential
- Test coverage gaps
- Integration points

## Phase 2: Documentation

Create a research findings document:

**File**: `.claude/research/YYYY-MM-DD-<topic>.md`

**Structure**:
```markdown
# Research: <Topic>

**Date**: YYYY-MM-DD
**Status**: Ready for Implementation

## Summary
<1-2 paragraph overview>

## Key Files
| File | Purpose |
|------|---------|
| path/to/file.py | Description |

## Current Architecture
<How it works now>

## Proposed Approach
<How we should implement>

## Risks & Mitigations
<What could go wrong>

## Implementation Checklist
- [ ] Step 1
- [ ] Step 2
- [ ] Step 3

## Questions Resolved
- Q: <question>
  A: <answer from research>

## Open Questions
- <Any remaining unknowns>
```

## Phase 3: Handoff

When research is complete:

1. Save findings to `.claude/research/`
2. Run `/checkpoint` to preserve session state
3. Inform user: "Research complete. Run `/clear` then start implementation with findings document."

## Rules for This Session

- **NO code changes** - Read only
- **NO premature solutions** - Understand first
- **Document everything** - Future session needs this
- **Ask questions** - Clarify before assuming

## Example Usage

```
/research authentication flow
/research how feature flags work
/research frontend state management
```

## When to Use

- Before major refactoring
- When entering unfamiliar code area
- Before architectural changes
- When requirements are unclear
- Before multi-day implementation work
