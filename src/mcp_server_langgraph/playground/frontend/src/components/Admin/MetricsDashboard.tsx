/**
 * MetricsDashboard Component
 *
 * Admin dashboard for viewing HEART framework metrics.
 * Shows aggregated metrics for both Builder and Playground apps.
 */

import React, { useEffect, useState } from 'react';

// ==============================================================================
// Types
// ==============================================================================

export interface AggregateMetrics {
  period: string;
  app_name?: string;
  nps_score_avg?: number;
  satisfaction_avg?: number;
  task_success_rate?: number;
  total_tasks_started?: number;
  total_tasks_completed?: number;
  total_tasks_errored?: number;
  avg_session_duration_ms?: number;
  total_interactions?: number;
  top_features?: Record<string, number>;
  new_users_count?: number;
  onboarding_completion_rate?: number;
  avg_return_visits?: number;
  avg_days_active?: number;
}

export interface DashboardData {
  builder: Partial<AggregateMetrics>;
  playground: Partial<AggregateMetrics>;
  total_metrics_count: number;
  total_events_count: number;
  generated_at: string;
}

export interface MetricsDashboardProps {
  fetchDashboard?: () => Promise<DashboardData>;
}

interface MetricCardProps {
  title: string;
  metrics: Partial<AggregateMetrics>;
  ariaLabel: string;
}

// ==============================================================================
// Helpers
// ==============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

function formatDuration(ms: number): string {
  const minutes = Math.round(ms / 60000);
  return `${minutes} min`;
}

function formatPercentage(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

function formatNumber(num: number): string {
  return num.toLocaleString();
}

// ==============================================================================
// MetricCard Component
// ==============================================================================

function MetricCard({ title, metrics, ariaLabel }: MetricCardProps) {
  const npsScore = metrics.nps_score_avg ?? 0;
  const successRate = metrics.task_success_rate ?? 0;

  // NPS color based on score
  const getNpsColor = (score: number) => {
    if (score >= 9) return 'text-green-600 dark:text-green-400';
    if (score >= 7) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-red-600 dark:text-red-400';
  };

  return (
    <section
      role="region"
      aria-label={ariaLabel}
      className={clsx(
        'p-6 rounded-lg',
        'bg-white dark:bg-gray-800',
        'border border-gray-200 dark:border-gray-700'
      )}
    >
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        {title}
      </h3>

      <div className="grid grid-cols-2 gap-4">
        {/* NPS Score */}
        <div>
          <span className="text-sm text-gray-500 dark:text-gray-400">NPS Score</span>
          <p className={clsx('text-2xl font-bold', getNpsColor(npsScore))}>
            {npsScore.toFixed(1)}
          </p>
        </div>

        {/* Task Success Rate */}
        <div>
          <span className="text-sm text-gray-500 dark:text-gray-400">Task Success</span>
          <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {formatPercentage(successRate)}
          </p>
        </div>

        {/* Session Duration */}
        <div>
          <span className="text-sm text-gray-500 dark:text-gray-400">Avg Session</span>
          <p className="text-lg font-medium text-gray-700 dark:text-gray-300">
            {metrics.avg_session_duration_ms
              ? formatDuration(metrics.avg_session_duration_ms)
              : '-'}
          </p>
        </div>

        {/* Total Interactions */}
        <div>
          <span className="text-sm text-gray-500 dark:text-gray-400">Interactions</span>
          <p className="text-lg font-medium text-gray-700 dark:text-gray-300">
            {formatNumber(metrics.total_interactions ?? 0)}
          </p>
        </div>

        {/* New Users */}
        <div>
          <span className="text-sm text-gray-500 dark:text-gray-400">New Users</span>
          <p className="text-lg font-medium text-gray-700 dark:text-gray-300">
            {metrics.new_users_count ?? 0}
          </p>
        </div>

        {/* Tasks */}
        <div>
          <span className="text-sm text-gray-500 dark:text-gray-400">Tasks</span>
          <p className="text-lg font-medium text-gray-700 dark:text-gray-300">
            {formatNumber(metrics.total_tasks_completed ?? 0)}/
            {formatNumber(metrics.total_tasks_started ?? 0)}
          </p>
        </div>
      </div>

      {/* Top Features */}
      {metrics.top_features && Object.keys(metrics.top_features).length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
          <span className="text-sm text-gray-500 dark:text-gray-400">Top Features</span>
          <div className="mt-2 flex flex-wrap gap-2">
            {Object.entries(metrics.top_features)
              .slice(0, 3)
              .map(([feature, count]) => (
                <span
                  key={feature}
                  className={clsx(
                    'px-2 py-1 text-xs rounded-full',
                    'bg-gray-100 dark:bg-gray-700',
                    'text-gray-700 dark:text-gray-300'
                  )}
                >
                  {feature.replace(/_/g, ' ')}: {count}
                </span>
              ))}
          </div>
        </div>
      )}
    </section>
  );
}

// ==============================================================================
// Loading Skeleton
// ==============================================================================

function LoadingSkeleton() {
  return (
    <div className="animate-pulse" aria-label="Loading">
      <div className="h-8 bg-gray-200 dark:bg-gray-700 rounded w-64 mb-6" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
        <div className="h-64 bg-gray-200 dark:bg-gray-700 rounded" />
      </div>
    </div>
  );
}

// ==============================================================================
// Error State
// ==============================================================================

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="text-center py-12">
      <p className="text-red-600 dark:text-red-400 mb-4">
        Failed to load dashboard data
      </p>
      <button
        onClick={onRetry}
        className={clsx(
          'px-4 py-2 rounded-lg font-medium',
          'bg-blue-600 text-white',
          'hover:bg-blue-700',
          'focus:outline-none focus:ring-2 focus:ring-blue-500'
        )}
      >
        Retry
      </button>
    </div>
  );
}

// ==============================================================================
// Default Fetcher
// ==============================================================================

async function defaultFetchDashboard(): Promise<DashboardData> {
  const response = await fetch('/api/v1/metrics/dashboard', { method: 'GET' });
  if (!response.ok) {
    throw new Error(`Failed to get dashboard: ${response.status}`);
  }
  return response.json();
}

// ==============================================================================
// MetricsDashboard Component
// ==============================================================================

export function MetricsDashboard({ fetchDashboard = defaultFetchDashboard }: MetricsDashboardProps) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const dashboardData = await fetchDashboard();
      setData(dashboardData);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <span className="sr-only">Loading</span>
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          HEART Metrics Dashboard
        </h1>
        <ErrorState onRetry={fetchData} />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1
          role="heading"
          className="text-2xl font-bold text-gray-900 dark:text-white"
        >
          HEART Metrics Dashboard
        </h1>
        <button
          onClick={fetchData}
          aria-label="Refresh"
          className={clsx(
            'px-4 py-2 rounded-lg font-medium',
            'bg-gray-100 dark:bg-gray-700',
            'text-gray-700 dark:text-gray-300',
            'hover:bg-gray-200 dark:hover:bg-gray-600',
            'focus:outline-none focus:ring-2 focus:ring-gray-500'
          )}
        >
          Refresh
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-900/30">
          <span className="text-sm text-blue-600 dark:text-blue-400">Total Metrics</span>
          <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">
            {formatNumber(data.total_metrics_count)}
          </p>
        </div>
        <div className="p-4 rounded-lg bg-green-50 dark:bg-green-900/30">
          <span className="text-sm text-green-600 dark:text-green-400">Total Events</span>
          <p className="text-2xl font-bold text-green-700 dark:text-green-300">
            {formatNumber(data.total_events_count)}
          </p>
        </div>
        <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-900/30">
          <span className="text-sm text-purple-600 dark:text-purple-400">Period</span>
          <p className="text-2xl font-bold text-purple-700 dark:text-purple-300">
            {data.builder.period || '7d'}
          </p>
        </div>
        <div className="p-4 rounded-lg bg-gray-50 dark:bg-gray-800">
          <span className="text-sm text-gray-600 dark:text-gray-400">Last Updated</span>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mt-1">
            {new Date(data.generated_at).toLocaleString()}
          </p>
        </div>
      </div>

      {/* App Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <MetricCard
          title="Builder"
          metrics={data.builder}
          ariaLabel="Builder metrics"
        />
        <MetricCard
          title="Playground"
          metrics={data.playground}
          ariaLabel="Playground metrics"
        />
      </div>
    </div>
  );
}

export default MetricsDashboard;
