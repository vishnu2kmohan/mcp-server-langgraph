"""
Test security report generation.

Following TDD principles - these tests define the expected behavior
before implementation.
"""

import json
import tempfile
from pathlib import Path

import pytest

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


def test_generate_report_creates_markdown_file():
    """Test that generate_report creates a markdown report file."""
    from scripts.security.generate_report import generate_report

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)
        bandit_file = output_dir / "bandit-report.json"
        safety_file = output_dir / "safety-report.json"
        pip_audit_file = output_dir / "pip-audit-report.json"

        # Create minimal valid JSON files
        bandit_file.write_text('{"results": [], "metrics": {"_totals": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}}}')
        safety_file.write_text('{"vulnerabilities": []}')
        pip_audit_file.write_text('{"dependencies": []}')

        report_path = generate_report(output_dir)

        assert report_path.exists()
        assert report_path.suffix == ".md"
        assert "security-scan-report.md" in report_path.name


def test_generate_report_includes_severity_summary():
    """Test that report includes severity counts for all findings."""
    from scripts.security.generate_report import generate_report

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Create Bandit report with findings
        bandit_data = {
            "results": [
                {
                    "issue_severity": "HIGH",
                    "issue_confidence": "HIGH",
                    "issue_text": "SQL injection detected",
                    "filename": "src/api/auth.py",
                    "line_number": 42,
                    "test_id": "B608",
                    "test_name": "hardcoded_sql_expressions",
                },
                {
                    "issue_severity": "MEDIUM",
                    "issue_confidence": "HIGH",
                    "issue_text": "Weak cryptographic key",
                    "filename": "src/auth/crypto.py",
                    "line_number": 78,
                    "test_id": "B303",
                    "test_name": "blacklist",
                },
            ],
            "metrics": {"_totals": {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 1, "LOW": 0}},
        }

        (output_dir / "bandit-report.json").write_text(json.dumps(bandit_data))
        (output_dir / "safety-report.json").write_text('{"vulnerabilities": []}')
        (output_dir / "pip-audit-report.json").write_text('{"dependencies": []}')

        report_path = generate_report(output_dir)
        content = report_path.read_text()

        assert "## Summary" in content
        assert "HIGH" in content  # Should have HIGH severity in table or headings
        assert "MEDIUM" in content  # Should have MEDIUM severity in table or headings
        assert "1" in content  # Should show counts


def test_generate_report_includes_vulnerability_details():
    """Test that report includes detailed vulnerability information."""
    from scripts.security.generate_report import generate_report

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Create Safety report with vulnerability
        safety_data = {
            "vulnerabilities": [
                {
                    "vulnerability_id": "CVE-2024-12345",
                    "package_name": "requests",
                    "analyzed_version": "2.25.0",
                    "vulnerable_spec": "<2.31.0",
                    "advisory": "Server-side request forgery vulnerability",
                    "cve_id": "CVE-2024-12345",
                }
            ]
        }

        (output_dir / "bandit-report.json").write_text(
            '{"results": [], "metrics": {"_totals": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}}}'
        )
        (output_dir / "safety-report.json").write_text(json.dumps(safety_data))
        (output_dir / "pip-audit-report.json").write_text('{"dependencies": []}')

        report_path = generate_report(output_dir)
        content = report_path.read_text()

        assert "CVE-2024-12345" in content or "requests" in content
        assert "Dependency Vulnerabilities" in content or "Dependencies" in content


def test_generate_report_handles_missing_files_gracefully():
    """Test that generate_report handles missing scan files gracefully."""
    from scripts.security.generate_report import generate_report

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        # Only create one file
        (output_dir / "bandit-report.json").write_text(
            '{"results": [], "metrics": {"_totals": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}}}'
        )

        report_path = generate_report(output_dir)

        assert report_path.exists()
        content = report_path.read_text()
        assert "Security Scan Report" in content or "security" in content.lower()


def test_generate_report_includes_timestamp():
    """Test that report includes generation timestamp."""
    from scripts.security.generate_report import generate_report

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = Path(tmpdir)

        (output_dir / "bandit-report.json").write_text(
            '{"results": [], "metrics": {"_totals": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}}}'
        )
        (output_dir / "safety-report.json").write_text('{"vulnerabilities": []}')
        (output_dir / "pip-audit-report.json").write_text('{"dependencies": []}')

        report_path = generate_report(output_dir)
        content = report_path.read_text()

        # Should include a date/timestamp
        assert "202" in content or "Generated" in content


def test_parse_bandit_report_extracts_findings():
    """Test that Bandit report parsing extracts all findings correctly."""
    from scripts.security.generate_report import parse_bandit_report

    bandit_data = {
        "results": [
            {
                "issue_severity": "HIGH",
                "issue_confidence": "MEDIUM",
                "issue_text": "Use of assert detected",
                "filename": "src/test.py",
                "line_number": 10,
                "test_id": "B101",
                "test_name": "assert_used",
            }
        ],
        "metrics": {"_totals": {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0}},
    }

    findings = parse_bandit_report(bandit_data)

    assert len(findings) == 1
    assert findings[0]["severity"] == "HIGH"
    assert findings[0]["confidence"] == "MEDIUM"
    assert findings[0]["description"] == "Use of assert detected"
    assert findings[0]["file"] == "src/test.py"
    assert findings[0]["line"] == 10
    assert findings[0]["test_id"] == "B101"


def test_parse_safety_report_extracts_vulnerabilities():
    """Test that Safety report parsing extracts vulnerabilities correctly."""
    from scripts.security.generate_report import parse_safety_report

    safety_data = {
        "vulnerabilities": [
            {
                "vulnerability_id": "12345",
                "package_name": "django",
                "analyzed_version": "3.0.0",
                "vulnerable_spec": "<3.2.0",
                "advisory": "SQL injection in admin interface",
                "cve_id": "CVE-2021-12345",
            }
        ]
    }

    findings = parse_safety_report(safety_data)

    assert len(findings) == 1
    assert findings[0]["package"] == "django"
    assert findings[0]["version"] == "3.0.0"
    assert findings[0]["cve"] == "CVE-2021-12345"
    assert "SQL injection" in findings[0]["advisory"]


def test_parse_pip_audit_report_extracts_vulnerabilities():
    """Test that pip-audit report parsing extracts vulnerabilities correctly."""
    from scripts.security.generate_report import parse_pip_audit_report

    pip_audit_data = {
        "dependencies": [
            {
                "name": "flask",
                "version": "1.0.0",
                "vulns": [{"id": "PYSEC-2023-123", "fix_versions": ["2.3.0"], "description": "Improper session handling"}],
            }
        ]
    }

    findings = parse_pip_audit_report(pip_audit_data)

    assert len(findings) == 1
    assert findings[0]["package"] == "flask"
    assert findings[0]["version"] == "1.0.0"
    assert findings[0]["vuln_id"] == "PYSEC-2023-123"
    assert "2.3.0" in findings[0]["fix_versions"]


def test_format_markdown_report_structure():
    """Test that markdown report has correct structure."""
    from scripts.security.generate_report import format_markdown_report

    findings = {
        "bandit": [],
        "safety": [],
        "pip_audit": [],
        "summary": {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0},
    }

    markdown = format_markdown_report(findings)

    assert "# Security Scan Report" in markdown
    assert "## Summary" in markdown
    assert "## Findings" in markdown or "## Code Security" in markdown
    assert "## Dependency Vulnerabilities" in markdown or "## Dependencies" in markdown


def test_categorize_by_severity_groups_findings():
    """Test that findings are correctly grouped by severity."""
    from scripts.security.generate_report import categorize_by_severity

    findings = [
        {"severity": "HIGH", "description": "Issue 1"},
        {"severity": "MEDIUM", "description": "Issue 2"},
        {"severity": "HIGH", "description": "Issue 3"},
        {"severity": "LOW", "description": "Issue 4"},
    ]

    categorized = categorize_by_severity(findings)

    assert len(categorized["HIGH"]) == 2
    assert len(categorized["MEDIUM"]) == 1
    assert len(categorized["LOW"]) == 1
    assert len(categorized["CRITICAL"]) == 0
