# Internal Project Documentation

This directory contains internal project documentation, technical guides, and implementation details that are not part of the user-facing Mintlify documentation.

## Contents

### Implementation Guides
- **PYDANTIC_AI_INTEGRATION.md** - Pydantic AI integration guide
- **PYDANTIC_MIGRATION_COMPLETE.md** - Pydantic migration details
- **STRICT_TYPING_GUIDE.md** - Python strict typing guide
- **MUTATION_TESTING.md** - Mutation testing documentation

### Operational Documentation
- **COMPLIANCE.md** - Compliance framework details
- **DEPLOYMENT.md** - Internal deployment procedures
- **SLA_OPERATIONS_RUNBOOK.md** - SLA operations runbook
- **DEPENDENCY_MANAGEMENT.md** - Dependency management guide

### Test and Quality Reports
- **TEST_FIXES_COMPLETE.md** - Test fixes documentation

### Other
- **index.html** - Internal documentation index page

## Purpose

This directory serves as a repository for:
- Technical implementation details
- Internal guides and procedures
- Migration and upgrade documentation
- Testing strategies
- Compliance implementation details

## Relationship to Other Documentation

### User-Facing Documentation → `../docs/`
- Mintlify `.mdx` format
- Published to documentation site
- For end users, API consumers, operators

### Project Reports → `../reports/`
- Test coverage reports
- CI/CD analysis
- Repository health metrics
- Timestamped and archived

### Architecture Decisions → `../adr/`
- Architecture Decision Records (ADRs)
- Immutable after approval
- Source markdown format

### Operational Runbooks → `../runbooks/`
- Operational procedures
- Incident response
- Disaster recovery

## Guidelines

### When to Use This Directory

Place content here when it:
- ✅ Is internal technical documentation
- ✅ Documents implementation details
- ✅ Provides guides for maintainers/contributors
- ✅ Is not intended for end users
- ✅ Doesn't fit in `docs/`, `reports/`, `adr/`, or `runbooks/`

### When NOT to Use This Directory

Do not place content here if it:
- ❌ Should be user-facing (use `docs/`)
- ❌ Is a project report (use `reports/`)
- ❌ Is an ADR (use `adr/`)
- ❌ Is an operational runbook (use `runbooks/`)
- ❌ Is configuration (use appropriate config directory)

## Maintenance

- Review quarterly for outdated content
- Move outdated content to `../archive/`
- Update cross-references when structure changes
- Keep file names descriptive and consistent

## Related Documentation

- [Repository Structure](../REPOSITORY_STRUCTURE.md)
- [Mintlify Documentation](../docs/README.md)
- [Reports Directory](../reports/README.md)
- [ADR Directory](../adr/README.md)
- [Runbooks Directory](../runbooks/README.md)

---

**Purpose:** Internal technical documentation and implementation guides
**Audience:** Maintainers, contributors, developers
**Format:** Standard Markdown (.md)
