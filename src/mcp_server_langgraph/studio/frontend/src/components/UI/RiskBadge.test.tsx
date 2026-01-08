/**
 * RiskBadge Component Tests
 *
 * TDD: Tests written FIRST before implementation.
 * RiskBadge displays risk levels with semantic colors and icons.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { RiskBadge } from "./RiskBadge";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("RiskBadge", () => {
  describe("rendering", () => {
    it("renders with risk level", () => {
      render(<RiskBadge level="low" />);
      expect(screen.getByTestId("risk-badge")).toBeInTheDocument();
    });

    it("displays risk level text", () => {
      render(<RiskBadge level="high" />);
      expect(screen.getByText("High")).toBeInTheDocument();
    });

    it("capitalizes risk level text", () => {
      render(<RiskBadge level="critical" />);
      expect(screen.getByText("Critical")).toBeInTheDocument();
    });
  });

  describe("risk levels", () => {
    it("renders low risk with success colors", () => {
      render(<RiskBadge level="low" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-success-600");
    });

    it("renders medium risk with warning colors", () => {
      render(<RiskBadge level="medium" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-warning-600");
    });

    it("renders high risk with error colors", () => {
      render(<RiskBadge level="high" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-error-600");
    });

    it("renders critical risk with stronger error colors", () => {
      render(<RiskBadge level="critical" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-error-700");
    });
  });

  describe("dark mode support", () => {
    it("includes dark mode classes for low risk", () => {
      render(<RiskBadge level="low" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge.className).toMatch(/dark:text-success-400/);
    });

    it("includes dark mode classes for high risk", () => {
      render(<RiskBadge level="high" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge.className).toMatch(/dark:text-error-400/);
    });

    it("includes dark mode classes for critical risk", () => {
      render(<RiskBadge level="critical" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge.className).toMatch(/dark:text-error-300/);
    });
  });

  describe("with icons", () => {
    it("shows icon when showIcon is true", () => {
      render(<RiskBadge level="high" showIcon />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge.querySelector("svg")).toBeInTheDocument();
    });

    it("hides icon by default", () => {
      render(<RiskBadge level="high" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge.querySelector("svg")).not.toBeInTheDocument();
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(<RiskBadge level="high" size="sm" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-xs");
    });

    it("renders medium size (default)", () => {
      render(<RiskBadge level="high" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-sm");
    });

    it("renders large size", () => {
      render(<RiskBadge level="high" size="lg" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-base");
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(<RiskBadge level="high" className="custom-class" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("custom-class");
    });

    it("accepts custom label", () => {
      render(<RiskBadge level="high" label="Severity" />);
      expect(screen.getByText("Severity: High")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has accessible role", () => {
      render(<RiskBadge level="high" />);
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("includes aria-label with risk level", () => {
      render(<RiskBadge level="critical" />);
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveAttribute("aria-label", "Risk level: Critical");
    });
  });
});
