/**
 * AdminDashboard Component
 *
 * Main dashboard for administrators with system health and HEART metrics.
 */

import { RefreshCw, Loader2 } from 'lucide-react';

export interface SystemHealth {
  status: 'healthy' | 'degraded' | 'unhealthy';
  uptime: number;
  activeUsers: number;
  activeSessions: number;
  errorRate: number;
}

export interface HEARTMetrics {
  happiness: number;
  engagement: number;
  adoption: number;
  retention: number;
  taskSuccess: number;
}

export interface AdminDashboardProps {
  systemHealth: SystemHealth;
  heartMetrics: HEARTMetrics;
  isLoading: boolean;
  onRefresh: () => void;
}

export function AdminDashboard({
  systemHealth,
  heartMetrics,
  isLoading,
  onRefresh,
}: AdminDashboardProps) {
  if (isLoading) {
    return (
      <div
        data-testid="dashboard-loading"
        className="flex items-center justify-center h-full"
      >
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const getHealthColor = (status: SystemHealth['status']) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'unhealthy':
        return 'bg-red-500';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Admin Dashboard
        </h1>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          aria-label="Refresh dashboard"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* System Health Section */}
      <section className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          System Health
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Status */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <div
                data-testid="health-status"
                className={`w-3 h-3 rounded-full ${getHealthColor(systemHealth.status)}`}
              />
              <span className="text-sm text-gray-600 dark:text-gray-300">
                Status
              </span>
            </div>
            <span className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
              {systemHealth.status}
            </span>
          </div>

          {/* Uptime */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <span className="text-sm text-gray-600 dark:text-gray-300 block mb-2">
              Uptime
            </span>
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              {systemHealth.uptime}%
            </span>
          </div>

          {/* Active Users */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <span className="text-sm text-gray-600 dark:text-gray-300 block mb-2">
              Active Users
            </span>
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              {systemHealth.activeUsers}
            </span>
          </div>

          {/* Error Rate */}
          <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
            <span className="text-sm text-gray-600 dark:text-gray-300 block mb-2">
              Error Rate
            </span>
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              {systemHealth.errorRate}%
            </span>
          </div>
        </div>
      </section>

      {/* HEART Metrics Section */}
      <section className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          HEART Metrics
        </h2>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <MetricCard label="Happiness" value={heartMetrics.happiness} />
          <MetricCard label="Engagement" value={heartMetrics.engagement} />
          <MetricCard label="Adoption" value={heartMetrics.adoption} />
          <MetricCard label="Retention" value={heartMetrics.retention} />
          <MetricCard label="Task Success" value={heartMetrics.taskSuccess} />
        </div>
      </section>
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: number;
}

function MetricCard({ label, value }: MetricCardProps) {
  const getColor = (value: number) => {
    if (value >= 80) return 'text-green-600';
    if (value >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
      <span className="text-sm text-gray-600 dark:text-gray-300 block mb-2">
        {label}
      </span>
      <span className={`text-lg font-semibold ${getColor(value)}`}>
        {value}%
      </span>
    </div>
  );
}
