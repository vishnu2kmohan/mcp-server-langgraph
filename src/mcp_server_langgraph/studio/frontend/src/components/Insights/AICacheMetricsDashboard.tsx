/**
 * AICacheMetricsDashboard Component
 *
 * Dashboard displaying AI cache performance metrics.
 * Features:
 * - Cache hit/miss ratio display with progress bar
 * - Error rate monitoring with color coding
 * - Average latency display
 * - Per-feature breakdown
 * - Compact mode for embedding
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Integrates with useAIMetrics hook for data.
 */

import {
  RefreshCw,
  Database,
  Zap,
  AlertTriangle,
  Clock,
  Activity,
  HardDrive,
} from "lucide-react";
import type {
  AIMetricsSnapshot,
  FeatureMetrics,
} from "../../hooks/useAIMetrics";
import type { CacheStats } from "../../hooks/useTieredCache";

// =============================================================================
// Types
// =============================================================================

export interface AICacheMetricsDashboardProps {
  /** Current metrics snapshot */
  snapshot: AIMetricsSnapshot;
  /** Per-feature metrics breakdown */
  featureMetrics: Record<string, FeatureMetrics>;
  /** Callback when refresh is requested */
  onRefresh?: () => void;
  /** Display in compact mode (hides feature breakdown) */
  compact?: boolean;
  /** Show loading indicator */
  isLoading?: boolean;
  /** Additional CSS classes */
  className?: string;
  /** Tiered cache stats (L1/L2) from useTieredCache hook */
  tieredCacheStats?: CacheStats;
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatPercentage(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatNumber(num: number): string {
  return num.toLocaleString();
}

function getCacheHitBarColor(ratio: number): string {
  if (ratio >= 0.7) return "bg-success-500";
  if (ratio >= 0.5) return "bg-warning-500";
  return "bg-error-500";
}

function getErrorRateColor(rate: number): string {
  if (rate < 0.05) return "text-success-600";
  if (rate < 0.1) return "text-warning-600";
  return "text-error-600";
}

function formatCacheAge(ageMs: number): string {
  const seconds = Math.floor(ageMs / 1000);
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h`;
}

// =============================================================================
// Metric Card Component
// =============================================================================

interface MetricCardProps {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  color?: "blue" | "green" | "purple" | "orange" | "red";
  testId?: string;
  valueClassName?: string;
}

function MetricCard({
  label,
  value,
  icon,
  color = "blue",
  testId,
  valueClassName,
}: MetricCardProps) {
  const colorClasses = {
    blue: "text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/30",
    green:
      "text-success-600 dark:text-success-400 bg-success-50 dark:bg-success-900/30",
    purple:
      "text-insight-600 dark:text-insight-400 bg-insight-50 dark:bg-insight-900/30",
    orange:
      "text-grafana-600 dark:text-grafana-400 bg-grafana-50 dark:bg-grafana-900/30",
    red: "text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/30",
  };

  return (
    <div className="p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
      <div className="flex items-center gap-2 mb-2">
        {icon && (
          <div className={`p-1.5 rounded ${colorClasses[color]}`}>{icon}</div>
        )}
        <span className="text-sm text-gray-500 dark:text-gray-400">
          {label}
        </span>
      </div>
      <div
        className={`text-2xl font-bold text-gray-900 dark:text-gray-100 ${valueClassName ?? ""}`}
        data-testid={testId}
      >
        {value}
      </div>
    </div>
  );
}

// =============================================================================
// Feature Row Component
// =============================================================================

interface FeatureRowProps {
  feature: string;
  metrics: FeatureMetrics;
}

function FeatureRow({ feature, metrics }: FeatureRowProps) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
        {feature}
      </span>
      <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
        <span data-testid={`feature-${feature}-requests`}>
          {metrics.requestCount} req
        </span>
        <span data-testid={`feature-${feature}-latency`}>
          {Math.round(metrics.averageLatency)}ms
        </span>
        {metrics.errorCount > 0 && (
          <span className="text-error-500">{metrics.errorCount} err</span>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AICacheMetricsDashboard({
  snapshot,
  featureMetrics,
  onRefresh,
  compact = false,
  isLoading = false,
  className = "",
  tieredCacheStats,
}: AICacheMetricsDashboardProps) {
  const hasData =
    snapshot.requestCount > 0 ||
    snapshot.cacheHits > 0 ||
    snapshot.cacheMisses > 0;
  const featureNames = Object.keys(featureMetrics);
  const hasTieredStats = tieredCacheStats !== undefined;

  return (
    <div
      data-testid="ai-cache-metrics-dashboard"
      data-compact={compact}
      className={`space-y-4 relative ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
          AI Cache Metrics
        </h3>
        <button
          type="button"
          onClick={onRefresh}
          aria-label="Refresh cache metrics"
          className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:text-gray-200 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Empty State */}
      {!hasData && !isLoading && (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <Database size={48} className="mx-auto mb-4 opacity-50" />
          <p>No cache data available yet</p>
        </div>
      )}

      {/* Metrics Grid */}
      {hasData && (
        <>
          {/* Cache Hit Ratio Progress */}
          <div className="p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Cache Hit Ratio
              </span>
              <span className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                {formatPercentage(snapshot.cacheHitRatio)}
              </span>
            </div>
            <div
              role="progressbar"
              aria-label="Cache hit ratio"
              aria-valuenow={Math.round(snapshot.cacheHitRatio * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              className="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
            >
              <div
                data-testid="cache-hit-progress-bar"
                className={`h-full ${getCacheHitBarColor(snapshot.cacheHitRatio)} transition-all duration-300`}
                style={{ width: `${snapshot.cacheHitRatio * 100}%` }}
              />
            </div>
          </div>

          {/* Main Metrics Grid */}
          <div className="grid gap-4 grid-cols-2 lg:grid-cols-3">
            <MetricCard
              label="Cache Hits"
              value={formatNumber(snapshot.cacheHits)}
              icon={<Zap size={16} />}
              color="green"
            />

            <MetricCard
              label="Cache Misses"
              value={formatNumber(snapshot.cacheMisses)}
              icon={<Database size={16} />}
              color="orange"
            />

            <MetricCard
              label="Error Rate"
              value={formatPercentage(snapshot.errorRate)}
              icon={<AlertTriangle size={16} />}
              color={
                snapshot.errorRate >= 0.1
                  ? "red"
                  : snapshot.errorRate >= 0.05
                    ? "orange"
                    : "green"
              }
              testId="error-rate-value"
              valueClassName={getErrorRateColor(snapshot.errorRate)}
            />

            <MetricCard
              label="Avg Latency"
              value={`${Math.round(snapshot.averageLatency)}ms`}
              icon={<Clock size={16} />}
              color="purple"
            />

            <MetricCard
              label="Total Requests"
              value={formatNumber(snapshot.requestCount)}
              icon={<Activity size={16} />}
              color="blue"
            />
          </div>

          {/* Feature Breakdown (hidden in compact mode) */}
          {!compact && featureNames.length > 0 && (
            <div className="p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Per-Feature Breakdown
              </h4>
              <div className="space-y-1">
                {featureNames.map((feature) => (
                  <FeatureRow
                    key={feature}
                    feature={feature}
                    metrics={featureMetrics[feature]!}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Tiered Cache Breakdown (hidden in compact mode) */}
          {!compact && hasTieredStats && tieredCacheStats && (
            <div className="p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                Tiered Cache Breakdown
              </h4>

              {/* Tiered Cache Bar Visualization */}
              <div
                data-testid="tiered-cache-bar"
                className="flex h-4 rounded-full overflow-hidden mb-4"
                role="img"
                aria-label="Tiered cache distribution"
              >
                {(() => {
                  const total =
                    tieredCacheStats.l1Hits +
                    tieredCacheStats.l2Hits +
                    tieredCacheStats.misses;
                  if (total === 0) return null;
                  const l1Pct = (tieredCacheStats.l1Hits / total) * 100;
                  const l2Pct = (tieredCacheStats.l2Hits / total) * 100;
                  const missPct = (tieredCacheStats.misses / total) * 100;
                  return (
                    <>
                      <div
                        className="bg-success-500"
                        style={{ width: `${l1Pct}%` }}
                        title={`L1 Hits: ${l1Pct.toFixed(1)}%`}
                      />
                      <div
                        className="bg-primary-500"
                        style={{ width: `${l2Pct}%` }}
                        title={`L2 Hits: ${l2Pct.toFixed(1)}%`}
                      />
                      <div
                        className="bg-gray-400"
                        style={{ width: `${missPct}%` }}
                        title={`Misses: ${missPct.toFixed(1)}%`}
                      />
                    </>
                  );
                })()}
              </div>

              {/* Legend */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5">
                    <Zap size={14} className="text-success-500" />
                    <span className="text-gray-600 dark:text-gray-400">
                      L1 (Memory)
                    </span>
                  </div>
                  <span
                    data-testid="l1-hits-value"
                    className="font-semibold text-gray-900 dark:text-gray-100"
                  >
                    {formatNumber(tieredCacheStats.l1Hits)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5">
                    <HardDrive size={14} className="text-primary-500" />
                    <span className="text-gray-600 dark:text-gray-400">
                      L2 (Session)
                    </span>
                  </div>
                  <span
                    data-testid="l2-hits-value"
                    className="font-semibold text-gray-900 dark:text-gray-100"
                  >
                    {formatNumber(tieredCacheStats.l2Hits)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5">
                    <Database
                      size={14}
                      className="text-gray-400 dark:text-gray-400"
                    />
                    <span className="text-gray-600 dark:text-gray-400">
                      Misses
                    </span>
                  </div>
                  <span
                    data-testid="tiered-misses-value"
                    className="font-semibold text-gray-900 dark:text-gray-100"
                  >
                    {formatNumber(tieredCacheStats.misses)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5">
                    <Clock size={14} className="text-insight-500" />
                    <span className="text-gray-600 dark:text-gray-400">
                      Cache Age
                    </span>
                  </div>
                  <span
                    data-testid="cache-age-value"
                    className="font-semibold text-gray-900 dark:text-gray-100"
                  >
                    {formatCacheAge(tieredCacheStats.age)}
                  </span>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Loading Overlay */}
      {isLoading && (
        <div
          data-testid="loading-indicator"
          className="absolute inset-0 bg-white/50 dark:bg-gray-900/50 flex items-center justify-center rounded-lg"
        >
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
        </div>
      )}
    </div>
  );
}

export default AICacheMetricsDashboard;
