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
  WS_ENDPOINTS,
} from "./websocket";

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

    it("should build URL with endpoint only", () => {
      const url = buildWebSocketUrl("/api/v1/ws/notifications");
      expect(url).toBe("wss://app.example.com/api/v1/ws/notifications");
    });

    it("should include query parameters", () => {
      const url = buildWebSocketUrl("/api/v1/ws/agents/requests", {
        session_id: "123",
      });
      expect(url).toBe(
        "wss://app.example.com/api/v1/ws/agents/requests?session_id=123",
      );
    });

    it("should include auth token when requested", async () => {
      // Mock the getAuthToken function
      const { getAuthToken } = await import("./storage");
      vi.mocked(getAuthToken).mockReturnValue("test-token-xyz");

      const url = buildWebSocketUrl("/api/v1/ws/mcp/auth", {}, true);
      expect(url).toBe(
        "wss://app.example.com/api/v1/ws/mcp/auth?token=test-token-xyz",
      );
    });

    it("should combine token and other params", async () => {
      const { getAuthToken } = await import("./storage");
      vi.mocked(getAuthToken).mockReturnValue("my-token");

      const url = buildWebSocketUrl(
        "/api/v1/ws/agents/requests",
        { session_id: "456" },
        true,
      );
      expect(url).toContain("token=my-token");
      expect(url).toContain("session_id=456");
    });
  });

  describe("WS_ENDPOINTS", () => {
    it("should have all expected endpoints", () => {
      expect(WS_ENDPOINTS.NOTIFICATIONS).toBe("/api/v1/ws/notifications");
      expect(WS_ENDPOINTS.AGENTS_REQUESTS).toBe("/api/v1/ws/agents/requests");
      expect(WS_ENDPOINTS.ALERTS).toBe("/api/v1/ws/alerts");
      expect(WS_ENDPOINTS.MCP).toBe("/api/v1/ws/mcp");
      expect(WS_ENDPOINTS.MCP_AUTH).toBe("/api/v1/ws/mcp/auth");
      expect(WS_ENDPOINTS.MCP_AGGREGATED).toBe("/api/v1/ws/mcp/aggregated");
      expect(WS_ENDPOINTS.METRICS_HEART).toBe("/api/v1/ws/metrics/heart");
    });

    it("should not contain hardcoded hosts or protocols", () => {
      Object.values(WS_ENDPOINTS).forEach((endpoint) => {
        expect(endpoint).not.toContain("localhost");
        expect(endpoint).not.toContain("ws://");
        expect(endpoint).not.toContain("wss://");
        expect(endpoint).toMatch(/^\/api\/v1\/ws\//);
      });
    });
  });
});
