/**
 * AgentInfoBadge Component
 *
 * Displays agent transparency information (P4).
 * Shows confidence, reasoning, and verification scores.
 */

import React, { useState, useCallback } from 'react';
import clsx from 'clsx';
import type { AgentMetadata } from '../../api/types';

export interface AgentInfoBadgeProps {
  metadata: AgentMetadata;
  className?: string;
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-success-600 dark:text-success-400';
  if (confidence >= 0.5) return 'text-warning-600 dark:text-warning-400';
  return 'text-error-600 dark:text-error-400';
}

function getConfidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return 'High';
  if (confidence >= 0.5) return 'Medium';
  return 'Low';
}

export function AgentInfoBadge({
  metadata,
  className,
}: AgentInfoBadgeProps): React.ReactElement {
  const [isExpanded, setIsExpanded] = useState(false);

  const handleToggle = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const hasDetails =
    metadata.reasoning ||
    metadata.verificationScore !== undefined ||
    metadata.refinementAttempts !== undefined ||
    metadata.contextTokensBefore !== undefined;

  return (
    <div className={clsx('mt-2', className)}>
      {/* Compact Badge */}
      <button
        onClick={handleToggle}
        className={clsx(
          'inline-flex items-center gap-2 px-2 py-1 rounded-lg text-xs',
          'bg-gray-100 dark:bg-dark-bg',
          'hover:bg-gray-200 dark:hover:bg-dark-hover',
          'transition-colors'
        )}
        aria-expanded={isExpanded}
        aria-label="Toggle agent details"
      >
        {/* Confidence indicator */}
        {metadata.confidence !== undefined && (
          <span className={clsx('font-medium', getConfidenceColor(metadata.confidence))}>
            {Math.round(metadata.confidence * 100)}% {getConfidenceLabel(metadata.confidence)}
          </span>
        )}

        {/* Response format */}
        {metadata.responseFormat && (
          <span className="text-gray-500 dark:text-dark-textMuted">
            • {metadata.responseFormat}
          </span>
        )}

        {/* Expand/collapse indicator */}
        {hasDetails && (
          <svg
            className={clsx(
              'w-3 h-3 text-gray-400 transition-transform',
              isExpanded && 'rotate-180'
            )}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {/* Expanded Details */}
      {isExpanded && hasDetails && (
        <div
          className={clsx(
            'mt-2 p-3 rounded-lg text-xs',
            'bg-gray-50 dark:bg-dark-bg',
            'border border-gray-200 dark:border-dark-border',
            'animate-in slide-in-from-top-1 duration-150'
          )}
        >
          {/* Reasoning */}
          {metadata.reasoning && (
            <div className="mb-3">
              <h4 className="font-medium text-gray-700 dark:text-dark-textSecondary mb-1">
                Agent Reasoning
              </h4>
              <p className="text-gray-600 dark:text-dark-textMuted">
                {metadata.reasoning}
              </p>
            </div>
          )}

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-2">
            {metadata.verificationScore !== undefined && (
              <div className="p-2 bg-white dark:bg-dark-surface rounded">
                <div className="text-gray-500 dark:text-dark-textMuted">Verification</div>
                <div className="font-medium text-gray-900 dark:text-dark-text">
                  {Math.round(metadata.verificationScore * 100)}%
                </div>
              </div>
            )}

            {metadata.refinementAttempts !== undefined && (
              <div className="p-2 bg-white dark:bg-dark-surface rounded">
                <div className="text-gray-500 dark:text-dark-textMuted">Refinements</div>
                <div className="font-medium text-gray-900 dark:text-dark-text">
                  {metadata.refinementAttempts}
                </div>
              </div>
            )}

            {metadata.contextTokensBefore !== undefined && metadata.contextTokensAfter !== undefined && (
              <div className="p-2 bg-white dark:bg-dark-surface rounded col-span-2">
                <div className="text-gray-500 dark:text-dark-textMuted">Context Compaction</div>
                <div className="font-medium text-gray-900 dark:text-dark-text">
                  {metadata.contextTokensBefore.toLocaleString()} → {metadata.contextTokensAfter.toLocaleString()} tokens
                  <span className="text-success-600 dark:text-success-400 ml-1">
                    (-{Math.round((1 - metadata.contextTokensAfter / metadata.contextTokensBefore) * 100)}%)
                  </span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
