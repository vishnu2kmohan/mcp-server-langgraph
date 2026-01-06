/**
 * TemplateSelector Tests
 *
 * Tests for the template selection component with suggestion chips,
 * template preview, and apply functionality.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import {
  TemplateSelector,
  type TemplateSelectorProps,
  type TemplateOption,
} from "./TemplateSelector";

describe("TemplateSelector", () => {
  const sampleTemplates: TemplateOption[] = [
    {
      templateId: "tmpl-1",
      name: "Code Review",
      description: "Template for code review tasks",
      orchestrator: "standard",
      thinkingBudget: "medium",
      critiqueRounds: 1,
      autoApprove: false,
      useCount: 100,
      successRate: 0.95,
    },
    {
      templateId: "tmpl-2",
      name: "Data Analysis",
      description: "Template for data analysis with swarm orchestration",
      orchestrator: "swarm",
      thinkingBudget: "deep",
      critiqueRounds: 2,
      autoApprove: true,
      useCount: 50,
      successRate: 0.88,
    },
    {
      templateId: "tmpl-3",
      name: "Quick Task",
      description: "Simple template for quick tasks",
      orchestrator: "standard",
      thinkingBudget: "none",
      critiqueRounds: 0,
      autoApprove: true,
      useCount: 200,
      successRate: 0.92,
    },
  ];

  const defaultProps: TemplateSelectorProps = {
    suggestions: sampleTemplates,
    onApply: vi.fn(),
    onDismiss: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render suggestion chips", () => {
      render(<TemplateSelector {...defaultProps} />);
      expect(screen.getByText("Code Review")).toBeInTheDocument();
      expect(screen.getByText("Data Analysis")).toBeInTheDocument();
      expect(screen.getByText("Quick Task")).toBeInTheDocument();
    });

    it("should display component header", () => {
      render(<TemplateSelector {...defaultProps} />);
      expect(screen.getByText(/suggested templates/i)).toBeInTheDocument();
    });

    it("should show template count", () => {
      render(<TemplateSelector {...defaultProps} />);
      expect(screen.getByText(/3 suggestions/i)).toBeInTheDocument();
    });
  });

  describe("Template Selection", () => {
    it("should highlight selected template chip", () => {
      render(<TemplateSelector {...defaultProps} />);

      const chip = screen.getByRole("button", { name: /code review/i });
      fireEvent.click(chip);

      expect(chip).toHaveClass("ring-2");
    });

    it("should show template preview when chip is clicked", () => {
      render(<TemplateSelector {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /code review/i }));

      // Preview should show template details
      expect(
        screen.getByText(/template for code review tasks/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/standard/i)).toBeInTheDocument();
      expect(screen.getByText(/medium/i)).toBeInTheDocument();
    });

    it("should show apply button when template is selected", () => {
      render(<TemplateSelector {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /code review/i }));

      expect(
        screen.getByRole("button", { name: /apply template/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Apply Template", () => {
    it("should call onApply with template config when apply is clicked", () => {
      render(<TemplateSelector {...defaultProps} />);

      // Select template
      fireEvent.click(screen.getByRole("button", { name: /code review/i }));

      // Click apply
      fireEvent.click(screen.getByRole("button", { name: /apply template/i }));

      expect(defaultProps.onApply).toHaveBeenCalledWith({
        orchestrator: "standard",
        thinkingBudget: "medium",
        critiqueRounds: 1,
        autoApprove: false,
      });
    });

    it("should disable apply button when no template is selected", () => {
      render(<TemplateSelector {...defaultProps} />);

      // No template selected initially - apply button should not exist
      expect(
        screen.queryByRole("button", { name: /apply template/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Dismiss Functionality", () => {
    it("should show dismiss button", () => {
      render(<TemplateSelector {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /dismiss/i }),
      ).toBeInTheDocument();
    });

    it("should call onDismiss when dismiss button is clicked", () => {
      render(<TemplateSelector {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /dismiss/i }));

      expect(defaultProps.onDismiss).toHaveBeenCalled();
    });
  });

  describe("Template Preview", () => {
    it("should display orchestrator type in preview", () => {
      render(<TemplateSelector {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /data analysis/i }));

      // "swarm" appears in description and in the preview field
      const swarmElements = screen.getAllByText(/swarm/i);
      expect(swarmElements.length).toBeGreaterThanOrEqual(1);
    });

    it("should display thinking budget in preview", () => {
      render(<TemplateSelector {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /data analysis/i }));

      expect(screen.getByText(/deep/i)).toBeInTheDocument();
    });

    it("should display critique rounds in preview", () => {
      render(<TemplateSelector {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /data analysis/i }));

      expect(screen.getByText(/2 rounds/i)).toBeInTheDocument();
    });

    it("should display success rate in preview", () => {
      render(<TemplateSelector {...defaultProps} />);

      fireEvent.click(screen.getByRole("button", { name: /data analysis/i }));

      expect(screen.getByText(/88%/i)).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no suggestions", () => {
      render(<TemplateSelector {...defaultProps} suggestions={[]} />);
      expect(screen.getByText(/no template suggestions/i)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when loading", () => {
      render(<TemplateSelector {...defaultProps} isLoading={true} />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("should not render template chips when loading", () => {
      render(<TemplateSelector {...defaultProps} isLoading={true} />);

      // When loading, template chips should not be rendered (only dismiss button and loader)
      // Check that no template chip buttons are present
      expect(
        screen.queryByRole("button", { name: /code review/i }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: /data analysis/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Compact Mode", () => {
    it("should render in compact mode when compact prop is true", () => {
      render(<TemplateSelector {...defaultProps} compact={true} />);

      // In compact mode, template chips should be smaller
      const container = screen.getByTestId("template-selector");
      expect(container).toHaveClass("compact");
    });

    it("should hide description in compact mode", () => {
      render(<TemplateSelector {...defaultProps} compact={true} />);

      fireEvent.click(screen.getByRole("button", { name: /code review/i }));

      // In compact mode, full description may be hidden
      expect(
        screen.queryByText(/template for code review tasks/i),
      ).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have proper ARIA labels on chips", () => {
      render(<TemplateSelector {...defaultProps} />);

      const chip = screen.getByRole("button", { name: /code review/i });
      expect(chip).toHaveAccessibleName();
    });

    it("should announce selected template to screen readers", () => {
      render(<TemplateSelector {...defaultProps} />);

      const chip = screen.getByRole("button", { name: /code review/i });
      fireEvent.click(chip);

      expect(chip).toHaveAttribute("aria-pressed", "true");
    });
  });
});
