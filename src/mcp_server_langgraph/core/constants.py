"""
Application-wide constants for maintainability.

This module centralizes magic numbers and configuration constants
to follow DRY principles and make the codebase more maintainable.

Usage:
    from mcp_server_langgraph.core.constants import MESSAGE_PREVIEW_LENGTH
"""

# ==============================================================================
# Context Management Constants
# ==============================================================================

# Characters to show in message previews/truncation
MESSAGE_PREVIEW_LENGTH: int = 200

# Token count that triggers conversation compaction
COMPACTION_THRESHOLD_TOKENS: int = 8000

# Target token count after compaction
TARGET_AFTER_COMPACTION_TOKENS: int = 4000

# Number of recent messages to keep uncompacted
RECENT_MESSAGE_COUNT: int = 5


# ==============================================================================
# Timeout Constants
# ==============================================================================

# Default timeout for LLM API calls (seconds)
DEFAULT_LLM_TIMEOUT_SECONDS: int = 60

# Default timeout for database connectivity checks (seconds)
DEFAULT_DATABASE_TIMEOUT_SECONDS: int = 5

# Default socket timeout for Redis connections (seconds)
DEFAULT_REDIS_SOCKET_TIMEOUT_SECONDS: int = 2


# ==============================================================================
# Retry Constants
# ==============================================================================

# Default maximum retry attempts for transient failures
DEFAULT_MAX_RETRIES: int = 3

# Default base delay for exponential backoff (seconds)
DEFAULT_RETRY_BASE_DELAY: float = 1.0

# Default maximum delay for exponential backoff (seconds)
DEFAULT_RETRY_MAX_DELAY: float = 60.0
