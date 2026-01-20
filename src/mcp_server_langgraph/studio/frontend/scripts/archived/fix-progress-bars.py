#!/usr/bin/env python3
"""
Fix Progress Bar Inline Styles

Migrates progress bar patterns from inline width to CSS custom property pattern.

Before:
  style={{ width: `${percentage}%` }}

After:
  style={{ '--progress': `${percentage}%` } as React.CSSProperties}
  className="progress-bar-fill"

This script handles the coordination between style and className attributes.
"""

import re
from typing import Any, Pattern, Match
import sys
from pathlib import Path


# Files with progress bar violations to fix
FILES_TO_FIX = [
    "src/ai/AgentTaskQueue.tsx",
    "src/ai/BackgroundAgentPanel.tsx",
    "src/components/Admin/AgentApprovalDialog.tsx",
    "src/components/Admin/BatchApprovalPanel.tsx",
    "src/components/Chat/AgentExecutionTracePanel.tsx",
    "src/components/Common/ProgressIndicator.tsx",
    "src/components/Cost/BudgetForecastChart.tsx",
    "src/components/Cost/BudgetStatusCard.tsx",
    "src/components/ErrorRecovery/RetryIndicator.tsx",
    "src/components/Feedback/SUSSurvey.tsx",
    "src/components/Insights/AICacheMetricsDashboard.tsx",
    "src/components/Insights/TokenUsageDashboard.tsx",
    "src/components/Onboarding/OnboardingWizard.tsx",
    "src/components/UI/TierUsageBar.tsx",
    "src/components/Workflow/WorkflowMiniView.tsx",
    "src/persona/WorkspacePresets.tsx",
]


def fix_progress_bar_pattern(content: str) -> tuple[str, int]:
    """
    Fix progress bar inline styles.

    Pattern[str]: style={{ width: `${expr}%` }}
    Replacement: style={{ '--progress': `${expr}%` } as React.CSSProperties}

    Also handles adding progress-bar-fill to className if nearby.

    Returns: (modified_content, fix_count)
    """
    fixes = 0

    # Pattern[str] 1: Simple width percentage
    # style={{ width: `${percentage}%` }}
    pattern1 = r'style=\{\{\s*width:\s*`\$\{([^}]+)\}%`\s*\}\}'

    def replace_simple(m: re.Match[str]) -> str:
        expr = m.group(1)
        return f"style={{{{ '--progress': `${{{expr}}}%` }} as React.CSSProperties}}"

    new_content, count1 = re.subn(pattern1, replace_simple, content)
    content = new_content
    fixes += count1

    # Pattern[str] 2: Width with Math operations
    # style={{ width: `${Math.min(x, 100)}%` }}
    pattern2 = r'style=\{\{\s*width:\s*`\$\{(Math\.[^}]+)\}%`\s*\}\}'

    new_content, count2 = re.subn(pattern2, replace_simple, content)
    content = new_content
    fixes += count2

    # Pattern[str] 3: Width with calculation
    # style={{ width: `${(a / b) * 100}%` }}
    pattern3 = r'style=\{\{\s*width:\s*`\$\{\(([^}]+)\)\s*\*\s*100\}%`\s*\}\}'

    def replace_calc(m: re.Match[str]) -> str:
        expr = m.group(1)
        return f"style={{{{ '--progress': `${{({expr}) * 100}}%` }} as React.CSSProperties}}"

    new_content, count3 = re.subn(pattern3, replace_calc, content)
    content = new_content
    fixes += count3

    # Pattern[str] 4: Width with property access multiplication
    # style={{ width: `${healthScore * 100}%` }}
    pattern4 = r'style=\{\{\s*width:\s*`\$\{([a-zA-Z_.]+)\s*\*\s*100\}%`\s*\}\}'

    def replace_mult(m: re.Match[str]) -> str:
        expr = m.group(1)
        return f"style={{{{ '--progress': `${{{expr} * 100}}%` }} as React.CSSProperties}}"

    new_content, count4 = re.subn(pattern4, replace_mult, content)
    content = new_content
    fixes += count4

    return content, fixes


def add_progress_bar_class(content: str) -> tuple[str, int]:
    """
    Add progress-bar-fill class to elements that have --progress style.

    Looks for patterns like:
    style={{ '--progress': ... }} className="existing-classes"

    And adds progress-bar-fill to className.
    """
    fixes = 0

    # Find elements with --progress style that need the class added
    # This is complex because we need to handle JSX properly
    # For now, we'll handle common patterns

    # Pattern[str]: style={{ '--progress': ... }}\s*className="..."
    # Add progress-bar-fill to existing className
    pattern = r"(style=\{\{\s*'--progress':[^}]+\}\s*as\s*React\.CSSProperties\})\s*(className=\")([^\"]*)(\")"

    def add_class(m: re.Match[str]) -> str:
        style = m.group(1)
        class_start = m.group(2)
        existing_classes = m.group(3)
        class_end = m.group(4)

        if "progress-bar" not in existing_classes:
            return f'{style} {class_start}progress-bar-fill {existing_classes}{class_end}'
        return m.group(0)

    new_content, count = re.subn(pattern, add_class, content)
    content = new_content
    fixes += count

    # Pattern[str]: style={{ '--progress': ... }} followed by no className
    # This is trickier - we'd need to add className

    return content, fixes


def process_file(file_path: Path) -> int:
    """Process a single file. Returns number of fixes applied."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0

    original = content

    # Apply fixes
    content, fix_count = fix_progress_bar_pattern(content)

    # Try to add className
    content, class_fixes = add_progress_bar_class(content)
    fix_count += class_fixes

    if content != original:
        try:
            file_path.write_text(content, encoding="utf-8")
            print(f"Fixed {fix_count} patterns in {file_path}")
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return 0

    return fix_count


def main() -> int:
    """Main entry point."""
    total_fixes = 0

    for file_str in FILES_TO_FIX:
        file_path = Path(file_str)
        if file_path.exists():
            fixes = process_file(file_path)
            total_fixes += fixes
        else:
            print(f"File not found: {file_path}", file=sys.stderr)

    print(f"\nTotal fixes applied: {total_fixes}")
    return 0 if total_fixes > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
