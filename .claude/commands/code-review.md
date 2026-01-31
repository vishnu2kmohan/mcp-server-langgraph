---
description: Review code changes with dual AI reviewers (Codex + Gemini) and apply fixes before commit
---
# Code Review with Dual AI Reviewers

Get external AI review of code changes using OpenAI Codex and Google Gemini CLI, then fix issues with clarifying questions before committing.

## Usage

```bash
/code-review [scope]
```

**Scopes**:
- `staged` (default): Only staged changes (`git diff --staged`)
- `all`: All uncommitted changes (`git diff HEAD`)
- `branch`: All changes vs base branch (`git diff main...HEAD`)

**Flags**:
- `--auto-fix`: Automatically apply all fixes (power user mode)

## Prerequisites

Before using this command, ensure:

1. **Codex CLI is installed**:
   ```bash
   npm install -g @openai/codex-cli
   ```

2. **Gemini CLI is installed**:
   ```bash
   npm install -g @google/gemini-cli
   ```

3. **User is authenticated**:
   ```bash
   codex login
   gemini auth login
   ```

## Session State Tracking

Track reviewer sessions across review rounds for context preservation:

```
CODE_REVIEW_ID=""                     # Unique ID for this review session (generated at start)
CODEX_REVIEW_SESSION_ID=""           # Current Codex session UUID
GEMINI_REVIEW_SESSION_ID=""           # Current Gemini session UUID
REVIEW_ROUND=1                 # Current iteration number
ADDRESSED_FINDINGS=[]          # Findings addressed in previous rounds
SKIP_REMAINING_CLARIFICATIONS=false  # Set true after user selects "apply all"
```

**Generate unique review ID at session start** (before invoking reviewers):
```bash
# Generate unique ID for this review session (avoids temp file conflicts)
CODE_REVIEW_ID=$(date +%s%N)  # Nanosecond timestamp, or use: $(uuidgen)
```

**Temp file naming** (session-specific to avoid conflicts):
```
/tmp/codex_code_review_${CODE_REVIEW_ID}.json
/tmp/gemini_code_review_${CODE_REVIEW_ID}.json
```

## Dual-Reviewer Configuration

Use both Codex and Gemini CLI for comprehensive code analysis:

| Reviewer | Model | Strengths |
|----------|-------|-----------|
| Codex | gpt-5.2-codex | Deep code reasoning, precise fixes |
| Gemini | gemini-3-pro-preview | Broad context (1M tokens), alternative perspectives |

### Security Settings (Read-Only Mode)

Both reviewers run with minimal permissions - they can read files freely but cannot modify them:

| Reviewer | Sandbox Mode | Read Operations | Write Operations |
|----------|--------------|-----------------|------------------|
| Codex | `--sandbox read-only` + `disk-full-read-access` | All reads allowed (Landlock enforced) | Blocked by Landlock |
| Gemini | `--sandbox` + `--allowed-tools` | read_file + run_shell_command (no confirmation) | Blocked by Docker |

**Note**: Codex `--sandbox read-only` requires Landlock kernel support (Linux 5.13+). The `disk-full-read-access`
permission allows Codex to read files from any path including `~/.claude/plans/`.

**Key security features:**
- **Read access**: Both reviewers can read files freely within sandbox constraints
- **Write blocked**: All write operations are blocked at OS/container level
- **No YOLO mode**: Gemini uses `--allowed-tools` (specific tools) not `--yolo` (all tools)
- **File path references**: File list passed in prompts, reviewers run git diff directly
- **Isolated execution**: Gemini runs in Docker container, Codex uses Landlock sandbox
- **No network access**: Network disabled by default in both CLIs
- **ADC mounting**: Gemini sandbox mounts ADC credentials via `SANDBOX_FLAGS` for Vertex AI auth
- **Plans directory**: `~/.claude/plans/` mounted read-only in Gemini sandbox for plan validation

### Clarification Rules

**ASK CLARIFICATION** when ALL of:
- Severity is "critical" or "important"
- Finding category is: security, bug, performance, or error_handling
- `--auto-fix` flag is NOT set
- `SKIP_REMAINING_CLARIFICATIONS` is false

**SKIP CLARIFICATION** when ANY of:
- Severity is "suggestion"
- Finding is trivial (single-line fix, obvious correction)
- Category is "quality" or "testing" (lower stakes)
- `--auto-fix` flag is set
- User previously chose "Apply all remaining without asking"

### Clarification Question Templates (Code Review)

| Category | Question | Options |
|----------|----------|---------|
| security | "How should this vulnerability be mitigated?" | Parameterized query, ORM/Query builder, Input validation, Let me specify... |
| bug | "How should this error case be handled?" | Throw exception, Return default value, Log and continue, Let me specify... |
| performance | "Which optimization approach?" | Add caching, Lazy loading, Optimize query, Let me specify... |
| error_handling | "What behavior on failure?" | Raise custom exception, Return None/empty, Retry with backoff, Let me specify... |

## Workflow

#### 0.5: Check Task List (Claude Code Tasks)

Also verify no outstanding tasks from TodoWrite/TaskCreate:

```bash
# Check if TaskList has pending items
# This is done programmatically within Claude Code
```

If tasks exist, display:

```
Claude Code Tasks:
  ✅ Task 1: Implement feature X (completed)
  ⚠️  Task 2: Add unit tests (in_progress)
  ❌ Task 3: Update README (pending)

2 tasks incomplete. Address before code review?
```

### Step 1: Determine Scope

Parse the argument `$ARGUMENTS` to determine review scope:

| Argument | Git Command | Description |
|----------|-------------|-------------|
| `staged` or empty | `git diff --staged` | Only staged changes |
| `all` | `git diff HEAD` | All uncommitted changes |
| `branch` | `git diff main...HEAD` | All changes on current branch |

### Step 2: Gather Changes

```bash
# Get diff based on scope
git diff --staged                    # staged
git diff HEAD                        # all
git diff main...HEAD                 # branch

# Get file list for context
git diff --staged --name-only        # staged files
git diff HEAD --name-only            # all modified files
git diff main...HEAD --name-only     # branch files
```

If no changes found:
```
No changes found for scope '[scope]'.

Try:
  • /code-review all       - Review all uncommitted changes
  • /code-review branch    - Review all changes on branch
  • git add <file>         - Stage changes first
```

### Step 3: Verify Reviewer CLIs

```bash
# Check Codex CLI
which codex || echo "ERROR: Codex CLI not found. Install with: npm install -g @openai/codex-cli"

# Check Gemini CLI
which gemini || echo "ERROR: Gemini CLI not found. Install with: npm install -g @google/gemini-cli"
```

If either is not installed, provide installation instructions. Both reviewers are recommended but the workflow can proceed with just one.

### Step 4: Invoke Dual-Reviewer Analysis

Send the diff to both Codex and Gemini CLI in parallel for comprehensive analysis.

**Execution: Use Claude's Native Background Tasks**

Run Codex and Gemini in parallel using Claude's `run_in_background=true`:

1. **Launch both reviewers** as separate Bash tool calls with `run_in_background=true`
2. **DO NOT** use shell output redirection (`>` or `| tee`) - let stdout flow to Claude's task output
3. **Use TaskOutput** to retrieve results after completion

```
# Parallel execution pattern:
Bash(run_in_background=true): codex exec ... "prompt"  → task_id: abc123
Bash(run_in_background=true): gemini ... "prompt"      → task_id: def456

# Then retrieve results:
TaskOutput(task_id="abc123") → Codex review JSON
TaskOutput(task_id="def456") → Gemini review JSON
```

**Note**: The bash examples below show the commands WITHOUT shell redirection. The `&` and `wait`
are retained for documentation but should be omitted when using `run_in_background=true`.

#### Round 1: Initial Review (New Sessions)

Run both reviewers in parallel for efficiency:

```bash
# Get file list and stats (context-efficient)
CHANGED_FILES=$(git diff --staged --name-only | tr '\n' ' ')
DIFF_STAT=$(git diff --staged --stat | tail -1)

# Detect active plan file for context (use most recent if no active session plan)
# Claude injects active plan via system reminder: "A plan file exists from plan mode at: /path/to/plan.md"
# If not found, use most recently modified plan in ~/.claude/plans/
PLAN_PATH=$(ls -t ~/.claude/plans/*.md 2>/dev/null | head -1)
PLAN_NAME=$(basename "$PLAN_PATH" 2>/dev/null || echo "none")

# Codex review (background)
# Best practices: Autonomous, action-biased, direct instructions
# Reference: https://developers.openai.com/codex/security/
# Uses Landlock read-only sandbox with full disk read access for ~/.claude/plans/
codex exec \
  --sandbox read-only \
  --skip-git-repo-check \
  -c 'sandbox_permissions=["disk-full-read-access"]' \
  -C "$(pwd)" \
  "Review staged changes for code quality.

Changed files: $CHANGED_FILES
Stats: $DIFF_STAT
Plan context: $PLAN_PATH

First, read the plan file to understand what these changes are meant to accomplish. Then run 'git diff --staged' to view the actual changes.

Analyze for: bugs, security (OWASP Top 10), performance (N+1, memory leaks), quality, type safety, missing tests. Verify changes align with the plan. Provide exact file:line references.

<output_schema>
{
  \"findings\": [{\"severity\": \"critical|important|suggestion\", \"category\": \"bug|security|performance|quality|testing\", \"file\": \"string\", \"line\": number, \"description\": \"string\", \"current_code\": \"string\", \"suggestion\": \"string\", \"fixed_code\": \"string\"}],
  \"summary\": \"string\",
  \"verdict\": \"approve|request_changes\"
}
</output_schema>

Return valid JSON only."
# When using run_in_background=true, output goes to TaskOutput - no file redirection needed

# Gemini review (background)
# Best practices: Direct, concise, context-then-question structure
# Reference: https://geminicli.com/docs/cli/sandbox/
# Mode: Docker sandbox (writes blocked by container)
# Tools: read_file + run_shell_command allowed without confirmation
# Context-efficient: Pass file list, let Gemini run git diff itself
# SANDBOX_FLAGS mounts:
# 1. ADC: Required for Vertex AI auth (docker-level mount, not affected by read_file restrictions)
# 2. Plans: Mount to project subdirectory for consistency with plan-status/plan-review
# NOTE: Use double quotes to allow shell expansion of $HOME and $PWD
export SANDBOX_FLAGS="-v $HOME/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json -v $HOME/.claude/plans:$PWD/.claude-plans:ro"
# Note: Use repeated --allowed-tools flags (space-separated array causes parsing issues)
# Note: Use --prompt flag (stdin pipe doesn't work reliably with run_in_background)
gemini \
  --model gemini-3-pro-preview \
  --output-format json \
  --sandbox \
  --allowed-tools run_shell_command \
  --allowed-tools read_file \
  --prompt "Review staged changes for code quality.

Changed files: $CHANGED_FILES
Stats: $DIFF_STAT
Plan context: .claude-plans/$PLAN_NAME

First, read the plan file at .claude-plans/$PLAN_NAME to understand what these changes are meant to accomplish. Then run 'git diff --staged' to view the actual changes.

Analyze for: bugs, security issues (OWASP Top 10), performance problems, quality issues, missing tests. Verify changes align with the plan. Provide exact file:line references.

Return as JSON: {\"findings\": [{\"severity\": \"critical|important|suggestion\", \"category\": \"bug|security|performance|quality|testing\", \"file\": \"string\", \"line\": number, \"description\": \"string\", \"current_code\": \"string\", \"suggestion\": \"string\", \"fixed_code\": \"string\"}], \"summary\": \"string\", \"verdict\": \"approve|request_changes\"}"
# When using run_in_background=true, output goes to TaskOutput - no file redirection needed

# Note: When using Claude's run_in_background=true, use TaskOutput to retrieve results
# The GEMINI_PID and wait commands are only needed for shell-level parallelism
```

After the initial review, capture the Codex session ID for subsequent rounds:

```bash
# Capture session ID from most recent Codex session
CODEX_REVIEW_SESSION_ID=$(ls -t ~/.codex/sessions/$(date +%Y)/*/*/*.jsonl 2>/dev/null | head -1 | xargs -I{} basename {} .jsonl | grep -oP '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' | head -1)

# Capture session ID from most recent Gemini session
GEMINI_REVIEW_SESSION_ID=$(ls -t ~/.gemini/sessions/*.json ~/.config/gemini/sessions/*.json 2>/dev/null | head -1 | xargs -I{} basename {} .json | grep -oP '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' | head -1)
```

#### Round 2+: Resume Existing Sessions

For subsequent review rounds, resume existing sessions for both Codex and Gemini to preserve context:

```bash
# Resume Codex session
codex exec resume $CODEX_REVIEW_SESSION_ID "Round [N]: Verify fixes from previous review.

IMPORTANT: Your entire response must be valid JSON only, no other text.

Previously addressed findings:
[List of findings that were fixed in the last round]

Re-analyze the updated diff and identify:
1. Whether previous issues are properly resolved
2. Any new issues or regressions introduced by the fixes
3. Remaining concerns not yet addressed

Return the same JSON structure:
{
  \"findings\": [...],
  \"summary\": \"Overall assessment of changes\",
  \"verdict\": \"approve|request_changes\"
}

Updated diff:

$(git diff --staged)"

# Resume Gemini session (--resume <UUID> loads previous context)
gemini \
  --resume $GEMINI_REVIEW_SESSION_ID \
  --model gemini-3-pro-preview \
  --output-format json \
  --sandbox \
  --allowed-tools run_shell_command \
  --allowed-tools read_file \
  --prompt "Round [N]: Verify fixes from previous review.

Re-analyze the updated diff (run 'git diff --staged') and verify previous issues are resolved.

Return JSON: {\"findings\": [...], \"summary\": \"...\", \"verdict\": \"approve|request_changes\"}"
```

**Benefits of dual-reviewer session persistence**:
- Both Codex and Gemini preserve full context across review rounds
- Reviewers remember previous findings and can verify fixes
- No need to re-explain the codebase or plan context

**Benefits of dual-reviewer approach**:
- Codex: Deep code reasoning, precise fixes, session persistence
- Gemini: Broad context (1M tokens), alternative perspectives
- Cross-validation reduces false negatives
- Different model architectures catch different issues

### Step 5: Reconcile Findings

After both reviewers complete, merge and deduplicate their findings:

#### Finding Reconciliation Logic

1. **Parse JSON** from both `/tmp/codex_code_review_${CODE_REVIEW_ID}.json` and `/tmp/gemini_code_review_${CODE_REVIEW_ID}.json`

2. **Deduplicate findings** by comparing:
   - Same file + same line + similar description = merge into single finding
   - Keep higher severity when merging (critical > important > suggestion)

3. **Tag each finding** with source:
   - `[Both]` - Both reviewers identified this issue
   - `[Codex]` - Only Codex identified this
   - `[Gemini]` - Only Gemini identified this

4. **Sort by severity** (critical first, then important, then suggestion)

5. **Reconcile verdicts**:
   - If either says `request_changes` → overall verdict is `REQUEST_CHANGES`
   - If both say `approve` → overall verdict is `APPROVED`

#### Handling Disagreements

When reviewers suggest different fixes for the same finding:
- Display both suggestions in the clarification question
- Include "Codex suggests: X" and "Gemini suggests: Y" as separate options
- Let user choose or provide custom approach

### Step 6: Parse and Display Results

Display reconciled findings in a structured format with source attribution:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🤖 DUAL REVIEW: CODEX + GEMINI                          ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Reviewers: Codex (gpt-5.2-codex) + Gemini (gemini-3-pro-preview)
┃ Scope: [staged/all/branch]                              ┃
┃ Files: [N] files, +[X]/-[Y] lines                       ┃
┃ Findings: [N] total ([X] both, [Y] Codex, [Z] Gemini)   ┃
┃ Verdict: [APPROVED / REQUEST_CHANGES]                   ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 🔴 CRITICAL                                             ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 1. [Both] 🔒 Security: SQL Injection                    ┃
┃    📁 src/api/users.py:47                               ┃
┃    Codex: Use parameterized query                       ┃
┃    Gemini: Use ORM or prepared statement                ┃
┃                                                         ┃
┃ 2. [Gemini] 🐛 Bug: Missing null check                  ┃
┃    📁 src/utils/parse.py:23                             ┃
┃    Fix: Check response.data is not None first           ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ ⚠️  IMPORTANT                                            ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 3. [Codex] ⚡ Performance: N+1 query pattern             ┃
┃    📁 src/api/orders.py:89                              ┃
┃    Fix: Use prefetch_related for eager loading          ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 💡 SUGGESTIONS                                          ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ [Suggestions with source tags...]                       ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Source tag meanings**:
- `[Both]` - High confidence: both reviewers identified this issue
- `[Codex]` - Codex-only finding (may be more code-specific)
- `[Gemini]` - Gemini-only finding (may be more context-aware)

### Step 7: Prompt for Action

```
Address findings?
  [A] All findings (Recommended)
  [C] Critical only
  [P] Pick specific findings
  [S] Skip review
```

### Step 8: Apply Fixes with Clarification

For each finding to address:

1. **Display finding details**:
   ```
   📝 Finding [N]/[Total]: [Description]
      📁 [path/to/file.py:line]
      Severity: [🔴 Critical / ⚠️  Important / 💡 Suggestion]
      Category: [Category]
      Source: [Both / Codex / Gemini]
   ```

2. **Ask clarification if needed** (see Clarification Rules above):

   For findings where both reviewers suggest different fixes:
   ```
   ❓ How should this vulnerability be mitigated?
     [1] [Codex fix description] (Codex)
     [2] [Gemini fix description] (Gemini)
     [3] Combine both approaches
     [4] Let me specify...

   Your choice:
   ```

   For single-reviewer findings needing clarification:
   ```
   ❓ [Category-specific question from templates]
     [1] [Option 1] (Recommended)
     [2] [Option 2]
     [3] [Option 3]
     [4] Let me specify...

   Your choice:
   ```

3. **Read the affected file**:
   ```bash
   # Read file to get full context around the line
   ```

4. **Show before/after based on chosen approach**:
   ```
   📝 Fixing finding [N]/[Total]: [Description]
   Using: [Chosen approach description]

   File: [path/to/file.py:line]

   Before:
   │ [current code with context]

   After:
   │ [fixed code with context]
   ```

5. **Get approval** (unless `--auto-fix`):
   ```
   Apply this fix? [Y/n/a]
     Y = Yes, apply this fix
     n = No, skip this finding
     a = Apply all remaining fixes with default approaches
   ```

   If user selects `a`:
   - Set `SKIP_REMAINING_CLARIFICATIONS = true`
   - Apply default approach for all remaining findings
   - Show what's being applied but don't wait for individual approval

6. **Apply fix**:
   - Use Edit tool to modify the file
   - Track applied vs skipped fixes

#### Example Clarification Flow

```
📝 Finding 1/3: SQL Injection vulnerability
   📁 src/api/users.py:47
   Severity: 🔴 Critical
   Category: security
   Source: [Both]

   Current: query = f"SELECT * FROM users WHERE id = {user_id}"

   Codex suggests: Use parameterized query with cursor.execute()
   Gemini suggests: Use SQLAlchemy ORM query builder

   ❓ How should this vulnerability be mitigated?
     [1] Parameterized query with cursor.execute() (Codex - Recommended)
     [2] SQLAlchemy ORM query builder (Gemini)
     [3] Add input validation + sanitization
     [4] Let me specify...

User: 1

Claude: Using parameterized query approach.

        Before:
        │ 45 │ def get_user(user_id: str):
        │ 46 │     conn = get_db_connection()
        │ 47 │     query = f"SELECT * FROM users WHERE id = {user_id}"
        │ 48 │     cursor.execute(query)

        After:
        │ 45 │ def get_user(user_id: str):
        │ 46 │     conn = get_db_connection()
        │ 47 │     query = "SELECT * FROM users WHERE id = %s"
        │ 48 │     cursor.execute(query, (user_id,))

        Apply this fix? [Y/n/a]

User: Y

Claude: ✅ Fix applied.

📝 Finding 2/3: Missing null check
   📁 src/utils/parse.py:23
   Severity: ⚠️  Important
   Category: bug
   Source: [Gemini]

   ❓ How should this error case be handled?
     [1] Return empty list/dict (Recommended)
     [2] Raise ValueError with message
     [3] Log warning and return None
     [4] Let me specify...

User: a  (apply all remaining)

Claude: ✅ Applying all remaining fixes with default approaches...

        Finding 2/3: Using "Return empty list" approach
        ✅ Applied to src/utils/parse.py:23

        Finding 3/3: Suggestion - skipped (non-critical)
```

### Step 9: Re-review (Optional)

After applying fixes, offer verification:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Round [N] complete. [X] fixes applied.
Session: [CODEX_REVIEW_SESSION_ID] (context preserved)

Re-run Codex review to verify?
  [Y] Yes, verify fixes (Recommended)
  [N] No, ready to proceed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If user chooses to re-run:
1. Increment `REVIEW_ROUND`
2. Add fixed findings to `ADDRESSED_FINDINGS` list
3. Use `codex exec resume $CODEX_REVIEW_SESSION_ID` (see Step 4, Round 2+)
4. This preserves full context from previous rounds

If new issues are introduced by fixes (regression), flag them and continue iterating.

**Session fallback**: If session is not found or too old, fall back to creating a new session with a summary of previous rounds in the prompt.

### Step 10: Completion Summary and Session Cleanup

**MANDATORY**: This step MUST run before exiting the review workflow. Cleanup is triggered when ANY of:
- User chooses "No" to re-review in Step 9
- User chooses "Skip review" in Step 7
- All findings have been addressed
- Review workflow completes for any reason

After the review is complete (user satisfied or all critical findings resolved), clean up both Codex and Gemini sessions:

```bash
# Clean up Codex session file to free disk space (specific session only)
if [ -n "$CODEX_REVIEW_SESSION_ID" ]; then
  find ~/.codex/sessions -name "*${CODEX_REVIEW_SESSION_ID}*.jsonl" -delete 2>/dev/null
fi

# Clean up Gemini CLI session file (specific session only)
# Gemini session ID is captured at review start alongside Codex
if [ -n "$GEMINI_REVIEW_SESSION_ID" ]; then
  find ~/.gemini/sessions -name "*${GEMINI_REVIEW_SESSION_ID}*" -delete 2>/dev/null
  find ~/.config/gemini/sessions -name "*${GEMINI_REVIEW_SESSION_ID}*" -delete 2>/dev/null
fi

# Clean up temporary review output files (always safe to delete)
rm -f /tmp/codex_code_review_${CODE_REVIEW_ID}.json /tmp/gemini_code_review_${CODE_REVIEW_ID}.json 2>/dev/null
```

Display the completion summary:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ✅ CODE REVIEW COMPLETE                                 ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Rounds: [N]                                             ┃
┃ Fixed: [X] critical, [Y] important                      ┃
┃ Skipped: [Z] suggestions                                ┃
┃                                                         ┃
┃ Modified files:                                         ┃
┃   • [file1.py]                                          ┃
┃   • [file2.py]                                          ┃
┃                                                         ┃
┃ Sessions cleaned up:                                    ┃
┃   • Codex: Yes                                          ┃
┃   • Gemini: Yes                                         ┃
┃   • Temp files: Yes                                     ┃
┃                                                         ┃
┃ Next steps:                                             ┃
┃   • Run tests: uv run --frozen pytest -x                         ┃
┃   • Re-stage changes: git add -p                        ┃
┃   • Commit: /commit                                     ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

Clear session state:
```
CODE_REVIEW_ID=""
CODEX_REVIEW_SESSION_ID=""
GEMINI_REVIEW_SESSION_ID=""
REVIEW_ROUND=1
ADDRESSED_FINDINGS=[]
SKIP_REMAINING_CLARIFICATIONS=false
PLAN_VALIDATED=false
```

## Error Handling

### Codex CLI Not Installed
```
❌ Codex CLI not found.

To install:
  npm install -g @openai/codex-cli

Then authenticate:
  codex login
```

### Gemini CLI Not Installed
```
⚠️  Gemini CLI not found.

To install:
  npm install -g @google/gemini-cli

Then authenticate:
  gemini auth login

Continuing with Codex-only review...
```

### Gemini Authentication Error
```
⚠️  Gemini authentication failed.

Run `gemini auth login` to authenticate with your Google account.

Continuing with Codex-only review...
```

### No Changes to Review
```
No changes found for scope 'staged'.

Try:
  • git add <file>         - Stage changes first
  • /code-review all       - Review all uncommitted changes
  • /code-review branch    - Review all changes on branch
```

### Large Diff Warning
```
⚠️  Large diff detected: [X] files, [Y] lines

Large diffs may:
  • Take longer to analyze
  • Hit token limits
  • Miss context

Consider:
  • Breaking into smaller commits
  • Reviewing specific files: /code-review staged (after staging subset)
```

### Codex Timeout
```
⚠️  Codex review timed out.

The diff may be too large. Try:
  1. Review fewer files at once
  2. Use /code-review staged with smaller staged set
```

### Session Not Found (Round 2+)
```
⚠️  Previous session not found. Starting fresh review.

This can happen if:
  • Session file was deleted
  • Session is too old (>24 hours)
  • Codex was updated

Continuing with new session...
```

When session resume fails, fall back gracefully:
1. Create a new session
2. Include summary of previously fixed findings in the prompt
3. Continue review workflow normally

### Cleanup on Interruption

If the review is interrupted (user switches tasks, `/clear` is called, or session ends unexpectedly), sessions may not be cleaned up automatically.

**Manual cleanup command** (run if review was interrupted):
```bash
# List orphaned code review temp files (review before deleting)
ls -la /tmp/codex_code_review_*.json /tmp/gemini_code_review_*.json 2>/dev/null

# Delete orphaned code review temp files
rm -f /tmp/codex_code_review_*.json /tmp/gemini_code_review_*.json 2>/dev/null

# List recent Codex sessions (review before deleting)
find ~/.codex/sessions -type f -mmin -60 -name "*.jsonl" -ls
# To delete: find ~/.codex/sessions -type f -mmin -60 -name "*.jsonl" -delete

# List recent Gemini sessions (review before deleting)
find ~/.gemini/sessions ~/.config/gemini/sessions -type f -mmin -60 -name "*.json" -ls 2>/dev/null
# To delete: find ~/.gemini/sessions ~/.config/gemini/sessions -type f -mmin -60 -name "*.json" -delete 2>/dev/null
```

**Session locations**:
- Codex: `~/.codex/sessions/YYYY/MM/DD/*.jsonl`
- Gemini: `~/.gemini/sessions/` or `~/.config/gemini/sessions/`
- Temp files: `/tmp/codex_code_review_${CODE_REVIEW_ID}.json`, `/tmp/gemini_code_review_${CODE_REVIEW_ID}.json`

## Category Definitions

| Category | Examples |
|----------|----------|
| 🐛 Bug | Logic errors, off-by-one, null pointer, race conditions |
| 🔒 Security | SQL injection, XSS, command injection, path traversal, hardcoded secrets |
| ⚡ Performance | N+1 queries, unnecessary loops, memory leaks, blocking I/O |
| 📐 Quality | Code smells, poor naming, excessive complexity, missing types |
| 🧪 Testing | Missing test cases, untested edge cases, flaky test patterns |

## Severity Definitions

| Severity | Description | Action Required |
|----------|-------------|-----------------|
| 🔴 Critical | Security vulnerabilities, data corruption risks, breaking bugs | Must fix before commit |
| ⚠️  Important | Potential bugs, performance issues, quality concerns | Strongly recommended |
| 💡 Suggestion | Style improvements, alternative approaches, minor enhancements | User discretion |

## Example Session

```
User: /code-review staged

Claude: 🔍 Gathering staged changes...
        Found: 3 files, +47/-12 lines

        📤 Sending to Codex + Gemini for review...
        ⏳ Running parallel analysis...

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🤖 DUAL REVIEW: CODEX + GEMINI                          ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Reviewers: Codex (gpt-5.2-codex) + Gemini (gemini-3-pro-preview)
┃ Scope: staged                                           ┃
┃ Files: 3 files, +47/-12 lines                           ┃
┃ Findings: 3 total (1 both, 1 Codex, 1 Gemini)           ┃
┃ Verdict: REQUEST_CHANGES                                ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 🔴 CRITICAL (2)                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 1. [Both] 🔒 Security: SQL Injection                    ┃
┃    📁 src/api/users.py:47                               ┃
┃    Codex: Use parameterized query                       ┃
┃    Gemini: Use SQLAlchemy ORM                           ┃
┃                                                         ┃
┃ 2. [Gemini] 🐛 Bug: Missing null check                  ┃
┃    📁 src/utils/parse.py:23                             ┃
┃    Fix: Check response.data is not None first           ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 💡 SUGGESTIONS (1)                                      ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 3. [Codex] 📐 Quality: Consider using dataclass         ┃
┃    📁 src/models/user.py:15                             ┃
┃    Plain dict could be a typed dataclass                ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

Address findings? [A]ll / [C]ritical only / [P]ick / [S]kip

User: A

Claude: 📝 Finding 1/3: SQL Injection
           📁 src/api/users.py:47
           Severity: 🔴 Critical
           Category: security
           Source: [Both]

        Current: query = f"SELECT * FROM users WHERE id = {user_id}"

        Codex suggests: Use parameterized query with cursor.execute()
        Gemini suggests: Use SQLAlchemy ORM query builder

        ❓ How should this vulnerability be mitigated?
          [1] Parameterized query with cursor.execute() (Codex - Recommended)
          [2] SQLAlchemy ORM query builder (Gemini)
          [3] Add input validation + sanitization
          [4] Let me specify...

User: 1

Claude: Using parameterized query approach.

        Before:
        │ 45 │ def get_user(user_id: str):
        │ 46 │     conn = get_db_connection()
        │ 47 │     query = f"SELECT * FROM users WHERE id = {user_id}"
        │ 48 │     cursor.execute(query)

        After:
        │ 45 │ def get_user(user_id: str):
        │ 46 │     conn = get_db_connection()
        │ 47 │     query = "SELECT * FROM users WHERE id = %s"
        │ 48 │     cursor.execute(query, (user_id,))

        Apply this fix? [Y/n/a]

User: Y

Claude: ✅ Fix applied.

        📝 Finding 2/3: Missing null check
           📁 src/utils/parse.py:23
           Severity: 🔴 Critical
           Category: bug
           Source: [Gemini]

        ❓ How should this error case be handled?
          [1] Return empty list/dict (Recommended)
          [2] Raise ValueError with message
          [3] Log warning and return None
          [4] Let me specify...

User: a  (apply all remaining)

Claude: ✅ Applying all remaining fixes with default approaches...

        Finding 2/3: Using "Return empty list" approach
        ✅ Applied to src/utils/parse.py:23

        Finding 3/3: Suggestion - skipped (non-critical)

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ✅ CODE REVIEW COMPLETE                                 ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Fixed: 2 critical issues                                ┃
┃ Skipped: 1 suggestion                                   ┃
┃                                                         ┃
┃ Modified files:                                         ┃
┃   • src/api/users.py                                    ┃
┃   • src/utils/parse.py                                  ┃
┃                                                         ┃
┃ Next steps:                                             ┃
┃   • Run tests: uv run --frozen pytest -x                         ┃
┃   • Re-stage: git add src/api/users.py src/utils/...    ┃
┃   • Commit: /commit                                     ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

## Auto-Fix Mode

For power users, `--auto-fix` applies all fixes automatically:

```
User: /code-review --auto-fix

Claude: 🔍 Gathering staged changes...
        📤 Sending to Codex for review...
        Found 3 issues. Auto-fixing...

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ AUTO-FIX SUMMARY                                        ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ ✅ Fixed: SQL injection in src/api/users.py:47          ┃
┃ ✅ Fixed: Missing null check in src/utils/parse.py:23   ┃
┃ ⏭️  Skipped: Style suggestion (non-critical)            ┃
┃                                                         ┃
┃ Files modified: 2                                       ┃
┃ Run `git diff` to review changes                        ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  [1] Accept all fixes
  [2] Review each fix
  [3] Revert all (git checkout)
```

## Integration

- **Before commit**: Run `/code-review staged` to catch issues
- **After fixing**: Run tests with `uv run --frozen pytest -x`
- **Commit workflow**: Stage fixes, then use `/commit`

## Best Practices

1. **Review before committing**: Catch issues early
2. **Use `staged` scope**: Review what you're about to commit
3. **Run tests after fixes**: Ensure fixes don't break anything
4. **Iterate if needed**: Re-run review after major fixes
5. **Address critical first**: Security and bugs before style

---

**Models**:
- Codex: Uses defaults from `~/.codex/config.toml` (typically gpt-5.2-codex with xhigh)
- Gemini: Uses `gemini-3-pro-preview` via Gemini CLI

**Timeout**: 180 seconds per reviewer (both run in parallel)

**Free Tier Limits** (Gemini):
- 60 requests/min, 1,000 requests/day with personal Google account
- 1M token context window

## Prompt Best Practices Sources

The prompts in this command follow official best practices:

- [Codex Prompting Guide](https://cookbook.openai.com/examples/gpt-5/codex_prompting_guide) - Autonomous, action-biased, tool-preferring
- [GPT-5.2-Codex Introduction](https://openai.com/index/introducing-gpt-5-2-codex/) - Context compaction, xhigh reasoning
- [Gemini 3 Prompting Guide](https://ai.google.dev/gemini-api/docs/gemini-3) - Direct, concise, context-then-question
- [Gemini CLI Documentation](https://geminicli.com/docs/) - JSON output, headless mode
