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

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { StepProgress } from "./StepProgress";

import { TestProvider } from "@/test-utils";

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

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render all steps", () => {
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={0} />
        </TestProvider>,
      );

      expect(screen.getByText("Upload Files")).toBeInTheDocument();
      expect(screen.getByText("Process")).toBeInTheDocument();
      expect(screen.getByText("Review")).toBeInTheDocument();
      expect(screen.getByText("Complete")).toBeInTheDocument();
    });

    it("should render step numbers", () => {
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={0} showNumbers />
        </TestProvider>,
      );

      expect(screen.getByText("1")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
      expect(screen.getByText("4")).toBeInTheDocument();
    });

    it("should render step descriptions when showDescriptions is true", () => {
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={0} showDescriptions />
        </TestProvider>,
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
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={2} />
        </TestProvider>,
      );

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
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={1} />
        </TestProvider>,
      );

      expect(screen.getByTestId("step-2")).toHaveAttribute(
        "data-status",
        "current",
      );
    });

    it("should mark pending steps", () => {
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={1} />
        </TestProvider>,
      );

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
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={2} errorStep={2} />
        </TestProvider>,
      );

      expect(screen.getByTestId("step-3")).toHaveAttribute(
        "data-status",
        "error",
      );
    });

    it("should show check icon for completed steps", () => {
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={2} />
        </TestProvider>,
      );

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
        <TestProvider>
          <StepProgress
            steps={mockSteps}
            currentStep={2}
            onStepClick={onStepClick}
          />
        </TestProvider>,
      );

      await user.click(screen.getByText("Upload Files"));

      expect(onStepClick).toHaveBeenCalledWith(0);
    });

    it("should allow clicking completed steps", async () => {
      const onStepClick = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <StepProgress
            steps={mockSteps}
            currentStep={2}
            onStepClick={onStepClick}
          />
        </TestProvider>,
      );

      await user.click(screen.getByText("Process"));

      expect(onStepClick).toHaveBeenCalledWith(1);
    });

    it("should disable clicking future steps when allowFutureSteps is false", async () => {
      const onStepClick = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <StepProgress
            steps={mockSteps}
            currentStep={1}
            onStepClick={onStepClick}
            allowFutureSteps={false}
          />
        </TestProvider>,
      );

      await user.click(screen.getByText("Review"));

      expect(onStepClick).not.toHaveBeenCalled();
    });

    it("should allow clicking future steps when allowFutureSteps is true", async () => {
      const onStepClick = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <StepProgress
            steps={mockSteps}
            currentStep={1}
            onStepClick={onStepClick}
            allowFutureSteps={true}
          />
        </TestProvider>,
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
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={0} />
        </TestProvider>,
      );

      expect(screen.getByTestId("step-progress")).toHaveAttribute(
        "data-orientation",
        "horizontal",
      );
    });

    it("should render vertical layout", () => {
      render(
        <TestProvider>
          <StepProgress
            steps={mockSteps}
            currentStep={0}
            orientation="vertical"
          />
        </TestProvider>,
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
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={0} />
        </TestProvider>,
      );

      const connectors = screen.getAllByTestId("step-connector");
      expect(connectors).toHaveLength(3); // n-1 connectors for n steps
    });

    it("should style completed connectors differently", () => {
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={2} />
        </TestProvider>,
      );

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
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={0} size="sm" />
        </TestProvider>,
      );

      expect(screen.getByTestId("step-progress")).toHaveAttribute(
        "data-size",
        "sm",
      );
    });

    it("should render medium size by default", () => {
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={0} />
        </TestProvider>,
      );

      expect(screen.getByTestId("step-progress")).toHaveAttribute(
        "data-size",
        "md",
      );
    });

    it("should render large size", () => {
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={0} size="lg" />
        </TestProvider>,
      );

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
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={1} />
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper navigation role", () => {
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={1} />
        </TestProvider>,
      );

      expect(screen.getByRole("navigation")).toBeInTheDocument();
    });

    it("should have aria-current for current step", () => {
      render(
        <TestProvider>
          <StepProgress steps={mockSteps} currentStep={1} />
        </TestProvider>,
      );

      expect(screen.getByTestId("step-2")).toHaveAttribute(
        "aria-current",
        "step",
      );
    });

    it("should have aria-label for navigation", () => {
      render(
        <TestProvider>
          <StepProgress
            steps={mockSteps}
            currentStep={1}
            ariaLabel="Workflow progress"
          />
        </TestProvider>,
      );

      expect(screen.getByRole("navigation")).toHaveAttribute(
        "aria-label",
        "Workflow progress",
      );
    });

    it("should have proper step button labels for screen readers", () => {
      render(
        <TestProvider>
          <StepProgress
            steps={mockSteps}
            currentStep={2}
            onStepClick={() => {}}
          />
        </TestProvider>,
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
        <TestProvider>
          <StepProgress
            steps={mockSteps}
            currentStep={0}
            className="custom-class"
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("step-progress")).toHaveClass("custom-class");
    });
  });
});
