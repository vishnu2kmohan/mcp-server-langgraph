/**
 * LLMThinkingTrace Component Tests
 *
 * TDD tests for displaying LLM native thinking content from models like:
 * - Claude Opus 4.5 / Sonnet 4 (thinking blocks)
 * - Gemini 2.5 Pro/Flash (thinking_content)
 *
 * Features:
 * - Collapsible thinking trace display
 * - Copy to clipboard
 * - Visual distinction from regular content
 * - Token count display
 * - Expandable/collapsible sections
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import {
  LLMThinkingTrace,
  type LLMThinkingTraceProps,
} from "./LLMThinkingTrace";

import { TestProvider } from "@/test-utils";

// Mock clipboard API
const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};
Object.assign(navigator, { clipboard: mockClipboard });

describe("LLMThinkingTrace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const defaultProps: LLMThinkingTraceProps = {
    thinkingContent:
      "Let me analyze this step by step.\n\n1. First, I need to understand the problem.\n2. Then, I'll break it down into components.\n3. Finally, I'll synthesize a solution.",
    isExpanded: false,
    onToggle: vi.fn(),
  };

  describe("rendering", () => {
    it("should render the thinking trace container", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByTestId("llm-thinking-trace")).toBeInTheDocument();
    });

    it("should display 'Thinking' label with brain icon", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/thinking/i)).toBeInTheDocument();
    });

    it("should show expand/collapse toggle button", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /toggle thinking/i }),
      ).toBeInTheDocument();
    });

    it("should hide content when collapsed", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={false} />
        </TestProvider>,
      );
      expect(screen.queryByTestId("thinking-content")).not.toBeInTheDocument();
    });

    it("should show content when expanded", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={true} />
        </TestProvider>,
      );
      expect(screen.getByTestId("thinking-content")).toBeInTheDocument();
      expect(screen.getByText(/step by step/i)).toBeInTheDocument();
    });

    it("should display thinking content with proper formatting", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={true} />
        </TestProvider>,
      );
      const content = screen.getByTestId("thinking-content");
      expect(content).toHaveClass("whitespace-pre-wrap");
    });

    it("should apply distinct styling to differentiate from regular content", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={true} />
        </TestProvider>,
      );
      const container = screen.getByTestId("llm-thinking-trace");
      // Should have a distinct background color (purple/violet theme for thinking)
      expect(container).toHaveClass("bg-insight-2");
    });
  });

  describe("toggle functionality", () => {
    it("should call onToggle when toggle button is clicked", () => {
      const onToggle = vi.fn();
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} onToggle={onToggle} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /toggle thinking/i }));
      expect(onToggle).toHaveBeenCalledTimes(1);
    });

    it("should show chevron-down icon when collapsed", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={false} />
        </TestProvider>,
      );
      expect(screen.getByTestId("chevron-icon")).toBeInTheDocument();
    });

    it("should show chevron-up icon when expanded", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={true} />
        </TestProvider>,
      );
      expect(screen.getByTestId("chevron-icon")).toBeInTheDocument();
    });
  });

  describe("copy functionality", () => {
    it("should show copy button when expanded", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={true} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /copy thinking/i }),
      ).toBeInTheDocument();
    });

    it("should copy thinking content to clipboard when copy button clicked", async () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={true} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /copy thinking/i }));

      await waitFor(() => {
        expect(mockClipboard.writeText).toHaveBeenCalledWith(
          defaultProps.thinkingContent,
        );
      });
    });

    it("should show 'Copied!' feedback after copying", async () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={true} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /copy thinking/i }));

      await waitFor(() => {
        expect(screen.getByText(/copied/i)).toBeInTheDocument();
      });
    });
  });

  describe("token count display", () => {
    it("should display thinking token count when provided", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} thinkingTokens={1234} />
        </TestProvider>,
      );
      expect(screen.getByText(/1,?234/)).toBeInTheDocument();
      expect(screen.getByText(/tokens/i)).toBeInTheDocument();
    });

    it("should not show token count when not provided", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.queryByText(/tokens/i)).not.toBeInTheDocument();
    });
  });

  describe("model indicator", () => {
    it("should display model name when provided", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace
            {...defaultProps}
            modelName="claude-opus-4-5-20251101"
          />
        </TestProvider>,
      );
      expect(screen.getByText(/claude-opus/i)).toBeInTheDocument();
    });

    it("should show thinking model badge for supported models", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace
            {...defaultProps}
            modelName="claude-opus-4-5-20251101"
            isThinkingModel={true}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("thinking-model-badge")).toBeInTheDocument();
    });
  });

  describe("streaming state", () => {
    it("should show streaming indicator when isStreaming is true", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace
            {...defaultProps}
            isExpanded={true}
            isStreaming={true}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("streaming-indicator")).toBeInTheDocument();
    });

    it("should animate streaming indicator", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace
            {...defaultProps}
            isExpanded={true}
            isStreaming={true}
          />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("streaming-indicator");
      expect(indicator).toHaveClass("animate-pulse");
    });
  });

  describe("empty state", () => {
    it("should not render when thinkingContent is empty", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} thinkingContent="" />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("llm-thinking-trace"),
      ).not.toBeInTheDocument();
    });

    it("should not render when thinkingContent is only whitespace", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} thinkingContent="   " />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("llm-thinking-trace"),
      ).not.toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have proper aria-expanded attribute", () => {
      const { rerender } = render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={false} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /toggle thinking/i }),
      ).toHaveAttribute("aria-expanded", "false");

      rerender(<LLMThinkingTrace {...defaultProps} isExpanded={true} />);
      expect(
        screen.getByRole("button", { name: /toggle thinking/i }),
      ).toHaveAttribute("aria-expanded", "true");
    });

    it("should have proper aria-label for copy button", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} isExpanded={true} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /copy thinking/i }),
      ).toHaveAttribute("aria-label");
    });
  });

  describe("long content handling", () => {
    it("should show 'Show more' for very long content when collapsed", () => {
      const longContent = "A".repeat(1000);
      render(
        <TestProvider>
          <LLMThinkingTrace
            {...defaultProps}
            thinkingContent={longContent}
            isExpanded={true}
            maxPreviewLength={200}
          />
        </TestProvider>,
      );
      // Should show truncated preview with expand option
      expect(screen.getByText(/show more/i)).toBeInTheDocument();
    });

    it("should show full content when 'Show more' is clicked", async () => {
      const longContent = "A".repeat(1000);
      render(
        <TestProvider>
          <LLMThinkingTrace
            {...defaultProps}
            thinkingContent={longContent}
            isExpanded={true}
            maxPreviewLength={200}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText(/show more/i));

      await waitFor(() => {
        expect(screen.getByText(/show less/i)).toBeInTheDocument();
      });
    });
  });

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(
        <TestProvider>
          <LLMThinkingTrace {...defaultProps} className="custom-class" />
        </TestProvider>,
      );
      expect(screen.getByTestId("llm-thinking-trace")).toHaveClass(
        "custom-class",
      );
    });
  });
});
