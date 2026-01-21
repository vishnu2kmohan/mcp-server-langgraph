/**
 * Cost Components
 *
 * Components for cost tracking and organizational cost attribution.
 *
 * NOTE: Component implementations are only available via lazy exports to enable
 * code-splitting. Import from ./lazy for component usage:
 *
 * ```tsx
 * import { LazyOrganizationCostDashboard } from "../components/Cost/lazy";
 * ```
 *
 * Type exports are available directly from this file.
 */

// Type-only exports (don't affect bundle size)
export type { OrganizationCostDashboardProps } from "./OrganizationCostDashboard";
export type { BudgetStatus, BudgetStatusCardProps } from "./BudgetStatusCard";
export type {
  CostForecast,
  BudgetForecastChartProps,
  TrendType,
} from "./BudgetForecastChart";

// Re-export lazy components for convenience
export {
  LazyOrganizationCostDashboard,
  LazyBudgetStatusCard,
  LazyBudgetForecastChart,
  LazyNativeToolComparison,
} from "./lazy";
