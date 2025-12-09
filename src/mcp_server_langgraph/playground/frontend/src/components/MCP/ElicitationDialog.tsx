/**
 * ElicitationDialog Component
 *
 * Modal dialog for MCP elicitation requests (2025-06-18 spec).
 * Displays a JSON schema form and provides Accept/Decline/Cancel actions.
 */

import React, { useState, useCallback, useId, useEffect } from 'react';
import clsx from 'clsx';
import { SchemaForm } from './SchemaForm';
import type { Elicitation, JSONSchema } from '../../api/mcp-types';

export interface ElicitationDialogProps {
  elicitation: Elicitation | null;
  onAccept: (content: Record<string, unknown>) => void;
  onDecline: () => void;
  onCancel: () => void;
}

export function ElicitationDialog({
  elicitation,
  onAccept,
  onDecline,
  onCancel,
}: ElicitationDialogProps): React.ReactElement | null {
  const titleId = useId();
  const formRef = React.useRef<{ getData: () => Record<string, unknown> } | null>(null);
  const [formData, setFormData] = useState<Record<string, unknown>>({});

  // Reset form data when elicitation changes
  useEffect(() => {
    if (elicitation) {
      setFormData({});
    }
  }, [elicitation?.id]);

  const handleFormChange = useCallback(
    (data: Record<string, unknown>) => {
      setFormData(data);
    },
    []
  );

  const handleAccept = useCallback(() => {
    onAccept(formData);
  }, [formData, onAccept]);

  // Handle Escape key to cancel
  useEffect(() => {
    if (!elicitation) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [elicitation, onCancel]);

  if (!elicitation) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onCancel}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={clsx(
          'relative z-10 w-full max-w-md mx-4',
          'bg-white dark:bg-dark-surface',
          'rounded-lg shadow-xl',
          'max-h-[90vh] overflow-auto'
        )}
      >
        <div className="p-6">
          {/* Header */}
          <div className="mb-4">
            <h2
              id={titleId}
              className="text-lg font-semibold text-gray-900 dark:text-dark-text"
            >
              Elicitation Request
            </h2>
            <p className="text-xs text-gray-500 dark:text-dark-textMuted mt-1">
              From: {elicitation.serverId}
            </p>
          </div>

          {/* Message */}
          <p className="text-sm text-gray-700 dark:text-dark-textSecondary mb-4">
            {elicitation.message}
          </p>

          {/* Schema Form */}
          <div className="mb-6">
            <SchemaForm
              schema={elicitation.requestedSchema}
              onSubmit={handleFormChange}
              onChange={handleFormChange}
              submitLabel="Update Values"
            />
          </div>

          {/* Action Buttons (per MCP 2025-06-18 spec) */}
          <div className="flex gap-3">
            <button
              onClick={handleAccept}
              className={clsx(
                'flex-1 px-4 py-2 rounded-lg font-medium',
                'bg-success-600 text-white',
                'hover:bg-success-700',
                'focus:outline-none focus:ring-2 focus:ring-success-500 focus:ring-offset-2'
              )}
            >
              Accept
            </button>
            <button
              onClick={onDecline}
              className={clsx(
                'flex-1 px-4 py-2 rounded-lg font-medium',
                'bg-warning-600 text-white',
                'hover:bg-warning-700',
                'focus:outline-none focus:ring-2 focus:ring-warning-500 focus:ring-offset-2'
              )}
            >
              Decline
            </button>
            <button
              onClick={onCancel}
              className={clsx(
                'flex-1 px-4 py-2 rounded-lg font-medium',
                'bg-gray-200 dark:bg-dark-border text-gray-700 dark:text-dark-text',
                'hover:bg-gray-300 dark:hover:bg-dark-surfaceHover',
                'focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2'
              )}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
