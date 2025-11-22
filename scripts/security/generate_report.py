#!/usr/bin/env python3
"""
Security scan report generator.

Consolidates findings from Bandit, Safety, and pip-audit into
a comprehensive markdown security report.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def parse_bandit_report(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Bandit JSON report and extract findings."""
    findings = []

    for result in data.get("results", []):
        findings.append(
            {
                "severity": result.get("issue_severity", "UNKNOWN"),
                "confidence": result.get("issue_confidence", "UNKNOWN"),
                "description": result.get("issue_text", ""),
                "file": result.get("filename", ""),
                "line": result.get("line_number", 0),
                "test_id": result.get("test_id", ""),
                "test_name": result.get("test_name", ""),
            }
        )

    return findings


def parse_safety_report(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Safety JSON report and extract vulnerabilities."""
    findings = []

    for vuln in data.get("vulnerabilities", []):
        findings.append(
            {
                "package": vuln.get("package_name", ""),
                "version": vuln.get("analyzed_version", ""),
                "cve": vuln.get("cve_id", vuln.get("vulnerability_id", "")),
                "advisory": vuln.get("advisory", ""),
                "vulnerable_spec": vuln.get("vulnerable_spec", ""),
            }
        )

    return findings


def parse_pip_audit_report(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse pip-audit JSON report and extract vulnerabilities."""
    findings = []

    for dep in data.get("dependencies", []):
        package = dep.get("name", "")
        version = dep.get("version", "")

        for vuln in dep.get("vulns", []):
            findings.append(
                {
                    "package": package,
                    "version": version,
                    "vuln_id": vuln.get("id", ""),
                    "description": vuln.get("description", ""),
                    "fix_versions": vuln.get("fix_versions", []),
                }
            )

    return findings


def categorize_by_severity(findings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group findings by severity level."""
    categorized = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}

    for finding in findings:
        severity = finding.get("severity", "UNKNOWN").upper()
        if severity in categorized:
            categorized[severity].append(finding)

    return categorized


def format_markdown_report(findings: dict[str, Any]) -> str:
    """Format findings into a comprehensive markdown report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = f"""# Security Scan Report

**Generated**: {timestamp}
**Scan Tools**: Bandit (code security), Safety (dependencies), pip-audit (dependencies)

---

## Summary

"""

    summary = findings.get("summary", {})
    total = summary.get("total", 0)
    critical = summary.get("critical", 0)
    high = summary.get("high", 0)
    medium = summary.get("medium", 0)
    low = summary.get("low", 0)

    md += f"""**Total Issues**: {total}

| Severity | Count |
|----------|-------|
| CRITICAL | {critical} |
| HIGH     | {high} |
| MEDIUM   | {medium} |
| LOW      | {low} |

---

## Code Security Findings (Bandit)

"""

    bandit_findings = findings.get("bandit", [])
    if bandit_findings:
        categorized = categorize_by_severity(bandit_findings)

        for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if categorized[severity]:
                md += f"\n### {severity} Severity\n\n"
                for finding in categorized[severity]:
                    md += f"""**{finding['file']}:{finding['line']}** - {finding['test_id']}\n"""
                    md += f"- **Issue**: {finding['description']}\n"
                    md += f"- **Confidence**: {finding['confidence']}\n"
                    md += f"- **Test**: {finding['test_name']}\n\n"
    else:
        md += "✅ No code security issues found.\n\n"

    md += "---\n\n## Dependency Vulnerabilities\n\n"

    safety_findings = findings.get("safety", [])
    pip_audit_findings = findings.get("pip_audit", [])

    if safety_findings or pip_audit_findings:
        md += "### Safety Vulnerabilities\n\n"
        if safety_findings:
            for vuln in safety_findings:
                md += f"""**{vuln['package']} {vuln['version']}** - {vuln['cve']}\n"""
                md += f"- **Advisory**: {vuln['advisory']}\n"
                md += f"- **Vulnerable**: {vuln['vulnerable_spec']}\n\n"
        else:
            md += "✅ No vulnerabilities found by Safety.\n\n"

        md += "### pip-audit Vulnerabilities\n\n"
        if pip_audit_findings:
            for vuln in pip_audit_findings:
                md += f"""**{vuln['package']} {vuln['version']}** - {vuln['vuln_id']}\n"""
                md += f"- **Description**: {vuln['description']}\n"
                if vuln["fix_versions"]:
                    md += f"- **Fix versions**: {', '.join(vuln['fix_versions'])}\n"
                md += "\n"
        else:
            md += "✅ No vulnerabilities found by pip-audit.\n\n"
    else:
        md += "✅ No dependency vulnerabilities found.\n\n"

    md += """---

## Recommendations

"""

    if total == 0:
        md += "✅ **No security issues detected.** The codebase appears secure.\n\n"
    else:
        if critical > 0:
            md += f"🔴 **{critical} CRITICAL issues** require immediate attention.\n"
        if high > 0:
            md += f"🟠 **{high} HIGH severity issues** should be fixed before release.\n"
        if medium > 0:
            md += f"🟡 **{medium} MEDIUM severity issues** should be addressed soon.\n"
        if low > 0:
            md += f"ℹ️ **{low} LOW severity issues** are informational.\n"
        md += "\n"

    md += """---

## Next Steps

1. Review all findings above
2. Prioritize fixes by severity (CRITICAL → HIGH → MEDIUM → LOW)
3. Update dependencies with known vulnerabilities
4. Re-run security scan after fixes
5. Ensure all tests pass after remediation

---

**Report End**
"""

    return md


def generate_report(output_dir: Path) -> Path:
    """
    Generate comprehensive security report from scan results.

    Args:
        output_dir: Directory containing JSON scan reports

    Returns:
        Path to generated markdown report
    """
    output_dir = Path(output_dir)

    # Load scan results
    bandit_file = output_dir / "bandit-report.json"
    safety_file = output_dir / "safety-report.json"
    pip_audit_file = output_dir / "pip-audit-report.json"

    bandit_findings = []
    safety_findings = []
    pip_audit_findings = []

    # Parse Bandit report
    if bandit_file.exists():
        try:
            with open(bandit_file) as f:
                bandit_data = json.load(f)
                bandit_findings = parse_bandit_report(bandit_data)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Could not parse Bandit report: {e}")

    # Parse Safety report
    if safety_file.exists():
        try:
            with open(safety_file) as f:
                safety_data = json.load(f)
                safety_findings = parse_safety_report(safety_data)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Could not parse Safety report: {e}")

    # Parse pip-audit report
    if pip_audit_file.exists():
        try:
            with open(pip_audit_file) as f:
                pip_audit_data = json.load(f)
                pip_audit_findings = parse_pip_audit_report(pip_audit_data)
        except (OSError, json.JSONDecodeError) as e:
            print(f"Warning: Could not parse pip-audit report: {e}")

    # Calculate summary
    categorized = categorize_by_severity(bandit_findings)
    summary = {
        "critical": len(categorized["CRITICAL"]),
        "high": len(categorized["HIGH"]),
        "medium": len(categorized["MEDIUM"]),
        "low": len(categorized["LOW"]),
        "total": len(bandit_findings) + len(safety_findings) + len(pip_audit_findings),
    }

    # Combine all findings
    all_findings = {"bandit": bandit_findings, "safety": safety_findings, "pip_audit": pip_audit_findings, "summary": summary}

    # Generate markdown report
    markdown = format_markdown_report(all_findings)

    # Write report
    report_path = output_dir / "security-scan-report.md"
    report_path.write_text(markdown)

    return report_path


def main():
    """Main entry point for CLI usage."""
    import sys

    if len(sys.argv) > 1:
        output_dir = Path(sys.argv[1])
    else:
        output_dir = Path("security-reports")

    if not output_dir.exists():
        print(f"Error: Directory {output_dir} does not exist")
        sys.exit(1)

    report_path = generate_report(output_dir)
    print(f"✅ Security report generated: {report_path}")


if __name__ == "__main__":
    main()
