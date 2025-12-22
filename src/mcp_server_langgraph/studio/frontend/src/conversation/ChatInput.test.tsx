/**
 * ChatInput Tests - Phase 2
 *
 * Tests for the chat input component with slash command support.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { ChatInput } from "./ChatInput";

expect.extend(toHaveNoViolations);

// =============================================================================
// Tests
// =============================================================================

describe("ChatInput", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render input container", () => {
      render(<ChatInput onSend={() => {}} />);
      expect(screen.getByTestId("chat-input-container")).toBeInTheDocument();
    });

    it("should render textarea", () => {
      render(<ChatInput onSend={() => {}} />);
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("should render send button", () => {
      render(<ChatInput onSend={() => {}} />);
      expect(screen.getByTestId("send-button")).toBeInTheDocument();
    });

    it("should show placeholder text", () => {
      render(<ChatInput onSend={() => {}} placeholder="Type here..." />);
      expect(screen.getByPlaceholderText("Type here...")).toBeInTheDocument();
    });
  });

  describe("Input Handling", () => {
    it("should update value on input", async () => {
      render(<ChatInput onSend={() => {}} />);
      const input = screen.getByRole("textbox");

      await userEvent.type(input, "Hello world");
      expect(input).toHaveValue("Hello world");
    });

    it("should call onSend when send button clicked", async () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} />);

      await userEvent.type(screen.getByRole("textbox"), "Test message");
      fireEvent.click(screen.getByTestId("send-button"));

      expect(onSend).toHaveBeenCalledWith("Test message");
    });

    it("should call onSend on Enter key", async () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} />);

      const input = screen.getByRole("textbox");
      await userEvent.type(input, "Test message{Enter}");

      expect(onSend).toHaveBeenCalledWith("Test message");
    });

    it("should not send on Shift+Enter", async () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} />);

      const input = screen.getByRole("textbox");
      await userEvent.type(input, "Line 1{Shift>}{Enter}{/Shift}Line 2");

      expect(onSend).not.toHaveBeenCalled();
    });

    it("should clear input after sending", async () => {
      render(<ChatInput onSend={() => {}} />);

      const input = screen.getByRole("textbox");
      await userEvent.type(input, "Test message{Enter}");

      expect(input).toHaveValue("");
    });
  });

  describe("Disabled State", () => {
    it("should disable input when disabled prop is true", () => {
      render(<ChatInput onSend={() => {}} disabled />);
      expect(screen.getByRole("textbox")).toBeDisabled();
    });

    it("should disable send button when disabled", () => {
      render(<ChatInput onSend={() => {}} disabled />);
      expect(screen.getByTestId("send-button")).toBeDisabled();
    });

    it("should disable send button when input is empty", () => {
      render(<ChatInput onSend={() => {}} />);
      expect(screen.getByTestId("send-button")).toBeDisabled();
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true", () => {
      render(<ChatInput onSend={() => {}} isLoading />);
      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });

    it("should disable input when loading", () => {
      render(<ChatInput onSend={() => {}} isLoading />);
      expect(screen.getByRole("textbox")).toBeDisabled();
    });
  });

  describe("Slash Commands", () => {
    it("should trigger onSlashCommand when / is typed", async () => {
      const onSlashCommand = vi.fn();
      render(<ChatInput onSend={() => {}} onSlashCommand={onSlashCommand} />);

      await userEvent.type(screen.getByRole("textbox"), "/");
      expect(onSlashCommand).toHaveBeenCalled();
    });

    it("should show slash command indicator when typing /", async () => {
      render(<ChatInput onSend={() => {}} />);
      await userEvent.type(screen.getByRole("textbox"), "/he");

      expect(screen.getByTestId("slash-command-indicator")).toBeInTheDocument();
    });
  });

  describe("Auto-resize", () => {
    it("should expand textarea for multiline content", async () => {
      render(<ChatInput onSend={() => {}} />);
      const input = screen.getByRole("textbox") as HTMLTextAreaElement;

      // Mock scrollHeight to simulate growing content (JSDOM doesn't implement it)
      Object.defineProperty(input, "scrollHeight", {
        configurable: true,
        get: () => 100,
      });

      await userEvent.type(
        input,
        "Line 1{Shift>}{Enter}{/Shift}Line 2{Shift>}{Enter}{/Shift}Line 3",
      );

      // Height should be set based on scrollHeight (capped at 200px)
      expect(input.style.height).toBe("100px");
    });
  });

  describe("Accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <ChatInput onSend={() => {}} ariaLabel="Message input" />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when disabled", async () => {
      const { container } = render(
        <ChatInput onSend={() => {}} ariaLabel="Message input" disabled />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when loading", async () => {
      const { container } = render(
        <ChatInput onSend={() => {}} ariaLabel="Message input" isLoading />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible label", () => {
      render(<ChatInput onSend={() => {}} ariaLabel="Message input" />);
      expect(screen.getByLabelText("Message input")).toBeInTheDocument();
    });

    it("should focus input on mount when autoFocus is true", () => {
      render(<ChatInput onSend={() => {}} autoFocus />);
      expect(screen.getByRole("textbox")).toHaveFocus();
    });
  });
});
