#!/usr/bin/env python3
"""
Fix Duplicate className Attributes

Merges duplicate className attributes into a single cn() call.

Before:
  className="foo bar"
  className={getIndentClass(x)}

After:
  className={cn("foo bar", getIndentClass(x))}
"""

import re
import sys
from pathlib import Path


def fix_duplicate_classnames(content: str) -> tuple[str, int]:
    """
    Fix duplicate className attributes by merging them with cn().

    Returns: (modified_content, fix_count)
    """
    fixes = 0

    # Pattern[str] 1: className="string" followed by className={expression}
    # This captures: className="foo" followed by className={bar}
    pattern1 = r'className="([^"]+)"\s*\n\s*className=\{([^}]+)\}'

    def merge_classnames(m: re.Match[str]) -> str:
        static_classes = m.group(1)
        dynamic_expr = m.group(2)
        return f'className={{cn("{static_classes}", {dynamic_expr})}}'

    new_content, count1 = re.subn(pattern1, merge_classnames, content)
    if count1 > 0:
        content = new_content
        fixes += count1

    # Pattern[str] 2: className={`${expr}`} followed by className={expression}
    pattern2 = r"className=\{`([^`]+)`\}\s*\n\s*className=\{([^}]+)\}"

    def merge_template(m: re.Match[str]) -> str:
        template = m.group(1)
        dynamic_expr = m.group(2)
        return f"className={{cn(`{template}`, {dynamic_expr})}}"

    new_content, count2 = re.subn(pattern2, merge_template, content)
    if count2 > 0:
        content = new_content
        fixes += count2

    return content, fixes


def ensure_cn_import(content: str) -> str:
    """Ensure cn is imported if used."""
    if "cn(" in content and "import { cn }" not in content and "import {cn}" not in content:
        # Check if cn is imported with other things
        if "from '@/utils/cn'" not in content and 'from "@/utils/cn"' not in content:
            # Add import at the top after other imports
            import_line = "import { cn } from '@/utils/cn';\n"
            # Find first import
            first_import = content.find("import ")
            if first_import != -1:
                # Find end of imports section (first non-import line)
                lines = content.split("\n")
                last_import_idx = 0
                for i, line in enumerate(lines):
                    if (
                        line.strip().startswith("import ")
                        or line.strip().startswith("} from")
                        or (line.strip() and not line.strip().startswith("//") and "from" in line and "'" in line)
                    ):
                        last_import_idx = i
                    elif (
                        line.strip()
                        and not line.strip().startswith("//")
                        and not line.strip().startswith("import")
                        and not line.strip().startswith("}")
                        and "from" not in line
                    ):
                        if i > last_import_idx + 1:
                            break

                # Insert after last import
                lines.insert(last_import_idx + 1, import_line.strip())
                content = "\n".join(lines)

    return content


def ensure_indent_import(content: str) -> str:
    """Ensure getIndentClass is imported if used."""
    if "getIndentClass(" in content and "import { getIndentClass }" not in content:
        if "from '@/utils/indent'" not in content and 'from "@/utils/indent"' not in content:
            import_line = "import { getIndentClass } from '@/utils/indent';\n"
            first_import = content.find("import ")
            if first_import != -1:
                lines = content.split("\n")
                last_import_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith("import "):
                        last_import_idx = i

                lines.insert(last_import_idx + 1, import_line.strip())
                content = "\n".join(lines)

    return content


def process_file(file_path: Path) -> int:
    """Process a single file. Returns number of fixes applied."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return 0

    original = content

    # Fix duplicate classNames
    content, fix_count = fix_duplicate_classnames(content)

    # Ensure imports
    content = ensure_cn_import(content)
    content = ensure_indent_import(content)

    if content != original:
        try:
            file_path.write_text(content, encoding="utf-8")
            print(f"Fixed {fix_count} duplicate className(s) in {file_path}")
        except Exception as e:
            print(f"Error writing {file_path}: {e}", file=sys.stderr)
            return 0

    return fix_count


def main() -> int:
    """Main entry point."""
    # Files that need fixing based on TypeScript errors
    files_to_fix = [
        "src/components/Artifacts/JSONArtifact.tsx",
        "src/components/DevTools/tabs/StateTab.tsx",
        "src/components/DevTools/tabs/TracesTab.tsx",
    ]

    total_fixes = 0

    for file_str in files_to_fix:
        file_path = Path(file_str)
        if file_path.exists():
            fixes = process_file(file_path)
            total_fixes += fixes
        else:
            print(f"File not found: {file_path}", file=sys.stderr)

    print(f"\nTotal fixes applied: {total_fixes}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
