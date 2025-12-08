"""
Visual Workflow Builder API

FastAPI backend for the visual workflow builder.

Endpoints:
- POST /api/builder/generate - Generate Python code from workflow
- POST /api/builder/validate - Validate workflow structure
- GET /api/builder/templates - List workflow templates
- POST /api/builder/save - Save workflow to file

Example:
    uvicorn mcp_server_langgraph.builder.api.server:app --reload
"""

import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncIterator, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

from mcp_server_langgraph.observability.telemetry import (
    init_observability,
    is_initialized,
    logger,
    shutdown_observability,
    tracer,
)

from mcp_server_langgraph.utils.spa_static_files import create_spa_static_files

from ..codegen import CodeGenerator, WorkflowDefinition
from ..storage import (
    PostgresWorkflowManager,
    RedisWorkflowManager,
    StoredWorkflow,
    create_postgres_engine,
    create_redis_pool,
    init_builder_database,
)
from ..workflow import WorkflowBuilder

# ==============================================================================
# API Models
# ==============================================================================


class GenerateCodeRequest(BaseModel):
    """Request to generate code from workflow."""

    workflow: dict[str, Any]


class GenerateCodeResponse(BaseModel):
    """Response with generated code."""

    code: str
    formatted: bool
    warnings: list[str] = []


class ValidateWorkflowRequest(BaseModel):
    """Request to validate workflow."""

    workflow: dict[str, Any]


class ValidateWorkflowResponse(BaseModel):
    """Response with validation results."""

    valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class SaveWorkflowRequest(BaseModel):
    """Request to save workflow to file."""

    workflow: dict[str, Any]
    output_path: str

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, v: str) -> str:
        """
        Validate output path for security.

        SECURITY: Prevents CWE-73 (External Control of File Name or Path) and
        CWE-434 (Unrestricted Upload of File with Dangerous Type) by enforcing
        strict path validation.

        Only allows paths within designated safe directories.
        """
        # Convert to Path for normalization
        path = Path(v).resolve()

        # Define allowed base directories (configurable via environment)
        # Use application-specific temp directory instead of hardcoded /tmp for better security
        default_dir = Path(tempfile.gettempdir()) / "mcp-server-workflows"
        allowed_base = os.getenv("BUILDER_OUTPUT_DIR", str(default_dir))
        allowed_base_path = Path(allowed_base).resolve()

        # Ensure the allowed base directory exists with secure permissions
        allowed_base_path.mkdir(mode=0o700, parents=True, exist_ok=True)

        # Check if path is within allowed directory
        try:
            path.relative_to(allowed_base_path)
        except ValueError:
            msg = (
                f"Invalid output path. Must be within allowed directory: {allowed_base}. "
                f"Use BUILDER_OUTPUT_DIR environment variable to configure safe directory."
            )
            raise ValueError(msg)

        # Additional checks for common attack patterns
        path_str = str(path)
        if ".." in path_str or path_str.startswith("/etc/") or path_str.startswith("/sys/"):
            msg = "Path traversal detected. Invalid output path."
            raise ValueError(msg)

        # Ensure .py extension
        if path.suffix != ".py":
            msg = "Output path must have .py extension"
            raise ValueError(msg)

        return str(path)


class ImportWorkflowRequest(BaseModel):
    """Request to import Python code into workflow."""

    code: str
    layout: Literal["hierarchical", "force", "grid"] = "hierarchical"


class CreateWorkflowRequest(BaseModel):
    """Request to create a new workflow."""

    name: str
    description: str = ""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []


class UpdateWorkflowRequest(BaseModel):
    """Request to update an existing workflow."""

    name: str | None = None
    description: str | None = None
    nodes: list[dict[str, Any]] | None = None
    edges: list[dict[str, Any]] | None = None


class WorkflowResponse(BaseModel):
    """Response with workflow data."""

    id: str
    name: str
    description: str = ""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    created_at: str
    updated_at: str


# ==============================================================================
# Workflow Storage (Postgres, Redis, or in-memory fallback)
# ==============================================================================
# Storage backend priority:
#   1. Postgres (BUILDER_POSTGRES_URL) - Production, durable persistence
#   2. Redis (BUILDER_REDIS_URL or REDIS_URL) - Session-like storage, optional TTL
#   3. In-memory - Development/testing only, data lost on restart

# Global workflow manager (initialized in lifespan)
_workflow_manager: PostgresWorkflowManager | RedisWorkflowManager | None = None

# In-memory fallback for development/testing without persistence
_workflows_fallback: dict[str, dict[str, Any]] = {}
_storage_backend: str = "memory"  # "postgres", "redis", or "memory"


# ==============================================================================
# Security & Authentication
# ==============================================================================


def verify_builder_auth(authorization: str = Header(None)) -> None:
    """
    Verify authentication for builder endpoints.

    SECURITY: Prevents unauthenticated access to code generation and file write endpoints.
    Addresses OWASP A01:2021 - Broken Access Control.

    In production, this should integrate with your main authentication system.
    For now, we use a simple bearer token approach.

    Args:
        authorization: Authorization header (Bearer token)

    Raises:
        HTTPException: 401 if not authenticated

    Environment handling:
        - development: Allow unauthenticated access (local dev only)
        - test: Require authentication (E2E tests)
        - production: Require authentication

    TODO: Integrate with main auth system (Keycloak, etc.)
    """
    # Allow unauthenticated access ONLY in development (not test or production)
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "development" and not authorization:
        # Log warning but allow
        print("WARNING: Builder accessed without auth in development mode")
        return

    # In test and production environments, require authentication
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide Bearer token in Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>",
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    # TODO: Validate token against your auth system
    # For now, we check against environment variable
    expected_token = os.getenv("BUILDER_AUTH_TOKEN")
    if expected_token and token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )


# ==============================================================================
# FastAPI Application
# ==============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Builder service lifecycle with observability and persistent storage.

    Initializes OpenTelemetry tracing and metrics on startup,
    connects to Postgres or Redis for workflow storage (priority: Postgres > Redis > Memory),
    gracefully shuts down on termination.
    """
    global _workflow_manager, _storage_backend

    # STARTUP - Observability
    if not is_initialized():
        try:
            from mcp_server_langgraph.core.config import Settings

            settings = Settings()
            init_observability(
                settings=settings,
                enable_file_logging=False,
            )
            logger.info("Builder service started with observability")
        except Exception as e:
            # Don't fail startup if observability init fails
            print(f"WARNING: Observability initialization failed: {e}")

    # STARTUP - Storage backend (priority: Postgres > Redis > Memory)
    # 1. Try Postgres first (for durable production storage)
    postgres_url = os.getenv("BUILDER_POSTGRES_URL", os.getenv("POSTGRES_URL"))
    if postgres_url:
        try:
            # Ensure asyncpg driver is used
            if not postgres_url.startswith("postgresql+asyncpg://"):
                postgres_url = postgres_url.replace("postgresql://", "postgresql+asyncpg://")

            engine = await create_postgres_engine(postgres_url)
            # Initialize database schema
            await init_builder_database(engine)
            _workflow_manager = PostgresWorkflowManager(engine=engine)
            _storage_backend = "postgres"
            logger.info(
                "Builder connected to PostgreSQL for workflow storage",
                extra={"backend": "postgres"},
            )
        except Exception as e:
            logger.warning(f"Failed to connect to PostgreSQL: {e}")
            # Fall through to Redis

    # 2. Try Redis if Postgres not configured or failed
    if _storage_backend == "memory":
        redis_url = os.getenv("BUILDER_REDIS_URL", os.getenv("REDIS_URL"))
        if redis_url:
            try:
                redis_client = await create_redis_pool(redis_url)
                # Test connection
                await redis_client.ping()
                # No TTL for workflows - they should persist indefinitely
                _workflow_manager = RedisWorkflowManager(redis_client=redis_client, ttl_seconds=None)
                _storage_backend = "redis"
                logger.info(
                    "Builder connected to Redis for workflow storage",
                    extra={"backend": "redis"},
                )
            except Exception as e:
                logger.warning(f"Failed to connect to Redis, using in-memory storage: {e}")

    # 3. Fallback to in-memory
    if _storage_backend == "memory":
        logger.info(
            "Using in-memory workflow storage (data will be lost on restart)",
            extra={"backend": "memory"},
        )

    yield  # Application runs here

    # SHUTDOWN
    if _workflow_manager:
        await _workflow_manager.close()
        logger.info(f"Builder {_storage_backend} connection closed")

    logger.info("Builder service shutting down")
    shutdown_observability()


app = FastAPI(
    title="MCP Server Visual Workflow Builder",
    description="Visual editor for LangGraph agent workflows with code export",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Endpoints
# ==============================================================================


@app.get("/api/builder")
def api_info() -> dict[str, Any]:
    """API information endpoint (moved from root to allow SPA serving)."""
    return {
        "name": "Visual Workflow Builder API",
        "version": "1.0.0",
        "features": [
            "Generate Python code from visual workflows",
            "Validate workflow structure",
            "Export production-ready code",
            "Template library",
        ],
        "unique_feature": "Code export (OpenAI AgentKit doesn't have this!)",
    }


@app.get("/api/builder/health")
def health_check() -> dict[str, str]:
    """
    Health check endpoint for Kubernetes probes.

    This endpoint is publicly accessible (no authentication required)
    to support liveness and readiness probes.

    Returns:
        Health status
    """
    return {"status": "healthy"}


@app.post("/api/builder/generate")
async def generate_code(
    request: GenerateCodeRequest,
    _auth: None = Depends(verify_builder_auth),
) -> GenerateCodeResponse:
    """
    Generate Python code from visual workflow.

    This is our unique feature! OpenAI AgentKit can't export code.

    Args:
        request: Workflow definition

    Returns:
        Generated Python code

    Example:
        POST /api/builder/generate
        {
            "workflow": {
                "name": "my_agent",
                "nodes": [...],
                "edges": [...]
            }
        }
    """
    with tracer.start_as_current_span(
        "builder.generate_code",
        attributes={
            "workflow.name": request.workflow.get("name", "unknown"),
            "workflow.node_count": len(request.workflow.get("nodes", [])),
        },
    ):
        try:
            # Parse workflow
            workflow = WorkflowDefinition(**request.workflow)

            # Generate code
            generator = CodeGenerator()
            code = generator.generate(workflow)

            # Check for warnings
            warnings = []
            if not workflow.description:
                warnings.append("Workflow description is empty - consider adding one")

            if len(workflow.nodes) < 2:
                warnings.append("Workflow has only one node - consider adding more steps")

            logger.info(
                "Code generated successfully",
                extra={
                    "workflow_name": workflow.name,
                    "node_count": len(workflow.nodes),
                    "code_length": len(code),
                },
            )

            return GenerateCodeResponse(code=code, formatted=True, warnings=warnings)

        except Exception as e:
            logger.warning(f"Code generation failed: {e!s}")
            raise HTTPException(status_code=400, detail=f"Code generation failed: {e!s}")


@app.post("/api/builder/validate")
async def validate_workflow(request: ValidateWorkflowRequest) -> ValidateWorkflowResponse:
    """
    Validate workflow structure.

    Checks for:
    - Valid node IDs
    - Valid edge connections
    - Entry point exists
    - No circular dependencies (future)
    - Unreachable nodes

    Args:
        request: Workflow to validate

    Returns:
        Validation results
    """
    with tracer.start_as_current_span(
        "builder.validate_workflow",
        attributes={
            "workflow.name": request.workflow.get("name", "unknown"),
            "workflow.node_count": len(request.workflow.get("nodes", [])),
            "workflow.edge_count": len(request.workflow.get("edges", [])),
        },
    ):
        try:
            workflow = WorkflowDefinition(**request.workflow)

            errors = []
            warnings = []

            # Validate nodes
            if not workflow.nodes:
                errors.append("Workflow must have at least one node")

            # Validate entry point
            node_ids = {n.id for n in workflow.nodes}
            if workflow.entry_point not in node_ids:
                errors.append(f"Entry point '{workflow.entry_point}' not found in nodes")

            # Validate edges
            for edge in workflow.edges:
                if edge.from_node not in node_ids:
                    errors.append(f"Edge source '{edge.from_node}' not found")
                if edge.to_node not in node_ids:
                    errors.append(f"Edge target '{edge.to_node}' not found")

            # Check for unreachable nodes
            reachable = {workflow.entry_point}
            queue = [workflow.entry_point]

            while queue:
                current = queue.pop(0)
                for edge in workflow.edges:
                    if edge.from_node == current and edge.to_node not in reachable:
                        reachable.add(edge.to_node)
                        queue.append(edge.to_node)

            unreachable = node_ids - reachable
            if unreachable:
                warnings.append(f"Unreachable nodes: {', '.join(unreachable)}")

            # Check for nodes with no outgoing edges (potential dead ends)
            nodes_with_outgoing = {e.from_node for e in workflow.edges}
            terminal_nodes = node_ids - nodes_with_outgoing

            if len(terminal_nodes) > 3:
                warnings.append(f"Many terminal nodes ({len(terminal_nodes)}): {', '.join(list(terminal_nodes)[:3])}...")

            is_valid = len(errors) == 0
            logger.info(
                "Workflow validation complete",
                extra={
                    "workflow_name": workflow.name,
                    "valid": is_valid,
                    "error_count": len(errors),
                    "warning_count": len(warnings),
                },
            )

            return ValidateWorkflowResponse(valid=is_valid, errors=errors, warnings=warnings)

        except Exception as e:
            logger.warning(f"Workflow validation failed: {e!s}")
            return ValidateWorkflowResponse(valid=False, errors=[f"Validation error: {e!s}"])


@app.post("/api/builder/save")
async def save_workflow(
    request: SaveWorkflowRequest,
    _auth: None = Depends(verify_builder_auth),
) -> dict[str, Any]:
    """
    Save workflow to Python file.

    Args:
        request: Workflow and output path

    Returns:
        Success message

    Example:
        POST /api/builder/save
        {
            "workflow": {...},
            "output_path": "src/agents/my_agent.py"
        }
    """
    try:
        # Parse and generate
        workflow = WorkflowDefinition(**request.workflow)
        generator = CodeGenerator()

        # SECURITY: Ensure directory exists and is writable (but path is already validated)
        output_path = Path(request.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate and save
        generator.generate_to_file(workflow, str(output_path))

        return {"success": True, "message": f"Workflow saved to {request.output_path}", "path": request.output_path}

    except ValueError as e:
        # Path validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {e!s}")


@app.get("/api/builder/templates")
async def list_templates() -> dict[str, Any]:
    """
    List available workflow templates.

    Returns:
        List of templates

    Example:
        GET /api/builder/templates
    """
    templates = [
        {
            "id": "simple_agent",
            "name": "Simple Agent",
            "description": "Basic single-node agent",
            "complexity": "beginner",
            "nodes": 1,
        },
        {
            "id": "research_agent",
            "name": "Research Agent",
            "description": "Search and summarize workflow",
            "complexity": "intermediate",
            "nodes": 3,
        },
        {
            "id": "customer_support",
            "name": "Customer Support",
            "description": "Multi-path support agent with escalation",
            "complexity": "advanced",
            "nodes": 6,
        },
        {
            "id": "multi_agent_supervisor",
            "name": "Multi-Agent Supervisor",
            "description": "Supervisor coordinating multiple specialists",
            "complexity": "advanced",
            "nodes": 5,
        },
    ]

    return {"templates": templates}


@app.get("/api/builder/templates/{template_id}")
async def get_template(template_id: str) -> dict[str, Any]:
    """
    Get a specific workflow template.

    Args:
        template_id: Template identifier

    Returns:
        Template definition

    Example:
        GET /api/builder/templates/research_agent
    """
    # Simple research agent template
    if template_id == "research_agent":
        builder = WorkflowBuilder("research_agent", "Research and summarize topics")

        builder.add_state_field("query", "str")
        builder.add_state_field("search_results", "List[str]")
        builder.add_state_field("summary", "str")

        builder.add_node("search", "tool", {"tool": "web_search"}, "Web Search")
        builder.add_node("filter", "custom", {}, "Filter Results")
        builder.add_node("summarize", "llm", {"model": "gemini-flash"}, "Summarize")

        builder.add_edge("search", "filter")
        builder.add_edge("filter", "summarize")

        return {"template": builder.to_json()}

    raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")


# ==============================================================================
# Workflow CRUD Endpoints (Redis-backed with in-memory fallback)
# ==============================================================================


def _stored_to_response(workflow: StoredWorkflow) -> WorkflowResponse:
    """Convert StoredWorkflow to API response."""
    return WorkflowResponse(
        id=workflow.id,
        name=workflow.name,
        description=workflow.description,
        nodes=workflow.nodes,
        edges=workflow.edges,
        created_at=workflow.created_at.isoformat(),
        updated_at=workflow.updated_at.isoformat(),
    )


@app.post("/api/builder/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: CreateWorkflowRequest,
    _auth: None = Depends(verify_builder_auth),
) -> WorkflowResponse:
    """
    Create a new workflow.

    Args:
        request: Workflow data

    Returns:
        Created workflow with ID

    Example:
        POST /api/builder/workflows
        {"name": "My Workflow", "nodes": [...], "edges": [...]}
    """
    if _storage_backend != "memory" and _workflow_manager:
        # Use persistent storage (Postgres or Redis)
        workflow = await _workflow_manager.create_workflow(
            name=request.name,
            description=request.description,
            nodes=request.nodes,
            edges=request.edges,
        )
        logger.info(
            f"Workflow created ({_storage_backend})",
            extra={"workflow_id": workflow.id, "workflow_name": request.name, "backend": _storage_backend},
        )
        return _stored_to_response(workflow)
    else:
        # In-memory fallback
        workflow_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        workflow_data: dict[str, Any] = {
            "id": workflow_id,
            "name": request.name,
            "description": request.description,
            "nodes": request.nodes,
            "edges": request.edges,
            "created_at": now,
            "updated_at": now,
        }

        _workflows_fallback[workflow_id] = workflow_data

        logger.info(
            "Workflow created (in-memory)",
            extra={"workflow_id": workflow_id, "workflow_name": request.name},
        )

        return WorkflowResponse(
            id=workflow_id,
            name=request.name,
            description=request.description,
            nodes=request.nodes,
            edges=request.edges,
            created_at=now,
            updated_at=now,
        )


@app.get("/api/builder/workflows")
async def list_workflows(
    _auth: None = Depends(verify_builder_auth),
) -> dict[str, Any]:
    """
    List all workflows.

    Returns:
        List of workflows
    """
    if _storage_backend != "memory" and _workflow_manager:
        summaries = await _workflow_manager.list_workflows()
        workflows = [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "node_count": s.node_count,
                "edge_count": s.edge_count,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in summaries
        ]
        return {"workflows": workflows, "storage_backend": _storage_backend}
    else:
        workflows = list(_workflows_fallback.values())
        return {"workflows": workflows, "storage_backend": "memory"}


@app.get("/api/builder/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    _auth: None = Depends(verify_builder_auth),
) -> WorkflowResponse:
    """
    Get a specific workflow by ID.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Workflow data
    """
    if _storage_backend != "memory" and _workflow_manager:
        workflow = await _workflow_manager.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        return _stored_to_response(workflow)
    else:
        if workflow_id not in _workflows_fallback:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
        return WorkflowResponse(**_workflows_fallback[workflow_id])


@app.put("/api/builder/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    _auth: None = Depends(verify_builder_auth),
) -> WorkflowResponse:
    """
    Update an existing workflow.

    Args:
        workflow_id: Workflow identifier
        request: Updated workflow data

    Returns:
        Updated workflow
    """
    if _storage_backend != "memory" and _workflow_manager:
        workflow = await _workflow_manager.update_workflow(
            workflow_id=workflow_id,
            name=request.name,
            description=request.description,
            nodes=request.nodes,
            edges=request.edges,
        )
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

        logger.info(
            f"Workflow updated ({_storage_backend})",
            extra={"workflow_id": workflow_id, "backend": _storage_backend},
        )
        return _stored_to_response(workflow)
    else:
        if workflow_id not in _workflows_fallback:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

        workflow_dict = _workflows_fallback[workflow_id]
        now = datetime.now(UTC).isoformat()

        # Update only provided fields
        if request.name is not None:
            workflow_dict["name"] = request.name
        if request.description is not None:
            workflow_dict["description"] = request.description
        if request.nodes is not None:
            workflow_dict["nodes"] = request.nodes
        if request.edges is not None:
            workflow_dict["edges"] = request.edges

        workflow_dict["updated_at"] = now

        logger.info(
            "Workflow updated (in-memory)",
            extra={"workflow_id": workflow_id},
        )

        return WorkflowResponse(**workflow_dict)


@app.delete("/api/builder/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    _auth: None = Depends(verify_builder_auth),
) -> None:
    """
    Delete a workflow.

    Args:
        workflow_id: Workflow identifier
    """
    if _storage_backend != "memory" and _workflow_manager:
        deleted = await _workflow_manager.delete_workflow(workflow_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

        logger.info(
            f"Workflow deleted ({_storage_backend})",
            extra={"workflow_id": workflow_id, "backend": _storage_backend},
        )
    else:
        if workflow_id not in _workflows_fallback:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")

        del _workflows_fallback[workflow_id]

        logger.info(
            "Workflow deleted (in-memory)",
            extra={"workflow_id": workflow_id, "backend": "memory"},
        )


@app.post("/api/builder/import")
async def import_workflow(
    request: ImportWorkflowRequest,
    _auth: None = Depends(verify_builder_auth),
) -> dict[str, Any]:
    """
    Import Python code into visual workflow.

    Round-trip capability: Code → Visual (import) + Visual → Code (export)

    Args:
        request: Import request containing code and layout

    Returns:
        Workflow definition ready for visual builder

    Example:
        POST /api/builder/import
        {
            "code": "from langgraph.graph import StateGraph\\n...",
            "layout": "hierarchical"
        }
    """
    try:
        from ..importer import import_from_code, validate_import

        # Import code
        workflow = import_from_code(request.code, layout_algorithm=request.layout)

        # Validate
        validation = validate_import(workflow)

        return {
            "workflow": workflow,
            "validation": validation,
            "message": "Code imported successfully",
        }

    except SyntaxError as e:
        raise HTTPException(status_code=400, detail=f"Invalid Python syntax: {e!s}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {e!s}")


@app.get("/api/builder/node-types")
async def list_node_types() -> dict[str, Any]:
    """
    List available node types for the builder.

    Returns:
        Node type definitions with configuration schemas
    """
    node_types = [
        {
            "type": "tool",
            "name": "Tool",
            "description": "Execute a tool or function",
            "icon": "tool",
            "config_schema": {"tool": {"type": "string", "required": True, "description": "Tool name"}},
        },
        {
            "type": "llm",
            "name": "LLM",
            "description": "Call language model",
            "icon": "brain",
            "config_schema": {
                "model": {"type": "string", "required": True, "description": "Model name"},
                "temperature": {"type": "number", "required": False, "default": 0.7},
            },
        },
        {
            "type": "conditional",
            "name": "Conditional",
            "description": "Conditional routing based on state",
            "icon": "split",
            "config_schema": {},
        },
        {
            "type": "approval",
            "name": "Approval",
            "description": "Human approval checkpoint",
            "icon": "user-check",
            "config_schema": {"risk_level": {"type": "string", "enum": ["low", "medium", "high", "critical"]}},
        },
        {
            "type": "custom",
            "name": "Custom",
            "description": "Custom Python function",
            "icon": "code",
            "config_schema": {},
        },
    ]

    return {"node_types": node_types}


# ==============================================================================
# SPA Static Files Mount (React Frontend)
# ==============================================================================
# Mount AFTER all API routes - SPAStaticFiles is a catch-all for client-side routing

# Calculate frontend dist path relative to this module
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"

# Only mount if frontend is built (graceful degradation for API-only mode)
_spa_handler = create_spa_static_files(str(_frontend_dist), caching=True)
if _spa_handler is not None:
    app.mount("/", _spa_handler, name="spa")


# ==============================================================================
# Run Server
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("🎨 Visual Workflow Builder API")
    print("=" * 80)
    print("\nStarting server...")
    print("\n📍 Endpoints:")
    print("   • Info:      http://localhost:8001/")
    print("   • Generate:  POST http://localhost:8001/api/builder/generate")
    print("   • Validate:  POST http://localhost:8001/api/builder/validate")
    print("   • Templates: GET http://localhost:8001/api/builder/templates")
    print("   • Docs:      http://localhost:8001/docs")
    print("\n🌟 Unique Feature: Code Export (OpenAI AgentKit doesn't have this!)")
    print("=" * 80)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)  # nosec B104
