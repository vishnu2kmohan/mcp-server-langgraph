"""
Code execution module for MCP server

Provides secure sandboxed code execution with resource limits and security controls.
"""

from mcp_server_langgraph.execution.code_validator import CodeValidationError, CodeValidator, ValidationResult
from mcp_server_langgraph.execution.resource_limits import ResourceLimitError, ResourceLimits
from mcp_server_langgraph.execution.sandbox import ExecutionResult, Sandbox, SandboxError


# Optional: KubernetesSandbox requires kubernetes package
# Import conditionally to avoid failures when kubernetes is not installed
try:
    from mcp_server_langgraph.execution.kubernetes_sandbox import KubernetesSandbox

    _KUBERNETES_AVAILABLE = True
except ImportError:
    KubernetesSandbox = None  # type: ignore
    _KUBERNETES_AVAILABLE = False

# Optional: DockerSandbox requires docker package
# Import conditionally to avoid failures when docker is not installed
try:
    from mcp_server_langgraph.execution.docker_sandbox import DockerSandbox

    _DOCKER_AVAILABLE = True
except ImportError:
    DockerSandbox = None  # type: ignore
    _DOCKER_AVAILABLE = False

__all__ = [
    "CodeValidator",
    "CodeValidationError",
    "ValidationResult",
    "ResourceLimits",
    "ResourceLimitError",
    "Sandbox",
    "SandboxError",
    "ExecutionResult",
    "DockerSandbox",
    "KubernetesSandbox",
]
