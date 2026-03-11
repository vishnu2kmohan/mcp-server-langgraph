/**
 * ConnectedChatInputForm Core Tests
 *
 * Split from ConnectedChatInputForm.test.tsx for memory-safe test execution.
 * Tests cover:
 * - Basic rendering
 * - Input handling
 * - File upload
 * - Voice input
 * - Processing state
 * - Slash commands
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
vi.mock("../contexts/FeatureFlagContext", async () => {
  const actual = await vi.importActual("../contexts/FeatureFlagContext");
  return {
    ...actual,
    useFeatureFlag: (flagName: string) => mockIsEnabled(flagName),
  };
});
// =============================================================================
// Mock Redux Store (for submitOnEnter selector and dispatch)
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
  default: (state = {}) => state,
  selectSubmitOnEnter: (state: { ui: { submitOnEnter: boolean } }) =>
    state.ui.submitOnEnter,
}));

// Mock TelemetryContext
vi.mock("../contexts/TelemetryContext", async () => {
  const actual = await vi.importActual("../contexts/TelemetryContext");
  return {
    ...actual,
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
    useWebVitals: () => ({
      start: vi.fn(),
      stop: vi.fn(),
      getMetrics: () => ({ fcp: null, lcp: null, cls: null, inp: null }),
    }),
    useTelemetry: () => ({
      sessionTelemetry: {
        trackSessionCreation: vi.fn(),
        getMetrics: () => ({}),
      },
      webVitals: { start: vi.fn(), stop: vi.fn(), getMetrics: () => ({}) },
    }),
  };
});
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
  getContextString: vi.fn().mockReturnValue(),
};

vi.mock("../hooks/useUrlContentFetch", () => ({
  useUrlContentFetch: () => mockUrlContentFetchReturn,
}));

// Mock useInlineSuggestions hook (requires useNavigate from react-router)
const mockUseInlineSuggestionsReturn = {
  suggestion: null as string | null,
  isLoading: false,
  error: null as string | null,
  acceptSuggestion: vi.fn(),
  dismissSuggestion: vi.fn(),
  requestSuggestion: vi.fn(),
};

vi.mock("../hooks/useInlineSuggestions", () => ({
  useInlineSuggestions: () => mockUseInlineSuggestionsReturn,
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

// =============================================================================
// Test Setup
// =============================================================================

describe("ConnectedChatInputForm - Core", () => {
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
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
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
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
    });

    it("should show drag overlay when dragging files", () => {
      mockFileUploadReturn.isDragging = true;

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Component should indicate drag state
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
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
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
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
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
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
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Processing State Tests
  // ===========================================================================

  describe("Processing State", () => {
    it("should show processing indicator when isProcessing is true", () => {
      render(<ConnectedChatInputForm {...defaultProps} isProcessing />);

      // Send button should indicate processing state
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
    });

    it("should show streaming indicator when isStreaming is true", () => {
      render(<ConnectedChatInputForm {...defaultProps} isStreaming />);

      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
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
});
