/**
 * ResponseRating Component Tests
 *
 * Tests for the thumbs up/down feedback component that allows users
 * to rate AI responses for quality feedback.
 *
 * TDD RED Phase: Write failing tests first.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { ResponseRating, type ResponseRatingProps } from "./ResponseRating";

describe("ResponseRating", () => {
  const mockOnRate = vi.fn();

  const defaultProps: ResponseRatingProps = {
    messageId: "msg-001",
    onRate: mockOnRate,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render thumbs up and thumbs down buttons", () => {
      render(<ResponseRating {...defaultProps} />);

      expect(screen.getByTestId("rating-thumbs-up")).toBeInTheDocument();
      expect(screen.getByTestId("rating-thumbs-down")).toBeInTheDocument();
    });

    it("should show neutral state initially when no rating provided", () => {
      render(<ResponseRating {...defaultProps} />);

      const thumbsUp = screen.getByTestId("rating-thumbs-up");
      const thumbsDown = screen.getByTestId("rating-thumbs-down");

      // Neither should be active initially
      expect(thumbsUp).not.toHaveClass("text-green-500");
      expect(thumbsDown).not.toHaveClass("text-red-500");
    });
  });

  describe("rating actions", () => {
    it("should call onRate with 'up' when thumbs up is clicked", () => {
      render(<ResponseRating {...defaultProps} />);

      fireEvent.click(screen.getByTestId("rating-thumbs-up"));

      expect(mockOnRate).toHaveBeenCalledWith("msg-001", "up");
    });

    it("should call onRate with 'down' when thumbs down is clicked", () => {
      render(<ResponseRating {...defaultProps} />);

      fireEvent.click(screen.getByTestId("rating-thumbs-down"));

      expect(mockOnRate).toHaveBeenCalledWith("msg-001", "down");
    });

    it("should call onRate with null when clicking active rating to remove", () => {
      render(<ResponseRating {...defaultProps} currentRating="up" />);

      fireEvent.click(screen.getByTestId("rating-thumbs-up"));

      expect(mockOnRate).toHaveBeenCalledWith("msg-001", null);
    });
  });

  describe("current rating display", () => {
    it("should highlight thumbs up when currentRating is up", () => {
      render(<ResponseRating {...defaultProps} currentRating="up" />);

      const thumbsUp = screen.getByTestId("rating-thumbs-up");
      expect(thumbsUp).toHaveClass("text-green-500");
    });

    it("should highlight thumbs down when currentRating is down", () => {
      render(<ResponseRating {...defaultProps} currentRating="down" />);

      const thumbsDown = screen.getByTestId("rating-thumbs-down");
      expect(thumbsDown).toHaveClass("text-red-500");
    });
  });

  describe("feedback text", () => {
    it("should show feedback text input when showFeedbackInput is true and rated down", () => {
      const mockOnFeedback = vi.fn();
      render(
        <ResponseRating
          {...defaultProps}
          currentRating="down"
          showFeedbackInput
          onFeedback={mockOnFeedback}
        />,
      );

      expect(screen.getByTestId("feedback-input")).toBeInTheDocument();
    });

    it("should not show feedback input for thumbs up rating", () => {
      render(
        <ResponseRating
          {...defaultProps}
          currentRating="up"
          showFeedbackInput
        />,
      );

      expect(screen.queryByTestId("feedback-input")).not.toBeInTheDocument();
    });

    it("should call onFeedback when feedback is submitted", async () => {
      const mockOnFeedback = vi.fn();
      render(
        <ResponseRating
          {...defaultProps}
          currentRating="down"
          showFeedbackInput
          onFeedback={mockOnFeedback}
        />,
      );

      const input = screen.getByTestId("feedback-input");
      fireEvent.change(input, { target: { value: "Response was incorrect" } });
      fireEvent.click(screen.getByTestId("submit-feedback"));

      expect(mockOnFeedback).toHaveBeenCalledWith(
        "msg-001",
        "Response was incorrect",
      );
    });
  });

  describe("loading state", () => {
    it("should disable buttons when isSubmitting is true", () => {
      render(<ResponseRating {...defaultProps} isSubmitting />);

      expect(screen.getByTestId("rating-thumbs-up")).toBeDisabled();
      expect(screen.getByTestId("rating-thumbs-down")).toBeDisabled();
    });

    it("should show loading indicator when isSubmitting", () => {
      render(<ResponseRating {...defaultProps} isSubmitting />);

      expect(screen.getByTestId("rating-loading")).toBeInTheDocument();
    });
  });

  describe("thank you message", () => {
    it("should show thank you message after rating", async () => {
      render(
        <ResponseRating {...defaultProps} currentRating="up" showThankYou />,
      );

      expect(screen.getByText(/thank you/i)).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have aria-label on buttons", () => {
      render(<ResponseRating {...defaultProps} />);

      expect(screen.getByTestId("rating-thumbs-up")).toHaveAttribute(
        "aria-label",
        "Rate as helpful",
      );
      expect(screen.getByTestId("rating-thumbs-down")).toHaveAttribute(
        "aria-label",
        "Rate as not helpful",
      );
    });

    it("should have aria-pressed reflecting current state", () => {
      render(<ResponseRating {...defaultProps} currentRating="up" />);

      expect(screen.getByTestId("rating-thumbs-up")).toHaveAttribute(
        "aria-pressed",
        "true",
      );
      expect(screen.getByTestId("rating-thumbs-down")).toHaveAttribute(
        "aria-pressed",
        "false",
      );
    });

    it("should support keyboard navigation", () => {
      render(<ResponseRating {...defaultProps} />);

      const thumbsUp = screen.getByTestId("rating-thumbs-up");
      fireEvent.keyDown(thumbsUp, { key: "Enter" });

      expect(mockOnRate).toHaveBeenCalledWith("msg-001", "up");
    });
  });

  describe("compact mode", () => {
    it("should render smaller buttons in compact mode", () => {
      render(<ResponseRating {...defaultProps} compact />);

      const container = screen.getByTestId("response-rating-container");
      expect(container).toHaveClass("gap-1");
    });
  });

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(<ResponseRating {...defaultProps} className="custom-class" />);

      const container = screen.getByTestId("response-rating-container");
      expect(container).toHaveClass("custom-class");
    });
  });
});
