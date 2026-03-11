/**
 * MessageBubble Tests - Phase 2
 *
 * Tests for individual chat message bubbles with user/assistant styling.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  waitFor,
} from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import { MessageBubble } from "./MessageBubble";
import type { ChatMessage } from "../types";

import { TestProvider } from "@/test-utils";

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

const messageWithThinking: ChatMessage = {
  id: "msg-4",
  role: "assistant",
  content: "The answer is 42.",
  timestamp: Date.parse("2024-01-01T12:03:00Z"),
  thinkingContent:
    "Let me think about this step by step...\n1. First consideration\n2. Second consideration",
  thinkingTokens: 150,
  modelName: "claude-opus-4-5-20251101",
};

const messageWithoutThinking: ChatMessage = {
  id: "msg-5",
  role: "assistant",
  content: "Hello!",
  timestamp: Date.parse("2024-01-01T12:04:00Z"),
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
      render(
        <TestProvider>
          <MessageBubble message={userMessage} />
        </TestProvider>,
      );
      expect(screen.getByTestId("message-bubble")).toBeInTheDocument();
    });

    it("should display message content", () => {
      render(
        <TestProvider>
          <MessageBubble message={userMessage} />
        </TestProvider>,
      );
      expect(screen.getByText("Hello, can you help me?")).toBeInTheDocument();
    });

    it("should show timestamp when showTimestamp is true", () => {
      render(
        <TestProvider>
          <MessageBubble message={userMessage} showTimestamp />
        </TestProvider>,
      );
      expect(screen.getByTestId("message-timestamp")).toBeInTheDocument();
    });

    it("should hide timestamp by default", () => {
      render(
        <TestProvider>
          <MessageBubble message={userMessage} />
        </TestProvider>,
      );
      expect(screen.queryByTestId("message-timestamp")).not.toBeInTheDocument();
    });
  });

  describe("User Messages", () => {
    it("should apply user styling for user messages", () => {
      render(
        <TestProvider>
          <MessageBubble message={userMessage} />
        </TestProvider>,
      );
      const bubble = screen.getByTestId("message-bubble");
      expect(bubble).toHaveClass("user");
    });

    it("should show user avatar for user messages", () => {
      render(
        <TestProvider>
          <MessageBubble message={userMessage} />
        </TestProvider>,
      );
      expect(screen.getByTestId("user-avatar")).toBeInTheDocument();
    });

    it("should align user messages to the right", () => {
      render(
        <TestProvider>
          <MessageBubble message={userMessage} />
        </TestProvider>,
      );
      const container = screen.getByTestId("message-container");
      expect(container).toHaveClass("justify-end");
    });
  });

  describe("Assistant Messages", () => {
    it("should apply assistant styling for assistant messages", () => {
      render(
        <TestProvider>
          <MessageBubble message={assistantMessage} />
        </TestProvider>,
      );
      const bubble = screen.getByTestId("message-bubble");
      expect(bubble).toHaveClass("assistant");
    });

    it("should show AI avatar for assistant messages", () => {
      render(
        <TestProvider>
          <MessageBubble message={assistantMessage} />
        </TestProvider>,
      );
      expect(screen.getByTestId("ai-avatar")).toBeInTheDocument();
    });

    it("should align assistant messages to the left", () => {
      render(
        <TestProvider>
          <MessageBubble message={assistantMessage} />
        </TestProvider>,
      );
      const container = screen.getByTestId("message-container");
      expect(container).toHaveClass("justify-start");
    });
  });

  describe("Code Blocks", () => {
    it("should render code blocks with syntax highlighting", () => {
      render(
        <TestProvider>
          <MessageBubble message={messageWithCode} />
        </TestProvider>,
      );
      expect(screen.getByTestId("code-block")).toBeInTheDocument();
    });

    it("should show copy button for code blocks", () => {
      render(
        <TestProvider>
          <MessageBubble message={messageWithCode} />
        </TestProvider>,
      );
      expect(screen.getByTestId("copy-code-button")).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should show copy button on hover", () => {
      render(
        <TestProvider>
          <MessageBubble message={userMessage} />
        </TestProvider>,
      );
      const bubble = screen.getByTestId("message-bubble");
      fireEvent.mouseEnter(bubble);
      expect(screen.getByTestId("copy-message-button")).toBeInTheDocument();
    });

    it("should call onCopy when copy button clicked", async () => {
      const onCopy = vi.fn();
      render(
        <TestProvider>
          <MessageBubble message={userMessage} onCopy={onCopy} />
        </TestProvider>,
      );

      const bubble = screen.getByTestId("message-bubble");
      fireEvent.mouseEnter(bubble);
      fireEvent.click(screen.getByTestId("copy-message-button"));

      expect(onCopy).toHaveBeenCalledWith(userMessage);
    });
  });

  describe("Loading State", () => {
    it("should show typing indicator when isTyping is true", () => {
      render(
        <TestProvider>
          <MessageBubble message={assistantMessage} isTyping />
        </TestProvider>,
      );
      expect(screen.getByTestId("typing-indicator")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible role for messages", () => {
      render(
        <TestProvider>
          <MessageBubble message={userMessage} />
        </TestProvider>,
      );
      expect(screen.getByRole("article")).toBeInTheDocument();
    });

    it("should have aria-label for message role", () => {
      render(
        <TestProvider>
          <MessageBubble message={assistantMessage} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("article", { name: /assistant message/i }),
      ).toBeInTheDocument();
    });

    it("should have no accessibility violations for user message", async () => {
      const { container } = render(
        <TestProvider>
          <MessageBubble message={userMessage} />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations for assistant message", async () => {
      const { container } = render(
        <TestProvider>
          <MessageBubble message={assistantMessage} />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("Thinking Trace", () => {
    // LLMThinkingTrace is lazy-loaded, so all queries must use waitFor

    it("should render thinking trace when message has thinkingContent", async () => {
      render(
        <TestProvider>
          <MessageBubble message={messageWithThinking} />
        </TestProvider>,
      );
      await waitFor(() => {
        expect(screen.getByTestId("llm-thinking-trace")).toBeInTheDocument();
      });
    });

    it("should not render thinking trace when message has no thinkingContent", async () => {
      render(
        <TestProvider>
          <MessageBubble message={messageWithoutThinking} />
        </TestProvider>,
      );
      // Wait a tick for lazy loading to settle, then check absence
      await waitFor(() => {
        expect(
          screen.queryByTestId("llm-thinking-trace"),
        ).not.toBeInTheDocument();
      });
    });

    it("should render thinking trace collapsed by default for historical messages", async () => {
      render(
        <TestProvider>
          <MessageBubble message={messageWithThinking} />
        </TestProvider>,
      );
      // Wait for lazy component to load
      await waitFor(() => {
        expect(screen.getByTestId("llm-thinking-trace")).toBeInTheDocument();
      });
      // The thinking content should not be visible (collapsed)
      expect(screen.queryByTestId("thinking-content")).not.toBeInTheDocument();
    });

    it("should expand thinking trace when toggle is clicked", async () => {
      render(
        <TestProvider>
          <MessageBubble message={messageWithThinking} />
        </TestProvider>,
      );
      // Wait for lazy component to load
      await waitFor(() => {
        expect(screen.getByTestId("llm-thinking-trace")).toBeInTheDocument();
      });
      const toggleButton = screen.getByLabelText(/toggle thinking/i);
      fireEvent.click(toggleButton);
      expect(screen.getByTestId("thinking-content")).toBeInTheDocument();
    });

    it("should display thinking tokens when provided", async () => {
      render(
        <TestProvider>
          <MessageBubble message={messageWithThinking} />
        </TestProvider>,
      );
      // Wait for lazy component to load
      await waitFor(() => {
        // Token count should be visible in header even when collapsed
        expect(screen.getByText(/150 tokens/i)).toBeInTheDocument();
      });
    });

    it("should not render thinking trace for user messages even if thinkingContent exists", async () => {
      const userMsgWithThinking: ChatMessage = {
        ...userMessage,
        thinkingContent: "Some thinking",
      };
      render(
        <TestProvider>
          <MessageBubble message={userMsgWithThinking} />
        </TestProvider>,
      );
      await waitFor(() => {
        expect(
          screen.queryByTestId("llm-thinking-trace"),
        ).not.toBeInTheDocument();
      });
    });
  });
});
