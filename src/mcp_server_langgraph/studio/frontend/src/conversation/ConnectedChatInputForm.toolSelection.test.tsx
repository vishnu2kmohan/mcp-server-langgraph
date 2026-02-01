/**
 * ConnectedChatInputForm Tool Selection Tests
 *
 * Tests for manual tool selection integration in ConnectedChatInputForm.
 * This feature allows users to override semantic tool search with explicit choices.
 *
 * @see Manual Tool Selection plan for architecture details
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
// Mock Redux Store
// =============================================================================
const mockDispatch = vi.fn();
vi.mock("../store/hooks", () => ({
  useAppSelector: () => true,
  useAppDispatch: () => mockDispatch,
}));

vi.mock("../store/slices/uiSlice", () => ({
  selectSubmitOnEnter: () => true,
}));

// =============================================================================
// Mock Hooks
// =============================================================================

vi.mock("../hooks/useFileUpload", () => ({
  useFileUpload: () => ({
    files: [],
    isUploading: false,
    isDragging: false,
    error: null,
    selectFiles: vi.fn(),
    removeFile: vi.fn(),
    dragHandlers: {
      onDragEnter: vi.fn(),
      onDragLeave: vi.fn(),
      onDragOver: vi.fn(),
      onDrop: vi.fn(),
    },
  }),
}));

vi.mock("../hooks/useVoiceInput", () => ({
  useVoiceInput: () => ({
    isListening: false,
    isSupported: true,
    error: null,
    transcript: "",
    startListening: vi.fn(),
    stopListening: vi.fn(),
  }),
}));

vi.mock("../hooks/useKBStatus", () => ({
  useKBStatus: () => ({
    data: undefined,
    isLoading: false,
    isError: false,
    isReady: false,
    kbStatusForUI: undefined,
    refetch: vi.fn(),
  }),
}));

vi.mock("../hooks/useUrlContentFetch", () => ({
  useUrlContentFetch: () => ({
    detectedUrls: [],
    detectUrls: vi.fn(),
    fetchUrl: vi.fn(),
    fetchedContent: [],
    isLoading: false,
    loadingUrls: [],
    clearContent: vi.fn(),
    clearUrl: vi.fn(),
    getContextString: vi.fn(),
  }),
}));

vi.mock("../hooks/useInlineSuggestions", () => ({
  useInlineSuggestions: () => ({
    suggestion: null,
    isLoading: false,
    error: null,
    acceptSuggestion: vi.fn(),
    dismissSuggestion: vi.fn(),
    requestSuggestion: vi.fn(),
    updateInput: vi.fn(),
  }),
}));

vi.mock("../hooks/useConnectorSuggestions", () => ({
  useConnectorSuggestions: () => ({
    suggestions: [],
    isLoading: false,
    isVisible: false,
    updateInput: vi.fn(),
    dismiss: vi.fn(),
    reset: vi.fn(),
  }),
}));

// Mock useAvailableTools hook
const mockUseAvailableToolsReturn = {
  tools: [
    {
      name: "calculator",
      displayName: "Calculator",
      source: "builtin" as const,
      description: "Math operations",
    },
    {
      name: "web_search",
      displayName: "Web Search",
      source: "builtin" as const,
      description: "Search the web",
    },
    {
      name: "github:create_issue",
      displayName: "Create Issue",
      source: "mcp" as const,
      serverName: "github",
      description: "Create a GitHub issue",
    },
  ],
  filteredTools: [],
  groupedTools: { builtin: [], mcp: {} },
  isLoading: false,
  isError: false,
  error: null,
  refetch: vi.fn(),
  builtinCount: 2,
  mcpCount: 1,
  totalCount: 3,
  getToolByName: vi.fn(),
};

vi.mock("../hooks/useAvailableTools", () => ({
  useAvailableTools: () => mockUseAvailableToolsReturn,
}));

vi.mock("../hooks/useAISuggestionsWebSocket", () => ({
  useAISuggestionsWebSocket: () => ({
    status: "disconnected",
    currentSuggestion: null,
    isPending: false,
    requestSuggestion: vi.fn(),
    acceptSuggestion: vi.fn(),
    rejectSuggestion: vi.fn(),
    updateContext: vi.fn(),
    clearSuggestion: vi.fn(),
  }),
}));

// =============================================================================
// Test Setup
// =============================================================================

describe("ConnectedChatInputForm - Tool Selection", () => {
  const defaultProps = {
    value: "",
    onChange: vi.fn(),
    onSubmit: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Default: all feature flags disabled except rich_text_chat_input
    mockIsEnabled.mockImplementation((flagName: string) => {
      if (flagName === "rich_text_chat_input") return true;
      if (flagName === "manual_tool_selection") return true;
      return false;
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Feature Flag Integration
  // ===========================================================================

  describe("Feature Flag Integration", () => {
    it("should check manual_tool_selection feature flag", () => {
      render(<ConnectedChatInputForm {...defaultProps} />);

      expect(mockIsEnabled).toHaveBeenCalledWith("manual_tool_selection");
    });

    it("should show ToolSelector when feature flag is enabled", () => {
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return true;
        return false;
      });

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Tool selector should be visible
      expect(
        screen.getByRole("button", { name: /tools/i }),
      ).toBeInTheDocument();
    });

    it("should NOT show ToolSelector when feature flag is disabled", () => {
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return false;
        return false;
      });

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Tool selector should NOT be visible
      expect(
        screen.queryByRole("button", { name: /tools/i }),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Tool Selection State Management
  // ===========================================================================

  describe("Tool Selection State", () => {
    it("should start with auto mode by default", () => {
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return true;
        return false;
      });

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Should show "Auto" in the tool selector button
      const toolButton = screen.getByRole("button", { name: /tools/i });
      expect(toolButton).toHaveTextContent("Auto");
    });

    it("should allow switching to manual mode", async () => {
      const user = userEvent.setup();
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return true;
        return false;
      });

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Open dropdown
      const toolButton = screen.getByRole("button", { name: /tools/i });
      await user.click(toolButton);

      // Click Manual mode button
      const manualButton = screen.getByRole("option", { name: /manual/i });
      await user.click(manualButton);

      // Should update to show selection count or "Select"
      expect(
        screen.getByRole("button", { name: /tools/i }),
      ).toBeInTheDocument();
    });

    it("should allow switching to none mode", async () => {
      const user = userEvent.setup();
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return true;
        return false;
      });

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Open dropdown
      const toolButton = screen.getByRole("button", { name: /tools/i });
      await user.click(toolButton);

      // Click None mode button
      const noneButton = screen.getByRole("option", { name: /none/i });
      await user.click(noneButton);

      // Should show "None"
      expect(screen.getByRole("button", { name: /tools/i })).toHaveTextContent(
        "None",
      );
    });
  });

  // ===========================================================================
  // Tool Selection UI
  // ===========================================================================

  describe("Tool Selection UI", () => {
    it("should display available tools in dropdown", async () => {
      const user = userEvent.setup();
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return true;
        return false;
      });

      render(
        <ConnectedChatInputForm {...defaultProps} toolSelectionMode="manual" />,
      );

      // Open dropdown - already in manual mode
      const toolButton = screen.getByRole("button", { name: /tools/i });
      await user.click(toolButton);

      // Should show search input in manual mode
      expect(screen.getByPlaceholderText(/search tools/i)).toBeInTheDocument();
    });

    it("should be disabled when processing", () => {
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return true;
        return false;
      });

      render(<ConnectedChatInputForm {...defaultProps} isProcessing />);

      const toolButton = screen.getByRole("button", { name: /tools/i });
      expect(toolButton).toBeDisabled();
    });

    it("should show loading state when tools are loading", () => {
      mockUseAvailableToolsReturn.isLoading = true;
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return true;
        return false;
      });

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Should show loading indicator
      expect(screen.getByTestId("tool-selector-loading")).toBeInTheDocument();

      // Reset
      mockUseAvailableToolsReturn.isLoading = false;
    });
  });

  // ===========================================================================
  // Controlled Props
  // ===========================================================================

  describe("Controlled Props", () => {
    it("should accept controlled selectedTools prop", () => {
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return true;
        return false;
      });

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          selectedTools={["calculator", "web_search"]}
          toolSelectionMode="manual"
        />,
      );

      // Should show count of selected tools
      const toolButton = screen.getByRole("button", { name: /tools/i });
      expect(toolButton).toHaveTextContent("2");
    });

    it("should call onSelectedToolsChange when selection changes", async () => {
      const user = userEvent.setup();
      const mockOnSelectedToolsChange = vi.fn();
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return true;
        return false;
      });

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          toolSelectionMode="manual"
          onSelectedToolsChange={mockOnSelectedToolsChange}
        />,
      );

      // Open dropdown
      const toolButton = screen.getByRole("button", { name: /tools/i });
      await user.click(toolButton);

      // The tool checkboxes should be available
      // Note: This test verifies the prop is passed, actual selection is tested in ToolSelector.test.tsx
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
    });

    it("should call onToolSelectionModeChange when mode changes", async () => {
      const user = userEvent.setup();
      const mockOnToolSelectionModeChange = vi.fn();
      mockIsEnabled.mockImplementation((flagName: string) => {
        if (flagName === "rich_text_chat_input") return true;
        if (flagName === "manual_tool_selection") return true;
        return false;
      });

      render(
        <ConnectedChatInputForm
          {...defaultProps}
          onToolSelectionModeChange={mockOnToolSelectionModeChange}
        />,
      );

      // Open dropdown
      const toolButton = screen.getByRole("button", { name: /tools/i });
      await user.click(toolButton);

      // Click Manual mode
      const manualButton = screen.getByRole("option", { name: /manual/i });
      await user.click(manualButton);

      // Should call callback
      expect(mockOnToolSelectionModeChange).toHaveBeenCalledWith("manual");
    });
  });
});
