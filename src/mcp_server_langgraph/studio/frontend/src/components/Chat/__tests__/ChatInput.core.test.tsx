/**
 * ChatInput Core Tests
 *
 * Covers: core functionality, send button, auto focus, layout, error states,
 * loading states, accessibility
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createMockProps } from "./ChatInput.fixtures";
import { TestProvider } from "@/test-utils";
import { ChatInput } from "../ChatInput";

describe("ChatInput - core", () => {
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
});
