/**
 * ConnectedConversationPanel Streaming Tests
 *
 * Tests for streaming error display and thinking content (Phase 3.4).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
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

vi.mock("../hooks/useAvailableTools", () => ({
  useAvailableTools: () => ({
    tools: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock("../hooks/useAISuggestionsWebSocket", () => ({
  useAISuggestionsWebSocket: () => ({
    isConnected: false,
    suggestions: [],
    contextStats: null,
    error: null,
  }),
}));

vi.mock("../hooks/useConnectorSuggestions", () => ({
  useConnectorSuggestions: () => ({
    suggestions: [],
    visible: false,
    dismiss: vi.fn(),
    isLoading: false,
    inputValue: "",
    setInputValue: vi.fn(),
    enabled: false,
  }),
}));

// Mock RTK Query hooks for InlineConnectionCard
vi.mock("../api", () => ({
  useListConnectionTemplatesQuery: () => ({
    data: { templates: [] },
    isLoading: false,
    error: null,
  }),
  useCreateConnectionMutation: () => [vi.fn(), { isLoading: false }],
  useTestConnectionMutation: () => [vi.fn(), { isLoading: false }],
  useStartOAuth2FlowMutation: () => [vi.fn(), { isLoading: false }],
}));

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedConversationPanel - Streaming Error Display", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should display streaming error when error occurs", () => {
    const store = createTestStore();

    // Set error state in mock
    mockStreamingChatReturn.error = "Connection failed: Network error";

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    // Error should be displayed
    expect(screen.getByTestId("streaming-error")).toBeInTheDocument();
    expect(screen.getByText(/Connection failed/i)).toBeInTheDocument();
  });

  it("should not display error indicator when no error", () => {
    const store = createTestStore();

    // No error
    mockStreamingChatReturn.error = null;

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    // Error indicator should not be present
    expect(screen.queryByTestId("streaming-error")).not.toBeInTheDocument();
  });

  it("should allow dismissing streaming error", async () => {
    const store = createTestStore();
    const user = userEvent.setup();

    mockStreamingChatReturn.error = "Temporary connection issue";

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    // Error should be displayed
    expect(screen.getByTestId("streaming-error")).toBeInTheDocument();

    // Click dismiss button
    const dismissButton = screen.getByTestId("dismiss-streaming-error");
    await user.click(dismissButton);

    // Error should be dismissed (component state, not mock)
    await waitFor(() => {
      expect(screen.queryByTestId("streaming-error")).not.toBeInTheDocument();
    });
  });
});

describe("ConnectedConversationPanel - Thinking Content Display", () => {
  beforeEach(() => {
    resetMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should display thinking content when available", () => {
    const store = createTestStore();

    mockStreamingChatReturn.thinkingContent =
      "Analyzing the user request for code generation...";
    mockStreamingChatReturn.isStreaming = true;

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    expect(screen.getByTestId("thinking-content")).toBeInTheDocument();
    expect(screen.getByText(/Analyzing the user request/i)).toBeInTheDocument();
  });

  it("should not display thinking section when no thinking content", () => {
    const store = createTestStore();

    mockStreamingChatReturn.thinkingContent = "";
    mockStreamingChatReturn.isStreaming = true;

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    expect(screen.queryByTestId("thinking-content")).not.toBeInTheDocument();
  });

  it("should display thinking tokens badge when available", () => {
    const store = createTestStore();

    mockStreamingChatReturn.thinkingContent = "Deep thinking...";
    mockStreamingChatReturn.thinkingTokens = 1250;
    mockStreamingChatReturn.isStreaming = true;

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    expect(screen.getByTestId("thinking-tokens-badge")).toBeInTheDocument();
    expect(screen.getByText("1,250")).toBeInTheDocument();
  });

  it("should be collapsible", async () => {
    const store = createTestStore();
    const user = userEvent.setup();

    mockStreamingChatReturn.thinkingContent =
      "Extended thinking process for complex analysis...";
    mockStreamingChatReturn.isStreaming = true;

    render(<ConnectedConversationPanel />, { wrapper: createWrapper(store) });

    // Thinking content visible by default
    expect(screen.getByText(/Extended thinking process/i)).toBeInTheDocument();

    // Click to collapse
    const collapseButton = screen.getByTestId("toggle-thinking-content");
    await user.click(collapseButton);

    // Content should be hidden
    await waitFor(() => {
      expect(
        screen.queryByText(/Extended thinking process/i),
      ).not.toBeInTheDocument();
    });
  });
});
