#!/usr/bin/env python3
"""
Export OpenAPI Schema

Generates the OpenAPI specification from the FastAPI application
and saves it to api/openapi.json for frontend type generation.

Usage:
    uv run python scripts/export_openapi.py

The generated spec can be used by the frontend:
    cd src/mcp_server_langgraph/studio/frontend
    npm run generate-types
"""

import json
import os
import sys
from pathlib import Path

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Set minimal environment for app creation
# MUST be set BEFORE importing app module since app is created at module level
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ.setdefault("JWT_SECRET_KEY", "openapi-export-dummy-key-not-for-production")
os.environ.setdefault("AUTH_PROVIDER", "inmemory")
os.environ.setdefault("TESTING", "true")  # Skip startup validation


def export_openapi() -> None:
    """Export the OpenAPI schema from the FastAPI application."""
    # Import the app instance (created at module level with TESTING=true skip validation)
    from mcp_server_langgraph.app import app

    # Get the OpenAPI schema
    openapi_schema = app.openapi()

    # Output path
    output_path = Path(__file__).parent.parent / "api" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write the schema
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI schema exported to: {output_path}")
    print(f"Schema contains {len(openapi_schema.get('paths', {}))} paths")
    print(f"Schema contains {len(openapi_schema.get('components', {}).get('schemas', {}))} schemas")


if __name__ == "__main__":
    export_openapi()
