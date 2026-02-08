/**
 * FollowUpSuggestions Tests - Phase 2
 *
 * Tests for AI-generated follow-up suggestion chips.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { FollowUpSuggestions, type Suggestion } from "./FollowUpSuggestions";

import { TestProvider } from "@/test-utils";

expect.extend(toHaveNoViolations);

// =============================================================================
// Test Data
// =============================================================================

const mockSuggestions: Suggestion[] = [
  {
    id: "sug-1",
    text: "Tell me more about React hooks",
    type: "follow-up",
  },
  {
    id: "sug-2",
    text: "Show me an example",
    type: "action",
  },
  {
    id: "sug-3",
    text: "What are the benefits?",
    type: "follow-up",
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("FollowUpSuggestions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render suggestions container", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("follow-up-suggestions")).toBeInTheDocument();
    });

    it("should render all suggestions", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );
      expect(
        screen.getByText("Tell me more about React hooks"),
      ).toBeInTheDocument();
      expect(screen.getByText("Show me an example")).toBeInTheDocument();
      expect(screen.getByText("What are the benefits?")).toBeInTheDocument();
    });

    it("should not render when no suggestions", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions suggestions={[]} onSelect={() => {}} />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("follow-up-suggestions"),
      ).not.toBeInTheDocument();
    });

    it("should render as chips by default", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );
      const chips = screen.getAllByTestId("suggestion-chip");
      expect(chips).toHaveLength(3);
    });
  });

  describe("Selection", () => {
    it("should call onSelect when suggestion clicked", () => {
      const onSelect = vi.fn();
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={onSelect}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("Show me an example"));
      expect(onSelect).toHaveBeenCalledWith(mockSuggestions[1]);
    });

    it("should highlight suggestion on hover", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );

      const chip = screen.getAllByTestId("suggestion-chip")[0];
      fireEvent.mouseEnter(chip);
      expect(chip).toHaveClass("hover");
    });
  });

  describe("Keyboard Navigation", () => {
    it("should select suggestion on Enter key", () => {
      const onSelect = vi.fn();
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={onSelect}
          />
        </TestProvider>,
      );

      const chip = screen.getAllByTestId("suggestion-chip")[0];
      chip.focus();
      fireEvent.keyDown(chip, { key: "Enter" });
      expect(onSelect).toHaveBeenCalledWith(mockSuggestions[0]);
    });

    it("should focus next suggestion on ArrowRight", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );

      const chips = screen.getAllByTestId("suggestion-chip");
      chips[0].focus();
      fireEvent.keyDown(chips[0], { key: "ArrowRight" });
      expect(chips[1]).toHaveFocus();
    });
  });

  describe("Loading State", () => {
    it("should show loading skeleton when isLoading", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions suggestions={[]} onSelect={() => {}} isLoading />
        </TestProvider>,
      );
      expect(screen.getByTestId("suggestions-skeleton")).toBeInTheDocument();
    });
  });

  describe("Animation", () => {
    it("should animate in when visible", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
            animate
          />
        </TestProvider>,
      );
      const container = screen.getByTestId("follow-up-suggestions");
      expect(container).toHaveClass("animate-in");
    });
  });

  describe("Styles", () => {
    it("should apply action type styling", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );
      const actionChip = screen
        .getByText("Show me an example")
        .closest("[data-testid='suggestion-chip']");
      expect(actionChip).toHaveClass("action");
    });

    it("should apply follow-up type styling", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );
      const followUpChip = screen
        .getByText("Tell me more about React hooks")
        .closest("[data-testid='suggestion-chip']");
      expect(followUpChip).toHaveClass("follow-up");
    });
  });

  describe("Max Suggestions", () => {
    it("should limit displayed suggestions when maxSuggestions is set", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
            maxSuggestions={2}
          />
        </TestProvider>,
      );
      const chips = screen.getAllByTestId("suggestion-chip");
      expect(chips).toHaveLength(2);
    });
  });

  describe("Accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when loading", async () => {
      const { container } = render(
        <TestProvider>
          <FollowUpSuggestions suggestions={[]} onSelect={() => {}} isLoading />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have navigation role", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByRole("navigation")).toBeInTheDocument();
    });

    it("should have accessible labels for suggestions", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );
      const chips = screen.getAllByTestId("suggestion-chip");
      chips.forEach((chip) => {
        expect(chip).toHaveAttribute("aria-label");
      });
    });

    it("should be focusable", () => {
      render(
        <TestProvider>
          <FollowUpSuggestions
            suggestions={mockSuggestions}
            onSelect={() => {}}
          />
        </TestProvider>,
      );
      const chips = screen.getAllByTestId("suggestion-chip");
      chips.forEach((chip) => {
        expect(chip).toHaveAttribute("tabIndex", "0");
      });
    });
  });
});
