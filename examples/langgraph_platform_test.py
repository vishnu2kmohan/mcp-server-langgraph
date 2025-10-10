"""
Example: Testing LangGraph Platform Deployment

This example demonstrates:
1. Testing graph locally before deployment
2. Invoking deployed graph on platform
3. Streaming responses from platform
4. Handling errors
"""
import os
import sys
import json
from typing import Dict, Any

# For local testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.messages import HumanMessage


def test_local_graph():
    """Test the graph locally before deploying"""
    print("=" * 60)
    print("Testing Graph Locally")
    print("=" * 60)

    from agent import agent_graph

    # Test invocation
    test_inputs = {
        "messages": [HumanMessage(content="What is LangGraph Platform?")],
        "user_id": "test_user",
        "request_id": "test_001"
    }

    print(f"\nInput: {test_inputs['messages'][0].content}")
    print("\nInvoking graph...")

    result = agent_graph.invoke(test_inputs)

    print(f"\nResponse: {result['messages'][-1].content}")
    print("\n✓ Local graph works!")


def test_platform_deployment():
    """Test invoking the deployed graph on LangGraph Platform"""
    print("\n" + "=" * 60)
    print("Testing Platform Deployment")
    print("=" * 60)

    # Check if deployment URL is configured
    deployment_url = os.getenv("LANGGRAPH_DEPLOYMENT_URL")
    if not deployment_url:
        print("\n⚠ LANGGRAPH_DEPLOYMENT_URL not set")
        print("\nTo test platform deployment:")
        print("  1. Deploy your graph: langgraph deploy")
        print("  2. Get deployment URL: langgraph deployment get <name>")
        print("  3. Set LANGGRAPH_DEPLOYMENT_URL environment variable")
        print("\nOr use CLI directly:")
        print("  langgraph deployment invoke <deployment-name> \\")
        print("    --input '{\"messages\": [{\"role\": \"user\", \"content\": \"test\"}]}'")
        return

    print(f"\nDeployment URL: {deployment_url}")
    print("\n⚠ Platform invocation requires HTTP client")
    print("Use the LangGraph CLI instead:")
    print(f"\nlanggraph deployment invoke <deployment-name> \\")
    print(f"  --input '{{\"messages\": [{{\"role\": \"user\", \"content\": \"test\"}}]}}'")


def test_with_cli():
    """Example CLI commands for testing deployment"""
    print("\n" + "=" * 60)
    print("CLI Testing Examples")
    print("=" * 60)

    examples = [
        {
            "name": "Basic Invocation",
            "command": """langgraph deployment invoke mcp-server-langgraph \\
  --input '{"messages": [{"role": "user", "content": "Hello!"}]}'"""
        },
        {
            "name": "With User Context",
            "command": """langgraph deployment invoke mcp-server-langgraph \\
  --input '{"messages": [{"role": "user", "content": "Analyze data"}], "user_id": "alice"}' \\
  --config '{"configurable": {"user_id": "alice", "request_id": "req123"}}'"""
        },
        {
            "name": "Streaming Response",
            "command": """langgraph deployment invoke mcp-server-langgraph \\
  --input '{"messages": [{"role": "user", "content": "Tell me a story"}]}' \\
  --stream"""
        },
        {
            "name": "Check Deployment Status",
            "command": "langgraph deployment get mcp-server-langgraph"
        },
        {
            "name": "View Logs",
            "command": "langgraph deployment logs mcp-server-langgraph --follow"
        }
    ]

    for example in examples:
        print(f"\n{example['name']}:")
        print(f"  {example['command']}")


def test_error_handling():
    """Test error handling"""
    print("\n" + "=" * 60)
    print("Testing Error Handling")
    print("=" * 60)

    from agent import agent_graph

    test_cases = [
        {
            "name": "Empty Messages",
            "input": {"messages": [], "user_id": "test", "request_id": "err001"},
            "expected_error": True
        },
        {
            "name": "Invalid Message Type",
            "input": {"messages": ["not a message object"], "user_id": "test", "request_id": "err002"},
            "expected_error": True
        }
    ]

    for test in test_cases:
        print(f"\nTest: {test['name']}")
        try:
            result = agent_graph.invoke(test['input'])
            if test['expected_error']:
                print("  ✗ Expected error but succeeded")
            else:
                print("  ✓ Success")
        except Exception as e:
            if test['expected_error']:
                print(f"  ✓ Expected error: {type(e).__name__}")
            else:
                print(f"  ✗ Unexpected error: {e}")


def show_deployment_checklist():
    """Show pre-deployment checklist"""
    print("\n" + "=" * 60)
    print("Pre-Deployment Checklist")
    print("=" * 60)

    checklist = [
        "✓ Test graph locally (this script)",
        "✓ All dependencies in langgraph/requirements.txt",
        "✓ langgraph.json configured correctly",
        "✓ Environment variables set in LangSmith",
        "✓ API keys added as secrets",
        "✓ Graph entrypoint correct (langgraph/agent.py:graph)",
        "✓ Logged in to LangChain (langgraph login)",
        "✓ LangSmith project created",
    ]

    print("\nBefore deploying, ensure:")
    for item in checklist:
        print(f"  {item}")

    print("\nDeployment commands:")
    print("  # Test locally first")
    print("  langgraph dev")
    print()
    print("  # Deploy to staging")
    print("  langgraph deploy my-agent-staging --tag staging")
    print()
    print("  # Test staging")
    print("  langgraph deployment invoke my-agent-staging --input '...'")
    print()
    print("  # Deploy to production")
    print("  langgraph deploy my-agent-prod --tag production")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  LangGraph Platform Testing")
    print("=" * 60)

    # Run tests
    test_local_graph()
    test_platform_deployment()
    test_with_cli()
    test_error_handling()
    show_deployment_checklist()

    print("\n" + "=" * 60)
    print("  Testing Complete!")
    print("=" * 60)
    print("\n📍 Next steps:")
    print("  1. Fix any failed tests")
    print("  2. Review deployment checklist")
    print("  3. Deploy to staging: langgraph deploy <name>-staging")
    print("  4. Test staging deployment thoroughly")
    print("  5. Deploy to production: langgraph deploy <name>-prod")
    print("\n")


if __name__ == "__main__":
    main()
