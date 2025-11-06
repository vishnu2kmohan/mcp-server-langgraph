# Migration Guides

This document serves as an index to all migration and upgrade guides for the MCP Server LangGraph project.

## Version Migrations

### v2.8.0 Migration Guides

#### Authentication Migration (v2.8.0)
**Guide**: [`docs/guides/authentication-migration-v2-8.mdx`](docs/guides/authentication-migration-v2-8.mdx)

Migration guide for authentication changes in v2.8.0, including:
- New authentication provider pattern
- Keycloak SSO integration updates
- JWT token handling changes
- Session storage architecture updates

**When to use**: Upgrading from v2.7.x to v2.8.0

---

## Tool Migrations

### UV Package Manager Migration
**Guide**: [`docs/guides/uv-migration.mdx`](docs/guides/uv-migration.mdx)

Complete guide for migrating from pip/poetry to uv package manager, including:
- Installation and setup
- Dependency migration
- Virtual environment management
- CI/CD pipeline updates
- Performance improvements (10-100x faster)

**When to use**:
- Adopting uv for faster dependency management
- Migrating existing pip/poetry projects
- Setting up new development environments

---

### Container Migration Guide
**Guide**: [`docs/guides/container-migration.mdx`](docs/guides/container-migration.mdx)

Guide for containerization and Docker deployment migrations, including:
- Dockerfile optimization
- Multi-stage build patterns
- Docker Compose v2 migration
- Kubernetes deployment updates
- Health check configuration

**When to use**:
- Moving from local development to containers
- Upgrading Docker Compose v1 to v2
- Kubernetes deployment migrations

---

## Breaking Changes by Version

### v2.8.0 Breaking Changes
- **Authentication**: New provider pattern requires configuration updates
- **Sessions**: Redis backend now required for distributed deployments
- **Configuration**: Environment variable naming standardization

See: [`CHANGELOG.md`](CHANGELOG.md#280---2025-10-21) for complete details

### v2.7.0 Breaking Changes
- **Observability**: OpenTelemetry integration requires new configuration
- **Compliance**: GDPR/HIPAA modules require explicit opt-in

See: [`CHANGELOG.md`](CHANGELOG.md#270---2025-09-15) for complete details

---

## Quick Migration Checklist

Before upgrading to a new major/minor version:

- [ ] **Review CHANGELOG.md** - Check breaking changes section
- [ ] **Read version-specific migration guide** (if available)
- [ ] **Backup configuration** - Copy `.env` and config files
- [ ] **Update dependencies** - Run `uv sync` or `make install-dev`
- [ ] **Run tests** - Verify `make test` passes
- [ ] **Update environment variables** - Check for new/changed vars
- [ ] **Test in staging** - Deploy to staging environment first
- [ ] **Review logs** - Check for deprecation warnings
- [ ] **Update documentation** - Internal runbooks, deployment docs

---

## Additional Resources

- **CHANGELOG**: [`CHANGELOG.md`](CHANGELOG.md) - Complete version history
- **Deployment Guides**: [`docs/deployment/`](docs/deployment/) - Platform-specific deployment instructions
- **API Changes**: [`docs/api-reference/`](docs/api-reference/) - API versioning and compatibility
- **ADRs**: [`docs/architecture/`](docs/architecture/) - Architecture decision records

---

## Version Support Policy

- **Current stable version**: v2.8.0
- **LTS support**: v2.7.x supported until Q2 2026
- **Security patches**: v2.6.x+ receive security updates
- **Deprecation policy**: 6-month notice before removal

See: [`docs/guides/versioning-strategy.mdx`](docs/guides/versioning-strategy.mdx) for complete versioning policy

---

## Need Help?

If you encounter issues during migration:

1. **Check documentation**: Review version-specific migration guides
2. **Search issues**: [GitHub Issues](https://github.com/vishnu2kmohan/mcp-server-langgraph/issues)
3. **Ask community**: [Discussions](https://github.com/vishnu2kmohan/mcp-server-langgraph/discussions)
4. **Report bugs**: [New Issue](https://github.com/vishnu2kmohan/mcp-server-langgraph/issues/new)

---

**Last Updated**: 2025-11-06
**Applies to**: v2.8.0 and later
