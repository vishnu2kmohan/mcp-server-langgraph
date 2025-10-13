# Dependency Audit Report - October 13, 2025

**Project**: MCP Server with LangGraph
**Audit Date**: 2025-10-13
**Next Audit Due**: 2025-11-13 (First Monday of the month)

---

## Executive Summary

**Overall Status**: ⚠️ **ACTION REQUIRED**

- **Total Packages**: 305 installed packages
- **Outdated Packages**: 65 packages have newer versions available
- **Security Vulnerabilities**: 1 active vulnerability (pip 25.2, fix pending in 25.3)
- **Open Dependabot PRs**: 15 PRs requiring review
- **Dependency Conflicts**: 1 minor conflict (solaar requiring dbus-python)

**Critical Actions Required**:
1. ✅ **COMPLETED**: Upgraded black from 24.1.1 → 25.9.0 (fixes CVE-2024-21503)
2. ⏳ **WAITING**: pip 25.3 release (fixes CVE-2025-8869)
3. 🔴 **HIGH PRIORITY**: Test and merge security patches (cryptography, PyJWT, actions/checkout)
4. 🟡 **MEDIUM PRIORITY**: Address LangGraph major version update (0.2.28 → 0.6.10)
5. 🟢 **LOW PRIORITY**: Batch merge minor updates for testing/CI tools

---

## Security Vulnerabilities

### 1. ✅ RESOLVED: Black ReDoS Vulnerability (CVE-2024-21503)

**Package**: black
**Vulnerable Version**: 24.1.1
**Current Version**: 25.9.0 ✅
**Fix Version**: 24.3.0+
**Severity**: MEDIUM
**CVSS Score**: Not specified

**Description**: Regular Expression Denial of Service (ReDoS) via the `lines_with_leading_tabs_expanded` function in strings.py. Exploitable when running Black on untrusted input or docstrings with thousands of leading tab characters.

**Action Taken**: Upgraded to black 25.9.0 using `uv pip install --upgrade black` on 2025-10-13.

**Status**: ✅ **RESOLVED**

---

### 2. ⏳ PENDING: Pip Tarfile Extraction Vulnerability (CVE-2025-8869)

**Package**: pip
**Vulnerable Version**: 25.2 (current)
**Fix Version**: 25.3 (not yet released)
**Severity**: HIGH
**GitHub Advisory**: GHSA-4xh5-x5gv-qwph

**Description**: In the fallback extraction path for source distributions, pip used Python's tarfile module without verifying that symbolic/hard link targets resolve inside the intended extraction directory. A malicious sdist can include links that escape the target directory and overwrite arbitrary files during `pip install`.

**Impact**: Arbitrary file overwrite outside the build directory, potentially leading to:
- Configuration tampering
- Startup file modification
- Code execution (environment-dependent)

**Conditions**: Triggered when installing an attacker-controlled sdist from an index or URL.

**Mitigation Strategy**:
1. **Immediate**: Only install packages from trusted sources (PyPI verified publishers)
2. **Short-term**: Monitor pip releases for version 25.3
3. **Defense in Depth**: Use Python interpreter with PEP 706 safe-extraction (not a substitute)

**Status**: ⏳ **WAITING FOR FIX** (pip 25.3 release)

**Recommended Actions**:
- Monitor [pip release notes](https://pip.pypa.io/en/stable/news/)
- Add to dependency update tracker for immediate upgrade when 25.3 releases
- Review all package installations from last 30 days for untrusted sources

---

## Open Dependabot PRs Analysis

**Total PRs**: 15
**CI Status**: All PRs failing (expected, require testing)

### Priority 0: Critical Security Patches (SLA: 48 hours)

None currently open. Black vulnerability was addressed manually.

### Priority 1: Security & Core Dependencies (SLA: 1-2 weeks)

| PR # | Package | Current | Target | Type | Risk | Action Required |
|------|---------|---------|--------|------|------|-----------------|
| **#32** | cryptography | 42.0.2 | 42.0.8 | PATCH | 🟢 LOW | Security patch - test & merge |
| **#30** | PyJWT | 2.8.0 | 2.10.1 | MINOR | 🟢 LOW | Test authentication stack |
| **#29** | openfga-sdk | 0.5.0 | 0.9.7 | MINOR | 🟡 MEDIUM | Test authorization layer |
| **#23** | fastapi | 0.109.0 | 0.119.0 | MINOR | 🟡 MEDIUM | Test REST API endpoints |
| **#26** | actions/checkout | 4 | 5 | MAJOR | 🟢 LOW | Update CI/CD workflows |
| **#22** | langgraph | 0.2.28 | 0.6.10 | MAJOR | 🔴 HIGH | Feature branch + 2-week testing |

**Recommended Action**: Create `deps/security-patches-2025-10-13` branch to test #32, #30 first.

### Priority 2: Development Tools (SLA: 1 month)

| PR # | Package | Current | Target | Type | Risk |
|------|---------|---------|--------|------|------|
| **#24** | mypy | 1.8.0 | 1.18.2 | MINOR | 🟢 LOW |
| **#31** | pytest-mock | 3.12.0 | 3.15.1 | MINOR | 🟢 VERY LOW |
| **#28** | pytest-xdist | 3.5.0 | 3.8.0 | MINOR | 🟢 VERY LOW |
| **#33** | respx | 0.20.2 | 0.22.0 | MINOR | 🟢 VERY LOW |
| **#34** | faker | 22.0.0 | 22.7.0 | MINOR | 🟢 VERY LOW |

**Recommended Action**: Batch merge after P1 updates complete. Group test execution.

### Priority 3: CI/CD Actions (SLA: 1 month)

| PR # | Package | Current | Target | Type | Risk |
|------|---------|---------|--------|------|------|
| **#25** | actions/labeler | 5 | 6 | MAJOR | 🟢 VERY LOW |
| **#21** | actions/download-artifact | 4 | 5 | MAJOR | 🟢 VERY LOW |
| **#20** | actions/setup-python | 5 | 6 | MAJOR | 🟢 VERY LOW |
| **#27** | azure/setup-kubectl | 3 | 4 | MAJOR | 🟢 VERY LOW |

**Recommended Action**: Batch merge after verifying workflow syntax.

---

## Outdated Critical Packages

Packages requiring updates from our production dependencies:

| Package | Current | Latest | Impact | Priority |
|---------|---------|--------|--------|----------|
| **cryptography** | 46.0.1 | 46.0.2 | Security/Auth | P1 |
| **pydantic** | 2.11.9 | 2.12.0 | Data validation | P1 |
| **pydantic_core** | 2.33.2 | 2.41.1 | Pydantic dependency | P1 |
| **langgraph** | 0.2.28 | 0.6.10 | Core agent functionality | P0 |
| **fastapi** | 0.109.0 | 0.119.0 | REST API | P1 |
| **openfga-sdk** | 0.5.0 | 0.9.7 | Authorization | P1 |
| **mypy** | 1.8.0 | 1.18.2 | Type checking | P2 |

**Note**: Many of these have corresponding Dependabot PRs (see table above).

---

## Dependency File Inconsistencies

**Problem**: Version mismatches between `pyproject.toml` and `requirements.txt`

| Package | pyproject.toml | requirements.txt | Status |
|---------|----------------|------------------|--------|
| **litellm** | >=1.52.3 | >=1.50.0 | ❌ Inconsistent |
| **cryptography** | >=42.0.2 | >=41.0.0 | ❌ Inconsistent |
| **opentelemetry-api** | >=1.22.0 | >=1.21.0 | ❌ Inconsistent |
| **fastapi** | >=0.109.0 | >=0.104.0 | ❌ Inconsistent |

**Impact**: Potential dependency resolution conflicts, unclear which version is authoritative.

**Recommended Action**: Consolidate to `pyproject.toml` as single source of truth (see `docs/DEPENDENCY_MANAGEMENT.md`).

---

## License Compliance

**Status**: ✅ **COMPLIANT**

- No GPL or AGPL licenses detected
- All dependencies use permissive licenses (MIT, Apache 2.0, BSD, PSF)
- License audit conducted using `pip-licenses`

**Next Review**: 2025-11-13 (monthly)

---

## Dependency Statistics

- **Total Packages**: 305
- **Outdated**: 65 (21.3%)
- **Development Packages**: ~80 (pytest, black, mypy, etc.)
- **Production Packages**: ~225
- **Security Vulnerabilities**: 1 (pip 25.2, awaiting fix)
- **Dependency Conflicts**: 1 (minor, dbus-python for solaar)

---

## Implementation Timeline (4-Phase Strategy)

### Week 1: Immediate Actions (Oct 13-20, 2025)

- [x] Document dependency management strategy (`docs/DEPENDENCY_MANAGEMENT.md`)
- [x] Create monthly audit script (`scripts/dependency-audit.sh`)
- [x] Run initial dependency audit
- [x] Fix black vulnerability (24.1.1 → 25.9.0)
- [ ] Merge security patches (cryptography, PyJWT)
- [ ] Batch merge CI/CD actions (#25, #21, #20, #27)
- [ ] Batch merge test framework updates (#31, #28, #33, #34)
- [ ] Consolidate dependency files (deprecate requirements.txt)
- [ ] Update Dependabot config with grouping strategy

### Week 2: Testing Major Updates (Oct 21-27, 2025)

- [ ] Create feature branch `feature/langgraph-0.6.10`
- [ ] Review LangGraph release notes (0.3.x → 0.6.x)
- [ ] Test LangGraph 0.6.10 (comprehensive testing)
- [ ] Test FastAPI 0.119.0
- [ ] Test OpenFGA SDK 0.9.7
- [ ] Document breaking changes

### Week 3: Merge Non-Critical Updates (Oct 28 - Nov 3, 2025)

- [ ] Merge FastAPI (if tests pass)
- [ ] Merge OpenFGA SDK (if tests pass)
- [ ] Merge mypy 1.18.2
- [ ] Merge remaining test framework updates

### Week 4: LangGraph Migration (Nov 4-10, 2025)

- [ ] Final comprehensive testing of LangGraph 0.6.10
- [ ] Update agent documentation for API changes
- [ ] Merge LangGraph 0.6.10 to main
- [ ] Release v2.3.0 with updated dependencies
- [ ] Monitor production for 48 hours

---

## Testing Requirements

### For ALL Dependency Updates

```bash
# 1. Create test branch
git checkout -b deps/test-<package>-<version>

# 2. Install updated dependency
uv pip install -e ".[dev]"

# 3. Run unit tests
ENABLE_TRACING=false ENABLE_METRICS=false ENABLE_CONSOLE_EXPORT=false \
  uv run python3 -m pytest -m unit --tb=line -q

# 4. Run security scan
bandit -r src/

# 5. Run linting
make lint

# 6. Check for dependency conflicts
pip check
```

### For Major Version Updates (LangGraph, FastAPI)

```bash
# Additional tests for major updates

# 1. Run ALL test suites
pytest tests/ -v --tb=short

# 2. Run integration tests (if available)
pytest -m integration

# 3. Manual testing
make run-dev
# Perform manual smoke tests

# 4. Check for API changes
# Review release notes and changelog
```

---

## Recommendations

### Immediate (This Week)

1. ✅ **COMPLETED**: Fix black vulnerability
2. 🔴 **HIGH PRIORITY**: Create security patch branch and test cryptography 42.0.8 + PyJWT 2.10.1
3. 🟡 **MEDIUM**: Batch merge CI/CD action updates after workflow validation
4. 🟢 **LOW**: Update Dependabot config with intelligent grouping

### Short-Term (Next 2-4 Weeks)

1. Test and merge LangGraph 0.6.10 (HIGH RISK - requires feature branch)
2. Test and merge FastAPI 0.119.0 (MEDIUM RISK)
3. Test and merge OpenFGA SDK 0.9.7 (MEDIUM RISK)
4. Consolidate to pyproject.toml as single source of truth
5. Monitor for pip 25.3 release (CVE fix)

### Long-Term (Next 1-3 Months)

1. Automate dependency testing workflow (`.github/workflows/dependency-test.yml`)
2. Schedule monthly audits (first Monday of each month)
3. Implement automated security scanning (weekly via GitHub Actions)
4. Create dependency update playbook for team

---

## Audit Script Usage

The dependency audit script is now available at `scripts/dependency-audit.sh`:

```bash
# Make executable (already done)
chmod +x scripts/dependency-audit.sh

# Run monthly audit
./scripts/dependency-audit.sh

# Save report to file
./scripts/dependency-audit.sh | tee dependency-audit-$(date +%Y%m%d).txt
```

**Schedule**: First Monday of every month (automated via cron or GitHub Actions)

---

## Next Steps

1. **Create security patch branch** for testing cryptography + PyJWT updates
2. **Investigate CI failures** on Dependabot PRs to understand root causes
3. **Update Dependabot configuration** with grouping strategy
4. **Monitor pip releases** for version 25.3 to fix CVE-2025-8869
5. **Schedule LangGraph testing** for Week 2 (feature branch)
6. **Review this report** at next team meeting for approval

---

## Appendix: Full Audit Output

See attached file: `dependency-audit-20251013.txt`

---

**Report Generated**: 2025-10-13 08:30 EDT
**Generated By**: Dependency Audit Script v1.0
**Next Audit**: 2025-11-13 (First Monday of November)
