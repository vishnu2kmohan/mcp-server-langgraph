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

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MetricCard } from "./MetricCard";

describe("MetricCard", () => {
  describe("Basic Rendering", () => {
    it("should render label", () => {
      render(<MetricCard label="Happiness" value={85} />);

      expect(screen.getByText("Happiness")).toBeInTheDocument();
    });

    it("should render value with percentage", () => {
      render(<MetricCard label="Happiness" value={85} />);

      expect(screen.getByText("85%")).toBeInTheDocument();
    });

    it("should render value without percentage when showPercentage is false", () => {
      render(
        <MetricCard label="Active Users" value={150} showPercentage={false} />,
      );

      expect(screen.getByText("150")).toBeInTheDocument();
      expect(screen.queryByText("150%")).not.toBeInTheDocument();
    });
  });

  describe("Color Coding", () => {
    it("should show green for high values (>= 80)", () => {
      render(<MetricCard label="Happiness" value={85} />);

      const valueElement = screen.getByText("85%");
      expect(valueElement).toHaveClass("text-green-600");
    });

    it("should show yellow for medium values (60-79)", () => {
      render(<MetricCard label="Adoption" value={68} />);

      const valueElement = screen.getByText("68%");
      expect(valueElement).toHaveClass("text-yellow-600");
    });

    it("should show red for low values (< 60)", () => {
      render(<MetricCard label="Engagement" value={45} />);

      const valueElement = screen.getByText("45%");
      expect(valueElement).toHaveClass("text-red-600");
    });
  });

  describe("Trend Indicator", () => {
    it("should show positive trend with up arrow", () => {
      render(<MetricCard label="Happiness" value={85} trend={12} />);

      expect(screen.getByTestId("trend-up")).toBeInTheDocument();
      expect(screen.getByText("+12%")).toBeInTheDocument();
    });

    it("should show negative trend with down arrow", () => {
      render(<MetricCard label="Engagement" value={68} trend={-5} />);

      expect(screen.getByTestId("trend-down")).toBeInTheDocument();
      expect(screen.getByText("-5%")).toBeInTheDocument();
    });

    it("should not show trend indicator when trend is zero", () => {
      render(<MetricCard label="Adoption" value={72} trend={0} />);

      expect(screen.queryByTestId("trend-up")).not.toBeInTheDocument();
      expect(screen.queryByTestId("trend-down")).not.toBeInTheDocument();
    });

    it("should not show trend when trend prop is not provided", () => {
      render(<MetricCard label="Retention" value={88} />);

      expect(screen.queryByTestId("trend-up")).not.toBeInTheDocument();
      expect(screen.queryByTestId("trend-down")).not.toBeInTheDocument();
    });

    it("should show positive trend in green", () => {
      render(<MetricCard label="Happiness" value={85} trend={12} />);

      const trendElement = screen.getByText("+12%");
      expect(trendElement).toHaveClass("text-green-500");
    });

    it("should show negative trend in red", () => {
      render(<MetricCard label="Engagement" value={68} trend={-5} />);

      const trendElement = screen.getByText("-5%");
      expect(trendElement).toHaveClass("text-red-500");
    });
  });

  describe("Variants", () => {
    it("should apply compact variant styling", () => {
      render(<MetricCard label="NPS" value={42} variant="compact" />);

      const card = screen.getByTestId("metric-card");
      expect(card).toHaveClass("p-3");
    });

    it("should apply default variant styling", () => {
      render(<MetricCard label="NPS" value={42} />);

      const card = screen.getByTestId("metric-card");
      expect(card).toHaveClass("p-4");
    });

    it("should apply large variant styling", () => {
      render(<MetricCard label="NPS" value={42} variant="large" />);

      const card = screen.getByTestId("metric-card");
      expect(card).toHaveClass("p-6");
    });
  });

  describe("Icon", () => {
    it("should render icon when provided", () => {
      render(
        <MetricCard
          label="Users"
          value={150}
          icon={<span data-testid="custom-icon">👥</span>}
        />,
      );

      expect(screen.getByTestId("custom-icon")).toBeInTheDocument();
    });
  });

  describe("Description", () => {
    it("should render description when provided", () => {
      render(
        <MetricCard
          label="NPS Score"
          value={42}
          description="Net Promoter Score for the last 30 days"
        />,
      );

      expect(
        screen.getByText("Net Promoter Score for the last 30 days"),
      ).toBeInTheDocument();
    });
  });
});
