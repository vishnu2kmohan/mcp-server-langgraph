#!/usr/bin/env python3
"""
Validate OpenFGA tuples against model schema.

This script validates that sample-tuples.json only contains tuples that
can be directly assigned according to the model.json schema. It catches
issues like trying to directly assign computed-only relations.

Usage:
    python scripts/validation/validate_openfga_tuples.py

Exit codes:
    0 - All tuples valid
    1 - Validation errors found
    2 - File not found or parse error

Reference: ADR-0068 - Gateway-Level Authentication
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

# Config file paths (relative to repo root)
REPO_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = REPO_ROOT / "config" / "openfga"
MODEL_PATH = CONFIG_DIR / "model.json"
TUPLES_PATH = CONFIG_DIR / "sample-tuples.json"


def load_json_file(path: Path) -> dict | None:
    """Load and parse a JSON file, returning None on error."""
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: File not found: {path}")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {path}: {e}")
        return None


def extract_object_type(obj: str) -> str:
    """Extract type from object string (e.g., 'vector_store:default' -> 'vector_store')."""
    if ":" in obj:
        return obj.split(":")[0]
    return obj


def extract_user_type(user: str) -> str:
    """Extract type from user string (e.g., 'user:alice' -> 'user')."""
    if ":" in user:
        return user.split(":")[0]
    return user


def get_type_definitions(model: dict) -> dict[str, dict]:
    """Extract type name -> type definition mapping from model."""
    return {t["type"]: t for t in model.get("type_definitions", [])}


def get_directly_assignable_relations(model: dict) -> dict[str, set[str]]:
    """
    Extract type -> directly assignable relations mapping from model.

    A relation is directly assignable if it has an entry in the type's
    metadata.relations with directly_related_user_types. Relations that
    are computed-only (via computedUserset without "this": {}) will NOT
    have a metadata entry and cannot be directly assigned in tuples.
    """
    result: dict[str, set[str]] = {}
    for type_def in model.get("type_definitions", []):
        type_name = type_def.get("type")
        metadata_relations = type_def.get("metadata", {}).get("relations", {})
        result[type_name] = set(metadata_relations.keys())
    return result


def get_all_relations(model: dict) -> dict[str, set[str]]:
    """Extract type -> all relations (including computed) mapping from model."""
    result: dict[str, set[str]] = {}
    for type_def in model.get("type_definitions", []):
        type_name = type_def.get("type")
        relations = set(type_def.get("relations", {}).keys())
        result[type_name] = relations
    return result


def validate_tuples_against_model(tuples: Sequence[dict], model: dict) -> list[str]:
    """
    Validate tuples against model schema.

    Returns a list of error messages for invalid tuples.
    """
    errors: list[str] = []
    type_defs = get_type_definitions(model)
    directly_assignable = get_directly_assignable_relations(model)
    all_relations = get_all_relations(model)

    for i, t in enumerate(tuples):
        # Skip section header entries (documentation dividers, not tuples)
        if "_section" in t:
            continue

        # Skip comment-only entries
        if "user" not in t or "relation" not in t or "object" not in t:
            continue

        user = t["user"]
        relation = t["relation"]
        obj = t["object"]

        obj_type = extract_object_type(obj)
        user_type = extract_user_type(user)

        # Check object type exists
        if obj_type not in type_defs:
            errors.append(f"Tuple {i}: Object '{obj}' references undefined type '{obj_type}'")
            continue

        # Check user type exists
        if user_type not in type_defs:
            errors.append(f"Tuple {i}: User '{user}' references undefined type '{user_type}'")
            continue

        # Check relation exists for object type
        if obj_type in all_relations:
            valid = all_relations[obj_type]
            if relation not in valid:
                errors.append(f"Tuple {i}: Relation '{relation}' not defined for type '{obj_type}'. Valid relations: {valid}")
                continue

        # Check relation is directly assignable (not computed-only)
        if obj_type in directly_assignable:
            valid_direct = directly_assignable[obj_type]
            if relation not in valid_direct:
                computed = all_relations.get(obj_type, set()) - valid_direct
                errors.append(
                    f"Tuple {i}: Relation '{relation}' is computed-only for type '{obj_type}' "
                    f"and cannot be directly assigned. "
                    f"Tuple: ({user}, {relation}, {obj}). "
                    f"Directly assignable: {valid_direct}. "
                    f"Computed-only: {computed}."
                )

    return errors


def main() -> int:
    """Main entry point."""
    print("Validating OpenFGA tuples against model schema...")
    print(f"  Model: {MODEL_PATH}")
    print(f"  Tuples: {TUPLES_PATH}")
    print()

    # Load files
    model = load_json_file(MODEL_PATH)
    if model is None:
        return 2

    tuples_config = load_json_file(TUPLES_PATH)
    if tuples_config is None:
        return 2

    tuples = tuples_config.get("tuples", [])
    if not tuples:
        print("WARNING: No tuples found in config")
        return 0

    # Count valid tuples (excluding section headers and comment-only entries)
    valid_tuples = [t for t in tuples if "_section" not in t and "user" in t and "relation" in t and "object" in t]
    print(f"Found {len(valid_tuples)} tuples to validate")
    print()

    # Validate
    errors = validate_tuples_against_model(tuples, model)

    if errors:
        print(f"ERROR: {len(errors)} invalid tuple(s) found:")
        for e in errors:
            print(f"  - {e}")
        print()
        print("Fix these issues before seeding OpenFGA.")
        return 1

    print(f"OK: All {len(valid_tuples)} tuples are valid against model schema")
    return 0


if __name__ == "__main__":
    sys.exit(main())
