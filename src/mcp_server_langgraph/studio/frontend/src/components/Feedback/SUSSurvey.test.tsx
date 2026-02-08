/**
 * SUSSurvey Component Tests
 *
 * TDD tests for the System Usability Scale survey component.
 * Tests cover:
 * - All 10 SUS questions displayed
 * - Rating scale (1-5) for each question
 * - Score calculation
 * - Submission handling
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { SUSSurvey } from "./SUSSurvey";

import { TestProvider } from "@/test-utils";

describe("SUSSurvey", () => {
  const defaultProps = {
    onSubmit: vi.fn(),
    onDismiss: vi.fn(),
  };

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render survey title", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/System Usability Survey/i)).toBeInTheDocument();
    });

    it("should render all 10 SUS questions", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      // Standard SUS questions
      expect(
        screen.getByText(/I think that I would like to use this system/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/I found the system unnecessarily complex/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/I thought the system was easy to use/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/I would need support of a technical person/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/various functions.*well integrated/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/too much inconsistency/i)).toBeInTheDocument();
      expect(
        screen.getByText(/most people would learn.*very quickly/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/very cumbersome to use/i)).toBeInTheDocument();
      expect(screen.getByText(/I felt very confident/i)).toBeInTheDocument();
      expect(
        screen.getByText(/I needed to learn a lot of things/i),
      ).toBeInTheDocument();
    });

    it("should render 5-point scale for each question", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      // Each question has 5 radio buttons (Strongly Disagree to Strongly Agree)
      const radioGroups = screen.getAllByRole("radiogroup");
      expect(radioGroups).toHaveLength(10);
    });

    it("should show scale labels", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Strongly Disagree")).toBeInTheDocument();
      expect(screen.getByText("Strongly Agree")).toBeInTheDocument();
    });
  });

  describe("Rating Selection", () => {
    it("should allow selecting a rating for each question", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      const firstQuestionRadios = screen.getAllByRole("radio").slice(0, 5);
      fireEvent.click(firstQuestionRadios[3]); // Select rating 4

      expect(firstQuestionRadios[3]).toBeChecked();
    });

    it("should highlight selected rating", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      const firstQuestionRadios = screen.getAllByRole("radio").slice(0, 5);
      fireEvent.click(firstQuestionRadios[2]); // Select rating 3

      // Selected radio should be visually highlighted
      expect(firstQuestionRadios[2]).toBeChecked();
    });
  });

  describe("Submission", () => {
    it("should disable submit button until all questions answered", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      const submitButton = screen.getByRole("button", { name: /submit/i });
      expect(submitButton).toBeDisabled();
    });

    it("should enable submit button when all questions answered", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      // Answer all 10 questions
      const radios = screen.getAllByRole("radio");
      for (let i = 0; i < 10; i++) {
        fireEvent.click(radios[i * 5 + 2]); // Select middle rating for each
      }

      const submitButton = screen.getByRole("button", { name: /submit/i });
      expect(submitButton).toBeEnabled();
    });

    it("should call onSubmit with calculated SUS score", () => {
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} onSubmit={onSubmit} />
        </TestProvider>,
      );

      // Answer all 10 questions with rating 3 (middle)
      const radios = screen.getAllByRole("radio");
      for (let i = 0; i < 10; i++) {
        fireEvent.click(radios[i * 5 + 2]); // Rating 3 for each
      }

      const submitButton = screen.getByRole("button", { name: /submit/i });
      fireEvent.click(submitButton);

      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          score: expect.any(Number),
          responses: expect.any(Array),
        }),
      );
    });

    it("should calculate correct SUS score", () => {
      const onSubmit = vi.fn();
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} onSubmit={onSubmit} />
        </TestProvider>,
      );

      // Answer odd questions (1,3,5,7,9) with 5 and even questions (2,4,6,8,10) with 1
      // This gives max score: (5-1)*5 + (5-1)*5 = 20*2.5 = 50... wait
      // SUS formula: For odd items (positive): score - 1
      // For even items (negative): 5 - score
      // Sum * 2.5 = SUS score
      // All 5s for odd, all 1s for even: (4+4+4+4+4 + 4+4+4+4+4) * 2.5 = 40 * 2.5 = 100
      const radios = screen.getAllByRole("radio");
      for (let i = 0; i < 10; i++) {
        if (i % 2 === 0) {
          // Odd questions (index 0, 2, 4...) - positive statements
          fireEvent.click(radios[i * 5 + 4]); // Rating 5
        } else {
          // Even questions (index 1, 3, 5...) - negative statements
          fireEvent.click(radios[i * 5]); // Rating 1
        }
      }

      const submitButton = screen.getByRole("button", { name: /submit/i });
      fireEvent.click(submitButton);

      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          score: 100,
        }),
      );
    });
  });

  describe("Dismissal", () => {
    it("should render dismiss button", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /maybe later/i }),
      ).toBeInTheDocument();
    });

    it("should call onDismiss when dismiss button clicked", () => {
      const onDismiss = vi.fn();
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} onDismiss={onDismiss} />
        </TestProvider>,
      );

      const dismissButton = screen.getByRole("button", {
        name: /maybe later/i,
      });
      fireEvent.click(dismissButton);

      expect(onDismiss).toHaveBeenCalled();
    });
  });

  describe("Progress", () => {
    it("should show progress indicator", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/0 of 10/i)).toBeInTheDocument();
    });

    it("should update progress as questions are answered", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      const radios = screen.getAllByRole("radio");
      fireEvent.click(radios[2]); // Answer first question

      expect(screen.getByText(/1 of 10/i)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible question labels", () => {
      render(
        <TestProvider>
          <SUSSurvey {...defaultProps} />
        </TestProvider>,
      );

      const radioGroups = screen.getAllByRole("radiogroup");
      radioGroups.forEach((group) => {
        expect(group).toHaveAttribute("aria-labelledby");
      });
    });
  });
});
