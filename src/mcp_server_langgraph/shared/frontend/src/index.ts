/**
 * Shared Frontend Library
 *
 * Centralized design system, hooks, and components for:
 * - Visual Workflow Builder
 * - Interactive Playground
 *
 * @module @mcp-server-langgraph/shared-frontend
 */

// Hooks
export * from './hooks';

// Styles & Design Tokens
export * from './styles';

// Components
export * from './components';

// API utilities - explicit exports to avoid duplicate type exports
// (TaskMetrics, EngagementMetrics, etc. are already exported from hooks)
export {
  sendHeartMetrics,
  sendEvents,
  getAggregateMetrics,
  getDashboard,
  type HeartMetricsBatch,
  type MetricsReceipt,
  type FeatureEvent,
  type EventReceipt,
  type AggregateMetrics,
  type DashboardData,
} from './api';
