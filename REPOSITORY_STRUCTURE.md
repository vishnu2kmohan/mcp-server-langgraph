# Repository Structure

This document describes the organization of the `mcp-server-langgraph` repository and the purpose of each directory.

## Directory Layout

```
mcp-server-langgraph/
├── docs/                      # 📚 Mintlify documentation (user-facing)
│   ├── getting-started/       # Getting started guides
│   ├── api-reference/         # API documentation
│   ├── guides/                # How-to guides
│   ├── deployment/            # Deployment guides
│   ├── architecture/          # Architecture Decision Records (ADRs)
│   ├── advanced/              # Advanced topics
│   ├── development/           # Development guides
│   └── security/              # Security documentation
│
├── src/                       # 🐍 Python source code
│   └── mcp_server_langgraph/  # Main package
│
├── tests/                     # 🧪 Test suite
│   ├── api/                   # API tests
│   ├── contract/              # Contract tests
│   ├── property/              # Property-based tests
│   └── regression/            # Regression tests
│
├── reports/                   # 📊 Project reports
│   ├── archive/               # Archived reports
│   ├── CI_CD_ANALYSIS_REPORT_*.md
│   ├── TEST_COVERAGE_IMPROVEMENT_REPORT_*.md
│   └── REPOSITORY_HEALTH_REPORT_*.md
│
├── adr/                       # 📝 Architecture Decision Records (source markdown)
│   ├── 0001-llm-multi-provider.md
│   ├── 0002-openfga-authorization.md
│   └── ...
│
├── runbooks/                  # 📖 Operational runbooks
│   └── (operational procedures and playbooks)
│
├── deployments/               # 🚀 Deployment configurations
│   ├── langgraph-platform/    # LangGraph Platform
│   ├── kubernetes/            # Kubernetes manifests
│   ├── helm/                  # Helm charts
│   └── cloud-run/             # Google Cloud Run
│
├── config/                    # ⚙️ Configuration files
│   ├── retention_policies.yaml
│   └── feature_flags.yaml
│
├── docker/                    # 🐳 Docker configurations
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── monitoring/                # 📈 Monitoring and observability
│   ├── grafana/               # Grafana dashboards
│   └── prometheus/            # Prometheus configs
│
├── examples/                  # 💡 Usage examples
│   └── (example scripts and notebooks)
│
├── hooks/                     # 🪝 Git hooks
│   └── (pre-commit, pre-push hooks)
│
├── .github/                   # 🤖 GitHub workflows
│   └── workflows/             # CI/CD pipelines
│
├── template/                  # 📋 Project templates
│   └── (cookiecutter templates)
│
├── reference/                 # 📚 Reference materials
│   └── (API specs, schemas)
│
├── integrations/              # 🔌 Integration guides
│   └── (third-party integrations)
│
├── archive/                   # 🗄️ Archived content
│   └── (deprecated documentation)
│
├── logs/                      # 📝 Application logs
│   └── (runtime logs)
│
└── Root-level files
    ├── mint.json              # Mintlify configuration
    ├── .mintlifyignore        # Mintlify exclusions
    ├── pyproject.toml         # Python project config
    ├── README.md              # Main README
    ├── CHANGELOG.md           # Version history
    ├── COMPLIANCE.md          # Compliance documentation
    ├── SECURITY.md            # Security policy
    └── ...
```

## Key Principles

### 1. Clean Separation of Concerns

- **`docs/`** - Only Mintlify documentation (`.mdx` files for user-facing docs)
- **`reports/`** - Project reports and metrics (not user docs)
- **`adr/`** - Source ADR markdown files (converted to `.mdx` in `docs/architecture/`)
- **`runbooks/`** - Internal operational procedures
- **`src/`** - Production code only
- **`tests/`** - All test code

### 2. Mintlify Integration

The `docs/` directory is exclusively for Mintlify documentation:

```bash
# Run Mintlify dev server
mintlify dev

# Only scans docs/ directory
# All other directories excluded via .mintlifyignore
```

**What's in docs/:**
- ✅ Getting started guides (`getting-started/`)
- ✅ API reference (`api-reference/`)
- ✅ How-to guides (`guides/`)
- ✅ Deployment guides (`deployment/`)
- ✅ Architecture docs (`architecture/`)
- ✅ Advanced topics (`advanced/`)
- ✅ Development guides (`development/`)
- ✅ Security docs (`security/`)

**What's NOT in docs/:**
- ❌ Reports (moved to `reports/`)
- ❌ ADR source files (moved to `adr/`)
- ❌ Runbooks (moved to `runbooks/`)
- ❌ Templates (moved to `template/`)
- ❌ Reference materials (moved to `reference/`)
- ❌ Standalone markdown files (moved to root)

### 3. Documentation Types

#### User-Facing Documentation (`docs/`)
- Format: `.mdx` (Mintlify)
- Audience: End users, API consumers, operators
- Examples: Quickstart, API reference, deployment guides

#### Project Documentation (Root)
- Format: `.md` (standard markdown)
- Audience: Contributors, maintainers
- Examples: COMPLIANCE.md, CONTRIBUTING.md, CHANGELOG.md

#### Internal Documentation
- **Reports** (`reports/`) - Test coverage, CI/CD analysis
- **ADRs** (`adr/`) - Architecture decision records (source)
- **Runbooks** (`runbooks/`) - Operational procedures

### 4. Versioning Strategy

- **Mintlify docs** (`docs/`) - Updated per release, published to docs site
- **Changelog** (`CHANGELOG.md`) - Version history
- **ADRs** (`adr/`) - Immutable after approval
- **Reports** (`reports/`) - Timestamped, archived after 90 days

## Working with Documentation

### Adding User Documentation

1. Create `.mdx` file in appropriate `docs/` subdirectory
2. Add reference to `mint.json` navigation
3. Run `mintlify dev` to preview
4. Commit and push

### Adding Project Reports

1. Create markdown file in `reports/`
2. Use naming convention: `REPORT_NAME_YYYYMMDD.md`
3. After 90 days, move to `reports/archive/`

### Adding Architecture Decisions

1. Create ADR in `adr/` using template
2. Convert to `.mdx` for `docs/architecture/`
3. Add to `mint.json` navigation
4. ADR source in `adr/` remains immutable

## Maintenance

### Quarterly Cleanup

- Archive old reports to `reports/archive/`
- Review and update `docs/` content
- Update CHANGELOG.md
- Regenerate API documentation

### Pre-Release Checklist

- [ ] Update version in `pyproject.toml`
- [ ] Update `CHANGELOG.md`
- [ ] Regenerate API docs
- [ ] Deploy Mintlify docs (`mintlify deploy`)
- [ ] Tag release in git

## Related Documentation

- [Mintlify Usage Guide](docs/MINTLIFY_USAGE.md)
- [Contributing Guide](.github/CONTRIBUTING.md)
- [Security Policy](SECURITY.md)
- [Compliance Framework](docs-internal/COMPLIANCE.md)

---

**Last Updated:** 2025-10-14
**Maintainer:** Repository Maintainers
