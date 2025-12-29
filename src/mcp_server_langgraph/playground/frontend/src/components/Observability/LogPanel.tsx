/**
 * LogPanel Component
 *
 * Displays structured logs with level filtering and formatting.
 */

import React from 'react';
import clsx from 'clsx';
import type { LogEntry, LogLevel } from '../../api/types';

export interface LogPanelProps {
  logs: LogEntry[];
  isLoading?: boolean;
}

function getLevelBadgeClass(level: LogLevel): string {
  switch (level) {
    case 'error':
      return 'badge-error';
    case 'warning':
      return 'badge-warning';
    case 'info':
      return 'badge-info';
    case 'debug':
      return 'badge bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-200';
    default:
      return 'badge';
  }
}

function formatTime(dateString: string): string {
  return new Date(dateString).toLocaleTimeString();
}

export function LogPanel({
  logs,
  isLoading = false,
}: LogPanelProps): React.ReactElement {
  if (isLoading) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        <div className="animate-pulse">Loading logs...</div>
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
        No logs yet
      </div>
    );
  }

  return (
    <div className="font-mono text-sm divide-y divide-gray-200 dark:divide-dark-border">
      {logs.map((log) => (
        <div
          key={log.id}
          className={clsx(
            'p-2 flex items-start gap-2',
            log.level === 'error' && 'bg-error-50 dark:bg-error-900/10'
          )}
        >
          <span className="text-xs text-gray-400 flex-shrink-0">
            {formatTime(log.timestamp)}
          </span>
          <span className={clsx('badge', getLevelBadgeClass(log.level))}>
            {log.level.toUpperCase()}
          </span>
          <span className="text-gray-500 dark:text-dark-textMuted flex-shrink-0">
            [{log.logger}]
          </span>
          <span className="text-gray-900 dark:text-dark-text break-all">
            {log.message}
          </span>
        </div>
      ))}
    </div>
  );
}
