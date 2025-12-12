/**
 * ToolCard Component
 *
 * Displays a single MCP tool with name, description, and selection state.
 */

import React from 'react';
import clsx from 'clsx';
import type { MCPTool } from '../../api/mcp-types';

export interface ToolCardProps {
  tool: MCPTool;
  isSelected?: boolean;
  onClick?: () => void;
}

function ToolIcon({ className }: { className?: string }) {
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
        d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z"
      />
    </svg>
  );
}

export function ToolCard({ tool, isSelected = false, onClick }: ToolCardProps): React.ReactElement {
  const paramCount = Object.keys(tool.inputSchema.properties || {}).length;
  const requiredCount = (tool.inputSchema.required || []).length;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left p-3 rounded-lg border transition-colors',
        isSelected
          ? 'bg-primary-50 dark:bg-primary-900/20 border-primary-500'
          : 'bg-white dark:bg-dark-surface border-gray-200 dark:border-dark-border hover:bg-gray-50 dark:hover:bg-dark-hover'
      )}
    >
      <div className="flex items-start gap-3">
        <div
          className={clsx(
            'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center',
            isSelected
              ? 'bg-primary-500 text-white'
              : 'bg-gray-100 dark:bg-dark-bg text-gray-600 dark:text-dark-textSecondary'
          )}
        >
          <ToolIcon className="w-5 h-5" />
        </div>

        <div className="flex-1 min-w-0">
          <h4
            className={clsx(
              'font-medium truncate',
              isSelected
                ? 'text-primary-700 dark:text-primary-400'
                : 'text-gray-900 dark:text-dark-text'
            )}
          >
            {tool.name}
          </h4>
          <p className="text-sm text-gray-500 dark:text-dark-textMuted line-clamp-2">
            {tool.description}
          </p>

          {/* Parameter info */}
          {paramCount > 0 && (
            <div className="mt-1 text-xs text-gray-400 dark:text-dark-textMuted">
              {paramCount} param{paramCount !== 1 ? 's' : ''}
              {requiredCount > 0 && ` (${requiredCount} required)`}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
