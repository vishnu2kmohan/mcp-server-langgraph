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
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Conditional imports for OTLP exporters (optional dependencies)
try:
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as OTLPMetricExporterGRPC
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as OTLPSpanExporterGRPC

    GRPC_AVAILABLE = True
except ImportError:
    GRPC_AVAILABLE = False
    OTLPMetricExporterGRPC = None
    OTLPSpanExporterGRPC = None

try:
    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as OTLPMetricExporterHTTP
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPSpanExporterHTTP

    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    OTLPMetricExporterHTTP = None
    OTLPSpanExporterHTTP = None

from mcp_server_langgraph.observability.json_logger import CustomJSONFormatter

# Configuration
SERVICE_NAME = "mcp-server-langgraph"
OTLP_ENDPOINT = "http://localhost:4317"  # Change to your OTLP collector

# Control verbose logging (defaults to False to reduce noise)
# Set OBSERVABILITY_VERBOSE=true to enable detailed initialization logs
OBSERVABILITY_VERBOSE = os.getenv("OBSERVABILITY_VERBOSE", "false").lower() in ("true", "1", "yes")


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

    def _setup_tracing(self) -> None:
        """Configure distributed tracing"""
        # Get version from settings
        try:
            from mcp_server_langgraph.core.config import settings

            service_version = settings.service_version
        except Exception:
            from mcp_server_langgraph import __version__

            service_version = __version__

        # Get actual environment from settings instead of hardcoding "production"
        try:
            from mcp_server_langgraph.core.config import settings as config_settings

            environment = config_settings.environment
        except Exception:
            environment = "unknown"

        resource = Resource.create(
            {"service.name": self.service_name, "service.version": service_version, "deployment.environment": environment}
        )

        provider = TracerProvider(resource=resource)

        # OTLP exporter for production (if available)
        if GRPC_AVAILABLE and OTLPSpanExporterGRPC is not None:
            otlp_exporter = OTLPSpanExporterGRPC(endpoint=self.otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        elif HTTP_AVAILABLE and OTLPSpanExporterHTTP is not None:
            otlp_exporter = OTLPSpanExporterHTTP(endpoint=self.otlp_endpoint.replace(":4317", ":4318"))
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        elif OBSERVABILITY_VERBOSE:
            print("⚠ OTLP exporters not available, using console-only tracing")

        # Console exporter for development
        if self.enable_console_export:
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))

        trace.set_tracer_provider(provider)

        self.tracer_provider = provider  # Store provider for shutdown
        self.tracer = trace.get_tracer(__name__)
        if OBSERVABILITY_VERBOSE:
            print(f"✓ Tracing configured: {self.service_name}")

    def _setup_metrics(self) -> None:
        """Configure metrics collection"""
        resource = Resource.create({"service.name": self.service_name})

        readers = []

        # OTLP metric exporter (if available)
        if GRPC_AVAILABLE and OTLPMetricExporterGRPC is not None:
            otlp_metric_exporter = OTLPMetricExporterGRPC(endpoint=self.otlp_endpoint)
            otlp_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=5000)
            readers.append(otlp_reader)
        elif HTTP_AVAILABLE and OTLPMetricExporterHTTP is not None:
            otlp_metric_exporter = OTLPMetricExporterHTTP(endpoint=self.otlp_endpoint.replace(":4317", ":4318"))
            otlp_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=5000)
            readers.append(otlp_reader)
        elif OBSERVABILITY_VERBOSE:
            print("⚠ OTLP exporters not available, using console-only metrics")

        # Console exporter for development
        if self.enable_console_export:
            console_metric_exporter = ConsoleMetricExporter()
            console_reader = PeriodicExportingMetricReader(console_metric_exporter)
            readers.append(console_reader)

        provider = MeterProvider(resource=resource, metric_readers=readers)

        otel_metrics.set_meter_provider(provider)
        self.meter_provider = provider  # Store provider for shutdown
        self.meter = otel_metrics.get_meter(__name__)

        # Create common metrics
        self._create_metrics()
        if OBSERVABILITY_VERBOSE:
            print(f"✓ Metrics configured: {self.service_name}")

    def _create_metrics(self) -> None:
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

        # Resilience pattern metrics (ADR-0026)
        # Circuit breaker metrics
        self.circuit_breaker_state_gauge = self.meter.create_gauge(
            name="circuit_breaker.state",
            description="Circuit breaker state (0=closed, 1=open, 0.5=half-open)",
            unit="1",
        )
        self.circuit_breaker_failure_counter = self.meter.create_counter(
            name="circuit_breaker.failures",
            description="Total circuit breaker failures",
            unit="1",
        )
        self.circuit_breaker_success_counter = self.meter.create_counter(
            name="circuit_breaker.successes",
            description="Total circuit breaker successes",
            unit="1",
        )

        # Retry metrics
        self.retry_attempt_counter = self.meter.create_counter(
            name="retry.attempts",
            description="Total retry attempts",
            unit="1",
        )
        self.retry_exhausted_counter = self.meter.create_counter(
            name="retry.exhausted",
            description="Total retry exhaustion events",
            unit="1",
        )
        self.retry_success_after_retry_counter = self.meter.create_counter(
            name="retry.success_after_retry",
            description="Total successful retries",
            unit="1",
        )

        # Timeout metrics
        self.timeout_exceeded_counter = self.meter.create_counter(
            name="timeout.exceeded",
            description="Total timeout violations",
            unit="1",
        )
        self.timeout_duration_histogram = self.meter.create_histogram(
            name="timeout.duration",
            description="Timeout duration in seconds",
            unit="s",
        )

        # Bulkhead metrics
        self.bulkhead_rejected_counter = self.meter.create_counter(
            name="bulkhead.rejections",
            description="Total bulkhead rejections",
            unit="1",
        )
        self.bulkhead_active_operations_gauge = self.meter.create_gauge(
            name="bulkhead.active_operations",
            description="Current active operations in bulkhead",
            unit="1",
        )
        self.bulkhead_queue_depth_gauge = self.meter.create_gauge(
            name="bulkhead.queue_depth",
            description="Current queued operations in bulkhead",
            unit="1",
        )

        # Fallback metrics
        self.fallback_used_counter = self.meter.create_counter(
            name="fallback.used",
            description="Total fallback invocations",
            unit="1",
        )

        # Error counter by type (for custom exceptions)
        self.error_counter = self.meter.create_counter(
            name="error.total",
            description="Total errors by type",
            unit="1",
        )

    def _setup_logging(self, enable_file_logging: bool = False) -> None:
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
                print("✓ Logging already configured, reusing existing setup")
            return

        # Instrument logging to include trace context
        LoggingInstrumentor().instrument(set_logging_format=True)

        # Choose formatter based on log_format setting
        formatter: logging.Formatter
        console_formatter: logging.Formatter

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

        handlers: list[logging.Handler] = [console_handler]

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

    def get_tracer(self) -> trace.Tracer:
        """Get tracer instance"""
        return self.tracer

    def get_meter(self) -> otel_metrics.Meter:
        """Get meter instance"""
        return self.meter

    def get_logger(self) -> logging.Logger:
        """Get logger instance"""
        return self.logger

    def _setup_langsmith(self) -> None:
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
    settings: Any | None = None,
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


def shutdown_observability() -> None:
    """
    Shutdown observability system and flush all pending telemetry data.

    This function should be called during application shutdown to ensure:
    - All pending spans are flushed to exporters
    - All pending metrics are exported
    - HTTP connections to collectors are closed gracefully
    - No telemetry data is lost

    Usage:
        - Call from FastAPI lifespan shutdown event
        - Register with atexit.register() as fallback
        - Call in exception handlers before exit

    Thread Safety:
        This function is NOT thread-safe. Call only during shutdown when
        no new telemetry is being generated.
    """
    global _observability_config

    if _observability_config is None:
        return  # Nothing to shutdown

    try:
        # Flush tracer spans
        if hasattr(_observability_config, "tracer_provider"):
            tracer_provider = _observability_config.tracer_provider
            if hasattr(tracer_provider, "force_flush"):
                tracer_provider.force_flush(timeout_millis=5000)
                if OBSERVABILITY_VERBOSE:
                    print("✅ Flushed trace spans", file=sys.stderr)

            # Shutdown span processors
            if hasattr(tracer_provider, "shutdown"):
                tracer_provider.shutdown()
                if OBSERVABILITY_VERBOSE:
                    print("✅ Shutdown tracer provider", file=sys.stderr)

        # Flush and shutdown meter provider
        if hasattr(_observability_config, "meter_provider"):
            meter_provider = _observability_config.meter_provider
            if hasattr(meter_provider, "force_flush"):
                meter_provider.force_flush(timeout_millis=5000)
                if OBSERVABILITY_VERBOSE:
                    print("✅ Flushed metrics", file=sys.stderr)

            if hasattr(meter_provider, "shutdown"):
                meter_provider.shutdown()
                if OBSERVABILITY_VERBOSE:
                    print("✅ Shutdown meter provider", file=sys.stderr)

        if OBSERVABILITY_VERBOSE:
            print("✅ Observability system shutdown complete", file=sys.stderr)

    except Exception as e:
        # Log error but don't raise - shutdown should be graceful
        print(f"⚠️  Error during observability shutdown: {e}", file=sys.stderr)

    finally:
        _observability_config = None  # Mark as shutdown


# Note: config is available via get_config() function or via the lazy 'config' proxy below


def get_tracer() -> Any:
    """
    Get tracer instance (lazy accessor with safe fallback).

    Returns the configured tracer if observability is initialized,
    otherwise returns a no-op tracer that doesn't raise errors.

    Returns:
        Tracer instance (either ObservabilityConfig tracer or no-op tracer)
    """
    if _observability_config is None:
        # Return no-op tracer if observability not initialized
        from opentelemetry.trace import get_tracer as get_noop_tracer

        return get_noop_tracer(__name__)
    return get_config().get_tracer()


def get_meter() -> Any:
    """
    Get meter instance (lazy accessor with safe fallback).

    Returns the configured meter if observability is initialized,
    otherwise returns a no-op meter that doesn't raise errors.

    Returns:
        Meter instance (either ObservabilityConfig meter or no-op meter)
    """
    if _observability_config is None:
        # Return no-op meter if observability not initialized
        from opentelemetry.metrics import get_meter as get_noop_meter

        return get_noop_meter(__name__)
    return get_config().get_meter()


def get_logger() -> Any:
    """
    Get logger instance (lazy accessor with safe fallback).

    Returns the configured logger if observability is initialized,
    otherwise returns a basic Python logger that logs to stderr.

    This prevents RuntimeError when functions like create_user_provider()
    or create_session_store() are called before init_observability()
    (e.g., in test fixtures or standalone scripts).

    Returns:
        Logger instance (either ObservabilityConfig logger or fallback logger)
    """
    if _observability_config is None:
        # Return fallback logger if observability not initialized
        # Uses standard Python logging to stderr
        fallback_logger = logging.getLogger("mcp-server-langgraph-fallback")
        if not fallback_logger.handlers:
            # Configure fallback logger on first use
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
            fallback_logger.addHandler(handler)
            fallback_logger.setLevel(logging.INFO)
        return fallback_logger
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


# Resilience pattern metrics (convenient exports for resilience module)
# These are lazy proxies that will raise RuntimeError if accessed before init_observability()
circuit_breaker_state_gauge = type(
    "LazyMetric",
    (),
    {
        "add": lambda self, *args, **kwargs: config.circuit_breaker_state_gauge.add(*args, **kwargs),
        "set": lambda self, *args, **kwargs: config.circuit_breaker_state_gauge.set(*args, **kwargs),
    },
)()

circuit_breaker_failure_counter = type(
    "LazyMetric", (), {"add": lambda self, *args, **kwargs: config.circuit_breaker_failure_counter.add(*args, **kwargs)}
)()

circuit_breaker_success_counter = type(
    "LazyMetric", (), {"add": lambda self, *args, **kwargs: config.circuit_breaker_success_counter.add(*args, **kwargs)}
)()

retry_attempt_counter = type(
    "LazyMetric", (), {"add": lambda self, *args, **kwargs: config.retry_attempt_counter.add(*args, **kwargs)}
)()

retry_exhausted_counter = type(
    "LazyMetric", (), {"add": lambda self, *args, **kwargs: config.retry_exhausted_counter.add(*args, **kwargs)}
)()

retry_success_after_retry_counter = type(
    "LazyMetric", (), {"add": lambda self, *args, **kwargs: config.retry_success_after_retry_counter.add(*args, **kwargs)}
)()

timeout_exceeded_counter = type(
    "LazyMetric", (), {"add": lambda self, *args, **kwargs: config.timeout_exceeded_counter.add(*args, **kwargs)}
)()

timeout_duration_histogram = type(
    "LazyMetric", (), {"record": lambda self, *args, **kwargs: config.timeout_duration_histogram.record(*args, **kwargs)}
)()

bulkhead_rejected_counter = type(
    "LazyMetric", (), {"add": lambda self, *args, **kwargs: config.bulkhead_rejected_counter.add(*args, **kwargs)}
)()

bulkhead_active_operations_gauge = type(
    "LazyMetric", (), {"set": lambda self, *args, **kwargs: config.bulkhead_active_operations_gauge.set(*args, **kwargs)}
)()

bulkhead_queue_depth_gauge = type(
    "LazyMetric", (), {"set": lambda self, *args, **kwargs: config.bulkhead_queue_depth_gauge.set(*args, **kwargs)}
)()

fallback_used_counter = type(
    "LazyMetric", (), {"add": lambda self, *args, **kwargs: config.fallback_used_counter.add(*args, **kwargs)}
)()

error_counter = type("LazyMetric", (), {"add": lambda self, *args, **kwargs: config.error_counter.add(*args, **kwargs)})()
