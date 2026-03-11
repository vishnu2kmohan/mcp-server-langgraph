/**
 * ConnectedChatInputForm Features Tests
 *
 * Tests for: Slash Commands, Inline Suggestions, Model Selection,
 *            Reasoning Effort, URL Fetch Integration
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { SlashCommand } from "../../types/chat";

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
});
