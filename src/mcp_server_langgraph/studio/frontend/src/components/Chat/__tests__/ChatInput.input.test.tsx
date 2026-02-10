/**
 * ChatInput Input Behavior Tests
 *
 * Covers: keyboard shortcuts for formatting, submitOnEnter preference,
 * cursor position tracking, character count and maxLength, thinking toggle
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createMockProps } from "./ChatInput.fixtures";
import { TestProvider } from "@/test-utils";
import { ChatInput } from "../ChatInput";

describe("ChatInput - input", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
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
});
