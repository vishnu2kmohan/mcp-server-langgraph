"""
Privacy Module for PII Protection

This module provides PII (Personally Identifiable Information) detection
and tokenization for protecting sensitive data before LLM exposure.

Required for GDPR, HIPAA, and SOC2 compliance.

Usage:
    from mcp_server_langgraph.privacy import PIITokenizer, detect_pii

    # Detect PII in text
    detections = detect_pii("Contact: john@example.com")

    # Tokenize to protect PII
    tokenizer = PIITokenizer()
    tokenized_text, lookup = tokenizer.tokenize("Email: john@example.com")

    # Later, restore original
    original = tokenizer.untokenize(tokenized_text, lookup)
"""

from mcp_server_langgraph.privacy.detectors import PIIDetection, PIIType, detect_pii
from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable
from mcp_server_langgraph.privacy.middleware import PIIMiddleware
from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

__all__ = [
    "PIIDetection",
    "PIIMiddleware",
    "PIITokenizer",
    "PIIType",
    "EncryptedLookupTable",
    "detect_pii",
]
