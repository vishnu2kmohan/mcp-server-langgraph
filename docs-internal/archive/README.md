# Internal Documentation Archive
**Purpose**: Historical records of completed sprints, audits, and remediation efforts

This directory contains archived documentation for completed work that is no longer actively maintained but preserved for historical reference.

---

## Directory Structure

### `/sprints`
Completed sprint summaries and progress reports.

**Contents**:
- `TECHNICAL_DEBT_SPRINT_COMPLETE.md` - Technical debt sprint completion report
- `technical-debt-sprint-progress.md` - Daily progress tracking
- `sprint-final-summary.md` - Final sprint summary
- `technical-debt-sprint-day1-summary.md` - Day 1 summary
- `TODO_STATUS_2025-11-08.md` - TODO tracking snapshot (2025-11-08)

**Active Sprint Docs**: See `../sprints/` for current sprint planning

---

### `/audits`
Completed audit reports and remediation summaries.

**Contents**:
- `DOCUMENTATION_AUDIT_2025-10-20_FINAL.md` - October 2025 documentation audit (final)
- `documentation-audit-report.md` - Initial audit report
- `documentation-fixes-applied.md` - Fixes applied log
- `INFRASTRUCTURE_AUDIT_COMPLETE.md` - Infrastructure audit completion
- `infrastructure-audit-phase1-summary.md` - Phase 1 summary
- `infrastructure-audit-phase2-3-summary.md` - Phase 2-3 summary

**Active Audits**: See `../audits/` for current audits (e.g., `DOCUMENTATION_AUDIT_2025-11-10.md`)

---

### `/codex`
OpenAI Codex validation and remediation reports (completed).

**Contents** (11 files):
- `CODEX_FINAL_SUMMARY.md` - Final Codex validation summary
- `CODEX_REMEDIATION_COMPLETE.md` - Remediation completion report
- `CODEX_FINDINGS_VALIDATION_REPORT.md` - Findings validation
- `CODEX_FINDINGS_REMEDIATION_REPORT.md` - Findings remediation
- `CODEX_FINDINGS_RESOLUTION_REPORT.md` - Findings resolution
- `CODEX_FINDINGS_TDD_SAFEGUARDS.md` - TDD safeguards implementation
- `CODEX_GITHUB_ACTIONS_WORKFLOW_VALIDATION.md` - GitHub Actions validation
- `CODEX_REMEDIATION_STATUS.md` - Remediation status tracking
- `CODEX_REMEDIATION_SUMMARY.md` - Remediation summary
- `CODEX_REMEDIATION_VALIDATION_REPORT.md` - Remediation validation
- `CODEX_VALIDATION_REPORT.md` - Final validation report

**Status**: All Codex remediation completed as of 2025-11-10

---

### `/releases`
Historical release documentation (if needed).

**Status**: Currently empty
**Active Releases**: See `../releases/` or `/docs/releases/` for current release notes

---

## Archive Policy

### What Gets Archived
- ✅ Completed sprint reports (after sprint conclusion)
- ✅ Finalized audit reports (after remediation complete)
- ✅ Completed remediation campaigns (e.g., Codex validation)
- ✅ Historical snapshots (e.g., TODO status on specific dates)

### What Stays Active
- ⚡ Current sprint planning and tracking
- ⚡ Ongoing audits and their remediation plans
- ⚡ Active operational runbooks
- ⚡ Current architecture documentation
- ⚡ Testing and deployment guides

### Archiving Schedule
- **Sprints**: Archived 30 days after completion
- **Audits**: Archived when superseded by newer audits
- **Remediation**: Archived immediately upon completion
- **Snapshots**: Archived immediately (historical record)

---

## How to Use This Archive

### Finding Historical Information

**Sprint History**:
```bash
ls -lt archive/sprints/
cat archive/sprints/TECHNICAL_DEBT_SPRINT_COMPLETE.md
```

**Audit History**:
```bash
ls -lt archive/audits/
cat archive/audits/DOCUMENTATION_AUDIT_2025-10-20_FINAL.md
```

**Codex Validation**:
```bash
ls -1 archive/codex/
cat archive/codex/CODEX_FINAL_SUMMARY.md
```

### Searching Archives

```bash
# Search for specific topic across all archives
grep -r "performance" archive/

# Find files modified in specific timeframe
find archive/ -name "*.md" -newermt "2025-10-01"

# Search by file type
find archive/sprints/ -name "*COMPLETE*.md"
```

---

## Archive Maintenance

### Quarterly Review
Every quarter (Jan, Apr, Jul, Oct):
1. Review active docs for completion
2. Move completed work to archive
3. Update this README
4. Remove duplicate or superseded documents

### Last Archived
**Date**: 2025-11-10
**By**: Documentation audit remediation
**Files Archived**: 22 files (5 sprints, 6 audits, 11 codex)

---

## See Also

- **Active Documentation**: `../README.md`
- **Current Audits**: `../audits/`
- **Active Sprints**: `../sprints/`
- **Operational Docs**: `../operations/`
- **Testing Guides**: `../testing/`

---

**Archive Policy**: Retain indefinitely for historical reference
**Last Updated**: 2025-11-10
