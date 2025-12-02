---
description: Manage and cleanup git worktrees created for Claude Code sessions.
---
# Cleanup Git Worktrees

**Purpose**: Manage and cleanup git worktrees created for Claude Code sessions.

**When to use**: After ending a Claude Code session to clean up old worktrees.

---

## Instructions

You are helping the user cleanup git worktrees created by the `start-worktree-session.sh` script.

### Phase 1: List Worktrees

1. Run the cleanup script in dry-run mode to show what would be deleted:
   ```bash
   ./scripts/cleanup-worktrees.sh --dry-run
   ```

2. Show the user:
   - Total number of worktrees
   - How many are clean (no uncommitted changes)
   - How many are dirty (have uncommitted changes)
   - Details about each worktree (branch, commit, creation date)

### Phase 2: Ask User Preference

Ask the user how they want to proceed:
- **Option 1**: Delete all clean worktrees automatically
- **Option 2**: Interactively choose which worktrees to delete
- **Option 3**: Delete ALL worktrees (even with uncommitted changes) - DANGEROUS!
- **Option 4**: Keep all worktrees (no deletion)

### Phase 3: Execute Cleanup

Based on user's choice:

**Option 1 - Auto-delete clean**:
```bash
./scripts/cleanup-worktrees.sh --auto
```

**Option 2 - Interactive**:
```bash
./scripts/cleanup-worktrees.sh
```

**Option 3 - Delete all (DANGEROUS)**:
```bash
./scripts/cleanup-worktrees.sh --all --auto
```

**Option 4 - No deletion**:
Skip execution and inform user that worktrees are preserved.

### Phase 4: Summary

After cleanup, show:
- Number of worktrees deleted
- Number of worktrees kept
- Remaining worktrees (if any)
- Disk space reclaimed (optional)

---

## Important Notes

1. **Clean worktrees**: No uncommitted changes, safe to delete
2. **Dirty worktrees**: Have uncommitted changes, should preserve unless user explicitly requests deletion
3. **Session worktrees**: Only manages worktrees created by `start-worktree-session.sh` (matching pattern `mcp-server-langgraph-session-*`)
4. **Main repository**: Never deletes the main repository

---

## Examples

**Example 1: User wants to cleanup after ending session**
```
User: Cleanup my worktrees
Assistant: I'll check your worktrees and show what can be cleaned up.
[Runs: ./scripts/cleanup-worktrees.sh --dry-run]
[Shows: 3 clean worktrees, 1 dirty worktree]
[Asks: How would you like to proceed?]
[User chooses: Auto-delete clean worktrees]
[Runs: ./scripts/cleanup-worktrees.sh --auto]
[Shows: Deleted 3 worktrees, kept 1 dirty worktree]
```

**Example 2: User wants to review before deleting**
```
User: /cleanup-worktrees
Assistant: Let me show you the current worktrees...
[Runs: ./scripts/cleanup-worktrees.sh --dry-run]
[Shows worktree details]
[Asks: Would you like to interactively choose which to delete?]
[User: Yes]
[Runs: ./scripts/cleanup-worktrees.sh]
[Script prompts for each worktree, user decides]
```

---

## Safety

- Always run `--dry-run` first to show user what would be deleted
- Warn user before deleting dirty worktrees (uncommitted changes)
- Confirm before using `--all` flag (dangerous operation)
- Preserve worktrees by default unless user explicitly requests deletion

---

## Troubleshooting

**Issue**: Script can't delete a worktree
- **Cause**: Worktree may be locked or in use
- **Solution**:
  ```bash
  git worktree unlock /path/to/worktree
  ./scripts/cleanup-worktrees.sh --auto
  ```

**Issue**: Worktree has uncommitted changes but user wants to delete
- **Cause**: User needs to commit or discard changes first
- **Options**:
  1. Navigate to worktree and commit changes
  2. Use `--all` flag to force delete (loses changes!)

**Issue**: Can't find worktrees directory
- **Cause**: No worktrees have been created yet
- **Solution**: Normal - nothing to cleanup

---

**Last Updated**: 2025-11-15
