# Archived Documentation - November 2025

This directory contains completed session reports and validation summaries from November 2025.

## Purpose

Session reports are archived here after:
1. Work is completed and merged
2. Report has been reviewed
3. Action items are tracked elsewhere (GitHub issues, project boards, etc.)
4. 30+ days have passed since creation OR work is definitively complete

## Files

### CI/CD & Build Reports
- **CI_CD_REMEDIATION_FINAL_REPORT.md** - Final CI/CD remediation summary
- **CODE_BLOCK_FIXES_SUMMARY.md** - Code block validation fixes summary

### Code Quality & Validation Reports
- **CODEBLOCK_VALIDATION_REPORT.md** - Code block validation results
- **CODEX_VALIDATION_REPORT_2025-11-15.md** - OpenAI Codex integration test validation (Nov 15, 2025)
- **VALIDATOR_FINAL_FINDINGS.md** - Final validator findings summary
- **VALIDATOR_IMPROVEMENTS_SUMMARY.md** - Validator improvements and enhancements

### Remediation & Fix Reports
- **FINAL_REMEDIATION_REPORT.md** - Comprehensive final remediation summary
- **FIXES_SUMMARY_2025-01-06.md** - Fixes applied on January 6, 2025
- **TEST_FIXES_SUMMARY.md** - Test suite fixes summary

### Documentation Validation
- **DOCUMENTATION_VALIDATION.md** - Documentation validation results (Nov 13, 2025)

## Archive Policy

### When to Archive

Files should be moved to archive when they meet ALL of these criteria:
1. **Completeness**: Work described in the report is 100% complete
2. **Review**: Report has been reviewed by team
3. **Tracking**: Action items are tracked in appropriate tools (GitHub, Jira, etc.)
4. **Age**: Either 30+ days old OR work is definitively complete

### When NOT to Archive

Keep in root if:
- Report describes ongoing work
- Action items are not yet tracked elsewhere
- File is referenced by active documentation
- File was created within last 7 days (let it "cool off" first)

## Retrieving Archived Files

All archived files are tracked in git history. To retrieve:

```bash
# View archived file
cat docs-internal/archive/2025-11/FILENAME.md

# Copy archived file back to root (if needed)
cp docs-internal/archive/2025-11/FILENAME.md .

# View git history of archived file
git log --follow docs-internal/archive/2025-11/FILENAME.md
```

## Archive Organization

Archives are organized by year-month (YYYY-MM) to facilitate:
- Easy chronological browsing
- Efficient git operations
- Clear separation of work periods
- Simple cleanup of very old archives (e.g., > 2 years)

## Cleanup Policy

Archives older than 2 years may be:
- Compressed into a single summary document
- Moved to cold storage
- Deleted if no longer needed (with git history preserved)

This policy will be reviewed annually.

---

**Archive Created**: 2025-11-15
**Last Updated**: 2025-11-15
**Files Archived**: 10 reports
**Next Review**: 2026-11-15
