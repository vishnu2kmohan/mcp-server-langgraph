# Database Operations

**Usage**: `/db-operations` or `/db-operations <action>`

**Purpose**: Manage PostgreSQL database operations for OpenFGA and application data

**Actions**:
- `shell` - Access database shell
- `backup` - Create database backup
- `restore` - Restore from backup
- `migrate` - Run migrations

---

## 📊 Database Overview

The MCP Server LangGraph uses PostgreSQL for:
- **OpenFGA data**: Authorization tuples and models
- **Session data**: (if configured for PostgreSQL backend)
- **Application state**: Persistent storage

**Connection Details**:
- Host: `localhost`
- Port: `5432`
- Database: `openfga`
- User: `postgres`
- Container: `postgres` (via docker-compose)

---

## 🔧 Database Operations

### Access Database Shell

Open PostgreSQL interactive shell:

```bash
make db-shell
```

**What it does**:
- Connects to PostgreSQL container
- Opens `psql` interactive shell
- Connected to `openfga` database

**Example session**:
```sql
openfga=# \dt
-- List all tables

openfga=# SELECT * FROM store;
-- View OpenFGA stores

openfga=# \d authorization_model
-- Describe authorization_model table

openfga=# \q
-- Quit
```

**Common psql commands**:
- `\dt` - List tables
- `\d table_name` - Describe table
- `\l` - List databases
- `\du` - List users
- `\q` - Quit

---

### Create Database Backup

Create timestamped backup:

```bash
make db-backup
```

**What it does**:
- Creates `backups/` directory if needed
- Dumps database to SQL file
- Filename: `openfga_backup_YYYYMMDD_HHMMSS.sql`
- Includes all tables, data, and schema

**Example**:
```
Creating database backup...
✓ Backup created in backups/

Backup file: backups/openfga_backup_20251021_143022.sql
Size: 2.4 MB
```

**Backup includes**:
- All OpenFGA stores
- Authorization models
- Tuples (user-role-resource relationships)
- Configuration data

**Storage location**: `./backups/`

**Retention**: Manual cleanup (keep critical backups)

---

### Restore from Backup

Restore database from backup file:

```bash
make db-restore
```

**What it does**:
- Lists available backups (by date, newest first)
- Prompts for confirmation
- Restores from latest backup
- **⚠️ Overwrites current database**

**Interactive process**:
```
⚠️  This will restore from the latest backup
backups/openfga_backup_20251021_143022.sql
Continue? (y/n)
```

**Important**:
- ⚠️ **Destructive operation** - backs up current state first
- Creates automatic backup before restore
- Requires confirmation (y/n)
- Can be cancelled with Ctrl+C

**To restore specific backup**:
```bash
# List backups
ls -lt backups/*.sql | head -5

# Restore manually
docker compose exec -T postgres psql -U postgres -d openfga < backups/openfga_backup_YYYYMMDD_HHMMSS.sql
```

---

### Run Database Migrations

Execute pending migrations:

```bash
make db-migrate
```

**Status**: ⚠️ Placeholder (not yet implemented)

**Future implementation**:
- Will run database schema migrations
- For application schema evolution
- Safe, versioned migrations

**Current**:
```
Running database migrations...
⚠️  No migrations configured yet
This target is a placeholder for future database migration scripts
```

**When migrations are added**:
- Alembic or similar migration tool
- Version-controlled schema changes
- Safe upgrade/downgrade paths

---

## 🛡️ Safety & Best Practices

### Before Major Changes

**Always backup before**:
- Changing OpenFGA authorization model
- Updating application schema
- Bulk data modifications
- Restoring from old backup

```bash
# 1. Create backup
make db-backup

# 2. Make changes
# ... your changes ...

# 3. Verify
make db-shell
# Check data integrity
```

### Backup Strategy

**Recommended schedule**:
- **Before deployments**: Always
- **After significant data changes**: Always
- **Daily**: Production environments
- **Before restore operations**: Automatic

**Backup retention**:
```bash
# Keep last 7 days
find backups/ -name "*.sql" -mtime +7 -delete

# Keep last 10 backups
ls -t backups/*.sql | tail -n +11 | xargs rm
```

### Disaster Recovery

**If database is corrupted**:

1. **Stop services**:
   ```bash
   docker compose stop
   ```

2. **Restore from latest backup**:
   ```bash
   make db-restore
   ```

3. **Restart services**:
   ```bash
   docker compose start
   ```

4. **Verify**:
   ```bash
   make health-check
   make test-auth
   ```

---

## 📋 Common Database Tasks

### Check Database Size

```bash
make db-shell

# In psql:
SELECT pg_size_pretty(pg_database_size('openfga'));
```

### View OpenFGA Stores

```bash
make db-shell

# In psql:
SELECT id, name, created_at FROM store;
```

### Count Authorization Tuples

```bash
make db-shell

# In psql:
SELECT store_id, COUNT(*)
FROM tuple
GROUP BY store_id;
```

### Check Table Sizes

```bash
make db-shell

# In psql:
SELECT
    relname as table_name,
    pg_size_pretty(pg_total_relation_size(relid)) as size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

### Export Specific Table

```bash
# Export tuples table
docker compose exec -T postgres pg_dump -U postgres -d openfga -t tuple > tuples_backup.sql
```

---

## 🔍 Troubleshooting

### Issue: Cannot connect to database

**Check if PostgreSQL is running**:
```bash
docker compose ps postgres

# If not running:
docker compose up -d postgres
```

**Check connection**:
```bash
docker compose exec postgres pg_isready -U postgres
```

### Issue: Backup fails

**Check disk space**:
```bash
df -h .
```

**Check backups directory exists**:
```bash
mkdir -p backups
chmod 755 backups
```

**Check PostgreSQL container is healthy**:
```bash
docker compose ps postgres
docker compose logs postgres
```

### Issue: Restore fails

**Common causes**:
- Database doesn't exist (should be auto-created)
- Backup file corrupted
- Insufficient permissions

**Debug**:
```bash
# Check backup file is valid SQL
head -20 backups/openfga_backup_*.sql

# Verify file size (should be > 0)
ls -lh backups/

# Try manual restore with verbose output
docker compose exec -T postgres psql -U postgres -d openfga -v ON_ERROR_STOP=1 < backups/your_backup.sql
```

### Issue: Database corrupted

**Nuclear option - fresh start**:
```bash
# ⚠️ DESTROYS ALL DATA - backup first!

# Stop all services
docker compose down

# Remove database volume
docker volume rm mcp-server-langgraph_postgres_data

# Start fresh
docker compose up -d postgres

# Re-run OpenFGA setup
make setup-openfga
```

---

## 💾 Backup Automation

### Automated Daily Backups (Cron)

Add to crontab:
```bash
crontab -e

# Add line:
0 2 * * * cd /path/to/mcp-server-langgraph && make db-backup
```

This backs up database at 2 AM daily.

### Pre-deployment Hook

Add to deployment script:
```bash
#!/bin/bash
# deploy.sh

# Backup before deployment
make db-backup

# Deploy
make deploy-production

# Verify
make health-check
```

---

## 🔗 Related Commands

- `/setup-env` - Initial database setup
- `/debug-auth` - Debug authorization (uses database)
- `/health-check` - Verify database connectivity

---

## 📊 Database Monitoring

### Monitor via Grafana

OpenFGA dashboard shows database metrics:
```bash
make monitoring-dashboard
```

Navigate to OpenFGA dashboard for:
- Query performance
- Connection pool usage
- Table sizes
- Slow queries

### Check Database Health

```bash
make health-check
```

Includes PostgreSQL health check (port 5432).

---

## 📝 Example Session

```
User: /db-operations backup

Claude:
Creating database backup...

Executing: make db-backup

Creating database backup...
✓ Backup created in backups/

Backup Details:
- File: backups/openfga_backup_20251021_143022.sql
- Size: 2.4 MB
- Database: openfga
- Tables: 12
- Timestamp: 2025-10-21 14:30:22

Backup includes:
✓ OpenFGA stores (3)
✓ Authorization models (5)
✓ Tuples (1,247)
✓ All table schemas

To restore this backup:
make db-restore

To verify backup:
ls -lh backups/openfga_backup_20251021_143022.sql
```

---

## ⚠️ Important Warnings

**Database Operations Are Sensitive**:
- ❌ **Never run** `db-restore` on production without backup
- ❌ **Never delete** backups without verifying newer backups exist
- ❌ **Never modify** database directly without understanding impact
- ✅ **Always backup** before major changes
- ✅ **Always test** restore process periodically
- ✅ **Always verify** data integrity after restore

**Production Guidelines**:
- Test all operations in development first
- Keep multiple backup generations
- Document all manual database changes
- Use migrations for schema changes
- Monitor database performance
- Have rollback plan ready

---

**Last Updated**: 2025-10-21
**Command Version**: 1.0
**Database**: PostgreSQL 14+
**Container**: docker-compose postgres service
