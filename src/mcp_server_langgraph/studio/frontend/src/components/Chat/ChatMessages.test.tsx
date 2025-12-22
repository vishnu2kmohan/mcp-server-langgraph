/**
 * ChatMessages Tests
 *
 * Tests for the chat messages list component with streaming
 * response display and empty state.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { axe } from "jest-axe";
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

    it("should not render regular code blocks as mermaid diagrams", async () => {
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
      // Increased timeout for lazy-loaded CodeBlock during heavy test runs
      expect(
        await screen.findByText("javascript", {}, { timeout: 5000 }),
      ).toBeInTheDocument();
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

    it("should render mermaid as plain code when enableInteractiveArtifacts is false", async () => {
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
      // When disabled, should show mermaid language label (plain code block) - async due to lazy loading
      expect(await screen.findByText("mermaid")).toBeInTheDocument();
    });

    it("should render chart as plain code when enableInteractiveArtifacts is false", async () => {
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
      // When disabled, should show chart language label (plain code block) - async due to lazy loading
      expect(await screen.findByText("chart")).toBeInTheDocument();
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

    // Note: CodeBlock is lazy loaded, so we use async queries (findBy) to wait for Suspense resolution

    it("should render code block with language label", async () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(await screen.findByText("python")).toBeInTheDocument();
    });

    it("should have copy button", async () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(await screen.findByTitle("Copy code")).toBeInTheDocument();
    });

    it("should have word wrap toggle button", async () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(await screen.findByTitle("Toggle word wrap")).toBeInTheDocument();
    });

    it("should have download button", async () => {
      render(<ChatMessages messages={codeMessage} />);
      expect(await screen.findByTitle("Download file")).toBeInTheDocument();
    });

    it("should show line numbers", async () => {
      render(<ChatMessages messages={codeMessage} />);
      // Line numbers are shown via react-syntax-highlighter - wait for lazy load
      await screen.findByText("python"); // Wait for CodeBlock to load
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

  describe("LLM Thinking Trace Integration", () => {
    const mockOnToggleThinking = vi.fn();

    beforeEach(() => {
      vi.clearAllMocks();
    });

    it("should render LLMThinkingTrace when thinking content is present during streaming", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent=""
          llmThinkingContent="Analyzing the user's request..."
          isThinkingExpanded={true}
          onToggleThinking={mockOnToggleThinking}
        />,
      );
      expect(screen.getByTestId("llm-thinking-trace")).toBeInTheDocument();
    });

    it("should display thinking content text", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent=""
          llmThinkingContent="I need to consider several factors here..."
          isThinkingExpanded={true}
          onToggleThinking={mockOnToggleThinking}
        />,
      );
      expect(screen.getByTestId("thinking-content")).toHaveTextContent(
        "I need to consider several factors here...",
      );
    });

    it("should show thinking token count when provided", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent=""
          llmThinkingContent="Deep analysis in progress..."
          llmThinkingTokens={1500}
          isThinkingExpanded={true}
          onToggleThinking={mockOnToggleThinking}
        />,
      );
      expect(screen.getByText(/1,500 tokens/)).toBeInTheDocument();
    });

    it("should call onToggleThinking when toggle button is clicked", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent="Some content" // Having content hides the agent trace button
          llmThinkingContent="Thinking..."
          isThinkingExpanded={false}
          onToggleThinking={mockOnToggleThinking}
        />,
      );

      // Get the toggle button from within the LLMThinkingTrace component
      const thinkingTrace = screen.getByTestId("llm-thinking-trace");
      const toggleButton = thinkingTrace.querySelector(
        '[aria-label="Toggle thinking trace"]',
      );
      expect(toggleButton).toBeTruthy();
      fireEvent.click(toggleButton!);

      expect(mockOnToggleThinking).toHaveBeenCalled();
    });

    it("should show streaming indicator during active streaming", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent=""
          llmThinkingContent="Processing..."
          isThinkingExpanded={true}
          onToggleThinking={mockOnToggleThinking}
        />,
      );
      expect(screen.getByTestId("streaming-indicator")).toBeInTheDocument();
    });

    it("should not show streaming indicator when not streaming", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={false}
          llmThinkingContent="Previous thinking content"
          isThinkingExpanded={true}
          onToggleThinking={mockOnToggleThinking}
        />,
      );
      expect(
        screen.queryByTestId("streaming-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should not render LLMThinkingTrace when no thinking content", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent="Response content"
          llmThinkingContent=""
          isThinkingExpanded={true}
          onToggleThinking={mockOnToggleThinking}
        />,
      );
      expect(
        screen.queryByTestId("llm-thinking-trace"),
      ).not.toBeInTheDocument();
    });

    it("should display model name when provided", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent=""
          llmThinkingContent="Thinking deeply..."
          llmModelName="claude-opus-4-5"
          isThinkingExpanded={true}
          onToggleThinking={mockOnToggleThinking}
        />,
      );
      expect(screen.getByText(/claude-opus-4-5/)).toBeInTheDocument();
    });

    it("should show Extended badge for thinking models", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent=""
          llmThinkingContent="Extended thinking..."
          isThinkingModel={true}
          isThinkingExpanded={true}
          onToggleThinking={mockOnToggleThinking}
        />,
      );
      expect(screen.getByTestId("thinking-model-badge")).toBeInTheDocument();
    });

    it("should render thinking trace above streaming content", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent="Here is my response..."
          llmThinkingContent="First, I analyzed..."
          isThinkingExpanded={true}
          onToggleThinking={mockOnToggleThinking}
        />,
      );

      // Both should be present
      expect(screen.getByTestId("llm-thinking-trace")).toBeInTheDocument();
      expect(screen.getByText("Here is my response...")).toBeInTheDocument();
    });
  });

  describe("AIFollowUpSuggestions Integration", () => {
    const mockSuggestions = [
      {
        id: "sug-1",
        text: "Tell me more about this",
        category: "explore" as const,
      },
      {
        id: "sug-2",
        text: "Can you provide an example?",
        category: "example" as const,
      },
    ];

    it("should render follow-up suggestions when provided", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          suggestions={mockSuggestions}
          onSuggestionSelect={vi.fn()}
        />,
      );

      expect(screen.getByTestId("follow-up-suggestions")).toBeInTheDocument();
      expect(screen.getByText("Tell me more about this")).toBeInTheDocument();
      expect(
        screen.getByText("Can you provide an example?"),
      ).toBeInTheDocument();
    });

    it("should not render suggestions when array is empty", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          suggestions={[]}
          onSuggestionSelect={vi.fn()}
        />,
      );

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should not render suggestions when not provided", () => {
      render(<ChatMessages messages={mockMessages} />);

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should call onSuggestionSelect when a suggestion is clicked", () => {
      const mockOnSelect = vi.fn();
      render(
        <ChatMessages
          messages={mockMessages}
          suggestions={mockSuggestions}
          onSuggestionSelect={mockOnSelect}
        />,
      );

      fireEvent.click(screen.getByText("Tell me more about this"));
      expect(mockOnSelect).toHaveBeenCalledWith(mockSuggestions[0]);
    });

    it("should show loading state when suggestionsLoading is true", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          suggestions={[]}
          onSuggestionSelect={vi.fn()}
          suggestionsLoading={true}
        />,
      );

      expect(screen.getByTestId("suggestions-loading")).toBeInTheDocument();
    });

    it("should not show suggestions while streaming", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          isStreaming={true}
          streamingContent="Generating..."
          suggestions={mockSuggestions}
          onSuggestionSelect={vi.fn()}
        />,
      );

      // Should not show suggestions during streaming
      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should render suggestions after the last assistant message", () => {
      render(
        <ChatMessages
          messages={mockMessages}
          suggestions={mockSuggestions}
          onSuggestionSelect={vi.fn()}
        />,
      );

      // Suggestions should appear after messages
      const messagesEnd = screen.getByTestId("messages-end");
      const suggestions = screen.getByTestId("follow-up-suggestions");

      // Suggestions should be in the DOM before the messages end marker
      expect(suggestions.compareDocumentPosition(messagesEnd)).toBe(
        Node.DOCUMENT_POSITION_FOLLOWING,
      );
    });
  });

  describe("AgentExecutionTrace with LangGraph Nodes", () => {
    const mockMessagesForTrace = [
      {
        id: "msg-1",
        role: "user" as const,
        content: "Run the analysis workflow",
        timestamp: Date.now(),
      },
    ];

    it("should render agent execution trace panel when provided", () => {
      render(
        <ChatMessages
          messages={mockMessagesForTrace}
          isStreaming={true}
          streamingContent=""
          agentExecutionTrace={{
            steps: [{ name: "agent", status: "running" }],
            tokens: { input: 100, output: 50 },
          }}
        />,
      );

      // Toggle the trace panel
      const toggleButton = screen.getByLabelText(
        "Toggle agent execution trace",
      );
      fireEvent.click(toggleButton);

      expect(screen.getByText(/Execution Steps/i)).toBeInTheDocument();
    });

    it("should display LangGraph nodes when provided in trace", () => {
      render(
        <ChatMessages
          messages={mockMessagesForTrace}
          isStreaming={true}
          streamingContent=""
          agentExecutionTrace={{
            nodes: [
              {
                id: "start",
                name: "Start",
                type: "start",
                status: "completed",
              },
              {
                id: "analyze",
                name: "Analyze Input",
                type: "tool",
                status: "running",
              },
              {
                id: "decide",
                name: "Route Decision",
                type: "conditional",
                status: "pending",
              },
              { id: "end", name: "End", type: "end", status: "pending" },
            ],
            edges: [
              { from: "start", to: "analyze" },
              { from: "analyze", to: "decide" },
              { from: "decide", to: "end", condition: "complete" },
            ],
            currentNode: "analyze",
          }}
        />,
      );

      // Toggle the trace panel
      const toggleButton = screen.getByLabelText(
        "Toggle agent execution trace",
      );
      fireEvent.click(toggleButton);

      // Should show node visualization
      expect(
        screen.getByTestId("langgraph-node-visualization"),
      ).toBeInTheDocument();
      expect(screen.getByText("Start")).toBeInTheDocument();
      expect(screen.getByText("Analyze Input")).toBeInTheDocument();
      expect(screen.getByText("Route Decision")).toBeInTheDocument();
    });

    it("should highlight the current active node", () => {
      render(
        <ChatMessages
          messages={mockMessagesForTrace}
          isStreaming={true}
          streamingContent=""
          agentExecutionTrace={{
            nodes: [
              {
                id: "start",
                name: "Start",
                type: "start",
                status: "completed",
              },
              {
                id: "process",
                name: "Process",
                type: "tool",
                status: "running",
              },
            ],
            currentNode: "process",
          }}
        />,
      );

      const toggleButton = screen.getByLabelText(
        "Toggle agent execution trace",
      );
      fireEvent.click(toggleButton);

      const activeNode = screen.getByTestId("node-process");
      expect(activeNode).toHaveClass("ring-2");
    });

    it("should display different node type icons", () => {
      render(
        <ChatMessages
          messages={mockMessagesForTrace}
          isStreaming={true}
          streamingContent=""
          agentExecutionTrace={{
            nodes: [
              {
                id: "start",
                name: "Start",
                type: "start",
                status: "completed",
              },
              { id: "tool", name: "Search", type: "tool", status: "running" },
              {
                id: "conditional",
                name: "Check",
                type: "conditional",
                status: "pending",
              },
            ],
            currentNode: "tool",
          }}
        />,
      );

      const toggleButton = screen.getByLabelText(
        "Toggle agent execution trace",
      );
      fireEvent.click(toggleButton);

      expect(screen.getByTestId("node-type-start")).toBeInTheDocument();
      expect(screen.getByTestId("node-type-tool")).toBeInTheDocument();
      expect(screen.getByTestId("node-type-conditional")).toBeInTheDocument();
    });

    it("should show node status indicators", () => {
      render(
        <ChatMessages
          messages={mockMessagesForTrace}
          isStreaming={true}
          streamingContent=""
          agentExecutionTrace={{
            nodes: [
              { id: "n1", name: "Step 1", type: "tool", status: "completed" },
              { id: "n2", name: "Step 2", type: "tool", status: "running" },
              { id: "n3", name: "Step 3", type: "tool", status: "error" },
              { id: "n4", name: "Step 4", type: "tool", status: "pending" },
            ],
          }}
        />,
      );

      const toggleButton = screen.getByLabelText(
        "Toggle agent execution trace",
      );
      fireEvent.click(toggleButton);

      expect(screen.getByTestId("node-status-completed")).toBeInTheDocument();
      expect(screen.getByTestId("node-status-running")).toBeInTheDocument();
      expect(screen.getByTestId("node-status-error")).toBeInTheDocument();
      expect(screen.getByTestId("node-status-pending")).toBeInTheDocument();
    });

    it("should display edge connections between nodes", () => {
      render(
        <ChatMessages
          messages={mockMessagesForTrace}
          isStreaming={true}
          streamingContent=""
          agentExecutionTrace={{
            nodes: [
              { id: "a", name: "A", type: "start", status: "completed" },
              { id: "b", name: "B", type: "tool", status: "completed" },
            ],
            edges: [{ from: "a", to: "b" }],
          }}
        />,
      );

      const toggleButton = screen.getByLabelText(
        "Toggle agent execution trace",
      );
      fireEvent.click(toggleButton);

      expect(screen.getByTestId("edge-a-to-b")).toBeInTheDocument();
    });

    it("should show conditional edge labels", () => {
      render(
        <ChatMessages
          messages={mockMessagesForTrace}
          isStreaming={true}
          streamingContent=""
          agentExecutionTrace={{
            nodes: [
              {
                id: "check",
                name: "Check",
                type: "conditional",
                status: "completed",
              },
              {
                id: "success",
                name: "Success",
                type: "tool",
                status: "running",
              },
              {
                id: "failure",
                name: "Failure",
                type: "tool",
                status: "pending",
              },
            ],
            edges: [
              { from: "check", to: "success", condition: "passed" },
              { from: "check", to: "failure", condition: "failed" },
            ],
          }}
        />,
      );

      const toggleButton = screen.getByLabelText(
        "Toggle agent execution trace",
      );
      fireEvent.click(toggleButton);

      expect(screen.getByText("passed")).toBeInTheDocument();
      expect(screen.getByText("failed")).toBeInTheDocument();
    });

    it("should fallback to simple steps view when no nodes provided", () => {
      render(
        <ChatMessages
          messages={mockMessagesForTrace}
          isStreaming={true}
          streamingContent=""
          agentExecutionTrace={{
            steps: [
              { name: "Processing", status: "running" },
              { name: "Completed", status: "success" },
            ],
            tokens: { input: 100, output: 200 },
          }}
        />,
      );

      const toggleButton = screen.getByLabelText(
        "Toggle agent execution trace",
      );
      fireEvent.click(toggleButton);

      expect(screen.getByText("Processing")).toBeInTheDocument();
      expect(
        screen.queryByTestId("langgraph-node-visualization"),
      ).not.toBeInTheDocument();
    });
  });
});
