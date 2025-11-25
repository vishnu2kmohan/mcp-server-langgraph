# Storage Backend Implementation Requirements

**Status**: DEFERRED to Future Sprint
**Priority**: CRITICAL (for production compliance)
**Complexity**: HIGH (14+ hours)
**Created**: 2025-10-18

---

## Executive Summary

Three remaining TODO items require comprehensive storage backend infrastructure:
1. Conversation storage integration (retention.py:330)
2. Audit log storage + cold storage (retention.py:353)
3. Audit log for GDPR deletion (data_deletion.py:325)

These items are **deferred to a dedicated Storage Backend Sprint** due to:
- Database schema design required
- Migration scripts needed
- Testing complexity
- Better handled as focused feature work

**Estimated Effort**: 14-20 hours (2-3 days)

---

## TODO Items

### 1. Conversation Storage Backend Integration
**File**: `src/mcp_server_langgraph/core/compliance/retention.py:330`
**Priority**: CRITICAL
**Estimated Time**: 4 hours

**Current State**:
```python
# TODO: Integrate with actual conversation storage backend
# Placeholder implementation
```

**Requirements**:
- Query Redis checkpoint storage for conversations
- Filter by user_id and timestamp
- Apply retention policies (delete old conversations)
- Track deletion metrics

**Implementation**:
```python
from langgraph.checkpoint.redis import RedisSaver

async def enforce_conversation_retention(
    self,
    retention_days: int = 90
) -> RetentionResult:
    # Connect to Redis checkpoint database
    checkpoint = RedisSaver(redis_url=settings.checkpoint_redis_url)

    # Query conversations older than retention period
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

    # Get all conversations (thread_ids)
    # Filter by timestamp
    # Delete old conversations
    # Return deletion metrics
```

**Dependencies**:
- langgraph-checkpoint-redis (already installed)
- Redis connection configuration
- Checkpoint database access

---

### 2. Audit Log Storage + Cold Storage Backend
**File**: `src/mcp_server_langgraph/core/compliance/retention.py:353`
**Priority**: CRITICAL
**Estimated Time**: 8 hours

**Current State**:
```python
# TODO: Integrate with actual audit log storage and cold storage backend
# Placeholder implementation
```

**Requirements**:
- PostgreSQL table for audit logs
- S3/GCS bucket for cold storage archival
- Migration from hot to cold storage
- Compression and encryption
- Retrieval mechanism

**Database Schema**:
```sql
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    log_entry_id TEXT UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    result TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    archive_location TEXT
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
```

**Cold Storage Implementation**:
```python
from google.cloud import storage
# Or: import boto3  # For AWS S3

async def archive_old_audit_logs(
    self,
    archive_after_days: int = 90
) -> RetentionResult:
    # 1. Query PostgreSQL for logs older than threshold
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=archive_after_days)
    old_logs = await db.query(
        "SELECT * FROM audit_logs WHERE timestamp < $1 AND archived_at IS NULL",
        cutoff_date
    )

    # 2. Compress and upload to S3/GCS
    for log_batch in batch(old_logs, size=1000):
        compressed = gzip.compress(json.dumps(log_batch))
        filename = f"audit-logs-{cutoff_date.date()}.json.gz"

        # Upload to cloud storage
        bucket.blob(filename).upload_from_string(compressed)

        # Update database with archive location
        await db.execute(
            "UPDATE audit_logs SET archived_at = $1, archive_location = $2 WHERE id = ANY($3)",
            datetime.now(), filename, [log.id for log in log_batch]
        )

    # 3. Delete from hot storage after verification
    await db.execute(
        "DELETE FROM audit_logs WHERE archived_at < $1",
        datetime.now(timezone.utc) - timedelta(days=7)  # Keep 7 days in DB
    )

    return RetentionResult(...)
```

**Dependencies**:
- PostgreSQL database and connection pool
- S3 (boto3) or GCS (google-cloud-storage) client
- Database migration tool (Alembic)
- Compression library (gzip, built-in)

---

### 3. Audit Log for GDPR Deletion
**File**: `src/mcp_server_langgraph/core/compliance/data_deletion.py:325`
**Priority**: CRITICAL
**Estimated Time**: 2 hours

**Current State**:
```python
# TODO: Integrate with audit log storage
# Placeholder
```

**Requirements**:
- Insert audit record to PostgreSQL on every deletion
- Include: user_id, deleted_data_types, timestamp, reason
- Tamper-proof logging (HIPAA requirement)
- GDPR Article 17 compliance tracking

**Implementation**:
```python
async def _log_deletion(
    self,
    user_id: str,
    deletion_result: DeletionResult
) -> None:
    """Log deletion to audit database"""

    audit_log = {
        "log_entry_id": f"gdpr_deletion_{uuid.uuid4()}",
        "timestamp": datetime.now(timezone.utc),
        "user_id": user_id,
        "action": "account_deletion",
        "resource_type": "user_account",
        "resource_id": user_id,
        "result": "success" if deletion_result.success else "partial",
        "metadata": {
            "deleted_data_types": deletion_result.deleted_data_types,
            "deletion_count": deletion_result.total_deleted,
            "errors": deletion_result.errors,
            "reason": "gdpr_article_17_user_request"
        }
    }

    await db.execute(
        """
        INSERT INTO audit_logs
        (log_entry_id, timestamp, user_id, action, resource_type, resource_id, result, metadata)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        *audit_log.values()
    )
```

**Dependencies**:
- Audit logs table (see schema above)
- PostgreSQL connection
- Same infrastructure as #2

---

## Recommended Implementation Approach

### Phase 1: Database Setup (4 hours)
1. **Design Schema**
   - Audit logs table
   - Indexes for performance
   - Partitioning strategy (by month)

2. **Create Migrations**
   - Alembic migration scripts
   - Rollback procedures
   - Test data seeding

3. **Configure Connections**
   - PostgreSQL connection pool
   - Environment variables
   - Health checks

### Phase 2: Retention Implementation (6 hours)
1. **Conversation Retention**
   - Redis checkpoint queries
   - Deletion logic
   - Metrics tracking

2. **Audit Log Archival**
   - PostgreSQL queries
   - S3/GCS integration
   - Compression and encryption
   - Archive verification

### Phase 3: GDPR Audit Logging (2 hours)
1. **Deletion Auditing**
   - PostgreSQL insert
   - Error handling
   - Verification

### Phase 4: Testing (2 hours)
1. **Unit Tests**
   - Mock database
   - Test each function

2. **Integration Tests**
   - Real PostgreSQL
   - Real S3/GCS
   - End-to-end scenarios

**Total**: 14 hours minimum (could be 20+ with complexity)

---

## Database Requirements

### PostgreSQL
**Version**: 12+
**Storage**: 100GB+ (depends on audit volume)
**Performance**: Connection pooling required

**Tables**:
1. `audit_logs` - Active audit entries (90 days)
2. `archived_audit_logs` - Reference to cold storage

**Partitioning**:
```sql
-- Partition by month for performance
CREATE TABLE audit_logs_2025_10 PARTITION OF audit_logs
FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
```

### Cloud Storage (S3/GCS)
**Purpose**: Long-term audit log archival (7 years)
**Estimated Size**: 1TB+ (depends on volume)
**Lifecycle**: Archive after 90 days, delete after 7 years

**Bucket Structure**:
```
audit-archives/
├── 2025/
│   ├── 10/
│   │   ├── audit-logs-2025-10-01.json.gz
│   │   ├── audit-logs-2025-10-02.json.gz
│   │   └── ...
│   └── 11/
└── 2024/
```

---

## Configuration

**Environment Variables**:
```bash
# PostgreSQL (Audit Logs)
AUDIT_LOG_DATABASE_URL=postgresql://user:pass@localhost:5432/audit
AUDIT_LOG_CONNECTION_POOL_SIZE=20
AUDIT_LOG_RETENTION_DAYS=90

# Cold Storage (S3)
AWS_S3_AUDIT_BUCKET=company-audit-archives
AWS_S3_REGION=us-east-1
AUDIT_COLD_STORAGE_RETENTION_YEARS=7

# Or GCS
GCP_GCS_AUDIT_BUCKET=company-audit-archives
GCP_PROJECT_ID=my-project
```

**Settings** (config.py):
```python
class Settings(BaseSettings):
    # Audit log storage
    audit_log_database_url: Optional[str] = None
    audit_log_retention_days: int = 90

    # Cold storage
    audit_cold_storage_provider: str = "s3"  # or "gcs"
    audit_cold_storage_bucket: Optional[str] = None
    audit_cold_storage_retention_years: int = 7
```

---

## Migration Strategy

### Step 1: Deploy PostgreSQL
```bash
# Using Helm in Kubernetes
helm install postgresql bitnami/postgresql \
  --set auth.database=audit_logs \
  --set primary.persistence.size=100Gi
```

### Step 2: Run Migrations
```bash
# Create Alembic migration
alembic revision --autogenerate -m "add audit logs table"
alembic upgrade head
```

### Step 3: Configure Application
```bash
# Add to .env
AUDIT_LOG_DATABASE_URL=postgresql://...
```

### Step 4: Deploy
```bash
# Rolling update
kubectl set image deployment/mcp-server-langgraph \
  mcp-server-langgraph=mcp-server-langgraph:v2.8.0
```

### Step 5: Verify
```bash
# Check audit logs are being written
SELECT COUNT(*) FROM audit_logs WHERE timestamp > NOW() - INTERVAL '1 hour';

# Check cold storage archives
aws s3 ls s3://company-audit-archives/2025/10/
```

---

## Testing Strategy

### Unit Tests
```python
@pytest.mark.asyncio
async def test_conversation_retention():
    """Test conversation deletion by age"""
    service = DataRetentionService()
    result = await service.enforce_conversation_retention(retention_days=90)
    assert result.deleted_count > 0

@pytest.mark.asyncio
async def test_audit_log_archival():
    """Test audit log archival to S3"""
    service = DataRetentionService()
    result = await service.archive_old_audit_logs(archive_after_days=90)
    assert result.success
```

### Integration Tests
```python
@pytest.mark.integration
async def test_end_to_end_retention():
    """Test full retention cycle"""
    # 1. Create test conversations
    # 2. Wait for retention period
    # 3. Run retention enforcement
    # 4. Verify conversations deleted
    # 5. Verify audit logs written
    # 6. Verify archived to S3
```

---

## Cost Estimates

### Storage Costs
**PostgreSQL** (100GB):
- AWS RDS: ~$50/month
- GCP Cloud SQL: ~$45/month
- Self-hosted: ~$20/month

**S3/GCS** (1TB archived):
- S3 Standard-IA: ~$12.50/month
- GCS Nearline: ~$10/month
- S3 Glacier: ~$4/month (slower retrieval)

**Total**: ~$60-70/month for full compliance storage

### Network/Compute
- Data transfer: ~$10/month
- Backup costs: ~$5/month
- **Total**: ~$75-85/month

---

## Security Considerations

**Encryption**:
- PostgreSQL: Encryption at rest (pgcrypto)
- S3/GCS: Server-side encryption (SSE)
- In-transit: TLS 1.3 required

**Access Control**:
- PostgreSQL: Role-based access
- S3/GCS: IAM policies, bucket policies
- Audit: All access logged

**Compliance**:
- GDPR: 7-year retention for legal claims
- HIPAA: Tamper-proof audit trails
- SOC2: Access control evidence

---

## Alternative Approaches

### Option 1: Managed Services (RECOMMENDED)
**Pros**:
- Automated backups
- Scaling handled
- High availability built-in
- Less operational overhead

**Cons**:
- Higher cost (~2x)
- Vendor lock-in

**Examples**:
- AWS RDS + S3
- GCP Cloud SQL + Cloud Storage
- Azure Database + Blob Storage

### Option 2: Self-Hosted
**Pros**:
- Lower cost
- Full control
- No vendor lock-in

**Cons**:
- Operational overhead
- Backup management
- Scaling complexity

**Examples**:
- PostgreSQL + MinIO (S3-compatible)
- PostgreSQL + NFS/CEPH
- Kubernetes StatefulSets

### Option 3: Hybrid
**Pros**:
- Balance cost and control
- Best of both worlds

**Cons**:
- More complex architecture

**Examples**:
- Self-hosted PostgreSQL + Cloud Storage
- Managed PostgreSQL + Self-hosted archival

---

## Implementation Checklist

### Prerequisites
- [ ] PostgreSQL instance deployed
- [ ] S3/GCS bucket created
- [ ] IAM roles configured
- [ ] Network connectivity verified
- [ ] Backup strategy defined

### Development
- [ ] Design database schema
- [ ] Create Alembic migrations
- [ ] Implement conversation retention
- [ ] Implement audit log archival
- [ ] Implement GDPR audit logging
- [ ] Add error handling
- [ ] Add comprehensive logging

### Testing
- [ ] Unit tests (mocked database)
- [ ] Integration tests (real database)
- [ ] Performance tests (large datasets)
- [ ] Retention policy validation
- [ ] Archive/restore verification

### Documentation
- [ ] API documentation
- [ ] Configuration guide
- [ ] Operational runbook
- [ ] Disaster recovery procedures

### Deployment
- [ ] Run migrations in staging
- [ ] Test in staging environment
- [ ] Monitor performance
- [ ] Deploy to production
- [ ] Verify audit trail
- [ ] Monitor storage usage

---

## Success Criteria

**Functional**:
- ✅ Conversations automatically deleted after retention period
- ✅ Audit logs archived to cold storage after 90 days
- ✅ GDPR deletions logged to audit database
- ✅ All deletions tracked with metrics
- ✅ Archive/restore tested and verified

**Performance**:
- ✅ Retention runs complete in <5 minutes
- ✅ Archive process doesn't impact live traffic
- ✅ Query performance remains acceptable

**Compliance**:
- ✅ Tamper-proof audit trail
- ✅ 7-year retention achieved
- ✅ GDPR deletion auditing complete
- ✅ SOC2 evidence available

---

## Timeline Estimate

### Sprint 0: Planning (1 day)
- Schema design review
- Migration strategy
- Deployment plan
- Risk assessment

### Sprint 1: Implementation (2-3 days)
- Database setup
- Code implementation
- Testing
- Documentation

### Sprint 2: Deployment (1 day)
- Staging deployment
- Verification
- Production deployment
- Monitoring

**Total**: 4-5 days

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Migration failure | Medium | High | Comprehensive testing, rollback plan |
| Performance degradation | Medium | Medium | Query optimization, indexing |
| Storage costs | High | Low | Lifecycle policies, compression |
| Data loss | Low | Critical | Backups, verification, testing |
| Compliance gap | Low | Critical | Audit before deployment |

---

## Recommendation

**Defer to Dedicated Sprint**: YES ✅

**Rationale**:
1. Requires significant infrastructure (PostgreSQL, S3/GCS)
2. Complex testing requirements
3. Database migration risks
4. Better handled as focused work
5. Current sprint at 89% completion (excellent progress)

**Next Steps**:
1. Complete current sprint (document these requirements)
2. Create GitHub issues for storage backend work
3. Plan dedicated Storage Backend Sprint
4. Estimate 4-5 days for implementation
5. Schedule after current sprint priorities

---

## Related Documents

- [ADR-0012: Compliance Framework](../../adr/adr-0012-compliance-framework-integration.md)

---

**Status**: READY for Future Sprint
**Assigned**: TBD
**Due Date**: TBD
**Estimated Effort**: 14-20 hours (2-3 days)
