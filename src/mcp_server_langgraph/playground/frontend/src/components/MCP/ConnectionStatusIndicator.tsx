/**
 * ConnectionStatusIndicator Component
 *
 * Real-time indicator showing MCP server connection status.
 * Displays connection state with visual indicators and counts.
 */

import React, { useMemo } from 'react';
import clsx from 'clsx';
import { useMCPHost } from '../../contexts/MCPHostContext';
import type { MCPConnectionStatus } from '../../api/mcp-types';

export interface ConnectionStatusIndicatorProps {
  variant?: 'default' | 'compact';
  className?: string;
}

type OverallStatus = 'connected' | 'connecting' | 'error' | 'disconnected';

interface StatusInfo {
  status: OverallStatus;
  connectedCount: number;
  totalCount: number;
  primaryServerName?: string;
}

function getStatusInfo(
  servers: Map<string, { status: MCPConnectionStatus; serverInfo?: { name?: string } }>,
  primaryServerId: string | null
): StatusInfo {
  const total = servers.size;

  if (total === 0) {
    return { status: 'disconnected', connectedCount: 0, totalCount: 0 };
  }

  let connectedCount = 0;
  let hasConnecting = false;
  let hasError = false;
  let primaryServerName: string | undefined;

  for (const [id, server] of servers) {
    if (server.status === 'connected') {
      connectedCount++;
    }
    if (server.status === 'connecting') {
      hasConnecting = true;
    }
    if (server.status === 'error') {
      hasError = true;
    }
    if (id === primaryServerId && server.serverInfo?.name) {
      primaryServerName = server.serverInfo.name;
    }
  }

  let status: OverallStatus;
  if (hasConnecting) {
    status = 'connecting';
  } else if (connectedCount > 0) {
    status = 'connected';
  } else if (hasError) {
    status = 'error';
  } else {
    status = 'disconnected';
  }

  return { status, connectedCount, totalCount: total, primaryServerName };
}

function getIndicatorClasses(status: OverallStatus): string {
  switch (status) {
    case 'connected':
      return 'bg-success-500';
    case 'connecting':
      return 'bg-warning-500 animate-pulse';
    case 'error':
      return 'bg-error-500';
    case 'disconnected':
    default:
      return 'bg-gray-400 dark:bg-gray-600';
  }
}

function getStatusText(info: StatusInfo): string {
  switch (info.status) {
    case 'connected':
      return info.totalCount > 1 ? `${info.connectedCount} of ${info.totalCount}` : 'Connected';
    case 'connecting':
      return 'Connecting...';
    case 'error':
      return 'Error';
    case 'disconnected':
    default:
      return 'Disconnected';
  }
}

export function ConnectionStatusIndicator({
  variant = 'default',
  className,
}: ConnectionStatusIndicatorProps): React.ReactElement {
  const { servers, primaryServerId } = useMCPHost();

  const statusInfo = useMemo(
    () => getStatusInfo(servers as Map<string, { status: MCPConnectionStatus; serverInfo?: { name?: string } }>, primaryServerId),
    [servers, primaryServerId]
  );

  const indicatorClasses = getIndicatorClasses(statusInfo.status);
  const statusText = getStatusText(statusInfo);

  return (
    <div
      className={clsx(
        'flex items-center gap-2',
        className
      )}
      aria-label="MCP Connection Status"
      role="status"
    >
      {/* Status indicator dot */}
      <span
        data-testid="status-indicator"
        className={clsx(
          'w-2 h-2 rounded-full',
          indicatorClasses
        )}
      />

      {/* Status text (hidden in compact mode) */}
      {variant !== 'compact' && (
        <span className="text-sm text-gray-600 dark:text-dark-textSecondary">
          {statusText}
        </span>
      )}
    </div>
  );
}
