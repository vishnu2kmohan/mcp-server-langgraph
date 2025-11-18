#!/usr/bin/env python3
"""Fix subprocess.run() calls with timeout < 30s by increasing to 30s."""

import sys
from pathlib import Path


try:
    import libcst as cst
except ImportError:
    print("Error: libcst not installed")
    sys.exit(1)


class ShortTimeoutFixer(cst.CSTTransformer):
    """Transformer that increases short timeouts to minimum 30s."""

    def __init__(self):
        self.modifications = 0

    def leave_Call(self, original_node: cst.Call, updated_node: cst.Call) -> cst.Call:
        """Increase timeout values < 30 to 30."""
        # Check if this is a subprocess.run() call
        if isinstance(updated_node.func, cst.Attribute):
            if (
                updated_node.func.attr.value == "run"
                and isinstance(updated_node.func.value, cst.Name)
                and updated_node.func.value.value == "subprocess"
            ):
                # Find timeout parameter and check if it's < 30
                new_args = []
                modified = False

                for arg in updated_node.args:
                    if arg.keyword and arg.keyword.value == "timeout":
                        # Check if timeout value is < 30
                        if isinstance(arg.value, cst.Integer):
                            timeout_val = int(arg.value.value)
                            if timeout_val < 30:
                                # Replace with 30
                                new_arg = arg.with_changes(value=cst.Integer("30"))
                                new_args.append(new_arg)
                                modified = True
                                self.modifications += 1
                                continue

                    new_args.append(arg)

                if modified:
                    updated_node = updated_node.with_changes(args=new_args)

        return updated_node


def fix_file(file_path: Path) -> int:
    """Fix short timeouts in a single file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            source_code = f.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return 0

    try:
        tree = cst.parse_module(source_code)
    except cst.ParserSyntaxError as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        return 0

    transformer = ShortTimeoutFixer()
    modified_tree = tree.visit(transformer)

    if transformer.modifications > 0:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(modified_tree.code)

    return transformer.modifications


def main():
    """Fix files with short timeouts."""
    repo_root = Path(__file__).parent.parent
    tests_dir = repo_root / "tests"

    # Files identified by the test
    files_to_fix = [
        "test_test_utilities.py",
        "integration/test_docker_health_checks.py",
        "integration/test_docker_image_assets.py",
        "meta/test_id_pollution_prevention.py",
        "meta/test_performance_regression.py",
        "meta/test_plugin_guards.py",
        "regression/test_bearer_scheme_override_diagnostic.py",
    ]

    total_modifications = 0

    for file_rel in files_to_fix:
        file_path = tests_dir / file_rel
        if file_path.exists():
            mods = fix_file(file_path)
            if mods > 0:
                total_modifications += mods
                print(f"Fixed {file_path.relative_to(repo_root)}: {mods} call(s)")

    print(f"\n=== SUMMARY ===")
    print(f"Total modifications: {total_modifications}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
