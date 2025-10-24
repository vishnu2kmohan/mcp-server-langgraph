# LiteLLM Integration Guide

Complete guide for using multiple LLM providers with the MCP Server with LangGraph.

## Table of Contents

- [Overview](#overview)
- [Supported Providers](#supported-providers)
- [Configuration](#configuration)
- [Provider Setup](#provider-setup)
- [Model Examples](#model-examples)
- [Fallback Strategy](#fallback-strategy)
- [Best Practices](#best-practices)

## Overview

The MCP Server with LangGraph uses [LiteLLM](https://docs.litellm.ai/) to support **100+ LLM providers** with a unified interface. This allows you to:

- ✅ Switch between providers without code changes
- ✅ Use open-source models (Llama, Qwen, Mistral, etc.)
- ✅ Implement automatic fallback between models
- ✅ Optimize costs by provider/model selection
- ✅ Test locally with Ollama before deploying

## Supported Providers

### Cloud Providers

| Provider | Models | Configuration Required |
|----------|--------|------------------------|
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus/Haiku | `ANTHROPIC_API_KEY` |
| **OpenAI** | GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo | `OPENAI_API_KEY` |
| **Google** | Gemini 1.5 Pro/Flash, Gemini 2.0 | `GOOGLE_API_KEY` |
| **Azure OpenAI** | GPT-4, GPT-3.5 | `AZURE_API_KEY`, `AZURE_API_BASE` |
| **AWS Bedrock** | Claude, Llama, Titan | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |

### Open-Source (Ollama)

| Model Family | Models | Local Setup |
|--------------|--------|-------------|
| **Llama** | Llama 3.1, Llama 2 (7B-70B) | Install Ollama |
| **Qwen** | Qwen 2.5 (0.5B-72B) | Install Ollama |
| **Mistral** | Mistral 7B, Mixtral 8x7B | Install Ollama |
| **DeepSeek** | DeepSeek Coder, DeepSeek LLM | Install Ollama |
| **Others** | Phi-3, Gemma, Yi, etc. | Install Ollama |

## Configuration

### Environment Variables

Create or update `.env`:

```bash
# Choose your primary provider (default: google)
LLM_PROVIDER=google  # google, anthropic, openai, azure, bedrock, ollama

# Model name (provider-specific format)
# Default: Gemini 2.5 Flash (latest, fastest)
MODEL_NAME=gemini-2.5-flash-002

# Model parameters
MODEL_TEMPERATURE=0.7
MODEL_MAX_TOKENS=8192
MODEL_TIMEOUT=60

# Fallback configuration
ENABLE_FALLBACK=true
FALLBACK_MODELS=["gemini-2.5-pro", "claude-3-5-sonnet-20241022", "gpt-4o"]
```

### API Keys

```bash
# Google Gemini (Primary - Get from: https://aistudio.google.com/apikey)
GOOGLE_API_KEY=...

# Anthropic (Fallback)
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI (Fallback)
OPENAI_API_KEY=sk-...

# Azure OpenAI
AZURE_API_KEY=...
AZURE_API_BASE=https://your-resource.openai.azure.com
AZURE_API_VERSION=2024-02-15-preview
AZURE_DEPLOYMENT_NAME=gpt-4

# AWS Bedrock
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
```

## Provider Setup

### 2. Anthropic (Claude)

```bash
# Get API key from https://console.anthropic.com/

# Configure
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
export MODEL_NAME=claude-3-5-sonnet-20241022

# Available models:
# - claude-3-5-sonnet-20241022 (excellent all-around)
# - claude-3-opus-20240229 (most capable)
# - claude-3-haiku-20240307 (fastest)
```

### 3. OpenAI

```bash
# Get API key from https://platform.openai.com/

# Configure
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export MODEL_NAME=gpt-4o

# Available models:
# - gpt-4o (multimodal)
# - gpt-4-turbo
# - gpt-3.5-turbo
```

### 1. Google Gemini (Default - Recommended)

```bash
# Get API key from https://aistudio.google.com/apikey

# Configure
export LLM_PROVIDER=google
export GOOGLE_API_KEY=...
export MODEL_NAME=gemini-2.5-flash

# Production-grade Gemini models (officially supported):
# - gemini-2.5-flash (Fast, efficient, production-ready - RECOMMENDED)
# - gemini-2.5-pro (Most capable for complex reasoning, production-ready)
#
# Note: Only these two models are production-grade. Other Gemini variants
# may be experimental or preview releases not suitable for production use.
```

### 4. Azure OpenAI

```bash
# Deploy model in Azure Portal

# Configure
export LLM_PROVIDER=azure
export AZURE_API_KEY=...
export AZURE_API_BASE=https://your-resource.openai.azure.com
export AZURE_DEPLOYMENT_NAME=gpt-4
export MODEL_NAME=azure/gpt-4

# Model format: azure/<deployment-name>
```

### 5. AWS Bedrock

```bash
# Configure AWS credentials

# Configure
export LLM_PROVIDER=bedrock
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1
export MODEL_NAME=anthropic.claude-3-sonnet-20240229-v1:0

# Available models:
# - anthropic.claude-3-5-sonnet-20241022-v2:0
# - anthropic.claude-3-opus-20240229-v1:0
# - meta.llama3-1-70b-instruct-v1:0
# - amazon.titan-text-premier-v1:0
```

### 6. Ollama (Local/Open-Source)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull llama3.1:8b
ollama pull qwen2.5:7b
ollama pull mistral:7b
ollama pull deepseek-coder:6.7b

# Configure
export LLM_PROVIDER=ollama
export OLLAMA_BASE_URL=http://localhost:11434
export MODEL_NAME=ollama/llama3.1:8b

# Model format: ollama/<model-name>:<tag>
```

## Model Examples

### Anthropic Models

```bash
# Claude 3.5 Sonnet (Best overall, 200K context)
MODEL_NAME=claude-3-5-sonnet-20241022

# Claude 3 Opus (Most capable, 200K context)
MODEL_NAME=claude-3-opus-20240229

# Claude 3 Haiku (Fastest, 200K context)
MODEL_NAME=claude-3-haiku-20240307
```

### OpenAI Models

```bash
# GPT-4o (Multimodal, 128K context)
MODEL_NAME=gpt-4o

# GPT-4 Turbo (High intelligence, 128K context)
MODEL_NAME=gpt-4-turbo

# GPT-3.5 Turbo (Fast and cheap, 16K context)
MODEL_NAME=gpt-3.5-turbo
```

### Google Gemini Models (Default/Recommended)

```bash
# Gemini 2.5 Flash (Production-grade: fast, efficient - RECOMMENDED)
MODEL_NAME=gemini-2.5-flash

# Gemini 2.5 Pro (Production-grade: most capable for complex tasks)
MODEL_NAME=gemini-2.5-pro
```

### Ollama (Open-Source)

```bash
# Llama 3.1 (Meta's latest)
MODEL_NAME=ollama/llama3.1:8b          # 8B parameters
MODEL_NAME=ollama/llama3.1:70b         # 70B parameters

# Qwen 2.5 (Alibaba, multilingual)
MODEL_NAME=ollama/qwen2.5:7b           # 7B parameters
MODEL_NAME=ollama/qwen2.5:32b          # 32B parameters

# Mistral (Open, efficient)
MODEL_NAME=ollama/mistral:7b           # 7B base
MODEL_NAME=ollama/mixtral:8x7b         # 8x7B MoE

# DeepSeek Coder (Code specialist)
MODEL_NAME=ollama/deepseek-coder:6.7b  # Code generation

# Phi-3 (Microsoft, small but capable)
MODEL_NAME=ollama/phi3:mini            # 3.8B parameters
MODEL_NAME=ollama/phi3:medium          # 14B parameters
```

## Fallback Strategy

The agent automatically falls back to alternative models if the primary fails:

```bash
# Configure fallback models
ENABLE_FALLBACK=true
FALLBACK_MODELS=["gpt-4o", "gemini-1.5-pro", "claude-3-5-sonnet-20241022"]
```

### Fallback Order Example

```python
# Primary: Claude 3.5 Sonnet
LLM_PROVIDER=anthropic
MODEL_NAME=claude-3-5-sonnet-20241022

# Fallbacks (in order):
FALLBACK_MODELS=[
    "gpt-4o",                              # Try OpenAI GPT-4o
    "gemini-1.5-pro",                      # Try Google Gemini
    "ollama/llama3.1:8b"                   # Try local Llama
]
```

### Fallback Behavior

1. **Primary model fails** → Try first fallback
2. **First fallback fails** → Try second fallback
3. **All fallbacks fail** → Return error

Fallback triggers on:
- API rate limits
- Model unavailability
- Network errors
- Timeout errors

## Best Practices

### 1. Cost Optimization

```bash
# Development: Use cheaper/local models
LLM_PROVIDER=ollama
MODEL_NAME=ollama/llama3.1:8b

# Staging: Use mid-tier models
LLM_PROVIDER=openai
MODEL_NAME=gpt-3.5-turbo

# Production: Use best models with fallback
LLM_PROVIDER=anthropic
MODEL_NAME=claude-3-5-sonnet-20241022
FALLBACK_MODELS=["gpt-4o", "gemini-1.5-pro"]
```

### 2. Latency Optimization

**Fastest models:**
```bash
# Cloud (sub-second)
- claude-3-haiku-20240307
- gpt-3.5-turbo
- gemini-1.5-flash

# Local (depends on hardware)
- ollama/phi3:mini
- ollama/llama3.1:8b
- ollama/mistral:7b
```

### 3. Context Length

**Large context needs:**
```bash
# 1M+ tokens
- gemini-1.5-pro (1M)
- gemini-1.5-flash (1M)

# 200K tokens
- claude-3-5-sonnet (200K)
- claude-3-opus (200K)

# 128K tokens
- gpt-4o (128K)
- gpt-4-turbo (128K)
```

### 4. Multilingual Support

**Best for non-English:**
```bash
- qwen2.5:7b (70+ languages)
- gemini-1.5-pro (100+ languages)
- claude-3-5-sonnet (excellent multilingual)
```

### 5. Code Generation

**Best for coding:**
```bash
- deepseek-coder:6.7b (specialized)
- claude-3-5-sonnet (excellent)
- gpt-4o (very good)
```

## Testing Different Providers

### Quick Test Script

```bash
# Test Anthropic
export LLM_PROVIDER=anthropic MODEL_NAME=claude-3-5-sonnet-20241022
python examples/test_llm.py

# Test OpenAI
export LLM_PROVIDER=openai MODEL_NAME=gpt-4o
python examples/test_llm.py

# Test Google
export LLM_PROVIDER=google MODEL_NAME=gemini-1.5-pro
python examples/test_llm.py

# Test Ollama
export LLM_PROVIDER=ollama MODEL_NAME=ollama/llama3.1:8b
python examples/test_llm.py
```

### Test with MCP Server

```bash
# Update .env with desired provider
vim .env

# Run MCP server
python -m mcp_server_langgraph.mcp.server_streamable

# Test with example client
python examples/streamable_http_client.py
```

## Monitoring

LiteLLM usage is automatically tracked with OpenTelemetry:

```python
# Metrics collected:
- llm.invoke (successful calls by model)
- llm.fallback (fallback usage by model)
- llm.failed (failed calls by model)

# Traces include:
- Provider name
- Model name
- Token usage
- Latency
- Error details
```

View in Jaeger: http://localhost:16686

## Troubleshooting

### API Key Not Working

```bash
# Verify key is set
echo $ANTHROPIC_API_KEY

# Test key directly
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

### Ollama Connection Failed

```bash
# Check Ollama is running
ollama serve

# Test connection
curl http://localhost:11434/api/tags

# Verify model is pulled
ollama list
```

### Model Not Found

```bash
# LiteLLM uses specific formats:
✅ claude-3-5-sonnet-20241022
❌ claude-3.5-sonnet

✅ ollama/llama3.1:8b
❌ llama3.1

✅ azure/gpt-4
❌ gpt-4 (when using Azure)
```

## Resources

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Supported Models](https://docs.litellm.ai/docs/providers)
- [Ollama Models](https://ollama.com/library)
- [Provider Pricing](https://docs.litellm.ai/docs/completion/cost_tracking)

## Support

For LiteLLM issues:
- [LiteLLM GitHub](https://github.com/BerriAI/litellm)
- [Discord Community](https://discord.gg/wuPM9dRgDw)

---

**Last Updated**: 2025-01-10
