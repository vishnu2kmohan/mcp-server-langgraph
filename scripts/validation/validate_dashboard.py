#!/usr/bin/env python3
"""
Unified Validation Dashboard

Runs all validation checks and produces a consolidated report.
Useful for pre-push validation and CI/CD pipelines.

Usage:
    python scripts/validation/validate_dashboard.py [--fast] [--json] [--ci]

Options:
    --fast    Run only fast checks (< 5 seconds each)
    --json    Output results as JSON
    --ci      CI mode - exit 1 on any failure
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class CheckResult:
    name: str
    status: Status
    duration_seconds: float
    message: str | None = None
    details: str | None = None


@dataclass
class ValidationReport:
    checks: list[CheckResult]
    total_duration: float
    passed: int
    failed: int
    skipped: int
    errors: int

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total_duration_seconds": round(self.total_duration, 2),
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
                "errors": self.errors,
                "success": self.failed == 0 and self.errors == 0,
            },
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "duration_seconds": round(c.duration_seconds, 2),
                    "message": c.message,
                }
                for c in self.checks
            ],
        }


# Define validation checks
CHECKS = [
    # Fast checks (< 5 seconds)
    {
        "name": "Python Syntax",
        "command": ["uv", "run", "--frozen", "python", "-m", "py_compile", "src/mcp_server_langgraph/__init__.py"],
        "fast": True,
    },
    {
        "name": "Ruff Linting",
        "command": ["uv", "run", "--frozen", "ruff", "check", "src/", "--quiet"],
        "fast": True,
    },
    {
        "name": "Ruff Formatting",
        "command": ["uv", "run", "--frozen", "ruff", "format", "--check", "src/", "--quiet"],
        "fast": True,
    },
    {
        "name": "UV Lock Sync",
        "command": ["uv", "lock", "--check"],
        "fast": True,
    },
    {
        "name": "UV Pip Check",
        "command": ["uv", "pip", "check"],
        "fast": True,
    },
    # Medium checks (5-30 seconds)
    {
        "name": "MyPy Type Checking",
        "command": ["uv", "run", "--frozen", "mypy", "src/mcp_server_langgraph", "--config-file=pyproject.toml"],
        "fast": False,
    },
    {
        "name": "Pytest Collection",
        "command": ["uv", "run", "--frozen", "pytest", "--collect-only", "-q", "tests/unit/", "--ignore=tests/unit/api/"],
        "fast": False,
        "env": {"OTEL_SDK_DISABLED": "true"},
    },
    # Slow checks (> 30 seconds) - only in full mode
    {
        "name": "Unit Tests (Sample)",
        "command": [
            "uv",
            "run",
            "--frozen",
            "pytest",
            "tests/unit/core/test_feature_flags.py",
            "-v",
            "--tb=short",
            "-x",
        ],
        "fast": False,
        "env": {"OTEL_SDK_DISABLED": "true"},
    },
]


def run_check(check: dict, verbose: bool = False) -> CheckResult:
    """Run a single validation check."""
    name = check["name"]
    command = check["command"]
    env = check.get("env", {})

    # Merge with current environment
    import os

    full_env = os.environ.copy()
    full_env.update(env)

    start = time.time()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
            env=full_env,
        )
        duration = time.time() - start

        if result.returncode == 0:
            return CheckResult(
                name=name,
                status=Status.PASSED,
                duration_seconds=duration,
                message="All checks passed",
            )
        else:
            return CheckResult(
                name=name,
                status=Status.FAILED,
                duration_seconds=duration,
                message=f"Exit code {result.returncode}",
                details=result.stderr[:500] if result.stderr else result.stdout[:500],
            )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name=name,
            status=Status.ERROR,
            duration_seconds=300,
            message="Timeout after 300 seconds",
        )
    except Exception as e:
        return CheckResult(
            name=name,
            status=Status.ERROR,
            duration_seconds=time.time() - start,
            message=str(e),
        )


def run_validation(fast_only: bool = False, verbose: bool = False) -> ValidationReport:
    """Run all validation checks and return a report."""
    checks_to_run = [c for c in CHECKS if not fast_only or c.get("fast", False)]

    results = []
    total_start = time.time()

    for check in checks_to_run:
        if verbose:
            print(f"Running: {check['name']}...", end=" ", flush=True)

        result = run_check(check, verbose)
        results.append(result)

        if verbose:
            status_icon = {
                Status.PASSED: "\u2705",
                Status.FAILED: "\u274c",
                Status.SKIPPED: "\u23ed",
                Status.ERROR: "\u26a0\ufe0f",
            }[result.status]
            print(f"{status_icon} ({result.duration_seconds:.1f}s)")

    total_duration = time.time() - total_start

    return ValidationReport(
        checks=results,
        total_duration=total_duration,
        passed=sum(1 for r in results if r.status == Status.PASSED),
        failed=sum(1 for r in results if r.status == Status.FAILED),
        skipped=sum(1 for r in results if r.status == Status.SKIPPED),
        errors=sum(1 for r in results if r.status == Status.ERROR),
    )


def print_report(report: ValidationReport) -> None:
    """Print a formatted validation report."""
    print("\n" + "=" * 60)
    print("VALIDATION DASHBOARD REPORT")
    print("=" * 60)

    # Summary
    success = report.failed == 0 and report.errors == 0
    status_text = "\u2705 ALL CHECKS PASSED" if success else "\u274c VALIDATION FAILED"
    print(f"\nStatus: {status_text}")
    print(f"Duration: {report.total_duration:.1f}s")
    print(f"Passed: {report.passed} | Failed: {report.failed} | Errors: {report.errors} | Skipped: {report.skipped}")

    # Details
    print("\n" + "-" * 60)
    print("CHECK DETAILS")
    print("-" * 60)

    for check in report.checks:
        status_icon = {
            Status.PASSED: "\u2705",
            Status.FAILED: "\u274c",
            Status.SKIPPED: "\u23ed",
            Status.ERROR: "\u26a0\ufe0f",
        }[check.status]
        print(f"{status_icon} {check.name}: {check.status.value} ({check.duration_seconds:.1f}s)")
        if check.status in (Status.FAILED, Status.ERROR) and check.details:
            for line in check.details.split("\n")[:5]:
                print(f"    {line}")

    print("=" * 60 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified Validation Dashboard")
    parser.add_argument("--fast", action="store_true", help="Run only fast checks")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--ci", action="store_true", help="CI mode - exit 1 on failure")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    # Run validation
    report = run_validation(fast_only=args.fast, verbose=args.verbose or not args.json)

    # Output results
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report)

    # Exit code
    if args.ci and (report.failed > 0 or report.errors > 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
