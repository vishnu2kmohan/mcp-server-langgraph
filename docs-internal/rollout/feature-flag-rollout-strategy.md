# Feature Flag Rollout Strategy

## Overview

This document outlines the rollout strategy for new features added during the comprehensive audit (Phases 1-4). All features are behind feature flags for safe, gradual deployment.

## Audit-Related Feature Flags

| Flag | Default | Risk | Priority |
|------|---------|------|----------|
| `enable_multi_tenant_isolation` | `false` | **Critical** | P0 |
| `enable_progressive_context_discovery` | `false` | Medium | P1 |
| `enable_semantic_skill_search` | `false` | Low | P2 |
| `enable_semantic_memory_retrieval` | `false` | Low | P2 |
| `enable_progressive_skill_loading` | `false` | Low | P2 |

## Rollout Phases

### Phase 1: Multi-Tenant Isolation (P0 - Security Critical)

**Flag:** `enable_multi_tenant_isolation`

**Pre-Requisites:**
- [ ] Staging environment with multiple test tenants
- [ ] All existing vectors have `tenant_id` in payload metadata
- [ ] Monitoring dashboards for cross-tenant query attempts

**Rollout Steps:**
1. Enable in development environment
2. Run integration tests with multi-tenant scenarios
3. Enable in staging with synthetic tenants
4. Verify no cross-tenant data leakage
5. Enable in production for new tenants first
6. Gradually migrate existing tenants

**Monitoring:**
```python
# Key metrics to monitor
- vector_search.tenant_filter_applied (counter)
- vector_search.tenant_mismatch_blocked (counter)
- semantic_search.latency_with_tenant_filter (histogram)
```

**Rollback Trigger:**
- Cross-tenant data access detected
- >10% increase in search latency
- Error rate >1%

---

### Phase 2: Progressive Context Discovery (P1)

**Flag:** `enable_progressive_context_discovery`

**What it does:**
- Enables iterative semantic search for complex queries
- Uses query complexity detection to route appropriately
- Falls back to simple semantic_search for simple queries

**Pre-Requisites:**
- [ ] Embedding service configured and healthy
- [ ] Token budget monitoring in place
- [ ] Baseline latency metrics captured

**Rollout Steps:**
1. Enable in development
2. Test with known complex queries (multi-entity, comparisons)
3. Enable in staging with 10% traffic
4. Monitor token usage and latency
5. Gradually increase to 100%

**Monitoring:**
```python
# Key metrics
- context.progressive_discover.iterations (histogram)
- context.progressive_discover.latency_ms (histogram)
- context.query_complexity.is_complex (counter)
```

**Rollback Trigger:**
- Average iterations > 5 (indicates runaway)
- Latency p99 > 5s
- Token usage > 2x baseline

---

### Phase 3: Semantic Skill Search (P2)

**Flag:** `enable_semantic_skill_search`

**What it does:**
- Stage 3/4 of ProgressiveSkillLoader
- Uses embeddings to find relevant skills by task description
- Fills remaining slots after explicit/default skills

**Pre-Requisites:**
- [ ] Skill embeddings indexed in vector store
- [ ] SkillSearchTool configured with embedding service
- [ ] Baseline skill loading metrics

**Rollout Steps:**
1. Enable in development
2. Verify skill discovery accuracy
3. Enable in staging
4. A/B test skill relevance vs baseline
5. Enable in production

**Monitoring:**
```python
# Key metrics
- skills.semantic_search.results_count (histogram)
- skills.semantic_search.min_score (histogram)
- skills.stage3_loaded (counter)
```

---

### Phase 4: Semantic Memory Retrieval (P2)

**Flag:** `enable_semantic_memory_retrieval`

**What it does:**
- Vector-based memory retrieval in MemoryStore
- Uses embeddings instead of keyword matching
- Requires embedding_service and vector_provider configuration

**Pre-Requisites:**
- [ ] Memory embeddings indexed
- [ ] EmbeddingServiceProtocol implementation configured
- [ ] VectorProviderProtocol implementation configured

**Rollout Steps:**
1. Enable in development
2. Compare retrieval quality vs keyword baseline
3. Enable in staging
4. Monitor memory retrieval latency
5. Enable in production

**Monitoring:**
```python
# Key metrics
- memory.semantic_search.score_distribution (histogram)
- memory.semantic_search.latency_ms (histogram)
- memory.keyword_fallback.count (counter)
```

---

## Environment Configuration

### Development
```bash
# .env.development
FF_ENABLE_MULTI_TENANT_ISOLATION=true
FF_ENABLE_PROGRESSIVE_CONTEXT_DISCOVERY=true
FF_ENABLE_SEMANTIC_SKILL_SEARCH=true
FF_ENABLE_SEMANTIC_MEMORY_RETRIEVAL=true
FF_ENABLE_PROGRESSIVE_SKILL_LOADING=true
```

### Staging (Gradual)
```bash
# .env.staging
FF_ENABLE_MULTI_TENANT_ISOLATION=true
FF_ENABLE_PROGRESSIVE_CONTEXT_DISCOVERY=true
FF_ENABLE_SEMANTIC_SKILL_SEARCH=false
FF_ENABLE_SEMANTIC_MEMORY_RETRIEVAL=false
```

### Production (Conservative)
```bash
# .env.production - start with all false
FF_ENABLE_MULTI_TENANT_ISOLATION=false
FF_ENABLE_PROGRESSIVE_CONTEXT_DISCOVERY=false
FF_ENABLE_SEMANTIC_SKILL_SEARCH=false
FF_ENABLE_SEMANTIC_MEMORY_RETRIEVAL=false
```

---

## Rollback Procedures

### Immediate Rollback
```bash
# Disable specific flag
export FF_ENABLE_<FLAG_NAME>=false
# Restart service
kubectl rollout restart deployment/mcp-server
```

### Graceful Rollback
1. Set flag to `false` in config
2. Deploy config change
3. Existing requests complete normally
4. New requests use fallback behavior

---

## Success Criteria

| Flag | Success Metric |
|------|---------------|
| Multi-tenant | Zero cross-tenant access, <5% latency increase |
| Progressive discovery | 20% improvement in complex query relevance |
| Semantic skill search | 15% improvement in skill match accuracy |
| Semantic memory | 25% improvement in memory retrieval relevance |

---

## Related ADRs

- **ADR-0092**: Hierarchical Capability Architecture
- **ADR-0095**: Multi-Tenant Vector Search Isolation

---

## Contact

For rollout coordination, contact the platform team.
