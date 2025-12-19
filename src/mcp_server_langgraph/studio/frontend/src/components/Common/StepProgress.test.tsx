/**
 * StepProgress Tests
 *
 * TDD tests for the Step Progress component.
 * Tests cover:
 * - Multi-step workflow display
 * - Step states (pending, current, completed, error)
 * - Step navigation
 * - Horizontal and vertical layouts
 * - WCAG 2.1 AA accessibility
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { StepProgress } from "./StepProgress";

expect.extend(toHaveNoViolations);

const mockSteps = [
  { id: "1", label: "Upload Files", description: "Select files to upload" },
  { id: "2", label: "Process", description: "Processing your files" },
  { id: "3", label: "Review", description: "Review the results" },
  { id: "4", label: "Complete", description: "Finish the workflow" },
];

describe("StepProgress", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render all steps", () => {
      render(<StepProgress steps={mockSteps} currentStep={0} />);

      expect(screen.getByText("Upload Files")).toBeInTheDocument();
      expect(screen.getByText("Process")).toBeInTheDocument();
      expect(screen.getByText("Review")).toBeInTheDocument();
      expect(screen.getByText("Complete")).toBeInTheDocument();
    });

    it("should render step numbers", () => {
      render(<StepProgress steps={mockSteps} currentStep={0} showNumbers />);

      expect(screen.getByText("1")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
      expect(screen.getByText("4")).toBeInTheDocument();
    });

    it("should render step descriptions when showDescriptions is true", () => {
      render(
        <StepProgress steps={mockSteps} currentStep={0} showDescriptions />,
      );

      expect(screen.getByText("Select files to upload")).toBeInTheDocument();
      expect(screen.getByText("Processing your files")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Step States Tests
  // ===========================================================================

  describe("step states", () => {
    it("should mark completed steps", () => {
      render(<StepProgress steps={mockSteps} currentStep={2} />);

      expect(screen.getByTestId("step-1")).toHaveAttribute(
        "data-status",
        "completed",
      );
      expect(screen.getByTestId("step-2")).toHaveAttribute(
        "data-status",
        "completed",
      );
    });

    it("should mark current step", () => {
      render(<StepProgress steps={mockSteps} currentStep={1} />);

      expect(screen.getByTestId("step-2")).toHaveAttribute(
        "data-status",
        "current",
      );
    });

    it("should mark pending steps", () => {
      render(<StepProgress steps={mockSteps} currentStep={1} />);

      expect(screen.getByTestId("step-3")).toHaveAttribute(
        "data-status",
        "pending",
      );
      expect(screen.getByTestId("step-4")).toHaveAttribute(
        "data-status",
        "pending",
      );
    });

    it("should mark error step", () => {
      render(<StepProgress steps={mockSteps} currentStep={2} errorStep={2} />);

      expect(screen.getByTestId("step-3")).toHaveAttribute(
        "data-status",
        "error",
      );
    });

    it("should show check icon for completed steps", () => {
      render(<StepProgress steps={mockSteps} currentStep={2} />);

      const completedSteps = screen.getAllByTestId("step-completed-icon");
      expect(completedSteps).toHaveLength(2);
    });
  });

  // ===========================================================================
  // Navigation Tests
  // ===========================================================================

  describe("navigation", () => {
    it("should call onStepClick when step is clicked", async () => {
      const onStepClick = vi.fn();
      const user = userEvent.setup();
      render(
        <StepProgress
          steps={mockSteps}
          currentStep={2}
          onStepClick={onStepClick}
        />,
      );

      await user.click(screen.getByText("Upload Files"));

      expect(onStepClick).toHaveBeenCalledWith(0);
    });

    it("should allow clicking completed steps", async () => {
      const onStepClick = vi.fn();
      const user = userEvent.setup();
      render(
        <StepProgress
          steps={mockSteps}
          currentStep={2}
          onStepClick={onStepClick}
        />,
      );

      await user.click(screen.getByText("Process"));

      expect(onStepClick).toHaveBeenCalledWith(1);
    });

    it("should disable clicking future steps when allowFutureSteps is false", async () => {
      const onStepClick = vi.fn();
      const user = userEvent.setup();
      render(
        <StepProgress
          steps={mockSteps}
          currentStep={1}
          onStepClick={onStepClick}
          allowFutureSteps={false}
        />,
      );

      await user.click(screen.getByText("Review"));

      expect(onStepClick).not.toHaveBeenCalled();
    });

    it("should allow clicking future steps when allowFutureSteps is true", async () => {
      const onStepClick = vi.fn();
      const user = userEvent.setup();
      render(
        <StepProgress
          steps={mockSteps}
          currentStep={1}
          onStepClick={onStepClick}
          allowFutureSteps={true}
        />,
      );

      await user.click(screen.getByText("Review"));

      expect(onStepClick).toHaveBeenCalledWith(2);
    });
  });

  // ===========================================================================
  // Layout Tests
  // ===========================================================================

  describe("layout", () => {
    it("should render horizontal layout by default", () => {
      render(<StepProgress steps={mockSteps} currentStep={0} />);

      expect(screen.getByTestId("step-progress")).toHaveAttribute(
        "data-orientation",
        "horizontal",
      );
    });

    it("should render vertical layout", () => {
      render(
        <StepProgress
          steps={mockSteps}
          currentStep={0}
          orientation="vertical"
        />,
      );

      expect(screen.getByTestId("step-progress")).toHaveAttribute(
        "data-orientation",
        "vertical",
      );
    });
  });

  // ===========================================================================
  // Connector Lines Tests
  // ===========================================================================

  describe("connector lines", () => {
    it("should render connector lines between steps", () => {
      render(<StepProgress steps={mockSteps} currentStep={0} />);

      const connectors = screen.getAllByTestId("step-connector");
      expect(connectors).toHaveLength(3); // n-1 connectors for n steps
    });

    it("should style completed connectors differently", () => {
      render(<StepProgress steps={mockSteps} currentStep={2} />);

      const connectors = screen.getAllByTestId("step-connector");
      expect(connectors[0]).toHaveAttribute("data-completed", "true");
      expect(connectors[1]).toHaveAttribute("data-completed", "true");
      expect(connectors[2]).toHaveAttribute("data-completed", "false");
    });
  });

  // ===========================================================================
  // Size Variants Tests
  // ===========================================================================

  describe("size variants", () => {
    it("should render small size", () => {
      render(<StepProgress steps={mockSteps} currentStep={0} size="sm" />);

      expect(screen.getByTestId("step-progress")).toHaveAttribute(
        "data-size",
        "sm",
      );
    });

    it("should render medium size by default", () => {
      render(<StepProgress steps={mockSteps} currentStep={0} />);

      expect(screen.getByTestId("step-progress")).toHaveAttribute(
        "data-size",
        "md",
      );
    });

    it("should render large size", () => {
      render(<StepProgress steps={mockSteps} currentStep={0} size="lg" />);

      expect(screen.getByTestId("step-progress")).toHaveAttribute(
        "data-size",
        "lg",
      );
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <StepProgress steps={mockSteps} currentStep={1} />,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper navigation role", () => {
      render(<StepProgress steps={mockSteps} currentStep={1} />);

      expect(screen.getByRole("navigation")).toBeInTheDocument();
    });

    it("should have aria-current for current step", () => {
      render(<StepProgress steps={mockSteps} currentStep={1} />);

      expect(screen.getByTestId("step-2")).toHaveAttribute(
        "aria-current",
        "step",
      );
    });

    it("should have aria-label for navigation", () => {
      render(
        <StepProgress
          steps={mockSteps}
          currentStep={1}
          ariaLabel="Workflow progress"
        />,
      );

      expect(screen.getByRole("navigation")).toHaveAttribute(
        "aria-label",
        "Workflow progress",
      );
    });

    it("should have proper step button labels for screen readers", () => {
      render(
        <StepProgress
          steps={mockSteps}
          currentStep={2}
          onStepClick={() => {}}
        />,
      );

      expect(
        screen.getByRole("button", { name: /upload files.*completed/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Custom ClassName Tests
  // ===========================================================================

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(
        <StepProgress
          steps={mockSteps}
          currentStep={0}
          className="custom-class"
        />,
      );

      expect(screen.getByTestId("step-progress")).toHaveClass("custom-class");
    });
  });
});
