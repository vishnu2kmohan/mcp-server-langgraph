# Backup Procedures

Backup strategy, retention, automation, disaster recovery, and production guidelines for PostgreSQL database operations.

---

## Backup Strategy

**Recommended schedule**:
- **Before deployments**: Always
- **After significant data changes**: Always
- **Daily**: Production environments
- **Before restore operations**: Automatic

**Backup retention**:
```bash
# Keep last 7 days
find backups/ -name "*.sql" -mtime +7 -delete

# Keep last 10 backups (cross-platform, handles filenames with spaces safely)
uv run --frozen python3 -c "
from pathlib import Path
import os
files = sorted(Path('backups').glob('*.sql'), key=os.path.getmtime, reverse=True)
for f in files[10:]:  # Keep 10 newest
    f.unlink()
"
```

---

## Disaster Recovery

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

## Backup Automation

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

## Production Guidelines

- Test all operations in development first
- Keep multiple backup generations
- Document all manual database changes
- Use migrations for schema changes
- Monitor database performance
- Have rollback plan ready
