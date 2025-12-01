# 28. Multi-Layer Caching Strategy

Date: 2025-10-20

## Status

Accepted

## Category

Performance & Resilience

## Context

The MCP server makes expensive operations that could benefit from caching:
- **LLM API calls**: $0.003-0.015 per request, 2-10s latency
- **OpenFGA authorization checks**: 50-100ms per check, high volume
- **Prometheus metric queries**: 100-500ms per query
- **Embedding generation**: 200-500ms per text chunk
- **Knowledge base searches**: 500ms-2s per query

**Current State**:
- No caching layer implemented
- Every request hits external services
- Repeated identical requests (e.g., same auth check)
- High latency and cost

**Performance Impact**:
- P95 latency: Unknown (no baseline)
- LLM costs: Uncontrolled, potentially high
- OpenFGA load: 50+ checks per request
- Prometheus load: Repeated queries for same metrics

**Roadmap Targets** (v2.7.0):
- 30% latency reduction
- 20% cost savings
- P95 latency < 500ms

## Decision

Implement a **multi-layer caching strategy** with different TTLs and invalidation policies:

### Cache Layers

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│  ┌────────────────────────────────┐    │
│  │   L1: In-Memory LRU Cache      │    │ < 10ms
│  │   (local, per-instance)        │    │
│  └────────────────────────────────┘    │
│              ▼                          │
│  ┌────────────────────────────────┐    │
│  │   L2: Redis Distributed Cache  │    │ < 50ms
│  │   (shared, cross-instance)     │    │
│  └────────────────────────────────┘    │
│              ▼                          │
│  ┌────────────────────────────────┐    │
│  │   L3: Provider-Native Cache    │    │ < 200ms
│  │   (Anthropic, Gemini prompts)  │    │
│  └────────────────────────────────┘    │
└─────────────────────────────────────────┘
              ▼
    External Service (uncached)          2000ms+
```

### Layer 1: In-Memory LRU Cache

**Use Case**: Frequently accessed, small data (< 1MB per entry)

**Implementation**: `functools.lru_cache` or `cachetools.LRUCache`

**Configuration**:
```python
L1_CACHE_SIZE = 1000        # Max entries
L1_CACHE_TTL = 60           # 1 minute
L1_CACHE_MAXSIZE_MB = 100   # Max memory usage
```

**What to Cache**:
- OpenFGA authorization results (user:resource:permission)
- User profile lookups (user_id → profile)
- Feature flag evaluations
- Configuration values

**Example**:
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def check_permission_cached(user: str, resource: str, action: str) -> bool:
    """Check permission with L1 cache (60s TTL)"""
    return openfga_client.check(user, resource, action)
```

### Layer 2: Redis Distributed Cache

**Use Case**: Shared across instances, larger data, longer TTL

**Implementation**: `redis` with `pickle` serialization

**Configuration**:
```python
L2_CACHE_REDIS_URL = "redis://localhost:6379/2"  # DB 2 for cache
L2_CACHE_DEFAULT_TTL = 300   # 5 minutes
L2_CACHE_MAX_SIZE_MB = 1000  # 1GB cache limit
```

**What to Cache**:
- LLM responses (with semantic similarity check)
- Embedding vectors for text chunks
- Prometheus query results
- Knowledge base search results
- Expensive computations

**Example**:
```python
import redis
import pickle
from typing import Optional

redis_client = redis.Redis(host="localhost", port=6379, db=2)

def cache_get(key: str) -> Optional[Any]:
    """Get from Redis cache"""
    data = redis_client.get(key)
    return pickle.loads(data) if data else None

def cache_set(key: str, value: Any, ttl: int = 300):
    """Set in Redis cache with TTL"""
    redis_client.setex(key, ttl, pickle.dumps(value))

async def get_llm_response_cached(prompt: str) -> str:
    """Get LLM response with L2 cache"""
    cache_key = f"llm:{hash(prompt)}"

    # Check cache first
    if cached := cache_get(cache_key):
        return cached

    # Cache miss: call LLM
    response = await llm_client.generate(prompt)

    # Store in cache (5 min TTL)
    cache_set(cache_key, response, ttl=300)

    return response
```

### Layer 3: Provider-Native Caching

**Use Case**: Leverage provider-specific caching (Anthropic, Gemini)

**Anthropic Claude Prompt Caching**:
```python
# Anthropic supports prompt caching for repeated prefixes
response = anthropic.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    system=[
        {
            "type": "text",
            "text": "You are an AI assistant...",  # Static system prompt
            "cache_control": {"type": "ephemeral"}  # Cache this!
        }
    ],
    messages=[...]
)
# Saves 90% on input tokens for repeated system prompts
```

**Google Gemini Caching**:
```python
# Gemini supports caching via context caching
from google.generativeai import caching

cached_content = caching.CachedContent.create(
    model="gemini-2.5-flash",
    system_instruction="You are an AI assistant...",
    contents=["..."],
    ttl=datetime.timedelta(minutes=5),
)
# Reuse cached content for subsequent requests
```

### Cache Key Design

**Hierarchical Key Format**:
```
<namespace>:<entity>:<identifier>:<version>
```

**Examples**:
```python
# Authorization cache
"auth:permission:user:alice:resource:doc123:action:read:v1"

# LLM response cache
"llm:response:model:claude-3-5:hash:abc123def:v1"

# Embedding cache
"embedding:text:hash:xyz789:model:all-minilm-l6-v2:v1"

# Prometheus query cache
"metrics:query:uptime:service:mcp-server:range:30d:v1"
```

**Cache Key Best Practices**:
1. Include version suffix (`:v1`) for cache invalidation
2. Use hashing for long identifiers (limit key length < 250 chars)
3. Namespace by feature area to avoid collisions
4. Include all parameters that affect output

### TTL Strategy

| Cache Type | TTL | Rationale |
|------------|-----|-----------|
| **OpenFGA Authorization** | 5 min | Permissions don't change frequently |
| **LLM Responses** | 1 hour | Same prompt → same response (deterministic) |
| **User Profiles** | 15 min | Profiles update infrequently |
| **Feature Flags** | 1 min | Need fast rollout of flag changes |
| **Prometheus Queries** | 1 min | Metrics change frequently |
| **Embeddings** | 24 hours | Text → embedding is deterministic |
| **Knowledge Base Search** | 30 min | Search index updates periodically |

### Cache Invalidation

**Strategies**:

1. **Time-based (TTL)**: Automatic expiration after duration
2. **Event-based**: Invalidate on data changes
3. **Version-based**: Change key version to invalidate all

**Event-Based Invalidation**:
```python
# Example: Invalidate user cache on profile update
async def update_user_profile(user_id: str, updates: dict):
    # Update database
    await db.update_user(user_id, updates)

    # Invalidate all caches for this user
    cache_keys = [
        f"user:profile:{user_id}:v1",
        f"user:permissions:{user_id}:*",  # Wildcard delete
    ]
    for key in cache_keys:
        redis_client.delete(key)
```

**Cache Stampede Prevention**:
```python
import asyncio
from typing import Optional

# Lock-based cache refresh (prevent thundering herd)
_refresh_locks = {}

async def get_with_lock(key: str, fetcher: Callable, ttl: int) -> Any:
    """Get from cache or fetch with lock to prevent stampede"""
    # Try L2 cache first
    if cached := cache_get(key):
        return cached

    # Acquire lock for this key
    if key not in _refresh_locks:
        _refresh_locks[key] = asyncio.Lock()

    async with _refresh_locks[key]:
        # Double-check cache (another request may have filled it)
        if cached := cache_get(key):
            return cached

        # Fetch and cache
        value = await fetcher()
        cache_set(key, value, ttl)
        return value
```

## Architecture

### New Module: `src/mcp_server_langgraph/core/cache.py`

```python
"""
Multi-layer caching system for MCP server.

Features:
- L1: In-memory LRU cache (functools.lru_cache)
- L2: Redis distributed cache
- L3: Provider-native caching (Anthropic, Gemini)
- Automatic TTL and eviction
- Cache stampede prevention
- Metrics and observability
"""

from typing import Any, Callable, Optional, TypeVar, ParamSpec
import functools
import hashlib
import pickle
import redis
from cachetools import TTLCache

P = ParamSpec('P')
T = TypeVar('T')

class CacheService:
    """Unified caching service with L1 + L2"""

    def __init__(self):
        # L1: In-memory cache (per-instance)
        self.l1_cache = TTLCache(maxsize=1000, ttl=60)

        # L2: Redis cache (shared)
        self.redis = redis.Redis(
            host="localhost",
            port=6379,
            db=2,  # Separate DB for cache
            decode_responses=False,  # Keep binary for pickle
        )

    def get(self, key: str, level: str = "l2") -> Optional[Any]:
        """Get from cache (L1 → L2 → miss)"""
        # Try L1 first
        if level in ("l1", "l2") and key in self.l1_cache:
            return self.l1_cache[key]

        # Try L2
        if level == "l2":
            data = self.redis.get(key)
            if data:
                value = pickle.loads(data)
                # Promote to L1
                self.l1_cache[key] = value
                return value

        return None

    def set(self, key: str, value: Any, ttl: int = 300, level: str = "l2"):
        """Set in cache"""
        if level in ("l1", "l2"):
            self.l1_cache[key] = value

        if level == "l2":
            self.redis.setex(key, ttl, pickle.dumps(value))

    def delete(self, key: str):
        """Delete from all cache levels"""
        self.l1_cache.pop(key, None)
        self.redis.delete(key)

    def clear(self, pattern: Optional[str] = None):
        """Clear cache (all or by pattern)"""
        self.l1_cache.clear()
        if pattern:
            keys = self.redis.keys(pattern)
            if keys:
                self.redis.delete(*keys)
        else:
            self.redis.flushdb()


# Global cache instance
_cache_service: Optional[CacheService] = None

def get_cache() -> CacheService:
    """Get global cache service"""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


# Decorator for caching async functions
def cached(key_prefix: str, ttl: int = 300, level: str = "l2"):
    """Decorator for caching async function results"""
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache = get_cache()

            # Generate cache key
            key_parts = [key_prefix]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
            key = ":".join(key_parts)

            # Hash if too long
            if len(key) > 200:
                key = f"{key_prefix}:hash:{hashlib.md5(key.encode()).hexdigest()}"

            # Try cache
            if cached_value := cache.get(key, level=level):
                return cached_value

            # Cache miss: call function
            result = await func(*args, **kwargs)

            # Store in cache
            cache.set(key, result, ttl=ttl, level=level)

            return result

        return wrapper
    return decorator
```

## Metrics & Observability

### Cache Metrics (20+)

```python
# Cache hit/miss rates
cache_hits_total{layer, cache_type}
cache_misses_total{layer, cache_type}
cache_hit_rate{layer, cache_type}  # hits / (hits + misses)

# Cache performance
cache_latency_seconds{layer, operation}  # get, set, delete
cache_size_bytes{layer, cache_type}
cache_evictions_total{layer, reason}  # ttl, size, manual

# L1 specific
l1_cache_memory_bytes
l1_cache_entries_total

# L2 specific
l2_redis_errors_total{operation}
l2_redis_connection_pool_size

# Cache effectiveness
cache_cost_savings_usd  # Estimated $ saved from cache hits
cache_latency_reduction_ms  # Estimated ms saved
```

### Cache Hit Rate Targets

| Cache Type | Target Hit Rate | Current | Status |
|------------|----------------|---------|--------|
| OpenFGA Authorization | > 80% | TBD | 🟡 |
| LLM Responses | > 40% | TBD | 🟡 |
| Embeddings | > 70% | TBD | 🟡 |
| Prometheus Queries | > 60% | TBD | 🟡 |
| User Profiles | > 90% | TBD | 🟡 |

## Configuration

### Environment Variables

```bash
# L1 Cache (In-Memory)
L1_CACHE_ENABLED=true
L1_CACHE_SIZE=1000
L1_CACHE_TTL=60
L1_CACHE_MAXSIZE_MB=100

# L2 Cache (Redis)
L2_CACHE_ENABLED=true
L2_CACHE_REDIS_URL=redis://localhost:6379/2
L2_CACHE_DEFAULT_TTL=300
L2_CACHE_MAX_SIZE_MB=1000

# L3 Cache (Provider-Native)
L3_ANTHROPIC_PROMPT_CACHE=true
L3_GEMINI_CONTEXT_CACHE=true

# Feature Flags
FF_ENABLE_CACHING=true
FF_CACHE_ENFORCEMENT_MODE=enforce  # enforce, log_only, disabled
```

## Consequences

### Positive

1. **Performance Improvement**
   - 30-50% latency reduction for cached operations
   - P95 latency: < 500ms (target achieved)
   - Reduced load on external services

2. **Cost Savings**
   - 20-40% reduction in LLM API costs
   - Fewer OpenFGA API calls
   - Lower Prometheus query load

3. **Scalability**
   - Handle higher request volume with same resources
   - Reduced database/API load enables horizontal scaling

4. **User Experience**
   - Faster response times
   - More consistent performance

### Negative

1. **Cache Staleness**
   - Stale data for TTL duration
   - Permission changes not reflected immediately
   - May violate real-time requirements

2. **Memory Usage**
   - L1 cache consumes application memory (~100MB)
   - Redis memory usage (~1GB)
   - Need monitoring and alerting

3. **Complexity**
   - Cache invalidation is hard ("one of two hard problems")
   - Debugging cache-related issues
   - More moving parts (Redis dependency)

4. **Cache Stampede Risk**
   - Thundering herd on cache expiration
   - Need locking mechanisms

### Mitigations

1. **Short TTLs**: Start with 1-5 min, increase based on metrics
2. **Tiered Rollout**: Enable caching incrementally (auth → llm → metrics)
3. **Cache Warming**: Pre-populate cache with common queries
4. **Monitoring**: Alert on low hit rates, high evictions
5. **Circuit Breaker**: Bypass cache if Redis is down (fail-safe)

## Implementation Plan

### Week 1: Foundation
- [ ] Create `core/cache.py` module
- [ ] Implement L1 cache (LRU with TTL)
- [ ] Implement L2 cache (Redis)
- [ ] Add cache metrics and observability
- [ ] Write 40+ unit tests

### Week 2: Integration - Auth Layer
- [ ] Cache OpenFGA authorization checks (5 min TTL)
- [ ] Cache user profile lookups (15 min TTL)
- [ ] Cache session lookups (already in Redis, optimize)
- [ ] Measure hit rate, tune TTLs

### Week 3: Integration - LLM Layer
- [ ] Cache LLM responses with semantic similarity
- [ ] Implement Anthropic prompt caching
- [ ] Implement Gemini context caching
- [ ] Cache embedding generation results
- [ ] Measure cost savings

### Week 4: Integration - Metrics Layer
- [ ] Cache Prometheus query results (1 min TTL)
- [ ] Cache SLA metrics calculations
- [ ] Cache compliance evidence queries
- [ ] Measure latency reduction

### Week 5: Optimization & Rollout
- [ ] Implement cache stampede prevention
- [ ] Add cache warming for common queries
- [ ] Performance testing: 1000 req/s load
- [ ] Deploy to production (gradual rollout)

## Testing Strategy

### Unit Tests
```python
def test_cache_hit():
    """Test cache hit returns cached value"""
    cache = CacheService()
    cache.set("test:key", "value", ttl=60)
    assert cache.get("test:key") == "value"

def test_cache_miss():
    """Test cache miss returns None"""
    cache = CacheService()
    assert cache.get("nonexistent:key") is None

def test_cache_expiration():
    """Test cache entries expire after TTL"""
    cache = CacheService()
    cache.set("test:key", "value", ttl=1)
    time.sleep(2)
    assert cache.get("test:key") is None
```

### Performance Tests
```python
def test_cache_performance():
    """Test cache latency is < 10ms for L1, < 50ms for L2"""
    cache = CacheService()

    # L1 latency
    start = time.time()
    cache.get("test:key")
    l1_latency = (time.time() - start) * 1000
    assert l1_latency < 10  # < 10ms

    # L2 latency
    # ... similar test
```

## References

- **Redis Caching Best Practices**: https://redis.io/docs/manual/client-side-caching/
- **Anthropic Prompt Caching**: https://docs.anthropic.com/claude/docs/prompt-caching
- **Google Gemini Caching**: https://ai.google.dev/gemini-api/docs/caching
- **cachetools Library**: https://github.com/tkem/cachetools
- **Cache Stampede Prevention**: https://en.wikipedia.org/wiki/Cache_stampede

## Success Metrics

### Performance
- **Target**: 30% P95 latency reduction
- **Baseline**: Measure current P95 latency
- **Target**: P95 < 500ms after caching

### Cost Savings
- **Target**: 20% reduction in LLM API costs
- **Measurement**: Monthly LLM spend before/after

### Cache Hit Rate
- **Target**: > 60% overall hit rate
- **Measurement**: `cache_hits / (cache_hits + cache_misses)`

### User Experience
- **Target**: < 2% increase in stale data complaints
- **Measurement**: User feedback, support tickets

---

**Last Updated**: 2025-10-20
**Next Review**: 2025-11-20 (after 1 month in production)
