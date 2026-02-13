# Troubleshooting

Database troubleshooting, monitoring, and example session for PostgreSQL operations.

---

## Issue: Cannot connect to database

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

---

## Issue: Backup fails

**Check disk space**:
```bash
df -h .
```

**Check backups directory exists**:
```bash
mkdir -p backups
# Unix/macOS only - Windows users can skip this step
chmod 755 backups
```

**Check PostgreSQL container is healthy**:
```bash
docker compose ps postgres
docker compose logs postgres
```

---

## Issue: Restore fails

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

---

## Issue: Database corrupted

**Nuclear option - fresh start**:
```bash
# DESTROYS ALL DATA - backup first!

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

## Database Monitoring

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

## Example Session

```
User: /db-operations backup

Claude:
Creating database backup...

Executing: make db-backup

Creating database backup...
Backup created in backups/

Backup Details:
- File: backups/openfga_backup_20251021_143022.sql
- Size: 2.4 MB
- Database: openfga
- Tables: 12
- Timestamp: 2025-10-21 14:30:22

Backup includes:
- OpenFGA stores (3)
- Authorization models (5)
- Tuples (1,247)
- All table schemas

To restore this backup:
make db-restore

To verify backup:
ls -lh backups/openfga_backup_20251021_143022.sql
```
