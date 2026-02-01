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
vi.mock("../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flagName: string) => mockIsEnabled(flagName),
}));

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
  selectSubmitOnEnter: (state: { ui: { submitOnEnter: boolean } }) =>
    state.ui.submitOnEnter,
}));

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

    it("should render RichTextInput when feature flag is enabled", () => {
      mockIsEnabled.mockImplementation(
        (flagName: string) => flagName === "rich_text_chat_input",
      );

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Pill container with RichTextInput should be present
      expect(screen.getByTestId("pill-container")).toBeInTheDocument();
      expect(screen.getByTestId("rich-text-input")).toBeInTheDocument();
    });

    it("should render plain textarea when feature flag is disabled", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Legacy input wrapper should be present, not pill container
      expect(screen.getByTestId("input-wrapper")).toBeInTheDocument();
      expect(screen.queryByTestId("pill-container")).not.toBeInTheDocument();
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
      const user = userEvent.setup();
      mockIsEnabled.mockImplementation(
        (flagName: string) => flagName === "rich_text_chat_input",
      );

      render(<ConnectedChatInputForm {...defaultProps} />);

      // AttachmentMenu button (+ button) should be accessible in RichText mode
      const attachmentMenuButton = screen.getByTestId("attachment-menu-button");
      expect(attachmentMenuButton).toBeInTheDocument();

      // Clicking should open menu with file upload option
      await user.click(attachmentMenuButton);
      expect(screen.getByText("Upload file")).toBeInTheDocument();
    });

    it("should preserve slash commands in RichText mode", () => {
      mockIsEnabled.mockImplementation(
        (flagName: string) => flagName === "rich_text_chat_input",
      );

      render(<ConnectedChatInputForm {...defaultProps} value="/" />);

      // Slash command menu should appear
      expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
    });

    it("should call useFeatureFlag with correct flag name", () => {
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Feature flag should be checked
      expect(mockIsEnabled).toHaveBeenCalledWith("rich_text_chat_input");
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
