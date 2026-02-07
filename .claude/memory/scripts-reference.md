---
purpose: Quick reference to commonly needed scripts
priority: medium
category: reference
last-updated: 2026-02-07
---

# Existing Scripts Reference

**Full Inventory**: `scripts/SCRIPT_INVENTORY.md` (192 scripts documented)

---

## Bulk Fix Scripts (scripts/archive/unused/)

| Script | Purpose |
|--------|---------|
| `bulk_fix_async_mock.py` | Fix AsyncMock issues across codebase |
| `add_xdist_markers_bulk.py` | Add xdist_group markers to tests |

---

## Validation Hooks (pre-commit)

### AsyncMock Validation

| Hook ID | Script | Purpose |
|---------|--------|---------|
| `check-asyncmock-instantiation` | `check_asyncmock_usage.py` | Catch `AsyncMock` class assignment |
| `check-async-mock-configuration` | `check_async_mock_configuration.py` | Enforce `spec=` parameter |

### Test Quality

| Hook ID | Script | Purpose |
|---------|--------|---------|
| `check-test-naming` | `check_test_naming.py` | Enforce 3+ word test names |
| `check-test-memory-safety` | `check_test_memory_safety.py` | Require gc.collect() in teardown |
| `check-test-sleep-duration` | `check_test_sleep_duration.py` | No sleep > 5s |
| `check-test-environment-isolation` | `check_test_environment_isolation.py` | Use monkeypatch, not os.environ |

### Infrastructure

| Hook ID | Script | Purpose |
|---------|--------|---------|
| `check-subprocess-timeout` | `check_subprocess_timeout.py` | Require timeout parameter |
| `check-otel-attribute-naming` | `check_otel_attribute_naming.py` | Dot notation for OTEL |

---

## Dev Tools (scripts/dev/)

| Script | Purpose |
|--------|---------|
| `add_xdist_markers_bulk.py` | Add xdist_group markers |
| `generate_script_inventory.py` | Regenerate SCRIPT_INVENTORY.md |

---

## Before Creating New Scripts

1. **Read inventory**: `scripts/SCRIPT_INVENTORY.md`
2. **Search existing**: `Glob scripts/**/*.py`
3. **Check archived**: `scripts/archive/unused/`
4. **Check hooks**: `.pre-commit-config.yaml`
