/**
 * MCPConnectionContext Tests
 *
 * Tests for the MCP connection provider that ensures a single WebSocket connection
 * is shared across the app.
 */

import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { MCPConnectionProvider, useMCPConnection } from "./MCPConnectionContext";

// Mock useMCPWebSocket hook
vi.mock("../hooks/useMCPWebSocket", () => ({
  useMCPWebSocket: vi.fn(() => ({
    status: "connected",
    isInitialized: true,
    serverInfo: { name: "test-server", version: "1.0.0" },
    capabilities: { tools: { listChanged: true } },
    tools: [],
    resources: [],
    prompts: [],
    error: null,
    initialize: vi.fn(),
    listTools: vi.fn(),
    listResources: vi.fn(),
    listPrompts: vi.fn(),
    callTool: vi.fn(),
    readResource: vi.fn(),
    getPrompt: vi.fn(),
    sendResponse: vi.fn(),
    disconnect: vi.fn(),
    reconnect: vi.fn(),
  })),
}));

describe("MCPConnectionContext", () => {
  describe("useMCPConnection", () => {
    it("throws error when used outside provider", () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

      expect(() => {
        renderHook(() => useMCPConnection());
      }).toThrow("useMCPConnection must be used within MCPConnectionProvider");

      consoleSpy.mockRestore();
    });

    it("returns MCP connection when used within provider", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <MCPConnectionProvider>{children}</MCPConnectionProvider>
      );

      const { result } = renderHook(() => useMCPConnection(), { wrapper });

      expect(result.current).toBeDefined();
      expect(result.current.status).toBe("connected");
      expect(result.current.isInitialized).toBe(true);
      expect(result.current.sendResponse).toBeDefined();
    });

    it("provides all useMCPWebSocket return values", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) => (
        <MCPConnectionProvider>{children}</MCPConnectionProvider>
      );

      const { result } = renderHook(() => useMCPConnection(), { wrapper });

      // Verify all expected properties exist
      expect(result.current).toHaveProperty("status");
      expect(result.current).toHaveProperty("isInitialized");
      expect(result.current).toHaveProperty("serverInfo");
      expect(result.current).toHaveProperty("capabilities");
      expect(result.current).toHaveProperty("tools");
      expect(result.current).toHaveProperty("resources");
      expect(result.current).toHaveProperty("prompts");
      expect(result.current).toHaveProperty("error");
      expect(result.current).toHaveProperty("initialize");
      expect(result.current).toHaveProperty("listTools");
      expect(result.current).toHaveProperty("listResources");
      expect(result.current).toHaveProperty("listPrompts");
      expect(result.current).toHaveProperty("callTool");
      expect(result.current).toHaveProperty("readResource");
      expect(result.current).toHaveProperty("getPrompt");
      expect(result.current).toHaveProperty("sendResponse");
      expect(result.current).toHaveProperty("disconnect");
      expect(result.current).toHaveProperty("reconnect");
    });
  });
});
