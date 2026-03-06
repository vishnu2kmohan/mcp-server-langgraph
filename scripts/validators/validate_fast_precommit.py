#!/usr/bin/env python3
"""Consolidated fast pre-commit validator.

Runs multiple lightweight validation checks in a single Python process,
eliminating repeated interpreter startup overhead (~0.4s per invocation).

Checks included:
1. Alembic duplicate revision IDs
2. WebSocket permissions schema alignment (OpenFGA model)
3. ADR synchronization (badge count, numbering, mdx sync)

The frontend design system check is NOT included because it delegates to
a subprocess (design-system.py) and wouldn't benefit from in-process execution.

Usage:
    python scripts/validators/validate_fast_precommit.py
    python scripts/validators/validate_fast_precommit.py --check alembic
    python scripts/validators/validate_fast_precommit.py --check websocket --check adr

Exit codes:
    0 - All checks passed
    1 - One or more checks failed
"""

from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path

# Find project root
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent


# =============================================================================
# Check 1: Alembic Duplicate Revision IDs
# =============================================================================
def check_alembic_duplicates() -> tuple[bool, str]:
    """Check for duplicate Alembic revision IDs."""
    versions_dir = PROJECT_ROOT / "alembic" / "versions"

    if not versions_dir.exists():
        return True, "alembic: skipped (no alembic/versions/ directory)"

    revision_to_files: dict[str, list[str]] = {}
    for migration_file in versions_dir.glob("*.py"):
        if migration_file.name.startswith("_"):
            continue
        content = migration_file.read_text()
        match = re.search(r'revision[:\s].*?[=]\s*["\']([^"\']+)["\']', content)
        if match:
            rev_id = match.group(1)
            revision_to_files.setdefault(rev_id, []).append(migration_file.name)

    duplicates = [(rev, files) for rev, files in revision_to_files.items() if len(files) > 1]

    if duplicates:
        lines = ["alembic: FAILED - duplicate revision IDs"]
        for rev_id, files in duplicates:
            lines.append(f"  revision '{rev_id}' in: {', '.join(files)}")
        return False, "\n".join(lines)

    migration_count = len(list(versions_dir.glob("*.py")))
    return True, f"alembic: OK ({migration_count} migrations, no duplicates)"


# =============================================================================
# Check 2: WebSocket Permissions Schema
# =============================================================================
def check_websocket_permissions() -> tuple[bool, str]:
    """Validate WebSocket permissions align with OpenFGA model."""
    user_py = PROJECT_ROOT / "src/mcp_server_langgraph/api/v1/user.py"
    model_json = PROJECT_ROOT / "config/openfga/model.json"

    if not user_py.exists():
        return True, "websocket-permissions: skipped (user.py not found)"
    if not model_json.exists():
        return True, "websocket-permissions: skipped (model.json not found)"

    # Extract permissions map via AST
    source = user_py.read_text()
    tree = ast.parse(source)
    permissions_map: dict[str, tuple[str, str, str]] = {}

    for node in ast.walk(tree):
        target_name = None
        value_node = None
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "WEBSOCKET_PERMISSIONS_MAP":
                    target_name = target.id
                    value_node = node.value
                    break
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "WEBSOCKET_PERMISSIONS_MAP":
                target_name = node.target.id
                value_node = node.value

        if target_name and value_node and isinstance(value_node, ast.Dict):
            for key, value in zip(value_node.keys, value_node.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(value, ast.Tuple):
                    vals = tuple(elt.value for elt in value.elts if isinstance(elt, ast.Constant))
                    if len(vals) == 3:
                        permissions_map[key.value] = vals

    if not permissions_map:
        return False, "websocket-permissions: FAILED - WEBSOCKET_PERMISSIONS_MAP not found"

    # Load OpenFGA model
    with model_json.open() as f:
        model = json.load(f)

    types_relations: dict[str, set[str]] = {}
    for type_def in model.get("type_definitions", []):
        type_name = type_def.get("type", "")
        relations = set(type_def.get("relations", {}).keys())
        types_relations[type_name] = relations

    # Validate
    errors: list[str] = []
    for perm_key, (obj_type, _obj_id, relation) in permissions_map.items():
        if obj_type not in types_relations:
            errors.append(f"  '{perm_key}': type '{obj_type}' not in model.json")
        elif relation not in types_relations[obj_type]:
            errors.append(f"  '{perm_key}': relation '{relation}' not in type '{obj_type}'")

    if errors:
        return False, "websocket-permissions: FAILED\n" + "\n".join(errors)

    return True, f"websocket-permissions: OK ({len(permissions_map)} permissions validated)"


# =============================================================================
# Check 3: ADR Synchronization
# =============================================================================
def check_adr_sync() -> tuple[bool, str]:
    """Validate ADR synchronization (badge, numbering, mdx sync)."""
    adr_dir = PROJECT_ROOT / "adr"
    docs_dir = PROJECT_ROOT / "docs" / "architecture"
    readme_path = PROJECT_ROOT / "README.md"

    if not adr_dir.exists():
        return True, "adr-sync: skipped (no adr/ directory)"

    results: list[str] = []
    passed = True

    # Badge count
    actual_count = len(list(adr_dir.glob("adr-*.md")))
    if readme_path.exists():
        content = readme_path.read_text()
        badge_match = re.search(r"ADRs-(\d+)-informational", content)
        if badge_match:
            badge_count = int(badge_match.group(1))
            if actual_count != badge_count:
                results.append(f"  badge mismatch: {badge_count} in README vs {actual_count} files")
                passed = False

    # Duplicate numbering
    adr_numbers = []
    for f in adr_dir.glob("adr-*.md"):
        m = re.match(r"adr-(\d+)-", f.name)
        if m:
            adr_numbers.append(int(m.group(1)))

    counts = Counter(adr_numbers)
    duplicates = [num for num, count in counts.items() if count > 1]
    if duplicates:
        results.append(f"  duplicate ADR numbers: {sorted(duplicates)}")
        passed = False

    # MDX sync
    source_adrs = {f.stem for f in adr_dir.glob("adr-*.md")}
    docs_adrs = {f.stem for f in docs_dir.glob("adr-*.mdx")} if docs_dir.exists() else set()
    missing = source_adrs - docs_adrs
    if missing:
        results.append(f"  {len(missing)} ADRs missing .mdx in docs/architecture/")
        passed = False

    if passed:
        return True, f"adr-sync: OK ({actual_count} ADRs, numbering valid, mdx synced)"

    return False, "adr-sync: FAILED\n" + "\n".join(results)


# =============================================================================
# Main
# =============================================================================
ALL_CHECKS = {
    "alembic": check_alembic_duplicates,
    "websocket": check_websocket_permissions,
    "adr": check_adr_sync,
}


def main() -> int:
    """Run all fast pre-commit checks in a single process."""
    # Parse optional --check arguments
    checks_to_run = list(ALL_CHECKS.keys())
    if "--check" in sys.argv:
        checks_to_run = []
        args = sys.argv[1:]
        i = 0
        while i < len(args):
            if args[i] == "--check" and i + 1 < len(args):
                checks_to_run.append(args[i + 1])
                i += 2
            else:
                i += 1

    print(f"Running {len(checks_to_run)} pre-commit checks...")
    print()

    failed = 0
    for name in checks_to_run:
        check_fn = ALL_CHECKS.get(name)
        if not check_fn:
            print(f"  unknown check: {name}")
            failed += 1
            continue

        ok, message = check_fn()
        print(f"  {message}")
        if not ok:
            failed += 1

    print()
    total = len(checks_to_run)
    passed = total - failed
    if failed:
        print(f"FAILED: {passed}/{total} checks passed, {failed} failed")
        return 1

    print(f"OK: {passed}/{total} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
