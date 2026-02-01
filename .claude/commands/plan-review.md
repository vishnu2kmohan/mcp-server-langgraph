---
description: Review implementation plans with triple AI reviewers (Claude + Codex + Gemini) and act on findings
---
# Plan Review with Triple AI Reviewers

Get comprehensive AI review of implementation plans using Claude (primary analyst) plus OpenAI Codex and Google Gemini CLI in parallel, then address findings collaboratively with clarifying questions.

## Usage

```bash
/plan-review [plan-file-path]
```

**Arguments**:
- `plan-file-path` (optional): Path to plan file. If omitted, searches `~/.claude/plans/*.md`

**Flags**:
- `--auto-fix`: Automatically apply all suggested revisions (power user mode)

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
PLAN_REVIEW_ID=""                         # Unique ID for this review session (generated at start)
CODEX_PLAN_REVIEW_SESSION_ID=""           # Current Codex session UUID
GEMINI_PLAN_REVIEW_SESSION_ID=""           # Current Gemini session UUID
REVIEW_ROUND=1                 # Current iteration number
ADDRESSED_FINDINGS=[]          # Findings addressed in previous rounds
SKIP_REMAINING_CLARIFICATIONS=false  # Set true after user selects "apply all"
```

**Generate unique review ID at session start** (before invoking reviewers):
```bash
# Generate unique ID for this review session (avoids temp file conflicts)
PLAN_REVIEW_ID=$(date +%s%N)  # Nanosecond timestamp, or use: $(uuidgen)
```

**Temp file naming** (session-specific to avoid conflicts):
```
/tmp/codex_plan_review_${PLAN_REVIEW_ID}.json
/tmp/gemini_plan_review_${PLAN_REVIEW_ID}.json
```

## Triple-Reviewer Configuration

Use Claude as primary analyst with Codex and Gemini CLI running in parallel for comprehensive analysis:

| Reviewer | Model | Strengths |
|----------|-------|-----------|
| Claude | claude-opus-4-5 | Session context, codebase familiarity, tool access |
| Codex | gpt-5.2-codex | Deep reasoning, code-level fixes |
| Gemini | gemini-3-pro-preview | Broad context (1M tokens), alternative perspectives |

### Security Settings (Read-Only Mode)

Both reviewers run with minimal permissions - they can read files freely but cannot modify them:

| Reviewer | Sandbox Mode | Read Operations | Write Operations |
|----------|--------------|-----------------|------------------|
| Codex | `--sandbox read-only` + `disk-full-read-access` | All reads allowed (Landlock enforced) | Blocked by Landlock |
| Gemini | `--sandbox` + `--allowed-tools` | read_file + run_shell_command (no confirmation) | Blocked by Docker |

**Key security features:**
- **Read access**: Both reviewers can read files freely within sandbox constraints
- **Write blocked**: All write operations are blocked at OS/container level
- **No YOLO mode**: Gemini uses `--allowed-tools` (specific tools) not `--yolo` (all tools)
- **File path references**: File paths passed in prompts, reviewers read files directly
- **Isolated execution**: Gemini runs in Docker container, Codex uses Landlock sandbox
- **No network access**: Network disabled by default in both CLIs
- **ADC mounting**: Gemini sandbox mounts ADC credentials via `SANDBOX_FLAGS` for Vertex AI auth
- **Plans directory**: `~/.claude/plans/` mounted read-only in Gemini sandbox for plan file access

### Clarification Rules

**ASK CLARIFICATION** when ALL of:
- Severity is "critical" or "important"
- Finding category is: security, architecture, error_handling, or performance
- `--auto-fix` flag is NOT set
- `SKIP_REMAINING_CLARIFICATIONS` is false

**SKIP CLARIFICATION** when ANY of:
- Severity is "suggestion"
- Finding is trivial (single-line fix, obvious correction)
- Category is "quality" or "testing" (lower stakes)
- `--auto-fix` flag is set
- User previously chose "Apply all remaining without asking"

### Clarification Question Templates (Plan Review)

| Category | Question | Options |
|----------|----------|---------|
| architecture | "Which architectural approach?" | Context-specific options based on finding |
| security | "How should this security concern be addressed?" | Context-specific options |
| completeness | "What should be added to complete this section?" | Context-specific options |
| error_handling | "How should error cases be documented?" | Add error handling section, Inline in implementation, Separate ADR, Let me specify... |
| performance | "Which optimization strategy?" | Add caching layer, Optimize algorithm, Add lazy loading, Let me specify... |

## Workflow

### Step 1: Locate Plan File

Locate the plan file to review using this priority order:

#### 1.1: Check Active Session Plan (Highest Priority)

Look in the current conversation context for an active plan. Claude Code injects plan information
via system reminders when a plan is active:

```
A plan file exists from plan mode at: /path/to/plan.md
```

If an active session plan is found in the conversation context:
- Use that plan path automatically
- Display: `📋 Using active session plan: [path]`

#### 1.2: Check User-Provided Path (Second Priority)

Check if argument `$ARGUMENTS` specifies a plan file path.

If provided:
- Verify file exists at specified path
- Display: `📋 Using specified plan: [path]`

#### 1.3: Search Plans Directory (Fallback - Requires Confirmation)

If no active session plan and no path argument provided:
- Search for plan files in `~/.claude/plans/*.md`
- Sort by modification time (most recent first)
- **ALWAYS prompt user to confirm** which plan to use (even if only one found)
- If none found, inform user and exit

**User confirmation is required** because without an active session plan, we cannot be certain
which plan the user intends to review. Use the AskUserQuestion tool:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ⚠️  NO ACTIVE SESSION PLAN DETECTED                      ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                          ┃
┃ Found [N] plan file(s) in ~/.claude/plans/:              ┃
┃                                                          ┃
┃   1. plan-name-1.md (modified: 2 hours ago)              ┃
┃   2. plan-name-2.md (modified: 1 day ago)                ┃
┃   3. plan-name-3.md (modified: 3 days ago)               ┃
┃                                                          ┃
┃ Which plan would you like to review?                     ┃
┃                                                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

Present options using AskUserQuestion with:
- Up to 4 most recently modified plans as options
- "Other" option allows user to specify a different path

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 📋 PLAN DETECTION                                        ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                          ┃
┃ Priority Order:                                          ┃
┃   1. Active session plan (auto-detected, no confirmation)┃
┃   2. User-provided path argument (no confirmation)       ┃
┃   3. Plans directory search (REQUIRES confirmation)      ┃
┃                                                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Step 2: Verify Reviewer CLIs

Before invoking reviewers, verify both CLIs are available:

```bash
# Check Codex CLI
which codex || echo "ERROR: Codex CLI not found. Install with: npm install -g @openai/codex-cli"

# Check Gemini CLI
which gemini || echo "ERROR: Gemini CLI not found. Install with: npm install -g @google/gemini-cli"
```

If either external CLI is not installed, provide installation instructions. Both external CLIs (Codex/Gemini) are recommended; if one is missing, proceed with Claude + the remaining CLI; if both are missing, proceed Claude-only with a warning about reduced accuracy.

### Step 3: Invoke Triple-Reviewer Analysis

Send the plan to Claude (primary), Codex, and Gemini in parallel for comprehensive analysis.

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
# Use the original plan file path (from Step 1)
# PLAN_PATH = path provided by user or found in ~/.claude/plans/

# Codex review (background)
# Best practices: Autonomous, action-biased, direct instructions
# Reference: https://developers.openai.com/codex/security/
# Uses Landlock read-only sandbox with full disk read access for ~/.claude/plans/
codex exec \
  --sandbox read-only \
  --skip-git-repo-check \
  -c 'sandbox_permissions=["disk-full-read-access"]' \
  -C "$(dirname "$PLAN_PATH")" \
  "Review the implementation plan.

File to review: $(basename "$PLAN_PATH")

Read the file and analyze for: architecture soundness, security (OWASP Top 10), performance, error handling, completeness (tests, docs, deployment).

Return JSON: {\"findings\": [{\"severity\": \"critical|important|suggestion\", \"category\": \"...\", \"section\": \"...\", \"description\": \"...\", \"suggestion\": \"...\"}], \"summary\": \"...\", \"verdict\": \"approve|request_changes\"}"
# When using run_in_background=true, output goes to TaskOutput - no file redirection needed

# Gemini review (background)
# Best practices: Direct, concise, context-then-question structure
# Reference: https://geminicli.com/docs/cli/sandbox/
# Mode: Docker sandbox (writes blocked by container)
# Tools: read_file + run_shell_command allowed without confirmation
# Context-efficient: Pass file path, let Gemini read the file itself
# Note: Use repeated --allowed-tools flags (space-separated array causes parsing issues)
# Note: Use --prompt flag (stdin pipe doesn't work reliably with run_in_background)
# SANDBOX_FLAGS mounts:
# 1. ADC: Required for Vertex AI auth (docker-level mount, not affected by read_file restrictions)
# 2. Plans: Mount to project subdirectory so read_file tool can access it
# NOTE: Use double quotes to allow shell expansion of $HOME and $PWD
export SANDBOX_FLAGS="-v $HOME/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json -v $HOME/.claude/plans:$PWD/.claude-plans:ro"

# Transform host path to container path (mounted inside project as .claude-plans/)
GEMINI_PLAN_PATH=$(basename "$PLAN_PATH")

gemini \
  --model gemini-3-pro-preview \
  --sandbox \
  --allowed-tools run_shell_command \
  --allowed-tools read_file \
  --prompt "Review the implementation plan.

File to review: .claude-plans/$GEMINI_PLAN_PATH

Read the file and analyze for: architecture, security (OWASP Top 10), performance, error handling, completeness.

Return JSON: {\"findings\": [{\"severity\": \"critical|important|suggestion\", \"category\": \"...\", \"section\": \"...\", \"description\": \"...\", \"suggestion\": \"...\"}], \"summary\": \"...\", \"verdict\": \"approve|request_changes\"}"
# When using run_in_background=true, output goes to TaskOutput - no file redirection needed

# Note: When using Claude's run_in_background=true, use TaskOutput to retrieve results
# The GEMINI_PID and wait commands are only needed for shell-level parallelism
```

#### Claude Primary Analysis (Parallel with External AIs)

While Codex and Gemini run in background, Claude performs its own plan review:

1. **Read the plan file content** using the Read tool
2. **Check for**:
   - Security concerns (hardcoded secrets, missing auth, injection risks)
   - Architectural issues (coupling, scalability, missing error handling)
   - Completeness (missing steps, unclear requirements, edge cases)
   - Consistency (contradictions, outdated references)
3. **Cross-reference with**:
   - Existing codebase patterns (via file reads)
   - Related ADRs in `docs/adr/`
   - Testing requirements in plan
4. **Generate findings** in same JSON format as external reviewers:
   ```json
   {
     "findings": [
       {
         "severity": "critical|important|suggestion",
         "category": "security|architecture|completeness|error_handling|performance",
         "section": "Section Name",
         "description": "Issue description",
         "suggestion": "Recommended fix"
       }
     ],
     "summary": "Overall assessment",
     "verdict": "approve|request_changes"
   }
   ```

**Claude's unique advantages:**
- Full access to session context and conversation history
- Can read referenced files directly via Read tool
- Familiar with codebase patterns from current session
- No sandbox restrictions on file access

After the initial review, capture the Codex session ID for subsequent rounds:

```bash
# Capture session ID from most recent Codex session
CODEX_PLAN_REVIEW_SESSION_ID=$(ls -t ~/.codex/sessions/$(date +%Y)/*/*/*.jsonl 2>/dev/null | head -1 | xargs -I{} basename {} .jsonl | grep -oP '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' | head -1)

# Capture session ID from most recent Gemini session
GEMINI_PLAN_REVIEW_SESSION_ID=$(ls -t ~/.gemini/sessions/*.json ~/.config/gemini/sessions/*.json 2>/dev/null | head -1 | xargs -I{} basename {} .json | grep -oP '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' | head -1)
```

#### Round 2+: Resume Existing Sessions

For subsequent review rounds, resume existing sessions for both Codex and Gemini to preserve context:

```bash
# Resume Codex session
codex exec resume $CODEX_PLAN_REVIEW_SESSION_ID "Round [N]: Verify fixes from previous review.

IMPORTANT: Your entire response must be valid JSON only, no other text.

Previously addressed findings:
[List of findings that were addressed in the last round]

Re-analyze the updated plan and identify:
1. Whether previous issues are properly resolved
2. Any new issues introduced by the fixes
3. Remaining concerns not yet addressed

Return the same JSON structure:
{
  \"findings\": [...],
  \"summary\": \"Overall assessment of changes\",
  \"verdict\": \"approve|request_changes\"
}

Updated plan:

$(cat <plan-file>)"

# Resume Gemini session (--resume <UUID> loads previous context)
# SANDBOX_FLAGS for ADC and plans directory access
export SANDBOX_FLAGS="-v $HOME/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json -v $HOME/.claude/plans:$PWD/.claude-plans:ro"
gemini \
  --resume $GEMINI_PLAN_REVIEW_SESSION_ID \
  --model gemini-3-pro-preview \
  --sandbox \
  --allowed-tools run_shell_command \
  --allowed-tools read_file \
  --prompt "Round [N]: Verify fixes from previous review.

Re-read the plan file at .claude-plans/$PLAN_NAME and verify previous issues are resolved.

Return JSON: {\"findings\": [...], \"summary\": \"...\", \"verdict\": \"approve|request_changes\"}"
```

**Benefits of triple-reviewer session persistence**:
- All three reviewers preserve context across review rounds
- Reviewers remember previous findings and can verify fixes
- No need to re-explain the plan context

**Benefits of triple-reviewer approach**:
- Claude: Session context, codebase familiarity, direct tool access
- Codex: Deep reasoning, code-level expertise, session persistence
- Gemini: Broad context (1M tokens), alternative perspectives
- Cross-validation with 3 AIs provides highest confidence
- Different model architectures catch different issues

### Step 4: Reconcile Findings (3-Way Merge)

After all three reviewers complete, merge and deduplicate their findings:

#### Finding Reconciliation Logic

1. **Parse JSON** from Claude's analysis, TaskOutput for Codex, and TaskOutput for Gemini

2. **Deduplicate findings** by comparing:
   - Same section + similar description = merge into single finding
   - Keep higher severity when merging (critical > important > suggestion)

3. **Tag each finding with consensus level**:
   - `[Consensus]` - All 3 AIs identified this issue (HIGH confidence)
   - `[Claude+Codex]` - Claude and Codex agree (MEDIUM confidence)
   - `[Claude+Gemini]` - Claude and Gemini agree (MEDIUM confidence)
   - `[Codex+Gemini]` - Codex and Gemini agree (MEDIUM confidence)
   - `[Claude-only]` - Only Claude identified this (LOWER confidence)
   - `[Codex-only]` - Only Codex identified this (LOWER confidence)
   - `[Gemini-only]` - Only Gemini identified this (LOWER confidence)

4. **Sort by confidence then severity**:
   - Consensus first, then 2-of-3, then single
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

When reviewers suggest different approaches for the same finding:
- Display all available suggestions in the clarification question
- Include "Claude suggests: X", "Codex suggests: Y", and "Gemini suggests: Z" as separate options
- Highlight consensus approaches when 2+ AIs agree
- Let user choose or provide custom approach

### Step 5: Parse and Display Results

Display reconciled findings in a structured format with source attribution:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🤖 TRIPLE REVIEW: CLAUDE + CODEX + GEMINI               ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Reviewers: Claude + Codex + Gemini                      ┃
┃ Findings: [N] total ([X] consensus, [Y] 2-of-3, [Z] single)┃
┃ Verdict: [APPROVED / REQUEST_CHANGES]                   ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 🔴 CRITICAL (must address)                              ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 1. [Consensus] Missing Redis failure handling           ┃
┃    📁 Section: "Implementation"                         ┃
┃    Claude: Add circuit breaker with graceful degradation┃
┃    Codex: Add fallback to allow requests when down      ┃
┃    Gemini: Implement circuit breaker pattern            ┃
┃                                                         ┃
┃ 2. [Claude+Codex] Security: Missing input validation    ┃
┃    📁 Section: "API Design"                             ┃
┃    Suggestion: Add input sanitization before processing ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ ⚠️  IMPORTANT (should address)                          ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 3. [Gemini-only] Single rate limit for all endpoints    ┃
┃    📁 Section: "Configuration"                          ┃
┃    Suggestion: Consider per-endpoint limits             ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 💡 SUGGESTIONS (optional)                               ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ [List suggestions with consensus tags]                  ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

**Consensus tag meanings**:
- `[Consensus]` - HIGH confidence: all 3 AIs identified this issue
- `[Claude+Codex]`, `[Claude+Gemini]`, `[Codex+Gemini]` - MEDIUM confidence: 2 of 3 agree
- `[Claude-only]`, `[Codex-only]`, `[Gemini-only]` - LOWER confidence: single AI finding

### Step 6: Prompt for Action

Present options to the user:

```
How would you like to proceed?

  [A] Address all findings (Recommended)
      I'll update the plan to address each issue

  [C] Address critical only
      Focus on critical issues (blocks approval)

  [P] Pick specific findings
      Choose which findings to address

  [S] Skip review
      Continue without changes
```

### Step 7: Address Findings with Clarification

For each finding to be addressed:

1. **Display finding details**:
   ```
   📝 Finding [N]/[Total]: [Description]
      📁 Section: "[Section Name]"
      Severity: [🔴 Critical / ⚠️  Important / 💡 Suggestion]
      Category: [Category]
      Source: [Consensus / Claude+Codex / Claude+Gemini / Codex+Gemini / Claude-only / Codex-only / Gemini-only]
   ```

2. **Ask clarification if needed** (see Clarification Rules above):

   For findings where reviewers suggest different approaches:
   ```
   ❓ How should this issue be addressed?
     [1] [Claude suggestion] (Claude recommends)
     [2] [Codex suggestion] (Codex recommends)
     [3] [Gemini suggestion] (Gemini recommends)
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

3. **Generate revision based on chosen approach**:
   ```
   Current plan text:
   > [Relevant section from plan]

   Proposed revision ([approach name]):
   > [Updated section addressing the finding]
   ```

4. **Get approval**:
   ```
   Apply this revision? [Y/n/a]
     Y = Yes, apply this revision
     n = No, skip this finding
     a = Apply all remaining revisions with default approaches
   ```

   If user selects `a`:
   - Set `SKIP_REMAINING_CLARIFICATIONS = true`
   - Apply default approach for all remaining findings
   - Show what's being applied but don't wait for individual approval

5. **Apply if approved**:
   - Use Edit tool to update the plan file
   - Track which findings have been addressed

#### Example Clarification Flow

```
📝 Finding 1/3: Missing Redis failure handling
   📁 Section: "Implementation"
   Severity: 🔴 Critical
   Category: error_handling
   Source: [Both]

   Codex suggests: Add fallback to allow requests when Redis is down
   Gemini suggests: Implement circuit breaker pattern for Redis

   ❓ How should Redis failures be handled?
     [1] Allow requests through with warning log (Codex)
     [2] Circuit breaker with automatic recovery (Gemini)
     [3] Combine: Circuit breaker + allow-through fallback
     [4] Let me specify...

User: 3

Claude: Using combined approach: circuit breaker + allow-through fallback.

        Current plan text (Implementation section):
        > ## Implementation
        > 1. Create RateLimiter class with Redis backend
        > 2. Implement check_rate_limit() method
        > 3. Return 429 when limit exceeded

        Proposed revision:
        > ## Implementation
        > 1. Create RateLimiter class with Redis backend
        > 2. Implement check_rate_limit() method
        > 3. Return 429 when limit exceeded
        > 4. **Graceful degradation**:
        >    - Add circuit breaker pattern for Redis connection
        >    - When circuit is open, allow requests with warning log
        >    - Auto-recovery when Redis becomes available

        Apply this revision? [Y/n/a]

User: Y

Claude: ✅ Applied revision to Implementation section.
```

### Step 8: Iteration (Optional)

After addressing findings, offer to re-run the review:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Round [N] complete. [X] findings addressed.
Session: [CODEX_PLAN_REVIEW_SESSION_ID] (context preserved)

Re-run Codex review to verify?
  [Y] Yes, verify fixes (Recommended)
  [N] No, I'm satisfied
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If user chooses to re-run:
1. Increment `REVIEW_ROUND`
2. Add addressed findings to `ADDRESSED_FINDINGS` list
3. Use `codex exec resume $CODEX_PLAN_REVIEW_SESSION_ID` (see Step 3, Round 2+)
4. This preserves full context from previous rounds

Continue iterating until:
- Codex returns `verdict: "approve"`
- All critical findings resolved
- User chooses to skip remaining

**Session fallback**: If session is not found or too old, fall back to creating a new session with a summary of previous rounds in the prompt.

### Step 9: Completion Summary and Session Cleanup

**MANDATORY**: This step MUST run before exiting the review workflow. Cleanup is triggered when ANY of:
- User chooses "No" to re-review in Step 8
- User chooses "Skip review" in Step 6
- All findings have been addressed
- Review workflow completes for any reason

After the review is complete (user satisfied or all critical findings resolved), clean up both Codex and Gemini sessions:

```bash
# Clean up Codex session file to free disk space (specific session only)
if [ -n "$CODEX_PLAN_REVIEW_SESSION_ID" ]; then
  find ~/.codex/sessions -name "*${CODEX_PLAN_REVIEW_SESSION_ID}*.jsonl" -delete 2>/dev/null
fi

# Clean up Gemini CLI session file (specific session only)
# Gemini session ID is captured at review start alongside Codex
if [ -n "$GEMINI_PLAN_REVIEW_SESSION_ID" ]; then
  find ~/.gemini/sessions -name "*${GEMINI_PLAN_REVIEW_SESSION_ID}*" -delete 2>/dev/null
  find ~/.config/gemini/sessions -name "*${GEMINI_PLAN_REVIEW_SESSION_ID}*" -delete 2>/dev/null
fi

# Clean up temporary review output files (always safe to delete)
rm -f /tmp/codex_plan_review_${PLAN_REVIEW_ID}.json /tmp/gemini_plan_review_${PLAN_REVIEW_ID}.json 2>/dev/null
```

Display the completion summary:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ✅ PLAN REVIEW COMPLETE                                 ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Rounds: [N]                                             ┃
┃ Findings addressed: [X] critical, [Y] important         ┃
┃ Findings skipped: [Z] suggestions                       ┃
┃                                                         ┃
┃ Plan file updated: [path/to/plan.md]                    ┃
┃                                                         ┃
┃ Sessions cleaned up:                                    ┃
┃   • Codex: Yes                                          ┃
┃   • Gemini: Yes                                         ┃
┃   • Temp files: Yes                                     ┃
┃                                                         ┃
┃ Next steps:                                             ┃
┃   • Start implementation: /tdd                          ┃
┃   • Review plan again: /plan-review                     ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

Clear session state:
```
PLAN_REVIEW_ID=""
CODEX_PLAN_REVIEW_SESSION_ID=""
GEMINI_PLAN_REVIEW_SESSION_ID=""
REVIEW_ROUND=1
ADDRESSED_FINDINGS=[]
SKIP_REMAINING_CLARIFICATIONS=false
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

### Authentication Error
```
❌ Codex authentication failed.

Run `codex login` to authenticate with your OpenAI account.
```

### Gemini Authentication Error
```
⚠️  Gemini authentication failed.

Run `gemini auth login` to authenticate with your Google account.

Continuing with Codex-only review...
```

### No Plan File Found
```
❌ No plan file found.

Either:
  1. Specify a path: /plan-review path/to/plan.md
  2. Create a plan in ~/.claude/plans/ directory
```

### Codex Timeout
```
⚠️  Codex review timed out after 60 seconds.

The plan may be too large. Consider:
  1. Splitting the plan into smaller sections
  2. Running /plan-review on specific sections
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
2. Include summary of previously addressed findings in the prompt
3. Continue review workflow normally

### Cleanup on Interruption

If the review is interrupted (user switches tasks, `/clear` is called, or session ends unexpectedly), sessions may not be cleaned up automatically.

**Manual cleanup command** (run if review was interrupted):
```bash
# List orphaned plan review temp files (review before deleting)
ls -la /tmp/codex_plan_review_*.json /tmp/gemini_plan_review_*.json 2>/dev/null

# Delete orphaned plan review temp files
rm -f /tmp/codex_plan_review_*.json /tmp/gemini_plan_review_*.json 2>/dev/null

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
- Temp files: `/tmp/codex_plan_review_${PLAN_REVIEW_ID}.json`, `/tmp/gemini_plan_review_${PLAN_REVIEW_ID}.json`

## Severity Definitions

| Severity | Description | Action Required |
|----------|-------------|-----------------|
| 🔴 Critical | Blocks approval. Security vulnerabilities, major architectural flaws, missing essential components | Must address before proceeding |
| ⚠️  Important | Should address. Missing error handling, performance concerns, incomplete sections | Recommended to address |
| 💡 Suggestion | Nice to have. Alternative approaches, style improvements, optional enhancements | User discretion |

## Example Session

```
User: /plan-review ~/.claude/plans/rate-limiting.md

Claude: 🔍 Reading plan file...
        📤 Launching Claude + Codex + Gemini analysis...
        ⏳ Running triple-AI parallel review...

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ 🤖 TRIPLE REVIEW: CLAUDE + CODEX + GEMINI               ┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃                                                         ┃
┃ Reviewers: Claude + Codex + Gemini                      ┃
┃ Findings: 3 total (1 consensus, 1 two-of-3, 1 single)   ┃
┃ Verdict: REQUEST_CHANGES                                ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 🔴 CRITICAL (1)                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 1. [Consensus] Missing Redis failure handling           ┃
┃    📁 Section: "Implementation"                         ┃
┃    Claude: Add circuit breaker with graceful degradation┃
┃    Codex: Add fallback to allow requests when down      ┃
┃    Gemini: Implement circuit breaker pattern            ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ ⚠️  IMPORTANT (1)                                        ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 2. [Claude+Gemini] Single rate limit for all endpoints  ┃
┃    📁 Section: "Configuration"                          ┃
┃    Consider per-endpoint limits for /api/chat vs /api/  ┃
┃    health.                                              ┃
┃                                                         ┃
┃ ─────────────────────────────────────────────────────── ┃
┃ 💡 SUGGESTIONS (1)                                      ┃
┃ ─────────────────────────────────────────────────────── ┃
┃                                                         ┃
┃ 3. [Codex-only] Consider sliding window algorithm       ┃
┃    📁 Section: "Algorithm"                              ┃
┃    Fixed window has thundering herd issues at window    ┃
┃    boundaries.                                          ┃
┃                                                         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

How would you like to proceed?
  [A] Address all findings (Recommended)
  [C] Address critical only
  [P] Pick specific findings
  [S] Skip review

User: A

Claude: 📝 Finding 1/3: Missing Redis failure handling
           📁 Section: "Implementation"
           Severity: 🔴 Critical
           Category: error_handling
           Source: [Both]

        Codex suggests: Add fallback to allow requests when Redis is down
        Gemini suggests: Implement circuit breaker pattern

        ❓ How should Redis failures be handled?
          [1] Allow requests through with warning log (Codex)
          [2] Circuit breaker with automatic recovery (Gemini)
          [3] Combine: Circuit breaker + allow-through fallback (Recommended)
          [4] Let me specify...

User: 3

Claude: Using combined approach: circuit breaker + allow-through fallback.

        Current plan text (Implementation section):
        > ## Implementation
        > 1. Create RateLimiter class with Redis backend
        > 2. Implement check_rate_limit() method
        > 3. Return 429 when limit exceeded

        Proposed revision:
        > ## Implementation
        > 1. Create RateLimiter class with Redis backend
        > 2. Implement check_rate_limit() method
        > 3. Return 429 when limit exceeded
        > 4. **Graceful degradation**:
        >    - Add circuit breaker pattern for Redis connection
        >    - When circuit is open, allow requests with warning log
        >    - Auto-recovery when Redis becomes available

        Apply this revision? [Y/n/a]

User: Y

Claude: ✅ Applied revision to Implementation section.

        📝 Finding 2/3: Single rate limit for all endpoints
        [...]
```

## Integration

- **After approval**: Use `/tdd` to begin implementation
- **If rejected**: Continue iterating or manually revise plan
- **Task tracking**: Findings can be converted to TodoWrite tasks

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
