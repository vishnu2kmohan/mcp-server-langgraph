# AI CLI Tool Patterns

**Purpose**: Document correct patterns for invoking Codex and Gemini CLIs safely
**Last Updated**: 2026-01-31
**Verified against**: Codex CLI v0.92.0, Gemini CLI v0.26.0

---

## Overview

When invoking external AI CLI tools (Codex, Gemini), security is paramount:
- **Codex**: Uses Landlock sandbox (`--sandbox read-only`) to block writes at OS level
- **Gemini**: Uses Docker sandbox (`--sandbox`) with `--allowed-tools` to control tool access
- **Never use**: `--yolo` (Gemini) or `--dangerously-bypass-approvals-and-sandbox` (Codex)

---

## Codex CLI

### Verified Flags (from `codex exec --help`)

| Flag | Purpose |
|------|---------|
| `--sandbox <mode>` | `read-only`, `workspace-write`, `danger-full-access` |
| `--skip-git-repo-check` | Allow running outside Git repo |
| `-C <dir>` | Change working directory |
| `-c <key=value>` | Override config values |
| `--output-schema <file>` | JSON schema for response |
| `-o, --output-last-message <file>` | Write last message to file |

### Safe Read-Only Code Review

```bash
codex exec \
  --sandbox read-only \
  --skip-git-repo-check \
  -C "$(pwd)" \
  "Your prompt here"
```

**How `--sandbox read-only` works:**
- Landlock (Linux kernel security) enforces read-only access
- All file writes are blocked at OS level
- Git read commands (diff, status, log) work fine
- Git write commands (push, commit, etc.) are blocked

**Landlock Kernel Requirement**:
- Requires `CONFIG_SECURITY_LANDLOCK=y` in kernel config
- Requires `landlock` in LSM boot parameter: `lsm=landlock,capability,yama`
- Check availability: `cat /sys/kernel/security/landlock/abi_version`
- If unavailable, Codex falls back to file read tools (no shell execution)

**Note**: There is NO `--rules` flag. The sandbox mode itself controls permissions.

---

## Gemini CLI

### Verified Flags (from `gemini --help`)

| Flag | Purpose |
|------|---------|
| `-s, --sandbox` | Enable Docker sandbox (boolean) |
| `--allowed-tools <tools...>` | Tools allowed without confirmation (array) |
| `--approval-mode <mode>` | `default`, `auto_edit`, `yolo`, `plan` |
| `-p, --prompt <string>` | Prompt for headless mode |
| `-m, --model <string>` | Model to use |
| `-o, --output-format <format>` | `text`, `json`, `stream-json` |

### Valid Tool Names for `--allowed-tools`

| Tool Name | Description |
|-----------|-------------|
| `read_file` | Read file contents |
| `write_file` | Create/modify files |
| `edit` | Edit file contents |
| `run_shell_command` | Execute shell commands |
| `web_fetch` | Retrieve content from URLs |
| `google_web_search` | Search the web |
| `save_memory` | Store information across sessions |
| `write_todos` | Manage subtasks |
| `activate_skill` | Activate Agent Skills |

### Safe Read-Only Review

**CRITICAL**: The `--sandbox` Docker container cannot access host ADC credentials by default.
You MUST mount the ADC file using `SANDBOX_FLAGS`:

```bash
# Mount ADC credentials into the sandbox container
# For git worktrees, also mount the git common directory
GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null)
export SANDBOX_FLAGS="-v $HOME/.config/gcloud/application_default_credentials.json:${TMPDIR:-/tmp}/adc.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=${TMPDIR:-/tmp}/adc.json -v ${GIT_COMMON_DIR}:${GIT_COMMON_DIR}:ro"

# Use stdin for prompt (piped from echo)
# Use REPEATED --allowed-tools flags (space-separated causes parsing issues)
echo "Your prompt here" | gemini \
  --model gemini-3-pro-preview \
  --output-format json \
  --sandbox \
  --allowed-tools run_shell_command \
  --allowed-tools read_file
```

**How it works:**
- `--sandbox` runs commands in Docker container (blocks writes)
- `--allowed-tools` must be repeated for each tool (array syntax causes parsing issues)
- Prompt via stdin (echo pipe) avoids conflicts with --allowed-tools array
- `SANDBOX_FLAGS` mounts ADC file and git common dir into container
- Sandbox restricts what `run_shell_command` can do (no writes)

**Common Pitfalls**:
1. Using `--allowed-tools tool1 tool2` (space-separated) causes the second tool to be
   interpreted as a positional prompt. Use repeated flags instead.
2. Git worktrees need the common .git directory mounted for git commands to work.

### Forbidden Flags

| Flag | Why Forbidden |
|------|---------------|
| `--yolo` or `-y` | Auto-accepts ALL actions, ignores safety |
| `--approval-mode yolo` | Same as `--yolo` |

---

## Permission Summary

| Command | Codex | Gemini |
|---------|-------|--------|
| `/code-review` | `--sandbox read-only` | `--sandbox --allowed-tools read_file run_shell_command` |
| `/plan-review` | `--sandbox read-only` | `--sandbox --allowed-tools read_file run_shell_command` |

---

## Session Cleanup

### Cleanup Triggers (MANDATORY)

Session cleanup MUST run when ANY of these occur:
- User chooses "No" to re-review
- User chooses "Skip review"
- All findings have been addressed
- Review workflow completes for any reason

### Session Variable Naming Convention

| Command | Unique ID | Codex Session | Gemini Session |
|---------|-----------|---------------|----------------|
| `/code-review` | `CODE_REVIEW_ID` | `CODEX_REVIEW_SESSION_ID` | `GEMINI_REVIEW_SESSION_ID` |
| `/plan-review` | `PLAN_REVIEW_ID` | `CODEX_PLAN_REVIEW_SESSION_ID` | `GEMINI_PLAN_REVIEW_SESSION_ID` |

### Temp File Naming (session-specific, cross-platform)

> **Note**: Use `mktemp` for secure temp file creation. These patterns show naming conventions.
> - Unix: `${TMPDIR:-/tmp}/` or `$TMPDIR/`
> - Windows: `%TEMP%\` or Python's `tempfile.gettempdir()`

```bash
# Secure temp file creation (cross-platform)
TMPDIR="${TMPDIR:-/tmp}"
CODEX_REVIEW_FILE=$(mktemp "${TMPDIR}/codex_code_review_${CODE_REVIEW_ID}_XXXXXX.json")
GEMINI_REVIEW_FILE=$(mktemp "${TMPDIR}/gemini_code_review_${CODE_REVIEW_ID}_XXXXXX.json")
trap "rm -f $CODEX_REVIEW_FILE $GEMINI_REVIEW_FILE" EXIT
```

### Manual Cleanup (if interrupted)

```bash
# List orphaned temp files (cross-platform)
TMPDIR="${TMPDIR:-/tmp}"
ls -la "${TMPDIR}"/codex_*_review_*.json "${TMPDIR}"/gemini_*_review_*.json 2>/dev/null

# Delete orphaned temp files
rm -f "${TMPDIR}"/codex_*_review_*.json "${TMPDIR}"/gemini_*_review_*.json 2>/dev/null

# List recent sessions (review before deleting!)
find ~/.codex/sessions -type f -mmin -60 -name "*.jsonl" -ls
find ~/.gemini/sessions ~/.config/gemini/sessions -type f -mmin -60 -name "*.json" -ls 2>/dev/null
```

### Session Locations

- Codex: `~/.codex/sessions/YYYY/MM/DD/*.jsonl`
- Gemini: `~/.gemini/sessions/` or `~/.config/gemini/sessions/`

---

## Troubleshooting

### Codex: Command blocked

The `--sandbox read-only` mode blocks all writes via Landlock. This is expected.
Read operations (git diff, cat, etc.) should work fine.

### Gemini: Enters plan mode

1. Ensure `--sandbox` is present
2. Use `--allowed-tools` with specific tool names
3. Do NOT use `--approval-mode plan`

### Gemini: Makes unauthorized changes

1. NEVER use `--yolo` or `--approval-mode yolo`
2. Ensure `--sandbox` flag is present
3. Only allow `read_file` and `run_shell_command` (sandbox blocks writes)

### Gemini: "Could not load the default credentials" in sandbox

The Docker sandbox cannot access host Application Default Credentials.

**Solution**: Mount the ADC file into the container:

```bash
export SANDBOX_FLAGS="-v $HOME/.config/gcloud/application_default_credentials.json:${TMPDIR:-/tmp}/adc.json:ro -e GOOGLE_APPLICATION_CREDENTIALS=${TMPDIR:-/tmp}/adc.json"
gemini --sandbox -- "Your prompt"
```

### Gemini: "Cannot use both a positional prompt and --prompt flag"

The `--allowed-tools` array flag consumes subsequent tokens including your prompt.

**Solution**: Use `--` separator before the positional prompt:

```bash
# WRONG - --allowed-tools consumes "Your prompt"
gemini --allowed-tools read_file run_shell_command -p "Your prompt"

# CORRECT - -- stops flag parsing
gemini --allowed-tools read_file run_shell_command -- "Your prompt"
```

---

## References

- [Codex Security](https://developers.openai.com/codex/security/)
- [Codex CLI Reference](https://developers.openai.com/codex/cli/reference/)
- [Codex Basic Configuration](https://developers.openai.com/codex/config-basic/)
- [Codex Sandbox Documentation](https://github.com/openai/codex/blob/main/docs/sandbox.md)
- [Gemini CLI Sandbox Docs](https://geminicli.com/docs/cli/sandbox/)
- [Gemini CLI Tools](https://geminicli.com/docs/tools/)
- [Gemini CLI Configuration](https://github.com/google-gemini/gemini-cli/blob/main/docs/get-started/configuration.md)
