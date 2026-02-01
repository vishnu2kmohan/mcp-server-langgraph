#!/usr/bin/env python3
"""
Fix STYLE.md compliance issues in Admin components.

Issues addressed:
1. Add useReducedMotion import and hook
2. Add cn() import where missing
3. Replace animate-spin with reduced motion check
4. Replace animate-pulse with reduced motion check
"""

import re
from pathlib import Path

ADMIN_DIR = Path(__file__).parent.parent / "src" / "components" / "Admin"

# Files to process (excluding tests and stories)
FILES_TO_PROCESS = [
    "AIQualityMetricsCard.tsx",
    "AIRecommendationCard.tsx",
    "AlertDetailPanel.tsx",
    "AlertsPanel.tsx",
    "MetricCard.tsx",
    "UserManager.tsx",
    "AgentApprovalAuditLog.tsx",
    "AgentApprovalDialog.tsx",
    "AuditLogFilters.tsx",
    "ClarificationDialog.tsx",
    "OrganizationManager.tsx",
    "RemediationApprovalDialog.tsx",
]


def add_imports(content: str, file_path: Path) -> str:
    """Add missing imports for useReducedMotion and cn."""

    # Check if file uses animate-spin or animate-pulse
    has_animation = "animate-spin" in content or "animate-pulse" in content

    # Check if cn is already imported
    has_cn_import = "import { cn }" in content or "from '../../utils/cn'" in content or 'from "../../utils/cn"' in content

    # Check if useReducedMotion is already imported
    has_reduced_motion_import = "useReducedMotion" in content

    # Add useReducedMotion import if needed
    if has_animation and not has_reduced_motion_import:
        # Find the first import statement to add after
        import_match = re.search(r"^import\s+.*?;", content, re.MULTILINE)
        if import_match:
            # Add after first import
            insert_pos = import_match.end()
            content = content[:insert_pos] + '\nimport { useReducedMotion } from "motion/react";' + content[insert_pos:]
            print(f"  Added useReducedMotion import to {file_path.name}")

    # Add cn import if needed (check for template literal class usage)
    if not has_cn_import and ("className={`" in content or "${" in content):
        # Find where to add cn import
        import_match = re.search(r"^import\s+.*?;", content, re.MULTILINE)
        if import_match:
            insert_pos = import_match.end()
            content = content[:insert_pos] + '\nimport { cn } from "../../utils/cn";' + content[insert_pos:]
            print(f"  Added cn import to {file_path.name}")

    return content


def add_hook_call(content: str, file_path: Path) -> str:
    """Add useReducedMotion hook call if import was added."""

    # Only add if import exists but hook call doesn't
    if "useReducedMotion" in content and "prefersReducedMotion" not in content:
        # Find the component function body (after opening brace)
        # Look for common patterns
        patterns = [
            r"(export function \w+\([^)]*\)\s*\{)",
            r"(function \w+\([^)]*\)\s*\{)",
            r"(export const \w+\s*=\s*\([^)]*\)\s*=>\s*\{)",
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                insert_pos = match.end()
                # Check if there's already state declarations
                next_line = content[insert_pos : insert_pos + 200]
                if "const [" in next_line or "useState" in next_line:
                    # Find after the useState declarations
                    state_end = content.find("\n\n", insert_pos)
                    if state_end != -1:
                        insert_pos = state_end

                content = (
                    content[:insert_pos]
                    + "\n  // WCAG 2.2 AA: Respect user's reduced motion preference\n  const prefersReducedMotion = useReducedMotion();\n"
                    + content[insert_pos:]
                )
                print(f"  Added useReducedMotion hook to {file_path.name}")
                break

    return content


def fix_animations(content: str, file_path: Path) -> str:
    """Replace animate-spin and animate-pulse with reduced motion checks."""

    if "prefersReducedMotion" not in content:
        return content

    # Pattern[str] 1: Simple className="... animate-spin ..."
    # Replace with cn() pattern
    replacements_made = 0

    # Fix animate-spin patterns
    if "animate-spin" in content and "!prefersReducedMotion" not in content:
        # Pattern[str]: className="w-4 h-4 animate-spin"
        content = re.sub(
            r'className="([^"]*?)animate-spin([^"]*?)"',
            lambda m: f'className={{cn("{m.group(1).strip()} {m.group(2).strip()}", !prefersReducedMotion && "animate-spin")}}',
            content,
        )
        replacements_made += 1

    # Fix animate-pulse patterns
    if "animate-pulse" in content and "!prefersReducedMotion" not in content:
        content = re.sub(
            r'className="([^"]*?)animate-pulse([^"]*?)"',
            lambda m: f'className={{cn("{m.group(1).strip()} {m.group(2).strip()}", !prefersReducedMotion && "animate-pulse")}}',
            content,
        )
        replacements_made += 1

    if replacements_made > 0:
        print(f"  Fixed {replacements_made} animation pattern(s) in {file_path.name}")

    return content


def process_file(file_path: Path) -> bool:
    """Process a single file for STYLE.md compliance."""

    if not file_path.exists():
        print(f"  Skipping {file_path.name} (not found)")
        return False

    content = file_path.read_text()
    original = content

    # Apply fixes
    content = add_imports(content, file_path)
    content = add_hook_call(content, file_path)
    content = fix_animations(content, file_path)

    # Write if changed
    if content != original:
        file_path.write_text(content)
        return True

    return False


def main() -> None:
    """Main entry point."""
    print("Fixing STYLE.md compliance in Admin components...")
    print(f"Directory: {ADMIN_DIR}")
    print()

    files_changed = 0

    for filename in FILES_TO_PROCESS:
        file_path = ADMIN_DIR / filename
        print(f"Processing {filename}...")
        if process_file(file_path):
            files_changed += 1
        else:
            print("  No changes needed")

    print()
    print(f"Processed {len(FILES_TO_PROCESS)} files, {files_changed} changed")


if __name__ == "__main__":
    main()
