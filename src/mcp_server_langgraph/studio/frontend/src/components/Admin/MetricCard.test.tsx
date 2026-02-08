/**
 * MetricCard Component Tests
 *
 * TDD tests for the enhanced metric card with trend indicators.
 * Tests cover:
 * - Basic rendering
 * - Trend direction (up/down/neutral)
 * - Color coding based on value
 * - Trend percentage display
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MetricCard } from "./MetricCard";

import { TestProvider } from "@/test-utils";

describe("MetricCard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render label", () => {
      render(
        <TestProvider>
          <MetricCard label="Happiness" value={85} />
        </TestProvider>,
      );

      expect(screen.getByText("Happiness")).toBeInTheDocument();
    });

    it("should render value with percentage", () => {
      render(
        <TestProvider>
          <MetricCard label="Happiness" value={85} />
        </TestProvider>,
      );

      expect(screen.getByText("85%")).toBeInTheDocument();
    });

    it("should render value without percentage when showPercentage is false", () => {
      render(
        <TestProvider>
          <MetricCard label="Active Users" value={150} showPercentage={false} />
        </TestProvider>,
      );

      expect(screen.getByText("150")).toBeInTheDocument();
      expect(screen.queryByText("150%")).not.toBeInTheDocument();
    });
  });

  describe("Color Coding", () => {
    it("should show green for high values (>= 80)", () => {
      render(
        <TestProvider>
          <MetricCard label="Happiness" value={85} />
        </TestProvider>,
      );

      const valueElement = screen.getByText("85%");
      expect(valueElement).toHaveClass("text-success-10");
    });

    it("should show yellow for medium values (60-79)", () => {
      render(
        <TestProvider>
          <MetricCard label="Adoption" value={68} />
        </TestProvider>,
      );

      const valueElement = screen.getByText("68%");
      expect(valueElement).toHaveClass("text-warning-9");
    });

    it("should show red for low values (< 60)", () => {
      render(
        <TestProvider>
          <MetricCard label="Engagement" value={45} />
        </TestProvider>,
      );

      const valueElement = screen.getByText("45%");
      expect(valueElement).toHaveClass("text-error-10");
    });
  });

  describe("Trend Indicator", () => {
    it("should show positive trend with up arrow", () => {
      render(
        <TestProvider>
          <MetricCard label="Happiness" value={85} trend={12} />
        </TestProvider>,
      );

      expect(screen.getByTestId("trend-up")).toBeInTheDocument();
      expect(screen.getByText("+12%")).toBeInTheDocument();
    });

    it("should show negative trend with down arrow", () => {
      render(
        <TestProvider>
          <MetricCard label="Engagement" value={68} trend={-5} />
        </TestProvider>,
      );

      expect(screen.getByTestId("trend-down")).toBeInTheDocument();
      expect(screen.getByText("-5%")).toBeInTheDocument();
    });

    it("should not show trend indicator when trend is zero", () => {
      render(
        <TestProvider>
          <MetricCard label="Adoption" value={72} trend={0} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("trend-up")).not.toBeInTheDocument();
      expect(screen.queryByTestId("trend-down")).not.toBeInTheDocument();
    });

    it("should not show trend when trend prop is not provided", () => {
      render(
        <TestProvider>
          <MetricCard label="Retention" value={88} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("trend-up")).not.toBeInTheDocument();
      expect(screen.queryByTestId("trend-down")).not.toBeInTheDocument();
    });

    it("should show positive trend in green", () => {
      render(
        <TestProvider>
          <MetricCard label="Happiness" value={85} trend={12} />
        </TestProvider>,
      );

      const trendElement = screen.getByText("+12%");
      expect(trendElement).toHaveClass("text-success-9");
    });

    it("should show negative trend in red", () => {
      render(
        <TestProvider>
          <MetricCard label="Engagement" value={68} trend={-5} />
        </TestProvider>,
      );

      const trendElement = screen.getByText("-5%");
      expect(trendElement).toHaveClass("text-error-9");
    });
  });

  describe("Variants", () => {
    it("should apply compact variant styling", () => {
      render(
        <TestProvider>
          <MetricCard label="NPS" value={42} variant="compact" />
        </TestProvider>,
      );

      const card = screen.getByTestId("metric-card");
      expect(card).toHaveClass("p-3");
    });

    it("should apply default variant styling", () => {
      render(
        <TestProvider>
          <MetricCard label="NPS" value={42} />
        </TestProvider>,
      );

      const card = screen.getByTestId("metric-card");
      expect(card).toHaveClass("p-4");
    });

    it("should apply large variant styling", () => {
      render(
        <TestProvider>
          <MetricCard label="NPS" value={42} variant="large" />
        </TestProvider>,
      );

      const card = screen.getByTestId("metric-card");
      expect(card).toHaveClass("p-6");
    });
  });

  describe("Icon", () => {
    it("should render icon when provided", () => {
      render(
        <TestProvider>
          <MetricCard
            label="Users"
            value={150}
            icon={<span data-testid="custom-icon">👥</span>}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("custom-icon")).toBeInTheDocument();
    });
  });

  describe("Description", () => {
    it("should render description when provided", () => {
      render(
        <TestProvider>
          <MetricCard
            label="NPS Score"
            value={42}
            description="Net Promoter Score for the last 30 days"
          />
        </TestProvider>,
      );

      expect(
        screen.getByText("Net Promoter Score for the last 30 days"),
      ).toBeInTheDocument();
    });
  });
});
