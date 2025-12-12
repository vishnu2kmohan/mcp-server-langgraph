"""
Template Recommendation Module

Provides AI-powered workflow template recommendations.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowTemplate:
    """A workflow template that can be used as a starting point."""

    id: str
    name: str
    description: str
    category: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    tags: list[str] = field(default_factory=list)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access for backward compatibility."""
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        """Get attribute with default."""
        return getattr(self, key, default)


# Built-in templates
BUILT_IN_TEMPLATES = [
    WorkflowTemplate(
        id="chatbot-basic",
        name="Basic Chatbot",
        description="Simple conversational chatbot with LLM",
        category="conversational",
        nodes=[
            {"id": "input", "type": "input", "data": {"label": "User Input"}},
            {"id": "llm", "type": "llm", "data": {"model": "gpt-4"}},
            {"id": "output", "type": "output", "data": {"label": "Response"}},
        ],
        edges=[
            {"source": "input", "target": "llm"},
            {"source": "llm", "target": "output"},
        ],
        tags=["chatbot", "conversational", "basic", "llm"],
    ),
    WorkflowTemplate(
        id="chatbot-rag",
        name="RAG Chatbot",
        description="Chatbot with retrieval-augmented generation for document Q&A",
        category="conversational",
        nodes=[
            {"id": "input", "type": "input", "data": {"label": "User Query"}},
            {"id": "retriever", "type": "tool", "data": {"tool": "vector_search"}},
            {"id": "llm", "type": "llm", "data": {"model": "gpt-4"}},
            {"id": "output", "type": "output", "data": {"label": "Answer"}},
        ],
        edges=[
            {"source": "input", "target": "retriever"},
            {"source": "retriever", "target": "llm"},
            {"source": "llm", "target": "output"},
        ],
        tags=["chatbot", "rag", "retrieval", "documents", "qa"],
    ),
    WorkflowTemplate(
        id="api-agent",
        name="API Agent",
        description="Agent that calls external APIs to complete tasks",
        category="integration",
        nodes=[
            {"id": "input", "type": "input", "data": {"label": "Task"}},
            {"id": "planner", "type": "llm", "data": {"model": "gpt-4"}},
            {"id": "api-tool", "type": "tool", "data": {"tool": "http_request"}},
            {"id": "output", "type": "output", "data": {"label": "Result"}},
        ],
        edges=[
            {"source": "input", "target": "planner"},
            {"source": "planner", "target": "api-tool"},
            {"source": "api-tool", "target": "output"},
        ],
        tags=["api", "agent", "http", "rest", "integration"],
    ),
    WorkflowTemplate(
        id="data-pipeline",
        name="Data Processing Pipeline",
        description="Process and transform data through multiple stages",
        category="data",
        nodes=[
            {"id": "input", "type": "input", "data": {"label": "Raw Data"}},
            {"id": "transform", "type": "code", "data": {"language": "python"}},
            {"id": "validate", "type": "code", "data": {"language": "python"}},
            {"id": "output", "type": "output", "data": {"label": "Processed Data"}},
        ],
        edges=[
            {"source": "input", "target": "transform"},
            {"source": "transform", "target": "validate"},
            {"source": "validate", "target": "output"},
        ],
        tags=["data", "pipeline", "etl", "transform", "processing"],
    ),
    WorkflowTemplate(
        id="multi-agent",
        name="Multi-Agent System",
        description="Multiple AI agents collaborating to solve complex tasks",
        category="agents",
        nodes=[
            {"id": "input", "type": "input", "data": {"label": "Task"}},
            {"id": "coordinator", "type": "llm", "data": {"model": "gpt-4"}},
            {"id": "researcher", "type": "llm", "data": {"model": "gpt-4"}},
            {"id": "writer", "type": "llm", "data": {"model": "gpt-4"}},
            {"id": "output", "type": "output", "data": {"label": "Result"}},
        ],
        edges=[
            {"source": "input", "target": "coordinator"},
            {"source": "coordinator", "target": "researcher"},
            {"source": "coordinator", "target": "writer"},
            {"source": "researcher", "target": "writer"},
            {"source": "writer", "target": "output"},
        ],
        tags=["multi-agent", "agents", "collaboration", "complex"],
    ),
]


class TemplateRecommender:
    """Recommends workflow templates based on user descriptions.

    Uses semantic similarity to match user intent to available templates.

    Example:
        recommender = TemplateRecommender()
        matches = await recommender.recommend("Build a chatbot with RAG")
    """

    def __init__(self) -> None:
        """Initialize the template recommender."""
        self._templates = list(BUILT_IN_TEMPLATES)

    def get_available_templates(self) -> list[WorkflowTemplate]:
        """Get all available templates.

        Returns:
            List of available workflow templates
        """
        return self._templates

    async def recommend(
        self,
        description: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Recommend templates matching the description.

        Args:
            description: User description of desired workflow
            top_k: Maximum number of templates to return

        Returns:
            List of matching templates with similarity scores
        """
        results = []

        for template in self._templates:
            similarity = await self._compute_similarity(description, template)
            results.append(
                {
                    "template": template,
                    "similarity": similarity,
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "category": template.category,
                }
            )

        # Sort by similarity descending
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:top_k]

    async def _compute_similarity(
        self,
        description: str,
        template: WorkflowTemplate,
    ) -> float:
        """Compute similarity between description and template.

        Args:
            description: User description
            template: Workflow template

        Returns:
            Similarity score between 0 and 1
        """
        # Simple keyword-based similarity for now
        # In production, this would use embeddings
        description_lower = description.lower()
        score = 0.0

        # Check name match
        if template.name.lower() in description_lower:
            score += 0.3

        # Check tag matches
        matched_tags = 0
        for tag in template.tags:
            if tag.lower() in description_lower:
                matched_tags += 1

        if template.tags:
            score += 0.5 * (matched_tags / len(template.tags))

        # Check description match
        template_words = set(template.description.lower().split())
        description_words = set(description_lower.split())
        common_words = template_words & description_words
        if template_words:
            score += 0.2 * (len(common_words) / len(template_words))

        return min(score, 1.0)
