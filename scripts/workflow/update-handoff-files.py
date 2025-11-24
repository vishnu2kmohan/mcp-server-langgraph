#!/usr/bin/env python3
"""
Auto-populate handoff files from git history and context.

This script automatically generates:
- last-session.md: Summary of recent work
- blockers.md: Current blockers from TODOs and issues
- next-steps.md: Recommended next actions

Usage:
    python scripts/workflow/update-handoff-files.py
    python scripts/workflow/update-handoff-files.py --session-duration 120
"""

import argparse
import subprocess
from datetime import datetime
from pathlib import Path


class HandoffGenerator:
    """Generate handoff files from git history and project state."""

    def __init__(self, repo_root: Path, session_duration_minutes: int = 120):
        self.repo_root = repo_root
        self.claude_dir = repo_root / ".claude"
        self.handoff_dir = self.claude_dir / "handoff"
        self.session_duration = session_duration_minutes

    def run_git_command(self, args: list[str]) -> str:
        """Run a git command and return output."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Git command failed: {e}")
            return ""

    def get_recent_commits(self, hours: int = 24) -> list[dict[str, str]]:
        """Get commits from the last N hours."""
        since = f"{hours} hours ago"
        log_format = "%H|%an|%ae|%ai|%s"
        output = self.run_git_command(["log", f"--since={since}", f"--format={log_format}"])

        commits = []
        for line in output.split("\n"):
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

    def get_current_branch(self) -> str:
        """Get current git branch."""
        return self.run_git_command(["rev-parse", "--abbrev-ref", "HEAD"])

    def get_git_status(self) -> dict[str, list[str]]:
        """Get git status (modified, untracked, staged)."""
        status = {"modified": [], "untracked": [], "staged": []}

        output = self.run_git_command(["status", "--short"])
        for line in output.split("\n"):
            if not line:
                continue

            status_code = line[:2]
            filename = line[3:]

            if status_code[0] in ["M", "A", "D", "R", "C"]:
                status["staged"].append(filename)
            elif status_code[1] == "M":
                status["modified"].append(filename)
            elif status_code == "??":
                status["untracked"].append(filename)

        return status

    def categorize_commit(self, message: str) -> str:
        """Categorize commit by type."""
        message_lower = message.lower()

        if message_lower.startswith("feat"):
            return "feature"
        elif message_lower.startswith("fix"):
            return "bug fix"
        elif message_lower.startswith("docs"):
            return "documentation"
        elif message_lower.startswith("test"):
            return "test"
        elif message_lower.startswith("refactor"):
            return "refactoring"
        elif message_lower.startswith("chore"):
            return "chore"
        elif message_lower.startswith("perf"):
            return "performance"
        else:
            return "other"

    def extract_todos_from_code(self) -> list[dict[str, str]]:
        """Extract TODO comments from code."""
        todos = []

        # Search for TODO comments in Python files
        src_dir = self.repo_root / "src"
        if src_dir.exists():
            for py_file in src_dir.rglob("*.py"):
                try:
                    content = py_file.read_text()
                    for line_num, line in enumerate(content.split("\n"), 1):
                        if "TODO" in line or "FIXME" in line or "HACK" in line:
                            todos.append(
                                {
                                    "file": str(py_file.relative_to(self.repo_root)),
                                    "line": line_num,
                                    "text": line.strip(),
                                    "type": "TODO" if "TODO" in line else ("FIXME" if "FIXME" in line else "HACK"),
                                }
                            )
                except Exception:
                    continue

        return todos[:20]  # Limit to 20 most recent

    def detect_blockers(self) -> list[dict[str, str]]:
        """Detect potential blockers from various sources."""
        blockers = []

        # Check for failing tests
        try:
            test_output = subprocess.run(
                ["pytest", "--collect-only", "-q"],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if "error" in test_output.stderr.lower():
                blockers.append(
                    {
                        "type": "Test Issues",
                        "severity": "medium",
                        "description": "Test collection errors detected",
                        "action": "Run /test-summary to investigate",
                    }
                )
        except Exception:
            pass

        # Check for high-priority TODOs
        todos = self.extract_todos_from_code()
        fixme_count = sum(1 for t in todos if t["type"] == "FIXME")
        if fixme_count > 5:
            blockers.append(
                {
                    "type": "Code Quality",
                    "severity": "low",
                    "description": f"{fixme_count} FIXME comments found",
                    "action": "Review and address FIXME comments",
                }
            )

        # Check git status for conflicts
        status_output = self.run_git_command(["status"])
        if "conflict" in status_output.lower():
            blockers.append(
                {
                    "type": "Merge Conflict",
                    "severity": "high",
                    "description": "Git merge conflicts detected",
                    "action": "Resolve conflicts before proceeding",
                }
            )

        return blockers

    def determine_next_steps(self, commits: list[dict], git_status: dict) -> list[dict[str, str]]:
        """Determine recommended next steps based on current state."""
        steps = []

        # If there are uncommitted changes
        if git_status["modified"] or git_status["untracked"]:
            steps.append(
                {
                    "priority": "high",
                    "action": "Commit current work",
                    "details": f"{len(git_status['modified'])} modified, {len(git_status['untracked'])} untracked files",
                    "command": "git add . && git commit -m 'feat: <description>'",
                }
            )

        # If recent work is complete
        if not git_status["modified"] and not git_status["untracked"] and commits:
            steps.append(
                {
                    "priority": "medium",
                    "action": "Push changes to remote",
                    "details": f"{len(commits)} commits ready to push",
                    "command": "git push origin main",
                }
            )

        # Check coverage
        coverage_file = self.repo_root / "htmlcov" / "index.html"
        if coverage_file.exists():
            steps.append(
                {
                    "priority": "medium",
                    "action": "Review test coverage",
                    "details": "Coverage report available",
                    "command": "/coverage-gaps",
                }
            )

        # Suggest running tests
        steps.append(
            {
                "priority": "high",
                "action": "Run test suite",
                "details": "Verify all tests pass before proceeding",
                "command": "/test-summary",
            }
        )

        # Suggest checking CI
        steps.append(
            {
                "priority": "medium",
                "action": "Check CI status",
                "details": "Ensure CI pipeline is green",
                "command": "/ci-status",
            }
        )

        return steps[:5]  # Top 5 priorities

    def generate_last_session(self) -> str:
        """Generate last-session.md content."""
        now = datetime.now()
        commits = self.get_recent_commits(hours=self.session_duration // 60)
        branch = self.get_current_branch()
        git_status = self.get_git_status()

        # Categorize commits
        commit_categories = {}
        for commit in commits:
            category = self.categorize_commit(commit["message"])
            commit_categories.setdefault(category, []).append(commit)

        content = f"""# Last Session Summary

**Session Date**: {now.strftime("%Y-%m-%d")}
**Duration**: ~{self.session_duration // 60} hours
**Branch**: {branch}
**Auto-Generated**: Yes

---

## 🎯 Session Activity

### Commits ({len(commits)} total)

"""

        # Add commits by category
        for category, cat_commits in sorted(commit_categories.items()):
            content += f"**{category.title()}** ({len(cat_commits)} commits):\n"
            for commit in cat_commits[:5]:  # Top 5 per category
                content += f"- {commit['hash']} - {commit['message']}\n"
            if len(cat_commits) > 5:
                content += f"- ... and {len(cat_commits) - 5} more\n"
            content += "\n"

        # Add git status
        content += f"""---

## 📊 Current State

**Modified Files**: {len(git_status['modified'])}
"""
        for f in git_status["modified"][:10]:
            content += f"- {f}\n"

        content += f"\n**Untracked Files**: {len(git_status['untracked'])}\n"
        for f in git_status["untracked"][:10]:
            content += f"- {f}\n"

        content += f"\n**Staged Files**: {len(git_status['staged'])}\n"
        for f in git_status["staged"][:10]:
            content += f"- {f}\n"

        # Add metrics
        content += f"""
---

## 📈 Session Metrics

- **Total Commits**: {len(commits)}
- **Files Changed**: {len(git_status['modified']) + len(git_status['staged'])}
- **Branch**: {branch}
- **Session Duration**: ~{self.session_duration} minutes

---

## 💡 Key Insights

"""

        if commits:
            most_active = max(commit_categories, key=lambda k: len(commit_categories[k]))
            count = len(commit_categories[most_active])
            content += f"- Most active: {most_active} ({count} commits)\n"

        if git_status["modified"] or git_status["untracked"]:
            content += f"- Work in progress: {len(git_status['modified']) + len(git_status['untracked'])} uncommitted files\n"

        content += """
---

**Note**: This file is auto-generated. Run `python scripts/workflow/update-handoff-files.py` to refresh.
"""

        return content

    def generate_blockers(self) -> str:
        """Generate blockers.md content."""
        now = datetime.now()
        blockers = self.detect_blockers()
        git_status = self.get_git_status()

        content = f"""# Current Blockers

**Last Updated**: {now.strftime("%Y-%m-%d %H:%M")}
**Auto-Generated**: Yes

---

## 🚧 Active Blockers

"""

        if not blockers:
            content += "**None detected!** ✅\n\nAll systems operational.\n"
        else:
            for blocker in blockers:
                severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}[blocker["severity"]]
                content += f"""
### {severity_emoji} {blocker['type']}

**Severity**: {blocker['severity'].upper()}

**Issue**: {blocker['description']}

**Action**: {blocker['action']}

---
"""

        # Add waiting for section
        content += """
## ⏸️ Waiting For

"""

        if git_status["modified"] or git_status["untracked"]:
            content += f"""
### User Decision

**Item**: Commit pending changes

**Status**: {len(git_status['modified']) + len(git_status['untracked'])} files waiting to be committed

**Action Needed**: Review and commit changes

**Command**: `git add . && git commit -m "feat: <description>"`

---
"""
        else:
            content += "**Nothing waiting** - All clear to proceed! ✅\n\n---\n"

        # Add recently resolved
        content += """
## ✅ Recently Resolved

*(This section requires manual updates)*

---

## 🎯 Next Steps to Unblock

"""

        if blockers:
            content += "1. Address active blockers above\n"
            content += "2. Run validation: `/validate`\n"
            content += "3. Check test status: `/test-summary`\n"
        else:
            content += "**Nothing blocking!** Ready to:\n"
            content += "1. Continue development\n"
            content += "2. Create pull request\n"
            content += "3. Deploy changes\n"

        content += """
---

**Note**: This file is auto-generated. Run `python scripts/workflow/update-handoff-files.py` to refresh.
"""

        return content

    def generate_next_steps(self) -> str:
        """Generate next-steps.md content."""
        now = datetime.now()
        commits = self.get_recent_commits(hours=24)
        git_status = self.get_git_status()
        steps = self.determine_next_steps(commits, git_status)

        content = f"""# Next Steps

**Last Updated**: {now.strftime("%Y-%m-%d %H:%M")}
**Auto-Generated**: Yes

---

## 🎯 Recommended Actions

"""

        for i, step in enumerate(steps, 1):
            priority_emoji = {"high": "🔥", "medium": "⚠️", "low": "ℹ️"}[step["priority"]]
            content += f"""
### {i}. {priority_emoji} {step['action']}

**Priority**: {step['priority'].upper()}

**Details**: {step['details']}

**Command**:
```bash
{step['command']}
```

---
"""

        # Add workflow suggestions
        content += """
## 🔧 Suggested Workflows

### Quick Quality Check
```bash
/test-summary
/coverage-gaps
/ci-status
```

### Pre-Commit Workflow
```bash
/test-summary
/validate
git add .
git commit -m "feat: <description>"
```

### Pre-PR Workflow
```bash
/test-summary all
/coverage-gaps
/benchmark
/ci-status
# Create PR
/pr-checks
```

---

## 📋 Available Commands

**Testing**:
- `/test-summary` - Run and analyze tests
- `/coverage-gaps` - Visual coverage heatmap
- `/improve-coverage <threshold>` - Coverage improvement plan

**Quality**:
- `/validate` - All validations
- `/benchmark` - Performance trends
- `/type-safety-status` - Mypy progress

**Documentation**:
- `/create-adr <title>` - Generate ADR
- `/create-test <module>` - Generate test file
- `/docs-audit` - Documentation audit

**Deployment**:
- `/deploy <target> <env>` - Deploy application
- `/ci-status` - Check CI pipeline

**Debugging**:
- `/quick-debug <error>` - AI-assisted debug
- `/test-failure-analysis` - Deep test analysis

---

**Note**: This file is auto-generated. Run `python scripts/workflow/update-handoff-files.py` to refresh.
"""

        return content

    def update_all_handoff_files(self):
        """Update all handoff files."""
        self.handoff_dir.mkdir(parents=True, exist_ok=True)

        print("🔄 Updating handoff files...")

        # Generate last-session.md
        print("  - Generating last-session.md...")
        last_session = self.generate_last_session()
        (self.handoff_dir / "last-session.md").write_text(last_session)

        # Generate blockers.md
        print("  - Generating blockers.md...")
        blockers = self.generate_blockers()
        (self.handoff_dir / "blockers.md").write_text(blockers)

        # Generate next-steps.md
        print("  - Generating next-steps.md...")
        next_steps = self.generate_next_steps()
        (self.handoff_dir / "next-steps.md").write_text(next_steps)

        print("✅ Handoff files updated successfully!")
        print(f"   Location: {self.handoff_dir}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Auto-populate handoff files from git history")
    parser.add_argument(
        "--session-duration",
        type=int,
        default=120,
        help="Session duration in minutes (default: 120)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output",
    )

    args = parser.parse_args()

    # Find repo root
    repo_root = Path.cwd()
    while not (repo_root / ".git").exists() and repo_root != repo_root.parent:
        repo_root = repo_root.parent

    if not (repo_root / ".git").exists():
        print("Error: Not in a git repository")
        return 1

    generator = HandoffGenerator(repo_root, args.session_duration)
    generator.update_all_handoff_files()

    return 0


if __name__ == "__main__":
    exit(main())
