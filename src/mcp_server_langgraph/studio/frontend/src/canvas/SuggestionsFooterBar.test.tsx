/**
 * SuggestionsFooterBar Tests
 *
 * Tests for the collapsible AI suggestions footer bar.
 * Replaces the floating CanvasShortcutsMenu with a non-intrusive footer.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SuggestionsFooterBar } from "./SuggestionsFooterBar";
import type { AISuggestion } from "../types/artifacts";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Test Fixtures
// =============================================================================

const mockSuggestions: AISuggestion[] = [
  {
    id: "sug-1",
    type: "refactor",
    label: "Extract function",
    description: "Extract repeated logic into a reusable function",
    confidence: 0.92,
  },
  {
    id: "sug-2",
    type: "optimize",
    label: "Use memo",
    description: "Wrap component with React.memo for performance",
    confidence: 0.85,
  },
  {
    id: "sug-3",
    type: "fix",
    label: "Add null check",
    description: "Add null check to prevent runtime error",
    confidence: 0.78,
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("SuggestionsFooterBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("Rendering", () => {
    it("should render with data-testid", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} />
        </TestProvider>,
      );
      expect(screen.getByTestId("suggestions-footer-bar")).toBeInTheDocument();
    });

    it("should show collapsed state by default", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} />
        </TestProvider>,
      );
      expect(
        screen.queryByTestId("suggestions-content"),
      ).not.toBeInTheDocument();
    });

    it("should display suggestion count badge", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} />
        </TestProvider>,
      );
      expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("should not show count badge when no suggestions", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} />
        </TestProvider>,
      );
      expect(screen.queryByText("0")).not.toBeInTheDocument();
    });

    it("should display AI Suggestions label", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} />
        </TestProvider>,
      );
      expect(screen.getByText("AI Suggestions")).toBeInTheDocument();
    });

    it("should have sparkles icon", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} />
        </TestProvider>,
      );
      expect(screen.getByTestId("sparkles-icon")).toBeInTheDocument();
    });
  });

  describe("Expand/Collapse", () => {
    it("should expand when header is clicked", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} />
        </TestProvider>,
      );

      const header = screen.getByTestId("suggestions-header");
      await user.click(header);

      expect(screen.getByTestId("suggestions-content")).toBeInTheDocument();
    });

    it("should collapse when header is clicked again", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} />
        </TestProvider>,
      );

      const header = screen.getByTestId("suggestions-header");
      await user.click(header); // expand
      await user.click(header); // collapse

      expect(
        screen.queryByTestId("suggestions-content"),
      ).not.toBeInTheDocument();
    });

    it("should have aria-expanded attribute", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} />
        </TestProvider>,
      );

      const header = screen.getByTestId("suggestions-header");
      expect(header).toHaveAttribute("aria-expanded", "false");

      await user.click(header);
      expect(header).toHaveAttribute("aria-expanded", "true");
    });

    it("should show chevron up when collapsed", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} />
        </TestProvider>,
      );
      expect(screen.getByTestId("chevron-up-icon")).toBeInTheDocument();
    });

    it("should show chevron down when expanded", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("suggestions-header"));
      expect(screen.getByTestId("chevron-down-icon")).toBeInTheDocument();
    });
  });

  describe("Suggestions Display", () => {
    it("should display suggestion items when expanded", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("suggestions-header"));

      expect(screen.getByText("Extract function")).toBeInTheDocument();
      expect(screen.getByText("Use memo")).toBeInTheDocument();
      expect(screen.getByText("Add null check")).toBeInTheDocument();
    });

    it("should display suggestion descriptions", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("suggestions-header"));

      expect(
        screen.getByText("Extract repeated logic into a reusable function"),
      ).toBeInTheDocument();
    });

    it("should show empty state when no suggestions", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("suggestions-header"));

      expect(screen.getByText(/no suggestions/i)).toBeInTheDocument();
    });
  });

  describe("Suggestion Actions", () => {
    it("should call onAccept when suggestion is accepted", async () => {
      const user = userEvent.setup();
      const onAccept = vi.fn();
      render(
        <TestProvider>
          <SuggestionsFooterBar
            suggestions={mockSuggestions}
            onAccept={onAccept}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("suggestions-header"));
      await user.click(screen.getByTestId("accept-sug-1"));

      expect(onAccept).toHaveBeenCalledWith(mockSuggestions[0]);
    });

    it("should call onDismiss when suggestion is dismissed", async () => {
      const user = userEvent.setup();
      const onDismiss = vi.fn();
      render(
        <TestProvider>
          <SuggestionsFooterBar
            suggestions={mockSuggestions}
            onDismiss={onDismiss}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("suggestions-header"));
      await user.click(screen.getByTestId("dismiss-sug-1"));

      expect(onDismiss).toHaveBeenCalledWith(mockSuggestions[0]);
    });
  });

  describe("Refresh", () => {
    it("should have refresh button", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} />
        </TestProvider>,
      );
      expect(screen.getByTestId("refresh-button")).toBeInTheDocument();
    });

    it("should call onRefresh when refresh button clicked", async () => {
      const user = userEvent.setup();
      const onRefresh = vi.fn();
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} onRefresh={onRefresh} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("refresh-button"));

      expect(onRefresh).toHaveBeenCalled();
    });

    it("should show loading spinner when isLoading is true", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} isLoading />
        </TestProvider>,
      );
      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });

    it("should disable refresh button when loading", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} isLoading />
        </TestProvider>,
      );
      expect(screen.getByTestId("refresh-button")).toBeDisabled();
    });
  });

  describe("Styling", () => {
    it("should have border-t for visual separation", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} />
        </TestProvider>,
      );
      expect(screen.getByTestId("suggestions-footer-bar")).toHaveClass(
        "border-t",
      );
    });

    it("should apply custom className", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={[]} className="custom-class" />
        </TestProvider>,
      );
      expect(screen.getByTestId("suggestions-footer-bar")).toHaveClass(
        "custom-class",
      );
    });

    it("should have max-height constraint on expanded content", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("suggestions-header"));

      expect(screen.getByTestId("suggestions-content")).toHaveClass(
        "max-h-[200px]",
      );
    });
  });

  describe("Controlled Mode", () => {
    it("should respect isExpanded prop", () => {
      render(
        <TestProvider>
          <SuggestionsFooterBar suggestions={mockSuggestions} isExpanded />
        </TestProvider>,
      );
      expect(screen.getByTestId("suggestions-content")).toBeInTheDocument();
    });

    it("should call onToggle when header clicked in controlled mode", async () => {
      const user = userEvent.setup();
      const onToggle = vi.fn();
      render(
        <TestProvider>
          <SuggestionsFooterBar
            suggestions={mockSuggestions}
            isExpanded={false}
            onToggle={onToggle}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("suggestions-header"));

      expect(onToggle).toHaveBeenCalled();
    });
  });
});
