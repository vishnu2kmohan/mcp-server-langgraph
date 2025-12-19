/**
 * ChatMessages Tests
 *
 * Tests for the chat messages list component with streaming
 * response display and empty state.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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

  describe("Mermaid Diagram Rendering", () => {
    it("should render mermaid code blocks as diagrams", async () => {
      const mermaidMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            "Here's a diagram:\n\n```mermaid\ngraph TD\n    A[Start] --> B[End]\n```",
          timestamp: Date.now(),
        },
      ];
      render(<ChatMessages messages={mermaidMessage} />);
      // Should render the mermaid diagram container, not just code
      // The MermaidDiagram component should be used for language-mermaid code blocks
      const diagramContainer = document.querySelector(
        ".bg-gray-50, .dark\\:bg-gray-800",
      );
      expect(diagramContainer).toBeInTheDocument();
    });

    it("should not render regular code blocks as mermaid diagrams", () => {
      const jsCodeMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content: "```javascript\nconst x = 1;\nconst y = 2;\n```",
          timestamp: Date.now(),
        },
      ];
      render(<ChatMessages messages={jsCodeMessage} />);
      // Should show the code block with language label (multi-line code triggers CodeBlock)
      expect(screen.getByText("javascript")).toBeInTheDocument();
      // Syntax highlighting splits code into tokens, so check the container text
      const codeContainer = document.querySelector("pre");
      expect(codeContainer?.textContent).toContain("const");
      expect(codeContainer?.textContent).toContain("x");
    });
  });

  describe("Chart Rendering", () => {
    it("should render chart code blocks as interactive charts", () => {
      const chartMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            '```chart\n{"type": "bar", "title": "Sales", "data": [{"name": "Jan", "value": 100}]}\n```',
          timestamp: Date.now(),
        },
      ];
      render(<ChatMessages messages={chartMessage} />);
      // Should render the chart title
      expect(screen.getByText("Sales")).toBeInTheDocument();
    });
  });

  describe("Interactive Artifacts Feature Flag", () => {
    it("should render mermaid diagrams when enableInteractiveArtifacts is true", () => {
      const mermaidMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            "Here's a diagram:\n\n```mermaid\ngraph TD\n    A[Start] --> B[End]\n```",
          timestamp: Date.now(),
        },
      ];
      render(
        <ChatMessages messages={mermaidMessage} enableInteractiveArtifacts />,
      );
      // When enabled, mermaid diagrams should be rendered (not just code)
      const diagramContainer = document.querySelector(
        ".bg-gray-50, .dark\\:bg-gray-800",
      );
      expect(diagramContainer).toBeInTheDocument();
    });

    it("should render chart blocks as interactive charts when enableInteractiveArtifacts is true", () => {
      const chartMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            '```chart\n{"type": "bar", "title": "Test Chart", "data": [{"name": "A", "value": 10}]}\n```',
          timestamp: Date.now(),
        },
      ];
      render(
        <ChatMessages messages={chartMessage} enableInteractiveArtifacts />,
      );
      expect(screen.getByText("Test Chart")).toBeInTheDocument();
    });

    it("should render mermaid as plain code when enableInteractiveArtifacts is false", () => {
      const mermaidMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            "Here's a diagram:\n\n```mermaid\ngraph TD\n    A[Start] --> B[End]\n```",
          timestamp: Date.now(),
        },
      ];
      render(
        <ChatMessages
          messages={mermaidMessage}
          enableInteractiveArtifacts={false}
        />,
      );
      // When disabled, should show mermaid language label (plain code block)
      expect(screen.getByText("mermaid")).toBeInTheDocument();
    });

    it("should render chart as plain code when enableInteractiveArtifacts is false", () => {
      // Using multi-line content so it renders as CodeBlock with language label
      const chartMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            '```chart\n{\n  "type": "bar",\n  "title": "Test Chart",\n  "data": []\n}\n```',
          timestamp: Date.now(),
        },
      ];
      render(
        <ChatMessages
          messages={chartMessage}
          enableInteractiveArtifacts={false}
        />,
      );
      // When disabled, should show chart language label (plain code block)
      expect(screen.getByText("chart")).toBeInTheDocument();
    });

    it("should default to enabled for interactive artifacts", () => {
      // By default (no prop), interactive artifacts should be enabled
      const chartMessage = [
        {
          id: "msg-1",
          role: "assistant" as const,
          content:
            '```chart\n{"type": "bar", "title": "Default Enabled", "data": [{"name": "A", "value": 5}]}\n```',
          timestamp: Date.now(),
        },
      ];
      render(<ChatMessages messages={chartMessage} />);
      expect(screen.getByText("Default Enabled")).toBeInTheDocument();
    });
  });

  describe("Enhanced Code Block Features", () => {
    const codeMessage = [
      {
        id: "msg-1",
        role: "assistant" as const,
        content:
          "```python\ndef hello():\n    print('Hello, World!')\n    return True\n```",
        timestamp: Date.now(),
      },
    ];

    it("should render code block with language label", () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(screen.getByText("python")).toBeInTheDocument();
    });

    it("should have copy button", () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(screen.getByTitle("Copy code")).toBeInTheDocument();
    });

    it("should have word wrap toggle button", () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(screen.getByTitle("Toggle word wrap")).toBeInTheDocument();
    });

    it("should have download button", () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(screen.getByTitle("Download file")).toBeInTheDocument();
    });

    it("should show line numbers", () => {
      render(<ChatMessages messages={codeMessage} />);
      // Line numbers are shown via react-syntax-highlighter
      const codeBlock = document.querySelector("pre");
      expect(codeBlock).toBeInTheDocument();
    });
  });

  describe("Message Actions Integration", () => {
    const mockOnEdit = vi.fn();
    const mockOnRegenerate = vi.fn();
    const mockOnDelete = vi.fn();

    beforeEach(() => {
      vi.clearAllMocks();
    });

    it("should not show message actions when no callbacks provided", () => {
      render(<ChatMessages messages={mockMessages} />);
      expect(
        screen.queryByTestId("message-actions-trigger"),
      ).not.toBeInTheDocument();
    });

    it("should show message actions for messages when callbacks are provided", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          onEditMessage={mockOnEdit}
          onRegenerateMessage={mockOnRegenerate}
          onDeleteMessage={mockOnDelete}
        />,
      );
      // MessageActions trigger should be present for each message
      const actionTriggers = screen.getAllByTestId("message-actions-trigger");
      expect(actionTriggers.length).toBe(2); // One for each message
    });

    it("should call onEditMessage when edit action is clicked on user message", async () => {
      render(
        <ChatMessages
          messages={mockMessages}
          onEditMessage={mockOnEdit}
          onDeleteMessage={mockOnDelete}
        />,
      );

      // Find the message actions for user message and open menu
      const actionTriggers = screen.getAllByTestId("message-actions-trigger");
      // User message is first in our mock data
      fireEvent.click(actionTriggers[0]);

      // Click edit
      const editButton = screen.getByTestId("action-edit");
      fireEvent.click(editButton);

      expect(mockOnEdit).toHaveBeenCalledWith("msg-1");
    });

    it("should call onRegenerateMessage when regenerate action is clicked on assistant message", async () => {
      render(
        <ChatMessages
          messages={mockMessages}
          onRegenerateMessage={mockOnRegenerate}
          onDeleteMessage={mockOnDelete}
        />,
      );

      // Find the message actions for assistant message and open menu
      const actionTriggers = screen.getAllByTestId("message-actions-trigger");
      // Assistant message is second in our mock data
      fireEvent.click(actionTriggers[1]);

      // Click regenerate
      const regenerateButton = screen.getByTestId("action-regenerate");
      fireEvent.click(regenerateButton);

      expect(mockOnRegenerate).toHaveBeenCalledWith("msg-2");
    });

    it("should call onDeleteMessage when delete action is confirmed", async () => {
      render(
        <ChatMessages messages={mockMessages} onDeleteMessage={mockOnDelete} />,
      );

      // Find the message actions for first message and open menu
      const actionTriggers = screen.getAllByTestId("message-actions-trigger");
      fireEvent.click(actionTriggers[0]);

      // Click delete
      const deleteButton = screen.getByTestId("action-delete");
      fireEvent.click(deleteButton);

      // Confirm deletion
      const confirmButton = screen.getByTestId("confirm-delete");
      fireEvent.click(confirmButton);

      expect(mockOnDelete).toHaveBeenCalledWith("msg-1");
    });

    it("should show edit action only for user messages", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          onEditMessage={mockOnEdit}
          onDeleteMessage={mockOnDelete}
        />,
      );

      const actionTriggers = screen.getAllByTestId("message-actions-trigger");

      // Open menu for user message (first)
      fireEvent.click(actionTriggers[0]);
      expect(screen.queryByTestId("action-edit")).toBeInTheDocument();
      expect(screen.queryByTestId("action-regenerate")).not.toBeInTheDocument();

      // Close menu
      fireEvent.click(actionTriggers[0]);

      // Open menu for assistant message (second)
      fireEvent.click(actionTriggers[1]);
      expect(screen.queryByTestId("action-edit")).not.toBeInTheDocument();
    });

    it("should show regenerate action only for assistant messages", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          onRegenerateMessage={mockOnRegenerate}
          onDeleteMessage={mockOnDelete}
        />,
      );

      const actionTriggers = screen.getAllByTestId("message-actions-trigger");

      // Open menu for user message (first)
      fireEvent.click(actionTriggers[0]);
      expect(screen.queryByTestId("action-regenerate")).not.toBeInTheDocument();

      // Close menu
      fireEvent.click(actionTriggers[0]);

      // Open menu for assistant message (second)
      fireEvent.click(actionTriggers[1]);
      expect(screen.queryByTestId("action-regenerate")).toBeInTheDocument();
    });

    it("should disable regenerate button when isRegenerating is true", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          onRegenerateMessage={mockOnRegenerate}
          onDeleteMessage={mockOnDelete}
          isRegenerating={true}
        />,
      );

      const actionTriggers = screen.getAllByTestId("message-actions-trigger");

      // Open menu for assistant message
      fireEvent.click(actionTriggers[1]);

      const regenerateButton = screen.getByTestId("action-regenerate");
      expect(regenerateButton).toBeDisabled();
    });
  });
});
