#!/usr/bin/env python3
"""Validate YAML frontmatter in all skills and command files.

Checks:
  - YAML frontmatter is parseable
  - Required fields present (name/description for skills, description for commands)
  - allowed-tools present
  - Description follows WHAT+WHEN pattern (contains "Use when" or "Use for" or "Use before")
  - Stubs reference a valid SKILL.md path
  - Line count thresholds (commands <300 lines, skills <500 lines)
  - disable-model-invocation present on known side-effect commands

Usage:
  uv run --frozen scripts/validate_skills.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# Side-effect commands that MUST have disable-model-invocation: true
SIDE_EFFECT_COMMANDS = {
    "deploy",
    "deploy-dev",
    "db-operations",
    "cleanup-worktrees",
    "start-sprint",
    "release-prep",
    "setup-env",
}

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WHEN_PATTERN = re.compile(r"Use (when|for|before|after|during|to )", re.IGNORECASE)


def parse_frontmatter(path: Path) -> tuple[dict | None, str]:
    """Extract YAML frontmatter from a markdown file."""
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML not installed. Run: uv add pyyaml", file=sys.stderr)
        sys.exit(2)

    content = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(content)
    if not match:
        return None, content

    try:
        data = yaml.safe_load(match.group(1))
        return data if isinstance(data, dict) else None, content
    except yaml.YAMLError as e:
        print(f"  YAML ERROR: {e}")
        return None, content


def validate_command(path: Path, errors: list[str], warnings: list[str]) -> None:
    """Validate a command .md file."""
    name = path.stem
    data, content = parse_frontmatter(path)
    line_count = content.count("\n") + 1

    if data is None:
        errors.append(f"{path}: No valid YAML frontmatter found")
        return

    # Required: description
    desc = data.get("description", "")
    if not desc:
        errors.append(f"{path}: Missing 'description' field")
    elif not WHEN_PATTERN.search(desc):
        warnings.append(f"{path}: Description missing WHEN clause (add 'Use when...')")

    # Required: allowed-tools
    if "allowed-tools" not in data:
        errors.append(f"{path}: Missing 'allowed-tools' field")

    # Side-effect commands must have disable-model-invocation
    if name in SIDE_EFFECT_COMMANDS and not data.get("disable-model-invocation"):
        errors.append(f"{path}: Side-effect command missing 'disable-model-invocation: true'")

    # Stubs should be short
    is_stub = "See skill:" in content or "migrated to a skill" in content
    if is_stub:
        if line_count > 30:
            warnings.append(f"{path}: Stub is {line_count} lines (expected <30)")
        # Verify referenced skill exists
        skill_ref = re.search(r"\.claude/skills/(\S+)/SKILL\.md", content)
        if skill_ref:
            skill_path = path.parent.parent / "skills" / skill_ref.group(1) / "SKILL.md"
            if not skill_path.exists():
                errors.append(f"{path}: References non-existent skill at {skill_path}")
    elif line_count > 300:
        warnings.append(f"{path}: Command is {line_count} lines (consider migrating to skill)")


def validate_skill(path: Path, errors: list[str], warnings: list[str]) -> None:
    """Validate a SKILL.md file."""
    data, content = parse_frontmatter(path)
    line_count = content.count("\n") + 1

    if data is None:
        errors.append(f"{path}: No valid YAML frontmatter found")
        return

    # Required: name
    if not data.get("name"):
        errors.append(f"{path}: Missing 'name' field")

    # Required: description
    desc = data.get("description", "")
    if not desc:
        errors.append(f"{path}: Missing 'description' field")
    elif not WHEN_PATTERN.search(desc):
        warnings.append(f"{path}: Description missing WHEN clause (add 'Use when...')")

    # Recommended: allowed-tools
    if "allowed-tools" not in data:
        warnings.append(f"{path}: Missing 'allowed-tools' field")

    # Line count check
    if line_count > 500:
        warnings.append(f"{path}: SKILL.md is {line_count} lines (recommended <500)")

    # Check for references/ directory if skill is large
    refs_dir = path.parent / "references"
    if line_count > 300 and not refs_dir.exists():
        warnings.append(f"{path}: Large skill ({line_count}L) without references/ directory")


def main() -> int:
    """Run validation across all skills and commands."""
    project_root = Path(__file__).resolve().parent.parent
    errors: list[str] = []
    warnings: list[str] = []
    command_files: list[Path] = []
    skill_files: list[Path] = []
    root_skill_files: list[Path] = []

    # Validate .claude/commands/*.md (excluding README.md)
    commands_dir = project_root / ".claude" / "commands"
    if commands_dir.exists():
        command_files = sorted(p for p in commands_dir.glob("*.md") if p.name != "README.md")
        print(f"Validating {len(command_files)} commands in .claude/commands/...")
        for path in command_files:
            validate_command(path, errors, warnings)

    # Validate .claude/skills/*/SKILL.md (project skills)
    project_skills_dir = project_root / ".claude" / "skills"
    if project_skills_dir.exists():
        skill_files = sorted(project_skills_dir.glob("*/SKILL.md"))
        print(f"Validating {len(skill_files)} project skills in .claude/skills/...")
        for path in skill_files:
            validate_skill(path, errors, warnings)

    # Validate skills/*/SKILL.md (root skills)
    root_skills_dir = project_root / "skills"
    if root_skills_dir.exists():
        root_skill_files = sorted(root_skills_dir.glob("*/SKILL.md"))
        print(f"Validating {len(root_skill_files)} root skills in skills/...")
        for path in root_skill_files:
            validate_skill(path, errors, warnings)

    # Print results
    print()
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  W: {w}")
        print()

    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  E: {e}")
        print()
        print("FAILED")
        return 1

    total = len(command_files) + len(skill_files) + len(root_skill_files)
    print(f"ALL PASSED: {total} files validated, {len(warnings)} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
