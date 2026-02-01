/**
 * Permission-based Connection Control Tests for useAuditWebSocket
 *
 * Security requirement: WebSocket connections must only be established when:
 * 1. User is authenticated (isAuthenticated=true)
 * 2. User has audit permission (wsPermissions.audit=true)
 *
 * When either condition is false, URL should be empty string "" to prevent connection.
 */

import { renderHook, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useAuditWebSocket } from "./useAuditWebSocket";

// Default metrics matching ReconnectionMetrics interface
const createMockMetrics = () => ({
  totalReconnections: 0,
  totalAttempts: 0,
  consecutiveFailures: 0,
  lastReconnectionTime: null,
  lastDisconnectionTime: null,
  avgReconnectionDurationMs: null,
  totalReconnectionTimeMs: 0,
  failuresByReason: {
    max_attempts_exceeded: 0,
    token_expired: 0,
    token_refresh_failed: 0,
    protocol_version_mismatch: 0,
    network_error: 0,
    server_error: 0,
    invalid_url: 0,
    manual_disconnect: 0,
    unknown: 0,
  },
  successRate: null,
  recentAttempts: [],
});

// Track what URL was passed to useRealtimeSync
let capturedUrl = "";

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: vi.fn((options) => {
    capturedUrl = options.url;
    return {
      status: "connected",
      send: vi.fn(),
      disconnect: vi.fn(),
      reconnect: vi.fn(),
      reconnectAttempts: 0,
      lastMessageTime: null,
      metrics: createMockMetrics(),
    };
  }),
}));

// Mock getAuthToken and STORAGE_KEYS
vi.mock("../utils/storage", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../utils/storage")>();
  return {
    ...actual,
    getAuthToken: vi.fn(() => "mock-test-token"),
  };
});

// Variables to control mock behavior per test
let mockIsAuthenticated = true;
let mockWsPermissions: { audit: boolean } | null = {
  audit: true,
};

// Mock Redux hooks with controllable values
const mockDispatch = vi.fn();
vi.mock("../store/hooks", () => ({
  useAppDispatch: () => mockDispatch,
  useAppSelector: vi.fn((selector) => {
    if (selector.name?.includes("Authenticated")) return mockIsAuthenticated;
    if (selector.name?.includes("WebSocketPermissions"))
      return mockWsPermissions;
    return true;
  }),
}));

describe("useAuditWebSocket permission-based connection control", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedUrl = "";
    // Reset to default authenticated state with permission
    mockIsAuthenticated = true;
    mockWsPermissions = { audit: true };
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should NOT create WebSocket URL when audit permission is denied", () => {
    // Mock: authenticated=true but permission=false
    mockIsAuthenticated = true;
    mockWsPermissions = { audit: false };

    renderHook(() => useAuditWebSocket());

    // When permission denied, URL should be empty string to prevent connection
    expect(capturedUrl).toBe("");
  });

  it("should NOT create WebSocket URL when user is not authenticated", () => {
    // Mock: authenticated=false
    mockIsAuthenticated = false;
    mockWsPermissions = { audit: true };

    renderHook(() => useAuditWebSocket());

    // When not authenticated, URL should be empty string
    expect(capturedUrl).toBe("");
  });

  it("should create WebSocket URL when authenticated AND has permission", () => {
    // Mock: both authenticated=true and permission=true
    mockIsAuthenticated = true;
    mockWsPermissions = { audit: true };

    renderHook(() => useAuditWebSocket());

    // When both conditions met, URL should contain the WebSocket endpoint
    expect(capturedUrl).toContain("/api/v1/ws/audit");
  });

  it("should handle null websocket permissions (fail-closed)", () => {
    // Mock: authenticated but wsPermissions is null (OpenFGA unavailable)
    mockIsAuthenticated = true;
    mockWsPermissions = null;

    renderHook(() => useAuditWebSocket());

    // When permissions are null, should fail-closed (no connection)
    expect(capturedUrl).toBe("");
  });

  it("should handle both unauthenticated and no permission (fail-closed)", () => {
    // Mock: neither authenticated nor has permission
    mockIsAuthenticated = false;
    mockWsPermissions = { audit: false };

    renderHook(() => useAuditWebSocket());

    // Should fail-closed
    expect(capturedUrl).toBe("");
  });
});
