#!/usr/bin/env python3
"""
Test suite for Mermaid diagram validation.

This test suite follows TDD principles to ensure Mermaid syntax errors
are caught by validators, preventing invalid diagrams from being deployed.

Tests cover:
1. Sequence diagram validation (classDef/class are invalid in sequence diagrams)
2. Basic mermaid syntax validation (mismatched subgraph/end)
"""

import gc
import sys
from pathlib import Path

import pytest

# Add scripts/validators directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "validators"))

# Mark this as both unit and meta test to ensure it runs in CI
pytestmark = [pytest.mark.unit, pytest.mark.meta]


# Import will fail until we implement the functions - that's expected in TDD RED phase
try:
    from check_mermaid_styling import (
        has_invalid_sequence_directives,
        is_flowchart_diagram,
        is_sequence_diagram,
        validate_mermaid_syntax,
    )
except ImportError:
    # Functions don't exist yet - this is expected in RED phase
    has_invalid_sequence_directives = None
    validate_mermaid_syntax = None
    is_sequence_diagram = None
    is_flowchart_diagram = None


@pytest.mark.xdist_group(name="test_sequence_diagram_validation")
class TestSequenceDiagramValidation:
    """Test validation of sequence diagram directives."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(has_invalid_sequence_directives is None, reason="Function not implemented yet")
    def test_sequence_diagram_with_classdef_is_invalid(self):
        """Sequence diagrams should not contain classDef directives."""
        block = """
sequenceDiagram
    participant A
    participant B
    A->>B: Hello
    classDef foo fill:#8dd3c7
"""
        is_valid, error = has_invalid_sequence_directives(block)
        assert not is_valid
        assert error is not None
        assert "classDef" in error

    @pytest.mark.skipif(has_invalid_sequence_directives is None, reason="Function not implemented yet")
    def test_sequence_diagram_with_class_assignment_is_invalid(self):
        """Sequence diagrams should not contain class assignments."""
        block = """
sequenceDiagram
    participant User
    participant App
    User->>App: Request
    App-->>User: Response

    class User clientStyle
    class App serverStyle
"""
        is_valid, error = has_invalid_sequence_directives(block)
        assert not is_valid
        assert error is not None
        assert "class" in error.lower()

    @pytest.mark.skipif(has_invalid_sequence_directives is None, reason="Function not implemented yet")
    def test_sequence_diagram_with_both_classdef_and_class_is_invalid(self):
        """Sequence diagrams should not contain either classDef or class directives."""
        block = """
%% ColorBrewer2 Set3 palette - each component type uniquely colored
%%{init: {'theme':'base', 'themeVariables': {'actorBkg':'#8dd3c7'}}}%%
sequenceDiagram
    participant User
    participant App
    User->>App: Request

    classDef clientStyle fill:#8dd3c7,stroke:#2a9d8f
    class User clientStyle
"""
        is_valid, error = has_invalid_sequence_directives(block)
        assert not is_valid
        assert error is not None

    @pytest.mark.skipif(has_invalid_sequence_directives is None, reason="Function not implemented yet")
    def test_sequence_diagram_without_classdef_is_valid(self):
        """Sequence diagrams without classDef/class are valid."""
        block = """
%% ColorBrewer2 Set3 palette - each component type uniquely colored
%%{init: {'theme':'base', 'themeVariables': {'actorBkg':'#8dd3c7'}}}%%
sequenceDiagram
    participant User
    participant App
    User->>App: Request
    App-->>User: Response
"""
        is_valid, error = has_invalid_sequence_directives(block)
        assert is_valid
        assert error is None

    @pytest.mark.skipif(has_invalid_sequence_directives is None, reason="Function not implemented yet")
    def test_flowchart_with_classdef_is_valid(self):
        """Flowcharts can use classDef directives - they should pass validation."""
        block = """
flowchart TD
    A[Start] --> B[End]
    classDef foo fill:#8dd3c7,stroke:#2a9d8f
    class A foo
"""
        is_valid, error = has_invalid_sequence_directives(block)
        assert is_valid
        assert error is None

    @pytest.mark.skipif(has_invalid_sequence_directives is None, reason="Function not implemented yet")
    def test_non_sequence_diagram_skips_validation(self):
        """Non-sequence diagrams should skip this validation."""
        block = """
graph TD
    A --> B
    classDef foo fill:#8dd3c7
    class A foo
"""
        is_valid, error = has_invalid_sequence_directives(block)
        assert is_valid  # Should pass because it's not a sequence diagram
        assert error is None


@pytest.mark.xdist_group(name="test_mermaid_syntax_validation")
class TestMermaidSyntaxValidation:
    """Test basic mermaid syntax validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(validate_mermaid_syntax is None, reason="Function not implemented yet")
    def test_mismatched_subgraph_end_is_invalid(self):
        """Detect mismatched subgraph/end counts."""
        block = """
flowchart TD
    subgraph Layer1
        A --> B
    subgraph Layer2
        C --> D
    end
"""
        # Missing one 'end' - should be invalid
        is_valid, error = validate_mermaid_syntax(block)
        assert not is_valid
        assert error is not None
        assert "subgraph" in error.lower() or "end" in error.lower()

    @pytest.mark.skipif(validate_mermaid_syntax is None, reason="Function not implemented yet")
    def test_matched_subgraph_end_is_valid(self):
        """Properly matched subgraph/end should pass."""
        block = """
flowchart TD
    subgraph Layer1
        A --> B
    end
    subgraph Layer2
        C --> D
    end
"""
        is_valid, error = validate_mermaid_syntax(block)
        assert is_valid
        assert error is None

    @pytest.mark.skipif(validate_mermaid_syntax is None, reason="Function not implemented yet")
    def test_nested_subgraph_is_valid(self):
        """Nested subgraphs with proper end counts should pass."""
        block = """
flowchart TD
    subgraph Outer
        subgraph Inner
            A --> B
        end
        C --> D
    end
"""
        is_valid, error = validate_mermaid_syntax(block)
        assert is_valid
        assert error is None

    @pytest.mark.skipif(validate_mermaid_syntax is None, reason="Function not implemented yet")
    def test_simple_flowchart_without_subgraph_is_valid(self):
        """Simple flowcharts without subgraphs should pass."""
        block = """
flowchart TD
    A[Start] --> B[Process]
    B --> C[End]
"""
        is_valid, error = validate_mermaid_syntax(block)
        assert is_valid
        assert error is None

    @pytest.mark.skipif(validate_mermaid_syntax is None, reason="Function not implemented yet")
    def test_sequence_diagram_skips_subgraph_validation(self):
        """Sequence diagrams don't use subgraph, so should skip this validation."""
        block = """
sequenceDiagram
    participant A
    A->>B: Hello
"""
        is_valid, error = validate_mermaid_syntax(block)
        assert is_valid  # Should pass because sequence diagrams don't use subgraph
        assert error is None


@pytest.mark.xdist_group(name="test_diagram_type_detection")
class TestDiagramTypeDetection:
    """Test diagram type detection functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(is_sequence_diagram is None, reason="Function not imported")
    def test_detects_sequence_diagram(self):
        """Detect sequence diagrams correctly."""
        block = """
sequenceDiagram
    participant A
    A->>B: Hello
"""
        assert is_sequence_diagram(block)

    @pytest.mark.skipif(is_sequence_diagram is None, reason="Function not imported")
    def test_detects_sequence_diagram_with_init(self):
        """Detect sequence diagrams that start with %%{init:...}%%."""
        block = """
%%{init: {'theme':'base'}}%%
sequenceDiagram
    participant A
    A->>B: Hello
"""
        assert is_sequence_diagram(block)

    @pytest.mark.skipif(is_sequence_diagram is None, reason="Function not imported")
    def test_flowchart_is_not_sequence_diagram(self):
        """Flowcharts should not be detected as sequence diagrams."""
        block = """
flowchart TD
    A --> B
"""
        assert not is_sequence_diagram(block)

    @pytest.mark.skipif(is_flowchart_diagram is None, reason="Function not imported")
    def test_detects_flowchart_diagram(self):
        """Detect flowchart diagrams correctly."""
        block = """
flowchart TD
    A --> B
"""
        assert is_flowchart_diagram(block)

    @pytest.mark.skipif(is_flowchart_diagram is None, reason="Function not imported")
    def test_detects_graph_as_flowchart(self):
        """Graph (deprecated) should be detected as flowchart for validation purposes."""
        block = """
graph TD
    A --> B
"""
        assert is_flowchart_diagram(block)


@pytest.mark.xdist_group(name="test_real_world_examples")
class TestRealWorldExamples:
    """Test cases based on actual errors found in the documentation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.skipif(has_invalid_sequence_directives is None, reason="Function not implemented yet")
    def test_terraform_aws_irsa_diagram_pattern(self):
        """Test the pattern found in terraform-aws.mdx IRSA diagram."""
        # This is the actual pattern from the terraform-aws.mdx file
        block = """
%% ColorBrewer2 Set3 palette - each component type uniquely colored
%%{init: {'theme':'base', 'themeVariables': { 'fontSize':'14px', 'primaryColor':'#8dd3c7','primaryTextColor':'#000','primaryBorderColor':'#555','lineColor':'#fb8072','secondaryColor':'#fdb462','tertiaryColor':'#bebada'}}}%%
sequenceDiagram
    participant Pod
    participant OIDC as EKS OIDC Provider
    participant STS as AWS STS
    participant SM as Secrets Manager

    Pod->>OIDC: Request credentials with service account token
    OIDC->>STS: Exchange token for temporary AWS credentials
    STS-->>OIDC: Return temporary credentials (15 min - 12 hrs)
    OIDC-->>Pod: Inject AWS credentials as environment variables
    Pod->>SM: Access secrets using temporary credentials
    SM-->>Pod: Return secret value

    classDef clientStyle fill:#8dd3c7,stroke:#5fa99d,stroke-width:2px,color:#333
    classDef validationStyle fill:#fdb462,stroke:#e8873f,stroke-width:2px,color:#333
    classDef serviceStyle fill:#bebada,stroke:#9b8ec7,stroke-width:2px,color:#333
    classDef storageStyle fill:#80b1d3,stroke:#5a91b8,stroke-width:2px,color:#333

    class Pod clientStyle
    class OIDC,STS validationStyle
    class SM storageStyle
"""
        is_valid, error = has_invalid_sequence_directives(block)
        assert not is_valid, "terraform-aws.mdx pattern should be detected as invalid"
        assert error is not None

    @pytest.mark.skipif(has_invalid_sequence_directives is None, reason="Function not implemented yet")
    def test_keycloak_sso_diagram_pattern(self):
        """Test the pattern found in keycloak-sso.mdx."""
        block = """
%% ColorBrewer2 Set3 palette - each component type uniquely colored
%%{init: {'theme':'base', 'themeVariables': {'actorBkg':'#8dd3c7','actorBorder':'#2a9d8f'}}}%%
sequenceDiagram
    participant User
    participant App as MCP Server
    participant KC as Keycloak

    User->>App: Request with credentials
    App->>KC: Authenticate (OIDC)
    KC-->>App: Access + Refresh tokens

    classDef clientStyle fill:#8dd3c7,stroke:#5fa99d,stroke-width:2px,color:#333
    class User clientStyle
"""
        is_valid, error = has_invalid_sequence_directives(block)
        assert not is_valid, "keycloak-sso.mdx pattern should be detected as invalid"
        assert error is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
