/**
 * ConnectedChatInputForm Telemetry Integration Tests
 *
 * Tests that execution mode changes and bypass approvals are tracked
 * via sessionTelemetry.
 *
 * @see test-utils.tsx for MOTION_PROPS and filterMotionProps documentation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConnectedChatInputForm } from "./ConnectedChatInputForm";

// =============================================================================
// Mock TelemetryContext
// =============================================================================
const mockTrackExecutionModeChange = vi.fn();
const mockTrackBypassApproval = vi.fn();

vi.mock("../contexts/TelemetryContext", async () => {
  const actual = await vi.importActual("../contexts/TelemetryContext");
  return {
    ...actual,
    useSessionTelemetry: () => ({
      trackExecutionModeChange: mockTrackExecutionModeChange,
      trackBypassApproval: mockTrackBypassApproval,
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
// Mock Redux Store
// =============================================================================
let _mockExecutionMode = "default";
const mockDispatch = vi.fn();

vi.mock("../store/hooks", () => ({
  useAppSelector: (selector: (state: unknown) => unknown) => {
    const selectorStr = selector.toString();
    if (selectorStr.includes("submitOnEnter")) {
      return true;
    }
    // For all other selectors, let the slice mock handle it
    return selector({});
  },
  useAppDispatch: () => mockDispatch,
}));

vi.mock("../store/slices/uiSlice", () => ({
  default: (state = {}) => state,
  selectSubmitOnEnter: () => true,
}));

// Mock executionModeSlice - must return functions that useAppSelector can call
vi.mock("../store/slices/executionModeSlice", async () => {
  const actual = await vi.importActual("../store/slices/executionModeSlice");
  return {
    ...actual,
    selectExecutionMode: () => "default",
    selectCanBypass: () => true, // Alice has permission
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
// =============================================================================
// Mock API
// =============================================================================
vi.mock("../api", async () => {
  const actual = await vi.importActual("../api");
  return {
    ...actual,
    useCheckBypassPermissionQuery: () => ({
      data: { allowed: true },
      isLoading: false,
      isError: false,
    }),
  };
});

// =============================================================================
// Mock Other Hooks
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
    getContextString: vi.fn().mockReturnValue(""),
  }),
}));

vi.mock("../hooks/useInlineSuggestions", () => ({
  useInlineSuggestions: () => ({
    suggestion: "",
    isLoading: false,
    updateInput: vi.fn(),
    acceptSuggestion: vi.fn(),
    dismissSuggestion: vi.fn(),
  }),
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

vi.mock("../store/slices/chatConnectionSlice", async () => {
  const actual = await vi.importActual("../store/slices/chatConnectionSlice");
  return {
    ...actual,
    startConnectionSetup: vi.fn((payload) => ({
      type: "chatConnection/startConnectionSetup",
      payload,
    })),
  };
});
// =============================================================================
// Test Suite
// =============================================================================

describe("ConnectedChatInputForm Telemetry Integration", () => {
  const defaultProps = {
    value: "",
    onChange: vi.fn(),
    onSubmit: vi.fn(),
    sessionId: "test-session-123",
  };

  beforeEach(() => {
    vi.clearAllMocks();
    _mockExecutionMode = "default";
    // Enable execution mode toggle by default
    mockIsEnabled.mockImplementation(
      (flag: string) => flag === "execution_mode_toggle",
    );
  });

  afterEach(() => {
    cleanup();
  });

  describe("Execution Mode Change Telemetry", () => {
    it("should track mode change when clicking SegmentedControl segment", async () => {
      const user = userEvent.setup();

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Find and click the Plan mode segment
      const planSegment = screen.getByRole("radio", { name: /plan mode/i });
      await user.click(planSegment);

      // Verify dispatch was called
      expect(mockDispatch).toHaveBeenCalled();

      // Verify telemetry was tracked with correct trigger
      expect(mockTrackExecutionModeChange).toHaveBeenCalledWith({
        fromMode: "default",
        toMode: "plan",
        sessionId: "test-session-123",
        trigger: "click",
      });
    });

    it("should track mode change when using keyboard shortcut", async () => {
      const user = userEvent.setup();

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Focus on textarea and press Ctrl+Shift+M
      const textarea = screen.getByRole("textbox");
      await user.click(textarea);
      await user.keyboard("{Control>}{Shift>}m{/Shift}{/Control}");

      // Verify telemetry was tracked with keyboard trigger
      expect(mockTrackExecutionModeChange).toHaveBeenCalledWith(
        expect.objectContaining({
          trigger: "keyboard",
        }),
      );
    });

    it("should include sessionId in telemetry event", async () => {
      const user = userEvent.setup();

      render(
        <ConnectedChatInputForm {...defaultProps} sessionId="my-session-456" />,
      );

      const planSegment = screen.getByRole("radio", { name: /plan mode/i });
      await user.click(planSegment);

      expect(mockTrackExecutionModeChange).toHaveBeenCalledWith(
        expect.objectContaining({
          sessionId: "my-session-456",
        }),
      );
    });

    it("should track mode change to auto_accept mode", async () => {
      const user = userEvent.setup();

      render(<ConnectedChatInputForm {...defaultProps} />);

      // Click auto segment - use more specific selector to avoid matching "auto-approval"
      const autoSegment = screen.getByRole("radio", { name: /auto mode/i });

      await user.click(autoSegment);

      expect(mockTrackExecutionModeChange).toHaveBeenCalledWith(
        expect.objectContaining({
          toMode: "auto_accept",
        }),
      );
    });

    it("should not track telemetry when execution mode toggle is disabled", async () => {
      const user = userEvent.setup();
      mockIsEnabled.mockImplementation(() => false);

      render(<ConnectedChatInputForm {...defaultProps} />);

      // SegmentedControl shouldn't be visible when disabled
      expect(
        screen.queryByRole("radio", { name: /plan mode/i }),
      ).not.toBeInTheDocument();

      // Type in textarea and verify no telemetry
      const textarea = screen.getByRole("textbox");
      await user.click(textarea);
      await user.keyboard("{Control>}{Shift>}m{/Shift}{/Control}");

      expect(mockTrackExecutionModeChange).not.toHaveBeenCalled();
    });
  });

  describe("Telemetry Context Integration", () => {
    it("should use telemetry from context", () => {
      render(<ConnectedChatInputForm {...defaultProps} />);

      // Component should render without error
      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
    });
  });
});
