/**
 * Sidebar Component
 *
 * Collapsible sidebar for session list and navigation.
 */

import React, { ReactNode } from 'react';
import clsx from 'clsx';

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
        {collapsed ? null : children}
      </div>
    </aside>
  );
}
