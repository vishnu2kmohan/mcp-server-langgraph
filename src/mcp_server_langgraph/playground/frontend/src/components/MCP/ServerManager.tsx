/**
 * ServerManager Component
 *
 * Manages MCP server connections with add/remove functionality.
 */

import React, { useState, useCallback } from 'react';
import clsx from 'clsx';
import type { MCPServerConnection } from '../../api/mcp-types';

export interface ServerManagerProps {
  servers: MCPServerConnection[];
  onAddServer: (url: string) => void;
  onRemoveServer: (serverId: string) => void;
}

function getStatusColor(status: MCPServerConnection['status']): string {
  switch (status) {
    case 'connected':
      return 'bg-success-500';
    case 'connecting':
      return 'bg-warning-500';
    case 'disconnected':
      return 'bg-gray-400';
    case 'error':
      return 'bg-error-500';
    default:
      return 'bg-gray-400';
  }
}

function getStatusText(status: MCPServerConnection['status']): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export function ServerManager({
  servers,
  onAddServer,
  onRemoveServer,
}: ServerManagerProps): React.ReactElement {
  const [newServerUrl, setNewServerUrl] = useState('');

  const handleAddServer = useCallback(() => {
    if (newServerUrl.trim()) {
      onAddServer(newServerUrl.trim());
      setNewServerUrl('');
    }
  }, [newServerUrl, onAddServer]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        handleAddServer();
      }
    },
    [handleAddServer]
  );

  return (
    <div className="space-y-4">
      {/* Add Server Form */}
      <div className="flex gap-2">
        <input
          type="url"
          value={newServerUrl}
          onChange={(e) => setNewServerUrl(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Server URL (e.g., http://localhost:8001)"
          className={clsx(
            'flex-1 px-3 py-2 border rounded-lg',
            'bg-white dark:bg-dark-surface',
            'border-gray-300 dark:border-dark-border',
            'text-gray-900 dark:text-dark-text',
            'placeholder-gray-400 dark:placeholder-dark-textMuted',
            'focus:outline-none focus:ring-2 focus:ring-primary-500'
          )}
        />
        <button
          onClick={handleAddServer}
          disabled={!newServerUrl.trim()}
          className={clsx(
            'px-4 py-2 rounded-lg font-medium',
            'bg-primary-600 text-white',
            'hover:bg-primary-700',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'
          )}
        >
          Add
        </button>
      </div>

      {/* Server List */}
      {servers.length === 0 ? (
        <div className="p-4 text-center text-gray-500 dark:text-dark-textMuted">
          No servers connected
        </div>
      ) : (
        <div className="space-y-2">
          {servers.map((server) => (
            <div
              key={server.id}
              className={clsx(
                'p-3 rounded-lg border',
                'bg-white dark:bg-dark-surface',
                'border-gray-200 dark:border-dark-border'
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  {/* Server ID and Status */}
                  <div className="flex items-center gap-2">
                    <span
                      className={clsx(
                        'w-2 h-2 rounded-full',
                        getStatusColor(server.status)
                      )}
                      aria-hidden="true"
                    />
                    <span className="font-medium text-gray-900 dark:text-dark-text truncate">
                      {server.id}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-dark-textMuted">
                      {getStatusText(server.status)}
                    </span>
                  </div>

                  {/* URL */}
                  <p className="text-xs text-gray-500 dark:text-dark-textMuted mt-1 truncate">
                    {server.url}
                  </p>

                  {/* Error message */}
                  {server.error && (
                    <p className="text-xs text-error-600 dark:text-error-400 mt-1">
                      {server.error}
                    </p>
                  )}

                  {/* Capability Badges */}
                  <div className="flex flex-wrap gap-1 mt-2">
                    {server.capabilities?.tools && (
                      <span className="px-2 py-0.5 text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded">
                        Tools
                      </span>
                    )}
                    {server.capabilities?.resources && (
                      <span className="px-2 py-0.5 text-xs bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300 rounded">
                        Resources
                      </span>
                    )}
                    {server.capabilities?.prompts && (
                      <span className="px-2 py-0.5 text-xs bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300 rounded">
                        Prompts
                      </span>
                    )}
                  </div>
                </div>

                {/* Remove Button */}
                <button
                  onClick={() => onRemoveServer(server.id)}
                  className={clsx(
                    'p-1 rounded text-gray-400 dark:text-dark-textMuted',
                    'hover:text-error-600 dark:hover:text-error-400',
                    'hover:bg-error-50 dark:hover:bg-error-900/20',
                    'focus:outline-none focus:ring-2 focus:ring-error-500'
                  )}
                  aria-label={`Remove ${server.id}`}
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
