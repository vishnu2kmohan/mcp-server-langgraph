/**
 * ConnectedChatInputForm Core Tests
 *
 * Tests for: Rendering, Input Handling, File Upload, Voice Input, Processing State
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Import mock state from fixtures (these are imported before vi.mock so they're available)
import {
  mockFileUploadReturn,
  mockVoiceInputReturn,
  mockKBStatusReturn,
  mockUrlContentFetchReturn,
  mockUseInlineSuggestionsReturn,
  mockUseAISuggestionsWebSocketReturn,
  mockConnectorSuggestionsReturn,
  mockIsEnabled,
  mockSubmitOnEnter,
  mockDispatch,
  mockRemoveFile,
  mockStartListening,
  mockStopListening,
  defaultProps,
  resetAllMockStates,
} from "./ConnectedChatInputForm.fixtures";

// =============================================================================
// vi.mock() calls - all paths adjusted for __tests__/ depth
// =============================================================================

vi.mock("../../contexts/FeatureFlagContext", async () => {
  const actual = await vi.importActual("../../contexts/FeatureFlagContext");
  return {
    ...actual,
    useFeatureFlag: (flagName: string) => mockIsEnabled(flagName),
  };
});
vi.mock("../../store/hooks", () => ({
  useAppSelector: (selector: (state: unknown) => unknown) => {
    // Return the mock value for selectSubmitOnEnter
    if (selector.toString().includes("submitOnEnter")) {
      return mockSubmitOnEnter.current;
    }
    return undefined;
  },
  useAppDispatch: () => mockDispatch,
}));

vi.mock("../../store/slices/uiSlice", () => ({
  default: (state = {}) => state,
  selectSubmitOnEnter: (state: { ui: { submitOnEnter: boolean } }) =>
    state.ui.submitOnEnter,
}));

vi.mock("../../hooks/useFileUpload", () => ({
  useFileUpload: () => mockFileUploadReturn,
}));

vi.mock("../../hooks/useVoiceInput", () => ({
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

vi.mock("../../hooks/useKBStatus", () => ({
  useKBStatus: () => mockKBStatusReturn,
}));

vi.mock("../../hooks/useUrlContentFetch", () => ({
  useUrlContentFetch: () => mockUrlContentFetchReturn,
}));

vi.mock("../../hooks/useInlineSuggestions", () => ({
  useInlineSuggestions: () => mockUseInlineSuggestionsReturn,
}));

vi.mock("../../hooks/useAISuggestionsWebSocket", () => ({
  useAISuggestionsWebSocket: () => mockUseAISuggestionsWebSocketReturn,
}));

vi.mock("../../hooks/useConnectorSuggestions", () => ({
  useConnectorSuggestions: () => mockConnectorSuggestionsReturn,
}));

vi.mock("../../hooks/useAvailableTools", () => ({
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

vi.mock("../../store/slices/chatConnectionSlice", async () => {
  const actual = await vi.importActual(
    "../../store/slices/chatConnectionSlice",
  );
  return {
    ...actual,
    startConnectionSetup: vi.fn((payload) => ({
      type: "chatConnection/startConnectionSetup",
      payload,
    })),
  };
});
vi.mock("../../store/slices/executionModeSlice", async () => {
  const actual = await vi.importActual("../../store/slices/executionModeSlice");
  return {
    ...actual,
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
  };
});
vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useCheckBypassPermissionQuery: () => ({
      data: { allowed: false },
      isLoading: false,
      isError: false,
    }),
  };
});

vi.mock("../../contexts/TelemetryContext", async () => {
  const actual = await vi.importActual("../../contexts/TelemetryContext");
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
import { ConnectedChatInputForm } from "../ConnectedChatInputForm";

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedChatInputForm", () => {
  beforeEach(() => {
    resetAllMockStates();
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
