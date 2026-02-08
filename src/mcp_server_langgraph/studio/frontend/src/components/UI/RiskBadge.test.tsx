/**
 * RiskBadge Component Tests
 *
 * TDD: Tests written FIRST before implementation.
 * RiskBadge displays risk levels with semantic colors and icons.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { RiskBadge } from "./RiskBadge";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("RiskBadge", () => {
  describe("rendering", () => {
    it("renders with risk level", () => {
      render(
        <TestProvider>
          <RiskBadge level="low" />
        </TestProvider>,
      );
      expect(screen.getByTestId("risk-badge")).toBeInTheDocument();
    });

    it("displays risk level text", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" />
        </TestProvider>,
      );
      expect(screen.getByText("High")).toBeInTheDocument();
    });

    it("capitalizes risk level text", () => {
      render(
        <TestProvider>
          <RiskBadge level="critical" />
        </TestProvider>,
      );
      expect(screen.getByText("Critical")).toBeInTheDocument();
    });
  });

  describe("risk levels", () => {
    it("renders low risk with success colors", () => {
      render(
        <TestProvider>
          <RiskBadge level="low" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-success-10");
    });

    it("renders medium risk with warning colors", () => {
      render(
        <TestProvider>
          <RiskBadge level="medium" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-warning-9");
    });

    it("renders high risk with error colors", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-error-10");
    });

    it("renders critical risk with stronger error colors", () => {
      render(
        <TestProvider>
          <RiskBadge level="critical" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-error-11");
    });
  });

  describe("dark mode support", () => {
    it("includes dark mode classes for low risk", () => {
      render(
        <TestProvider>
          <RiskBadge level="low" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge.className).toMatch(/dark:text-success-7/);
    });

    it("includes dark mode classes for high risk", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge.className).toMatch(/dark:text-error-7/);
    });

    it("includes dark mode classes for critical risk", () => {
      render(
        <TestProvider>
          <RiskBadge level="critical" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge.className).toMatch(/dark:text-error-9/);
    });
  });

  describe("with icons", () => {
    it("shows icon when showIcon is true", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" showIcon />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge.querySelector("svg")).toBeInTheDocument();
    });

    it("hides icon by default", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge.querySelector("svg")).not.toBeInTheDocument();
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" size="sm" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-xs");
    });

    it("renders medium size (default)", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-sm");
    });

    it("renders large size", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" size="lg" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("text-base");
    });
  });

  describe("customization", () => {
    it("accepts custom className", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" className="custom-class" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveClass("custom-class");
    });

    it("accepts custom label", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" label="Severity" />
        </TestProvider>,
      );
      expect(screen.getByText("Severity: High")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has accessible role", () => {
      render(
        <TestProvider>
          <RiskBadge level="high" />
        </TestProvider>,
      );
      expect(screen.getByRole("status")).toBeInTheDocument();
    });

    it("includes aria-label with risk level", () => {
      render(
        <TestProvider>
          <RiskBadge level="critical" />
        </TestProvider>,
      );
      const badge = screen.getByTestId("risk-badge");
      expect(badge).toHaveAttribute("aria-label", "Risk level: Critical");
    });
  });
});
