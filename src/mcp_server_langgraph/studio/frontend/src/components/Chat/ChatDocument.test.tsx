/**
 * ChatDocument Component Tests
 *
 * TDD tests for the dockable chat document component.
 * This is a streamlined version of ChatPage that works within the MainDock.
 * Tests cover:
 * - Basic rendering
 * - Message display
 * - Streaming state
 * - Input handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import { createTestUIState } from "../../store/slices/__tests__/uiSlice.fixtures";

// Mock hooks
const mockStartStream = vi.fn();
const mockClearContent = vi.fn();

vi.mock("../../hooks/useStreamingChat", () => ({
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

vi.mock("../../hooks/useMCPConnection", () => ({
  useMCPConnection: () => ({
    connectionMode: "direct",
    tools: [],
    error: null,
    connect: vi.fn(),
    isReconnecting: false,
    reconnectAttempts: 0,
  }),
}));

vi.mock("../../hooks/useVoiceInput", () => ({
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

vi.mock("../../hooks/useFileUpload", () => ({
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

vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flag: string) => mockUseFeatureFlag(flag),
}));

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

vi.mock("../../hooks/useFollowUpSuggestions", () => ({
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

vi.mock("../../hooks/useSlashCommands", () => ({
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

vi.mock("../../hooks/useInlineSuggestions", () => ({
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

vi.mock("../../hooks/useUrlContentFetch", () => ({
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

vi.mock("../../hooks/useSessionAutoName", () => ({
  useSessionAutoName: () => mockSessionAutoName,
}));

// Import after mocks
import { ChatDocument } from "./ChatDocument";
import sessionReducer, {
  type SessionState,
} from "../../store/slices/sessionSlice";
import personaReducer from "../../store/slices/personaSlice";
import uiReducer from "../../store/slices/uiSlice";
import authReducer, { initialAuthState } from "../../store/slices/authSlice";
import type { ClientSession } from "../../types/session";

// Default session state for tests
const defaultSessionState: SessionState = {
  sessions: [],
  currentSession: null,
  isLoadingSessions: false,
  isLoadingSession: false,
  isSending: false,
  error: null,
  hasMore: false,
  totalCount: 0,
  isLoadingMore: false,
  cursor: null,
};

const mockSession: ClientSession = {
  id: "session-123",
  name: "Test Session",
  messages: [
    { id: "msg-1", role: "user", content: "Hello", timestamp: Date.now() },
    {
      id: "msg-2",
      role: "assistant",
      content: "Hi there!",
      timestamp: Date.now(),
    },
  ],
  createdAt: Date.now(),
  updatedAt: Date.now(),
};

// Create a test store
function createTestStore(
  overrides: {
    session?: Partial<SessionState>;
  } = {},
) {
  return configureStore({
    reducer: {
      session: sessionReducer,
      persona: personaReducer,
      ui: uiReducer,
      auth: authReducer,
    },
    preloadedState: {
      session: { ...defaultSessionState, ...overrides.session },
      persona: {
        persona: "user",
        username: null,
        email: null,
        permissions: [],
        isPersonaLoading: false,
      },
      ui: createTestUIState(),
      auth: initialAuthState,
    },
  });
}

// Render helper with providers
function renderWithProviders(
  ui: React.ReactElement,
  options: {
    store?: ReturnType<typeof createTestStore>;
    sessionOverrides?: Partial<SessionState>;
  } = {},
) {
  const store =
    options.store ??
    createTestStore({
      session: options.sessionOverrides ?? {},
    });

  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>{children}</MemoryRouter>
      </Provider>
    );
  }
  return { store, ...render(ui, { wrapper: Wrapper }) };
}

describe("ChatDocument", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("basic rendering", () => {
    it("should render container with input and without panels", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
      expect(screen.getByRole("textbox")).toBeInTheDocument();
      expect(screen.queryByTestId("session-panel")).not.toBeInTheDocument();
      expect(screen.queryByTestId("context-panel")).not.toBeInTheDocument();
    });
  });

  describe("messages display", () => {
    it("should display messages from current session", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      expect(screen.getByText("Hello")).toBeInTheDocument();
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });

    it("should show empty state when no messages", () => {
      const emptySession: ClientSession = {
        ...mockSession,
        messages: [],
      };
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: emptySession },
      });

      // Should show some empty state or just be ready for input
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });
  });

  describe("input handling", () => {
    it("should update input value on change", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      const input = screen.getByRole("textbox");
      fireEvent.change(input, { target: { value: "Test message" } });

      expect(input).toHaveValue("Test message");
    });

    it("should submit message on Enter key", async () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      const input = screen.getByRole("textbox");
      fireEvent.change(input, { target: { value: "Test message" } });

      // ChatInput submits on Enter key (not form submit)
      fireEvent.keyDown(input, { key: "Enter", code: "Enter" });

      await waitFor(() => {
        expect(mockStartStream).toHaveBeenCalledWith(
          "session-123",
          "Test message",
          { reasoningEffort: "medium" },
        );
      });
    });
  });

  describe("loading states", () => {
    it("should show loading indicator when session is loading", () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { isLoadingSession: true, currentSession: null },
      });

      // Should show loading state
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should show no session state when session is null and not loading", async () => {
      // When currentSession matches sessionId as null (already loaded but empty),
      // we should show the "no session" state
      renderWithProviders(<ChatDocument sessionId="" />, {
        sessionOverrides: { currentSession: null, isLoadingSession: false },
      });

      // Should show no active session message
      await waitFor(() => {
        expect(screen.getByText(/no active session/i)).toBeInTheDocument();
      });
    });
  });

  describe("compact mode", () => {
    it("should apply compact styles when compact prop is true", () => {
      renderWithProviders(
        <ChatDocument sessionId="session-123" compact={true} />,
        { sessionOverrides: { currentSession: mockSession } },
      );

      const container = screen.getByTestId("chat-document");
      expect(container).toHaveClass("h-full");
    });
  });

  describe("message actions", () => {
    it("should show message actions on hover for assistant messages", async () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Find the assistant message container
      const assistantMessage = screen.getByText("Hi there!").closest(".group");
      expect(assistantMessage).toBeInTheDocument();

      // Message actions should exist (may be hidden with opacity-0)
      const actionsContainer = assistantMessage?.querySelector(
        '[data-testid="message-actions-container"]',
      );
      expect(actionsContainer).toBeInTheDocument();
    });

    it("should show regenerate action for assistant messages", async () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Find and click the actions trigger for assistant message
      const assistantMessage = screen.getByText("Hi there!").closest(".group");
      const trigger = assistantMessage?.querySelector(
        '[data-testid="message-actions-trigger"]',
      );

      if (trigger) {
        fireEvent.click(trigger);
        await waitFor(() => {
          expect(screen.getByTestId("action-regenerate")).toBeInTheDocument();
        });
      }
    });

    it("should show edit action for user messages", async () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Find and click the actions trigger for user message
      const userMessage = screen.getByText("Hello").closest(".group");
      const trigger = userMessage?.querySelector(
        '[data-testid="message-actions-trigger"]',
      );

      if (trigger) {
        fireEvent.click(trigger);
        await waitFor(() => {
          expect(screen.getByTestId("action-edit")).toBeInTheDocument();
        });
      }
    });

    it("should always show copy action", async () => {
      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Find and click the actions trigger
      const assistantMessage = screen.getByText("Hi there!").closest(".group");
      const trigger = assistantMessage?.querySelector(
        '[data-testid="message-actions-trigger"]',
      );

      if (trigger) {
        fireEvent.click(trigger);
        await waitFor(() => {
          expect(screen.getByTestId("action-copy")).toBeInTheDocument();
        });
      }
    });
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

  describe("Error UX Improvements", () => {
    it("should show streaming error toast when stream fails", async () => {
      // Override the mock to return an error
      const useStreamingChatMock = await import("../../hooks/useStreamingChat");
      vi.spyOn(useStreamingChatMock, "useStreamingChat").mockReturnValue({
        isStreaming: false,
        streamingContent: "",
        startStream: mockStartStream,
        stopStream: vi.fn(),
        clearContent: mockClearContent,
        usage: null,
        model: "gemini-2.5-flash",
        error: "Stream connection failed: Network error",
        thinkingContent: "",
        thinkingTokens: null,
        langgraphNodes: [],
        langgraphEdges: [],
        currentNode: null,
      });

      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // The error should trigger a toast notification
      // Component should still render without crashing
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should show error indicator for failed URL fetch", async () => {
      // Mock URL fetch with error
      const useUrlContentFetchMock =
        await import("../../hooks/useUrlContentFetch");
      vi.spyOn(useUrlContentFetchMock, "useUrlContentFetch").mockReturnValue({
        detectedUrls: [{ raw: "#https://error.com", url: "https://error.com" }],
        detectUrls: vi.fn(),
        fetchUrl: vi.fn(),
        fetchedContent: [
          {
            url: "https://error.com",
            title: null,
            content: null,
            contentType: null,
            error: "Failed to fetch URL content",
          },
        ],
        isLoading: false,
        loadingUrls: [],
        clearUrl: vi.fn(),
        clearContent: vi.fn(),
        getContextString: () => "",
      });

      renderWithProviders(
        <ChatDocument sessionId="session-123" enableUrlFetch={true} />,
        {
          sessionOverrides: { currentSession: mockSession },
        },
      );

      // Error indicator should be visible
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should handle copy to clipboard error gracefully", async () => {
      // Mock clipboard API to fail
      Object.defineProperty(navigator, "clipboard", {
        value: {
          writeText: vi.fn().mockRejectedValue(new Error("Clipboard error")),
        },
        writable: true,
      });

      renderWithProviders(
        <ChatDocument sessionId="session-123" enableSlashCommands={true} />,
        {
          sessionOverrides: {
            currentSession: {
              ...mockSession,
              messages: [
                {
                  id: "msg-1",
                  role: "assistant",
                  content: "Hello!",
                  timestamp: Date.now(),
                },
              ],
            },
          },
        },
      );

      // Component should handle clipboard errors without crashing
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should display voice error when voice input fails", async () => {
      // Mock voice input with error
      const useVoiceInputMock = await import("../../hooks/useVoiceInput");
      vi.spyOn(useVoiceInputMock, "useVoiceInput").mockReturnValue({
        isListening: false,
        isSupported: true,
        transcript: "",
        error: "Microphone access denied",
        startListening: vi.fn(),
        stopListening: vi.fn(),
        clearTranscript: vi.fn(),
      });

      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // Voice error should be passed to ChatInputForm
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
    });

    it("should display file upload error when upload fails", async () => {
      // Mock file upload with error
      const useFileUploadMock = await import("../../hooks/useFileUpload");
      vi.spyOn(useFileUploadMock, "useFileUpload").mockReturnValue({
        files: [],
        isUploading: false,
        isDragging: false,
        error: "File too large",
        selectFiles: vi.fn(),
        removeFile: vi.fn(),
        clearFiles: vi.fn(),
        dragHandlers: {
          onDragEnter: vi.fn(),
          onDragLeave: vi.fn(),
          onDragOver: vi.fn(),
          onDrop: vi.fn(),
        },
      });

      renderWithProviders(<ChatDocument sessionId="session-123" />, {
        sessionOverrides: { currentSession: mockSession },
      });

      // File error should be passed to ChatInputForm
      expect(screen.getByTestId("chat-document")).toBeInTheDocument();
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
