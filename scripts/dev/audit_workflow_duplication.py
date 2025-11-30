#!/usr/bin/env python3
"""
Workflow Duplication Audit Script

Analyzes GitHub Actions workflow files to identify duplication patterns
and opportunities for consolidation via composite actions.

Target: Phase 5.4 - Audit 29+ workflow files for duplication
"""

from collections import Counter, defaultdict
from pathlib import Path

import yaml


class WorkflowAuditor:
    """Audit GitHub Actions workflows for duplication."""

    def __init__(self, workflows_dir: Path):
        """Initialize auditor."""
        self.workflows_dir = Path(workflows_dir)
        self.workflows: dict[str, dict] = {}
        self.action_usage: Counter = Counter()
        self.job_steps: dict[str, list[str]] = defaultdict(list)
        self.duplicate_sequences: list[tuple[list[str], list[str]]] = []

    def load_workflows(self) -> None:
        """Load all workflow files."""
        # Glob doesn't support {yml,yaml} syntax, so we need to iterate both
        for pattern in ["*.yml", "*.yaml"]:
            for workflow_file in self.workflows_dir.glob(pattern):
                try:
                    with open(workflow_file) as f:
                        content = yaml.safe_load(f)
                        if content:
                            self.workflows[workflow_file.name] = content
                except Exception as e:
                    print(f"⚠️  Error loading {workflow_file.name}: {e}")

    def analyze_action_usage(self) -> None:
        """Analyze which GitHub Actions are used across workflows."""
        for workflow in self.workflows.values():
            jobs = workflow.get("jobs", {})
            for job_name, job_config in jobs.items():
                steps = job_config.get("steps", [])
                for step in steps:
                    if "uses" in step:
                        action = step["uses"]
                        # Normalize action names (remove version)
                        action_base = action.split("@")[0]
                        self.action_usage[action_base] += 1

    def extract_step_sequence(self, steps: list[dict]) -> list[str]:
        """Extract a normalized sequence of step identifiers."""
        sequence = []
        for step in steps:
            if "uses" in step:
                action = step["uses"].split("@")[0]
                sequence.append(f"uses:{action}")
            elif "run" in step:
                # Normalize run commands
                cmd = step["run"].strip().split("\n")[0][:50]
                sequence.append(f"run:{cmd}")
            elif "name" in step:
                sequence.append(f"step:{step['name']}")
        return sequence

    def find_duplicate_sequences(self, min_length: int = 3) -> None:
        """Find duplicate step sequences across workflows."""
        # Extract all step sequences
        sequences: dict[str, list[tuple[str, str]]] = defaultdict(list)

        for workflow_name, workflow in self.workflows.items():
            jobs = workflow.get("jobs", {})
            for job_name, job_config in jobs.items():
                steps = job_config.get("steps", [])
                sequence = self.extract_step_sequence(steps)

                # Find all subsequences of length >= min_length
                for i in range(len(sequence) - min_length + 1):
                    for j in range(i + min_length, len(sequence) + 1):
                        subseq = tuple(sequence[i:j])
                        sequences[subseq].append((workflow_name, job_name))

        # Filter to only duplicates
        for sequence, locations in sequences.items():
            if len(locations) >= 2 and len(sequence) >= min_length:
                self.duplicate_sequences.append((list(sequence), locations))

    def generate_report(self) -> str:
        """Generate comprehensive duplication report."""
        report = []
        report.append("=" * 80)
        report.append("GitHub Actions Workflow Duplication Audit")
        report.append("=" * 80)
        report.append("")

        # Summary statistics
        report.append("📊 Summary Statistics")
        report.append(f"  Total workflows: {len(self.workflows)}")
        total_jobs = sum(len(w.get("jobs", {})) for w in self.workflows.values())
        report.append(f"  Total jobs: {total_jobs}")
        report.append(f"  Unique actions used: {len(self.action_usage)}")
        report.append("")

        # Most commonly used actions
        report.append("🔄 Most Frequently Used Actions (Top 10)")
        for action, count in self.action_usage.most_common(10):
            report.append(f"  {count:3d}× {action}")
        report.append("")

        # Actions used in many workflows (candidates for composite actions)
        report.append("🎯 Actions Used in 5+ Workflows (Composite Action Candidates)")
        frequent_actions = [(action, count) for action, count in self.action_usage.items() if count >= 5]
        frequent_actions.sort(key=lambda x: x[1], reverse=True)
        for action, count in frequent_actions:
            report.append(f"  {count:3d}× {action}")
        report.append("")

        # Duplicate step sequences
        report.append("🔍 Duplicate Step Sequences (3+ steps)")
        if self.duplicate_sequences:
            # Sort by sequence length (longest first)
            sorted_sequences = sorted(self.duplicate_sequences, key=lambda x: len(x[0]), reverse=True)

            shown = 0
            for sequence, locations in sorted_sequences[:20]:  # Show top 20
                if len(locations) >= 2:
                    shown += 1
                    report.append(f"\n  Sequence #{shown} ({len(sequence)} steps, found in {len(locations)} locations):")
                    for step in sequence[:5]:  # Show first 5 steps
                        report.append(f"    • {step}")
                    if len(sequence) > 5:
                        report.append(f"    ... and {len(sequence) - 5} more steps")

                    report.append("  Found in:")
                    for workflow, job in locations:
                        report.append(f"    - {workflow} → {job}")

            if len(sorted_sequences) > 20:
                report.append(f"\n  ... and {len(sorted_sequences) - 20} more duplicate sequences")
        else:
            report.append("  No duplicate sequences found (minimum length: 3 steps)")
        report.append("")

        # Recommendations
        report.append("=" * 80)
        report.append("💡 Recommendations")
        report.append("=" * 80)
        report.append("")

        report.append("1. **Create Composite Actions** for frequently used action combinations:")
        for action, count in frequent_actions[:5]:
            report.append(f"   - {action} (used {count} times)")
        report.append("")

        report.append("2. **Consolidate Common Setup Steps**:")
        report.append("   - UV setup (appears in multiple workflows)")
        report.append("   - Python environment setup")
        report.append("   - Docker setup")
        report.append("   - Checkout and caching patterns")
        report.append("")

        report.append("3. **Consider Workflow Templates** for similar workflows:")
        report.append("   - Test workflows (unit, integration, E2E)")
        report.append("   - Deployment workflows (dev, staging, production)")
        report.append("   - Validation workflows (docs, configs, security)")
        report.append("")

        report.append("4. **Estimated Savings**:")
        total_duplicate_steps = sum(len(seq) * (len(locs) - 1) for seq, locs in self.duplicate_sequences)
        report.append(f"   - {len(self.duplicate_sequences)} duplicate sequences found")
        report.append(f"   - ~{total_duplicate_steps} duplicate step definitions")
        report.append(f"   - Potential maintenance reduction: {len(frequent_actions)} composite actions")
        report.append("")

        report.append("=" * 80)
        report.append("Generated by: scripts/dev/audit_workflow_duplication.py")
        report.append("=" * 80)

        return "\n".join(report)


def main():
    """Run workflow duplication audit."""
    workflows_dir = Path(".github/workflows")

    if not workflows_dir.exists():
        print(f"❌ Workflows directory not found: {workflows_dir}")
        return 1

    print("🔍 Auditing GitHub Actions workflows for duplication...\n")

    auditor = WorkflowAuditor(workflows_dir)

    print("Loading workflows...")
    auditor.load_workflows()
    print(f"✓ Loaded {len(auditor.workflows)} workflows\n")

    print("Analyzing action usage...")
    auditor.analyze_action_usage()
    print(f"✓ Found {len(auditor.action_usage)} unique actions\n")

    print("Finding duplicate step sequences...")
    auditor.find_duplicate_sequences(min_length=3)
    print(f"✓ Found {len(auditor.duplicate_sequences)} duplicate sequences\n")

    print("Generating report...\n")
    report = auditor.generate_report()
    print(report)

    # Save report
    report_path = Path("docs-internal/WORKFLOW_DUPLICATION_AUDIT.md")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    print(f"\n📄 Report saved to: {report_path}")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
