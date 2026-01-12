---
description: Save session state before /clear for seamless resumption
allowed-tools: Read, Write, Bash, Glob
---

# Session Checkpoint

Save current session state to enable seamless resumption after `/clear`.

## When to Use

- Before running `/clear` on a long session
- When switching to unrelated work temporarily
- End of day to preserve progress
- Before risky operations that might need rollback
- When context is getting heavy but work isn't done

## Checkpoint Contents

Generate a checkpoint file at `.claude/checkpoints/YYYY-MM-DD-HHMMSS.md`:

### 1. Session Metadata

```markdown
# Session Checkpoint

**Created**: YYYY-MM-DD HH:MM:SS
**Branch**: <current git branch>
**Session Duration**: <approximate>
**Context Level**: <estimated: low/medium/high>
```

### 2. Work Summary

```markdown
## What Was Accomplished

- <Completed item 1>
- <Completed item 2>
- <In-progress item>

## Current State

<Brief description of where things stand>
```

### 3. Key Context

```markdown
## Files Modified This Session

<List from git status>

## Key Decisions Made

- Decision 1: <rationale>
- Decision 2: <rationale>

## Important Findings

- <Discovery 1>
- <Discovery 2>
```

### 4. Resumption Guide

```markdown
## To Resume This Work

1. Run `/clear` (if not done)
2. Read this checkpoint file
3. Read these key files:
   - <file1>
   - <file2>
4. Continue with: <next step>

## Next Steps (Priority Order)

1. [ ] <Immediate next action>
2. [ ] <Following action>
3. [ ] <Cleanup/polish>

## Open Questions

- <Question needing resolution>

## Blockers

- <Any blocking issues>
```

## Execution Steps

1. **Capture git state**:
```bash
git status --short
git diff --stat
git log --oneline -5
```

2. **Check for uncommitted work**:
```bash
git diff --name-only
```

3. **Generate timestamp**:
```bash
date +"%Y-%m-%d-%H%M%S"
```

4. **Write checkpoint file** to `.claude/checkpoints/`

5. **Confirm with user**:
```
Checkpoint saved to: .claude/checkpoints/YYYY-MM-DD-HHMMSS.md

Safe to run /clear. To resume:
1. /clear
2. Read the checkpoint file
3. Continue from "Next Steps"
```

## Checkpoint File Lifecycle

- **Create**: When running `/checkpoint`
- **Use**: After `/clear`, read to restore context
- **Archive**: After work is complete, can be deleted or kept for reference
- **Cleanup**: Periodically remove old checkpoints (>7 days)

## Quick Checkpoint (Minimal)

For a fast checkpoint when in a hurry:

```markdown
# Quick Checkpoint - YYYY-MM-DD HH:MM

Branch: <branch>
Working on: <one-liner>
Next: <immediate next step>
Files: <key files>
```

## Integration with /catchup

After `/clear`, the resumption flow is:

```
/clear
→ Read .claude/checkpoints/<latest>.md
→ /catchup (for git context)
→ Continue work
```
