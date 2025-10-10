"""
Example: Using LangSmith for tracing and observability

This example demonstrates:
1. Enabling LangSmith tracing
2. Adding custom metadata and tags
3. Collecting user feedback
4. Analyzing traces programmatically
"""
import os
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

# Import agent
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import agent_graph
from langsmith_config import langsmith_config, get_run_metadata, get_run_tags

# Import LangSmith client for feedback
try:
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    print("⚠ LangSmith not installed. Install with: pip install langsmith")
    LANGSMITH_AVAILABLE = False
    Client = None


def example_basic_tracing():
    """Example 1: Basic automatic tracing"""
    print("=" * 60)
    print("Example 1: Basic Automatic Tracing")
    print("=" * 60)

    # Simple invocation - automatically traced if LANGSMITH_TRACING=true
    result = agent_graph.invoke({
        "messages": [HumanMessage(content="What is LangGraph?")],
        "user_id": "user123",
        "request_id": "req456"
    })

    print(f"\nResponse: {result['messages'][-1].content}")
    print("\n✓ Check LangSmith UI to see the trace!")
    print(f"  Project: {os.getenv('LANGSMITH_PROJECT', 'default')}")
    print(f"  URL: https://smith.langchain.com/")


def example_custom_metadata():
    """Example 2: Adding custom metadata and tags"""
    print("\n" + "=" * 60)
    print("Example 2: Custom Metadata and Tags")
    print("=" * 60)

    # Create custom run configuration
    config = RunnableConfig(
        run_name="premium-user-query",
        tags=get_run_tags(
            user_id="alice@company.com",
            additional_tags=["premium", "priority-high", "sales-dept"]
        ),
        metadata=get_run_metadata(
            user_id="alice@company.com",
            request_id="req789",
            additional_metadata={
                "session_id": "sess_abc123",
                "request_source": "web",
                "cost_center": "sales",
                "user_tier": "premium"
            }
        )
    )

    # Invoke with configuration
    result = agent_graph.invoke({
        "messages": [HumanMessage(content="Analyze this quarter's performance")],
        "user_id": "alice@company.com",
        "request_id": "req789"
    }, config=config)

    print(f"\nResponse: {result['messages'][-1].content}")
    print("\n✓ Check LangSmith UI - this trace has rich metadata!")
    print("  Filter by tags: premium, priority-high")
    print("  Check metadata for business context")


def example_collect_feedback():
    """Example 3: Collecting user feedback"""
    print("\n" + "=" * 60)
    print("Example 3: Collecting User Feedback")
    print("=" * 60)

    if not LANGSMITH_AVAILABLE:
        print("⚠ Skipping - LangSmith not installed")
        return

    # First, make a request
    result = agent_graph.invoke({
        "messages": [HumanMessage(content="Explain deployment options")],
        "user_id": "bob@company.com",
        "request_id": "req999"
    })

    print(f"\nResponse: {result['messages'][-1].content[:100]}...")

    # Simulate user providing feedback
    print("\n📝 Simulating user feedback...")

    # To collect feedback, we need the run_id from the trace
    # In practice, you'd capture this from the trace or use a callback

    # Example feedback submission (requires run_id from actual trace)
    print("""
To collect feedback in production:

1. Capture run_id from trace:
   from langchain.callbacks import get_run_id
   run_id = get_run_id()

2. Submit feedback:
   from langsmith import Client
   client = Client()
   client.create_feedback(
       run_id=run_id,
       key="user_rating",
       score=1.0,  # 0.0 to 1.0 (1.0 = thumbs up)
       comment="Very helpful explanation!",
       source_info={"user_id": "bob@company.com"}
   )

3. View feedback in LangSmith UI:
   - Go to your project
   - Click "Feedback" tab
   - Analyze trends
""")


def example_error_tracking():
    """Example 4: Error tracking and debugging"""
    print("\n" + "=" * 60)
    print("Example 4: Error Tracking")
    print("=" * 60)

    try:
        # Intentionally cause an error (empty messages)
        result = agent_graph.invoke({
            "messages": [],  # This will cause an error
            "user_id": "test_user",
            "request_id": "error_test"
        })
    except Exception as e:
        print(f"\n✗ Error occurred: {type(e).__name__}: {e}")
        print("\n✓ Error is traced in LangSmith!")
        print("  - Full stack trace available")
        print("  - Input data captured")
        print("  - Filter by status:error in UI")


def example_analyze_traces():
    """Example 5: Programmatic trace analysis"""
    print("\n" + "=" * 60)
    print("Example 5: Programmatic Trace Analysis")
    print("=" * 60)

    if not LANGSMITH_AVAILABLE:
        print("⚠ Skipping - LangSmith not installed")
        return

    client = Client()

    # Get recent traces
    print("\n📊 Fetching recent traces...")

    try:
        runs = list(client.list_runs(
            project_name=os.getenv("LANGSMITH_PROJECT", "default"),
            limit=5
        ))

        print(f"\nFound {len(runs)} recent traces:")
        for run in runs:
            print(f"\n  Run ID: {run.id}")
            print(f"  Status: {run.status}")
            print(f"  Latency: {run.latency:.2f}s" if run.latency else "  Latency: N/A")
            print(f"  Tokens: {run.total_tokens}" if hasattr(run, 'total_tokens') else "  Tokens: N/A")

    except Exception as e:
        print(f"\n⚠ Could not fetch traces: {e}")
        print("  Ensure LANGSMITH_API_KEY is set")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("  LangSmith Tracing Examples")
    print("=" * 60)

    # Check if LangSmith is configured
    if not langsmith_config.is_enabled():
        print("\n⚠ LangSmith is not enabled!")
        print("\nTo enable LangSmith, set these environment variables:")
        print("  export LANGSMITH_API_KEY='your-api-key'")
        print("  export LANGSMITH_TRACING=true")
        print("  export LANGSMITH_PROJECT='mcp-server-langgraph'")
        print("\nOr add to your .env file")
        return

    print(f"\n✓ LangSmith is enabled")
    print(f"  Project: {os.getenv('LANGSMITH_PROJECT', 'default')}")

    # Run examples
    example_basic_tracing()
    example_custom_metadata()
    example_collect_feedback()
    example_error_tracking()
    example_analyze_traces()

    print("\n" + "=" * 60)
    print("  All examples completed!")
    print("=" * 60)
    print("\n📍 Next steps:")
    print("  1. View traces in LangSmith UI: https://smith.langchain.com/")
    print("  2. Try filtering by tags and metadata")
    print("  3. Create datasets from traces")
    print("  4. Set up evaluations")
    print("\n")


if __name__ == "__main__":
    main()
