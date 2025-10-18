# GDPR Storage Backend Configuration

## Overview

The GDPR compliance endpoints (`/api/v1/users/me/*`) require persistent storage to meet data subject rights requirements under GDPR Articles 15, 16, 17, 20, and 21.

**CRITICAL**: In-memory storage is **NOT production-ready** and will cause data loss on server restart, violating GDPR compliance requirements.

## Environment Variables

### Required Configuration

Set these environment variables in your production deployment:

```bash
# Required: Set environment to production
ENVIRONMENT=production

# Required: Choose persistent backend (postgres or redis)
GDPR_STORAGE_BACKEND=postgres  # or "redis"
```

### Development/Testing

For local development and testing only:

```bash
ENVIRONMENT=development
GDPR_STORAGE_BACKEND=memory
```

## Storage Backend Options

### Option 1: PostgreSQL (Recommended)

PostgreSQL provides ACID compliance and is ideal for GDPR data subject rights.

**Configuration:**

```bash
GDPR_STORAGE_BACKEND=postgres
GDPR_POSTGRES_URL=postgresql://user:pass@localhost:5432/gdpr_db
```

**Implementation Required:**

Currently, PostgreSQL integration is not yet implemented. To add support:

1. Create migrations for user profiles and consent records
2. Implement `PostgresConsentStore` in `src/mcp_server_langgraph/api/gdpr.py`
3. Replace `_consent_storage` dict with database queries

**Schema Example:**

```sql
CREATE TABLE user_profiles (
    user_id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    preferences JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE consent_records (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    consent_type VARCHAR(50) NOT NULL,
    granted BOOLEAN NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    UNIQUE(user_id, consent_type)
);

CREATE INDEX idx_consent_user_id ON consent_records(user_id);
```

### Option 2: Redis

Redis provides fast, persistent key-value storage suitable for consent management.

**Configuration:**

```bash
GDPR_STORAGE_BACKEND=redis
GDPR_REDIS_URL=redis://localhost:6379/2  # Use separate DB from sessions
```

**Implementation Required:**

1. Create `RedisConsentStore` class
2. Use Redis hashes for user profiles: `user:profile:{user_id}`
3. Use Redis hashes for consents: `user:consents:{user_id}`
4. Configure TTL if retention policies apply

**Example Implementation:**

```python
import redis
from typing import Dict, Any, Optional

class RedisConsentStore:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    def set_consent(self, user_id: str, consent_type: str, data: Dict[str, Any]):
        key = f"user:consents:{user_id}"
        self.redis.hset(key, consent_type, json.dumps(data))

    def get_consents(self, user_id: str) -> Dict[str, dict]:
        key = f"user:consents:{user_id}"
        consents = self.redis.hgetall(key)
        return {k.decode(): json.loads(v) for k, v in consents.items()}
```

## Production Guard

The application includes a runtime guard that **prevents startup** if:

```
ENVIRONMENT=production AND GDPR_STORAGE_BACKEND=memory
```

**Error Message:**

```
RuntimeError: CRITICAL: GDPR endpoints cannot use in-memory storage in production.
Set GDPR_STORAGE_BACKEND=postgres or GDPR_STORAGE_BACKEND=redis,
or set ENVIRONMENT=development for testing.
Data subject rights (GDPR compliance) require persistent storage.
```

## Migration Checklist

Before deploying GDPR endpoints to production:

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `GDPR_STORAGE_BACKEND=postgres` or `redis`
- [ ] Configure database connection strings
- [ ] Run database migrations (if PostgreSQL)
- [ ] Implement persistent storage integration
- [ ] Test data subject rights workflows
- [ ] Verify data is persisted across restarts
- [ ] Configure backup and retention policies
- [ ] Document data retention periods
- [ ] Update privacy policy with GDPR rights

## GDPR Compliance Requirements

### Data Retention

Configure retention policies based on your legal requirements:

```python
# Example: 90-day retention for consent records
CONSENT_RETENTION_DAYS=90
PROFILE_RETENTION_DAYS=365
```

### Audit Trail

All GDPR operations are logged with:

- User ID
- Operation type (access, rectification, erasure, etc.)
- Timestamp
- GDPR article (15, 16, 17, 20, 21)

**Log Example:**

```json
{
  "message": "User consent updated",
  "user_id": "user:alice",
  "consent_type": "analytics",
  "granted": true,
  "gdpr_article": "21",
  "timestamp": "2025-10-18T12:34:56Z"
}
```

### Data Deletion (Article 17)

When users exercise right to erasure:

1. User profile and preferences are **deleted**
2. Consent records are **deleted**
3. Audit logs are **anonymized** (user_id replaced with hash)
4. Sessions are **revoked**
5. Conversations are **deleted**

**Retention for Compliance:**

Some data may be retained for legal/compliance reasons:

- Anonymized audit logs (for GDPR compliance proof)
- Aggregated analytics (no PII)
- Financial records (tax law requirements)

## Testing

### Unit Tests

```bash
pytest tests/integration/test_gdpr_endpoints.py -v
```

### Integration Tests

Test with real database:

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Run integration tests
GDPR_STORAGE_BACKEND=postgres \
GDPR_POSTGRES_URL=postgresql://test:test@localhost:5432/test_db \
pytest tests/integration/test_gdpr_endpoints.py
```

### Production Guard Test

Verify production guard:

```bash
# Should fail
ENVIRONMENT=production GDPR_STORAGE_BACKEND=memory python -c "import mcp_server_langgraph.api.gdpr"

# Should succeed
ENVIRONMENT=production GDPR_STORAGE_BACKEND=postgres python -c "import mcp_server_langgraph.api.gdpr"
```

## Deployment Examples

### Docker Compose

```yaml
services:
  app:
    image: mcp-server-langgraph:latest
    environment:
      - ENVIRONMENT=production
      - GDPR_STORAGE_BACKEND=postgres
      - GDPR_POSTGRES_URL=postgresql://gdpr:${DB_PASSWORD}@postgres:5432/gdpr_db
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=gdpr_db
      - POSTGRES_USER=gdpr
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Kubernetes

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gdpr-config
data:
  ENVIRONMENT: "production"
  GDPR_STORAGE_BACKEND: "postgres"

---
apiVersion: v1
kind: Secret
metadata:
  name: gdpr-secrets
type: Opaque
stringData:
  GDPR_POSTGRES_URL: "postgresql://gdpr:password@postgres-service:5432/gdpr_db"
```

## Troubleshooting

### Error: "GDPR endpoints use in-memory storage"

**Cause:** GDPR_STORAGE_BACKEND not set or set to "memory"

**Solution:**

```bash
export GDPR_STORAGE_BACKEND=postgres
export GDPR_POSTGRES_URL=postgresql://...
```

### Error: "RuntimeError: CRITICAL: GDPR endpoints cannot use in-memory storage"

**Cause:** Running in production with memory backend

**Solution:** Change backend or environment:

```bash
# Option 1: Use persistent backend
export GDPR_STORAGE_BACKEND=postgres

# Option 2: Switch to development (NOT for production!)
export ENVIRONMENT=development
```

### Data Loss on Restart

**Cause:** Using in-memory storage in non-development environment

**Solution:** Migrate to PostgreSQL or Redis immediately

## References

- [GDPR Article 15: Right to Access](https://gdpr-info.eu/art-15-gdpr/)
- [GDPR Article 16: Right to Rectification](https://gdpr-info.eu/art-16-gdpr/)
- [GDPR Article 17: Right to Erasure](https://gdpr-info.eu/art-17-gdpr/)
- [GDPR Article 20: Right to Data Portability](https://gdpr-info.eu/art-20-gdpr/)
- [GDPR Article 21: Right to Object](https://gdpr-info.eu/art-21-gdpr/)

## Support

For implementation assistance:

1. Check existing issues: https://github.com/vishnu2kmohan/mcp-server-langgraph/issues
2. Create new issue with `gdpr` and `compliance` labels
3. Include environment details and error messages
