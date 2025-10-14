# LangSmith Integration Guide

Complete guide for integrating LangSmith observability into the MCP Server with LangGraph.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Tracing](#tracing)
- [Datasets and Evaluation](#datasets-and-evaluation)
- [Feedback Collection](#feedback-collection)
- [Debugging](#debugging)
- [Best Practices](#best-practices)

---

## Overview

LangSmith is LangChain's observability and debugging platform. It provides:

- **Automatic Tracing**: Capture all LLM calls and agent steps
- **Prompt Engineering**: Iterate on prompts with production data
- **Dataset Creation**: Build test datasets from traces
- **Evaluation**: Compare model performance
- **Debugging**: Root cause analysis for failures
- **User Feedback**: Collect and analyze user ratings
- **Cost Tracking**: Monitor LLM API costs

### Why LangSmith?

✅ **For Developers**:
- See exactly what your agent is doing
- Debug failures with full context
- Optimize prompts based on real usage
- Track costs per user/session

✅ **For Teams**:
- Share traces for collaboration
- Create regression test suites
- Monitor production performance
- Analyze user feedback

---

## Quick Start

### 1. Create LangSmith Account

1. Visit: https://smith.langchain.com/
2. Sign up for free account
3. Create a new project (e.g., "mcp-server-langgraph")

### 2. Get API Key

1. Go to: https://smith.langchain.com/settings
2. Click "Create API Key"
3. Copy the key (starts with `lsv2_pt_...`)

### 3. Enable LangSmith Tracing

**Option A: Environment Variables**

```bash
# Add to your .env file
LANGSMITH_API_KEY=lsv2_pt_your_key_here
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=mcp-server-langgraph
```

**Option B: Programmatic Configuration**

```python
from mcp_server_langgraph.core.config import settings

# LangSmith is automatically configured if API key is set
# Tracing starts immediately when you run your agent
```

### 4. Run Your Agent

```bash
# Start the agent
python -m mcp_server_langgraph.mcp.server_stdio

# Or run with explicit tracing
LANGSMITH_TRACING=true python -m mcp_server_langgraph.mcp.server_stdio
```

### 5. View Traces

1. Go to: https://smith.langchain.com/
2. Select your project
3. See all traces appear in real-time!

---

## Configuration

### Environment Variables

**Required**:
```bash
LANGSMITH_API_KEY=lsv2_pt_your_key_here     # Your API key
LANGSMITH_TRACING=true                       # Enable tracing
```

**Optional**:
```bash
LANGSMITH_PROJECT=mcp-server-langgraph        # Project name
LANGSMITH_ENDPOINT=https://api.smith.langchain.com  # API endpoint
LANGSMITH_TRACING_V2=true                    # Use v2 tracing (recommended)
```

### Programmatic Configuration

The agent is pre-configured to use LangSmith. Configuration is in `src/mcp_server_langgraph/core/config.py`:

```python
class Settings(BaseSettings):
    # LangSmith Observability
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "mcp-server-langgraph"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_tracing: bool = False
    langsmith_tracing_v2: bool = True

    # Observability Backend Selection
    observability_backend: str = "both"  # opentelemetry, langsmith, both
```

### Dual Observability (OpenTelemetry + LangSmith)

This project supports **both** OpenTelemetry and LangSmith:

- **OpenTelemetry**: Infrastructure metrics, distributed tracing, custom metrics
- **LangSmith**: LLM-specific tracing, prompt engineering, evaluations

**Enable both**:
```bash
# .env
OBSERVABILITY_BACKEND=both
LANGSMITH_TRACING=true
```

**Use only LangSmith**:
```bash
OBSERVABILITY_BACKEND=langsmith
LANGSMITH_TRACING=true
```

---

## Tracing

### Automatic Tracing

When LangSmith is enabled, **all agent invocations are automatically traced**:

```python
from mcp_server_langgraph.core.agent import agent_graph

# This invocation is automatically traced
result = agent_graph.invoke({
    "messages": [HumanMessage(content="Hello")],
    "user_id": "user123",
    "request_id": "req456"
})
```

**What's captured**:
- All LLM calls (prompts, completions, tokens)
- Agent routing decisions
- Tool invocations
- Intermediate states
- Timing information
- Error stack traces

### Manual Tracing

Add custom metadata to traces:

```python
from mcp_server_langgraph.observability.langsmith import langsmith_config

# Create run configuration
run_config = langsmith_config.create_run_config(
    run_name="user-query",
    user_id="user123",
    request_id="req456",
    tags=["production", "premium-user"],
    metadata={"query_type": "analysis"}
)

# Use in invocation
result = agent_graph.invoke(inputs, config=run_config)
```

### Nested Tracing

LangSmith automatically creates hierarchical traces:

```
┌─ Agent Invocation (2.3s)
│  ├─ Router Node (0.1s)
│  ├─ Tool Call: search (1.5s)
│  │  └─ LLM Call (0.8s)
│  └─ Response Generation (0.7s)
│     └─ LLM Call (0.6s)
```

### Tracing with Context

Add business context to traces:

```python
from langchain_core.runnables import RunnableConfig

config = RunnableConfig(
    tags=["user:alice", "department:sales", "priority:high"],
    metadata={
        "user_id": "alice@company.com",
        "session_id": "sess_123",
        "request_source": "slack",
        "cost_center": "sales-dept"
    }
)

result = agent_graph.invoke(inputs, config=config)
```

---

## Datasets and Evaluation

### Create Dataset from Traces

1. **In LangSmith UI**:
   - Go to your project
   - Filter traces (e.g., "success only", "last 7 days")
   - Click "Add to Dataset"
   - Name your dataset (e.g., "prod-examples-2025-01")

2. **Programmatically**:

```python
from langsmith import Client

client = Client()

# Create dataset
dataset = client.create_dataset("my-test-set")

# Add examples
client.create_examples(
    inputs=[
        {"messages": [{"role": "user", "content": "What is LangGraph?"}]},
        {"messages": [{"role": "user", "content": "How do I deploy?"}]}
    ],
    outputs=[
        {"response": "LangGraph is a framework for building..."},
        {"response": "To deploy, you can use..."}
    ],
    dataset_id=dataset.id
)
```

### Run Evaluations

Compare model performance on datasets:

```python
from langsmith import Client
from mcp_server_langgraph.core.agent import agent_graph

client = Client()

# Run evaluation
results = client.run_on_dataset(
    dataset_name="my-test-set",
    llm_or_chain_factory=lambda: agent_graph,
    project_name="eval-2025-01-10"
)

# View results in LangSmith UI
```

### Custom Evaluators

Create custom evaluation metrics:

```python
from langsmith.evaluation import evaluate

def accuracy_evaluator(run, example):
    """Check if response contains expected keywords"""
    response = run.outputs.get("response", "")
    expected = example.outputs.get("expected_keywords", [])

    score = sum(1 for kw in expected if kw.lower() in response.lower()) / len(expected)

    return {"score": score, "key": "accuracy"}

# Run evaluation with custom evaluator
evaluate(
    lambda inputs: agent_graph.invoke(inputs),
    data="my-test-set",
    evaluators=[accuracy_evaluator],
    experiment_prefix="custom-eval"
)
```

---

## Feedback Collection

### Programmatic Feedback

Collect user feedback on responses:

```python
from langsmith import Client

client = Client()

# After agent response, collect feedback
run_id = "run-uuid-from-trace"  # Get from trace

client.create_feedback(
    run_id=run_id,
    key="user_rating",
    score=1.0,  # 0.0 to 1.0
    comment="Great response!",
    source_info={"user_id": "user123"}
)
```

### Feedback Schema

**Built-in feedback types**:
- **Thumbs up/down**: Binary rating
  ```python
  client.create_feedback(run_id=run_id, key="thumbs", score=1.0)  # thumbs up
  ```

- **Star rating**: 1-5 stars
  ```python
  client.create_feedback(run_id=run_id, key="stars", score=0.8)  # 4 stars
  ```

- **Correctness**: Factual accuracy
  ```python
  client.create_feedback(run_id=run_id, key="correctness", score=1.0)
  ```

### Feedback Analysis

View feedback in LangSmith:
1. Go to project
2. Click "Feedback" tab
3. Filter by feedback type
4. Analyze trends over time

---

## Debugging

### Find Failing Traces

**In LangSmith UI**:
1. Go to your project
2. Filter: `status:error`
3. Sort by: `timestamp desc`
4. Click on trace to see details

**Programmatically**:
```python
from langsmith import Client

client = Client()

# Get recent error traces
runs = client.list_runs(
    project_name="mcp-server-langgraph",
    error=True,
    limit=10
)

for run in runs:
    print(f"Error: {run.error}")
    print(f"Stack trace: {run.stacktrace}")
```

### Analyze Slow Traces

Find performance bottlenecks:

**In LangSmith UI**:
1. Filter: `latency > 5s`
2. Sort by: `latency desc`
3. Expand trace to see timing breakdown

**Optimize based on findings**:
- Identify slow LLM calls → use faster model
- Identify slow tool calls → add caching
- Identify redundant calls → optimize logic

### Compare Traces

Compare successful vs failed traces:

1. Select two traces (shift+click)
2. Click "Compare"
3. See side-by-side diff of:
   - Inputs
   - Intermediate steps
   - Outputs
   - Timing

### Root Cause Analysis

For any trace, you can see:
- **Full input/output**: Exact data sent and received
- **Intermediate steps**: All agent decisions
- **LLM calls**: Prompts and completions
- **Error stack traces**: Full Python traceback
- **Timing breakdown**: Where time was spent
- **Token usage**: Tokens per LLM call
- **Cost**: Estimated cost per call

---

## Best Practices

### 1. Project Organization

Create separate projects for:
- **Development**: `my-agent-dev`
- **Staging**: `my-agent-staging`
- **Production**: `my-agent-prod`

```bash
# Set project per environment
LANGSMITH_PROJECT=my-agent-prod python -m mcp_server_langgraph.mcp.server_stdio
```

### 2. Tagging Strategy

Use consistent tags:
- **Environment**: `production`, `staging`, `development`
- **User tier**: `free`, `pro`, `enterprise`
- **Feature**: `chat`, `analysis`, `search`
- **Priority**: `high`, `medium`, `low`

```python
config = RunnableConfig(
    tags=["production", "pro-user", "chat", "high-priority"]
)
```

### 3. Metadata Best Practices

Include actionable metadata:
```python
metadata = {
    "user_id": "user123",           # Track per-user
    "session_id": "sess_456",       # Group conversations
    "request_source": "web",        # API vs web vs mobile
    "model_version": "v1.2.0",      # Track model changes
    "deployment": "us-west-2",      # Geographic tracking
    "cost_center": "sales",         # Business unit
}
```

### 4. Sampling for High Volume

For very high-traffic applications:

```python
import random

# Sample 10% of requests
should_trace = random.random() < 0.1

if should_trace:
    config = RunnableConfig(tags=["sampled"])
else:
    config = RunnableConfig(tags=["not-traced"])
```

### 5. Cost Monitoring

Track costs in LangSmith:
1. Go to project
2. Click "Analytics"
3. View "Cost Over Time"
4. Set budget alerts

**Optimize costs**:
- Use cheaper models for simple tasks
- Implement caching
- Set max token limits
- Monitor high-cost users

### 6. Privacy and Compliance

**Redact sensitive data**:
```python
def redact_pii(text):
    # Redact emails, phone numbers, etc.
    import re
    text = re.sub(r'\b[\w.-]+@[\w.-]+\.\w+\b', '[EMAIL]', text)
    text = re.sub(r'\b\d{3}-\d{3}-\d{4}\b', '[PHONE]', text)
    return text

# Before logging
inputs = {"messages": [{"content": redact_pii(user_input)}]}
```

**GDPR compliance**:
- Delete user traces on request
- Set data retention policies
- Use metadata for user identification

### 7. Performance Monitoring

Set up monitoring for:
- **Latency (P95)**: Alert if >5 seconds
- **Error rate**: Alert if >5%
- **Token usage**: Alert on anomalies
- **Cost per user**: Track trends

---

## Advanced Features

### Prompt Hub

Save and version prompts:

```python
from langchain import hub

# Pull prompt from hub
prompt = hub.pull("my-org/agent-prompt:v3")

# Use in agent
model_with_prompt = model.bind(prompt=prompt)
```

### Online Evaluation

Run evaluations on production traces:

```python
from langsmith.evaluation import evaluate_existing

# Evaluate last 100 production traces
evaluate_existing(
    "mcp-server-langgraph",
    data="last-100-traces",
    evaluators=[accuracy_evaluator, toxicity_evaluator]
)
```

### A/B Testing

Compare model versions:

```python
# Version A
config_a = RunnableConfig(tags=["model:gpt-4", "version:a"])

# Version B
config_b = RunnableConfig(tags=["model:claude-3.5", "version:b"])

# Analyze in LangSmith: filter by tag, compare metrics
```

---

## Troubleshooting

### Traces Not Appearing

**Check**:
1. API key is set: `echo $LANGSMITH_API_KEY`
2. Tracing is enabled: `echo $LANGSMITH_TRACING`
3. Project name is correct: `echo $LANGSMITH_PROJECT`
4. Network connectivity to api.smith.langchain.com

**Test connection**:
```python
from langsmith import Client

client = Client()
print(client.list_projects())  # Should list your projects
```

### Slow Tracing Performance

LangSmith tracing is async and shouldn't slow down requests. If you experience slowness:

1. **Check network latency** to api.smith.langchain.com
2. **Reduce trace size**: Avoid logging huge payloads
3. **Use sampling**: Don't trace every request

### Missing LLM Calls

If LLM calls aren't traced:

```python
# Ensure using LangChain models
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

# These are automatically traced
model = ChatAnthropic(model="claude-3-5-sonnet-20241022")
```

---

## Resources

- **LangSmith Docs**: https://docs.langchain.com/langsmith
- **LangSmith Cookbook**: https://github.com/langchain-ai/langsmith-cookbook
- **API Reference**: https://docs.smith.langchain.com/api-reference
- **Community**: https://github.com/langchain-ai/langsmith-sdk/discussions

**Need help?**
- LangSmith support: https://support.langchain.com/
- Project issues: https://github.com/vishnu2kmohan/mcp-server-langgraph/issues

---

**Last Updated**: 2025-10-10
