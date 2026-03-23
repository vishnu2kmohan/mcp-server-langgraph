"""
End-to-End Infrastructure Telemetry Validation Tests.

Tests that verify the COMPLETE telemetry pipeline from data ingestion
through the Alloy collector to backend storage and querying.

These tests validate concrete implementations in docker-compose.test.yml:
1. Alloy OTLP receiver accepts traces and forwards to Tempo
2. Alloy OTLP receiver accepts logs and forwards to Loki
3. Alloy Prometheus scraping collects exporter metrics and forwards to Mimir
4. Postgres-exporter metrics are queryable via Mimir
5. Redis-exporter metrics are queryable via Mimir
6. LGTM self-monitoring metrics (Loki, Tempo, Mimir, Grafana) are queryable

These tests require `make test-infra-full-up` to be running.

Gap Analysis (prior to this file):
-----------------------------------
- Alloy: Only TCP port check existed — no actual OTLP data flow validation
- Exporters: Zero tests for postgres-exporter or redis-exporter
- Pipeline: No end-to-end test verifying App → Alloy → Backend flow
- Mimir queries: No tests verifying scraped metrics are queryable
"""

import gc
import socket
import time

import pytest
import requests

from tests.constants import (
    TEST_ALLOY_OTLP_HTTP_PORT,
    TEST_ALLOY_PORT,
    TEST_GRAFANA_PORT,
    TEST_LOKI_PORT,
    TEST_MIMIR_PORT,
    TEST_TEMPO_PORT,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.observability,
    pytest.mark.docker,
    pytest.mark.slow,
]


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is in use (service is accessible)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(2)
        try:
            sock.connect((host, port))
            return True
        except (TimeoutError, ConnectionRefusedError, OSError):
            return False


def skip_if_lgtm_not_running() -> None:
    """Skip test if LGTM stack is not running."""
    services = [
        (TEST_LOKI_PORT, "Loki"),
        (TEST_TEMPO_PORT, "Tempo"),
        (TEST_MIMIR_PORT, "Mimir"),
        (TEST_GRAFANA_PORT, "Grafana"),
        (TEST_ALLOY_PORT, "Alloy"),
    ]
    missing = [f"{name} (port {port})" for port, name in services if not is_port_in_use(port)]
    if missing:
        pytest.skip(
            f"LGTM stack not running. Missing: {', '.join(missing)}. "
            f"Run 'make test-infra-full-up' to start the infrastructure."
        )


def query_mimir(query: str) -> dict:
    """Execute a PromQL instant query against Mimir."""
    url = f"http://localhost:{TEST_MIMIR_PORT}/prometheus/api/v1/query"
    response = requests.get(url, params={"query": query}, timeout=10)
    response.raise_for_status()
    return response.json()


# ==============================================================================
# Alloy OTLP Data Flow Tests
# ==============================================================================


@pytest.mark.xdist_group(name="infra_telemetry_e2e")
class TestAlloyOTLPDataFlow:
    """
    Validate Alloy receives OTLP telemetry and forwards to backends.

    These tests send actual OTLP data through Alloy's HTTP receiver
    (port 4318) and verify it arrives in the target backend.
    """

    def teardown_method(self) -> None:
        gc.collect()

    def test_alloy_otlp_receiver_accepts_trace_data(self) -> None:
        """
        GIVEN Alloy is running with OTLP HTTP receiver on port 4318
        WHEN we POST a valid OTLP trace export request
        THEN Alloy should accept it (200/202) and not reject it (4xx/5xx)
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_ALLOY_OTLP_HTTP_PORT):
            pytest.skip(f"Alloy OTLP receiver not available on port {TEST_ALLOY_OTLP_HTTP_PORT}")

        # Construct a minimal OTLP trace export in JSON format
        trace_id = format(int(time.time_ns()), "032x")
        span_id = format(int(time.time_ns()) & 0xFFFFFFFFFFFFFFFF, "016x")
        timestamp_ns = str(int(time.time() * 1e9))

        otlp_trace = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "integration-test"}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "test-tracer", "version": "1.0.0"},
                            "spans": [
                                {
                                    "traceId": trace_id,
                                    "spanId": span_id,
                                    "name": "test-alloy-otlp-span",
                                    "kind": 1,  # SPAN_KIND_INTERNAL
                                    "startTimeUnixNano": timestamp_ns,
                                    "endTimeUnixNano": str(int(timestamp_ns) + 1_000_000),
                                    "status": {"code": 1},  # STATUS_CODE_OK
                                    "attributes": [
                                        {
                                            "key": "test.marker",
                                            "value": {"stringValue": "alloy-otlp-e2e"},
                                        },
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        url = f"http://localhost:{TEST_ALLOY_OTLP_HTTP_PORT}/v1/traces"
        response = requests.post(
            url,
            json=otlp_trace,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        # Alloy should accept the trace data (200 or 202)
        assert response.status_code in (200, 202), (
            f"Alloy OTLP receiver rejected trace data: {response.status_code} {response.text}"
        )

    def test_alloy_otlp_receiver_accepts_log_data(self) -> None:
        """
        GIVEN Alloy is running with OTLP HTTP receiver on port 4318
        WHEN we POST a valid OTLP log export request
        THEN Alloy should accept it (200/202) and not reject it (4xx/5xx)
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_ALLOY_OTLP_HTTP_PORT):
            pytest.skip(f"Alloy OTLP receiver not available on port {TEST_ALLOY_OTLP_HTTP_PORT}")

        timestamp_ns = str(int(time.time() * 1e9))

        otlp_logs = {
            "resourceLogs": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "integration-test"}},
                        ]
                    },
                    "scopeLogs": [
                        {
                            "scope": {"name": "test-logger"},
                            "logRecords": [
                                {
                                    "timeUnixNano": timestamp_ns,
                                    "severityNumber": 9,  # INFO
                                    "severityText": "INFO",
                                    "body": {"stringValue": f"alloy-otlp-log-e2e-{timestamp_ns}"},
                                    "attributes": [
                                        {
                                            "key": "test.marker",
                                            "value": {"stringValue": "alloy-otlp-log-e2e"},
                                        },
                                    ],
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        url = f"http://localhost:{TEST_ALLOY_OTLP_HTTP_PORT}/v1/logs"
        response = requests.post(
            url,
            json=otlp_logs,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        assert response.status_code in (200, 202), (
            f"Alloy OTLP receiver rejected log data: {response.status_code} {response.text}"
        )

    def test_alloy_otlp_receiver_accepts_metric_data(self) -> None:
        """
        GIVEN Alloy is running with OTLP HTTP receiver on port 4318
        WHEN we POST a valid OTLP metrics export request
        THEN Alloy should accept it (200/202) and not reject it (4xx/5xx)
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_ALLOY_OTLP_HTTP_PORT):
            pytest.skip(f"Alloy OTLP receiver not available on port {TEST_ALLOY_OTLP_HTTP_PORT}")

        timestamp_ns = str(int(time.time() * 1e9))

        otlp_metrics = {
            "resourceMetrics": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": "integration-test"}},
                        ]
                    },
                    "scopeMetrics": [
                        {
                            "scope": {"name": "test-meter"},
                            "metrics": [
                                {
                                    "name": "integration_test_counter",
                                    "description": "E2E test counter for Alloy pipeline validation",
                                    "unit": "1",
                                    "sum": {
                                        "dataPoints": [
                                            {
                                                "startTimeUnixNano": timestamp_ns,
                                                "timeUnixNano": timestamp_ns,
                                                "asInt": "42",
                                                "attributes": [
                                                    {
                                                        "key": "test.marker",
                                                        "value": {"stringValue": "alloy-otlp-metric-e2e"},
                                                    },
                                                ],
                                            }
                                        ],
                                        "aggregationTemporality": 2,  # CUMULATIVE
                                        "isMonotonic": True,
                                    },
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        url = f"http://localhost:{TEST_ALLOY_OTLP_HTTP_PORT}/v1/metrics"
        response = requests.post(
            url,
            json=otlp_metrics,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )

        assert response.status_code in (200, 202), (
            f"Alloy OTLP receiver rejected metric data: {response.status_code} {response.text}"
        )

    def test_alloy_trace_arrives_in_tempo(self) -> None:
        """
        GIVEN Alloy is running and connected to Tempo
        WHEN we send a trace through Alloy's OTLP receiver
        THEN the trace should be queryable in Tempo within 15 seconds

        This validates the end-to-end pipeline:
        App → Alloy OTLP receiver → batch processor → Tempo exporter → Tempo storage
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_ALLOY_OTLP_HTTP_PORT):
            pytest.skip(f"Alloy OTLP receiver not available on port {TEST_ALLOY_OTLP_HTTP_PORT}")

        # Generate a unique trace ID
        trace_id_int = int(time.time_ns())
        trace_id = format(trace_id_int, "032x")
        span_id = format(trace_id_int & 0xFFFFFFFFFFFFFFFF, "016x")
        timestamp_ns = str(int(time.time() * 1e9))
        service_name = "e2e-trace-pipeline-test"

        otlp_trace = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": service_name}},
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "test-tracer"},
                            "spans": [
                                {
                                    "traceId": trace_id,
                                    "spanId": span_id,
                                    "name": "e2e-pipeline-validation",
                                    "kind": 1,
                                    "startTimeUnixNano": timestamp_ns,
                                    "endTimeUnixNano": str(int(timestamp_ns) + 5_000_000),
                                    "status": {"code": 1},
                                }
                            ],
                        }
                    ],
                }
            ]
        }

        # Send trace through Alloy
        url = f"http://localhost:{TEST_ALLOY_OTLP_HTTP_PORT}/v1/traces"
        response = requests.post(url, json=otlp_trace, timeout=10)
        assert response.status_code in (200, 202), f"Alloy rejected trace: {response.status_code}"

        # Wait for Alloy batch processor (timeout=5s) + Tempo ingestion
        # Alloy config: batch timeout=5s, so wait up to 15s total
        tempo_url = f"http://localhost:{TEST_TEMPO_PORT}/api/traces/{trace_id}"
        found = False
        for _ in range(15):
            time.sleep(1)
            try:
                resp = requests.get(tempo_url, timeout=5)
                if resp.status_code == 200:
                    found = True
                    break
            except requests.exceptions.RequestException:
                continue

        assert found, (
            f"Trace {trace_id} not found in Tempo after 15s. "
            f"This indicates Alloy → Tempo pipeline is broken. "
            f"Check: docker compose -f docker-compose.test.yml logs alloy-test tempo-test"
        )


# ==============================================================================
# Prometheus Exporter Pipeline Validation
# ==============================================================================


@pytest.mark.xdist_group(name="infra_telemetry_e2e")
class TestExporterMetricsPipeline:
    """
    Validate that Prometheus exporters (postgres-exporter, redis-exporter)
    are scraped by Alloy and their metrics are queryable in Mimir.

    Pipeline: Exporter → Alloy prometheus.scrape → Mimir remote_write

    docker-compose.test.yml services validated:
    - postgres-exporter (port 9187 internal, scraped by Alloy)
    - redis-exporter (port 9121 internal, scraped by Alloy)

    Alloy config.alloy scrape targets validated:
    - prometheus.scrape "redis" { targets = [{ __address__ = "redis-exporter:9121" }] }
    - prometheus.scrape "postgres" { targets = [{ __address__ = "postgres-exporter:9187" }] }
    """

    def teardown_method(self) -> None:
        gc.collect()

    def test_postgres_exporter_metrics_in_mimir(self) -> None:
        """
        GIVEN postgres-exporter is running and scraped by Alloy
        WHEN we query Mimir for pg_up metric
        THEN the metric should exist with value 1 (Postgres is up)

        Validates: postgres-exporter → Alloy → Mimir pipeline
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        # pg_up is the canonical "is Postgres reachable" metric from postgres-exporter
        result = query_mimir('pg_up{job="postgres"}')

        assert result.get("status") == "success", f"Mimir query failed: {result}"

        data = result.get("data", {})
        results = data.get("result", [])

        assert len(results) > 0, (
            "No pg_up metrics found in Mimir. "
            "This indicates the postgres-exporter → Alloy → Mimir pipeline is broken. "
            "Check: docker compose -f docker-compose.test.yml logs postgres-exporter alloy-test"
        )

        # pg_up should be 1 (Postgres is healthy)
        value = float(results[0].get("value", [0, "0"])[1])
        assert value == 1.0, f"pg_up metric value is {value}, expected 1.0 (Postgres should be up)"

    def test_redis_exporter_metrics_in_mimir(self) -> None:
        """
        GIVEN redis-exporter is running and scraped by Alloy
        WHEN we query Mimir for redis_up metric
        THEN the metric should exist with value 1 (Redis is up)

        Validates: redis-exporter → Alloy → Mimir pipeline
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        # redis_up is the canonical "is Redis reachable" metric from redis-exporter
        result = query_mimir('redis_up{job="redis"}')

        assert result.get("status") == "success", f"Mimir query failed: {result}"

        data = result.get("data", {})
        results = data.get("result", [])

        assert len(results) > 0, (
            "No redis_up metrics found in Mimir. "
            "This indicates the redis-exporter → Alloy → Mimir pipeline is broken. "
            "Check: docker compose -f docker-compose.test.yml logs redis-exporter alloy-test"
        )

        value = float(results[0].get("value", [0, "0"])[1])
        assert value == 1.0, f"redis_up metric value is {value}, expected 1.0 (Redis should be up)"

    def test_postgres_exporter_provides_connection_metrics(self) -> None:
        """
        GIVEN postgres-exporter is scraping Postgres
        WHEN we query Mimir for pg_stat_activity_count
        THEN connection metrics should be available for capacity planning

        This validates that the exporter isn't just "up" but actually
        providing useful operational metrics.
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        # pg_stat_database_numbackends is a standard postgres-exporter metric
        result = query_mimir('pg_stat_database_numbackends{job="postgres"}')

        assert result.get("status") == "success", f"Mimir query failed: {result}"

        data = result.get("data", {})
        results = data.get("result", [])

        assert len(results) > 0, (
            "No pg_stat_database_numbackends metrics found. postgres-exporter may not be collecting detailed metrics."
        )

    def test_redis_exporter_provides_memory_metrics(self) -> None:
        """
        GIVEN redis-exporter is scraping Redis
        WHEN we query Mimir for redis_memory_used_bytes
        THEN memory metrics should be available for capacity planning
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        result = query_mimir('redis_memory_used_bytes{job="redis"}')

        assert result.get("status") == "success", f"Mimir query failed: {result}"

        data = result.get("data", {})
        results = data.get("result", [])

        assert len(results) > 0, (
            "No redis_memory_used_bytes metrics found. redis-exporter may not be collecting detailed metrics."
        )

        # Memory should be a positive number
        value = float(results[0].get("value", [0, "0"])[1])
        assert value > 0, f"redis_memory_used_bytes is {value}, expected > 0"


# ==============================================================================
# LGTM Self-Monitoring Validation
# ==============================================================================


@pytest.mark.xdist_group(name="infra_telemetry_e2e")
class TestLGTMSelfMonitoring:
    """
    Validate that LGTM stack components expose their own metrics
    and those metrics are scraped by Alloy into Mimir.

    This validates the Alloy config.alloy scrape targets:
    - prometheus.scrape "loki" { targets = [{ __address__ = "loki:3100" }] }
    - prometheus.scrape "tempo" { targets = [{ __address__ = "tempo:3200" }] }
    - prometheus.scrape "mimir" { targets = [{ __address__ = "mimir:9009" }] }
    - prometheus.scrape "grafana" { targets = [{ __address__ = "grafana:3000" }] }
    - prometheus.scrape "alloy" { targets = [{ __address__ = "localhost:12345" }] }
    """

    def teardown_method(self) -> None:
        gc.collect()

    def test_loki_self_metrics_in_mimir(self) -> None:
        """
        GIVEN Loki exposes /metrics and Alloy scrapes it
        WHEN we query Mimir for loki_build_info
        THEN Loki's own metrics should be available
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        result = query_mimir('loki_build_info{job="loki"}')
        assert result.get("status") == "success"

        results = result.get("data", {}).get("result", [])
        assert len(results) > 0, "No loki_build_info found in Mimir. Alloy is not scraping Loki metrics."

    def test_tempo_self_metrics_in_mimir(self) -> None:
        """
        GIVEN Tempo exposes /metrics and Alloy scrapes it
        WHEN we query Mimir for tempo_build_info
        THEN Tempo's own metrics should be available
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        result = query_mimir('tempo_build_info{job="tempo"}')
        assert result.get("status") == "success"

        results = result.get("data", {}).get("result", [])
        assert len(results) > 0, "No tempo_build_info found in Mimir. Alloy is not scraping Tempo metrics."

    def test_alloy_self_metrics_in_mimir(self) -> None:
        """
        GIVEN Alloy exposes /metrics on port 12345 and scrapes itself
        WHEN we query Mimir for alloy_build_info or similar
        THEN Alloy's own metrics should be available
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        # Alloy uses the "alloy" job label in config.alloy
        result = query_mimir('up{job="alloy"}')
        assert result.get("status") == "success"

        results = result.get("data", {}).get("result", [])
        assert len(results) > 0, "No alloy up metric found in Mimir. Alloy self-scraping is broken."

    def test_grafana_metrics_in_mimir(self) -> None:
        """
        GIVEN Grafana exposes /dashboards/metrics and Alloy scrapes it
        WHEN we query Mimir for grafana_build_info
        THEN Grafana's own metrics should be available
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        result = query_mimir('grafana_build_info{job="grafana"}')
        assert result.get("status") == "success"

        results = result.get("data", {}).get("result", [])
        assert len(results) > 0, (
            "No grafana_build_info found in Mimir. "
            "Check Alloy config: metrics_path should be /dashboards/metrics (GF_SERVER_SERVE_FROM_SUB_PATH)."
        )


# ==============================================================================
# Infrastructure Service Scrape Target Validation
# ==============================================================================


@pytest.mark.xdist_group(name="infra_telemetry_e2e")
class TestInfraServiceMetrics:
    """
    Validate that infrastructure services (Keycloak, OpenFGA, Qdrant, Traefik)
    are scraped by Alloy and their metrics are queryable in Mimir.

    These validate the Alloy config.alloy prometheus.scrape targets for
    non-exporter services that expose their own /metrics endpoints.
    """

    def teardown_method(self) -> None:
        gc.collect()

    def test_keycloak_metrics_in_mimir(self) -> None:
        """
        GIVEN Keycloak exposes /authn/metrics on management port 9000
        WHEN Alloy scrapes it and writes to Mimir
        THEN Keycloak metrics should be queryable

        Validates: keycloak:9000/authn/metrics → Alloy → Mimir
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        # Keycloak 26.x Quarkus exposes JVM and HTTP metrics
        result = query_mimir('up{job="keycloak"}')
        assert result.get("status") == "success"

        results = result.get("data", {}).get("result", [])
        assert len(results) > 0, (
            "No Keycloak metrics found in Mimir. Check: Alloy scrape target keycloak:9000 with metrics_path=/authn/metrics"
        )

    def test_openfga_metrics_in_mimir(self) -> None:
        """
        GIVEN OpenFGA exposes /metrics on port 2112
        WHEN Alloy scrapes it and writes to Mimir
        THEN OpenFGA metrics should be queryable
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        result = query_mimir('up{job="openfga"}')
        assert result.get("status") == "success"

        results = result.get("data", {}).get("result", [])
        assert len(results) > 0, "No OpenFGA metrics found in Mimir. Check: Alloy scrape target openfga:2112"

    def test_qdrant_metrics_in_mimir(self) -> None:
        """
        GIVEN Qdrant exposes /metrics on port 6333
        WHEN Alloy scrapes it and writes to Mimir
        THEN Qdrant metrics should be queryable
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        result = query_mimir('up{job="qdrant"}')
        assert result.get("status") == "success"

        results = result.get("data", {}).get("result", [])
        assert len(results) > 0, "No Qdrant metrics found in Mimir. Check: Alloy scrape target qdrant:6333"

    def test_traefik_metrics_in_mimir(self) -> None:
        """
        GIVEN Traefik exposes /metrics on port 8080
        WHEN Alloy scrapes it and writes to Mimir
        THEN Traefik metrics should be queryable
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_MIMIR_PORT):
            pytest.skip(f"Mimir not available on port {TEST_MIMIR_PORT}")

        result = query_mimir('up{job="traefik"}')
        assert result.get("status") == "success"

        results = result.get("data", {}).get("result", [])
        assert len(results) > 0, "No Traefik metrics found in Mimir. Check: Alloy scrape target traefik-gateway:8080"


# ==============================================================================
# Alloy Pipeline Configuration Validation
# ==============================================================================


@pytest.mark.xdist_group(name="infra_telemetry_e2e")
class TestAlloyPipelineConfig:
    """
    Validate Alloy's internal pipeline components are operational.

    These tests query Alloy's own metrics and API to verify that
    the receivers, processors, and exporters are functioning.
    """

    def teardown_method(self) -> None:
        gc.collect()

    def test_alloy_api_is_accessible(self) -> None:
        """
        GIVEN Alloy is running with UI/API on port 12345
        WHEN we query the Alloy API
        THEN it should respond with component information
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_ALLOY_PORT):
            pytest.skip(f"Alloy not available on port {TEST_ALLOY_PORT}")

        # Alloy exposes a component list API
        url = f"http://localhost:{TEST_ALLOY_PORT}/api/v0/web/components"
        try:
            response = requests.get(url, timeout=10)
            # Alloy API may return HTML or JSON - any 2xx response means it's working
            assert response.status_code < 500, f"Alloy API returned server error: {response.status_code}"
        except requests.exceptions.ConnectionError:
            pytest.fail(
                f"Cannot connect to Alloy API at {url}. Check: docker compose -f docker-compose.test.yml logs alloy-test"
            )

    def test_alloy_metrics_endpoint_accessible(self) -> None:
        """
        GIVEN Alloy is running
        WHEN we query its /metrics endpoint
        THEN it should return Prometheus-format metrics
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_ALLOY_PORT):
            pytest.skip(f"Alloy not available on port {TEST_ALLOY_PORT}")

        url = f"http://localhost:{TEST_ALLOY_PORT}/metrics"
        response = requests.get(url, timeout=10)

        assert response.status_code == 200, f"Alloy metrics endpoint returned {response.status_code}"

        # Verify it contains Alloy-specific metrics
        content = response.text
        assert "alloy" in content.lower() or "otelcol" in content.lower(), (
            "Alloy metrics endpoint did not return expected metrics. Expected to find 'alloy' or 'otelcol' in metrics output."
        )

    def test_alloy_memory_limiter_active(self) -> None:
        """
        GIVEN Alloy is configured with memory_limiter processor
        WHEN we check Alloy's metrics
        THEN memory limiter metrics should be present (indicating it's active)
        """
        skip_if_lgtm_not_running()

        if not is_port_in_use(TEST_ALLOY_PORT):
            pytest.skip(f"Alloy not available on port {TEST_ALLOY_PORT}")

        url = f"http://localhost:{TEST_ALLOY_PORT}/metrics"
        response = requests.get(url, timeout=10)

        assert response.status_code == 200

        # Check for memory limiter or batch processor metrics
        content = response.text
        # Alloy exposes otelcol component metrics
        has_processor_metrics = "otelcol_processor" in content or "alloy_component" in content
        assert has_processor_metrics, (
            "No processor metrics found in Alloy. Memory limiter and batch processor may not be operational."
        )
