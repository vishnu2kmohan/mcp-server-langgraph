/**
 * ConfidenceIndicator Component Tests
 *
 * TDD: Tests written FIRST before implementation.
 * ConfidenceIndicator displays AI confidence scores with semantic colors.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ConfidenceIndicator } from "./ConfidenceIndicator";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ConfidenceIndicator", () => {
  describe("rendering", () => {
    it("renders with confidence score", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} />
        </TestProvider>,
      );
      expect(screen.getByTestId("confidence-indicator")).toBeInTheDocument();
    });

    it("displays percentage by default", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} />
        </TestProvider>,
      );
      expect(screen.getByText("85%")).toBeInTheDocument();
    });

    it("displays decimal when showDecimal is true", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} showDecimal />
        </TestProvider>,
      );
      expect(screen.getByText("0.85")).toBeInTheDocument();
    });
  });

  describe("confidence levels", () => {
    it("renders high confidence (>= 0.9) with success colors", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.95} />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-success-10");
    });

    it("renders medium confidence (>= 0.7, < 0.9) with warning colors", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.75} />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-warning-9");
    });

    it("renders low confidence (< 0.7) with error colors", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.5} />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-error-10");
    });

    it("handles edge case at 0.9 boundary", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.9} />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-success-10");
    });

    it("handles edge case at 0.7 boundary", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.7} />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-warning-9");
    });
  });

  describe("dark mode support", () => {
    it("includes dark mode classes for high confidence", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.95} />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator.className).toMatch(/dark:text-success-7/);
    });

    it("includes dark mode classes for medium confidence", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.75} />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator.className).toMatch(/dark:text-warning-9/);
    });

    it("includes dark mode classes for low confidence", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.5} />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator.className).toMatch(/dark:text-error-7/);
    });
  });

  describe("with label", () => {
    it("renders with custom label", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} label="Confidence" />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator.textContent).toContain("Confidence:");
      expect(indicator.textContent).toContain("85%");
    });

    it("renders label before score", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} label="AI Score" />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator.textContent).toBe("AI Score: 85%");
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} size="sm" />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-xs");
    });

    it("renders medium size (default)", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-sm");
    });

    it("renders large size", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} size="lg" />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("text-base");
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} className="custom-class" />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveClass("custom-class");
    });
  });

  describe("accessibility", () => {
    it("includes aria-label with confidence value", () => {
      render(
        <TestProvider>
          <ConfidenceIndicator score={0.85} />
        </TestProvider>,
      );
      const indicator = screen.getByTestId("confidence-indicator");
      expect(indicator).toHaveAttribute("aria-label", "Confidence: 85%");
    });
  });
});
