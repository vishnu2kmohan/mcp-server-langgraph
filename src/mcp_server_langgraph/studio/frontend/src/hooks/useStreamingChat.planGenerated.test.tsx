/**
 * Tests for useStreamingChat plan_generated SSE Event Handling
 *
 * TDD tests for Issue 7: Wire up plan rendering integration.
 * The hook should dispatch planGenerated events to Redux executionModeSlice.
 *
 * RED Phase: These tests define the expected behavior.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { useStreamingChat } from "./useStreamingChat";
import langGraphReducer from "../store/slices/langGraphSlice";
import executionModeReducer, {
  selectCurrentPlan,
  selectPlanStatus,
} from "../store/slices/executionModeSlice";

// Mock authenticatedFetch
vi.mock("../utils/authenticatedFetch", () => ({
  authenticatedFetch: vi.fn(),
}));

// Mock intendedRoute
vi.mock("../utils/intendedRoute", () => ({
  saveCurrentRouteAsIntended: vi.fn(),
}));

// Create mock response stream
function createMockStream(chunks: string[]) {
  let index = 0;
  return {
    getReader: () => ({
      read: async () => {
        if (index >= chunks.length) {
          return { done: true, value: undefined };
        }
        const chunk = new TextEncoder().encode(chunks[index]);
        index++;
        return { done: false, value: chunk };
      },
    }),
  };
}

// Create mock fetch response
function createMockResponse(chunks: string[]) {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    body: createMockStream(chunks),
  };
}

// Create test wrapper with Redux store including executionMode slice
function createWrapper() {
  const store = configureStore({
    reducer: {
      langGraph: langGraphReducer,
      executionMode: executionModeReducer,
    },
  });

  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>
      <MemoryRouter>{children}</MemoryRouter>
    </Provider>
  );

  return { Wrapper, store };
}

describe("useStreamingChat plan_generated SSE handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  it("should dispatch setPlan to Redux when plan_generated SSE event is received", async () => {
    const { authenticatedFetch } = await import("../utils/authenticatedFetch");
    const mockFetch = vi.mocked(authenticatedFetch);

    const planEvent = {
      plan_generated: {
        plan_id: "plan-123",
        status: "awaiting_approval",
        complexity: "complex",
        risk_level: "high",
        task_type: "code_generation",
        executor_model: "claude-3-5-sonnet-20241022",
        estimated_cost: "$0.15",
        tools_needed: ["write_file", "execute_code"],
        thinking_budget: "high",
        critique_rounds: 2,
        requires_approval: true,
      },
    };

    const sseChunks = [
      `data: ${JSON.stringify(planEvent)}\n\n`,
      'data: {"delta": {"content": "Planning complete..."}}\n\n',
      "data: [DONE]\n\n",
    ];

    mockFetch.mockResolvedValue(
      createMockResponse(sseChunks) as unknown as Response,
    );

    const { Wrapper, store } = createWrapper();
    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.startStream("session-456", "Generate a React component");
    });

    // Wait for the stream to process
    await waitFor(() => {
      expect(result.current.isStreaming).toBe(false);
    });

    // Verify Redux state was updated with plan
    const state = store.getState();
    const currentPlan = selectCurrentPlan(state);
    const planStatus = selectPlanStatus(state);

    expect(currentPlan).not.toBeNull();
    expect(currentPlan?.planId).toBe("plan-123");
    expect(currentPlan?.complexity).toBe("complex");
    expect(currentPlan?.riskLevel).toBe("high");
    expect(currentPlan?.requiresApproval).toBe(true);
    expect(currentPlan?.sessionId).toBe("session-456");
    expect(planStatus).toBe("awaiting_approval");
  });

  it("should include sessionId in dispatched plan", async () => {
    const { authenticatedFetch } = await import("../utils/authenticatedFetch");
    const mockFetch = vi.mocked(authenticatedFetch);

    const planEvent = {
      plan_generated: {
        plan_id: "plan-abc",
        status: "awaiting_approval",
        complexity: "simple",
        risk_level: "low",
        task_type: "explanation",
        executor_model: "gpt-4o",
        estimated_cost: "$0.02",
        tools_needed: [],
        thinking_budget: "low",
        critique_rounds: 0,
        requires_approval: false,
      },
    };

    const sseChunks = [
      `data: ${JSON.stringify(planEvent)}\n\n`,
      "data: [DONE]\n\n",
    ];

    mockFetch.mockResolvedValue(
      createMockResponse(sseChunks) as unknown as Response,
    );

    const { Wrapper, store } = createWrapper();
    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.startStream("my-session-id", "Explain this code");
    });

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(false);
    });

    const state = store.getState();
    const currentPlan = selectCurrentPlan(state);
    expect(currentPlan?.sessionId).toBe("my-session-id");
  });

  it("should handle plan_generated with all fields correctly", async () => {
    const { authenticatedFetch } = await import("../utils/authenticatedFetch");
    const mockFetch = vi.mocked(authenticatedFetch);

    // Full 27-field plan event matching ExecutionPlan interface
    const planEvent = {
      plan_generated: {
        // Core identification
        plan_id: "plan-full",
        session_id: "session-test",
        status: "awaiting_approval",
        // Classification
        complexity: "complicated",
        risk_level: "medium",
        task_type: "refactoring",
        // Model configuration
        executor_model: "claude-3-opus-20240229",
        critic_model: "claude-sonnet-4",
        // Cost tracking
        estimated_cost: "$0.50",
        actual_cost: null,
        // Content
        message: "Refactor this module",
        tools_needed: ["read_file", "write_file", "search_codebase"],
        // Approval configuration
        force_approval: false,
        confidence: 0.85,
        // Orchestrator
        suggested_orchestrator: "standard",
        orchestrator: "standard",
        // Computed
        requires_approval: true,
        // Thinking configuration
        thinking_budget: "medium",
        critique_rounds: 1,
        // Timestamps
        created_at: "2025-01-27T10:00:00Z",
        expires_at: "2025-01-27T11:00:00Z",
        executed_at: null,
        approved_by: null,
        approved_at: null,
        rejected_by: null,
        rejected_at: null,
        rejection_reason: null,
      },
    };

    const sseChunks = [
      `data: ${JSON.stringify(planEvent)}\n\n`,
      "data: [DONE]\n\n",
    ];

    mockFetch.mockResolvedValue(
      createMockResponse(sseChunks) as unknown as Response,
    );

    const { Wrapper, store } = createWrapper();
    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.startStream("session-test", "Refactor this module");
    });

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(false);
    });

    const state = store.getState();
    const currentPlan = selectCurrentPlan(state);

    // Verify full 27-field plan was parsed correctly
    expect(currentPlan).toEqual({
      // Core identification
      planId: "plan-full",
      sessionId: "session-test",
      status: "awaiting_approval",
      // Classification
      complexity: "complicated",
      riskLevel: "medium",
      taskType: "refactoring",
      // Model configuration
      executorModel: "claude-3-opus-20240229",
      criticModel: "claude-sonnet-4",
      // Cost tracking
      estimatedCost: "$0.50",
      actualCost: null,
      // Content
      message: "Refactor this module",
      toolsNeeded: ["read_file", "write_file", "search_codebase"],
      // Approval configuration
      forceApproval: false,
      confidence: 0.85,
      // Orchestrator
      suggestedOrchestrator: "standard",
      orchestrator: "standard",
      // Computed
      requiresApproval: true,
      // Thinking configuration
      thinkingBudget: "medium",
      critiqueRounds: 1,
      // Timestamps
      createdAt: "2025-01-27T10:00:00Z",
      expiresAt: "2025-01-27T11:00:00Z",
      executedAt: null,
      approvedBy: null,
      approvedAt: null,
      rejectedBy: null,
      rejectedAt: null,
      rejectionReason: null,
    });
  });

  it("should not dispatch plan when plan_generated is missing", async () => {
    const { authenticatedFetch } = await import("../utils/authenticatedFetch");
    const mockFetch = vi.mocked(authenticatedFetch);

    // No plan_generated event, just regular content
    const sseChunks = [
      'data: {"delta": {"content": "Hello!"}}\n\n',
      "data: [DONE]\n\n",
    ];

    mockFetch.mockResolvedValue(
      createMockResponse(sseChunks) as unknown as Response,
    );

    const { Wrapper, store } = createWrapper();
    const { result } = renderHook(() => useStreamingChat(), {
      wrapper: Wrapper,
    });

    act(() => {
      result.current.startStream("session-no-plan", "Just say hello");
    });

    await waitFor(() => {
      expect(result.current.isStreaming).toBe(false);
    });

    // Verify no plan was set
    const state = store.getState();
    const currentPlan = selectCurrentPlan(state);
    expect(currentPlan).toBeNull();
  });
});
