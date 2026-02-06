/**
 * ConnectedChatInputForm Integration Tests
 *
 * Split from ConnectedChatInputForm.test.tsx for memory-safe test execution.
 * Tests cover:
 * - Knowledge Base integration
 * - URL fetch integration
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
    if (selector.toString().includes("submitOnEnter")) {
      return mockSubmitOnEnter.current;
    }
    return undefined;
  },
  useAppDispatch: () => mockDispatch,
}));

vi.mock("../store/slices/uiSlice", () => ({
  default: (state = {}) => state,
  selectSubmitOnEnter: (state: { ui: { submitOnEnter: boolean } }) =>
    state.ui.submitOnEnter,
}));

// Mock TelemetryContext
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

describe("ConnectedChatInputForm - Integration", () => {
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
  // Knowledge Base Integration Tests
  // ===========================================================================

  describe("Knowledge Base Integration", () => {
    // Helper to enable both kb_focus and rich_text_chat_input flags
    // KB Focus is now in the AttachmentMenu submenu (Slack-style redesign)
    const enableKBFocusFlags = () => {
      mockIsEnabled.mockImplementation(
        (flag: string) =>
          flag === "kb_focus" || flag === "rich_text_chat_input",
      );
    };

    // TODO: AttachmentMenu is not yet integrated into ConnectedChatInputForm
    // These tests will be enabled when AttachmentMenu integration is complete
    it.todo(
      "should render KB Focus submenu in AttachmentMenu when feature flag is enabled",
    );

    it.skip("should render KB Focus submenu in AttachmentMenu when feature flag is enabled - PENDING IMPLEMENTATION", async () => {
      const user = userEvent.setup();
      enableKBFocusFlags();

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Open the AttachmentMenu (+ button)
      await user.click(screen.getByTestId("attachment-menu-button"));

      // KB Focus menu item should be in the dropdown
      expect(screen.getByTestId("menu-item-kb-focus")).toBeInTheDocument();
    });

    it.skip("should not render KB Focus submenu when feature flag is disabled", async () => {
      const user = userEvent.setup();
      // Only enable rich_text_chat_input, but NOT kb_focus
      mockIsEnabled.mockImplementation(
        (flag: string) => flag === "rich_text_chat_input",
      );

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Open the AttachmentMenu
      await user.click(screen.getByTestId("attachment-menu-button"));

      // KB Focus should not be in menu
      expect(
        screen.queryByTestId("menu-item-kb-focus"),
      ).not.toBeInTheDocument();
    });

    it.skip("should show KB Focus submenu options", async () => {
      const user = userEvent.setup();
      enableKBFocusFlags();

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Open the AttachmentMenu
      await user.click(screen.getByTestId("attachment-menu-button"));

      // Hover over KB Focus to open submenu
      await user.hover(screen.getByTestId("menu-item-kb-focus"));

      // Submenu should show options
      expect(screen.getByTestId("kb-focus-submenu")).toBeInTheDocument();
      expect(screen.getByText("All Sources")).toBeInTheDocument();
    });

    it.skip("should initialize with 'all' focus mode by default", async () => {
      const user = userEvent.setup();
      enableKBFocusFlags();

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Open the AttachmentMenu
      await user.click(screen.getByTestId("attachment-menu-button"));

      // Hover to open submenu
      await user.hover(screen.getByTestId("menu-item-kb-focus"));

      // "All Sources" should be checked by default
      expect(screen.getByTestId("kb-focus-check-all")).toBeInTheDocument();
    });

    it.skip("should allow changing KB focus mode via submenu", async () => {
      const user = userEvent.setup();
      enableKBFocusFlags();

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Open the AttachmentMenu
      await user.click(screen.getByTestId("attachment-menu-button"));

      // Hover over KB Focus to open submenu
      await user.hover(screen.getByTestId("menu-item-kb-focus"));

      // Click "Web Only" option
      await user.click(screen.getByText("Web Only"));

      // Re-open menu to verify selection
      await user.click(screen.getByTestId("attachment-menu-button"));
      await user.hover(screen.getByTestId("menu-item-kb-focus"));

      // "Web Only" should now be checked
      expect(screen.getByTestId("kb-focus-check-web_only")).toBeInTheDocument();
    });

    it.skip("should handle unavailable KB status gracefully", async () => {
      const user = userEvent.setup();
      enableKBFocusFlags();
      mockKBStatusReturn.data = {
        status: "unavailable",
        qdrantConnected: false,
      };
      mockKBStatusReturn.kbStatusForUI = "unavailable";

      render(<ConnectedChatInputForm {...defaultProps} />);

      // AttachmentMenu should still be accessible
      await user.click(screen.getByTestId("attachment-menu-button"));

      // KB Focus menu item should still render
      expect(screen.getByTestId("menu-item-kb-focus")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // URL Fetch Tests (Sprint 1 - Chat Input Gap Fix)
  // ===========================================================================

  describe("URL Fetch Integration", () => {
    beforeEach(() => {
      mockIsEnabled.mockImplementation(
        (flagName: string) => flagName === "rich_text_chat_input",
      );
    });

    it("should enable URL fetch when enableUrlFetch is true", () => {
      // Set up mock to have detected URLs
      mockUrlContentFetchReturn.detectedUrls = [
        { raw: "#https://example.com", url: "https://example.com" },
      ];

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          enableUrlFetch={true}
          value="Check this #https://example.com"
        />,
      );

      // URL fetch indicator should appear when URL pattern detected
      expect(screen.getByTestId("url-fetch-indicator")).toBeInTheDocument();
    });

    it("should not show URL fetch indicator when enableUrlFetch is false", () => {
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          enableUrlFetch={false}
          value="Check this #https://example.com"
        />,
      );

      expect(
        screen.queryByTestId("url-fetch-indicator"),
      ).not.toBeInTheDocument();
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

      // Fetched URL badge should show after successful fetch
      expect(screen.getByTestId("url-fetched-badge")).toBeInTheDocument();
    });

    it("should default enableUrlFetch to false", () => {
      render(
        <ConnectedChatInputForm
          {...defaultProps}
          value="Check this #https://example.com"
        />,
      );

      expect(
        screen.queryByTestId("url-fetch-indicator"),
      ).not.toBeInTheDocument();
    });
  });
});
