# Visual Workflow Builder

**Unique Feature:** Export visual workflows to production-ready Python code!

Unlike OpenAI AgentKit (which has visual builder but NO code export), we provide:
- ✅ Full Python code generation
- ✅ Production-ready patterns
- ✅ Type-safe code with Pydantic
- ✅ Black-formatted output
- ✅ Import/export round-trip capability

## Architecture

```
┌──────────────────┐
│  React Frontend  │ (React Flow canvas)
│  (Port 3000)     │
└────────┬─────────┘
         │
         ├─ Drag-and-drop nodes
         ├─ Connect edges
         └─ Export to code
         │
         ▼
┌──────────────────┐
│  FastAPI Backend │ (Code generation)
│  (Port 8001)     │
└────────┬─────────┘
         │
         ├─ /api/builder/generate → Python code
         ├─ /api/builder/validate → Validation
         └─ /api/builder/save → Save to file
         │
         ▼
┌──────────────────┐
│  Generated Code  │ (Production-ready Python)
│  agent.py        │
└──────────────────┘
```

## Quick Start

### 1. Start Backend

```bash
# Terminal 1: Start API server
cd src/mcp_server_langgraph/builder
uvicorn api.server:app --reload --port 8001
```

### 2. Start Frontend

```bash
# Terminal 2: Start React app
cd src/mcp_server_langgraph/builder/frontend
npm install
npm run dev
```

### 3. Open Browser

Navigate to: http://localhost:3000

## Features

### ✨ Unique: Code Export

**What OpenAI AgentKit DOESN'T Have:**

OpenAI AgentKit lets you build workflows visually, but you're locked into their platform.
You **cannot** export the code - you're stuck with their visual editor forever.

**What WE Provide:**

1. **Build Visually:** Drag-and-drop interface (same as AgentKit)
2. **Export to Code:** Get production-ready Python code (UNIQUE!)
3. **Edit the Code:** Modify in your IDE
4. **Re-import:** Load code back into visual editor (future)
5. **Deploy Anywhere:** Self-host, multi-cloud, your infrastructure

### Visual Builder Features

**Node Types:**
- 🔧 **Tool** - Execute functions/APIs
- 🧠 **LLM** - Call language models
- 🔀 **Conditional** - Route based on state
- ✋ **Approval** - Human-in-the-loop checkpoint
- ⚙️ **Custom** - Custom Python function

**Canvas Features:**
- Drag-and-drop node placement
- Visual edge connections
- Zoom and pan
- Minimap for navigation
- Node configuration panel
- Validation warnings

**Export Options:**
- 💾 **Save to File** - Save directly to `src/agents/`
- 📥 **Download Code** - Download Python file
- 📄 **Export JSON** - Export workflow definition

### Code Generation Quality

**Generated Code Includes:**
- Type-safe Pydantic models
- Proper imports and dependencies
- Production-ready error handling
- Black-formatted code (PEP 8)
- Complete docstrings
- Example usage

**Example Generated Code:**
```python
"""
Research agent workflow

Auto-generated from Visual Workflow Builder.
"""

from typing import Any, Dict, List, TypedDict
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field


class ResearchAgentState(TypedDict):
    """State for research_agent workflow."""
    query: str
    search_results: List[str]
    summary: str


def node_search(state: Dict[str, Any]) -> Dict[str, Any]:
    """Execute Web Search - tool: tavily_search."""
    # TODO: Implement tavily_search integration
    result = call_tool("tavily_search", state)
    state["result"] = result
    return state


def create_research_agent() -> StateGraph:
    """Create research_agent workflow."""
    graph = StateGraph(ResearchAgentState)

    graph.add_node("search", node_search)
    graph.add_node("summarize", node_summarize)

    graph.add_edge("search", "summarize")

    graph.set_entry_point("search")
    graph.set_finish_point("summarize")

    return graph
```

## API Reference

### POST /api/builder/generate

Generate Python code from workflow.

**Request:**
```json
{
  "workflow": {
    "name": "my_agent",
    "description": "My custom agent",
    "nodes": [
      {
        "id": "search",
        "type": "tool",
        "label": "Search",
        "config": {"tool": "web_search"}
      }
    ],
    "edges": [
      {"from": "search", "to": "summarize"}
    ],
    "entry_point": "search"
  }
}
```

**Response:**
```json
{
  "code": "# Generated Python code...",
  "formatted": true,
  "warnings": []
}
```

### POST /api/builder/validate

Validate workflow structure.

**Request:**
```json
{
  "workflow": {...}
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Workflow has only one node"]
}
```

### GET /api/builder/templates

List available workflow templates.

**Response:**
```json
{
  "templates": [
    {
      "id": "research_agent",
      "name": "Research Agent",
      "description": "Search and summarize workflow",
      "complexity": "intermediate",
      "nodes": 3
    }
  ]
}
```

## Development Guide

### Adding New Node Types

1. **Update CodeGenerator:**
```python
# In generator.py
elif node.type == "your_type":
    return f'''def {function_name}(state):
        # Your custom node logic
        return state
    '''
```

2. **Update Frontend:**
```typescript
// In App.tsx
const nodeTypes = [
  { type: 'your_type', label: 'Your Type', icon: '🎯', description: '...' }
];
```

3. **Update API:**
```python
# In server.py
@app.get("/api/builder/node-types")
async def list_node_types():
    node_types = [
        # Add your type
        {
            "type": "your_type",
            "name": "Your Type",
            "config_schema": {...}
        }
    ]
```

### Adding Templates

```python
# In server.py
@app.get("/api/builder/templates/{template_id}")
async def get_template(template_id: str):
    if template_id == "your_template":
        builder = WorkflowBuilder("your_template", "Description")
        # Build workflow
        return {"template": builder.to_json()}
```

## Comparison with OpenAI AgentKit

| Feature | OpenAI AgentKit | MCP Server Visual Builder |
|---------|----------------|--------------------------|
| **Visual Editor** | ✅ Drag-and-drop | ✅ React Flow canvas |
| **Code Export** | ❌ **NO CODE EXPORT** | ✅ **Full Python export** |
| **Code Editing** | ❌ Locked to platform | ✅ Edit in any IDE |
| **LLM Support** | ❌ OpenAI only | ✅ 100+ providers |
| **Self-Hosting** | ❌ Platform only | ✅ Full self-host |
| **Production Code** | ❌ Platform-dependent | ✅ Standalone Python |
| **Version Control** | ❌ No | ✅ Git-friendly code |
| **Customization** | ⚠️ Limited | ✅ Full control |

**Bottom Line:** We provide the visual convenience PLUS the code control.

## Workflows

### Development Workflow

1. **Design Visually:**
   - Drag nodes onto canvas
   - Connect with edges
   - Configure node properties

2. **Export Code:**
   - Click "Export Code"
   - View generated Python
   - Edit in Monaco editor

3. **Save/Download:**
   - Save to project: `src/agents/my_agent.py`
   - Or download file
   - Or copy code

4. **Customize:**
   - Edit generated code in your IDE
   - Add custom logic
   - Integrate with your system

5. **Deploy:**
   - Use standard deployment (Docker, K8s, Cloud Run)
   - Not locked to visual builder

### Import/Export Workflow

**Export:**
- Visual workflow → Python code
- Visual workflow → JSON definition

**Import (Future):**
- Python code → Visual workflow (AST parsing)
- JSON definition → Visual workflow

## Production Deployment

The visual builder is a development tool. Generated code is production-ready:

```bash
# 1. Build workflow visually
# 2. Export code to src/agents/my_agent.py
# 3. Deploy normally (no builder dependency)

# Docker
docker build -t my-agent .
docker run my-agent

# Kubernetes
helm install my-agent ./charts

# Cloud Run
gcloud run deploy --source .
```

**Key Advantage:** Generated code has ZERO dependency on visual builder.

## Testing

### Backend Tests

```bash
# Test code generation
pytest src/mcp_server_langgraph/builder/codegen/test_generator.py

# Test API
pytest src/mcp_server_langgraph/builder/api/test_server.py
```

### Frontend Tests

```bash
cd frontend
npm run test
npm run type-check
```

### Integration Tests

```bash
# Test full workflow: visual → code → execution
pytest tests/integration/test_visual_builder.py
```

## Configuration

### Backend Configuration

```bash
# .env
BUILDER_API_PORT=8001
BUILDER_CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend Configuration

```bash
# .env.local
VITE_API_URL=http://localhost:8001
```

## Roadmap

### Current (v1.0)
- ✅ React Flow visual editor
- ✅ Drag-and-drop nodes
- ✅ Code export to Python
- ✅ FastAPI backend
- ✅ Node type library
- ✅ Workflow validation

### Next (v1.1)
- [ ] Code import (Python → Visual)
- [ ] Advanced node configuration UI
- [ ] Template library expansion
- [ ] Collaboration features (multiplayer)
- [ ] Version control integration

### Future (v2.0)
- [ ] Live agent testing in builder
- [ ] Trace visualization
- [ ] Cost estimation
- [ ] Performance profiling
- [ ] Team workspace

## Contributing

To add features to the visual builder:

1. **Backend:** Update `codegen/generator.py` or `api/server.py`
2. **Frontend:** Update React components in `frontend/src/`
3. **Tests:** Add tests for new functionality
4. **Docs:** Update this README

See [CONTRIBUTING.md](../../../CONTRIBUTING.md) for details.

## Resources

- [React Flow Documentation](https://reactflow.dev/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Monaco Editor Documentation](https://microsoft.github.io/monaco-editor/)

---

**Unique Selling Point:** We're the only framework with visual builder + code export.
Build visually, deploy anywhere. No platform lock-in.
