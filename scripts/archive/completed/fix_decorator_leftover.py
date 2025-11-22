#!/usr/bin/env python3
"""Fix leftover @pytest.fixture decorators after fixture removal."""

import re
from pathlib import Path


def fix_leftover_decorators(file_path: Path) -> bool:
    """Remove leftover @pytest.fixture(scope="module", autouse=True) decorators."""
    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  ❌ Error reading {file_path}: {e}")
        return False

    # Pattern to match the decorator line
    pattern = r'@pytest\.fixture\(scope="module", autouse=True\)\n'

    if re.search(pattern, content):
        # Remove the decorator line
        new_content = re.sub(pattern, "", content)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  ✅ Fixed {file_path}")
            return True
        except Exception as e:
            print(f"  ❌ Error writing {file_path}: {e}")
            return False
    return False


def main():
    test_dir = Path(__file__).parent.parent / "tests"

    # Get all files with leftover decorators
    import subprocess

    result = subprocess.run(
        ["grep", "-rn", '@pytest.fixture(scope="module", autouse=True)', "tests/", "--include=*.py"],
        capture_output=True,
        text=True,
        cwd=test_dir.parent,
    )

    if result.returncode != 0:
        print("✅ No leftover decorators found!")
        return

    files_to_fix = set()
    for line in result.stdout.strip().split("\n"):
        if line:
            file_path = line.split(":")[0]
            files_to_fix.add(file_path)

    print(f"🔧 Fixing {len(files_to_fix)} files with leftover decorators...")
    print()

    fixed_count = 0
    for file_rel_path in sorted(files_to_fix):
        file_path = test_dir.parent / file_rel_path
        if fix_leftover_decorators(file_path):
            fixed_count += 1

    print()
    print(f"✅ Fixed {fixed_count} files")


if __name__ == "__main__":
    main()
