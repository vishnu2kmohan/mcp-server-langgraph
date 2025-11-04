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

from typing import Any, Dict, List, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..codegen import CodeGenerator, WorkflowDefinition
from ..workflow import WorkflowBuilder

# ==============================================================================
# API Models
# ==============================================================================


class GenerateCodeRequest(BaseModel):
    """Request to generate code from workflow."""

    workflow: Dict[str, Any]


class GenerateCodeResponse(BaseModel):
    """Response with generated code."""

    code: str
    formatted: bool
    warnings: List[str] = []


class ValidateWorkflowRequest(BaseModel):
    """Request to validate workflow."""

    workflow: Dict[str, Any]


class ValidateWorkflowResponse(BaseModel):
    """Response with validation results."""

    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class SaveWorkflowRequest(BaseModel):
    """Request to save workflow to file."""

    workflow: Dict[str, Any]
    output_path: str


class ImportWorkflowRequest(BaseModel):
    """Request to import Python code into workflow."""

    code: str
    layout: Literal["hierarchical", "force", "grid"] = "hierarchical"


# ==============================================================================
# FastAPI Application
# ==============================================================================

app = FastAPI(
    title="MCP Server Visual Workflow Builder",
    description="Visual editor for LangGraph agent workflows with code export",
    version="1.0.0",
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


@app.get("/")  # type: ignore[misc]
def root() -> Dict[str, Any]:
    """API information."""
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


@app.post("/api/builder/generate", response_model=GenerateCodeResponse)  # type: ignore[misc]
async def generate_code(request: GenerateCodeRequest) -> GenerateCodeResponse:
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

        return GenerateCodeResponse(code=code, formatted=True, warnings=warnings)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Code generation failed: {str(e)}")


@app.post("/api/builder/validate", response_model=ValidateWorkflowResponse)  # type: ignore[misc]
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

        return ValidateWorkflowResponse(valid=len(errors) == 0, errors=errors, warnings=warnings)

    except Exception as e:
        return ValidateWorkflowResponse(valid=False, errors=[f"Validation error: {str(e)}"])


@app.post("/api/builder/save")  # type: ignore[misc]
async def save_workflow(request: SaveWorkflowRequest) -> Dict[str, Any]:
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

        # Generate and save
        generator.generate_to_file(workflow, request.output_path)

        return {"success": True, "message": f"Workflow saved to {request.output_path}", "path": request.output_path}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Save failed: {str(e)}")


@app.get("/api/builder/templates")  # type: ignore[misc]
async def list_templates() -> Dict[str, Any]:
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


@app.get("/api/builder/templates/{template_id}")  # type: ignore[misc]
async def get_template(template_id: str) -> Dict[str, Any]:
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


@app.post("/api/builder/import")  # type: ignore[misc]
async def import_workflow(request: ImportWorkflowRequest) -> Dict[str, Any]:
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
        raise HTTPException(status_code=400, detail=f"Invalid Python syntax: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@app.get("/api/builder/node-types")  # type: ignore[misc]
async def list_node_types() -> Dict[str, Any]:
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
