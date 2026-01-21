"""
Data Flow Integration Tests.

This package contains E2E integration tests that verify complete data flows
from producers (LLM factory, agent orchestrator, etc.) through storage
to API endpoints.

These tests are designed to catch wiring bugs where individual components
work in isolation but the end-to-end data flow is broken.
"""
