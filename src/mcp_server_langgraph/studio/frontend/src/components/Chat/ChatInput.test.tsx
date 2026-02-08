/**
 * ChatInput Component Tests
 *
 * Unified chat input component that consolidates ChatInputForm and RichTextInput.
 * Tests cover:
 * - Core input/submit functionality
 * - Model settings dropdown (model selector + thinking controls)
 * - File attachments
 * - Tool selector
 * - KB Focus selector
 * - Voice input
 * - Inline suggestions
 * - Keyboard shortcuts
 * - Accessibility
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInput } from "./ChatInput";
import type { ChatInputProps } from "./ChatInput";

import { TestProvider } from "@/test-utils";

// Mock props factory
const createMockProps = (
  overrides: Partial<ChatInputProps> = {},
): ChatInputProps => ({
  value: "",
  onChange: vi.fn(),
  onSubmit: vi.fn(),
  disabled: false,
  ...overrides,
});

describe("ChatInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("core functionality", () => {
    it("renders textarea with placeholder", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps()} />
        </TestProvider>,
      );

      expect(
        screen.getByPlaceholderText("Type your message..."),
      ).toBeInTheDocument();
    });

    it("displays controlled value", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ value: "Hello world" })} />
        </TestProvider>,
      );

      expect(screen.getByDisplayValue("Hello world")).toBeInTheDocument();
    });

    it("calls onChange when typing", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ onChange })} />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.type(textarea, "test");

      expect(onChange).toHaveBeenCalled();
    });

    it("calls onSubmit when Enter is pressed with content", async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({ value: "test message", onSubmit })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Enter}");

      expect(onSubmit).toHaveBeenCalled();
    });

    it("does not submit empty message", async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ value: "", onSubmit })} />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Enter}");

      expect(onSubmit).not.toHaveBeenCalled();
    });

    it("does not submit whitespace-only message", async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ value: "   ", onSubmit })} />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Enter}");

      expect(onSubmit).not.toHaveBeenCalled();
    });

    it("creates newline on Shift+Enter", async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ value: "test", onSubmit })} />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Shift>}{Enter}{/Shift}");

      expect(onSubmit).not.toHaveBeenCalled();
    });

    it("disables textarea when disabled prop is true", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ disabled: true })} />
        </TestProvider>,
      );

      expect(
        screen.getByPlaceholderText("Type your message..."),
      ).toBeDisabled();
    });
  });

  describe("send button", () => {
    it("renders send button", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps()} />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    });

    it("disables send button when value is empty", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ value: "" })} />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    });

    it("enables send button when value has content", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ value: "test" })} />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /send/i })).not.toBeDisabled();
    });

    it("calls onSubmit when send button is clicked", async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ value: "test", onSubmit })} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /send/i }));

      expect(onSubmit).toHaveBeenCalled();
    });

    it("shows stop button when streaming", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "test",
              isStreaming: true,
              onStopStreaming: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /stop/i })).toBeInTheDocument();
    });

    it("calls onStopStreaming when stop button is clicked", async () => {
      const user = userEvent.setup();
      const onStopStreaming = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "test",
              isStreaming: true,
              onStopStreaming,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /stop/i }));

      expect(onStopStreaming).toHaveBeenCalled();
    });
  });

  describe("attachment button", () => {
    it("renders attachment button with plus icon", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps()} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /attach/i }),
      ).toBeInTheDocument();
    });

    it("disables attachment button when disabled", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ disabled: true })} />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /attach/i })).toBeDisabled();
    });
  });

  describe("model settings dropdown", () => {
    const mockModels = [
      {
        id: "claude-opus-4-5",
        name: "Claude Opus 4.5",
        provider: "anthropic",
        supportsThinking: true,
      },
      {
        id: "claude-sonnet-4",
        name: "Claude Sonnet 4",
        provider: "anthropic",
        supportsThinking: false,
      },
      {
        id: "gpt-4o",
        name: "GPT-4o",
        provider: "openai",
        supportsThinking: false,
      },
    ];

    it("renders model settings button with brain icon when showModelSelector is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("model-settings-button")).toBeInTheDocument();
    });

    it("does not render model settings when showModelSelector is false", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ showModelSelector: false })} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("model-settings-button"),
      ).not.toBeInTheDocument();
    });

    it("displays selected model name on button", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Claude Opus 4.5")).toBeInTheDocument();
    });

    it("displays provider badge on button", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      // formatProviderDisplay properly cases provider names
      expect(screen.getByText("Anthropic")).toBeInTheDocument();
    });

    it("opens dropdown when clicked", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByTestId("model-settings-dropdown")).toBeInTheDocument();
    });

    it("shows all available models in dropdown", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByText("Claude Sonnet 4")).toBeInTheDocument();
      expect(screen.getByText("GPT-4o")).toBeInTheDocument();
    });

    it("calls onModelChange when model is selected", async () => {
      const user = userEvent.setup();
      const onModelChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              onModelChange,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));
      await user.click(screen.getByText("GPT-4o"));

      expect(onModelChange).toHaveBeenCalledWith("gpt-4o");
    });

    it("shows thinking controls when model supports thinking", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              modelSupportsThinking: true,
              reasoningEffort: "medium",
              onReasoningEffortChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByTestId("thinking-controls")).toBeInTheDocument();
    });

    it("hides thinking controls when model does not support thinking", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "gpt-4o",
              availableModels: mockModels,
              modelSupportsThinking: false,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.queryByTestId("thinking-controls")).not.toBeInTheDocument();
    });

    it("calls onReasoningEffortChange when thinking level is changed", async () => {
      const user = userEvent.setup();
      const onReasoningEffortChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              modelSupportsThinking: true,
              reasoningEffort: "medium",
              onReasoningEffortChange,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));
      await user.click(screen.getByRole("button", { name: /high/i }));

      expect(onReasoningEffortChange).toHaveBeenCalledWith("high");
    });

    it("closes dropdown when Escape is pressed", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));
      expect(screen.getByTestId("model-settings-dropdown")).toBeInTheDocument();

      await user.keyboard("{Escape}");
      expect(
        screen.queryByTestId("model-settings-dropdown"),
      ).not.toBeInTheDocument();
    });
  });

  describe("tool selector", () => {
    it("renders tool selector when showToolSelector is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showToolSelector: true,
              selectedTools: [],
              onSelectedToolsChange: vi.fn(),
              toolSelectionMode: "auto",
              onToolSelectionModeChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("tool-selector")).toBeInTheDocument();
    });

    it("does not render tool selector when showToolSelector is false", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ showToolSelector: false })} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("tool-selector")).not.toBeInTheDocument();
    });
  });

  describe("KB focus selector", () => {
    it("renders KB focus when showKBFocus is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showKBFocus: true,
              kbFocusValue: "all",
              onKBFocusChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("kb-focus-selector")).toBeInTheDocument();
    });

    it("does not render KB focus when showKBFocus is false", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ showKBFocus: false })} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("kb-focus-selector")).not.toBeInTheDocument();
    });
  });

  describe("voice input", () => {
    it("renders voice button when voice is supported", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              isVoiceSupported: true,
              isListening: false,
              onStartListening: vi.fn(),
              onStopListening: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /voice/i }),
      ).toBeInTheDocument();
    });

    it("does not render voice button when voice is not supported", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ isVoiceSupported: false })} />
        </TestProvider>,
      );

      expect(
        screen.queryByRole("button", { name: /voice/i }),
      ).not.toBeInTheDocument();
    });

    it("calls onStartListening when voice button is clicked", async () => {
      const user = userEvent.setup();
      const onStartListening = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              isVoiceSupported: true,
              isListening: false,
              onStartListening,
              onStopListening: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /voice/i }));

      expect(onStartListening).toHaveBeenCalled();
    });

    it("calls onStopListening when listening and voice button is clicked", async () => {
      const user = userEvent.setup();
      const onStopListening = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              isVoiceSupported: true,
              isListening: true,
              onStartListening: vi.fn(),
              onStopListening,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /stop.*voice/i }));

      expect(onStopListening).toHaveBeenCalled();
    });
  });

  describe("inline suggestions", () => {
    it("displays inline suggestion as ghost text", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "Hello",
              enableInlineSuggestions: true,
              inlineSuggestion: " world",
            })}
          />
        </TestProvider>,
      );

      const suggestion = screen.getByTestId("inline-suggestion");
      expect(suggestion).toBeInTheDocument();
      expect(suggestion.textContent).toBe(" world");
    });

    it("calls onAcceptSuggestion when Tab is pressed", async () => {
      const user = userEvent.setup();
      const onAcceptSuggestion = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "Hello",
              enableInlineSuggestions: true,
              inlineSuggestion: " world",
              onAcceptSuggestion,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Tab}");

      expect(onAcceptSuggestion).toHaveBeenCalledWith(" world");
    });

    it("calls onDismissSuggestion when Escape is pressed", async () => {
      const user = userEvent.setup();
      const onDismissSuggestion = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "Hello",
              enableInlineSuggestions: true,
              inlineSuggestion: " world",
              onDismissSuggestion,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Escape}");

      expect(onDismissSuggestion).toHaveBeenCalled();
    });
  });

  describe("keyboard shortcuts for formatting", () => {
    it("applies bold formatting on Ctrl+B", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "test",
              onChange,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      // Select all text then apply bold
      await user.keyboard("{Control>}a{/Control}{Control>}b{/Control}");

      expect(onChange).toHaveBeenCalled();
      // The call should wrap with **
      const calls = onChange.mock.calls;
      const hasStars = calls.some(
        (call) => typeof call[0] === "string" && call[0].includes("**"),
      );
      expect(hasStars).toBe(true);
    });

    it("applies italic formatting on Ctrl+I", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "test",
              onChange,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Control>}a{/Control}{Control>}i{/Control}");

      expect(onChange).toHaveBeenCalled();
    });

    it("applies code formatting on Ctrl+`", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "test",
              onChange,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Control>}a{/Control}{Control>}`{/Control}");

      expect(onChange).toHaveBeenCalled();
    });
  });

  describe("accessibility", () => {
    it("has accessible textarea label", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps()} />
        </TestProvider>,
      );

      // The textarea should be accessible via its label
      const textarea = screen.getByRole("textbox", { name: /message/i });
      expect(textarea).toBeInTheDocument();
    });

    it("model settings button has aria-haspopup", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: [
                {
                  id: "claude-opus-4-5",
                  name: "Claude Opus 4.5",
                  provider: "anthropic",
                },
              ],
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("model-settings-button")).toHaveAttribute(
        "aria-haspopup",
        "true",
      );
    });

    it("model settings dropdown has proper listbox role", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: [
                {
                  id: "claude-opus-4-5",
                  name: "Claude Opus 4.5",
                  provider: "anthropic",
                },
              ],
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    it("send button has aria-label", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps()} />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /send/i })).toHaveAttribute(
        "aria-label",
      );
    });
  });

  describe("layout", () => {
    it("renders single bottom controls row", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              showToolSelector: true,
              showKBFocus: true,
              isVoiceSupported: true,
              selectedModel: "test",
              availableModels: [{ id: "test", name: "Test", provider: "test" }],
              selectedTools: [],
              onSelectedToolsChange: vi.fn(),
              toolSelectionMode: "auto",
              onToolSelectionModeChange: vi.fn(),
              kbFocusValue: "all",
              onKBFocusChange: vi.fn(),
              isListening: false,
              onStartListening: vi.fn(),
              onStopListening: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("controls-row")).toBeInTheDocument();
    });

    it("does not render formatting toolbar (+/- toggle)", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps()} />
        </TestProvider>,
      );

      expect(
        screen.queryByRole("button", { name: /formatting/i }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByTestId("formatting-toolbar"),
      ).not.toBeInTheDocument();
    });

    it("renders pill container with rounded styling", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps()} />
        </TestProvider>,
      );

      expect(screen.getByTestId("chat-input-form")).toBeInTheDocument();
    });
  });

  describe("drag and drop", () => {
    it("shows drop zone overlay when dragging", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              isDragging: true,
              dragHandlers: {
                onDragOver: vi.fn(),
                onDragLeave: vi.fn(),
                onDrop: vi.fn(),
              },
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("drop-zone-overlay")).toBeInTheDocument();
    });

    it("hides drop zone overlay when not dragging", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              isDragging: false,
            })}
          />
        </TestProvider>,
      );

      expect(screen.queryByTestId("drop-zone-overlay")).not.toBeInTheDocument();
    });
  });

  describe("file previews", () => {
    it("displays uploaded files", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              uploadFiles: [
                {
                  id: "1",
                  file: new File([""], "test.pdf"),
                  status: "complete" as const,
                  progress: 100,
                },
              ],
              onRemoveFile: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByText("test.pdf")).toBeInTheDocument();
    });

    it("calls onRemoveFile when remove button is clicked", async () => {
      const user = userEvent.setup();
      const onRemoveFile = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              uploadFiles: [
                {
                  id: "1",
                  file: new File([""], "test.pdf"),
                  status: "complete" as const,
                  progress: 100,
                },
              ],
              onRemoveFile,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /remove/i }));

      expect(onRemoveFile).toHaveBeenCalledWith("1");
    });
  });

  describe("file selection", () => {
    it("calls onSelectFiles when attachment button triggers file input", async () => {
      const user = userEvent.setup();
      const onSelectFiles = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              onSelectFiles,
            })}
          />
        </TestProvider>,
      );

      // Find the hidden file input
      const fileInput = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;
      expect(fileInput).toBeInTheDocument();

      // Create a test file
      const testFile = new File(["test content"], "test.txt", {
        type: "text/plain",
      });

      // Simulate file selection
      await user.upload(fileInput, testFile);

      expect(onSelectFiles).toHaveBeenCalledWith([testFile]);
    });

    it("accepts multiple files when configured", async () => {
      const user = userEvent.setup();
      const onSelectFiles = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              onSelectFiles,
              acceptMultipleFiles: true,
            })}
          />
        </TestProvider>,
      );

      const fileInput = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;
      expect(fileInput).toHaveAttribute("multiple");

      const file1 = new File(["content1"], "file1.txt", { type: "text/plain" });
      const file2 = new File(["content2"], "file2.txt", { type: "text/plain" });

      await user.upload(fileInput, [file1, file2]);

      expect(onSelectFiles).toHaveBeenCalledWith([file1, file2]);
    });
  });

  describe("auto focus", () => {
    it("focuses textarea on mount when autoFocus is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              autoFocus: true,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByRole("textbox", { name: /message/i });
      expect(document.activeElement).toBe(textarea);
    });

    it("does not focus textarea on mount when autoFocus is false", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              autoFocus: false,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByRole("textbox", { name: /message/i });
      expect(document.activeElement).not.toBe(textarea);
    });
  });

  describe("models loading state", () => {
    const mockModels = [
      {
        id: "claude-opus-4-5",
        name: "Claude Opus 4.5",
        provider: "anthropic",
        supportsThinking: true,
      },
    ];

    it("shows loading indicator in model dropdown when isModelsLoading is true", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              isModelsLoading: true,
            })}
          />
        </TestProvider>,
      );

      // Open dropdown
      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByTestId("models-loading")).toBeInTheDocument();
    });

    it("does not show loading indicator when isModelsLoading is false", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              isModelsLoading: false,
            })}
          />
        </TestProvider>,
      );

      // Open dropdown
      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.queryByTestId("models-loading")).not.toBeInTheDocument();
    });
  });

  describe("slash commands", () => {
    const mockSlashCommands = [
      { name: "help", description: "Show help", icon: "help" },
      { name: "clear", description: "Clear conversation", icon: "trash" },
    ];

    it("shows slash command menu when user types /", async () => {
      const _user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "/",
              onChange,
              slashCommands: mockSlashCommands,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
    });

    it("calls onSlashCommandSelect when a command is clicked", async () => {
      const user = userEvent.setup();
      const onSlashCommandSelect = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "/",
              slashCommands: mockSlashCommands,
              onSlashCommandSelect,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByText("/help"));

      expect(onSlashCommandSelect).toHaveBeenCalledWith(mockSlashCommands[0]);
    });
  });

  // ===========================================================================
  // P0: Error States
  // ===========================================================================
  describe("error states", () => {
    it("displays voice error when voiceError is provided", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              isVoiceSupported: true,
              voiceError: "Microphone access denied",
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Microphone access denied")).toBeInTheDocument();
    });

    it("displays file error when fileError is provided", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              fileError: "File too large (max 10MB)",
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByText("File too large (max 10MB)")).toBeInTheDocument();
    });

    it("allows dismissing voice error", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              isVoiceSupported: true,
              voiceError: "Microphone access denied",
            })}
          />
        </TestProvider>,
      );

      const dismissButton = screen.getByRole("button", {
        name: /dismiss.*error/i,
      });
      await user.click(dismissButton);

      expect(
        screen.queryByText("Microphone access denied"),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // P0: Loading States
  // ===========================================================================
  describe("loading states", () => {
    it("shows upload indicator when isUploading is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              isUploading: true,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("upload-indicator")).toBeInTheDocument();
    });

    it("shows suggestion loading spinner when isSuggestionLoading is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              enableInlineSuggestions: true,
              isSuggestionLoading: true,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestion-loading")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // P0: Submit Behavior
  // ===========================================================================
  describe("submitOnEnter preference", () => {
    it("submits on Enter when submitOnEnter is true (default)", async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "test message",
              onSubmit,
              submitOnEnter: true,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Enter}");

      expect(onSubmit).toHaveBeenCalled();
    });

    it("does not submit on Enter when submitOnEnter is false", async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "test message",
              onSubmit,
              onChange,
              submitOnEnter: false,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Enter}");

      expect(onSubmit).not.toHaveBeenCalled();
    });

    it("submits on Ctrl+Enter when submitOnEnter is false", async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "test message",
              onSubmit,
              submitOnEnter: false,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Control>}{Enter}{/Control}");

      expect(onSubmit).toHaveBeenCalled();
    });

    it("inserts newline on Shift+Enter regardless of submitOnEnter", async () => {
      const user = userEvent.setup();
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "test",
              onSubmit,
              submitOnEnter: true,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);
      await user.keyboard("{Shift>}{Enter}{/Shift}");

      expect(onSubmit).not.toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // P0: Cursor Position Tracking
  // ===========================================================================
  describe("cursor position tracking", () => {
    it("calls onCursorPositionChange when cursor moves", async () => {
      const user = userEvent.setup();
      const onCursorPositionChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "hello world",
              onCursorPositionChange,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.click(textarea);

      expect(onCursorPositionChange).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // P1: Thinking Toggle
  // ===========================================================================
  describe("thinking toggle", () => {
    const mockModels = [
      {
        id: "claude-opus-4-5",
        name: "Claude Opus 4.5",
        provider: "anthropic",
        supportsThinking: true,
      },
    ];

    it("shows thinking toggle when enableThinking prop is provided", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              modelSupportsThinking: true,
              enableThinking: true,
              onEnableThinkingChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByTestId("thinking-toggle")).toBeInTheDocument();
    });

    it("calls onEnableThinkingChange when toggle is clicked", async () => {
      const user = userEvent.setup();
      const onEnableThinkingChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              modelSupportsThinking: true,
              enableThinking: true,
              onEnableThinkingChange,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));
      await user.click(screen.getByTestId("thinking-toggle"));

      expect(onEnableThinkingChange).toHaveBeenCalledWith(false);
    });
  });

  // ===========================================================================
  // P1: URL Content Fetch
  // ===========================================================================
  describe("URL content fetch", () => {
    it("shows URL loading indicator when urlFetchLoading contains URLs", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              enableUrlFetch: true,
              urlFetchLoading: ["https://example.com"],
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("url-fetch-loading")).toBeInTheDocument();
    });

    it("displays fetched URL badges", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              enableUrlFetch: true,
              fetchedUrls: [
                {
                  url: "https://example.com",
                  title: "Example Site",
                  content: "...",
                },
              ],
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Example Site")).toBeInTheDocument();
    });

    it("calls onRemoveFetchedUrl when URL badge is removed", async () => {
      const user = userEvent.setup();
      const onRemoveFetchedUrl = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              enableUrlFetch: true,
              fetchedUrls: [
                {
                  url: "https://example.com",
                  title: "Example Site",
                  content: "...",
                },
              ],
              onRemoveFetchedUrl,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /remove.*url/i }));

      expect(onRemoveFetchedUrl).toHaveBeenCalledWith("https://example.com");
    });
  });

  // ===========================================================================
  // P2: Mentions System
  // ===========================================================================
  describe("mentions system", () => {
    const mockMentionOptions = [
      {
        type: "model" as const,
        value: "claude-opus-4-5",
        label: "Claude Opus 4.5",
      },
      { type: "file" as const, value: "readme.md", label: "readme.md" },
    ];

    it("shows mention suggestions when @ is typed", async () => {
      const _user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "@",
              onChange,
              mentionOptions: mockMentionOptions,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("mention-suggestions")).toBeInTheDocument();
    });

    it("inserts mention when suggestion is clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "@cl",
              onChange,
              mentionOptions: mockMentionOptions,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByText("Claude Opus 4.5"));

      expect(onChange).toHaveBeenCalledWith(
        expect.stringContaining("@claude-opus-4-5"),
      );
    });
  });

  // ===========================================================================
  // P2: Recent Models and Model Search
  // ===========================================================================
  describe("recent models and model search", () => {
    const mockModels = [
      { id: "claude-opus-4-5", name: "Claude Opus 4.5", provider: "anthropic" },
      { id: "claude-sonnet-4", name: "Claude Sonnet 4", provider: "anthropic" },
      { id: "gpt-4o", name: "GPT-4o", provider: "openai" },
    ];

    it("shows recent models section when recentModels is provided", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              recentModels: ["gpt-4o", "claude-sonnet-4"],
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByText("Recent")).toBeInTheDocument();
    });

    it("shows model search input when enableModelSearch is true", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              enableModelSearch: true,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByPlaceholderText(/search models/i)).toBeInTheDocument();
    });

    it("filters models based on search query", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              enableModelSearch: true,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));
      await user.type(screen.getByPlaceholderText(/search models/i), "gpt");

      // GPT-4o should be visible in the dropdown
      expect(screen.getByText("GPT-4o")).toBeInTheDocument();
      // Claude models should be filtered out from the dropdown list
      // (Claude Opus 4.5 will still appear on the button as the selected model)
      const dropdown = screen.getByTestId("model-settings-dropdown");
      expect(dropdown.querySelector('[role="option"]')?.textContent).toContain(
        "GPT-4o",
      );
      // Verify Claude Sonnet 4 is not in the dropdown (it was never the selected model)
      expect(screen.queryByText("Claude Sonnet 4")).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // P2: Character Count and maxLength
  // ===========================================================================
  describe("character count and maxLength", () => {
    it("shows character count when maxLength is provided", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "Hello",
              maxLength: 100,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByText("5 / 100")).toBeInTheDocument();
    });

    it("prevents input beyond maxLength", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "12345",
              onChange,
              maxLength: 5,
            })}
          />
        </TestProvider>,
      );

      const textarea = screen.getByPlaceholderText("Type your message...");
      await user.type(textarea, "6");

      // onChange should not be called with value exceeding maxLength
      expect(onChange).not.toHaveBeenCalledWith("123456");
    });

    it("shows warning when approaching maxLength", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "a".repeat(95),
              maxLength: 100,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("char-count-warning")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // P3: KB Status Indicator
  // ===========================================================================
  describe("KB status indicator", () => {
    it("shows KB status indicator when kbStatus is provided", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showKBFocus: true,
              kbFocusValue: "kb_only",
              onKBFocusChange: vi.fn(),
              kbStatus: "ready",
              kbStatusMessage: "Knowledge base is ready",
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("kb-status-indicator")).toBeInTheDocument();
    });

    it("shows tooltip with kbStatusMessage on hover", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showKBFocus: true,
              kbFocusValue: "kb_only",
              onKBFocusChange: vi.fn(),
              kbStatus: "misconfigured",
              kbStatusMessage: "API key not configured",
            })}
          />
        </TestProvider>,
      );

      await user.hover(screen.getByTestId("kb-status-indicator"));

      expect(screen.getByText("API key not configured")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // P3: Model Lifecycle Badges
  // ===========================================================================
  describe("model lifecycle badges", () => {
    const mockModelsWithStatus = [
      {
        id: "claude-opus-4-5",
        name: "Claude Opus 4.5",
        provider: "anthropic",
        status: "current" as const,
      },
      {
        id: "claude-3-opus",
        name: "Claude 3 Opus",
        provider: "anthropic",
        status: "deprecated" as const,
        sunsetDate: "2025-06-01",
      },
      {
        id: "gpt-4-preview",
        name: "GPT-4 Preview",
        provider: "openai",
        status: "preview" as const,
      },
    ];

    it("shows lifecycle badge for deprecated models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModelsWithStatus,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByText("Deprecated")).toBeInTheDocument();
    });

    it("shows preview badge for preview models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModelsWithStatus,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByText("Preview")).toBeInTheDocument();
    });

    it("shows sunset date for deprecated models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModelsWithStatus,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByText(/sunset.*2025-06-01/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // P3: Tools Loading State
  // ===========================================================================
  describe("tools loading state", () => {
    it("shows loading indicator in tool selector when isToolsLoading is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showToolSelector: true,
              isToolsLoading: true,
              onSelectedToolsChange: vi.fn(),
              onToolSelectionModeChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("tools-loading")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // P3: PreferencesMenu Integration
  // ===========================================================================
  describe("PreferencesMenu integration", () => {
    const mockModels = [
      { id: "claude-opus-4-5", name: "Claude Opus 4.5", provider: "anthropic" },
      { id: "claude-sonnet-4", name: "Claude Sonnet 4", provider: "anthropic" },
    ];

    it("renders PreferencesMenu when showPreferencesMenu is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showPreferencesMenu: true,
              availableModels: mockModels,
              selectedModel: "claude-opus-4-5",
              onModelChange: vi.fn(),
              onThinkingLevelChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(
        screen.getByTestId("preferences-menu-trigger"),
      ).toBeInTheDocument();
    });

    it("hides model selector when showPreferencesMenu is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showPreferencesMenu: true,
              showModelSelector: true,
              availableModels: mockModels,
              selectedModel: "claude-opus-4-5",
              onModelChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      // PreferencesMenu should be visible
      expect(
        screen.getByTestId("preferences-menu-trigger"),
      ).toBeInTheDocument();
      // Standard model selector should NOT be visible (preferences menu replaces it)
      expect(
        screen.queryByTestId("model-settings-button"),
      ).not.toBeInTheDocument();
    });

    it("passes model props to PreferencesMenu", async () => {
      const onModelChange = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showPreferencesMenu: true,
              availableModels: mockModels,
              selectedModel: "claude-opus-4-5",
              onModelChange,
            })}
          />
        </TestProvider>,
      );

      // Open preferences menu
      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Verify menu opened
      expect(screen.getByTestId("preferences-dropdown")).toBeInTheDocument();
    });

    it("passes thinking level props to PreferencesMenu", async () => {
      const onThinkingLevelChange = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showPreferencesMenu: true,
              availableModels: mockModels,
              selectedModel: "claude-opus-4-5",
              thinkingLevel: "medium",
              onThinkingLevelChange,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Verify thinking submenu trigger exists
      expect(
        screen.getByTestId("submenu-trigger-thinking"),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // P3: ExecutionMode Integration
  // ===========================================================================
  describe("ExecutionMode integration", () => {
    it("renders SegmentedControl when onExecutionModeChange is provided", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              executionMode: "default",
              onExecutionModeChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      // SegmentedControl wrapper is rendered when onExecutionModeChange is provided
      expect(
        screen.getByTestId("execution-mode-segmented"),
      ).toBeInTheDocument();
    });

    it("renders ExecutionModeIndicator when only onCycleExecutionMode is provided", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              executionMode: "plan",
              onCycleExecutionMode: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      // ExecutionModeIndicator shows the mode badge when only cycling is available
      expect(
        screen.getByTestId("execution-mode-indicator"),
      ).toBeInTheDocument();
    });

    it("calls onExecutionModeChange when mode is changed via SegmentedControl", async () => {
      const onExecutionModeChange = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              executionMode: "default",
              onExecutionModeChange,
            })}
          />
        </TestProvider>,
      );

      // Find and click the plan mode option
      const planOption = screen.getByRole("radio", { name: /plan/i });
      await user.click(planOption);

      expect(onExecutionModeChange).toHaveBeenCalledWith("plan");
    });

    it("calls onCycleExecutionMode when keyboard shortcut is used", async () => {
      const onCycleExecutionMode = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              executionMode: "default",
              onCycleExecutionMode,
            })}
          />
        </TestProvider>,
      );

      // Focus the textarea
      const textarea = screen.getByRole("textbox");
      await user.click(textarea);

      // Ctrl+Shift+M cycles execution mode
      await user.keyboard("{Control>}{Shift>}m{/Shift}{/Control}");

      expect(onCycleExecutionMode).toHaveBeenCalled();
    });
  });

  describe("Provider Display Formatting", () => {
    const mockModelsWithVendor = [
      {
        id: "claude-opus-4-5",
        name: "Claude Opus 4.5",
        provider: "anthropic",
        vendor: "vertex_ai_anthropic" as const,
      },
      {
        id: "gemini-2.5-pro",
        name: "Gemini 2.5 Pro",
        provider: "google",
        vendor: "vertex_ai" as const,
      },
      {
        id: "gpt-4o",
        name: "GPT-4o",
        provider: "openai",
      },
    ];

    it("displays formatted provider names with proper casing in dropdown", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModelsWithVendor,
            })}
          />
        </TestProvider>,
      );

      // Open the model dropdown
      await user.click(screen.getByTestId("model-settings-button"));

      // Should show properly formatted provider names with vendor context
      // Vertex AI models show "(Vertex AI)" suffix, direct API models show just the provider
      // Use getAllByText since button AND dropdown both show the selected model's provider
      expect(
        screen.getAllByText("Anthropic (Vertex AI)").length,
      ).toBeGreaterThan(0);
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
      expect(screen.getByText("Google (Vertex AI)")).toBeInTheDocument();
    });

    it("shows vendor info when different from provider", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModelsWithVendor,
            })}
          />
        </TestProvider>,
      );

      // Open the model dropdown
      await user.click(screen.getByTestId("model-settings-button"));

      // Vertex AI models should show vendor context (getAllByText since multiple may exist)
      const vertexElements = screen.getAllByText(/Vertex AI/);
      expect(vertexElements.length).toBeGreaterThan(0);
    });
  });
});
