"""
OpenTelemetry observability setup with tracing, logging, and metrics
"""
import logging
import sys
from typing import Any

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Configuration
SERVICE_NAME = "langgraph-mcp-agent"
OTLP_ENDPOINT = "http://localhost:4317"  # Change to your OTLP collector


class ObservabilityConfig:
    """Centralized observability configuration"""

    def __init__(
        self,
        service_name: str = SERVICE_NAME,
        otlp_endpoint: str = OTLP_ENDPOINT,
        enable_console_export: bool = True
    ):
        self.service_name = service_name
        self.otlp_endpoint = otlp_endpoint
        self.enable_console_export = enable_console_export

        self._setup_tracing()
        self._setup_metrics()
        self._setup_logging()

    def _setup_tracing(self):
        """Configure distributed tracing"""
        resource = Resource.create({
            "service.name": self.service_name,
            "service.version": "1.0.0",
            "deployment.environment": "production"
        })

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
        print(f"✓ Tracing configured: {self.service_name}")

    def _setup_metrics(self):
        """Configure metrics collection"""
        resource = Resource.create({
            "service.name": self.service_name
        })

        # OTLP metric exporter
        otlp_metric_exporter = OTLPMetricExporter(endpoint=self.otlp_endpoint)
        otlp_reader = PeriodicExportingMetricReader(otlp_metric_exporter, export_interval_millis=5000)

        readers = [otlp_reader]

        # Console exporter for development
        if self.enable_console_export:
            console_metric_exporter = ConsoleMetricExporter()
            console_reader = PeriodicExportingMetricReader(console_metric_exporter)
            readers.append(console_reader)

        provider = MeterProvider(
            resource=resource,
            metric_readers=readers
        )

        metrics.set_meter_provider(provider)
        self.meter = metrics.get_meter(__name__)

        # Create common metrics
        self._create_metrics()
        print(f"✓ Metrics configured: {self.service_name}")

    def _create_metrics(self):
        """Create standard metrics for the service"""
        self.tool_calls = self.meter.create_counter(
            name="agent.tool.calls",
            description="Number of tool calls",
            unit="1"
        )

        self.successful_calls = self.meter.create_counter(
            name="agent.calls.successful",
            description="Number of successful calls",
            unit="1"
        )

        self.failed_calls = self.meter.create_counter(
            name="agent.calls.failed",
            description="Number of failed calls",
            unit="1"
        )

        self.auth_failures = self.meter.create_counter(
            name="auth.failures",
            description="Number of authentication failures",
            unit="1"
        )

        self.authz_failures = self.meter.create_counter(
            name="authz.failures",
            description="Number of authorization failures",
            unit="1"
        )

        self.response_time = self.meter.create_histogram(
            name="agent.response.duration",
            description="Response time distribution",
            unit="ms"
        )

    def _setup_logging(self):
        """Configure structured logging with OpenTelemetry"""
        # Instrument logging to include trace context
        LoggingInstrumentor().instrument(set_logging_format=True)

        # Configure root logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s] - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'{self.service_name}.log')
            ]
        )

        self.logger = logging.getLogger(self.service_name)
        print(f"✓ Logging configured: {self.service_name}")

    def get_tracer(self):
        """Get tracer instance"""
        return self.tracer

    def get_meter(self):
        """Get meter instance"""
        return self.meter

    def get_logger(self):
        """Get logger instance"""
        return self.logger


# Initialize global observability
config = ObservabilityConfig()
tracer = config.get_tracer()
meter = config.get_meter()
logger = config.get_logger()
metrics = config  # For easy access to metric instruments


# Context propagation utilities
propagator = TraceContextTextMapPropagator()


def inject_context(carrier: dict[str, str]) -> None:
    """Inject trace context into carrier (e.g., HTTP headers)"""
    propagator.inject(carrier)


def extract_context(carrier: dict[str, str]) -> Any:
    """Extract trace context from carrier"""
    return propagator.extract(carrier)
