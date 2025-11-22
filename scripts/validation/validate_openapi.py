#!/usr/bin/env python3
"""
OpenAPI Schema Validation Script

Generates OpenAPI schema from FastAPI app and validates compliance.
"""

import importlib
import json
import sys
from pathlib import Path

try:
    from fastapi.openapi.utils import get_openapi
    from openapi_spec_validator import validate_spec
except ImportError:
    print("Error: Required packages not installed")
    print("Run: uv pip install openapi-spec-validator")
    sys.exit(1)


def generate_openapi_schema(app_module: str = "mcp_server_langgraph.mcp.server_streamable") -> dict:
    """
    Generate OpenAPI schema from FastAPI application

    Args:
        app_module: Name of the module containing the FastAPI app

    Returns:
        OpenAPI schema as dictionary
    """
    try:
        # Import the FastAPI app
        module = importlib.import_module(app_module)
        app = module.app

        # Generate OpenAPI schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )

        return schema

    except Exception as e:
        print(f"Error generating schema from {app_module}: {e}")
        raise


def save_schema(schema: dict, output_path: Path) -> None:
    """Save OpenAPI schema to file"""
    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)
    print(f"✓ Schema saved to {output_path}")


def validate_openapi_schema(schema: dict) -> bool:
    """
    Validate OpenAPI schema against OpenAPI 3.0 specification

    Args:
        schema: OpenAPI schema dictionary

    Returns:
        True if valid, False otherwise
    """
    try:
        validate_spec(schema)
        print("✓ OpenAPI schema is valid")
        return True
    except Exception as e:
        print(f"✗ OpenAPI schema validation failed: {e}")
        return False


def check_endpoint_coverage(schema: dict) -> dict:
    """
    Check that all endpoints are documented

    Returns:
        Dictionary with coverage statistics
    """
    paths = schema.get("paths", {})
    stats = {
        "total_paths": len(paths),
        "total_operations": 0,
        "documented_operations": 0,
        "undocumented": [],
    }

    for path, methods in paths.items():
        for method, operation in methods.items():
            if method in ["get", "post", "put", "delete", "patch", "options", "head"]:
                stats["total_operations"] += 1

                if operation.get("description") or operation.get("summary"):
                    stats["documented_operations"] += 1
                else:
                    stats["undocumented"].append(f"{method.upper()} {path}")

    stats["coverage_percent"] = (
        (stats["documented_operations"] / stats["total_operations"] * 100) if stats["total_operations"] > 0 else 0
    )

    return stats


def check_schema_definitions(schema: dict) -> dict:
    """
    Check that all request/response models are defined

    Returns:
        Dictionary with schema statistics
    """
    components = schema.get("components", {})
    schemas = components.get("schemas", {})

    stats = {
        "total_schemas": len(schemas),
        "schemas_with_examples": 0,
        "schemas_with_descriptions": 0,
    }

    for schema_name, schema_def in schemas.items():
        if "example" in schema_def or "examples" in schema_def:
            stats["schemas_with_examples"] += 1

        if "description" in schema_def:
            stats["schemas_with_descriptions"] += 1

    return stats


def check_breaking_changes(old_schema_path: Path, new_schema: dict) -> list:
    """
    Compare schemas and detect breaking changes

    Args:
        old_schema_path: Path to previous schema
        new_schema: New schema dictionary

    Returns:
        List of breaking changes detected
    """
    if not old_schema_path.exists():
        print(f"ℹ No baseline schema found at {old_schema_path}")
        return []

    with open(old_schema_path) as f:
        old_schema = json.load(f)

    breaking_changes = []

    # Check for removed paths
    old_paths = set(old_schema.get("paths", {}).keys())
    new_paths = set(new_schema.get("paths", {}).keys())
    removed_paths = old_paths - new_paths

    for path in removed_paths:
        breaking_changes.append(f"BREAKING: Removed endpoint {path}")

    # Check for removed methods
    for path in old_paths & new_paths:
        old_methods = set(old_schema["paths"][path].keys())
        new_methods = set(new_schema["paths"][path].keys())
        removed_methods = old_methods - new_methods

        for method in removed_methods:
            breaking_changes.append(f"BREAKING: Removed method {method.upper()} {path}")

    # Check for removed required fields
    old_schemas = old_schema.get("components", {}).get("schemas", {})
    new_schemas = new_schema.get("components", {}).get("schemas", {})

    for schema_name in old_schemas.keys() & new_schemas.keys():
        old_required = set(old_schemas[schema_name].get("required", []))
        new_required = set(new_schemas[schema_name].get("required", []))
        new_required_fields = new_required - old_required

        for field in new_required_fields:
            breaking_changes.append(f"BREAKING: New required field '{field}' in {schema_name}")

    return breaking_changes


def main():
    """Main validation script"""
    print("=" * 70)
    print("OpenAPI Schema Validation")
    print("=" * 70)

    # Paths
    project_root = Path(__file__).parent.parent
    schema_path = project_root / "openapi.json"
    baseline_schema_path = project_root / "openapi.baseline.json"

    # Generate schema
    print("\n1. Generating OpenAPI schema...")
    try:
        schema = generate_openapi_schema("mcp_server_langgraph.mcp.server_streamable")
    except Exception as e:
        print(f"Failed to generate schema: {e}")
        return 1

    # Validate schema
    print("\n2. Validating OpenAPI schema...")
    if not validate_openapi_schema(schema):
        return 1

    # Check endpoint coverage
    print("\n3. Checking endpoint documentation coverage...")
    coverage_stats = check_endpoint_coverage(schema)
    print(f"   Total paths: {coverage_stats['total_paths']}")
    print(f"   Total operations: {coverage_stats['total_operations']}")
    print(f"   Documented operations: {coverage_stats['documented_operations']}")
    print(f"   Coverage: {coverage_stats['coverage_percent']:.1f}%")

    if coverage_stats["undocumented"]:
        print("\n   Undocumented endpoints:")
        for endpoint in coverage_stats["undocumented"]:
            print(f"     - {endpoint}")

    # Check schema definitions
    print("\n4. Checking schema definitions...")
    schema_stats = check_schema_definitions(schema)
    print(f"   Total schemas: {schema_stats['total_schemas']}")
    print(f"   Schemas with descriptions: {schema_stats['schemas_with_descriptions']}")
    print(f"   Schemas with examples: {schema_stats['schemas_with_examples']}")

    # Check for breaking changes
    print("\n5. Checking for breaking changes...")
    breaking_changes = check_breaking_changes(baseline_schema_path, schema)

    if breaking_changes:
        print(f"   ⚠ Found {len(breaking_changes)} breaking changes:")
        for change in breaking_changes:
            print(f"     - {change}")
    else:
        print("   ✓ No breaking changes detected")

    # Save current schema
    print("\n6. Saving schema...")
    save_schema(schema, schema_path)

    # Summary
    print("\n" + "=" * 70)
    print("Summary:")
    print("  Schema valid: ✓")
    print(f"  Coverage: {coverage_stats['coverage_percent']:.1f}%")
    print(f"  Breaking changes: {len(breaking_changes)}")

    if coverage_stats["coverage_percent"] < 100:
        print("\n⚠ Warning: Not all endpoints are documented")

    if breaking_changes:
        print("\n⚠ Warning: Breaking changes detected!")
        print("  Review changes before releasing")

    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
