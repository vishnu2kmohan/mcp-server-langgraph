/**
 * HEART Metrics Hook
 *
 * Re-exports from shared frontend library with backward-compatible API.
 * See: src/mcp_server_langgraph/shared/frontend/src/hooks/useHeartMetrics.tsx
 *
 * @deprecated Import from '@mcp-server-langgraph/shared-frontend' instead
 */

// Re-export from shared library
export {
  useHeartMetrics,
  HeartMetricsProvider,
  type HeartMetrics,
  type HeartMetricsContextValue,
  type HeartMetricsProviderProps,
  type TaskMetrics,
  type EngagementMetrics,
  type HappinessMetrics,
  type AdoptionMetrics,
  type RetentionMetrics,
} from '../../../../shared/frontend/src/hooks/useHeartMetrics';

export { useHeartMetrics as default } from '../../../../shared/frontend/src/hooks/useHeartMetrics';
