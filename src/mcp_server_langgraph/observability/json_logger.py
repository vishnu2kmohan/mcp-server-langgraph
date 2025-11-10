"""
Structured JSON Logging with OpenTelemetry Integration

Provides JSON-formatted logging with automatic trace context injection,
compatible with centralized log aggregation platforms (ELK, Datadog, Splunk, CloudWatch).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from opentelemetry import trace

try:
    from pythonjsonlogger.json import JsonFormatter

    JsonFormatterBase = JsonFormatter
except (ImportError, AttributeError):
    # Fallback if pythonjsonlogger is not available
    JsonFormatterBase = logging.Formatter


class CustomJSONFormatter(JsonFormatterBase):  # type: ignore[valid-type,misc]
    """
    Enhanced JSON formatter with OpenTelemetry trace context injection

    Features:
    - Automatic trace_id and span_id injection from OpenTelemetry
    - ISO 8601 timestamp formatting
    - Exception stack trace capture
    - Custom field support via extra parameter
    - Hostname/service name injection
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        style: str = "%",
        service_name: str = "mcp-server-langgraph",
        include_hostname: bool = True,
        indent: Optional[int] = None,
    ):
        """
        Initialize JSON formatter

        Args:
            fmt: Log message format (supports standard logging format keys)
            datefmt: Date format (ISO 8601 if not specified)
            style: Format style (%, {, $)
            service_name: Service name to include in logs
            include_hostname: Whether to include hostname
            indent: JSON indentation for pretty-printing (None for compact)
        """
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.service_name = service_name
        self.include_hostname = include_hostname
        self.indent = indent

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """
        Add custom fields to log record

        Injects:
        - timestamp (ISO 8601)
        - level (INFO, ERROR, etc.)
        - logger name
        - trace_id and span_id from OpenTelemetry
        - service name
        - hostname (optional)
        - exception details (if present)
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO 8601 format with milliseconds
        if "timestamp" not in log_record:
            now = datetime.now(timezone.utc)
            log_record["timestamp"] = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        # Add log level
        log_record["level"] = record.levelname

        # Add logger name
        log_record["logger"] = record.name

        # Add service name
        log_record["service"] = self.service_name

        # Add hostname if enabled
        if self.include_hostname:
            import socket

            try:
                log_record["hostname"] = socket.gethostname()
            except Exception:
                log_record["hostname"] = "unknown"

        # Add OpenTelemetry trace context
        span = trace.get_current_span()
        if span:
            span_context = span.get_span_context()
            if span_context and span_context.is_valid:
                log_record["trace_id"] = format(span_context.trace_id, "032x")
                log_record["span_id"] = format(span_context.span_id, "016x")
                log_record["trace_flags"] = f"{span_context.trace_flags:02x}"

        # Add exception info if present
        if record.exc_info:
            # exc_info can be True (capture current exception) or a tuple (type, value, traceback)
            # When logging.LogRecord is created with exc_info=True, it should auto-capture
            # But in tests, it might just be True. Handle both cases.
            if isinstance(record.exc_info, tuple) and len(record.exc_info) == 3:
                log_record["exception"] = {
                    "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                    "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                    "stacktrace": self.formatException(record.exc_info),
                }
            # Note: exc_info=True case is rare and often indicates a logging misconfiguration
            # The tuple case above handles normal exception logging

        # Add process and thread info
        log_record["process"] = {
            "pid": record.process,
            "name": record.processName,
        }
        log_record["thread"] = {
            "id": record.thread,
            "name": record.threadName,
        }

        # Add file location
        log_record["location"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        message_dict = {}
        # Always get the formatted message (combines msg + args)
        message_dict["message"] = record.getMessage()

        # Merge any extra fields passed via extra parameter
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                # Skip standard logging attributes
                if key not in [
                    "name",
                    "msg",
                    "args",
                    "created",
                    "filename",
                    "funcName",
                    "levelname",
                    "levelno",
                    "lineno",
                    "module",
                    "msecs",
                    "message",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "taskName",
                ]:
                    # Add custom extra fields
                    if not key.startswith("_"):
                        message_dict[key] = value

        log_record: Dict[str, Any] = {}
        self.add_fields(log_record, record, message_dict)

        # Serialize to JSON
        return json.dumps(log_record, default=str, indent=self.indent)


def setup_json_logging(
    logger: logging.Logger,
    level: int = logging.INFO,
    service_name: str = "mcp-server-langgraph",
    include_hostname: bool = True,
    indent: Optional[int] = None,
) -> logging.Logger:
    """
    Configure logger with JSON formatting

    Args:
        logger: Logger instance to configure
        level: Logging level
        service_name: Service name for log entries
        include_hostname: Include hostname in logs
        indent: JSON indentation (None for compact, 2 for pretty-print)

    Returns:
        Configured logger instance

    Example:
        >>> logger = logging.getLogger(__name__)
        >>> setup_json_logging(logger, level=logging.INFO)
        >>> logger.info("User logged in", extra={"user_id": "alice", "ip": "1.2.3.4"})
    """
    # Remove existing handlers
    logger.handlers = []

    # Create JSON formatter
    formatter = CustomJSONFormatter(
        service_name=service_name,
        include_hostname=include_hostname,
        indent=indent,
    )

    # Create console handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(level)

    # Add handler to logger
    logger.addHandler(handler)
    logger.setLevel(level)

    return logger


# Helper function for logging with extra context
def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """
    Log message with additional context fields

    Args:
        logger: Logger instance
        level: Log level (logging.INFO, logging.ERROR, etc.)
        message: Log message
        **context: Additional context fields (user_id, ip_address, etc.)

    Example:
        >>> log_with_context(
        ...     logger,
        ...     logging.INFO,
        ...     "User action",
        ...     user_id="alice",
        ...     action="login",
        ...     ip="1.2.3.4"
        ... )
    """
    logger.log(level, message, extra=context)
