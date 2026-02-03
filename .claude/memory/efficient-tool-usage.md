# Efficient Tool Usage Patterns

**Purpose**: Guide Claude toward script-based bulk operations and tool chaining
**Last Updated**: 2025-01-10

---

## Decision Framework

### When to Write a Script vs Individual Tool Calls

| Condition | Action |
|-----------|--------|
| 3+ files need similar changes | Write a bash/python script |
| Pattern-based replacement across codebase | Use `rg` + `sed` or `rg` + `xargs` pipeline |
| Sequential dependent operations | Chain with `&&` in single Bash call |
| Independent operations | Parallel tool calls in single message |
| Complex transformation logic | Write a Python script |
| Simple find-and-replace | Single `rg -l | xargs sed` pipeline |

### NEVER Do This

```
# BAD: Sequential Edit calls for similar changes
Edit file1.py: old -> new
Edit file2.py: old -> new
Edit file3.py: old -> new
...repeat 10 times...
```

### ALWAYS Do This Instead

> **Cross-Platform Note**: Use Python for reliable cross-platform in-place editing.
> - macOS sed: `sed -i ''`
> - Linux sed: `sed -i`
> - Portable (Unix): `perl -pi -e` (if Perl available)
> - **Most Portable**: Python (works on all platforms including Windows)

```bash
# GOOD: Python for bulk replacement (most portable - works on Windows, macOS, Linux)
uv run --frozen python3 -c "
from pathlib import Path
import re
for f in Path('.').rglob('*.py'):
    c = f.read_text()
    if 'old_pattern' in c:
        f.write_text(re.sub(r'old_pattern', 'new_pattern', c))
        print(f'Modified: {f}')
"

# GOOD: With preview first
rg "old_pattern" --type py  # Preview matches

# ALTERNATIVE: perl -pi -e (Unix only - requires Perl)
rg -l "old_pattern" --type py | xargs perl -pi -e 's/old_pattern/new_pattern/g'
```

---

## Shell Pipeline Patterns

### Bulk Rename/Replace

> **Note**: Examples use `perl -pi -e` for cross-platform compatibility.

```bash
# Replace string across Python files (cross-platform)
rg -l "OldClass" --type py | xargs perl -pi -e 's/OldClass/NewClass/g'

# Replace in specific directory
rg -l "old_func" src/mcp_server_langgraph/core/ | xargs perl -pi -e 's/old_func/new_func/g'

# Replace with word boundaries (safer)
rg -l '\bold_name\b' --type py | xargs perl -pi -e 's/\bold_name\b/new_name/g'
```

### Bulk Add/Modify Imports

```bash
# Add import to files that use a symbol but don't import it (Python for reliability)
uv run --frozen python3 -c "
from pathlib import Path
import re
for f in Path('.').rglob('*.py'):
    content = f.read_text()
    if 'FeatureFlag.' in content and 'from mcp_server_langgraph.core.feature_flags import FeatureFlag' not in content:
        f.write_text('from mcp_server_langgraph.core.feature_flags import FeatureFlag\n' + content)
"
```

### Bulk Update Test Markers

```bash
# Add marker to all tests in a directory (cross-platform)
rg -l "^def test_" tests/unit/auth/ | xargs perl -pi -e 's/\@pytest.mark.unit/\@pytest.mark.unit\n\@pytest.mark.auth/g'
```

### Bulk File Operations

```bash
# Find and process files matching pattern
fd -e py -x echo "Processing {}"

# Parallel execution
fd -e py | xargs -P 4 -I{} uv run ruff check {}
```

---

## Python Script Templates

### Bulk Code Transformation

When sed isn't enough, write a Python script:

```python
#!/usr/bin/env python3
"""Bulk transformation script - run with: uv run python script.py"""
import re
from pathlib import Path

def transform_file(path: Path) -> bool:
    """Transform a single file. Returns True if modified."""
    content = path.read_text()
    original = content

    # Your transformation logic here
    content = re.sub(r'old_pattern', 'new_pattern', content)

    if content != original:
        path.write_text(content)
        print(f"Modified: {path}")
        return True
    return False

def main():
    files = list(Path("src").rglob("*.py"))
    modified = sum(transform_file(f) for f in files)
    print(f"\nModified {modified}/{len(files)} files")

if __name__ == "__main__":
    main()
```

### AST-Based Transformation

For complex Python refactoring:

```python
#!/usr/bin/env python3
"""AST-based refactoring - safer than regex for Python code."""
import ast
import astor  # or use ast.unparse in Python 3.9+
from pathlib import Path

class Transformer(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        # Your transformation logic
        return self.generic_visit(node)

def transform_file(path: Path):
    source = path.read_text()
    tree = ast.parse(source)
    new_tree = Transformer().visit(tree)
    new_source = astor.to_source(new_tree)
    path.write_text(new_source)
```

---

## Parallel Tool Calls

### When to Parallelize

Always parallelize tool calls when:
- Reading multiple independent files
- Running independent searches (Grep/Glob)
- Executing independent commands
- Launching multiple Task agents

### Example: Parallel Reads

```
# In a single message, call Read for all files:
Read file1.py
Read file2.py
Read file3.py
Read file4.py
# All execute in parallel
```

### Example: Parallel Searches

```
# In a single message:
Grep pattern1 in src/
Grep pattern2 in tests/
Glob **/*.tsx
# All execute in parallel
```

---

## Common Bulk Operations in This Codebase

### Feature Flag Addition

```bash
# 1. Add to feature_flags.py enum
# 2. Find all usages that need the flag
rg -l "some_feature" --type py

# 3. Bulk add flag check (cross-platform)
rg -l "some_feature" --type py | xargs perl -pi -e 's/some_feature/FeatureFlag.SOME_FEATURE.is_enabled() and some_feature/g'
```

### Test Marker Updates

```bash
# Add integration marker to tests that use real infrastructure (cross-platform)
rg -l "@pytest.mark.asyncio" tests/integration/ | \
  xargs rg -l "async def test_.*real" | \
  xargs perl -pi -e 's/\@pytest.mark.asyncio/\@pytest.mark.asyncio\n\@pytest.mark.requires_infrastructure/g'
```

### Import Reorganization

```bash
# Find files with old import path
rg -l "from mcp_server_langgraph.old_module" --type py

# Bulk update (cross-platform)
rg -l "from mcp_server_langgraph.old_module" --type py | \
  xargs perl -pi -e 's/from mcp_server_langgraph.old_module/from mcp_server_langgraph.new_module/g'
```

### Frontend Component Prop Updates

```bash
# Update prop name across TSX files (cross-platform)
rg -l "oldProp=" --type tsx | xargs perl -pi -e 's/oldProp=/newProp=/g'

# Update type definition and usages together
rg -l "oldProp:" src/mcp_server_langgraph/studio/frontend/src/ | \
  xargs perl -pi -e 's/oldProp:/newProp:/g'
```

### API Endpoint Renaming

```bash
# Find all references (backend + frontend + tests)
rg "/api/v1/old-endpoint"

# Bulk replace (cross-platform)
rg -l "/api/v1/old-endpoint" | xargs perl -pi -e 's|/api/v1/old-endpoint|/api/v1/new-endpoint|g'
```

---

## Efficiency Checklist

Before making changes, ask:

1. **How many files?** If 3+, write a script
2. **Is it pattern-based?** Use `rg | xargs sed`
3. **Need preview?** Run `rg` first without modification
4. **Complex logic?** Write Python script
5. **Independent operations?** Parallelize tool calls
6. **Need AST awareness?** Use Python ast module

---

## Tool Selection Priority

| Task | First Choice | Fallback |
|------|--------------|----------|
| Find files | `fd` or Glob | `find` |
| Search content | `rg` or Grep | - |
| Bulk replace | `rg -l \| xargs sed` | Python script |
| Complex transform | Python script | - |
| JSON processing | `jq` | Python |
| YAML processing | `yq` | Python |
| Parallel exec | `xargs -P N` | Task tool |

---

## Anti-Patterns to Avoid

1. **Don't loop with individual Edit calls** - Write a script
2. **Don't read files sequentially** - Parallel Read calls
3. **Don't run related greps separately** - Combine patterns or parallelize
4. **Don't manually construct JSON** - Use jq
5. **Don't repeat yourself** - If doing it twice, script it

---

**Remember**: Scripts are documentation. A well-written bulk change script explains WHAT changed and can be re-run if needed.
