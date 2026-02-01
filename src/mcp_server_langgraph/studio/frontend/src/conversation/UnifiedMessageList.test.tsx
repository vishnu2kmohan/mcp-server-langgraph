/**
 * UnifiedMessageList Tests (Enhanced v3)
 *
 * Tests for the consolidated message rendering component (ADR-0104).
 * Uses Vitest for mocking and includes scrollIntoView stubs.
 */
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { UnifiedMessageList } from "./UnifiedMessageList";
import type { ChatMessage } from "../types/session";

expect.extend(toHaveNoViolations);

// =============================================================================
// Mocks
// =============================================================================

// Mock clipboard
const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};
Object.assign(navigator, { clipboard: mockClipboard });

// Mock scrollIntoView
Element.prototype.scrollIntoView = vi.fn();

// Mock requestAnimationFrame
global.requestAnimationFrame = vi.fn((cb) => {
  cb(0);
  return 0;
});
global.cancelAnimationFrame = vi.fn();

// Mock the TelemetryContext
vi.mock("../contexts/TelemetryContext", () => ({
  TelemetryProvider: ({ children }: { children: React.ReactNode }) => children,
  useSessionTelemetry: () => ({
    trackSessionCreation: vi.fn(),
    trackRevalidation: vi.fn(),
    trackSync: vi.fn(),
    trackBypassApproval: vi.fn(),
    getMetrics: () => ({}),
  }),
}));

// Mock heavy components
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

// =============================================================================
// Test Data
// =============================================================================

const createMockMessage = (
  overrides: Partial<ChatMessage> = {},
): ChatMessage => ({
  id: `msg-${Math.random().toString(36).slice(2, 11)}`,
  role: "user",
  content: "Hello, world!",
  timestamp: Date.now(),
  ...overrides,
});

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
      render(<UnifiedMessageList messages={[]} showEmptyState={false} />);
      expect(screen.getByTestId("unified-message-list")).toBeInTheDocument();
    });

    it("should render user messages", () => {
      const messages = [createMockMessage({ role: "user", content: "Hello" })];

      render(<UnifiedMessageList messages={messages} />);
      expect(screen.getByText("Hello")).toBeInTheDocument();
    });

    it("should render assistant messages", () => {
      const messages = [
        createMockMessage({ role: "assistant", content: "Hi there!" }),
      ];

      render(<UnifiedMessageList messages={messages} />);
      expect(screen.getByText("Hi there!")).toBeInTheDocument();
    });

    it("should render multiple messages in order", () => {
      const messages = [
        createMockMessage({ role: "user", content: "First message" }),
        createMockMessage({ role: "assistant", content: "Second message" }),
        createMockMessage({ role: "user", content: "Third message" }),
      ];

      render(<UnifiedMessageList messages={messages} />);

      expect(screen.getByText("First message")).toBeInTheDocument();
      expect(screen.getByText("Second message")).toBeInTheDocument();
      expect(screen.getByText("Third message")).toBeInTheDocument();
    });
  });

  describe("Auto-Scroll", () => {
    it("should scroll when new message arrives", async () => {
      const { rerender } = render(
        <UnifiedMessageList messages={[]} showEmptyState={false} />,
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
        <UnifiedMessageList
          messages={[createMockMessage({ content: "Hello" })]}
          isScrolledUp={true}
        />,
      );

      expect(Element.prototype.scrollIntoView).not.toHaveBeenCalled();
    });

    it("should use content length as dependency during streaming", async () => {
      const { rerender } = render(
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
        />,
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
        />,
      );

      expect(screen.getByLabelText("Generating response")).toBeInTheDocument();
    });

    it("should show typing indicator when streaming with no content", () => {
      render(
        <UnifiedMessageList
          messages={[]}
          isStreaming={true}
          showEmptyState={false}
        />,
      );

      expect(screen.getByTestId("typing-indicator")).toBeInTheDocument();
    });

    it("should not show typing indicator when streaming message has content", () => {
      render(
        <UnifiedMessageList
          messages={[
            createMockMessage({
              role: "assistant",
              content: "Some content",
              isStreaming: true,
            }),
          ]}
          isStreaming={true}
        />,
      );

      expect(screen.queryByTestId("typing-indicator")).not.toBeInTheDocument();
    });

    it("should show processing indicator for empty streaming message", () => {
      render(
        <UnifiedMessageList
          messages={[
            createMockMessage({
              role: "assistant",
              content: "",
              isStreaming: true,
            }),
          ]}
          isStreaming={true}
        />,
      );

      expect(screen.getByText("Processing...")).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true and not streaming", () => {
      render(
        <UnifiedMessageList
          messages={[createMockMessage()]}
          isLoading={true}
          isStreaming={false}
        />,
      );
      expect(screen.getByText("Processing...")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no messages", () => {
      render(<UnifiedMessageList messages={[]} showEmptyState />);
      expect(screen.getByTestId("ai-empty-state")).toBeInTheDocument();
    });

    it("should not show empty state when there are messages", () => {
      const messages = [createMockMessage()];
      render(<UnifiedMessageList messages={messages} showEmptyState />);
      expect(screen.queryByTestId("ai-empty-state")).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have a role of log for screen readers", () => {
      render(<UnifiedMessageList messages={[]} showEmptyState={false} />);
      expect(screen.getByRole("log")).toBeInTheDocument();
    });

    it("should have aria-live polite for new messages", () => {
      render(<UnifiedMessageList messages={[]} showEmptyState={false} />);
      const list = screen.getByTestId("unified-message-list");
      expect(list).toHaveAttribute("aria-live", "polite");
    });
  });

  describe("Source Citations", () => {
    it("should render source citations when message has sources", () => {
      const messages = [
        createMockMessage({
          role: "assistant",
          content: "Here is the information.",
          sources: [{ title: "Source 1", url: "https://example.com/1" }],
        }),
      ];

      render(<UnifiedMessageList messages={messages} />);
      expect(screen.getByTestId("source-citations")).toBeInTheDocument();
      expect(screen.getByText("Source 1")).toBeInTheDocument();
    });
  });

  describe("LLM Thinking Traces", () => {
    it("should render thinking trace when message has thinkingContent", async () => {
      const messages = [
        createMockMessage({
          role: "assistant",
          content: "Final answer",
          thinkingContent: "Let me think about this...",
        }),
      ];

      render(<UnifiedMessageList messages={messages} />);

      // Wait for lazy-loaded component to resolve
      await waitFor(() => {
        expect(screen.getByTestId("llm-thinking-trace")).toBeInTheDocument();
      });
    });

    it("should not render thinking trace when thinkingContent is empty", () => {
      const messages = [
        createMockMessage({
          role: "assistant",
          content: "Simple response",
        }),
      ];

      render(<UnifiedMessageList messages={messages} />);
      expect(
        screen.queryByTestId("llm-thinking-trace"),
      ).not.toBeInTheDocument();
    });
  });

  describe("ResponseRating", () => {
    it("should render rating controls with correct API props", () => {
      const onRateMessage = vi.fn();
      const messages = [
        createMockMessage({
          id: "msg-1",
          role: "assistant",
          content: "Rate this response",
        }),
      ];

      render(
        <UnifiedMessageList
          messages={messages}
          onRateMessage={onRateMessage}
          messageRatings={{ "msg-1": "up" }}
          showRating
        />,
      );

      const rating = screen.getByTestId("response-rating");
      expect(rating).toBeInTheDocument();
      expect(rating).toHaveAttribute("data-message-id", "msg-1");
    });

    it("should not render rating controls when showRating is false", () => {
      const messages = [
        createMockMessage({
          role: "assistant",
          content: "No rating here",
        }),
      ];

      render(<UnifiedMessageList messages={messages} showRating={false} />);
      expect(screen.queryByTestId("response-rating")).not.toBeInTheDocument();
    });
  });

  describe("Token Usage", () => {
    it("should render token usage when showTokenUsage is true", () => {
      const messages = [
        createMockMessage({
          role: "assistant",
          content: "Response with tokens",
          usage: { promptTokens: 100, completionTokens: 50 },
        }),
      ];

      render(<UnifiedMessageList messages={messages} showTokenUsage />);
      expect(screen.getByTestId("token-usage-display")).toBeInTheDocument();
    });

    it("should use compact mode for token usage", () => {
      const messages = [
        createMockMessage({
          role: "assistant",
          content: "Response",
          usage: { promptTokens: 100, completionTokens: 50 },
        }),
      ];

      render(<UnifiedMessageList messages={messages} showTokenUsage />);
      expect(screen.getByTestId("token-usage-display")).toHaveAttribute(
        "data-compact",
        "true",
      );
    });
  });

  describe("Confidence Indicator", () => {
    it("should render confidence indicator when message has confidence", () => {
      const messages = [
        createMockMessage({
          role: "assistant",
          content: "Confident response",
          agentMetadata: { confidence: 0.92 },
        }),
      ];

      render(<UnifiedMessageList messages={messages} />);
      expect(screen.getByTestId("confidence-indicator")).toBeInTheDocument();
      expect(screen.getByText("92%")).toBeInTheDocument();
    });
  });

  describe("Hallucination Reporting", () => {
    it("should render hallucination indicator when enabled", () => {
      const onReportHallucination = vi.fn();
      const messages = [
        createMockMessage({
          id: "msg-1",
          role: "assistant",
          content: "Response",
        }),
      ];

      render(
        <UnifiedMessageList
          messages={messages}
          enableHallucinationReporting
          onReportHallucination={onReportHallucination}
        />,
      );

      expect(screen.getByTestId("hallucination-indicator")).toBeInTheDocument();
    });

    it("should show reported state", () => {
      const onReportHallucination = vi.fn();
      const messages = [
        createMockMessage({
          id: "msg-1",
          role: "assistant",
          content: "Response",
          isReported: true,
        }),
      ];

      render(
        <UnifiedMessageList
          messages={messages}
          enableHallucinationReporting
          onReportHallucination={onReportHallucination}
        />,
      );

      expect(screen.getByText("Reported")).toBeInTheDocument();
    });
  });

  describe("Per-Message Agent Traces", () => {
    it("should show trace toggle when executionTrace exists", () => {
      const messages = [
        createMockMessage({
          id: "msg-1",
          role: "assistant",
          content: "Response",
          agentMetadata: {
            executionTrace: {
              traceId: "trace-123",
              steps: [{ name: "step1", status: "completed" }],
            },
          },
        }),
      ];

      render(<UnifiedMessageList messages={messages} showAgentTraces={true} />);

      expect(screen.getByTestId("agent-trace-toggle")).toBeInTheDocument();
    });

    it("should expand trace panel when toggle clicked", async () => {
      const user = userEvent.setup();
      const messages = [
        createMockMessage({
          id: "msg-1",
          role: "assistant",
          content: "Response",
          agentMetadata: {
            executionTrace: {
              traceId: "trace-123",
              steps: [{ name: "step1", status: "completed" }],
            },
          },
        }),
      ];

      render(<UnifiedMessageList messages={messages} showAgentTraces={true} />);

      const toggle = screen.getByTestId("agent-trace-toggle");
      await user.click(toggle);

      await waitFor(() => {
        expect(
          screen.getByTestId("agent-execution-trace-panel"),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Avatars", () => {
    it("should show assistant avatar when showAvatars is true", () => {
      const messages = [
        createMockMessage({
          role: "assistant",
          content: "Hello",
        }),
      ];

      render(<UnifiedMessageList messages={messages} showAvatars />);
      expect(screen.getByTestId("assistant-avatar")).toBeInTheDocument();
    });

    it("should show user avatar with initials", () => {
      const messages = [
        createMockMessage({
          role: "user",
          content: "Hello",
        }),
      ];

      render(
        <UnifiedMessageList
          messages={messages}
          showAvatars
          userInitials="JD"
        />,
      );
      expect(screen.getByTestId("user-avatar")).toBeInTheDocument();
      expect(screen.getByText("JD")).toBeInTheDocument();
    });
  });

  describe("Scroll-to-Bottom Button", () => {
    it("should show scroll button when isScrolledUp", () => {
      render(
        <UnifiedMessageList
          messages={[createMockMessage()]}
          isScrolledUp
          onScrollToBottom={() => {}}
        />,
      );

      expect(screen.getByLabelText("Scroll to bottom")).toBeInTheDocument();
    });

    it("should call onScrollToBottom when clicked", async () => {
      const user = userEvent.setup();
      const onScrollToBottom = vi.fn();

      render(
        <UnifiedMessageList
          messages={[createMockMessage()]}
          isScrolledUp
          onScrollToBottom={onScrollToBottom}
        />,
      );

      await user.click(screen.getByLabelText("Scroll to bottom"));
      expect(onScrollToBottom).toHaveBeenCalled();
    });
  });

  describe("Follow-up Suggestions", () => {
    it("should render follow-up suggestions when provided", () => {
      const suggestions = [
        { id: "s1", text: "Tell me more", category: "general" },
        { id: "s2", text: "What about X?", category: "clarification" },
      ];

      render(
        <UnifiedMessageList
          messages={[createMockMessage()]}
          followUpSuggestions={suggestions}
        />,
      );

      expect(screen.getByTestId("follow-up-suggestions")).toBeInTheDocument();
      expect(screen.getByText("Tell me more")).toBeInTheDocument();
      expect(screen.getByText("What about X?")).toBeInTheDocument();
    });

    it("should call onSuggestionSelect when clicked", async () => {
      const user = userEvent.setup();
      const onSuggestionSelect = vi.fn();
      const suggestions = [{ id: "s1", text: "Click me", category: "general" }];

      render(
        <UnifiedMessageList
          messages={[createMockMessage()]}
          followUpSuggestions={suggestions}
          onSuggestionSelect={onSuggestionSelect}
        />,
      );

      await user.click(screen.getByText("Click me"));
      expect(onSuggestionSelect).toHaveBeenCalledWith(suggestions[0]);
    });

    it("should not show suggestions when streaming", () => {
      const suggestions = [
        { id: "s1", text: "Suggestion", category: "general" },
      ];

      render(
        <UnifiedMessageList
          messages={[createMockMessage()]}
          followUpSuggestions={suggestions}
          isStreaming
        />,
      );

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });
  });

  describe("CVA Variants", () => {
    it("should apply user message styles", () => {
      const messages = [
        createMockMessage({ id: "user-msg", role: "user", content: "Hello" }),
      ];

      render(<UnifiedMessageList messages={messages} />);
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

      render(<UnifiedMessageList messages={messages} />);
      const messageRow = screen.getByTestId("message-assistant-msg");
      expect(messageRow).toHaveClass("justify-start");
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("Accessibility", () => {
    // Helper to wait for Suspense components
    const waitForSuspense = async () => {
      await new Promise((resolve) => setTimeout(resolve, 100));
    };

    it("should have no accessibility violations", async () => {
      const messages = [
        createMockMessage({ id: "1", role: "user", content: "Hello" }),
        createMockMessage({ id: "2", role: "assistant", content: "Hi there!" }),
      ];
      const { container } = render(<UnifiedMessageList messages={messages} />);
      await waitForSuspense();
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when empty", async () => {
      const { container } = render(<UnifiedMessageList messages={[]} />);
      await waitForSuspense();
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when loading", async () => {
      const messages = [createMockMessage()];
      const { container } = render(
        <UnifiedMessageList messages={messages} isLoading />,
      );
      await waitForSuspense();
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when streaming", async () => {
      const messages = [
        createMockMessage({ id: "1", role: "user", content: "Hello" }),
        createMockMessage({
          id: "streaming-message",
          role: "assistant",
          content: "Thinking...",
          isStreaming: true,
        }),
      ];
      const { container } = render(
        <UnifiedMessageList messages={messages} isStreaming />,
      );
      await waitForSuspense();
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible list role", () => {
      const messages = [createMockMessage()];
      render(<UnifiedMessageList messages={messages} />);
      expect(screen.getByRole("log")).toBeInTheDocument();
    });

    it("should have aria-live region for new messages", () => {
      const messages = [createMockMessage()];
      render(<UnifiedMessageList messages={messages} />);
      expect(screen.getByTestId("unified-message-list")).toHaveAttribute(
        "aria-live",
        "polite",
      );
    });
  });
});
