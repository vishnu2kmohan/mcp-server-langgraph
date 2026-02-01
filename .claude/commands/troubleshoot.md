---
description: Diagnose issues with Multi-AI analysis (Claude + Gemini by default, +Codex with --heavy)
argument-hint: <issue description>
---
# Troubleshoot with Multi-AI Diagnosis

Diagnose and resolve issues using Claude (primary) plus Gemini CLI. Use `--heavy` to add Codex for triple-AI diagnostic accuracy.

## Usage

```bash
/troubleshoot <issue description>
/troubleshoot "issue" [file1.png] [file2.log]
/troubleshoot --allow-secrets "issue" .env
```

**Arguments**:
- `issue description` (required): Description of the problem to diagnose
- `file paths` (optional): Images, logs, or configs to include in analysis

**Flags**:
- `--light`: Claude Code only (fastest, 2 min timeout)
- `--medium`: Claude Code + Gemini (default, 5 min timeout)
- `--heavy`: Claude Code + Gemini + Codex (most thorough, 10 min timeout)
- `--timeout <duration>`: Override default timeout (e.g., `5m`, `90s`, `2min30sec`, `30s10m`). Must be a single token without spaces.
- `--allow-secrets`: Include sensitive files (`.env`, credentials) - use with caution

> **Breaking Change (v2.0)**: Default intensity changed from triple-AI to dual-AI.
> Use `--heavy` for full Claude + Gemini + Codex analysis, or set
> `TRIPLE_AI_DEFAULT_INTENSITY=heavy` environment variable.

## Key Differentiators

| Aspect | `/quick-debug` | `/plan-review` | `/troubleshoot` |
|--------|---------------|----------------|-----------------|
| AI Count | 1 (Claude) | 2 (Codex+Gemini) | 3 (All) |
| Purpose | Fast fix | Plan validation | Deep diagnosis |
| Mode | Immediate | Optional plan | Plan mode default |
| Output | Quick fix | Findings list | Diagnosis + plan |
| Scope | Known patterns | Plan document | Any issue |
| **Multimodal** | No | No | **Yes** (images, logs, PDFs) |
| **Multi-Round** | No | Yes | **Yes** (incremental artifacts) |

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

---

## Multi-AI Architecture

### Role Distribution

| AI | Role | Strengths | Web Capabilities |
|----|------|-----------|------------------|
| **Claude** | Orchestrator + Primary Analyst | Deep codebase context, session state, tool access | WebSearch, WebFetch (native) |
| **Codex** | Code-Level Diagnostician | Code reasoning, fix generation, pattern detection | `--search on` flag |
| **Gemini** | Context-Aware Investigator | 1M token context, broad patterns, alternative perspectives | google_web_search, web_fetch tools |

### Web Search Security

**IMPORTANT**: Web search is DISABLED when `--allow-secrets` is set to prevent data leakage.

```bash
# Determine if web search is safe
ENABLE_WEB_SEARCH=true
if [[ "$ALLOW_SECRETS" == "true" ]]; then
  ENABLE_WEB_SEARCH=false
  echo "NOTE: Web search disabled for all AIs (--allow-secrets is set)"
fi
```

**When web search is enabled**, AIs should use it to validate:
- Error messages and stack traces for known issues
- Infrastructure configuration best practices
- Library compatibility and version requirements

### Parallel Execution Flow

```
User: /troubleshoot "Tests fail with ConnectionError to Redis"
                |
    +-----------+-----------+
    v           v           v
  Claude     Codex       Gemini
 (primary)  (background) (background)
    |           |           |
    |     +-----+-----+     |
    |     v           v     |
    |   Code        Pattern |
    |   Analysis    Search  |
    |     |           |     |
    +-----+-----------+-----+
          v           v
      Reconcile Findings
          |
          v
    Unified Diagnosis + Plan
```

---

## Session State Tracking

Track diagnostic sessions across rounds for context preservation:

```
TROUBLESHOOT_ID=""               # Unique ID for this troubleshoot session
CODEX_DIAG_SESSION_ID=""         # Codex session UUID (from first invocation)
GEMINI_DIAG_SESSION_ID=""        # Gemini session UUID (from first invocation)
TROUBLESHOOT_ARTIFACTS=()        # All files from all rounds
TROUBLESHOOT_ROUND=1             # Current round number
TROUBLESHOOT_HISTORY=()          # Previous diagnoses for context
SESSION_TTL=3600                 # Session expiry: 1 hour
AI_INTENSITY="medium"            # Intensity level: light|medium|heavy (default: medium)
AI_TIMEOUT=300                   # Timeout in seconds (default: 5 min for medium)
```

**Generate unique session ID at start**:
```bash
# Generate unique ID for this troubleshoot session
TROUBLESHOOT_ID=$(date +%s%N)  # Nanosecond timestamp
```

**Temp file naming** (session-specific):
```
/tmp/codex_troubleshoot_${TROUBLESHOOT_ID}.json
/tmp/gemini_troubleshoot_${TROUBLESHOOT_ID}.json
```

---

## Multimodal Input Support

### Supported File Types

| Type | Extensions | Use Cases |
|------|------------|-----------|
| Images | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` | Error dialogs, stack traces, UI bugs |
| Logs | `.log`, `.txt` | Application logs, crash dumps |
| PDFs | `.pdf` | Documentation, error reports |
| Config | `.json`, `.yaml`, `.toml`, `.env` | Configuration files |

### CLI Syntax by Tool

| Tool | Syntax | Example |
|------|--------|---------|
| **Codex** | `--image, -i path[,path...]` | `codex exec --image error.png,trace.png "diagnose"` |
| **Gemini** | `@./path` inline in prompt | `"Analyze: @./screenshot.png @./error.log"` |
| **Claude** | Native via Read tool | Reads images directly from conversation |

### Security Settings (Read-Only Mode)

Both external reviewers run with minimal permissions:

| Reviewer | Sandbox Mode | Read Operations | Write Operations |
|----------|--------------|-----------------|------------------|
| Codex | `--sandbox read-only` + `disk-full-read-access` | All reads allowed (Landlock enforced) | Blocked by Landlock |
| Gemini | `--sandbox` + `--allowed-tools read_file` | read_file only (no shell) | Blocked by Docker |

**Key security features:**
- **Read access**: Both reviewers can read files within sandbox constraints
- **Write blocked**: All write operations blocked at OS/container level
- **No YOLO mode**: Gemini uses `--allowed-tools` (specific tools) not `--yolo`
- **Isolated execution**: Gemini runs in Docker, Codex uses Landlock sandbox
- **No network access**: Network disabled by default in both CLIs

---

## Workflow

### Step 0: Input Parsing with Security Validation

Parse `$ARGUMENTS` to extract issue description, file attachments, and intensity flags with security hardening:

```bash
# Parse human-friendly timeout to seconds (handles any order: 30s10m, 1h5s, etc.)
parse_timeout() {
  local input="$1"
  local total_seconds=0
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

# Security: Validate and sanitize all file paths
validate_path() {
  local path="$1"
  # Reject paths starting with '-' (option injection)
  [[ "$path" == -* ]] && return 1
  # Reject paths with shell metacharacters
  [[ "$path" =~ [\;\|\&\$\`\(\)\{\}] ]] && return 1
  # Reject directory traversal attempts
  [[ "$path" == *..* ]] && return 1
  # Reject symlinks (could point outside allowed directories)
  [[ -L "$path" ]] && return 1
  # Resolve path and check against allowed directories
  local resolved_path
  resolved_path=$(realpath -e "$path" 2>/dev/null) || return 1
  # Reject absolute paths outside allowed directories (check resolved path)
  if [[ "$resolved_path" == /* ]]; then
    [[ "$resolved_path" != /tmp/* && "$resolved_path" != "$HOME"/* && "$resolved_path" != "$PWD"/* ]] && return 1
  fi
  return 0
}

# Security: Check if file contains sensitive data
is_sensitive_file() {
  local path="$1"
  local basename=$(basename "$path")
  # Denylist for sensitive files (OWASP A02/A04)
  case "$basename" in
    .env|.env.*|*.pem|*.key|*credentials*|*secret*|*.p12|*.pfx)
      return 0 ;;  # Is sensitive
    *)
      return 1 ;;  # Not sensitive
  esac
}

# Detect and validate file arguments (use arrays for safety)
declare -a IMAGE_FILES=()
declare -a OTHER_FILES=()
declare -a SENSITIVE_FILES=()
DESCRIPTION=""
ALLOW_SECRETS=false

# Intensity flag parsing
AI_INTENSITY="${TRIPLE_AI_DEFAULT_INTENSITY:-medium}"
[[ -n "$TRIPLE_AI_DEFAULT_INTENSITY" && ! "$TRIPLE_AI_DEFAULT_INTENSITY" =~ ^(light|medium|heavy)$ ]] && AI_INTENSITY="medium"
INTENSITY_FLAG_COUNT=0
CUSTOM_TIMEOUT=""
TIMEOUT_FLAG_COUNT=0
SKIP_NEXT=false

# Split $ARGUMENTS into array for iteration
# (In Claude Code commands, $ARGUMENTS contains the user's input)
read -r -a args <<< "$ARGUMENTS"

for i in "${!args[@]}"; do
  if [[ "$SKIP_NEXT" == true ]]; then
    SKIP_NEXT=false
    continue
  fi

  arg="${args[$i]}"

  # Check for intensity flags first
  case "$arg" in
    --light)  AI_INTENSITY="light"; ((INTENSITY_FLAG_COUNT++)); continue ;;
    --medium) AI_INTENSITY="medium"; ((INTENSITY_FLAG_COUNT++)); continue ;;
    --heavy)  AI_INTENSITY="heavy"; ((INTENSITY_FLAG_COUNT++)); continue ;;
    --timeout)
      next_idx=$((i + 1))
      [[ -n "${args[$next_idx]}" ]] && { CUSTOM_TIMEOUT="${args[$next_idx]}"; ((TIMEOUT_FLAG_COUNT++)); SKIP_NEXT=true; continue; } || { echo "ERROR: --timeout requires a value"; exit 1; }
      ;;
    --timeout=*)
      CUSTOM_TIMEOUT="${arg#--timeout=}"
      [[ -z "$CUSTOM_TIMEOUT" ]] && { echo "ERROR: --timeout= requires a value"; exit 1; }
      ((TIMEOUT_FLAG_COUNT++))
      continue
      ;;
  esac

  # Check for --allow-secrets flag
  if [[ "$arg" == "--allow-secrets" ]]; then
    ALLOW_SECRETS=true
    continue
  fi

  # Validate path before processing
  if [[ -f "$arg" ]]; then
    if ! validate_path "$arg"; then
      echo "Warning: Rejected invalid path: $arg" >&2
      continue
    fi

    # Check for sensitive files
    if is_sensitive_file "$arg"; then
      if [[ "$ALLOW_SECRETS" == true ]]; then
        echo "Warning: Including sensitive file (--allow-secrets): $arg" >&2
      else
        SENSITIVE_FILES+=("$arg")
        echo "Blocked sensitive file: $arg (use --allow-secrets to override)" >&2
        continue
      fi
    fi

    if [[ "$arg" =~ \.(png|jpg|jpeg|gif|webp)$ ]]; then
      IMAGE_FILES+=("$arg")
    else
      OTHER_FILES+=("$arg")
    fi
  else
    DESCRIPTION="${DESCRIPTION:+$DESCRIPTION }$arg"
  fi
done

# Validate flags
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

# Build comma-separated image list (properly quoted)
IMAGE_FILES_CSV=""
for img in "${IMAGE_FILES[@]}"; do
  IMAGE_FILES_CSV="${IMAGE_FILES_CSV:+$IMAGE_FILES_CSV,}$img"
done
```

**Sensitive File Detection**:
```
+-----------------------------------------------------------+
| SENSITIVE FILES DETECTED                                  |
+-----------------------------------------------------------+
|                                                           |
| The following files were blocked from external AI:        |
|   * .env (environment secrets)                            |
|   * credentials.json (API keys)                           |
|                                                           |
| To include these files, re-run with --allow-secrets:      |
|   /troubleshoot --allow-secrets "issue" .env              |
|                                                           |
| WARNING: This sends secrets to external AI services       |
|                                                           |
+-----------------------------------------------------------+
```

### Step 1: Validate Input

Verify issue description is provided:

```
If DESCRIPTION is empty:
  Display error and usage example:

  Error: Issue description required.

  Usage:
    /troubleshoot "Tests fail with ConnectionError"
    /troubleshoot "UI button not responding" ./screenshot.png
    /troubleshoot ./error.log "API returning 500"
```

### Step 2: Categorize Issue Type

Analyze description to determine issue category:

| Category | Keywords | Examples |
|----------|----------|----------|
| test_failure | test, pytest, assert, fail | "pytest fails with ImportError" |
| runtime_error | error, exception, crash | "Application crashes on startup" |
| type_error | mypy, type, annotation | "mypy reports 50 type errors" |
| infrastructure | docker, redis, postgres, connection | "Redis connection timeout" |
| performance | slow, timeout, memory, hang | "API response time increased 10x" |
| ui_bug | ui, display, render, button | "Button not responding" |
| unknown | (default) | "Something is broken" |

### Step 3: Gather Context with Size Limits

Collect relevant context for analysis (Claude primary):

```bash
# Context size limits to prevent token overflow
MAX_GIT_LOG_LINES=10
MAX_TREE_DEPTH=3
MAX_LOG_BYTES=10000
MAX_FILE_SIZE=50000

# Gather context with size caps
gather_context() {
  # Git log (limited)
  GIT_CONTEXT=$(git log -"$MAX_GIT_LOG_LINES" --oneline 2>/dev/null | head -20)

  # Branch and status
  BRANCH=$(git branch --show-current 2>/dev/null)
  STATUS=$(git status --short 2>/dev/null | head -20)

  # Docker services (if available)
  DOCKER_CONTEXT=""
  if command -v docker-compose >/dev/null; then
    DOCKER_CONTEXT=$(docker-compose ps --format table 2>/dev/null | head -15)
  fi

  # Tree structure (limited depth)
  TREE_CONTEXT=$(tree -L "$MAX_TREE_DEPTH" --noreport -I 'node_modules|.git|__pycache__|.venv' 2>/dev/null | head -50)

  # Logs (truncated to size limit)
  LOG_CONTEXT=""
  if [[ -f "logs/app.log" ]]; then
    LOG_CONTEXT=$(tail -c "$MAX_LOG_BYTES" logs/app.log 2>/dev/null)
  fi
}

# Summarize large content before sending to AI
summarize_if_large() {
  local content="$1"
  local max_size="$2"
  local label="$3"

  if [[ ${#content} -gt $max_size ]]; then
    echo "[$label truncated: showing last $max_size chars of ${#content}]"
    echo "${content: -$max_size}"
  else
    echo "$content"
  fi
}
```

**Context sources:**
- Recent git changes (`git log -10 --oneline`, max 20 lines)
- Current branch and status
- Active services (`docker-compose ps`, max 15 lines)
- Python environment validation
- Repository tree (depth 3, excluding node_modules/.git/.venv)
- Attached artifacts (images, logs, configs)

### Step 4: Verify External AI CLIs (Intensity-Conditional)

Before invoking external reviewers, verify CLIs based on intensity level. This is an **Agent-level workflow**:

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

### Step 5: Invoke AI Analysis (Intensity-Conditional)

**Execution: Use Claude's Native Background Tasks**

Run external AIs based on intensity level using Claude's `run_in_background=true`:

**Conditional invocation pattern:**
```bash
# Claude always runs (primary analyst)
# Claude performs analysis using Read tool and session context

# Launch Gemini (unless --light)
if [[ "$AI_INTENSITY" != "light" ]]; then
  # Gemini invocation as background task
fi

# Launch Codex (only if --heavy)
if [[ "$AI_INTENSITY" == "heavy" ]]; then
  # Codex invocation as background task
fi
```

1. **Launch external reviewers** as separate Bash tool calls with `run_in_background=true` (based on intensity)
2. **DO NOT** use shell output redirection (`>` or `| tee`) - let stdout flow to Claude's task output
3. **Use TaskOutput** to retrieve results after completion

```
# Parallel execution pattern:
Bash(run_in_background=true): codex exec ... "prompt"  -> task_id: abc123
Bash(run_in_background=true): gemini ... "prompt"      -> task_id: def456

# Claude performs primary analysis concurrently

# Then retrieve results:
TaskOutput(task_id="abc123") -> Codex diagnosis JSON
TaskOutput(task_id="def456") -> Gemini diagnosis JSON
```

#### Codex Invocation (Security-Hardened, Multimodal)

```bash
# Build command using arrays for injection safety
declare -a CODEX_CMD=(
  codex exec
  --sandbox read-only
  --skip-git-repo-check
  -c 'sandbox_permissions=["disk-full-read-access"]'
  -C "$(pwd)"
)

# Add images if present (using validated array)
if [[ ${#IMAGE_FILES[@]} -gt 0 ]]; then
  CODEX_CMD+=(--image "$IMAGE_FILES_CSV")
fi

# Use -- to terminate options before user-provided prompt
CODEX_CMD+=(--)

# Escape user description for safe interpolation
SAFE_DESCRIPTION=$(printf '%q' "$DESCRIPTION")

# Execute with timeout and error handling
timeout $AI_TIMEOUT "${CODEX_CMD[@]}" "Diagnose this issue: $SAFE_DESCRIPTION

${IMAGE_FILES_CSV:+[Attached images show the error/issue - analyze them carefully]}

Context:
- Repository: $(pwd)
- Recent changes: [git log output]
- Branch: $(git branch --show-current)
- Issue Category: [category]

Analyze the codebase for:
1. Root cause identification (use attached images if present)
2. Affected files and lines
3. Potential fixes (with code snippets)
4. Similar patterns that may also be affected

<output_schema>
{
  \"root_cause\": \"string\",
  \"confidence\": 0.0-1.0,
  \"image_analysis\": \"string (if images attached)\",
  \"affected_files\": [{\"path\": \"\", \"lines\": [], \"issue\": \"\"}],
  \"fixes\": [{\"file\": \"\", \"description\": \"\", \"code\": \"\"}],
  \"related_issues\": [\"string\"],
  \"requires_infrastructure\": boolean
}
</output_schema>

Return valid JSON only."
```

**Security Notes:**
- Uses bash arrays to prevent word splitting and glob expansion
- `--` terminates options to prevent `-` prefixed descriptions from being parsed as flags
- `printf '%q'` escapes shell metacharacters in user input
- Timeout prevents runaway processes

#### Gemini Invocation (Security-Hardened, Multimodal @ Syntax)

```bash
# Build file references for Gemini using @ syntax (from validated arrays)
GEMINI_FILE_REFS=""
for img in "${IMAGE_FILES[@]}"; do
  # Validate path is safe before including
  if validate_path "$img"; then
    GEMINI_FILE_REFS="${GEMINI_FILE_REFS} @./$img"
  fi
done
for file in "${OTHER_FILES[@]}"; do
  if validate_path "$file"; then
    GEMINI_FILE_REFS="${GEMINI_FILE_REFS} @./$file"
  fi
done

# Escape user description
SAFE_DESCRIPTION=$(printf '%q' "$DESCRIPTION")

# Build command with arrays
declare -a GEMINI_CMD=(
  gemini
  --model gemini-3-pro-preview
  --sandbox
  --allowed-tools read_file
)

# Note: run_shell_command removed - Gemini acts as read-only analyzer (least-privilege)

# SANDBOX_FLAGS mounts ADC for Vertex AI auth
export SANDBOX_FLAGS="-v $HOME/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json"

# Execute with timeout
timeout $AI_TIMEOUT "${GEMINI_CMD[@]}" --prompt "Diagnose this issue: $SAFE_DESCRIPTION

${GEMINI_FILE_REFS:+Attached files to analyze: $GEMINI_FILE_REFS}

Context:
- Repository structure: [tree output]
- Error patterns: [relevant logs]
- Configuration: [relevant configs]
- Issue Category: [category]

Investigate:
1. Environmental factors (Python version, deps, Docker)
2. Configuration issues (.env, settings, docker-compose)
3. Dependency conflicts or version mismatches
4. Infrastructure/service health
5. Alternative root causes beyond the obvious
${GEMINI_FILE_REFS:+6. Visual analysis of attached screenshots/images}

<output_schema>
{
  \"diagnosis\": \"string\",
  \"image_findings\": \"string (OCR/visual analysis if images attached)\",
  \"environmental_factors\": [{\"factor\": \"\", \"status\": \"ok|warning|error\", \"detail\": \"\"}],
  \"config_issues\": [{\"file\": \"\", \"issue\": \"\", \"fix\": \"\"}],
  \"infrastructure_checks\": [{\"service\": \"\", \"status\": \"\", \"action\": \"\"}],
  \"alternative_causes\": [\"string\"],
  \"recommended_order\": [\"step1\", \"step2\", ...]
}
</output_schema>

Return valid JSON only."
```

**Security Notes:**
- Uses bash arrays to prevent injection
- Removed `run_shell_command` - Gemini acts as read-only analyzer (least-privilege)
- All file paths validated before inclusion
- Timeout prevents runaway processes

#### Claude Primary Analysis

While external AIs run in background, Claude performs primary analysis:

- Read relevant files based on issue description
- Check `.claude/memory/` for known patterns
- Analyze test failures if applicable
- Cross-reference with recent-work.md
- Read attached images/files directly

### Step 6: Capture Session IDs

After initial invocation, capture session IDs for potential multi-round troubleshooting:

```bash
# Capture session ID from most recent Codex session
CODEX_DIAG_SESSION_ID=$(ls -t ~/.codex/sessions/$(date +%Y)/*/*/*.jsonl 2>/dev/null | head -1 | xargs -I{} basename {} .jsonl | grep -oP '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' | head -1)

# Capture session ID from most recent Gemini session
GEMINI_DIAG_SESSION_ID=$(ls -t ~/.gemini/sessions/*.json ~/.config/gemini/sessions/*.json 2>/dev/null | head -1 | xargs -I{} basename {} .json | grep -oP '[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}' | head -1)
```

### Step 7: Reconcile Findings

After all three AIs complete analysis, merge and reconcile their findings.

#### Error Handling and Timeouts

```bash
# Per-tool timeout configuration
CODEX_TIMEOUT=120   # seconds
GEMINI_TIMEOUT=120  # seconds
MAX_RETRIES=2
RETRY_BACKOFF=5     # seconds

# Retry with exponential backoff
invoke_with_retry() {
  local cmd="$1"
  local timeout="$2"
  local retries=0

  while [[ $retries -lt $MAX_RETRIES ]]; do
    if timeout "$timeout" bash -c "$cmd"; then
      return 0
    fi
    retries=$((retries + 1))
    echo "Warning: Retry $retries/$MAX_RETRIES after ${RETRY_BACKOFF}s..." >&2
    sleep $((RETRY_BACKOFF * retries))
  done
  return 1
}

# Check tool availability before invoking
check_tools() {
  local missing=()
  command -v codex >/dev/null || missing+=("codex")
  command -v gemini >/dev/null || missing+=("gemini")

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Warning: Missing tools: ${missing[*]}" >&2
    echo "   Continuing with available AIs..." >&2
  fi
}
```

#### Parse AI Outputs with JSON Validation

```bash
# Validate JSON structure against expected schema
validate_response() {
  local json="$1"
  local source="$2"

  # Check if valid JSON
  if ! echo "$json" | jq empty 2>/dev/null; then
    echo "Warning: [$source] Invalid JSON response, attempting salvage..." >&2
    # Try to extract JSON from markdown code blocks
    json=$(echo "$json" | sed -n '/```json/,/```/p' | sed '1d;$d')
    if ! echo "$json" | jq empty 2>/dev/null; then
      echo "Error: [$source] Could not parse response" >&2
      return 1
    fi
  fi

  echo "$json"
}
```

#### Graceful Degradation

```
If Codex fails:
  -> Continue with Gemini + Claude only
  -> Annotate findings with [Gemini+Claude] (reduced confidence)

If Gemini fails:
  -> Continue with Codex + Claude only
  -> Annotate findings with [Codex+Claude] (reduced confidence)

If both fail:
  -> Claude-only diagnosis
  -> Display warning: "External AI unavailable, using Claude analysis only"
```

#### Merge Findings (Intensity-Dependent)

**--heavy (3 AIs)**:
```
For each finding:
  - If all 3 AIs agree -> [Consensus] tag (HIGH confidence)
  - If 2 AIs agree -> [Codex+Gemini] or [Claude+X] tag (MEDIUM confidence)
  - If only 1 AI found -> [Codex-only] etc. (LOWER confidence, still valid)
```

**--medium (2 AIs)**:
```
For each finding:
  - If Claude+Gemini agree -> [Consensus] tag (HIGH confidence)
  - If only Claude found -> [Claude-only]
  - If only Gemini found -> [Gemini-only]
```

**--light (1 AI)**:
```
All findings tagged [Claude] (no consensus possible)
```

#### Prioritize Findings By

1. **Confidence** (consensus > partial > single)
2. **Impact** (infrastructure > code > config)
3. **Fix complexity** (quick wins first)

### Step 8: Display Diagnosis

#### Dynamic Header Based on Intensity

```bash
# Generate header based on which AIs participated
case "$AI_INTENSITY" in
  light)
    HEADER="CLAUDE DIAGNOSIS"
    PARTICIPANTS="Claude"
    ;;
  medium)
    HEADER="DUAL-AI DIAGNOSIS: CLAUDE + GEMINI"
    PARTICIPANTS="Claude, Gemini"
    ;;
  heavy)
    HEADER="TRIPLE-AI DIAGNOSIS: CLAUDE + CODEX + GEMINI"
    PARTICIPANTS="Claude, Codex, Gemini"
    ;;
esac
```

Display reconciled findings in a structured format:

```
+-----------------------------------------------------------+
| [HEADER]                                                  |
+-----------------------------------------------------------+
| PARTICIPANTS: [PARTICIPANTS]                              |
| Issue: [issue description]                                |
| Confidence: [HIGH/MEDIUM/LOW]                             |
| Root Cause: [primary diagnosis]                           |
+-----------------------------------------------------------+

----------------------------------------------------------------
 ROOT CAUSE
----------------------------------------------------------------

[Consensus] Redis service not running

All three AIs identified Redis as the primary issue:
  * Claude: Detected ConnectionError in test logs
  * Codex: Found missing Redis health check in conftest.py
  * Gemini: Confirmed docker-compose shows Redis down

----------------------------------------------------------------
 CONTRIBUTING FACTORS
----------------------------------------------------------------

1. [Claude+Codex] Missing retry logic in session store
   File: src/auth/session.py:42
   Fix: Add tenacity retry decorator

2. [Gemini] Stale Redis connection pool
   File: src/core/redis.py:15
   Fix: Implement connection pool health checks

----------------------------------------------------------------
 ENVIRONMENTAL
----------------------------------------------------------------

[OK] Python version: 3.12.4
[OK] Dependencies: All installed
[ERROR] Docker: Redis container not running
[WARNING] Config: REDIS_URL points to localhost (not Docker network)

----------------------------------------------------------------
 RECOMMENDATIONS
----------------------------------------------------------------

1. Start Redis service
2. Update REDIS_URL in .env
3. Add connection retry logic
4. Add health check to conftest.py
```

### Step 9: Generate Action Plan

Based on reconciled findings, generate a structured action plan for plan mode:

#### Finding Categories and Icons

- ROOT CAUSE - Primary issue identified
- CONTRIBUTING FACTORS - Secondary issues
- ENVIRONMENTAL - Infrastructure/config
- RECOMMENDATIONS - Preventive measures

#### Generate TodoWrite Tasks

```
[ ] Fix: [primary fix] - [file:line]
[ ] Verify: Run [test command] to confirm fix
[ ] Check: [environmental factor] if primary fix fails
[ ] Prevent: [add test/validation to prevent recurrence]
```

#### Plan Mode Integration

- Write diagnosis to plan file (if in plan mode)
- Include all three AI perspectives
- Provide step-by-step resolution path

### Step 10: Multi-Round Support (Incremental Artifacts)

Frontend troubleshooting often requires multiple rounds with new screenshots at each step.

**Flow:**
```
Round 1: /troubleshoot "Button not responding" ./initial-state.png
  -> Diagnosis: "Check event handler binding"
  -> User tests fix, issue persists

Round 2: User drags in new screenshot showing console errors
  -> Claude detects new image in conversation
  -> Forwards to Codex: codex exec resume $SESSION_ID --image console-error.png
  -> Forwards to Gemini: gemini --resume $GEMINI_SESSION_ID --prompt "..."
  -> Updated diagnosis with new context

Round 3: User adds image of UI state
  -> Both AIs receive new image via session resume
  -> Comprehensive fix plan generated
```

**On new artifact in conversation:**
```bash
add_artifact() {
  local new_file="$1"

  # Validate path before adding
  if ! validate_path "$new_file"; then
    echo "Warning: Rejected invalid artifact path: $new_file" >&2
    return 1
  fi

  TROUBLESHOOT_ARTIFACTS+=("$new_file")
  TROUBLESHOOT_ROUND=$((TROUBLESHOOT_ROUND + 1))

  # Get previous diagnosis safely (portable - avoid bash 4.3+ negative indexing)
  local prev_diagnosis=""
  if ((${#TROUBLESHOOT_HISTORY[@]} > 0)); then
    local last_idx=$((${#TROUBLESHOOT_HISTORY[@]} - 1))
    prev_diagnosis="${TROUBLESHOOT_HISTORY[$last_idx]}"
  fi

  # Determine if file is an image (for Codex --image flag)
  local is_image=false
  if [[ "$new_file" =~ \.(png|jpg|jpeg|gif|webp)$ ]]; then
    is_image=true
  fi

  # Resume Codex session with new artifact
  if [[ -n "$CODEX_DIAG_SESSION_ID" ]]; then
    if [[ "$is_image" == true ]]; then
      # Use --image flag for image files
      timeout $AI_TIMEOUT codex exec resume "$CODEX_DIAG_SESSION_ID" \
        --image "$new_file" \
        -- "New image artifact provided. Previous diagnosis: $prev_diagnosis.
         Analyze this new visual evidence and update your diagnosis."
    else
      # For non-image files, instruct Codex to read the file
      timeout $AI_TIMEOUT codex exec resume "$CODEX_DIAG_SESSION_ID" \
        -- "New artifact provided at path: $new_file
         Previous diagnosis: $prev_diagnosis.
         Read the file and analyze this new evidence to update your diagnosis."
    fi
  fi

  # Resume Gemini session with new artifact (Gemini handles all file types via @)
  if [[ -n "$GEMINI_DIAG_SESSION_ID" ]]; then
    timeout $AI_TIMEOUT gemini \
      --resume "$GEMINI_DIAG_SESSION_ID" \
      --model gemini-3-pro-preview \
      --sandbox \
      --allowed-tools read_file \
      --prompt "New artifact provided: @./$new_file
       Previous diagnosis: $prev_diagnosis.
       Analyze this new evidence and update your diagnosis."
  fi
}
```

**Claude's Role in Multi-Round:**
- Detects new images/files added to conversation
- Maintains running context of previous diagnoses
- Decides when to re-invoke Codex/Gemini vs. proceed with current info
- Synthesizes findings across all rounds into unified action plan

### Step 11: Session Cleanup

**MANDATORY**: This step MUST run before exiting the troubleshoot workflow.

```bash
# Cleanup sessions on completion (intensity-conditional)
cleanup_sessions() {
  # Only clean up Gemini if it was used (medium or heavy)
  if [[ "$AI_INTENSITY" != "light" && -n "$GEMINI_DIAG_SESSION_ID" ]]; then
    find ~/.gemini/sessions ~/.config/gemini/sessions -name "*${GEMINI_DIAG_SESSION_ID}*" -delete 2>/dev/null
  fi

  # Only clean up Codex if it was used (heavy only)
  if [[ "$AI_INTENSITY" == "heavy" && -n "$CODEX_DIAG_SESSION_ID" ]]; then
    find ~/.codex/sessions -name "*${CODEX_DIAG_SESSION_ID}*.jsonl" -delete 2>/dev/null
  fi

  rm -f /tmp/troubleshoot_${TROUBLESHOOT_ID}_*.json 2>/dev/null
}
```

Display completion summary:

```
+-----------------------------------------------------------+
| TROUBLESHOOT COMPLETE                                     |
+-----------------------------------------------------------+
|                                                           |
| Rounds: [N]                                               |
| Artifacts analyzed: [X] images, [Y] logs                  |
| Root cause identified: [YES/NO]                           |
|                                                           |
| Sessions cleaned up:                                      |
|   * Codex: Yes                                            |
|   * Gemini: Yes                                           |
|   * Temp files: Yes                                       |
|                                                           |
| Next steps:                                               |
|   * Apply fix: [primary action]                           |
|   * Run tests: uv run --frozen pytest -x                  |
|   * Commit: /commit                                       |
|                                                           |
+-----------------------------------------------------------+
```

Clear session state:
```
TROUBLESHOOT_ID=""
CODEX_DIAG_SESSION_ID=""
GEMINI_DIAG_SESSION_ID=""
TROUBLESHOOT_ROUND=1
TROUBLESHOOT_ARTIFACTS=()
TROUBLESHOOT_HISTORY=()
```

---

## Error Handling

### Codex CLI Not Installed
```
Error: Codex CLI not found.

To install:
  npm install -g @openai/codex-cli

Then authenticate:
  codex login

Continuing with Gemini + Claude...
```

### Gemini CLI Not Installed
```
Warning: Gemini CLI not found.

To install:
  npm install -g @google/gemini-cli

Then authenticate:
  gemini auth login

Continuing with Codex + Claude...
```

### Both External AIs Failed
```
Warning: External AI unavailable.

Both Codex and Gemini failed to respond. Causes:
  * Network connectivity issues
  * Authentication expired
  * Rate limit exceeded

Continuing with Claude-only diagnosis...
This may have reduced diagnostic accuracy.
```

### Timeout Errors
```
Warning: [Codex/Gemini] timed out after 120 seconds.

The issue may be complex. Try:
  1. Simplify the issue description
  2. Reduce attached file sizes
  3. Re-run with --verbose for details
```

### Session Not Found (Multi-Round)
```
Warning: Previous session not found. Starting fresh diagnosis.

This can happen if:
  * Session file was deleted
  * Session is too old (>1 hour TTL)
  * CLI was updated

Continuing with new session...
```

### Cleanup on Interruption

If troubleshooting is interrupted, sessions may not be cleaned up automatically.

**Manual cleanup command**:
```bash
# List orphaned troubleshoot temp files
ls -la /tmp/troubleshoot_*.json /tmp/codex_troubleshoot_*.json /tmp/gemini_troubleshoot_*.json 2>/dev/null

# Delete orphaned temp files
rm -f /tmp/troubleshoot_*.json /tmp/codex_troubleshoot_*.json /tmp/gemini_troubleshoot_*.json 2>/dev/null

# List recent Codex sessions
find ~/.codex/sessions -type f -mmin -60 -name "*.jsonl" -ls

# List recent Gemini sessions
find ~/.gemini/sessions ~/.config/gemini/sessions -type f -mmin -60 -name "*.json" -ls 2>/dev/null
```

---

## Privacy and Data Handling

**Data Flow:**
```
User Input -> Claude (local) -> Codex (OpenAI) + Gemini (Google)
                              |
                         External AI Services
```

**What is sent to external services:**
- Issue description (required)
- Attached images/files (if provided and not blocked)
- Repository context (limited, see size caps)
- Git log summary (last 10 commits)

**What is NOT sent:**
- `.env` files (blocked by default)
- Credential files (`*.pem`, `*.key`, `credentials*`)
- Full repository contents (only relevant context)
- Session history from other troubleshoot sessions

**User control:**
- `--allow-secrets`: Opt-in to send sensitive files (with warning)
- All file paths are validated before transmission
- Session data is cleaned up after 1 hour TTL

**Compliance notes:**
- No PII is logged by the troubleshoot command
- External AI provider policies apply (OpenAI, Google)
- Users should review their organization's AI usage policies

---

## Severity Definitions

| Severity | Description | Tag |
|----------|-------------|-----|
| HIGH | All 3 AIs agree on diagnosis | [Consensus] |
| MEDIUM | 2 of 3 AIs agree | [Claude+Codex] etc. |
| LOW | Single AI finding | [Codex-only] etc. |

---

## Example Sessions

### Example 1: Basic Troubleshooting

```
User: /troubleshoot "pytest fails with ImportError"

Claude: Analyzing issue: "pytest fails with ImportError"
        Category: test_failure

        Gathering context...
        Launching Codex + Gemini in parallel...
        Running Claude primary analysis...

        [Waiting for external AIs...]

+-----------------------------------------------------------+
| TRIPLE-AI DIAGNOSIS: CLAUDE + CODEX + GEMINI              |
+-----------------------------------------------------------+
| Issue: pytest fails with ImportError                      |
| Confidence: HIGH                                          |
| Root Cause: Missing function in uncommitted changes       |
+-----------------------------------------------------------+

----------------------------------------------------------------
 ROOT CAUSE
----------------------------------------------------------------

[Consensus] Function 'get_session_store' exists in working copy
but is not committed.

All three AIs identified the same root cause:
  * Claude: Found function in src/auth/session.py:42
  * Codex: Detected uncommitted changes in session.py
  * Gemini: Confirmed git status shows modified session.py

----------------------------------------------------------------
 ACTION PLAN
----------------------------------------------------------------

[ ] Commit missing changes
    git add src/mcp_server_langgraph/auth/session.py
    git commit -m "feat: add session store functions"

[ ] Verify fix
    uv run --frozen pytest tests/test_auth.py -v

[ ] Prevent recurrence
    Add pre-commit hook to check for uncommitted imports

Proceed with fix? [Y/n]
```

### Example 2: With Screenshot

```
User: /troubleshoot "UI button not responding" ./error-dialog.png

Claude: Analyzing issue with 1 attached image
        Category: ui_bug

        [Sending image to Codex...]
        [Sending image to Gemini...]
        [Analyzing locally with Claude...]

+-----------------------------------------------------------+
| TRIPLE-AI DIAGNOSIS: CLAUDE + CODEX + GEMINI              |
+-----------------------------------------------------------+
| Issue: UI button not responding                           |
| Confidence: HIGH                                          |
| Root Cause: Event handler not bound                       |
+-----------------------------------------------------------+

----------------------------------------------------------------
 IMAGE ANALYSIS
----------------------------------------------------------------

Codex detected: "TypeError: Cannot read property 'onClick' of undefined"
Gemini OCR: Console shows "Uncaught TypeError at Button.tsx:23"

----------------------------------------------------------------
 ROOT CAUSE
----------------------------------------------------------------

[Consensus] Button onClick handler is undefined

  * Claude: Button component missing onClick prop
  * Codex: Handler defined but not passed to component
  * Gemini: Parent component doesn't bind handler

Fix: Add onClick handler binding in parent component

----------------------------------------------------------------
 AFFECTED FILES
----------------------------------------------------------------

1. src/studio/components/Button.tsx:23
   Issue: onClick prop used but not defined
   Fix: Add onClick to component props

2. src/studio/pages/Dashboard.tsx:45
   Issue: Handler defined but not passed
   Fix: Pass onClick prop to Button

Proceed with fix? [Y/n]
```

### Example 3: Multi-Round with New Artifacts

```
User: /troubleshoot "API returning 500"

Claude: [Round 1 diagnosis...]

        Root cause: Missing database connection

User: [Drags in new screenshot showing database logs]

Claude: Detected new artifact: ./db-logs.png
        Round 2: Updating diagnosis with new evidence...

        [Re-analyzing with Codex + Gemini...]

+-----------------------------------------------------------+
| TRIPLE-AI DIAGNOSIS: UPDATED (Round 2)                    |
+-----------------------------------------------------------+
| Previous: Missing database connection                     |
| Updated: Database connection pool exhausted               |
| New Evidence: db-logs.png shows max_connections reached   |
+-----------------------------------------------------------+

Updated Fix:
  1. Increase max_pool_size in database config
  2. Add connection pool monitoring
  3. Implement connection cleanup on request end
```

### Example 4: Sensitive File Warning

```
User: /troubleshoot "API auth failing" .env

Claude:
+-----------------------------------------------------------+
| SENSITIVE FILES DETECTED                                  |
+-----------------------------------------------------------+
|                                                           |
| The following files were blocked from external AI:        |
|   * .env (environment secrets)                            |
|                                                           |
| To include these files, re-run with --allow-secrets:      |
|   /troubleshoot --allow-secrets "API auth failing" .env   |
|                                                           |
| WARNING: This sends secrets to external AI services       |
|                                                           |
+-----------------------------------------------------------+

Continuing diagnosis without .env file...
```

---

## Integration

- **Before**: Use `/quick-debug` for known patterns (faster)
- **After**: Use `/tdd` to implement fixes
- **Verification**: Use `/validate` to confirm fixes
- **Commit**: Use `/commit` when ready

---

## Related Commands

| Command | Use Case |
|---------|----------|
| `/quick-debug` | Fast single-AI debugging (simpler cases) |
| `/plan-review` | Plan validation (after troubleshoot generates plan) |
| `/code-review` | Code validation (before committing fixes) |
| `/test-failure-analysis` | Deep test failure analysis (can feed into troubleshoot) |
| `/validate` | Run all validations after fix |

---

## Configuration

**Models**:
- Claude: Current session model (opus-4.5)
- Codex: Uses defaults from `~/.codex/config.toml` (typically gpt-5.2-codex)
- Gemini: Uses `gemini-3-pro-preview` via Gemini CLI

**Timeouts**:
- Per-AI timeout: 120 seconds
- Total timeout: 300 seconds (5 minutes)
- Session TTL: 3600 seconds (1 hour)

**Free Tier Limits** (Gemini):
- 60 requests/min, 1,000 requests/day
- 1M token context window

---

## Prompt Best Practices Sources

The prompts in this command follow official best practices:

- [Codex Prompting Guide](https://cookbook.openai.com/examples/gpt-5/codex_prompting_guide) - Autonomous, action-biased
- [Codex CLI Image Support](https://developers.openai.com/codex/cli/reference/) - `--image` flag usage
- [Gemini 3 Prompting Guide](https://ai.google.dev/gemini-api/docs/gemini-3) - Direct, concise
- [Gemini CLI File Input](https://addyosmani.com/blog/gemini-cli/) - `@` file syntax
- [Gemini Image Understanding](https://ai.google.dev/gemini-api/docs/image-understanding) - Multimodal analysis

---

**Last Updated**: 2026-01-31
**Command Version**: 1.0
**AI Systems**: Claude (Opus 4.5) + Codex (GPT-5.2) + Gemini (3 Pro)
