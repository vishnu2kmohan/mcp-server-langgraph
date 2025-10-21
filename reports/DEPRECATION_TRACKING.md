# Deprecation Tracking

Documentation of deprecated code and planned removal timeline.

Generated: 2025-10-20
Last Updated: 2025-10-21
Status: Active

---

## Recent Cleanup (2025-10-21)

The following deprecated items have been **removed** from the codebase:

### ✅ Removed Deprecations
1. **Deployment Configs**: Deleted `deployments/DEPRECATED/` directory (~224KB)
   - `kubernetes-20251021-002310/` - Old Kubernetes manifests
   - `kustomize-20251021-002310/` - Old Kustomize overlays
   - **Impact**: No breaking changes - consolidated structure is active

2. **Docker Files**: Deleted `docker/DEPRECATED/` directory (379 lines)
   - `Dockerfile.deprecated` - Old multi-stage build
   - `Dockerfile.old` - Legacy build configuration
   - **Impact**: No breaking changes - current Dockerfile is optimized

3. **Requirements File**: Deleted `requirements-infisical.txt`
   - Functionality migrated to `pyproject.toml[project.optional-dependencies.secrets]`
   - **Migration Guide**: See `docs/guides/uv-migration.md`

4. **MCP Manifest**: Removed SSE transport from `.mcp/manifest.json`
   - Deprecated `http-sse` transport removed
   - Only `stdio` and `streamable-http` transports remain
   - **Impact**: No breaking changes - SSE was never implemented

### Disk Space Reclaimed
- Total: ~246KB of deprecated files removed
- Repository is now cleaner and easier to maintain

---

## Overview

This document tracks deprecated fields, APIs, and patterns in the codebase along with their migration paths and removal timelines.

All deprecations follow a structured process:
1. **Deprecated** - Marked deprecated, migration path documented (current)
2. **Removal Warning** - Logs warning when used (future)
3. **Removal** - Fully removed from codebase (future)

---

## Active Deprecations

### 1. MCP Request Field: `username` → `user_id`

**Status**: Deprecated in v2.x, Removal planned for v3.0
**Priority**: Low (backward compatibility maintained)
**Impact**: API breaking change when removed

#### Affected Files
- `src/mcp_server_langgraph/mcp/server_stdio.py:66-73, 94-101, 200`
- `src/mcp_server_langgraph/mcp/server_streamable.py:156-163, 180-187, 312`

#### Details

**Old API** (deprecated):
```python
class CreateThreadRequest(BaseModel):
    username: str | None = Field(
        default=None,
        deprecated=True,
        description="DEPRECATED: Use 'user_id' instead"
    )
```

**New API**:
```python
class CreateThreadRequest(BaseModel):
    user_id: str = Field(
        description="User identifier for authentication and authorization"
    )
```

#### Migration Path

For API consumers:
```python
# Old (deprecated, still works)
request = CreateThreadRequest(username="alice")

# New (recommended)
request = CreateThreadRequest(user_id="alice")
```

The `effective_user_id` property provides backward compatibility:
```python
@property
def effective_user_id(self) -> str:
    """Get effective user ID, prioritizing user_id over deprecated username."""
    return self.user_id if hasattr(self, "user_id") and self.user_id else (self.username or "")
```

#### Removal Plan

**v2.x (Current)**:
- ✅ Field marked as deprecated in Pydantic model
- ✅ Documentation updated to use `user_id`
- ✅ Backward compatibility maintained via `effective_user_id`

**v2.9.0 (Next minor)**:
- [ ] Add deprecation warning when `username` is used
- [ ] Update all examples and documentation to use `user_id`
- [ ] Add migration guide to MIGRATION.md

**v3.0.0 (Next major - Breaking Change)**:
- [ ] Remove `username` field entirely
- [ ] Remove `effective_user_id` property
- [ ] Update BREAKING_CHANGES.md
- [ ] Add breaking change notice in release notes

---

### 2. Config Field: `embedding_model` → `embedding_model_name`

**Status**: Deprecated (comment-based, not formally marked)
**Priority**: Low (backward compatibility maintained)
**Impact**: Minor - configuration breaking change

#### Affected Files
- `src/mcp_server_langgraph/core/config.py:172-174`

#### Details

**Old Config** (deprecated):
```python
embedding_model: str = "all-MiniLM-L6-v2"
# Deprecated: use embedding_model_name instead
```

**New Config**:
```python
# TODO: Document the actual field name
# Appears to be embedding_model_name based on comment
```

#### Current Status

⚠️ **Issue Identified**: The deprecation is comment-based only. Need to:
1. Verify if `embedding_model_name` field exists
2. Add formal `deprecated=True` to Pydantic field
3. Add migration property if needed
4. Document in MIGRATION.md

#### Investigation Required

```python
# Check if this exists in config.py:
embedding_model_name: str = Field(
    default="all-MiniLM-L6-v2",
    description="Embedding model name"
)

# If so, add:
embedding_model: str = Field(
    default="all-MiniLM-L6-v2",
    deprecated=True,
    description="DEPRECATED: Use embedding_model_name instead"
)
```

#### Removal Plan

**v2.9.0**:
- [ ] Investigate actual config structure
- [ ] Add formal deprecation if missing
- [ ] Document migration path
- [ ] Add to MIGRATION.md

**v3.0.0**:
- [ ] Remove deprecated field
- [ ] Update configuration examples
- [ ] Update BREAKING_CHANGES.md

---

## Deprecation Best Practices

### Marking Deprecations

**Pydantic Fields** (Recommended):
```python
from pydantic import Field

class MyModel(BaseModel):
    old_field: str = Field(
        deprecated=True,
        description="DEPRECATED: Use new_field instead. Removal planned for v3.0"
    )
    new_field: str = Field(
        description="Replacement for old_field"
    )
```

**Functions/Methods**:
```python
import warnings

def old_function(arg):
    warnings.warn(
        "old_function is deprecated, use new_function instead. "
        "Removal planned for v3.0",
        DeprecationWarning,
        stacklevel=2
    )
    return new_function(arg)
```

### Migration Properties

Provide compatibility shim:
```python
@property
def old_field(self) -> str:
    """DEPRECATED: Use new_field instead."""
    warnings.warn(
        "old_field is deprecated, use new_field",
        DeprecationWarning,
        stacklevel=2
    )
    return self.new_field
```

### Documentation

1. **In-Code**:
   - Mark with `deprecated=True`
   - Add DEPRECATED prefix to docstring
   - Reference replacement

2. **MIGRATION.md**:
   - Add migration guide
   - Show before/after examples
   - List affected versions

3. **CHANGELOG.md**:
   - Deprecation announced in minor version
   - Removal announced in major version

4. **BREAKING_CHANGES.md**:
   - Document breaking change
   - Provide migration path
   - List workarounds

---

## Removal Timeline

### v2.8.0 (Current)
- Deprecations documented
- Backward compatibility maintained

### v2.9.0 (Next Minor - Planned)
- Add deprecation warnings
- Update all documentation
- Publish migration guide

### v3.0.0 (Next Major - Breaking Changes)
- Remove all deprecated fields
- Update BREAKING_CHANGES.md
- Comprehensive migration guide

---

## Tracking

### How to Find Deprecations

```bash
# Search for Pydantic deprecated fields
grep -rn "deprecated=True" src/

# Search for deprecation comments
grep -rni "deprecated" src/ | grep -E "(DEPRECATED|deprecated:)"

# Search for deprecation warnings
grep -rn "DeprecationWarning" src/
```

### Regular Review

**Schedule**: Quarterly review of deprecations

**Process**:
1. Review this document
2. Check usage metrics (if available)
3. Update removal timeline
4. Communicate changes to users

---

## Communication

### Where to Announce

1. **CHANGELOG.md** - Version where deprecated
2. **MIGRATION.md** - Migration guides
3. **BREAKING_CHANGES.md** - Breaking changes (on removal)
4. **GitHub Releases** - Release notes
5. **Documentation** - Inline warnings

### Deprecation Notice Template

```markdown
## Deprecation: [Feature/Field Name]

**Deprecated in**: v2.x.x
**Removal planned**: v3.0.0

The `old_feature` has been deprecated in favor of `new_feature`.

**Before**:
```python
# Old usage
```

**After**:
```python
# New usage
```

**Migration**: See MIGRATION.md for detailed migration guide.
```

---

## Summary

### Current Status (as of 2025-10-21)
- **Active Code Deprecations**: 2
  - **Formally Marked**: 1 (`username` field with `deprecated=True`)
  - **Comment-Only**: 1 (`embedding_model` field - needs formalization)
- **Removed Deprecations**: 4 (deployment configs, Docker files, requirements file, SSE transport)
- **Removal Planned**: v3.0.0 for active deprecations

### Completed Action Items
1. ✅ Document all deprecations (this file)
2. ✅ Remove DEPRECATED directories and files (2025-10-21 cleanup)
3. ✅ Update deprecation tracking documentation

### Pending Action Items
1. [ ] Formalize `embedding_model` deprecation with proper Pydantic marking
2. [ ] Add runtime deprecation warnings for `username` field (v2.9.0)
3. [ ] Update all examples to use `user_id` instead of `username`
4. [ ] Add comprehensive migration guide to MIGRATION.md
5. [ ] Plan v3.0.0 breaking changes removal

---

**Maintained by**: Development Team
**Last Updated**: 2025-10-21
**Next Review**: 2025-11-21 (monthly during active deprecation period)
