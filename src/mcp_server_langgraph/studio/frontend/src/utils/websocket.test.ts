/**
 * WebSocket URL Utilities Tests
 *
 * Tests for centralized WebSocket URL construction following 12-Factor principles.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getApiHost,
  getWsProtocol,
  buildWebSocketUrl,
  buildWebSocketUrlWithPath,
  WS_ENDPOINTS,
} from "./websocket";
import { getAuthToken } from "./storage";

// Mock the storage module
vi.mock("./storage", () => ({
  getAuthToken: vi.fn(() => null),
}));

describe("websocket utilities", () => {
  const originalWindow = global.window;
  const _originalImportMeta = import.meta;

  beforeEach(() => {
    vi.resetAllMocks();
  });

  afterEach(() => {
    // Restore window if it was modified
    if (global.window !== originalWindow) {
      global.window = originalWindow;
    }
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("getApiHost", () => {
    it("should use window.location.host when available", () => {
      // Setup window.location
      Object.defineProperty(global, "window", {
        value: {
          location: {
            host: "app.example.com",
            protocol: "https:",
          },
        },
        writable: true,
      });

      expect(getApiHost()).toBe("app.example.com");
    });

    it("should return fallback when window is undefined (SSR)", () => {
      // Simulate SSR environment
      Object.defineProperty(global, "window", {
        value: undefined,
        writable: true,
      });

      const host = getApiHost();
      // Should return the SSR fallback
      expect(host).toBe("localhost:8000");
    });
  });

  describe("getWsProtocol", () => {
    it("should return wss: for https pages", () => {
      Object.defineProperty(global, "window", {
        value: {
          location: {
            host: "app.example.com",
            protocol: "https:",
          },
        },
        writable: true,
      });

      expect(getWsProtocol()).toBe("wss:");
    });

    it("should return ws: for http pages", () => {
      Object.defineProperty(global, "window", {
        value: {
          location: {
            host: "localhost:5175",
            protocol: "http:",
          },
        },
        writable: true,
      });

      expect(getWsProtocol()).toBe("ws:");
    });

    it("should return ws: when window is undefined (SSR)", () => {
      Object.defineProperty(global, "window", {
        value: undefined,
        writable: true,
      });

      expect(getWsProtocol()).toBe("ws:");
    });
  });

  describe("buildWebSocketUrl", () => {
    beforeEach(() => {
      Object.defineProperty(global, "window", {
        value: {
          location: {
            host: "app.example.com",
            protocol: "https:",
          },
        },
        writable: true,
      });
    });

    it("should build URL with endpoint and protocol version", () => {
      const url = buildWebSocketUrl("/api/v1/ws/notifications");
      expect(url).toBe("wss://app.example.com/api/v1/ws/notifications?v=1.0.0");
    });

    it("should include protocol version in all URLs", () => {
      const url = buildWebSocketUrl("/api/v1/ws/notifications");
      expect(url).toContain("v=1.0.0");
    });

    it("should include query parameters with protocol version", () => {
      const url = buildWebSocketUrl("/api/v1/ws/agents/requests", {
        session_id: "123",
      });
      expect(url).toContain("v=1.0.0");
      expect(url).toContain("session_id=123");
    });

    it("should include auth token when requested", async () => {
      // Mock the getAuthToken function
      const { getAuthToken } = await import("./storage");
      vi.mocked(getAuthToken).mockReturnValue("test-token-xyz");

      const url = buildWebSocketUrl("/api/v1/ws/mcp/auth", {}, true);
      expect(url).toContain("v=1.0.0");
      expect(url).toContain("token=test-token-xyz");
    });

    it("should combine token and other params with protocol version", async () => {
      const { getAuthToken } = await import("./storage");
      vi.mocked(getAuthToken).mockReturnValue("my-token");

      const url = buildWebSocketUrl(
        "/api/v1/ws/agents/requests",
        { session_id: "456" },
        true,
      );
      expect(url).toContain("v=1.0.0");
      expect(url).toContain("token=my-token");
      expect(url).toContain("session_id=456");
    });
  });

  describe("WS_ENDPOINTS", () => {
    it("should have all expected endpoints", () => {
      // Core endpoints
      expect(WS_ENDPOINTS.NOTIFICATIONS).toBe("/api/v1/ws/notifications");
      expect(WS_ENDPOINTS.AGENTS_REQUESTS).toBe("/api/v1/ws/agents/requests");
      expect(WS_ENDPOINTS.ALERTS).toBe("/api/v1/ws/alerts");

      // MCP endpoints
      expect(WS_ENDPOINTS.MCP).toBe("/api/v1/ws/mcp");
      expect(WS_ENDPOINTS.MCP_AUTH).toBe("/api/v1/ws/mcp/auth");
      expect(WS_ENDPOINTS.MCP_AGGREGATED).toBe("/api/v1/ws/mcp/aggregated");
      expect(WS_ENDPOINTS.MCP_TASKS).toBe("/api/v1/ws/mcp/tasks");
      expect(WS_ENDPOINTS.MCP_SESSION).toBe("/api/v1/ws/mcp/:sessionId");

      // AI/UX endpoints
      expect(WS_ENDPOINTS.AI_SUGGESTIONS).toBe("/api/v1/ws/ai/suggestions");

      // Workflow endpoints
      expect(WS_ENDPOINTS.WORKFLOW_EXECUTION).toBe(
        "/api/v1/ws/workflows/:workflowId",
      );

      // Monitoring endpoints
      expect(WS_ENDPOINTS.METRICS_HEART).toBe("/api/v1/ws/metrics/heart");
      expect(WS_ENDPOINTS.COST).toBe("/api/v1/ws/usage/cost");
      expect(WS_ENDPOINTS.BUDGET_ALERTS).toBe("/api/v1/ws/budget/alerts");

      // Connections endpoints (standardized under /api/v1/ws/)
      expect(WS_ENDPOINTS.CONNECTIONS_REALTIME).toBe(
        "/api/v1/ws/connections/realtime",
      );
      expect(WS_ENDPOINTS.CONNECTIONS_HEALTH).toBe(
        "/api/v1/ws/connections/health",
      );

      // DevTools endpoints
      expect(WS_ENDPOINTS.DEVTOOLS).toBe("/api/v1/ws/devtools");

      // Audit endpoints
      expect(WS_ENDPOINTS.AUDIT).toBe("/api/v1/ws/audit");

      // Trace endpoints
      expect(WS_ENDPOINTS.TRACES).toBe("/api/v1/ws/traces");
    });

    it("should not contain hardcoded hosts or protocols", () => {
      Object.values(WS_ENDPOINTS).forEach((endpoint) => {
        expect(endpoint).not.toContain("localhost");
        expect(endpoint).not.toContain("ws://");
        expect(endpoint).not.toContain("wss://");
        // All endpoints should start with /api/v1/
        expect(endpoint).toMatch(/^\/api\/v1\//);
      });
    });
  });

  describe("buildWebSocketUrlWithPath", () => {
    beforeEach(() => {
      Object.defineProperty(global, "window", {
        value: {
          location: {
            protocol: "https:",
            host: "app.example.com",
          },
        },
        writable: true,
      });
    });

    it("should replace single path parameter with protocol version", () => {
      const url = buildWebSocketUrlWithPath(WS_ENDPOINTS.WORKFLOW_EXECUTION, {
        workflowId: "abc-123",
      });
      expect(url).toBe(
        "wss://app.example.com/api/v1/ws/workflows/abc-123?v=1.0.0",
      );
    });

    it("should replace multiple path parameters with protocol version", () => {
      const url = buildWebSocketUrlWithPath("/api/v1/ws/:foo/:bar", {
        foo: "value1",
        bar: "value2",
      });
      expect(url).toBe("wss://app.example.com/api/v1/ws/value1/value2?v=1.0.0");
    });

    it("should include query parameters with protocol version", () => {
      const url = buildWebSocketUrlWithPath(
        WS_ENDPOINTS.WORKFLOW_EXECUTION,
        { workflowId: "abc-123" },
        { debug: "true", verbose: "1" },
      );
      expect(url).toContain("/api/v1/ws/workflows/abc-123");
      expect(url).toContain("v=1.0.0");
      expect(url).toContain("debug=true");
      expect(url).toContain("verbose=1");
    });

    it("should include auth token when requested", () => {
      vi.mocked(getAuthToken).mockReturnValue("test-token");
      const url = buildWebSocketUrlWithPath(
        WS_ENDPOINTS.MCP_SESSION,
        { sessionId: "session-789" },
        {},
        true,
      );
      expect(url).toContain("/api/v1/ws/mcp/session-789");
      expect(url).toContain("token=test-token");
    });
  });
});
