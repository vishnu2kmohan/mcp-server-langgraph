"""
AI-Native APIs

Provides endpoints for AI-powered features:
- Node configuration assistance
- Workflow suggestions (future)
- Template recommendations (future)

Reference: Phase B - AI Feature Exposure
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from mcp_server_langgraph.observability.telemetry import logger
from mcp_server_langgraph.studio.ai.node_config import (
    NodeConfigAssistant,
    NodeTypeRegistry,
)


ai_router = APIRouter(tags=["ai"])


# =============================================================================
# Request/Response Models
# =============================================================================


class NodeConfigHelpRequest(BaseModel):
    """Request for node configuration help."""

    node_type: str = Field(description="The type of node (llm, tool, input, output, code, condition)")
    context: dict[str, Any] | None = Field(
        None,
        description="Optional context including existing nodes, workflow goal, etc.",
    )


class NodeConfigHelpResponse(BaseModel):
    """Response containing node configuration help."""

    help_text: str = Field(description="Human-readable help text")
    suggested_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Suggested configuration values",
    )
    examples: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Example configurations",
    )
    suggested_connections: list[dict[str, str]] | None = Field(
        None,
        description="Suggested connections to/from existing nodes",
    )


class NodeConfigValidateRequest(BaseModel):
    """Request to validate node configuration."""

    node_type: str = Field(description="The type of node")
    config: dict[str, Any] = Field(description="The configuration to validate")


class NodeConfigValidateResponse(BaseModel):
    """Response containing validation results."""

    valid: bool = Field(description="Whether the configuration is valid")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class NodeTypesResponse(BaseModel):
    """Response containing available node types."""

    node_types: list[str] = Field(description="List of available node types")


# =============================================================================
# Module-level instances
# =============================================================================

_assistant = NodeConfigAssistant()
_registry = NodeTypeRegistry()


# =============================================================================
# Endpoints
# =============================================================================


@ai_router.post(
    "/node-config/help",
    status_code=status.HTTP_200_OK,
    summary="Get Node Configuration Help",
    description="Get AI-powered configuration help for a workflow node type",
)
async def get_node_config_help(request: NodeConfigHelpRequest) -> NodeConfigHelpResponse:
    """
    Get configuration help for a node type.

    Example:
        ```
        POST /api/v1/ai/node-config/help
        {
            "node_type": "llm",
            "context": {
                "workflow_goal": "Build a chatbot",
                "existing_nodes": [
                    {"id": "input-1", "type": "input"}
                ]
            }
        }
        ```
    """
    logger.info(
        "Node config help requested",
        extra={
            "node_type": request.node_type,
            "has_context": request.context is not None,
        },
    )

    result = await _assistant.get_help(
        node_type=request.node_type,
        context=request.context,
    )

    return NodeConfigHelpResponse(
        help_text=result.get("help_text", f"Configure the {request.node_type} node."),
        suggested_config=result.get("suggested_config", {}),
        examples=result.get("examples", []),
        suggested_connections=result.get("suggested_connections"),
    )


@ai_router.post(
    "/node-config/validate",
    status_code=status.HTTP_200_OK,
    summary="Validate Node Configuration",
    description="Validate a node configuration against its schema",
)
async def validate_node_config(request: NodeConfigValidateRequest) -> NodeConfigValidateResponse:
    """
    Validate node configuration.

    Example:
        ```
        POST /api/v1/ai/node-config/validate
        {
            "node_type": "llm",
            "config": {
                "model": "gpt-4",
                "temperature": 0.7
            }
        }
        ```
    """
    logger.info(
        "Node config validation requested",
        extra={
            "node_type": request.node_type,
            "config_keys": list(request.config.keys()),
        },
    )

    result = await _assistant.validate_config(
        node_type=request.node_type,
        config=request.config,
    )

    return NodeConfigValidateResponse(
        valid=result.get("valid", False),
        errors=result.get("errors", []),
        warnings=result.get("warnings", []),
    )


@ai_router.get(
    "/node-types",
    status_code=status.HTTP_200_OK,
    summary="Get Available Node Types",
    description="Get all available workflow node types",
)
async def get_node_types() -> NodeTypesResponse:
    """
    Get all available node types.

    Example:
        ```
        GET /api/v1/ai/node-types
        ```
    """
    return NodeTypesResponse(node_types=_registry.get_all_types())


@ai_router.get(
    "/node-types/{node_type}/schema",
    status_code=status.HTTP_200_OK,
    summary="Get Node Type Schema",
    description="Get the JSON Schema for a specific node type",
)
async def get_node_type_schema(node_type: str) -> dict[str, Any]:
    """
    Get schema for a node type.

    Example:
        ```
        GET /api/v1/ai/node-types/llm/schema
        ```
    """
    schema = _registry.get_schema(node_type)

    if schema is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node type '{node_type}' not found",
        )

    return schema
