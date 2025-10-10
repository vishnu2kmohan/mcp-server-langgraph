#!/usr/bin/env python3
"""Generate OpenAPI schema from FastAPI application."""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server_streamable import app


def generate_openapi_schema():
    """Generate and save OpenAPI schema."""
    schema = app.openapi()

    # Save to file
    output_path = Path(__file__).parent.parent / "openapi.json"

    with open(output_path, "w") as f:
        json.dump(schema, f, indent=2)

    print(f"✓ OpenAPI schema generated: {output_path}")
    print(f"  Endpoints: {len(schema.get('paths', {}))}")
    print(f"  Schemas: {len(schema.get('components', {}).get('schemas', {}))}")


if __name__ == "__main__":
    generate_openapi_schema()
