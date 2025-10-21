#!/usr/bin/env python3
"""
Example: Enhanced Structured Note-Taking with LLM Extraction

Demonstrates Anthropic's structured note-taking pattern:
1. Extract key information from conversations
2. Categorize into 6 types (decisions, requirements, facts, action_items, issues, preferences)
3. Preserve important context for long-horizon tasks
4. Fall back to rule-based extraction if LLM unavailable

Prerequisites:
- LLM configured (for enhanced extraction)
- Set ENABLE_LLM_EXTRACTION=true in .env

Usage:
    python examples/llm_extraction_demo.py
"""

import asyncio

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from mcp_server_langgraph.core.context_manager import ContextManager


async def example_1_basic_extraction():
    """Example 1: Basic LLM-based extraction"""
    print("\n" + "=" * 70)
    print("Example 1: Basic LLM-Based Extraction")
    print("=" * 70)

    manager = ContextManager()

    # Simulate a conversation about a project
    conversation = [
        HumanMessage(content="We need to build a new API gateway for our microservices"),
        AIMessage(content="Great! What are the key requirements?"),
        HumanMessage(content="It must support at least 100K requests per second with 99.9% uptime"),
        AIMessage(content="Got it. What technology should we use?"),
        HumanMessage(content="We decided to use Kong API Gateway with PostgreSQL"),
        AIMessage(content="Good choice. I'll note that Kong supports rate limiting and authentication"),
        HumanMessage(content="We need to implement OAuth2 authentication first"),
        AIMessage(content="There's currently an issue with the Redis connection pooling"),
        HumanMessage(content="I prefer using Docker Compose for local development"),
    ]

    print("\n📝 Conversation:")
    for i, msg in enumerate(conversation, 1):
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        print(f"   {i}. {role}: {msg.content[:60]}...")

    print("\n🔍 Extracting key information with LLM...")

    try:
        key_info = await manager.extract_key_information_llm(conversation)

        print("\n📊 Extracted Information:")

        categories = ["decisions", "requirements", "facts", "action_items", "issues", "preferences"]

        for category in categories:
            items = key_info.get(category, [])
            if items:
                print(f"\n   {category.upper().replace('_', ' ')}:")
                for item in items:
                    print(f"   • {item}")
            else:
                print(f"\n   {category.upper().replace('_', ' ')}: (none)")

    except Exception as e:
        print(f"\n❌ LLM extraction failed: {e}")
        print("   Falling back to rule-based extraction...")

        # Fallback to rule-based
        key_info = manager.extract_key_information(conversation)
        print("\n📊 Extracted Information (Rule-Based):")
        for category, items in key_info.items():
            if items:
                print(f"\n   {category.upper()}:")
                for item in items:
                    print(f"   • {item[:100]}...")


async def example_2_long_conversation():
    """Example 2: Extracting from long conversation"""
    print("\n" + "=" * 70)
    print("Example 2: Long Conversation Extraction")
    print("=" * 70)

    manager = ContextManager()

    # Simulate a longer conversation
    long_conversation = [
        HumanMessage(content="Let's discuss the Q4 roadmap for our platform"),
        AIMessage(content="Sure! What are the priorities?"),
        HumanMessage(content="We decided to focus on three main areas: performance, security, and UX"),
        AIMessage(content="Good breakdown. Let's start with performance."),
        HumanMessage(content="The system must handle 1M daily active users without degradation"),
        AIMessage(content="That's a significant requirement. What's current capacity?"),
        HumanMessage(content="Currently we're at 250K DAU with some slowdowns during peak"),
        AIMessage(content="So we need 4x scale-up. Any constraints?"),
        HumanMessage(content="Budget is limited to $50K for infrastructure upgrades"),
        AIMessage(content="For security, what are the priorities?"),
        HumanMessage(content="We need to implement SOC 2 compliance controls"),
        AIMessage(content="That includes encryption at rest and in transit, audit logging..."),
        HumanMessage(content="Yes, and we need to complete a penetration test by end of quarter"),
        AIMessage(content="What about the UX improvements?"),
        HumanMessage(content="Users are reporting slow page load times on mobile"),
        AIMessage(content="I found that our images are not optimized - averaging 2MB each"),
        HumanMessage(content="Let's implement image compression and lazy loading"),
        AIMessage(content="I'll create tickets for the development team"),
        HumanMessage(content="I prefer we use WebP format for images to maximize compression"),
        AIMessage(content="There's an issue with the current build pipeline - deployments take 45 minutes"),
        HumanMessage(content="That needs to be fixed before we scale development"),
    ]

    print(f"\n📝 Long conversation: {len(long_conversation)} messages")

    print("\n🔍 Extracting structured information...")

    try:
        key_info = await manager.extract_key_information_llm(long_conversation)

        print("\n📊 Structured Summary:")

        summaries = {
            "decisions": "🎯",
            "requirements": "📋",
            "facts": "💡",
            "action_items": "✅",
            "issues": "⚠️",
            "preferences": "👍",
        }

        for category, emoji in summaries.items():
            items = key_info.get(category, [])
            count = len(items)
            print(f"\n   {emoji} {category.upper().replace('_', ' ')} ({count}):")

            if items:
                for i, item in enumerate(items[:3], 1):  # Show first 3
                    print(f"      {i}. {item}")
                if len(items) > 3:
                    print(f"      ... and {len(items) - 3} more")
            else:
                print("      (none)")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def example_3_compaction_with_extraction():
    """Example 3: Combine compaction with extraction"""
    print("\n" + "=" * 70)
    print("Example 3: Compaction + Extraction")
    print("=" * 70)

    manager = ContextManager(
        compaction_threshold=500,  # Low threshold for demo
        target_after_compaction=250,
        recent_message_count=3,
    )

    # Create conversation that will trigger compaction
    messages = []
    for i in range(10):
        messages.append(HumanMessage(content=f"This is message {i} with some content about the project. " * 10))
        messages.append(AIMessage(content=f"Response to message {i} with technical details and analysis. " * 10))

    # Add some important messages at the end
    messages.extend(
        [
            HumanMessage(content="We've decided to migrate to Kubernetes for orchestration"),
            AIMessage(content="Good decision. The system must support auto-scaling and rolling deployments"),
            HumanMessage(content="Current infrastructure can't handle more than 10K RPS"),
            AIMessage(content="We need to implement database connection pooling immediately"),
            HumanMessage(content="There's an issue with memory leaks in the worker processes"),
            AIMessage(content="I prefer using Prometheus for monitoring"),
        ]
    )

    print(f"\n📝 Original conversation: {len(messages)} messages")

    # Check if compaction needed
    needs_compaction = manager.needs_compaction(messages)
    print(f"   Compaction needed: {needs_compaction}")

    if needs_compaction:
        print("\n🔄 Compacting conversation...")
        compaction_result = await manager.compact_conversation(messages)

        print(f"\n   Original: {compaction_result.original_token_count} tokens, {len(messages)} messages")
        print(
            f"   Compacted: {compaction_result.compacted_token_count} tokens, {len(compaction_result.compacted_messages)} messages"  # noqa: E501
        )
        print(f"   Compression ratio: {compaction_result.compression_ratio:.2%}")
        print(f"   Messages summarized: {compaction_result.messages_summarized}")

        messages = compaction_result.compacted_messages

    # Extract from compacted conversation
    print("\n🔍 Extracting key information from compacted conversation...")

    try:
        key_info = await manager.extract_key_information_llm(messages)

        print("\n📊 Key Information (after compaction):")

        important_categories = ["decisions", "requirements", "issues", "action_items"]

        for category in important_categories:
            items = key_info.get(category, [])
            if items:
                print(f"\n   {category.upper().replace('_', ' ')}:")
                for item in items:
                    print(f"   • {item}")

        print("\n   ✅ Important information preserved despite compaction")

    except Exception as e:
        print(f"\n❌ Error: {e}")


async def example_4_fallback_mechanism():
    """Example 4: Demonstrate fallback to rule-based extraction"""
    print("\n" + "=" * 70)
    print("Example 4: Fallback Mechanism")
    print("=" * 70)

    manager = ContextManager()

    conversation = [
        HumanMessage(content="We decided to implement a new caching layer"),
        AIMessage(content="The system must support distributed caching"),
        HumanMessage(content="There's an error in the Redis configuration"),
        HumanMessage(content="We need to update the documentation"),
        HumanMessage(content="I prefer using Redis over Memcached"),
    ]

    print("\n📝 Conversation:")
    for msg in conversation:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        print(f"   {role}: {msg.content}")

    print("\n🔍 Trying LLM extraction...")

    try:
        llm_result = await manager.extract_key_information_llm(conversation)
        print("   ✓ LLM extraction successful")

        print("\n📊 LLM Extraction Results:")
        for category, items in llm_result.items():
            if items:
                print(f"   {category}: {len(items)} items")

    except Exception as e:
        print(f"   ✗ LLM extraction failed: {e}")
        print("\n   Falling back to rule-based extraction...")

        rule_result = manager.extract_key_information(conversation)

        print("\n📊 Rule-Based Extraction Results:")
        for category, items in rule_result.items():
            if items:
                print(f"   {category}: {len(items)} items")
                for item in items:
                    print(f"      • {item}")

        print("\n   ✅ Fallback mechanism ensures reliability")


async def example_5_progressive_note_taking():
    """Example 5: Progressive note-taking for long-horizon tasks"""
    print("\n" + "=" * 70)
    print("Example 5: Progressive Note-Taking")
    print("=" * 70)

    manager = ContextManager()

    print("\n📚 Scenario: Multi-session project planning")
    print("\nSimulating 3 conversation sessions...")

    # Session 1: Initial planning
    print("\n--- Session 1: Initial Planning ---")
    session1 = [
        HumanMessage(content="Let's plan the migration to microservices architecture"),
        AIMessage(content="Great! What's the current architecture?"),
        HumanMessage(content="We have a monolithic Rails app handling 50K requests/day"),
        AIMessage(content="What are the key requirements for the migration?"),
        HumanMessage(content="Zero downtime, maintain current performance, complete in 6 months"),
        HumanMessage(content="We decided to start with the user service as the first microservice"),
    ]

    notes_session1 = await manager.extract_key_information_llm(session1)

    print("\n📝 Notes from Session 1:")
    for category in ["decisions", "requirements", "facts"]:
        if notes_session1.get(category):
            print(f"   {category.upper()}: {len(notes_session1[category])} items")

    # Session 2: Technical decisions
    print("\n--- Session 2: Technical Decisions (next day) ---")

    # In real scenario, we'd load notes_session1 as context
    session2 = [
        SystemMessage(content=f"Previous notes: {notes_session1}"),  # Load previous context
        HumanMessage(content="Let's decide on the tech stack for microservices"),
        AIMessage(content="What are the priorities? Performance, developer experience, or cost?"),
        HumanMessage(content="We decided to use Go for performance-critical services, Node.js for others"),
        AIMessage(content="Good choices. What about data storage?"),
        HumanMessage(content="Each service should have its own database - PostgreSQL for now"),
        HumanMessage(content="We need to implement an API gateway for routing"),
    ]

    notes_session2 = await manager.extract_key_information_llm(session2)

    print("\n📝 Notes from Session 2:")
    for category in ["decisions", "requirements", "action_items"]:
        if notes_session2.get(category):
            print(f"   {category.upper()}: {len(notes_session2[category])} items")

    # Session 3: Implementation planning
    print("\n--- Session 3: Implementation Planning (week later) ---")

    # Load accumulated notes
    accumulated_context = f"Session 1: {notes_session1}\nSession 2: {notes_session2}"

    session3 = [
        SystemMessage(content=f"Previous notes: {accumulated_context}"),
        HumanMessage(content="Let's create the implementation plan"),
        AIMessage(content="Based on previous sessions, we're migrating to microservices starting with user service"),
        HumanMessage(content="First action item: Set up Kong API Gateway"),
        HumanMessage(content="Second: Extract user module from monolith"),
        HumanMessage(content="Third: Deploy user service to staging"),
        AIMessage(content="There's a potential issue with database migrations during the split"),
        HumanMessage(content="I prefer a gradual rollout with feature flags"),
    ]

    notes_session3 = await manager.extract_key_information_llm(session3)

    print("\n📝 Notes from Session 3:")
    for category in ["action_items", "issues", "preferences"]:
        if notes_session3.get(category):
            print(f"   {category.upper()}: {len(notes_session3[category])} items")

    # Combine all notes
    print("\n" + "=" * 70)
    print("📚 Complete Project Notes (All Sessions)")
    print("=" * 70)

    all_notes = {
        "decisions": notes_session1.get("decisions", [])
        + notes_session2.get("decisions", [])
        + notes_session3.get("decisions", []),
        "requirements": notes_session1.get("requirements", [])
        + notes_session2.get("requirements", [])
        + notes_session3.get("requirements", []),
        "facts": notes_session1.get("facts", []) + notes_session2.get("facts", []) + notes_session3.get("facts", []),
        "action_items": notes_session1.get("action_items", [])
        + notes_session2.get("action_items", [])
        + notes_session3.get("action_items", []),
        "issues": notes_session1.get("issues", []) + notes_session2.get("issues", []) + notes_session3.get("issues", []),
        "preferences": notes_session1.get("preferences", [])
        + notes_session2.get("preferences", [])
        + notes_session3.get("preferences", []),
    }

    for category, items in all_notes.items():
        if items:
            print(f"\n{category.upper().replace('_', ' ')} ({len(items)}):")
            for i, item in enumerate(items, 1):
                print(f"   {i}. {item}")

    print("\n✅ Progressive note-taking maintains context across sessions")


async def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("Enhanced Structured Note-Taking Examples")
    print("Anthropic Best Practice: Structured Note-Taking Pattern")
    print("=" * 70)

    try:
        # Example 1: Basic extraction
        await example_1_basic_extraction()

        # Example 2: Long conversations
        await example_2_long_conversation()

        # Example 3: Compaction + extraction
        await example_3_compaction_with_extraction()

        # Example 4: Fallback mechanism
        await example_4_fallback_mechanism()

        # Example 5: Progressive note-taking
        await example_5_progressive_note_taking()

        print("\n" + "=" * 70)
        print("✅ All examples completed successfully!")
        print("=" * 70)

        print("\n📚 Key Takeaways:")
        print("   • Extract key information into 6 categories")
        print("   • LLM-based extraction for higher accuracy")
        print("   • Rule-based fallback for reliability")
        print("   • Combine with compaction for long conversations")
        print("   • Progressive note-taking for multi-session projects")
        print("   • Preserve important context across conversations")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure LLM is configured:")
        print("   - Set model credentials in .env")
        print("   - Set ENABLE_LLM_EXTRACTION=true")
        raise


if __name__ == "__main__":
    asyncio.run(main())
