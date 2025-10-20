# Comprehensive Documentation Audit

Conduct a thorough analysis of all documentation in this codebase to ensure everything is up to date, well-organized, and tidy.

## Scope

Analyze the following documentation areas:

### 1. Mintlify Documentation (Primary)
- **Configuration**: Validate `docs/mint.json` structure and completeness
- **Navigation**: Verify all navigation entries reference existing files
- **MDX Files**: Check all `.mdx` files in `docs/` directory
- **Cross-references**: Validate internal links between documentation pages
- **Code snippets**: Ensure code examples are current and functional
- **Missing pages**: Identify navigation items without corresponding files
- **Orphaned files**: Find documentation files not referenced in navigation

### 2. Root-Level Documentation
- `README.md` - Main project documentation
- `TESTING.md` - Testing guidelines
- `SECURITY.md` - Security policies
- `CODE_OF_CONDUCT.md` - Community guidelines
- `DEVELOPER_ONBOARDING.md` - Developer setup
- `REPOSITORY_STRUCTURE.md` - Project organization
- `MIGRATION.md` - Migration guides
- `ROADMAP.md` - Project roadmap
- `CHANGELOG.md` - Change history
- Other root `.md` files

Validate:
- Accuracy of information
- Broken external links
- Outdated version references
- Consistency with current codebase state

### 3. Architecture Decision Records (ADRs)
- Compare `adr/*.md` with `docs/architecture/*.mdx`
- Verify sync between source ADRs and Mintlify versions
- Check for missing or outdated ADRs
- Validate ADR numbering and naming consistency

### 4. Internal Documentation
- `docs-internal/*.md` - Internal technical documentation
- Verify alignment with current implementation
- Check for outdated information

### 5. Specialized Documentation
- `examples/README.md` - Example documentation
- `deployments/README.md` - Deployment guides
- `monitoring/README.md` - Monitoring setup
- `config/README.md` - Configuration documentation
- `tests/README.md` - Testing documentation
- `runbooks/README.md` - Operational runbooks

### 6. Integration & Reference Docs
- `integrations/*.md` - Integration guides
- `reference/*.md` - Reference documentation
- Verify completeness and accuracy

## Analysis Steps

### Phase 1: Mintlify Validation
1. Parse `docs/mint.json` and validate JSON structure
2. Extract all navigation references
3. Verify each referenced file exists
4. Check for orphaned `.mdx` files not in navigation
5. Validate frontmatter in all `.mdx` files
6. Check for broken internal links (relative paths)
7. Verify code blocks have proper language tags
8. Check for missing images referenced in docs

### Phase 2: Documentation Consistency
1. Check version numbers across all docs match project version
2. Validate API endpoint documentation matches actual endpoints
3. Verify configuration examples match `.env.example`
4. Check deployment guides reference correct Docker/K8s manifests
5. Validate CLI command examples are current

### Phase 3: Link Validation
1. Scan for external URLs in all documentation
2. Test HTTP/HTTPS links (with rate limiting)
3. Identify broken or redirected links
4. Check GitHub links point to correct branches

### Phase 4: Content Analysis
1. Identify outdated screenshots or diagrams
2. Check for TODO/FIXME comments in documentation
3. Find inconsistent terminology usage
4. Verify all code examples use consistent style
5. Check for duplicate content across files

### Phase 5: Organization Review
1. Assess navigation structure clarity
2. Check for logical grouping of topics
3. Verify progressive disclosure (beginner → advanced)
4. Identify missing cross-references
5. Review documentation coverage gaps

### Phase 6: ADR Sync Check
1. List all ADRs in `adr/` directory
2. List all ADRs in `docs/architecture/`
3. Compare content for drift
4. Check Mintlify navigation includes all ADRs
5. Verify ADR status (proposed/accepted/deprecated)

## Output Format

Provide a structured report with:

### Executive Summary
- Overall documentation health score (%)
- Critical issues count
- Warning issues count
- Recommendations count

### Detailed Findings

#### 🔴 Critical Issues
Issues that break documentation or provide incorrect information:
- Missing files referenced in navigation
- Broken critical links
- Incorrect API documentation
- Security documentation gaps

#### 🟡 Warnings
Issues that reduce documentation quality:
- Outdated examples
- Minor broken links
- Inconsistent formatting
- Missing cross-references

#### 🔵 Recommendations
Suggestions for improvement:
- Organization enhancements
- Coverage gaps
- Clarity improvements
- Additional examples needed

### File-by-File Analysis
For each issue, provide:
- **File**: Exact path with line numbers where applicable
- **Issue Type**: Category of problem
- **Current State**: What's wrong
- **Expected State**: What it should be
- **Action Required**: Specific fix needed
- **Priority**: High/Medium/Low

### Mintlify Navigation Report
- Total pages in navigation: X
- Existing files: X
- Missing files: X
- Orphaned files: X
- Navigation depth analysis
- Suggested reorganization (if needed)

### Link Health Report
- Total links found: X
- Valid links: X
- Broken external links: X
- Broken internal links: X
- Redirected links: X

### ADR Sync Report
- ADRs in source: X
- ADRs in Mintlify: X
- Synced: X
- Out of sync: X
- Missing: X

### Coverage Analysis
Areas with documentation:
- ✅ Well documented
- ⚠️ Partially documented
- ❌ Not documented

Key areas to assess:
- API endpoints coverage
- Configuration options coverage
- Deployment scenarios coverage
- Troubleshooting scenarios coverage
- Security best practices coverage

## Remediation Plan

Provide prioritized action items:

### Immediate Actions (P0)
Critical fixes that must be addressed:
1. Fix broken navigation links
2. Correct inaccurate technical information
3. Add missing critical documentation

### Short-term Actions (P1)
Important improvements to complete soon:
1. Update outdated examples
2. Fix broken external links
3. Sync ADRs between locations

### Medium-term Actions (P2)
Quality improvements:
1. Reorganize navigation structure
2. Add missing cross-references
3. Improve code example consistency

### Long-term Actions (P3)
Enhancements and optimizations:
1. Fill documentation gaps
2. Add advanced examples
3. Create additional guides

## Deliverables

1. **Comprehensive Audit Report**: Detailed markdown report
2. **Quick Reference Checklist**: Summary of all action items
3. **Prioritized Task List**: Organized by priority
4. **Suggested File Changes**: Specific edits needed

## Validation Commands

After remediation, run these checks:
```bash
# Validate Mintlify docs can build
cd docs && mintlify dev

# Check for broken links (if you have a link checker)
find docs -name "*.mdx" -exec grep -h "http" {} \;

# Validate all navigation targets exist
# (custom script output if available)
```

## Success Criteria

Documentation is considered "clean" when:
- ✅ All navigation links resolve to existing files
- ✅ No critical broken links
- ✅ Version numbers are consistent
- ✅ API documentation matches implementation
- ✅ ADRs are synced across locations
- ✅ No TODO/FIXME in production docs
- ✅ Code examples follow consistent style
- ✅ All deployment guides are current
- ✅ Security documentation is complete
- ✅ No orphaned documentation files

---

**Note**: This command performs a READ-ONLY analysis. It will not modify any files unless explicitly requested for remediation in a follow-up task.
