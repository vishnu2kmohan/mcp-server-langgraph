/**
 * GuidedTour Component Tests
 *
 * TDD tests for the guided tour feature.
 * Highlights key interface elements and explains their purpose.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { GuidedTour, GuidedTourProps, TourStep } from "./GuidedTour";

const mockSteps: TourStep[] = [
  {
    target: "#sidebar-navigation",
    title: "Sidebar Navigation",
    content: "Navigate between pages using the sidebar menu.",
    position: "right",
  },
  {
    target: "#command-palette-trigger",
    title: "Command Palette",
    content: "Press Cmd+K to quickly search and navigate.",
    position: "bottom",
  },
  {
    target: "#new-session-button",
    title: "Start New Session",
    content: "Click here to start a new chat session.",
    position: "left",
  },
];

describe("GuidedTour", () => {
  const defaultProps: GuidedTourProps = {
    isActive: true,
    steps: mockSteps,
    onComplete: vi.fn(),
    onSkip: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should render when isActive is true", () => {
      render(<GuidedTour {...defaultProps} />);
      expect(screen.getByRole("tooltip")).toBeInTheDocument();
    });

    it("should not render when isActive is false", () => {
      render(<GuidedTour {...defaultProps} isActive={false} />);
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });

    it("should not render when steps array is empty", () => {
      render(<GuidedTour {...defaultProps} steps={[]} />);
      expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    });
  });

  describe("Step Display", () => {
    it("should display first step title", () => {
      render(<GuidedTour {...defaultProps} />);
      expect(screen.getByText("Sidebar Navigation")).toBeInTheDocument();
    });

    it("should display first step content", () => {
      render(<GuidedTour {...defaultProps} />);
      expect(screen.getByText(/navigate between pages/i)).toBeInTheDocument();
    });

    it("should show step counter", () => {
      render(<GuidedTour {...defaultProps} />);
      expect(screen.getByText(/1 of 3/i)).toBeInTheDocument();
    });
  });

  describe("Navigation", () => {
    it("should display Next button", () => {
      render(<GuidedTour {...defaultProps} />);
      expect(screen.getByRole("button", { name: /next/i })).toBeInTheDocument();
    });

    it("should advance to next step when Next clicked", () => {
      render(<GuidedTour {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      expect(screen.getByText("Command Palette")).toBeInTheDocument();
      expect(screen.getByText(/2 of 3/i)).toBeInTheDocument();
    });

    it("should show Previous button after first step", () => {
      render(<GuidedTour {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      expect(
        screen.getByRole("button", { name: /previous/i }),
      ).toBeInTheDocument();
    });

    it("should go back when Previous clicked", () => {
      render(<GuidedTour {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      fireEvent.click(screen.getByRole("button", { name: /previous/i }));
      expect(screen.getByText("Sidebar Navigation")).toBeInTheDocument();
    });

    it("should not show Previous on first step", () => {
      render(<GuidedTour {...defaultProps} />);
      expect(
        screen.queryByRole("button", { name: /previous/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Completion", () => {
    it("should show Finish button on last step", () => {
      render(<GuidedTour {...defaultProps} />);
      // Navigate to last step
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      expect(
        screen.getByRole("button", { name: /finish/i }),
      ).toBeInTheDocument();
    });

    it("should call onComplete when Finish clicked", () => {
      render(<GuidedTour {...defaultProps} />);
      // Navigate to last step and finish
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      fireEvent.click(screen.getByRole("button", { name: /finish/i }));
      expect(defaultProps.onComplete).toHaveBeenCalledWith({
        stepsCompleted: 3,
      });
    });
  });

  describe("Skip Functionality", () => {
    it("should show Skip button", () => {
      render(<GuidedTour {...defaultProps} />);
      expect(screen.getByRole("button", { name: /skip/i })).toBeInTheDocument();
    });

    it("should call onSkip when Skip clicked", () => {
      render(<GuidedTour {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /skip/i }));
      expect(defaultProps.onSkip).toHaveBeenCalledWith({ stepSkippedAt: 1 });
    });

    it("should report which step was skipped", () => {
      render(<GuidedTour {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      fireEvent.click(screen.getByRole("button", { name: /skip/i }));
      expect(defaultProps.onSkip).toHaveBeenCalledWith({ stepSkippedAt: 2 });
    });
  });

  describe("Keyboard Navigation", () => {
    it("should close on Escape key", () => {
      render(<GuidedTour {...defaultProps} />);
      fireEvent.keyDown(document, { key: "Escape" });
      expect(defaultProps.onSkip).toHaveBeenCalled();
    });

    it("should advance on ArrowRight key", () => {
      render(<GuidedTour {...defaultProps} />);
      fireEvent.keyDown(document, { key: "ArrowRight" });
      expect(screen.getByText("Command Palette")).toBeInTheDocument();
    });

    it("should go back on ArrowLeft key", () => {
      render(<GuidedTour {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      fireEvent.keyDown(document, { key: "ArrowLeft" });
      expect(screen.getByText("Sidebar Navigation")).toBeInTheDocument();
    });
  });

  describe("Progress Indicator", () => {
    it("should display progress dots", () => {
      render(<GuidedTour {...defaultProps} />);
      const progressDots = screen.getAllByTestId("tour-progress-dot");
      expect(progressDots).toHaveLength(3);
    });

    it("should highlight current step dot", () => {
      render(<GuidedTour {...defaultProps} />);
      const progressDots = screen.getAllByTestId("tour-progress-dot");
      expect(progressDots[0]).toHaveClass("bg-blue-500");
    });

    it("should update highlighted dot on navigation", () => {
      render(<GuidedTour {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /next/i }));
      const progressDots = screen.getAllByTestId("tour-progress-dot");
      expect(progressDots[1]).toHaveClass("bg-blue-500");
    });
  });

  describe("Backdrop", () => {
    it("should render spotlight overlay", () => {
      render(<GuidedTour {...defaultProps} />);
      expect(screen.getByTestId("tour-backdrop")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have tooltip role", () => {
      render(<GuidedTour {...defaultProps} />);
      expect(screen.getByRole("tooltip")).toBeInTheDocument();
    });

    it("should have accessible step description", () => {
      render(<GuidedTour {...defaultProps} />);
      const tooltip = screen.getByRole("tooltip");
      expect(tooltip).toHaveAttribute("aria-live", "polite");
    });
  });
});
