"""
Visual Workflow Builder for MCP Server with LangGraph

A React Flow-based visual editor for agent workflows with unique code export capability.

Unique Features (vs OpenAI AgentKit):
- ✅ Export to Python code (they don't have this!)
- ✅ Import from existing code
- ✅ Works with any LLM provider
- ✅ Self-hostable
- ✅ Production-grade code generation

Components:
- codegen: Code generation from visual workflows
- api: FastAPI backend for builder
- frontend: React Flow visual editor

Example:
    from mcp_server_langgraph.builder import WorkflowBuilder

    # Create builder
    builder = WorkflowBuilder()

    # Define workflow visually (or via API)
    builder.add_node("search", node_type="tool", config={"tool": "web_search"})
    builder.add_node("summarize", node_type="llm", config={"model": "gemini-flash"})
    builder.add_edge("search", "summarize")

    # Export to Python code
    python_code = builder.export_code()
    print(python_code)

    # Result: Production-ready Python code with LangGraph
"""

from .codegen.generator import CodeGenerator, WorkflowDefinition
from .workflow import WorkflowBuilder

__all__ = ["WorkflowBuilder", "CodeGenerator", "WorkflowDefinition"]
