# ADR-0095: Multi-Tenant Vector Search Isolation

| Status | Accepted |
|--------|----------|
| Date | 2026-01-06 |
| Authors | Claude Opus 4.5 |
| Deciders | Backend Architecture, Security |
| Consulted | Compliance, Infrastructure |
| Informed | All Contributors |

## Context and Problem Statement

The `DynamicContextLoader` uses Qdrant for semantic search to inject relevant context into LLM prompts. However, in multi-tenant deployments, there's no isolation between tenants' data:

1. **Security Risk**: One tenant's semantic search could return another tenant's documents
2. **Compliance Violations**: HIPAA, GDPR, and SOC2 require strict data isolation
3. **Settings Mismatch**: `enable_multi_tenant_isolation` setting exists but isn't implemented

### Problem Statement

How do we ensure that semantic search results are properly scoped to the requesting tenant, preventing cross-tenant data leakage while maintaining search performance?

## Decision Drivers

1. **Security**: Prevent cross-tenant data access (CRITICAL)
2. **Compliance**: Meet HIPAA, GDPR, SOC2 data isolation requirements
3. **Performance**: Maintain fast vector search (Qdrant recommends payload filtering)
4. **Backward Compatibility**: Don't break existing single-tenant deployments
5. **Simplicity**: Use Qdrant's native multitenancy features

## Considered Options

### Option 1: Per-Tenant Collections

Create a separate Qdrant collection for each tenant.

**Pros:**
- Complete physical isolation
- Simple mental model

**Cons:**
- Collection management overhead (create/delete per tenant)
- Inefficient for many tenants (Qdrant not optimized for many small collections)
- Conflicts with Qdrant's multitenancy best practices

### Option 2: Payload Filtering with `is_tenant` Index (Recommended)

Use a single collection with `tenant_id` in payload and an indexed filter.

**Pros:**
- Follows Qdrant multitenancy best practices
- Efficient for large numbers of tenants
- No collection management overhead
- Supports Qdrant's `is_tenant` optimization (1.16+)

**Cons:**
- Requires filter on every query (minor overhead)
- Must ensure `tenant_id` is always included in upserts

## Decision

Implement **Option 2: Payload Filtering with `is_tenant` Index**.

### Implementation

#### 1. Collection Schema

Configure the `tenant_id` field with `is_tenant=True` for optimized filtering:

```python
from qdrant_client.models import PayloadSchemaType

# On collection creation/update
await client.create_payload_index(
    collection_name=collection_name,
    field_name="tenant_id",
    field_schema=PayloadSchemaType.KEYWORD,
    is_tenant=True,  # Qdrant 1.16+ optimization
)
```

#### 2. DynamicContextLoader Changes

Add mandatory `tenant_id` parameter to all search/load methods:

```python
async def semantic_search(
    self,
    query: str,
    tenant_id: str,  # NEW: Required for multi-tenant isolation
    top_k: int = 5,
    ref_type_filter: str | None = None,
    min_score: float = 0.5,
) -> list[ContextReference]:
    # ... existing code ...

    # Build filter with tenant isolation
    must_conditions = [
        FieldCondition(
            key="tenant_id",
            match=MatchValue(value=tenant_id),
        )
    ]

    if ref_type_filter:
        must_conditions.append(
            FieldCondition(
                key="ref_type",
                match=MatchValue(value=ref_type_filter),
            )
        )

    search_filter = Filter(must=must_conditions)

    # Search with tenant filter
    results = await client.search(
        collection_name=self.collection_name,
        query_vector=query_embedding,
        limit=top_k,
        query_filter=search_filter,
        score_threshold=min_score,
    )
```

#### 3. Context Ingestion

Ensure all upserts include `tenant_id`:

```python
async def upsert_context(
    self,
    content: str,
    tenant_id: str,  # Required
    ref_id: str | None = None,
    metadata: dict | None = None,
) -> str:
    payload = {
        "text": content,
        "tenant_id": tenant_id,  # Always include
        **(metadata or {}),
    }
    # ... upsert logic ...
```

#### 4. Settings Integration

Use existing `enable_multi_tenant_isolation` setting:

```python
# In DynamicContextLoader.__init__
self.enable_tenant_isolation = settings.enable_multi_tenant_isolation

# In semantic_search
if self.enable_tenant_isolation:
    if not tenant_id:
        raise ValueError("tenant_id required when multi-tenant isolation is enabled")
    # Add tenant filter
else:
    # Legacy mode: no tenant filtering (single-tenant deployments)
```

### Migration Path

1. **Phase 1**: Add `tenant_id` parameter (optional, defaults to None for backward compatibility)
2. **Phase 2**: Populate `tenant_id` on existing documents via backfill migration
3. **Phase 3**: Enable `enable_multi_tenant_isolation=True` in settings
4. **Phase 4**: Make `tenant_id` required (breaking change in major version)

## Consequences

### Positive

- **Security**: Complete data isolation between tenants
- **Compliance**: Meets HIPAA, GDPR, SOC2 requirements
- **Performance**: Qdrant's `is_tenant` optimization maintains fast search
- **Scalability**: Single collection scales to many tenants efficiently

### Negative

- **Migration Required**: Existing data needs `tenant_id` backfill
- **API Change**: Methods require `tenant_id` parameter
- **Complexity**: Filter construction slightly more complex

### Risks

- **Missed Tenant ID**: If upsert forgets `tenant_id`, document is inaccessible
- **Filter Bypass**: Direct Qdrant access could bypass tenant filter (mitigate via network policies)

## Related ADRs

- ADR-0094: KB Focus Mode (related context retrieval control)
- ADR-0006: Session Storage Architecture (tenant scoping patterns)

## References

- [Qdrant Multitenancy Guide](https://qdrant.tech/documentation/guides/multitenancy/)
- [Qdrant 1.16 Tiered Multitenancy](https://qdrant.tech/blog/qdrant-1.16.x/)
- HIPAA 45 CFR 164.312: Technical Safeguards for PHI Access Control
