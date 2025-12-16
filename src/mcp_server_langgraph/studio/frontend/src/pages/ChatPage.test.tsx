/**
 * ChatPage Tests
 *
 * TDD tests for the chat interface page.
 * Tests cover:
 * - Loading state
 * - No session state
 * - Message display
 * - Message sending
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ChatPage } from "./ChatPage";
import sessionReducer, {
  initialSessionState,
} from "../store/slices/sessionSlice";
import * as streamingChatModule from "../hooks/useStreamingChat";
import * as mcpConnectionModule from "../hooks/useMCPConnection";
import * as voiceInputModule from "../hooks/useVoiceInput";
import * as fileUploadModule from "../hooks/useFileUpload";
import * as backgroundSyncModule from "../hooks/useBackgroundSync";
import * as tierLimitsModule from "../hooks/useTierLimits";
import type { SessionState, Session } from "../types/session";

// Mock the streaming chat hook
vi.mock("../hooks/useStreamingChat");

// Mock the MCP connection hook
vi.mock("../hooks/useMCPConnection");

// Mock the voice input hook
vi.mock("../hooks/useVoiceInput");

// Mock the file upload hook
vi.mock("../hooks/useFileUpload");

// Mock the background sync hook
vi.mock("../hooks/useBackgroundSync");

// Mock the tier limits hook
vi.mock("../hooks/useTierLimits");

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

const mockUseStreamingChat = vi.mocked(streamingChatModule.useStreamingChat);
const mockUseMCPConnection = vi.mocked(mcpConnectionModule.useMCPConnection);
const mockUseVoiceInput = vi.mocked(voiceInputModule.useVoiceInput);
const mockUseFileUpload = vi.mocked(fileUploadModule.useFileUpload);
const mockUseBackgroundSync = vi.mocked(backgroundSyncModule.useBackgroundSync);
const mockUseTierLimits = vi.mocked(tierLimitsModule.useTierLimits);

// Create a test store with custom session state
const createTestStore = (sessionState: Partial<SessionState> = {}) => {
  return configureStore({
    reducer: {
      session: sessionReducer,
    },
    preloadedState: {
      session: { ...initialSessionState, ...sessionState },
    },
  });
};

// Helper to render with store and router - async to handle state updates
const renderWithProviders = async (
  component: React.ReactNode,
  {
    sessionState = {},
    initialEntries = ["/"],
  }: { sessionState?: Partial<SessionState>; initialEntries?: string[] } = {},
) => {
  const store = createTestStore(sessionState);
  let result: ReturnType<typeof render>;
  await act(async () => {
    result = render(
      <Provider store={store}>
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={initialEntries}
        >
          {component}
        </MemoryRouter>
      </Provider>,
    );
  });
  return {
    store,
    ...result!,
  };
};

describe("ChatPage", () => {
  const mockStartStream = vi.fn();
  const mockStopStream = vi.fn();
  const mockClearContent = vi.fn();
  const mockConnect = vi.fn();
  const mockDisconnect = vi.fn();
  const mockCallTool = vi.fn();
  const mockStartListening = vi.fn();
  const mockStopListening = vi.fn();
  const mockClearTranscript = vi.fn();
  const mockSelectFiles = vi.fn();
  const mockRemoveFile = vi.fn();
  const mockClearFilesUpload = vi.fn();
  const mockUploadFiles = vi.fn();
  const mockCancelUpload = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();

    // Default MCP connection mock
    mockUseMCPConnection.mockReturnValue({
      isConnected: true,
      connectionMode: "websocket" as const,
      tools: [
        { name: "calculator", description: "Perform math calculations" },
        { name: "web_search", description: "Search the web" },
      ],
      error: null,
      connect: mockConnect,
      disconnect: mockDisconnect,
      callTool: mockCallTool,
    });

    // Default streaming chat mock
    mockUseStreamingChat.mockReturnValue({
      isStreaming: false,
      streamingContent: "",
      error: null,
      usage: null,
      model: null,
      startStream: mockStartStream,
      stopStream: mockStopStream,
      clearContent: mockClearContent,
    });

    // Default voice input mock
    mockUseVoiceInput.mockReturnValue({
      isListening: false,
      isSupported: true,
      transcript: "",
      error: null,
      startListening: mockStartListening,
      stopListening: mockStopListening,
      clearTranscript: mockClearTranscript,
    });

    // Default file upload mock
    mockUseFileUpload.mockReturnValue({
      files: [],
      isUploading: false,
      isDragging: false,
      progress: 0,
      error: null,
      selectFiles: mockSelectFiles,
      removeFile: mockRemoveFile,
      clearFiles: mockClearFilesUpload,
      uploadFiles: mockUploadFiles,
      cancelUpload: mockCancelUpload,
      dragHandlers: {
        onDragEnter: vi.fn(),
        onDragLeave: vi.fn(),
        onDragOver: vi.fn(),
        onDrop: vi.fn(),
      },
    });

    // Default background sync mock
    mockUseBackgroundSync.mockReturnValue({
      isSupported: true,
      isInitialized: true,
      isOnline: true,
      isSyncing: false,
      pendingCount: 0,
      lastError: null,
      queueRequest: vi.fn(),
      syncNow: vi.fn(),
      clearQueue: vi.fn(),
      getQueue: vi.fn(() => []),
    });

    // Default tier limits mock
    mockUseTierLimits.mockReturnValue({
      tier: "shared" as const,
      maxSessions: 5,
      maxWorkflows: 3,
      maxConnectionsPerProject: 2,
      activeSessions: 1,
      isApproachingLimit: false,
      isAtLimit: false,
      nextTier: "hybrid",
      isLoading: false,
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner when loading session", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { isLoadingSession: true },
      });

      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("No Session State", () => {
    it("should show no session message when no current session", async () => {
      // Set isLoadingSessions to prevent fetchSessions from being called
      await renderWithProviders(<ChatPage />, {
        sessionState: { isLoadingSessions: true },
      });

      expect(screen.getByText("No Active Session")).toBeInTheDocument();
      expect(
        screen.getByText("Create a new session to start chatting."),
      ).toBeInTheDocument();
    });
  });

  describe("Session Loaded", () => {
    const mockSession: Session = {
      id: "session-1",
      name: "Test Session",
      config: {
        modelProvider: "openai",
        modelName: "gpt-4",
        temperature: 0.7,
        maxTokens: 4096,
      },
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("should display session name in header", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText("Test Session")).toBeInTheDocument();
    });

    it("should display message count", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText("0 messages")).toBeInTheDocument();
    });

    it("should show empty state when no messages", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(
        screen.getByText("No messages yet. Start a conversation!"),
      ).toBeInTheDocument();
    });

    it("should show Clear button", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText("Clear")).toBeInTheDocument();
    });
  });

  describe("Messages Display", () => {
    const mockSessionWithMessages: Session = {
      id: "session-1",
      name: "Test Session",
      config: {
        modelProvider: "openai",
        modelName: "gpt-4",
        temperature: 0.7,
        maxTokens: 4096,
      },
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

    it("should display messages", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSessionWithMessages },
      });

      expect(screen.getByText("Hello")).toBeInTheDocument();
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });

    it("should display correct message count", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSessionWithMessages },
      });

      expect(screen.getByText("2 messages")).toBeInTheDocument();
    });
  });

  describe("Message Sending", () => {
    const mockSession: Session = {
      id: "session-1",
      name: "Test Session",
      config: {
        modelProvider: "openai",
        modelName: "gpt-4",
        temperature: 0.7,
        maxTokens: 4096,
      },
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("should have input field and send button", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(
        screen.getByPlaceholderText("Type your message..."),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    });

    it("should disable send button when input is empty", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      const sendButton = screen.getByRole("button", { name: /send/i });
      expect(sendButton).toBeDisabled();
    });

    it("should enable send button when input has text", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      const input = screen.getByPlaceholderText("Type your message...");
      fireEvent.change(input, { target: { value: "Hello" } });

      const sendButton = screen.getByRole("button", { name: /send/i });
      expect(sendButton).not.toBeDisabled();
    });

    it("should dispatch addMessage and start stream when form is submitted", async () => {
      const { store } = await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      const input = screen.getByPlaceholderText("Type your message...");
      fireEvent.change(input, { target: { value: "Hello" } });

      const form = input.closest("form")!;
      fireEvent.submit(form);

      await waitFor(() => {
        // Check that user message was added to Redux store
        const state = store.getState();
        expect(state.session.currentSession?.messages).toHaveLength(1);
        expect(state.session.currentSession?.messages[0].role).toBe("user");
        expect(state.session.currentSession?.messages[0].content).toBe("Hello");
        // Should start streaming
        expect(mockStartStream).toHaveBeenCalledWith("session-1", "Hello");
      });
    });

    it("should clear input after sending", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      const input = screen.getByPlaceholderText("Type your message...");
      fireEvent.change(input, { target: { value: "Hello" } });

      const form = input.closest("form")!;
      fireEvent.submit(form);

      await waitFor(() => {
        expect(input).toHaveValue("");
      });
    });
  });

  describe("Sending State", () => {
    const mockSession: Session = {
      id: "session-1",
      name: "Test Session",
      config: {
        modelProvider: "openai",
        modelName: "gpt-4",
        temperature: 0.7,
        maxTokens: 4096,
      },
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("should show thinking indicator when sending (legacy)", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession, isSending: true },
      });

      expect(screen.getByText("Thinking...")).toBeInTheDocument();
    });

    it("should show streaming content when streaming", async () => {
      mockUseStreamingChat.mockReturnValue({
        isStreaming: true,
        streamingContent: "Hello from AI",
        error: null,
        startStream: mockStartStream,
        stopStream: mockStopStream,
        clearContent: mockClearContent,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText(/Hello from AI/)).toBeInTheDocument();
    });

    it("should disable input when streaming", async () => {
      mockUseStreamingChat.mockReturnValue({
        isStreaming: true,
        streamingContent: "",
        error: null,
        startStream: mockStartStream,
        stopStream: mockStopStream,
        clearContent: mockClearContent,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      const input = screen.getByPlaceholderText("Type your message...");
      expect(input).toBeDisabled();
    });
  });

  describe("Error Handling", () => {
    const mockSession: Session = {
      id: "session-1",
      name: "Test Session",
      config: {
        modelProvider: "openai",
        modelName: "gpt-4",
        temperature: 0.7,
        maxTokens: 4096,
      },
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("should display error banner when error exists", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: {
          currentSession: mockSession,
          error: "Something went wrong",
        },
      });

      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });

    it("should show dismiss button for errors", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: {
          currentSession: mockSession,
          error: "Something went wrong",
        },
      });

      expect(screen.getByText("Dismiss")).toBeInTheDocument();
    });

    it("should clear error when dismiss is clicked", async () => {
      const { store } = await renderWithProviders(<ChatPage />, {
        sessionState: {
          currentSession: mockSession,
          error: "Something went wrong",
        },
      });

      fireEvent.click(screen.getByText("Dismiss"));

      await waitFor(() => {
        const state = store.getState();
        expect(state.session.error).toBeNull();
      });
    });
  });

  describe("Auto Session Management", () => {
    it("should have sessions state empty by default", async () => {
      // Set isLoadingSessions to prevent fetchSessions from being called
      const { store } = await renderWithProviders(<ChatPage />, {
        sessionState: { isLoadingSessions: true },
      });

      const state = store.getState();
      expect(state.session.sessions).toEqual([]);
      expect(state.session.currentSession).toBeNull();
    });

    it("should not throw when no session exists", async () => {
      // Set isLoadingSessions to prevent fetchSessions from being called
      await expect(async () => {
        await renderWithProviders(<ChatPage />, {
          sessionState: { isLoadingSessions: true },
        });
      }).not.toThrow();
    });
  });

  describe("Usage Tracking", () => {
    const mockSession: Session = {
      id: "session-1",
      name: "Test Session",
      config: {
        modelProvider: "openai",
        modelName: "gpt-4",
        temperature: 0.7,
        maxTokens: 4096,
      },
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("should display session cost from streaming usage", async () => {
      mockUseStreamingChat.mockReturnValue({
        isStreaming: false,
        streamingContent: "",
        error: null,
        usage: {
          promptTokens: 100,
          completionTokens: 50,
          totalTokens: 150,
        },
        model: "gpt-4",
        startStream: mockStartStream,
        stopStream: mockStopStream,
        clearContent: mockClearContent,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      // Session cost should be displayed in the ContextPanel
      expect(screen.getByText(/150/)).toBeInTheDocument(); // Total tokens
    });

    it("should show model name from streaming response", async () => {
      mockUseStreamingChat.mockReturnValue({
        isStreaming: false,
        streamingContent: "",
        error: null,
        usage: {
          promptTokens: 10,
          completionTokens: 5,
          totalTokens: 15,
        },
        model: "gpt-4-turbo",
        startStream: mockStartStream,
        stopStream: mockStopStream,
        clearContent: mockClearContent,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      // Model should be displayed
      expect(screen.getByText(/gpt-4-turbo/)).toBeInTheDocument();
    });
  });

  describe("MCP Connection Integration", () => {
    const mockSession: Session = {
      id: "session-1",
      name: "Test Session",
      config: {
        modelProvider: "openai",
        modelName: "gpt-4",
        temperature: 0.7,
        maxTokens: 4096,
      },
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("should show connected status when MCP is connected via WebSocket", async () => {
      mockUseMCPConnection.mockReturnValue({
        isConnected: true,
        connectionMode: "websocket",
        tools: [],
        error: null,
        connect: mockConnect,
        disconnect: mockDisconnect,
        callTool: mockCallTool,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    it("should show disconnected status when MCP is not connected", async () => {
      mockUseMCPConnection.mockReturnValue({
        isConnected: false,
        connectionMode: "disconnected",
        tools: [],
        error: null,
        connect: mockConnect,
        disconnect: mockDisconnect,
        callTool: mockCallTool,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText("Disconnected")).toBeInTheDocument();
    });

    it("should show REST mode indicator when using REST fallback", async () => {
      mockUseMCPConnection.mockReturnValue({
        isConnected: true,
        connectionMode: "rest",
        tools: [],
        error: null,
        connect: mockConnect,
        disconnect: mockDisconnect,
        callTool: mockCallTool,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText("REST")).toBeInTheDocument();
    });

    it("should display tools from MCP connection", async () => {
      mockUseMCPConnection.mockReturnValue({
        isConnected: true,
        connectionMode: "websocket",
        tools: [
          { name: "calculator", description: "Perform math calculations" },
          { name: "web_search", description: "Search the web" },
        ],
        error: null,
        connect: mockConnect,
        disconnect: mockDisconnect,
        callTool: mockCallTool,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      // Tools are displayed in the ContextPanel
      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.getByText("web_search")).toBeInTheDocument();
    });

    it("should initialize MCP connection with autoConnect option", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      // Verify the hook was called with autoConnect: true
      expect(mockUseMCPConnection).toHaveBeenCalledWith(
        expect.objectContaining({ autoConnect: true }),
      );
    });

    it("should show connection error when MCP connection fails", async () => {
      mockUseMCPConnection.mockReturnValue({
        isConnected: false,
        connectionMode: "disconnected",
        tools: [],
        error: "Connection failed",
        connect: mockConnect,
        disconnect: mockDisconnect,
        callTool: mockCallTool,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText("Connection failed")).toBeInTheDocument();
    });
  });

  describe("Session Search and Pagination", () => {
    const multipleSessions: Session[] = [
      {
        id: "session-1",
        name: "First Session",
        createdAt: Date.now() - 100000,
        updatedAt: Date.now() - 100000,
        messages: [],
        messageCount: 5,
      },
      {
        id: "session-2",
        name: "Second Session",
        createdAt: Date.now() - 50000,
        updatedAt: Date.now() - 50000,
        messages: [],
        messageCount: 3,
      },
      {
        id: "session-3",
        name: "Third Session",
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [],
        messageCount: 0,
      },
    ];

    it("should render search input in SessionPanel", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: {
          sessions: multipleSessions,
          currentSession: multipleSessions[0],
        },
      });

      expect(
        screen.getByPlaceholderText("Search sessions..."),
      ).toBeInTheDocument();
    });

    it("should filter sessions when search query is entered", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: {
          sessions: multipleSessions,
          currentSession: multipleSessions[0],
        },
      });

      const searchInput = screen.getByPlaceholderText("Search sessions...");
      fireEvent.change(searchInput, { target: { value: "First" } });

      await waitFor(() => {
        // Only First Session should be in the session list
        // Note: 'First Session' appears twice - in list and header (as currentSession)
        expect(screen.getAllByText("First Session")).toHaveLength(2);
        // Second and Third should not be in the list at all
        expect(screen.queryByText("Second Session")).not.toBeInTheDocument();
        expect(screen.queryByText("Third Session")).not.toBeInTheDocument();
      });
    });

    it("should show status filter buttons", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: {
          sessions: multipleSessions,
          currentSession: multipleSessions[0],
        },
      });

      expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Active" }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Archived" }),
      ).toBeInTheDocument();
    });

    it("should show total session count", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: {
          sessions: multipleSessions,
          currentSession: multipleSessions[0],
          totalCount: 25,
        },
      });

      expect(screen.getByText(/of 25 sessions/)).toBeInTheDocument();
    });

    it("should show Load More button when more sessions available", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: {
          sessions: multipleSessions,
          currentSession: multipleSessions[0],
          hasMore: true,
        },
      });

      expect(screen.getByText("Load More")).toBeInTheDocument();
    });

    it("should dispatch fetchMoreSessions when Load More is clicked", async () => {
      // Mock fetch for fetchMoreSessions thunk
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [
              {
                id: "s3",
                name: "Session 3",
                createdAt: Date.now(),
                updatedAt: Date.now(),
                messageCount: 0,
              },
            ],
            total: 3,
            next_cursor: null,
          }),
      });
      global.fetch = mockFetch;

      await renderWithProviders(<ChatPage />, {
        sessionState: {
          sessions: multipleSessions,
          currentSession: multipleSessions[0],
          hasMore: true,
          cursor: "cursor123",
        },
      });

      fireEvent.click(screen.getByText("Load More"));

      // fetchMoreSessions should be dispatched and use the cursor
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
        const callUrl =
          mockFetch.mock.calls[mockFetch.mock.calls.length - 1][0];
        expect(callUrl).toContain("cursor=cursor123");
      });
    });

    it("should dispatch fetchSessions with search param after debounce", async () => {
      // Mock fetch for fetchSessions
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [],
            total: 0,
            next_cursor: null,
          }),
      });
      global.fetch = mockFetch;

      await renderWithProviders(<ChatPage />, {
        sessionState: {
          sessions: multipleSessions,
          currentSession: multipleSessions[0],
        },
      });

      // Clear initial fetch calls
      mockFetch.mockClear();

      // Type in search input
      const searchInput = screen.getByPlaceholderText("Search sessions...");
      fireEvent.change(searchInput, { target: { value: "test query" } });

      // Wait for debounce (300ms default) and API call
      await waitFor(
        () => {
          expect(mockFetch).toHaveBeenCalled();
          const callUrl =
            mockFetch.mock.calls[mockFetch.mock.calls.length - 1][0];
          expect(callUrl).toContain("search=test");
        },
        { timeout: 500 },
      );
    });

    it("should dispatch fetchSessions with status param when filter changes", async () => {
      // Mock fetch for fetchSessions
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [],
            total: 0,
            next_cursor: null,
          }),
      });
      global.fetch = mockFetch;

      await renderWithProviders(<ChatPage />, {
        sessionState: {
          sessions: multipleSessions,
          currentSession: multipleSessions[0],
        },
      });

      // Clear initial fetch calls
      mockFetch.mockClear();

      // Click status filter button
      const activeButton = screen.getByRole("button", { name: "Active" });
      fireEvent.click(activeButton);

      // Wait for API call with status param
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
        const callUrl =
          mockFetch.mock.calls[mockFetch.mock.calls.length - 1][0];
        expect(callUrl).toContain("status=active");
      });
    });

    it("should refetch with both search and status params", async () => {
      // Mock fetch for fetchSessions
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            items: [],
            total: 0,
            next_cursor: null,
          }),
      });
      global.fetch = mockFetch;

      await renderWithProviders(<ChatPage />, {
        sessionState: {
          sessions: multipleSessions,
          currentSession: multipleSessions[0],
        },
      });

      // Clear initial fetch calls
      mockFetch.mockClear();

      // Set search
      const searchInput = screen.getByPlaceholderText("Search sessions...");
      fireEvent.change(searchInput, { target: { value: "my search" } });

      // Wait for debounce
      await waitFor(
        () => {
          expect(mockFetch).toHaveBeenCalled();
        },
        { timeout: 500 },
      );

      mockFetch.mockClear();

      // Now click status filter
      const archivedButton = screen.getByRole("button", { name: "Archived" });
      fireEvent.click(archivedButton);

      // Should include both search and status
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
        const callUrl =
          mockFetch.mock.calls[mockFetch.mock.calls.length - 1][0];
        expect(callUrl).toContain("search=my");
        expect(callUrl).toContain("status=archived");
      });
    });
  });

  describe("Voice Input Integration", () => {
    const mockSession: Session = {
      id: "session-1",
      name: "Test Session",
      config: {
        modelProvider: "openai",
        modelName: "gpt-4",
        temperature: 0.7,
        maxTokens: 4096,
      },
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("should render mic button when voice input is supported", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByLabelText("Start voice input")).toBeInTheDocument();
    });

    it("should not render mic button when voice input is not supported", async () => {
      mockUseVoiceInput.mockReturnValue({
        isListening: false,
        isSupported: false,
        transcript: "",
        error: null,
        startListening: mockStartListening,
        stopListening: mockStopListening,
        clearTranscript: mockClearTranscript,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(
        screen.queryByLabelText("Start voice input"),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByLabelText("Stop voice input"),
      ).not.toBeInTheDocument();
    });

    it("should start listening when mic button is clicked", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      const micButton = screen.getByLabelText("Start voice input");
      fireEvent.click(micButton);

      expect(mockStartListening).toHaveBeenCalled();
    });

    it("should show stop button when listening", async () => {
      mockUseVoiceInput.mockReturnValue({
        isListening: true,
        isSupported: true,
        transcript: "",
        error: null,
        startListening: mockStartListening,
        stopListening: mockStopListening,
        clearTranscript: mockClearTranscript,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByLabelText("Stop voice input")).toBeInTheDocument();
    });

    it("should stop listening when stop button is clicked", async () => {
      mockUseVoiceInput.mockReturnValue({
        isListening: true,
        isSupported: true,
        transcript: "",
        error: null,
        startListening: mockStartListening,
        stopListening: mockStopListening,
        clearTranscript: mockClearTranscript,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      const stopButton = screen.getByLabelText("Stop voice input");
      fireEvent.click(stopButton);

      expect(mockStopListening).toHaveBeenCalled();
    });

    it("should show recording indicator when listening", async () => {
      mockUseVoiceInput.mockReturnValue({
        isListening: true,
        isSupported: true,
        transcript: "",
        error: null,
        startListening: mockStartListening,
        stopListening: mockStopListening,
        clearTranscript: mockClearTranscript,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      // Recording indicator should be visible (pulsing dot or similar)
      expect(screen.getByTestId("recording-indicator")).toBeInTheDocument();
    });

    it("should append transcript to input field", async () => {
      mockUseVoiceInput.mockReturnValue({
        isListening: false,
        isSupported: true,
        transcript: "Hello world",
        error: null,
        startListening: mockStartListening,
        stopListening: mockStopListening,
        clearTranscript: mockClearTranscript,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      const input = screen.getByPlaceholderText("Type your message...");
      expect(input).toHaveValue("Hello world");
    });

    it("should disable mic button while streaming", async () => {
      mockUseStreamingChat.mockReturnValue({
        isStreaming: true,
        streamingContent: "Generating...",
        error: null,
        startStream: mockStartStream,
        stopStream: mockStopStream,
        clearContent: mockClearContent,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      const micButton = screen.getByLabelText("Start voice input");
      expect(micButton).toBeDisabled();
    });

    it("should show voice error when voice input fails", async () => {
      mockUseVoiceInput.mockReturnValue({
        isListening: false,
        isSupported: true,
        transcript: "",
        error: "Microphone access denied",
        startListening: mockStartListening,
        stopListening: mockStopListening,
        clearTranscript: mockClearTranscript,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText("Microphone access denied")).toBeInTheDocument();
    });

    it("should clear transcript after message is sent", async () => {
      mockUseVoiceInput.mockReturnValue({
        isListening: false,
        isSupported: true,
        transcript: "Voice message",
        error: null,
        startListening: mockStartListening,
        stopListening: mockStopListening,
        clearTranscript: mockClearTranscript,
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      const form = screen
        .getByPlaceholderText("Type your message...")
        .closest("form")!;
      fireEvent.submit(form);

      await waitFor(() => {
        expect(mockClearTranscript).toHaveBeenCalled();
      });
    });
  });

  describe("File Upload Integration", () => {
    const mockSession: Session = {
      id: "session-1",
      name: "Test Session",
      config: {
        modelProvider: "openai",
        modelName: "gpt-4",
        temperature: 0.7,
        maxTokens: 4096,
      },
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("should render file attachment button", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByLabelText("Attach file")).toBeInTheDocument();
    });

    it("should show drop zone indicator when dragging file", async () => {
      mockUseFileUpload.mockReturnValue({
        files: [],
        isUploading: false,
        isDragging: true,
        progress: 0,
        error: null,
        selectFiles: mockSelectFiles,
        removeFile: mockRemoveFile,
        clearFiles: mockClearFilesUpload,
        uploadFiles: mockUploadFiles,
        cancelUpload: mockCancelUpload,
        dragHandlers: {
          onDragEnter: vi.fn(),
          onDragLeave: vi.fn(),
          onDragOver: vi.fn(),
          onDrop: vi.fn(),
        },
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByTestId("drop-zone-overlay")).toBeInTheDocument();
    });

    it("should display attached files in preview", async () => {
      mockUseFileUpload.mockReturnValue({
        files: [
          {
            id: "file-1",
            file: new File(["test"], "test.txt", { type: "text/plain" }),
            status: "pending" as const,
            progress: 0,
          },
        ],
        isUploading: false,
        isDragging: false,
        progress: 0,
        error: null,
        selectFiles: mockSelectFiles,
        removeFile: mockRemoveFile,
        clearFiles: mockClearFilesUpload,
        uploadFiles: mockUploadFiles,
        cancelUpload: mockCancelUpload,
        dragHandlers: {
          onDragEnter: vi.fn(),
          onDragLeave: vi.fn(),
          onDragOver: vi.fn(),
          onDrop: vi.fn(),
        },
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText("test.txt")).toBeInTheDocument();
    });

    it("should show remove button for each file", async () => {
      mockUseFileUpload.mockReturnValue({
        files: [
          {
            id: "file-1",
            file: new File(["test"], "doc.pdf", { type: "application/pdf" }),
            status: "pending" as const,
            progress: 0,
          },
        ],
        isUploading: false,
        isDragging: false,
        progress: 0,
        error: null,
        selectFiles: mockSelectFiles,
        removeFile: mockRemoveFile,
        clearFiles: mockClearFilesUpload,
        uploadFiles: mockUploadFiles,
        cancelUpload: mockCancelUpload,
        dragHandlers: {
          onDragEnter: vi.fn(),
          onDragLeave: vi.fn(),
          onDragOver: vi.fn(),
          onDrop: vi.fn(),
        },
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByLabelText("Remove file")).toBeInTheDocument();
    });

    it("should call removeFile when remove button is clicked", async () => {
      mockUseFileUpload.mockReturnValue({
        files: [
          {
            id: "file-1",
            file: new File(["test"], "doc.pdf", { type: "application/pdf" }),
            status: "pending" as const,
            progress: 0,
          },
        ],
        isUploading: false,
        isDragging: false,
        progress: 0,
        error: null,
        selectFiles: mockSelectFiles,
        removeFile: mockRemoveFile,
        clearFiles: mockClearFilesUpload,
        uploadFiles: mockUploadFiles,
        cancelUpload: mockCancelUpload,
        dragHandlers: {
          onDragEnter: vi.fn(),
          onDragLeave: vi.fn(),
          onDragOver: vi.fn(),
          onDrop: vi.fn(),
        },
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      fireEvent.click(screen.getByLabelText("Remove file"));

      expect(mockRemoveFile).toHaveBeenCalledWith("file-1");
    });

    it("should show upload progress", async () => {
      mockUseFileUpload.mockReturnValue({
        files: [
          {
            id: "file-1",
            file: new File(["test"], "large.zip", { type: "application/zip" }),
            status: "uploading" as const,
            progress: 65,
          },
        ],
        isUploading: true,
        isDragging: false,
        progress: 65,
        error: null,
        selectFiles: mockSelectFiles,
        removeFile: mockRemoveFile,
        clearFiles: mockClearFilesUpload,
        uploadFiles: mockUploadFiles,
        cancelUpload: mockCancelUpload,
        dragHandlers: {
          onDragEnter: vi.fn(),
          onDragLeave: vi.fn(),
          onDragOver: vi.fn(),
          onDrop: vi.fn(),
        },
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText("65%")).toBeInTheDocument();
    });

    it("should show file upload error", async () => {
      mockUseFileUpload.mockReturnValue({
        files: [
          {
            id: "file-1",
            file: new File(["test"], "huge.bin", {
              type: "application/octet-stream",
            }),
            status: "error" as const,
            progress: 0,
            error: "File size exceeds 10MB limit",
          },
        ],
        isUploading: false,
        isDragging: false,
        progress: 0,
        error: "File size exceeds 10MB limit",
        selectFiles: mockSelectFiles,
        removeFile: mockRemoveFile,
        clearFiles: mockClearFilesUpload,
        uploadFiles: mockUploadFiles,
        cancelUpload: mockCancelUpload,
        dragHandlers: {
          onDragEnter: vi.fn(),
          onDragLeave: vi.fn(),
          onDragOver: vi.fn(),
          onDrop: vi.fn(),
        },
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      // Error appears in both the error banner and the file preview
      expect(
        screen.getAllByText("File size exceeds 10MB limit").length,
      ).toBeGreaterThanOrEqual(1);
    });

    it("should clear files after message is sent", async () => {
      mockUseFileUpload.mockReturnValue({
        files: [
          {
            id: "file-1",
            file: new File(["test"], "test.txt", { type: "text/plain" }),
            status: "pending" as const,
            progress: 0,
          },
        ],
        isUploading: false,
        isDragging: false,
        progress: 0,
        error: null,
        selectFiles: mockSelectFiles,
        removeFile: mockRemoveFile,
        clearFiles: mockClearFilesUpload,
        uploadFiles: mockUploadFiles,
        cancelUpload: mockCancelUpload,
        dragHandlers: {
          onDragEnter: vi.fn(),
          onDragLeave: vi.fn(),
          onDragOver: vi.fn(),
          onDrop: vi.fn(),
        },
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      // Type a message
      const input = screen.getByPlaceholderText("Type your message...");
      fireEvent.change(input, { target: { value: "Test message" } });

      const form = input.closest("form")!;
      fireEvent.submit(form);

      await waitFor(() => {
        expect(mockClearFilesUpload).toHaveBeenCalled();
      });
    });

    it("should disable attachment button while uploading", async () => {
      mockUseFileUpload.mockReturnValue({
        files: [
          {
            id: "file-1",
            file: new File(["test"], "large.zip", { type: "application/zip" }),
            status: "uploading" as const,
            progress: 50,
          },
        ],
        isUploading: true,
        isDragging: false,
        progress: 50,
        error: null,
        selectFiles: mockSelectFiles,
        removeFile: mockRemoveFile,
        clearFiles: mockClearFilesUpload,
        uploadFiles: mockUploadFiles,
        cancelUpload: mockCancelUpload,
        dragHandlers: {
          onDragEnter: vi.fn(),
          onDragLeave: vi.fn(),
          onDragOver: vi.fn(),
          onDrop: vi.fn(),
        },
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByLabelText("Attach file")).toBeDisabled();
    });

    it("should call selectFiles when files are selected via file input", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      // Get the hidden file input
      const fileInput = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;
      expect(fileInput).toBeInTheDocument();

      // Create mock files
      const file1 = new File(["content1"], "file1.txt", { type: "text/plain" });
      const file2 = new File(["content2"], "file2.pdf", {
        type: "application/pdf",
      });

      // Simulate file selection via onChange
      Object.defineProperty(fileInput, "files", {
        value: [file1, file2],
        configurable: true,
      });
      fireEvent.change(fileInput);

      // Verify selectFiles was called with file array
      expect(mockSelectFiles).toHaveBeenCalledWith([file1, file2]);
    });

    it("should reset file input value after selection for same file re-selection", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      // Get the hidden file input
      const fileInput = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      // Create mock file
      const file = new File(["content"], "test.txt", { type: "text/plain" });

      // Spy on value setter to verify it's called with empty string
      const valueSetter = vi.fn();
      Object.defineProperty(fileInput, "value", {
        set: valueSetter,
        configurable: true,
      });

      // Simulate file selection
      Object.defineProperty(fileInput, "files", {
        value: [file],
        configurable: true,
      });
      fireEvent.change(fileInput);

      // After onChange, value should be reset to empty string
      expect(valueSetter).toHaveBeenCalledWith("");
    });

    it("should not call selectFiles when no files selected", async () => {
      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      // Get the hidden file input
      const fileInput = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      // Simulate change with null files (e.g., user cancels file picker)
      Object.defineProperty(fileInput, "files", {
        value: null,
        configurable: true,
      });
      fireEvent.change(fileInput);

      // selectFiles should not be called when files is null
      expect(mockSelectFiles).not.toHaveBeenCalled();
    });
  });

  describe("Mobile Responsive Layout", () => {
    it("should render mobile sessions toggle button", async () => {
      await renderWithProviders(<ChatPage />);
      expect(
        screen.getByRole("button", { name: /toggle sessions/i }),
      ).toBeInTheDocument();
    });

    it("should render mobile context toggle button", async () => {
      await renderWithProviders(<ChatPage />);
      expect(
        screen.getByRole("button", { name: /toggle context/i }),
      ).toBeInTheDocument();
    });

    it("should have mobile toggle buttons with proper accessibility", async () => {
      await renderWithProviders(<ChatPage />);
      const sessionsButton = screen.getByRole("button", {
        name: /toggle sessions/i,
      });
      const contextButton = screen.getByRole("button", {
        name: /toggle context/i,
      });

      expect(sessionsButton).toHaveAttribute("aria-label");
      expect(contextButton).toHaveAttribute("aria-label");
    });

    it("should have mobile-friendly layout classes", async () => {
      const { container } = await renderWithProviders(<ChatPage />);
      // Main container should use flex layout
      const mainContainer = container.querySelector(".flex");
      expect(mainContainer).toBeInTheDocument();
    });
  });

  describe("Background Sync / Offline Support", () => {
    const mockSession: Session = {
      id: "session-1",
      name: "Test Session",
      config: {
        modelProvider: "openai",
        modelName: "gpt-4",
        temperature: 0.7,
        maxTokens: 4096,
      },
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("should show pending messages count when offline", async () => {
      mockUseBackgroundSync.mockReturnValue({
        isSupported: true,
        isInitialized: true,
        isOnline: false,
        isSyncing: false,
        pendingCount: 2,
        lastError: null,
        queueRequest: vi.fn(),
        syncNow: vi.fn(),
        clearQueue: vi.fn(),
        getQueue: vi.fn(() => []),
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText(/2 pending/i)).toBeInTheDocument();
    });

    it("should show syncing indicator when syncing", async () => {
      mockUseBackgroundSync.mockReturnValue({
        isSupported: true,
        isInitialized: true,
        isOnline: true,
        isSyncing: true,
        pendingCount: 1,
        lastError: null,
        queueRequest: vi.fn(),
        syncNow: vi.fn(),
        clearQueue: vi.fn(),
        getQueue: vi.fn(() => []),
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.getByText(/syncing/i)).toBeInTheDocument();
    });

    it("should not show pending count when online with no pending", async () => {
      mockUseBackgroundSync.mockReturnValue({
        isSupported: true,
        isInitialized: true,
        isOnline: true,
        isSyncing: false,
        pendingCount: 0,
        lastError: null,
        queueRequest: vi.fn(),
        syncNow: vi.fn(),
        clearQueue: vi.fn(),
        getQueue: vi.fn(() => []),
      });

      await renderWithProviders(<ChatPage />, {
        sessionState: { currentSession: mockSession },
      });

      expect(screen.queryByText(/pending/i)).not.toBeInTheDocument();
    });
  });
});
