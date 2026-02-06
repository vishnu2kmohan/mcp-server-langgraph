/**
 * ChatMessages Basic Tests
 *
 * =============================================================================
 * TEST ARCHITECTURE - ChatMessages Component Family
 * =============================================================================
 *
 * This file tests basic message display, streaming, and accessibility.
 * The ChatMessages tests are split across multiple files for memory optimization.
 *
 * TEST FILE FAMILY:
 * - ChatMessages.test.tsx (this file)     - Basic display, streaming, accessibility
 * - ChatMessages.artifacts.test.tsx       - Code blocks, diagrams, charts
 * - ChatMessages.integration.test.tsx     - Message actions, thinking trace
 * - ChatMessages.suggestions.test.tsx     - AI follow-up suggestions
 *
 * RELATED COMPONENT TESTS (dedicated test files for sub-components):
 * - AgentExecutionTracePanel.test.tsx (28 tests) - LangGraph visualization, trace AI
 * - MarkdownContent.test.tsx                     - Markdown rendering
 * - CodeBlock.test.tsx                           - Syntax highlighting
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { axe } from "jest-axe";

// Mock AIEmptyState to avoid Redux Provider requirement
vi.mock("../EmptyState/AIEmptyState", () => ({
  AIEmptyState: () => (
    <div data-testid="ai-empty-state">
      <p>No messages yet</p>
      <p>Start a conversation by typing a message below</p>
    </div>
  ),
}));

import { ChatMessages } from "./ChatMessages";

describe("ChatMessages", () => {
  const mockMessages = [
    {
      id: "msg-1",
      role: "user" as const,
      content: "Hello, how are you?",
      timestamp: Date.now() - 60000,
    },
    {
      id: "msg-2",
      role: "assistant" as const,
      content: "I am doing well, thank you!",
      timestamp: Date.now() - 30000,
    },
  ];

  // Cleanup after each test to prevent DOM leakage and state pollution
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("Message Display", () => {
    it("should render all messages", () => {
      render(<ChatMessages messages={mockMessages} />);
      expect(screen.getByText("Hello, how are you?")).toBeInTheDocument();
      expect(
        screen.getByText("I am doing well, thank you!"),
      ).toBeInTheDocument();
    });

    it("should render user message with correct styling", () => {
      render(<ChatMessages messages={mockMessages} />);
      const userMessage = screen.getByText("Hello, how are you?");
      // Traverse up to find the outer flex container with justify-end
      // Structure: group flex container > wrapper > message bubble > prose > p > text
      const flexContainer = userMessage.closest(".group");
      expect(flexContainer?.className).toContain("justify-end");
    });

    it("should render assistant message with correct styling", () => {
      render(<ChatMessages messages={mockMessages} />);
      const assistantMessage = screen.getByText("I am doing well, thank you!");
      // Traverse up to find the outer flex container with justify-start
      // Structure: group flex container > wrapper > message bubble > prose > p > text
      const flexContainer = assistantMessage.closest(".group");
      expect(flexContainer?.className).toContain("justify-start");
    });

    it("should display message timestamp", () => {
      render(<ChatMessages messages={mockMessages} />);
      // Timestamps are rendered for each message
      const timestamps = screen.getAllByText(/\d{1,2}:\d{2}/);
      expect(timestamps.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no messages", () => {
      render(<ChatMessages messages={[]} />);
      expect(screen.getByText(/no messages yet/i)).toBeInTheDocument();
    });

    it("should show prompt to start conversation", () => {
      render(<ChatMessages messages={[]} />);
      expect(screen.getByText(/start a conversation/i)).toBeInTheDocument();
    });
  });

  describe("Streaming Response", () => {
    it("should show streaming content when streaming", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent="This is streaming..."
        />,
      );
      expect(screen.getByText("This is streaming...")).toBeInTheDocument();
    });

    it("should show processing indicator when streaming with no content", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent=""
        />,
      );
      expect(screen.getByText(/processing/i)).toBeInTheDocument();
    });

    it("should show cursor animation when streaming", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent="Streaming text"
        />,
      );
      // Should have a pulsing cursor indicator
      const cursor = document.querySelector(".animate-pulse");
      expect(cursor).toBeInTheDocument();
    });
  });

  describe("Legacy Sending State", () => {
    it("should show sending indicator when isSending and not streaming", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isSending={true}
          isStreaming={false}
        />,
      );
      expect(screen.getByText(/processing/i)).toBeInTheDocument();
    });

    it("should not show sending indicator when streaming", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isSending={true}
          isStreaming={true}
          streamingContent="Response"
        />,
      );
      // Should only see one processing indicator (from streaming), not two
      const processingElements = screen.queryAllByText(/processing/i);
      expect(processingElements.length).toBeLessThanOrEqual(1);
    });
  });

  describe("Scroll Behavior", () => {
    it("should render messagesEndRef div for auto-scroll", () => {
      render(<ChatMessages messages={mockMessages} />);
      // The component should include a scroll anchor
      expect(
        document.querySelector('[data-testid="messages-end"]'),
      ).toBeInTheDocument();
    });
  });

  describe("Long Messages", () => {
    it("should render multiline message content via markdown", () => {
      const messagesWithWhitespace = [
        {
          id: "msg-1",
          role: "user" as const,
          content: "Line 1\n\nLine 2\nLine 3",
          timestamp: Date.now(),
        },
      ];
      render(<ChatMessages messages={messagesWithWhitespace} />);
      // MarkdownContent renders via prose classes which handle whitespace
      // The content is wrapped in prose container for proper markdown rendering
      const messageElement = screen.getByText(/Line 1/);
      const proseContainer = messageElement.closest(".prose");
      expect(proseContainer).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible message structure", () => {
      render(<ChatMessages messages={mockMessages} />);
      // Messages should be rendered as text content
      expect(screen.getByText("Hello, how are you?")).toBeInTheDocument();
    });

    it("should maintain message order", () => {
      render(<ChatMessages messages={mockMessages} />);
      const messageTexts = screen.getAllByText(/how are you|doing well/i);
      expect(messageTexts[0]).toHaveTextContent("Hello, how are you?");
      expect(messageTexts[1]).toHaveTextContent("I am doing well, thank you!");
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(<ChatMessages messages={mockMessages} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("Avatar Display (show_chat_avatars feature)", () => {
    it("should not render avatars by default", () => {
      render(<ChatMessages messages={mockMessages} />);

      expect(screen.queryByTestId("user-avatar")).not.toBeInTheDocument();
      expect(screen.queryByTestId("assistant-avatar")).not.toBeInTheDocument();
    });

    it("should render user avatar when showAvatars is true", () => {
      render(<ChatMessages messages={mockMessages} showAvatars={true} />);

      expect(screen.getByTestId("user-avatar")).toBeInTheDocument();
    });

    it("should render assistant avatar when showAvatars is true", () => {
      render(<ChatMessages messages={mockMessages} showAvatars={true} />);

      expect(screen.getByTestId("assistant-avatar")).toBeInTheDocument();
    });

    it("should display user initials in avatar when provided", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          showAvatars={true}
          userInitials="JD"
        />,
      );

      expect(screen.getByText("JD")).toBeInTheDocument();
    });

    it("should render bot icon for assistant avatar", () => {
      render(<ChatMessages messages={mockMessages} showAvatars={true} />);

      const assistantAvatar = screen.getByTestId("assistant-avatar");
      expect(assistantAvatar).toBeInTheDocument();
      // Avatar should contain bot icon (svg)
      expect(assistantAvatar.querySelector("svg")).toBeInTheDocument();
    });
  });
});
