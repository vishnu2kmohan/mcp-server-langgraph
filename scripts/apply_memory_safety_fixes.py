#!/usr/bin/env python3
"""
Script to apply memory safety fixes to test files (xdist_group decorator + gc.collect() teardown)

This script:
1. Adds `import gc` to test files
2. Adds `@pytest.mark.xdist_group(name="...")` decorator to each test class
3. Adds `teardown_method()` with `gc.collect()` to each test class
"""

import re
import sys
from pathlib import Path


def process_file(file_path: str, group_name: str) -> bool:
    """
    Process a single test file to add memory safety fixes.

    Args:
        file_path: Path to the test file
        group_name: Name for the xdist group

    Returns:
        True if file was modified, False otherwise
    """
    file_path = Path(file_path)
    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        return False

    # Read file
    with open(file_path) as f:
        lines = f.readlines()

    modified = False

    # Add import gc if not present
    has_gc_import = any("import gc" in line for line in lines)
    if not has_gc_import:
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith("from "):
                # Insert after first import block
                if i > 0 and not (lines[i - 1].startswith("import ") or lines[i - 1].startswith("from ")):
                    continue
                # Find end of import block
                j = i
                while j < len(lines) and (
                    lines[j].startswith("import ") or lines[j].startswith("from ") or lines[j].strip() == ""
                ):
                    j += 1
                # Insert gc import before first non-import line
                lines.insert(j, "import gc\n")
                modified = True
                break

    # Process all test classes
    i = 0
    while i < len(lines):
        # Look for test class definitions
        if re.match(r"^class Test\w+:", lines[i]):
            # Check if already has decorator
            if i > 0 and "@pytest.mark.xdist_group" in lines[i - 1]:
                i += 1
                continue

            # Add decorator before class
            lines.insert(i, f'@pytest.mark.xdist_group(name="{group_name}")\n')
            modified = True
            i += 1  # Skip decorator
            i += 1  # Skip class definition

            # Skip docstring if present
            if i < len(lines) and lines[i].strip().startswith('"""'):
                if lines[i].strip().endswith('"""') and lines[i].strip() != '"""':
                    # Single-line docstring
                    i += 1
                else:
                    # Multi-line docstring
                    i += 1
                    while i < len(lines) and '"""' not in lines[i]:
                        i += 1
                    if i < len(lines):
                        i += 1  # Skip closing """

            # Check if teardown already exists
            has_teardown = False
            for j in range(i, min(i + 20, len(lines))):
                if "def teardown_method" in lines[j]:
                    has_teardown = True
                    break

            if not has_teardown:
                # Insert teardown method
                teardown = [
                    "\n",
                    "    def teardown_method(self):\n",
                    '        """Force GC to prevent mock accumulation in xdist workers"""\n',
                    "        gc.collect()\n",
                ]
                for line in reversed(teardown):
                    lines.insert(i, line)
                modified = True

        i += 1

    # Write back if modified
    if modified:
        with open(file_path, "w") as f:
            f.writelines(lines)
        print(f"✓ Updated: {file_path}")
        return True
    print(f"  Skipped (no changes needed): {file_path}")
    return False


def main():
    """Main entry point"""
    # Define files to process with their group names
    files_to_process = [
        # Batch 2: API Endpoints
        ("tests/api/test_service_principals_endpoints.py", "service_principals_api_tests"),
        ("tests/api/test_api_keys_endpoints.py", "api_keys_api_tests"),
        # Batch 3: GDPR Compliance
        ("tests/test_gdpr.py", "gdpr_tests"),
        ("tests/integration/test_gdpr_endpoints.py", "gdpr_integration_tests"),
        # Batch 4: Session & Auth
        ("tests/test_session_timeout.py", "session_timeout_tests"),
        ("tests/test_llm_factory_contract.py", "llm_factory_tests"),
        # Batch 5: Startup & Validation
        ("tests/integration/test_app_startup_validation.py", "app_startup_integration_tests"),
        ("tests/unit/test_dependencies_wiring.py", "dependencies_wiring_tests"),
        ("tests/smoke/test_ci_startup_smoke.py", "ci_startup_smoke_tests"),
        # Batch 6: Core Services
        ("tests/test_user_provider.py", "user_provider_tests"),
        ("tests/test_context_manager.py", "context_manager_tests"),
        # tests/conftest.py - special case, will handle separately
    ]

    total = len(files_to_process)
    updated = 0

    print(f"Processing {total} test files...\n")

    for file_path, group_name in files_to_process:
        if process_file(file_path, group_name):
            updated += 1

    print(f"\n{'=' * 60}")
    print(f"Summary: {updated}/{total} files updated")
    print(f"{'=' * 60}")

    return 0 if updated > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
