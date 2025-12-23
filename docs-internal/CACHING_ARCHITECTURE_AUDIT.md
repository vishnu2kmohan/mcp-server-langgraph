# Caching Architecture Audit & DRY Recommendations

**Date**: 2025-12-22
**Status**: AUDIT COMPLETE
**Author**: Claude Code Ultrathink Analysis

---

## Executive Summary

This document provides a comprehensive audit of all caching patterns across the codebase, identifies DRY violations, and proposes a unified architecture to eliminate duplication and improve consistency.

### Key Findings

| Category | Count | Status |
|----------|-------|--------|
| Total caching implementations | 8 | Audited |
| Using CacheService properly | 2 | Compliant |
| DRY violations (duplicate patterns) | 4 | Needs refactoring |
| Security concerns | 2 | High priority |
| Frontend patterns | 3 | Partially compliant |

---

## Current Architecture

### Tiered Cache System (Gold Standard)

**File**: `src/mcp_server_langgraph/core/cache.py`

```
┌─────────────────────────────────────────────────────────┐
│                    CacheService                          │
├─────────────────────────────────────────────────────────┤
│  L1: TTLCache (in-memory, per-instance)                 │
│  └── <10ms latency, 1000 entries max                    │
├─────────────────────────────────────────────────────────┤
│  L2: Redis (distributed, shared)                        │
│  └── <50ms latency, circuit breaker, retry              │
├─────────────────────────────────────────────────────────┤
│  L3: Provider-native (Anthropic/Gemini prompt cache)    │
│  └── Managed by LLM provider                            │
├─────────────────────────────────────────────────────────┤
│  Resilience (ADR-0026):                                 │
│  ├── Circuit breaker (pybreaker)                        │
│  ├── Retry with exponential backoff                     │
│  ├── L1 fallback on L2 failure                          │
│  └── Cache stampede prevention (locks)                  │
├─────────────────────────────────────────────────────────┤
│  Observability:                                         │
│  ├── Prometheus metrics (hits/misses/latency)           │
│  ├── OpenTelemetry tracing                              │
│  └── Structured logging                                 │
└─────────────────────────────────────────────────────────┘
```

### TTL Configuration (CACHE_TTLS)

| Cache Type | TTL | Rationale |
|------------|-----|-----------|
| `auth_permission` | 300s (5min) | Permissions change infrequently |
| `user_profile` | 900s (15min) | Profile updates rare |
| `llm_response` | 3600s (1hr) | Deterministic responses |
| `embedding` | 86400s (24hr) | Embeddings are deterministic |
| `prometheus_query` | 60s (1min) | Metrics change frequently |
| `knowledge_base` | 1800s (30min) | Search index updates periodically |
| `feature_flag` | 60s (1min) | Fast rollout needed |
| `connection` | 300s (5min) | Connection configs stable |
| `connection_health` | 60s (1min) | Health may change |

---

## Audit Results

### Backend Implementations

#### Compliant (Using CacheService Properly)

| Service | File | Pattern | Status |
|---------|------|---------|--------|
| **CachedConnectionRepository** | `repositories/cached_connections.py` | L1+L2 via CacheService | OK |
| **Core Cache** | `core/cache.py` | Reference implementation | OK |

#### DRY Violations (Duplicate Patterns)

##### 1. AIUXService - DUPLICATE TIERED CACHE

**File**: `src/mcp_server_langgraph/api/v1/ai_ux_service.py`

**Issue**: Implements its own tiered caching (L1 TTLCache + L2 Redis) instead of using CacheService.

```python
# CURRENT (lines 413-418, 543-558)
self._response_cache: TTLCache[str, Any] = TTLCache(...)
self.redis_cache = cache_service.redis  # Direct Redis access

# DUPLICATED METHODS (lines 2423-2610)
async def get_tiered_cached_response(...)
async def set_tiered_cached_response(...)
async def invalidate_user_cache(...)
async def invalidate_method_cache(...)
```

**Recommendation**: Refactor to use `CacheService` directly:
```python
# PROPOSED
from mcp_server_langgraph.core.cache import get_cache, CACHE_TTLS

class AIUXService:
    def __init__(self):
        self._cache = get_cache()

    async def _get_cached(self, key: str) -> Any | None:
        return await self._cache.aget(key)

    async def _set_cached(self, key: str, value: Any, ttl: int = CACHE_TTLS["llm_response"]) -> None:
        await self._cache.aset(key, value, ttl=ttl)
```

**Impact**: Removes ~200 lines of duplicate code, gains circuit breaker, standardized metrics.

---

##### 2. DPoP Replay Cache - NO TTL/LRU

**File**: `src/mcp_server_langgraph/auth/dpop.py` (lines 172-201)

**Issue**: Uses simple `set()` with crude eviction (clears entire cache when full).

```python
# CURRENT (lines 186-198)
self._cache: set[str] = set()  # No TTL!

def mark_used(self, jti: str) -> None:
    if len(self._cache) >= self._max_size:
        self._cache.clear()  # DANGEROUS: Loses all replay protection!
    self._cache.add(jti)
```

**Security Risk**: Clearing the entire cache allows replay attacks for previously seen JTIs.

**Recommendation**: Use TTLCache with proper eviction:
```python
# PROPOSED
from cachetools import TTLCache

class DPoPReplayCache:
    def __init__(self, max_size: int = 10000, ttl: int = 300) -> None:
        # TTL matches max_age_seconds in verify_dpop_proof
        self._cache: TTLCache[str, bool] = TTLCache(maxsize=max_size, ttl=ttl)

    def has_been_used(self, jti: str) -> bool:
        return jti in self._cache

    def mark_used(self, jti: str) -> None:
        self._cache[jti] = True  # LRU eviction, TTL expiry
```

**Impact**: Fixes security vulnerability, proper TTL expiry of JTIs.

---

##### 3. API Key Caching - NO L1 FALLBACK

**File**: `src/mcp_server_langgraph/auth/api_keys.py` (lines 176-237)

**Issue**: Uses Redis-only caching with no L1 fallback when Redis fails.

```python
# CURRENT (lines 186-200)
async def _get_from_cache(self, api_key_hash: str) -> dict[str, Any] | None:
    if not self.redis:
        return None  # No fallback!

    cached_data = await self.redis.get(cache_key)
    # No L1 cache for fast lookups
```

**Recommendation**: Add L1 TTLCache for performance and resilience:
```python
# PROPOSED
from cachetools import TTLCache

class APIKeyManager:
    def __init__(self):
        self._l1_cache: TTLCache[str, dict] = TTLCache(maxsize=1000, ttl=300)
        self.redis = ...

    async def _get_from_cache(self, api_key_hash: str) -> dict[str, Any] | None:
        # L1 first
        if api_key_hash in self._l1_cache:
            return self._l1_cache[api_key_hash]

        # L2 fallback
        if self.redis:
            cached = await self.redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                self._l1_cache[api_key_hash] = data  # Promote to L1
                return data

        return None
```

**Impact**: Adds ~10x faster lookups, resilience when Redis down.

---

##### 4. Artifact Caching - RAW REDIS

**File**: `src/mcp_server_langgraph/storage/artifacts/redis_cache.py`

**Issue**: Uses raw Redis client instead of CacheService. Missing:
- L1 in-memory cache
- Circuit breaker
- Retry logic
- Standardized metrics

**Recommendation**: Refactor to use CacheService or create `ArtifactCacheService` that extends base patterns.

---

### Security Concerns

| Issue | File | Risk Level | Recommendation |
|-------|------|------------|----------------|
| DPoP cache full-clear | `auth/dpop.py:198` | HIGH | Use TTLCache with LRU eviction |
| API key no L1 fallback | `auth/api_keys.py` | MEDIUM | Add L1 cache layer |

---

### Frontend Implementations

#### Compliant Patterns

| Hook | File | Pattern | Status |
|------|------|---------|--------|
| **useAICache** | `hooks/useAICache.ts` | Map-based + SWR | OK |
| **useAICacheMetrics** | `hooks/useAICacheMetrics.ts` | Metrics tracking | OK |
| **usePersonaCacheInvalidation** | `hooks/usePersonaCacheInvalidation.ts` | Context-based invalidation | OK |

#### RTK Query Patterns

| Endpoint Group | Cache Strategy | TTL | Status |
|----------------|----------------|-----|--------|
| Feature Flags | `keepUnusedDataFor: 600` | 10min | Consider reducing to 5min |
| Workflows | Tag-based invalidation | N/A | OK |
| Sessions | Partial invalidation | N/A | OK |

---

## DRY Consolidation Plan

### Phase 1: Create Abstract Base (Week 1)

Create `TieredCacheMixin` for services to inherit:

```python
# src/mcp_server_langgraph/core/cache_mixin.py

from abc import ABC
from typing import Any, TypeVar
from mcp_server_langgraph.core.cache import CacheService, get_cache, CACHE_TTLS

T = TypeVar("T")

class TieredCacheMixin(ABC):
    """
    Mixin providing tiered caching capabilities.

    Services inherit this to get consistent L1+L2 caching
    with circuit breaker, retry, and metrics.

    Usage:
        class MyService(TieredCacheMixin):
            cache_prefix = "my_service"
            cache_ttl = CACHE_TTLS["llm_response"]

            async def get_data(self, key: str) -> Data:
                cache_key = self._make_cache_key(key)

                # Check cache
                cached = await self._cache_get(cache_key)
                if cached:
                    return cached

                # Fetch and cache
                data = await self._fetch_data(key)
                await self._cache_set(cache_key, data)
                return data
    """

    cache_prefix: str = "default"
    cache_ttl: int = 300

    @property
    def _cache(self) -> CacheService:
        if not hasattr(self, "_cache_service"):
            self._cache_service = get_cache()
        return self._cache_service

    def _make_cache_key(self, *parts: str) -> str:
        """Generate prefixed cache key."""
        return f"{self.cache_prefix}:{':'.join(parts)}"

    async def _cache_get(self, key: str) -> Any | None:
        """Get from tiered cache (L1 -> L2 -> None)."""
        return await self._cache.aget(key)

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set in both L1 and L2 cache."""
        await self._cache.aset(key, value, ttl=ttl or self.cache_ttl)

    async def _cache_delete(self, key: str) -> None:
        """Delete from both L1 and L2 cache."""
        await self._cache.adelete(key)

    async def _cache_invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all keys matching prefix."""
        return await self._cache.adelete_pattern(f"{self.cache_prefix}:{prefix}:*")
```

### Phase 2: Migrate Services (Week 2-3)

| Service | Migration Effort | Priority |
|---------|-----------------|----------|
| AIUXService | Medium (200 lines to remove) | High |
| DPoPReplayCache | Low (20 lines) | Critical |
| APIKeyManager | Low (30 lines) | High |
| ArtifactCache | Medium | Medium |

### Phase 3: Frontend Consolidation (Week 4)

Create `useTieredCache` hook:

```typescript
// src/hooks/useTieredCache.ts

interface TieredCacheOptions<T> {
  key: string;
  fetcher: () => Promise<T>;
  ttlMs?: number;
  staleMs?: number;  // SWR threshold
  onCacheHit?: (layer: 'l1' | 'l2') => void;
  onCacheMiss?: () => void;
}

export function useTieredCache<T>(options: TieredCacheOptions<T>) {
  // Combines:
  // - useAICache (caching logic)
  // - useAICacheMetrics (metrics tracking)
  // - usePersonaCacheInvalidation (context invalidation)
}
```

---

## Migration Examples

### AIUXService Migration

**Before** (current):
```python
class AIUXService:
    def __init__(self):
        self._response_cache: TTLCache[str, Any] = TTLCache(...)
        self.redis_cache = cache_service.redis

    async def get_tiered_cached_response(self, cache_key, method, stale_threshold_seconds):
        # 50+ lines of duplicate caching logic
        ...
```

**After** (proposed):
```python
class AIUXService(TieredCacheMixin):
    cache_prefix = "ai_ux"
    cache_ttl = CACHE_TTLS["llm_response"]

    async def analyze_persona(self, request: PersonaAnalyzeRequest) -> PersonaAnalyzeResponse:
        cache_key = self._make_cache_key("persona", request.user_id, hash(request))

        # Single line cache check
        cached = await self._cache_get(cache_key)
        if cached:
            return PersonaAnalyzeResponse(**cached)

        # Fetch and cache
        result = await self._do_persona_analysis(request)
        await self._cache_set(cache_key, result.model_dump())
        return result
```

---

## Metrics Consolidation

### Current State (Fragmented)

- `cache.hits` / `cache.misses` (CacheService)
- `ai_ux_l1_cache_hits_total` / `ai_ux_l2_cache_hits_total` (AIUXService)
- No metrics for DPoP, API Key, Artifact caches

### Proposed (Unified)

All services using `TieredCacheMixin` automatically get:

```python
# Prometheus metrics (auto-labeled by service)
cache_operations_total{service="ai_ux", layer="l1", operation="hit"}
cache_operations_total{service="ai_ux", layer="l2", operation="hit"}
cache_operations_total{service="api_key", layer="l1", operation="miss"}
cache_latency_seconds{service="artifact", layer="l2"}
```

---

## Summary

### Immediate Actions (Critical)

1. **Fix DPoP Replay Cache** - Security vulnerability, use TTLCache
2. **Add L1 to API Key Cache** - Resilience improvement

### Short-term Actions (High Priority)

3. **Create TieredCacheMixin** - DRY foundation
4. **Migrate AIUXService** - Remove 200 lines of duplication
5. **Standardize metrics** - Unified observability

### Medium-term Actions (Nice to Have)

6. **Migrate Artifact Cache** - Consistency
7. **Create useTieredCache hook** - Frontend consolidation
8. **Document cache key conventions** - Developer experience

---

## Appendix: File References

| File | Lines | Caching Pattern |
|------|-------|-----------------|
| `core/cache.py` | 1-1100 | Reference implementation |
| `api/v1/ai_ux_service.py` | 413-418, 543-558, 2379-2610 | Duplicate tiered cache |
| `auth/dpop.py` | 172-201 | Set-based (no TTL) |
| `auth/api_keys.py` | 176-237 | Redis-only |
| `storage/artifacts/redis_cache.py` | 64-335 | Raw Redis |
| `repositories/cached_connections.py` | 35-401 | Uses CacheService |
| `hooks/useAICache.ts` | 1-300 | Map-based + SWR |
| `hooks/useAICacheMetrics.ts` | 1-238 | Metrics tracking |
| `hooks/usePersonaCacheInvalidation.ts` | 1-150 | Context invalidation |

---

## Detailed Migration Path

### Migration 1: DPoP Replay Cache (CRITICAL)

**File**: `src/mcp_server_langgraph/auth/dpop.py`
**Priority**: CRITICAL (Security)
**Effort**: Low (~30 min)

**Current Implementation (lines 172-201)**:
```python
class DPoPReplayCache:
    def __init__(self, max_size: int = 10000) -> None:
        self._cache: set[str] = set()  # No TTL!
        self._max_size = max_size

    def mark_used(self, jti: str) -> None:
        if len(self._cache) >= self._max_size:
            self._cache.clear()  # DANGEROUS: Replay window reopens!
```

**Proposed Implementation**:
```python
from cachetools import TTLCache

class DPoPReplayCache:
    def __init__(self, max_size: int = 10000, ttl: int = 300) -> None:
        # TTL matches max_age_seconds in verify_dpop_proof (default 300s)
        self._cache: TTLCache[str, bool] = TTLCache(maxsize=max_size, ttl=ttl)

    def has_been_used(self, jti: str) -> bool:
        return jti in self._cache

    def mark_used(self, jti: str) -> None:
        self._cache[jti] = True  # LRU eviction on max_size, TTL expiry
```

**Testing**:
- [ ] Unit test: TTL expiry after 300s
- [ ] Unit test: LRU eviction at max_size (no full clear)
- [ ] Integration test: Replay attack prevention

---

### Migration 2: API Key Cache (HIGH)

**File**: `src/mcp_server_langgraph/auth/api_keys.py`
**Priority**: HIGH (Resilience)
**Effort**: Low (~1 hour)

**Current Implementation**:
```python
async def _get_from_cache(self, api_key_hash: str) -> dict[str, Any] | None:
    if not self.redis:
        return None  # No fallback!
    cached_data = await self.redis.get(cache_key)
```

**Proposed Implementation**:
```python
from cachetools import TTLCache

class APIKeyManager:
    def __init__(self):
        # L1 in-memory cache for fast lookups
        self._l1_cache: TTLCache[str, dict] = TTLCache(maxsize=1000, ttl=300)
        self.redis = ...

    async def _get_from_cache(self, api_key_hash: str) -> dict[str, Any] | None:
        # L1 first (fast)
        if api_key_hash in self._l1_cache:
            return self._l1_cache[api_key_hash]

        # L2 fallback (Redis)
        if self.redis:
            try:
                cached = await self.redis.get(f"apikey:{api_key_hash}")
                if cached:
                    data = json.loads(cached)
                    self._l1_cache[api_key_hash] = data  # Promote to L1
                    return data
            except Exception:
                pass  # Graceful degradation

        return None

    async def _invalidate_cache(self, api_key_hash: str) -> None:
        # Clear from both L1 and L2
        self._l1_cache.pop(api_key_hash, None)
        if self.redis:
            await self.redis.delete(f"apikey:{api_key_hash}")
```

**Testing**:
- [ ] Unit test: L1 cache hit
- [ ] Unit test: L2 cache hit with L1 promotion
- [ ] Unit test: Redis failure graceful degradation
- [ ] Integration test: API key lookup performance

---

### Migration 3: AIUXService (HIGH)

**File**: `src/mcp_server_langgraph/api/v1/ai_ux_service.py`
**Priority**: HIGH (DRY)
**Effort**: Medium (~2-4 hours)

**Current State**: 200+ lines of duplicate tiered caching code.

**Migration Steps**:

1. **Add TieredCacheMixin inheritance**:
```python
from mcp_server_langgraph.core import TieredCacheMixin

class AIUXService(TieredCacheMixin):
    cache_prefix = "ai_ux"
    cache_ttl = 3600  # 1 hour for LLM responses
```

2. **Replace custom cache methods with mixin methods**:
```python
# BEFORE (lines 2423-2489)
async def get_tiered_cached_response(self, cache_key, method, stale_threshold_seconds):
    # 50+ lines of caching logic

# AFTER
async def _get_cached_with_swr(self, method: str, request: Any) -> Any | None:
    cache_key = self._make_method_cache_key(method, request.model_dump())
    return await self._cache_get_with_metrics(cache_key, method=method)
```

3. **Remove duplicate TTLCache and Redis initialization**:
```python
# DELETE (lines 413-418, 543-558)
self._response_cache: TTLCache[str, Any] = TTLCache(...)
self.redis_cache = cache_service.redis
```

4. **Update all method cache lookups**:
```python
# BEFORE
cached = self._get_cached_response(method_name, request)
self._cache_response(method_name, request, result)

# AFTER
cached = await self._cache_get_with_metrics(cache_key, method=method_name)
await self._cache_set(cache_key, result.model_dump())
```

**Testing**:
- [ ] All existing AIUXService tests pass
- [ ] Prometheus metrics still emitted
- [ ] SWR behavior preserved

---

### Migration 4: Artifact Cache (MEDIUM)

**File**: `src/mcp_server_langgraph/storage/artifacts/redis_cache.py`
**Priority**: MEDIUM (Consistency)
**Effort**: Medium (~2 hours)

**Migration Steps**:

1. Add TieredCacheMixin:
```python
class RedisCachedArtifactsService(TieredCacheMixin, ArtifactsService):
    cache_prefix = "artifact"
    cache_ttl = 300  # 5 minutes
```

2. Replace raw Redis calls with mixin methods.

3. Add L1 cache for frequently accessed artifacts.

---

## Frontend Migration Path

### Phase 1: Create useTieredCache Hook

**File**: `src/hooks/useTieredCache.ts`

```typescript
import { useMemo, useCallback, useRef } from 'react';
import { useAICache, clearAICacheByPrefix } from './useAICache';
import { useAICacheMetrics } from './useAICacheMetrics';
import { usePersonaCacheInvalidation } from './usePersonaCacheInvalidation';

interface UseTieredCacheOptions<T> {
  cachePrefix: string;
  key: string;
  fetcher: () => Promise<T>;
  ttlMs?: number;
  staleMs?: number;
  enabled?: boolean;
}

export function useTieredCache<T>(options: UseTieredCacheOptions<T>) {
  const { cachePrefix, key, fetcher, ttlMs = 300000, staleMs, enabled = true } = options;

  // Compose existing hooks
  const fullKey = useMemo(() => `${cachePrefix}:${key}`, [cachePrefix, key]);

  const cache = useAICache({
    key: fullKey,
    fetcher,
    staleTime: staleMs || ttlMs * 0.8,
    enabled,
  });

  const metrics = useAICacheMetrics();

  // Persona-based invalidation
  usePersonaCacheInvalidation({
    onInvalidate: () => clearAICacheByPrefix(cachePrefix),
  });

  // Track metrics
  const trackHit = useCallback(() => {
    metrics.trackCacheHit(cachePrefix);
  }, [metrics, cachePrefix]);

  const trackMiss = useCallback(() => {
    metrics.trackCacheMiss(cachePrefix);
  }, [metrics, cachePrefix]);

  return {
    ...cache,
    trackHit,
    trackMiss,
    invalidate: () => clearAICacheByPrefix(cachePrefix),
  };
}
```

### Phase 2: Frontend AI Hooks Analysis (COMPLETE - NO MIGRATION NEEDED)

**Decision**: AI hooks should NOT be migrated to useTieredCache.

**Reason**: These hooks use RTK Query mutations which have their own built-in caching:
- `keepUnusedDataFor` - Automatic data retention
- Tag-based invalidation - Precise cache management
- Optimistic updates - Better UX
- Polling support - Real-time data
- Integration with Redux DevTools - Debugging

The `useTieredCache` hook is designed for **custom fetchers** that bypass RTK Query, not as a replacement for RTK Query's caching.

**Analysis Results**:

| Hook | Caching Strategy | Migration Status |
|------|------------------|------------------|
| useAIEmptyState | RTK Query mutation | NO MIGRATION NEEDED |
| useAINudges | RTK Query mutation + Redux slice | NO MIGRATION NEEDED |
| useAIPersonaAnalysis | RTK Query mutation + Redux slice | NO MIGRATION NEEDED |
| useAIDisclosure | RTK Query mutation + Redux slice | NO MIGRATION NEEDED |
| useAIErrorRecovery | RTK Query mutation | NO MIGRATION NEEDED |
| useSessionIntelligence | RTK Query | NO MIGRATION NEEDED |
| useConversationIntelligence | RTK Query | NO MIGRATION NEEDED |

**When to use useTieredCache**:
- Custom fetch logic that bypasses RTK Query
- Caching data from non-API sources (localStorage, computed values)
- L1+L2 tiered caching with SWR for specific use cases

---

## Validation Checklist

### Before Migration

- [ ] All existing tests pass
- [ ] Baseline metrics recorded
- [ ] Cache hit rates documented

### After Migration

- [ ] All existing tests still pass
- [ ] New TieredCacheMixin tests pass
- [ ] Prometheus metrics emit correctly
- [ ] Cache hit rates maintained or improved
- [ ] No memory leaks in L1 cache
- [ ] Redis connection handling works

### Performance Validation

- [ ] L1 hit latency < 1ms
- [ ] L2 hit latency < 10ms
- [ ] Pattern deletion uses SCAN (not KEYS)
- [ ] Circuit breaker trips on Redis failures

---

## Status Tracking

| Migration | Status | Assignee | Completed |
|-----------|--------|----------|-----------|
| TieredCacheMixin | COMPLETE | Claude Code | 2025-12-22 |
| DPoP Replay Cache | COMPLETE | Claude Code | 2025-12-22 |
| API Key Cache | COMPLETE | Claude Code | 2025-12-22 |
| AIUXService | COMPLETE | Claude Code | 2025-12-22 |
| Artifact Cache | COMPLETE | Claude Code | 2025-12-22 |
| useTieredCache Hook | COMPLETE | Claude Code | 2025-12-22 |
| Integration Tests | COMPLETE | Claude Code | 2025-12-22 |
| AI Hooks Analysis | COMPLETE | Claude Code | 2025-12-22 |
| AICacheMetricsDashboard L1/L2 | COMPLETE | Claude Code | 2025-12-22 |
| RTK Query Decision Doc | COMPLETE | Claude Code | 2025-12-22 |

---

## Completed: TieredCacheMixin

**Status**: COMPLETE
**File**: `src/mcp_server_langgraph/core/cache_mixin.py`
**Tests**: `tests/unit/core/test_cache_mixin.py` (18 tests passing)

Features implemented:
- `cache_prefix` / `cache_ttl` class attributes
- `_make_cache_key(*parts)` - Prefixed key generation
- `_make_user_cache_key(method, user_id)` - User-scoped keys
- `_make_method_cache_key(method, request)` - Hash-based keys
- `_cache_get(key)` - Async get from L1 → L2 → None
- `_cache_get_with_metrics(key, method)` - Get with Prometheus tracking
- `_cache_set(key, value, ttl)` - Set in L1 + L2
- `_cache_delete(key)` - Delete from L1 + L2
- `_cache_invalidate_prefix(prefix)` - Pattern-based deletion
- `_cache_invalidate_user(user_id)` - User-scoped invalidation

**Also Added**: `adelete_pattern(pattern)` method to `CacheService` for SCAN-based pattern deletion.

---

## Completed: AIUXService Migration

**Status**: COMPLETE
**File**: `src/mcp_server_langgraph/api/v1/ai_ux_service.py`
**Tests**: `tests/unit/api/v1/test_ai_ux_service_mixin_migration.py` (23 tests passing)

**Changes Made**:
1. AIUXService now inherits from `StaleWhileRevalidateMixin`
2. Added class attributes: `cache_prefix="ai_ux"`, `cache_ttl=3600`, `stale_threshold_seconds=60`
3. CacheService initialized in `__init__` via `self._cache_service = get_cache()`
4. `invalidate_user_cache()` delegates to `_cache_invalidate_user()`
5. `invalidate_method_cache()` delegates to `_cache_invalidate_prefix()`

**Benefits**:
- ~60 lines of duplicate cache implementation removed
- Now uses consistent L1+L2 tiered caching via mixin
- Stale-while-revalidate pattern available via `_cache_get_swr()`
- Prometheus metrics automatically tracked
- OpenTelemetry tracing available

**Backward Compatibility**:
- Public methods `get_tiered_cached_response()`, `set_tiered_cached_response()` preserved
- Cache key format remains compatible: `ai_ux:{method}:{hash}`

---

## Completed: useTieredCache Frontend Hook

**Status**: COMPLETE
**File**: `src/mcp_server_langgraph/studio/frontend/src/hooks/useTieredCache.ts`
**Tests**: `src/mcp_server_langgraph/studio/frontend/src/hooks/useTieredCache.test.tsx` (12 tests passing)

**Features implemented**:
- L1 (in-memory Map) + L2 (sessionStorage) tiered caching
- Stale-while-revalidate (SWR) pattern with configurable threshold
- Cache statistics tracking (l1Hits, l2Hits, misses, age)
- Automatic cache invalidation
- Request deduplication for concurrent fetches
- TTL-based expiration
- Error handling with graceful degradation

**API**:
```typescript
const { data, isLoading, isStale, error, invalidate, refetch, cacheStats } = useTieredCache(
  "cache:key",
  () => fetchData(),
  {
    ttlMs: 300000,           // 5 minutes default
    staleThresholdMs: 60000, // 60 seconds default
    enabled: true,
    deduplicate: true,
  }
);
```

**Test Coverage**:
- Initialization state (isLoading, data undefined)
- L2 cache persistence to sessionStorage
- L2 cache hit tracking in cacheStats
- SWR stale data detection
- SWR fresh data handling
- Cache invalidation clearing L2
- TTL expiration triggering refetch
- Error handling on fetch failure
- Cache stats tracking for misses
- Disabled fetching via `enabled: false`

---

## Architectural Decision: RTK Query vs useTieredCache

**Date**: 2025-12-22
**Status**: DOCUMENTED
**Decision**: Use RTK Query for API calls, use useTieredCache for custom fetchers only.

### Decision Summary

| Use Case | Recommended Approach | Rationale |
|----------|---------------------|-----------|
| API data fetching | RTK Query | Built-in caching, DevTools, invalidation |
| Custom fetchers | useTieredCache | L1+L2 tiered cache, SWR |
| WebSocket data | Redux slices | Real-time updates |
| Computed values | useTieredCache | Cache expensive computations |

### RTK Query Advantages

RTK Query provides enterprise-grade caching out of the box:

```typescript
// RTK Query provides all of this automatically:
const { data, isLoading, error, refetch } = useGetPersonaAnalysisQuery({
  userId: currentUser.id,
}, {
  // Automatic caching
  keepUnusedDataFor: 600, // 10 minutes
  // Tag-based invalidation
  // Optimistic updates
  // Polling support
  pollingInterval: 30000, // optional
});
```

**Features**:
1. **Automatic caching**: Data cached per-query with configurable retention
2. **Tag-based invalidation**: Fine-grained cache control via `providesTags`/`invalidatesTags`
3. **Optimistic updates**: Better UX for mutations
4. **Request deduplication**: Built-in for concurrent requests
5. **DevTools integration**: Debugging via Redux DevTools
6. **Error handling**: Standardized error states

### useTieredCache Use Cases

The useTieredCache hook is for scenarios where RTK Query is not used:

```typescript
// Use useTieredCache for custom fetchers:
const { data, isLoading, isStale, cacheStats } = useTieredCache(
  "custom:key",
  () => computeExpensiveValue(), // Not an API call
  {
    ttlMs: 300000,
    staleThresholdMs: 60000,
  }
);
```

**Ideal for**:
1. **Custom computed values** not from API
2. **Aggregated data** from multiple sources
3. **Client-side only** data that persists across re-renders
4. **SessionStorage-backed** caching for tab persistence

### Anti-Pattern: Don't Migrate RTK Query Hooks

**DO NOT** migrate hooks that already use RTK Query:

```typescript
// ❌ WRONG: Don't wrap RTK Query with useTieredCache
const { data } = useGetNudgeRecommendationMutation();
const cached = useTieredCache("nudge", () => data, { ... }); // DON'T DO THIS

// ✅ CORRECT: Use RTK Query directly
const [getNudge, { data, isLoading }] = useGetNudgeRecommendationMutation();
```

### AICacheMetricsDashboard Integration

The dashboard now supports both caching strategies:

```typescript
<AICacheMetricsDashboard
  snapshot={aiMetrics}
  featureMetrics={featureMetrics}
  // Optional: tiered cache stats from useTieredCache
  tieredCacheStats={cacheStats}
/>
```

When `tieredCacheStats` is provided, the dashboard shows:
- L1 (Memory) hit count
- L2 (Session) hit count
- Cache misses
- Cache age

---

## Completed: Integration Tests for Cache Mixin

**Status**: COMPLETE
**File**: `tests/integration/core/test_cache_mixin_redis.py`
**Tests**: 17 tests passing

**Test Categories**:

1. **TieredCacheMixin Basic Operations**:
   - `test_cache_set_and_get_with_redis` - Basic set/get flow
   - `test_cache_key_generation_is_deterministic` - Key consistency
   - `test_cache_get_returns_none_for_missing_key` - Cache miss handling
   - `test_cache_delete_removes_value` - Deletion verification
   - `test_cache_invalidate_prefix_removes_matching_keys` - Pattern invalidation
   - `test_cache_invalidate_user_removes_user_keys` - User-based invalidation
   - `test_cache_get_tiered_returns_data_from_l2` - L2 retrieval after L1 clear

2. **StaleWhileRevalidateMixin Operations**:
   - `test_swr_returns_fresh_data_on_miss` - Fresh fetch and cache
   - `test_swr_returns_cached_fresh_data` - Cache hit without refetch
   - `test_swr_detects_stale_data` - Stale data detection
   - `test_swr_timestamp_persists_in_redis` - `_cached_at` persistence

3. **Metrics Integration**:
   - `test_cache_get_with_metrics_tracks_hits` - Hit tracking
   - `test_cache_get_with_metrics_tracks_misses` - Miss tracking
   - `test_cache_get_observed_tracks_latency` - Latency histogram

4. **Error Handling**:
   - `test_cache_get_handles_connection_error_gracefully` - Graceful degradation
   - `test_cache_set_handles_serialization_error` - Unserializable value handling

5. **TTL Behavior**:
   - `test_cache_respects_ttl` - Expiration verification

**Prerequisites**:
- Redis running on `TEST_REDIS_PORT` (9379 by default)
- Tests auto-skip if Redis unavailable
- Uses isolated DB 15 for test isolation

---

## Future: Redis L2 Backend for Frontend Cross-Tab Caching

**Status**: PLANNED
**Priority**: MEDIUM
**Target**: Production environments

### Problem Statement

The current frontend `useTieredCache` hook uses:
- **L1**: In-memory Map (per-tab, fastest)
- **L2**: SessionStorage (per-tab, 5MB limit, lost on tab close)

This means:
1. Cache is **not shared across browser tabs** - each tab fetches independently
2. Cache is **lost on tab close** - users starting new sessions refetch everything
3. Cache is **limited to 5MB** - may fail on large datasets

### Proposed Solution

Add optional Redis L2 backend via API proxy:

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Browser)                        │
├─────────────────────────────────────────────────────────────┤
│  L1: In-Memory Map (fastest, per-tab)                       │
├─────────────────────────────────────────────────────────────┤
│  L2 Option A: SessionStorage (default, per-tab, offline)    │
│  L2 Option B: Redis via API (production, cross-tab, shared) │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ (L2 Option B only)
┌─────────────────────────────────────────────────────────────┐
│             POST /api/v1/cache/{operation}                   │
│             - GET /api/v1/cache/{key}                        │
│             - PUT /api/v1/cache/{key}                        │
│             - DELETE /api/v1/cache/{key}                     │
│             - DELETE /api/v1/cache/prefix/{prefix}           │
├─────────────────────────────────────────────────────────────┤
│                    Backend (FastAPI)                         │
├─────────────────────────────────────────────────────────────┤
│                    Redis (shared L2)                         │
│             - User-scoped keys: cache:user:{id}:{key}       │
│             - TTL enforcement                                │
│             - Circuit breaker + retry                        │
└─────────────────────────────────────────────────────────────┘
```

### API Endpoints

```python
# src/mcp_server_langgraph/api/v1/frontend_cache.py

from fastapi import APIRouter, Depends
from mcp_server_langgraph.core.cache import get_cache, CacheService
from mcp_server_langgraph.auth.dependencies import get_current_user

frontend_cache_router = APIRouter(prefix="/cache", tags=["frontend-cache"])

@frontend_cache_router.get("/{key}")
async def get_cached_value(
    key: str,
    cache: CacheService = Depends(get_cache),
    user: User = Depends(get_current_user),
) -> CacheResponse:
    """Get cached value for frontend (user-scoped)."""
    full_key = f"frontend:{user.id}:{key}"
    value = await cache.aget(full_key)
    return CacheResponse(key=key, value=value, hit=value is not None)

@frontend_cache_router.put("/{key}")
async def set_cached_value(
    key: str,
    request: CacheSetRequest,
    cache: CacheService = Depends(get_cache),
    user: User = Depends(get_current_user),
) -> CacheResponse:
    """Set cached value for frontend (user-scoped)."""
    full_key = f"frontend:{user.id}:{key}"
    await cache.aset(full_key, request.value, ttl=request.ttl_seconds or 300)
    return CacheResponse(key=key, success=True)

@frontend_cache_router.delete("/{key}")
async def delete_cached_value(
    key: str,
    cache: CacheService = Depends(get_cache),
    user: User = Depends(get_current_user),
) -> CacheResponse:
    """Delete cached value for frontend."""
    full_key = f"frontend:{user.id}:{key}"
    await cache.adelete(full_key)
    return CacheResponse(key=key, success=True)

@frontend_cache_router.delete("/prefix/{prefix}")
async def invalidate_prefix(
    prefix: str,
    cache: CacheService = Depends(get_cache),
    user: User = Depends(get_current_user),
) -> CacheInvalidateResponse:
    """Invalidate all keys matching prefix."""
    pattern = f"frontend:{user.id}:{prefix}:*"
    count = await cache.adelete_pattern(pattern)
    return CacheInvalidateResponse(prefix=prefix, deleted_count=count)
```

### Frontend Hook Update

```typescript
// src/hooks/useTieredCache.ts

export interface UseTieredCacheOptions {
  ttlMs?: number;
  staleThresholdMs?: number;
  enabled?: boolean;
  deduplicate?: boolean;
  /** Use Redis L2 via API instead of sessionStorage */
  useRedisL2?: boolean;
}

// L2 Redis adapter
async function getFromRedisL2<T>(key: string): Promise<CacheEntry<T> | null> {
  try {
    const response = await fetch(`/api/v1/cache/${encodeURIComponent(key)}`);
    if (!response.ok) return null;
    const data = await response.json();
    return data.hit ? data.value : null;
  } catch {
    return null; // Fallback to sessionStorage
  }
}

async function setToRedisL2<T>(key: string, entry: CacheEntry<T>, ttlMs: number): Promise<void> {
  try {
    await fetch(`/api/v1/cache/${encodeURIComponent(key)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        value: entry,
        ttl_seconds: Math.floor(ttlMs / 1000),
      }),
    });
  } catch {
    // Fallback to sessionStorage on error
    setToSessionL2(key, entry);
  }
}
```

### Feature Flag

```typescript
// Enable Redis L2 based on feature flag
const { useRedisL2 } = useFeatureFlags();

const { data, isLoading } = useTieredCache(
  "my:cache:key",
  () => fetchData(),
  {
    ttlMs: 300000,
    useRedisL2: useRedisL2, // From feature flag
  }
);
```

### Configuration

```yaml
# Feature flag default values
enable_frontend_redis_cache: false  # Opt-in for production
frontend_cache_ttl_seconds: 300     # 5 minute default
frontend_cache_prefix: "frontend"   # Redis key prefix
```

### Benefits

| Benefit | Description |
|---------|-------------|
| **Cross-Tab Sharing** | All browser tabs share cached data, reducing API load |
| **Session Persistence** | Cache survives tab close, browser restart |
| **Larger Capacity** | Redis can store much more than 5MB sessionStorage limit |
| **Centralized Metrics** | Backend Prometheus metrics for frontend cache patterns |
| **Consistent Invalidation** | Backend can invalidate frontend cache on data changes |

### Security Considerations

1. **User-Scoped Keys**: All cache keys prefixed with user ID to prevent cross-user data leakage
2. **Authentication Required**: All endpoints require valid auth token
3. **Rate Limiting**: Apply rate limits to prevent cache flooding
4. **TTL Enforcement**: Maximum TTL enforced server-side (e.g., 1 hour)
5. **Value Size Limits**: Maximum value size to prevent memory exhaustion

### Implementation Phases

| Phase | Scope | Effort |
|-------|-------|--------|
| **Phase 1** | API endpoints + tests | 1-2 days |
| **Phase 2** | Frontend hook update | 1 day |
| **Phase 3** | Feature flag + metrics | 0.5 days |
| **Phase 4** | Production rollout | 1 day |

### Rollout Strategy

1. **Alpha**: Enable for admin users only
2. **Beta**: Enable for developer personas (alice-*)
3. **GA**: Enable for all production users
4. **Monitoring**: Track cache hit rates, latency, errors

### Metrics

```prometheus
# Backend metrics
frontend_cache_requests_total{operation="get|set|delete", hit="true|false"}
frontend_cache_latency_seconds{operation="get|set|delete"}
frontend_cache_errors_total{operation="get|set|delete", error_type="..."}

# Frontend metrics (via useAICacheMetrics)
frontend_cache_l2_redis_hits
frontend_cache_l2_redis_misses
frontend_cache_l2_fallback_to_session
```

### Decision: When to Use Redis L2

| Scenario | Recommendation |
|----------|----------------|
| Development/localhost | SessionStorage (simpler, no API calls) |
| Preview environments | SessionStorage (isolated testing) |
| Production (single-tab users) | SessionStorage (lower latency) |
| Production (multi-tab power users) | Redis L2 (cross-tab sharing) |
| Large dataset caching | Redis L2 (no 5MB limit) |

### Dependencies

- Redis already deployed (used by backend CacheService)
- Feature flags system operational
- Authentication working for API calls
- Rate limiter configured
