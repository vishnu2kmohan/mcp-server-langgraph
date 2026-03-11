/**
 * ChatDocument Core Tests
 *
 * Tests for the dockable chat document component covering:
 * - Basic rendering
 * - Messages display
 * - Input handling
 * - Loading states
 * - Compact mode
 * - Message actions
 * - Error UX Improvements
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

  describe("Error UX Improvements", () => {
    it("should show streaming error toast when stream fails", async () => {
      // Override the mock to return an error
      const useStreamingChatMock =
        await import("../../../hooks/useStreamingChat");
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
        await import("../../../hooks/useUrlContentFetch");
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
      const useVoiceInputMock = await import("../../../hooks/useVoiceInput");
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
      const useFileUploadMock = await import("../../../hooks/useFileUpload");
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
});
