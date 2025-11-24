#!/usr/bin/env python3
"""
Generate comprehensive script inventory for scripts/ directory.

Analyzes all Python and shell scripts, categorizes them by usage in:
- .pre-commit-config.yaml hooks
- Makefile targets
- GitHub Actions workflows

Updates scripts/SCRIPT_INVENTORY.md with current inventory.

Usage:
    python scripts/generate_script_inventory.py
    python scripts/generate_script_inventory.py --dry-run
    python scripts/generate_script_inventory.py --output scripts/SCRIPT_INVENTORY.md
"""

import argparse
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def get_repo_root() -> Path:
    """Get repository root directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    return Path(result.stdout.strip())


def find_all_scripts(repo_root: Path) -> dict[str, list[Path]]:
    """Find all Python and shell scripts."""
    scripts_dir = repo_root / "scripts"

    python_scripts = sorted(scripts_dir.rglob("*.py"))
    shell_scripts = sorted(scripts_dir.rglob("*.sh"))

    # Filter out __pycache__ and .pytest_cache
    python_scripts = [s for s in python_scripts if "__pycache__" not in str(s) and ".pytest_cache" not in str(s)]

    return {
        "python": python_scripts,
        "shell": shell_scripts,
        "all": sorted(python_scripts + shell_scripts),
    }


def find_hook_usage(repo_root: Path, scripts: list[Path]) -> dict[Path, list[str]]:
    """Find which scripts are used in pre-commit hooks."""
    config_path = repo_root / ".pre-commit-config.yaml"
    if not config_path.exists():
        return {}

    with open(config_path) as f:
        config_content = f.read()

    usage = {}
    for script in scripts:
        # Get script name relative to repo root
        rel_path = script.relative_to(repo_root)
        script_name = script.name

        # Search for script in config (entry: or other patterns)
        if str(rel_path) in config_content or script_name in config_content:
            # Find hook IDs that reference this script
            hook_ids = []
            lines = config_content.split("\n")
            for i, line in enumerate(lines):
                if str(rel_path) in line or script_name in line:
                    # Search backwards for "- id:" line
                    for j in range(i, max(0, i - 20), -1):
                        id_match = re.match(r"\s+- id:\s+(\S+)", lines[j])
                        if id_match:
                            hook_ids.append(id_match.group(1))
                            break

            if hook_ids:
                usage[script] = hook_ids

    return usage


def find_makefile_usage(repo_root: Path, scripts: list[Path]) -> dict[Path, list[str]]:
    """Find which scripts are used in Makefile targets."""
    makefile_path = repo_root / "Makefile"
    if not makefile_path.exists():
        return {}

    with open(makefile_path) as f:
        makefile_content = f.read()

    usage = {}
    for script in scripts:
        rel_path = script.relative_to(repo_root)
        script_name = script.name

        if str(rel_path) in makefile_content or script_name in makefile_content:
            # Find target names that reference this script
            targets = []
            lines = makefile_content.split("\n")
            current_target = None

            for line in lines:
                # Check if this is a target definition
                target_match = re.match(r"^([a-zA-Z0-9_-]+):", line)
                if target_match:
                    current_target = target_match.group(1)
                # Check if script is referenced in current context
                elif current_target and (str(rel_path) in line or script_name in line):
                    if current_target not in targets:
                        targets.append(current_target)

            if targets:
                usage[script] = targets

    return usage


def find_workflow_usage(repo_root: Path, scripts: list[Path]) -> dict[Path, list[str]]:
    """Find which scripts are used in GitHub Actions workflows."""
    workflows_dir = repo_root / ".github" / "workflows"
    if not workflows_dir.exists():
        return {}

    usage = {}
    workflow_files = list(workflows_dir.glob("*.yaml")) + list(workflows_dir.glob("*.yml"))

    for script in scripts:
        rel_path = script.relative_to(repo_root)
        script_name = script.name
        workflows_using = []

        for workflow_file in workflow_files:
            with open(workflow_file) as f:
                content = f.read()

            if str(rel_path) in content or script_name in content:
                workflows_using.append(workflow_file.stem)

        if workflows_using:
            usage[script] = workflows_using

    return usage


def categorize_scripts(
    scripts: list[Path],
    hook_usage: dict,
    makefile_usage: dict,
    workflow_usage: dict,
) -> dict[str, list[Path]]:
    """Categorize scripts by usage pattern."""
    categories = {
        "multi_system": [],  # Used in multiple systems (hooks + make + workflows)
        "hooks_only": [],
        "makefile_only": [],
        "workflows_only": [],
        "hooks_makefile": [],  # Dual usage
        "hooks_workflows": [],  # Dual usage
        "makefile_workflows": [],  # Dual usage
        "unused": [],
    }

    for script in scripts:
        in_hooks = script in hook_usage
        in_makefile = script in makefile_usage
        in_workflows = script in workflow_usage

        usage_count = sum([in_hooks, in_makefile, in_workflows])

        if usage_count == 0:
            categories["unused"].append(script)
        elif usage_count == 3:
            categories["multi_system"].append(script)
        elif usage_count == 2:
            if in_hooks and in_makefile:
                categories["hooks_makefile"].append(script)
            elif in_hooks and in_workflows:
                categories["hooks_workflows"].append(script)
            else:
                categories["makefile_workflows"].append(script)
        elif in_hooks:
            categories["hooks_only"].append(script)
        elif in_makefile:
            categories["makefile_only"].append(script)
        else:
            categories["workflows_only"].append(script)

    return categories


def generate_inventory(
    scripts: dict,
    hook_usage: dict,
    makefile_usage: dict,
    workflow_usage: dict,
    categories: dict,
) -> str:
    """Generate markdown inventory document."""
    total = len(scripts["all"])
    python_count = len(scripts["python"])
    shell_count = len(scripts["shell"])

    used_count = total - len(categories["unused"])
    unused_count = len(categories["unused"])

    content = f"""# Scripts Directory Inventory

**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Auto-generated** by `scripts/generate_script_inventory.py`
**Total Scripts**: {total}
**Python Scripts**: {python_count}
**Shell Scripts**: {shell_count}
**Actively Used**: {used_count} ({used_count/total*100:.1f}%)
**Unused/Utilities**: {unused_count} ({unused_count/total*100:.1f}%)

---

## Executive Summary

| Category | Count | Percentage | Description |
|----------|-------|------------|-------------|
| **Multi-System** | {len(categories["multi_system"])} | {len(categories["multi_system"])/total*100:.1f}% | Used in hooks + Makefile + workflows |
| **Hooks + Makefile** | {len(categories["hooks_makefile"])} | {len(categories["hooks_makefile"])/total*100:.1f}% | Dual integration (hooks + Make) |
| **Hooks + Workflows** | {len(categories["hooks_workflows"])} | {len(categories["hooks_workflows"])/total*100:.1f}% | Dual integration (hooks + CI/CD) |
| **Makefile + Workflows** | {len(categories["makefile_workflows"])} | {len(categories["makefile_workflows"])/total*100:.1f}% | Dual integration (Make + CI/CD) |
| **Hooks Only** | {len(categories["hooks_only"])} | {len(categories["hooks_only"])/total*100:.1f}% | Pre-commit hooks only |
| **Makefile Only** | {len(categories["makefile_only"])} | {len(categories["makefile_only"])/total*100:.1f}% | Makefile targets only |
| **Workflows Only** | {len(categories["workflows_only"])} | {len(categories["workflows_only"])/total*100:.1f}% | GitHub Actions only |
| **Unused/Utilities** | {unused_count} | {unused_count/total*100:.1f}% | Not referenced in active systems |

---

## CRITICAL Scripts (Multi-System Integration)

These scripts are used across multiple systems and are essential for the project.

"""

    if categories["multi_system"]:
        content += "| Script | Hook IDs | Makefile Targets | Workflows |\n"
        content += "|--------|----------|------------------|----------|\n"
        for script in sorted(categories["multi_system"]):
            script_name = script.name
            hooks = ", ".join(hook_usage.get(script, []))
            make_targets = ", ".join(makefile_usage.get(script, []))
            workflows = ", ".join(workflow_usage.get(script, []))
            content += f"| `{script_name}` | {hooks} | {make_targets} | {workflows} |\n"
    else:
        content += "*No scripts found*\n"

    content += "\n---\n\n## Dual Integration Scripts\n\n"

    # Hooks + Makefile
    if categories["hooks_makefile"]:
        content += "### Hooks + Makefile\n\n"
        content += "| Script | Hook IDs | Makefile Targets |\n"
        content += "|--------|----------|------------------|\n"
        for script in sorted(categories["hooks_makefile"]):
            script_name = script.name
            hooks = ", ".join(hook_usage.get(script, []))
            make_targets = ", ".join(makefile_usage.get(script, []))
            content += f"| `{script_name}` | {hooks} | {make_targets} |\n"
        content += "\n"

    # Hooks + Workflows
    if categories["hooks_workflows"]:
        content += "### Hooks + Workflows\n\n"
        content += "| Script | Hook IDs | Workflows |\n"
        content += "|--------|----------|----------|\n"
        for script in sorted(categories["hooks_workflows"]):
            script_name = script.name
            hooks = ", ".join(hook_usage.get(script, []))
            workflows = ", ".join(workflow_usage.get(script, []))
            content += f"| `{script_name}` | {hooks} | {workflows} |\n"
        content += "\n"

    # Makefile + Workflows
    if categories["makefile_workflows"]:
        content += "### Makefile + Workflows\n\n"
        content += "| Script | Makefile Targets | Workflows |\n"
        content += "|--------|------------------|----------|\n"
        for script in sorted(categories["makefile_workflows"]):
            script_name = script.name
            make_targets = ", ".join(makefile_usage.get(script, []))
            workflows = ", ".join(workflow_usage.get(script, []))
            content += f"| `{script_name}` | {make_targets} | {workflows} |\n"
        content += "\n"

    content += "---\n\n## Single-System Integration Scripts\n\n"

    # Hooks Only
    if categories["hooks_only"]:
        content += f"### Pre-Commit Hooks Only ({len(categories['hooks_only'])} scripts)\n\n"
        content += "| Script | Hook IDs |\n"
        content += "|--------|----------|\n"
        for script in sorted(categories["hooks_only"])[:20]:  # Show first 20
            script_name = script.name
            hooks = ", ".join(hook_usage.get(script, []))
            content += f"| `{script_name}` | {hooks} |\n"
        if len(categories["hooks_only"]) > 20:
            content += f"\n*... and {len(categories['hooks_only']) - 20} more scripts*\n"
        content += "\n"

    # Makefile Only
    if categories["makefile_only"]:
        content += f"### Makefile Only ({len(categories['makefile_only'])} scripts)\n\n"
        content += "| Script | Makefile Targets |\n"
        content += "|--------|------------------|\n"
        for script in sorted(categories["makefile_only"])[:20]:
            script_name = script.name
            make_targets = ", ".join(makefile_usage.get(script, []))
            content += f"| `{script_name}` | {make_targets} |\n"
        if len(categories["makefile_only"]) > 20:
            content += f"\n*... and {len(categories['makefile_only']) - 20} more scripts*\n"
        content += "\n"

    # Workflows Only
    if categories["workflows_only"]:
        content += f"### GitHub Actions Workflows Only ({len(categories['workflows_only'])} scripts)\n\n"
        content += "| Script | Workflows |\n"
        content += "|--------|----------|\n"
        for script in sorted(categories["workflows_only"])[:20]:
            script_name = script.name
            workflows = ", ".join(workflow_usage.get(script, []))
            content += f"| `{script_name}` | {workflows} |\n"
        if len(categories["workflows_only"]) > 20:
            content += f"\n*... and {len(categories['workflows_only']) - 20} more scripts*\n"
        content += "\n"

    content += f"""---

## Unused/Utility Scripts ({unused_count} scripts)

These scripts are not referenced in .pre-commit-config.yaml, Makefile, or GitHub Actions workflows.

**Categories**:
- One-time fix/migration scripts (candidates for archival)
- Development analysis tools (keep as utilities)
- Infrastructure setup scripts (evaluate individually)

### Analysis by Directory

"""

    # Group unused scripts by directory
    unused_by_dir = defaultdict(list)
    for script in categories["unused"]:
        parent = script.parent.name
        unused_by_dir[parent].append(script.name)

    for directory in sorted(unused_by_dir.keys()):
        scripts_in_dir = unused_by_dir[directory]
        content += f"**{directory}/**: {len(scripts_in_dir)} scripts\n"
        if len(scripts_in_dir) <= 10:
            for script_name in sorted(scripts_in_dir):
                content += f"  - `{script_name}`\n"
        else:
            for script_name in sorted(scripts_in_dir)[:5]:
                content += f"  - `{script_name}`\n"
            content += f"  - *... and {len(scripts_in_dir) - 5} more*\n"
        content += "\n"

    content += """---

## Recommendations

### Phase 5.2: Archive Unused Scripts
- Move one-time fix/migration scripts to `scripts/archive/completed/`
- Archive scripts with `add_*` or `fix_*` naming patterns
- Keep development analysis tools in `scripts/dev/`

### Phase 5.3: Add Tests for Critical Scripts
- Priority: Multi-system integration scripts (highest impact)
- Target: 80%+ coverage for CRITICAL scripts
- Use `tests/meta/test_scripts_governance.py` as template

### Phase 5.4: Audit Workflows for Duplication
- Review 29 workflow files for redundant script calls
- Consolidate duplicate validation logic
- Create composite actions for common patterns

---

## Maintenance

**Audit Frequency**: Quarterly (every 3 months)
**Regenerate**: Run `python scripts/generate_script_inventory.py`
**Auto-update**: Add to pre-commit hooks or monthly cron job

---

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**By**: scripts/generate_script_inventory.py
**Commit**: {subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, timeout=5).stdout.strip()}
"""

    return content


def main():
    parser = argparse.ArgumentParser(description="Generate script inventory")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout instead of writing file")
    parser.add_argument("--output", default="scripts/SCRIPT_INVENTORY.md", help="Output file path")
    args = parser.parse_args()

    repo_root = get_repo_root()

    print("🔍 Scanning scripts directory...")
    scripts = find_all_scripts(repo_root)
    print(f"   Found {len(scripts['all'])} scripts ({len(scripts['python'])} Python, {len(scripts['shell'])} Shell)")

    print("🔍 Analyzing pre-commit hook usage...")
    hook_usage = find_hook_usage(repo_root, scripts["all"])
    print(f"   Found {len(hook_usage)} scripts used in hooks")

    print("🔍 Analyzing Makefile usage...")
    makefile_usage = find_makefile_usage(repo_root, scripts["all"])
    print(f"   Found {len(makefile_usage)} scripts used in Makefile")

    print("🔍 Analyzing GitHub Actions workflow usage...")
    workflow_usage = find_workflow_usage(repo_root, scripts["all"])
    print(f"   Found {len(workflow_usage)} scripts used in workflows")

    print("📊 Categorizing scripts...")
    categories = categorize_scripts(scripts["all"], hook_usage, makefile_usage, workflow_usage)

    print("\n📋 Summary:")
    print(f"   Multi-system: {len(categories['multi_system'])}")
    print(
        f"   Dual integration: {len(categories['hooks_makefile']) + len(categories['hooks_workflows']) + len(categories['makefile_workflows'])}"
    )
    print(
        f"   Single system: {len(categories['hooks_only']) + len(categories['makefile_only']) + len(categories['workflows_only'])}"
    )
    print(f"   Unused/Utilities: {len(categories['unused'])}")

    print("\n📝 Generating inventory document...")
    inventory = generate_inventory(scripts, hook_usage, makefile_usage, workflow_usage, categories)

    if args.dry_run:
        print("\n" + "=" * 80)
        print(inventory)
    else:
        output_path = repo_root / args.output
        output_path.write_text(inventory)
        print(f"\n✅ Inventory written to: {output_path}")
        print(f"   Total scripts: {len(scripts['all'])}")
        print(
            f"   Used: {len(scripts['all']) - len(categories['unused'])} ({(len(scripts['all']) - len(categories['unused']))/len(scripts['all'])*100:.1f}%)"
        )
        print(f"   Unused: {len(categories['unused'])} ({len(categories['unused'])/len(scripts['all'])*100:.1f}%)")


if __name__ == "__main__":
    main()
