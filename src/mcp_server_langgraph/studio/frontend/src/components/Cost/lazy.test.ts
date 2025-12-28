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
  it("exports OrganizationCostDashboard", async () => {
    const { OrganizationCostDashboard } = await import("./index");
    expect(OrganizationCostDashboard).toBeDefined();
  });

  it("exports BudgetStatusCard", async () => {
    const { BudgetStatusCard } = await import("./index");
    expect(BudgetStatusCard).toBeDefined();
  });

  it("exports BudgetForecastChart", async () => {
    const { BudgetForecastChart } = await import("./index");
    expect(BudgetForecastChart).toBeDefined();
  });
});
