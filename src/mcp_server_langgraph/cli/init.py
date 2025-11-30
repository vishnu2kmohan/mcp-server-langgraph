"""
Project initialization command for MCP Server CLI.

Handles creation of new MCP Server projects with different templates.
"""

from pathlib import Path
from typing import Literal

ProjectTemplate = Literal["quickstart", "production", "enterprise"]


def init_project(name: str, template: ProjectTemplate = "production") -> None:
    """
    Initialize a new MCP Server project with the specified template.

    Args:
        name: Name of the project (will be used as directory name)
        template: Project template to use:
            - quickstart: Minimal in-memory setup (2-minute start)
            - production: Full Docker Compose stack (15-minute start)
            - enterprise: Kubernetes with Keycloak + OpenFGA

    Raises:
        FileExistsError: If project directory already exists
        ValueError: If template is invalid
    """
    if template not in ["quickstart", "production", "enterprise"]:
        msg = f"Invalid template: {template}. Must be one of: quickstart, production, enterprise"
        raise ValueError(msg)

    project_dir = Path(name)

    if project_dir.exists():
        msg = f"Directory '{name}' already exists"
        raise FileExistsError(msg)

    # Create project directory
    project_dir.mkdir(parents=True)

    if template == "quickstart":
        _create_quickstart_project(project_dir, name)
    elif template == "production":
        _create_production_project(project_dir, name)
    else:  # enterprise
        _create_enterprise_project(project_dir, name)


def _create_quickstart_project(project_dir: Path, name: str) -> None:
    """
    Create a minimal quick-start project.

    Features:
    - In-memory storage (no Docker needed)
    - Simple agent with basic tools
    - FastAPI server with minimal config
    - Ready to run in < 2 minutes
    """
    # Create directory structure
    (project_dir / "src").mkdir()
    (project_dir / "tests").mkdir()

    # Create pyproject.toml
    pyproject_content = f"""[project]
name = "{name}"
version = "0.1.0"
description = "MCP Server with LangGraph - Quick Start Project"
requires-python = ">=3.11"
dependencies = [
    "mcp-server-langgraph>=2.8.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "langgraph>=1.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.3.4",
    "pytest-asyncio>=0.25.0",
]
"""
    (project_dir / "pyproject.toml").write_text(pyproject_content)

    # Create app.py
    app_content = '''"""
MCP Server Quick Start Application

A minimal MCP server with in-memory storage and basic tools.
Ready to run in < 2 minutes!
"""

from fastapi import FastAPI
from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Annotated

app = FastAPI(title="MCP Server Quick Start")


# Define agent state
class AgentState(TypedDict):
    """State for the quick-start agent."""
    messages: Annotated[list[str], "The conversation messages"]
    query: str
    response: str


# Create simple agent graph
graph = StateGraph(AgentState)


def handle_query(state: AgentState) -> AgentState:
    """Handle user query with a simple response."""
    query = state["query"]
    state["response"] = f"Echo: {query}"
    state["messages"].append(f"User: {query}")
    state["messages"].append(f"Agent: {state['response']}")
    return state


# Build graph
graph.add_node("handle", handle_query)
graph.set_entry_point("handle")
graph.set_finish_point("handle")

# Compile with in-memory checkpointer
checkpointer = MemorySaver()
agent = graph.compile(checkpointer=checkpointer)


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "healthy", "message": "MCP Server Quick Start is running!"}


@app.post("/chat")
def chat(query: str):
    """Chat with the agent."""
    result = agent.invoke(
        {"query": query, "messages": [], "response": ""},
        config={"configurable": {"thread_id": "quickstart"}}
    )
    return {"response": result["response"], "messages": result["messages"]}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting MCP Server Quick Start...")
    print("📝 Visit http://localhost:8000/docs for API documentation")
    print("💬 Try: curl -X POST http://localhost:8000/chat?query=Hello")
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    (project_dir / "app.py").write_text(app_content)

    # Create README
    readme_content = f"""# {name}

MCP Server with LangGraph - Quick Start Project

## Quick Start (< 2 minutes)

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Run the server:**
   ```bash
   uv run python app.py
   ```

3. **Test the agent:**
   ```bash
   curl -X POST "http://localhost:8000/chat?query=Hello"
   ```

4. **View API docs:**
   Open http://localhost:8000/docs in your browser

## Next Steps

- 📖 [Add more tools](https://docs.mcp-server-langgraph.com/guides/adding-tools)
- 🧪 [Write tests](https://docs.mcp-server-langgraph.com/advanced/testing)
- 🚀 [Deploy to production](https://docs.mcp-server-langgraph.com/deployment/overview)

## Features

✅ In-memory storage (no Docker needed)
✅ Simple agent with basic echo functionality
✅ FastAPI server with auto-generated docs
✅ Ready to extend with custom tools and logic

## Upgrade to Production

When you're ready for production features:

```bash
# Add authentication, observability, and more
mcpserver init --template production --name {name}-production
```

See [Production vs Quick Start](https://docs.mcp-server-langgraph.com/comparisons/choosing-framework) for comparison.
"""
    (project_dir / "README.md").write_text(readme_content)

    # Create .gitignore
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Tests
.pytest_cache/
.coverage
htmlcov/
"""
    (project_dir / ".gitignore").write_text(gitignore_content)


def _create_production_project(project_dir: Path, name: str) -> None:
    """
    Create a full production project with Docker Compose.

    Features:
    - Docker Compose stack (Redis, PostgreSQL)
    - Complete observability (LangSmith, Prometheus, Grafana)
    - Environment-based configuration
    - Production-ready structure
    """
    # TODO: Implement cookiecutter-based generation
    # For now, create a placeholder with instructions
    readme_content = f"""# {name}

MCP Server with LangGraph - Production Project

## Production Setup (15 minutes)

This project template will be generated using our production Cookiecutter template.

**Coming Soon:** Full cookiecutter integration

For now, use our existing setup:

```bash
# Clone the repository
git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git {name}
cd {name}

# Start the stack
docker compose up -d

# Run setup scripts
make setup
```

## Features

✅ Docker Compose stack (Redis, PostgreSQL, Jaeger, Prometheus, Grafana)
✅ JWT authentication with Keycloak
✅ OpenFGA authorization
✅ LangSmith + OpenTelemetry observability
✅ Infisical secrets management
✅ Production-ready configuration

See [Documentation](https://docs.mcp-server-langgraph.com/deployment/docker) for full setup.
"""
    (project_dir / "README.md").write_text(readme_content)


def _create_enterprise_project(project_dir: Path, name: str) -> None:
    """
    Create an enterprise project with Kubernetes manifests.

    Features:
    - Kubernetes manifests (Helm charts)
    - Terraform modules (GKE: Complete, EKS: Modules ready, AKS: In development)
    - GitOps ready (ArgoCD)
    - Multi-region support

    Platform Maturity:
    - GKE: Production Ready (full automation, dev/staging/prod)
    - EKS: Beta (modules complete, prod environment ready)
    - AKS: Alpha (manual deployment only)
    """
    # TODO: Implement full enterprise template generation
    readme_content = f"""# {name}

MCP Server with LangGraph - Enterprise Project

## Enterprise Setup (1-2 hours)

This project template includes Kubernetes manifests for enterprise deployment.

**Coming Soon:** Full enterprise template with Terraform + Helm

For now, use our enterprise deployment guides:

- [GKE Deployment](https://docs.mcp-server-langgraph.com/deployment/kubernetes/gke)
- [EKS Deployment](https://docs.mcp-server-langgraph.com/deployment/kubernetes/eks)
- [AKS Deployment](https://docs.mcp-server-langgraph.com/deployment/kubernetes/aks)

## Features

✅ Helm charts for Kubernetes
✅ Terraform modules (GCP, AWS, Azure)
✅ GitOps with ArgoCD
✅ Multi-region deployment
✅ Complete compliance (GDPR, HIPAA, SOC 2)
✅ Enterprise security (Keycloak, OpenFGA, Binary Authorization)

See [Enterprise Documentation](https://docs.mcp-server-langgraph.com/deployment/kubernetes) for full setup.
"""
    (project_dir / "README.md").write_text(readme_content)
