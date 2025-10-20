"""
SOC2 compliance implementation.

Provides evidence collection and audit logging for SOC2 compliance:
- Access reviews and audit trails
- Security event logging
- Evidence collection for auditors
"""

from mcp_server_langgraph.compliance.soc2.evidence import EvidenceCollector

__all__ = [
    "EvidenceCollector",
]
