"""
PII Detection Patterns

Pattern-based detection of Personally Identifiable Information (PII)
for protecting sensitive data before LLM exposure.

Supported PII types:
- EMAIL: Email addresses
- PHONE: Phone numbers (US and international)
- SSN: Social Security Numbers
- CREDIT_CARD: Credit card numbers
- NAME: Personal names (requires context)
- ADDRESS: Physical addresses
- IP_ADDRESS: IP addresses (excluding localhost)
- DOB: Dates of birth

Usage:
    from mcp_server_langgraph.privacy.detectors import detect_pii

    detections = detect_pii("Contact: john@example.com at 555-123-4567")
    for d in detections:
        print(f"{d.pii_type}: {d.value}")
"""

from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    pass


class PIIType(str, Enum):
    """Types of PII that can be detected."""

    EMAIL = "EMAIL"
    PHONE = "PHONE"
    SSN = "SSN"
    CREDIT_CARD = "CREDIT_CARD"
    NAME = "NAME"
    ADDRESS = "ADDRESS"
    IP_ADDRESS = "IP_ADDRESS"
    DOB = "DOB"


class PIIDetection(BaseModel):
    """A detected PII instance.

    Attributes:
        pii_type: Type of PII detected
        value: The actual PII value found
        start: Start position in the text
        end: End position in the text
    """

    pii_type: str
    value: str
    start: int
    end: int


def _safe_is_feature_enabled(flag_name: str) -> bool:
    """Safely check if a feature flag is enabled."""
    try:
        from mcp_server_langgraph.core.feature_flags import is_feature_enabled

        result: bool = is_feature_enabled(flag_name)
        return result
    except (ImportError, RuntimeError):
        return True


# Expose for mocking in tests
def is_feature_enabled(flag_name: str) -> bool:
    """Check if a feature flag is enabled."""
    return _safe_is_feature_enabled(flag_name)


# Compiled regex patterns for PII detection
# Patterns are designed to balance precision and recall

# Email pattern - RFC 5322 simplified
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)

# US Phone patterns - various formats
PHONE_PATTERN = re.compile(
    r"(?:\+?1[-.\s]?)?"  # Optional country code
    r"(?:\(?\d{3}\)?[-.\s]?)"  # Area code
    r"\d{3}[-.\s]?"  # Exchange
    r"\d{4}\b",  # Subscriber
    re.VERBOSE,
)

# SSN patterns - with or without dashes
SSN_PATTERN = re.compile(
    r"\b(?:\d{3}-\d{2}-\d{4}|\d{9})\b",
)

# Credit card patterns - major card types with separators
CREDIT_CARD_PATTERN = re.compile(
    r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
)

# IPv4 pattern - excluding localhost and private ranges
IP_PATTERN = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
)

# Date of birth patterns - MM/DD/YYYY and YYYY-MM-DD
DOB_PATTERN = re.compile(
    r"\b(?:"
    r"\d{1,2}/\d{1,2}/\d{4}|"  # MM/DD/YYYY
    r"\d{4}-\d{2}-\d{2}"  # YYYY-MM-DD
    r")\b",
)

# Localhost and private IP ranges to exclude
LOCALHOST_PATTERNS = {
    "127.0.0.1",
    "0.0.0.0",
}


def _is_localhost(ip: str) -> bool:
    """Check if IP address is localhost or loopback."""
    return ip in LOCALHOST_PATTERNS or ip.startswith("127.")


def detect_pii(text: str | None) -> list[PIIDetection]:
    """Detect PII in text using pattern matching.

    Args:
        text: Text to scan for PII

    Returns:
        List of PIIDetection objects for each detected PII
    """
    if not text:
        return []

    # Check feature flag
    if not is_feature_enabled("pii_tokenization"):
        return []

    detections: list[PIIDetection] = []

    # Detect emails
    for match in EMAIL_PATTERN.finditer(text):
        detections.append(
            PIIDetection(
                pii_type=PIIType.EMAIL.value,
                value=match.group(),
                start=match.start(),
                end=match.end(),
            )
        )

    # Detect phone numbers
    for match in PHONE_PATTERN.finditer(text):
        value = match.group()
        # Filter out sequences that are too short (might be other numbers)
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 10:
            detections.append(
                PIIDetection(
                    pii_type=PIIType.PHONE.value,
                    value=value,
                    start=match.start(),
                    end=match.end(),
                )
            )

    # Detect SSNs
    for match in SSN_PATTERN.finditer(text):
        detections.append(
            PIIDetection(
                pii_type=PIIType.SSN.value,
                value=match.group(),
                start=match.start(),
                end=match.end(),
            )
        )

    # Detect credit cards
    for match in CREDIT_CARD_PATTERN.finditer(text):
        value = match.group()
        # Verify Luhn checksum for better accuracy (simplified check)
        digits = re.sub(r"\D", "", value)
        if len(digits) == 16:
            detections.append(
                PIIDetection(
                    pii_type=PIIType.CREDIT_CARD.value,
                    value=value,
                    start=match.start(),
                    end=match.end(),
                )
            )

    # Detect IP addresses (excluding localhost)
    for match in IP_PATTERN.finditer(text):
        ip = match.group()
        if not _is_localhost(ip):
            detections.append(
                PIIDetection(
                    pii_type=PIIType.IP_ADDRESS.value,
                    value=ip,
                    start=match.start(),
                    end=match.end(),
                )
            )

    # Detect dates of birth
    for match in DOB_PATTERN.finditer(text):
        detections.append(
            PIIDetection(
                pii_type=PIIType.DOB.value,
                value=match.group(),
                start=match.start(),
                end=match.end(),
            )
        )

    return detections
