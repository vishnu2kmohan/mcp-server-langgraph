#!/usr/bin/env python3
"""
OpenFGA Model Composition and Extraction Utilities.

This script provides utilities to:
1. Extract types from model.json into modular .fga files (DSL format)
2. Compose modular .fga files back into model.json
3. Validate that all types are covered by module definitions

Bidirectional Workflow:
- Extract: model.json → .fga modules (for review/documentation)
- Compose: .fga modules → model.json (for modular editing)
- Validate: Check that all types are covered by modules

Commands:
  python compose_model.py extract   - model.json → .fga modules
  python compose_model.py compose   - .fga modules → model.json
  python compose_model.py validate  - Verify module coverage

Reference: ADR-0068 Phase 8 - Modularization
"""

import json
from pathlib import Path
from typing import Any

# Module definitions: (module_name, type_list, description)
MODULES = [
    ("01-core", ["user", "organization", "service_principal"], "Base identity types"),
    (
        "02-resources",
        ["tool", "workflow", "session", "project", "artifact", "conversation", "vector_store"],
        "Main business resources",
    ),
    ("03-observability", ["dashboard", "logs", "traces", "metrics", "observability"], "Monitoring and telemetry"),
    ("04-access-control", ["authz", "system", "api_key", "partner"], "Authentication & authorization"),
    ("05-ai-agents", ["ai", "agent"], "AI and agent configuration"),
    ("06-skills", ["skill", "marketplace"], "Skills and marketplace"),
    ("07-semantic-index", ["tool_index", "skill_index", "memory_index"], "Semantic search indices"),
    ("08-infrastructure", ["gateway", "identity", "mcp", "mcp_connection", "connection"], "Infrastructure access"),
    ("09-financial", ["cost", "budget", "execution", "compliance", "config", "chat"], "Financial and compliance"),
]


def type_to_fga_dsl(type_def: dict[str, Any]) -> str:
    """Convert a JSON type definition to OpenFGA DSL format."""
    lines = []
    type_name = type_def["type"]
    description = type_def.get("description", "")

    # Type header with optional description
    if description:
        lines.append(f"# {description}")
    lines.append(f"type {type_name}")

    # Relations
    relations = type_def.get("relations", {})
    if relations:
        lines.append("  relations")

        for rel_name, rel_def in relations.items():
            rel_str = _relation_to_dsl(rel_name, rel_def, type_def.get("metadata", {}).get("relations", {}).get(rel_name, {}))
            lines.append(f"    {rel_str}")

    return "\n".join(lines)


def _relation_to_dsl(name: str, definition: dict, metadata: dict) -> str:
    """Convert a relation definition to DSL format."""
    # Get directly related types from metadata
    related_types = []
    if "directly_related_user_types" in metadata:
        for t in metadata["directly_related_user_types"]:
            if "relation" in t:
                related_types.append(f"{t['type']}#{t['relation']}")
            elif t.get("wildcard"):
                related_types.append(f"{t['type']}:*")
            else:
                related_types.append(t["type"])

    # Simple "this" relation
    if "this" in definition and len(definition) == 1:
        if related_types:
            return f"define {name}: [{', '.join(related_types)}]"
        return f"define {name}: [user]"

    # Computed userset
    if "computedUserset" in definition:
        return f"define {name}: {definition['computedUserset']['relation']}"

    # Union
    if "union" in definition:
        parts = []
        for child in definition["union"]["child"]:
            if "this" in child:
                if related_types:
                    parts.append(f"[{', '.join(related_types)}]")
                else:
                    parts.append("[user]")
            elif "computedUserset" in child:
                parts.append(child["computedUserset"]["relation"])
            elif "tupleToUserset" in child:
                tupleset = child["tupleToUserset"]["tupleset"]["relation"]
                computed = child["tupleToUserset"]["computedUserset"]["relation"]
                parts.append(f"{tupleset}->{computed}")

        return f"define {name}: {' or '.join(parts)}"

    # Intersection (FGA DSL 'and' syntax)
    if "intersection" in definition:
        parts = []
        for child in definition["intersection"]["child"]:
            if "this" in child:
                if related_types:
                    parts.append(f"[{', '.join(related_types)}]")
                else:
                    parts.append("[user]")
            elif "computedUserset" in child:
                parts.append(child["computedUserset"]["relation"])
            elif "tupleToUserset" in child:
                tupleset = child["tupleToUserset"]["tupleset"]["relation"]
                computed = child["tupleToUserset"]["computedUserset"]["relation"]
                parts.append(f"{tupleset}->{computed}")

        return f"define {name}: {' and '.join(parts)}"

    # Difference (FGA DSL 'but not' syntax)
    if "difference" in definition:
        base = definition["difference"]["base"]
        subtract = definition["difference"]["subtract"]

        # Convert base to string
        if "this" in base:
            base_str = f"[{', '.join(related_types)}]" if related_types else "[user]"
        elif "computedUserset" in base:
            base_str = base["computedUserset"]["relation"]
        elif "tupleToUserset" in base:
            tupleset = base["tupleToUserset"]["tupleset"]["relation"]
            computed = base["tupleToUserset"]["computedUserset"]["relation"]
            base_str = f"{tupleset}->{computed}"
        else:
            base_str = "[user]"

        # Convert subtract to string
        if "this" in subtract:
            subtract_str = "[user]"
        elif "computedUserset" in subtract:
            subtract_str = subtract["computedUserset"]["relation"]
        elif "tupleToUserset" in subtract:
            tupleset = subtract["tupleToUserset"]["tupleset"]["relation"]
            computed = subtract["tupleToUserset"]["computedUserset"]["relation"]
            subtract_str = f"{tupleset}->{computed}"
        else:
            subtract_str = "[user]"

        return f"define {name}: {base_str} but not {subtract_str}"

    # Fallback
    return f"define {name}: [user]"


# =============================================================================
# Compose Functions: FGA DSL → JSON (Phase 8b - Bidirectional Sync)
# =============================================================================


def parse_fga_type(fga_content: str) -> dict[str, Any]:
    """
    Parse a single FGA type definition from DSL format to JSON.

    Handles:
    - Simple types: type user
    - Relations with direct types: define member: [user]
    - Multiple types: define owner: [user, service_principal]
    - Computed relations: define viewer: owner
    - Union relations: [user] or owner or organization->member
    - TupleToUserset: organization->member

    Args:
        fga_content: FGA DSL content for a single type (may include preceding comment)

    Returns:
        Dict matching OpenFGA model.json type_definitions structure
    """
    lines = fga_content.strip().split("\n")
    result: dict[str, Any] = {"type": "", "relations": {}, "metadata": {"relations": {}}}

    current_type = None
    in_relations = False

    for line in lines:
        stripped = line.strip()

        # Skip comments and empty lines
        if stripped.startswith("#") or not stripped:
            continue

        # Parse type declaration
        if stripped.startswith("type "):
            current_type = stripped[5:].strip()
            result["type"] = current_type
            continue

        # Enter relations section
        if stripped == "relations":
            in_relations = True
            continue

        # Parse relation definition
        if in_relations and stripped.startswith("define "):
            rel_name, rel_def, metadata = _parse_relation(stripped)
            result["relations"][rel_name] = rel_def
            if metadata:
                result["metadata"]["relations"][rel_name] = metadata

    return result


def _parse_relation(define_line: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Parse a single relation definition line.

    Args:
        define_line: Line like "define member: [user]" or "define viewer: owner"

    Returns:
        Tuple of (relation_name, relation_definition, metadata)
    """
    # Remove "define " prefix
    content = define_line[7:].strip()

    # Split on first colon
    colon_idx = content.index(":")
    rel_name = content[:colon_idx].strip()
    rel_expr = content[colon_idx + 1 :].strip()

    relation_def: dict[str, Any] = {}
    metadata: dict[str, Any] = {}

    # Check for difference (contains " but not ")
    # Difference has highest precedence, check first
    if " but not " in rel_expr:
        parts = rel_expr.split(" but not ", 1)  # Split only on first occurrence
        base_expr = parts[0].strip()
        subtract_expr = parts[1].strip()

        # Parse base
        if base_expr.startswith("[") and base_expr.endswith("]"):
            base = {"this": {}}
            metadata["directly_related_user_types"] = _parse_type_list(base_expr)
        elif "->" in base_expr:
            tupleset, computed = base_expr.split("->")
            base = {
                "tupleToUserset": {
                    "tupleset": {"relation": tupleset.strip()},
                    "computedUserset": {"relation": computed.strip()},
                }
            }
        else:
            base = {"computedUserset": {"relation": base_expr}}

        # Parse subtract
        if subtract_expr.startswith("[") and subtract_expr.endswith("]"):
            subtract = {"this": {}}
            # Note: subtract types don't typically need metadata
        elif "->" in subtract_expr:
            tupleset, computed = subtract_expr.split("->")
            subtract = {
                "tupleToUserset": {
                    "tupleset": {"relation": tupleset.strip()},
                    "computedUserset": {"relation": computed.strip()},
                }
            }
        else:
            subtract = {"computedUserset": {"relation": subtract_expr}}

        relation_def = {"difference": {"base": base, "subtract": subtract}}

    # Check for intersection (contains " and " but not " or ")
    # Intersection has higher precedence, so check first
    elif " and " in rel_expr and " or " not in rel_expr:
        parts = [p.strip() for p in rel_expr.split(" and ")]
        children = []

        for part in parts:
            if part.startswith("[") and part.endswith("]"):
                # Direct types: [user, service_principal]
                children.append({"this": {}})
                metadata["directly_related_user_types"] = _parse_type_list(part)
            elif "->" in part:
                # TupleToUserset: organization->member
                tupleset, computed = part.split("->")
                children.append(
                    {
                        "tupleToUserset": {
                            "tupleset": {"relation": tupleset.strip()},
                            "computedUserset": {"relation": computed.strip()},
                        }
                    }
                )
            else:
                # Computed userset reference
                children.append({"computedUserset": {"relation": part}})

        relation_def = {"intersection": {"child": children}}

    # Check for union (contains " or ")
    elif " or " in rel_expr:
        parts = [p.strip() for p in rel_expr.split(" or ")]
        children = []

        for part in parts:
            if part.startswith("[") and part.endswith("]"):
                # Direct types: [user, service_principal]
                children.append({"this": {}})
                metadata["directly_related_user_types"] = _parse_type_list(part)
            elif "->" in part:
                # TupleToUserset: organization->member
                tupleset, computed = part.split("->")
                children.append(
                    {
                        "tupleToUserset": {
                            "tupleset": {"relation": tupleset.strip()},
                            "computedUserset": {"relation": computed.strip()},
                        }
                    }
                )
            else:
                # Computed userset reference
                children.append({"computedUserset": {"relation": part}})

        relation_def = {"union": {"child": children}}

    elif rel_expr.startswith("[") and rel_expr.endswith("]"):
        # Simple direct relation: [user] or [user, service_principal]
        relation_def = {"this": {}}
        metadata["directly_related_user_types"] = _parse_type_list(rel_expr)

    elif "->" in rel_expr:
        # Single tupleToUserset (rare but possible)
        tupleset, computed = rel_expr.split("->")
        relation_def = {
            "tupleToUserset": {
                "tupleset": {"relation": tupleset.strip()},
                "computedUserset": {"relation": computed.strip()},
            }
        }

    else:
        # Computed userset: viewer: owner
        relation_def = {"computedUserset": {"relation": rel_expr}}

    return rel_name, relation_def, metadata


def _parse_type_list(bracket_expr: str) -> list[dict[str, Any]]:
    """
    Parse bracketed type list like [user, service_principal] or [organization#member].

    Args:
        bracket_expr: String like "[user, service_principal]"

    Returns:
        List of type dicts for directly_related_user_types
    """
    # Remove brackets
    inner = bracket_expr[1:-1].strip()
    if not inner:
        return []

    types = [t.strip() for t in inner.split(",")]
    result = []

    for t in types:
        if "#" in t:
            # Type with relation: organization#member
            type_name, relation = t.split("#")
            result.append({"type": type_name.strip(), "relation": relation.strip()})
        elif t.endswith(":*"):
            # Wildcard: user:*
            result.append({"type": t[:-2], "wildcard": {}})
        else:
            # Simple type
            result.append({"type": t})

    return result


def parse_fga_module(fga_content: str) -> list[dict[str, Any]]:
    """
    Parse a complete FGA module file and extract all type definitions.

    Args:
        fga_content: Complete .fga file content including model/schema header

    Returns:
        List of type definition dicts
    """
    types = []

    # Split content by "type " to find type blocks
    # First, normalize the content to identify type boundaries
    lines = fga_content.split("\n")

    # Track type blocks
    type_blocks = []
    current_block: list[str] = []
    in_type = False
    preceding_comment = None

    for line in lines:
        stripped = line.strip()

        # Skip model/schema declarations
        if stripped in ("model", "") or stripped.startswith("schema "):
            continue

        # Track comments that might precede a type
        if stripped.startswith("#"):
            if not in_type:
                preceding_comment = stripped
            else:
                current_block.append(line)
            continue

        # Start of a new type
        if stripped.startswith("type "):
            # Save previous block if exists
            if current_block:
                type_blocks.append("\n".join(current_block))

            # Start new block with optional preceding comment
            current_block = []
            if preceding_comment:
                current_block.append(preceding_comment)
                preceding_comment = None
            current_block.append(line)
            in_type = True
            continue

        # Continue current type block
        if in_type:
            if stripped.startswith("define ") or stripped == "relations" or not stripped:
                current_block.append(line)
            elif stripped and not stripped.startswith("#"):
                # Non-empty, non-comment line that's not a relation - might be end of type
                pass

    # Don't forget the last block
    if current_block:
        type_blocks.append("\n".join(current_block))

    # Parse each type block
    for block in type_blocks:
        if block.strip():
            type_def = parse_fga_type(block)
            if type_def.get("type"):
                types.append(type_def)

    return types


def compose_modules(modules_dir: Path) -> dict[str, Any]:
    """
    Compose all .fga module files into a single model.json structure.

    Args:
        modules_dir: Path to directory containing .fga module files

    Returns:
        Complete model dict with schema_version, type_definitions, and conditions
    """
    result: dict[str, Any] = {"schema_version": "1.1", "type_definitions": []}

    # Load conditions from 00-conditions.json if exists
    conditions_path = modules_dir / "00-conditions.json"
    if conditions_path.exists():
        with open(conditions_path) as f:
            content = f.read()
            # Skip comment lines at start
            lines = content.split("\n")
            json_start = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("{"):
                    json_start = i
                    break
            json_content = "\n".join(lines[json_start:])
            conditions_data = json.loads(json_content)
            if "conditions" in conditions_data:
                result["conditions"] = conditions_data["conditions"]

    # Get all .fga files sorted by name (preserves module order)
    fga_files = sorted(modules_dir.glob("*.fga"))

    for fga_file in fga_files:
        with open(fga_file) as f:
            content = f.read()

        types = parse_fga_module(content)
        result["type_definitions"].extend(types)

    return result


def extract_modules(model_path: Path, modules_dir: Path) -> None:
    """Extract types from model.json into modular .fga files."""
    with open(model_path) as f:
        model = json.load(f)

    type_defs = {t["type"]: t for t in model["type_definitions"]}
    modules_dir.mkdir(parents=True, exist_ok=True)

    for module_name, types, description in MODULES:
        module_content = [
            f"# Module: {module_name}",
            f"# Description: {description}",
            "# Reference: ADR-0068 Phase 8 - Modularization",
            "",
            "model",
            "  schema 1.1",
            "",
        ]

        for type_name in types:
            if type_name in type_defs:
                module_content.append(type_to_fga_dsl(type_defs[type_name]))
                module_content.append("")

        module_path = modules_dir / f"{module_name}.fga"
        with open(module_path, "w") as f:
            f.write("\n".join(module_content))

        print(f"Created: {module_path}")

    # Write conditions module
    if "conditions" in model:
        conditions_content = [
            "# Module: 00-conditions",
            "# Description: Conditional authorization expressions",
            "# Reference: ADR-0068 Phase 6 - Conditions",
            "",
            json.dumps({"conditions": model["conditions"]}, indent=2),
        ]

        conditions_path = modules_dir / "00-conditions.json"
        with open(conditions_path, "w") as f:
            f.write("\n".join(conditions_content))

        print(f"Created: {conditions_path}")


def get_module_types() -> dict[str, list[str]]:
    """Get mapping of module name to type list."""
    return {name: types for name, types, _ in MODULES}


def validate_coverage(model_path: Path) -> None:
    """Validate that all types are covered by modules."""
    with open(model_path) as f:
        model = json.load(f)

    model_types = {t["type"] for t in model["type_definitions"]}
    module_types = set()
    for _, types, _ in MODULES:
        module_types.update(types)

    missing = model_types - module_types
    extra = module_types - model_types

    if missing:
        print(f"Types in model but not in modules: {missing}")
    if extra:
        print(f"Types in modules but not in model: {extra}")

    if not missing and not extra:
        print("All types covered by modules")


# =============================================================================
# Round-Trip Diff Validation
# =============================================================================


def validate_roundtrip_diff(original: dict[str, Any], composed: dict[str, Any]) -> dict[str, Any]:
    """
    Validate differences between original and composed models.

    Compares type definitions and relations to identify:
    - Missing/extra types
    - Missing/extra relations per type
    - Relation structure differences

    Args:
        original: Original model.json dict
        composed: Composed model dict (from compose_modules)

    Returns:
        Diff report dict with:
        - types_match: bool - True if all types match
        - missing_types: list - Types in original but not composed
        - extra_types: list - Types in composed but not original
        - relation_diffs: dict - Per-type relation differences
    """
    original_types = {t["type"]: t for t in original.get("type_definitions", [])}
    composed_types = {t["type"]: t for t in composed.get("type_definitions", [])}

    original_names = set(original_types.keys())
    composed_names = set(composed_types.keys())

    missing_types = list(original_names - composed_names)
    extra_types = list(composed_names - original_names)

    # Check relation differences for common types
    relation_diffs: dict[str, dict[str, Any]] = {}
    common_types = original_names & composed_names

    for type_name in common_types:
        orig_rels = set(original_types[type_name].get("relations", {}).keys())
        comp_rels = set(composed_types[type_name].get("relations", {}).keys())

        missing_rels = list(orig_rels - comp_rels)
        extra_rels = list(comp_rels - orig_rels)

        if missing_rels or extra_rels:
            relation_diffs[type_name] = {
                "missing": missing_rels,
                "extra": extra_rels,
            }

    types_match = len(missing_types) == 0 and len(extra_types) == 0 and len(relation_diffs) == 0

    return {
        "types_match": types_match,
        "missing_types": missing_types,
        "extra_types": extra_types,
        "relation_diffs": relation_diffs,
    }


def generate_diff_report(diff: dict[str, Any]) -> str:
    """
    Generate human-readable diff report from validate_roundtrip_diff result.

    Args:
        diff: Diff dict from validate_roundtrip_diff

    Returns:
        Formatted string report
    """
    lines = []

    if diff.get("types_match"):
        lines.append("✓ All types and relations match")
        return "\n".join(lines)

    lines.append("Round-Trip Diff Report")
    lines.append("=" * 40)

    if diff.get("missing_types"):
        lines.append("\nMissing Types (in original, not in composed):")
        for t in diff["missing_types"]:
            lines.append(f"  - {t}")

    if diff.get("extra_types"):
        lines.append("\nExtra Types (in composed, not in original):")
        for t in diff["extra_types"]:
            lines.append(f"  + {t}")

    if diff.get("relation_diffs"):
        lines.append("\nRelation Differences:")
        for type_name, rel_diff in diff["relation_diffs"].items():
            lines.append(f"\n  Type: {type_name}")
            for rel in rel_diff.get("missing", []):
                lines.append(f"    - {rel} (missing)")
            for rel in rel_diff.get("extra", []):
                lines.append(f"    + {rel} (extra)")

    return "\n".join(lines)


# =============================================================================
# JSON Schema Validation
# =============================================================================


def get_openfga_schema() -> dict[str, Any]:
    """
    Get OpenFGA authorization model JSON schema.

    Returns a simplified schema for validating model structure.
    Based on OpenFGA v1.1 authorization model specification.

    Returns:
        JSON Schema dict
    """
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "OpenFGA Authorization Model",
        "type": "object",
        "required": ["schema_version", "type_definitions"],
        "properties": {
            "schema_version": {
                "type": "string",
                "enum": ["1.1", "1.2"],
                "description": "Model schema version",
            },
            "type_definitions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type"],
                    "properties": {
                        "type": {"type": "string", "minLength": 1},
                        "relations": {
                            "type": "object",
                            "additionalProperties": {"$ref": "#/$defs/relation"},
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "relations": {
                                    "type": "object",
                                    "additionalProperties": {
                                        "type": "object",
                                        "properties": {
                                            "directly_related_user_types": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "required": ["type"],
                                                    "properties": {
                                                        "type": {"type": "string"},
                                                        "relation": {"type": "string"},
                                                        "wildcard": {"type": "object"},
                                                    },
                                                },
                                            }
                                        },
                                    },
                                }
                            },
                        },
                    },
                },
            },
            "conditions": {
                "type": "object",
                "additionalProperties": {
                    "type": "object",
                    "required": ["name", "expression"],
                    "properties": {
                        "name": {"type": "string"},
                        "expression": {"type": "string"},
                        "parameters": {"type": "object"},
                    },
                },
            },
        },
        "$defs": {
            "relation": {
                "type": "object",
                "oneOf": [
                    {"required": ["this"]},
                    {"required": ["computedUserset"]},
                    {"required": ["tupleToUserset"]},
                    {"required": ["union"]},
                    {"required": ["intersection"]},
                    {"required": ["difference"]},
                ],
                "properties": {
                    "this": {"type": "object"},
                    "computedUserset": {
                        "type": "object",
                        "required": ["relation"],
                        "properties": {"relation": {"type": "string"}},
                    },
                    "tupleToUserset": {
                        "type": "object",
                        "required": ["tupleset", "computedUserset"],
                        "properties": {
                            "tupleset": {
                                "type": "object",
                                "required": ["relation"],
                            },
                            "computedUserset": {
                                "type": "object",
                                "required": ["relation"],
                            },
                        },
                    },
                    "union": {
                        "type": "object",
                        "required": ["child"],
                        "properties": {"child": {"type": "array", "items": {"$ref": "#/$defs/relation"}}},
                    },
                    "intersection": {
                        "type": "object",
                        "required": ["child"],
                        "properties": {"child": {"type": "array", "items": {"$ref": "#/$defs/relation"}}},
                    },
                    "difference": {
                        "type": "object",
                        "required": ["base", "subtract"],
                    },
                },
            }
        },
    }


def _relation_is_directly_assignable(rel_def: dict[str, Any]) -> bool:
    """
    Check if a relation definition allows direct tuple assignment.

    A relation is directly assignable if it has "this: {}" at any level,
    either directly or within a union/intersection/difference.

    This is important because OpenFGA rejects models where a computed-only
    relation (no 'this') has 'directly_related_user_types' in metadata.

    Args:
        rel_def: The relation definition to check

    Returns:
        True if the relation can be directly assigned (has 'this: {}')
    """
    # Direct "this" at top level
    if "this" in rel_def:
        return True

    # Check union children
    union = rel_def.get("union", {})
    if union:
        children = union.get("child", [])
        for child in children:
            if isinstance(child, dict) and "this" in child:
                return True

    # Check intersection children
    intersection = rel_def.get("intersection", {})
    if intersection:
        children = intersection.get("child", [])
        for child in children:
            if isinstance(child, dict) and "this" in child:
                return True

    # Check difference base
    difference = rel_def.get("difference", {})
    if difference:
        base = difference.get("base", {})
        if isinstance(base, dict) and "this" in base:
            return True

    return False


def validate_model_schema(model: dict[str, Any]) -> dict[str, Any]:
    """
    Validate model against OpenFGA JSON schema.

    Performs structural validation to ensure:
    - Required fields present
    - Valid relation structures
    - Valid metadata structures

    Args:
        model: Model dict to validate

    Returns:
        Validation result dict with:
        - valid: bool - True if model passes validation
        - errors: list - List of validation error messages
    """
    errors: list[str] = []

    # Check required fields
    if "schema_version" not in model:
        errors.append("Missing required field: schema_version")

    if "type_definitions" not in model:
        errors.append("Missing required field: type_definitions")
    elif not isinstance(model["type_definitions"], list):
        errors.append("type_definitions must be an array")
    else:
        # Validate each type definition
        for i, type_def in enumerate(model["type_definitions"]):
            if not isinstance(type_def, dict):
                errors.append(f"type_definitions[{i}] must be an object")
                continue

            if "type" not in type_def:
                errors.append(f"type_definitions[{i}] missing required field: type")

            # Validate relations
            relations = type_def.get("relations", {})
            if not isinstance(relations, dict):
                errors.append(f"type_definitions[{i}].relations must be an object")
            else:
                for rel_name, rel_def in relations.items():
                    if not isinstance(rel_def, dict):
                        errors.append(f"type_definitions[{i}].relations.{rel_name} must be an object")
                        continue

                    # Check for valid relation structure
                    valid_keys = {
                        "this",
                        "computedUserset",
                        "tupleToUserset",
                        "union",
                        "intersection",
                        "difference",
                    }
                    rel_keys = set(rel_def.keys())
                    if not rel_keys & valid_keys:
                        errors.append(
                            f"type_definitions[{i}].relations.{rel_name} has invalid structure. "
                            f"Expected one of: {valid_keys}. Got: {rel_keys}"
                        )

                    # Check if relation is directly assignable
                    # A relation is directly assignable if it has "this: {}" at any level
                    is_directly_assignable = _relation_is_directly_assignable(rel_def)

                    # Validate metadata consistency with relation definition
                    type_name = type_def.get("type", f"type_{i}")
                    metadata = type_def.get("metadata", {})
                    rel_metadata = metadata.get("relations", {}).get(rel_name, {})

                    if rel_metadata.get("directly_related_user_types"):
                        if not is_directly_assignable:
                            errors.append(
                                f"{type_name}.{rel_name}: non-assignable relation "
                                f"(no 'this' definition) should not have "
                                f"'directly_related_user_types' in metadata. "
                                f"Either add 'this: {{}}' to make it assignable, "
                                f"or remove 'directly_related_user_types' from metadata."
                            )

    # Validate conditions if present
    conditions = model.get("conditions")
    if conditions is not None:
        if not isinstance(conditions, dict):
            errors.append("conditions must be an object")
        else:
            for cond_name, cond_def in conditions.items():
                if not isinstance(cond_def, dict):
                    errors.append(f"conditions.{cond_name} must be an object")
                elif "name" not in cond_def or "expression" not in cond_def:
                    errors.append(f"conditions.{cond_name} missing required fields: name, expression")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


# =============================================================================
# Condition Parameter Validation
# =============================================================================

# Valid OpenFGA condition parameter types
VALID_CONDITION_TYPE_NAMES = {
    "TYPE_NAME_ANY",
    "TYPE_NAME_BOOL",
    "TYPE_NAME_STRING",
    "TYPE_NAME_INT",
    "TYPE_NAME_UINT",
    "TYPE_NAME_DOUBLE",
    "TYPE_NAME_DURATION",
    "TYPE_NAME_TIMESTAMP",
    "TYPE_NAME_LIST",
    "TYPE_NAME_MAP",
    "TYPE_NAME_IPADDRESS",
}


def validate_condition_params(condition: dict[str, Any]) -> dict[str, Any]:
    """
    Validate a single condition definition.

    Checks:
    - Required fields (name, expression) are present
    - Parameter types are valid OpenFGA types

    Args:
        condition: Condition definition dict

    Returns:
        Validation result with 'valid' bool and 'errors' list
    """
    errors: list[str] = []

    # Check required fields
    if "name" not in condition:
        errors.append("Missing required field: name")

    if "expression" not in condition:
        errors.append("Missing required field: expression")

    # Validate parameters if present
    parameters = condition.get("parameters", {})
    if parameters:
        for param_name, param_def in parameters.items():
            if not isinstance(param_def, dict):
                errors.append(f"Parameter '{param_name}' must be an object")
                continue

            type_name = param_def.get("type_name")
            if type_name and type_name not in VALID_CONDITION_TYPE_NAMES:
                errors.append(
                    f"Parameter '{param_name}' has invalid type_name: {type_name}. "
                    f"Valid types: {sorted(VALID_CONDITION_TYPE_NAMES)}"
                )

            # Validate generic_types for LIST/MAP types
            if type_name in ("TYPE_NAME_LIST", "TYPE_NAME_MAP"):
                generic_types = param_def.get("generic_types", [])
                for i, gt in enumerate(generic_types):
                    if isinstance(gt, dict):
                        gt_type = gt.get("type_name")
                        if gt_type and gt_type not in VALID_CONDITION_TYPE_NAMES:
                            errors.append(f"Parameter '{param_name}' generic_types[{i}] has invalid type: {gt_type}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def validate_model_conditions(model: dict[str, Any]) -> dict[str, Any]:
    """
    Validate all conditions in a model.

    Args:
        model: Complete model dict with conditions

    Returns:
        Validation result with 'valid' bool and 'errors' list
    """
    errors: list[str] = []

    conditions = model.get("conditions", {})
    if not conditions:
        # No conditions to validate
        return {"valid": True, "errors": []}

    for cond_name, cond_def in conditions.items():
        result = validate_condition_params(cond_def)
        if not result["valid"]:
            for error in result["errors"]:
                errors.append(f"conditions.{cond_name}: {error}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


# =============================================================================
# Module Sync Validation
# =============================================================================


def check_sync_status(model_path: Path, modules_dir: Path) -> dict[str, Any]:
    """
    Check synchronization status between model.json and modules.

    Compares types in model.json with types defined in .fga modules.

    Args:
        model_path: Path to model.json
        modules_dir: Path to modules directory

    Returns:
        Sync status dict with:
        - in_sync: bool - True if model and modules match
        - missing_types: list - Types in model but not in modules
        - extra_types: list - Types in modules but not in model
        - relation_diffs: dict - Per-type relation differences
    """
    # Load model types
    with open(model_path) as f:
        model = json.load(f)

    model_types = {t["type"] for t in model.get("type_definitions", [])}

    # Load module types
    module_types: set[str] = set()

    if modules_dir.exists():
        for fga_file in modules_dir.glob("*.fga"):
            with open(fga_file) as f:
                content = f.read()

            types = parse_fga_module(content)
            for t in types:
                if t.get("type"):
                    module_types.add(t["type"])

    # Calculate differences
    missing_types = list(model_types - module_types)
    extra_types = list(module_types - model_types)

    # For now, relation diffs are empty (could be extended)
    relation_diffs: dict[str, Any] = {}

    in_sync = len(missing_types) == 0 and len(extra_types) == 0

    return {
        "in_sync": in_sync,
        "missing_types": missing_types,
        "extra_types": extra_types,
        "relation_diffs": relation_diffs,
    }


def generate_sync_report(status: dict[str, Any]) -> str:
    """
    Generate human-readable sync status report.

    Args:
        status: Sync status dict from check_sync_status

    Returns:
        Formatted string report
    """
    lines = []

    if status.get("in_sync"):
        lines.append("✓ Modules are in sync with model.json")
        return "\n".join(lines)

    lines.append("Module Sync Status Report")
    lines.append("=" * 40)

    if status.get("missing_types"):
        lines.append("\nMissing in modules (in model.json only):")
        for t in status["missing_types"]:
            lines.append(f"  - {t}")

    if status.get("extra_types"):
        lines.append("\nExtra in modules (not in model.json):")
        for t in status["extra_types"]:
            lines.append(f"  + {t}")

    if status.get("relation_diffs"):
        lines.append("\nRelation Differences:")
        for type_name, rel_diff in status["relation_diffs"].items():
            lines.append(f"\n  Type: {type_name}")
            for rel in rel_diff.get("missing", []):
                lines.append(f"    - {rel} (missing)")
            for rel in rel_diff.get("extra", []):
                lines.append(f"    + {rel} (extra)")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    base_dir = Path(__file__).parent
    model_path = base_dir / "model.json"
    modules_dir = base_dir / "modules"

    if len(sys.argv) > 1 and sys.argv[1] == "extract":
        print("Extracting modules from model.json...")
        extract_modules(model_path, modules_dir)
        print("\nRun 'python compose_model.py validate' to verify coverage.")
    elif len(sys.argv) > 1 and sys.argv[1] == "compose":
        print("Composing modules into model.json...")
        if not modules_dir.exists():
            print(f"Error: Modules directory not found: {modules_dir}")
            sys.exit(1)
        composed = compose_modules(modules_dir)
        # Write to model.json (backup first)
        backup_path = model_path.with_suffix(".json.bak")
        if model_path.exists():
            import shutil

            shutil.copy(model_path, backup_path)
            print(f"Backup created: {backup_path}")
        with open(model_path, "w") as f:
            json.dump(composed, f, indent=2)
        print(f"Composed {len(composed['type_definitions'])} types into {model_path}")
    elif len(sys.argv) > 1 and sys.argv[1] == "validate":
        print("Validating module coverage...")
        validate_coverage(model_path)
    else:
        print("Usage:")
        print("  python compose_model.py extract   - Extract modules from model.json")
        print("  python compose_model.py compose   - Compose modules into model.json")
        print("  python compose_model.py validate  - Validate module coverage")
        print("")
        print("Bidirectional Workflow:")
        print("  Extract (model.json → modules):")
        print("    1. Edit model.json (source of truth)")
        print("    2. Run 'python compose_model.py extract' to regenerate modules")
        print("    3. Run 'python compose_model.py validate' to verify coverage")
        print("")
        print("  Compose (modules → model.json):")
        print("    1. Edit .fga module files in modules/ directory")
        print("    2. Run 'python compose_model.py compose' to regenerate model.json")
        print("    3. Run 'python compose_model.py validate' to verify coverage")
