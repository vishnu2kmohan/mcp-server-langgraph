/**
 * UnifiedMessageList Core Tests
 *
 * Tests for: Basic Rendering, Auto-Scroll, Streaming, Loading State,
 *            Empty State, Scroll-to-Bottom Button, CVA Variants,
 *            Accessibility (basic)
 */
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { TestProvider } from "@/test-utils";
import {
  createMockMessage,
  mockClipboard,
} from "./UnifiedMessageList.fixtures";

// =============================================================================
// Global mocks
// =============================================================================
Object.assign(navigator, { clipboard: mockClipboard });
Element.prototype.scrollIntoView = vi.fn();
global.requestAnimationFrame = vi.fn((cb) => {
  cb(0);
  return 0;
});
global.cancelAnimationFrame = vi.fn();

// =============================================================================
// vi.mock() calls - paths adjusted for __tests__/ depth
// =============================================================================

vi.mock("../../contexts/TelemetryContext", () => ({
  TelemetryProvider: ({ children }: { children: React.ReactNode }) => children,
  useSessionTelemetry: () => ({
    trackSessionCreation: vi.fn(),
    trackRevalidation: vi.fn(),
    trackSync: vi.fn(),
    trackBypassApproval: vi.fn(),
    getMetrics: () => ({}),
  }),
}));

vi.mock("@/components/Chat/MarkdownContent", () => ({
  MarkdownContent: ({ content }: { content: string }) => (
    <div data-testid="markdown-content">{content}</div>
  ),
}));

vi.mock("@/components/Chat/SourceCitations", () => ({
  SourceCitations: ({ sources }: { sources: unknown[] }) => (
    <div data-testid="source-citations">
      {sources.map((s: unknown, i: number) => (
        <span key={i}>{(s as { title: string }).title}</span>
      ))}
    </div>
  ),
}));

vi.mock("@/components/Chat/ResponseRating", () => ({
  ResponseRating: ({
    messageId,
    currentRating,
  }: {
    messageId: string;
    currentRating?: string;
  }) => (
    <div data-testid="response-rating" data-message-id={messageId}>
      <button
        type="button"
        aria-label="thumbs up"
        data-rating={currentRating === "up" ? "active" : ""}
      >
        Up
      </button>
      <button
        type="button"
        aria-label="thumbs down"
        data-rating={currentRating === "down" ? "active" : ""}
      >
        Down
      </button>
    </div>
  ),
}));

vi.mock("@/components/Chat/TokenUsageDisplay", () => ({
  TokenUsageDisplay: ({
    promptTokens,
    completionTokens,
    compact,
  }: {
    promptTokens: number;
    completionTokens: number;
    compact?: boolean;
  }) => (
    <div data-testid="token-usage-display" data-compact={compact}>
      {promptTokens} + {completionTokens} tokens
    </div>
  ),
}));

vi.mock("@/components/Chat/ConfidenceIndicator", () => ({
  ConfidenceIndicator: ({
    score,
    compact,
  }: {
    score: number;
    compact?: boolean;
  }) => (
    <div data-testid="confidence-indicator" data-compact={compact}>
      {Math.round(score * 100)}%
    </div>
  ),
}));

vi.mock("@/components/Chat/HallucinationIndicator", () => ({
  HallucinationIndicator: ({
    messageId,
    isReported,
  }: {
    messageId: string;
    isReported?: boolean;
  }) => (
    <div data-testid="hallucination-indicator" data-message-id={messageId}>
      {isReported ? "Reported" : "Flag"}
    </div>
  ),
}));

vi.mock("@/components/Chat/LLMThinkingTrace", () => ({
  LLMThinkingTrace: ({ thinkingContent }: { thinkingContent: string }) => (
    <div data-testid="llm-thinking-trace">{thinkingContent.slice(0, 50)}</div>
  ),
}));

vi.mock("@/components/Chat/AgentTraceToggleButton", () => ({
  AgentTraceToggleButton: ({
    isExpanded,
    onToggle,
  }: {
    isExpanded: boolean;
    onToggle: () => void;
  }) => (
    <button
      type="button"
      data-testid="agent-trace-toggle"
      aria-expanded={isExpanded}
      onClick={onToggle}
    >
      Toggle Trace
    </button>
  ),
}));

vi.mock("@/components/Chat/AgentExecutionTracePanel", () => ({
  AgentExecutionTracePanel: () => (
    <div data-testid="agent-execution-trace-panel">Trace Panel</div>
  ),
}));

vi.mock("@/components/Chat/MessageActions", () => ({
  MessageActions: ({
    messageId,
    onEdit,
    onDelete,
    onRegenerate,
  }: {
    messageId: string;
    onEdit?: (id: string) => void;
    onDelete?: (id: string) => void;
    onRegenerate?: (id: string) => void;
  }) => (
    <div data-testid="message-actions" data-message-id={messageId}>
      {onEdit && (
        <button type="button" onClick={() => onEdit(messageId)}>
          Edit
        </button>
      )}
      {onDelete && (
        <button type="button" onClick={() => onDelete(messageId)}>
          Delete
        </button>
      )}
      {onRegenerate && (
        <button type="button" onClick={() => onRegenerate(messageId)}>
          Regenerate
        </button>
      )}
    </div>
  ),
}));

vi.mock("@/components/EmptyState/AIEmptyState", () => ({
  AIEmptyState: () => <div data-testid="ai-empty-state">No messages yet</div>,
}));

import { UnifiedMessageList } from "../UnifiedMessageList";

// =============================================================================
// Tests
// =============================================================================

describe("UnifiedMessageList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render without crashing", () => {
      render(
        <TestProvider>
          <UnifiedMessageList messages={[]} showEmptyState={false} />
        </TestProvider>,
      );
      expect(screen.getByTestId("unified-message-list")).toBeInTheDocument();
    });

    it("should render user messages", () => {
      const messages = [createMockMessage({ role: "user", content: "Hello" })];

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );
      expect(screen.getByText("Hello")).toBeInTheDocument();
    });

    it("should render assistant messages", () => {
      const messages = [
        createMockMessage({ role: "assistant", content: "Hi there!" }),
      ];

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });

    it("should render multiple messages in order", () => {
      const messages = [
        createMockMessage({ role: "user", content: "First message" }),
        createMockMessage({ role: "assistant", content: "Second message" }),
        createMockMessage({ role: "user", content: "Third message" }),
      ];

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );

      expect(screen.getByText("First message")).toBeInTheDocument();
      expect(screen.getByText("Second message")).toBeInTheDocument();
      expect(screen.getByText("Third message")).toBeInTheDocument();
    });
  });

  describe("Auto-Scroll", () => {
    it("should scroll when new message arrives", async () => {
      const { rerender } = render(
        <TestProvider>
          <UnifiedMessageList messages={[]} showEmptyState={false} />
        </TestProvider>,
      );

      rerender(
        <UnifiedMessageList
          messages={[createMockMessage({ content: "Hello" })]}
        />,
      );

      await waitFor(() => {
        expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
      });
    });

    it("should not scroll when isScrolledUp=true", () => {
      vi.clearAllMocks();
      render(
        <TestProvider>
          <UnifiedMessageList
            messages={[createMockMessage({ content: "Hello" })]}
            isScrolledUp={true}
          />
        </TestProvider>,
      );

      expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
    });

    it("should use content length as dependency during streaming", async () => {
      const { rerender } = render(
        <TestProvider>
          <UnifiedMessageList
            messages={[
              createMockMessage({
                id: "streaming-message",
                role: "assistant",
                content: "Hello",
                isStreaming: true,
              }),
            ]}
            isStreaming={true}
          />
        </TestProvider>,
      );

      vi.clearAllMocks();

      rerender(
        <UnifiedMessageList
          messages={[
            createMockMessage({
              id: "streaming-message",
              role: "assistant",
              content: "Hello, world!", // Content grew
              isStreaming: true,
            }),
          ]}
          isStreaming={true}
        />,
      );

      await waitFor(() => {
        expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
      });
    });
  });

  describe("Streaming", () => {
    it("should show streaming cursor for streaming messages", () => {
      render(
        <TestProvider>
          <UnifiedMessageList
            messages={[
              createMockMessage({
                id: "streaming-message",
                role: "assistant",
                content: "Thinking...",
                isStreaming: true,
              }),
            ]}
            isStreaming={true}
          />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Generating response")).toBeInTheDocument();
    });

    it("should show typing indicator when streaming with no content", () => {
      render(
        <TestProvider>
          <UnifiedMessageList
            messages={[]}
            isStreaming={true}
            showEmptyState={false}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("typing-indicator")).toBeInTheDocument();
    });

    it("should not show typing indicator when streaming message has content", () => {
      render(
        <TestProvider>
          <UnifiedMessageList
            messages={[
              createMockMessage({
                role: "assistant",
                content: "Some content",
                isStreaming: true,
              }),
            ]}
            isStreaming={true}
          />
        </TestProvider>,
      );

      expect(screen.queryByTestId("typing-indicator")).not.toBeInTheDocument();
    });

    it("should show processing indicator for empty streaming message", () => {
      render(
        <TestProvider>
          <UnifiedMessageList
            messages={[
              createMockMessage({
                role: "assistant",
                content: "",
                isStreaming: true,
              }),
            ]}
            isStreaming={true}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Processing...")).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true and not streaming", () => {
      render(
        <TestProvider>
          <UnifiedMessageList
            messages={[createMockMessage()]}
            isLoading={true}
            isStreaming={false}
          />
        </TestProvider>,
      );
      expect(screen.getByText("Processing...")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no messages", () => {
      render(
        <TestProvider>
          <UnifiedMessageList messages={[]} showEmptyState />
        </TestProvider>,
      );
      expect(screen.getByTestId("ai-empty-state")).toBeInTheDocument();
    });

    it("should not show empty state when there are messages", () => {
      const messages = [createMockMessage()];
      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} showEmptyState />
        </TestProvider>,
      );
      expect(screen.queryByTestId("ai-empty-state")).not.toBeInTheDocument();
    });
  });

  describe("Scroll-to-Bottom Button", () => {
    it("should show scroll button when isScrolledUp", () => {
      render(
        <TestProvider>
          <UnifiedMessageList
            messages={[createMockMessage()]}
            isScrolledUp
            onScrollToBottom={() => {}}
          />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Scroll to bottom")).toBeInTheDocument();
    });

    it("should call onScrollToBottom when clicked", async () => {
      const user = userEvent.setup();
      const onScrollToBottom = vi.fn();

      render(
        <TestProvider>
          <UnifiedMessageList
            messages={[createMockMessage()]}
            isScrolledUp
            onScrollToBottom={onScrollToBottom}
          />
        </TestProvider>,
      );

      await user.click(screen.getByLabelText("Scroll to bottom"));
      expect(onScrollToBottom).toHaveBeenCalled();
    });
  });

  describe("CVA Variants", () => {
    it("should apply user message styles", () => {
      const messages = [
        createMockMessage({ id: "user-msg", role: "user", content: "Hello" }),
      ];

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );
      const messageRow = screen.getByTestId("message-user-msg");
      expect(messageRow).toHaveClass("justify-end");
    });

    it("should apply assistant message styles", () => {
      const messages = [
        createMockMessage({
          id: "assistant-msg",
          role: "assistant",
          content: "Hi",
        }),
      ];

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );
      const messageRow = screen.getByTestId("message-assistant-msg");
      expect(messageRow).toHaveClass("justify-start");
    });
  });

  describe("Accessibility", () => {
    it("should have a role of log for screen readers", () => {
      render(
        <TestProvider>
          <UnifiedMessageList messages={[]} showEmptyState={false} />
        </TestProvider>,
      );
      expect(screen.getByRole("log")).toBeInTheDocument();
    });

    it("should have aria-live polite for new messages", () => {
      render(
        <TestProvider>
          <UnifiedMessageList messages={[]} showEmptyState={false} />
        </TestProvider>,
      );
      const list = screen.getByTestId("unified-message-list");
      expect(list).toHaveAttribute("aria-live", "polite");
    });
  });
});
