# Google Gemini 2.5 Setup Guide

Quick setup guide for using Google Gemini 2.5 models (default configuration).

## Why Gemini 2.5?

The MCP Server with LangGraph defaults to **Gemini 2.5 Flash** for several reasons:

✅ **Latest Technology** - Google's newest model family (2025)
✅ **Fastest Performance** - Sub-second response times
✅ **Cost Efficient** - More affordable than GPT-4 or Claude
✅ **Multimodal** - Native support for text, images, video, audio
✅ **Large Context** - 1M+ token context window
✅ **High Quality** - Competitive with GPT-4o and Claude 3.5 Sonnet

## Quick Start

### 1. Get API Key

1. Visit: https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click **"Get API key"**
4. Create a new API key or use existing one
5. Copy the key (starts with `AI...`)

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env  # or vim .env, or use your favorite editor
```

Update these values:

```bash
# LLM Provider (already set to google by default)
LLM_PROVIDER=google

# Google API Key (paste your key here)
GOOGLE_API_KEY=AIza...your-key-here

# Model (already set to latest Gemini 2.5 Flash)
MODEL_NAME=gemini-2.5-flash-002
```

### 3. Test Connection

```bash
# Test Gemini connection
python examples/test_llm.py

# Expected output:
# Provider: google
# Model: gemini-2.5-flash-002
# ✓ LLM initialized successfully
# ✓ Response: 4
```

### 4. Run MCP Server

```bash
# Run StreamableHTTP server
python -m mcp_server_langgraph.mcp.server_streamable

# Or run stdio server
python -m mcp_server_langgraph.mcp.server_stdio
```

## Gemini 2.5 Models

### gemini-2.5-flash-002 (Default - Recommended)

- **Speed**: Fastest Gemini model (sub-second responses)
- **Cost**: Most cost-effective
- **Context**: 1M+ tokens
- **Use Cases**: Production applications, chatbots, real-time apps
- **Best For**: 95% of use cases

```bash
MODEL_NAME=gemini-2.5-flash-002
MODEL_MAX_TOKENS=8192
```

### gemini-2.5-pro (Most Capable)

- **Speed**: Slower but more capable
- **Cost**: Higher cost, premium quality
- **Context**: 1M+ tokens
- **Use Cases**: Complex reasoning, research, analysis
- **Best For**: High-complexity tasks requiring deep reasoning

```bash
MODEL_NAME=gemini-2.5-pro
MODEL_MAX_TOKENS=8192
```

## Model Comparison

| Model | Speed | Cost | Quality | Context | Best For |
|-------|-------|------|---------|---------|----------|
| **Gemini 2.5 Flash** | ⚡⚡⚡ | 💰 | ⭐⭐⭐⭐ | 1M+ | Production (Default) |
| Gemini 2.5 Pro | ⚡⚡ | 💰💰💰 | ⭐⭐⭐⭐⭐ | 1M+ | Complex reasoning |
| Claude 3.5 Sonnet | ⚡⚡ | 💰💰 | ⭐⭐⭐⭐⭐ | 200K | Coding, analysis |
| GPT-4o | ⚡⚡ | 💰💰 | ⭐⭐⭐⭐ | 128K | General purpose |

## Pricing (Approximate)

**Gemini 2.5 Flash:**
- Input: $0.075 per 1M tokens
- Output: $0.30 per 1M tokens
- **~4x cheaper than GPT-4o**
- **~3x cheaper than Claude 3.5**

**Gemini 2.5 Pro:**
- Input: $1.25 per 1M tokens
- Output: $5.00 per 1M tokens
- Comparable to GPT-4o pricing

## Fallback Configuration

The default configuration includes automatic fallback:

```bash
# Primary: Gemini 2.5 Flash
MODEL_NAME=gemini-2.5-flash-002

# Fallbacks (in order):
ENABLE_FALLBACK=true
FALLBACK_MODELS=["gemini-2.5-pro","claude-3-5-sonnet-20241022","gpt-4o"]
```

**Fallback triggers:**
- Rate limits
- API errors
- Timeouts
- Model unavailability

## Advanced Configuration

### Increase Context Window

```bash
# Use full 1M context (if needed)
MODEL_MAX_TOKENS=1000000

# Note: Very large context increases latency and cost
```

### Adjust Temperature

```bash
# More creative (0.8-1.0)
MODEL_TEMPERATURE=0.9

# More deterministic (0.0-0.3)
MODEL_TEMPERATURE=0.2

# Default balanced (0.7)
MODEL_TEMPERATURE=0.7
```

### Timeout Settings

```bash
# Default timeout (60 seconds)
MODEL_TIMEOUT=60

# Longer timeout for complex queries
MODEL_TIMEOUT=120
```

## Multimodal Capabilities

Gemini 2.5 natively supports:

- ✅ **Text** - Natural language
- ✅ **Images** - Image understanding and generation
- ✅ **Video** - Video analysis
- ✅ **Audio** - Speech and audio processing
- ✅ **Code** - Programming languages

### Example: Image Analysis

```python
from langchain_core.messages import HumanMessage

messages = [
    HumanMessage(content=[
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": "https://example.com/image.jpg"}
    ])
]

response = await llm.ainvoke(messages)
```

## Rate Limits

**Free Tier:**
- 15 requests per minute
- 1 million tokens per day
- 1,500 requests per day

**Paid Tier:**
- 360 requests per minute
- 4 million tokens per minute
- No daily limits

**Tip:** Enable fallback models to handle rate limits gracefully.

## Troubleshooting

### API Key Not Working

```bash
# Verify key is set
echo $GOOGLE_API_KEY

# Test directly
curl -X POST https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash-002:generateContent?key=$GOOGLE_API_KEY \
  -H 'Content-Type: application/json' \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

### Rate Limit Errors

```bash
# Enable fallback to handle rate limits
ENABLE_FALLBACK=true

# Or upgrade to paid tier
# Visit: https://console.cloud.google.com/billing
```

### Model Not Found

```bash
# Verify model name is correct
MODEL_NAME=gemini-2.5-flash-002  # ✅ Correct

# Common mistakes:
# MODEL_NAME=gemini-2.5-flash     # ❌ Missing version
# MODEL_NAME=gemini-flash-2.5     # ❌ Wrong order
```

### Slow Responses

```bash
# Use Flash model (default)
MODEL_NAME=gemini-2.5-flash-002

# Reduce max tokens
MODEL_MAX_TOKENS=4096

# Increase timeout
MODEL_TIMEOUT=90
```

## Monitoring

Gemini usage is automatically tracked:

```bash
# View traces in Jaeger
open http://localhost:16686

# View metrics in Prometheus
open http://localhost:9090

# Search for:
# - llm.invoke (successful calls)
# - llm.failed (failed calls)
# - llm.fallback (fallback usage)
```

## Switching to Other Providers

### Switch to Anthropic

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
export MODEL_NAME=claude-3-5-sonnet-20241022
```

### Switch to OpenAI

```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export MODEL_NAME=gpt-4o
```

### Switch to Local (Ollama)

```bash
# Install Ollama first
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull llama3.1:8b

# Configure
export LLM_PROVIDER=ollama
export MODEL_NAME=ollama/llama3.1:8b
```

## Resources

- **API Documentation**: https://ai.google.dev/docs
- **Get API Key**: https://aistudio.google.com/apikey
- **Pricing**: https://ai.google.dev/pricing
- **Model Info**: https://ai.google.dev/models/gemini
- **AI Studio**: https://aistudio.google.com

## Support

- **Google AI Forum**: https://discuss.ai.google.dev
- **GitHub Issues**: Report issues with the agent
- **Documentation**: See integrations/litellm.md for all providers

---

**Default Configuration Summary:**
- **Provider**: Google
- **Model**: gemini-2.5-flash-002
- **Fallback**: gemini-2.5-pro, claude-3-5-sonnet, gpt-4o
- **Cost**: ~75% cheaper than alternatives
- **Speed**: Fastest available

**You're ready to use Gemini 2.5!** 🚀
