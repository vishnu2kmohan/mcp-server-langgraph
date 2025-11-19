"""
Customer Support Agent Template

A production-ready customer support agent with:
- Intent classification
- FAQ lookup
- Technical support routing
- Escalation to human agents
- Sentiment analysis
- Response templates

Usage:
    from templates.agents.customer_support_agent import create_support_agent

    agent = create_support_agent(
        knowledge_base_path="./kb.json",
        escalation_webhook="https://api.example.com/escalate"
    )

    result = agent.invoke({"query": "My payment failed"})
    print(result["response"])
"""

from typing import Literal

from langgraph.graph import StateGraph
from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# State Definitions
# ------------------------------------------------------------------------------


class SupportState(BaseModel):
    """State for customer support agent."""

    query: str = Field(description="Customer query")
    intent: Literal["faq", "technical", "billing", "complaint", "escalate", "unknown"] = Field(
        default="unknown", description="Classified intent"
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(default="neutral", description="Customer sentiment")
    priority: Literal["low", "medium", "high", "urgent"] = Field(default="medium", description="Support priority")
    response: str = Field(default="", description="Agent response")
    escalated: bool = Field(default=False, description="Whether escalated to human")
    faq_matches: list[dict[str, str]] = Field(default_factory=list, description="Matching FAQ entries")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional metadata")


# ------------------------------------------------------------------------------
# Node Functions
# ------------------------------------------------------------------------------


def classify_intent(state: SupportState) -> SupportState:
    """
    Classify customer query intent.

    Uses keyword matching and patterns to determine intent.
    In production, replace with LLM-based classification.
    """
    query_lower = state.query.lower()

    # Intent classification rules
    if any(word in query_lower for word in ["price", "cost", "billing", "payment", "charge", "refund"]):
        state.intent = "billing"
        state.priority = "high"
    elif any(word in query_lower for word in ["error", "bug", "crash", "not working", "broken", "issue"]):
        state.intent = "technical"
        state.priority = "medium"
    elif any(word in query_lower for word in ["angry", "frustrated", "terrible", "worst", "complaint"]):
        state.intent = "complaint"
        state.priority = "urgent"
        state.sentiment = "negative"
    elif any(word in query_lower for word in ["how", "what", "when", "where", "why", "help", "guide"]):
        state.intent = "faq"
        state.priority = "low"
    else:
        state.intent = "unknown"
        state.priority = "medium"

    # Sentiment analysis (simplified)
    if any(word in query_lower for word in ["great", "excellent", "love", "thank", "perfect"]):
        state.sentiment = "positive"
    elif any(word in query_lower for word in ["bad", "terrible", "awful", "hate", "worst", "angry"]):
        state.sentiment = "negative"

    return state


def search_knowledge_base(state: SupportState) -> SupportState:
    """
    Search FAQ knowledge base for matching articles.

    In production, integrate with:
    - Elasticsearch
    - Vector databases (Qdrant, Pinecone)
    - FAQ management systems
    """
    # Simulated FAQ database
    faq_database = [
        {"question": "How do I reset my password?", "answer": "Click 'Forgot Password' on the login page..."},
        {"question": "What payment methods do you accept?", "answer": "We accept credit cards, PayPal, and wire transfer."},
        {"question": "How do I cancel my subscription?", "answer": "Go to Settings > Billing > Cancel Subscription..."},
        {
            "question": "Why is my payment failing?",
            "answer": "Common reasons: insufficient funds, expired card, or incorrect billing address.",
        },
    ]

    # Simple keyword matching
    query_keywords = set(state.query.lower().split())
    matches = []

    for faq in faq_database:
        faq_keywords = set(faq["question"].lower().split())
        similarity = len(query_keywords & faq_keywords) / len(query_keywords | faq_keywords)

        if similarity > 0.3:  # 30% similarity threshold
            matches.append({"question": faq["question"], "answer": faq["answer"], "score": similarity})

    # Sort by similarity
    matches.sort(key=lambda x: x["score"], reverse=True)
    state.faq_matches = matches[:3]  # Top 3 matches

    return state


def handle_faq(state: SupportState) -> SupportState:
    """Handle FAQ queries with knowledge base lookup."""
    if state.faq_matches:
        # Found matching FAQs
        best_match = state.faq_matches[0]
        state.response = f"""I found this answer in our knowledge base:

**{best_match["question"]}**

{best_match["answer"]}

Is this what you were looking for? If you need more help, I can connect you with a specialist."""
    else:
        # No matches found
        state.response = """I couldn't find an exact answer to your question in our knowledge base.

Let me connect you with a specialist who can help you better."""
        state.escalated = True

    return state


def handle_technical(state: SupportState) -> SupportState:
    """Handle technical support queries."""
    state.response = f"""I understand you're experiencing a technical issue:
"{state.query}"

Let me help you troubleshoot:

1. **First, try these quick fixes:**
   - Clear your browser cache
   - Try a different browser
   - Check your internet connection

2. **If the issue persists:**
   I'm creating a support ticket and connecting you with our technical team.
   They'll be in touch within 1 hour.

Ticket ID: #{hash(state.query) % 100000}

Is there anything else I can help with while you wait?"""

    state.metadata["ticket_id"] = str(hash(state.query) % 100000)
    state.metadata["escalation_type"] = "technical"

    return state


def handle_billing(state: SupportState) -> SupportState:
    """Handle billing-related queries."""
    state.response = f"""I can help with your billing question:
"{state.query}"

For security reasons, I'm connecting you with our billing specialist
who can access your account details and assist you directly.

What to expect:
- Response time: Within 30 minutes
- Available: Mon-Fri 9AM-5PM EST
- You'll receive an email confirmation

Is there anything else I can help with?"""

    state.escalated = True
    state.metadata["escalation_type"] = "billing"
    state.metadata["department"] = "finance"

    return state


def handle_complaint(state: SupportState) -> SupportState:
    """Handle complaints with priority escalation."""
    state.response = f"""I'm very sorry to hear about your experience.

I want to make sure this gets the attention it deserves.
I'm immediately escalating your concern to our customer success manager.

What happens next:
- Priority escalation created
- Manager will contact you within 15 minutes
- You'll receive a direct phone call or email
- We'll work to resolve this as quickly as possible

Reference: URGENT-{hash(state.query) % 100000}

Thank you for your patience. We value your feedback and want to make this right."""

    state.escalated = True
    state.priority = "urgent"
    state.metadata["escalation_type"] = "complaint"
    state.metadata["urgent_ref"] = f"URGENT-{hash(state.query) % 100000}"

    return state


def escalate_to_human(state: SupportState) -> SupportState:
    """Escalate to human agent."""
    state.response = """I'm connecting you with one of our specialists who can provide more detailed assistance.

They'll have full context of our conversation and will be with you shortly.

Average wait time: 2-3 minutes

Thank you for your patience!"""

    state.escalated = True
    state.metadata["escalation_time"] = "immediate"

    return state


# ------------------------------------------------------------------------------
# Routing Logic
# ------------------------------------------------------------------------------


def route_by_intent(state: SupportState) -> str:
    """Route to appropriate handler based on intent."""
    routing_map = {
        "faq": "handle_faq",
        "technical": "handle_technical",
        "billing": "handle_billing",
        "complaint": "handle_complaint",
        "unknown": "escalate",
    }

    return routing_map.get(state.intent, "escalate")


# ------------------------------------------------------------------------------
# Agent Creation
# ------------------------------------------------------------------------------


def create_support_agent(knowledge_base_path: str | None = None, escalation_webhook: str | None = None):
    """
    Create customer support agent.

    Args:
        knowledge_base_path: Path to FAQ knowledge base JSON
        escalation_webhook: Webhook URL for escalations

    Returns:
        Compiled LangGraph agent

    Example:
        >>> agent = create_support_agent()
        >>> result = agent.invoke(SupportState(query="How do I reset my password?"))
        >>> print(result.response)
    """
    # Create graph
    graph = StateGraph(SupportState)

    # Add nodes
    graph.add_node("classify", classify_intent)
    graph.add_node("search_kb", search_knowledge_base)
    graph.add_node("handle_faq", handle_faq)
    graph.add_node("handle_technical", handle_technical)
    graph.add_node("handle_billing", handle_billing)
    graph.add_node("handle_complaint", handle_complaint)
    graph.add_node("escalate", escalate_to_human)

    # Define edges
    graph.set_entry_point("classify")
    graph.add_edge("classify", "search_kb")
    graph.add_conditional_edges("search_kb", route_by_intent)

    # All handlers end at finish
    for node in ["handle_faq", "handle_technical", "handle_billing", "handle_complaint", "escalate"]:
        graph.set_finish_point(node)

    # Compile
    return graph.compile()


# ------------------------------------------------------------------------------
# Example Usage
# ------------------------------------------------------------------------------


if __name__ == "__main__":
    # Create agent
    agent = create_support_agent()

    # Test queries
    test_queries = [
        "How do I reset my password?",
        "My payment keeps failing!",
        "The app crashes every time I try to export",
        "This is the worst service ever. I want a refund!",
        "What time do you close?",
    ]

    print("=" * 80)
    print("CUSTOMER SUPPORT AGENT - TEST RUN")
    print("=" * 80)

    for query in test_queries:
        print(f"\n{'=' * 80}")
        print(f"CUSTOMER: {query}")
        print(f"{'=' * 80}")

        result = agent.invoke(SupportState(query=query))

        print(f"\nIntent: {result.intent}")
        print(f"Priority: {result.priority}")
        print(f"Sentiment: {result.sentiment}")
        print(f"Escalated: {result.escalated}")
        print(f"\nRESPONSE:\n{result.response}")

    print(f"\n{'=' * 80}\n")
