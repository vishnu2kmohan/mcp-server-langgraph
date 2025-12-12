/**
 * AlertPanel Component
 *
 * Displays alerts with severity-based styling and acknowledgment.
 */

import React from 'react';
import clsx from 'clsx';
import type { Alert, AlertSeverity } from '../../api/types';

export interface AlertPanelProps {
  alerts: Alert[];
  isLoading?: boolean;
  onAcknowledge?: (alertId: string) => void;
}

function getSeverityClass(severity: AlertSeverity): string {
  switch (severity) {
    case 'critical':
      return 'alert-critical';
    case 'high':
      return 'alert-high';
    case 'medium':
      return 'alert-medium';
    case 'low':
      return 'alert-low';
    default:
      return '';
  }
}

function formatTime(dateString: string): string {
  return new Date(dateString).toLocaleTimeString();
}

export function AlertPanel({
  alerts,
  isLoading = false,
  onAcknowledge,
}: AlertPanelProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        <div className="animate-pulse">Loading alerts...</div>
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        No alerts
      </div>
    );
  }

  return (
    <div
      className="space-y-2 p-2"
      role="region"
      aria-live="assertive"
      aria-label="Alerts"
    >
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={clsx(
            'p-3 rounded-lg',
            getSeverityClass(alert.severity),
            alert.acknowledged && 'opacity-60'
          )}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900 dark:text-dark-text">
                  {alert.title}
                </span>
                <span className="badge text-xs uppercase">{alert.severity}</span>
              </div>
              <p className="text-sm text-gray-600 dark:text-dark-textSecondary mt-1">
                {alert.description}
              </p>
              <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                <span>{alert.source}</span>
                <span>{formatTime(alert.timestamp)}</span>
                {alert.acknowledged && (
                  <span className="text-success-600 dark:text-success-400">
                    Acknowledged
                  </span>
                )}
              </div>
            </div>
            {!alert.acknowledged && onAcknowledge && (
              <button
                onClick={() => onAcknowledge(alert.id)}
                className="btn btn-ghost text-sm"
                aria-label={`Acknowledge ${alert.title}`}
              >
                Acknowledge
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
