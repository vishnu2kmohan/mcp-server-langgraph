/**
 * ConnectedConversationPanel Rendering Tests
 *
 * Tests for basic component rendering.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
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
  mockFetch,
  resetMocks,
} from "./ConnectedConversationPanel.mocks.test-utils";

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
    intent: "code_request",
    confidence: 0.92,
    subIntents: ["generate", "explain"],
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
    primaryGoal: null,
    subGoals: [],
    progressPercent: 0,
    currentFocus: null,
    completedSubGoals: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

vi.mock("../hooks/useKBStatus", () => ({
  useKBStatus: () => ({
    data: undefined,
    status: "ready" as const,
    statusMessage: "Knowledge Base ready",
    isLoading: false,
    isError: false,
    error: null,
    isReady: true,
    isMisconfigured: false,
    isUnavailable: false,
    collectionName: "test-collection",
    vectorsCount: 100,
    contextStats: undefined,
    kbStatusForUI: "ready" as const,
    refetch: vi.fn(),
  }),
}));

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedConversationPanel - Rendering", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should render conversation panel", () => {
    const store = createTestStore();
    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
  });

  it("should render ConversationPanel component", () => {
    const store = createTestStore();
    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    expect(screen.getByTestId("conversation-panel")).toBeInTheDocument();
  });

  it("should apply custom className to wrapper container", () => {
    const store = createTestStore();
    render(<ConnectedConversationPanel className="custom-class" />, {
      wrapper: createWrapper(store),
    });

    // className is applied to the wrapper div containing both AI indicators and ConversationPanel
    // We verify by checking that custom-class exists in the component hierarchy
    const conversationPanel = screen.getByTestId("conversation-panel");
    expect(conversationPanel.parentElement).toHaveClass("custom-class");
  });
});
