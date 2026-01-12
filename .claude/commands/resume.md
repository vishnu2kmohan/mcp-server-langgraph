---
description: Resume work from latest checkpoint after /clear
allowed-tools: Read, Glob, Bash
---

# Resume Session

Quickly restore context after `/clear` by reading the latest checkpoint.

## Steps

1. **Find latest checkpoint**:
```bash
ls -t .claude/checkpoints/*.md 2>/dev/null | head -1
```

2. **Read checkpoint** (if exists):
- Parse the checkpoint file
- Extract "Next Steps" section
- Identify key files to read

3. **Read key files** (parallel):
- Files listed in checkpoint
- Maximum 5 files for efficiency

4. **Run catchup** for git context:
```bash
git status
git log --oneline -5
git diff --stat
```

5. **Present summary**:
```
Resumed from checkpoint: <filename>
Branch: <branch>
Last working on: <summary>
Next steps:
1. <step 1>
2. <step 2>
Ready to continue.
```

## If No Checkpoint Found

Fall back to basic catchup:
- Read recent-work.md
- Show git status
- Prompt user for task context

## Usage

After `/clear`:
```
/resume
```

This is equivalent to:
```
Read .claude/checkpoints/<latest>.md
/catchup
```

## Checkpoint Cleanup

Offer to clean old checkpoints if >5 exist:
```
Found 8 checkpoints. Delete checkpoints older than 7 days? (y/n)
```
