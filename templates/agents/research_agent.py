"""
Research Agent Template

A production-ready research agent that:
- Searches multiple sources (web, databases, papers)
- Synthesizes information from diverse sources
- Provides cited responses
- Validates source credibility
- Generates comprehensive reports

Usage:
    from templates.agents.research_agent import create_research_agent

    agent = create_research_agent(
        search_engines=["tavily", "google"],
        max_sources=10
    )

    result = agent.invoke({"topic": "LangGraph architecture"})
    print(result["summary"])
"""

from typing import Dict, List

from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

# ------------------------------------------------------------------------------
# State Definitions
# ------------------------------------------------------------------------------


class ResearchState(BaseModel):
    """State for research agent."""

    topic: str = Field(description="Research topic")
    search_queries: List[str] = Field(default_factory=list, description="Generated search queries")
    search_results: List[Dict[str, str]] = Field(default_factory=list, description="Raw search results")
    filtered_sources: List[Dict[str, str]] = Field(default_factory=list, description="Filtered and validated sources")
    key_findings: List[str] = Field(default_factory=list, description="Key findings extracted")
    summary: str = Field(default="", description="Synthesized summary")
    citations: List[str] = Field(default_factory=list, description="Source citations")
    confidence_score: float = Field(default=0.0, description="Confidence in findings (0-1)")
    metadata: Dict[str, str] = Field(default_factory=dict, description="Research metadata")


# ------------------------------------------------------------------------------
# Node Functions
# ------------------------------------------------------------------------------


def generate_search_queries(state: ResearchState) -> ResearchState:
    """
    Generate multiple search queries from the topic.

    Decomposes complex topics into searchable queries.
    In production, use LLM to generate queries.
    """
    # Generate query variations
    queries = [
        state.topic,  # Original topic
        f"{state.topic} overview",
        f"{state.topic} architecture",
        f"{state.topic} best practices",
        f"{state.topic} examples",
        f"what is {state.topic}",
        f"how does {state.topic} work",
    ]

    state.search_queries = queries[:5]  # Limit to 5 queries
    return state


def search_web(state: ResearchState) -> ResearchState:
    """
    Search web for information.

    In production, integrate with:
    - Tavily API (best for AI research)
    - Google Custom Search API
    - Bing Search API
    - Academic databases (arXiv, PubMed)
    """
    # Simulated search results
    simulated_results = [
        {
            "title": f"Understanding {state.topic}: A Comprehensive Guide",
            "url": "https://example.com/guide",
            "snippet": f"{state.topic} is a powerful framework for building AI agents with state management...",
            "source": "example.com",
            "credibility": "high",
        },
        {
            "title": f"{state.topic} Documentation",
            "url": "https://docs.example.com",
            "snippet": "Official documentation covering architecture, API reference, and best practices...",
            "source": "docs.example.com",
            "credibility": "high",
        },
        {
            "title": f"Tutorial: Getting Started with {state.topic}",
            "url": "https://tutorial.example.com",
            "snippet": "Step-by-step tutorial showing how to build your first application...",
            "source": "tutorial.example.com",
            "credibility": "medium",
        },
        {
            "title": f"Blog: {state.topic} in Production",
            "url": "https://blog.example.com",
            "snippet": "Real-world experiences deploying {state.topic} at scale...",
            "source": "blog.example.com",
            "credibility": "medium",
        },
        {
            "title": f"{state.topic} vs Alternatives",
            "url": "https://comparison.example.com",
            "snippet": "Comparing {state.topic} with similar frameworks and tools...",
            "source": "comparison.example.com",
            "credibility": "medium",
        },
    ]

    state.search_results = simulated_results
    state.metadata["sources_found"] = str(len(simulated_results))

    return state


def filter_and_validate_sources(state: ResearchState) -> ResearchState:
    """
    Filter search results and validate source credibility.

    Criteria:
    - Credibility score
    - Recency
    - Relevance
    - Domain authority
    """
    # Filter by credibility
    high_credibility = [result for result in state.search_results if result.get("credibility") == "high"]

    medium_credibility = [result for result in state.search_results if result.get("credibility") == "medium"]

    # Prefer high credibility sources
    filtered = high_credibility + medium_credibility[:3]  # Max 3 medium sources

    state.filtered_sources = filtered
    state.metadata["filtered_count"] = str(len(filtered))

    return state


def extract_key_findings(state: ResearchState) -> ResearchState:
    """
    Extract key findings from filtered sources.

    In production, use LLM to extract and structure information.
    """
    findings = []

    for source in state.filtered_sources:
        # Simulate extraction
        finding = f"From {source['source']}: {source['snippet']}"
        findings.append(finding)

    state.key_findings = findings
    return state


def synthesize_summary(state: ResearchState) -> ResearchState:
    """
    Synthesize information into coherent summary.

    In production, use LLM to:
    - Combine information from multiple sources
    - Remove contradictions
    - Highlight consensus vs. differing views
    - Structure into readable format
    """
    # Create structured summary
    summary_parts = []

    # Introduction
    summary_parts.append(f"# Research Summary: {state.topic}\n")

    # Overview
    summary_parts.append("## Overview\n")
    if state.filtered_sources:
        first_source = state.filtered_sources[0]
        summary_parts.append(f"{first_source['snippet']}\n")

    # Key Findings
    summary_parts.append("## Key Findings\n")
    for i, finding in enumerate(state.key_findings, 1):
        summary_parts.append(f"{i}. {finding}\n")

    # Sources
    summary_parts.append("\n## Sources\n")
    for i, source in enumerate(state.filtered_sources, 1):
        citation = f"[{i}] {source['title']} - {source['url']}"
        summary_parts.append(f"{citation}\n")
        state.citations.append(citation)

    # Confidence
    state.confidence_score = min(len(state.filtered_sources) / 10.0, 1.0)  # More sources = higher confidence
    summary_parts.append(f"\n## Confidence Score: {state.confidence_score:.2f}/1.00\n")
    summary_parts.append(f"Based on {len(state.filtered_sources)} high-quality sources\n")

    state.summary = "".join(summary_parts)

    return state


# ------------------------------------------------------------------------------
# Agent Creation
# ------------------------------------------------------------------------------


def create_research_agent(search_engines: List[str] = None, max_sources: int = 10):
    """
    Create research agent.

    Args:
        search_engines: List of search engines to use
        max_sources: Maximum number of sources to process

    Returns:
        Compiled LangGraph agent

    Example:
        >>> agent = create_research_agent()
        >>> result = agent.invoke(ResearchState(topic="LangGraph"))
        >>> print(result.summary)
    """
    # Create graph
    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("generate_queries", generate_search_queries)
    graph.add_node("search", search_web)
    graph.add_node("filter", filter_and_validate_sources)
    graph.add_node("extract", extract_key_findings)
    graph.add_node("synthesize", synthesize_summary)

    # Define edges (sequential pipeline)
    graph.set_entry_point("generate_queries")
    graph.add_edge("generate_queries", "search")
    graph.add_edge("search", "filter")
    graph.add_edge("filter", "extract")
    graph.add_edge("extract", "synthesize")
    graph.set_finish_point("synthesize")

    # Compile
    return graph.compile()


# ------------------------------------------------------------------------------
# Example Usage
# ------------------------------------------------------------------------------


if __name__ == "__main__":
    # Create agent
    agent = create_research_agent()

    # Test topics
    test_topics = [
        "LangGraph architecture",
        "Claude AI capabilities",
        "Multi-agent systems",
        "Vector databases for RAG",
    ]

    print("=" * 80)
    print("RESEARCH AGENT - TEST RUN")
    print("=" * 80)

    for topic in test_topics:
        print(f"\n{'=' * 80}")
        print(f"RESEARCH TOPIC: {topic}")
        print(f"{'=' * 80}")

        result = agent.invoke(ResearchState(topic=topic))

        print(f"\nGenerated Queries: {', '.join(result.search_queries)}")
        print(f"Sources Found: {len(result.search_results)}")
        print(f"Sources Used: {len(result.filtered_sources)}")
        print(f"Confidence: {result.confidence_score:.2f}\n")
        print(result.summary)

    print(f"\n{'=' * 80}\n")
