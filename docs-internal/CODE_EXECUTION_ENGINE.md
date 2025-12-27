# Code Execution Engine

**Status**: Active
**Last Updated**: 2025-12-27
**Owner**: Platform Security Team

## Purpose

This document describes the architecture of the sandboxed code execution engine, which enables secure execution of Python code in isolated Docker containers or Kubernetes Jobs.

---

## Overview

The execution engine provides a **defense-in-depth** approach to code execution:

1. **Application Layer** - AST-based code validation and import whitelisting
2. **Container/Pod Layer** - Resource limits, capability dropping, read-only filesystem
3. **Network Layer** - Complete network isolation by default
4. **Orchestration Layer** - RBAC, namespace isolation, automatic cleanup

---

## Module Structure

```
src/mcp_server_langgraph/execution/
├── sandbox.py           # Abstract base class defining sandbox interface
├── docker_sandbox.py    # Docker container implementation
├── kubernetes_sandbox.py# Kubernetes Job implementation
├── resource_limits.py   # Resource constraint configuration
├── code_validator.py    # AST-based security validation
├── sandbox_context.py   # Execution context with MCP tool integration
├── sandbox_runner.py    # Generic sandbox operations runner
├── tool_bridge.py       # Programmatic tool calling from sandbox
├── langgraph_manager.py # LangGraph workflow execution integration
└── domain_proxy.py      # Network allowlist enforcement (HTTP proxy)
```

---

## Core Classes

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    success: bool           # Whether execution succeeded
    stdout: str            # Standard output
    stderr: str            # Standard error
    exit_code: int         # Process exit code (0 = success)
    execution_time: float  # Duration in seconds
    timed_out: bool        # True if killed due to timeout
    memory_used_mb: float  # Peak memory usage (optional)
    error_message: str     # Human-readable error (if failed)
```

### Sandbox (Abstract Base)

```python
class Sandbox(ABC):
    def __init__(self, limits: ResourceLimits): ...

    @abstractmethod
    def execute(self, code: str) -> ExecutionResult: ...

    async def aexecute(self, code: str) -> ExecutionResult:
        """Non-blocking wrapper using asyncio.to_thread"""
```

---

## Sandbox Implementations

### DockerSandbox

**Location**: `docker_sandbox.py`

**Security Hardening:**
```
- user="nobody"                       # Non-root execution
- read_only=True                      # Read-only root FS
- security_opt=["no-new-privileges"]  # Prevent privilege escalation
- cap_drop=["ALL"]                    # Drop all Linux capabilities
- network_mode="none"                 # Network isolation
- tmpfs for /tmp and /var/tmp         # Ephemeral, in-memory FS
```

**Constructor:**
```python
DockerSandbox(
    limits: ResourceLimits,
    image: str = "python:3.12-slim",
    socket_path: str = "/var/run/docker.sock"
)
```

### KubernetesSandbox

**Location**: `kubernetes_sandbox.py`

**Pod Security Context:**
```python
Container Level:
- allow_privilege_escalation=False
- run_as_non_root=True
- run_as_user=1000
- read_only_root_filesystem=False  # Need writable /tmp
- capabilities.drop=["ALL"]

Pod Level:
- run_as_non_root=True
- run_as_user=1000
- fs_group=1000
```

**Constructor:**
```python
KubernetesSandbox(
    limits: ResourceLimits,
    namespace: str = "default",
    image: str = "python:3.12-slim",
    job_ttl: int = 300  # TTL in seconds
)
```

---

## Resource Limits

**Location**: `resource_limits.py`

### Configuration (Frozen Dataclass)

```python
@dataclass(frozen=True)
class ResourceLimits:
    timeout_seconds: int = 30        # 1-600 seconds
    memory_limit_mb: int = 512       # 64-8192 MB
    cpu_quota: float = 1.0           # 0.1-8.0 cores
    disk_quota_mb: int = 100         # 1-10240 MB
    max_processes: int = 1           # 1-100 processes
    network_mode: NetworkMode = "none"  # "none"|"allowlist"|"unrestricted"
    allowed_domains: tuple[str, ...] = ()
```

### Preset Profiles

| Profile | Timeout | Memory | CPU | Disk | Processes | Network |
|---------|---------|--------|-----|------|-----------|---------|
| `production()` | 30s | 512MB | 1.0 | 100MB | 1 | none |
| `development()` | 300s | 2GB | 2.0 | 1GB | 10 | unrestricted |
| `testing()` | 10s | 256MB | 0.5 | 50MB | 1 | none |
| `data_processing()` | 300s | 4GB | 4.0 | 512MB | 4 | allowlist |

---

## Code Validator

**Location**: `code_validator.py`

### Blocked Modules (52 total)

```python
# Core OS/System
os, sys, subprocess, pty, fcntl, termios, tty, shutil

# Data Serialization (unsafe)
pickle, marshal

# System Interaction
ctypes, importlib, resource, signal, multiprocessing, threading

# Networking
socket, urllib, urllib.request, httplib, http.client, requests

# Debugging/Introspection
code, pdb, inspect, gc, weakref, ast, dis, imp, runpy
```

### Blocked Builtins (21 total)

```python
# Code Execution
eval, exec, compile, __import__

# Introspection
globals, locals, vars, getattr, setattr, delattr

# I/O
open, input, breakpoint
```

### Validation Result

```python
@dataclass
class ValidationResult:
    is_valid: bool       # True if no errors
    errors: list[str]    # Fatal security violations
    warnings: list[str]  # Suspicious patterns (allowed with warning)
```

---

## API Endpoint

**Endpoint**: `POST /api/v1/sandbox/run`

### Request

```python
class SandboxRunRequest(BaseModel):
    type: str           # "bash", "web_fetch", "write_file", etc.
    command: str | None # For bash
    url: str | None     # For web_fetch
    file_path: str | None
    content: str | None
    payload: dict | None
    timeout: int | None
```

### Response

```python
class SandboxRunResponse(BaseModel):
    stdout: str | None
    stderr: str | None
    exit_code: int | None
    duration_ms: float | None
    timed_out: bool | None
    error: str | None
```

### Supported Operations

| Operation | Description |
|-----------|-------------|
| `bash` | Shell command execution |
| `web_fetch` | HTTP/HTTPS URL fetching (max 10MB) |
| `write_file` | Create/overwrite files in sandbox |
| `edit_file` | Find and replace in files |
| `screenshot` | Web page capture (Playwright) |
| `computer_use` | Browser automation (Playwright) |

---

## Configuration

### Environment Variables

```bash
# Enable/Disable (SECURITY: disabled by default)
ENABLE_CODE_EXECUTION=false

# Backend Selection
CODE_EXECUTION_BACKEND="docker-engine"  # or "kubernetes"

# Resource Limits
CODE_EXECUTION_TIMEOUT=30
CODE_EXECUTION_MEMORY_LIMIT_MB=512
CODE_EXECUTION_CPU_QUOTA=1.0
CODE_EXECUTION_DISK_QUOTA_MB=100
CODE_EXECUTION_MAX_PROCESSES=1

# Network
CODE_EXECUTION_NETWORK_MODE="none"
CODE_EXECUTION_ALLOWED_DOMAINS=[]

# Import Whitelist
CODE_EXECUTION_ALLOWED_IMPORTS=[
    "json", "math", "datetime", "collections",
    "itertools", "functools", "typing", "dataclasses"
]

# Docker Configuration
CODE_EXECUTION_DOCKER_IMAGE="python:3.12-slim"
CODE_EXECUTION_DOCKER_SOCKET="/var/run/docker.sock"

# Kubernetes Configuration
CODE_EXECUTION_K8S_NAMESPACE="default"
CODE_EXECUTION_K8S_JOB_TTL=300
```

---

## Security Model

### Defense-in-Depth Layers

```
┌─────────────────────────────────────────────────┐
│  1. Application Layer                            │
│     - AST-based code validation                  │
│     - Import whitelisting                        │
│     - Feature flags (disabled by default)        │
├─────────────────────────────────────────────────┤
│  2. Container/Pod Layer                          │
│     - Read-only root filesystem                  │
│     - Non-root user (nobody/uid 1000)            │
│     - All capabilities dropped                   │
│     - Privilege escalation prevented             │
│     - Memory/CPU/process limits                  │
├─────────────────────────────────────────────────┤
│  3. Network Layer                                │
│     - Default: "none" (complete isolation)       │
│     - Optional: domain allowlist (HTTP proxy)    │
├─────────────────────────────────────────────────┤
│  4. Orchestration Layer (Kubernetes)             │
│     - Namespace isolation                        │
│     - RBAC policies                              │
│     - Pod security standards                     │
│     - Automatic TTL cleanup                      │
└─────────────────────────────────────────────────┘
```

### Network Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `none` | Complete network isolation | **Default**, highest security |
| `allowlist` | Domain-restricted access via proxy | Data fetching with control |
| `unrestricted` | Full network access | Development only |

---

## Execution Flow

```
Client Request
    ↓
API Endpoint (/api/v1/sandbox/run)
    ↓
Authentication Check (Keycloak JWT)
    ↓
Configuration Check (enable_code_execution)
    ↓
Code Validation (AST-based)
    ↓
Sandbox Runner (Select backend)
    ↓
┌─────────────────────┬─────────────────────┐
│      Docker         │     Kubernetes      │
├─────────────────────┼─────────────────────┤
│ Create container    │ Create job spec     │
│ Apply security opts │ Apply pod security  │
│ Start + wait        │ Wait for completion │
│ Retrieve logs       │ Retrieve pod logs   │
│ Cleanup container   │ TTL-based cleanup   │
└─────────────────────┴─────────────────────┘
    ↓
ExecutionResult
    ↓
API Response
```

---

## Tool Bridge (Programmatic Tool Calling)

**Feature Flag**: `enable_programmatic_tools` (disabled by default)

```python
class ToolBridge:
    async def call_tool(tool_name: str, args: dict) -> ToolResult
    async def gather_tools(*calls) -> list[ToolResult]
    def list_tools() -> list[str]
```

Allows sandboxed Python code to invoke MCP tools via `call_tool()` API.

---

## Testing

| Test Type | Location |
|-----------|----------|
| Unit tests | `tests/unit/execution/` |
| Integration | `tests/integration/execution/` |
| Config tests | `tests/unit/config/test_code_execution_config.py` |

---

## Related Documentation

- [Feature Flag Catalog](./FEATURE_FLAG_CATALOG.md) - Code execution flags
- [API Reference: Code Execution](../docs/api-reference/code-execution.mdx) - User-facing docs
- [Security Best Practices](../docs/security/best-practices.mdx) - Security guidelines
