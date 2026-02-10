/**
 * ConnectedChatInputForm Integrations Tests
 *
 * Tests for: Feature Flag Integration, Knowledge Base Integration,
 *            Preferences Menu Integration
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
  defaultProps,
  resetAllMockStates,
} from "./ConnectedChatInputForm.fixtures";

// =============================================================================
// vi.mock() calls - all paths adjusted for __tests__/ depth
// =============================================================================

vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flagName: string) => mockIsEnabled(flagName),
}));

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

vi.mock("../../store/slices/chatConnectionSlice", () => ({
  startConnectionSetup: vi.fn((payload) => ({
    type: "chatConnection/startConnectionSetup",
    payload,
  })),
}));

vi.mock("../../store/slices/executionModeSlice", () => ({
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

vi.mock("../../contexts/TelemetryContext", () => ({
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
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
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
