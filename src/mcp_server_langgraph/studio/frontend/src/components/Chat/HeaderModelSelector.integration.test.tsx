/**
 * HeaderModelSelector Integration Tests
 *
 * Tests for model selector integration with ConversationPanel:
 * - Model selection flows to streaming API
 * - Thinking level selection propagates correctly
 * - Session header displays selector properly
 *
 * @see ADR-0102 for model selector consolidation decision
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  within,
  waitFor,
  cleanup,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HeaderModelSelector, type ModelOption } from "./HeaderModelSelector";
import type { ReasoningEffortLevel } from "./ReasoningEffortSelector";
import { TestProvider } from "../../test-utils";

// =============================================================================
// Test Data
// =============================================================================

const mockModels: ModelOption[] = [
  {
    id: "claude-opus-4.5",
    name: "Claude Opus 4.5",
    provider: "anthropic",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "claude-sonnet-4",
    name: "Claude Sonnet 4",
    provider: "anthropic",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "openai",
    supportsThinking: false,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "gemini-2.5-pro",
    name: "Gemini 2.5 Pro",
    provider: "google",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "preview",
  },
];

// =============================================================================
// Integration Test Component
// =============================================================================

interface SessionHeaderProps {
  title?: string;
  selectedModel: string;
  availableModels: ModelOption[];
  thinkingLevel: ReasoningEffortLevel;
  onModelChange: (modelId: string) => void;
  onThinkingLevelChange: (level: ReasoningEffortLevel) => void;
  onSendMessage?: (model: string, thinkingLevel: ReasoningEffortLevel) => void;
}

/**
 * Test wrapper simulating session header context with HeaderModelSelector.
 * This mimics the actual usage in ConnectedConversationPanel.
 * Wrapped with TestProvider for RTK Query support (useNativeCapabilities hook).
 */
function SessionHeaderWithModelSelector({
  title = "New Conversation",
  selectedModel,
  availableModels,
  thinkingLevel,
  onModelChange,
  onThinkingLevelChange,
  onSendMessage,
}: SessionHeaderProps) {
  const handleSend = () => {
    onSendMessage?.(selectedModel, thinkingLevel);
  };

  return (
    <div
      data-testid="session-header"
      className="flex items-center justify-between px-4 py-2 border-b"
    >
      <div className="flex items-center gap-3 min-w-0">
        <h2
          className="text-sm font-medium truncate"
          data-testid="session-title"
        >
          {title}
        </h2>
        <HeaderModelSelector
          selectedModel={selectedModel}
          availableModels={availableModels}
          thinkingLevel={thinkingLevel}
          onModelChange={onModelChange}
          onThinkingLevelChange={onThinkingLevelChange}
          compact
        />
      </div>
      <button onClick={handleSend} data-testid="send-button">
        Send
      </button>
    </div>
  );
}

// =============================================================================
// Tests
// =============================================================================

describe("HeaderModelSelector Integration", () => {
  const defaultProps = {
    selectedModel: "claude-opus-4.5",
    availableModels: mockModels,
    thinkingLevel: "medium" as ReasoningEffortLevel,
    onModelChange: vi.fn(),
    onThinkingLevelChange: vi.fn(),
    onSendMessage: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("Session Header Integration", () => {
    it("renders model selector alongside session title", () => {
      render(
        <TestProvider>
          <SessionHeaderWithModelSelector {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("session-header")).toBeInTheDocument();
      expect(screen.getByTestId("session-title")).toHaveTextContent(
        "New Conversation",
      );
      expect(screen.getByTestId("header-model-selector")).toBeInTheDocument();
    });

    it("displays compact model name in header context", () => {
      render(
        <TestProvider>
          <SessionHeaderWithModelSelector {...defaultProps} />
        </TestProvider>,
      );

      // In compact mode, "Claude Opus 4.5" should show as "Opus 4.5"
      expect(screen.getByText(/Opus/)).toBeInTheDocument();
    });

    it("displays thinking level for thinking-capable models", () => {
      render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            thinkingLevel="high"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/High/i)).toBeInTheDocument();
    });

    it("hides thinking level for non-thinking models", () => {
      render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel="gpt-4o"
          />
        </TestProvider>,
      );

      // GPT-4o doesn't support thinking, so no level should be shown
      expect(screen.queryByText(/Medium/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/Low/i)).not.toBeInTheDocument();
      expect(screen.queryByText(/High/i)).not.toBeInTheDocument();
    });
  });

  describe("Model Selection Flow", () => {
    it("calls onModelChange when model is selected", async () => {
      const user = userEvent.setup();
      const onModelChange = vi.fn();

      render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Open dropdown
      await user.click(screen.getByTestId("header-model-selector"));

      // Select a different model
      await user.click(screen.getByRole("option", { name: /GPT-4o/ }));

      expect(onModelChange).toHaveBeenCalledWith("gpt-4o");
    });

    it("selected model is passed to send message callback", async () => {
      const user = userEvent.setup();
      const onSendMessage = vi.fn();

      render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel="gemini-2.5-pro"
            thinkingLevel="high"
            onSendMessage={onSendMessage}
          />
        </TestProvider>,
      );

      // Click send
      await user.click(screen.getByTestId("send-button"));

      expect(onSendMessage).toHaveBeenCalledWith("gemini-2.5-pro", "high");
    });

    it("updates selected model in pill after selection", async () => {
      const user = userEvent.setup();
      let selectedModel = "claude-opus-4.5";
      const onModelChange = vi.fn((id: string) => {
        selectedModel = id;
      });

      const { rerender } = render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel={selectedModel}
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Initial state - Opus shown
      expect(screen.getByText(/Opus/)).toBeInTheDocument();

      // Open dropdown and select GPT-4o
      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("option", { name: /GPT-4o/ }));

      // Rerender with updated model
      rerender(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel={selectedModel}
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // GPT-4o should now be displayed
      expect(screen.getByText(/GPT-4o/)).toBeInTheDocument();
    });
  });

  describe("Thinking Level Flow", () => {
    it("calls onThinkingLevelChange when level is changed", async () => {
      const user = userEvent.setup();
      const onThinkingLevelChange = vi.fn();

      render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            onThinkingLevelChange={onThinkingLevelChange}
          />
        </TestProvider>,
      );

      // Open dropdown
      await user.click(screen.getByTestId("header-model-selector"));

      // Change thinking level
      await user.click(screen.getByRole("radio", { name: /High/i }));

      expect(onThinkingLevelChange).toHaveBeenCalledWith("high");
    });

    it("thinking level is passed to send message callback", async () => {
      const user = userEvent.setup();
      const onSendMessage = vi.fn();

      render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            thinkingLevel="low"
            onSendMessage={onSendMessage}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("send-button"));

      expect(onSendMessage).toHaveBeenCalledWith("claude-opus-4.5", "low");
    });

    it("thinking level section appears for thinking-capable models", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <SessionHeaderWithModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("thinking-level-section")).toBeInTheDocument();
    });

    it("thinking level section hidden for non-thinking models", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel="gpt-4o"
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(
        screen.queryByTestId("thinking-level-section"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Model Switching Affects Thinking Level Visibility", () => {
    it("switching from thinking to non-thinking model hides thinking level", async () => {
      const user = userEvent.setup();
      let selectedModel = "claude-opus-4.5";
      const onModelChange = vi.fn((id: string) => {
        selectedModel = id;
      });

      const { rerender } = render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel={selectedModel}
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Initially thinking level should be visible
      expect(screen.getByText(/Medium/i)).toBeInTheDocument();

      // Switch to GPT-4o
      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("option", { name: /GPT-4o/ }));

      rerender(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel={selectedModel}
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Thinking level should now be hidden
      expect(screen.queryByText(/Medium/i)).not.toBeInTheDocument();
    });

    it("switching from non-thinking to thinking model shows thinking level", async () => {
      const user = userEvent.setup();
      let selectedModel = "gpt-4o";
      const onModelChange = vi.fn((id: string) => {
        selectedModel = id;
      });

      const { rerender } = render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel={selectedModel}
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Initially thinking level should be hidden
      expect(screen.queryByText(/Medium/i)).not.toBeInTheDocument();

      // Switch to Claude Sonnet 4
      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("option", { name: /Claude Sonnet 4/ }));

      rerender(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel={selectedModel}
            onModelChange={onModelChange}
          />
        </TestProvider>,
      );

      // Thinking level should now be visible
      expect(screen.getByText(/Medium/i)).toBeInTheDocument();
    });
  });

  describe("Full Message Flow Simulation", () => {
    it("simulates complete model selection → thinking level → send flow", async () => {
      const user = userEvent.setup();
      let selectedModel = "claude-opus-4.5";
      let thinkingLevel: ReasoningEffortLevel = "medium";
      const onModelChange = vi.fn((id: string) => {
        selectedModel = id;
      });
      const onThinkingLevelChange = vi.fn((level: ReasoningEffortLevel) => {
        thinkingLevel = level;
      });
      const onSendMessage = vi.fn();

      const { rerender } = render(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel={selectedModel}
            thinkingLevel={thinkingLevel}
            onModelChange={onModelChange}
            onThinkingLevelChange={onThinkingLevelChange}
            onSendMessage={onSendMessage}
          />
        </TestProvider>,
      );

      // Step 1: Open dropdown
      await user.click(screen.getByTestId("header-model-selector"));

      // Step 2: Select a different model
      await user.click(screen.getByRole("option", { name: /Claude Sonnet 4/ }));

      rerender(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel={selectedModel}
            thinkingLevel={thinkingLevel}
            onModelChange={onModelChange}
            onThinkingLevelChange={onThinkingLevelChange}
            onSendMessage={onSendMessage}
          />
        </TestProvider>,
      );

      // Step 3: Open dropdown again and set thinking level to high
      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("radio", { name: /High/i }));

      rerender(
        <TestProvider>
          <SessionHeaderWithModelSelector
            {...defaultProps}
            selectedModel={selectedModel}
            thinkingLevel={thinkingLevel}
            onModelChange={onModelChange}
            onThinkingLevelChange={onThinkingLevelChange}
            onSendMessage={onSendMessage}
          />
        </TestProvider>,
      );

      // Close dropdown by clicking outside
      await user.keyboard("{Escape}");

      // Step 4: Send message
      await user.click(screen.getByTestId("send-button"));

      // Verify the full flow
      expect(onModelChange).toHaveBeenCalledWith("claude-sonnet-4");
      expect(onThinkingLevelChange).toHaveBeenCalledWith("high");
      expect(onSendMessage).toHaveBeenCalledWith("claude-sonnet-4", "high");
    });
  });

  describe("Dropdown Persistence", () => {
    it("dropdown remains open after changing thinking level", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <SessionHeaderWithModelSelector {...defaultProps} />
        </TestProvider>,
      );

      // Open dropdown
      await user.click(screen.getByTestId("header-model-selector"));
      expect(screen.getByTestId("model-dropdown")).toBeInTheDocument();

      // Change thinking level
      await user.click(screen.getByRole("radio", { name: /High/i }));

      // Dropdown should still be open
      expect(screen.getByTestId("model-dropdown")).toBeInTheDocument();
    });

    it("dropdown closes after model selection", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <SessionHeaderWithModelSelector {...defaultProps} />
        </TestProvider>,
      );

      // Open dropdown
      await user.click(screen.getByTestId("header-model-selector"));
      expect(screen.getByTestId("model-dropdown")).toBeInTheDocument();

      // Select a model
      await user.click(screen.getByRole("option", { name: /GPT-4o/ }));

      // Dropdown should close
      await waitFor(() => {
        expect(screen.queryByTestId("model-dropdown")).not.toBeInTheDocument();
      });
    });
  });

  describe("Status Badge Display", () => {
    it("shows preview badge in dropdown for preview models", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <SessionHeaderWithModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      const geminiOption = screen.getByRole("option", {
        name: /Gemini 2.5 Pro/,
      });
      expect(within(geminiOption).getByText("Preview")).toBeInTheDocument();
    });

    it("shows thinking badge for thinking-capable models in dropdown", async () => {
      const user = userEvent.setup();

      render(
        <TestProvider>
          <SessionHeaderWithModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      // Claude models should have thinking badge
      const opusOption = screen.getByRole("option", {
        name: /Claude Opus 4.5/,
      });
      expect(
        within(opusOption).getByTestId("thinking-badge"),
      ).toBeInTheDocument();

      // GPT-4o should not have thinking badge
      const gptOption = screen.getByRole("option", { name: /GPT-4o/ });
      expect(
        within(gptOption).queryByTestId("thinking-badge"),
      ).not.toBeInTheDocument();
    });
  });
});
