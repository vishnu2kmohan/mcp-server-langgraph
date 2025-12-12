/**
 * ObservabilityTabs Component
 *
 * Tabbed interface for switching between observability views.
 */

import React, { useState } from 'react';
import clsx from 'clsx';
import { TracePanel } from './TracePanel';
import { LogPanel } from './LogPanel';
import { MetricsPanel } from './MetricsPanel';
import { AlertPanel } from './AlertPanel';
import type { TraceInfo, LogEntry, MetricsSummary, Alert } from '../../api/types';

type TabId = 'traces' | 'logs' | 'metrics' | 'alerts';

interface Tab {
  id: TabId;
  label: string;
}

const TABS: Tab[] = [
  { id: 'traces', label: 'Traces' },
  { id: 'logs', label: 'Logs' },
  { id: 'metrics', label: 'Metrics' },
  { id: 'alerts', label: 'Alerts' },
];

export interface ObservabilityTabsProps {
  traces?: TraceInfo[];
  logs?: LogEntry[];
  metrics?: MetricsSummary | null;
  alerts?: Alert[];
  alertCount?: number;
  isLoading?: boolean;
  onSelectTrace?: (traceId: string) => void;
  onAcknowledgeAlert?: (alertId: string) => void;
}

export function ObservabilityTabs({
  traces = [],
  logs = [],
  metrics = null,
  alerts = [],
  alertCount,
  isLoading = false,
  onSelectTrace,
  onAcknowledgeAlert,
}: ObservabilityTabsProps): React.ReactElement {
  const [activeTab, setActiveTab] = useState<TabId>('traces');

  const displayAlertCount = alertCount ?? alerts.filter((a) => !a.acknowledged).length;

  return (
    <div className="flex flex-col h-full">
      {/* Tab buttons */}
      <div
        className="flex border-b border-gray-200 dark:border-dark-border"
        role="tablist"
        aria-label="Observability views"
      >
        {TABS.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`panel-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'px-4 py-2 text-sm font-medium transition-colors',
              'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-inset',
              activeTab === tab.id
                ? 'text-primary-600 dark:text-primary-400 border-b-2 border-primary-600 dark:border-primary-400'
                : 'text-gray-500 dark:text-dark-textMuted hover:text-gray-700 dark:hover:text-dark-textSecondary'
            )}
          >
            {tab.label}
            {tab.id === 'alerts' && displayAlertCount > 0 && (
              <span className="ml-2 inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full bg-error-100 text-error-700 dark:bg-error-900 dark:text-error-300">
                {displayAlertCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab panels */}
      <div className="flex-1 overflow-auto">
        {activeTab === 'traces' && (
          <div id="panel-traces" role="tabpanel" aria-labelledby="tab-traces">
            <TracePanel
              traces={traces}
              isLoading={isLoading}
              onTraceSelect={onSelectTrace}
            />
          </div>
        )}
        {activeTab === 'logs' && (
          <div id="panel-logs" role="tabpanel" aria-labelledby="tab-logs">
            <LogPanel logs={logs} isLoading={isLoading} />
          </div>
        )}
        {activeTab === 'metrics' && (
          <div id="panel-metrics" role="tabpanel" aria-labelledby="tab-metrics">
            <MetricsPanel metrics={metrics} isLoading={isLoading} />
          </div>
        )}
        {activeTab === 'alerts' && (
          <div id="panel-alerts" role="tabpanel" aria-labelledby="tab-alerts">
            <AlertPanel
              alerts={alerts}
              isLoading={isLoading}
              onAcknowledge={onAcknowledgeAlert}
            />
          </div>
        )}
      </div>
    </div>
  );
}
