/**
 * WebSocket Authentication Contract Tests
 *
 * These tests validate that frontend WebSocket hooks correctly include
 * authentication tokens when connecting to backend endpoints that require auth.
 *
 * This is a CONTRACT test - it validates the agreement between frontend and backend:
 * - Backend defines which endpoints require authentication (require_auth=True)
 * - Frontend must include auth token when connecting to those endpoints
 *
 * Why this test exists:
 * - Prevents the "user=None" bug where WebSocket connections fail silently
 * - Catches mismatches between frontend and backend auth requirements
 * - Ensures new WebSocket hooks follow the established pattern
 *
 * Related files:
 * - Backend: src/mcp_server_langgraph/api/v1/ws_router.py (defines require_auth)
 * - Frontend: src/utils/websocket.ts (buildWebSocketUrl function)
 * - Frontend hooks: src/hooks/use*WebSocket.ts
 *
 * @see ADR-0068 for WebSocket URL consolidation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock getAuthToken to return a test token
vi.mock("./storage", () => ({
  getAuthToken: () => "test-jwt-token-for-contract-test",
}));

// Import after mock setup
import { buildWebSocketUrl, WS_ENDPOINTS } from "./websocket";

/**
 * Backend WebSocket endpoint authentication requirements.
 *
 * This is the "contract" - the source of truth from the backend.
 * Each entry maps an endpoint path to whether it requires authentication.
 *
 * IMPORTANT: Keep this in sync with ws_router.py WebSocketConfig settings.
 * When adding a new WebSocket endpoint, add it here with the correct auth requirement.
 */
const BACKEND_AUTH_REQUIREMENTS: Record<
  string,
  { requireAuth: boolean; backendLine: string }
> = {
  // MCP endpoints
  "/api/v1/ws/mcp/tasks": { requireAuth: true, backendLine: "ws_router.py:81" },
  "/api/v1/ws/mcp/aggregated": {
    requireAuth: true,
    backendLine: "ws_router.py:140",
  },
  "/api/v1/ws/mcp": { requireAuth: false, backendLine: "ws_router.py:557" },
  "/api/v1/ws/mcp/auth": { requireAuth: true, backendLine: "ws_router.py:588" },

  // Notifications
  "/api/v1/ws/notifications": {
    requireAuth: true,
    backendLine: "ws_router.py:177",
  },

  // Connections
  "/api/v1/ws/connections/realtime": {
    requireAuth: true,
    backendLine: "ws_router.py:215",
  },
  "/api/v1/ws/connections/health": {
    requireAuth: true,
    backendLine: "ws_router.py:383",
  },

  // Metrics & Cost
  "/api/v1/ws/metrics/heart": {
    requireAuth: true,
    backendLine: "ws_router.py:248",
  },
  "/api/v1/ws/usage/cost": {
    requireAuth: true,
    backendLine: "ws_router.py:281",
  },

  // Alerts
  "/api/v1/ws/alerts": { requireAuth: true, backendLine: "ws_router.py:426" },
  "/api/v1/ws/budget/alerts": {
    requireAuth: true,
    backendLine: "ws_router.py:781",
  },

  // Audit
  "/api/v1/ws/audit": { requireAuth: true, backendLine: "ws_router.py:467" },

  // Agent requests
  "/api/v1/ws/agents/requests": {
    requireAuth: true,
    backendLine: "ws_router.py:515",
  },

  // AI Suggestions
  "/api/v1/ws/ai/suggestions": {
    requireAuth: true,
    backendLine: "ws_router.py:673",
  },

  // Traces
  "/api/v1/ws/traces": { requireAuth: true, backendLine: "ws_router.py:730" },

  // DevTools
  "/api/v1/ws/devtools": { requireAuth: true, backendLine: "ws_router.py:835" },
};

/**
 * Frontend WebSocket endpoint constants.
 *
 * These are defined in src/utils/websocket.ts and should match the backend paths.
 */
const FRONTEND_ENDPOINTS_TO_TEST: Array<{
  name: string;
  endpoint: string;
  shouldIncludeToken: boolean;
}> = [
  // MCP endpoints
  {
    name: "MCP_TASKS",
    endpoint: WS_ENDPOINTS.MCP_TASKS,
    shouldIncludeToken: true,
  },
  {
    name: "MCP_AGGREGATED",
    endpoint: WS_ENDPOINTS.MCP_AGGREGATED,
    shouldIncludeToken: true,
  },
  { name: "MCP", endpoint: WS_ENDPOINTS.MCP, shouldIncludeToken: false },
  {
    name: "MCP_AUTH",
    endpoint: WS_ENDPOINTS.MCP_AUTH,
    shouldIncludeToken: true,
  },

  // Notifications
  {
    name: "NOTIFICATIONS",
    endpoint: WS_ENDPOINTS.NOTIFICATIONS,
    shouldIncludeToken: true,
  },

  // Connections
  {
    name: "CONNECTIONS_REALTIME",
    endpoint: WS_ENDPOINTS.CONNECTIONS_REALTIME,
    shouldIncludeToken: true,
  },
  {
    name: "CONNECTIONS_HEALTH",
    endpoint: WS_ENDPOINTS.CONNECTIONS_HEALTH,
    shouldIncludeToken: true,
  },

  // Metrics & Cost
  {
    name: "METRICS_HEART",
    endpoint: WS_ENDPOINTS.METRICS_HEART,
    shouldIncludeToken: true,
  },
  { name: "COST", endpoint: WS_ENDPOINTS.COST, shouldIncludeToken: true },

  // Alerts
  { name: "ALERTS", endpoint: WS_ENDPOINTS.ALERTS, shouldIncludeToken: true },
  {
    name: "BUDGET_ALERTS",
    endpoint: WS_ENDPOINTS.BUDGET_ALERTS,
    shouldIncludeToken: true,
  },

  // Audit
  { name: "AUDIT", endpoint: WS_ENDPOINTS.AUDIT, shouldIncludeToken: true },

  // Agent requests
  {
    name: "AGENTS_REQUESTS",
    endpoint: WS_ENDPOINTS.AGENTS_REQUESTS,
    shouldIncludeToken: true,
  },

  // AI Suggestions
  {
    name: "AI_SUGGESTIONS",
    endpoint: WS_ENDPOINTS.AI_SUGGESTIONS,
    shouldIncludeToken: true,
  },

  // Traces
  { name: "TRACES", endpoint: WS_ENDPOINTS.TRACES, shouldIncludeToken: true },

  // DevTools
  {
    name: "DEVTOOLS",
    endpoint: WS_ENDPOINTS.DEVTOOLS,
    shouldIncludeToken: true,
  },
];

describe("WebSocket Authentication Contract", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  describe("Frontend endpoint paths match backend", () => {
    it.each(FRONTEND_ENDPOINTS_TO_TEST)(
      "$name endpoint path should exist in backend requirements",
      ({ endpoint }) => {
        expect(BACKEND_AUTH_REQUIREMENTS[endpoint]).toBeDefined();
      },
    );
  });

  describe("Auth token inclusion matches backend requirements", () => {
    it.each(FRONTEND_ENDPOINTS_TO_TEST)(
      "$name: when includeAuthToken=$shouldIncludeToken, URL should match backend requirement",
      ({ name: _name, endpoint, shouldIncludeToken }) => {
        const backendReq = BACKEND_AUTH_REQUIREMENTS[endpoint];

        // Build URL with the expected token inclusion
        const url = buildWebSocketUrl(endpoint, {}, shouldIncludeToken);

        if (backendReq.requireAuth) {
          // Backend requires auth, so URL MUST include token
          expect(url).toContain("token=");
        } else {
          // Backend doesn't require auth, token is optional
          // If shouldIncludeToken is false, token should not be present
          if (!shouldIncludeToken) {
            expect(url).not.toContain("token=");
          }
        }

        // Validate shouldIncludeToken matches backend requirement
        if (backendReq.requireAuth) {
          expect(shouldIncludeToken).toBe(true);
        }
      },
    );
  });

  describe("buildWebSocketUrl token behavior", () => {
    it("should include token when includeAuthToken=true", () => {
      const url = buildWebSocketUrl(WS_ENDPOINTS.NOTIFICATIONS, {}, true);
      expect(url).toContain("token=test-jwt-token-for-contract-test");
    });

    it("should NOT include token when includeAuthToken=false", () => {
      const url = buildWebSocketUrl(WS_ENDPOINTS.MCP, {}, false);
      expect(url).not.toContain("token=");
    });

    it("should NOT include token when includeAuthToken is false", () => {
      // Note: includeAuthToken is now REQUIRED, so we explicitly pass false
      const url = buildWebSocketUrl(WS_ENDPOINTS.MCP, {}, false);
      expect(url).not.toContain("token=");
    });

    it("should always include protocol version", () => {
      const url = buildWebSocketUrl(WS_ENDPOINTS.NOTIFICATIONS, {}, true);
      expect(url).toContain("v=");
    });
  });

  describe("All authenticated endpoints have corresponding WS_ENDPOINTS constant", () => {
    it("every backend endpoint requiring auth should have a frontend constant", () => {
      const authenticatedBackendEndpoints = Object.entries(
        BACKEND_AUTH_REQUIREMENTS,
      )
        .filter(([, req]) => req.requireAuth)
        .map(([path]) => path);

      const frontendEndpointPaths = Object.values(WS_ENDPOINTS).filter(
        (path) => !path.includes(":"), // Exclude parameterized paths
      );

      for (const backendPath of authenticatedBackendEndpoints) {
        // Frontend WS_ENDPOINTS already include /api/v1, so direct comparison
        const hasMatch = frontendEndpointPaths.some(
          (fePath) => backendPath === fePath,
        );
        expect(hasMatch).toBe(true);
      }
    });
  });
});

/**
 * Meta-test: Ensure this contract file stays in sync with backend
 *
 * This test reminds developers to update the contract when adding new endpoints.
 */
describe("Contract Maintenance", () => {
  it("should have at least 15 endpoints defined (sanity check)", () => {
    expect(
      Object.keys(BACKEND_AUTH_REQUIREMENTS).length,
    ).toBeGreaterThanOrEqual(15);
  });

  it("should have matching frontend and backend endpoint counts", () => {
    const backendEndpoints = Object.keys(BACKEND_AUTH_REQUIREMENTS).filter(
      (path) => !path.includes(":"),
    );
    const frontendEndpoints = Object.values(WS_ENDPOINTS).filter(
      (path) => !path.includes(":"),
    );

    // Allow some flexibility but they should be close
    expect(
      Math.abs(backendEndpoints.length - frontendEndpoints.length),
    ).toBeLessThanOrEqual(2);
  });
});
