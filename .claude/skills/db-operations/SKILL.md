---
name: db-operations
description: Manage PostgreSQL database operations for OpenFGA and application data. Use for database shell access, backups, restores, and migrations.
allowed-tools:
  - Bash(docker ps:*)
  - Bash(docker inspect:*)
  - Bash(make:*)
  - Read
  - Glob
  - Grep
disable-model-invocation: true
---
# Database Operations

**Usage**: `/db-operations` or `/db-operations <action>`

**Purpose**: Manage PostgreSQL database operations for OpenFGA and application data

**Actions**:
- `shell` - Access database shell
- `backup` - Create database backup
- `restore` - Restore from backup
- `migrate` - Run migrations

---

## Database Overview

The MCP Server LangGraph uses PostgreSQL for:
- **OpenFGA data**: Authorization tuples and models
- **Session data**: (if configured for PostgreSQL backend)
- **Application state**: Persistent storage

**Connection Details**:
- Host: `localhost`
- Port: `5432`
- Database: `openfga`
- User: `postgres`
- Container: `postgres` (via docker compose)

---

## Core Operations

### Access Database Shell

Open PostgreSQL interactive shell:

```bash
make db-shell
```

Connects to the PostgreSQL container and opens `psql` against the `openfga` database.

**Common psql commands**:
- `\dt` - List tables
- `\d table_name` - Describe table
- `\l` - List databases
- `\du` - List users
- `\q` - Quit

For common query examples (database size, OpenFGA stores, tuples, table sizes, exports), read [references/query-reference.md](references/query-reference.md).

---

### Create Database Backup

Create timestamped backup:

```bash
make db-backup
```

- Creates `backups/` directory if needed
- Dumps database to SQL file: `openfga_backup_YYYYMMDD_HHMMSS.sql`
- Includes all tables, data, and schema (stores, authorization models, tuples, config)
- Storage location: `./backups/`
- Retention: Manual cleanup (keep critical backups)

For backup strategy, retention scripts, automation, and disaster recovery procedures, read [references/backup-procedures.md](references/backup-procedures.md).

---

### Restore from Backup

Restore database from backup file:

```bash
make db-restore
```

- Lists available backups (by date, newest first)
- Prompts for confirmation
- Restores from latest backup
- **WARNING: Overwrites current database**
- Creates automatic backup before restore
- Can be cancelled with Ctrl+C

**To restore a specific backup**:
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

**Status**: Placeholder (not yet implemented)

- Will run database schema migrations via Alembic or similar
- Version-controlled schema changes with safe upgrade/downgrade paths

Current output:
```
Running database migrations...
No migrations configured yet
This target is a placeholder for future database migration scripts
```

---

## Safety & Best Practices

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

---

## Related Commands

- `/setup-env` - Initial database setup
- `/debug-auth` - Debug authorization (uses database)
- `/health-check` - Verify database connectivity

---

## Important Warnings

**Database Operations Are Sensitive**:
- **Never run** `db-restore` on production without backup
- **Never delete** backups without verifying newer backups exist
- **Never modify** database directly without understanding impact
- **Always backup** before major changes
- **Always test** restore process periodically
- **Always verify** data integrity after restore

For troubleshooting connection issues, backup/restore failures, database corruption recovery, and monitoring, read [references/troubleshooting.md](references/troubleshooting.md).

---

**Last Updated**: 2025-10-21
**Database**: PostgreSQL 14+
**Container**: docker compose postgres service
