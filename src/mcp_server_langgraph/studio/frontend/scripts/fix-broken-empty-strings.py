#!/usr/bin/env python3
"""Fix broken empty string patterns from previous migration."""

import re
from pathlib import Path

FIXES = [
    # Fix broken assignments: = ; → = "";
    (r"= ;$", '= "";'),
    # Fix broken ternary: : } → : "" }
    (r": \}", ': "" }'),
    # Fix broken template strings ending: ` → `}`
    (r": \)`", ': "")`'),
    # Fix broken array elements: { description: }, → { description: "" },
    (r"description: \}", 'description: "" }'),
    # Fix broken query: query: }, → query: "" },
    (r"query: \}", 'query: "" }'),
]

COMPILED = [(re.compile(p), r) for p, r in FIXES]


def fix_file(path: Path) -> int:
    try:
        content = path.read_text(encoding="utf-8")
    except Exception:
        return 0

    original = content
    total = 0

    for pattern, repl in COMPILED:
        content, count = pattern.subn(repl, content)
        total += count

    if content != original:
        path.write_text(content, encoding="utf-8")
        return total
    return 0


def main() -> None:
    src = Path("src")
    files = list(src.rglob("*.tsx")) + list(src.rglob("*.ts"))
    files = [f for f in files if "node_modules" not in str(f)]

    total = 0
    for f in files:
        count = fix_file(f)
        if count:
            print(f"  Fixed {f}: {count} patterns")
            total += count

    print(f"\nTotal fixes: {total}")


if __name__ == "__main__":
    main()
