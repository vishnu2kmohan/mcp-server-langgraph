/**
 * useHITLDialogs Hook Tests
 *
 * TDD tests for the Human-in-the-Loop (HITL) dialogs state management hook.
 * Tests are written FIRST before implementation (RED phase).
 *
 * The hook encapsulates:
 * - Approval and clarification dialog state
 * - Loading states (approving, rejecting, submitting)
 * - Dismissed request IDs tracking
 * - WebSocket integration for real-time requests
 * - Auto-show dialogs when pending requests arrive
 * - Handlers for approve, reject, respond, close
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";
import { http, HttpResponse, delay } from "msw";
import { server } from "../mocks/server";
import backgroundAgentReducer from "../store/slices/backgroundAgentSlice";
import personaReducer from "../store/slices/personaSlice";
import { api } from "../api";

// Mock feature flag hook
const mockUseFeatureFlag = vi.fn();
vi.mock("../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flag: string) => mockUseFeatureFlag(flag),
}));

// Mock useAgentRequestWebSocket
const mockWebSocketReturn = {
  pendingApprovals: [] as Array<{
    request_id: string;
    session_id: string;
    task_id: string;
    agent_name: string;
    confidence: number;
    threshold: number;
    proposed_action: string;
    trigger_reason: string;
    context: Record<string, unknown>;
    requested_at: string;
  }>,
  pendingClarifications: [] as Array<{
    request_id: string;
    session_id: string;
    task_id: string;
    agent_name: string;
    clarification_type: string;
    question: string;
    options?: string[];
    placeholder?: string;
    required: boolean;
    context: Record<string, unknown>;
    requested_at: string;
  }>,
  isConnected: true,
};
vi.mock("./useAgentRequestWebSocket", () => ({
  useAgentRequestWebSocket: vi.fn(() => mockWebSocketReturn),
}));

// Mock storage
vi.mock("../utils/storage", () => ({
  storage: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn(),
    clear: vi.fn(),
  },
  getAuthToken: vi.fn(() => "test-token"),
  STORAGE_KEYS: {
    AUTH_TOKEN: "auth_token",
  },
}));

// Import hook after mocks
import { useHITLDialogs } from "./useHITLDialogs";

// Create test store with RTK Query API
const createTestStore = () => {
  return configureStore({
    reducer: {
      backgroundAgent: backgroundAgentReducer,
      persona: personaReducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
    preloadedState: {
      backgroundAgent: {
        agents: [],
      },
      persona: {
        persona: "admin",
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
    } as Record<string, unknown>,
  });
};

// Wrapper for renderHook
const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return ({ children }: { children: ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );
};

// Sample approval payload
const sampleApproval = {
  request_id: "req-1",
  session_id: "session-1",
  task_id: "task-1",
  agent_name: "TestAgent",
  confidence: 0.7,
  threshold: 0.8,
  proposed_action: "Delete file",
  trigger_reason: "Low confidence",
  context: {},
  requested_at: new Date().toISOString(),
};

// Sample clarification payload
const sampleClarification = {
  request_id: "req-2",
  session_id: "session-1",
  task_id: "task-2",
  agent_name: "TestAgent",
  clarification_type: "choice",
  question: "Which option do you prefer?",
  options: ["Option A", "Option B"],
  required: true,
  context: {},
  requested_at: new Date().toISOString(),
};

describe("useHITLDialogs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default feature flags
    mockUseFeatureFlag.mockImplementation((flag: string) => {
      if (flag === "agent_hitl") return true;
      return false;
    });
    // Reset WebSocket mock
    mockWebSocketReturn.pendingApprovals = [];
    mockWebSocketReturn.pendingClarifications = [];
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Initial State", () => {
    it("returns initial dialog state as closed", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.showApprovalDialog).toBe(false);
      expect(result.current.showClarificationDialog).toBe(false);
      expect(result.current.activeApproval).toBeNull();
      expect(result.current.activeClarification).toBeNull();
    });

    it("returns initial loading states as false", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.isApproving).toBe(false);
      expect(result.current.isRejecting).toBe(false);
      expect(result.current.isClarificationSubmitting).toBe(false);
    });

    it("exposes enabled state based on feature flag", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.enabled).toBe(true);
    });

    it("returns enabled as false when feature flag is disabled", () => {
      mockUseFeatureFlag.mockImplementation(() => false);
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.enabled).toBe(false);
    });
  });

  describe("Pending Requests from WebSocket", () => {
    it("exposes pending approvals from WebSocket", () => {
      mockWebSocketReturn.pendingApprovals = [sampleApproval];
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.pendingApprovals).toHaveLength(1);
      expect(result.current.pendingApprovals[0].request_id).toBe("req-1");
    });

    it("exposes pending clarifications from WebSocket", () => {
      mockWebSocketReturn.pendingClarifications = [sampleClarification];
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.pendingClarifications).toHaveLength(1);
      expect(result.current.pendingClarifications[0].request_id).toBe("req-2");
    });
  });

  describe("Dialog Open/Close", () => {
    it("provides openApprovalDialog function", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      expect(typeof result.current.openApprovalDialog).toBe("function");
    });

    it("opens approval dialog when openApprovalDialog is called", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });

      expect(result.current.showApprovalDialog).toBe(true);
      expect(result.current.activeApproval).toEqual(sampleApproval);
    });

    it("closes approval dialog when closeApprovalDialog is called", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });
      expect(result.current.showApprovalDialog).toBe(true);

      act(() => {
        result.current.closeApprovalDialog();
      });

      expect(result.current.showApprovalDialog).toBe(false);
      expect(result.current.activeApproval).toBeNull();
    });

    it("tracks dismissed request IDs when dialog is closed", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });
      act(() => {
        result.current.closeApprovalDialog();
      });

      expect(result.current.isDismissed("req-1")).toBe(true);
    });

    it("opens clarification dialog when openClarificationDialog is called", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openClarificationDialog(sampleClarification);
      });

      expect(result.current.showClarificationDialog).toBe(true);
      expect(result.current.activeClarification).toEqual(sampleClarification);
    });

    it("closes clarification dialog when closeClarificationDialog is called", () => {
      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openClarificationDialog(sampleClarification);
      });
      act(() => {
        result.current.closeClarificationDialog();
      });

      expect(result.current.showClarificationDialog).toBe(false);
      expect(result.current.activeClarification).toBeNull();
    });
  });

  describe("Approval Actions", () => {
    it("calls approve API when handleApprove is called", async () => {
      // Set up MSW handler
      let apiCalled = false;
      let requestBody: Record<string, unknown> | null = null;
      server.use(
        http.post("/api/v1/agents/requests/:requestId/approve", async ({ request }) => {
          apiCalled = true;
          requestBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({ success: true });
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });

      await act(async () => {
        await result.current.handleApprove("req-1", "Approved by user");
      });

      expect(apiCalled).toBe(true);
      expect(requestBody).toEqual({
        approved_by: "testuser",
        reason: "Approved by user",
        modifications: undefined,
      });
    });

    it("sets isApproving to true during approval", async () => {
      // Set up MSW handler with delay
      server.use(
        http.post("/api/v1/agents/requests/:requestId/approve", async () => {
          await delay(100);
          return HttpResponse.json({ success: true });
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });

      let approvePromise: Promise<void>;
      act(() => {
        approvePromise = result.current.handleApprove("req-1");
      });

      // Should be approving while API is in flight
      expect(result.current.isApproving).toBe(true);

      await act(async () => {
        await approvePromise!;
      });

      expect(result.current.isApproving).toBe(false);
    });

    it("closes dialog and clears active approval on successful approval", async () => {
      server.use(
        http.post("/api/v1/agents/requests/:requestId/approve", () => {
          return HttpResponse.json({ success: true });
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });

      await act(async () => {
        await result.current.handleApprove("req-1");
      });

      expect(result.current.showApprovalDialog).toBe(false);
      expect(result.current.activeApproval).toBeNull();
    });

    it("calls reject API when handleReject is called", async () => {
      let apiCalled = false;
      server.use(
        http.post("/api/v1/agents/requests/:requestId/reject", () => {
          apiCalled = true;
          return HttpResponse.json({ success: true });
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });

      await act(async () => {
        await result.current.handleReject("req-1", "Not approved");
      });

      expect(apiCalled).toBe(true);
    });

    it("sets isRejecting to true during rejection", async () => {
      server.use(
        http.post("/api/v1/agents/requests/:requestId/reject", async () => {
          await delay(100);
          return HttpResponse.json({ success: true });
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });

      let rejectPromise: Promise<void>;
      act(() => {
        rejectPromise = result.current.handleReject("req-1");
      });

      expect(result.current.isRejecting).toBe(true);

      await act(async () => {
        await rejectPromise!;
      });

      expect(result.current.isRejecting).toBe(false);
    });
  });

  describe("Clarification Actions", () => {
    it("calls respond API when handleClarificationRespond is called", async () => {
      let apiCalled = false;
      server.use(
        http.post("/api/v1/agents/requests/:requestId/respond", () => {
          apiCalled = true;
          return HttpResponse.json({ success: true });
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openClarificationDialog(sampleClarification);
      });

      const response = {
        request_id: "req-2",
        response_type: "choice" as const,
        selected_option: "Option A",
      };

      await act(async () => {
        await result.current.handleClarificationRespond(response);
      });

      expect(apiCalled).toBe(true);
    });

    it("sets isClarificationSubmitting to true during submission", async () => {
      server.use(
        http.post("/api/v1/agents/requests/:requestId/respond", async () => {
          await delay(100);
          return HttpResponse.json({ success: true });
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openClarificationDialog(sampleClarification);
      });

      const response = {
        request_id: "req-2",
        response_type: "choice" as const,
        selected_option: "Option A",
      };

      let submitPromise: Promise<void>;
      act(() => {
        submitPromise = result.current.handleClarificationRespond(response);
      });

      expect(result.current.isClarificationSubmitting).toBe(true);

      await act(async () => {
        await submitPromise!;
      });

      expect(result.current.isClarificationSubmitting).toBe(false);
    });

    it("closes dialog on successful clarification response", async () => {
      server.use(
        http.post("/api/v1/agents/requests/:requestId/respond", () => {
          return HttpResponse.json({ success: true });
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openClarificationDialog(sampleClarification);
      });

      const response = {
        request_id: "req-2",
        response_type: "choice" as const,
        selected_option: "Option A",
      };

      await act(async () => {
        await result.current.handleClarificationRespond(response);
      });

      expect(result.current.showClarificationDialog).toBe(false);
      expect(result.current.activeClarification).toBeNull();
    });
  });

  describe("Redux Integration", () => {
    it("dispatches updateAgentStatus on approval", async () => {
      server.use(
        http.post("/api/v1/agents/requests/:requestId/approve", () => {
          return HttpResponse.json({ success: true });
        }),
      );

      const store = createTestStore();
      const dispatchSpy = vi.spyOn(store, "dispatch");

      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });

      await act(async () => {
        await result.current.handleApprove("req-1");
      });

      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: expect.stringContaining("updateAgentStatus"),
          payload: expect.objectContaining({
            id: "task-1",
            status: "running",
          }),
        }),
      );
    });

    it("dispatches updateAgentStatus with failed status on rejection", async () => {
      server.use(
        http.post("/api/v1/agents/requests/:requestId/reject", () => {
          return HttpResponse.json({ success: true });
        }),
      );

      const store = createTestStore();
      const dispatchSpy = vi.spyOn(store, "dispatch");

      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });

      await act(async () => {
        await result.current.handleReject("req-1", "Not allowed");
      });

      expect(dispatchSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: expect.stringContaining("updateAgentStatus"),
          payload: expect.objectContaining({
            id: "task-1",
            status: "failed",
          }),
        }),
      );
    });
  });

  describe("Error Handling", () => {
    it("handles approval API error gracefully", async () => {
      server.use(
        http.post("/api/v1/agents/requests/:requestId/approve", () => {
          return HttpResponse.json({ error: "Server error" }, { status: 500 });
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });

      await act(async () => {
        await result.current.handleApprove("req-1");
      });

      // Should still be showing dialog on error
      expect(result.current.showApprovalDialog).toBe(true);
      expect(result.current.isApproving).toBe(false);
    });

    it("handles network error gracefully", async () => {
      server.use(
        http.post("/api/v1/agents/requests/:requestId/approve", () => {
          return HttpResponse.error();
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.openApprovalDialog(sampleApproval);
      });

      await act(async () => {
        await result.current.handleApprove("req-1");
      });

      // Should still be showing dialog on error
      expect(result.current.showApprovalDialog).toBe(true);
      expect(result.current.isApproving).toBe(false);
    });
  });

  describe("Disabled State", () => {
    it("does not process requests when disabled", () => {
      mockUseFeatureFlag.mockImplementation(() => false);
      mockWebSocketReturn.pendingApprovals = [sampleApproval];

      const store = createTestStore();
      const { result } = renderHook(() => useHITLDialogs(), {
        wrapper: createWrapper(store),
      });

      // Should not auto-open dialog when disabled
      expect(result.current.showApprovalDialog).toBe(false);
    });
  });
});
