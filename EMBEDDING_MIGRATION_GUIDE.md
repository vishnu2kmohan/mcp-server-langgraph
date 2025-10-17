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
- Supports both `google` (Gemini API) and `local` (sentence-transformers) providers

**File**: `src/mcp_server_langgraph/core/config.py`
- Added `embedding_provider`, `embedding_model_name`, `embedding_dimensions`, `embedding_task_type` settings
- Kept `embedding_model` for backwards compatibility (deprecated)

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

✅ **No Model Hosting**: No need to download or serve embedding models
✅ **Better Quality**: 768-dimensional embeddings with Matryoshka truncation support
✅ **Task Optimization**: Optimized for retrieval, similarity, classification, etc.
✅ **Scalability**: API-based, scales automatically
✅ **Cost-Effective**: Google's embedding API is very affordable

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

## Why Not Claude/Anthropic?

**Anthropic does not provide dedicated embedding models**. Claude is a conversational LLM only. For embeddings, the recommended alternatives are:
1. **Google Gemini** (recommended, already integrated)
2. OpenAI (text-embedding-3-small, text-embedding-3-large)
3. Amazon Bedrock (Titan, Cohere)

We chose Google Gemini because:
- Already using Google API in this project
- High quality embeddings
- Good pricing
- Task-type optimization

## Support

For issues or questions:
- Check the [Google Gemini Embeddings docs](https://ai.google.dev/gemini-api/docs/embeddings)
- Review [LangChain Google GenAI integration](https://python.langchain.com/docs/integrations/text_embedding/google_generative_ai/)
- Open an issue in the project repository
