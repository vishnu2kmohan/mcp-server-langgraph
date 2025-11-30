# Security Scanning Tools

Comprehensive security scanning and reporting infrastructure for the mcp-server-langgraph project.

## Quick Start

```bash
# Run comprehensive security scan
make security-scan-full
```

This will:
1. Run Bandit for code security analysis
2. Run Safety for dependency vulnerability scanning (if installed)
3. Run pip-audit for dependency vulnerability scanning (if installed)
4. Generate consolidated markdown report

## Reports

After running the scan, you'll find these files in `security-reports/`:

- `bandit-report.json` - Bandit code security findings (JSON)
- `safety-report.json` - Safety dependency vulnerabilities (JSON)
- `pip-audit-report.json` - pip-audit dependency vulnerabilities (JSON)
- `security-scan-report.md` - Consolidated markdown report

## Installation

### Required Tools

**Bandit** (already installed):
- Pre-configured in the project
- Scans Python code for security issues

**Optional Tools** (recommended for comprehensive scanning):

```bash
# Install Safety for dependency vulnerability scanning
uv tool install safety

# Install pip-audit for dependency vulnerability scanning
uv tool install pip-audit
```

## Usage

### Comprehensive Scan (Recommended)

```bash
make security-scan-full
```

Runs all security tools and generates consolidated report.

### Quick Code Scan Only

```bash
make security-check
```

Runs only Bandit for quick code security check.

### Manual Report Generation

```bash
# Generate report from existing JSON files
uv run --frozen python scripts/security/generate_report.py security-reports
```

## Report Format

The consolidated report includes:

- **Summary**: Total issues by severity (CRITICAL, HIGH, MEDIUM, LOW)
- **Code Security Findings**: Issues found by Bandit with file/line references
- **Dependency Vulnerabilities**: CVEs and vulnerabilities from Safety and pip-audit
- **Recommendations**: Prioritized action items
- **Next Steps**: Remediation workflow

## CI/CD Integration

The security scanning tools are also integrated into CI/CD:

- `.github/workflows/security-scan.yaml` - Daily automated scans
- Pre-commit hooks run Bandit on changed files
- GitHub Security tab receives SARIF reports

## Severity Levels

- **CRITICAL**: Immediate fix required (blocks releases)
- **HIGH**: Fix before release
- **MEDIUM**: Fix soon
- **LOW**: Informational (best practices)

## Example Output

```
🔒 Running comprehensive security scan...

1/3 Running Bandit (code security)...
✓ No high/critical issues found

2/3 Running Safety (dependency vulnerabilities)...
✓ No vulnerabilities found

3/3 Running pip-audit (dependency vulnerabilities)...
✓ No vulnerabilities found

📊 Generating consolidated report...
✅ Security report generated: security-reports/security-scan-report.md

Total Issues: 31
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 0
- LOW: 31
```

## Tests

The report generation system follows TDD principles:

```bash
# Run security report tests
uv run --frozen pytest tests/test_security_report.py -v
```

All 10 tests verify:
- Report generation
- JSON parsing
- Markdown formatting
- Error handling
- Severity categorization

## Troubleshooting

### Safety/pip-audit Not Found

If you see warnings about missing tools:

```bash
uv tool install safety
uv tool install pip-audit
```

### Permission Errors

Ensure the `security-reports/` directory is writable:

```bash
mkdir -p security-reports
chmod 755 security-reports
```

### Empty Reports

If tools fail to run, fallback empty reports are generated:
- `{"vulnerabilities": []}` for Safety
- `{"dependencies": []}` for pip-audit

This ensures report generation always succeeds.

## Architecture

```
scripts/security/
├── __init__.py           # Package marker
├── generate_report.py    # Main report generator
└── README.md            # This file

Makefile                 # security-scan-full target
tests/
└── test_security_report.py  # TDD tests (10 tests, 100% passing)

security-reports/        # Generated artifacts (gitignored)
├── bandit-report.json
├── safety-report.json
├── pip-audit-report.json
└── security-scan-report.md
```

## Best Practices

1. **Run before commits**: Catch issues early
2. **Review all findings**: Even LOW severity issues matter
3. **Update dependencies**: Keep libraries current
4. **Fix HIGH/CRITICAL first**: Prioritize by severity
5. **Re-scan after fixes**: Verify issues resolved

## Related Documentation

- [SECURITY_REMEDIATION_REPORT.md](../../archive/reports/SECURITY_REMEDIATION_REPORT.md) - Previous security audit results
- [Security Scan Workflow](../../.github/workflows/security-scan.yaml) - CI/CD integration
- [Pre-commit Config](../../.pre-commit-config.yaml) - Bandit hook configuration

## Maintenance

This tooling follows the project's TDD standards:

- ✅ All tests written before implementation
- ✅ 100% test coverage on core functions
- ✅ Comprehensive error handling
- ✅ Graceful degradation when tools unavailable

Last updated: 2025-11-07
