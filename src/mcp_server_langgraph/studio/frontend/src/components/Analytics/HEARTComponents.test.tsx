/**
 * HEART Dashboard Components Tests
 *
 * TDD - Sprint 4 - Phase 3.3: HEART Metrics Dashboard
 *
 * Tests for extracted HEART dashboard sub-components:
 * - DimensionCard: Individual HEART dimension display
 * - OverallHealthScore: Aggregate health score
 * - TimeRangeSelector: Time period picker
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import React from "react";

import {
  DimensionCard,
  OverallHealthScore,
  TimeRangeSelector,
} from "./HEARTComponents";

import { TestProvider } from "@/test-utils";

// =============================================================================
// DimensionCard Tests
// =============================================================================

describe("DimensionCard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
  it("renders dimension with label and icon", () => {
    render(
      <TestProvider>
        <DimensionCard dimension="happiness" score={85} hasData />
      </TestProvider>,
    );

    expect(screen.getByText("Happiness")).toBeInTheDocument();
    expect(screen.getByText("😊")).toBeInTheDocument();
  });

  it("displays score when hasData is true", () => {
    render(
      <TestProvider>
        <DimensionCard dimension="engagement" score={75} hasData />
      </TestProvider>,
    );

    expect(screen.getByText("75")).toBeInTheDocument();
  });

  it("displays 'No data' when hasData is false", () => {
    render(
      <TestProvider>
        <DimensionCard dimension="adoption" score={0} hasData={false} />
      </TestProvider>,
    );

    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("applies correct color based on dimension", () => {
    const { container } = render(
      <TestProvider>
        <DimensionCard dimension="retention" score={80} hasData />
      </TestProvider>,
    );

    const card = container.querySelector(".dimension-card");
    expect(card).toHaveStyle({ borderLeftColor: "#8b5cf6" });
  });

  it("has correct ARIA role and label", () => {
    render(
      <TestProvider>
        <DimensionCard dimension="task_success" score={90} hasData />
      </TestProvider>,
    );

    expect(
      screen.getByRole("region", { name: "Task Success" }),
    ).toBeInTheDocument();
  });

  it("renders all five HEART dimensions correctly", () => {
    const dimensions = [
      { dimension: "happiness" as const, icon: "😊" },
      { dimension: "engagement" as const, icon: "🔥" },
      { dimension: "adoption" as const, icon: "📈" },
      { dimension: "retention" as const, icon: "🔄" },
      { dimension: "task_success" as const, icon: "✅" },
    ];

    dimensions.forEach(({ dimension, icon }) => {
      const { unmount } = render(
        <TestProvider>
          <DimensionCard dimension={dimension} score={75} hasData />
        </TestProvider>,
      );
      expect(screen.getByText(icon)).toBeInTheDocument();
      unmount();
    });
  });
});

// =============================================================================
// OverallHealthScore Tests
// =============================================================================

describe("OverallHealthScore", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
  it("renders overall health score", () => {
    render(
      <TestProvider>
        <OverallHealthScore score={78} />
      </TestProvider>,
    );

    expect(screen.getByText("78")).toBeInTheDocument();
    expect(screen.getByText("Overall Health")).toBeInTheDocument();
  });

  it("has correct test ID", () => {
    render(
      <TestProvider>
        <OverallHealthScore score={85} />
      </TestProvider>,
    );

    expect(screen.getByTestId("overall-health-score")).toBeInTheDocument();
  });

  it("applies green color for high scores (>=80)", () => {
    const { container } = render(
      <TestProvider>
        <OverallHealthScore score={85} />
      </TestProvider>,
    );

    const circle = container.querySelector(".health-score-circle");
    expect(circle).toHaveStyle({ borderColor: "#22c55e" });
  });

  it("applies yellow color for medium scores (60-79)", () => {
    const { container } = render(
      <TestProvider>
        <OverallHealthScore score={65} />
      </TestProvider>,
    );

    const circle = container.querySelector(".health-score-circle");
    expect(circle).toHaveStyle({ borderColor: "#eab308" });
  });

  it("applies orange color for low scores (40-59)", () => {
    const { container } = render(
      <TestProvider>
        <OverallHealthScore score={50} />
      </TestProvider>,
    );

    const circle = container.querySelector(".health-score-circle");
    expect(circle).toHaveStyle({ borderColor: "#f97316" });
  });

  it("applies red color for very low scores (<40)", () => {
    const { container } = render(
      <TestProvider>
        <OverallHealthScore score={30} />
      </TestProvider>,
    );

    const circle = container.querySelector(".health-score-circle");
    expect(circle).toHaveStyle({ borderColor: "#ef4444" });
  });

  it("has correct ARIA label", () => {
    render(
      <TestProvider>
        <OverallHealthScore score={70} />
      </TestProvider>,
    );

    expect(
      screen.getByRole("region", { name: "Overall Health Score" }),
    ).toBeInTheDocument();
  });
});

// =============================================================================
// TimeRangeSelector Tests
// =============================================================================

describe("TimeRangeSelector", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });
  it("renders with initial value", () => {
    render(
      <TestProvider>
        <TimeRangeSelector value="30d" onChange={vi.fn()} />
      </TestProvider>,
    );

    const select = screen.getByLabelText("Time range");
    expect(select).toHaveValue("30d");
  });

  it("shows all time range options", () => {
    render(
      <TestProvider>
        <TimeRangeSelector value="7d" onChange={vi.fn()} />
      </TestProvider>,
    );

    expect(
      screen.getByRole("option", { name: "Last 7 days" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Last 30 days" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Last 90 days" }),
    ).toBeInTheDocument();
  });

  it("calls onChange when selection changes", () => {
    const onChange = vi.fn();
    render(
      <TestProvider>
        <TimeRangeSelector value="7d" onChange={onChange} />
      </TestProvider>,
    );

    const select = screen.getByLabelText("Time range");
    fireEvent.change(select, { target: { value: "90d" } });

    expect(onChange).toHaveBeenCalledWith("90d");
  });

  it("updates displayed value when prop changes", () => {
    const { rerender } = render(
      <TestProvider>
        <TimeRangeSelector value="7d" onChange={vi.fn()} />
      </TestProvider>,
    );

    expect(screen.getByLabelText("Time range")).toHaveValue("7d");

    rerender(<TimeRangeSelector value="90d" onChange={vi.fn()} />);

    expect(screen.getByLabelText("Time range")).toHaveValue("90d");
  });

  it("has accessible label", () => {
    render(
      <TestProvider>
        <TimeRangeSelector value="30d" onChange={vi.fn()} />
      </TestProvider>,
    );

    expect(screen.getByLabelText("Time range")).toBeInTheDocument();
  });
});
