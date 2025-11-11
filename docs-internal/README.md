# Internal Documentation

This directory contains internal documentation for maintainers, contributors, and developers.

## Directory Structure

### 📦 archive/
**Historical documentation** (completed work, for reference only):
- `archive/sprints/` - Completed sprint reports
- `archive/audits/` - Completed audit reports
- `archive/codex/` - Codex validation & remediation (completed)
- `archive/releases/` - Historical release notes
- See `archive/README.md` for full inventory and archive policy

### 📐 architecture/
Technical architecture and design documentation:
- `AGENTIC_LOOP_GUIDE.md` - Implementation guide for agentic loop
- `PYDANTIC_AI_INTEGRATION.md` - Pydantic AI integration details
- `STRICT_TYPING_GUIDE.md` - Gradual mypy strict mode rollout

### 🔍 audits/
**Active** audit reports and assessments (timestamped):
- `DOCUMENTATION_AUDIT_2025-11-10.md` - Latest documentation audit
- `DOCUMENTATION_AUDIT_CHECKLIST_2025-11-10.md` - Quick reference
- `VERSION_REFERENCE_ANALYSIS_2025-11-10.md` - Version consistency analysis
- `REMEDIATION_SUMMARY_2025-11-10.md` - Remediation summary
- **Historical audits**: See `archive/audits/` for completed audits

### 🔧 operations/
Operational guides and runbooks:
- `SLA_OPERATIONS_RUNBOOK.md` - SLA monitoring and incident response
- `DEPENDENCY_MANAGEMENT.md` - Dependency update procedures
- `STORAGE_BACKEND_REQUIREMENTS.md` - Storage backend configuration

### 🔄 migrations/
Migration guides for major changes:
- `EMBEDDING_MIGRATION_GUIDE.md` - Embedding provider migration
- `MIGRATION.md` - General migration procedures

### 🚀 releases/
Release-specific documentation:
- `RELEASE_v2.8.0_COMMANDS.md` - Release commands and procedures

### 🏃 sprints/
**Active** sprint planning and tracking:
- `TODO-CATALOG.md` - Current TODO items
- **Historical sprints**: See `archive/sprints/` for completed sprints

### 🧪 testing/
Testing guides and reports:
- `MUTATION_TESTING.md` - Mutation testing procedures
- `TEST_RESULTS_SUMMARY.md` - Test execution summaries
- `TESTING_QUICK_START.md` - Quick start testing guide

### 📋 Root-level Files
- `BREAKING_CHANGES.md` - Breaking changes log
- `COMPLIANCE.md` - Compliance framework documentation
- `DEPLOYMENT.md` - Internal deployment notes
- `DOCUMENTATION_VERSIONING.md` - Documentation versioning strategy
- `GITHUB_ACTIONS_FIXES.md` - CI/CD fixes and improvements
- `MINTLIFY_USAGE.md` - Mintlify usage guide
- `PIP_AUTHENTICATION_FIX.md` - PIP authentication workarounds
- `ROOT_DIRECTORY_POLICY.md` - Root directory organization policy
- `SECURITY_REMEDIATION.md` - Security issue remediation

## Document Retention

- **Audits**: Archived when superseded to `archive/audits/`
- **Sprints**: Archived 30 days after completion to `archive/sprints/`
- **Remediation Campaigns**: Archived immediately upon completion to `archive/codex/`, `archive/*/`
- **Migrations**: Kept for 1 year after migration completion
- **Architecture**: Permanent (updated as needed)
- **Operations**: Permanent (kept current)

See `archive/README.md` for complete archive policy and search procedures.

## Contributing

When adding new internal documentation:

1. Choose the appropriate subdirectory based on content type
2. Use descriptive filenames with UPPERCASE convention
3. Add timestamps for time-sensitive documents (e.g., `_YYYY-MM-DD`)
4. Update this README if adding new categories
5. Link from relevant external docs (docs/) if applicable

## Related Documentation

- **User Documentation**: [docs/](../docs/) - Mintlify documentation
- **ADRs**: [adr/](../adr/) - Architecture Decision Records
- **Runbooks**: [runbooks/](../runbooks/) - Operational runbooks
- **Reports**: [reports/](../reports/) - Project reports and metrics

---

**Last Updated:** 2025-11-10
**Maintained By:** Repository Maintainers
**Last Archived:** 2025-11-10 (22 files archived)
