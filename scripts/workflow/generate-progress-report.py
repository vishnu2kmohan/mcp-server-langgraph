#!/usr/bin/env python3
"""
Progress Report Generator - Automated sprint progress reporting

This script:
1. Analyzes git commits since sprint start
2. Collects code metrics (files, lines, commits)
3. Calculates sprint velocity and completion rate
4. Generates formatted progress report
5. Updates sprint tracking document

Usage:
    python scripts/workflow/generate-progress-report.py               # Current sprint
    python scripts/workflow/generate-progress-report.py --since 2025-10-18  # Specific date
    python scripts/workflow/generate-progress-report.py --sprint-file docs-internal/SPRINT_PROGRESS_20251018.md

Author: Claude Code (Workflow Optimization)
Created: 2025-10-20
"""

import argparse
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class CommitInfo:
    """Information about a git commit"""
    hash: str
    date: datetime
    author: str
    message: str
    files_changed: int
    insertions: int
    deletions: int
    commit_type: str  # feat, fix, docs, test, etc.

    @property
    def net_lines(self) -> int:
        return self.insertions - self.deletions


class ProgressReportGenerator:
    """Generates automated sprint progress reports"""

    COMMIT_TYPE_PATTERN = {
        'feat': 'Feature',
        'fix': 'Bug Fix',
        'docs': 'Documentation',
        'test': 'Testing',
        'refactor': 'Refactoring',
        'chore': 'Chore',
        'style': 'Style',
        'perf': 'Performance',
    }

    def __init__(self, since_date: Optional[str] = None):
        self.since_date = since_date or self._get_week_ago()
        self.commits: List[CommitInfo] = []

    def _get_week_ago(self) -> str:
        """Get date one week ago"""
        week_ago = datetime.now() - timedelta(days=7)
        return week_ago.strftime('%Y-%m-%d')

    def collect_metrics(self):
        """Collect git metrics"""
        print(f"Collecting metrics since {self.since_date}...")

        # Get commit hashes
        cmd = ['git', 'log', f'--since={self.since_date}', '--pretty=format:%H']
        result = subprocess.run(cmd, capture_output=True, text=True)
        commit_hashes = result.stdout.strip().split('\n')

        if not commit_hashes or commit_hashes == ['']:
            print("No commits found in date range")
            return

        # Get detailed info for each commit
        for commit_hash in commit_hashes:
            commit_info = self._get_commit_info(commit_hash)
            if commit_info:
                self.commits.append(commit_info)

        print(f"Found {len(self.commits)} commits")

    def _get_commit_info(self, commit_hash: str) -> Optional[CommitInfo]:
        """Get detailed information about a commit"""
        try:
            # Get commit message and metadata
            cmd = ['git', 'show', '--no-patch', '--pretty=format:%H|%aI|%an|%s', commit_hash]
            result = subprocess.run(cmd, capture_output=True, text=True)
            hash_str, date_str, author, message = result.stdout.strip().split('|', 3)

            # Get file statistics
            cmd = ['git', 'show', '--numstat', '--pretty=format:', commit_hash]
            result = subprocess.run(cmd, capture_output=True, text=True)

            insertions = 0
            deletions = 0
            files_changed = 0

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 2:
                    try:
                        ins = int(parts[0]) if parts[0] != '-' else 0
                        dels = int(parts[1]) if parts[1] != '-' else 0
                        insertions += ins
                        deletions += dels
                        files_changed += 1
                    except ValueError:
                        continue

            # Determine commit type
            commit_type = 'other'
            for type_prefix in self.COMMIT_TYPE_PATTERN.keys():
                if message.lower().startswith(f'{type_prefix}:') or message.lower().startswith(f'{type_prefix}('):
                    commit_type = type_prefix
                    break

            return CommitInfo(
                hash=commit_hash[:7],
                date=datetime.fromisoformat(date_str.replace('Z', '+00:00')),
                author=author,
                message=message,
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions,
                commit_type=commit_type
            )

        except Exception as e:
            print(f"Error processing commit {commit_hash}: {e}")
            return None

    def generate_report(self) -> str:
        """Generate comprehensive progress report"""
        if not self.commits:
            return "No commits found in the specified period."

        report = []
        report.append("# Sprint Progress Report\n")
        report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Period**: Since {self.since_date}")
        report.append(f"**Duration**: {self._calculate_duration()} days\n")
        report.append("---\n")

        # Summary metrics
        report.append("## 📊 Summary Metrics\n")
        total_commits = len(self.commits)
        total_files = sum(c.files_changed for c in self.commits)
        total_insertions = sum(c.insertions for c in self.commits)
        total_deletions = sum(c.deletions for c in self.commits)
        net_change = total_insertions - total_deletions

        report.append(f"- **Total Commits**: {total_commits}")
        report.append(f"- **Files Modified**: {total_files}")
        report.append(f"- **Lines Added**: +{total_insertions:,}")
        report.append(f"- **Lines Removed**: -{total_deletions:,}")
        report.append(f"- **Net Change**: {net_change:+,}\n")
        report.append("---\n")

        # Commit breakdown by type
        report.append("## 📁 Commits by Type\n")
        type_counts = Counter(c.commit_type for c in self.commits)
        for commit_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            type_name = self.COMMIT_TYPE_PATTERN.get(commit_type, commit_type.title())
            percentage = (count / total_commits) * 100
            report.append(f"- **{type_name}**: {count} ({percentage:.1f}%)")
        report.append("\n---\n")

        # Daily activity
        report.append("## 📅 Daily Activity\n")
        daily_commits = self._group_by_day()
        for date in sorted(daily_commits.keys(), reverse=True)[:7]:  # Last 7 days
            commits = daily_commits[date]
            total_lines = sum(c.insertions + c.deletions for c in commits)
            report.append(f"### {date}")
            report.append(f"- {len(commits)} commits, {total_lines:,} lines changed")
            for commit in commits:
                report.append(f"  - `{commit.hash}` {commit.message}")
            report.append("")
        report.append("---\n")

        # Most active files
        report.append("## 🔥 Most Modified Files\n")
        file_changes = self._get_file_changes()
        for file_path, count in sorted(file_changes.items(), key=lambda x: -x[1])[:10]:
            report.append(f"- `{file_path}`: {count} changes")
        report.append("\n---\n")

        # Velocity metrics
        report.append("## 🚀 Velocity Metrics\n")
        duration_days = max(1, self._calculate_duration())
        commits_per_day = total_commits / duration_days
        lines_per_day = (total_insertions + total_deletions) / duration_days

        report.append(f"- **Commits per day**: {commits_per_day:.1f}")
        report.append(f"- **Lines changed per day**: {lines_per_day:,.0f}")
        report.append(f"- **Average commit size**: {(total_insertions + total_deletions) / total_commits:.0f} lines\n")
        report.append("---\n")

        # Recommendations
        report.append("## 💡 Insights\n")

        # High velocity
        if commits_per_day > 5:
            report.append("- ⚡ **High velocity**: Excellent progress rate!")

        # Documentation commits
        doc_commits = type_counts.get('docs', 0)
        if doc_commits / total_commits > 0.3:
            report.append("- 📚 **Documentation-heavy**: Good documentation practice!")

        # Test commits
        test_commits = type_counts.get('test', 0)
        if test_commits / total_commits > 0.2:
            report.append("- 🧪 **Test-driven**: Strong testing discipline!")

        # Large commits
        avg_lines = (total_insertions + total_deletions) / total_commits
        if avg_lines > 500:
            report.append("- 📦 **Large commits**: Consider smaller, more frequent commits")

        report.append("\n---\n")
        report.append("**Auto-generated by**: `scripts/workflow/generate-progress-report.py`\n")

        return '\n'.join(report)

    def _calculate_duration(self) -> int:
        """Calculate duration in days"""
        if not self.commits:
            return 1

        earliest = min(c.date for c in self.commits)
        latest = max(c.date for c in self.commits)
        return max(1, (latest - earliest).days + 1)

    def _group_by_day(self) -> Dict[str, List[CommitInfo]]:
        """Group commits by day"""
        daily = defaultdict(list)
        for commit in self.commits:
            date_str = commit.date.strftime('%Y-%m-%d')
            daily[date_str].append(commit)
        return dict(daily)

    def _get_file_changes(self) -> Dict[str, int]:
        """Get count of changes per file"""
        cmd = ['git', 'log', f'--since={self.since_date}', '--name-only', '--pretty=format:']
        result = subprocess.run(cmd, capture_output=True, text=True)

        file_counts = Counter()
        for line in result.stdout.strip().split('\n'):
            if line:
                file_counts[line] += 1

        return dict(file_counts)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Generate sprint progress report')
    parser.add_argument('--since', help='Start date (YYYY-MM-DD). Default: 7 days ago')
    parser.add_argument('--sprint-file', help='Sprint tracking file to update')
    parser.add_argument('--output', help='Output file for report (default: stdout)')

    args = parser.parse_args()

    # Create generator and collect metrics
    generator = ProgressReportGenerator(since_date=args.since)
    generator.collect_metrics()

    # Generate report
    report = generator.generate_report()

    # Output report
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"\n✅ Report saved to: {args.output}")
    else:
        print("\n" + report)

    # Update sprint file if specified
    if args.sprint_file:
        sprint_path = Path(args.sprint_file)
        if sprint_path.exists():
            print(f"\n📝 Updating {args.sprint_file}...")
            # TODO: Implement sprint file update logic
            print("⚠️  Sprint file update not yet implemented - manual update required")
        else:
            print(f"⚠️  Sprint file not found: {args.sprint_file}")


if __name__ == '__main__':
    main()
