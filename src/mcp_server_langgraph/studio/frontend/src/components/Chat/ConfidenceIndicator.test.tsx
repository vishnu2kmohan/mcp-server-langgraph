/**
 * ConfidenceIndicator Component Tests
 *
 * TDD tests for the AI confidence score visualization.
 * Tests cover:
 * - Score display
 * - Visual indicators (color coding)
 * - Warning badges for low confidence
 * - Accessibility
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ConfidenceIndicator } from "./ConfidenceIndicator";

describe("ConfidenceIndicator", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
  describe("Score Display", () => {
    it("should render confidence score as percentage", () => {
      render(<ConfidenceIndicator score={0.92} />);

      expect(screen.getByText("92%")).toBeInTheDocument();
    });

    it("should round score to nearest integer", () => {
      render(<ConfidenceIndicator score={0.876} />);

      expect(screen.getByText("88%")).toBeInTheDocument();
    });
  });

  describe("Visual Indicators", () => {
    it("should show green indicator for high confidence (>= 0.8)", () => {
      render(<ConfidenceIndicator score={0.92} />);

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-green-600");
    });

    it("should show yellow indicator for medium confidence (0.6-0.79)", () => {
      render(<ConfidenceIndicator score={0.72} />);

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-yellow-600");
    });

    it("should show red indicator for low confidence (< 0.6)", () => {
      render(<ConfidenceIndicator score={0.45} />);

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-red-600");
    });
  });

  describe("Low Confidence Warning", () => {
    it("should show warning badge for low confidence", () => {
      render(<ConfidenceIndicator score={0.45} />);

      expect(screen.getByText(/verify this information/i)).toBeInTheDocument();
    });

    it("should not show warning for high confidence", () => {
      render(<ConfidenceIndicator score={0.92} />);

      expect(
        screen.queryByText(/verify this information/i),
      ).not.toBeInTheDocument();
    });

    it("should show warning icon for scores below 0.7", () => {
      render(<ConfidenceIndicator score={0.65} />);

      expect(screen.getByTestId("warning-icon")).toBeInTheDocument();
    });
  });

  describe("Compact Mode", () => {
    it("should render in compact mode without text", () => {
      render(<ConfidenceIndicator score={0.85} compact />);

      expect(screen.queryByText("85%")).not.toBeInTheDocument();
      expect(screen.getByTestId("confidence-indicator")).toBeInTheDocument();
    });

    it("should show tooltip on hover in compact mode", () => {
      render(<ConfidenceIndicator score={0.85} compact />);

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveAttribute("title", "Confidence: 85%");
    });
  });

  describe("Accessibility", () => {
    it("should have accessible label", () => {
      render(<ConfidenceIndicator score={0.92} />);

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveAttribute(
        "aria-label",
        expect.stringContaining("confidence"),
      );
    });

    it("should indicate confidence level for screen readers", () => {
      render(<ConfidenceIndicator score={0.92} />);

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveAttribute(
        "aria-label",
        expect.stringContaining("high"),
      );
    });
  });

  describe("Edge Cases", () => {
    it("should handle score of 1.0 (100%)", () => {
      render(<ConfidenceIndicator score={1.0} />);

      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should handle score of 0 (0%)", () => {
      render(<ConfidenceIndicator score={0} />);

      expect(screen.getByText("0%")).toBeInTheDocument();
    });

    it("should clamp scores above 1.0", () => {
      render(<ConfidenceIndicator score={1.5} />);

      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should clamp negative scores to 0", () => {
      render(<ConfidenceIndicator score={-0.1} />);

      expect(screen.getByText("0%")).toBeInTheDocument();
    });
  });
});
