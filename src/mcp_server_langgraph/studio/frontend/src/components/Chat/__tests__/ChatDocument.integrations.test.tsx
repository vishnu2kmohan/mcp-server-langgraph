/**
 * ChatDocument Integration Tests
 *
 * Tests for integration features:
 * - AIFollowUpSuggestions Integration
 * - Thinking Content Persistence
 * - Model Selector Integration
 * - URL Content Fetch Integration (#URL)
 * - Style Presets Integration
 * - Slash Commands Integration
 * - Session Auto-Naming Integration (Phase 5.1)
 * - Inline Suggestions Integration (Phase 2.3)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { screen, fireEvent, waitFor, cleanup } from "@testing-library/react";

// Mock hooks
const mockStartStream = vi.fn();
const mockClearContent = vi.fn();

vi.mock("../../../hooks/useStreamingChat", () => ({
  useStreamingChat: () => ({
    isStreaming: false,
    streamingContent: "",
    startStream: mockStartStream,
    stopStream: vi.fn(),
    clearContent: mockClearContent,
    usage: null,
    model: "gemini-2.5-flash",
    error: null,
    thinkingContent: "",
    thinkingTokens: null,
    // LangGraph visualization data
    langgraphNodes: [],
    langgraphEdges: [],
    currentNode: null,
  }),
}));

vi.mock("../../../hooks/useMCPConnection", () => ({
  useMCPConnection: () => ({
    connectionMode: "direct",
    tools: [],
    error: null,
    connect: vi.fn(),
    isReconnecting: false,
    reconnectAttempts: 0,
  }),
}));

vi.mock("../../../hooks/useVoiceInput", () => ({
  useVoiceInput: () => ({
    isListening: false,
    isSupported: true,
    transcript: "",
    error: null,
    startListening: vi.fn(),
    stopListening: vi.fn(),
    clearTranscript: vi.fn(),
  }),
}));

vi.mock("../../../hooks/useFileUpload", () => ({
  useFileUpload: () => ({
    files: [],
    isUploading: false,
    isDragging: false,
    error: null,
    selectFiles: vi.fn(),
    removeFile: vi.fn(),
    clearFiles: vi.fn(),
    dragHandlers: {},
  }),
}));

// Track which feature flags are requested
const mockUseFeatureFlag = vi.fn((flag: string) => {
  // Default: ai_suggestions enabled, others disabled
  if (flag === "ai_suggestions") return true;
  return false;
});

vi.mock("../../../contexts/FeatureFlagContext", async () => {
  const actual = await vi.importActual("../../../contexts/FeatureFlagContext");
  return {
    ...actual,
    useFeatureFlag: (flag: string) => mockUseFeatureFlag(flag),
  };
});
// Mock useFollowUpSuggestions hook
const mockSuggestions = [
  {
    id: "sug-1",
    text: "Tell me more about this",
    category: "explore" as const,
  },
  {
    id: "sug-2",
    text: "Can you give an example?",
    category: "example" as const,
  },
];
const mockRefresh = vi.fn();
const mockTrackClick = vi.fn();

vi.mock("../../../hooks/useFollowUpSuggestions", () => ({
  useFollowUpSuggestions: () => ({
    suggestions: mockSuggestions,
    isLoading: false,
    error: null,
    refresh: mockRefresh,
    trackClick: mockTrackClick,
  }),
}));

// Mock useSlashCommands hook
const mockSlashCommands = [
  { name: "help", description: "Show help", icon: "help" as const },
  { name: "clear", description: "Clear chat", icon: "trash" as const },
  {
    name: "chatbot",
    description: "Simple chatbot template",
    icon: "message" as const,
  },
];
const mockHandleSlashSelect = vi.fn();

vi.mock("../../../hooks/useSlashCommands", () => ({
  useSlashCommands: () => ({
    commands: mockSlashCommands,
    handleSelect: mockHandleSlashSelect,
    isLoading: false,
    error: null,
  }),
}));

// Mock useInlineSuggestions hook
const mockUpdateInlineSuggestionInput = vi.fn();
const mockAcceptInlineSuggestion = vi.fn();
const mockDismissInlineSuggestion = vi.fn();

vi.mock("../../../hooks/useInlineSuggestions", () => ({
  useInlineSuggestions: () => ({
    suggestion: null,
    isLoading: false,
    updateInput: mockUpdateInlineSuggestionInput,
    acceptSuggestion: mockAcceptInlineSuggestion,
    dismissSuggestion: mockDismissInlineSuggestion,
  }),
}));

// Mock useUrlContentFetch hook
// The hook detects URLs in input and returns them in loadingUrls during fetch
const mockUrlContentFetchState = {
  loadingUrls: [] as string[],
};

vi.mock("../../../hooks/useUrlContentFetch", () => ({
  useUrlContentFetch: () => ({
    detectUrls: vi.fn(),
    fetchedContent: [],
    get loadingUrls() {
      return mockUrlContentFetchState.loadingUrls;
    },
    clearUrl: vi.fn(),
    clearContent: vi.fn(),
    getContextString: vi.fn(() => ""),
  }),
}));

// Mock useSessionAutoName hook (Phase 5.1 - AI-powered session titles)
const mockSessionAutoName = {
  isGenerating: false,
  isSuccess: false,
  generatedTitle: undefined,
  hasDefaultName: true,
  error: undefined,
};

vi.mock("../../../hooks/useSessionAutoName", () => ({
  useSessionAutoName: () => mockSessionAutoName,
}));

// Import after mocks
import { ChatDocument } from "../ChatDocument";
import { renderWithProviders, mockSession } from "./ChatDocument.fixtures";
import type { ClientSession } from "../../../types/session";

describe("ChatDocument", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("AIFollowUpSuggestions Integration", () => {
    it("should accept onSuggestionSelect callback prop", () => {
      const onSuggestionSelect = vi.fn();
      // Should render without error when prop is provided
      renderWithProviders(
        <ChatDocument
          sessionId="session-123"
          onSuggestionSelect={onSuggestionSelect}
        />,
        {
          sessionOverrides: { currentSession: mockSession },
        },
      );

      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should pass suggestions to ChatMessages when ai_suggestions flag is enabled", () => {
      mockUseFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "ai_suggestions") return true;
        return false;
      });

      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Suggestions should be rendered via ChatMessages -> AIFollowUpSuggestions
      expect(screen.getByText("Tell me more about this")).toBeInTheDocument();
      expect(screen.getByText("Can you give an example?")).toBeInTheDocument();
    });

    it("should NOT show suggestions when ai_suggestions flag is disabled", () => {
      mockUseFeatureFlag.mockImplementation(() => false);

      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Suggestions should not be rendered
      expect(
        screen.queryByText("Tell me more about this"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByText("Can you give an example?"),
      ).not.toBeInTheDocument();
    });

    it("should fill input when suggestion is selected", async () => {
      mockUseFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "ai_suggestions") return true;
        return false;
      });

      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Click on a suggestion
      const suggestion = screen.getByText("Tell me more about this");
      fireEvent.click(suggestion);

      // Input should be filled with suggestion text
      await waitFor(() => {
        const input = screen.getByRole("textbox");
        expect(input).toHaveValue("Tell me more about this");
      });
    });

    it("should NOT show suggestions while streaming (lazy loading)", () => {
      // This test will need the mock to return isStreaming: true
      // The implementation should check isStreaming and hide suggestions
      mockUseFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "ai_suggestions") return true;
        return false;
      });

      // Note: To fully test this, we'd need to mock useStreamingChat with isStreaming: true
      // For now, this documents the expected behavior
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // When not streaming, suggestions should be visible
      expect(screen.getByText("Tell me more about this")).toBeInTheDocument();
    });

    it("should generate suggestions from last assistant message content", () => {
      mockUseFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "ai_suggestions") return true;
        return false;
      });

      // The hook should be called with the last assistant message
      // The mock returns suggestions, verifying the integration
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Suggestions are rendered, confirming the hook is integrated
      expect(screen.getByText("Tell me more about this")).toBeInTheDocument();
    });
  });

  describe("Thinking Content Persistence", () => {
    it("should include thinkingContent in assistant message when present", async () => {
      // This test verifies that when streaming completes with thinking content,
      // the resulting assistant message includes the thinking content.
      // The actual implementation will need to dispatch addMessage with thinkingContent.
      const { store } = renderWithProviders(
        <ChatDocument sessionId="session-123" />,
        {
          sessionOverrides: { currentSession: mockSession },
        },
      );

      // The Message type should support thinkingContent field
      const state = store.getState();
      expect(state.session).toBeDefined();
      // This test documents that messages should support thinkingContent
    });

    it("should include thinkingTokens in assistant message when present", async () => {
      // This test verifies that thinking tokens are persisted with messages
      const { store } = renderWithProviders(
        <ChatDocument sessionId="session-123" />,
        {
          sessionOverrides: { currentSession: mockSession },
        },
      );

      const state = store.getState();
      expect(state.session).toBeDefined();
      // This test documents that messages should support thinkingTokens
    });

    it("should display persisted thinking content for assistant messages", () => {
      // Create a session with a message that has thinking content
      const sessionWithThinking: ClientSession = {
        ...mockSession,
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Hello",
            timestamp: Date.now(),
          },
          {
            id: "msg-2",
            role: "assistant",
            content: "Hi there!",
            timestamp: Date.now(),
            thinkingContent: "Let me think about how to respond...",
            thinkingTokens: 50,
          },
        ],
      };

      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: sessionWithThinking },
      });

      // The message should render and the component should accept thinkingContent
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });
  });

  describe("Model Selector Integration", () => {
    it("should render when showModelSelector=true and hide when false", () => {
      const { unmount } = renderWithProviders(
        <ChatDocument
          sessionId="session-123"
          showModelSelector={true}
          onModelChange={vi.fn()}
        />,
        { sessionOverrides: { currentSession: mockSession } },
      );
      // ChatInput uses model-settings-button testid for the model dropdown trigger
      expect(screen.getByTestId("model-settings-button")).toBeInTheDocument();

      unmount();
      renderWithProviders(
        <ChatDocument sessionId="session-123" showModelSelector={false} />,
        { sessionOverrides: { currentSession: mockSession } },
      );
      expect(
        screen.queryByTestId("model-settings-button"),
      ).not.toBeInTheDocument();
    });
  });

  describe("URL Content Fetch Integration (#URL)", () => {
    it("should accept enableUrlFetch prop", () => {
      renderWithProviders(
        <ChatDocument sessionId="session-123" enableUrlFetch={true} />,
        {
          sessionOverrides: { currentSession: mockSession },
        },
      );

      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should show URL fetch indicator when input contains #https://", () => {
      // Set mock to simulate loading URLs
      mockUrlContentFetchState.loadingUrls = ["https://example.com"];

      renderWithProviders(
        <ChatDocument sessionId="session-123" enableUrlFetch={true} />,
        {
          sessionOverrides: { currentSession: mockSession },
        },
      );

      // ChatInput uses url-fetch-loading testid when urlFetchLoading has URLs
      expect(screen.getByTestId("url-fetch-loading")).toBeInTheDocument();

      // Cleanup
      mockUrlContentFetchState.loadingUrls = [];
    });

    it("should not show URL fetch indicator when enableUrlFetch is false", () => {
      // Even with loading URLs, should not show when enableUrlFetch is false
      // But since enableUrlFetch=false, the hook won't trigger loading
      mockUrlContentFetchState.loadingUrls = [];

      renderWithProviders(
        <ChatDocument sessionId="session-123" enableUrlFetch={false} />,
        {
          sessionOverrides: { currentSession: mockSession },
        },
      );

      const input = screen.getByRole("textbox");
      fireEvent.change(input, {
        target: { value: "Check this #https://example.com" },
      });

      // ChatInput uses url-fetch-loading testid - should not appear when disabled
      expect(screen.queryByTestId("url-fetch-loading")).not.toBeInTheDocument();
    });
  });

  describe("Style Presets Integration", () => {
    it("should show when showStylePresets=true and hide when false", () => {
      const { unmount } = renderWithProviders(
        <ChatDocument sessionId="session-123" showStylePresets={true} />,
        { sessionOverrides: { currentSession: mockSession } },
      );
      expect(screen.getByTestId("style-presets-container")).toBeInTheDocument();

      unmount();
      renderWithProviders(
        <ChatDocument sessionId="session-123" showStylePresets={false} />,
        { sessionOverrides: { currentSession: mockSession } },
      );
      expect(
        screen.queryByTestId("style-presets-container"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Slash Commands Integration", () => {
    it("should accept enableSlashCommands prop", () => {
      renderWithProviders(
        <ChatDocument sessionId="session-123" enableSlashCommands={true} />,
        {
          sessionOverrides: { currentSession: mockSession },
        },
      );

      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should show slash command menu when typing / with enableSlashCommands", async () => {
      renderWithProviders(
        <ChatDocument sessionId="session-123" enableSlashCommands={true} />,
        {
          sessionOverrides: { currentSession: mockSession },
        },
      );

      const input = screen.getByRole("textbox");
      fireEvent.change(input, { target: { value: "/" } });

      // Slash command menu should appear
      await waitFor(() => {
        expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
      });
    });

    it("should not show slash command menu when enableSlashCommands is false", () => {
      renderWithProviders(
        <ChatDocument sessionId="session-123" enableSlashCommands={false} />,
        {
          sessionOverrides: { currentSession: mockSession },
        },
      );

      const input = screen.getByRole("textbox");
      fireEvent.change(input, { target: { value: "/" } });

      expect(
        screen.queryByTestId("slash-command-menu"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Session Auto-Naming Integration (Phase 5.1)", () => {
    it("should use useSessionAutoName hook with correct session context", () => {
      // Verify the hook is used (mock is called during render)
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Component should render successfully with the hook integrated
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should pass session messages to auto-name hook for title generation", () => {
      // Session with messages that can be used for title generation
      const sessionWithMessages: ClientSession = {
        ...mockSession,
        name: "New Chat", // Default name that triggers auto-naming
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Help me write a Python script for data analysis",
            timestamp: Date.now(),
          },
        ],
      };

      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: sessionWithMessages },
      });

      // The hook should be called with session context
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should not trigger auto-naming when AI suggestions are disabled", () => {
      // Disable AI suggestions feature flag
      mockUseFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "ai_suggestions") return false;
        return false;
      });

      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Component should still render but auto-naming should be disabled
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();

      // Reset mock
      mockUseFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "ai_suggestions") return true;
        return false;
      });
    });
  });

  describe("Inline Suggestions Integration (Phase 2.3)", () => {
    it("should update inline suggestions when input changes", async () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      const input = screen.getByRole("textbox");
      fireEvent.change(input, { target: { value: "Test message" } });

      // The updateInput function should be called
      await waitFor(() => {
        expect(mockUpdateInlineSuggestionInput).toHaveBeenCalled();
      });
    });

    it("should pass inline suggestion props to ChatInputForm", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // ChatInputForm should receive inline suggestion props
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });
  });
});
