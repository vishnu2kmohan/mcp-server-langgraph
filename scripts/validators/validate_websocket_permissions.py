#!/usr/bin/env python3
"""
WebSocket Permissions Schema Validator

Validates alignment between:
1. WEBSOCKET_PERMISSIONS_MAP in src/mcp_server_langgraph/api/v1/user.py
2. OpenFGA model in config/openfga/model.json

Security Requirement: Ensures all WebSocket permissions map to valid OpenFGA
type:relation tuples, preventing authorization bypasses from schema drift.

Exit codes:
- 0: All validations passed
- 1: Validation errors found
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

# Expected number of WebSocket permissions
EXPECTED_PERMISSION_COUNT = 17

# Find project root (where pyproject.toml lives)
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent

USER_PY_PATH = PROJECT_ROOT / "src/mcp_server_langgraph/api/v1/user.py"
OPENFGA_MODEL_PATH = PROJECT_ROOT / "config/openfga/model.json"


def extract_websocket_permissions_map(user_py_path: Path) -> dict[str, tuple[str, str, str]]:
    """Extract WEBSOCKET_PERMISSIONS_MAP from user.py using AST parsing.

    This approach avoids importing the module which could trigger
    side effects or require dependencies.
    """
    if not user_py_path.exists():
        print(f"ERROR: {user_py_path} not found")
        sys.exit(1)

    source = user_py_path.read_text()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        # Handle both regular assignment and annotated assignment (with type hints)
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
            permissions_map = {}
            for key, value in zip(value_node.keys, value_node.values, strict=True):
                if isinstance(key, ast.Constant) and isinstance(value, ast.Tuple):
                    permission_key = key.value
                    tuple_values = tuple(
                        elt.value for elt in value.elts if isinstance(elt, ast.Constant)
                    )
                    if len(tuple_values) == 3:
                        permissions_map[permission_key] = tuple_values
            return permissions_map

    print("ERROR: WEBSOCKET_PERMISSIONS_MAP not found in user.py")
    sys.exit(1)


def load_openfga_model(model_path: Path) -> dict[str, Any]:
    """Load OpenFGA model.json."""
    if not model_path.exists():
        print(f"ERROR: {model_path} not found")
        sys.exit(1)

    with model_path.open() as f:
        return json.load(f)


def extract_types_and_relations(model: dict[str, Any]) -> dict[str, set[str]]:
    """Extract all types and their relations from OpenFGA model.

    Returns a dict mapping type name -> set of relation names.
    """
    types_relations: dict[str, set[str]] = {}

    for type_def in model.get("type_definitions", []):
        type_name = type_def.get("type", "")
        relations = set(type_def.get("relations", {}).keys())
        types_relations[type_name] = relations

    return types_relations


def validate_permissions(
    permissions_map: dict[str, tuple[str, str, str]], types_relations: dict[str, set[str]]
) -> list[str]:
    """Validate that all permissions map to valid OpenFGA types and relations.

    Returns list of error messages.
    """
    errors: list[str] = []

    for perm_key, (obj_type, obj_id, relation) in permissions_map.items():
        # Check if type exists
        if obj_type not in types_relations:
            errors.append(
                f"Permission '{perm_key}': OpenFGA type '{obj_type}' not found in model.json"
            )
            continue

        # Check if relation exists for this type
        type_relations = types_relations[obj_type]
        if relation not in type_relations:
            errors.append(
                f"Permission '{perm_key}': Relation '{relation}' not found in type '{obj_type}'. "
                f"Available relations: {sorted(type_relations)}"
            )

    return errors


def main() -> int:
    """Run all validations and report results."""
    print("Validating WebSocket Permissions Schema...")
    print(f"  user.py: {USER_PY_PATH}")
    print(f"  model.json: {OPENFGA_MODEL_PATH}")
    print()

    # Extract permissions map from user.py
    permissions_map = extract_websocket_permissions_map(USER_PY_PATH)
    print(f"Found {len(permissions_map)} permissions in WEBSOCKET_PERMISSIONS_MAP")

    # Check permission count
    if len(permissions_map) != EXPECTED_PERMISSION_COUNT:
        print(
            f"WARNING: Expected {EXPECTED_PERMISSION_COUNT} permissions, "
            f"found {len(permissions_map)}"
        )

    # Load and parse OpenFGA model
    model = load_openfga_model(OPENFGA_MODEL_PATH)
    types_relations = extract_types_and_relations(model)
    print(f"Found {len(types_relations)} types in OpenFGA model")
    print()

    # Validate permissions
    errors = validate_permissions(permissions_map, types_relations)

    if errors:
        print("VALIDATION ERRORS:")
        for error in errors:
            print(f"  - {error}")
        print()
        print(f"Found {len(errors)} error(s)")
        return 1

    print("All permissions validated successfully!")
    print()

    # Print summary table
    print("Permission Mapping Summary:")
    print("-" * 70)
    print(f"{'Permission Key':<25} {'Type':<15} {'Object ID':<20} {'Relation':<10}")
    print("-" * 70)
    for perm_key, (obj_type, obj_id, relation) in sorted(permissions_map.items()):
        print(f"{perm_key:<25} {obj_type:<15} {obj_id:<20} {relation:<10}")
    print("-" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
