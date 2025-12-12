/**
 * SamplingDialog Component
 *
 * Modal dialog for MCP sampling requests (server→client LLM requests).
 * Shows the pending LLM request for user approval.
 */

import React, { useId, useEffect } from 'react';
import clsx from 'clsx';
import type { PendingSamplingRequest, SamplingMessage, ModelHint } from '../../api/mcp-types';

export interface SamplingDialogProps {
  request: PendingSamplingRequest | null;
  onApprove: () => void;
  onReject: (reason?: string) => void;
}

export function SamplingDialog({
  request,
  onApprove,
  onReject,
}: SamplingDialogProps): React.ReactElement | null {
  const titleId = useId();

  // Handle Escape key to reject
  useEffect(() => {
    if (!request) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onReject('User cancelled');
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [request, onReject]);

  if (!request) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={() => onReject('User cancelled')}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={clsx(
          'relative z-10 w-full max-w-lg mx-4',
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
              Sampling Request
            </h2>
            <p className="text-xs text-gray-500 dark:text-dark-textMuted mt-1">
              From: {request.serverId}
            </p>
          </div>

          {/* System Prompt */}
          {request.systemPrompt && (
            <div className="mb-4">
              <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary mb-1">
                System Prompt
              </h3>
              <div className="p-3 bg-gray-100 dark:bg-dark-surfaceHover rounded-lg">
                <p className="text-sm text-gray-800 dark:text-dark-text whitespace-pre-wrap">
                  {request.systemPrompt}
                </p>
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary mb-1">
              Messages
            </h3>
            <div className="space-y-2">
              {request.messages.map((msg: SamplingMessage, idx: number) => (
                <div
                  key={idx}
                  className={clsx(
                    'p-3 rounded-lg',
                    msg.role === 'user'
                      ? 'bg-primary-50 dark:bg-primary-900/20'
                      : 'bg-gray-100 dark:bg-dark-surfaceHover'
                  )}
                >
                  <div className="text-xs font-medium text-gray-500 dark:text-dark-textMuted mb-1 uppercase">
                    {msg.role}
                  </div>
                  <p className="text-sm text-gray-800 dark:text-dark-text whitespace-pre-wrap">
                    {msg.content.type === 'text' ? msg.content.text : '[Non-text content]'}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Model Preferences */}
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-700 dark:text-dark-textSecondary mb-1">
              Model Preferences
            </h3>
            <div className="flex flex-wrap gap-2">
              {request.modelPreferences?.hints?.map((hint: ModelHint, idx: number) => (
                <span
                  key={idx}
                  className="px-2 py-1 text-xs bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 rounded"
                >
                  {hint.name}
                </span>
              ))}
            </div>
          </div>

          {/* Max Tokens */}
          <div className="mb-6 flex items-center justify-between text-sm">
            <span className="text-gray-600 dark:text-dark-textSecondary">Max Tokens</span>
            <span className="font-medium text-gray-900 dark:text-dark-text">
              {request.maxTokens}
            </span>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={onApprove}
              className={clsx(
                'flex-1 px-4 py-2 rounded-lg font-medium',
                'bg-success-600 text-white',
                'hover:bg-success-700',
                'focus:outline-none focus:ring-2 focus:ring-success-500 focus:ring-offset-2'
              )}
            >
              Approve
            </button>
            <button
              onClick={() => onReject()}
              className={clsx(
                'flex-1 px-4 py-2 rounded-lg font-medium',
                'bg-error-600 text-white',
                'hover:bg-error-700',
                'focus:outline-none focus:ring-2 focus:ring-error-500 focus:ring-offset-2'
              )}
            >
              Reject
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
