/**
 * AgentReasoningPanel Component
 *
 * A collapsible panel showing agent's reasoning, tool calls,
 * and context compaction. Part of P4.3 Agent Transparency.
 */

import React, { useState, useCallback } from 'react';
import clsx from 'clsx';

export interface ToolCallInfo {
  name: string;
  arguments: Record<string, unknown>;
  result?: string;
  error?: string;
}

export interface ContextCompactionInfo {
  before: number;
  after: number;
  method?: string;
}

export interface RefinementInfo {
  iteration: number;
  change: string;
  score: number;
}

export interface AgentReasoningData {
  reasoning: string;
  routingDecision?: string;
  confidence?: number;
  toolCalls?: ToolCallInfo[];
  contextCompaction?: ContextCompactionInfo;
  refinementHistory?: RefinementInfo[];
}

export interface AgentReasoningPanelProps {
  data: AgentReasoningData;
  defaultExpanded?: boolean;
  className?: string;
}

function ChevronIcon({ isExpanded, className }: { isExpanded: boolean; className?: string }) {
  return (
    <svg
      className={clsx(
        'w-4 h-4 transition-transform',
        isExpanded && 'rotate-180',
        className
      )}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
}

function ToolIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z"
      />
    </svg>
  );
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'text-success-600 dark:text-success-400';
  if (confidence >= 0.5) return 'text-warning-600 dark:text-warning-400';
  return 'text-error-600 dark:text-error-400';
}

export function AgentReasoningPanel({
  data,
  defaultExpanded = false,
  className,
}: AgentReasoningPanelProps): React.ReactElement {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  const handleToggle = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const toolCount = data.toolCalls?.length ?? 0;

  return (
    <div
      className={clsx(
        'border border-gray-200 dark:border-dark-border rounded-lg overflow-hidden',
        'bg-white dark:bg-dark-surface',
        className
      )}
    >
      {/* Header */}
      <button
        onClick={handleToggle}
        className={clsx(
          'w-full flex items-center justify-between px-4 py-3',
          'text-left text-sm font-medium',
          'text-gray-700 dark:text-dark-textSecondary',
          'hover:bg-gray-50 dark:hover:bg-dark-hover',
          'transition-colors'
        )}
        aria-expanded={isExpanded}
      >
        <div className="flex items-center gap-2">
          <span>Agent Reasoning</span>
          {toolCount > 0 && (
            <span className="px-2 py-0.5 text-xs rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-400">
              {toolCount} tool{toolCount !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <ChevronIcon isExpanded={isExpanded} />
      </button>

      {/* Content */}
      {isExpanded && (
        <div
          className={clsx(
            'px-4 pb-4 space-y-4',
            'animate-in slide-in-from-top-1 duration-150'
          )}
        >
          {/* Reasoning */}
          <div>
            <h4 className="text-xs font-medium text-gray-500 dark:text-dark-textMuted uppercase tracking-wider mb-2">
              Reasoning
            </h4>
            <p className="text-sm text-gray-700 dark:text-dark-textSecondary leading-relaxed">
              {data.reasoning}
            </p>
          </div>

          {/* Routing & Confidence Row */}
          {(data.routingDecision || data.confidence !== undefined) && (
            <div className="flex flex-wrap gap-4">
              {data.routingDecision && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 dark:text-dark-textMuted uppercase tracking-wider mb-1">
                    Routing
                  </h4>
                  <span className="inline-flex items-center px-2 py-1 rounded text-sm bg-gray-100 dark:bg-dark-bg text-gray-700 dark:text-dark-textSecondary">
                    {data.routingDecision}
                  </span>
                </div>
              )}
              {data.confidence !== undefined && (
                <div>
                  <h4 className="text-xs font-medium text-gray-500 dark:text-dark-textMuted uppercase tracking-wider mb-1">
                    Confidence
                  </h4>
                  <span className={clsx('text-sm font-medium', getConfidenceColor(data.confidence))}>
                    {Math.round(data.confidence * 100)}%
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Tool Calls */}
          {data.toolCalls && data.toolCalls.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 dark:text-dark-textMuted uppercase tracking-wider mb-2">
                Tool Calls
              </h4>
              <div className="space-y-2">
                {data.toolCalls.map((tool, index) => (
                  <div
                    key={index}
                    className="p-3 rounded-lg bg-gray-50 dark:bg-dark-bg border border-gray-100 dark:border-dark-border"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <ToolIcon className="w-4 h-4 text-gray-400" />
                      <span className="font-medium text-sm text-gray-900 dark:text-dark-text">
                        {tool.name}
                      </span>
                    </div>
                    <div className="text-xs space-y-1">
                      <div className="text-gray-500 dark:text-dark-textMuted">
                        <span className="font-medium">Args:</span>{' '}
                        <code className="bg-gray-100 dark:bg-dark-surface px-1 rounded">
                          {JSON.stringify(tool.arguments)}
                        </code>
                      </div>
                      {tool.result && (
                        <div className="text-success-600 dark:text-success-400">
                          <span className="font-medium">Result:</span> {tool.result}
                        </div>
                      )}
                      {tool.error && (
                        <div className="text-error-600 dark:text-error-400">
                          <span className="font-medium">Error:</span> {tool.error}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Context Compaction */}
          {data.contextCompaction && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 dark:text-dark-textMuted uppercase tracking-wider mb-2">
                Context Compaction
              </h4>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-600 dark:text-dark-textSecondary">
                  {data.contextCompaction.before.toLocaleString()} →{' '}
                  {data.contextCompaction.after.toLocaleString()} tokens
                </span>
                <span className="text-success-600 dark:text-success-400">
                  (-
                  {Math.round(
                    (1 - data.contextCompaction.after / data.contextCompaction.before) * 100
                  )}
                  %)
                </span>
                {data.contextCompaction.method && (
                  <span className="text-gray-400 dark:text-dark-textMuted">
                    via {data.contextCompaction.method}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Refinement History */}
          {data.refinementHistory && data.refinementHistory.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 dark:text-dark-textMuted uppercase tracking-wider mb-2">
                Refinement History
              </h4>
              <div className="space-y-1">
                {data.refinementHistory.map((refinement) => (
                  <div
                    key={refinement.iteration}
                    className="flex items-center gap-3 text-sm text-gray-600 dark:text-dark-textSecondary"
                  >
                    <span className="font-medium text-gray-500 dark:text-dark-textMuted">
                      Iteration {refinement.iteration}
                    </span>
                    <span>{refinement.change}</span>
                    <span className={getConfidenceColor(refinement.score)}>
                      {Math.round(refinement.score * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
