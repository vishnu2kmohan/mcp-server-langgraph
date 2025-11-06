# LangGraph Platform Deployment

This directory contains the agent definition for deployment to LangGraph Platform.

## Dependencies

**This deployment uses the main project's `pyproject.toml` for dependencies.**

LangGraph Platform supports `pyproject.toml` natively. We do NOT need a separate `requirements.txt` file.

### Local Development

```bash
# From project root
uv sync --all-extras
```

### LangGraph Platform Configuration

Add to your `langgraph.json`:

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./deployments/langgraph_platform/agent.py:create_graph"
  }
}
```

The `"dependencies": ["."]` tells LangGraph Platform to install dependencies from the project's `pyproject.toml`.

## Deployment

```bash
# Build and deploy
langgraph build
langgraph deploy
```

LangGraph Platform will automatically:
1. Read dependencies from `../../pyproject.toml`
2. Install them in the deployment environment
3. Load the agent graph from `agent.py`

## No requirements.txt Needed

**Previous approach (DEPRECATED):**
```bash
# DON'T DO THIS
pip install -r requirements.txt
```

**Current approach (UV-native):**
```bash
# LangGraph Platform reads from pyproject.toml automatically
uv sync  # For local development only
```

---

**Source of Truth:** `../../pyproject.toml`
**Dependency Manager:** UV (locally), LangGraph Platform (deployment)
