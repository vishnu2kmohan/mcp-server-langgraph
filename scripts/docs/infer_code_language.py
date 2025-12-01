#!/usr/bin/env python3
"""
Ultra-reliable language inference for MDX code blocks.

This module provides robust language detection for code blocks that are
missing language tags. It uses pattern matching on the first few lines
of code to determine the most likely language.

Design Principles:
1. Conservative - When uncertain, default to 'text'
2. Order matters - More specific patterns checked first
3. Multi-line analysis - Look at first 5-10 non-empty lines
4. No false positives - Better to miss than misclassify
"""

import re
from dataclasses import dataclass


@dataclass
class LanguageMatch:
    """Result of language inference."""

    language: str
    confidence: float  # 0.0 to 1.0
    reason: str


# Priority-ordered language patterns
# Each tuple: (language, patterns_list, description)
LANGUAGE_PATTERNS = [
    # === HIGHEST PRIORITY: Python (very common, must catch "from X import Y") ===
    (
        "python",
        [
            r"^#!/usr/bin/(env\s+)?python",
            r"^from\s+\w+(\.\w+)*\s+import\s",  # from X import Y (before Dockerfile FROM)
            r"^import\s+\w+",
            r"^(def|class|async\s+def)\s+\w+",
            r"^@(pytest|app|router|dataclass|property)",
            r"^if\s+__name__\s*==",
        ],
        "Python syntax",
    ),
    # === Dockerfile: Must be specific to avoid false positives ===
    (
        "dockerfile",
        [
            r"^FROM\s+[\w./-]+:\w+",  # FROM image:tag (requires colon for tag)
            r"^FROM\s+[\w./-]+\s+(AS|as)\s+\w+",  # FROM image AS builder
            r"^(RUN|COPY|CMD|ENTRYPOINT|WORKDIR|ENV|EXPOSE|ARG|LABEL|ADD|VOLUME|USER|HEALTHCHECK)\s",
        ],
        "Dockerfile commands",
    ),
    # === Other unique identifiers ===
    (
        "hcl",
        [
            r'^(resource|module|variable|output|provider|terraform|locals|data)\s+"',
            r"^\s*(resource|module|variable|output|provider)\s+\{",
            r'^(resource|data)\s+"[a-z_]+"\s+"[a-z_-]+"\s*\{',
        ],
        "Terraform/HCL blocks",
    ),
    (
        "sql",
        [
            r"^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE)\s",
            r"^\s*(SELECT|INSERT INTO|UPDATE|DELETE FROM)\s",
        ],
        "SQL statements",
    ),
    (
        "graphql",
        [
            r"^(query|mutation|subscription|fragment|type|interface|enum|input|scalar)\s",
            r"^\{[\s\n]*[a-zA-Z]+\s*\{",
        ],
        "GraphQL schema/queries",
    ),
    # === HIGH PRIORITY: Strong indicators ===
    (
        "go",
        [
            r"^package\s+\w+",
            r"^import\s+\(",
            r"^func\s+\w+",
            r"^type\s+\w+\s+(struct|interface)",
        ],
        "Go syntax",
    ),
    (
        "rust",
        [
            r"^(use|mod|pub|fn|impl|struct|enum|trait)\s",
            r"^#\[(derive|cfg|test|allow|warn)\]",
            r"^fn\s+\w+\s*\(",
        ],
        "Rust syntax",
    ),
    (
        "java",
        [
            r"^(public|private|protected)\s+(class|interface|enum)\s",
            r"^(public|private|protected)\s+(static\s+)?(void|int|String|boolean)\s",
            r"^package\s+[a-z]+\.[a-z.]+;",
            r"^import\s+java\.",
        ],
        "Java syntax",
    ),
    (
        "typescript",
        [
            r"^(interface|type|enum)\s+\w+",
            r"^(export\s+)?(interface|type)\s+",
            r":\s*(string|number|boolean|any)\s*[;=\)]",
            r"^import\s+.*\s+from\s+['\"]",
            r"<[A-Z]\w*>",  # Generic types
        ],
        "TypeScript syntax",
    ),
    (
        "javascript",
        [
            r"^(const|let|var)\s+\w+\s*=",
            r"^(function|async\s+function)\s+\w+",
            r"^(export\s+)?(default\s+)?(function|class|const)",
            r"^import\s+.*\s+from\s+['\"]",
            r"=>\s*\{",  # Arrow functions
        ],
        "JavaScript syntax",
    ),
    # === YAML: Very common in this codebase ===
    (
        "yaml",
        [
            r"^(apiVersion|kind|metadata|spec|name|labels|annotations):",
            r"^[a-zA-Z_][a-zA-Z0-9_-]*:\s*$",  # Key with no value (nested)
            r"^[a-zA-Z_][a-zA-Z0-9_-]*:\s+[^\s]",  # Key: value
            r"^\s*-\s+\w+:",  # List of objects
            r"^---\s*$",  # YAML document separator
        ],
        "YAML syntax",
    ),
    # === JSON ===
    (
        "json",
        [
            r'^\s*\{\s*"',
            r'^\s*\[\s*\{?\s*"',
            r'^\s*"[^"]+"\s*:\s*[\[{"\d]',
        ],
        "JSON syntax",
    ),
    # === TOML ===
    (
        "toml",
        [
            r"^\[[\w.-]+\]",  # [section]
            r'^\w+\s*=\s*"',  # key = "value"
            r"^\[\[[\w.-]+\]\]",  # [[array.of.tables]]
        ],
        "TOML syntax",
    ),
    # === Shell/Bash: Most common ===
    (
        "bash",
        [
            r"^#!/bin/(ba)?sh",
            r"^(export|source|alias)\s+\w+",
            r"^\$\s",  # $ command prompt
            r"^(gcloud|gsutil|bq|kubectl|helm|docker|podman|terraform|tofu)\s",
            r"^(npm|yarn|pnpm|pip|uv|poetry|cargo|go|make|cmake)\s",
            r"^(curl|wget|http|ssh|scp|rsync)\s",
            r"^(git|gh|hub)\s",
            r"^(cd|ls|mkdir|rm|cp|mv|cat|grep|sed|awk|chmod|chown)\s",
            r"^(sudo|apt|apt-get|brew|yum|dnf|pacman)\s",
            r"^(echo|printf|read)\s",
            r"^(if|then|else|fi|for|do|done|while|case|esac)\s",
            r"^\w+=.*&&",  # VAR=value && command
            r"^#\s*(Install|Create|Update|Delete|Run|Build|Deploy|Set|Configure|Enable|Check|Get|List)",
        ],
        "Shell/Bash commands",
    ),
    # === XML/HTML ===
    (
        "xml",
        [
            r"^<\?xml\s",
            r"^<[a-zA-Z][a-zA-Z0-9]*(\s[^>]*)?>",
            r"^<!DOCTYPE\s",
        ],
        "XML syntax",
    ),
    (
        "html",
        [
            r"^<!DOCTYPE\s+html",
            r"^<html",
            r"^<(head|body|div|span|p|a|script|style)\s*>",
        ],
        "HTML syntax",
    ),
    # === CSS ===
    (
        "css",
        [
            r"^[.#]?[\w-]+\s*\{",
            r"^\s*(color|background|margin|padding|font|display|position):",
            r"^@(media|import|keyframes|font-face)\s",
        ],
        "CSS syntax",
    ),
    # === Markdown (must be after bash to avoid shell comments) ===
    # NOTE: Markdown headers (# Header) look like shell comments
    # Only match if there's clear markdown syntax, not just # at start
    (
        "markdown",
        [
            r"^\*\*\w.*\*\*",  # Bold
            r"^\[.+\]\(.+\)",  # Links
            r"^>\s+",  # Blockquotes
            # Don't match # headers - too ambiguous with shell comments
        ],
        "Markdown syntax",
    ),
    # === Properties/Dotenv (VAR=value format, common in .env files) ===
    (
        "properties",
        [
            r"^##?\s*\.env",  # ## .env comment at start
            r"^[A-Z][A-Z0-9_]+=",  # UPPER_CASE=value (environment variable style)
        ],
        "Properties/Dotenv syntax",
    ),
    # === INI/Config (requires [section] headers) ===
    (
        "ini",
        [
            r"^\[[\w\s.-]+\]\s*$",  # [Section] - only match if we have section headers
        ],
        "INI/Config syntax",
    ),
    # === Diff ===
    (
        "diff",
        [
            r"^(---|\+\+\+)\s+\S",
            r"^@@\s+-\d+,\d+\s+\+\d+,\d+\s+@@",
            r"^[-+]\s",
        ],
        "Diff/Patch syntax",
    ),
]


def infer_language(code_lines: list[str], max_lines: int = 10) -> LanguageMatch:
    """
    Infer the programming language from code content.

    Args:
        code_lines: Lines of code (without the opening/closing fences)
        max_lines: Maximum number of lines to analyze

    Returns:
        LanguageMatch with detected language, confidence, and reason
    """
    # Filter to non-empty, non-comment-only lines for analysis
    analysis_lines = []
    for line in code_lines[:max_lines]:
        stripped = line.strip()
        if stripped and not stripped.startswith("//"):
            analysis_lines.append(stripped)

    if not analysis_lines:
        return LanguageMatch("text", 0.5, "Empty or comment-only block")

    # Combine first few lines for multi-line pattern matching
    combined = "\n".join(analysis_lines[:5])
    first_line = analysis_lines[0]

    # Check each language pattern in priority order
    for language, patterns, description in LANGUAGE_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, first_line, re.IGNORECASE):
                return LanguageMatch(language, 0.9, f"Matched {description}: {pattern}")
            if re.search(pattern, combined, re.MULTILINE | re.IGNORECASE):
                return LanguageMatch(language, 0.8, f"Matched {description} in block: {pattern}")

    # Secondary heuristics for ambiguous cases

    # Check for YAML-like structure (key: value on multiple lines)
    yaml_lines = sum(1 for line in analysis_lines if re.match(r"^\s*[\w-]+:\s", line))
    if yaml_lines >= 2:
        return LanguageMatch("yaml", 0.7, f"Multiple key: value lines ({yaml_lines})")

    # Check for bash-like commands (starts with common command)
    bash_commands = r"^(cat|echo|cd|ls|mkdir|rm|cp|mv|chmod|touch|head|tail|grep|find|xargs|sort|uniq|wc|tr|cut|tee)\s"
    if re.match(bash_commands, first_line):
        return LanguageMatch("bash", 0.7, "Common shell command")

    # Check for shell comment at start (## or # followed by verb)
    if re.match(r"^##?\s+[A-Z]", first_line):
        # This is likely a bash script with comments
        return LanguageMatch("bash", 0.6, "Shell-style comment header")

    # Default to text for safety
    return LanguageMatch("text", 0.3, "No strong pattern match")


def should_add_language_tag(
    code_lines: list[str],
    min_confidence: float = 0.5,
) -> str | None:
    """
    Determine if we should add a language tag and what it should be.

    Args:
        code_lines: Lines of code content
        min_confidence: Minimum confidence to add tag

    Returns:
        Language string if we should add, None if we should leave as-is
    """
    result = infer_language(code_lines)

    if result.confidence >= min_confidence and result.language != "text":
        return result.language

    # For text, only add if we're confident it's not code
    if result.language == "text" and result.confidence >= 0.5:
        return "text"

    return None


if __name__ == "__main__":
    # Quick test
    test_cases = [
        (["gcloud config set project $PROJECT"], "bash"),
        (["apiVersion: v1", "kind: Pod"], "yaml"),
        (["import os", "from pathlib import Path"], "python"),
        (["const x = 1;", "let y = 2;"], "javascript"),
        (["SELECT * FROM users"], "sql"),
        (["FROM python:3.11", "RUN pip install"], "dockerfile"),
        (['resource "aws_instance" "main" {'], "hcl"),
    ]

    for lines, expected in test_cases:
        result = infer_language(lines)
        status = "✓" if result.language == expected else "✗"
        print(f"{status} {expected:12} -> {result.language:12} ({result.confidence:.1f}) {result.reason}")
