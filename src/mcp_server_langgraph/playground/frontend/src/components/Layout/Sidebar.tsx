/**
 * Sidebar Component
 *
 * Collapsible sidebar for session list, server management, and navigation.
 */

import React, { ReactNode, useState, useCallback } from 'react';
import clsx from 'clsx';
import { useMCPHost } from '../../contexts/MCPHostContext';
import { ServerManager } from '../MCP/ServerManager';

// Chevron icons
function ChevronLeftIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M15.75 19.5L8.25 12l7.5-7.5"
      />
    </svg>
  );
}

function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M8.25 4.5l7.5 7.5-7.5 7.5"
      />
    </svg>
  );
}

export interface SidebarProps {
  children: ReactNode;
  title?: string;
  collapsed?: boolean;
  onToggle?: () => void;
}

export function Sidebar({
  children,
  title,
  collapsed = false,
  onToggle,
}: SidebarProps): React.ReactElement {
  const { servers, addServer, removeServer } = useMCPHost();
  const [serversExpanded, setServersExpanded] = useState(true);

  // Convert servers Map to array for ServerManager
  const serverArray = Array.from(servers.values());

  // Generate unique ID for new server
  const handleAddServer = useCallback(
    async (url: string) => {
      const id = `server-${Date.now()}`;
      try {
        await addServer(id, url);
      } catch (error) {
        console.error('Failed to add server:', error);
      }
    },
    [addServer]
  );

  return (
    <aside
      className={clsx(
        'flex flex-col h-full bg-gray-50 dark:bg-dark-surface border-r border-gray-200 dark:border-dark-border transition-all duration-200',
        collapsed ? 'w-16' : 'w-80'
      )}
      role="complementary"
      aria-label="Sidebar"
    >
      {/* Header */}
      <div className="flex items-center justify-between h-14 px-4 border-b border-gray-200 dark:border-dark-border">
        {!collapsed && title && (
          <h2 className="font-medium text-gray-900 dark:text-dark-text">{title}</h2>
        )}
        {onToggle && (
          <button
            onClick={onToggle}
            className="btn btn-ghost p-1"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? (
              <ChevronRightIcon className="w-5 h-5" />
            ) : (
              <ChevronLeftIcon className="w-5 h-5" />
            )}
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {collapsed ? null : (
          <>
            {/* Sessions Section */}
            <div className="border-b border-gray-200 dark:border-dark-border">
              <div className="px-4 py-3">
                <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary uppercase tracking-wider">
                  Sessions
                </h3>
              </div>
              <div className="px-2 pb-3">{children}</div>
            </div>

            {/* MCP Servers Section */}
            <div className="border-b border-gray-200 dark:border-dark-border">
              <button
                onClick={() => setServersExpanded(!serversExpanded)}
                className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-100 dark:hover:bg-dark-hover transition-colors"
              >
                <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary uppercase tracking-wider">
                  MCP Servers
                </h3>
                <ChevronDownIcon
                  className={clsx(
                    'w-4 h-4 text-gray-400 transition-transform',
                    serversExpanded ? 'rotate-180' : ''
                  )}
                />
              </button>
              {serversExpanded && (
                <div className="px-2 pb-3">
                  <ServerManager
                    servers={serverArray}
                    onAddServer={handleAddServer}
                    onRemoveServer={removeServer}
                  />
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </aside>
  );
}

// Chevron down icon for collapsible sections
function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={1.5}
      stroke="currentColor"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19.5 8.25l-7.5 7.5-7.5-7.5"
      />
    </svg>
  );
}
