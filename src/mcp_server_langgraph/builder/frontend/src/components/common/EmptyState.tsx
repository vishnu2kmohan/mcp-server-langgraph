/**
 * EmptyState Components for Visual Workflow Builder
 *
 * Provides helpful empty state messaging with:
 * - Clear titles and descriptions
 * - Optional icons
 * - Call-to-action buttons
 *
 * Variants:
 * - EmptyCanvas: Empty workflow canvas
 * - EmptyCodePanel: No generated code
 * - ConnectionError: Network/API connection issues
 */

import React from 'react';
import { Package, Code2, WifiOff, MousePointerClick } from 'lucide-react';

// ==============================================================================
// Types
// ==============================================================================

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

// ==============================================================================
// Helper to combine class names
// ==============================================================================

function clsx(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(' ');
}

// ==============================================================================
// Base EmptyState Component
// ==============================================================================

export function EmptyState({
  title,
  description,
  icon,
  actionLabel,
  onAction,
  className,
}: EmptyStateProps): React.ReactElement {
  return (
    <div
      className={clsx(
        'flex flex-col items-center justify-center py-12 px-4 text-center',
        className
      )}
      data-testid="empty-state"
    >
      {icon && (
        <div className="mb-4 text-gray-400 dark:text-gray-500">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
        {title}
      </h3>
      {description && (
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-4">
          {description}
        </p>
      )}
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

// ==============================================================================
// EmptyCanvas Component (empty workflow)
// ==============================================================================

export interface EmptyCanvasProps {
  onGetStarted?: () => void;
  className?: string;
}

export function EmptyCanvas({ onGetStarted, className }: EmptyCanvasProps): React.ReactElement {
  return (
    <EmptyState
      title="Your Canvas is Empty"
      description="Drag nodes from the sidebar to get started building your workflow. Connect nodes to define the execution flow."
      icon={<MousePointerClick size={48} strokeWidth={1.5} />}
      actionLabel="Get Started"
      onAction={onGetStarted}
      className={className}
    />
  );
}

// ==============================================================================
// EmptyCodePanel Component (no generated code)
// ==============================================================================

export interface EmptyCodePanelProps {
  className?: string;
}

export function EmptyCodePanel({ className }: EmptyCodePanelProps): React.ReactElement {
  return (
    <EmptyState
      title="No Code Generated Yet"
      description="Add nodes to your canvas and connect them, then click 'Generate Code' to export production-ready Python code."
      icon={<Code2 size={48} strokeWidth={1.5} />}
      className={className}
    />
  );
}

// ==============================================================================
// ConnectionError Component (network issues)
// ==============================================================================

export interface ConnectionErrorProps {
  onRetry?: () => void;
  className?: string;
}

export function ConnectionError({ onRetry, className }: ConnectionErrorProps): React.ReactElement {
  return (
    <EmptyState
      title="Unable to Connect"
      description="We couldn't connect to the server. Check your network connection and try again."
      icon={<WifiOff size={48} strokeWidth={1.5} />}
      actionLabel="Retry"
      onAction={onRetry}
      className={className}
    />
  );
}

// ==============================================================================
// NoWorkflows Component (no saved workflows)
// ==============================================================================

export interface NoWorkflowsProps {
  onCreateNew?: () => void;
  className?: string;
}

export function NoWorkflows({ onCreateNew, className }: NoWorkflowsProps): React.ReactElement {
  return (
    <EmptyState
      title="No Workflows Yet"
      description="Create your first workflow to start automating tasks with AI agents."
      icon={<Package size={48} strokeWidth={1.5} />}
      actionLabel="Create Workflow"
      onAction={onCreateNew}
      className={className}
    />
  );
}
