"""
Integration tests for observability infrastructure.

This package contains integration tests for the Grafana LGTM stack:
- Loki (log aggregation)
- Grafana (dashboards and unified alerting)
- Tempo (distributed tracing)
- Mimir (metrics storage)
- Alloy (unified telemetry collector)

These tests verify that the observability infrastructure is properly configured
and functional when `make test-infra-full-up` is executed.
"""
