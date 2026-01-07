# Embedding Migration Guide: Sentence Transformers → Google Gemini Embeddings

## Overview

This project has been migrated from self-hosted `sentence-transformers` embeddings to API-based **Google Gemini embeddings**. This change eliminates the need to host and serve embedding models locally while providing better quality embeddings.

## What Changed

### 1. **Dependencies**
- ✅ Added: `langchain-google-genai>=0.2.0` (now in core dependencies)
- 📦 Moved: `sentence-transformers>=2.2.0` to optional dependencies (backwards compatibility)

### 2. **Default Embedding Provider**
- **Before**: `all-MiniLM-L6-v2` (384 dimensions, self-hosted)
- **After**: `models/text-embedding-004` (768 dimensions, Google API)

### 3. **Configuration Changes**

New environment variables in `.env`:

```bash
# Embedding Provider (default: google)
EMBEDDING_PROVIDER=google

# Embedding Model Name
EMBEDDING_MODEL_NAME=models/text-embedding-004

# Embedding Dimensions (must match model)
EMBEDDING_DIMENSIONS=768

# Google Task Type Optimization
EMBEDDING_TASK_TYPE=RETRIEVAL_DOCUMENT
```

### 4. **Code Changes**

**File**: `src/mcp_server_langgraph/core/dynamic_context_loader.py`
- New `_create_embeddings()` factory function supporting multiple providers
- Updated to use LangChain `Embeddings` interface
- Supports 5 embedding providers (see below)

**File**: `src/mcp_server_langgraph/core/config.py`
- Added `embedding_provider`, `embedding_model_name`, `embedding_dimensions`, `embedding_task_type` settings
- Kept `embedding_model` for backwards compatibility (deprecated)

**File**: `src/mcp_server_langgraph/skills/adapters.py` (NEW)
- `VectorProviderAdapter`: Bridges VectorSearchProvider to VectorProviderProtocol
- `EmbeddingServiceAdapter`: Bridges LangChain Embeddings to EmbeddingServiceProtocol
- `create_skill_search_tool()`: Factory for creating SkillSearchTool with adapters

## Migration Steps

### For New Deployments

1. **Install dependencies**:
   ```bash
   pip install -e .
   ```

2. **Configure Google API key** (if not already set):
   ```bash
   export GOOGLE_API_KEY="your-google-api-key"
   # Or add to .env file
   ```

3. **Start using dynamic context loading**:
   ```bash
   export ENABLE_DYNAMIC_CONTEXT_LOADING=true
   export EMBEDDING_PROVIDER=google
   export EMBEDDING_MODEL_NAME=models/text-embedding-004
   export EMBEDDING_DIMENSIONS=768
   ```

### For Existing Deployments

⚠️ **Important**: Existing Qdrant collections will need to be recreated due to dimension changes (384 → 768).

**Option 1: Recreate Collection (Recommended)**
```bash
# 1. Backup existing data (if needed)
# 2. Delete old collection
# 3. Restart with new configuration - collection will be auto-created

# Set environment variables
export EMBEDDING_PROVIDER=google
export EMBEDDING_MODEL_NAME=models/text-embedding-004
export EMBEDDING_DIMENSIONS=768
export QDRANT_COLLECTION_NAME=mcp_context_v2  # Use new collection name
```

**Option 2: Continue Using sentence-transformers (Legacy)**
```bash
# Keep using local embeddings
export EMBEDDING_PROVIDER=local
export EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
export EMBEDDING_DIMENSIONS=384

# Install sentence-transformers
pip install sentence-transformers>=2.2.0
```

## Advantages of Google Gemini Embeddings

- ✅ **No Model Hosting**: No need to download or serve embedding models
- ✅ **Better Quality**: 768-dimensional embeddings with Matryoshka truncation support
- ✅ **Task Optimization**: Optimized for retrieval, similarity, classification, etc.
- ✅ **Scalability**: API-based, scales automatically
- ✅ **Cost-Effective**: Google's embedding API is very affordable

## API Costs

Google Gemini embedding pricing (as of 2025):
- **Batch API**: ~50% cheaper than interactive
- **Model**: `text-embedding-004`
- Embeddings are generally very cheap (fractions of a cent per 1000 embeddings)

## Testing

After migration, test the dynamic context loader:

```python
from mcp_server_langgraph.core.dynamic_context_loader import DynamicContextLoader

# Initialize with Google embeddings
loader = DynamicContextLoader()

# Index some content
await loader.index_context(
    ref_id="test_1",
    content="Python is a programming language",
    ref_type="document",
    summary="About Python"
)

# Search
results = await loader.semantic_search("programming languages", top_k=5)
print(f"Found {len(results)} results")
```

## Rollback Plan

If you need to rollback to sentence-transformers:

1. Set environment variables:
   ```bash
   export EMBEDDING_PROVIDER=local
   export EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
   export EMBEDDING_DIMENSIONS=384
   ```

2. Install sentence-transformers:
   ```bash
   pip install sentence-transformers>=2.2.0
   ```

3. Use original collection or recreate with 384 dimensions

## Troubleshooting

### Error: "langchain-google-genai is required"
```bash
pip install langchain-google-genai>=0.2.0
```

### Error: "GOOGLE_API_KEY is required"
Set your Google API key:
```bash
export GOOGLE_API_KEY="your-key-here"
# Or add to .env file
```

### Error: "Dimension mismatch"
Ensure `EMBEDDING_DIMENSIONS` matches your model:
- Google `text-embedding-004`: 768
- Local `all-MiniLM-L6-v2`: 384

Recreate Qdrant collection with correct dimensions.

## Auto-Detection Feature

The project includes automatic embedding provider detection based on available API keys. This simplifies configuration for most deployments.

### Usage

```python
from mcp_server_langgraph.core.dynamic_context_loader import (
    auto_detect_embedding_provider,
    get_default_embedding_model,
)

# Auto-detect provider based on environment
provider = auto_detect_embedding_provider()
model = get_default_embedding_model(provider)

print(f"Using {provider} with model {model}")
```

### Detection Priority

The auto-detection checks for API keys in this order:

| Priority | Environment Variable | Provider | Default Model |
|----------|---------------------|----------|---------------|
| 1 | `GOOGLE_API_KEY` | `google` | `models/text-embedding-004` |
| 2 | `OPENAI_API_KEY` | `openai` | `text-embedding-3-small` |
| 3 | `HF_TOKEN` or `HUGGINGFACE_TOKEN` | `huggingface` | `sentence-transformers/all-MiniLM-L6-v2` |
| 4 | (none required) | `local` | `all-MiniLM-L6-v2` |

### Zero-Configuration Example

```bash
# Just set your API key - provider auto-detected
export GOOGLE_API_KEY="your-key"

# Start using embeddings - no EMBEDDING_PROVIDER needed
python -c "
from mcp_server_langgraph.core.dynamic_context_loader import auto_detect_embedding_provider
print(f'Provider: {auto_detect_embedding_provider()}')  # Output: google
"
```

## Supported Embedding Providers

The project supports 5 embedding providers. Choose based on your deployment needs:

> **Note**: The project defaults to `google_vertex` (Vertex AI) which uses GCP Workload Identity Federation
> and requires no API key when running on GKE. For local development without GCP, use `google` with an API key
> or let auto-detection choose based on available environment variables.

### 1. Google Gemini API (`google`) - **Recommended**

Lightweight API-based embeddings using Google Gemini.

```bash
# Installation (already in core deps)
pip install langchain-google-genai>=3.0.0

# Configuration
EMBEDDING_PROVIDER=google
EMBEDDING_MODEL_NAME=models/text-embedding-004
EMBEDDING_DIMENSIONS=768
GOOGLE_API_KEY=your-key
```

**Pros**: No model hosting, high quality, task optimization, affordable
**Cons**: Requires internet, API key required

### 2. Google Vertex AI (`google_vertex`)

Enterprise Google Cloud embeddings with Workload Identity Federation.

```bash
# Installation
pip install 'mcp-server-langgraph[embeddings-vertex]'

# Configuration
EMBEDDING_PROVIDER=google_vertex
EMBEDDING_MODEL_NAME=textembedding-gecko@latest
# Uses GCP OAuth (no API key needed with WIF)
```

**Pros**: Enterprise support, GKE integration, no API key with WIF
**Cons**: Requires GCP project setup

### 3. OpenAI (`openai`)

OpenAI's embedding API with latest models.

```bash
# Installation
pip install 'mcp-server-langgraph[embeddings-openai]'

# Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL_NAME=text-embedding-3-small  # or text-embedding-3-large
EMBEDDING_DIMENSIONS=1536  # or 3072 for large
OPENAI_API_KEY=your-key
```

**Pros**: High quality, well-documented, wide adoption
**Cons**: Higher cost than Google

### 4. HuggingFace (`huggingface`)

HuggingFace Inference API for access to thousands of models.

```bash
# Installation
pip install 'mcp-server-langgraph[embeddings-huggingface]'

# Configuration
EMBEDDING_PROVIDER=huggingface
EMBEDDING_MODEL_NAME=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
HF_TOKEN=your-token  # Optional, for private models
```

**Pros**: Wide model selection, flexible, community models
**Cons**: Variable quality depending on model

### 5. Local Sentence Transformers (`local`)

Self-hosted embeddings with full ML stack (~800MB overhead).

```bash
# Installation
pip install 'mcp-server-langgraph[embeddings-local]'

# Configuration
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
EMBEDDING_DIMENSIONS=384
```

**Pros**: Air-gapped deployments, data residency, no API costs
**Cons**: Large download, requires GPU for best performance

## Skill Search Integration

The `SkillSearchTool` provides semantic skill discovery using the configured embedding provider.

### Setup

```python
from mcp_server_langgraph.skills import create_skill_search_tool

# Create tool with configured adapters
tool = create_skill_search_tool()
if tool is not None:
    # Index skills
    from mcp_server_langgraph.skills import Skill
    skill = Skill(
        name="code-review",
        description="Review code for quality and best practices",
        tags=["code", "review"]
    )
    await tool.index_skill(skill, skill_id="skill-001")

    # Search for skills
    results = await tool.search("find code quality tools", limit=5)
    for result in results:
        print(f"{result.name}: {result.score:.2f}")
```

### Vector Provider Compatibility

The `VectorProviderAdapter` works with all vector providers:

| Provider | Collection Support | Metadata Filtering | Use Case |
|----------|-------------------|-------------------|----------|
| Qdrant | ✅ | ✅ | Production (recommended) |
| PgVector | ✅ | ✅ | PostgreSQL-based deployments |
| InMemory | ✅ | ✅ | Testing and development |

## Why Not Claude/Anthropic?

**Anthropic does not provide dedicated embedding models**. Claude is a conversational LLM only. For embeddings, the recommended alternatives are:
1. **Google Gemini** (recommended, already integrated)
2. OpenAI (text-embedding-3-small, text-embedding-3-large)
3. HuggingFace (wide model selection)
4. Local (air-gapped deployments)

We chose Google Gemini as default because:
- Already using Google API in this project
- High quality embeddings
- Good pricing
- Task-type optimization

## Support

For issues or questions:
- Check the [Google Gemini Embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings)
- Review [LangChain Google GenAI integration](https://python.langchain.com/docs/integrations/text_embedding/google_generative_ai/)
- Open an issue in the project repository
