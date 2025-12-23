/**
 * MessageBubble Tests - Phase 2
 *
 * Tests for individual chat message bubbles with user/assistant styling.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import { MessageBubble } from "./MessageBubble";
import type { ChatMessage } from "../types";

// =============================================================================
// Test Data
// =============================================================================

// Using canonical ChatMessage type from types/session.ts (timestamp: number)
const userMessage: ChatMessage = {
  id: "msg-1",
  role: "user",
  content: "Hello, can you help me?",
  timestamp: Date.parse("2024-01-01T12:00:00Z"), // 1704110400000
};

const assistantMessage: ChatMessage = {
  id: "msg-2",
  role: "assistant",
  content: "Of course! How can I assist you today?",
  timestamp: Date.parse("2024-01-01T12:01:00Z"), // 1704110460000
};

const messageWithCode: ChatMessage = {
  id: "msg-3",
  role: "assistant",
  content: "Here's an example:\n```javascript\nconsole.log('hello');\n```",
  timestamp: Date.parse("2024-01-01T12:02:00Z"), // 1704110520000
};

// =============================================================================
// Tests
// =============================================================================

describe("MessageBubble", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render message container", () => {
      render(<MessageBubble message={userMessage} />);
      expect(screen.getByTestId("message-bubble")).toBeInTheDocument();
    });

    it("should display message content", () => {
      render(<MessageBubble message={userMessage} />);
      expect(screen.getByText("Hello, can you help me?")).toBeInTheDocument();
    });

    it("should show timestamp when showTimestamp is true", () => {
      render(<MessageBubble message={userMessage} showTimestamp />);
      expect(screen.getByTestId("message-timestamp")).toBeInTheDocument();
    });

    it("should hide timestamp by default", () => {
      render(<MessageBubble message={userMessage} />);
      expect(screen.queryByTestId("message-timestamp")).not.toBeInTheDocument();
    });
  });

  describe("User Messages", () => {
    it("should apply user styling for user messages", () => {
      render(<MessageBubble message={userMessage} />);
      const bubble = screen.getByTestId("message-bubble");
      expect(bubble).toHaveClass("user");
    });

    it("should show user avatar for user messages", () => {
      render(<MessageBubble message={userMessage} />);
      expect(screen.getByTestId("user-avatar")).toBeInTheDocument();
    });

    it("should align user messages to the right", () => {
      render(<MessageBubble message={userMessage} />);
      const container = screen.getByTestId("message-container");
      expect(container).toHaveClass("justify-end");
    });
  });

  describe("Assistant Messages", () => {
    it("should apply assistant styling for assistant messages", () => {
      render(<MessageBubble message={assistantMessage} />);
      const bubble = screen.getByTestId("message-bubble");
      expect(bubble).toHaveClass("assistant");
    });

    it("should show AI avatar for assistant messages", () => {
      render(<MessageBubble message={assistantMessage} />);
      expect(screen.getByTestId("ai-avatar")).toBeInTheDocument();
    });

    it("should align assistant messages to the left", () => {
      render(<MessageBubble message={assistantMessage} />);
      const container = screen.getByTestId("message-container");
      expect(container).toHaveClass("justify-start");
    });
  });

  describe("Code Blocks", () => {
    it("should render code blocks with syntax highlighting", () => {
      render(<MessageBubble message={messageWithCode} />);
      expect(screen.getByTestId("code-block")).toBeInTheDocument();
    });

    it("should show copy button for code blocks", () => {
      render(<MessageBubble message={messageWithCode} />);
      expect(screen.getByTestId("copy-code-button")).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should show copy button on hover", () => {
      render(<MessageBubble message={userMessage} />);
      const bubble = screen.getByTestId("message-bubble");
      fireEvent.mouseEnter(bubble);
      expect(screen.getByTestId("copy-message-button")).toBeInTheDocument();
    });

    it("should call onCopy when copy button clicked", async () => {
      const onCopy = vi.fn();
      render(<MessageBubble message={userMessage} onCopy={onCopy} />);

      const bubble = screen.getByTestId("message-bubble");
      fireEvent.mouseEnter(bubble);
      fireEvent.click(screen.getByTestId("copy-message-button"));

      expect(onCopy).toHaveBeenCalledWith(userMessage);
    });
  });

  describe("Loading State", () => {
    it("should show typing indicator when isTyping is true", () => {
      render(<MessageBubble message={assistantMessage} isTyping />);
      expect(screen.getByTestId("typing-indicator")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible role for messages", () => {
      render(<MessageBubble message={userMessage} />);
      expect(screen.getByRole("article")).toBeInTheDocument();
    });

    it("should have aria-label for message role", () => {
      render(<MessageBubble message={assistantMessage} />);
      expect(
        screen.getByRole("article", { name: /assistant message/i }),
      ).toBeInTheDocument();
    });

    it("should have no accessibility violations for user message", async () => {
      const { container } = render(<MessageBubble message={userMessage} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations for assistant message", async () => {
      const { container } = render(
        <MessageBubble message={assistantMessage} />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
