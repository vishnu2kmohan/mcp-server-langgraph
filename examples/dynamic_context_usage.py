#!/usr/bin/env python3
"""
Example: Dynamic Context Loading with Qdrant

Demonstrates Anthropic's Just-in-Time context loading pattern:
1. Index contexts with lightweight identifiers
2. Semantic search for relevant content
3. Load only what's needed, when needed
4. Progressive discovery through iterative search

Prerequisites:
- Qdrant running on localhost:6333
- Set ENABLE_DYNAMIC_CONTEXT_LOADING=true in .env

Usage:
    python examples/dynamic_context_usage.py
"""

import asyncio

from mcp_server_langgraph.core.dynamic_context_loader import DynamicContextLoader, search_and_load_context
from mcp_server_langgraph.observability.telemetry import logger


async def example_1_basic_indexing_and_search():
    """Example 1: Basic indexing and semantic search"""
    print("\n" + "=" * 70)
    print("Example 1: Basic Indexing and Semantic Search")
    print("=" * 70)

    # Initialize loader
    loader = DynamicContextLoader(
        qdrant_url="localhost",
        qdrant_port=6333,
        collection_name="example_contexts",
    )

    print("\n1. Indexing sample contexts...")

    # Index some technical documentation
    contexts = [
        {
            "ref_id": "python_async_basics",
            "content": """
Python's asyncio library provides infrastructure for writing concurrent code using async/await syntax.
Key concepts:
- Event loop: Runs asynchronous tasks
- Coroutines: Functions defined with async def
- await: Suspends execution until result is ready
- Tasks: Wrap coroutines for concurrent execution

Example:
async def fetch_data():
    await asyncio.sleep(1)
    return "data"
""",
            "ref_type": "documentation",
            "summary": "Python asyncio basics and async/await syntax",
            "metadata": {"language": "python", "topic": "concurrency", "difficulty": "intermediate"},
        },
        {
            "ref_id": "docker_compose_guide",
            "content": """
Docker Compose is a tool for defining and running multi-container applications.
Key features:
- YAML configuration (docker-compose.yml)
- Service definitions with dependencies
- Volume and network management
- Environment variable configuration

Example docker-compose.yml:
services:
  app:
    image: myapp:latest
    depends_on:
      - db
  db:
    image: postgres:14
""",
            "ref_type": "documentation",
            "summary": "Docker Compose multi-container configuration",
            "metadata": {"tool": "docker", "topic": "devops", "difficulty": "beginner"},
        },
        {
            "ref_id": "redis_caching",
            "content": """
Redis is an in-memory data structure store used for caching and session management.
Common patterns:
- Cache-aside: Application checks cache before database
- Write-through: Write to cache and database simultaneously
- TTL (Time To Live): Automatic expiration of cached data

Python example:
import redis
client = redis.Redis(host='localhost', port=6379)
client.setex('key', 3600, 'value')  # Expires in 1 hour
""",
            "ref_type": "documentation",
            "summary": "Redis caching patterns and usage",
            "metadata": {"tool": "redis", "topic": "caching", "difficulty": "intermediate"},
        },
    ]

    # Index all contexts
    for ctx in contexts:
        ref = await loader.index_context(**ctx)
        print(f"   ✓ Indexed: {ref.ref_id} - {ref.summary}")

    print("\n2. Performing semantic search...")

    # Search for async programming
    query = "How do I write asynchronous code with coroutines?"
    print(f"\n   Query: '{query}'")

    results = await loader.semantic_search(query=query, top_k=3, min_score=0.5)

    print(f"\n   Found {len(results)} relevant contexts:")
    for i, result in enumerate(results, 1):
        print(f"\n   {i}. {result.ref_id}")
        print(f"      Relevance: {result.relevance_score:.2f}")
        print(f"      Summary: {result.summary}")
        print(f"      Type: {result.ref_type}")

    print("\n3. Loading full context...")

    loaded = await loader.load_batch(results, max_tokens=2000)

    print(f"\n   Loaded {len(loaded)} contexts ({sum(c.token_count for c in loaded)} tokens total)")
    for ctx in loaded:
        print(f"\n   {ctx.ref_id}:")
        print(f"   {ctx.content[:150]}...")


async def example_2_progressive_discovery():
    """Example 2: Progressive discovery pattern"""
    print("\n" + "=" * 70)
    print("Example 2: Progressive Discovery Pattern")
    print("=" * 70)

    loader = DynamicContextLoader(
        qdrant_url="localhost",
        qdrant_port=6333,
        collection_name="example_progressive",
    )

    # Index a knowledge base with increasing specificity
    knowledge_base = [
        {
            "ref_id": "ml_overview",
            "content": "Machine learning is a branch of AI focused on learning patterns from data without explicit programming.",
            "ref_type": "overview",
            "summary": "Machine learning overview",
        },
        {
            "ref_id": "supervised_learning",
            "content": "Supervised learning uses labeled training data to learn mappings from inputs to outputs. Examples: classification, regression.",
            "ref_type": "concept",
            "summary": "Supervised learning introduction",
        },
        {
            "ref_id": "neural_networks",
            "content": "Neural networks are ML models with layers of interconnected nodes inspired by biological neurons. Used for complex pattern recognition.",
            "ref_type": "concept",
            "summary": "Neural networks basics",
        },
        {
            "ref_id": "transformers",
            "content": "Transformers are neural network architectures using self-attention mechanisms. Revolutionary for NLP. Key innovation: parallel processing of sequences.",
            "ref_type": "advanced",
            "summary": "Transformer architecture",
        },
        {
            "ref_id": "bert",
            "content": "BERT (Bidirectional Encoder Representations from Transformers) uses masked language modeling for pre-training. Bidirectional context understanding.",
            "ref_type": "advanced",
            "summary": "BERT model architecture",
        },
    ]

    print("\n1. Indexing knowledge base...")
    for item in knowledge_base:
        await loader.index_context(**item)
        print(f"   ✓ {item['ref_id']}")

    print("\n2. Progressive discovery: Start broad, get specific")

    # Round 1: Broad query
    print("\n   Round 1: Broad exploration")
    query1 = "What is machine learning?"
    results1 = await loader.semantic_search(query1, top_k=2)
    print(f"   Query: '{query1}'")
    print(f"   Found: {', '.join(r.ref_id for r in results1)}")

    # Round 2: More specific based on Round 1 findings
    print("\n   Round 2: Deeper dive")
    query2 = "How do neural networks work?"
    results2 = await loader.semantic_search(query2, top_k=2)
    print(f"   Query: '{query2}'")
    print(f"   Found: {', '.join(r.ref_id for r in results2)}")

    # Round 3: Highly specific
    print("\n   Round 3: Specific implementation")
    query3 = "What makes transformers different from traditional neural nets?"
    results3 = await loader.semantic_search(query3, top_k=2)
    print(f"   Query: '{query3}'")
    print(f"   Found: {', '.join(r.ref_id for r in results3)}")

    print("\n   ✓ Progressive discovery allows iterative refinement")


async def example_3_token_budget_management():
    """Example 3: Loading contexts within token budget"""
    print("\n" + "=" * 70)
    print("Example 3: Token Budget Management")
    print("=" * 70)

    loader = DynamicContextLoader(
        qdrant_url="localhost",
        qdrant_port=6333,
        collection_name="example_budgets",
    )

    # Index various size contexts
    print("\n1. Indexing contexts of different sizes...")

    large_content = "Python " + ("is a programming language. " * 50)  # ~300 tokens
    medium_content = "Docker " + ("is a containerization tool. " * 20)  # ~120 tokens
    small_content = "Redis is an in-memory database."  # ~10 tokens

    await loader.index_context("large_doc", large_content, "document", "Large Python doc")
    await loader.index_context("medium_doc", medium_content, "document", "Medium Docker doc")
    await loader.index_context("small_doc", small_content, "document", "Small Redis doc")

    print("   ✓ Indexed 3 contexts (large, medium, small)")

    # Search and load with different budgets
    query = "programming tools and databases"
    references = await loader.semantic_search(query, top_k=10)

    print(f"\n2. Loading with different token budgets:")

    # Budget 1: Small (only small docs)
    loaded_small = await loader.load_batch(references, max_tokens=50)
    total_tokens_small = sum(c.token_count for c in loaded_small)
    print(f"\n   Budget: 50 tokens")
    print(f"   Loaded: {len(loaded_small)} contexts ({total_tokens_small} tokens)")

    # Budget 2: Medium (small + medium)
    loaded_medium = await loader.load_batch(references, max_tokens=200)
    total_tokens_medium = sum(c.token_count for c in loaded_medium)
    print(f"\n   Budget: 200 tokens")
    print(f"   Loaded: {len(loaded_medium)} contexts ({total_tokens_medium} tokens)")

    # Budget 3: Large (all)
    loaded_large = await loader.load_batch(references, max_tokens=500)
    total_tokens_large = sum(c.token_count for c in loaded_large)
    print(f"\n   Budget: 500 tokens")
    print(f"   Loaded: {len(loaded_large)} contexts ({total_tokens_large} tokens)")

    print("\n   ✓ Token budgets allow precise context control")


async def example_4_integration_with_agent():
    """Example 4: Using dynamic context with agent messages"""
    print("\n" + "=" * 70)
    print("Example 4: Integration with Agent Messages")
    print("=" * 70)

    loader = DynamicContextLoader(
        qdrant_url="localhost",
        qdrant_port=6333,
        collection_name="example_agent",
    )

    # Index some API documentation
    print("\n1. Indexing API documentation...")

    await loader.index_context(
        ref_id="api_auth",
        content="API authentication uses Bearer tokens in Authorization header. "
        "Example: Authorization: Bearer <token>. Tokens expire after 1 hour.",
        ref_type="api_doc",
        summary="API authentication guide",
    )

    await loader.index_context(
        ref_id="api_users",
        content="User endpoints: GET /users (list), GET /users/:id (details), "
        "POST /users (create), PUT /users/:id (update), DELETE /users/:id (delete)",
        ref_type="api_doc",
        summary="Users API endpoints",
    )

    print("   ✓ Indexed API documentation")

    # Simulate agent receiving user query
    print("\n2. Agent receives user query...")
    user_query = "How do I authenticate API requests?"

    print(f"   User: '{user_query}'")

    # Use search_and_load_context helper
    print("\n3. Loading relevant context...")
    loaded_contexts = await search_and_load_context(
        query=user_query,
        loader=loader,
        top_k=2,
        max_tokens=500,
    )

    print(f"   Loaded {len(loaded_contexts)} contexts")

    # Convert to messages for agent
    context_messages = loader.to_messages(loaded_contexts)

    print(f"\n4. Context ready for agent:")
    for msg in context_messages:
        print(f"\n   {msg.type}:")
        print(f"   {msg.content[:200]}...")

    print("\n   ✓ Context integrated into agent conversation")


async def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("Dynamic Context Loading Examples")
    print("Anthropic Best Practice: Just-in-Time Context Loading")
    print("=" * 70)

    try:
        # Example 1: Basic usage
        await example_1_basic_indexing_and_search()

        # Example 2: Progressive discovery
        await example_2_progressive_discovery()

        # Example 3: Token budgets
        await example_3_token_budget_management()

        # Example 4: Agent integration
        await example_4_integration_with_agent()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)

        print("\n📚 Key Takeaways:")
        print("   • Index contexts with lightweight identifiers")
        print("   • Use semantic search to find relevant content")
        print("   • Load only what's needed (token budgets)")
        print("   • Progressive discovery for complex queries")
        print("   • Integrate seamlessly with agent messages")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Qdrant is running:")
        print("   docker compose up -d qdrant")
        raise


if __name__ == "__main__":
    asyncio.run(main())
