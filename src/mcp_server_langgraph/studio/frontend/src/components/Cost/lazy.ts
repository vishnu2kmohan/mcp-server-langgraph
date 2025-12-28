/**
 * Lazy-loaded Cost Components
 *
 * Provides lazy-loaded versions of cost components for code splitting.
 * Use these when components are not needed on initial page load.
 */

import { lazy } from "react";

/**
 * Lazy-loaded OrganizationCostDashboard
 *
 * Use for organizational cost overview in admin pages.
 */
export const LazyOrganizationCostDashboard = lazy(
  () => import("./OrganizationCostDashboard"),
);

/**
 * Lazy-loaded BudgetStatusCard
 *
 * Use for displaying budget status with visual indicators.
 */
export const LazyBudgetStatusCard = lazy(() =>
  import("./BudgetStatusCard").then((module) => ({
    default: module.BudgetStatusCard,
  })),
);

/**
 * Lazy-loaded BudgetForecastChart
 *
 * Use for visualizing cost forecasts with confidence ranges.
 */
export const LazyBudgetForecastChart = lazy(() =>
  import("./BudgetForecastChart").then((module) => ({
    default: module.BudgetForecastChart,
  })),
);

// Re-export types for convenience
export type { OrganizationCostDashboardProps } from "./OrganizationCostDashboard";
export type { BudgetStatus, BudgetStatusCardProps } from "./BudgetStatusCard";
export type {
  CostForecast,
  BudgetForecastChartProps,
  TrendType,
} from "./BudgetForecastChart";
