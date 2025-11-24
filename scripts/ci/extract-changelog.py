#!/usr/bin/env python3
"""
CHANGELOG Extractor for GitHub Releases

Extracts version-specific content from CHANGELOG.md for release notes.
Extracted from .github/workflows/release.yaml for maintainability.

Usage:
    python scripts/ci/extract-changelog.py VERSION [--changelog PATH] [--output PATH]

Example:
    python scripts/ci/extract-changelog.py v2.8.0
    python scripts/ci/extract-changelog.py 2.8.0 --changelog CHANGELOG.md --output release_notes.md

Exit codes:
    0 - CHANGELOG section found
    1 - No CHANGELOG section found (generates fallback)
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def extract_changelog_section(version, changelog_path="CHANGELOG.md"):
    """Extract the section for a specific version from CHANGELOG.md"""
    version_no_v = version.lstrip("v")
    version_escaped = re.escape(version_no_v)

    changelog_file = Path(changelog_path)
    if not changelog_file.exists():
        print(f"⚠️  CHANGELOG file not found: {changelog_path}")
        return None, False

    with open(changelog_file, encoding="utf-8") as f:
        content = f.read()

    # Extract section between "## [VERSION]" and next "---"
    pattern = rf"^## \[{version_escaped}\].*?^---$"
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)

    if match:
        section = match.group(0)
        # Remove the trailing "---"
        section = section.rsplit("---", 1)[0].strip()

        # Basic validation - should have more than just the header
        if len(section.split("\n")) > 5:
            return section, True

    return None, False


def generate_fallback_notes(version, repository):
    """Generate fallback release notes from git commits"""
    try:
        # Get previous tag
        previous_tag_cmd = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0", "HEAD^"], capture_output=True, text=True, timeout=10
        )

        if previous_tag_cmd.returncode == 0:
            previous_tag = previous_tag_cmd.stdout.strip()
            # Get commits between tags
            log_cmd = subprocess.run(
                ["git", "log", f"{previous_tag}..HEAD", "--pretty=format:- %s (%h)", "--no-merges"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            commits = log_cmd.stdout
        else:
            # Get recent commits if no previous tag
            log_cmd = subprocess.run(
                ["git", "log", "--pretty=format:- %s (%h)", "--no-merges", "--max-count=20"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            commits = log_cmd.stdout

        notes = f"""## Changes in this Release

{commits}

## Docker Images

```bash
docker pull ghcr.io/{repository}:{version}
docker pull ghcr.io/{repository}:latest
```

## Documentation

- [Installation Guide](README.md)
- [Kubernetes Deployment](docs/deployment/kubernetes.md)
"""
        return notes

    except Exception as e:
        print(f"⚠️  Error generating fallback notes: {e}")
        return f"""## Release {version}

See the full changelog for details.
"""


def add_deployment_info(notes, version, repository):
    """Add deployment information to release notes"""
    deployment_section = f"""

## 🚀 Quick Start

### Docker Images

Pull the latest release:

```bash
docker pull ghcr.io/{repository}:{version}
docker pull ghcr.io/{repository}:latest
```

### Helm Deployment

Install with Helm:

```bash
helm upgrade --install mcp-server-langgraph \\
  oci://ghcr.io/{repository}/charts/mcp-server-langgraph \\
  --version {version}
```

## 📚 Documentation

- [Installation Guide](README.md)
- [Kubernetes Deployment](docs/deployment/kubernetes.md)
- [Testing Guide](docs/development/testing.md)
- [Release Process](docs/deployment/RELEASE_PROCESS.md)
"""
    return notes + deployment_section


def main():
    parser = argparse.ArgumentParser(description="Extract CHANGELOG section for release")
    parser.add_argument("version", help="Version to extract (e.g., v2.8.0 or 2.8.0)")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="Path to CHANGELOG file")
    parser.add_argument("--output", default="release_notes.md", help="Output file path")
    parser.add_argument("--repository", help="GitHub repository (e.g., owner/repo)")

    args = parser.parse_args()

    # Get repository from git if not provided
    if not args.repository:
        try:
            remote_cmd = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True, timeout=5
            )
            if remote_cmd.returncode == 0:
                # Extract owner/repo from git URL
                remote_url = remote_cmd.stdout.strip()
                match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote_url)
                if match:
                    args.repository = match.group(1)
        except Exception:
            pass

    if not args.repository:
        args.repository = "unknown/repository"

    version = args.version.lstrip("v")
    version_tag = f"v{version}"

    print(f"Extracting CHANGELOG section for version: {version}")

    section, found = extract_changelog_section(version, args.changelog)

    if found and section:
        print(f"✅ Found CHANGELOG content ({len(section.split())} words)")
        notes = add_deployment_info(section, version_tag, args.repository)
        has_changelog = True
    else:
        print("⚠️  No CHANGELOG content found, generating fallback from git commits")
        notes = generate_fallback_notes(version_tag, args.repository)
        has_changelog = False

    # Write to output file
    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(notes)

    print(f"📝 Release notes written to: {output_path}")
    print(f"   Has CHANGELOG: {has_changelog}")

    # Exit with code indicating whether CHANGELOG was found
    sys.exit(0 if has_changelog else 1)


if __name__ == "__main__":
    main()
