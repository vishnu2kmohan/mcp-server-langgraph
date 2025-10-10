# LangGraph Platform Deployment Guide

Complete guide for deploying the MCP Server with LangGraph to LangGraph Platform (LangChain's managed hosting service).

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Managing Deployments](#managing-deployments)
- [Monitoring](#monitoring)
- [Environment Management](#environment-management)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

LangGraph Platform is LangChain's fully managed hosting solution for LangGraph applications. It provides:

- **Serverless Deployment**: No infrastructure management required
- **Auto-scaling**: Automatic scaling based on demand
- **Built-in Observability**: Integrated with LangSmith tracing
- **Versioning**: Automatic versioning and rollback capabilities
- **Secrets Management**: Secure environment variable handling
- **CLI-based Workflow**: Simple deployment via command line

###Architecture

```
┌──────────────┐
│ LangGraph    │
│ CLI          │
└──────┬───────┘
       │ deploy
       ▼
┌────────────────────────────────────┐
│ LangGraph Platform                 │
│ ┌────────────────────────────────┐│
│ │ Your Agent (Containerized)     ││
│ │ - Auto-scaling                 ││
│ │ - Load balancing               ││
│ │ - Health checks                ││
│ └────────────────────────────────┘│
│ ┌────────────────────────────────┐│
│ │ LangSmith Integration          ││
│ │ - Automatic tracing            ││
│ │ - Request logging              ││
│ │ - Performance metrics          ││
│ └────────────────────────────────┘│
└────────────────────────────────────┘
```

### Why LangGraph Platform?

✅ **Pros**:
- Zero infrastructure setup
- Integrated LangSmith observability
- Automatic HTTPS and certificates
- Built-in versioning and rollbacks
- Pay-per-use pricing
- Global CDN and edge deployment

⚠️ **Considerations**:
- Requires LangChain account
- Platform-specific configuration
- Cold start latency for infrequent requests

---

## Prerequisites

### Required Tools

1. **Python 3.10+**
   ```bash
   python --version  # Should be 3.10 or higher
   ```

2. **LangGraph CLI**
   ```bash
   pip install langgraph-cli
   ```

3. **LangSmith CLI** (optional but recommended)
   ```bash
   pip install langsmith
   ```

### LangChain Account Setup

1. **Create LangChain account**:
   - Visit: https://smith.langchain.com/
   - Sign up for free account

2. **Get API Keys**:
   - **LangSmith API Key**: https://smith.langchain.com/settings
   - **LangGraph API Key**: https://smith.langchain.com/settings (same key)

3. **Login via CLI**:
   ```bash
   langgraph login
   # Enter your API key when prompted
   ```

### LLM API Keys

You'll need at least one LLM provider API key:
- **Anthropic** (recommended): https://console.anthropic.com/
- **OpenAI**: https://platform.openai.com/api-keys
- **Google AI** (Gemini): https://aistudio.google.com/apikey

---

## Quick Start

### One-Command Deployment

```bash
# 1. Navigate to project directory
cd mcp_server_langgraph

# 2. Login to LangChain (first time only)
langgraph login

# 3. Deploy to platform
langgraph deploy
```

That's it! Your agent is now live on LangGraph Platform.

### Verify Deployment

```bash
# Check deployment status
langgraph deployment get mcp-server-langgraph

# Get deployment URL
langgraph deployment get mcp-server-langgraph --json | grep url

# Test the deployment
langgraph deployment invoke mcp-server-langgraph \
  --input '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

---

## Configuration

### langgraph.json

The `langgraph.json` file configures your deployment:

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./langgraph/agent.py:graph"
  },
  "env": {
    "ANTHROPIC_API_KEY": "",
    "OPENAI_API_KEY": "",
    "LANGSMITH_TRACING": "true",
    "LANGSMITH_PROJECT": "mcp-server-langgraph"
  },
  "python_version": "3.11"
}
```

**Key Fields**:
- **`dependencies`**: List of dependency sources (`.` means current directory)
- **`graphs`**: Map of graph names to their module paths
- **`env`**: Environment variables (secrets should use LangSmith secrets)
- **`python_version`**: Python version to use (3.10, 3.11, or 3.12)

### Environment Variables

**Required**:
- `LANGSMITH_API_KEY`: LangSmith API key (set via secrets)
- At least one LLM API key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.)

**Optional**:
- `LANGSMITH_PROJECT`: Project name in LangSmith (default: from langgraph.json)
- `LANGSMITH_TRACING`: Enable tracing (default: true on platform)
- `JWT_SECRET_KEY`: For authentication (if using auth middleware)
- `OPENFGA_*`: OpenFGA configuration (if using authorization)

### Setting Secrets

Use LangSmith to securely store API keys:

```bash
# Set LLM API keys
langsmith secret set ANTHROPIC_API_KEY "your-key-here"
langsmith secret set OPENAI_API_KEY "your-key-here"

# Set authentication secrets
langsmith secret set JWT_SECRET_KEY "your-jwt-secret"

# Set authorization secrets (if using OpenFGA)
langsmith secret set OPENFGA_STORE_ID "your-store-id"
langsmith secret set OPENFGA_MODEL_ID "your-model-id"
```

**View secrets**:
```bash
langsmith secret list
```

---

## Deployment

### Initial Deployment

```bash
# Deploy with automatic name
langgraph deploy

# Deploy with specific name
langgraph deploy my-agent-prod

# Deploy with tag (environment)
langgraph deploy --tag production

# Deploy specific graph
langgraph deploy --graph agent
```

### Local Testing Before Deployment

```bash
# Start local development server
langgraph dev

# Test locally (in another terminal)
langgraph deployment invoke --local \
  --input '{"messages": [{"role": "user", "content": "Test"}]}'

# Stop with Ctrl+C when done
```

### Deployment with Scripts

```bash
# Using provided deployment script
cd scripts
./deploy_langgraph_platform.sh

# Skip local testing
./deploy_langgraph_platform.sh --skip-test

# Deploy to specific environment
ENVIRONMENT=production ./deploy_langgraph_platform.sh
```

### Update Deployment

```bash
# Redeploy (creates new revision)
langgraph deploy my-agent-prod

# Deploy specific revision
langgraph deploy my-agent-prod --revision 5
```

---

## Managing Deployments

### List Deployments

```bash
# List all your deployments
langgraph deployment list

# Get deployment details
langgraph deployment get my-agent-prod

# Get deployment in JSON format
langgraph deployment get my-agent-prod --json
```

### Invoke Deployed Graph

```bash
# Simple invocation
langgraph deployment invoke my-agent-prod \
  --input '{"messages": [{"role": "user", "content": "Hello!"}]}'

# With configuration
langgraph deployment invoke my-agent-prod \
  --input '{"messages": [{"role": "user", "content": "Analyze this"}]}' \
  --config '{"configurable": {"user_id": "user123"}}'

# Stream responses
langgraph deployment invoke my-agent-prod \
  --input '{"messages": [{"role": "user", "content": "Tell me a story"}]}' \
  --stream
```

### View Logs

```bash
# Stream real-time logs
langgraph deployment logs my-agent-prod --follow

# View recent logs
langgraph deployment logs my-agent-prod --tail 100

# Filter by log level
langgraph deployment logs my-agent-prod --level error
```

### Rollback Deployment

```bash
# List revisions
langgraph deployment revisions my-agent-prod

# Rollback to previous revision
langgraph deployment rollback my-agent-prod --revision 4
```

### Delete Deployment

```bash
# Delete deployment
langgraph deployment delete my-agent-prod

# Force delete (skip confirmation)
langgraph deployment delete my-agent-prod --force
```

---

## Monitoring

### LangSmith Integration

All deployments automatically integrate with LangSmith:

1. **View Traces**:
   - Go to: https://smith.langchain.com/
   - Select your project
   - View traces for all invocations

2. **Monitor Performance**:
   - Request latency
   - Token usage
   - Error rates
   - Cost tracking

3. **Debug Issues**:
   - View full LLM interactions
   - Inspect intermediate steps
   - Analyze failures

### Metrics Dashboard

Access metrics via LangSmith:
- **Request Count**: Total invocations
- **Latency (P50, P95, P99)**: Response time percentiles
- **Success Rate**: Percentage of successful requests
- **Token Usage**: Total tokens consumed
- **Cost**: Estimated costs per provider

### Alerts

Set up alerts in LangSmith:
```bash
# Via LangSmith UI
1. Go to Project Settings
2. Click "Alerts"
3. Configure alert rules:
   - High error rate (>5%)
   - High latency (P95 >5s)
   - Budget exceeded
```

---

## Environment Management

### Multiple Environments

Create separate deployments for each environment:

```bash
# Staging
langgraph deploy my-agent-staging --tag staging

# Production
langgraph deploy my-agent-prod --tag production

# Development
langgraph deploy my-agent-dev --tag development
```

### Environment-Specific Configuration

Create environment-specific `.env` files:

**.env.staging**:
```bash
ENVIRONMENT=staging
LANGSMITH_PROJECT=my-agent-staging
MODEL_NAME=claude-3-5-sonnet-20241022
LOG_LEVEL=DEBUG
```

**.env.production**:
```bash
ENVIRONMENT=production
LANGSMITH_PROJECT=my-agent-production
MODEL_NAME=claude-3-5-sonnet-20241022
LOG_LEVEL=INFO
```

### Load Environment Before Deployment

```bash
# Load staging environment
export $(cat .env.staging | grep -v '^#' | xargs)
langgraph deploy my-agent-staging

# Load production environment
export $(cat .env.production | grep -v '^#' | xargs)
langgraph deploy my-agent-prod
```

---

## Troubleshooting

### Common Issues

#### 1. Deployment Fails with "Graph not found"

**Symptoms**: `Error: Could not find graph 'agent'`

**Solution**:
- Verify `langgraph.json` has correct graph path
- Ensure graph file exists at specified path
- Check that graph variable is named correctly

```json
{
  "graphs": {
    "agent": "./langgraph/agent.py:graph"  // Correct path
  }
}
```

#### 2. Authentication Errors

**Symptoms**: `401 Unauthorized`

**Solution**:
```bash
# Re-login to LangChain
langgraph logout
langgraph login

# Verify authentication
langgraph whoami
```

#### 3. Missing Dependencies

**Symptoms**: `ModuleNotFoundError` in deployment logs

**Solution**:
- Add missing dependencies to `langgraph/requirements.txt`
- Or add to main `requirements.txt` if using `dependencies: ["."]`
- Redeploy after updating requirements

#### 4. Environment Variable Not Set

**Symptoms**: Agent fails with missing API key

**Solution**:
```bash
# Set secret via LangSmith
langsmith secret set ANTHROPIC_API_KEY "your-key"

# Or update langgraph.json env section
# Then redeploy
langgraph deploy
```

#### 5. Cold Start Latency

**Symptoms**: First request after idle period is slow

**Solutions**:
- Use keep-warm requests (scheduled invocations)
- Optimize imports (lazy load heavy dependencies)
- Reduce Docker image size
- Consider upgrading to dedicated capacity (enterprise)

### Debug Commands

```bash
# Check deployment health
langgraph deployment get my-agent-prod --json | grep status

# View environment variables
langgraph deployment get my-agent-prod --json | grep -A 20 env

# Test with debug output
langgraph deployment invoke my-agent-prod \
  --input '{"messages": [{"role": "user", "content": "test"}]}' \
  --debug

# Export deployment configuration
langgraph deployment get my-agent-prod --json > deployment-config.json
```

---

## Best Practices

### 1. Version Control

```bash
# Tag deployments with versions
langgraph deploy my-agent-prod --tag v1.2.0

# Include git commit in metadata
langgraph deploy --tag "$(git rev-parse --short HEAD)"
```

### 2. Secrets Management

✅ **Do**:
- Store all API keys in LangSmith secrets
- Use strong JWT secrets
- Rotate secrets regularly

❌ **Don't**:
- Hardcode secrets in code
- Commit secrets to version control
- Share secrets in plaintext

### 3. Testing

```bash
# Always test locally first
langgraph dev

# Run integration tests before deployment
pytest tests/integration/

# Deploy to staging before production
langgraph deploy my-agent-staging
# Test staging thoroughly
langgraph deploy my-agent-prod
```

### 4. Monitoring

- Enable LangSmith tracing (automatic on platform)
- Set up alerts for errors and latency
- Review traces regularly for optimization opportunities
- Monitor costs and token usage

### 5. Performance Optimization

- **Lazy load heavy dependencies**:
  ```python
  # Instead of importing at module level
  def use_heavy_lib():
      import heavy_library  # Import only when needed
      return heavy_library.function()
  ```

- **Cache frequently used data**:
  ```python
  from functools import lru_cache

  @lru_cache(maxsize=100)
  def get_cached_data(key):
      return expensive_operation(key)
  ```

- **Use streaming for long responses**:
  ```python
  # Enable streaming in your graph
  graph.stream(inputs, config)
  ```

### 6. Cost Optimization

- Choose appropriate model sizes
- Implement prompt caching where possible
- Set reasonable token limits
- Use cheaper models for routing/classification
- Monitor and set budget alerts

---

## CI/CD Integration

### GitHub Actions Example

See `.github/workflows/deploy-langgraph-platform.yml`:

```yaml
name: Deploy to LangGraph Platform

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install langgraph-cli langsmith

      - name: Deploy to LangGraph Platform
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
        run: |
          langgraph deploy my-agent-prod --tag production
```

### GitLab CI Example

```yaml
deploy-langgraph:
  stage: deploy
  image: python:3.11
  script:
    - pip install langgraph-cli
    - langgraph deploy my-agent-prod --tag production
  only:
    - main
  environment:
    name: production
```

---

## Next Steps

✅ **You've successfully deployed to LangGraph Platform!**

**Recommended next steps**:

1. **Set up monitoring**: Configure LangSmith alerts
2. **Test your deployment**: Run comprehensive tests
3. **Configure CI/CD**: Automate deployments
4. **Optimize performance**: Review traces and optimize
5. **Set up staging**: Create staging environment
6. **Documentation**: Document your deployment process

**Resources**:
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Platform Docs](https://docs.langchain.com/langgraph-platform)
- [LangSmith Documentation](https://docs.langchain.com/langsmith)
- [LangGraph CLI Reference](https://github.com/langchain-ai/langgraph-cli)

**Need help?**
- LangChain support: https://support.langchain.com/
- Project issues: https://github.com/vishnu2kmohan/mcp_server_langgraph/issues

---

**Last Updated**: 2025-10-10
