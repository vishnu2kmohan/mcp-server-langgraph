/**
 * Cost Lazy Loading Tests
 *
 * TDD tests for lazy-loaded cost components.
 */

import { describe, it, expect, afterEach, vi } from "vitest";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("Cost/lazy exports", () => {
  it("exports LazyOrganizationCostDashboard", async () => {
    const { LazyOrganizationCostDashboard } = await import("./lazy");
    expect(LazyOrganizationCostDashboard).toBeDefined();
  });

  it("exports LazyBudgetStatusCard", async () => {
    const { LazyBudgetStatusCard } = await import("./lazy");
    expect(LazyBudgetStatusCard).toBeDefined();
  });

  it("exports LazyBudgetForecastChart", async () => {
    const { LazyBudgetForecastChart } = await import("./lazy");
    expect(LazyBudgetForecastChart).toBeDefined();
  });

  it("exports type definitions", async () => {
    // Type imports should compile without error
    const module = await import("./lazy");
    expect(module).toBeDefined();
  });
});

describe("Cost/index exports", () => {
  it("exports LazyOrganizationCostDashboard", async () => {
    const { LazyOrganizationCostDashboard } = await import("./index");
    expect(LazyOrganizationCostDashboard).toBeDefined();
  });

  it("exports LazyBudgetStatusCard", async () => {
    const { LazyBudgetStatusCard } = await import("./index");
    expect(LazyBudgetStatusCard).toBeDefined();
  });

  it("exports LazyBudgetForecastChart", async () => {
    const { LazyBudgetForecastChart } = await import("./index");
    expect(LazyBudgetForecastChart).toBeDefined();
  });
});
