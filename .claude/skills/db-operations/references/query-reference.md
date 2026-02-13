# Common Database Tasks

Reference queries for PostgreSQL database operations. All queries run inside `psql` after `make db-shell`.

---

## Check Database Size

```bash
make db-shell

# In psql:
SELECT pg_size_pretty(pg_database_size('openfga'));
```

---

## View OpenFGA Stores

```bash
make db-shell

# In psql:
SELECT id, name, created_at FROM store;
```

---

## Count Authorization Tuples

```bash
make db-shell

# In psql:
SELECT store_id, COUNT(*)
FROM tuple
GROUP BY store_id;
```

---

## Check Table Sizes

```bash
make db-shell

# In psql:
SELECT
    relname as table_name,
    pg_size_pretty(pg_total_relation_size(relid)) as size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

---

## Export Specific Table

```bash
# Export tuples table
docker compose exec -T postgres pg_dump -U postgres -d openfga -t tuple > tuples_backup.sql
```
