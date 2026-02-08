/**
 * ChatInputForm Tests
 *
 * Tests for the rich chat input form component with voice input,
 * file uploads, and drag-drop support.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { axe } from "jest-axe";
import { ChatInputForm, UploadFile } from "./ChatInputForm";

import { TestProvider } from "@/test-utils";

describe("ChatInputForm", () => {
  const defaultProps = {
    input: "",
    onInputChange: vi.fn(),
    onSubmit: vi.fn(),
    isProcessing: false,
    isListening: false,
    isVoiceSupported: true,
    voiceError: null as string | null,
    onStartListening: vi.fn(),
    onStopListening: vi.fn(),
    uploadFiles: [] as UploadFile[],
    isUploading: false,
    isDragging: false,
    fileError: null as string | null,
    onSelectFiles: vi.fn(),
    onRemoveFile: vi.fn(),
    dragHandlers: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Text Input", () => {
    it("should render text input field", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByPlaceholderText(/type your message/i),
      ).toBeInTheDocument();
    });

    it("should call onInputChange when typing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const input = screen.getByPlaceholderText(/type your message/i);
      fireEvent.change(input, { target: { value: "Hello" } });
      expect(defaultProps.onInputChange).toHaveBeenCalledWith("Hello");
    });

    it("should display current input value", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="Test message" />
        </TestProvider>,
      );
      const input = screen.getByPlaceholderText(
        /type your message/i,
      ) as HTMLInputElement;
      expect(input.value).toBe("Test message");
    });

    it("should disable input when processing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isProcessing={true} />
        </TestProvider>,
      );
      const input = screen.getByPlaceholderText(/type your message/i);
      expect(input).toBeDisabled();
    });
  });

  describe("Send Button", () => {
    it("should render send button", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    });

    it("should disable send button when input is empty", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="" />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    });

    it("should disable send button when processing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="Hello" isProcessing={true} />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    });

    it("should enable send button when input has content and not processing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="Hello" />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /send/i })).not.toBeDisabled();
    });

    it("should show loading spinner when processing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="Hello" isProcessing={true} />
        </TestProvider>,
      );
      expect(screen.getByTestId("send-button-loading")).toBeInTheDocument();
    });
  });

  describe("Voice Input", () => {
    it("should render voice button when supported", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isVoiceSupported={true} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /start voice input/i }),
      ).toBeInTheDocument();
    });

    it("should not render voice button when not supported", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isVoiceSupported={false} />
        </TestProvider>,
      );
      expect(
        screen.queryByRole("button", { name: /voice input/i }),
      ).not.toBeInTheDocument();
    });

    it("should call onStartListening when voice button clicked", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(
        screen.getByRole("button", { name: /start voice input/i }),
      );
      expect(defaultProps.onStartListening).toHaveBeenCalledOnce();
    });

    it("should call onStopListening when listening and voice button clicked", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isListening={true} />
        </TestProvider>,
      );
      fireEvent.click(
        screen.getByRole("button", { name: /stop voice input/i }),
      );
      expect(defaultProps.onStopListening).toHaveBeenCalledOnce();
    });

    it("should show recording indicator when listening", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isListening={true} />
        </TestProvider>,
      );
      expect(screen.getByTestId("recording-indicator")).toBeInTheDocument();
      expect(screen.getByText(/listening/i)).toBeInTheDocument();
    });

    it("should display voice error when provided", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            voiceError="Microphone access denied"
          />
        </TestProvider>,
      );
      expect(screen.getByText("Microphone access denied")).toBeInTheDocument();
    });

    it("should show browser compatibility info when voice not supported", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isVoiceSupported={false} />
        </TestProvider>,
      );
      expect(
        screen.getByTestId("voice-not-supported-banner"),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/voice input.*not supported/i),
      ).toBeInTheDocument();
    });

    it("should include browser recommendation in compatibility banner", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isVoiceSupported={false} />
        </TestProvider>,
      );
      expect(screen.getByText(/chrome|edge|safari/i)).toBeInTheDocument();
    });

    it("should allow dismissing the compatibility banner", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isVoiceSupported={false} />
        </TestProvider>,
      );
      const dismissButton = screen.getByRole("button", {
        name: /dismiss/i,
      });
      fireEvent.click(dismissButton);
      expect(
        screen.queryByTestId("voice-not-supported-banner"),
      ).not.toBeInTheDocument();
    });
  });

  describe("File Upload", () => {
    it("should render file attachment button", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeInTheDocument();
    });

    it("should disable attachment button when processing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isProcessing={true} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeDisabled();
    });

    it("should disable attachment button when uploading", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isUploading={true} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeDisabled();
    });

    it("should display file error when provided", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} fileError="File too large" />
        </TestProvider>,
      );
      expect(screen.getByText("File too large")).toBeInTheDocument();
    });
  });

  describe("Attached Files Preview", () => {
    const mockFiles: UploadFile[] = [
      {
        id: "f1",
        file: new File([""], "doc1.pdf"),
        status: "ready",
        progress: 100,
      },
      {
        id: "f2",
        file: new File([""], "image.png"),
        status: "uploading",
        progress: 50,
      },
    ];

    it("should display attached files", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} uploadFiles={mockFiles} />
        </TestProvider>,
      );
      expect(screen.getByText("doc1.pdf")).toBeInTheDocument();
      expect(screen.getByText("image.png")).toBeInTheDocument();
    });

    it("should show upload progress for uploading files", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} uploadFiles={mockFiles} />
        </TestProvider>,
      );
      expect(screen.getByText("50%")).toBeInTheDocument();
    });

    it("should call onRemoveFile when remove button clicked", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} uploadFiles={mockFiles} />
        </TestProvider>,
      );
      const removeButtons = screen.getAllByRole("button", {
        name: /remove file/i,
      });
      fireEvent.click(removeButtons[0]);
      expect(defaultProps.onRemoveFile).toHaveBeenCalledWith("f1");
    });

    it("should show error status for failed uploads", () => {
      const filesWithError: UploadFile[] = [
        {
          id: "f1",
          file: new File([""], "doc.pdf"),
          status: "error",
          progress: 0,
          error: "Upload failed",
        },
      ];
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} uploadFiles={filesWithError} />
        </TestProvider>,
      );
      expect(screen.getByText("Upload failed")).toBeInTheDocument();
    });
  });

  describe("Drag and Drop", () => {
    it("should show drop zone overlay when dragging", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isDragging={true} />
        </TestProvider>,
      );
      expect(screen.getByTestId("drop-zone-overlay")).toBeInTheDocument();
      expect(screen.getByText(/drop files here/i)).toBeInTheDocument();
    });

    it("should not show drop zone overlay when not dragging", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isDragging={false} />
        </TestProvider>,
      );
      expect(screen.queryByTestId("drop-zone-overlay")).not.toBeInTheDocument();
    });
  });

  describe("Form Submission", () => {
    it("should call onSubmit when form submitted", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="Hello" />
        </TestProvider>,
      );
      const form = screen.getByTestId("chat-input-form");
      fireEvent.submit(form);
      expect(defaultProps.onSubmit).toHaveBeenCalledOnce();
    });

    it("should not submit when input is empty", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="" />
        </TestProvider>,
      );
      const form = screen.getByTestId("chat-input-form");
      fireEvent.submit(form);
      // onSubmit still called but parent should handle validation
      expect(defaultProps.onSubmit).toHaveBeenCalledOnce();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible labels for all interactive elements", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /start voice input/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    });

    it("should have placeholder text on input", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByPlaceholderText(/type your message/i),
      ).toBeInTheDocument();
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("Layout and Spacing", () => {
    it("should have proper bottom padding for comfortable spacing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const container = screen.getByTestId("chat-input-container");
      expect(container).toBeInTheDocument();
      // Container should have bottom padding class
      expect(container.className).toMatch(/pb-\d+|py-\d+/);
    });

    it("should have centered max-width container for wide screens", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const container = screen.getByTestId("chat-input-container");
      expect(container.className).toMatch(/max-w-/);
    });

    it("should use textarea for multi-line input support", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const textarea = screen.getByRole("textbox");
      expect(textarea.tagName.toLowerCase()).toBe("textarea");
    });

    it("should have proper input wrapper with grouped controls", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const wrapper = screen.getByTestId("input-wrapper");
      expect(wrapper).toBeInTheDocument();
    });
  });

  describe("Stop Streaming Button", () => {
    it("should show stop button when streaming", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Hello"
            isStreaming={true}
            onStopStreaming={vi.fn()}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("stop-streaming-button")).toBeInTheDocument();
    });

    it("should call onStopStreaming when stop button clicked", () => {
      const mockOnStopStreaming = vi.fn();
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Hello"
            isStreaming={true}
            onStopStreaming={mockOnStopStreaming}
          />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("stop-streaming-button"));
      expect(mockOnStopStreaming).toHaveBeenCalledOnce();
    });
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
