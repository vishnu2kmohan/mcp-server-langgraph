"""TaskAnalyzer for heuristic task analysis.

Provides heuristics for analyzing tasks to help determine:
- Task complexity (simple, complicated, complex)
- Risk level (low, medium, high)
- Whether exploration is required
- Whether multi-step execution is needed
- Whether batch processing is appropriate
- Whether approval is required
- Estimated tool count
- Suggested execution mode

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


@dataclass
class TaskAnalysis:
    """Result of task analysis.

    Attributes:
        complexity: Task complexity level
        risk_level: Risk level for the task
        requires_exploration: Whether task needs exploration/search
        requires_multi_step: Whether task needs multiple sequential steps
        requires_batch_processing: Whether task involves bulk operations
        requires_approval: Whether task requires human approval
        estimated_tool_count: Estimated number of tools needed
        suggested_execution_mode: Suggested execution mode for the task
    """

    complexity: Literal["simple", "complicated", "complex"]
    risk_level: Literal["low", "medium", "high"]
    requires_exploration: bool
    requires_multi_step: bool
    requires_batch_processing: bool
    requires_approval: bool
    estimated_tool_count: int
    suggested_execution_mode: Literal["pure_llm", "tool_calling", "react", "programmatic", "orchestrator"]


class TaskAnalyzer:
    """Analyzes tasks using heuristics to determine execution characteristics.

    Uses keyword and pattern matching to estimate task properties
    that inform execution mode selection.
    """

    # Patterns for complexity detection
    SIMPLE_PATTERNS: list[str] = [
        r"\bwhat is\b",
        r"\bexplain\b",
        r"\bdefine\b",
        r"\blist\b",
        r"\bprint\b",
        r"\bhello\b",
        r"\b\d+\s*[\+\-\*\/]\s*\d+\b",  # Math expressions
    ]

    COMPLEX_PATTERNS: list[str] = [
        r"\bdistributed\b",
        r"\bscalable\b",
        r"\barchitecture\b",
        r"\bsystem design\b",
        r"\bmicroservices\b",
        r"\bfailover\b",
        r"\breplication\b",
        r"\bsharding\b",
        r"\bdesign and implement\b",
    ]

    # Patterns for exploration detection
    EXPLORATION_PATTERNS: list[str] = [
        r"\bfind\b",
        r"\bsearch\b",
        r"\binvestigate\b",
        r"\bexplore\b",
        r"\bdiscover\b",
        r"\blocate\b",
        r"\blook for\b",
        r"\bwhere\b.*\b(is|are)\b",
        r"\bwhy\b.*\b(is|are|does|do)\b",
    ]

    # Patterns for multi-step detection
    MULTI_STEP_PATTERNS: list[str] = [
        r"\bfirst\b.*\bthen\b",
        r"\bstep\s*\d+\b",
        r"\b\d+\.\s+\w+",  # Numbered steps
        r"\bfinally\b",
        r"\bafterward\b",
        r"\bnext\b",
        r"\bfollowed by\b",
    ]

    # Patterns for batch processing detection
    BATCH_PATTERNS: list[str] = [
        r"\ball\b.*\b(files|records|items|entries|users|documents)\b",
        r"\bbulk\b",
        r"\bbatch\b",
        r"\b\d{2,}\s+(records|files|items|entries)\b",  # Many items
        r"\bevery\b.*\b(file|record|item)\b",
        r"\beach\b.*\b(file|record|item)\b",
        r"\brename all\b",
        r"\bupdate all\b",
        r"\bdelete all\b",
    ]

    # Patterns for high risk detection
    HIGH_RISK_PATTERNS: list[str] = [
        r"\bdelete\b.*\b(all|database|user|data|production)\b",
        r"\bpermanently\b",
        r"\birreversible\b",
        r"\bproduction\b",
        r"\bdeploy\b",
        r"\bdrop\b.*\b(table|database)\b",
        r"\btruncate\b",
        r"\bformat\b.*\bdisk\b",
    ]

    MEDIUM_RISK_PATTERNS: list[str] = [
        r"\bupdate\b",
        r"\bmodify\b",
        r"\bchange\b",
        r"\bedit\b",
        r"\bwrite\b",
        r"\bcreate\b",
        r"\badd\b",
        r"\binstall\b",
    ]

    # Patterns for approval detection
    APPROVAL_PATTERNS: list[str] = [
        r"\bpermanently\b",
        r"\birreversible\b",
        r"\bsend\b.*\b(email|message|notification)\b.*\b(all|users|customers)\b",
        r"\bpublish\b",
        r"\bbroadcast\b",
        r"\bpay\b|\bpayment\b",
        r"\btransfer\b.*\b(money|funds)\b",
    ]

    # Tool-related keywords
    TOOL_KEYWORDS: dict[str, int] = {
        "file": 1,
        "read": 1,
        "write": 1,
        "search": 1,
        "find": 1,
        "database": 1,
        "api": 1,
        "http": 1,
        "parse": 1,
        "execute": 1,
        "run": 1,
        "create": 1,
        "delete": 1,
        "update": 1,
        "download": 1,
        "upload": 1,
    }

    def __init__(self) -> None:
        """Initialize the TaskAnalyzer with compiled patterns."""
        self._simple_re = [re.compile(p, re.IGNORECASE) for p in self.SIMPLE_PATTERNS]
        self._complex_re = [re.compile(p, re.IGNORECASE) for p in self.COMPLEX_PATTERNS]
        self._exploration_re = [re.compile(p, re.IGNORECASE) for p in self.EXPLORATION_PATTERNS]
        self._multi_step_re = [re.compile(p, re.IGNORECASE) for p in self.MULTI_STEP_PATTERNS]
        self._batch_re = [re.compile(p, re.IGNORECASE) for p in self.BATCH_PATTERNS]
        self._high_risk_re = [re.compile(p, re.IGNORECASE) for p in self.HIGH_RISK_PATTERNS]
        self._medium_risk_re = [re.compile(p, re.IGNORECASE) for p in self.MEDIUM_RISK_PATTERNS]
        self._approval_re = [re.compile(p, re.IGNORECASE) for p in self.APPROVAL_PATTERNS]

    def analyze(self, task_description: str) -> TaskAnalysis:
        """Analyze a task description and return heuristic analysis.

        Args:
            task_description: Natural language description of the task

        Returns:
            TaskAnalysis with heuristic estimates
        """
        complexity = self._detect_complexity(task_description)
        risk_level = self._detect_risk_level(task_description)
        requires_exploration = self._detect_exploration(task_description)
        requires_multi_step = self._detect_multi_step(task_description)
        requires_batch = self._detect_batch_processing(task_description)
        requires_approval = self._detect_approval_required(task_description, risk_level)
        tool_count = self._estimate_tool_count(task_description)

        # Determine suggested execution mode based on analysis
        execution_mode = self._suggest_execution_mode(
            complexity=complexity,
            risk_level=risk_level,
            requires_exploration=requires_exploration,
            requires_multi_step=requires_multi_step,
            requires_batch=requires_batch,
            tool_count=tool_count,
        )

        return TaskAnalysis(
            complexity=complexity,
            risk_level=risk_level,
            requires_exploration=requires_exploration,
            requires_multi_step=requires_multi_step,
            requires_batch_processing=requires_batch,
            requires_approval=requires_approval,
            estimated_tool_count=tool_count,
            suggested_execution_mode=execution_mode,
        )

    def _detect_complexity(self, text: str) -> Literal["simple", "complicated", "complex"]:
        """Detect task complexity based on patterns."""
        # Check for complex patterns first
        if any(pattern.search(text) for pattern in self._complex_re):
            return "complex"

        # Check for simple patterns
        if any(pattern.search(text) for pattern in self._simple_re):
            return "simple"

        # Default to complicated
        return "complicated"

    def _detect_risk_level(self, text: str) -> Literal["low", "medium", "high"]:
        """Detect risk level based on patterns."""
        # Check for high risk patterns
        if any(pattern.search(text) for pattern in self._high_risk_re):
            return "high"

        # Check for medium risk patterns
        if any(pattern.search(text) for pattern in self._medium_risk_re):
            return "medium"

        # Default to low risk
        return "low"

    def _detect_exploration(self, text: str) -> bool:
        """Detect if exploration/search is required."""
        return any(pattern.search(text) for pattern in self._exploration_re)

    def _detect_multi_step(self, text: str) -> bool:
        """Detect if multi-step execution is required."""
        return any(pattern.search(text) for pattern in self._multi_step_re)

    def _detect_batch_processing(self, text: str) -> bool:
        """Detect if batch processing is required."""
        return any(pattern.search(text) for pattern in self._batch_re)

    def _detect_approval_required(self, text: str, risk_level: str) -> bool:
        """Detect if approval is required.

        Approval is required for:
        - High risk operations with destructive potential
        - Operations that affect external systems/users
        """
        # Check explicit approval patterns
        if any(pattern.search(text) for pattern in self._approval_re):
            return True

        # High risk + delete/permanent = approval needed
        return risk_level == "high"

    def _estimate_tool_count(self, text: str) -> int:
        """Estimate the number of tools needed based on keywords."""
        text_lower = text.lower()
        count = 0
        matched_keywords: set[str] = set()

        for keyword, weight in self.TOOL_KEYWORDS.items():
            if keyword in text_lower and keyword not in matched_keywords:
                count += weight
                matched_keywords.add(keyword)

        return count

    def _suggest_execution_mode(
        self,
        complexity: str,
        risk_level: str,
        requires_exploration: bool,
        requires_multi_step: bool,
        requires_batch: bool,
        tool_count: int,
    ) -> Literal["pure_llm", "tool_calling", "react", "programmatic", "orchestrator"]:
        """Suggest the best execution mode based on analysis.

        Decision logic:
        - No tools needed → pure_llm
        - Complex + high risk → orchestrator
        - Requires exploration → react
        - Requires batch processing → programmatic
        - Simple with few tools → tool_calling
        - Default → tool_calling
        """
        # No tools = pure LLM response
        if tool_count == 0:
            return "pure_llm"

        # Complex tasks with high risk need orchestrator supervision
        if complexity == "complex" and risk_level == "high":
            return "orchestrator"

        # Complex multi-step tasks need orchestrator
        if complexity == "complex" and requires_multi_step:
            return "orchestrator"

        # Exploration tasks benefit from ReACT reasoning
        if requires_exploration:
            return "react"

        # Multi-step without exploration → react for reasoning loop
        if requires_multi_step:
            return "react"

        # Batch processing is best done programmatically
        if requires_batch:
            return "programmatic"

        # Default to tool calling for standard tasks
        return "tool_calling"
