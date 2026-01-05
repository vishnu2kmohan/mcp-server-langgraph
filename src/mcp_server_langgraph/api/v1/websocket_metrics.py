"""
WebSocket Metrics API.

REST endpoint for receiving frontend WebSocket reconnection metrics.
Metrics are recorded in Prometheus for observability via Grafana.

Flow:
  Frontend (useWebSocketMetricsReporter)
    -> POST /api/v1/websocket/metrics
    -> Prometheus counters/histograms
    -> Grafana dashboard
"""

import logging
from typing import Any

from fastapi import APIRouter

from mcp_server_langgraph.websocket.metrics import (
    WebSocketBatchMetricsPayload,
    WebSocketMetricsPayload,
    process_batch_metrics,
    process_metrics_payload,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket-metrics"])


@router.post("/websocket/metrics")
async def submit_websocket_metrics(
    payload: WebSocketMetricsPayload,
) -> dict[str, Any]:
    """
    Submit WebSocket reconnection metrics from frontend.

    This endpoint receives metrics from the frontend's useWebSocketMetricsReporter
    hook and records them in Prometheus for observability.

    The endpoint follows a fire-and-forget pattern - it always returns 200
    even if Prometheus is unavailable, to avoid blocking the frontend.

    Args:
        payload: WebSocket metrics for a single endpoint

    Returns:
        Status response indicating metrics were accepted
    """
    try:
        process_metrics_payload(payload)
        logger.debug(
            "Recorded WebSocket metrics for endpoint: %s",
            payload.endpoint_id,
        )
    except Exception as e:
        # Fire-and-forget: log but don't fail the request
        logger.warning(
            "Failed to record WebSocket metrics for %s: %s",
            payload.endpoint_id,
            str(e),
        )

    return {
        "status": "accepted",
        "endpoint_id": payload.endpoint_id,
    }


@router.post("/websocket/metrics/batch")
async def submit_batch_websocket_metrics(
    payload: WebSocketBatchMetricsPayload,
) -> dict[str, Any]:
    """
    Submit WebSocket reconnection metrics for multiple endpoints.

    This endpoint receives batch metrics from the frontend, typically
    submitted periodically or on page unload to minimize API calls.

    Args:
        payload: Batch of WebSocket metrics for multiple endpoints

    Returns:
        Status response with count of processed endpoints
    """
    processed_count = 0

    try:
        process_batch_metrics(payload)
        processed_count = len(payload.endpoints)
        logger.debug(
            "Recorded batch WebSocket metrics for %d endpoints",
            processed_count,
        )
    except Exception as e:
        # Fire-and-forget: log but don't fail the request
        logger.warning(
            "Failed to record batch WebSocket metrics: %s",
            str(e),
        )
        # Still report how many we attempted
        processed_count = len(payload.endpoints)

    return {
        "status": "accepted",
        "processed": processed_count,
    }
