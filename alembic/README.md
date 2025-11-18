# Alembic Database Migrations

## Overview

This project uses **Alembic** for database schema migrations in production/development environments, and **direct SQL** for test environments to avoid asyncio conflicts.

## Database Architecture

### PostgreSQL Instance (Single)
Port: **9432** (test), **5432** (production)

### Databases

| Database | Purpose | Schema Management | Used By |
|----------|---------|------------------|---------|
| **mcp_test** | MCP application data (GDPR tables) | Direct SQL (`migrations/001_gdpr_schema.sql`) | Integration tests, E2E tests |
| **mcp_server** | Production MCP application data | Alembic migrations | Production deployments |
| **openfga_test** | OpenFGA authorization data | OpenFGA migrations (`openfga-migrate-test`) | OpenFGA service (test) |
| **keycloak_test** | Keycloak SSO data | Keycloak auto-migration | Keycloak service (test) |

## Migration Strategy

### Production/Development (Alembic)

**Use Alembic** for production deployments to maintain proper migration history and rollback capability.

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

**Environment Variables:**
- `DATABASE_URL`: Full PostgreSQL connection string (overrides all other settings)
- `POSTGRES_HOST`: PostgreSQL host (default: `localhost`)
- `POSTGRES_PORT`: PostgreSQL port (default: `5432`)
- `POSTGRES_USER`: PostgreSQL user (default: `postgres`)
- `POSTGRES_PASSWORD`: PostgreSQL password (default: `postgres`)
- `POSTGRES_DB`: Database name (default: `mcp_server`)

### Test Environment (Direct SQL)

**Use Direct SQL** via Docker init script to avoid `asyncio.run()` conflicts with pytest-asyncio.

**Automatic Initialization:**
When `docker-compose.test.yml` starts:
1. PostgreSQL container mounts `migrations/` to `/docker-entrypoint-initdb.d/`
2. Executes `000_init_databases.sh` which creates databases:
   - `mcp_test`
   - `openfga_test`
   - `keycloak_test`
3. Executes `001_gdpr_schema.sql` on `mcp_test` database

**Why Not Alembic for Tests?**

From `tests/integration/security/test_gdpr_schema_setup.py`:
```
OpenAI Codex Finding (2025-11-16):
====================================
Tests in test_sql_injection_gdpr.py failed with:
  asyncpg.exceptions.UndefinedTableError: relation "conversations" does not exist

Root cause: Alembic migrations use asyncio.run() which fails in pytest-asyncio context.
Exception was silently caught, schema never created.

Solution: Execute schema SQL directly using async connection, bypassing Alembic.
```

## Synchronization

**IMPORTANT**: Keep Alembic migrations and direct SQL in sync!

### Files to Update When Changing Schema

1. **Alembic migration** (production):
   - `alembic/versions/<revision>_description.py`
   - Created via: `alembic revision --autogenerate -m "description"`

2. **Direct SQL** (tests):
   - `migrations/001_gdpr_schema.sql`
   - Must manually mirror Alembic changes

3. **Test fixtures**:
   - `tests/conftest.py` - `db_pool_gdpr` fixture

### Schema Change Workflow

```bash
# 1. Update SQLAlchemy models (if using autogenerate)
# 2. Create Alembic migration
alembic revision --autogenerate -m "add_column_to_users"

# 3. Review and edit generated migration
vim alembic/versions/<revision>_add_column_to_users.py

# 4. Update direct SQL file to match
vim migrations/001_gdpr_schema.sql

# 5. Test locally
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d
make test-integration

# 6. Apply to production
alembic upgrade head
```

## Database URL Format

### Alembic (async)
```
postgresql+asyncpg://user:password@host:port/database
```

### Direct Connection (asyncpg)
```python
await asyncpg.create_pool(
    host="localhost",
    port=9432,
    user="postgres",
    password="postgres",
    database="mcp_test",
)
```

## Testing Database Initialization

```bash
# Verify GDPR schema tables exist
docker-compose -f docker-compose.test.yml up -d postgres-test
docker exec mcp-postgres-test psql -U postgres -d mcp_test -c "\dt"

# Should show:
#  user_profiles
#  user_preferences
#  consent_records
#  conversations
#  audit_logs
```

## Service-Specific Migrations

### OpenFGA
**Managed by:** OpenFGA's built-in migration system
**Migration Service:** `openfga-migrate-test` (in docker-compose.test.yml)
**Command:** `openfga migrate --datastore-engine=postgres --datastore-uri=...`

### Keycloak
**Managed by:** Keycloak automatically on startup
**No manual migrations needed** - Keycloak handles schema updates

## References

- Alembic Documentation: https://alembic.sqlalchemy.org
- Test Schema Setup: `tests/integration/security/test_gdpr_schema_setup.py`
- Direct SQL Migration: `migrations/001_gdpr_schema.sql`
- Init Script: `migrations/000_init_databases.sh`
- Test Fixtures: `tests/conftest.py` (line 1610: `db_pool_gdpr`)

## Troubleshooting

### "Table does not exist" in tests
**Cause:** Direct SQL not applied to `mcp_test` database
**Fix:** Check `migrations/000_init_databases.sh` executes successfully

### Alembic targets wrong database
**Cause:** Environment variables not set correctly
**Fix:** Set `POSTGRES_DB=mcp_server` for production, or `TESTING=true` for tests

### Migration version conflicts
**Cause:** Alembic history out of sync
**Fix:**
```bash
alembic current  # Check current version
alembic history  # Show all migrations
alembic stamp head  # Force set to latest (WARNING: only if DB schema matches!)
```

### Schema mismatch between Alembic and direct SQL
**Cause:** Files not kept in sync
**Fix:** Manually update `migrations/001_gdpr_schema.sql` to match latest Alembic migration
