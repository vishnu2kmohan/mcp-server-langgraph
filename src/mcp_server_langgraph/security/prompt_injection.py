"""
Enhanced Prompt Injection Detection Module

Provides multi-layered detection for prompt injection attacks including:
- Pattern-based detection for known attacks
- Encoding detection (base64, hex, unicode escapes)
- Risk scoring system for graduated responses
- Metrics for security monitoring

See ADR-0052 for security design rationale.
"""

import base64
import binascii
import re
from enum import Enum
from typing import Any

# Prometheus metrics (lazy initialization)
_metrics_available = False
_injection_detection_counter: Any = None
_injection_risk_histogram: Any = None


def _init_metrics() -> bool:
    """Initialize metrics lazily to avoid import issues."""
    global _metrics_available
    global _injection_detection_counter
    global _injection_risk_histogram

    if _injection_detection_counter is not None:
        return _metrics_available

    try:
        from prometheus_client import Counter, Histogram

        _injection_detection_counter = Counter(
            "security_prompt_injection_detections_total",
            "Total prompt injection detections by category and risk level",
            ["category", "risk_level"],
        )

        _injection_risk_histogram = Histogram(
            "security_prompt_injection_risk_score",
            "Risk score distribution for analyzed content",
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        )

        _metrics_available = True
    except ImportError:
        _metrics_available = False

    return _metrics_available


class RiskLevel(str, Enum):
    """Risk level classification for detected patterns."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DetectionCategory(str, Enum):
    """Categories of prompt injection attacks."""

    INSTRUCTION_OVERRIDE = "instruction_override"
    ROLE_PLAY = "role_play"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    JAILBREAK = "jailbreak"
    ENCODED_ATTACK = "encoded_attack"
    DELIMITER_ATTACK = "delimiter_attack"
    CODE_INJECTION = "code_injection"
    DATA_EXFILTRATION = "data_exfiltration"


# Pattern definitions with weights (higher = more suspicious)
_INJECTION_PATTERNS: dict[DetectionCategory, list[tuple[str, float]]] = {
    DetectionCategory.INSTRUCTION_OVERRIDE: [
        (r"ignore\s+(all\s+)?previous", 0.9),  # More flexible match
        (r"ignore\s+previous\s+(instructions?|prompts?|context)", 0.9),
        (r"disregard\s+(all\s+)?(previous|above|prior)", 0.9),
        (r"forget\s+(everything|your|all)", 0.8),
        (r"new\s+instructions?:?", 0.7),
        (r"override\s+(system|previous|default)", 0.8),
        (r"from\s+now\s+on,?\s+(you|ignore)", 0.7),
        (r"stop\s+being\s+(an?\s+)?ai", 0.6),
        (r"you\s+are\s+now\s+free", 0.6),
    ],
    DetectionCategory.ROLE_PLAY: [
        (r"pretend\s+(to\s+be|you\s+are)", 0.6),
        (r"act\s+as\s+(if|though|a)", 0.5),
        (r"role[- ]?play\s+as", 0.6),
        (r"you\s+are\s+(now\s+)?(?!a\s+helpful)", 0.5),
        (r"imagine\s+you\s+are", 0.4),
        (r"let'?s\s+play\s+a\s+game", 0.4),
    ],
    DetectionCategory.SYSTEM_PROMPT_LEAK: [
        (r"(show|reveal|display|print|output).*(system|initial)\s+prompt", 0.9),
        (r"show\s+me\s+(your\s+)?(system\s+)?prompt", 0.9),  # More flexible
        (r"what\s+(are|is)\s+your\s+(system\s+)?instructions?", 0.8),
        (r"repeat\s+(back\s+)?(your|the)\s+(system|original)\s+prompt", 0.9),
        (r"tell\s+me\s+your\s+(system\s+)?prompt", 0.8),
        (r"what\s+were\s+you\s+told", 0.6),
        (r"echo\s+(your\s+)?instructions?", 0.7),
        (r"your\s+system\s+prompt", 0.8),  # Catch "show me your system prompt"
    ],
    DetectionCategory.JAILBREAK: [
        (r"dan\s*(mode)?", 0.8),  # "Do Anything Now" jailbreak
        (r"developer\s+mode", 0.8),
        (r"jailbreak", 0.9),
        (r"bypass\s+(safety|filter|restriction)", 0.9),
        (r"disable\s+(safety|content\s+filter)", 0.9),
        (r"unlock\s+(hidden|secret)\s+(mode|feature)", 0.7),
        (r"hypothetically,?\s+if\s+you\s+could", 0.5),
        (r"for\s+(educational|research)\s+purposes", 0.4),
        (r"purely\s+fictional", 0.4),
    ],
    DetectionCategory.DELIMITER_ATTACK: [
        (r"<\|im_start\|>", 1.0),
        (r"<\|im_end\|>", 1.0),
        (r"<\|endoftext\|>", 1.0),
        (r"\[INST\]", 0.9),
        (r"\[/INST\]", 0.9),
        (r"<<SYS>>", 0.9),
        (r"<</SYS>>", 0.9),
        (r"###\s*(Human|Assistant|System):", 0.8),
        (r"---+\s*\n?\s*(system|human|assistant)", 0.7),
    ],
    DetectionCategory.CODE_INJECTION: [
        (r"exec\s*\(", 0.9),
        (r"eval\s*\(", 0.9),
        (r"__import__\s*\(", 0.9),
        (r"os\.(system|popen|exec)", 0.9),
        (r"subprocess\.(run|call|Popen)", 0.9),
        (r"\bimport\s+(os|sys|subprocess)", 0.7),
        (r"shell\s*=\s*True", 0.8),
    ],
    DetectionCategory.DATA_EXFILTRATION: [
        (r"send\s+(this\s+)?data\s+to", 0.8),
        (r"upload\s+(this|the\s+following)\s+to", 0.8),
        (r"http[s]?://[^\s]+\?.*=", 0.6),  # URLs with query params
        (r"webhook", 0.5),
        (r"curl\s+-", 0.7),
        (r"wget\s+", 0.7),
    ],
}


class InjectionDetectionResult:
    """Result of prompt injection detection analysis."""

    def __init__(self) -> None:
        self.detections: list[dict[str, Any]] = []
        self.risk_score: float = 0.0
        self.risk_level: RiskLevel = RiskLevel.NONE
        self.encoded_content_found: bool = False
        self.sanitized_content: str | None = None

    def add_detection(
        self,
        category: DetectionCategory,
        pattern: str,
        match: str,
        weight: float,
    ) -> None:
        """Add a detection to the results."""
        self.detections.append(
            {
                "category": category.value,
                "pattern": pattern,
                "matched_text": match[:100],  # Limit matched text length
                "weight": weight,
            }
        )
        # Accumulate risk score (capped at 1.0)
        self.risk_score = min(1.0, self.risk_score + weight * 0.3)

    def calculate_risk_level(self) -> None:
        """Calculate overall risk level from score."""
        if self.risk_score >= 0.8:
            self.risk_level = RiskLevel.CRITICAL
        elif self.risk_score >= 0.6:
            self.risk_level = RiskLevel.HIGH
        elif self.risk_score >= 0.4:
            self.risk_level = RiskLevel.MEDIUM
        elif self.risk_score > 0:
            self.risk_level = RiskLevel.LOW
        else:
            self.risk_level = RiskLevel.NONE

    @property
    def is_suspicious(self) -> bool:
        """Return True if any suspicious patterns were detected."""
        return len(self.detections) > 0 or self.encoded_content_found

    @property
    def should_block(self) -> bool:
        """Return True if the content should be blocked entirely."""
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for logging/API."""
        return {
            "is_suspicious": self.is_suspicious,
            "should_block": self.should_block,
            "risk_score": round(self.risk_score, 3),
            "risk_level": self.risk_level.value,
            "detection_count": len(self.detections),
            "detections": self.detections[:5],  # Limit to top 5
            "encoded_content_found": self.encoded_content_found,
        }


def _detect_encoded_content(content: str) -> tuple[bool, str | None]:
    """Detect and attempt to decode encoded content (base64, hex).

    Returns:
        Tuple of (found_encoded, decoded_content)
    """
    # Base64 detection - look for base64-like patterns
    base64_pattern = r"[A-Za-z0-9+/]{20,}={0,2}"
    matches = re.findall(base64_pattern, content)

    for match in matches:
        try:
            # Try to decode
            decoded = base64.b64decode(match).decode("utf-8", errors="ignore")
            # Check if decoded content looks like an injection
            if any(pattern in decoded.lower() for pattern in ["ignore", "system", "prompt", "instructions"]):
                return True, decoded
        except (binascii.Error, ValueError):
            pass

    # Hex detection - look for hex-encoded strings
    hex_pattern = r"(?:0x)?[0-9a-fA-F]{10,}"
    hex_matches = re.findall(hex_pattern, content)

    for match in hex_matches:
        try:
            clean_hex = match.lstrip("0x")
            if len(clean_hex) % 2 == 0:
                decoded = bytes.fromhex(clean_hex).decode("utf-8", errors="ignore")
                if len(decoded) > 5 and any(pattern in decoded.lower() for pattern in ["ignore", "system", "prompt"]):
                    return True, decoded
        except (ValueError, UnicodeDecodeError):
            pass

    return False, None


def analyze_content(content: str) -> InjectionDetectionResult:
    """Analyze content for prompt injection patterns.

    Args:
        content: The content to analyze

    Returns:
        InjectionDetectionResult with detailed analysis
    """
    result = InjectionDetectionResult()

    if not content or not content.strip():
        return result

    content_lower = content.lower()

    # Check each category of patterns
    for category, patterns in _INJECTION_PATTERNS.items():
        for pattern, weight in patterns:
            try:
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                for match in matches:
                    # Handle both string and tuple matches from regex groups
                    match_text = match if isinstance(match, str) else str(match)
                    result.add_detection(category, pattern, match_text, weight)
            except re.error:
                pass  # Skip invalid regex patterns

    # Check for encoded content
    encoded_found, decoded_content = _detect_encoded_content(content)
    if encoded_found:
        result.encoded_content_found = True
        result.risk_score = min(1.0, result.risk_score + 0.4)
        result.detections.append(
            {
                "category": DetectionCategory.ENCODED_ATTACK.value,
                "pattern": "encoded_content",
                "matched_text": decoded_content[:50] if decoded_content else "[encoded]",
                "weight": 0.8,
            }
        )

    # Calculate final risk level
    result.calculate_risk_level()

    # Record metrics
    _record_metrics(result)

    return result


def sanitize_content(
    content: str,
    replacement: str = "[filtered]",
) -> tuple[str, InjectionDetectionResult]:
    """Sanitize content by replacing detected injection patterns.

    Args:
        content: Content to sanitize
        replacement: String to replace detected patterns with

    Returns:
        Tuple of (sanitized_content, detection_result)
    """
    result = analyze_content(content)
    sanitized = content

    # Replace detected patterns
    for detection in result.detections:
        pattern = detection.get("pattern", "")
        if pattern and pattern != "encoded_content":
            try:
                sanitized = re.sub(
                    pattern,
                    replacement,
                    sanitized,
                    flags=re.IGNORECASE,
                )
            except re.error:
                pass  # Skip invalid patterns

    result.sanitized_content = sanitized
    return sanitized, result


def _record_metrics(result: InjectionDetectionResult) -> None:
    """Record detection metrics to Prometheus."""
    _init_metrics()

    if not _metrics_available:
        return

    # Record risk score
    if _injection_risk_histogram:
        _injection_risk_histogram.observe(result.risk_score)

    # Record detections by category
    if _injection_detection_counter:
        for detection in result.detections:
            _injection_detection_counter.labels(
                category=detection["category"],
                risk_level=result.risk_level.value,
            ).inc()


# Quick validation function for simple use cases
def is_potentially_malicious(content: str, threshold: float = 0.4) -> bool:
    """Quick check if content appears malicious.

    Args:
        content: Content to check
        threshold: Risk score threshold (0.0 - 1.0)

    Returns:
        True if risk score exceeds threshold
    """
    result = analyze_content(content)
    return result.risk_score >= threshold
