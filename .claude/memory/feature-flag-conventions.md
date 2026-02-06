---
purpose: Naming conventions for feature flags across backend and API
priority: medium
category: conventions
last-updated: 2026-02-05
---

# Feature Flag Naming Conventions

---

## The Two Naming Contexts

| Context | Naming | Example | Location |
|---------|--------|---------|----------|
| Backend fields | `enable_*` prefix | `enable_skills_marketplace` | `feature_flags.py` class fields |
| API responses | Short names | `skills_marketplace` | `get_ui_features_for_role()` return dict |

---

## Critical Pattern

When adding a new feature flag that the frontend will use:

```python
# In get_ui_features_for_role() - use SHORT name as dict key:
"skills_marketplace": self.enable_skills_marketplace,  # CORRECT
"enable_skills_marketplace": self.enable_skills_marketplace,  # WRONG
```

---

## Frontend Usage

```typescript
// Always use SHORT names with isEnabled():
isEnabled("skills_marketplace")  // CORRECT
isEnabled("enable_skills_marketplace")  // WRONG
```

---

## Contract Test Protection

The contract test at `tests/contract/test_feature_flags_frontend_contract.py` enforces:

1. All frontend-required flags are exposed by backend
2. Exposed flag names do NOT use `enable_` prefix
3. Frontend `isEnabled()` calls match exposed flags

**Pre-push hook** runs this automatically.

---

## Exception: Admin Debugging Cards

Components like `FeatureFlagsCard` display raw backend state from `/api/v1/agents/config`.
These intentionally show `enable_*` prefixed names because they reflect backend field names.

---

## Quick Checklist for New Flags

- [ ] Add field to `FeatureFlags` class with `enable_` prefix
- [ ] Add to `get_ui_features_for_role()` with SHORT name
- [ ] Add to `FRONTEND_REQUIRED_FLAGS` in contract test
- [ ] Use SHORT name in frontend `isEnabled()` calls
- [ ] Run contract test: `uv run pytest tests/contract/test_feature_flags_frontend_contract.py -v`
