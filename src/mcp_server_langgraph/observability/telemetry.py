"""
Unified observability setup with OpenTelemetry and LangSmith support
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from typing import Any

from opentelemetry import metrics as otel_metrics
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from mcp_server_langgraph.observability.json_logger import CustomJSONFormatter

# Configuration
SERVICE_NAME = "mcp-server-langgraph"
OTLP_ENDPOINT = "http://localhost:4317"  # Change to your OTLP collector

# Control verbose logging (set to False when embedded as library)
OBSERVABILITY_VERBOSE = os.getenv("OBSERVABILITY_VERBOSE", "true").lower() in ("true", "1", "yes")


class ObservabilityConfig:
    """Centralized observability configuration with OpenTelemetry and LangSmith support"""

    def __init__(
        self,
        service_name: str = SERVICE_NAME,
        otlp_endpoint: str = OTLP_ENDPOINT,
        enable_console_export: bool = True,
        enable_langsmith: bool = False,
        log_format: str = "json",  # "json" or "text"
        log_json_indent: int | None = None,  # None for compact, 2 for pretty-print
        enable_file_logging: bool = False,  # NEW: opt-in file logging
    ):
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint
        self.enable_console_export = enable_console_export
        self.enable_langsmith = enable_langsmith
        self.log_format = log_format
        self.log_json_indent = log_json_indent
        self.enable_file_logging = enable_file_logging

        # Setup OpenTelemetry
        self._setup_tracing()
        self._setup_metrics()
        self._setup_logging(enable_file_logging=enable_file_logging)

        # Setup LangSmith if enabled
        if self.enable_langsmith:
            self._setup_langsmith()

    def _setup_tracing(self):
        """Configure distributed tracing"""
        # Get version from settings
        try:
            from mcp_server_langgraph.core.config import settings

            service_version = settings.service_version
        except Exception:
            from mcp_server_langgraph import __version__

            service_version = __version__

        resource = Resource.create(
            {"service.name": self.service_name, "service.version": service_version, "deployment.environment": "production"}
        )

        provider = TracerProvider(resource=resource)

        # OTLP exporter for production
        otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Console exporter for development
        if self.enable_console_export:
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))

        trace.set_tracer_provider(provider)

        self.tracer = trace.get_tracer(__name__)
        if OBSERVABILITY_VERBOSE:
            print(f"✓ Tracing configured: {self.service_name}")

    def _setup_metrics(self):
        """Configure metrics collection"""
        resource = Resource.create({"service.name": self.service_name})

        # OTLP metric exporter
        otlp_metric_exporter = OTLPMetricExporter(endpoint=self.otlp_endpoint)
        otlp_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=5000)

        readers = [otlp_reader]

        # Console exporter for development
        if self.enable_console_export:
            console_metric_exporter = ConsoleMetricExporter()
            console_reader = PeriodicExportingMetricReader(console_metric_exporter)
            readers.append(console_reader)

        provider = MeterProvider(resource=resource, metric_readers=readers)

        otel_metrics.set_meter_provider(provider)
        self.meter = otel_metrics.get_meter(__name__)

        # Create common metrics
        self._create_metrics()
        if OBSERVABILITY_VERBOSE:
            print(f"✓ Metrics configured: {self.service_name}")

    def _create_metrics(self):
        """Create standard metrics for the service"""
        self.tool_calls = self.meter.create_counter(name="agent.tool.calls", description="Number of tool calls", unit="1")

        self.successful_calls = self.meter.create_counter(
            name="agent.calls.successful", description="Number of successful calls", unit="1"
        )

        self.failed_calls = self.meter.create_counter(
            name="agent.calls.failed", description="Number of failed calls", unit="1"
        )

        self.auth_failures = self.meter.create_counter(
            name="auth.failures", description="Number of authentication failures", unit="1"
        )

        self.authz_failures = self.meter.create_counter(
            name="authz.failures", description="Number of authorization failures", unit="1"
        )

        self.response_time = self.meter.create_histogram(
            name="agent.response.duration", description="Response time distribution", unit="ms"
        )

    def _setup_logging(self, enable_file_logging: bool = False):
        """
        Configure structured logging with OpenTelemetry and optional log rotation.

        Implements idempotent initialization to prevent duplicate handlers
        when re-imported or embedded in larger services.

        Args:
            enable_file_logging: Enable file-based log rotation (opt-in). Default: False.
                                Set to True for production deployments with persistent storage.
                                Leave False for serverless, containers, or read-only environments.
        """
        # Check if logging is already configured (idempotent guard)
        root_logger = logging.getLogger()
        if root_logger.handlers:
            # Logging already configured - skip to avoid duplicate handlers
            self.logger = logging.getLogger(self.service_name)
            if OBSERVABILITY_VERBOSE:
                print(f"✓ Logging already configured, reusing existing setup")
            return

        # Instrument logging to include trace context
        LoggingInstrumentor().instrument(set_logging_format=True)

        # Choose formatter based on log_format setting
        if self.log_format == "json":
            # JSON formatter with trace context
            formatter = CustomJSONFormatter(
                service_name=self.service_name,
                include_hostname=True,
                indent=self.log_json_indent,
            )
            # Console uses pretty-print in development, compact in production
            console_formatter = CustomJSONFormatter(
                service_name=self.service_name,
                include_hostname=False,  # Skip hostname for console
                indent=2 if os.getenv("ENVIRONMENT", "development") == "development" else None,
            )
        else:
            # Text formatter with trace context
            log_format_str = (
                "%(asctime)s - %(name)s - %(levelname)s - [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] - %(message)s"
            )
            formatter = logging.Formatter(log_format_str)
            console_formatter = formatter

        # Console handler (stdout) - always enabled
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)

        handlers = [console_handler]

        # File handlers - opt-in only
        if enable_file_logging:
            # Create logs directory if it doesn't exist
            logs_dir = Path("logs")
            logs_dir.mkdir(exist_ok=True)

            # Rotating file handler (size-based rotation)
            # Rotates when file reaches 10MB, keeps 5 backup files
            rotating_handler = RotatingFileHandler(
                filename=logs_dir / f"{self.service_name}.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            rotating_handler.setLevel(logging.INFO)
            rotating_handler.setFormatter(formatter)
            handlers.append(rotating_handler)

            # Time-based rotating handler (daily rotation)
            # Rotates daily at midnight, keeps 30 days of logs
            daily_handler = TimedRotatingFileHandler(
                filename=logs_dir / f"{self.service_name}-daily.log",
                when="midnight",
                interval=1,
                backupCount=30,
                encoding="utf-8",
            )
            daily_handler.setLevel(logging.INFO)
            daily_handler.setFormatter(formatter)
            handlers.append(daily_handler)

            # Error log handler (only ERROR and CRITICAL)
            error_handler = RotatingFileHandler(
                filename=logs_dir / f"{self.service_name}-error.log",
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding="utf-8",
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            handlers.append(error_handler)

        # Configure root logger
        logging.basicConfig(level=logging.INFO, handlers=handlers)

        self.logger = logging.getLogger(self.service_name)
        if OBSERVABILITY_VERBOSE:
            print(f"✓ Logging configured: {self.service_name}")
            print(f"  - Format: {self.log_format.upper()}")
            print("  - Console output: INFO and above")
            if enable_file_logging:
                print(f"  - Main log: logs/{self.service_name}.log (rotating, 10MB, 5 backups)")
                print(f"  - Daily log: logs/{self.service_name}-daily.log (daily, 30 days)")
                print(f"  - Error log: logs/{self.service_name}-error.log (ERROR and above)")
            else:
                print("  - File logging: disabled (console only)")

    def get_tracer(self):
        """Get tracer instance"""
        return self.tracer

    def get_meter(self):
        """Get meter instance"""
        return self.meter

    def get_logger(self):
        """Get logger instance"""
        return self.logger

    def _setup_langsmith(self):
        """Configure LangSmith tracing"""
        try:
            from mcp_server_langgraph.observability.langsmith import langsmith_config

            if langsmith_config.is_enabled():
                if OBSERVABILITY_VERBOSE:
                    print("✓ LangSmith integration enabled")
                    print("  - Dual observability: OpenTelemetry + LangSmith")
            else:
                if OBSERVABILITY_VERBOSE:
                    print("⚠ LangSmith configured but not enabled (check API key)")

        except ImportError:
            if OBSERVABILITY_VERBOSE:
                print("⚠ LangSmith not available (install langsmith package)")
        except Exception as e:
            if OBSERVABILITY_VERBOSE:
                print(f"⚠ LangSmith setup failed: {e}")


# ============================================================================
# Lazy Initialization System
# ============================================================================

_observability_config: ObservabilityConfig | None = None
_propagator: TraceContextTextMapPropagator | None = None


def is_initialized() -> bool:
    """Check if observability has been initialized."""
    return _observability_config is not None


def init_observability(
    settings=None,
    service_name: str = SERVICE_NAME,
    otlp_endpoint: str = OTLP_ENDPOINT,
    enable_console_export: bool = True,
    enable_langsmith: bool = False,
    log_format: str = "json",
    log_json_indent: int | None = None,
    enable_file_logging: bool = False,
) -> ObservabilityConfig:
    """
    Initialize observability system (tracing, metrics, logging).

    MUST be called explicitly by entry points after configuration is loaded.
    This prevents circular imports and filesystem operations during module import.

    Args:
        settings: Settings object (optional, will use params if not provided)
        service_name: Service identifier
        otlp_endpoint: OpenTelemetry collector endpoint
        enable_console_export: Export to console for development
        enable_langsmith: Enable LangSmith integration
        log_format: "json" or "text"
        log_json_indent: JSON indent for pretty-printing (None for compact)
        enable_file_logging: Enable file-based log rotation (opt-in)

    Returns:
        Initialized ObservabilityConfig instance

    Example:
        >>> from mcp_server_langgraph.core.config import settings
        >>> from mcp_server_langgraph.observability.telemetry import init_observability
        >>> config = init_observability(settings, enable_file_logging=True)
    """
    global _observability_config, _propagator

    if _observability_config is not None:
        # Already initialized - return existing config
        return _observability_config

    # Extract settings if provided
    if settings is not None:
        enable_langsmith = settings.langsmith_tracing and settings.observability_backend in ("langsmith", "both")
        log_format = getattr(settings, "log_format", "json")
        log_json_indent = getattr(settings, "log_json_indent", None)
        otlp_endpoint = getattr(settings, "otlp_endpoint", OTLP_ENDPOINT)
        enable_console_export = getattr(settings, "enable_console_export", True)
        # enable_file_logging can be overridden via settings
        enable_file_logging = getattr(settings, "enable_file_logging", enable_file_logging)

    _observability_config = ObservabilityConfig(
        service_name=service_name,
        otlp_endpoint=otlp_endpoint,
        enable_console_export=enable_console_export,
        enable_langsmith=enable_langsmith,
        log_format=log_format,
        log_json_indent=log_json_indent,
        enable_file_logging=enable_file_logging,
    )

    _propagator = TraceContextTextMapPropagator()

    return _observability_config


def get_config() -> ObservabilityConfig:
    """
    Get observability config (lazy accessor).

    Raises RuntimeError if not initialized.
    """
    if _observability_config is None:
        raise RuntimeError(
            "Observability not initialized. Call init_observability(settings) "
            "in your entry point before using observability features."
        )
    return _observability_config


# Note: config is available via get_config() function or via the lazy 'config' proxy below


def get_tracer():
    """Get tracer instance (lazy accessor)."""
    return get_config().get_tracer()


def get_meter():
    """Get meter instance (lazy accessor)."""
    return get_config().get_meter()


def get_logger():
    """Get logger instance (lazy accessor)."""
    return get_config().get_logger()


# Module-level exports with lazy initialization
# These will raise RuntimeError if accessed before init_observability()
tracer = type("LazyTracer", (), {"__getattr__": lambda self, name: getattr(get_tracer(), name)})()

meter = type("LazyMeter", (), {"__getattr__": lambda self, name: getattr(get_meter(), name)})()

logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(get_logger(), name)})()

# Alias for backward compatibility - provides access to both config and metric instruments
config = type("LazyConfig", (), {"__getattr__": lambda self, name: getattr(get_config(), name)})()

metrics = config  # metrics is an alias for config


# Context propagation utilities
def inject_context(carrier: dict[str, str]) -> None:
    """Inject trace context into carrier (e.g., HTTP headers)"""
    if _propagator is None:
        raise RuntimeError("Observability not initialized. Call init_observability() first.")
    _propagator.inject(carrier)


def extract_context(carrier: dict[str, str]) -> Any:
    """Extract trace context from carrier"""
    if _propagator is None:
        raise RuntimeError("Observability not initialized. Call init_observability() first.")
    return _propagator.extract(carrier)
