/**
 * MetricsPanel Component
 *
 * Displays LLM and tool metrics in a dashboard format.
 */

import React from 'react';
import type { MetricsSummary } from '../../api/types';

export interface MetricsPanelProps {
  metrics: MetricsSummary | null;
  isLoading?: boolean;
}

function formatNumber(num: number): string {
  return num.toLocaleString();
}

function formatPercent(num: number): string {
  return `${Math.round(num * 100)}%`;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

interface MetricCardProps {
  label: string;
  value: string;
  subtext?: string;
}

function MetricCard({ label, value, subtext }: MetricCardProps) {
  return (
    <div className="bg-gray-50 dark:bg-dark-surface rounded-lg p-4">
      <div className="text-sm text-gray-500 dark:text-dark-textMuted">{label}</div>
      <div className="text-2xl font-semibold text-gray-900 dark:text-dark-text mt-1">
        {value}
      </div>
      {subtext && (
        <div className="text-xs text-gray-400 mt-1">{subtext}</div>
      )}
    </div>
  );
}

export function MetricsPanel({
  metrics,
  isLoading = false,
}: MetricsPanelProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        <div className="animate-pulse">Loading metrics...</div>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        No metrics available
      </div>
    );
  }

  return (
    <div className="p-4 space-y-6">
      {/* LLM Metrics */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary mb-3">
          LLM Metrics
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <MetricCard
            label="Total Calls"
            value={formatNumber(metrics.llm.totalCalls)}
          />
          <MetricCard
            label="Total Tokens"
            value={formatNumber(metrics.llm.totalTokens)}
            subtext={`${formatNumber(metrics.llm.promptTokens)} prompt / ${formatNumber(metrics.llm.completionTokens)} completion`}
          />
          <MetricCard
            label="Avg Latency"
            value={formatDuration(metrics.llm.averageLatencyMs)}
            subtext={`p50: ${formatDuration(metrics.llm.p50LatencyMs)}, p99: ${formatDuration(metrics.llm.p99LatencyMs)}`}
          />
          <MetricCard
            label="Error Rate"
            value={formatPercent(metrics.llm.errorRate)}
          />
        </div>
      </div>

      {/* Tool Metrics */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary mb-3">
          Tool Metrics
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <MetricCard
            label="Total Calls"
            value={formatNumber(metrics.tools.totalCalls)}
          />
          <MetricCard
            label="Success Rate"
            value={formatPercent(metrics.tools.successRate)}
            subtext={`${metrics.tools.errorCount} errors`}
          />
          <MetricCard
            label="Avg Latency"
            value={formatDuration(metrics.tools.averageLatencyMs)}
          />
          <MetricCard
            label="Messages"
            value={formatNumber(metrics.messageCount)}
          />
        </div>
      </div>
    </div>
  );
}
