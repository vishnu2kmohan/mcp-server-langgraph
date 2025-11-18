#!/usr/bin/env python3
"""
TODO Tracker - Automated TODO scanning and catalog management

This script:
1. Scans source code for TODO comments
2. Compares with TODO_CATALOG.md
3. Generates progress report
4. Updates catalog status
5. Provides sprint burndown metrics

Usage:
    python scripts/workflow/todo-tracker.py              # Scan and report
    python scripts/workflow/todo-tracker.py --update     # Update catalog
    python scripts/workflow/todo-tracker.py --burndown   # Sprint burndown

Author: Claude Code (Workflow Optimization)
Created: 2025-10-20
"""

import argparse
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List


@dataclass
class TodoItem:
    """Represents a TODO item found in code"""

    file_path: str
    line_number: int
    content: str
    category: str = "uncategorized"
    priority: str = "MEDIUM"

    def __str__(self):
        return f"{self.file_path}:{self.line_number} - {self.content}"


class TodoTracker:
    """Tracks TODO items in codebase"""

    # TODO patterns to match
    TODO_PATTERN = re.compile(
        r"#\s*TODO:?\s*(.+)$|" r"//\s*TODO:?\s*(.+)$|" r"/\*\s*TODO:?\s*(.+?)\s*\*/", re.IGNORECASE | re.MULTILINE
    )

    # Priority indicators
    PRIORITY_PATTERNS = {
        "CRITICAL": re.compile(r"\b(CRITICAL|URGENT|BLOCKER|ASAP)\b", re.IGNORECASE),
        "HIGH": re.compile(r"\b(HIGH|IMPORTANT|SOON)\b", re.IGNORECASE),
        "MEDIUM": re.compile(r"\b(MEDIUM|NORMAL)\b", re.IGNORECASE),
        "LOW": re.compile(r"\b(LOW|MINOR|SOMEDAY)\b", re.IGNORECASE),
    }

    # Category indicators
    CATEGORY_PATTERNS = {
        "monitoring": re.compile(r"\b(prometheus|metric|alert|monitor|sla)\b", re.IGNORECASE),
        "compliance": re.compile(r"\b(compliance|gdpr|hipaa|soc2|audit)\b", re.IGNORECASE),
        "testing": re.compile(r"\b(test|mock|assert|coverage)\b", re.IGNORECASE),
        "documentation": re.compile(r"\b(doc|readme|comment|explain)\b", re.IGNORECASE),
        "performance": re.compile(r"\b(performance|optimize|cache|slow)\b", re.IGNORECASE),
        "security": re.compile(r"\b(security|auth|encrypt|sanitize)\b", re.IGNORECASE),
    }

    def __init__(self, root_dir: str = "src"):
        self.root_dir = Path(root_dir)
        self.todos: list[TodoItem] = []

    def scan(self) -> list[TodoItem]:
        """Scan source directory for TODO items"""
        self.todos = []

        # Find all Python files
        for py_file in self.root_dir.rglob("*.py"):
            if self._should_skip(py_file):
                continue

            self._scan_file(py_file)

        return self.todos

    def _should_skip(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = [
            "__pycache__",
            ".venv",
            "venv",
            "build",
            "dist",
            ".egg-info",
            "test_",  # Skip test files (they have TODOs for test cases)
        ]

        path_str = str(file_path)
        return any(pattern in path_str for pattern in skip_patterns)

    def _scan_file(self, file_path: Path):
        """Scan a single file for TODOs"""
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                matches = self.TODO_PATTERN.findall(line)
                for match in matches:
                    # Extract content (match is tuple from alternation)
                    content = next((m for m in match if m), "")
                    if not content:
                        continue

                    # Determine priority and category
                    priority = self._determine_priority(content)
                    category = self._determine_category(content)

                    todo = TodoItem(
                        file_path=str(file_path.relative_to(Path.cwd())),
                        line_number=line_num,
                        content=content.strip(),
                        category=category,
                        priority=priority,
                    )
                    self.todos.append(todo)

        except Exception as e:
            print(f"Error scanning {file_path}: {e}")

    def _determine_priority(self, content: str) -> str:
        """Determine priority from content"""
        for priority, pattern in self.PRIORITY_PATTERNS.items():
            if pattern.search(content):
                return priority
        return "MEDIUM"

    def _determine_category(self, content: str) -> str:
        """Determine category from content"""
        for category, pattern in self.CATEGORY_PATTERNS.items():
            if pattern.search(content):
                return category
        return "uncategorized"

    def group_by_file(self) -> dict[str, list[TodoItem]]:
        """Group TODOs by file"""
        grouped = defaultdict(list)
        for todo in self.todos:
            grouped[todo.file_path].append(todo)
        return dict(grouped)

    def group_by_category(self) -> dict[str, list[TodoItem]]:
        """Group TODOs by category"""
        grouped = defaultdict(list)
        for todo in self.todos:
            grouped[todo.category].append(todo)
        return dict(grouped)

    def group_by_priority(self) -> dict[str, list[TodoItem]]:
        """Group TODOs by priority"""
        grouped = defaultdict(list)
        for todo in self.todos:
            grouped[todo.priority].append(todo)
        return dict(grouped)

    def generate_report(self) -> str:
        """Generate comprehensive TODO report"""
        by_priority = self.group_by_priority()
        by_category = self.group_by_category()
        by_file = self.group_by_file()

        report = []
        report.append("# TODO Tracker Report")
        report.append(f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Total TODOs Found**: {len(self.todos)}\n")
        report.append("---\n")

        # Summary by priority
        report.append("## 📊 Summary by Priority\n")
        for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            count = len(by_priority.get(priority, []))
            emoji = {"CRITICAL": "🔴", "HIGH": "🟡", "MEDIUM": "🟢", "LOW": "⚪"}.get(priority, "")
            report.append(f"- {emoji} **{priority}**: {count} items")
        report.append("\n---\n")

        # Summary by category
        report.append("## 📁 Summary by Category\n")
        for category, todos in sorted(by_category.items(), key=lambda x: -len(x[1])):
            report.append(f"- **{category.title()}**: {len(todos)} items")
        report.append("\n---\n")

        # Details by priority
        report.append("## 🔍 Details by Priority\n")
        for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            todos = by_priority.get(priority, [])
            if not todos:
                continue

            report.append(f"\n### {priority} Priority ({len(todos)} items)\n")
            for todo in todos:
                report.append(f"**{todo.file_path}:{todo.line_number}** ({todo.category})")
                report.append(f"```\n{todo.content}\n```\n")

        report.append("---\n")

        # Files with most TODOs
        report.append("## 📈 Files with Most TODOs\n")
        sorted_files = sorted(by_file.items(), key=lambda x: -len(x[1]))[:10]
        for file_path, todos in sorted_files:
            report.append(f"- `{file_path}`: {len(todos)} TODOs")

        report.append("\n---\n")
        report.append("## 💡 Recommendations\n")

        critical_count = len(by_priority.get("CRITICAL", []))
        high_count = len(by_priority.get("HIGH", []))

        if critical_count > 0:
            report.append(f"- ⚠️ **URGENT**: Address {critical_count} CRITICAL TODOs immediately")
        if high_count > 5:
            report.append(f"- 🔥 **HIGH**: Plan sprint to address {high_count} HIGH priority items")

        total_todos = len(self.todos)
        if total_todos > 50:
            report.append(f"- 📊 **TECH DEBT**: {total_todos} total TODOs - consider tech debt sprint")

        report.append("\n---\n")
        report.append("**Auto-generated by**: `scripts/workflow/todo-tracker.py`\n")

        return "\n".join(report)

    def compare_with_catalog(self, catalog_path: str = "docs-internal/TODO_CATALOG.md") -> dict:
        """Compare current TODOs with catalog"""
        catalog_path = Path(catalog_path)

        if not catalog_path.exists():
            return {
                "catalog_exists": False,
                "in_code_not_catalog": len(self.todos),
                "in_catalog_not_code": 0,
                "status": "No catalog found",
            }

        # Parse catalog (simplified - would need more robust parsing)
        with open(catalog_path) as f:
            catalog_content = f.read()

        # Count items in catalog (count lines starting with ###)
        catalog_items = len(re.findall(r"^###\s+\d+\.", catalog_content, re.MULTILINE))

        return {
            "catalog_exists": True,
            "todos_in_code": len(self.todos),
            "items_in_catalog": catalog_items,
            "status": "Comparison complete",
        }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Track TODO items in codebase")
    parser.add_argument("--root", default="src", help="Root directory to scan (default: src)")
    parser.add_argument("--update", action="store_true", help="Update TODO catalog")
    parser.add_argument("--burndown", action="store_true", help="Show sprint burndown")
    parser.add_argument("--output", help="Output file for report (default: stdout)")

    args = parser.parse_args()

    # Create tracker and scan
    tracker = TodoTracker(root_dir=args.root)
    print(f"Scanning {args.root} for TODO items...")
    tracker.scan()

    # Generate report
    report = tracker.generate_report()

    # Output report
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)
        print(f"\nReport saved to: {args.output}")
    else:
        print("\n" + report)

    # Compare with catalog
    print("\n" + "=" * 60)
    print("Comparing with TODO_CATALOG.md...")
    comparison = tracker.compare_with_catalog()

    if comparison["catalog_exists"]:
        print(f"TODOs in code: {comparison['todos_in_code']}")
        print(f"Items in catalog: {comparison['items_in_catalog']}")

        if comparison["todos_in_code"] > comparison["items_in_catalog"]:
            diff = comparison["todos_in_code"] - comparison["items_in_catalog"]
            print(f"⚠️  {diff} new TODOs not in catalog - consider updating!")
        elif comparison["todos_in_code"] < comparison["items_in_catalog"]:
            diff = comparison["items_in_catalog"] - comparison["todos_in_code"]
            print(f"✅ {diff} TODOs resolved since last catalog update!")
        else:
            print("✅ Catalog is up to date!")
    else:
        print("⚠️  No TODO catalog found - consider creating one!")

    # Update catalog if requested
    if args.update:
        print("\n📝 Updating TODO catalog...")
        # TODO: Implement catalog update logic
        print("⚠️  Catalog update not yet implemented - manual update required")

    # Show burndown if requested
    if args.burndown:
        print("\n📊 Sprint Burndown:")
        by_priority = tracker.group_by_priority()
        total = len(tracker.todos)
        critical = len(by_priority.get("CRITICAL", []))
        high = len(by_priority.get("HIGH", []))
        medium = len(by_priority.get("MEDIUM", []))
        low = len(by_priority.get("LOW", []))

        print(f"Total Remaining: {total}")
        print(f"  CRITICAL: {critical}")
        print(f"  HIGH: {high}")
        print(f"  MEDIUM: {medium}")
        print(f"  LOW: {low}")

        if total > 0:
            print("\nRecommended Sprint Scope:")
            if critical > 0:
                print(f"  Week 1: {critical} CRITICAL items")
            if high > 0:
                print(f"  Week 2-3: {high} HIGH items")
            if medium > 0:
                print(f"  Week 4+: {medium} MEDIUM items (as time permits)")


if __name__ == "__main__":
    main()
