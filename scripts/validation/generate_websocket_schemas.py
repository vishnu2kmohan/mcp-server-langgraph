#!/usr/bin/env python3
"""
Generate JSON Schema files from WebSocket protocol Pydantic models.

This script generates JSON Schema files that can be used for:
    - API documentation
    - Contract testing
    - Client code generation
    - Frontend/Backend validation synchronization

Usage:
    uv run python scripts/validation/generate_websocket_schemas.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mcp_server_langgraph.websocket.protocols import (
    # DevTools
    ConsoleLogEntry,
    NetworkRequestEntry,
    NetworkUpdateEntry,
    # Traces
    TraceSpanEntry,
    TraceEventEntry,
    TraceSubscribeMessage,
    # Budget Alerts
    BudgetAlertEntry,
    BudgetSubscribedResponse,
    BudgetSubscribeEntitiesMessage,
    BudgetSubscribeAllMessage,
    # AI Suggestions
    SuggestionResponseEntry,
    SuggestionRequestMessage,
    SuggestionAcceptMessage,
    SuggestionRejectMessage,
    ContextUpdateMessage,
    # MCP Aggregated
    MCPServerStatusEntry,
    MCPToolCallEntry,
    # Error
    WebSocketError,
    # Version
    PROTOCOL_VERSION,
)


def generate_schemas(output_dir: Path) -> None:
    """Generate JSON Schema files for all protocol models."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define all models to generate schemas for
    models = {
        # DevTools Protocol
        "devtools/console-log-entry.json": ConsoleLogEntry,
        "devtools/network-request-entry.json": NetworkRequestEntry,
        "devtools/network-update-entry.json": NetworkUpdateEntry,
        # Traces Protocol
        "traces/trace-span-entry.json": TraceSpanEntry,
        "traces/trace-event-entry.json": TraceEventEntry,
        "traces/trace-subscribe-message.json": TraceSubscribeMessage,
        # Budget Alerts Protocol
        "budget-alerts/budget-alert-entry.json": BudgetAlertEntry,
        "budget-alerts/budget-subscribed-response.json": BudgetSubscribedResponse,
        "budget-alerts/budget-subscribe-entities-message.json": BudgetSubscribeEntitiesMessage,
        "budget-alerts/budget-subscribe-all-message.json": BudgetSubscribeAllMessage,
        # AI Suggestions Protocol
        "ai-suggestions/suggestion-response-entry.json": SuggestionResponseEntry,
        "ai-suggestions/suggestion-request-message.json": SuggestionRequestMessage,
        "ai-suggestions/suggestion-accept-message.json": SuggestionAcceptMessage,
        "ai-suggestions/suggestion-reject-message.json": SuggestionRejectMessage,
        "ai-suggestions/context-update-message.json": ContextUpdateMessage,
        # MCP Aggregated Protocol
        "mcp-aggregated/mcp-server-status-entry.json": MCPServerStatusEntry,
        "mcp-aggregated/mcp-tool-call-entry.json": MCPToolCallEntry,
        # Error
        "common/websocket-error.json": WebSocketError,
    }

    generated_count = 0
    for filename, model in models.items():
        schema_path = output_dir / filename
        schema_path.parent.mkdir(parents=True, exist_ok=True)

        # Generate JSON Schema
        schema = model.model_json_schema()

        # Add metadata
        schema["$schema"] = "http://json-schema.org/draft-07/schema#"
        schema["$id"] = f"https://mcp-server-langgraph/schemas/websocket/{filename}"
        schema["title"] = model.__name__
        if model.__doc__:
            schema["description"] = model.__doc__.strip()

        # Write to file
        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2)

        generated_count += 1
        print(f"  Generated: {filename}")

    # Generate protocol version file
    version_path = output_dir / "protocol-version.json"
    with open(version_path, "w") as f:
        json.dump(
            {
                "version": PROTOCOL_VERSION,
                "schemas": list(models.keys()),
            },
            f,
            indent=2,
        )
    print("  Generated: protocol-version.json")

    print(f"\nGenerated {generated_count + 1} schema files in {output_dir}")


def main() -> None:
    """Main entry point."""
    # Default output directory
    project_root = Path(__file__).parent.parent.parent
    output_dir = project_root / "docs" / "schemas" / "websocket"

    print("Generating WebSocket JSON Schemas...")
    print(f"Protocol Version: {PROTOCOL_VERSION}")
    print(f"Output directory: {output_dir}\n")

    generate_schemas(output_dir)

    print("\nDone! Schemas can be used for:")
    print("  - API documentation (OpenAPI/Swagger)")
    print("  - Contract testing")
    print("  - Frontend/Backend validation")
    print("  - Client code generation")


if __name__ == "__main__":
    main()
