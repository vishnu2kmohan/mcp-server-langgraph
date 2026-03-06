"""
Template Recommendation Module

Provides AI-powered workflow template recommendations.

Supports multiple embedding backends:
1. EmbeddingService (unified abstraction) - preferred
2. sentence-transformers (legacy) - fallback
3. Keyword matching - last resort

Usage:
    from mcp_server_langgraph.studio.ai.templates import get_template_recommender

    recommender = get_template_recommender()  # Uses EmbeddingService from settings
    matches = await recommender.recommend("Build a chatbot with RAG")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.llm.embeddings import EmbeddingService

# Lazy-load embeddings to handle missing dependency

logger = logging.getLogger(__name__)
_embeddings_available: bool | None = None
_embedding_model: Any = None
_template_embeddings: dict[str, Any] = {}


def _init_embeddings() -> bool:
    """Initialize sentence-transformers model lazily.

    Returns:
        True if embeddings are available, False otherwise
    """
    global _embeddings_available
    global _embedding_model

    if _embeddings_available is not None:
        return _embeddings_available

    try:
        from sentence_transformers import SentenceTransformer

        # Use all-MiniLM-L6-v2 - fast and efficient for semantic search
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        _embeddings_available = True
        return True

    except ImportError:
        _embeddings_available = False
        return False


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
    Supports multiple embedding backends:
    1. EmbeddingService (unified abstraction) - preferred when injected
    2. sentence-transformers (legacy) - fallback for backward compatibility
    3. Keyword matching - last resort when no embeddings available

    Example:
        # With EmbeddingService (recommended)
        from mcp_server_langgraph.studio.ai.templates import get_template_recommender
        recommender = get_template_recommender()
        matches = await recommender.recommend("Build a chatbot with RAG")

        # Legacy (backward compatible)
        recommender = TemplateRecommender()
        matches = await recommender.recommend("Build a chatbot with RAG")
    """

    def __init__(
        self,
        enable_embeddings: bool = True,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        """Initialize the template recommender.

        Args:
            enable_embeddings: Whether to use embedding-based similarity
            embedding_service: Optional EmbeddingService for unified embeddings.
                If provided, takes precedence over sentence-transformers.
        """
        self._templates = list(BUILT_IN_TEMPLATES)
        self._enable_embeddings = enable_embeddings
        self._embedding_service = embedding_service
        self._embeddings_initialized = False
        self._template_embeddings_cache: dict[str, list[float]] = {}

    def _initialize_embeddings(self) -> None:
        """Pre-compute embeddings for all templates (lazy initialization)."""
        global _template_embeddings

        if self._embeddings_initialized or not self._enable_embeddings:
            return

        if not _init_embeddings():
            self._embeddings_initialized = True
            return

        # Pre-compute embeddings for all templates
        for template in self._templates:
            if template.id not in _template_embeddings:
                text = self._get_template_text(template)
                _template_embeddings[template.id] = _embedding_model.encode(text)

        self._embeddings_initialized = True

    def _get_template_text(self, template: WorkflowTemplate) -> str:
        """Get combined text representation for embedding.

        Args:
            template: The workflow template

        Returns:
            Combined text for embedding
        """
        parts = [
            template.name,
            template.description,
            template.category,
            " ".join(template.tags),
        ]
        return " ".join(parts)

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

        Uses embedding-based semantic similarity when sentence-transformers
        is available, falling back to keyword matching otherwise.

        Args:
            description: User description of desired workflow
            top_k: Maximum number of templates to return

        Returns:
            List of matching templates with similarity scores
        """
        # Lazy-initialize embeddings on first recommendation
        self._initialize_embeddings()

        # Pre-compute query embedding once if using EmbeddingService
        query_embedding: list[float] | None = None
        if self._embedding_service is not None:
            try:
                query_embedding = await self._embedding_service.embed(description)
            except Exception as e:
                logger.debug("Failed to compute query embedding: %s", e)

        results = []

        for template in self._templates:
            similarity = await self._compute_similarity(description, template, query_embedding=query_embedding)
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

        # Sort by similarity descending - cast to float for type checker
        results.sort(key=lambda x: float(str(x["similarity"])), reverse=True)

        return results[:top_k]

    async def _compute_similarity(
        self,
        description: str,
        template: WorkflowTemplate,
        query_embedding: list[float] | None = None,
    ) -> float:
        """Compute similarity between description and template.

        Priority:
        1. EmbeddingService (unified abstraction) - if injected
        2. sentence-transformers (legacy) - if available
        3. Keyword matching - fallback

        Args:
            description: User description
            template: Workflow template
            query_embedding: Pre-computed query embedding (optimization)

        Returns:
            Similarity score between 0 and 1
        """
        # Priority 1: Use injected EmbeddingService with pre-computed query
        if self._embedding_service is not None and query_embedding is not None:
            try:
                return await self._compute_embedding_service_similarity(template, query_embedding)
            except Exception as e:
                logger.debug("EmbeddingService similarity failed, falling back: %s", e)

        # Priority 2: Use legacy sentence-transformers
        if self._enable_embeddings and _embeddings_available and _embedding_model is not None:
            try:
                return self._compute_embedding_similarity(description, template)
            except Exception as e:
                logger.debug("Embedding similarity failed, falling back to keywords: %s", e)

        # Priority 3: Keyword-based similarity
        return self._compute_keyword_similarity(description, template)

    async def _compute_embedding_service_similarity(
        self,
        template: WorkflowTemplate,
        query_embedding: list[float],
    ) -> float:
        """Compute similarity using the unified EmbeddingService.

        Args:
            template: Workflow template
            query_embedding: Pre-computed query embedding

        Returns:
            Cosine similarity score between 0 and 1
        """
        import numpy as np

        # Get or compute template embedding (cached)
        if template.id in self._template_embeddings_cache:
            template_embedding = self._template_embeddings_cache[template.id]
        else:
            template_text = self._get_template_text(template)
            template_embedding = await self._embedding_service.embed(template_text)
            self._template_embeddings_cache[template.id] = template_embedding

        # Compute cosine similarity
        query_arr = np.array(query_embedding)
        template_arr = np.array(template_embedding)

        dot_product = np.dot(query_arr, template_arr)
        norm_query = np.linalg.norm(query_arr)
        norm_template = np.linalg.norm(template_arr)

        if norm_query == 0 or norm_template == 0:
            return 0.0

        similarity = dot_product / (norm_query * norm_template)

        # Convert from [-1, 1] to [0, 1] range
        return float((similarity + 1) / 2)

    def _compute_embedding_similarity(
        self,
        description: str,
        template: WorkflowTemplate,
    ) -> float:
        """Compute cosine similarity using embeddings.

        Args:
            description: User description
            template: Workflow template

        Returns:
            Cosine similarity score between 0 and 1
        """
        import numpy as np

        # Get query embedding
        query_embedding = _embedding_model.encode(description)

        # Get or compute template embedding
        if template.id in _template_embeddings:
            template_embedding = _template_embeddings[template.id]
        else:
            template_text = self._get_template_text(template)
            template_embedding = _embedding_model.encode(template_text)
            _template_embeddings[template.id] = template_embedding

        # Compute cosine similarity
        dot_product = np.dot(query_embedding, template_embedding)
        norm_query = np.linalg.norm(query_embedding)
        norm_template = np.linalg.norm(template_embedding)

        if norm_query == 0 or norm_template == 0:
            return 0.0

        similarity = dot_product / (norm_query * norm_template)

        # Convert from [-1, 1] to [0, 1] range
        return float((similarity + 1) / 2)

    def _compute_keyword_similarity(
        self,
        description: str,
        template: WorkflowTemplate,
    ) -> float:
        """Compute keyword-based similarity (fallback method).

        Args:
            description: User description
            template: Workflow template

        Returns:
            Similarity score between 0 and 1
        """
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


def get_template_recommender(
    embedding_service: EmbeddingService | None = None,
) -> TemplateRecommender:
    """Factory function to create a TemplateRecommender with EmbeddingService.

    If no embedding_service is provided, uses get_embedding_service() to create
    one based on application settings.

    Args:
        embedding_service: Optional EmbeddingService instance.
            If None, creates one from settings.

    Returns:
        TemplateRecommender configured with the embedding service

    Example:
        # Use default from settings
        recommender = get_template_recommender()

        # Use custom embedding service
        from mcp_server_langgraph.llm.embeddings import InMemoryEmbeddingService
        service = InMemoryEmbeddingService(dimensions=768)
        recommender = get_template_recommender(embedding_service=service)
    """
    if embedding_service is None:
        from mcp_server_langgraph.llm.embeddings import get_embedding_service

        embedding_service = get_embedding_service()

    return TemplateRecommender(embedding_service=embedding_service)
