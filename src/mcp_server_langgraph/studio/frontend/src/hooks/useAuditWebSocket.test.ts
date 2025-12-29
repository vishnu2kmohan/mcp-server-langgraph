/**
 * useAuditWebSocket Hook Tests
 *
 * Tests for audit event streaming WebSocket hook following TDD.
 * RED phase: Write failing tests first.
 */

import { renderHook, act, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  useAuditWebSocket,
  type AuditEvent,
  type AuditFilter,
} from "./useAuditWebSocket";

// Mock Redux hooks to avoid needing Provider wrapper
const mockDispatch = vi.fn();
vi.mock("../store/hooks", () => ({
  useAppDispatch: () => mockDispatch,
  // Return true for selectIsAuthenticated (this hook only uses this selector)
  useAppSelector: () => true,
}));

// Mock useRealtimeSync
const mockSend = vi.fn();
const mockDisconnect = vi.fn();
const mockReconnect = vi.fn();
let mockOnMessage: ((data: unknown) => void) | undefined;
let _mockOnConnect: (() => void) | undefined;
let mockOnDisconnect: (() => void) | undefined;
let mockStatus = "connected" as const;

vi.mock("./useRealtimeSync", () => ({
  useRealtimeSync: vi.fn((options) => {
    mockOnMessage = options.onMessage;
    _mockOnConnect = options.onConnect;
    mockOnDisconnect = options.onDisconnect;
    return {
      status: mockStatus,
      send: mockSend,
      disconnect: mockDisconnect,
      reconnect: mockReconnect,
      metrics: { totalAttempts: 0 },
    };
  }),
}));

describe("useAuditWebSocket", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStatus = "connected";
    mockOnMessage = undefined;
    _mockOnConnect = undefined;
    mockOnDisconnect = undefined;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("connection management", () => {
    it("should return status from useRealtimeSync", () => {
      const { result } = renderHook(() => useAuditWebSocket());
      expect(result.current.status).toBe("connected");
    });

    it("should have empty events initially", () => {
      const { result } = renderHook(() => useAuditWebSocket());
      expect(result.current.events).toEqual([]);
    });

    it("should have null filter initially", () => {
      const { result } = renderHook(() => useAuditWebSocket());
      expect(result.current.currentFilter).toBeNull();
    });

    it("should expose disconnect and reconnect functions", () => {
      const { result } = renderHook(() => useAuditWebSocket());
      expect(typeof result.current.disconnect).toBe("function");
      expect(typeof result.current.reconnect).toBe("function");
    });

    it("should call disconnect when disconnect is called", () => {
      const { result } = renderHook(() => useAuditWebSocket());
      result.current.disconnect();
      expect(mockDisconnect).toHaveBeenCalled();
    });

    it("should call reconnect when reconnect is called", () => {
      const { result } = renderHook(() => useAuditWebSocket());
      result.current.reconnect();
      expect(mockReconnect).toHaveBeenCalled();
    });
  });

  describe("filter management", () => {
    it("should send filter when setFilter is called", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      const filter: AuditFilter = {
        categories: ["security", "authentication"],
        regulations: ["HIPAA"],
      };

      act(() => {
        result.current.setFilter(filter);
      });

      expect(mockSend).toHaveBeenCalledWith(filter);
    });

    it("should update currentFilter when filter_updated message is received", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      const filter: AuditFilter = {
        categories: ["security"],
        regulations: ["HIPAA", "FedRAMP"],
        actors: ["user:alice"],
        event_types: ["login_success"],
      };

      act(() => {
        mockOnMessage?.({ type: "filter_updated", filter });
      });

      expect(result.current.currentFilter).toEqual(filter);
    });

    it("should clear filter when clearFilter is called", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      // First set a filter
      act(() => {
        mockOnMessage?.({
          type: "filter_updated",
          filter: { categories: ["security"] },
        });
      });

      // Clear it
      act(() => {
        result.current.clearFilter();
      });

      // Should send empty filter
      expect(mockSend).toHaveBeenCalledWith({});
    });
  });

  describe("event handling", () => {
    it("should add event when audit event message is received", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      const event: AuditEvent = {
        event_id: "evt-001",
        timestamp: "2025-01-15T10:30:00Z",
        category: "authentication",
        event_type: "login_success",
        actor: "user:alice",
        resource: "session:123",
        details: { ip: "192.168.1.1" },
      };

      act(() => {
        mockOnMessage?.(event);
      });

      expect(result.current.events).toContainEqual(event);
    });

    it("should prepend new events (newest first)", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      const event1: AuditEvent = {
        event_id: "evt-001",
        timestamp: "2025-01-15T10:30:00Z",
        category: "authentication",
        event_type: "login_success",
        actor: "user:alice",
      };

      const event2: AuditEvent = {
        event_id: "evt-002",
        timestamp: "2025-01-15T10:31:00Z",
        category: "authentication",
        event_type: "logout",
        actor: "user:alice",
      };

      act(() => {
        mockOnMessage?.(event1);
        mockOnMessage?.(event2);
      });

      expect(result.current.events[0].event_id).toBe("evt-002");
      expect(result.current.events[1].event_id).toBe("evt-001");
    });

    it("should respect maxEvents limit", () => {
      const { result } = renderHook(() => useAuditWebSocket({ maxEvents: 2 }));

      const events: AuditEvent[] = [
        {
          event_id: "evt-001",
          timestamp: "2025-01-15T10:30:00Z",
          category: "auth",
          event_type: "login",
          actor: "alice",
        },
        {
          event_id: "evt-002",
          timestamp: "2025-01-15T10:31:00Z",
          category: "auth",
          event_type: "logout",
          actor: "alice",
        },
        {
          event_id: "evt-003",
          timestamp: "2025-01-15T10:32:00Z",
          category: "auth",
          event_type: "login",
          actor: "bob",
        },
      ];

      events.forEach((event) => {
        act(() => {
          mockOnMessage?.(event);
        });
      });

      expect(result.current.events).toHaveLength(2);
      expect(result.current.events[0].event_id).toBe("evt-003");
      expect(result.current.events[1].event_id).toBe("evt-002");
    });

    it("should clear events when clearEvents is called", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      const event: AuditEvent = {
        event_id: "evt-001",
        timestamp: "2025-01-15T10:30:00Z",
        category: "auth",
        event_type: "login",
        actor: "alice",
      };

      act(() => {
        mockOnMessage?.(event);
      });

      expect(result.current.events).toHaveLength(1);

      act(() => {
        result.current.clearEvents();
      });

      expect(result.current.events).toHaveLength(0);
    });
  });

  describe("callbacks", () => {
    it("should call onEvent callback when event is received", () => {
      const onEvent = vi.fn();
      renderHook(() => useAuditWebSocket({ onEvent }));

      const event: AuditEvent = {
        event_id: "evt-001",
        timestamp: "2025-01-15T10:30:00Z",
        category: "security",
        event_type: "access_denied",
        actor: "user:mallory",
      };

      act(() => {
        mockOnMessage?.(event);
      });

      expect(onEvent).toHaveBeenCalledWith(event);
    });

    it("should call onFilterUpdated callback when filter is updated", () => {
      const onFilterUpdated = vi.fn();
      renderHook(() => useAuditWebSocket({ onFilterUpdated }));

      const filter: AuditFilter = {
        categories: ["security"],
        regulations: ["SOC2"],
      };

      act(() => {
        mockOnMessage?.({ type: "filter_updated", filter });
      });

      expect(onFilterUpdated).toHaveBeenCalledWith(filter);
    });
  });

  describe("URL configuration", () => {
    it("should use default URL if not provided", async () => {
      renderHook(() => useAuditWebSocket());

      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          // Uses WS_ENDPOINTS.AUDIT which resolves to /ws/audit
          url: expect.stringContaining("/ws/audit"),
        }),
      );
    });

    it("should use custom URL if provided", async () => {
      renderHook(() => useAuditWebSocket({ url: "ws://custom:8000/audit" }));

      const { useRealtimeSync } = await import("./useRealtimeSync");
      expect(useRealtimeSync).toHaveBeenCalledWith(
        expect.objectContaining({
          url: "ws://custom:8000/audit",
        }),
      );
    });
  });

  describe("connection lifecycle", () => {
    it("should keep events on disconnect for resumption", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      const event: AuditEvent = {
        event_id: "evt-001",
        timestamp: "2025-01-15T10:30:00Z",
        category: "auth",
        event_type: "login",
        actor: "alice",
      };

      act(() => {
        mockOnMessage?.(event);
      });

      // Simulate disconnect
      act(() => {
        mockOnDisconnect?.();
      });

      // Events should be preserved
      expect(result.current.events).toHaveLength(1);
    });

    it("should track connection state for UI", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      expect(result.current.isConnected).toBe(true);
    });
  });

  describe("filter restoration on reconnect", () => {
    it("should restore filter when connection is re-established", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      const filter: AuditFilter = {
        categories: ["security", "authentication"],
        regulations: ["HIPAA", "SOC2"],
      };

      // Set a filter (this sends it initially)
      act(() => {
        result.current.setFilter(filter);
      });

      expect(mockSend).toHaveBeenCalledWith(filter);
      mockSend.mockClear();

      // Simulate receiving filter_updated confirmation from server
      act(() => {
        mockOnMessage?.({ type: "filter_updated", filter });
      });

      // Simulate reconnection
      act(() => {
        _mockOnConnect?.();
      });

      // Filter should be re-sent on reconnect
      expect(mockSend).toHaveBeenCalledWith(filter);
    });

    it("should not send filter on reconnect if no filter was set", () => {
      renderHook(() => useAuditWebSocket());

      mockSend.mockClear();

      // Simulate reconnection with no filter set
      act(() => {
        _mockOnConnect?.();
      });

      // No filter should be sent
      expect(mockSend).not.toHaveBeenCalled();
    });

    it("should not restore filter after clearFilter was called", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      const filter: AuditFilter = {
        categories: ["security"],
      };

      // Set a filter
      act(() => {
        result.current.setFilter(filter);
      });

      // Confirm filter was received
      act(() => {
        mockOnMessage?.({ type: "filter_updated", filter });
      });

      // Clear the filter
      act(() => {
        result.current.clearFilter();
      });

      // Simulate receiving cleared filter confirmation
      act(() => {
        mockOnMessage?.({ type: "filter_updated", filter: {} });
      });

      mockSend.mockClear();

      // Simulate reconnection
      act(() => {
        _mockOnConnect?.();
      });

      // No filter should be sent (it was cleared)
      expect(mockSend).not.toHaveBeenCalled();
    });
  });

  describe("pausing", () => {
    it("should track paused state", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      expect(result.current.isPaused).toBe(false);

      act(() => {
        result.current.pause();
      });

      expect(result.current.isPaused).toBe(true);

      act(() => {
        result.current.resume();
      });

      expect(result.current.isPaused).toBe(false);
    });

    it("should not add events when paused", () => {
      const { result } = renderHook(() => useAuditWebSocket());

      act(() => {
        result.current.pause();
      });

      const event: AuditEvent = {
        event_id: "evt-001",
        timestamp: "2025-01-15T10:30:00Z",
        category: "auth",
        event_type: "login",
        actor: "alice",
      };

      act(() => {
        mockOnMessage?.(event);
      });

      // Event should not be added when paused
      expect(result.current.events).toHaveLength(0);
    });
  });
});
