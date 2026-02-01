#!/usr/bin/env python3
"""
Generate WebSocket hook permission control test files.

This script creates permission test files for all WebSocket hooks that
implement permission-based connection control.

Each hook requires:
1. Authentication (isAuthenticated=true)
2. Specific permission (wsPermissions.<permission>=true)

When either condition is false, URL should be empty "" to prevent connection.
"""

import os

HOOKS = [
    # (hook_name, permission_key, ws_endpoint)
    ("useAISuggestionsWebSocket", "ai_suggestions", "/api/v1/ws/ai/suggestions"),
    ("useNotificationWebSocket", "notifications", "/api/v1/ws/notifications"),
    ("useCostTrackingWebSocket", "cost_tracking", "/api/v1/ws/cost/tracking"),
    ("useAgentRequestWebSocket", "agent_requests", "/api/v1/ws/agent-requests"),
    ("useHeartMetricsWebSocket", "heart_metrics", "/api/v1/ws/metrics/heart"),
    ("useBudgetAlertsWebSocket", "budget_alerts", "/api/v1/ws/budget/alerts"),
    ("useAlertWebSocket", "alerts", "/api/v1/ws/alerts"),
    ("useTraceWebSocket", "traces", "/api/v1/ws/traces"),
    ("useAuditWebSocket", "audit", "/api/v1/ws/audit"),
    ("useConnectionsRealtimeWebSocket", "connections_realtime", "/api/v1/ws/connections/realtime"),
    ("useMCPWebSocket", "mcp_aggregated", "/api/v1/ws/mcp"),
    ("useMCPTaskWebSocket", "mcp_tasks", "/api/v1/ws/mcp/tasks"),
]

TEMPLATE = """/**
 * Permission-based Connection Control Tests for {hook_name}
 *
 * Security requirement: WebSocket connections must only be established when:
 * 1. User is authenticated (isAuthenticated=true)
 * 2. User has {permission_key} permission (wsPermissions.{permission_key}=true)
 *
 * When either condition is false, URL should be empty string "" to prevent connection.
 */

import {{ renderHook, cleanup }} from "@testing-library/react";
import {{ describe, it, expect, vi, beforeEach, afterEach }} from "vitest";
import {{ {hook_name} }} from "./{hook_name}";

// Default metrics matching ReconnectionMetrics interface
const createMockMetrics = () => ({{
  totalReconnections: 0,
  totalAttempts: 0,
  consecutiveFailures: 0,
  lastReconnectionTime: null,
  lastDisconnectionTime: null,
  avgReconnectionDurationMs: null,
  totalReconnectionTimeMs: 0,
  failuresByReason: {{
    max_attempts_exceeded: 0,
    token_expired: 0,
    token_refresh_failed: 0,
    protocol_version_mismatch: 0,
    network_error: 0,
    server_error: 0,
    invalid_url: 0,
    manual_disconnect: 0,
    unknown: 0,
  }},
  successRate: null,
  recentAttempts: [],
}});

// Track what URL was passed to useRealtimeSync
let capturedUrl = "";

vi.mock("./useRealtimeSync", () => ({{
  useRealtimeSync: vi.fn((options) => {{
    capturedUrl = options.url;
    return {{
      status: "connected",
      send: vi.fn(),
      disconnect: vi.fn(),
      reconnect: vi.fn(),
      reconnectAttempts: 0,
      lastMessageTime: null,
      metrics: createMockMetrics(),
    }};
  }}),
}}));

// Mock getAuthToken and STORAGE_KEYS
vi.mock("../utils/storage", async (importOriginal) => {{
  const actual = await importOriginal<typeof import("../utils/storage")>();
  return {{
    ...actual,
    getAuthToken: vi.fn(() => "mock-test-token"),
  }};
}});

// Variables to control mock behavior per test
let mockIsAuthenticated = true;
let mockWsPermissions: {{ {permission_key}: boolean }} | null = {{
  {permission_key}: true,
}};

// Mock Redux hooks with controllable values
const mockDispatch = vi.fn();
vi.mock("../store/hooks", () => ({{
  useAppDispatch: () => mockDispatch,
  useAppSelector: vi.fn((selector) => {{
    if (selector.name?.includes("Authenticated")) return mockIsAuthenticated;
    if (selector.name?.includes("WebSocketPermissions")) return mockWsPermissions;
    return true;
  }}),
}}));

describe("{hook_name} permission-based connection control", () => {{
  beforeEach(() => {{
    vi.clearAllMocks();
    capturedUrl = "";
    // Reset to default authenticated state with permission
    mockIsAuthenticated = true;
    mockWsPermissions = {{ {permission_key}: true }};
  }});

  afterEach(() => {{
    cleanup();
    vi.clearAllMocks();
  }});

  it("should NOT create WebSocket URL when {permission_key} permission is denied", () => {{
    // Mock: authenticated=true but permission=false
    mockIsAuthenticated = true;
    mockWsPermissions = {{ {permission_key}: false }};

    renderHook(() => {hook_name}());

    // When permission denied, URL should be empty string to prevent connection
    expect(capturedUrl).toBe("");
  }});

  it("should NOT create WebSocket URL when user is not authenticated", () => {{
    // Mock: authenticated=false
    mockIsAuthenticated = false;
    mockWsPermissions = {{ {permission_key}: true }};

    renderHook(() => {hook_name}());

    // When not authenticated, URL should be empty string
    expect(capturedUrl).toBe("");
  }});

  it("should create WebSocket URL when authenticated AND has permission", () => {{
    // Mock: both authenticated=true and permission=true
    mockIsAuthenticated = true;
    mockWsPermissions = {{ {permission_key}: true }};

    renderHook(() => {hook_name}());

    // When both conditions met, URL should contain the WebSocket endpoint
    expect(capturedUrl).toContain("{ws_endpoint}");
  }});

  it("should handle null websocket permissions (fail-closed)", () => {{
    // Mock: authenticated but wsPermissions is null (OpenFGA unavailable)
    mockIsAuthenticated = true;
    mockWsPermissions = null;

    renderHook(() => {hook_name}());

    // When permissions are null, should fail-closed (no connection)
    expect(capturedUrl).toBe("");
  }});

  it("should handle both unauthenticated and no permission (fail-closed)", () => {{
    // Mock: neither authenticated nor has permission
    mockIsAuthenticated = false;
    mockWsPermissions = {{ {permission_key}: false }};

    renderHook(() => {hook_name}());

    // Should fail-closed
    expect(capturedUrl).toBe("");
  }});
}});
"""


def main() -> None:
    hooks_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hooks_path = os.path.join(hooks_dir, "src", "hooks")

    for hook_name, permission_key, ws_endpoint in HOOKS:
        test_filename = f"{hook_name}.permissions.test.ts"
        test_filepath = os.path.join(hooks_path, test_filename)

        content = TEMPLATE.format(
            hook_name=hook_name,
            permission_key=permission_key,
            ws_endpoint=ws_endpoint,
        )

        with open(test_filepath, "w") as f:
            f.write(content)

        print(f"Created: {test_filename}")

    print(f"\nGenerated {len(HOOKS)} permission test files")


if __name__ == "__main__":
    main()
