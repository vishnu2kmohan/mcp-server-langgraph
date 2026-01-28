/**
 * ConnectedConversationPanel InlinePlanCard Integration Tests
 *
 * Tests for execution plan approval workflow integration.
 * Verifies InlinePlanCard rendering and action callbacks.
 */
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConnectedConversationPanel } from "./ConnectedConversationPanel";
import {
  createTestStore,
  createWrapper,
} from "./ConnectedConversationPanel.fixtures";
import {
  mockSessionLoaderData,
  mockRevalidate,
  mockRevalidateMessages,
  mockUseSessionAutoName,
  mockStreamingChatReturn,
  resetMocks,
} from "./ConnectedConversationPanel.mocks.test-utils";
import type { ExecutionPlan } from "../store/slices/executionModeSlice";

// =============================================================================
// Mocks
// =============================================================================

vi.mock("react-router", async () => {
  const actual =
    await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useRouteLoaderData: vi.fn((routeId: string) => {
      if (routeId === "chat-session") {
        return mockSessionLoaderData;
      }
      if (routeId === "chat-index") {
        return undefined;
      }
      return undefined;
    }),
    useRevalidator: vi.fn(() => ({
      revalidate: mockRevalidate,
      state: "idle",
    })),
    useParams: () => ({ sessionId: "test-session-123" }),
    useNavigate: () => vi.fn(),
  };
});

vi.mock("../hooks/useMessageRevalidation", () => ({
  useMessageRevalidation: () => ({
    revalidateMessages: mockRevalidateMessages,
  }),
}));

vi.mock("../hooks/useSessionAutoName", () => ({
  useSessionAutoName: (options: unknown) => {
    mockUseSessionAutoName(options);
    return {
      isGenerating: false,
      isSuccess: false,
      generatedTitle: undefined,
      hasDefaultName: true,
      error: undefined,
    };
  },
  default: (options: unknown) => {
    mockUseSessionAutoName(options);
    return {
      isGenerating: false,
      isSuccess: false,
      generatedTitle: undefined,
      hasDefaultName: true,
      error: undefined,
    };
  },
}));

vi.mock("../hooks/useStreamingChat", () => ({
  useStreamingChat: () => mockStreamingChatReturn,
}));

vi.mock("../hooks/useConversationIntelligence", () => ({
  useIntentDetection: vi.fn(() => ({
    intent: null,
    confidence: null,
    subIntents: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useContextOptimization: vi.fn(() => ({
    suggestions: [],
    usagePercent: 50,
    currentTokens: 64000,
    maxTokens: 128000,
    recommendedAction: null,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useGoalTracking: vi.fn(() => ({
    goals: [],
    currentGoal: null,
    trackGoal: vi.fn(),
    completeGoal: vi.fn(),
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

vi.mock("../hooks/useAIRealTimeUXSuggestions", () => ({
  useAIRealTimeUXSuggestions: () => ({
    suggestions: [],
    requestSuggestions: vi.fn(),
    dismissSuggestion: vi.fn(),
    isConnected: true,
    error: null,
  }),
}));

vi.mock("../hooks/useArtifactExtraction", () => ({
  useArtifactExtraction: () => ({
    extractAndSaveArtifacts: vi.fn(),
    resetExtraction: vi.fn(),
    extractedArtifacts: [],
  }),
}));

vi.mock("../hooks/useSessionSync", () => ({
  useSessionSync: vi.fn(),
}));

vi.mock("../hooks/useInlineSuggestions", () => ({
  useInlineSuggestions: vi.fn(() => ({
    suggestion: "",
    isLoading: false,
    accept: vi.fn(),
    dismiss: vi.fn(),
  })),
}));

vi.mock("../hooks/useAISuggestionsWebSocket", () => ({
  useAISuggestionsWebSocket: vi.fn(() => ({
    isConnected: false,
    suggestions: [],
    error: null,
    requestSuggestions: vi.fn(),
    clearSuggestions: vi.fn(),
  })),
}));

vi.mock("../contexts/TelemetryContext", () => ({
  TelemetryProvider: ({ children }: { children: React.ReactNode }) => children,
  useSessionTelemetry: () => ({
    trackSessionCreation: vi.fn(),
    trackRevalidation: vi.fn(),
    trackSync: vi.fn(),
    trackBypassApproval: vi.fn(),
    getMetrics: () => ({}),
  }),
}));

// =============================================================================
// Test Data
// =============================================================================

// Full 27-field mockPlan matching ExecutionPlan interface
const mockPlan: ExecutionPlan = {
  // Core identification
  planId: "plan-123",
  sessionId: "test-session-123",
  status: "awaiting_approval",
  // Classification
  complexity: "complicated",
  riskLevel: "medium",
  taskType: "code_generation",
  // Model configuration
  executorModel: "claude-opus-4",
  criticModel: "claude-sonnet-4",
  // Cost tracking
  estimatedCost: "$0.15",
  actualCost: null,
  // Content
  message: "Generate a React component",
  toolsNeeded: ["code_interpreter", "file_write"],
  // Approval configuration
  forceApproval: false,
  confidence: 0.85,
  // Orchestrator
  suggestedOrchestrator: "standard",
  orchestrator: "standard",
  // Computed
  requiresApproval: true,
  // Thinking configuration
  thinkingBudget: "high",
  critiqueRounds: 2,
  // Timestamps
  createdAt: "2025-01-27T10:00:00Z",
  expiresAt: "2025-01-27T11:00:00Z",
  executedAt: null,
  approvedBy: null,
  approvedAt: null,
  rejectedBy: null,
  rejectedAt: null,
  rejectionReason: null,
};

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedConversationPanel - InlinePlanCard", () => {
  beforeEach(() => {
    resetMocks();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Plan Card Rendering", () => {
    it("should render InlinePlanCard when there is a pending plan that requires approval", () => {
      const store = createTestStore({
        executionMode: {
          executionMode: "plan",
          currentPlan: mockPlan,
          planStatus: "awaiting_approval",
          userIsAdmin: false,
          hasBypassPermission: false,
        },
      });

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // InlinePlanCard should be rendered
      expect(screen.getByTestId("inline-plan-card")).toBeInTheDocument();
      expect(screen.getByText("Execution Plan")).toBeInTheDocument();
    });

    it("should not render InlinePlanCard when there is no pending plan", () => {
      const store = createTestStore({
        executionMode: {
          executionMode: "default",
          currentPlan: null,
          planStatus: "idle",
          userIsAdmin: false,
          hasBypassPermission: false,
        },
      });

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // InlinePlanCard should not be rendered
      expect(screen.queryByTestId("inline-plan-card")).not.toBeInTheDocument();
    });

    it("should not render InlinePlanCard when plan is already approved", () => {
      const approvedPlan: ExecutionPlan = {
        ...mockPlan,
        status: "approved",
      };

      const store = createTestStore({
        executionMode: {
          executionMode: "plan",
          currentPlan: approvedPlan,
          planStatus: "approved",
          userIsAdmin: false,
          hasBypassPermission: false,
        },
      });

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // InlinePlanCard should not be rendered for approved plans
      expect(screen.queryByTestId("inline-plan-card")).not.toBeInTheDocument();
    });

    it("should not render InlinePlanCard when plan does not require approval", () => {
      const autoApprovedPlan: ExecutionPlan = {
        ...mockPlan,
        requiresApproval: false,
      };

      const store = createTestStore({
        executionMode: {
          executionMode: "auto_accept",
          currentPlan: autoApprovedPlan,
          planStatus: "awaiting_approval",
          userIsAdmin: false,
          hasBypassPermission: false,
        },
      });

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // InlinePlanCard should not be rendered when requiresApproval is false
      expect(screen.queryByTestId("inline-plan-card")).not.toBeInTheDocument();
    });
  });

  describe("Plan Card Actions", () => {
    it("should dispatch setPlanStatus approved when Approve button is clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore({
        executionMode: {
          executionMode: "plan",
          currentPlan: mockPlan,
          planStatus: "awaiting_approval",
          userIsAdmin: false,
          hasBypassPermission: false,
        },
      });

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Click Approve button
      const approveButton = screen.getByRole("button", { name: /approve/i });
      await user.click(approveButton);

      // Check that plan status was updated in store
      const state = store.getState();
      expect(state.executionMode.planStatus).toBe("approved");
    });

    it("should dispatch setPlanStatus rejected when Reject button is clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore({
        executionMode: {
          executionMode: "plan",
          currentPlan: mockPlan,
          planStatus: "awaiting_approval",
          userIsAdmin: false,
          hasBypassPermission: false,
        },
      });

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Click Reject button
      const rejectButton = screen.getByRole("button", { name: /reject/i });
      await user.click(rejectButton);

      // Check that plan status was updated in store
      const state = store.getState();
      expect(state.executionMode.planStatus).toBe("rejected");
    });
  });

  describe("Plan Card Display", () => {
    it("should display plan details correctly", () => {
      const store = createTestStore({
        executionMode: {
          executionMode: "plan",
          currentPlan: mockPlan,
          planStatus: "awaiting_approval",
          userIsAdmin: false,
          hasBypassPermission: false,
        },
      });

      render(<ConnectedConversationPanel />, {
        wrapper: createWrapper(store),
      });

      // Check plan details are displayed
      expect(screen.getByText("Complicated")).toBeInTheDocument();
      expect(screen.getByText("Medium Risk")).toBeInTheDocument();
      expect(screen.getByText("claude-opus-4")).toBeInTheDocument();
      expect(screen.getByText("$0.15")).toBeInTheDocument();
      expect(
        screen.getByText("code_interpreter, file_write"),
      ).toBeInTheDocument();
    });
  });
});
