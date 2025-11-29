# Developer Utilities

Manual tools for development workflow (analysis, profiling, and code generation).

**Last Updated**: 2025-11-24
**Total Tools**: 8 utilities
**Integration**: None (manual use only - not in hooks/Makefile/workflows)

---

## 📊 Analysis & Profiling Tools

Tools for analyzing code, performance, and quality (read-only operations).

### Performance Analysis

- **`measure_hook_performance.py`** - Profile pre-commit hook execution time
  - Usage: `python scripts/dev/measure_hook_performance.py --stage all`
  - Measures hook timing to identify slow validators
  - Helps optimize pre-commit performance

### Test Analysis

- **`identify_critical_tests.py`** - Identify high-impact tests for prioritization
  - Analyzes test dependencies and coverage impact
  - Helps determine which tests to run first for fast feedback
  - Useful for optimizing test suite execution order

### Code Quality & Documentation

- **`audit_resource_ratios.py`** - Analyze Kubernetes resource request/limit ratios
  - Validates that resource limits are reasonable multiples of requests
  - Prevents OOMKilled pods from misconfigured ratios
  - Checks compliance with GKE Autopilot constraints

- **`detect_missing_lang_tags.py`** - Find code blocks in MDX docs missing language tags
  - Ensures proper syntax highlighting in documentation
  - Validates documentation quality
  - Prevents rendering issues in Mintlify

---

## 🔧 Code Generation & Maintenance Tools

Tools for generating code, updating imports, and synchronizing documentation (write operations).

### API & Client Generation

- **`generate_openapi.py`** - Generate/update OpenAPI schema from FastAPI application
  - Extracts API schema from running FastAPI application
  - Validates schema against OpenAPI 3.0/3.1 specification
  - Usage: `python scripts/dev/generate_openapi.py`

- **`generate_clients.sh`** - Generate client libraries from OpenAPI specifications
  - Creates Python, TypeScript, and Go clients from the OpenAPI schema
  - Automates client SDK generation
  - Usage: `bash scripts/dev/generate_clients.sh`

### Code & Documentation Maintenance

- **`update_documentation.py`** - Automated documentation updates
  - Synchronizes code comments with MDX documentation
  - Updates API reference documentation
  - Usage: `python scripts/dev/update_documentation.py`

- **`update_imports.py`** - Bulk update import statements across codebase
  - Refactor imports after module reorganization
  - Update deprecated imports to modern alternatives
  - Usage: `python scripts/dev/update_imports.py [options]`

---

## 🚀 Usage Examples

### Analysis Workflow
```bash
# Measure pre-commit hook performance
python scripts/dev/measure_hook_performance.py --stage pre-commit

# Identify critical tests for fast feedback
python scripts/dev/identify_critical_tests.py

# Audit K8s resource ratios
python scripts/dev/audit_resource_ratios.py deployments/

# Find missing MDX language tags
python scripts/dev/detect_missing_lang_tags.py docs/
```

### Generation Workflow
```bash
# After API changes → regenerate schema and clients
python scripts/dev/generate_openapi.py
bash scripts/dev/generate_clients.sh

# After code reorganization → update imports
python scripts/dev/update_imports.py --dry-run
python scripts/dev/update_imports.py  # apply changes

# After adding new endpoints → sync documentation
python scripts/dev/update_documentation.py
```

---

## 📚 When to Use

| Tool Category | Use Case | Frequency |
|---------------|----------|-----------|
| **Analysis** | Debug performance, audit quality | As needed during development |
| **Generation** | After API changes, refactoring | When making structural changes |

**Note**: These are **manual tools** - run them when needed, not automatically.

---

## 🔄 Integration (Optional)

To integrate any tool into automated systems:

1. **Pre-commit hooks**: Add to `.pre-commit-config.yaml`
2. **Make targets**: Add to `Makefile`
3. **CI/CD**: Add to `.github/workflows/*.yaml`

See `scripts/SCRIPT_INVENTORY.md` for examples of integrated scripts.

---

## 🗂️ Directory Consolidation

**2025-11-24**: Consolidated `scripts/development/` → `scripts/dev/`
- **Rationale**: Eliminate naming confusion (dev ≈ development)
- **Pattern**: Follows industry standards (single dev utilities directory)
- **Principle**: YAGNI - 8 files don't justify separate directories

Previous structure:
- ❌ `scripts/dev/` (analysis tools)
- ❌ `scripts/development/` (generation tools)

Current structure:
- ✅ `scripts/dev/` (all manual developer utilities, categorized)

---

## 📖 See Also

- [scripts/SCRIPT_INVENTORY.md](../SCRIPT_INVENTORY.md) - Complete script catalog (192 scripts)
- [scripts/archive/README.md](../archive/README.md) - Archived scripts (54 scripts)
- [scripts/validators/](../validators/) - Validation scripts (49 files)
- [docs/development/](../../docs/development/) - Development guides

---

**Generated**: 2025-11-24
**Maintained By**: Infrastructure Team
**Review Frequency**: Quarterly (next: 2026-02-24)
