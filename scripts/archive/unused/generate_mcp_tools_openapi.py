"""
Generate OpenAPI specification for MCP tool wrappers

Creates a separate OpenAPI spec documenting MCP tools for SDK/CLI generation.
MCP tools are exposed via the /message endpoint but can be documented separately
for client library generation.
"""

import json
from pathlib import Path

# MCP Tools OpenAPI Specification
mcp_tools_spec = {
    "openapi": "3.1.0",
    "info": {
        "title": "MCP Server - Tool Wrappers API",
        "version": "2.8.0",
        "description": """
## MCP (Model Context Protocol) Tools API

This API provides HTTP wrappers around MCP protocol tools for client libraries and SDKs.

### Available Tools

1. **agent_chat** - Chat with AI agent (supports streaming)
2. **conversation_get** - Retrieve specific conversation
3. **conversation_search** - Search conversations with filters

### Authentication

All tools require JWT authentication via the `token` parameter or `Authorization` header.

### Response Formats

- **Concise**: ~500 tokens (faster, less context)
- **Detailed**: ~2000 tokens (comprehensive, more context)

### Usage

**Via MCP Protocol** (recommended):
```json
POST /message
{
  "method": "tools/call",
  "params": {
    "name": "agent_chat",
    "arguments": {
      "message": "Hello",
      "user_id": "alice",
      "token": "jwt_token"
    }
  }
}
```

**Via Tool Endpoints** (convenience):
```
POST /tools/agent_chat
{
  "message": "Hello",
  "user_id": "alice",
  "token": "jwt_token"
}
```
        """,
        "contact": {"name": "API Support"},
        "license": {"name": "MIT"},
    },
    "servers": [{"url": "http://localhost:8000", "description": "Local development"}],
    "paths": {
        "/tools/agent_chat": {
            "post": {
                "summary": "Chat with AI agent",
                "description": "Send a message to the AI agent and receive a response",
                "operationId": "agent_chat",
                "tags": ["MCP Tools"],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AgentChatRequest"}}},
                },
                "responses": {
                    "200": {
                        "description": "Agent response",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/AgentChatResponse"}}},
                    },
                    "401": {"description": "Unauthorized - Invalid token"},
                    "403": {"description": "Forbidden - Insufficient permissions"},
                    "429": {"description": "Too Many Requests - Rate limit exceeded"},
                },
            }
        },
        "/tools/conversation_get": {
            "post": {
                "summary": "Get specific conversation",
                "description": "Retrieve a conversation by thread_id",
                "operationId": "conversation_get",
                "tags": ["MCP Tools"],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ConversationGetRequest"}}},
                },
                "responses": {
                    "200": {
                        "description": "Conversation details",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ConversationResponse"}}},
                    },
                    "401": {"description": "Unauthorized"},
                    "404": {"description": "Conversation not found"},
                },
            }
        },
        "/tools/conversation_search": {
            "post": {
                "summary": "Search conversations",
                "description": "Search user conversations with filters",
                "operationId": "conversation_search",
                "tags": ["MCP Tools"],
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ConversationSearchRequest"}}},
                },
                "responses": {
                    "200": {
                        "description": "Search results",
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/ConversationSearchResponse"}}
                        },
                    },
                    "401": {"description": "Unauthorized"},
                },
            }
        },
    },
    "components": {
        "schemas": {
            "AgentChatRequest": {
                "type": "object",
                "required": ["message", "user_id", "token"],
                "properties": {
                    "message": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 10000,
                        "description": "The user message to send to the agent",
                        "example": "What is the weather today?",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "User identifier for authentication and authorization",
                        "example": "alice",
                    },
                    "token": {
                        "type": "string",
                        "description": "JWT authentication token",
                        "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    },
                    "thread_id": {
                        "type": "string",
                        "description": "Optional thread ID for conversation continuity",
                        "example": "conv_123",
                    },
                    "response_format": {
                        "type": "string",
                        "enum": ["concise", "detailed"],
                        "default": "concise",
                        "description": "Response verbosity level",
                    },
                },
            },
            "AgentChatResponse": {
                "type": "object",
                "properties": {
                    "response": {"type": "string", "description": "Agent response text"},
                    "thread_id": {"type": "string", "description": "Thread ID for conversation continuity"},
                    "tokens_used": {"type": "integer", "description": "Approximate tokens used"},
                },
            },
            "ConversationGetRequest": {
                "type": "object",
                "required": ["thread_id", "user_id", "token"],
                "properties": {
                    "thread_id": {
                        "type": "string",
                        "description": "Thread ID of conversation to retrieve",
                        "example": "conv_123",
                    },
                    "user_id": {"type": "string", "description": "User identifier", "example": "alice"},
                    "token": {"type": "string", "description": "JWT authentication token"},
                },
            },
            "ConversationSearchRequest": {
                "type": "object",
                "required": ["query", "user_id", "token"],
                "properties": {
                    "query": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 500,
                        "description": "Search query to filter conversations",
                        "example": "weather",
                    },
                    "user_id": {"type": "string", "description": "User identifier", "example": "alice"},
                    "token": {"type": "string", "description": "JWT authentication token"},
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 50,
                        "default": 10,
                        "description": "Maximum number of conversations to return",
                    },
                },
            },
            "ConversationResponse": {
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string"},
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["user", "assistant"]},
                                "content": {"type": "string"},
                                "timestamp": {"type": "string", "format": "date-time"},
                            },
                        },
                    },
                    "created_at": {"type": "string", "format": "date-time"},
                },
            },
            "ConversationSearchResponse": {
                "type": "object",
                "properties": {
                    "conversations": {"type": "array", "items": {"$ref": "#/components/schemas/ConversationResponse"}},
                    "total": {"type": "integer", "description": "Total number of matching conversations"},
                },
            },
        },
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT token obtained from /auth/login",
            }
        },
    },
    "tags": [{"name": "MCP Tools", "description": "MCP protocol tools exposed as HTTP endpoints"}],
}


def main():
    """Generate MCP tools OpenAPI spec"""
    output_path = Path(__file__).parent.parent / "openapi" / "mcp-tools.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(mcp_tools_spec, f, indent=2)

    print("✓ Generated MCP Tools OpenAPI spec")
    print(f"  Saved to: {output_path}")
    print(f"  Tools documented: {len(mcp_tools_spec['paths'])}")
    print(f"  Schemas: {len(mcp_tools_spec['components']['schemas'])}")


if __name__ == "__main__":
    main()
