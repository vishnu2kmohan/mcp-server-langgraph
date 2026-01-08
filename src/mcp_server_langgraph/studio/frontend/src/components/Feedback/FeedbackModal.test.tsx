/**
 * FeedbackModal Tests
 *
 * TDD tests for NPS/CSAT feedback collection modal.
 * Tests cover:
 * - Modal visibility and open/close
 * - NPS score selection (0-10 scale)
 * - CSAT rating selection (1-5 stars)
 * - Optional comment input
 * - Form submission
 * - Loading and success states
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { FeedbackModal } from "./FeedbackModal";

// Mock RTK Query hooks
const mockSubmitFeedback = vi.fn().mockReturnValue({
  unwrap: () => Promise.resolve({ success: true }),
});

vi.mock("../../api", () => ({
  useSubmitFeedbackMutation: vi.fn(() => [
    mockSubmitFeedback,
    { isLoading: false, isSuccess: false },
  ]),
}));

import { useSubmitFeedbackMutation } from "../../api";
const mockUseSubmitFeedbackMutation = vi.mocked(useSubmitFeedbackMutation);

// Minimal store for testing
const createTestStore = () => {
  return configureStore({
    reducer: {
      api: (state = {}) => state,
    },
  });
};

const renderWithStore = (component: React.ReactNode) => {
  const store = createTestStore();
  return {
    store,
    ...render(<Provider store={store}>{component}</Provider>),
  };
};

describe("FeedbackModal", () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    mockSubmitFeedback.mockReset();
    mockSubmitFeedback.mockReturnValue({
      unwrap: () => Promise.resolve({ success: true }),
    });
    mockUseSubmitFeedbackMutation.mockImplementation(() => [
      mockSubmitFeedback,
      { isLoading: false, isSuccess: false },
    ]);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should render when isOpen is true", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(screen.getByTestId("feedback-modal")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      renderWithStore(<FeedbackModal {...defaultProps} isOpen={false} />);

      expect(screen.queryByTestId("feedback-modal")).not.toBeInTheDocument();
    });

    it("should display modal title", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(screen.getByText(/share your feedback/i)).toBeInTheDocument();
    });

    it("should have close button", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(screen.getByTestId("close-feedback-modal")).toBeInTheDocument();
    });

    it("should call onClose when close button is clicked", () => {
      const onClose = vi.fn();
      renderWithStore(<FeedbackModal {...defaultProps} onClose={onClose} />);

      fireEvent.click(screen.getByTestId("close-feedback-modal"));

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("NPS Score Selection", () => {
    it("should display NPS question", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(screen.getByText(/how likely.*recommend/i)).toBeInTheDocument();
    });

    it("should display NPS scale (0-10)", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      for (let i = 0; i <= 10; i++) {
        expect(screen.getByTestId(`nps-score-${i}`)).toBeInTheDocument();
      }
    });

    it("should highlight selected NPS score", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      const score7 = screen.getByTestId("nps-score-7");
      fireEvent.click(score7);

      expect(score7).toHaveClass("bg-primary-600");
    });

    it("should allow changing NPS score selection", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      fireEvent.click(screen.getByTestId("nps-score-5"));
      fireEvent.click(screen.getByTestId("nps-score-9"));

      expect(screen.getByTestId("nps-score-5")).not.toHaveClass(
        "bg-primary-600",
      );
      expect(screen.getByTestId("nps-score-9")).toHaveClass("bg-primary-600");
    });

    it("should display NPS scale labels", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(screen.getByText(/not likely/i)).toBeInTheDocument();
      expect(screen.getByText(/very likely/i)).toBeInTheDocument();
    });
  });

  describe("CSAT Rating", () => {
    it("should display CSAT question", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(screen.getByText(/satisfaction/i)).toBeInTheDocument();
    });

    it("should display 5-star rating", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      for (let i = 1; i <= 5; i++) {
        expect(screen.getByTestId(`csat-star-${i}`)).toBeInTheDocument();
      }
    });

    it("should fill stars on selection", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      fireEvent.click(screen.getByTestId("csat-star-4"));

      // Stars 1-4 should be filled
      expect(screen.getByTestId("csat-star-1")).toHaveClass("text-warning-400");
      expect(screen.getByTestId("csat-star-2")).toHaveClass("text-warning-400");
      expect(screen.getByTestId("csat-star-3")).toHaveClass("text-warning-400");
      expect(screen.getByTestId("csat-star-4")).toHaveClass("text-warning-400");
      // Star 5 should not be filled
      expect(screen.getByTestId("csat-star-5")).not.toHaveClass(
        "text-warning-400",
      );
    });
  });

  describe("Comment Input", () => {
    it("should display comment textarea", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(
        screen.getByPlaceholderText(/additional comments/i),
      ).toBeInTheDocument();
    });

    it("should accept text input", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      const textarea = screen.getByPlaceholderText(/additional comments/i);
      fireEvent.change(textarea, { target: { value: "Great product!" } });

      expect(textarea).toHaveValue("Great product!");
    });
  });

  describe("Form Submission", () => {
    it("should have submit button", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /submit/i }),
      ).toBeInTheDocument();
    });

    it("should disable submit button when no rating is selected", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(screen.getByRole("button", { name: /submit/i })).toBeDisabled();
    });

    it("should enable submit button when NPS score is selected", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      fireEvent.click(screen.getByTestId("nps-score-8"));

      expect(
        screen.getByRole("button", { name: /submit/i }),
      ).not.toBeDisabled();
    });

    it("should call API when form is submitted", async () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      fireEvent.click(screen.getByTestId("nps-score-9"));
      fireEvent.click(screen.getByTestId("csat-star-5"));
      fireEvent.change(screen.getByPlaceholderText(/additional comments/i), {
        target: { value: "Love it!" },
      });
      fireEvent.click(screen.getByRole("button", { name: /submit/i }));

      await waitFor(() => {
        expect(mockSubmitFeedback).toHaveBeenCalledWith({
          nps_score: 9,
          csat_rating: 5,
          comment: "Love it!",
        });
      });
    });

    it("should show loading state during submission", () => {
      mockUseSubmitFeedbackMutation.mockImplementation(() => [
        mockSubmitFeedback,
        { isLoading: true, isSuccess: false },
      ]);

      renderWithStore(<FeedbackModal {...defaultProps} />);

      fireEvent.click(screen.getByTestId("nps-score-8"));

      expect(screen.getByTestId("submit-loading")).toBeInTheDocument();
    });

    it("should show success message after submission", () => {
      mockUseSubmitFeedbackMutation.mockImplementation(() => [
        mockSubmitFeedback,
        { isLoading: false, isSuccess: true },
      ]);

      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(screen.getByText(/thank you/i)).toBeInTheDocument();
    });

    it("should close modal after success acknowledgment", async () => {
      const onClose = vi.fn();
      mockUseSubmitFeedbackMutation.mockImplementation(() => [
        mockSubmitFeedback,
        { isLoading: false, isSuccess: true },
      ]);

      renderWithStore(<FeedbackModal {...defaultProps} onClose={onClose} />);

      fireEvent.click(screen.getByRole("button", { name: /close|done/i }));

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have aria-labelledby on modal", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      const modal = screen.getByTestId("feedback-modal");
      expect(modal).toHaveAttribute("aria-labelledby");
    });

    it("should have role=dialog", () => {
      renderWithStore(<FeedbackModal {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
  });
});
