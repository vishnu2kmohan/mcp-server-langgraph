"""
Artifact Name Generator Module

Generates machine-friendly programmatic names for artifacts based on their content.
Uses heuristics to extract meaningful names from code, diagrams, and other content types.
Falls back to LLM when heuristics fail or for complex content.

Uses LLMFactory for resilient LLM calls with SOLID compliance:
- Circuit breaker, retry, timeout, bulkhead patterns
- Dependency injection for testability
"""

import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.llm.factory import LLMFactory

logger = logging.getLogger(__name__)


class ArtifactNameGenerator:
    """Generates programmatic names for artifacts from their content.

    Uses content analysis and heuristics to extract meaningful names
    (function names, class names, diagram titles, etc.).

    Example:
        generator = ArtifactNameGenerator()
        name = await generator.generate(
            content="def calculate_total(items): ...",
            content_type="code",
            language="python",
        )
        # Returns: "calculate_total"
    """

    def __init__(
        self,
        model_name: str = "gemini-2.0-flash",
        max_name_length: int = 64,
        enable_llm: bool = True,
        llm_factory: "LLMFactory | None" = None,
    ) -> None:
        """Initialize the artifact name generator.

        Args:
            model_name: The LLM model to use (fast model recommended)
            max_name_length: Maximum length of generated name
            enable_llm: Whether to use LLM (set False for testing/heuristics only)
            llm_factory: Optional LLMFactory for dependency injection.
                         If not provided, will be lazily initialized from settings.
        """
        self.model_name = model_name
        self.max_name_length = max_name_length
        self.enable_llm = enable_llm
        self._llm_factory = llm_factory

    def _get_llm_factory(self) -> Any:
        """Get or create the LLM factory (lazy initialization).

        Returns:
            LLMFactory instance with resilience patterns.
        """
        if self._llm_factory is None:
            from mcp_server_langgraph.core.config import settings
            from mcp_server_langgraph.llm.factory import create_llm_from_config

            self._llm_factory = create_llm_from_config(settings)
        return self._llm_factory

    async def generate(
        self,
        content: str,
        content_type: str,
        language: str | None = None,
    ) -> str:
        """Generate a name from the artifact content.

        Args:
            content: The artifact content
            content_type: Type of content (code, mermaid, svg, json, etc.)
            language: Programming language (for code content)

        Returns:
            A machine-friendly programmatic name
        """
        if not content or not content.strip():
            return self._default_name(content_type)

        # Try heuristics first (faster, more deterministic)
        heuristic_name = self._generate_heuristic_name(content, content_type, language)
        if heuristic_name:
            return self._sanitize_name(heuristic_name)

        # Try LLM if enabled and heuristics failed
        if self.enable_llm:
            try:
                llm_name = await self._generate_with_llm(content, content_type, language)
                if llm_name:
                    return self._sanitize_name(llm_name)
            except Exception as e:
                logger.debug("LLM name generation failed: %s", e)

        return self._default_name(content_type)

    def _generate_heuristic_name(
        self,
        content: str,
        content_type: str,
        language: str | None = None,
    ) -> str | None:
        """Generate name using content-specific heuristics.

        Args:
            content: The artifact content
            content_type: Type of content
            language: Programming language

        Returns:
            Extracted name or None
        """
        content_type_lower = content_type.lower()

        if content_type_lower == "code":
            return self._extract_code_name(content, language)
        elif content_type_lower == "mermaid":
            return self._extract_mermaid_name(content)
        elif content_type_lower == "svg":
            return self._extract_svg_name(content)
        elif content_type_lower == "json":
            return self._extract_json_name(content)
        elif content_type_lower == "markdown":
            return self._extract_markdown_name(content)
        elif content_type_lower == "html":
            return self._extract_html_name(content)

        return None

    def _extract_code_name(self, content: str, language: str | None) -> str | None:
        """Extract name from code content.

        Looks for:
        - Function definitions
        - Class definitions
        - Exported constants
        - Module-level constants

        Args:
            content: The code content
            language: Programming language

        Returns:
            Extracted name or None
        """
        lang = (language or "").lower()

        # Python patterns
        if lang in ("python", "py", ""):
            # Class definition
            match = re.search(r"class\s+([A-Z][a-zA-Z0-9_]*)", content)
            if match:
                return self._camel_to_snake(match.group(1))

            # Function definition
            match = re.search(r"def\s+([a-z_][a-zA-Z0-9_]*)", content)
            if match:
                return match.group(1)

        # JavaScript/TypeScript patterns
        if lang in ("javascript", "typescript", "js", "ts", "jsx", "tsx", ""):
            # Exported const/function (React components, etc.)
            match = re.search(r"export\s+(?:const|function|class)\s+([A-Z][a-zA-Z0-9_]*)", content)
            if match:
                return self._camel_to_snake(match.group(1))

            # const arrow function
            match = re.search(r"const\s+([A-Z][a-zA-Z0-9_]*)\s*=", content)
            if match:
                return self._camel_to_snake(match.group(1))

            # Function declaration
            match = re.search(r"function\s+([a-zA-Z_][a-zA-Z0-9_]*)", content)
            if match:
                name = match.group(1)
                if name[0].isupper():
                    return self._camel_to_snake(name)
                return name

            # Class definition
            match = re.search(r"class\s+([A-Z][a-zA-Z0-9_]*)", content)
            if match:
                return self._camel_to_snake(match.group(1))

        # Go patterns
        if lang in ("go", "golang", ""):
            match = re.search(r"func\s+(?:\([^)]+\)\s+)?([A-Z][a-zA-Z0-9_]*)", content)
            if match:
                return self._camel_to_snake(match.group(1))

            match = re.search(r"type\s+([A-Z][a-zA-Z0-9_]*)\s+struct", content)
            if match:
                return self._camel_to_snake(match.group(1))

        # Rust patterns
        if lang in ("rust", "rs", ""):
            match = re.search(r"(?:pub\s+)?fn\s+([a-z_][a-z0-9_]*)", content)
            if match:
                return match.group(1)

            match = re.search(r"(?:pub\s+)?struct\s+([A-Z][a-zA-Z0-9_]*)", content)
            if match:
                return self._camel_to_snake(match.group(1))

        return None

    def _extract_mermaid_name(self, content: str) -> str | None:
        """Extract name from Mermaid diagram.

        Args:
            content: Mermaid diagram content

        Returns:
            Extracted name or None
        """
        # Look for title directive
        match = re.search(r"title\s*:\s*(.+)", content, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            return self._title_to_snake(title)

        # Identify diagram type
        first_line = content.strip().split("\n")[0].lower()
        if "flowchart" in first_line or "graph" in first_line:
            return "flowchart"
        elif "sequencediagram" in first_line or "sequence" in first_line:
            return "sequence_diagram"
        elif "classDiagram" in content.lower():
            return "class_diagram"
        elif "erdiagram" in first_line or "er diagram" in first_line:
            return "er_diagram"
        elif "gantt" in first_line:
            return "gantt_chart"
        elif "pie" in first_line:
            return "pie_chart"
        elif "statediagram" in first_line:
            return "state_diagram"

        return "diagram"

    def _extract_svg_name(self, content: str) -> str | None:
        """Extract name from SVG content.

        Args:
            content: SVG content

        Returns:
            Extracted name or None
        """
        # Look for title element
        match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            return self._title_to_snake(title)

        # Look for aria-label
        match = re.search(r'aria-label\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            return self._title_to_snake(match.group(1))

        return "svg_graphic"

    def _extract_json_name(self, content: str) -> str | None:
        """Extract name from JSON content.

        Args:
            content: JSON content

        Returns:
            Extracted name or None
        """
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                # Look for common name fields
                for key in ("name", "title", "id", "type", "$schema"):
                    if key in data and isinstance(data[key], str):
                        value = data[key]
                        # For schema URLs, extract the name
                        if key == "$schema" and "/" in value:
                            value = value.split("/")[-1].replace(".json", "")
                        return self._title_to_snake(value)

                # Use first key as identifier
                if data:
                    first_key = next(iter(data.keys()))
                    return self._title_to_snake(first_key) + "_config"

        except json.JSONDecodeError:
            pass

        return "json_data"

    def _extract_markdown_name(self, content: str) -> str | None:
        """Extract name from Markdown content.

        Args:
            content: Markdown content

        Returns:
            Extracted name or None
        """
        # Look for first heading
        match = re.search(r"^#{1,6}\s+(.+)$", content, re.MULTILINE)
        if match:
            return self._title_to_snake(match.group(1))

        return "document"

    def _extract_html_name(self, content: str) -> str | None:
        """Extract name from HTML content.

        Args:
            content: HTML content

        Returns:
            Extracted name or None
        """
        # Look for title tag
        match = re.search(r"<title[^>]*>([^<]+)</title>", content, re.IGNORECASE)
        if match:
            return self._title_to_snake(match.group(1))

        # Look for first h1
        match = re.search(r"<h1[^>]*>([^<]+)</h1>", content, re.IGNORECASE)
        if match:
            return self._title_to_snake(match.group(1))

        return "html_page"

    async def _generate_with_llm(
        self,
        content: str,
        content_type: str,
        language: str | None = None,
    ) -> str:
        """Generate name using LLM via LLMFactory with resilience patterns.

        Uses LLMFactory for circuit breaker, retry, timeout, and bulkhead
        patterns (SOLID compliance - ADR-0026).

        Args:
            content: The artifact content
            content_type: Type of content
            language: Programming language

        Returns:
            Generated name string
        """
        from langchain_core.messages import HumanMessage

        # Truncate very long content
        truncated = content[:1000] if len(content) > 1000 else content

        lang_hint = f" ({language})" if language else ""

        prompt = f"""Generate a short, machine-friendly programmatic name for this {content_type}{lang_hint} artifact:

```
{truncated}
```

Rules:
- Use snake_case (e.g., "user_authentication", "calculate_total")
- Be concise (1-4 words, max 64 characters)
- Capture the main purpose or entity
- No file extensions
- Return ONLY the name, nothing else

Name:"""

        # Use LLMFactory for resilient LLM calls
        factory = self._get_llm_factory()
        messages = [HumanMessage(content=prompt)]

        response = await factory.ainvoke(
            messages,
            temperature=0.2,
            max_tokens=30,
        )

        result = response.content
        return result.strip() if result else ""

    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case.

        Args:
            name: CamelCase name

        Returns:
            snake_case name
        """
        # Insert underscore before uppercase letters
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _title_to_snake(self, title: str) -> str:
        """Convert a title to snake_case.

        Args:
            title: Human-readable title

        Returns:
            snake_case name
        """
        # Remove special characters, keep alphanumeric and spaces
        clean = re.sub(r"[^\w\s]", "", title)
        # Replace spaces with underscores and lowercase
        return re.sub(r"\s+", "_", clean.strip()).lower()

    def _sanitize_name(self, name: str) -> str:
        """Clean and truncate the name.

        Args:
            name: Raw name string

        Returns:
            Sanitized name
        """
        # Remove quotes and extra whitespace
        name = name.strip().strip("\"'`")

        # Replace spaces with underscores
        name = re.sub(r"\s+", "_", name)

        # Remove non-alphanumeric except underscore
        name = re.sub(r"[^\w]", "", name)

        # Ensure starts with letter or underscore
        if name and name[0].isdigit():
            name = "_" + name

        # Truncate to max length
        if len(name) > self.max_name_length:
            # Try to break at underscore
            truncated = name[: self.max_name_length]
            last_underscore = truncated.rfind("_")
            if last_underscore > 10:
                truncated = truncated[:last_underscore]
            name = truncated

        return name if name else "untitled"

    def _default_name(self, content_type: str) -> str:
        """Return a default name based on content type.

        Args:
            content_type: Type of content

        Returns:
            Default name
        """
        defaults = {
            "code": "untitled_code",
            "mermaid": "diagram",
            "svg": "graphic",
            "json": "data",
            "markdown": "document",
            "html": "page",
            "text": "text",
            "chart": "chart",
            "table": "table",
        }
        return defaults.get(content_type.lower(), "untitled")


# Singleton instance
_name_generator: ArtifactNameGenerator | None = None


def get_artifact_name_generator() -> ArtifactNameGenerator:
    """Get the singleton artifact name generator instance."""
    global _name_generator  # noqa: PLW0603
    if _name_generator is None:
        _name_generator = ArtifactNameGenerator()
    return _name_generator


async def generate_artifact_name(
    content: str,
    content_type: str,
    language: str | None = None,
) -> str:
    """Generate an artifact name from content.

    Convenience function that uses the singleton generator.

    Args:
        content: The artifact content
        content_type: Type of content (code, mermaid, svg, json, etc.)
        language: Programming language (for code content)

    Returns:
        Generated name string
    """
    generator = get_artifact_name_generator()
    return await generator.generate(content, content_type, language)
