/**
 * ChatMessages Tests
 *
 * Tests for the chat messages list component with streaming
 * response display and empty state.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
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
      // Traverse up to find the flex container with justify-end
      // Structure: flex container > message bubble > prose > p > text
      const flexContainer = userMessage.closest(".flex");
      expect(flexContainer?.className).toContain("justify-end");
    });

    it("should render assistant message with correct styling", () => {
      render(<ChatMessages messages={mockMessages} />);
      const assistantMessage = screen.getByText("I am doing well, thank you!");
      // Traverse up to find the flex container with justify-start
      // Structure: flex container > message bubble > prose > p > text
      const flexContainer = assistantMessage.closest(".flex");
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

    it("should show thinking indicator when streaming with no content", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent=""
        />,
      );
      expect(screen.getByText(/thinking/i)).toBeInTheDocument();
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
      expect(screen.getByText(/thinking/i)).toBeInTheDocument();
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
      // Should only see one thinking indicator (from streaming), not two
      const thinkingElements = screen.queryAllByText(/thinking/i);
      expect(thinkingElements.length).toBeLessThanOrEqual(1);
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
  });

  describe("Source Citations", () => {
    const messagesWithSources = [
      {
        id: "msg-1",
        role: "user" as const,
        content: "What is LangGraph?",
        timestamp: Date.now() - 60000,
      },
      {
        id: "msg-2",
        role: "assistant" as const,
        content: "LangGraph is a framework for building stateful agents.",
        timestamp: Date.now() - 30000,
        sources: [
          {
            title: "LangGraph Documentation",
            url: "https://langchain-ai.github.io/langgraph",
          },
          {
            title: "LangChain Blog",
            url: "https://blog.langchain.dev/langgraph",
          },
        ],
      },
    ];

    it("should display sources section when assistant message has sources", () => {
      render(<ChatMessages messages={messagesWithSources} />);
      expect(screen.getByText("Sources:")).toBeInTheDocument();
    });

    it("should render source links", () => {
      render(<ChatMessages messages={messagesWithSources} />);
      expect(screen.getByText("LangGraph Documentation")).toBeInTheDocument();
      expect(screen.getByText("LangChain Blog")).toBeInTheDocument();
    });

    it("should have correct href on source links", () => {
      render(<ChatMessages messages={messagesWithSources} />);
      const docLink = screen.getByText("LangGraph Documentation");
      expect(docLink).toHaveAttribute(
        "href",
        "https://langchain-ai.github.io/langgraph",
      );
    });

    it("should open links in new tab", () => {
      render(<ChatMessages messages={messagesWithSources} />);
      const docLink = screen.getByText("LangGraph Documentation");
      expect(docLink).toHaveAttribute("target", "_blank");
      expect(docLink).toHaveAttribute("rel", "noopener noreferrer");
    });

    it("should not show sources for user messages", () => {
      const userWithSources = [
        {
          id: "msg-1",
          role: "user" as const,
          content: "Hello",
          timestamp: Date.now(),
          sources: [{ title: "Test", url: "https://test.com" }],
        },
      ];
      render(<ChatMessages messages={userWithSources} />);
      expect(screen.queryByText("Sources:")).not.toBeInTheDocument();
    });

    it("should not show sources section when sources array is empty", () => {
      const noSources = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content: "Response without sources",
          timestamp: Date.now(),
          sources: [],
        },
      ];
      render(<ChatMessages messages={noSources} />);
      expect(screen.queryByText("Sources:")).not.toBeInTheDocument();
    });
  });
});
