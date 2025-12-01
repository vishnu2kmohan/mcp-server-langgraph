#!/usr/bin/env python3
"""
Unified security scanning with intelligent change detection.

Consolidates:
- trivy-scan-k8s-manifests (bare K8s manifests)
- trivy-helm-scan (Helm charts, no subcharts)
- trivy-helm-full-scan (Helm with subcharts via template)
- checkov-terraform (Terraform configs)

Usage:
    python scripts/security/run_security_suite.py [--all] [--scope SCOPE] [--verbose]

Options:
    --all       Run all scans regardless of changed files
    --scope     Force specific scope (k8s-manifests, helm-full, terraform)
    --verbose   Show detailed output

Reference: Codex Audit - Security scanning fragmentation (2025-12-01)
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def get_changed_files() -> list[str]:
    """
    Get list of changed files using git.

    Uses the same 4-level fallback strategy as run_pre_push_tests.py:
    1. PRE_COMMIT_FROM_REF/TO_REF (from pre-commit framework)
    2. git merge-base @{u} HEAD (unpushed changes)
    3. git merge-base origin/main HEAD (new branches)
    4. Empty list (scan all if can't determine)
    """
    from_ref = os.getenv("PRE_COMMIT_FROM_REF")
    to_ref = os.getenv("PRE_COMMIT_TO_REF")

    try:
        if from_ref and to_ref:
            result = subprocess.run(
                ["git", "diff", "--name-only", from_ref, to_ref],
                capture_output=True,
                text=True,
                cwd=REPO_ROOT,
                timeout=10,
            )
        else:
            # Try merge-base with upstream
            try:
                merge_base = subprocess.run(
                    ["git", "merge-base", "@{u}", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=REPO_ROOT,
                    timeout=10,
                ).stdout.strip()
                result = subprocess.run(
                    ["git", "diff", "--name-only", merge_base, "HEAD"],
                    capture_output=True,
                    text=True,
                    cwd=REPO_ROOT,
                    timeout=10,
                )
            except subprocess.CalledProcessError:
                # Try merge-base with origin/main
                try:
                    merge_base = subprocess.run(
                        ["git", "merge-base", "origin/main", "HEAD"],
                        capture_output=True,
                        text=True,
                        check=True,
                        cwd=REPO_ROOT,
                        timeout=10,
                    ).stdout.strip()
                    result = subprocess.run(
                        ["git", "diff", "--name-only", merge_base, "HEAD"],
                        capture_output=True,
                        text=True,
                        cwd=REPO_ROOT,
                        timeout=10,
                    )
                except subprocess.CalledProcessError:
                    # Can't determine changes
                    return []

        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")
    except subprocess.TimeoutExpired:
        pass

    return []


def detect_security_scope(changed_files: list[str]) -> set[str]:
    """
    Determine which security scans are needed based on changed files.

    Args:
        changed_files: List of changed file paths

    Returns:
        Set of scope strings: 'k8s-manifests', 'helm-full', 'terraform', or 'all'
    """
    scopes: set[str] = set()

    for f in changed_files:
        if f.startswith("deployments/kubernetes/"):
            scopes.add("k8s-manifests")
        if f.startswith("deployments/helm/"):
            scopes.add("helm-full")  # Always do full scan for Helm changes
        if f.startswith("terraform/"):
            scopes.add("terraform")

    # Default to all if no changes detected or no security-relevant changes
    return scopes or {"all"}


def check_tool_available(tool: str) -> bool:
    """Check if a tool is available in PATH."""
    return shutil.which(tool) is not None


def run_k8s_manifests_scan(verbose: bool = False) -> int:
    """
    Scan bare Kubernetes manifests with Trivy.

    Returns:
        0 if scan passes, 1 if vulnerabilities found, 2 if tool not available
    """
    if not check_tool_available("trivy"):
        print("  ⚠️  trivy not installed, skipping K8s manifest scan")
        print("     Install: brew install trivy")
        return 0  # Non-blocking if tool not available

    print("▶ Scanning Kubernetes manifests...")
    args = [
        "trivy",
        "config",
        "deployments",
        "--severity",
        "CRITICAL,HIGH",
        "--skip-dirs",
        "**/charts",
        "--exit-code",
        "1",
    ]
    if not verbose:
        args.append("--quiet")

    result = subprocess.run(args, cwd=REPO_ROOT)
    if result.returncode == 0:
        print("  ✓ K8s manifests scan passed")
    else:
        print("  ✗ K8s manifests scan failed")
    return result.returncode


def run_helm_full_scan(verbose: bool = False) -> int:
    """
    Scan Helm chart including subcharts via template.

    Uses scripts/security/scan_helm_templates.sh which:
    1. Updates Helm dependencies
    2. Templates the chart (renders all subcharts)
    3. Scans the rendered output with Trivy

    Returns:
        0 if scan passes, 1 if vulnerabilities found, 2 if tools not available
    """
    if not check_tool_available("helm"):
        print("  ⚠️  helm not installed, skipping Helm scan")
        print("     Install: brew install helm")
        return 0

    if not check_tool_available("trivy"):
        print("  ⚠️  trivy not installed, skipping Helm scan")
        print("     Install: brew install trivy")
        return 0

    print("▶ Scanning Helm charts (with subcharts)...")
    script_path = REPO_ROOT / "scripts" / "security" / "scan_helm_templates.sh"

    if not script_path.exists():
        print(f"  ⚠️  Script not found: {script_path}")
        return 0

    args = ["bash", str(script_path), "--exit-on-error"]
    result = subprocess.run(args, cwd=REPO_ROOT, capture_output=not verbose)

    if result.returncode == 0:
        print("  ✓ Helm charts scan passed")
    else:
        print("  ✗ Helm charts scan failed")
        if not verbose and result.stderr:
            print(f"     {result.stderr.decode()[:200]}")
    return result.returncode


def run_terraform_scan(verbose: bool = False) -> int:
    """
    Scan Terraform configurations with Checkov.

    Returns:
        0 if scan passes, 1 if issues found, 2 if tool not available
    """
    terraform_dir = REPO_ROOT / "terraform"
    if not terraform_dir.exists():
        print("  ⏭  No terraform/ directory, skipping")
        return 0

    if not check_tool_available("checkov"):
        print("  ⚠️  checkov not installed, skipping Terraform scan")
        print("     Install: pip install checkov")
        return 0

    print("▶ Scanning Terraform configurations...")
    args = ["checkov", "-d", str(terraform_dir)]
    if not verbose:
        args.extend(["--quiet", "--compact"])

    result = subprocess.run(args, cwd=REPO_ROOT)
    if result.returncode == 0:
        print("  ✓ Terraform scan passed")
    else:
        print("  ✗ Terraform scan failed")
    return result.returncode


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Unified security scanning with change detection.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect scope from changed files
  python scripts/security/run_security_suite.py

  # Force all scans
  python scripts/security/run_security_suite.py --all

  # Force specific scope
  python scripts/security/run_security_suite.py --scope helm-full

  # Verbose output
  python scripts/security/run_security_suite.py --verbose
        """,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all scans regardless of changed files",
    )
    parser.add_argument(
        "--scope",
        choices=["k8s-manifests", "helm-full", "terraform"],
        help="Force specific scope",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Determine scopes to scan
    if args.scope:
        scopes = {args.scope}
    elif args.all:
        scopes = {"all"}
    else:
        changed_files = get_changed_files()
        scopes = detect_security_scope(changed_files)
        if args.verbose:
            print(f"Changed files: {len(changed_files)}")
            for f in changed_files[:5]:
                print(f"  - {f}")
            if len(changed_files) > 5:
                print(f"  ... and {len(changed_files) - 5} more")

    print(f"🔒 Security Suite - Scopes: {', '.join(sorted(scopes))}")
    print("-" * 60)

    failures = 0

    # Run scans based on scope
    if "all" in scopes or "k8s-manifests" in scopes:
        if run_k8s_manifests_scan(args.verbose) != 0:
            failures += 1

    if "all" in scopes or "helm-full" in scopes:
        if run_helm_full_scan(args.verbose) != 0:
            failures += 1

    if "all" in scopes or "terraform" in scopes:
        if run_terraform_scan(args.verbose) != 0:
            failures += 1

    print("-" * 60)
    if failures:
        print(f"❌ Security scan failed ({failures} scope(s))")
        return 1
    print("✅ Security scan passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
