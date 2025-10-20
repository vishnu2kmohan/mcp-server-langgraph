#!/usr/bin/env python3
"""
Auto-update Claude Code context files from repository state.

This script automatically updates context files in .claude/context/ by analyzing:
- Git commit history (recent-work.md)
- Test file patterns (testing-patterns.md - optional, can be slow)
- Code patterns (code-patterns.md - optional, can be slow)

Usage:
    python scripts/workflow/update-context-files.py                 # Update all
    python scripts/workflow/update-context-files.py --recent-work   # Only recent-work.md
    python scripts/workflow/update-context-files.py --quick         # Fast update (recent-work only)

Can be called from:
- Git hooks (post-commit, post-merge)
- Slash commands (/refresh-context)
- Makefile (make update-context)
- Manual execution
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


def get_repo_root() -> Path:
    """Get repository root directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        print("ERROR: Not in a git repository", file=sys.stderr)
        sys.exit(1)


def run_git_command(args: List[str], timeout: int = 10) -> str:
    """Run git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Git command failed: {e}", file=sys.stderr)
        return ""


def get_recent_commits(count: int = 15) -> List[Dict[str, str]]:
    """Get recent commits with metadata."""
    log_format = "%H|%an|%ae|%ad|%s"
    log_output = run_git_command(
        [
            "log",
            f"-n{count}",
            f"--format={log_format}",
            "--date=short",
        ]
    )

    commits = []
    for line in log_output.split("\n"):
        if not line:
            continue
        parts = line.split("|", 4)
        if len(parts) == 5:
            commits.append(
                {
                    "hash": parts[0][:7],
                    "author": parts[1],
                    "email": parts[2],
                    "date": parts[3],
                    "message": parts[4],
                }
            )

    return commits


def categorize_commit(message: str) -> str:
    """Categorize commit by type."""
    msg_lower = message.lower()

    if msg_lower.startswith("feat"):
        return "✨ Feature"
    elif msg_lower.startswith("fix"):
        return "🐛 Bug Fix"
    elif msg_lower.startswith("test"):
        return "🧪 Test"
    elif msg_lower.startswith("docs"):
        return "📝 Documentation"
    elif msg_lower.startswith("refactor"):
        return "♻️  Refactor"
    elif msg_lower.startswith("perf"):
        return "⚡ Performance"
    elif msg_lower.startswith("chore"):
        return "🔧 Chore"
    elif msg_lower.startswith("ci"):
        return "👷 CI/CD"
    elif msg_lower.startswith("style"):
        return "💄 Style"
    else:
        return "🔹 Other"


def get_recent_files(since_days: int = 7) -> List[Tuple[str, int]]:
    """Get recently modified files with change frequency."""
    log_output = run_git_command(
        [
            "log",
            f"--since={since_days}.days.ago",
            "--name-only",
            "--pretty=format:",
        ]
    )

    # Count file modifications
    file_counts: Dict[str, int] = {}
    for line in log_output.split("\n"):
        if line and not line.startswith(" "):
            file_counts[line] = file_counts.get(line, 0) + 1

    # Sort by frequency
    sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
    return sorted_files[:20]  # Top 20


def get_git_stats() -> Dict[str, any]:
    """Get repository statistics."""
    # Total commits
    total_commits = run_git_command(["rev-list", "--count", "HEAD"])

    # Contributors
    contributors = run_git_command(["shortlog", "-sn", "HEAD"])
    contributor_count = len(contributors.split("\n")) if contributors else 0

    # Branch info
    current_branch = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])

    # File counts
    src_files = run_git_command(["ls-files", "src/", "*.py"])
    test_files = run_git_command(["ls-files", "tests/", "*.py"])

    src_count = len([f for f in src_files.split("\n") if f])
    test_count = len([f for f in test_files.split("\n") if f])

    return {
        "total_commits": total_commits,
        "contributors": contributor_count,
        "current_branch": current_branch,
        "src_files": src_count,
        "test_files": test_count,
    }


def get_test_stats() -> Dict[str, int]:
    """Get test suite statistics."""
    try:
        result = subprocess.run(
            ["uv", "run", "pytest", "--collect-only", "-q"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout + result.stderr

        # Parse "X tests collected" or similar
        for line in output.split("\n"):
            if "test" in line and "collected" in line:
                parts = line.split()
                if parts and parts[0].isdigit():
                    return {"total_tests": int(parts[0])}

        return {"total_tests": 0}
    except Exception as e:
        print(f"WARNING: Could not collect test stats: {e}", file=sys.stderr)
        return {"total_tests": 0}


def update_recent_work(repo_root: Path) -> None:
    """Update recent-work.md with latest git activity."""
    print("Updating recent-work.md...")

    recent_work_path = repo_root / ".claude" / "context" / "recent-work.md"

    # Gather data
    commits = get_recent_commits(15)
    recent_files = get_recent_files(7)
    git_stats = get_git_stats()
    test_stats = get_test_stats()

    # Categorize commits
    categorized = {}
    for commit in commits:
        category = categorize_commit(commit["message"])
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(commit)

    # Generate content
    content = f"""# Recent Work Context

**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Auto-generated** by `scripts/workflow/update-context-files.py`

---

## 📊 Repository Overview

| Metric | Value |
|--------|-------|
| Total Commits | {git_stats['total_commits']} |
| Contributors | {git_stats['contributors']} |
| Current Branch | `{git_stats['current_branch']}` |
| Source Files | {git_stats['src_files']} Python files |
| Test Files | {git_stats['test_files']} Python files |
| Total Tests | {test_stats.get('total_tests', 'N/A')} tests |

---

## 🕐 Recent Commits (Last 15)

"""

    # Add categorized commits
    for category in sorted(categorized.keys()):
        content += f"\n### {category}\n\n"
        for commit in categorized[category]:
            content += f"- **`{commit['hash']}`** ({commit['date']}) - {commit['message']}\n"
            content += f"  _by {commit['author']}_\n\n"

    content += f"""---

## 📁 Recently Modified Files (Last 7 Days)

Files changed most frequently:

| File | Changes |
|------|---------|
"""

    for file_path, count in recent_files[:15]:
        content += f"| `{file_path}` | {count} |\n"

    content += f"""

---

## 🎯 Quick Context

### What's Been Happening

Based on recent commits, the team has been focused on:

"""

    # Auto-generate insights from commit categories
    for category, commits_list in sorted(categorized.items(), key=lambda x: len(x[1]), reverse=True):
        if len(commits_list) >= 2:  # Only mention significant categories
            content += f"- **{category}**: {len(commits_list)} recent commits\n"

    content += f"""

### Hot Spots

Most active areas in the codebase (by file change frequency):

"""

    # Group by directory
    dir_activity = {}
    for file_path, count in recent_files:
        if "/" in file_path:
            directory = file_path.split("/")[0]
            dir_activity[directory] = dir_activity.get(directory, 0) + count

    for directory, count in sorted(dir_activity.items(), key=lambda x: x[1], reverse=True)[:5]:
        content += f"- `{directory}/` - {count} file changes\n"

    content += f"""

---

## 🔄 Next Steps Suggestions

Based on recent activity, consider:

1. Review recent changes in hot spot directories
2. Check if any patterns suggest needed refactoring
3. Ensure test coverage for recently modified code
4. Update documentation for new features

---

## 📝 Usage

**Auto-update**: Run `python scripts/workflow/update-context-files.py --recent-work`

**Git hook**: Automatically updates after commits (if configured)

**Manual refresh**: When starting a new Claude Code session

---

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Source**: Git commit history (last 15 commits, 7 days of file activity)
"""

    # Write file
    recent_work_path.write_text(content)
    print(f"✅ Updated: {recent_work_path}")


def create_git_hook(repo_root: Path) -> None:
    """Create git post-commit hook to auto-update context."""
    hooks_dir = repo_root / ".git" / "hooks"
    hook_path = hooks_dir / "post-commit"

    hook_content = """#!/bin/bash
# Auto-update Claude Code context files after commit
# Generated by scripts/workflow/update-context-files.py

# Update recent-work.md (fast)
python scripts/workflow/update-context-files.py --recent-work --quiet
"""

    if hook_path.exists():
        print(f"⚠️  Git hook already exists: {hook_path}")
        print("   To append auto-update, add this line:")
        print("   python scripts/workflow/update-context-files.py --recent-work --quiet")
    else:
        hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path.write_text(hook_content)
        hook_path.chmod(0o755)  # Make executable
        print(f"✅ Created git hook: {hook_path}")


def main():
    parser = argparse.ArgumentParser(description="Auto-update Claude Code context files")
    parser.add_argument("--recent-work", action="store_true", help="Update only recent-work.md")
    parser.add_argument("--quick", action="store_true", help="Quick update (recent-work only)")
    parser.add_argument("--create-hook", action="store_true", help="Create git post-commit hook")
    parser.add_argument("--quiet", action="store_true", help="Suppress output except errors")

    args = parser.parse_args()

    repo_root = get_repo_root()

    if not args.quiet:
        print(f"🔄 Updating Claude Code context files in: {repo_root}")
        print()

    # Create git hook if requested
    if args.create_hook:
        create_git_hook(repo_root)
        return

    # Update files
    if args.recent_work or args.quick:
        update_recent_work(repo_root)
    else:
        # Full update (all context files)
        update_recent_work(repo_root)
        # Note: testing-patterns and code-patterns updates are complex and slow
        # They should be separate scripts or run less frequently
        if not args.quiet:
            print()
            print("ℹ️  Note: testing-patterns.md and code-patterns.md")
            print("   updates are not automated yet (too complex/slow).")
            print("   These should be updated manually or via separate scripts.")

    if not args.quiet:
        print()
        print("✅ Context update complete!")
        print()
        print("💡 To auto-update after commits, run:")
        print("   python scripts/workflow/update-context-files.py --create-hook")


if __name__ == "__main__":
    main()
