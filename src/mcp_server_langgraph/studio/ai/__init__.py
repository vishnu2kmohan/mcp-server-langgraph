"""
Studio AI Module

Provides AI-powered assistance for workflow development:
- Workflow suggestions
- Template recommendations
- Node configuration assistance
"""

from .node_config import NodeConfigAssistant, NodeTypeRegistry
from .suggestions import Suggestion, WorkflowSuggestionAgent
from .templates import TemplateRecommender, WorkflowTemplate

__all__ = [
    # Suggestions
    "WorkflowSuggestionAgent",
    "Suggestion",
    # Templates
    "TemplateRecommender",
    "WorkflowTemplate",
    # Node Config
    "NodeConfigAssistant",
    "NodeTypeRegistry",
]
