#!/usr/bin/env python3
"""
Production Deployment Validation Script

Validates that the codebase is ready for production deployment.
Run this before deploying to production environments.

Usage:
    python scripts/validate_production.py
    python scripts/validate_production.py --strict
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class ValidationResult:
    def __init__(self):
        self.passed: List[str] = []
        self.failed: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def add_pass(self, message: str):
        self.passed.append(message)
        print(f"{GREEN}✓{RESET} {message}")

    def add_fail(self, message: str):
        self.failed.append(message)
        print(f"{RED}✗{RESET} {message}")

    def add_warning(self, message: str):
        self.warnings.append(message)
        print(f"{YELLOW}⚠{RESET} {message}")

    def add_info(self, message: str):
        self.info.append(message)
        print(f"{BLUE}ℹ{RESET} {message}")

    def summary(self) -> Dict[str, int]:
        return {
            "passed": len(self.passed),
            "failed": len(self.failed),
            "warnings": len(self.warnings),
            "info": len(self.info),
        }

    def is_production_ready(self, strict: bool = False) -> bool:
        if self.failed:
            return False
        if strict and self.warnings:
            return False
        return True


def check_git_repository(result: ValidationResult) -> None:
    """Check if git repository is initialized"""
    print(f"\n{BOLD}Checking Git Repository...{RESET}")

    if (Path.cwd() / ".git").exists():
        result.add_pass("Git repository initialized")

        # Check for uncommitted changes
        try:
            output = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
            if output.stdout.strip():
                result.add_warning("Uncommitted changes detected")
            else:
                result.add_pass("No uncommitted changes")
        except subprocess.CalledProcessError:
            result.add_warning("Could not check git status")
    else:
        result.add_fail("Git repository not initialized (run: git init)")


def check_required_files(result: ValidationResult) -> None:
    """Check for required production files"""
    print(f"\n{BOLD}Checking Required Files...{RESET}")

    required_files = [
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
        ".gitignore",
        "requirements.txt",
        "requirements-pinned.txt",
        "pyproject.toml",
        "Dockerfile",
        "docker-compose.yml",
        ".env.example",
        "PRODUCTION_DEPLOYMENT.md",
        "SECURITY_AUDIT.md",
    ]

    for file in required_files:
        if Path(file).exists():
            result.add_pass(f"Found {file}")
        else:
            result.add_fail(f"Missing {file}")


def check_secrets_configuration(result: ValidationResult) -> None:
    """Check that secrets are properly configured"""
    print(f"\n{BOLD}Checking Secrets Configuration...{RESET}")

    # Check .env file exists but not committed
    if Path(".env").exists():
        result.add_warning(".env file exists - ensure it's not committed to git")

    # Check .gitignore includes .env
    if Path(".gitignore").exists():
        gitignore = Path(".gitignore").read_text()
        if ".env" in gitignore and "!.env.example" in gitignore:
            result.add_pass(".gitignore properly configured for secrets")
        else:
            result.add_fail(".gitignore missing .env protection")

    # Check for default secrets in code
    dangerous_patterns = [
        (r"jwt.*secret.*=.*['\"]change", "Default JWT secret detected"),
        (r"api.*key.*=.*['\"]sk-", "Hardcoded API key detected"),
        (r"password.*=.*['\"]password", "Default password detected"),
        (r"secret.*=.*['\"]secret", "Default secret detected"),
    ]

    python_files = list(Path(".").glob("**/*.py"))
    python_files = [f for f in python_files if "venv" not in str(f) and "test" not in str(f)]

    found_issues = False
    for file in python_files:
        content = file.read_text()
        for pattern, message in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                result.add_warning(f"{message} in {file}")
                found_issues = True

    if not found_issues:
        result.add_pass("No hardcoded secrets detected in code")


def check_production_status(result: ValidationResult) -> None:
    """Check production readiness markers"""
    print(f"\n{BOLD}Checking Production Status...{RESET}")

    # Check pyproject.toml for production status
    if Path("pyproject.toml").exists():
        content = Path("pyproject.toml").read_text()
        if "Development Status :: 5 - Production/Stable" in content:
            result.add_pass("Package marked as Production/Stable")
        elif "Development Status :: 4 - Beta" in content:
            result.add_warning("Package still marked as Beta")
        else:
            result.add_fail("Package development status unclear")

        # Check for placeholder values
        if "vishnu2kmohan" in content or "example.com" in content:
            result.add_warning("Placeholder organization names in pyproject.toml")


def check_kubernetes_configuration(result: ValidationResult) -> None:
    """Check Kubernetes deployment files"""
    print(f"\n{BOLD}Checking Kubernetes Configuration...{RESET}")

    k8s_dirs = ["kubernetes", "helm", "kustomize"]
    found_k8s = False

    for dir_name in k8s_dirs:
        if Path(dir_name).exists():
            found_k8s = True
            result.add_pass(f"Found {dir_name} deployment configuration")

    if not found_k8s:
        result.add_warning("No Kubernetes deployment configuration found")

    # Check for production-specific configurations
    if Path("helm/langgraph-agent/values.yaml").exists():
        result.add_pass("Helm chart values found")

    if Path("kubernetes/base").exists():
        base_files = ["deployment.yaml", "service.yaml", "configmap.yaml", "secret.yaml"]
        for file in base_files:
            if Path(f"kubernetes/base/{file}").exists():
                result.add_pass(f"Found kubernetes/base/{file}")


def check_docker_configuration(result: ValidationResult) -> None:
    """Check Docker configuration"""
    print(f"\n{BOLD}Checking Docker Configuration...{RESET}")

    if Path("Dockerfile").exists():
        content = Path("Dockerfile").read_text()

        # Check for multi-stage build
        if "FROM" in content and content.count("FROM") >= 2:
            result.add_pass("Multi-stage Dockerfile detected")
        else:
            result.add_warning("Consider using multi-stage Docker build")

        # Check for non-root user
        if "USER" in content and "root" not in content.lower():
            result.add_pass("Non-root user configured in Dockerfile")
        else:
            result.add_fail("Dockerfile should use non-root user")

        # Check for health check
        if "HEALTHCHECK" in content:
            result.add_pass("Health check configured in Dockerfile")
        else:
            result.add_warning("Consider adding HEALTHCHECK to Dockerfile")
    else:
        result.add_fail("Dockerfile not found")

    # Check .dockerignore
    if Path(".dockerignore").exists():
        result.add_pass(".dockerignore file exists")
        content = Path(".dockerignore").read_text()
        if ".env" in content:
            result.add_pass(".dockerignore excludes .env files")
    else:
        result.add_warning(".dockerignore file missing")


def check_tests(result: ValidationResult) -> None:
    """Check test configuration and coverage"""
    print(f"\n{BOLD}Checking Tests...{RESET}")

    if Path("tests").exists():
        test_files = list(Path("tests").glob("test_*.py"))
        if test_files:
            result.add_pass(f"Found {len(test_files)} test files")
        else:
            result.add_fail("No test files found in tests/")
    else:
        result.add_fail("tests/ directory not found")

    # Check for test configuration
    if Path("pytest.ini").exists() or Path("pyproject.toml").exists():
        result.add_pass("Test configuration found")

    # Try to run tests
    result.add_info("Run 'make test' or 'pytest' to verify all tests pass")


def check_ci_cd(result: ValidationResult) -> None:
    """Check CI/CD configuration"""
    print(f"\n{BOLD}Checking CI/CD Configuration...{RESET}")

    ci_files = [
        ".github/workflows/ci.yaml",
        ".gitlab-ci.yml",
        "Jenkinsfile",
        ".circleci/config.yml",
    ]

    found_ci = False
    for ci_file in ci_files:
        if Path(ci_file).exists():
            result.add_pass(f"Found CI/CD configuration: {ci_file}")
            found_ci = True

    if not found_ci:
        result.add_warning("No CI/CD configuration found")


def check_security(result: ValidationResult) -> None:
    """Run security checks"""
    print(f"\n{BOLD}Checking Security...{RESET}")

    # Check if bandit is available
    try:
        output = subprocess.run(["bandit", "--version"], capture_output=True, check=False)
        if output.returncode == 0:
            result.add_info("Run 'bandit -r . -x ./tests,./venv -ll' for security scan")
        else:
            result.add_warning("Bandit not installed (pip install bandit)")
    except FileNotFoundError:
        result.add_warning("Bandit not installed (pip install bandit)")

    # Check for security documentation
    if Path("SECURITY_AUDIT.md").exists():
        result.add_pass("Security audit documentation found")
    else:
        result.add_warning("SECURITY_AUDIT.md not found")


def check_dependencies(result: ValidationResult) -> None:
    """Check dependency management"""
    print(f"\n{BOLD}Checking Dependencies...{RESET}")

    if Path("requirements-pinned.txt").exists():
        result.add_pass("Pinned requirements found")

        # Check if versions are actually pinned
        content = Path("requirements-pinned.txt").read_text()
        lines = [l.strip() for l in content.split("\n") if l.strip() and not l.startswith("#")]
        unpinned = [l for l in lines if "==" not in l]

        if unpinned:
            result.add_warning(f"{len(unpinned)} dependencies not pinned with ==")
        else:
            result.add_pass("All dependencies pinned with exact versions")
    else:
        result.add_warning("requirements-pinned.txt not found")

    result.add_info("Run 'pip-audit' to check for known vulnerabilities")


def check_documentation(result: ValidationResult) -> None:
    """Check documentation completeness"""
    print(f"\n{BOLD}Checking Documentation...{RESET}")

    docs = [
        ("README.md", "Main documentation"),
        ("CHANGELOG.md", "Version history"),
        ("PRODUCTION_DEPLOYMENT.md", "Production deployment guide"),
        ("SECURITY_AUDIT.md", "Security checklist"),
        ("TESTING.md", "Testing guide"),
        ("LICENSE", "License file"),
    ]

    for doc, description in docs:
        if Path(doc).exists():
            result.add_pass(f"Found {description}: {doc}")
        else:
            result.add_warning(f"Missing {description}: {doc}")


def main():
    """Main validation function"""
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}MCP Server with LangGraph - Production Readiness Validation{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

    strict = "--strict" in sys.argv
    if strict:
        print(f"{YELLOW}Running in STRICT mode (warnings treated as errors){RESET}\n")

    result = ValidationResult()

    # Run all checks
    check_git_repository(result)
    check_required_files(result)
    check_secrets_configuration(result)
    check_production_status(result)
    check_docker_configuration(result)
    check_kubernetes_configuration(result)
    check_tests(result)
    check_ci_cd(result)
    check_security(result)
    check_dependencies(result)
    check_documentation(result)

    # Print summary
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}Validation Summary{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

    summary = result.summary()
    print(f"{GREEN}✓ Passed:{RESET}   {summary['passed']}")
    print(f"{RED}✗ Failed:{RESET}   {summary['failed']}")
    print(f"{YELLOW}⚠ Warnings:{RESET} {summary['warnings']}")
    print(f"{BLUE}ℹ Info:{RESET}     {summary['info']}")

    # Determine production readiness
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    if result.is_production_ready(strict):
        print(f"{BOLD}{GREEN}✓ PRODUCTION READY{RESET}")
        print(f"\nThis codebase meets production deployment standards.")
        if summary["warnings"] > 0:
            print(f"Address {summary['warnings']} warnings before deployment.")
        sys.exit(0)
    else:
        print(f"{BOLD}{RED}✗ NOT PRODUCTION READY{RESET}")
        print(f"\nPlease address the following before deploying to production:")
        print(f"  - {summary['failed']} critical issues")
        if strict:
            print(f"  - {summary['warnings']} warnings (strict mode)")
        print(f"\nReview the failures above and re-run this script.")
        sys.exit(1)


if __name__ == "__main__":
    main()
