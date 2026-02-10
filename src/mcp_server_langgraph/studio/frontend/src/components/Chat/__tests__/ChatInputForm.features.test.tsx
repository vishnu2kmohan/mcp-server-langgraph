/**
 * ChatInputForm Feature Tests
 *
 * Tests for advanced features:
 * - Reasoning Effort Selector
 * - Model Selection
 * - Slash Command Menu
 * - URL Content Fetch (#URL integration)
 * - Cursor Position Tracking
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { TestProvider } from "@/test-utils";
import { createDefaultProps } from "./ChatInputForm.fixtures";
import { ChatInputForm } from "../ChatInputForm";

describe("ChatInputForm", () => {
  let defaultProps: ReturnType<typeof createDefaultProps>;

  beforeEach(() => {
    defaultProps = createDefaultProps();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Reasoning Effort Selector", () => {
    const mockOnReasoningEffortChange = vi.fn();

    beforeEach(() => {
      vi.clearAllMocks();
    });

    it("should render reasoning effort selector when model supports thinking", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            modelSupportsThinking={true}
            reasoningEffort="medium"
            onReasoningEffortChange={mockOnReasoningEffortChange}
          />
        </TestProvider>,
      );
      expect(
        screen.getByTestId("reasoning-effort-selector"),
      ).toBeInTheDocument();
    });

    it("should not render reasoning effort selector when model does not support thinking", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            modelSupportsThinking={false}
            reasoningEffort="medium"
            onReasoningEffortChange={mockOnReasoningEffortChange}
          />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("reasoning-effort-selector"),
      ).not.toBeInTheDocument();
    });

    it("should not render reasoning effort selector when enableThinking is false", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            modelSupportsThinking={true}
            enableThinking={false}
            reasoningEffort="medium"
            onReasoningEffortChange={mockOnReasoningEffortChange}
          />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("reasoning-effort-selector"),
      ).not.toBeInTheDocument();
    });

    it("should call onReasoningEffortChange when effort level is changed", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            modelSupportsThinking={true}
            reasoningEffort="medium"
            onReasoningEffortChange={mockOnReasoningEffortChange}
          />
        </TestProvider>,
      );

      // In compact mode, button shows "H" for high
      const highButton = screen.getByText("H");
      fireEvent.click(highButton);
      expect(mockOnReasoningEffortChange).toHaveBeenCalledWith("high");
    });

    it("should display current reasoning effort level", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            modelSupportsThinking={true}
            reasoningEffort="high"
            onReasoningEffortChange={mockOnReasoningEffortChange}
          />
        </TestProvider>,
      );

      // In compact mode, button shows "H" for high and should be selected
      const highButton = screen.getByText("H").closest("button");
      expect(highButton).toHaveAttribute("aria-pressed", "true");
    });

    it("should show enable thinking toggle when model supports thinking", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            modelSupportsThinking={true}
            enableThinking={true}
            reasoningEffort="medium"
            onReasoningEffortChange={mockOnReasoningEffortChange}
            onEnableThinkingChange={vi.fn()}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("enable-thinking-toggle")).toBeInTheDocument();
    });

    it("should call onEnableThinkingChange when toggle is clicked", () => {
      const mockOnEnableThinkingChange = vi.fn();
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            modelSupportsThinking={true}
            enableThinking={true}
            reasoningEffort="medium"
            onReasoningEffortChange={mockOnReasoningEffortChange}
            onEnableThinkingChange={mockOnEnableThinkingChange}
          />
        </TestProvider>,
      );

      const toggle = screen.getByTestId("enable-thinking-toggle");
      fireEvent.click(toggle);
      expect(mockOnEnableThinkingChange).toHaveBeenCalledWith(false);
    });

    it("should render in compact mode", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            modelSupportsThinking={true}
            reasoningEffort="medium"
            onReasoningEffortChange={mockOnReasoningEffortChange}
          />
        </TestProvider>,
      );
      // In compact mode, should show abbreviated labels
      expect(screen.getByText("M")).toBeInTheDocument();
    });
  });

  describe("Model Selection", () => {
    const mockOnModelChange = vi.fn();

    beforeEach(() => {
      mockOnModelChange.mockClear();
    });

    it("should render model selector when showModelSelector is true", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            selectedModel="gpt-4"
            onModelChange={mockOnModelChange}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("model-selector")).toBeInTheDocument();
    });

    it("should not render model selector when showModelSelector is false", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={false}
            selectedModel="gpt-4"
            onModelChange={mockOnModelChange}
          />
        </TestProvider>,
      );
      expect(screen.queryByTestId("model-selector")).not.toBeInTheDocument();
    });

    it("should display the currently selected model", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            selectedModel="claude-3-opus"
            onModelChange={mockOnModelChange}
          />
        </TestProvider>,
      );
      expect(screen.getByText(/claude-3-opus/i)).toBeInTheDocument();
    });

    it("should call onModelChange when a new model is selected", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            selectedModel="gpt-4"
            availableModels={[
              { id: "gpt-4", name: "GPT-4", provider: "openai" },
              {
                id: "claude-3-opus",
                name: "Claude 3 Opus",
                provider: "anthropic",
              },
            ]}
            onModelChange={mockOnModelChange}
          />
        </TestProvider>,
      );

      // Click the model selector to open dropdown
      const modelButton = screen.getByTestId("model-selector-button");
      fireEvent.click(modelButton);

      // Select a different model
      const claudeOption = screen.getByTestId("model-option-claude-3-opus");
      fireEvent.click(claudeOption);

      expect(mockOnModelChange).toHaveBeenCalledWith("claude-3-opus");
    });

    it("should show model provider badge", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            showModelSelector={true}
            selectedModel="gpt-4"
            availableModels={[
              { id: "gpt-4", name: "GPT-4", provider: "openai" },
            ]}
            onModelChange={mockOnModelChange}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/openai/i)).toBeInTheDocument();
    });

    it("should disable model selector when processing", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            isProcessing={true}
            showModelSelector={true}
            selectedModel="gpt-4"
            onModelChange={mockOnModelChange}
          />
        </TestProvider>,
      );

      const modelButton = screen.getByTestId("model-selector-button");
      expect(modelButton).toBeDisabled();
    });
  });

  describe("Slash Command Menu", () => {
    const defaultSlashCommands = [
      { name: "help", description: "Show help", icon: "help" as const },
      { name: "clear", description: "Clear chat", icon: "trash" as const },
      { name: "export", description: "Export chat", icon: "download" as const },
    ];

    it("should show slash command menu when typing / at start of input", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="/"
            slashCommands={defaultSlashCommands}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
    });

    it("should not show slash command menu when / is not at start", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="hello /"
            slashCommands={defaultSlashCommands}
          />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("slash-command-menu"),
      ).not.toBeInTheDocument();
    });

    it("should filter commands based on input after /", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="/hel"
            slashCommands={defaultSlashCommands}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
      expect(screen.getByTestId("command-item-help")).toBeInTheDocument();
      expect(
        screen.queryByTestId("command-item-clear"),
      ).not.toBeInTheDocument();
    });

    it("should call onSlashCommandSelect when command is clicked", () => {
      const mockOnSlashCommandSelect = vi.fn();
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="/"
            slashCommands={defaultSlashCommands}
            onSlashCommandSelect={mockOnSlashCommandSelect}
          />
        </TestProvider>,
      );

      const helpCommand = screen.getByTestId("command-item-help");
      fireEvent.click(helpCommand);

      expect(mockOnSlashCommandSelect).toHaveBeenCalledWith(
        expect.objectContaining({ name: "help" }),
      );
    });

    it("should close menu when Escape key is pressed", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="/"
            slashCommands={defaultSlashCommands}
          />
        </TestProvider>,
      );

      const menu = screen.getByTestId("slash-command-menu");
      fireEvent.keyDown(menu, { key: "Escape" });

      // Menu should be closed - test by checking input is cleared or menu is hidden
      expect(
        screen.queryByTestId("slash-command-menu"),
      ).not.toBeInTheDocument();
    });

    it("should not show menu when slashCommands prop is not provided", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="/" />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("slash-command-menu"),
      ).not.toBeInTheDocument();
    });
  });

  describe("URL Content Fetch (#URL integration)", () => {
    it("should show URL indicator when input contains #https://", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Check this #https://example.com for info"
            enableUrlFetch={true}
          />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("url-fetch-indicator");
      expect(indicator).toBeInTheDocument();
      // Check that the indicator contains the hostname
      expect(indicator).toHaveTextContent("example.com");
    });

    it("should not show URL indicator when enableUrlFetch is false", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Check this #https://example.com"
            enableUrlFetch={false}
          />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("url-fetch-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should show loading state when fetching URL content", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Check #https://example.com"
            enableUrlFetch={true}
            urlFetchLoading={["https://example.com"]}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("url-fetch-loading")).toBeInTheDocument();
    });

    it("should show fetched URL badge with title", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Check #https://example.com"
            enableUrlFetch={true}
            fetchedUrls={[
              {
                url: "https://example.com",
                title: "Example Page",
                content: "Content here",
              },
            ]}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("url-fetched-badge")).toBeInTheDocument();
      expect(screen.getByText(/Example Page/)).toBeInTheDocument();
    });

    it("should allow removing fetched URL", () => {
      const mockOnRemoveFetchedUrl = vi.fn();
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Check #https://example.com"
            enableUrlFetch={true}
            fetchedUrls={[
              {
                url: "https://example.com",
                title: "Example Page",
                content: "Content",
              },
            ]}
            onRemoveFetchedUrl={mockOnRemoveFetchedUrl}
          />
        </TestProvider>,
      );

      const removeButton = screen.getByRole("button", {
        name: /remove.*example/i,
      });
      fireEvent.click(removeButton);

      expect(mockOnRemoveFetchedUrl).toHaveBeenCalledWith(
        "https://example.com",
      );
    });
  });

  describe("Cursor Position Tracking", () => {
    it("should call onCursorPositionChange when cursor moves in legacy textarea", () => {
      const mockCursorChange = vi.fn();
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Hello world"
            enableRichTextMode={false}
            onCursorPositionChange={mockCursorChange}
          />
        </TestProvider>,
      );

      const textarea = screen.getByRole("textbox");

      // Simulate select event (cursor position change)
      fireEvent.select(textarea);

      expect(mockCursorChange).toHaveBeenCalled();
    });

    it("should not throw when onCursorPositionChange is not provided", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Hello world"
            enableRichTextMode={false}
          />
        </TestProvider>,
      );

      const textarea = screen.getByRole("textbox");

      // Should not throw when selecting without callback
      expect(() => {
        fireEvent.select(textarea);
      }).not.toThrow();
    });

    it("should pass onCursorPositionChange to RichTextInput in RichText mode", () => {
      const mockCursorChange = vi.fn();
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Hello world"
            enableRichTextMode={true}
            onCursorPositionChange={mockCursorChange}
          />
        </TestProvider>,
      );

      // RichTextInput should be rendered (pill container testid)
      expect(screen.getByTestId("pill-container")).toBeInTheDocument();

      // The textarea inside RichTextInput should be present
      const textarea = screen.getByRole("textbox");
      expect(textarea).toBeInTheDocument();

      // Simulate select event
      fireEvent.select(textarea);

      expect(mockCursorChange).toHaveBeenCalled();
    });

    it("should report cursor position after text input", () => {
      const mockCursorChange = vi.fn();
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input=""
            enableRichTextMode={false}
            onCursorPositionChange={mockCursorChange}
          />
        </TestProvider>,
      );

      const textarea = screen.getByRole("textbox");

      // Type some text
      fireEvent.change(textarea, { target: { value: "Hello" } });

      // Trigger select event to report position
      fireEvent.select(textarea);

      expect(mockCursorChange).toHaveBeenCalled();
    });
  });
});
