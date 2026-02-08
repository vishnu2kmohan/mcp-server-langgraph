/**
 * HallucinationIndicator Component Tests
 *
 * TDD tests for AI hallucination detection and reporting UI.
 * Allows users to flag potential AI inaccuracies.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import {
  HallucinationIndicator,
  HallucinationIndicatorProps,
} from "./HallucinationIndicator";

import { TestProvider } from "@/test-utils";

describe("HallucinationIndicator", () => {
  const defaultProps: HallucinationIndicatorProps = {
    messageId: "msg-123",
    onReport: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should render flag button", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /report|flag/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Report Dialog", () => {
    it("should open dialog when flag button clicked", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should display report title", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));
      expect(screen.getByText(/report inaccuracy/i)).toBeInTheDocument();
    });

    it("should show category options", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      expect(screen.getByText(/factual error/i)).toBeInTheDocument();
      expect(screen.getByText(/outdated information/i)).toBeInTheDocument();
      expect(screen.getByText(/made up source/i)).toBeInTheDocument();
      expect(screen.getByText(/other issue/i)).toBeInTheDocument();
    });

    it("should allow selecting a category", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      const factualErrorButton = screen
        .getByText(/factual error/i)
        .closest("button");
      fireEvent.click(factualErrorButton!);

      // Uses radiogroup pattern with aria-checked (not aria-pressed)
      expect(factualErrorButton).toHaveAttribute("aria-checked", "true");
    });

    it("should use radiogroup pattern for single selection", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      expect(screen.getByRole("radiogroup")).toBeInTheDocument();
    });

    it("should have optional details textarea", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      expect(
        screen.getByPlaceholderText(/provide additional details/i),
      ).toBeInTheDocument();
    });
  });

  describe("Submission", () => {
    it("should disable submit until category selected", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      const submitButton = screen.getByRole("button", { name: /submit/i });
      expect(submitButton).toBeDisabled();
    });

    it("should enable submit after category selected", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      fireEvent.click(screen.getByText(/factual error/i).closest("button")!);
      const submitButton = screen.getByRole("button", { name: /submit/i });
      expect(submitButton).not.toBeDisabled();
    });

    it("should call onReport with correct data", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
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
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      fireEvent.click(screen.getByText(/factual error/i).closest("button")!);
      fireEvent.click(screen.getByRole("button", { name: /submit/i }));

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should show thank you message after submission", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      fireEvent.click(screen.getByText(/factual error/i).closest("button")!);
      fireEvent.click(screen.getByRole("button", { name: /submit/i }));

      expect(screen.getByText(/thank you/i)).toBeInTheDocument();
    });
  });

  describe("Cancel", () => {
    it("should have cancel button", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      expect(
        screen.getByRole("button", { name: /cancel/i }),
      ).toBeInTheDocument();
    });

    it("should close dialog on cancel", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should not call onReport on cancel", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));
      fireEvent.click(screen.getByRole("button", { name: /cancel/i }));

      expect(defaultProps.onReport).not.toHaveBeenCalled();
    });
  });

  describe("Already Reported", () => {
    it("should show reported state when isReported is true", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} isReported={true} />
        </TestProvider>,
      );
      expect(screen.getByText(/reported/i)).toBeInTheDocument();
    });

    it("should not render flag button when already reported", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} isReported={true} />
        </TestProvider>,
      );
      // Flag button should not be present when already reported
      expect(
        screen.queryByRole("button", { name: /report|flag/i }),
      ).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible button label", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      const button = screen.getByRole("button", { name: /report|flag/i });
      expect(button).toHaveAttribute("aria-label");
    });

    it("should have modal dialog role", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });

    it("should have aria-labelledby and aria-describedby on dialog", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby");
      expect(dialog).toHaveAttribute("aria-describedby");
    });

    it("should close dialog on ESC key", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));
      expect(screen.getByRole("dialog")).toBeInTheDocument();

      fireEvent.keyDown(document, { key: "Escape" });
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should have role=status with aria-label for reported state", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} isReported={true} />
        </TestProvider>,
      );
      const status = screen.getByRole("status");
      expect(status).toHaveAttribute(
        "aria-label",
        "This message has been reported as inaccurate",
      );
    });

    it("should have role=status with aria-live for thank you message", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));
      fireEvent.click(screen.getByText(/factual error/i).closest("button")!);
      fireEvent.click(screen.getByRole("button", { name: /submit/i }));

      const status = screen.getByRole("status");
      expect(status).toHaveAttribute("aria-live", "polite");
    });

    it("should have associated label for details textarea", () => {
      render(
        <TestProvider>
          <HallucinationIndicator {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /report|flag/i }));

      const textarea = screen.getByLabelText(/additional details/i);
      expect(textarea).toHaveAttribute("id", "hallucination-details");
    });
  });
});
