#!/usr/bin/env python3
"""
Test LLM providers with LiteLLM integration
"""
import asyncio
import sys

from langchain_core.messages import HumanMessage

# Add parent directory to path
sys.path.insert(0, "..")

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.llm.factory import create_llm_from_config


async def test_llm():
    """Test LLM with current configuration"""
    print("=" * 60)
    print("Testing LLM Configuration")
    print("=" * 60)
    print()

    print(f"Provider: {settings.llm_provider}")
    print(f"Model: {settings.model_name}")
    print(f"Temperature: {settings.model_temperature}")
    print(f"Max Tokens: {settings.model_max_tokens}")
    print(f"Fallback Enabled: {settings.enable_fallback}")
    if settings.enable_fallback:
        print(f"Fallback Models: {settings.fallback_models}")
    print()

    # Create LLM instance
    try:
        llm = create_llm_from_config(settings)
        print("✓ LLM initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize LLM: {e}")
        return

    print()

    # Test simple query
    print("Testing simple query...")
    messages = [HumanMessage(content="What is 2+2? Answer with just the number.")]

    try:
        response = await llm.ainvoke(messages)
        print(f"✓ Response: {response.content}")
    except Exception as e:
        print(f"✗ Query failed: {e}")
        return

    print()

    # Test more complex query
    print("Testing complex query...")
    messages = [HumanMessage(content="Explain what LangGraph is in one sentence.")]

    try:
        response = await llm.ainvoke(messages)
        print(f"✓ Response: {response.content}")
    except Exception as e:
        print(f"✗ Query failed: {e}")

    print()
    print("=" * 60)
    print("✓ Test complete!")
    print("=" * 60)


async def test_multiple_providers():
    """Test multiple providers sequentially"""
    providers = [
        ("anthropic", "claude-3-5-sonnet-20241022"),
        ("openai", "gpt-4o"),
        ("google", "gemini-1.5-pro"),
        ("ollama", "ollama/llama3.1:8b"),
    ]

    print("=" * 60)
    print("Testing Multiple Providers")
    print("=" * 60)
    print()

    for provider, model in providers:
        print(f"\nTesting {provider} ({model})...")
        print("-" * 60)

        # Update settings
        original_provider = settings.llm_provider
        original_model = settings.model_name

        settings.llm_provider = provider
        settings.model_name = model

        try:
            llm = create_llm_from_config(settings)
            messages = [HumanMessage(content="Say 'Hello from " + provider + "!'")]
            response = await llm.ainvoke(messages)
            print(f"✓ {provider}: {response.content}")
        except Exception as e:
            print(f"✗ {provider} failed: {e}")

        # Restore settings
        settings.llm_provider = original_provider
        settings.model_name = original_model

    print()
    print("=" * 60)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Test LLM providers")
    parser.add_argument("--multi", action="store_true", help="Test multiple providers")
    parser.add_argument("--provider", help="Override provider (anthropic, openai, google, ollama)")
    parser.add_argument("--model", help="Override model name")

    args = parser.parse_args()

    # Override settings if specified
    if args.provider:
        settings.llm_provider = args.provider
    if args.model:
        settings.model_name = args.model

    if args.multi:
        asyncio.run(test_multiple_providers())
    else:
        asyncio.run(test_llm())


if __name__ == "__main__":
    main()
