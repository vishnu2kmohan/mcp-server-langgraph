/**
 * UnifiedMessageList Features Tests
 *
 * Tests for: Source Citations, LLM Thinking Traces, ResponseRating,
 *            Token Usage, Confidence Indicator, Hallucination Reporting,
 *            Per-Message Agent Traces, Avatars, Follow-up Suggestions,
 *            Accessibility (axe-core)
 */
import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

import { TestProvider } from "@/test-utils";
import {
  createMockMessage,
  mockClipboard,
} from "./UnifiedMessageList.fixtures";

expect.extend(toHaveNoViolations);

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

vi.mock("../../contexts/TelemetryContext", async () => {
  const actual = await vi.importActual("../../contexts/TelemetryContext");
  return {
    ...actual,
    TelemetryProvider: ({ children }: { children: React.ReactNode }) =>
      children,
    useSessionTelemetry: () => ({
      trackSessionCreation: vi.fn(),
      trackRevalidation: vi.fn(),
      trackSync: vi.fn(),
      trackBypassApproval: vi.fn(),
      getMetrics: () => ({}),
    }),
    useWebVitals: () => ({
      start: vi.fn(),
      stop: vi.fn(),
      getMetrics: () => ({ fcp: null, lcp: null, cls: null, inp: null }),
    }),
    useTelemetry: () => ({
      sessionTelemetry: {
        trackSessionCreation: vi.fn(),
        getMetrics: () => ({}),
      },
      webVitals: { start: vi.fn(), stop: vi.fn(), getMetrics: () => ({}) },
    }),
  };
});
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

  describe("Source Citations", () => {
    it("should render source citations when message has sources", () => {
      const messages = [
        createMockMessage({
          role: "assistant",
          content: "Here is the information.",
          sources: [{ title: "Source 1", url: "https://example.com/1" }],
        }),
      ];

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );
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

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );

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

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );
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
        <TestProvider>
          <UnifiedMessageList
            messages={messages}
            onRateMessage={onRateMessage}
            messageRatings={{ "msg-1": "up" }}
            showRating
          />
        </TestProvider>,
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

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} showRating={false} />
        </TestProvider>,
      );
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

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} showTokenUsage />
        </TestProvider>,
      );
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

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} showTokenUsage />
        </TestProvider>,
      );
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

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );
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
        <TestProvider>
          <UnifiedMessageList
            messages={messages}
            enableHallucinationReporting
            onReportHallucination={onReportHallucination}
          />
        </TestProvider>,
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
        <TestProvider>
          <UnifiedMessageList
            messages={messages}
            enableHallucinationReporting
            onReportHallucination={onReportHallucination}
          />
        </TestProvider>,
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

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} showAgentTraces={true} />
        </TestProvider>,
      );

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

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} showAgentTraces={true} />
        </TestProvider>,
      );

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

      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} showAvatars />
        </TestProvider>,
      );
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
        <TestProvider>
          <UnifiedMessageList
            messages={messages}
            showAvatars
            userInitials="JD"
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("user-avatar")).toBeInTheDocument();
      expect(screen.getByText("JD")).toBeInTheDocument();
    });
  });

  describe("Follow-up Suggestions", () => {
    it("should render follow-up suggestions when provided", () => {
      const suggestions = [
        { id: "s1", text: "Tell me more", category: "general" },
        { id: "s2", text: "What about X?", category: "clarification" },
      ];

      render(
        <TestProvider>
          <UnifiedMessageList
            messages={[createMockMessage()]}
            followUpSuggestions={suggestions}
          />
        </TestProvider>,
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
        <TestProvider>
          <UnifiedMessageList
            messages={[createMockMessage()]}
            followUpSuggestions={suggestions}
            onSuggestionSelect={onSuggestionSelect}
          />
        </TestProvider>,
      );

      await user.click(screen.getByText("Click me"));
      expect(onSuggestionSelect).toHaveBeenCalledWith(suggestions[0]);
    });

    it("should not show suggestions when streaming", () => {
      const suggestions = [
        { id: "s1", text: "Suggestion", category: "general" },
      ];

      render(
        <TestProvider>
          <UnifiedMessageList
            messages={[createMockMessage()]}
            followUpSuggestions={suggestions}
            isStreaming
          />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests (axe-core)
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
      const { container } = render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );
      await waitForSuspense();
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when empty", async () => {
      const { container } = render(
        <TestProvider>
          <UnifiedMessageList messages={[]} />
        </TestProvider>,
      );
      await waitForSuspense();
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when loading", async () => {
      const messages = [createMockMessage()];
      const { container } = render(
        <TestProvider>
          <UnifiedMessageList messages={messages} isLoading />
        </TestProvider>,
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
        <TestProvider>
          <UnifiedMessageList messages={messages} isStreaming />
        </TestProvider>,
      );
      await waitForSuspense();
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible list role", () => {
      const messages = [createMockMessage()];
      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );
      expect(screen.getByRole("log")).toBeInTheDocument();
    });

    it("should have aria-live region for new messages", () => {
      const messages = [createMockMessage()];
      render(
        <TestProvider>
          <UnifiedMessageList messages={messages} />
        </TestProvider>,
      );
      expect(screen.getByTestId("unified-message-list")).toHaveAttribute(
        "aria-live",
        "polite",
      );
    });
  });
});
