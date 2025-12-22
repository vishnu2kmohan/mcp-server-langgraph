# 79. Multi-Framework Tool Parity

Date: 2025-12-21

## Status

Proposed

## Category

Architecture & Integration

## Context

A comprehensive audit comparing mcp-server-langgraph against three major agent frameworks (Claude Agent SDK, Google ADK, and OpenAI Agents SDK) identified several tool gaps that limit interoperability and feature completeness.

**Current Tool Inventory**:

| Our Tool | Description | Location |
|----------|-------------|----------|
| `read_file` | Read file contents | `tools/filesystem_tools.py` |
| `list_directory` | List directory contents (Glob) | `tools/filesystem_tools.py` |
| `search_files` | Search file contents (Grep) | `tools/filesystem_tools.py` |
| `web_search` | Web search | `tools/search_tools.py` |
| `search_knowledge_base` | RAG knowledge search | `tools/search_tools.py` |
| `execute_python` | Sandboxed Python execution | `tools/code_execution_tools.py` |
| `calculator` | Safe AST-based calculation | `tools/calculator_tools.py` |
| `think` | Structured reasoning (no-op) | `tools/think_tool.py` |

**Framework Comparison**:

| Tool | Claude SDK | Google ADK | OpenAI SDK | Ours | Gap? |
|------|------------|------------|------------|------|------|
| File Read | `Read` | Function tools | `FileSearchTool` | `read_file` | No |
| **File Write** | `Write` | Function tools | - | - | **YES** |
| **File Edit** | `Edit` | Function tools | - | - | **YES** |
| Glob | `Glob` | - | - | `list_directory` | No |
| Grep | `Grep` | - | - | `search_files` | No |
| Web Search | `WebSearch` | `Google Search` | `WebSearchTool` | `web_search` | No |
| **Web Fetch** | `WebFetch` | - | - | - | **YES** |
| Code Exec | `Bash` | `Code Execution` | `CodeInterpreterTool` | `execute_python` | Partial |

**Identified Gaps**:
1. **`write_file`**: No ability to create or overwrite files
2. **`edit_file`**: No ability to make precise edits to existing files
3. **`web_fetch`**: No ability to fetch and process URL content
4. **Output Guardrails**: No post-LLM response validation (OpenAI pattern)

**Why These Matter**:
- **Coding Agents**: Cannot create new files or modify existing ones
- **Research Agents**: Cannot fetch web content for analysis
- **Content Safety**: Cannot validate/filter LLM outputs before delivery

## Decision

Implement four new capabilities to achieve multi-framework tool parity:

### 1. `write_file` Tool

**Purpose**: Create new files or overwrite existing files with security validation.

**Implementation**: `src/mcp_server_langgraph/tools/write_file_tools.py`

```python
from langchain_core.tools import tool
from typing import Annotated
from pydantic import Field

@tool
def write_file(
    file_path: Annotated[str, Field(description="Relative path within workspace")],
    content: Annotated[str, Field(description="Content to write to the file")],
    create_directories: Annotated[bool, Field(default=True, description="Create parent directories if needed")],
) -> str:
    """Create or overwrite a file with the given content.

    Security: Path must be relative, within workspace, and pass validation.
    """
```

**Security Controls**:
- Path must be relative (no absolute paths starting with `/`)
- No path traversal (`..` segments rejected)
- Workspace boundary enforcement
- Size limit: 1MB default (configurable via `WRITE_FILE_MAX_SIZE_BYTES`)
- Backup existing file before overwrite (optional via `WRITE_FILE_CREATE_BACKUP`)
- OpenFGA permission check: `can:write` on `file:<path>`

**Feature Flag**: `enable_write_file_tool` (default: False)

### 2. `edit_file` Tool

**Purpose**: Make precise, diff-based edits to existing files.

**Implementation**: `src/mcp_server_langgraph/tools/edit_file_tools.py`

```python
@tool
def edit_file(
    file_path: Annotated[str, Field(description="Path to file to edit")],
    old_string: Annotated[str, Field(description="Exact text to find and replace")],
    new_string: Annotated[str, Field(description="Replacement text")],
    replace_all: Annotated[bool, Field(default=False, description="Replace all occurrences")],
) -> str:
    """Make precise edits to an existing file by replacing text.

    The old_string must exist exactly once in the file (unless replace_all=True).
    Creates a backup before editing.
    """
```

**Security Controls**:
- File must exist (no silent creation)
- `old_string` must exist in file (validation before edit)
- Unique match requirement unless `replace_all=True`
- Automatic backup before modification
- Preserves file encoding (UTF-8 with fallback detection)
- OpenFGA permission check: `can:edit` on `file:<path>`

**Feature Flag**: `enable_edit_file_tool` (default: False)

### 3. `web_fetch` Tool

**Purpose**: Fetch URL content and optionally process with a prompt.

**Implementation**: `src/mcp_server_langgraph/tools/web_fetch_tools.py`

```python
@tool
async def web_fetch(
    url: Annotated[str, Field(description="URL to fetch (HTTP/HTTPS only)")],
    prompt: Annotated[str | None, Field(default=None, description="Optional prompt to extract specific information")],
    convert_html: Annotated[bool, Field(default=True, description="Convert HTML to markdown")],
) -> str:
    """Fetch content from a URL and optionally process it.

    Supports HTML to markdown conversion for cleaner output.
    """
```

**Security Controls**:
- URL scheme validation (HTTPS preferred, HTTP auto-upgraded)
- No `file://`, `ftp://`, or other dangerous schemes
- Internal IP rejection (10.x, 192.168.x, 127.x, etc.)
- Domain allowlist/blocklist (configurable)
- Content size limit: 10MB default
- Timeout: 30 seconds default
- HTML sanitization before processing
- Rate limiting per domain

**Feature Flag**: `enable_web_fetch_tool` (default: False)

### 4. Output Guardrails

**Purpose**: Validate and filter LLM outputs before delivery to users.

**Implementation**: `src/mcp_server_langgraph/sdk/output_guardrails.py`

```python
from typing import Protocol
from dataclasses import dataclass

@dataclass
class GuardrailResult:
    allowed: bool
    modified_output: str | None = None
    reason: str | None = None
    tripwire_triggered: bool = False

class OutputGuardrail(Protocol):
    """Protocol for output guardrails following OpenAI pattern."""

    async def validate(
        self,
        output: str,
        context: dict[str, Any],
    ) -> GuardrailResult:
        """Validate LLM output and optionally modify it."""
        ...

# Built-in guardrails
class PIIGuardrail(OutputGuardrail):
    """Detect and redact PII from outputs."""

class ProfanityGuardrail(OutputGuardrail):
    """Filter profanity from outputs."""

class DisclaimerGuardrail(OutputGuardrail):
    """Add AI-generated disclaimers to outputs."""

class FormatGuardrail(OutputGuardrail):
    """Enforce output format requirements."""
```

**Integration**: Via `AFTER_MODEL` hook (see ADR-0080)

**Feature Flag**: `enable_output_guardrails` (default: False)

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Tool Registry Layer                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    New Tools (This ADR)                          │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │ write_file  │  │  edit_file  │  │       web_fetch         │  │   │
│  │  │ Create/     │  │  Diff-based │  │    URL + Optional       │  │   │
│  │  │ Overwrite   │  │  Edits      │  │    Processing           │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Output Guardrails                             │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  PII Detection │ Profanity Filter │ Disclaimer │ Format Check   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Security Layer                                │   │
│  ├─────────────────────────────────────────────────────────────────┤   │
│  │  Path Validation │ URL Validation │ OpenFGA Permissions          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Configuration

```python
# Environment variables for tool configuration
WRITE_FILE_MAX_SIZE_BYTES = 1048576  # 1MB
WRITE_FILE_CREATE_BACKUP = True
WRITE_FILE_ALLOWED_EXTENSIONS = ".py,.md,.txt,.json,.yaml,.yml,.toml"

EDIT_FILE_CREATE_BACKUP = True
EDIT_FILE_MAX_DIFF_SIZE = 10000  # characters

WEB_FETCH_TIMEOUT_SECONDS = 30
WEB_FETCH_MAX_SIZE_BYTES = 10485760  # 10MB
WEB_FETCH_BLOCKED_DOMAINS = ""  # comma-separated
WEB_FETCH_ALLOWED_DOMAINS = ""  # comma-separated (if set, only these allowed)
```

### Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `enable_write_file_tool` | False | Enable file creation/overwrite |
| `enable_edit_file_tool` | False | Enable diff-based file editing |
| `enable_web_fetch_tool` | False | Enable URL content fetching |
| `enable_output_guardrails` | False | Enable output validation |

## Consequences

### Positive

1. **Framework Parity**: Matches Claude Agent SDK's Write, Edit, WebFetch tools
2. **Coding Agent Support**: Agents can now create and modify files
3. **Research Capabilities**: Agents can fetch and analyze web content
4. **Content Safety**: Output guardrails prevent harmful content delivery
5. **Security-First**: All tools have comprehensive security controls

### Negative

1. **Attack Surface**: File operations increase security risk (mitigated by sandboxing)
2. **Complexity**: More tools to maintain and test
3. **Dependencies**: `web_fetch` requires HTTP client, HTML parser

### Neutral

1. **Feature Flags**: All disabled by default, opt-in adoption
2. **LLM Agnostic**: Works with any LLM provider via LiteLLM
3. **Backward Compatible**: Existing tools unchanged

## Implementation Plan

### TDD Test Cases (Write FIRST)

**`tests/unit/tools/test_write_file_tool.py`**:
```python
def test_write_file_creates_new_file()
def test_write_file_overwrites_existing_file()
def test_write_file_rejects_path_traversal()
def test_write_file_rejects_absolute_paths()
def test_write_file_respects_size_limit()
def test_write_file_creates_parent_directories()
def test_write_file_requires_permission()
def test_write_file_creates_backup_before_overwrite()
```

**`tests/unit/tools/test_edit_file_tool.py`**:
```python
def test_edit_file_applies_replacement()
def test_edit_file_rejects_nonexistent_file()
def test_edit_file_rejects_missing_old_string()
def test_edit_file_rejects_ambiguous_match()
def test_edit_file_handles_replace_all()
def test_edit_file_creates_backup()
def test_edit_file_preserves_encoding()
def test_edit_file_requires_permission()
```

**`tests/unit/tools/test_web_fetch_tool.py`**:
```python
async def test_web_fetch_returns_content()
async def test_web_fetch_handles_timeout()
async def test_web_fetch_rejects_blocked_domains()
async def test_web_fetch_rejects_internal_ips()
async def test_web_fetch_sanitizes_html()
async def test_web_fetch_respects_size_limit()
async def test_web_fetch_follows_redirects_safely()
async def test_web_fetch_converts_html_to_markdown()
```

**`tests/unit/core/test_output_guardrails.py`**:
```python
async def test_pii_guardrail_detects_email()
async def test_pii_guardrail_detects_phone()
async def test_profanity_guardrail_filters_content()
async def test_disclaimer_guardrail_adds_prefix()
async def test_format_guardrail_enforces_json()
async def test_guardrail_chain_execution()
async def test_tripwire_stops_processing()
```

### Files to Create

```
src/mcp_server_langgraph/tools/
├── write_file_tools.py      # NEW
├── edit_file_tools.py       # NEW
├── web_fetch_tools.py       # NEW
└── __init__.py              # UPDATE: register new tools

src/mcp_server_langgraph/sdk/
└── output_guardrails.py     # NEW

tests/unit/tools/
├── test_write_file_tool.py  # NEW
├── test_edit_file_tool.py   # NEW
└── test_web_fetch_tool.py   # NEW

tests/unit/core/
└── test_output_guardrails.py  # NEW
```

### Files to Modify

```
src/mcp_server_langgraph/tools/__init__.py      # Register new tools
src/mcp_server_langgraph/core/feature_flags.py  # Add feature flags
```

## Related ADRs

- ADR-0077: Claude Agent SDK Integration (foundation patterns)
- ADR-0078: Multi-Agent Orchestrator Patterns (subagent tool access)
- ADR-0080: LLM-Level Callback System (guardrail integration point)
- ADR-0082: MCP Client Capabilities (external tool consumption)

## References

- [Claude Agent SDK - Tools](https://platform.claude.com/docs/en/agent-sdk/tools)
- [OpenAI Agents SDK - Guardrails](https://openai.github.io/openai-agents-python/guardrails/)
- [Google ADK - Function Tools](https://google.github.io/adk-docs/tools/function-tools/)
