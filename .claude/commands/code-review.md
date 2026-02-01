---
description: Review code changes with Multi-AI reviewers (Claude + Gemini by default, +Codex with --heavy)
---
# Code Review with Multi-AI Reviewers

Get comprehensive AI review of code changes using Claude (primary analyst) plus Google Gemini CLI. Use `--heavy` to add OpenAI Codex for triple-AI analysis. Fix issues with clarifying questions before committing.

## Usage

```bash
/code-review [scope]
```

**Scopes**:
- `staged` (default): Only staged changes (`git diff --staged`)
- `all`: All uncommitted changes (`git diff HEAD`)
- `branch`: All changes vs base branch (`git diff main...HEAD`)

**Flags**:
- `--light`: Claude Code only (fastest, 2 min timeout)
- `--medium`: Claude Code + Gemini (default, 5 min timeout)
- `--heavy`: Claude Code + Gemini + Codex (most thorough, 10 min timeout)
- `--timeout <duration>`: Override default timeout (e.g., `5m`, `90s`, `2min30sec`, `30s10m`). Must be a single token without spaces.
- `--auto-fix`: Automatically apply all fixes (power user mode)

> **Breaking Change (v2.0)**: Default intensity changed from triple-AI to dual-AI.
> Use `--heavy` for full Claude + Gemini + Codex analysis, or set
> `TRIPLE_AI_DEFAULT_INTENSITY=heavy` environment variable.

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
CODE_REVIEW_ID=""                         # Unique ID for this review session (generated at start)
CODEX_REVIEW_SESSION_ID=""                # Current Codex session UUID
GEMINI_REVIEW_SESSION_ID=""               # Current Gemini session UUID
REVIEW_ROUND=1                            # Current iteration number
ADDRESSED_FINDINGS=[]                     # Findings addressed in previous rounds
SKIP_REMAINING_CLARIFICATIONS=false       # Set true after user selects "apply all"
AI_INTENSITY="medium"                     # Intensity level: light|medium|heavy (default: medium)
AI_TIMEOUT=300                            # Timeout in seconds (default: 5 min for medium)
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

## Intensity Level Parsing

Parse intensity flags (`--light`, `--medium`, `--heavy`) and timeout before processing arguments:

```bash
# Parse human-friendly timeout to seconds (handles any order: 30s10m, 1h5s, etc.)
parse_timeout() {
  local input="$1"
  local total_seconds=0

  # Remove spaces, quotes, and convert to lowercase
  input=$(echo "$input" | tr -d ' "'"'" | tr '[:upper:]' '[:lower:]')

  local remaining="$input"

  # Loop to extract time units in ANY order (30s10m works)
  while [[ -n "$remaining" ]]; do
    if [[ "$remaining" =~ ^([0-9]+)(h|hr|hours?)(.*)$ ]]; then
      total_seconds=$((total_seconds + ${BASH_REMATCH[1]} * 3600))
      remaining="${BASH_REMATCH[3]}"
    elif [[ "$remaining" =~ ^([0-9]+)(m|min|minutes?)(.*)$ ]]; then
      total_seconds=$((total_seconds + ${BASH_REMATCH[1]} * 60))
      remaining="${BASH_REMATCH[3]}"
    elif [[ "$remaining" =~ ^([0-9]+)(s|sec|seconds?)(.*)$ ]]; then
      total_seconds=$((total_seconds + ${BASH_REMATCH[1]}))
      remaining="${BASH_REMATCH[3]}"
    elif [[ "$remaining" =~ ^[0-9]+$ ]]; then
      total_seconds=$((total_seconds + remaining))
      remaining=""
    else
      echo "ERROR: Invalid timeout format: '$1' (unparsed: '$remaining')" >&2
      return 1
    fi
  done

  [[ $total_seconds -eq 0 ]] && { echo "ERROR: Timeout must be greater than 0" >&2; return 1; }
  [[ $total_seconds -gt 1800 ]] && { echo "WARNING: Capping at 30m" >&2; total_seconds=1800; }

  echo "$total_seconds"
}

# Environment variable override for default intensity
AI_INTENSITY="${TRIPLE_AI_DEFAULT_INTENSITY:-medium}"
[[ -n "$TRIPLE_AI_DEFAULT_INTENSITY" && ! "$TRIPLE_AI_DEFAULT_INTENSITY" =~ ^(light|medium|heavy)$ ]] && AI_INTENSITY="medium"

# Robust argument parsing
declare -a REMAINING_ARGS=()
INTENSITY_FLAG_COUNT=0
CUSTOM_TIMEOUT=""
TIMEOUT_FLAG_COUNT=0
SKIP_NEXT=false

read -r -a args <<< "$ARGUMENTS"

for i in "${!args[@]}"; do
  [[ "$SKIP_NEXT" == true ]] && { SKIP_NEXT=false; continue; }
  arg="${args[$i]}"
  case "$arg" in
    --light)  AI_INTENSITY="light"; ((INTENSITY_FLAG_COUNT++)) ;;
    --medium) AI_INTENSITY="medium"; ((INTENSITY_FLAG_COUNT++)) ;;
    --heavy)  AI_INTENSITY="heavy"; ((INTENSITY_FLAG_COUNT++)) ;;
    --timeout)
      next_idx=$((i + 1))
      [[ -n "${args[$next_idx]}" ]] && { CUSTOM_TIMEOUT="${args[$next_idx]}"; ((TIMEOUT_FLAG_COUNT++)); SKIP_NEXT=true; } || { echo "ERROR: --timeout requires a value"; exit 1; }
      ;;
    --timeout=*)
      CUSTOM_TIMEOUT="${arg#--timeout=}"
      [[ -z "$CUSTOM_TIMEOUT" ]] && { echo "ERROR: --timeout= requires a value"; exit 1; }
      ((TIMEOUT_FLAG_COUNT++))
      ;;
    *) REMAINING_ARGS+=("$arg") ;;
  esac
done

[[ $TIMEOUT_FLAG_COUNT -gt 1 ]] && { echo "ERROR: Multiple --timeout flags"; exit 1; }
[[ $INTENSITY_FLAG_COUNT -gt 1 ]] && { echo "ERROR: Multiple intensity flags"; exit 1; }

# Apply timeout
if [[ -n "$CUSTOM_TIMEOUT" ]]; then
  AI_TIMEOUT=$(parse_timeout "$CUSTOM_TIMEOUT") || exit 1
else
  case "$AI_INTENSITY" in
    light)  AI_TIMEOUT=120 ;;
    medium) AI_TIMEOUT=300 ;;
    heavy)  AI_TIMEOUT=600 ;;
  esac
fi

echo "Intensity: $AI_INTENSITY | Timeout: ${AI_TIMEOUT}s"
```

## Multi-AI Configuration

Use Claude as primary analyst with Codex and Gemini CLI running in parallel for comprehensive code analysis:

| Reviewer | Model | Strengths | Web Capabilities |
|----------|-------|-----------|------------------|
| Claude | claude-opus-4-5 | Session context, codebase familiarity, plan validation | WebSearch, WebFetch (native) |
| Codex | gpt-5.2-codex | Deep code reasoning, precise fixes | `--search on` flag |
| Gemini | gemini-3-pro-preview | Broad context (1M tokens), alternative perspectives | google_web_search, web_fetch tools |

### Web Search Security

**IMPORTANT**: Web search is DISABLED when reviewing code with sensitive content to prevent data leakage.

**When web search is enabled**, AIs should use it to validate:
- Security recommendations (OWASP, CWE updates)
- Library vulnerabilities and fixes
- Best practices for specific frameworks

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

### Step 2.5: Detect Plan Context (Optional)

For code review, Claude should check for an active implementation plan to validate changes against:

**Plan Detection Priority:**

1. **Active session plan** (highest priority)
   - Check conversation context for system reminder:
     `"A plan file exists from plan mode at: /path/to/plan.md"`
   - If found, use this path automatically (no confirmation needed)
   - Display: `📋 Using active session plan: [path]`

2. **Plans directory fallback**
   - If no active plan detected, search `~/.claude/plans/*.md`
   - Use most recently modified plan (no confirmation for code review)
   - Plan provides context for validating changes align with requirements

**Note**: Plan detection is optional for code review. If no plan is found, proceed with code review without plan validation.

### Step 3: Verify Reviewer CLIs (Intensity-Conditional)

Before invoking reviewers, verify CLIs based on intensity level. This is an **Agent-level workflow**:

```bash
# Check availability based on intensity level
GEMINI_AVAILABLE="no"
CODEX_AVAILABLE="no"

# Skip all checks if --light
if [[ "$AI_INTENSITY" != "light" ]]; then
  which gemini >/dev/null 2>&1 && GEMINI_AVAILABLE="yes"
fi

# Only check Codex if --heavy
if [[ "$AI_INTENSITY" == "heavy" ]]; then
  which codex >/dev/null 2>&1 && CODEX_AVAILABLE="yes"
fi
```

**If Gemini missing AND intensity requires it (medium/heavy)**: Agent uses `AskUserQuestion` to offer:
- "Continue with Claude-only" → sets `AI_INTENSITY = "light"`
- "Abort" → displays installation instructions and exits

**If Codex missing AND intensity is heavy**: Agent uses `AskUserQuestion` to offer:
- "Continue with Claude + Gemini" → sets `AI_INTENSITY = "medium"`
- "Abort" → displays installation instructions and exits

Agent proceeds with the (possibly adjusted) `AI_INTENSITY` value.

### Step 4: Invoke Multi-AI Analysis

Send the diff to Claude (primary), Codex, and Gemini in parallel for comprehensive analysis.

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

Launch AIs based on intensity level:

**Conditional invocation pattern:**
```bash
# Claude always runs (primary analyst)
# Claude performs analysis using Read tool and session context

# Launch Gemini (unless --light)
if [[ "$AI_INTENSITY" != "light" ]]; then
  # Gemini invocation (see below)
fi

# Launch Codex (only if --heavy)
if [[ "$AI_INTENSITY" == "heavy" ]]; then
  # Codex invocation (see below)
fi
```

Run reviewers in parallel for efficiency:

```bash
# Get file list and stats (context-efficient)
CHANGED_FILES=$(git diff --staged --name-only | tr '\n' ' ')
DIFF_STAT=$(git diff --staged --stat | tail -1)

# Detect active plan file for context using priority order:
# 1. Active session plan: Claude injects via system reminder:
#    "A plan file exists from plan mode at: /path/to/plan.md"
#    If found in conversation context, use automatically (no confirmation needed).
# 2. User-provided argument: Check if path was passed as argument
# 3. Plans directory search: Fallback to most recently modified plan in ~/.claude/plans/
#    (For code review, no confirmation needed since plan is just context, not the review target)
#
# NOTE: Claude (the AI) should check conversation context for active plan first.
# The bash variable below is only a fallback when no active plan is detected.
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

#### Claude Primary Analysis (Parallel with External AIs)

While Codex and Gemini run in background, Claude performs its own code review:

1. **Read the diff and affected files** using the Read tool
2. **Review for**:
   - Security vulnerabilities (OWASP Top 10)
   - Bug patterns (null handling, off-by-one, race conditions)
   - Performance issues (N+1 queries, missing indexes, blocking I/O)
   - Error handling (uncaught exceptions, missing validation)
   - Style/quality (naming, complexity, DRY violations)
3. **Validate against active plan** (if exists):
   - Check that changes align with plan requirements
   - Verify all planned items are implemented
   - Flag deviations from planned approach
4. **Check consistency with existing codebase patterns**:
   - Match error handling patterns
   - Match logging patterns
   - Match testing patterns
5. **Generate findings** in same JSON format as external reviewers:
   ```json
   {
     "findings": [
       {
         "severity": "critical|important|suggestion",
         "category": "bug|security|performance|quality|testing",
         "file": "path/to/file.py",
         "line": 42,
         "description": "Issue description",
         "current_code": "problematic code snippet",
         "suggestion": "how to fix",
         "fixed_code": "corrected code snippet"
       }
     ],
     "summary": "Overall assessment",
     "verdict": "approve|request_changes"
   }
   ```

**Claude's unique advantages:**
- Full access to session context and conversation history
- Can read full file context, not just diff
- Familiar with codebase patterns from current session
- Can validate changes against active implementation plan

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
# SANDBOX_FLAGS for ADC and plans directory access
export SANDBOX_FLAGS="-v $HOME/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json -v $HOME/.claude/plans:$PWD/.claude-plans:ro"
gemini \
  --resume $GEMINI_REVIEW_SESSION_ID \
  --model gemini-3-pro-preview \
  --sandbox \
  --allowed-tools run_shell_command \
  --allowed-tools read_file \
  --prompt "Round [N]: Verify fixes from previous review.

Re-analyze the updated diff (run 'git diff --staged') and verify previous issues are resolved.

Return JSON: {\"findings\": [...], \"summary\": \"...\", \"verdict\": \"approve|request_changes\"}"
```

**Benefits of triple-reviewer session persistence**:
- All three reviewers preserve context across review rounds
- Reviewers remember previous findings and can verify fixes
- No need to re-explain the codebase or plan context

**Benefits of triple-reviewer approach**:
- Claude: Session context, codebase familiarity, plan validation
- Codex: Deep code reasoning, precise fixes, session persistence
- Gemini: Broad context (1M tokens), alternative perspectives
- Cross-validation with 3 AIs provides highest confidence
- Different model architectures catch different issues

### Step 5: Reconcile Findings (3-Way Merge)

After all three reviewers complete, merge and deduplicate their findings:

#### Finding Reconciliation Logic

1. **Parse JSON** from Claude's analysis, TaskOutput for Codex, and TaskOutput for Gemini

2. **Deduplicate findings** by comparing:
   - Same file + same line + similar description = merge into single finding
   - Keep higher severity when merging (critical > important > suggestion)

3. **Tag each finding with consensus level** (intensity-dependent):

   **--heavy (3 AIs)**:
   - `[Consensus]` - All 3 AIs identified this issue (HIGH confidence)
   - `[Claude+Codex]`, `[Claude+Gemini]`, `[Codex+Gemini]` - 2 of 3 agree (MEDIUM)
   - `[Claude-only]`, `[Codex-only]`, `[Gemini-only]` - Single AI (LOWER)

   **--medium (2 AIs)**:
   - `[Consensus]` - Claude and Gemini both agree (HIGH confidence)
   - `[Claude-only]` - Only Claude identified this
   - `[Gemini-only]` - Only Gemini identified this

   **--light (1 AI)**:
   - `[Claude]` - All findings from Claude only (no consensus possible)

4. **Sort by confidence then severity**:
   - Consensus first, then partial, then single
   - Within each tier: critical > important > suggestion

5. **Reconcile verdicts**:
   - If ANY AI says `request_changes` → overall verdict is `REQUEST_CHANGES`
   - If ALL 3 say `approve` → overall verdict is `APPROVED`

#### Graceful Degradation

When external AIs fail or are unavailable:
- If Codex fails → Continue with Claude + Gemini (reduced confidence)
- If Gemini fails → Continue with Claude + Codex (reduced confidence)
- If both fail → Claude-only review with warning about reduced accuracy
- Display which AIs participated in the review header

#### Handling Disagreements

When reviewers suggest different fixes for the same finding:
- Display all available suggestions in the clarification question
- Include "Claude suggests: X", "Codex suggests: Y", and "Gemini suggests: Z" as separate options
- Highlight consensus approaches when 2+ AIs agree
- Let user choose or provide custom approach

### Step 6: Parse and Display Results

#### Dynamic Header Based on Intensity

```bash
# Generate header based on which AIs participated
case "$AI_INTENSITY" in
  light)
    HEADER="CLAUDE REVIEW"
    PARTICIPANTS="Claude"
    ;;
  medium)
    HEADER="DUAL REVIEW: CLAUDE + GEMINI"
    PARTICIPANTS="Claude, Gemini"
    ;;
  heavy)
    HEADER="TRIPLE REVIEW: CLAUDE + CODEX + GEMINI"
    PARTICIPANTS="Claude, Codex, Gemini"
    ;;
esac
```

Display reconciled findings in a structured format with source attribution:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🤖 [HEADER]                                             ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ PARTICIPANTS: [PARTICIPANTS]                            ┃
┃ Reviewers: [PARTICIPANTS]                               ┃
┃ Scope: [staged/all/branch]                              ┃
┃ Files: [N] files, +[X]/-[Y] lines                       ┃
┃ Findings: [N] total ([X] consensus, [Y] partial, [Z] single)┃
┃ Verdict: [APPROVED / REQUEST_CHANGES]                   ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 🔴 CRITICAL                                             ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 1. [Consensus] 🔒 Security: SQL Injection               ┃
┃    📁 src/api/users.py:47                               ┃
┃    Claude: Use parameterized query with %s placeholders ┃
┃    Codex: Use parameterized query                       ┃
┃    Gemini: Use ORM or prepared statement                ┃
┃                                                         ┃
┃ 2. [Claude+Gemini] 🐛 Bug: Missing null check           ┃
┃    📁 src/utils/parse.py:23                             ┃
┃    Fix: Check response.data is not None first           ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ ⚠️  IMPORTANT                                            ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 3. [Codex-only] ⚡ Performance: N+1 query pattern        ┃
┃    📁 src/api/orders.py:89                              ┃
┃    Fix: Use prefetch_related for eager loading          ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 💡 SUGGESTIONS                                          ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ [Suggestions with consensus tags...]                    ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Consensus tag meanings**:
- `[Consensus]` - HIGH confidence: all 3 AIs identified this issue
- `[Claude+Codex]`, `[Claude+Gemini]`, `[Codex+Gemini]` - MEDIUM confidence: 2 of 3 agree
- `[Claude-only]`, `[Codex-only]`, `[Gemini-only]` - LOWER confidence: single AI finding

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
      Source: [Consensus / Claude+Codex / Claude+Gemini / Codex+Gemini / Claude-only / Codex-only / Gemini-only]
   ```

2. **Ask clarification if needed** (see Clarification Rules above):

   For findings where reviewers suggest different fixes:
   ```
   ❓ How should this vulnerability be mitigated?
     [1] [Claude fix description] (Claude)
     [2] [Codex fix description] (Codex)
     [3] [Gemini fix description] (Gemini)
     [4] Combine approaches (highlight consensus when 2+ agree)
     [5] Let me specify...

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
# Clean up sessions that were actually created (intensity-conditional)

# Only clean up Gemini if it was used (medium or heavy)
if [[ "$AI_INTENSITY" != "light" && -n "$GEMINI_REVIEW_SESSION_ID" ]]; then
  find ~/.gemini/sessions -name "*${GEMINI_REVIEW_SESSION_ID}*" -delete 2>/dev/null
  find ~/.config/gemini/sessions -name "*${GEMINI_REVIEW_SESSION_ID}*" -delete 2>/dev/null
fi

# Only clean up Codex if it was used (heavy only)
if [[ "$AI_INTENSITY" == "heavy" && -n "$CODEX_REVIEW_SESSION_ID" ]]; then
  find ~/.codex/sessions -name "*${CODEX_REVIEW_SESSION_ID}*.jsonl" -delete 2>/dev/null
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

        📤 Launching Claude + Codex + Gemini analysis...
        ⏳ Running triple-AI parallel review...

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🤖 TRIPLE REVIEW: CLAUDE + CODEX + GEMINI               ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Reviewers: Claude + Codex + Gemini                      ┃
┃ Scope: staged                                           ┃
┃ Files: 3 files, +47/-12 lines                           ┃
┃ Findings: 3 total (1 consensus, 1 two-of-3, 1 single)   ┃
┃ Verdict: REQUEST_CHANGES                                ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 🔴 CRITICAL (2)                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 1. [Consensus] 🔒 Security: SQL Injection               ┃
┃    📁 src/api/users.py:47                               ┃
┃    Claude: Use parameterized query with %s placeholders ┃
┃    Codex: Use parameterized query                       ┃
┃    Gemini: Use SQLAlchemy ORM                           ┃
┃                                                         ┃
┃ 2. [Claude+Gemini] 🐛 Bug: Missing null check           ┃
┃    📁 src/utils/parse.py:23                             ┃
┃    Fix: Check response.data is not None first           ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 💡 SUGGESTIONS (1)                                      ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 3. [Codex-only] 📐 Quality: Consider using dataclass    ┃
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
           Source: [Consensus]

        Current: query = f"SELECT * FROM users WHERE id = {user_id}"

        Claude suggests: Use parameterized query with %s placeholders
        Codex suggests: Use parameterized query with cursor.execute()
        Gemini suggests: Use SQLAlchemy ORM query builder

        ❓ How should this vulnerability be mitigated?
          [1] Parameterized query with cursor.execute() (Consensus - Recommended)
          [2] SQLAlchemy ORM query builder (Gemini)
          [3] Add input validation + sanitization
          [4] Let me specify...

User: 1

Claude: Using parameterized query approach (consensus recommendation).

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
           Source: [Claude+Gemini]

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
