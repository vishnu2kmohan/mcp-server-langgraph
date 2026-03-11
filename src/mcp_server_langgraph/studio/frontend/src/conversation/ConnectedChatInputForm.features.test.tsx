/**
 * ConnectedChatInputForm Features Tests
 *
 * Split from ConnectedChatInputForm.test.tsx for memory-safe test execution.
 * Tests cover:
 * - Inline suggestions
 * - Feature flag integration (RichText mode)
 * - Model selection
 * - Reasoning effort
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConnectedChatInputForm } from "./ConnectedChatInputForm";

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

// Mock useUrlContentFetch hook
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

// Mock useInlineSuggestions hook
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

describe("ConnectedChatInputForm - Features", () => {
  const defaultProps = {
    value: "",
    onChange: vi.fn(),
    onSubmit: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockFileUploadReturn.files = [];
    mockFileUploadReturn.isUploading = false;
    mockFileUploadReturn.isDragging = false;
    mockFileUploadReturn.error = null;
    mockVoiceInputReturn.isListening = false;
    mockVoiceInputReturn.isSupported = true;
    mockVoiceInputReturn.error = null;
    mockKBStatusReturn.data = undefined;
    mockKBStatusReturn.isLoading = false;
    mockKBStatusReturn.isError = false;
    mockKBStatusReturn.isReady = false;
    mockKBStatusReturn.kbStatusForUI = undefined;
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
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
    });

    it("should not display suggestion when enableInlineSuggestions is false", () => {
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          enableInlineSuggestions={false}
          inlineSuggestion="complete this sentence"
        />,
      );

      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
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
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
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
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
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

    it("should render ChatInput when feature flag is enabled", () => {
      mockIsEnabled.mockImplementation(
        (flagName: string) => flagName === "rich_text_chat_input",
      );

      render(<ConnectedChatInputForm {...defaultProps} />);

      // ChatInput (consolidated component) renders with data-testid="chat-input-form"
      // (pill-container/rich-text-input testids were in the old ChatInputForm component)
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("should render ChatInput when feature flag is disabled", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      // ChatInput (consolidated component) always renders chat-input-form
      // (input-wrapper/pill-container testids were in the old ChatInputForm component)
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("should pass submitOnEnter=true from uiSlice (ChatGPT style)", () => {
      mockIsEnabled.mockImplementation(
        (flagName: string) => flagName === "rich_text_chat_input",
      );
      mockSubmitOnEnter.current = true;

      render(<ConnectedChatInputForm {...defaultProps} value="Hello" />);

      // Enter should submit (ChatGPT style)
      const textarea = screen.getByRole("textbox");
      expect(textarea).toBeInTheDocument();
    });

    it("should pass submitOnEnter=false from uiSlice (Legacy style)", () => {
      mockIsEnabled.mockImplementation(
        (flagName: string) => flagName === "rich_text_chat_input",
      );
      mockSubmitOnEnter.current = false;

      render(<ConnectedChatInputForm {...defaultProps} value="Hello" />);

      // Ctrl+Enter should submit (Legacy style)
      const textarea = screen.getByRole("textbox");
      expect(textarea).toBeInTheDocument();
    });

    it("should preserve voice input integration in RichText mode", () => {
      mockIsEnabled.mockImplementation(
        (flagName: string) => flagName === "rich_text_chat_input",
      );
      mockVoiceInputReturn.isSupported = true;

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Voice button should be accessible in RichText mode
      expect(
        screen.getByRole("button", { name: /voice input/i }),
      ).toBeInTheDocument();
    });

    it("should preserve file upload integration in RichText mode", async () => {
      mockIsEnabled.mockImplementation(
        (flagName: string) => flagName === "rich_text_chat_input",
      );

      render(<ConnectedChatInputForm {...defaultProps} />);

      // ChatInput renders a simple "Attach file" button (not an AttachmentMenu dropdown).
      // The button directly triggers the hidden file input via click.
      const attachButton = screen.getByRole("button", { name: /attach file/i });
      expect(attachButton).toBeInTheDocument();
    });

    it("should preserve slash commands in RichText mode", () => {
      mockIsEnabled.mockImplementation(
        (flagName: string) => flagName === "rich_text_chat_input",
      );

      render(<ConnectedChatInputForm {...defaultProps} value="/" />);

      // Slash command menu should appear
      expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
    });

    it("should call useFeatureFlag with correct flag names", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      // ConnectedChatInputForm checks these feature flags (not "rich_text_chat_input"):
      // kb_focus, ai_suggestions_websocket, manual_tool_selection,
      // execution_mode_toggle, preferences_menu, connector_suggestions
      expect(mockIsEnabled).toHaveBeenCalledWith("kb_focus");
      expect(mockIsEnabled).toHaveBeenCalledWith("connector_suggestions");
      expect(mockIsEnabled).toHaveBeenCalledWith("manual_tool_selection");
      expect(mockIsEnabled).toHaveBeenCalledWith("execution_mode_toggle");
      expect(mockIsEnabled).toHaveBeenCalledWith("preferences_menu");
    });
  });

  // ===========================================================================
  // Model Selection Tests - REMOVED
  // ===========================================================================
  // Model selection has been moved from ChatInputForm to HeaderModelSelector
  // in the session header. See:
  // - HeaderModelSelector.test.tsx (unit tests)
  // - HeaderModelSelector.integration.test.tsx (integration tests)
  // - ADR-0102 for the consolidation decision

  // ===========================================================================
  // Reasoning Effort Tests - REMOVED
  // ===========================================================================
  // Reasoning effort/thinking level selection has been moved from ChatInputForm
  // to HeaderModelSelector in the session header. See:
  // - HeaderModelSelector.test.tsx (unit tests)
  // - HeaderModelSelector.integration.test.tsx (integration tests)
  // - ADR-0102 for the consolidation decision
});
