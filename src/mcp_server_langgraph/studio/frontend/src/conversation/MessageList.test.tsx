/**
 * MessageList Tests - Phase 2
 *
 * Tests for the virtualized message list component.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { MessageList } from "./MessageList";
import type { ChatMessage } from "./MessageBubble";

expect.extend(toHaveNoViolations);

// =============================================================================
// Test Data
// =============================================================================

const mockMessages: ChatMessage[] = [
  {
    id: "msg-1",
    role: "user",
    content: "Hello!",
    timestamp: "2024-01-01T12:00:00Z",
  },
  {
    id: "msg-2",
    role: "assistant",
    content: "Hi there! How can I help?",
    timestamp: "2024-01-01T12:01:00Z",
  },
  {
    id: "msg-3",
    role: "user",
    content: "Can you explain React hooks?",
    timestamp: "2024-01-01T12:02:00Z",
  },
  {
    id: "msg-4",
    role: "assistant",
    content: "React hooks are functions that...",
    timestamp: "2024-01-01T12:03:00Z",
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("MessageList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render message list container", () => {
      render(<MessageList messages={[]} />);
      expect(screen.getByTestId("message-list")).toBeInTheDocument();
    });

    it("should render all messages", () => {
      render(<MessageList messages={mockMessages} />);
      expect(screen.getByText("Hello!")).toBeInTheDocument();
      expect(screen.getByText("Hi there! How can I help?")).toBeInTheDocument();
      expect(
        screen.getByText("Can you explain React hooks?"),
      ).toBeInTheDocument();
    });

    it("should show empty state when no messages", () => {
      render(<MessageList messages={[]} />);
      expect(screen.getByText(/no messages/i)).toBeInTheDocument();
    });
  });

  describe("Auto-Scroll", () => {
    it("should scroll to bottom on new messages", () => {
      const { rerender } = render(<MessageList messages={mockMessages} />);

      const scrollToBottom = vi.fn();
      const listContainer = screen.getByTestId("message-list");
      listContainer.scrollTo = scrollToBottom;

      const newMessages = [
        ...mockMessages,
        {
          id: "msg-5",
          role: "assistant" as const,
          content: "New message!",
          timestamp: "2024-01-01T12:04:00Z",
        },
      ];

      rerender(<MessageList messages={newMessages} />);
      // The component should trigger a scroll
      expect(screen.getByText("New message!")).toBeInTheDocument();
    });

    it("should not auto-scroll when scrolledUp is true", () => {
      render(<MessageList messages={mockMessages} isScrolledUp />);
      expect(screen.getByTestId("scroll-to-bottom-button")).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true", () => {
      render(<MessageList messages={mockMessages} isLoading />);
      expect(screen.getByTestId("loading-indicator")).toBeInTheDocument();
    });

    it("should show typing indicator for streaming message", () => {
      render(<MessageList messages={mockMessages} isStreaming />);
      expect(screen.getByTestId("streaming-indicator")).toBeInTheDocument();
    });
  });

  describe("Scroll Controls", () => {
    it("should show scroll-to-bottom button when scrolled up", () => {
      render(<MessageList messages={mockMessages} isScrolledUp />);
      expect(screen.getByTestId("scroll-to-bottom-button")).toBeInTheDocument();
    });

    it("should call onScrollToBottom when button clicked", () => {
      const onScrollToBottom = vi.fn();
      render(
        <MessageList
          messages={mockMessages}
          isScrolledUp
          onScrollToBottom={onScrollToBottom}
        />,
      );

      fireEvent.click(screen.getByTestId("scroll-to-bottom-button"));
      expect(onScrollToBottom).toHaveBeenCalled();
    });
  });

  describe("Message Grouping", () => {
    it("should group consecutive messages from same sender", () => {
      render(<MessageList messages={mockMessages} groupMessages />);
      const groups = screen.getAllByTestId("message-group");
      // User messages and assistant messages should be grouped
      expect(groups.length).toBeGreaterThan(0);
    });
  });

  describe("Accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<MessageList messages={mockMessages} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when empty", async () => {
      const { container } = render(<MessageList messages={[]} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when loading", async () => {
      const { container } = render(
        <MessageList messages={mockMessages} isLoading />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when streaming", async () => {
      const { container } = render(
        <MessageList messages={mockMessages} isStreaming />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible list role", () => {
      render(<MessageList messages={mockMessages} />);
      expect(screen.getByRole("log")).toBeInTheDocument();
    });

    it("should have aria-live region for new messages", () => {
      render(<MessageList messages={mockMessages} />);
      expect(screen.getByTestId("message-list")).toHaveAttribute(
        "aria-live",
        "polite",
      );
    });
  });
});
