/**
 * ChatMessages AI Follow-Up Suggestions Tests
 *
 * Tests for AI-powered follow-up suggestions.
 * Split from ChatMessages.agent.test.tsx for memory optimization.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ChatMessages } from "./ChatMessages";

import { TestProvider } from "@/test-utils";

describe("ChatMessages AI Suggestions", () => {
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
        <TestProvider>
          <ChatMessages
            messages={mockMessages}
            suggestions={mockSuggestions}
            onSuggestionSelect={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("follow-up-suggestions")).toBeInTheDocument();
      expect(screen.getByText("Tell me more about this")).toBeInTheDocument();
      expect(
        screen.getByText("Can you provide an example?"),
      ).toBeInTheDocument();
    });

    it("should not render suggestions when array is empty", () => {
      render(
        <TestProvider>
          <ChatMessages
            messages={mockMessages}
            suggestions={[]}
            onSuggestionSelect={vi.fn()}
          />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should not render suggestions when not provided", () => {
      render(
        <TestProvider>
          <ChatMessages messages={mockMessages} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should call onSuggestionSelect when a suggestion is clicked", () => {
      const mockOnSelect = vi.fn();
      render(
        <TestProvider>
          <ChatMessages
            messages={mockMessages}
            suggestions={mockSuggestions}
            onSuggestionSelect={mockOnSelect}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Tell me more about this"));
      expect(mockOnSelect).toHaveBeenCalledWith(mockSuggestions[0]);
    });

    it("should show loading state when suggestionsLoading is true", () => {
      render(
        <TestProvider>
          <ChatMessages
            messages={mockMessages}
            suggestions={[]}
            onSuggestionSelect={vi.fn()}
            suggestionsLoading={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("suggestions-loading")).toBeInTheDocument();
    });

    it("should not show suggestions while streaming", () => {
      render(
        <TestProvider>
          <ChatMessages
            messages={mockMessages}
            isStreaming={true}
            streamingContent="Generating..."
            suggestions={mockSuggestions}
            onSuggestionSelect={vi.fn()}
          />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should render suggestions after the last assistant message", () => {
      render(
        <TestProvider>
          <ChatMessages
            messages={mockMessages}
            suggestions={mockSuggestions}
            onSuggestionSelect={vi.fn()}
          />
        </TestProvider>,
      );

      const messagesEnd = screen.getByTestId("messages-end");
      const suggestions = screen.getByTestId("follow-up-suggestions");

      expect(suggestions.compareDocumentPosition(messagesEnd)).toBe(
        Node.DOCUMENT_POSITION_FOLLOWING,
      );
    });
  });
});
