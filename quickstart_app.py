#!/usr/bin/env python3
"""
MCP Server with LangGraph - Quick Start Application

Minimal setup for rapid prototyping (< 2 minutes).

Features:
- In-memory storage (no Docker needed)
- Free LLM defaults (Gemini Flash)
- FastAPI server with auto-generated docs
- Ready to extend with custom logic

Usage:
    # 1. Copy quick-start environment
    cp .env.quickstart .env

    # 2. Add your API key to .env
    # GOOGLE_API_KEY=your_key_here

    # 3. Run the server
    python quickstart_app.py

    # 4. Test the agent
    curl -X POST "http://localhost:8000/chat?query=Hello"

    # 5. View API docs
    open http://localhost:8000/docs
"""

from mcp_server_langgraph.presets import QuickStart


# Create quick-start agent
agent = QuickStart.create_app(
    name="MCP Server QuickStart",
    tools=[],  # Add tools as needed: ["search", "calculator"]
    llm="gemini-flash",  # Free tier default
    port=8000,
)

# Access the FastAPI app
app = agent

if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("🚀 MCP Server with LangGraph - Quick Start")
    print("=" * 80)
    print("\nStarting server...")
    print("\n📍 Endpoints:")
    print("   • Health:  http://localhost:8000/")
    print("   • Chat:    http://localhost:8000/chat")
    print("   • Docs:    http://localhost:8000/docs")
    print("\n💡 Example:")
    print('   curl -X POST "http://localhost:8000/chat?query=Hello"\n')
    print("=" * 80)
    print()

    uvicorn.run(
        "quickstart_app:app",
        host="0.0.0.0",  # nosec B104 - Intentional for quick-start local development
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info",
    )
