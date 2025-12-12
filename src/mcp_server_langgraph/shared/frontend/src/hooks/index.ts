/**
 * Shared React Hooks
 *
 * Unified hooks for dark mode, accessibility, and metrics.
 */

export { useDarkMode } from './useDarkMode';
export type { UseDarkModeOptions, UseDarkModeResult } from './useDarkMode';

export { useAccessibility, useFocusTrap, useAnnounce, useSkipLink } from './useAccessibility';
export type {
  UseAccessibilityOptions,
  UseAccessibilityResult,
  UseFocusTrapResult,
  UseAnnounceResult,
  UseSkipLinkResult,
} from './useAccessibility';

export { useHeartMetrics, HeartMetricsProvider } from './useHeartMetrics';
export type {
  HeartMetrics,
  HeartMetricsContextValue,
  HeartMetricsProviderProps,
  TaskMetrics,
  EngagementMetrics,
  HappinessMetrics,
  AdoptionMetrics,
  RetentionMetrics,
} from './useHeartMetrics';
