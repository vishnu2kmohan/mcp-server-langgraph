/**
 * ConfidenceIndicator Component Tests
 *
 * TDD: Tests written FIRST before implementation.
 * ConfidenceIndicator displays AI confidence scores with semantic colors.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ConfidenceIndicator } from "./ConfidenceIndicator";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ConfidenceIndicator", () => {
  describe("rendering", () => {
    it("renders with confidence score", () => {
      render(<ConfidenceIndicator score={0.85} />);
      expect(screen.getByTestId("confidence-indicator")).toBeInTheDocument();
    });

    it("displays percentage by default", () => {
      render(<ConfidenceIndicator score={0.85} />);
      expect(screen.getByText("85%")).toBeInTheDocument();
    });

    it("displays decimal when showDecimal is true", () => {
      render(<ConfidenceIndicator score={0.85} showDecimal />);
      expect(screen.getByText("0.85")).toBeInTheDocument();
    });
  });

  describe("confidence levels", () => {
    it("renders high confidence (>= 0.9) with success colors", () => {
      render(<ConfidenceIndicator score={0.95} />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-success-600");
    });

    it("renders medium confidence (>= 0.7, < 0.9) with warning colors", () => {
      render(<ConfidenceIndicator score={0.75} />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-warning-600");
    });

    it("renders low confidence (< 0.7) with error colors", () => {
      render(<ConfidenceIndicator score={0.5} />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-error-600");
    });

    it("handles edge case at 0.9 boundary", () => {
      render(<ConfidenceIndicator score={0.9} />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-success-600");
    });

    it("handles edge case at 0.7 boundary", () => {
      render(<ConfidenceIndicator score={0.7} />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-warning-600");
    });
  });

  describe("dark mode support", () => {
    it("includes dark mode classes for high confidence", () => {
      render(<ConfidenceIndicator score={0.95} />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator.className).toMatch(/dark:text-success-400/);
    });

    it("includes dark mode classes for medium confidence", () => {
      render(<ConfidenceIndicator score={0.75} />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator.className).toMatch(/dark:text-warning-400/);
    });

    it("includes dark mode classes for low confidence", () => {
      render(<ConfidenceIndicator score={0.5} />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator.className).toMatch(/dark:text-error-400/);
    });
  });

  describe("with label", () => {
    it("renders with custom label", () => {
      render(<ConfidenceIndicator score={0.85} label="Confidence" />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator.textContent).toContain("Confidence:");
      expect(indicator.textContent).toContain("85%");
    });

    it("renders label before score", () => {
      render(<ConfidenceIndicator score={0.85} label="AI Score" />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator.textContent).toBe("AI Score: 85%");
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(<ConfidenceIndicator score={0.85} size="sm" />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-xs");
    });

    it("renders medium size (default)", () => {
      render(<ConfidenceIndicator score={0.85} />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-sm");
    });

    it("renders large size", () => {
      render(<ConfidenceIndicator score={0.85} size="lg" />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-base");
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(<ConfidenceIndicator score={0.85} className="custom-class" />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("custom-class");
    });
  });

  describe("accessibility", () => {
    it("includes aria-label with confidence value", () => {
      render(<ConfidenceIndicator score={0.85} />);
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveAttribute("aria-label", "Confidence: 85%");
    });
  });
});
