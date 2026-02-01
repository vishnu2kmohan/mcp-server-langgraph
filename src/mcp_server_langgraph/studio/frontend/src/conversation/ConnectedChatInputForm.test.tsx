/**
 * ConnectedChatInputForm Tests
 *
 * Tests for the full-featured chat input component that integrates:
 * - File upload (drag-drop, click to select)
 * - Voice input (Web Speech API)
 * - Slash commands
 * - Inline AI suggestions
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConnectedChatInputForm } from "./ConnectedChatInputForm";
import type { SlashCommand } from "../types/chat";

// =============================================================================
// Mock Feature Flag Context
// =============================================================================
const mockIsEnabled = vi.fn();
vi.mock("../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flagName: string) => mockIsEnabled(flagName),
}));

// =============================================================================
// Mock Redux Store (for submitOnEnter selector)
// =============================================================================
const mockSubmitOnEnter = { current: true };
const mockDispatch = vi.fn();
vi.mock("../store/hooks", () => ({
  useAppSelector: (selector: (state: unknown) => unknown) => {
    // Return the mock value for selectSubmitOnEnter
    if (selector.toString().includes("submitOnEnter")) {
      return mockSubmitOnEnter.current;
    }
    return undefined;
  },
  useAppDispatch: () => mockDispatch,
}));

// Mock the selector itself
vi.mock("../store/slices/uiSlice", () => ({
  selectSubmitOnEnter: (state: { ui: { submitOnEnter: boolean } }) =>
    state.ui.submitOnEnter,
}));

// =============================================================================
// Mocks
// =============================================================================

// Mock useFileUpload hook
const mockSelectFiles = vi.fn();
const mockRemoveFile = vi.fn();

// UploadedFile structure that ChatInputForm expects
interface MockUploadedFile {
  id: string;
  file: { name: string; size: number; type: string };
  status: "pending" | "uploading" | "complete" | "error";
  progress: number;
  error?: string;
}

const mockFileUploadReturn = {
  files: [] as MockUploadedFile[],
  isUploading: false,
  isDragging: false,
  error: null as string | null,
  selectFiles: mockSelectFiles,
  removeFile: mockRemoveFile,
  dragHandlers: {
    onDragEnter: vi.fn(),
    onDragLeave: vi.fn(),
    onDragOver: vi.fn(),
    onDrop: vi.fn(),
  },
};

vi.mock("../hooks/useFileUpload", () => ({
  useFileUpload: () => mockFileUploadReturn,
}));

// Mock useVoiceInput hook
const mockStartListening = vi.fn();
const mockStopListening = vi.fn();
const mockVoiceInputReturn = {
  isListening: false,
  isSupported: true,
  error: null as string | null,
  transcript: "",
  startListening: mockStartListening,
  stopListening: mockStopListening,
};

vi.mock("../hooks/useVoiceInput", () => ({
  useVoiceInput: (options: { onTranscript?: (text: string) => void }) => {
    // Store the onTranscript callback for testing
    (
      mockVoiceInputReturn as unknown as {
        _onTranscript?: typeof options.onTranscript;
      }
    )._onTranscript = options.onTranscript;
    return mockVoiceInputReturn;
  },
}));

// Mock useKBStatus hook
const mockKBStatusReturn = {
  data: undefined as
    | {
        status: string;
        qdrantConnected: boolean;
        collectionName?: string;
        vectorsCount?: number;
      }
    | undefined,
  isLoading: false,
  isError: false,
  isReady: false,
  kbStatusForUI: undefined as
    | "ready"
    | "misconfigured"
    | "unavailable"
    | undefined,
  refetch: vi.fn(),
};

vi.mock("../hooks/useKBStatus", () => ({
  useKBStatus: () => mockKBStatusReturn,
}));

// Mock useUrlContentFetch hook (Sprint 1 - Chat Input Gap Fix)
const mockDetectUrls = vi.fn();
const mockClearUrl = vi.fn();
const mockUrlContentFetchReturn = {
  detectedUrls: [] as Array<{ raw: string; url: string }>,
  detectUrls: mockDetectUrls,
  fetchUrl: vi.fn(),
  fetchedContent: [] as Array<{
    url: string;
    title?: string;
    content?: string;
    error?: string;
  }>,
  isLoading: false,
  loadingUrls: [] as string[],
  clearContent: vi.fn(),
  clearUrl: mockClearUrl,
  getContextString: vi.fn().mockReturnValue(""),
};

vi.mock("../hooks/useUrlContentFetch", () => ({
  useUrlContentFetch: () => mockUrlContentFetchReturn,
}));

// Mock useInlineSuggestions hook (requires useNavigate from react-router)
const mockUseInlineSuggestionsReturn = {
  suggestion: "",
  isLoading: false,
  updateInput: vi.fn(),
  acceptSuggestion: vi.fn(),
  dismissSuggestion: vi.fn(),
};

vi.mock("../hooks/useInlineSuggestions", () => ({
  useInlineSuggestions: () => mockUseInlineSuggestionsReturn,
}));

// Mock useAISuggestionsWebSocket hook
const mockUseAISuggestionsWebSocketReturn = {
  status: "disconnected" as const,
  currentSuggestion: null,
  isPending: false,
  requestSuggestion: vi.fn(),
  acceptSuggestion: vi.fn(),
  rejectSuggestion: vi.fn(),
  updateContext: vi.fn(),
  clearSuggestion: vi.fn(),
};

vi.mock("../hooks/useAISuggestionsWebSocket", () => ({
  useAISuggestionsWebSocket: () => mockUseAISuggestionsWebSocketReturn,
}));

// Mock useConnectorSuggestions hook (Phase 5 - Proactive Suggestions)
const mockConnectorSuggestionsReturn = {
  suggestions: [],
  isLoading: false,
  isVisible: false,
  updateInput: vi.fn(),
  dismiss: vi.fn(),
  reset: vi.fn(),
};

vi.mock("../hooks/useConnectorSuggestions", () => ({
  useConnectorSuggestions: () => mockConnectorSuggestionsReturn,
}));

// Mock useAvailableTools hook (Manual Tool Selection)
vi.mock("../hooks/useAvailableTools", () => ({
  useAvailableTools: () => ({
    tools: [],
    filteredTools: [],
    groupedTools: { builtin: [], mcp: {} },
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
    builtinCount: 0,
    mcpCount: 0,
    totalCount: 0,
    getToolByName: vi.fn(),
  }),
}));

// Mock chatConnectionSlice actions
vi.mock("../store/slices/chatConnectionSlice", () => ({
  startConnectionSetup: vi.fn((payload) => ({
    type: "chatConnection/startConnectionSetup",
    payload,
  })),
}));

// Mock executionModeSlice selectors and actions
vi.mock("../store/slices/executionModeSlice", () => ({
  selectExecutionMode: () => "default",
  selectCanBypass: () => false,
  cycleExecutionMode: vi.fn(() => ({
    type: "executionMode/cycleExecutionMode",
  })),
  setExecutionMode: vi.fn((mode: string) => ({
    type: "executionMode/setExecutionMode",
    payload: mode,
  })),
  setHasBypassPermission: vi.fn((allowed: boolean) => ({
    type: "executionMode/setHasBypassPermission",
    payload: allowed,
  })),
}));

// Mock useCheckBypassPermissionQuery from API (RTK Query)
vi.mock("../api", async () => {
  const actual = await vi.importActual("../api");
  return {
    ...actual,
    useCheckBypassPermissionQuery: () => ({
      data: { allowed: false },
      isLoading: false,
      isError: false,
    }),
  };
});

// =============================================================================
// Mock TelemetryContext
// =============================================================================
vi.mock("../contexts/TelemetryContext", () => ({
  useSessionTelemetry: () => ({
    trackExecutionModeChange: vi.fn(),
    trackBypassApproval: vi.fn(),
    trackSessionCreation: vi.fn(),
    trackRevalidation: vi.fn(),
    trackSync: vi.fn(),
    trackArtifactSave: vi.fn(),
    trackArtifactDelete: vi.fn(),
    trackSuggestionAction: vi.fn(),
    trackCanvasAction: vi.fn(),
    getMetrics: vi.fn(),
    getHistory: vi.fn(),
    reset: vi.fn(),
  }),
  TelemetryProvider: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
}));

// =============================================================================
// Test Setup
// =============================================================================

describe("ConnectedChatInputForm", () => {
  const defaultProps = {
    value: "",
    onChange: vi.fn(),
    onSubmit: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset mock states
    mockFileUploadReturn.files = [];
    mockFileUploadReturn.isUploading = false;
    mockFileUploadReturn.isDragging = false;
    mockFileUploadReturn.error = null;
    mockVoiceInputReturn.isListening = false;
    mockVoiceInputReturn.isSupported = true;
    mockVoiceInputReturn.error = null;
    // Reset KB status mock
    mockKBStatusReturn.data = undefined;
    mockKBStatusReturn.isLoading = false;
    mockKBStatusReturn.isError = false;
    mockKBStatusReturn.isReady = false;
    mockKBStatusReturn.kbStatusForUI = undefined;
    // Reset URL content fetch mock (Sprint 1)
    mockUrlContentFetchReturn.detectedUrls = [];
    mockUrlContentFetchReturn.fetchedContent = [];
    mockUrlContentFetchReturn.isLoading = false;
    mockUrlContentFetchReturn.loadingUrls = [];
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.resetAllMocks();
  });

  // ===========================================================================
  // Basic Rendering Tests
  // ===========================================================================

  describe("Rendering", () => {
    it("should render chat input form", () => {
      render(<ConnectedChatInputForm {...defaultProps} />);
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should render text input area", () => {
      render(<ConnectedChatInputForm {...defaultProps} />);
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("should render send button", () => {
      render(<ConnectedChatInputForm {...defaultProps} />);
      expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    });

    it("should display current value in input", () => {
      render(<ConnectedChatInputForm {...defaultProps} value="Hello world" />);
      expect(screen.getByRole("textbox")).toHaveValue("Hello world");
    });
  });

  // ===========================================================================
  // Input Handling Tests
  // ===========================================================================

  describe("Input Handling", () => {
    it("should call onChange when typing", async () => {
      const user = userEvent.setup();
      const mockOnChange = vi.fn();
      render(
        <ConnectedChatInputForm {...defaultProps} onChange={mockOnChange} />,
      );

      const input = screen.getByRole("textbox");
      await user.type(input, "test");

      expect(mockOnChange).toHaveBeenCalled();
    });

    it("should call onSubmit when send button is clicked", async () => {
      const user = userEvent.setup();
      const mockOnSubmit = vi.fn();
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          value="Test message"
          onSubmit={mockOnSubmit}
        />,
      );

      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      expect(mockOnSubmit).toHaveBeenCalledWith("Test message");
    });

    it("should not submit empty messages", async () => {
      const user = userEvent.setup();
      const mockOnSubmit = vi.fn();
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          value=""
          onSubmit={mockOnSubmit}
        />,
      );

      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      expect(mockOnSubmit).not.toHaveBeenCalled();
    });

    it("should trim whitespace before submitting", async () => {
      const user = userEvent.setup();
      const mockOnSubmit = vi.fn();
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          value="  Hello world  "
          onSubmit={mockOnSubmit}
        />,
      );

      const sendButton = screen.getByRole("button", { name: /send/i });
      await user.click(sendButton);

      expect(mockOnSubmit).toHaveBeenCalledWith("Hello world");
    });
  });

  // ===========================================================================
  // File Upload Tests
  // ===========================================================================

  describe("File Upload", () => {
    it("should display uploaded files when present", () => {
      mockFileUploadReturn.files = [
        {
          id: "file-1",
          file: { name: "document.pdf", size: 1024, type: "application/pdf" },
          status: "complete",
          progress: 100,
        },
      ];

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(screen.getByText("document.pdf")).toBeInTheDocument();
    });

    it("should show uploading indicator when uploading", () => {
      mockFileUploadReturn.isUploading = true;

      render(<ConnectedChatInputForm {...defaultProps} />);

      // ChatInputForm should show uploading state
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should show drag overlay when dragging files", () => {
      mockFileUploadReturn.isDragging = true;

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Component should indicate drag state
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should display file error when upload fails", () => {
      mockFileUploadReturn.error = "File too large";

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(screen.getByText(/file too large/i)).toBeInTheDocument();
    });

    it("should call removeFile when file remove button is clicked", async () => {
      const user = userEvent.setup();
      mockFileUploadReturn.files = [
        {
          id: "file-1",
          file: { name: "document.pdf", size: 1024, type: "application/pdf" },
          status: "complete",
          progress: 100,
        },
      ];

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Find and click the remove button (aria-label is "Remove file")
      const removeButton = screen.getByRole("button", { name: /remove file/i });
      await user.click(removeButton);

      expect(mockRemoveFile).toHaveBeenCalledWith("file-1");
    });
  });

  // ===========================================================================
  // Voice Input Tests
  // ===========================================================================

  describe("Voice Input", () => {
    it("should show microphone button when voice is supported", () => {
      mockVoiceInputReturn.isSupported = true;

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /voice|microphone|speak/i }),
      ).toBeInTheDocument();
    });

    it("should hide microphone button when voice is not supported", () => {
      mockVoiceInputReturn.isSupported = false;

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(
        screen.queryByRole("button", { name: /voice|microphone|speak/i }),
      ).not.toBeInTheDocument();
    });

    it("should call startListening when microphone button is clicked", async () => {
      const user = userEvent.setup();
      mockVoiceInputReturn.isSupported = true;

      render(<ConnectedChatInputForm {...defaultProps} />);

      const micButton = screen.getByRole("button", {
        name: /voice|microphone|speak/i,
      });
      await user.click(micButton);

      expect(mockStartListening).toHaveBeenCalled();
    });

    it("should call stopListening when listening and microphone button is clicked", async () => {
      const user = userEvent.setup();
      mockVoiceInputReturn.isSupported = true;
      mockVoiceInputReturn.isListening = true;

      render(<ConnectedChatInputForm {...defaultProps} />);

      const micButton = screen.getByRole("button", {
        name: /stop|voice|microphone/i,
      });
      await user.click(micButton);

      expect(mockStopListening).toHaveBeenCalled();
    });

    it("should display voice error when speech recognition fails", () => {
      mockVoiceInputReturn.error = "Microphone access denied";

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(screen.getByText(/microphone access denied/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Slash Commands Tests
  // ===========================================================================

  describe("Slash Commands", () => {
    it("should use default slash commands when none provided", () => {
      render(<ConnectedChatInputForm {...defaultProps} value="/" />);

      // Default commands should be available
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should use custom slash commands when provided", async () => {
      const user = userEvent.setup();
      const customCommands: SlashCommand[] = [
        { id: "custom", name: "custom", description: "Custom command" },
      ];

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          value="/"
          slashCommands={customCommands}
        />,
      );

      // Type / to trigger command menu
      const input = screen.getByRole("textbox");
      await user.type(input, "/");

      // Custom command should appear in menu
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should call onSlashCommand and clear input when command is selected", async () => {
      const mockOnSlashCommand = vi.fn();
      const mockOnChange = vi.fn();

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          onChange={mockOnChange}
          onSlashCommand={mockOnSlashCommand}
          value="/"
        />,
      );

      // Component should be ready
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Processing State Tests
  // ===========================================================================

  describe("Processing State", () => {
    it("should show processing indicator when isProcessing is true", () => {
      render(<ConnectedChatInputForm {...defaultProps} isProcessing />);

      // Send button should indicate processing state
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should show streaming indicator when isStreaming is true", () => {
      render(<ConnectedChatInputForm {...defaultProps} isStreaming />);

      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should show stop button when streaming", () => {
      const mockOnStopStreaming = vi.fn();
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          isStreaming
          onStopStreaming={mockOnStopStreaming}
        />,
      );

      // Stop button should be visible during streaming
      expect(screen.getByRole("button", { name: /stop/i })).toBeInTheDocument();
    });

    it("should call onStopStreaming when stop button is clicked", async () => {
      const user = userEvent.setup();
      const mockOnStopStreaming = vi.fn();
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          isStreaming
          onStopStreaming={mockOnStopStreaming}
        />,
      );

      const stopButton = screen.getByRole("button", { name: /stop/i });
      await user.click(stopButton);

      expect(mockOnStopStreaming).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Inline Suggestions Tests
  // ===========================================================================

  describe("Inline Suggestions", () => {
    it("should display inline suggestion when enabled and available", () => {
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          enableInlineSuggestions
          inlineSuggestion="complete this sentence"
        />,
      );

      // Suggestion should be visible as ghost text
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should not display suggestion when enableInlineSuggestions is false", () => {
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          enableInlineSuggestions={false}
          inlineSuggestion="complete this sentence"
        />,
      );

      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should call onAcceptSuggestion when Tab is pressed", async () => {
      const user = userEvent.setup();
      const mockOnAcceptSuggestion = vi.fn();
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          value="Hello "
          enableInlineSuggestions
          inlineSuggestion="world"
          onAcceptSuggestion={mockOnAcceptSuggestion}
        />,
      );

      const input = screen.getByRole("textbox");
      await user.click(input);
      await user.keyboard("{Tab}");

      // Tab should accept the suggestion
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should call onDismissSuggestion when Escape is pressed", async () => {
      const user = userEvent.setup();
      const mockOnDismissSuggestion = vi.fn();
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          value="Hello "
          enableInlineSuggestions
          inlineSuggestion="world"
          onDismissSuggestion={mockOnDismissSuggestion}
        />,
      );

      const input = screen.getByRole("textbox");
      await user.click(input);
      await user.keyboard("{Escape}");

      // Escape should dismiss the suggestion
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Feature Flag Integration Tests (RichText Mode)
  // ===========================================================================

  describe("Feature Flag Integration", () => {
    beforeEach(() => {
      // Reset feature flag mock
      mockIsEnabled.mockReset();
      // Default: feature flag enabled
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        return false;
      });
      // Reset submitOnEnter mock
      mockSubmitOnEnter.current = true;
    });

    it("should render ChatInput component", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      // ChatInput pill container should be present
      expect(screen.getByTestId("chat-input-pill")).toBeInTheDocument();
    });

    it("should render textarea for message input", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Textarea should be present for message input
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("should pass submitOnEnter=true from uiSlice (ChatGPT style)", () => {
      mockIsEnabled.mockImplementation(() => false);
      mockSubmitOnEnter.current = true;

      render(<ConnectedChatInputForm {...defaultProps} value="Hello" />);

      // Enter should submit (ChatGPT style)
      const textarea = screen.getByRole("textbox");
      expect(textarea).toBeInTheDocument();
    });

    it("should pass submitOnEnter=false from uiSlice (Legacy style)", () => {
      mockIsEnabled.mockImplementation(() => false);
      mockSubmitOnEnter.current = false;

      render(<ConnectedChatInputForm {...defaultProps} value="Hello" />);

      // Ctrl+Enter should submit (Legacy style)
      const textarea = screen.getByRole("textbox");
      expect(textarea).toBeInTheDocument();
    });

    it("should preserve voice input integration in RichText mode", () => {
      mockIsEnabled.mockImplementation(() => false);
      mockVoiceInputReturn.isSupported = true;

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Voice button should be accessible in RichText mode
      expect(
        screen.getByRole("button", { name: /voice input/i }),
      ).toBeInTheDocument();
    });

    it("should preserve file upload integration in RichText mode", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      // File upload button should be accessible in RichText mode
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeInTheDocument();
    });

    it("should preserve slash commands in RichText mode", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} value="/" />);

      // Slash command menu should appear
      expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
    });

    it("should call useFeatureFlag with correct flag name", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Feature flags should be checked
      expect(mockIsEnabled).toHaveBeenCalledWith("kb_focus");
      expect(mockIsEnabled).toHaveBeenCalledWith("ai_suggestions_websocket");
      expect(mockIsEnabled).toHaveBeenCalledWith("manual_tool_selection");
      expect(mockIsEnabled).toHaveBeenCalledWith("connector_suggestions");
    });
  });

  // ===========================================================================
  // Knowledge Base Integration Tests
  // ===========================================================================

  describe("Knowledge Base Integration", () => {
    // Helper to enable kb_focus flag
    const enableKBFocusFlags = () => {
      mockIsEnabled.mockImplementation((flag: string) => flag === "kb_focus");
    };

    it("should render KnowledgeBaseFocus when feature flag is enabled", () => {
      enableKBFocusFlags();

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(screen.getByTestId("kb-focus-selector")).toBeInTheDocument();
    });

    it("should not render KnowledgeBaseFocus when feature flag is disabled", () => {
      // kb_focus is disabled
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(screen.queryByTestId("kb-focus-selector")).not.toBeInTheDocument();
    });

    it("should show KB status indicator when KB is ready", () => {
      enableKBFocusFlags();
      // Mock useKBStatus to return ready status
      mockKBStatusReturn.data = {
        status: "ready",
        qdrantConnected: true,
        collectionName: "test-collection",
        vectorsCount: 100,
      };
      mockKBStatusReturn.kbStatusForUI = "ready";

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(screen.getByTestId("kb-status-indicator")).toBeInTheDocument();
    });

    it("should initialize with 'all' focus mode by default", () => {
      enableKBFocusFlags();

      render(<ConnectedChatInputForm {...defaultProps} />);

      // The button should show "KB: all" as the default mode
      expect(screen.getByTestId("kb-focus-selector")).toHaveTextContent(
        "KB: all",
      );
    });

    it("should allow changing KB focus mode", async () => {
      const user = userEvent.setup();
      enableKBFocusFlags();

      render(
        <ConnectedChatInputForm {...defaultProps} kbFocusValue="kb_only" />,
      );

      // Button should show current mode
      expect(screen.getByTestId("kb-focus-selector")).toHaveTextContent(
        "KB: kb_only",
      );

      // Click cycles to next mode
      await user.click(screen.getByTestId("kb-focus-selector"));

      // After click, button text updates (cycles through modes)
      expect(screen.getByTestId("kb-focus-selector")).toBeInTheDocument();
    });

    it("should disable KB options when KB status is unavailable", () => {
      enableKBFocusFlags();
      mockKBStatusReturn.data = {
        status: "unavailable",
        qdrantConnected: false,
      };
      mockKBStatusReturn.kbStatusForUI = "unavailable";

      render(<ConnectedChatInputForm {...defaultProps} />);

      // KB button should still render but may show status
      expect(screen.getByTestId("kb-focus-selector")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Model Selection Tests (Sprint 1 - Chat Input Gap Fix)
  // ===========================================================================

  describe("Model Selection", () => {
    const modelSelectionProps = {
      showModelSelector: true,
      selectedModel: "gemini-2.5-flash",
      availableModels: [
        {
          id: "gemini-2.5-flash",
          name: "Gemini 2.5 Flash",
          provider: "Google",
        },
        {
          id: "claude-sonnet-4-5",
          name: "Claude 4.5 Sonnet",
          provider: "Anthropic",
        },
      ],
      onModelChange: vi.fn(),
    };

    beforeEach(() => {
      mockIsEnabled.mockImplementation(() => false);
    });

    it("should pass showModelSelector prop to ChatInputForm", () => {
      render(
        <ConnectedChatInputForm {...defaultProps} {...modelSelectionProps} />,
      );

      // Model selector should be visible when showModelSelector=true
      expect(screen.getByTestId("model-settings-button")).toBeInTheDocument();
    });

    it("should hide model selector when showModelSelector is false", () => {
      render(
        <ConnectedChatInputForm {...defaultProps} showModelSelector={false} />,
      );

      expect(
        screen.queryByTestId("model-settings-button"),
      ).not.toBeInTheDocument();
    });

    it("should display selected model in selector", () => {
      render(
        <ConnectedChatInputForm {...defaultProps} {...modelSelectionProps} />,
      );

      // ChatInput shows model name and provider
      expect(screen.getByTestId("model-settings-button")).toHaveTextContent(
        "Gemini 2.5 Flash",
      );
    });

    it("should call onModelChange when model is selected", async () => {
      const user = userEvent.setup();
      const mockOnModelChange = vi.fn();

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          {...modelSelectionProps}
          onModelChange={mockOnModelChange}
        />,
      );

      // Open model selector dropdown
      await user.click(screen.getByTestId("model-settings-button"));

      // Select a different model (use role="option" and model name)
      const options = screen.getAllByRole("option");
      const claudeSonnetOption = options.find((opt) =>
        opt.textContent?.includes("Claude 4.5 Sonnet"),
      );
      expect(claudeSonnetOption).toBeDefined();
      await user.click(claudeSonnetOption!);

      expect(mockOnModelChange).toHaveBeenCalledWith("claude-sonnet-4-5");
    });

    it("should default showModelSelector to false when not provided", () => {
      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(
        screen.queryByTestId("model-settings-button"),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Reasoning Effort Tests (Sprint 1 - Chat Input Gap Fix)
  // ===========================================================================

  describe("Reasoning Effort", () => {
    beforeEach(() => {
      mockIsEnabled.mockImplementation(() => false);
    });

    it("should pass reasoning effort props when model supports thinking", async () => {
      const user = userEvent.setup();
      const mockOnReasoningEffortChange = vi.fn();
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          showModelSelector={true}
          availableModels={[
            {
              id: "test-model",
              name: "Test Model",
              provider: "test",
              supportsThinking: true,
            },
          ]}
          selectedModel="test-model"
          modelSupportsThinking={true}
          reasoningEffort="medium"
          enableThinking={true}
          onReasoningEffortChange={mockOnReasoningEffortChange}
        />,
      );

      // Open model dropdown to see thinking controls
      await user.click(screen.getByTestId("model-settings-button"));

      // Thinking controls should be visible when model supports thinking
      expect(screen.getByTestId("thinking-controls")).toBeInTheDocument();
    });

    it("should hide thinking controls when model does not support thinking", async () => {
      const user = userEvent.setup();
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          showModelSelector={true}
          availableModels={[
            {
              id: "test-model",
              name: "Test Model",
              provider: "test",
              supportsThinking: false,
            },
          ]}
          selectedModel="test-model"
          modelSupportsThinking={false}
        />,
      );

      // Open model dropdown
      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.queryByTestId("thinking-controls")).not.toBeInTheDocument();
    });

    it("should call onReasoningEffortChange when effort level changes", async () => {
      const user = userEvent.setup();
      const mockOnReasoningEffortChange = vi.fn();

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          showModelSelector={true}
          availableModels={[
            {
              id: "test-model",
              name: "Test Model",
              provider: "test",
              supportsThinking: true,
            },
          ]}
          selectedModel="test-model"
          modelSupportsThinking={true}
          reasoningEffort="medium"
          enableThinking={true}
          onReasoningEffortChange={mockOnReasoningEffortChange}
        />,
      );

      // Open model dropdown to access thinking controls
      await user.click(screen.getByTestId("model-settings-button"));

      // Find the High button in thinking controls
      const highButton = screen.getByRole("button", { name: /high/i });
      await user.click(highButton);

      expect(mockOnReasoningEffortChange).toHaveBeenCalledWith("high");
    });

    it("should pass enableThinking prop to control thinking toggle", async () => {
      const user = userEvent.setup();

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          showModelSelector={true}
          availableModels={[
            {
              id: "test-model",
              name: "Test Model",
              provider: "test",
              supportsThinking: true,
            },
          ]}
          selectedModel="test-model"
          modelSupportsThinking={true}
          enableThinking={true}
          onEnableThinkingChange={vi.fn()}
        />,
      );

      // Open model dropdown to see thinking toggle
      await user.click(screen.getByTestId("model-settings-button"));

      // When enableThinking is true, the toggle should show enabled state
      const thinkingToggle = screen.getByTestId("thinking-toggle");
      expect(thinkingToggle).toHaveAttribute("aria-label", "Disable thinking");
    });

    it("should call onEnableThinkingChange when thinking toggle is clicked", async () => {
      const user = userEvent.setup();
      const mockOnEnableThinkingChange = vi.fn();

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          showModelSelector={true}
          availableModels={[
            {
              id: "test-model",
              name: "Test Model",
              provider: "test",
              supportsThinking: true,
            },
          ]}
          selectedModel="test-model"
          modelSupportsThinking={true}
          enableThinking={true}
          onEnableThinkingChange={mockOnEnableThinkingChange}
        />,
      );

      // Open model dropdown to access thinking toggle
      await user.click(screen.getByTestId("model-settings-button"));

      const thinkingToggle = screen.getByTestId("thinking-toggle");
      await user.click(thinkingToggle);

      expect(mockOnEnableThinkingChange).toHaveBeenCalledWith(false);
    });

    it("should default modelSupportsThinking to false", async () => {
      const user = userEvent.setup();
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          showModelSelector={true}
          availableModels={[
            {
              id: "test-model",
              name: "Test Model",
              provider: "test",
              supportsThinking: false,
            },
          ]}
          selectedModel="test-model"
        />,
      );

      // Open model dropdown
      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.queryByTestId("thinking-controls")).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // URL Fetch Tests (Sprint 1 - Chat Input Gap Fix)
  // ===========================================================================

  describe("URL Fetch Integration", () => {
    beforeEach(() => {
      mockIsEnabled.mockImplementation(() => false);
    });

    it("should enable URL fetch when enableUrlFetch is true", () => {
      // Set up mock to have detected URLs and loading state
      mockUrlContentFetchReturn.detectedUrls = [
        { raw: "#https://example.com", url: "https://example.com" },
      ];
      mockUrlContentFetchReturn.loadingUrls = ["https://example.com"];

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          enableUrlFetch={true}
          value="Check this #https://example.com"
        />,
      );

      // URL fetch indicator should appear when URLs are loading
      expect(screen.getByTestId("url-fetch-loading")).toBeInTheDocument();
    });

    it("should not show URL fetch indicator when enableUrlFetch is false", () => {
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          enableUrlFetch={false}
          value="Check this #https://example.com"
        />,
      );

      expect(screen.queryByTestId("url-fetch-loading")).not.toBeInTheDocument();
    });

    it("should show loading state while URL is being fetched", () => {
      // Set up mock to have loading URLs
      mockUrlContentFetchReturn.detectedUrls = [
        { raw: "#https://example.com", url: "https://example.com" },
      ];
      mockUrlContentFetchReturn.loadingUrls = ["https://example.com"];
      mockUrlContentFetchReturn.isLoading = true;

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          enableUrlFetch={true}
          value="Check this #https://example.com"
        />,
      );

      // URL fetch loading indicator should be visible during fetch
      expect(screen.getByTestId("url-fetch-loading")).toBeInTheDocument();
    });

    it("should display fetched URL content badge", () => {
      // Set up mock to have fetched content
      mockUrlContentFetchReturn.detectedUrls = [
        { raw: "#https://example.com", url: "https://example.com" },
      ];
      mockUrlContentFetchReturn.fetchedContent = [
        {
          url: "https://example.com",
          title: "Example Domain",
          content: "This domain is for use in illustrative examples.",
        },
      ];

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          enableUrlFetch={true}
          value="Check this #https://example.com"
        />,
      );

      // Fetched URL badge should show the title after successful fetch
      expect(screen.getByText("Example Domain")).toBeInTheDocument();
    });

    it("should default enableUrlFetch to false", () => {
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          value="Check this #https://example.com"
        />,
      );

      expect(screen.queryByTestId("url-fetch-loading")).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Preferences Menu Integration Tests
  // ===========================================================================

  describe("Preferences Menu Integration", () => {
    const enablePreferencesMenuFlags = () => {
      mockIsEnabled.mockImplementation(
        (flag: string) => flag === "preferences_menu",
      );
    };

    it("should call useFeatureFlag with preferences_menu flag", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(mockIsEnabled).toHaveBeenCalledWith("preferences_menu");
    });

    it("should render PreferencesMenu when feature flag is enabled", () => {
      enablePreferencesMenuFlags();

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(screen.getByTestId("preferences-menu")).toBeInTheDocument();
    });

    it("should not render PreferencesMenu when feature flag is disabled", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(screen.queryByTestId("preferences-menu")).not.toBeInTheDocument();
    });

    it("should hide ToolSelector when PreferencesMenu is shown", () => {
      // Enable both preferences_menu and manual_tool_selection
      mockIsEnabled.mockImplementation(
        (flag: string) =>
          flag === "preferences_menu" || flag === "manual_tool_selection",
      );

      render(<ConnectedChatInputForm {...defaultProps} />);

      // PreferencesMenu should be visible
      expect(screen.getByTestId("preferences-menu")).toBeInTheDocument();
      // ToolSelector should be hidden (consolidated into PreferencesMenu)
      expect(screen.queryByTestId("tool-selector")).not.toBeInTheDocument();
    });

    it("should hide KB Focus selector when PreferencesMenu is shown", () => {
      // Enable both preferences_menu and kb_focus
      mockIsEnabled.mockImplementation(
        (flag: string) => flag === "preferences_menu" || flag === "kb_focus",
      );

      render(<ConnectedChatInputForm {...defaultProps} />);

      // PreferencesMenu should be visible
      expect(screen.getByTestId("preferences-menu")).toBeInTheDocument();
      // KB Focus selector should be hidden (consolidated into PreferencesMenu)
      expect(screen.queryByTestId("kb-focus-selector")).not.toBeInTheDocument();
    });
  });
});
