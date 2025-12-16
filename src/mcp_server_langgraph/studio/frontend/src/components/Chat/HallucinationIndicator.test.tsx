/**
 * HallucinationIndicator Component Tests
 *
 * TDD tests for AI hallucination detection and reporting UI.
 * Allows users to flag potential AI inaccuracies.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import {
  HallucinationIndicator,
  HallucinationIndicatorProps,
} from "./HallucinationIndicator";

describe("HallucinationIndicator", () => {
  const defaultProps: HallucinationIndicatorProps = {
    messageId: "msg-123",
    onReport: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should render flag button", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /report|flag/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Report Dialog", () => {
    it("should open dialog when flag button clicked", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should display report title", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));
      expect(screen.getByText(/report inaccuracy/i)).toBeInTheDocument();
    });

    it("should show category options", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      expect(screen.getByText(/factual error/i)).toBeInTheDocument();
      expect(screen.getByText(/outdated information/i)).toBeInTheDocument();
      expect(screen.getByText(/incorrect citation/i)).toBeInTheDocument();
      expect(screen.getByText(/made up information/i)).toBeInTheDocument();
    });

    it("should allow selecting a category", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      const factualErrorButton = screen
        .getByText(/factual error/i)
        .closest("button");
      fireEvent.click(factualErrorButton!);

      expect(factualErrorButton).toHaveAttribute("aria-pressed", "true");
    });

    it("should have optional details textarea", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      expect(
        screen.getByPlaceholderText(/provide additional details/i),
      ).toBeInTheDocument();
    });
  });

  describe("Submission", () => {
    it("should disable submit until category selected", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      const submitButton = screen.getByRole("button", { name: /submit/i });
      expect(submitButton).toBeDisabled();
    });

    it("should enable submit after category selected", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      fireEvent.click(screen.getByText(/factual error/i).closest("button")!);
      const submitButton = screen.getByRole("button", { name: /submit/i });
      expect(submitButton).not.toBeDisabled();
    });

    it("should call onReport with correct data", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      // Select category
      fireEvent.click(screen.getByText(/factual error/i).closest("button")!);

      // Add details
      const textarea = screen.getByPlaceholderText(
        /provide additional details/i,
      );
      fireEvent.change(textarea, {
        target: { value: "The date is incorrect" },
      });

      // Submit
      fireEvent.click(screen.getByRole("button", { name: /submit/i }));

      expect(defaultProps.onReport).toHaveBeenCalledWith({
        messageId: "msg-123",
        category: "factual_error",
        details: "The date is incorrect",
        timestamp: expect.any(Number),
      });
    });

    it("should close dialog after submission", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      fireEvent.click(screen.getByText(/factual error/i).closest("button")!);
      fireEvent.click(screen.getByRole("button", { name: /submit/i }));

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should show thank you message after submission", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      fireEvent.click(screen.getByText(/factual error/i).closest("button")!);
      fireEvent.click(screen.getByRole("button", { name: /submit/i }));

      expect(screen.getByText(/thank you/i)).toBeInTheDocument();
    });
  });

  describe("Cancel", () => {
    it("should have cancel button", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
    });

    it("should close dialog on cancel", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should not call onReport on cancel", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(defaultProps.onReport).not.toHaveBeenCalled();
    });
  });

  describe("Already Reported", () => {
    it("should show reported state when isReported is true", () => {
      render(<HallucinationIndicator {...defaultProps} isReported={true} />);
      expect(screen.getByText(/reported/i)).toBeInTheDocument();
    });

    it("should not render flag button when already reported", () => {
      render(<HallucinationIndicator {...defaultProps} isReported={true} />);
      // Flag button should not be present when already reported
      expect(
        screen.queryByRole("button", { name: /report|flag/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible button label", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      const button = screen.getByRole("button", { name: /report|flag/i });
      expect(button).toHaveAttribute("aria-label");
    });

    it("should have modal dialog role", () => {
      render(<HallucinationIndicator {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });
  });
});
