# Deprecation Tracking

Documentation of deprecated code and planned removal timeline.

Generated: 2025-10-20
Status: Active

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

### Current Status
- **Total Deprecations**: 2
- **Formally Marked**: 1 (`username` field)
- **Comment-Only**: 1 (`embedding_model` field)
- **Removal Planned**: v3.0.0

### Action Items
1. ✅ Document all deprecations (this file)
2. [ ] Formalize `embedding_model` deprecation
3. [ ] Add deprecation warnings (v2.9.0)
4. [ ] Update MIGRATION.md
5. [ ] Plan v3.0.0 removal

---

**Maintained by**: Development Team
**Last Updated**: 2025-10-20
**Next Review**: 2025-11-20 (monthly during active deprecation period)
