/**
 * useAgentRequestWebSocket Hook Tests
 *
 * TDD tests for the agent HITL request WebSocket hook.
 *
 * Features:
 * - Connect to agent request WebSocket endpoint
 * - Handle approval_required messages
 * - Handle clarification_required messages
 * - Handle approval_updated messages
 * - Handle execution_resumed messages
 * - Ping/pong keepalive
 * - Connection status tracking
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import React from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import backgroundAgentReducer from "../store/slices/backgroundAgentSlice";
import authReducer from "../store/slices/authSlice";
import {
  useAgentRequestWebSocket,
  type ApprovalRequiredPayload,
  type ClarificationRequiredPayload,
  type ApprovalUpdatedPayload,
  type ExecutionResumedPayload,
  parseAgentRequestMessage,
} from "./useAgentRequestWebSocket";
import * as storageModule from "../utils/storage";

// =============================================================================
// Mock Setup
// =============================================================================

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static OPEN = 1;
  static CLOSED = 3;
  readyState = 1; // OPEN
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: ((error: Event) => void) | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    // Auto-connect
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 0);
  }

  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = 3; // CLOSED
    if (this.onclose) this.onclose();
  });

  // Helper to simulate incoming message
  simulateMessage(data: unknown) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }

  static reset() {
    MockWebSocket.instances = [];
  }
}

// Test store creator
function createTestStore(isAuthenticated = true) {
  return configureStore({
    reducer: {
      backgroundAgent: backgroundAgentReducer,
      auth: authReducer,
    },
    preloadedState: {
      auth: {
        user: isAuthenticated
          ? {
              id: "test-user",
              email: "test@example.com",
              roles: ["user"],
              persona: "user" as const,
            }
          : null,
        tokens: null,
        organizations: [],
        currentOrganization: null,
        permissions: [],
        lastSynced: null,
        isLoading: false,
        error: null,
      },
    },
  });
}

// Test wrapper
function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

// =============================================================================
// Tests
// =============================================================================

describe("useAgentRequestWebSocket", () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    MockWebSocket.reset();
    vi.stubGlobal("WebSocket", MockWebSocket);
    store = createTestStore();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe("Connection", () => {
    it("should connect to WebSocket when mounted", async () => {
      renderHook(() => useAgentRequestWebSocket(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      expect(MockWebSocket.instances.length).toBe(1);
    });

    it("should include token in URL when available", async () => {
      // Mock getAuthToken to return a token
      vi.spyOn(storageModule, "getAuthToken").mockReturnValue("test-jwt-token");

      renderHook(() => useAgentRequestWebSocket(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      expect(MockWebSocket.instances[0].url).toContain("token=test-jwt-token");
    });

    it("should return connected status when WebSocket opens", async () => {
      const { result } = renderHook(() => useAgentRequestWebSocket(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      expect(result.current.status).toBe("connected");
    });

    it("should not connect when enabled is false", async () => {
      renderHook(() => useAgentRequestWebSocket({ enabled: false }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      expect(MockWebSocket.instances.length).toBe(0);
    });
  });

  describe("approval_required Messages", () => {
    const mockApprovalPayload: ApprovalRequiredPayload = {
      request_id: "req-001",
      session_id: "session-001",
      task_id: "task-001",
      agent_name: "Research Assistant",
      confidence: 0.65,
      threshold: 0.7,
      proposed_action: "Send report to API",
      trigger_reason: "low_confidence",
      context: { tokens_used: 1000 },
      requested_at: "2024-01-15T10:36:00Z",
    };

    it("should call onApprovalRequired when message received", async () => {
      const onApprovalRequired = vi.fn();
      renderHook(() => useAgentRequestWebSocket({ onApprovalRequired }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "approval_required",
          payload: mockApprovalPayload,
        });
      });

      expect(onApprovalRequired).toHaveBeenCalledWith(mockApprovalPayload);
    });

    it("should update pendingApprovals when message received", async () => {
      const { result } = renderHook(() => useAgentRequestWebSocket(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "approval_required",
          payload: mockApprovalPayload,
        });
      });

      expect(result.current.pendingApprovals).toHaveLength(1);
      expect(result.current.pendingApprovals[0].request_id).toBe("req-001");
    });
  });

  describe("clarification_required Messages", () => {
    const mockClarificationPayload: ClarificationRequiredPayload = {
      request_id: "clar-001",
      session_id: "session-001",
      task_id: "task-001",
      agent_name: "Data Analyst",
      clarification_type: "choice",
      question: "Which approach?",
      options: [{ id: "fast", label: "Fast" }],
      placeholder: null,
      required: true,
      context: {},
      requested_at: "2024-01-15T10:36:00Z",
    };

    it("should call onClarificationRequired when message received", async () => {
      const onClarificationRequired = vi.fn();
      renderHook(() => useAgentRequestWebSocket({ onClarificationRequired }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "clarification_required",
          payload: mockClarificationPayload,
        });
      });

      expect(onClarificationRequired).toHaveBeenCalledWith(
        mockClarificationPayload,
      );
    });

    it("should update pendingClarifications when message received", async () => {
      const { result } = renderHook(() => useAgentRequestWebSocket(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "clarification_required",
          payload: mockClarificationPayload,
        });
      });

      expect(result.current.pendingClarifications).toHaveLength(1);
      expect(result.current.pendingClarifications[0].request_id).toBe(
        "clar-001",
      );
    });
  });

  describe("approval_updated Messages", () => {
    const mockApprovalUpdatedPayload: ApprovalUpdatedPayload = {
      request_id: "req-001",
      status: "approved",
      decided_by: "admin@example.com",
      decided_at: "2024-01-15T10:40:00Z",
      reason: "Looks good",
    };

    it("should call onApprovalUpdated when message received", async () => {
      const onApprovalUpdated = vi.fn();
      renderHook(() => useAgentRequestWebSocket({ onApprovalUpdated }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "approval_updated",
          payload: mockApprovalUpdatedPayload,
        });
      });

      expect(onApprovalUpdated).toHaveBeenCalledWith(
        mockApprovalUpdatedPayload,
      );
    });

    it("should remove from pendingApprovals when approved", async () => {
      const { result } = renderHook(() => useAgentRequestWebSocket(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      // First add a pending approval
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "approval_required",
          payload: {
            request_id: "req-001",
            session_id: "session-001",
            task_id: "task-001",
            agent_name: "Test",
            confidence: 0.5,
            threshold: 0.7,
            proposed_action: "Test",
            trigger_reason: "low_confidence",
            context: {},
            requested_at: "2024-01-15T10:36:00Z",
          },
        });
      });

      expect(result.current.pendingApprovals).toHaveLength(1);

      // Then update it as approved
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "approval_updated",
          payload: mockApprovalUpdatedPayload,
        });
      });

      expect(result.current.pendingApprovals).toHaveLength(0);
    });
  });

  describe("execution_resumed Messages", () => {
    const mockExecutionResumedPayload: ExecutionResumedPayload = {
      request_id: "req-001",
      task_id: "task-001",
      agent_name: "Research Assistant",
      status: "approved",
      resumed_at: "2024-01-15T10:41:00Z",
    };

    it("should call onExecutionResumed when message received", async () => {
      const onExecutionResumed = vi.fn();
      renderHook(() => useAgentRequestWebSocket({ onExecutionResumed }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "execution_resumed",
          payload: mockExecutionResumedPayload,
        });
      });

      expect(onExecutionResumed).toHaveBeenCalledWith(
        mockExecutionResumedPayload,
      );
    });
  });

  describe("Ping/Pong Keepalive", () => {
    it("should send ping periodically", async () => {
      renderHook(() => useAgentRequestWebSocket(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      const ws = MockWebSocket.instances[0];

      // Fast forward 30 seconds (default ping interval)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(30000);
      });

      expect(ws.send).toHaveBeenCalledWith(JSON.stringify({ type: "ping" }));
    });
  });

  describe("Disconnect/Reconnect", () => {
    it("should provide disconnect function", async () => {
      const { result } = renderHook(() => useAgentRequestWebSocket(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      await act(async () => {
        result.current.disconnect();
      });

      expect(MockWebSocket.instances[0].close).toHaveBeenCalled();
    });

    it("should provide reconnect function", async () => {
      const { result } = renderHook(() => useAgentRequestWebSocket(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      const initialCount = MockWebSocket.instances.length;

      await act(async () => {
        result.current.disconnect();
        await vi.advanceTimersByTimeAsync(100);
      });

      await act(async () => {
        result.current.reconnect();
        await vi.advanceTimersByTimeAsync(100);
      });

      expect(MockWebSocket.instances.length).toBeGreaterThan(initialCount);
    });
  });

  describe("Subscription Restoration", () => {
    it("should send subscribe message with sessionId on connect", async () => {
      renderHook(() => useAgentRequestWebSocket({ sessionId: "session-123" }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      const ws = MockWebSocket.instances[0];
      expect(ws.send).toHaveBeenCalledWith(
        JSON.stringify({ type: "subscribe", session_id: "session-123" }),
      );
    });

    it("should request pending items on reconnect", async () => {
      const { result } = renderHook(
        () => useAgentRequestWebSocket({ sessionId: "session-123" }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      const firstWs = MockWebSocket.instances[0];
      firstWs.send.mockClear();

      // Disconnect and reconnect
      await act(async () => {
        result.current.disconnect();
        await vi.advanceTimersByTimeAsync(100);
      });

      await act(async () => {
        result.current.reconnect();
        // 100ms for reconnect timeout + extra for WebSocket onopen to fire
        await vi.advanceTimersByTimeAsync(200);
      });

      const secondWs = MockWebSocket.instances[1];
      // Should send subscribe message on reconnect
      expect(secondWs.send).toHaveBeenCalledWith(
        JSON.stringify({ type: "subscribe", session_id: "session-123" }),
      );
      // Should request pending items
      expect(secondWs.send).toHaveBeenCalledWith(
        JSON.stringify({ type: "get_pending" }),
      );
    });

    it("should preserve pending approvals during temporary disconnect", async () => {
      const { result } = renderHook(
        () => useAgentRequestWebSocket({ sessionId: "session-123" }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      // Receive an approval request
      act(() => {
        MockWebSocket.instances[0].simulateMessage({
          type: "approval_required",
          payload: {
            request_id: "req-001",
            session_id: "session-123",
            task_id: "task-001",
            agent_name: "Test Agent",
            confidence: 0.5,
            threshold: 0.7,
            proposed_action: "Test action",
            trigger_reason: "low_confidence",
            context: {},
            requested_at: "2024-01-15T10:36:00Z",
          },
        });
      });

      expect(result.current.pendingApprovals).toHaveLength(1);

      // Disconnect
      await act(async () => {
        result.current.disconnect();
        await vi.advanceTimersByTimeAsync(100);
      });

      // Pending approvals should be preserved
      expect(result.current.pendingApprovals).toHaveLength(1);
      expect(result.current.pendingApprovals[0].request_id).toBe("req-001");
    });

    it("should not send subscribe message if no sessionId provided", async () => {
      renderHook(() => useAgentRequestWebSocket(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(100);
      });

      const ws = MockWebSocket.instances[0];
      const subscribeCalls = ws.send.mock.calls.filter(
        (call: string[]) => call[0] && JSON.parse(call[0]).type === "subscribe",
      );
      expect(subscribeCalls).toHaveLength(0);
    });
  });
});

describe("parseAgentRequestMessage", () => {
  it("should parse approval_required message", () => {
    const message = parseAgentRequestMessage({
      type: "approval_required",
      payload: {
        request_id: "req-001",
        session_id: "session-001",
        task_id: "task-001",
        agent_name: "Test",
        confidence: 0.5,
        threshold: 0.7,
        proposed_action: "Test",
        trigger_reason: "low_confidence",
        context: {},
        requested_at: "2024-01-15T10:36:00Z",
      },
    });

    expect(message).not.toBeNull();
    expect(message?.type).toBe("approval_required");
  });

  it("should parse clarification_required message", () => {
    const message = parseAgentRequestMessage({
      type: "clarification_required",
      payload: {
        request_id: "clar-001",
        session_id: "session-001",
        task_id: "task-001",
        agent_name: "Test",
        clarification_type: "text",
        question: "What?",
        options: [],
        placeholder: null,
        required: true,
        context: {},
        requested_at: "2024-01-15T10:36:00Z",
      },
    });

    expect(message).not.toBeNull();
    expect(message?.type).toBe("clarification_required");
  });

  it("should parse approval_updated message", () => {
    const message = parseAgentRequestMessage({
      type: "approval_updated",
      payload: {
        request_id: "req-001",
        status: "approved",
        decided_by: "admin@example.com",
        decided_at: "2024-01-15T10:40:00Z",
        reason: null,
      },
    });

    expect(message).not.toBeNull();
    expect(message?.type).toBe("approval_updated");
  });

  it("should parse execution_resumed message", () => {
    const message = parseAgentRequestMessage({
      type: "execution_resumed",
      payload: {
        request_id: "req-001",
        task_id: "task-001",
        agent_name: "Test",
        status: "approved",
        resumed_at: "2024-01-15T10:41:00Z",
      },
    });

    expect(message).not.toBeNull();
    expect(message?.type).toBe("execution_resumed");
  });

  it("should return null for invalid message", () => {
    const message = parseAgentRequestMessage({
      type: "unknown_type",
      payload: {},
    });

    expect(message).toBeNull();
  });

  it("should return null for non-object input", () => {
    const message = parseAgentRequestMessage("invalid");

    expect(message).toBeNull();
  });
});
