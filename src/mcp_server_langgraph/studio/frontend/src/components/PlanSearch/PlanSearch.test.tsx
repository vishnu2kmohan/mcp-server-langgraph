/**
 * PlanSearch Tests
 *
 * Tests for the template search component with semantic search,
 * field filters, and sort options.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  act,
} from "@testing-library/react";
import {
  PlanSearch,
  type PlanSearchProps,
  type PlanTemplate,
} from "./PlanSearch";

describe("PlanSearch", () => {
  const sampleTemplates: PlanTemplate[] = [
    {
      templateId: "tmpl-1",
      name: "Code Review Template",
      description: "Template for code review tasks",
      orchestrator: "standard",
      thinkingBudget: "medium",
      critiqueRounds: 1,
      autoApprove: false,
      createdBy: "user@example.com",
      createdAt: "2025-01-01T00:00:00Z",
      useCount: 100,
      successRate: 0.95,
      tags: ["python", "review"],
    },
    {
      templateId: "tmpl-2",
      name: "Data Analysis Template",
      description: "Template for data analysis",
      orchestrator: "swarm",
      thinkingBudget: "deep",
      critiqueRounds: 2,
      autoApprove: true,
      createdBy: "admin@example.com",
      createdAt: "2025-01-02T00:00:00Z",
      useCount: 50,
      successRate: 0.88,
      tags: ["data", "analysis"],
    },
  ];

  const defaultProps: PlanSearchProps = {
    templates: sampleTemplates,
    onSearch: vi.fn(),
    onSelect: vi.fn(),
    isLoading: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render search input", () => {
      render(<PlanSearch {...defaultProps} />);
      expect(
        screen.getByPlaceholderText(/search templates/i),
      ).toBeInTheDocument();
    });

    it("should render filter dropdown for orchestrator", () => {
      render(<PlanSearch {...defaultProps} />);
      expect(screen.getByLabelText(/orchestrator/i)).toBeInTheDocument();
    });

    it("should render sort dropdown", () => {
      render(<PlanSearch {...defaultProps} />);
      expect(screen.getByLabelText(/sort by/i)).toBeInTheDocument();
    });

    it("should render template list", () => {
      render(<PlanSearch {...defaultProps} />);
      expect(screen.getByText("Code Review Template")).toBeInTheDocument();
      expect(screen.getByText("Data Analysis Template")).toBeInTheDocument();
    });

    it("should display template metadata", () => {
      render(<PlanSearch {...defaultProps} />);
      expect(screen.getByText(/100 uses/i)).toBeInTheDocument();
      expect(screen.getByText(/95%/i)).toBeInTheDocument();
    });
  });

  describe("Search Functionality", () => {
    it("should call onSearch when typing in search input", async () => {
      vi.useFakeTimers();
      render(<PlanSearch {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/search templates/i);
      fireEvent.change(searchInput, { target: { value: "code review" } });

      // Advance past debounce delay
      act(() => {
        vi.advanceTimersByTime(350);
      });

      expect(defaultProps.onSearch).toHaveBeenCalled();
      vi.useRealTimers();
    });

    it("should debounce search input", async () => {
      vi.useFakeTimers();
      render(<PlanSearch {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/search templates/i);
      fireEvent.change(searchInput, { target: { value: "test" } });

      // Should not call immediately
      expect(defaultProps.onSearch).not.toHaveBeenCalled();

      // Advance timers past debounce delay
      act(() => {
        vi.advanceTimersByTime(350);
      });

      expect(defaultProps.onSearch).toHaveBeenCalled();
      vi.useRealTimers();
    });
  });

  describe("Filtering", () => {
    it("should filter by orchestrator type", () => {
      render(<PlanSearch {...defaultProps} />);

      const orchestratorSelect = screen.getByLabelText(/orchestrator/i);
      fireEvent.change(orchestratorSelect, { target: { value: "swarm" } });

      expect(defaultProps.onSearch).toHaveBeenCalledWith(
        expect.objectContaining({
          orchestrator: "swarm",
        }),
      );
    });

    it("should filter by tags when tag chips are clicked", () => {
      render(<PlanSearch {...defaultProps} />);

      // Click on the first "python" tag chip (the one in the filter section)
      // The filter chip has specific styling classes that differentiate it
      const pythonTags = screen.getAllByRole("button", { name: /python/i });
      // First one is the filter chip (has rounded-full class)
      fireEvent.click(pythonTags[0]);

      expect(defaultProps.onSearch).toHaveBeenCalledWith(
        expect.objectContaining({
          tags: expect.arrayContaining(["python"]),
        }),
      );
    });
  });

  describe("Sorting", () => {
    it("should sort by popularity by default", () => {
      render(<PlanSearch {...defaultProps} />);
      const sortSelect = screen.getByLabelText(/sort by/i);
      expect(sortSelect).toHaveValue("popularity");
    });

    it("should call onSearch with sort option when changed", () => {
      render(<PlanSearch {...defaultProps} />);

      const sortSelect = screen.getByLabelText(/sort by/i);
      fireEvent.change(sortSelect, { target: { value: "success_rate" } });

      expect(defaultProps.onSearch).toHaveBeenCalledWith(
        expect.objectContaining({
          sortBy: "success_rate",
        }),
      );
    });

    it("should have all sort options available", () => {
      render(<PlanSearch {...defaultProps} />);

      expect(
        screen.getByRole("option", { name: /popularity/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /success rate/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /recent/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Template Selection", () => {
    it("should call onSelect when template card is clicked", () => {
      render(<PlanSearch {...defaultProps} />);

      const templateCard = screen
        .getByText("Code Review Template")
        .closest("button");
      if (templateCard) {
        fireEvent.click(templateCard);
      }

      expect(defaultProps.onSelect).toHaveBeenCalledWith(sampleTemplates[0]);
    });

    it("should highlight selected template", () => {
      render(<PlanSearch {...defaultProps} selectedTemplateId="tmpl-1" />);

      const templateCard = screen
        .getByText("Code Review Template")
        .closest("button");
      expect(templateCard).toHaveClass("ring-2");
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true", () => {
      render(<PlanSearch {...defaultProps} isLoading={true} />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("should disable interactions while loading", () => {
      render(<PlanSearch {...defaultProps} isLoading={true} />);
      expect(screen.getByPlaceholderText(/search templates/i)).toBeDisabled();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no templates match", () => {
      render(<PlanSearch {...defaultProps} templates={[]} />);
      expect(screen.getByText(/no templates found/i)).toBeInTheDocument();
    });

    it("should suggest clearing filters in empty state", () => {
      render(<PlanSearch {...defaultProps} templates={[]} />);
      expect(
        screen.getByRole("button", { name: /clear filters/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should display error message when error prop is provided", () => {
      render(<PlanSearch {...defaultProps} error="Failed to load templates" />);
      expect(screen.getByText(/failed to load templates/i)).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      const onRetry = vi.fn();
      render(
        <PlanSearch
          {...defaultProps}
          error="Network error"
          onRetry={onRetry}
        />,
      );
      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA labels", () => {
      render(<PlanSearch {...defaultProps} />);
      expect(screen.getByRole("searchbox")).toHaveAccessibleName();
    });

    it("should have focusable search input", () => {
      render(<PlanSearch {...defaultProps} />);

      const searchInput = screen.getByPlaceholderText(/search templates/i);
      searchInput.focus();

      expect(searchInput).toHaveFocus();
    });
  });
});
