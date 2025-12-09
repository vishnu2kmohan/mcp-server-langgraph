/**
 * SessionCard Component
 *
 * Displays a session summary in the sidebar list.
 */

import React from 'react';
import clsx from 'clsx';
import type { SessionSummary } from '../../api/types';

// Trash icon
function TrashIcon({ className }: { className?: string }) {
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
        d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"
      />
    </svg>
  );
}

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export interface SessionCardProps {
  session: SessionSummary;
  isSelected?: boolean;
  onClick?: (sessionId: string) => void;
  onDelete?: (sessionId: string) => void;
}

export function SessionCard({
  session,
  isSelected = false,
  onClick,
  onDelete,
}: SessionCardProps): React.ReactElement {
  const handleClick = () => {
    onClick?.(session.id);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(session.id);
  };

  return (
    <button
      onClick={handleClick}
      className={clsx(
        'w-full text-left p-3 rounded-lg border transition-colors',
        'hover:bg-gray-100 dark:hover:bg-dark-surfaceHover',
        isSelected
          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
          : 'border-gray-200 dark:border-dark-border bg-white dark:bg-dark-surface'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-medium text-gray-900 dark:text-dark-text truncate">
            {session.name}
          </h3>
          <p className="text-sm text-gray-500 dark:text-dark-textMuted mt-1">
            {session.messageCount} messages
          </p>
          <p className="text-xs text-gray-400 dark:text-dark-textMuted mt-1">
            {formatRelativeTime(session.updatedAt)}
          </p>
        </div>
        {onDelete && (
          <button
            onClick={handleDelete}
            className="p-1 text-gray-400 hover:text-error-500 transition-colors"
            aria-label="Delete session"
          >
            <TrashIcon className="w-4 h-4" />
          </button>
        )}
      </div>
    </button>
  );
}
