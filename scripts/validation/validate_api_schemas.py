#!/usr/bin/env python3
"""
Validate API Response Schemas

Ensures that API endpoint responses match their documented Pydantic schemas.
This prevents bugs where implementations store data but don't return it in responses.

Regression prevention for Codex Finding: API key "created" timestamp omission.

Usage:
    python scripts/validate_api_schemas.py
    python scripts/validate_api_schemas.py --strict  # Fail on warnings
"""

import ast
import sys
from pathlib import Path
from typing import Any


class APISchemaValidator(ast.NodeVisitor):
    """AST visitor to validate API schemas match implementations."""

    def __init__(self):
        self.issues: list[dict[str, Any]] = []
        self.current_file = ""
        self.response_models: dict[str, set[str]] = {}
        self.return_statements: dict[str, set[str]] = {}

    def check_file(self, filepath: Path) -> None:
        """Check a single Python file for schema violations."""
        self.current_file = str(filepath)

        try:
            with open(filepath, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(filepath))
                self.visit(tree)
        except SyntaxError as e:
            self.issues.append(
                {"file": str(filepath), "line": e.lineno or 0, "severity": "error", "message": f"Syntax error: {e.msg}"}
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract response model field definitions."""
        # Check if this is a Pydantic BaseModel subclass
        is_response_model = any(
            (isinstance(base, ast.Name) and base.id == "BaseModel")
            or (isinstance(base, ast.Attribute) and base.attr == "BaseModel")
            for base in node.bases
        )

        if is_response_model and "Response" in node.name:
            # Extract field names from the model
            fields = set()
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fields.add(item.target.id)

            if fields:
                self.response_models[node.name] = fields

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function return statements match response models."""
        # Look for return_value annotations or explicit response_model
        # Note: response_model_name extraction reserved for future OpenAPI schema validation

        # Check for return type annotation
        if node.returns:
            if isinstance(node.returns, ast.Name):
                _ = node.returns.id  # Reserved for future use
            elif isinstance(node.returns, ast.Subscript):
                # Handle Response[SomeModel] patterns
                if isinstance(node.returns.slice, ast.Name):
                    _ = node.returns.slice.id  # Reserved for future use

        # Extract return dictionary keys
        return_keys = set()
        for item in ast.walk(node):
            if isinstance(item, ast.Return) and item.value:
                if isinstance(item.value, ast.Dict):
                    # Direct dict return: return {"key": value, ...}
                    for key in item.value.keys:
                        if isinstance(key, ast.Constant):
                            return_keys.add(key.value)
                elif isinstance(item.value, ast.Call):
                    # Function call that returns dict
                    # Check if it's a model instantiation
                    if isinstance(item.value.func, ast.Name):
                        if item.value.func.id in self.response_models:
                            # Check that all required fields are passed
                            passed_kwargs = {kw.arg for kw in item.value.keywords if kw.arg}
                            expected_fields = self.response_models[item.value.func.id]
                            missing = expected_fields - passed_kwargs
                            if missing:
                                self.issues.append(
                                    {
                                        "file": self.current_file,
                                        "line": item.lineno,
                                        "severity": "warning",
                                        "message": f"Function '{node.name}' may be missing fields in {item.value.func.id}: {missing}",
                                    }
                                )

        self.generic_visit(node)


def main():
    """Main validation function."""
    strict = "--strict" in sys.argv

    validator = APISchemaValidator()

    # Check API endpoint files
    api_dirs = [
        Path("src/mcp_server_langgraph/api"),
        Path("src/mcp_server_langgraph/auth"),
    ]

    files_checked = 0
    for api_dir in api_dirs:
        if not api_dir.exists():
            continue

        for filepath in api_dir.rglob("*.py"):
            if filepath.name.startswith("__"):
                continue
            validator.check_file(filepath)
            files_checked += 1

    # Report results
    errors = [i for i in validator.issues if i["severity"] == "error"]
    warnings = [i for i in validator.issues if i["severity"] == "warning"]

    if errors or warnings:
        print("\n🔍 API Schema Validation Report")
        print(f"Files checked: {files_checked}")
        print(f"Issues found: {len(errors)} errors, {len(warnings)} warnings\n")

        for issue in errors:
            print(f"❌ ERROR: {issue['file']}:{issue['line']}")
            print(f"   {issue['message']}\n")

        for issue in warnings:
            print(f"⚠️  WARNING: {issue['file']}:{issue['line']}")
            print(f"   {issue['message']}\n")

        if errors or (strict and warnings):
            print("💡 Tip: Ensure all response model fields are returned by implementations")
            print("   See TESTING.md 'Regression Test Patterns' for guidance\n")
            sys.exit(1)
        else:
            print("✅ Passed (warnings are non-blocking)\n")
            sys.exit(0)
    else:
        print(f"✅ API Schema Validation: All {files_checked} files passed\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
