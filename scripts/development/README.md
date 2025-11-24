# Development Utilities

Code generation and maintenance automation for the development workflow.

**Last Updated**: 2025-11-24
**Purpose**: Automate repetitive code generation and documentation update tasks

---

## Tools

### Code Generation
- **`generate_clients.sh`** - Generate client libraries from OpenAPI specifications
  - Creates Python, TypeScript, and Go clients from the OpenAPI schema
  - Usage: `bash scripts/development/generate_clients.sh`

- **`generate_openapi.py`** - Generate/update OpenAPI schema from FastAPI application
  - Extracts API schema from running FastAPI application
  - Validates schema against OpenAPI 3.0/3.1 specification
  - Usage: `python scripts/development/generate_openapi.py`

### Documentation Automation
- **`update_documentation.py`** - Automated documentation updates
  - Synchronizes code comments with MDX documentation
  - Updates API reference documentation
  - Usage: `python scripts/development/update_documentation.py`

### Code Maintenance
- **`update_imports.py`** - Bulk update import statements across codebase
  - Refactor imports after module reorganization
  - Update deprecated imports to modern alternatives
  - Usage: `python scripts/development/update_imports.py [options]`

---

## Usage

These tools are **NOT integrated** into CI/CD or git hooks. They are for manual developer use only.

**When to use**:
- After API changes → regenerate OpenAPI schema and clients
- After code reorganization → update imports
- After adding new API endpoints → update documentation

**Frequency**: As needed during development (not automated)

---

## Comparison with `scripts/dev/`

| Directory | Purpose | Integration | Examples |
|-----------|---------|-------------|----------|
| **development/** | Code generation & automation | Manual only | generate_clients.sh, update_imports.py |
| **dev/** | Analysis & profiling tools | Manual only | measure_hook_performance.py, audit_resource_ratios.py |

**TL;DR**:
- `development/` = **GENERATE** code/docs
- `dev/` = **ANALYZE** code/performance

---

## Integration Status

**Hooks**: ❌ Not integrated
**Makefile**: ❌ Not integrated
**GitHub Actions**: ❌ Not integrated

These are utility scripts for developers to run manually when needed.

---

## Maintenance

**Audit Frequency**: Quarterly (every 3 months)
**Next Audit**: 2026-02-24
**Owner**: Infrastructure Team

---

**See Also**:
- [scripts/dev/README.md](../dev/README.md) - Development analysis tools
- [scripts/SCRIPT_INVENTORY.md](../SCRIPT_INVENTORY.md) - Complete script catalog
- [docs/development/](../../docs/development/) - Development guides

---

**Generated**: 2025-11-24
**Maintained By**: Infrastructure Team
