/**
 * ChatMessages Integration Tests
 *
 * Tests for message actions and LLM thinking trace.
 * Split from ChatMessages.test.tsx for memory optimization.
 *
 * Related test files:
 * - ChatMessages.test.tsx - Basic display, streaming, accessibility
 * - ChatMessages.artifacts.test.tsx - Code blocks, diagrams, charts
 * - ChatMessages.agent.test.tsx - AI suggestions, agent execution trace
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ChatMessages } from "./ChatMessages";

describe("ChatMessages Integration", () => {
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
      const actionTriggers = screen.getAllByTestId("message-actions-trigger");
      expect(actionTriggers.length).toBe(2);
    });

    it("should call onEditMessage when edit action is clicked on user message", async () => {
      render(
        <ChatMessages
          messages={mockMessages}
          onEditMessage={mockOnEdit}
          onDeleteMessage={mockOnDelete}
        />,
      );

      const actionTriggers = screen.getAllByTestId("message-actions-trigger");
      fireEvent.click(actionTriggers[0]);

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

      const actionTriggers = screen.getAllByTestId("message-actions-trigger");
      fireEvent.click(actionTriggers[1]);

      const regenerateButton = screen.getByTestId("action-regenerate");
      fireEvent.click(regenerateButton);

      expect(mockOnRegenerate).toHaveBeenCalledWith("msg-2");
    });

    it("should call onDeleteMessage when delete action is confirmed", async () => {
      render(
        <ChatMessages messages={mockMessages} onDeleteMessage={mockOnDelete} />,
      );

      const actionTriggers = screen.getAllByTestId("message-actions-trigger");
      fireEvent.click(actionTriggers[0]);

      const deleteButton = screen.getByTestId("action-delete");
      fireEvent.click(deleteButton);

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

      fireEvent.click(actionTriggers[0]);
      expect(screen.queryByTestId("action-edit")).toBeInTheDocument();
      expect(screen.queryByTestId("action-regenerate")).not.toBeInTheDocument();

      fireEvent.click(actionTriggers[0]);

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

      fireEvent.click(actionTriggers[0]);
      expect(screen.queryByTestId("action-regenerate")).not.toBeInTheDocument();

      fireEvent.click(actionTriggers[0]);

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
          streamingContent="Some content"
          llmThinkingContent="Thinking..."
          isThinkingExpanded={false}
          onToggleThinking={mockOnToggleThinking}
        />,
      );

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

      expect(screen.getByTestId("llm-thinking-trace")).toBeInTheDocument();
      expect(screen.getByText("Here is my response...")).toBeInTheDocument();
    });
  });
});
