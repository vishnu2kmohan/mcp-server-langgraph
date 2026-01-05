#!/usr/bin/env python3
"""
OpenFGA Model Inheritance Analyzer.

Analyzes the OpenFGA model to identify relation inheritance patterns and
potential "inheritance gaps" that could cause authorization bugs.

An "inheritance gap" occurs when:
1. A type has a higher-privilege relation (e.g., 'admin')
2. The type also has a lower-privilege relation (e.g., 'user')
3. The lower-privilege relation is NOT computed from the higher-privilege relation
4. This can cause authorization bugs when endpoints require the lower-privilege relation

Example (the ai:suggestions bug):
- The 'ai' type has 'admin' and 'user' relations
- 'viewer' is computed from both 'admin' and 'user'
- BUT 'user' is NOT computed from 'admin'
- Endpoints requiring 'user' relation DENY admin users unless explicit tuples exist

Usage:
    python scripts/validation/analyze_openfga_inheritance.py

    # With verbose output
    python scripts/validation/analyze_openfga_inheritance.py --verbose

    # JSON output for CI
    python scripts/validation/analyze_openfga_inheritance.py --json

    # Check specific type
    python scripts/validation/analyze_openfga_inheritance.py --type ai

Reference: ADR-0091 (API Response Transformation Strategy)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RelationInfo:
    """Information about a single relation in a type."""

    name: str
    is_direct: bool  # Can be directly assigned via tuples
    computed_from: list[str] = field(default_factory=list)  # Relations it inherits from
    computes_to: list[str] = field(default_factory=list)  # Relations that inherit from this


@dataclass
class TypeAnalysis:
    """Analysis of a single type's relations and inheritance."""

    type_name: str
    relations: dict[str, RelationInfo] = field(default_factory=dict)
    inheritance_gaps: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class InheritanceGap:
    """Describes a potential inheritance gap that could cause authorization bugs."""

    type_name: str
    higher_privilege: str
    lower_privilege: str
    severity: str  # "high", "medium", "low"
    description: str
    recommendation: str


# =============================================================================
# Constants
# =============================================================================

# Common privilege hierarchies (higher → lower)
# If a type has these relations, we expect the higher to compute to the lower
EXPECTED_HIERARCHIES = [
    ("owner", "admin"),
    ("owner", "editor"),
    ("owner", "viewer"),
    ("owner", "user"),
    ("admin", "editor"),
    ("admin", "viewer"),
    ("admin", "user"),  # This is the gap that caused the ai:suggestions bug
    ("editor", "viewer"),
    ("user", "viewer"),
]


# =============================================================================
# Parsing Functions
# =============================================================================


def get_project_root() -> Path:
    """Get the project root directory."""
    # scripts/validation/analyze_openfga_inheritance.py -> scripts/validation -> scripts -> root
    return Path(__file__).parent.parent.parent


def load_openfga_model(model_path: Path | None = None) -> dict[str, Any]:
    """Load the OpenFGA model.json."""
    if model_path is None:
        model_path = get_project_root() / "config" / "openfga" / "model.json"

    if not model_path.exists():
        raise FileNotFoundError(f"OpenFGA model not found at {model_path}")

    with model_path.open() as f:
        return json.load(f)


def parse_relation_definition(relation_def: dict[str, Any]) -> RelationInfo:
    """
    Parse a relation definition from the OpenFGA model.

    Returns:
        RelationInfo with computed_from and is_direct populated.
    """
    computed_from: list[str] = []
    is_direct = False

    # Check for direct assignment
    if "this" in relation_def:
        is_direct = True

    # Check for union (multiple sources)
    if "union" in relation_def:
        for child in relation_def["union"].get("child", []):
            if "this" in child:
                is_direct = True
            if "computedUserset" in child:
                computed_relation = child["computedUserset"].get("relation")
                if computed_relation:
                    computed_from.append(computed_relation)

    # Check for simple computedUserset
    if "computedUserset" in relation_def:
        computed_relation = relation_def["computedUserset"].get("relation")
        if computed_relation:
            computed_from.append(computed_relation)

    return RelationInfo(
        name="",  # Will be set by caller
        is_direct=is_direct,
        computed_from=computed_from,
    )


def analyze_type(type_def: dict[str, Any]) -> TypeAnalysis:
    """
    Analyze a single type definition for inheritance patterns.

    Returns:
        TypeAnalysis with relations and inheritance gaps.
    """
    type_name = type_def.get("type", "")
    description = type_def.get("description", "")
    relations_def = type_def.get("relations", {})

    analysis = TypeAnalysis(type_name=type_name, description=description)

    # Parse each relation
    for rel_name, rel_def in relations_def.items():
        rel_info = parse_relation_definition(rel_def)
        rel_info.name = rel_name
        analysis.relations[rel_name] = rel_info

    # Build reverse mapping (computes_to)
    for rel_name, rel_info in analysis.relations.items():
        for computed_from in rel_info.computed_from:
            if computed_from in analysis.relations:
                analysis.relations[computed_from].computes_to.append(rel_name)

    return analysis


def find_inheritance_gaps(analysis: TypeAnalysis) -> list[InheritanceGap]:
    """
    Find potential inheritance gaps in a type's relations.

    An inheritance gap occurs when a higher-privilege relation doesn't
    compute to a lower-privilege relation as expected.

    Returns:
        List of InheritanceGap describing potential issues.
    """
    gaps: list[InheritanceGap] = []

    for higher, lower in EXPECTED_HIERARCHIES:
        # Check if both relations exist in this type
        if higher not in analysis.relations or lower not in analysis.relations:
            continue

        # Check if lower is computed from higher (directly or transitively)
        if not _is_computed_transitively(higher, lower, analysis.relations):
            # This is a potential gap
            severity = _determine_severity(higher, lower)
            gaps.append(
                InheritanceGap(
                    type_name=analysis.type_name,
                    higher_privilege=higher,
                    lower_privilege=lower,
                    severity=severity,
                    description=(
                        f"'{lower}' is NOT computed from '{higher}'. "
                        f"Users with '{higher}' relation will be DENIED access to "
                        f"endpoints requiring '{lower}' relation."
                    ),
                    recommendation=(
                        f"Add explicit '{lower}' tuples for users who have '{higher}' relation, "
                        f"OR modify the model to compute '{lower}' from '{higher}'."
                    ),
                )
            )

    return gaps


def _is_computed_transitively(
    from_relation: str,
    to_relation: str,
    relations: dict[str, RelationInfo],
    max_depth: int = 5,
) -> bool:
    """
    Check if to_relation is computed from from_relation (transitively).

    Returns:
        True if there's an inheritance path from from_relation to to_relation.
    """
    if from_relation == to_relation:
        return True

    # BFS to find path
    visited: set[str] = set()
    queue = [to_relation]

    while queue and len(visited) < max_depth * 10:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        rel_info = relations.get(current)
        if rel_info:
            for computed_from in rel_info.computed_from:
                if computed_from == from_relation:
                    return True
                if computed_from not in visited:
                    queue.append(computed_from)

    return False


def _determine_severity(higher: str, lower: str) -> str:
    """Determine severity of an inheritance gap."""
    # admin not inheriting user is high severity (caused real bugs)
    if higher == "admin" and lower == "user":
        return "high"
    # Owner not inheriting anything is medium
    if higher == "owner":
        return "medium"
    # Other gaps are low severity
    return "low"


# =============================================================================
# Analysis Functions
# =============================================================================


def analyze_model(model: dict[str, Any]) -> tuple[list[TypeAnalysis], list[InheritanceGap]]:
    """
    Analyze the entire OpenFGA model.

    Returns:
        Tuple of (type_analyses, all_gaps)
    """
    type_analyses: list[TypeAnalysis] = []
    all_gaps: list[InheritanceGap] = []

    for type_def in model.get("type_definitions", []):
        analysis = analyze_type(type_def)
        type_analyses.append(analysis)

        gaps = find_inheritance_gaps(analysis)
        all_gaps.extend(gaps)

    return type_analyses, all_gaps


def generate_text_report(
    type_analyses: list[TypeAnalysis],
    gaps: list[InheritanceGap],
    verbose: bool = False,
) -> str:
    """Generate a human-readable text report."""
    lines: list[str] = []

    lines.append("=" * 80)
    lines.append("OpenFGA Model Inheritance Analysis Report")
    lines.append("=" * 80)
    lines.append("")

    # Summary
    lines.append(f"Total types analyzed: {len(type_analyses)}")
    lines.append(f"Inheritance gaps found: {len(gaps)}")
    high_gaps = [g for g in gaps if g.severity == "high"]
    medium_gaps = [g for g in gaps if g.severity == "medium"]
    low_gaps = [g for g in gaps if g.severity == "low"]
    lines.append(f"  - High severity: {len(high_gaps)}")
    lines.append(f"  - Medium severity: {len(medium_gaps)}")
    lines.append(f"  - Low severity: {len(low_gaps)}")
    lines.append("")

    # High severity gaps (require explicit tuples)
    if high_gaps:
        lines.append("-" * 80)
        lines.append("HIGH SEVERITY GAPS (Require explicit tuples)")
        lines.append("-" * 80)
        for gap in high_gaps:
            lines.append("")
            lines.append(f"Type: {gap.type_name}")
            lines.append(f"  Gap: {gap.higher_privilege} → {gap.lower_privilege}")
            lines.append(f"  Issue: {gap.description}")
            lines.append(f"  Fix: {gap.recommendation}")
        lines.append("")

    # Medium/Low severity gaps (informational)
    if (medium_gaps or low_gaps) and verbose:
        lines.append("-" * 80)
        lines.append("MEDIUM/LOW SEVERITY GAPS (Informational)")
        lines.append("-" * 80)
        for gap in medium_gaps + low_gaps:
            lines.append(f"  [{gap.severity.upper()}] {gap.type_name}: {gap.higher_privilege} → {gap.lower_privilege}")
        lines.append("")

    # Verbose: Type details
    if verbose:
        lines.append("-" * 80)
        lines.append("TYPE DETAILS")
        lines.append("-" * 80)
        for analysis in type_analyses:
            if not analysis.relations:
                continue
            lines.append("")
            lines.append(f"Type: {analysis.type_name}")
            if analysis.description:
                lines.append(f"  Description: {analysis.description}")
            lines.append("  Relations:")
            for rel_name, rel_info in analysis.relations.items():
                direct_marker = "[direct]" if rel_info.is_direct else "[computed]"
                if rel_info.computed_from:
                    computed_str = f" ← {', '.join(rel_info.computed_from)}"
                else:
                    computed_str = ""
                lines.append(f"    - {rel_name} {direct_marker}{computed_str}")
        lines.append("")

    # Reference
    lines.append("-" * 80)
    lines.append("Reference: ADR-0091 (API Response Transformation Strategy)")
    lines.append("The 'ai:suggestions' bug was caused by admin having 'admin' relation")
    lines.append("but the WebSocket requiring 'user' relation (not computed from admin).")
    lines.append("-" * 80)

    return "\n".join(lines)


def generate_json_report(
    type_analyses: list[TypeAnalysis],
    gaps: list[InheritanceGap],
) -> dict[str, Any]:
    """Generate a JSON report for CI integration."""
    return {
        "summary": {
            "total_types": len(type_analyses),
            "total_gaps": len(gaps),
            "high_severity_gaps": len([g for g in gaps if g.severity == "high"]),
            "medium_severity_gaps": len([g for g in gaps if g.severity == "medium"]),
            "low_severity_gaps": len([g for g in gaps if g.severity == "low"]),
        },
        "gaps": [
            {
                "type": gap.type_name,
                "higher_privilege": gap.higher_privilege,
                "lower_privilege": gap.lower_privilege,
                "severity": gap.severity,
                "description": gap.description,
                "recommendation": gap.recommendation,
            }
            for gap in gaps
        ],
        "types": [
            {
                "name": analysis.type_name,
                "description": analysis.description,
                "relations": {
                    name: {
                        "is_direct": info.is_direct,
                        "computed_from": info.computed_from,
                        "computes_to": info.computes_to,
                    }
                    for name, info in analysis.relations.items()
                },
            }
            for analysis in type_analyses
            if analysis.relations
        ],
    }


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze OpenFGA model for inheritance gaps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed type information",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON for CI integration",
    )
    parser.add_argument(
        "--type",
        "-t",
        dest="filter_type",
        help="Only analyze specific type(s), comma-separated",
    )
    parser.add_argument(
        "--model-path",
        type=Path,
        help="Path to model.json (default: config/openfga/model.json)",
    )
    parser.add_argument(
        "--fail-on-high",
        action="store_true",
        help="Exit with error code if high severity gaps found",
    )

    args = parser.parse_args()

    try:
        model = load_openfga_model(args.model_path)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    type_analyses, gaps = analyze_model(model)

    # Filter by type if requested
    if args.filter_type:
        filter_types = set(args.filter_type.split(","))
        type_analyses = [a for a in type_analyses if a.type_name in filter_types]
        gaps = [g for g in gaps if g.type_name in filter_types]

    # Generate report
    if args.json:
        report = generate_json_report(type_analyses, gaps)
        print(json.dumps(report, indent=2))
    else:
        report = generate_text_report(type_analyses, gaps, verbose=args.verbose)
        print(report)

    # Check for failure condition
    if args.fail_on_high:
        high_gaps = [g for g in gaps if g.severity == "high"]
        if high_gaps:
            print(f"\nERROR: Found {len(high_gaps)} high severity inheritance gaps", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
