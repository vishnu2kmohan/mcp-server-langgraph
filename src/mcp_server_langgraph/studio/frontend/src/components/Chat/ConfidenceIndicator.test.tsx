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

import { TestProvider } from "@/test-utils";

describe("ConfidenceIndicator", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
  describe("Score Display", () => {
    it("should render confidence score as percentage", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.92} />
        </TestProvider>,
      );

      expect(screen.getByText("92%")).toBeInTheDocument();
    });

    it("should round score to nearest integer", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.876} />
        </TestProvider>,
      );

      expect(screen.getByText("88%")).toBeInTheDocument();
    });
  });

  describe("Visual Indicators", () => {
    it("should show green indicator for high confidence (>= 0.8)", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.92} />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-success-10");
    });

    it("should show yellow indicator for medium confidence (0.6-0.79)", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.72} />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-warning-9");
    });

    it("should show red indicator for low confidence (< 0.6)", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.45} />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-error-10");
    });
  });

  describe("Low Confidence Warning", () => {
    it("should show warning badge for low confidence", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.45} />
        </TestProvider>,
      );

      expect(screen.getByText(/verify this information/i)).toBeInTheDocument();
    });

    it("should not show warning for high confidence", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.92} />
        </TestProvider>,
      );

      expect(
        screen.queryByText(/verify this information/i),
      ).not.toBeInTheDocument();
    });

    it("should show warning icon for scores below 0.7", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.65} />
        </TestProvider>,
      );

      expect(screen.getByTestId("warning-icon")).toBeInTheDocument();
    });
  });

  describe("Compact Mode", () => {
    it("should render in compact mode without text", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} compact />
        </TestProvider>,
      );

      expect(screen.queryByText("85%")).not.toBeInTheDocument();
      expect(screen.getByTestId("confidence-indicator")).toBeInTheDocument();
    });

    it("should show tooltip on hover in compact mode", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} compact />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveAttribute("title", "Confidence: 85%");
    });
  });

  describe("Accessibility", () => {
    it("should have accessible label", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.92} />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveAttribute(
        "aria-label",
        expect.stringContaining("confidence"),
      );
    });

    it("should indicate confidence level for screen readers", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.92} />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveAttribute(
        "aria-label",
        expect.stringContaining("high"),
      );
    });
  });

  describe("Edge Cases", () => {
    it("should handle score of 1.0 (100%)", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={1.0} />
        </TestProvider>,
      );

      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should handle score of 0 (0%)", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0} />
        </TestProvider>,
      );

      expect(screen.getByText("0%")).toBeInTheDocument();
    });

    it("should clamp scores above 1.0", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={1.5} />
        </TestProvider>,
      );

      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should clamp negative scores to 0", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={-0.1} />
        </TestProvider>,
      );

      expect(screen.getByText("0%")).toBeInTheDocument();
    });
  });
});
