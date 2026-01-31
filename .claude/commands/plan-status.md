---
description: Check plan completion status with dual AI verification (Codex + Gemini)
---
# Plan Status Check with Dual AI Verification

Check the completion status of the active plan using both Codex and Gemini CLI for thorough verification,
and optionally continue working until all items are complete.

## Usage

```bash
/plan-status [plan-file-path]
```

**Arguments**:
- `plan-file-path` (optional): Path to plan file. If omitted, uses active session plan or searches `~/.claude/plans/`

**Flags**:
- `--continue`: If incomplete, continue working on plan until all items are complete
- `--summary`: Show summary only (no detailed item list)
- `--skip-ai`: Skip AI verification, use local parsing only (faster but less thorough)

## Prerequisites

Before using this command, ensure:

1. **Codex CLI is installed** (optional but recommended):
   ```bash
   npm install -g @openai/codex-cli
   codex login
   ```

2. **Gemini CLI is installed** (optional but recommended):
   ```bash
   npm install -g @google/gemini-cli
   gemini auth login
   ```

If neither CLI is installed, the command falls back to local parsing only.

## Session State Tracking

```
PLAN_STATUS_ID=""              # Unique ID for this status check session
CODEX_STATUS_SESSION_ID=""     # Codex session UUID (if used)
GEMINI_STATUS_SESSION_ID=""    # Gemini session UUID (if used)
```

**Generate unique status ID at session start**:
```bash
PLAN_STATUS_ID=$(date +%s%N)
```

## Plan Detection Priority

1. **Active session plan** (from conversation context) - auto-detected, no confirmation
2. **User-provided path argument** - use specified path
3. **Plans directory search** - requires user confirmation if multiple found

## Workflow

### Step 1: Locate Plan File

Check for active session plan in conversation context. Claude Code injects plan information
via system reminders when a plan is active:

```
A plan file exists from plan mode at: /path/to/plan.md
```

If found, use automatically. Otherwise check `$ARGUMENTS` for path, then search `~/.claude/plans/`.

### Step 2: Parse Plan for All Item Types

Scan the plan file for ALL item types:

```bash
# Unchecked TODO items [ ]
INCOMPLETE_TODOS=$(grep -c '^\s*-\s*\[ \]' "$PLAN_PATH" 2>/dev/null || echo "0")

# Checked TODO items [x] or [X]
COMPLETE_TODOS=$(grep -c '^\s*-\s*\[[xX]\]' "$PLAN_PATH" 2>/dev/null || echo "0")

# TODO:, FIXME:, WIP:, PENDING: markers
PENDING_MARKERS=$(grep -cE '(TODO:|FIXME:|WIP:|PENDING:)' "$PLAN_PATH" 2>/dev/null || echo "0")

# Optional/deferred items (still need completion)
OPTIONAL_ITEMS=$(grep -cE '(OPTIONAL:|DEFERRED:|LATER:|MAYBE:)' "$PLAN_PATH" 2>/dev/null || echo "0")

# Blocked items (need unblocking)
BLOCKED_ITEMS=$(grep -cE '(BLOCKED:|WAITING:|UNBLOCK:)' "$PLAN_PATH" 2>/dev/null || echo "0")

# Incomplete phases/steps
INCOMPLETE_PHASES=$(grep -cE '(Phase.*:.*\[ \]|Step.*:.*\[ \])' "$PLAN_PATH" 2>/dev/null || echo "0")

# Incomplete sprints/milestones
SPRINT_ITEMS=$(grep -cE '(Sprint.*:.*\[ \]|Milestone.*:.*\[ \])' "$PLAN_PATH" 2>/dev/null || echo "0")
```

### Step 3: Check Claude Code Tasks

Also check for pending tasks from TaskList:

```
# Use TaskList tool to get pending tasks
# Count tasks with status != "completed"
```

### Step 4: Calculate Completion Status

```python
total_incomplete = (
    INCOMPLETE_TODOS +
    PENDING_MARKERS +
    OPTIONAL_ITEMS +
    BLOCKED_ITEMS +
    INCOMPLETE_PHASES +
    SPRINT_ITEMS +
    pending_tasks_count
)

is_complete = (total_incomplete == 0)
completion_percentage = COMPLETE_TODOS / (COMPLETE_TODOS + INCOMPLETE_TODOS) * 100
```

### Step 5: AI Verification (Unless --skip-ai)

If `--skip-ai` is NOT set and at least one CLI is available, invoke dual AI verification.

**Execution: Use Claude's Native Background Tasks**

Run Codex and Gemini in parallel using Claude's `run_in_background=true`:
1. Launch both reviewers as separate Bash tool calls with `run_in_background=true`
2. DO NOT use shell output redirection - let stdout flow to Claude's task output
3. Use TaskOutput to retrieve results after completion

#### Codex Verification

```bash
# Uses Landlock read-only sandbox with full disk read access for ~/.claude/plans/
codex exec \
  --sandbox read-only \
  --skip-git-repo-check \
  -c 'sandbox_permissions=["disk-full-read-access"]' \
  -C "$(dirname "$PLAN_PATH")" \
  "Verify plan completion status.

File to analyze: $(basename "$PLAN_PATH")

Read the file and identify ALL incomplete items:
1. Unchecked TODOs: [ ] items
2. TODO:, FIXME:, WIP:, PENDING: markers
3. OPTIONAL:, DEFERRED:, LATER:, MAYBE: items
4. BLOCKED:, WAITING:, UNBLOCK: items
5. Incomplete Phase/Step/Sprint/Milestone items

Return JSON:
{
  \"verified\": true,
  \"incomplete_count\": <number>,
  \"incomplete_items\": [
    {\"type\": \"todo|marker|optional|blocked|phase\", \"text\": \"...\", \"line\": <number>}
  ],
  \"hidden_items\": [
    \"Items that might be missed by simple regex (e.g., in comments, code blocks)\"
  ],
  \"completion_percentage\": <0-100>,
  \"verdict\": \"complete|incomplete\"
}"
```

#### Gemini Verification

```bash
# SANDBOX_FLAGS mounts:
# 1. ADC: Required for Vertex AI auth (docker-level mount, not affected by read_file restrictions)
# 2. Plans: Mount to project subdirectory so read_file tool can access it
# NOTE: Use double quotes to allow shell expansion of $HOME and $PWD
export SANDBOX_FLAGS="-v $HOME/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json -v $HOME/.claude/plans:$PWD/.claude-plans:ro"

# Transform host path to container path (mounted inside project as .claude-plans/)
GEMINI_PLAN_PATH=$(basename "$PLAN_PATH")

# Note: Use --prompt flag (stdin pipe doesn't work reliably with run_in_background)
gemini \
  --model gemini-3-pro-preview \
  --output-format json \
  --sandbox \
  --allowed-tools run_shell_command \
  --allowed-tools read_file \
  --prompt "Verify plan completion status.

File to analyze: .claude-plans/$GEMINI_PLAN_PATH

Read the file and identify ALL incomplete items:
1. Unchecked TODOs: [ ] items
2. TODO:, FIXME:, WIP:, PENDING: markers
3. OPTIONAL:, DEFERRED:, LATER:, MAYBE: items (these COUNT as incomplete)
4. BLOCKED:, WAITING:, UNBLOCK: items (these COUNT as incomplete)
5. Incomplete Phase/Step/Sprint/Milestone items

IMPORTANT: Optional and deferred items are NOT complete until explicitly marked done.

Return JSON:
{
  \"verified\": true,
  \"incomplete_count\": <number>,
  \"incomplete_items\": [...],
  \"hidden_items\": [...],
  \"completion_percentage\": <0-100>,
  \"verdict\": \"complete|incomplete\"
}"
```

#### Reconcile AI Findings

After both reviewers complete:

1. **Parse JSON** from Codex and Gemini TaskOutput results
2. **Merge incomplete_items** lists, deduplicating by line number
3. **Merge hidden_items** - items AI found that regex missed
4. **Reconcile verdicts**:
   - If EITHER says `incomplete` → overall status is INCOMPLETE
   - If BOTH say `complete` → overall status is COMPLETE
5. **Update completion percentage** to use AI-verified count

```python
# Reconciliation logic
ai_incomplete_items = deduplicate(
    codex_result.get("incomplete_items", []) +
    gemini_result.get("incomplete_items", [])
)
hidden_items = set(
    codex_result.get("hidden_items", []) +
    gemini_result.get("hidden_items", [])
)
ai_verified = True
ai_verdict = "complete" if (
    codex_result.get("verdict") == "complete" and
    gemini_result.get("verdict") == "complete"
) else "incomplete"
```

### Step 6: Display Status

#### If 100% Complete (AI Verified):

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ✅ PLAN COMPLETE (100%) - AI VERIFIED                   ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Plan: ~/.claude/plans/feature-implementation.md         ┃
┃                                                         ┃
┃ Verification: Codex ✅ + Gemini ✅                      ┃
┃                                                         ┃
┃ All Items Complete:                                     ┃
┃   ✅ TODOs: 12/12                                       ┃
┃   ✅ Phases: 3/3                                        ┃
┃   ✅ Sprints: 2/2                                       ┃
┃   ✅ Tasks: All resolved                                ┃
┃   ✅ No pending markers (TODO/FIXME/WIP)                ┃
┃   ✅ No blocked items                                   ┃
┃   ✅ No deferred items                                  ┃
┃                                                         ┃
┃ Ready for: /code-review, /commit                        ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

#### If 100% Complete (Local Only - --skip-ai):

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ✅ PLAN COMPLETE (100%) - LOCAL PARSE                   ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Plan: ~/.claude/plans/feature-implementation.md         ┃
┃                                                         ┃
┃ ⚠️  AI verification skipped (--skip-ai)                 ┃
┃                                                         ┃
┃ All Items Complete:                                     ┃
┃   ✅ TODOs: 12/12                                       ┃
┃   ✅ Phases: 3/3                                        ┃
┃   ✅ Sprints: 2/2                                       ┃
┃   ✅ Tasks: All resolved                                ┃
┃                                                         ┃
┃ Ready for: /code-review, /commit                        ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

#### If Incomplete (AI Verified):

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ⚠️  PLAN INCOMPLETE (67%) - AI VERIFIED                  ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Plan: ~/.claude/plans/feature-implementation.md         ┃
┃                                                         ┃
┃ Verification: Codex ✅ + Gemini ✅                      ┃
┃                                                         ┃
┃ Remaining Items (8 total):                              ┃
┃                                                         ┃
┃   ❌ TODOs: 3 remaining                                 ┃
┃      - [ ] Add integration tests                        ┃
┃      - [ ] Update documentation                         ┃
┃      - [ ] Add error handling for edge case             ┃
┃                                                         ┃
┃   ❌ Tasks: 2 unresolved                                ┃
┃      - #4: Implement retry logic (in_progress)          ┃
┃      - #7: Add logging (pending)                        ┃
┃                                                         ┃
┃   ❌ Deferred: 1 item                                   ┃
┃      - DEFERRED: Add caching layer                      ┃
┃                                                         ┃
┃   ❌ Blocked: 1 item                                    ┃
┃      - BLOCKED: Waiting for API spec                    ┃
┃                                                         ┃
┃   ❌ Sprints: 1 milestone pending                       ┃
┃      - Sprint 2: Performance optimization               ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 🔍 AI-Detected Hidden Items (missed by regex):         ┃
┃   - "Need to handle edge case" in code comment (L:45)   ┃
┃   - Implicit TODO in implementation section             ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ Use --continue to work on remaining items               ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Step 7: Handle --continue Flag

If `--continue` flag is set and plan is incomplete:

1. **Display remaining items** (as above)

2. **Work through items in priority order**:
   - BLOCKED items first (need unblocking)
   - In-progress tasks (finish what's started)
   - Pending tasks
   - Remaining TODOs
   - Optional/deferred items
   - Sprint milestones

3. **For each item**:
   - Read the plan section for context
   - Implement the item
   - Mark as complete in the plan file (change `[ ]` to `[x]`)
   - Update task status if applicable

4. **Loop until complete**:
   - After each item, re-check completion status
   - Continue until 100% complete or user interrupts

5. **Final status**:
   ```
   ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
   ┃ ✅ PLAN NOW COMPLETE (100%)                             ┃
   ┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
   ┃                                                         ┃
   ┃ Items completed this session: 8                         ┃
   ┃                                                         ┃
   ┃ Ready for: /code-review, /commit                        ┃
   ┃                                                         ┃
   ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
   ```

## Return Value

The command returns a status that can be used by other commands:

- `PLAN_COMPLETE=true` - All items complete, safe to proceed
- `PLAN_COMPLETE=false` - Incomplete items remain
- `PLAN_NOT_FOUND=true` - No plan file found (proceed with caution)

## Integration with Other Commands

This command can be used alongside:
- `/code-review` - Run `/plan-status` first to verify completion before code review
- `/commit` - Run `/plan-status` to ensure all items are done before committing
- `/pr-checks` - Include plan status as part of PR validation workflow

**Note:** These commands do not auto-invoke `/plan-status` - the user decides when to check plan completion.

## Example Usage

```bash
# Check status of active plan
/plan-status

# Check specific plan file
/plan-status ~/.claude/plans/feature-x.md

# Check and continue until complete
/plan-status --continue

# Quick summary only
/plan-status --summary
```

## Example Session

```
User: /plan-status

Claude:
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ⚠️  PLAN INCOMPLETE (75%)                                ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Plan: ~/.claude/plans/purrfect-orbiting-pretzel.md      ┃
┃                                                         ┃
┃ Remaining Items (2 total):                              ┃
┃                                                         ┃
┃   ❌ TODOs: 2 remaining                                 ┃
┃      - [ ] Test /plan-review command                    ┃
┃      - [ ] Test /code-review command                    ┃
┃                                                         ┃
┃ Use --continue to work on remaining items               ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

User: /plan-status --continue

Claude: Working on remaining items...

        📝 Item 1/2: Test /plan-review command
        [Executes /plan-review and validates it works]
        ✅ Marked complete

        📝 Item 2/2: Test /code-review command
        [Executes /code-review and validates it works]
        ✅ Marked complete

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ✅ PLAN NOW COMPLETE (100%)                             ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Items completed this session: 2                         ┃
┃                                                         ┃
┃ Ready for: /code-review, /commit                        ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Session Cleanup

After status check completes, clean up session state:

```bash
# Clean up Codex session file (if used)
if [ -n "$CODEX_STATUS_SESSION_ID" ]; then
  find ~/.codex/sessions -name "*${CODEX_STATUS_SESSION_ID}*.jsonl" -delete 2>/dev/null
fi

# Clean up Gemini session file (if used)
if [ -n "$GEMINI_STATUS_SESSION_ID" ]; then
  find ~/.gemini/sessions ~/.config/gemini/sessions -name "*${GEMINI_STATUS_SESSION_ID}*" -delete 2>/dev/null
fi

# Clear session state
PLAN_STATUS_ID=""
CODEX_STATUS_SESSION_ID=""
GEMINI_STATUS_SESSION_ID=""
```

## Error Handling

### No CLIs Available

```
⚠️  No AI verification CLIs found.

Falling back to local parsing only.

To enable AI verification, install:
  npm install -g @openai/codex-cli
  npm install -g @google/gemini-cli
```

### One CLI Available

If only one CLI is available, proceed with single-reviewer verification and note it in the output:

```
Verification: Codex ✅ (Gemini unavailable)
```

or

```
Verification: Gemini ✅ (Codex unavailable)
```

### AI Timeout

```
⚠️  AI verification timed out after 60 seconds.

Falling back to local parsing results.
```

### Disagreement Between Reviewers

If Codex and Gemini disagree on completion status:

```
┃ ⚠️  VERIFICATION CONFLICT                               ┃
┃                                                         ┃
┃ Codex says: COMPLETE (100%)                             ┃
┃ Gemini says: INCOMPLETE (3 items)                       ┃
┃                                                         ┃
┃ Gemini found items Codex missed:                        ┃
┃   - DEFERRED: Add caching layer (L:45)                  ┃
┃   - OPTIONAL: Performance optimization (L:78)           ┃
┃   - WIP: Error handling section (L:112)                 ┃
┃                                                         ┃
┃ Using conservative estimate: INCOMPLETE                 ┃
```

## Models

- **Codex**: Uses defaults from `~/.codex/config.toml` (typically gpt-5.2-codex with xhigh)
- **Gemini**: Uses `gemini-3-pro-preview` via Gemini CLI

**Timeout**: 60 seconds per reviewer (both run in parallel)
