/**
 * AgentExecutionTracePanel Component
 *
 * Displays agent execution trace data including:
 * - LangGraph node visualization (when nodes provided)
 * - Execution steps fallback (when no nodes)
 * - Token usage statistics
 * - Raw output (collapsible)
 * - Sprint 5: AI-powered trace intelligence
 *
 * Extracted from ChatMessages.tsx for improved modularity.
 */

import { LangGraphNodeVisualization } from "./LangGraphNodeVisualization";
import { useTraceSummary, useTraceAnomaly } from "../../hooks";
import type { AgentExecutionTrace } from "../../types/chat";

export interface AgentExecutionTracePanelProps {
  /** The agent execution trace data to display */
  trace: AgentExecutionTrace | undefined;
  /** Optional additional CSS classes */
  className?: string;
  /** User ID for AI analysis (required when enableAI is true) */
  userId?: string;
  /** Session ID for AI analysis */
  sessionId?: string;
  /** Trace ID for AI trace analysis */
  traceId?: string;
  /** Enable AI-powered trace intelligence (Sprint 5) */
  enableAI?: boolean;
}

/**
 * Determines if the trace has any usable data to display
 */
function hasUsableData(trace: AgentExecutionTrace): boolean {
  return !!(
    (trace.nodes && trace.nodes.length > 0) ||
    (trace.steps && trace.steps.length > 0) ||
    trace.tokens ||
    trace.rawOutput
  );
}

export function AgentExecutionTracePanel({
  trace,
  className = "",
  userId = "",
  sessionId = "",
  traceId = "",
  enableAI = false,
}: AgentExecutionTracePanelProps) {
  // Sprint 5: AI-powered trace intelligence hooks
  const {
    summary: aiSummary,
    keyActions,
    isLoading: summaryLoading,
  } = useTraceSummary({
    userId,
    sessionId,
    traceId,
    enabled: enableAI && !!traceId,
  });

  const {
    anomalies,
    bottlenecks,
    healthScore,
    optimizationSuggestions,
    isLoading: anomalyLoading,
  } = useTraceAnomaly({
    userId,
    sessionId,
    traceId,
    enabled: enableAI && !!traceId,
  });

  const aiLoading = summaryLoading || anomalyLoading;

  // Empty state when trace is undefined
  if (!trace) {
    return (
      <div
        className={`mt-2 p-3 bg-neutral-50 dark:bg-neutral-900 rounded border border-neutral-200 dark:border-neutral-700 text-xs ${className}`}
        data-testid="agent-trace-panel-empty"
      >
        <p className="text-neutral-400 dark:text-neutral-400 italic font-sans">
          Processing... trace data will appear here.
        </p>
      </div>
    );
  }

  // Empty state when trace has no usable data
  if (!hasUsableData(trace)) {
    return (
      <div
        className={`mt-2 p-3 bg-neutral-50 dark:bg-neutral-900 rounded border border-neutral-200 dark:border-neutral-700 text-xs ${className}`}
        data-testid="agent-trace-panel"
      >
        <p className="text-neutral-400 dark:text-neutral-400 italic font-sans">
          Processing... trace data will appear here.
        </p>
      </div>
    );
  }

  const hasNodes = trace.nodes && trace.nodes.length > 0;
  const hasSteps = !hasNodes && trace.steps && trace.steps.length > 0;

  return (
    <div
      className={`mt-2 p-3 bg-neutral-50 dark:bg-neutral-900 rounded border border-neutral-200 dark:border-neutral-700 text-xs font-mono ${className}`}
      data-testid="agent-trace-panel"
    >
      {/* LangGraph Node Visualization - when nodes are provided */}
      {hasNodes && (
        <div className="mb-3">
          <p className="text-neutral-500 dark:text-neutral-400 mb-2 font-sans text-xs font-semibold">
            Workflow Execution:
          </p>
          <LangGraphNodeVisualization
            nodes={trace.nodes!}
            edges={trace.edges}
            currentNode={trace.currentNode}
          />
        </div>
      )}

      {/* Simple Steps visualization - fallback when no nodes */}
      {hasSteps && (
        <div className="mb-2">
          <p className="text-neutral-500 dark:text-neutral-400 mb-1 font-sans text-xs font-semibold">
            Execution Steps:
          </p>
          <ul className="space-y-1">
            {trace.steps!.map((step, i) => (
              <li key={i} className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    step.status === "completed"
                      ? "bg-success-500"
                      : step.status === "running"
                        ? "bg-primary-500 animate-pulse"
                        : "bg-neutral-400"
                  }`}
                />
                <span className="text-neutral-700 dark:text-neutral-300">
                  {step.name}
                </span>
                {step.duration !== undefined && (
                  <span className="text-neutral-400 dark:text-neutral-400">
                    ({step.duration}ms)
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Token usage */}
      {trace.tokens && (
        <div className="mb-2 flex gap-4 text-neutral-500 dark:text-neutral-400">
          <span>Input: {trace.tokens.input} tokens</span>
          <span>Output: {trace.tokens.output} tokens</span>
        </div>
      )}

      {/* Raw output */}
      {trace.rawOutput && (
        <details className="mt-2">
          <summary className="cursor-pointer text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:text-neutral-400 dark:hover:text-neutral-200 font-sans">
            Raw Output
          </summary>
          <pre className="mt-1 p-2 bg-neutral-100 dark:bg-neutral-800 rounded overflow-x-auto max-h-48 overflow-y-auto text-neutral-600 dark:text-neutral-300 whitespace-pre-wrap">
            {trace.rawOutput}
          </pre>
        </details>
      )}

      {/* Sprint 5: AI-Powered Trace Intelligence */}
      {enableAI && (
        <>
          {/* AI Summary Panel */}
          {aiSummary && (
            <div
              className="mt-3 p-3 bg-primary-50 dark:bg-primary-900/20 rounded border border-primary-200 dark:border-primary-800"
              data-testid="ai-trace-summary"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-primary-600 dark:text-primary-400 font-semibold font-sans text-xs">
                  AI Summary
                </span>
                {aiLoading && (
                  <span className="w-3 h-3 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
                )}
              </div>
              <p className="text-neutral-700 dark:text-neutral-300 font-sans text-xs">
                {aiSummary}
              </p>

              {/* Key Actions */}
              {keyActions && keyActions.length > 0 && (
                <div className="mt-2">
                  <span className="text-neutral-500 dark:text-neutral-400 text-xs font-sans">
                    Key actions:
                  </span>
                  <ul className="mt-1 space-y-0.5">
                    {keyActions.map((action, idx) => (
                      <li
                        key={idx}
                        className="text-neutral-600 dark:text-neutral-300 text-xs font-sans flex items-center gap-1"
                      >
                        <span className="text-primary-500">•</span>
                        {action}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Health Score Indicator */}
          {healthScore !== null && (
            <div
              className="mt-2 flex items-center gap-2"
              data-testid="ai-health-score"
            >
              <span className="text-neutral-500 dark:text-neutral-400 text-xs font-sans">
                Health:
              </span>
              <div className="flex items-center gap-1">
                <div className="w-16 h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      healthScore >= 0.8
                        ? "bg-success-500"
                        : healthScore >= 0.6
                          ? "bg-warning-500"
                          : "bg-error-500"
                    }`}
                    style={{ width: `${healthScore * 100}%` }}
                  />
                </div>
                <span
                  className={`text-xs font-semibold ${
                    healthScore >= 0.8
                      ? "text-success-600 dark:text-success-400"
                      : healthScore >= 0.6
                        ? "text-warning-600 dark:text-warning-400"
                        : "text-error-600 dark:text-error-400"
                  }`}
                >
                  {Math.round(healthScore * 100)}%
                </span>
              </div>
            </div>
          )}

          {/* Bottleneck Indicators */}
          {bottlenecks && bottlenecks.length > 0 && (
            <div
              className="mt-2 p-2 bg-warning-50 dark:bg-warning-900/20 rounded border border-warning-200 dark:border-warning-800"
              data-testid="ai-bottleneck-indicator"
            >
              <span className="text-warning-700 dark:text-warning-400 text-xs font-semibold font-sans">
                Bottlenecks Detected:
              </span>
              <ul className="mt-1 space-y-1">
                {bottlenecks.map((bottleneck, idx) => (
                  <li
                    key={idx}
                    className="text-warning-600 dark:text-warning-300 text-xs font-sans flex items-center justify-between"
                  >
                    <span>{bottleneck.stepName}</span>
                    <span className="font-mono">
                      {bottleneck.durationMs}ms ({bottleneck.percentageOfTotal}
                      %)
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Anomaly Warnings */}
          {anomalies && anomalies.length > 0 && (
            <div className="mt-2 space-y-1">
              {anomalies.map((anomaly, idx) => (
                <div
                  key={idx}
                  className={`p-2 rounded text-xs font-sans flex items-start gap-2 ${
                    anomaly.severity === "error"
                      ? "bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 text-error-700 dark:text-error-300"
                      : anomaly.severity === "warning"
                        ? "bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 text-warning-700 dark:text-warning-300"
                        : "bg-primary-50 dark:bg-primary-900/20 border border-primary-200 dark:border-primary-800 text-primary-700 dark:text-primary-300"
                  }`}
                  data-testid="ai-anomaly-badge"
                >
                  <span
                    className={`px-1.5 py-0.5 rounded text-xs font-semibold uppercase ${
                      anomaly.severity === "error"
                        ? "bg-error-200 dark:bg-error-800 text-error-800 dark:text-error-200"
                        : anomaly.severity === "warning"
                          ? "bg-warning-200 dark:bg-warning-800 text-warning-800 dark:text-warning-200"
                          : "bg-primary-200 dark:bg-primary-800 text-primary-800 dark:text-primary-200"
                    }`}
                  >
                    {anomaly.severity}
                  </span>
                  <div className="flex-1">
                    <span className="font-semibold">{anomaly.stepName}:</span>{" "}
                    {anomaly.message}
                    {anomaly.suggestedFix && (
                      <p className="mt-1 text-neutral-600 dark:text-neutral-400 italic">
                        Suggestion: {anomaly.suggestedFix}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Optimization Suggestions */}
          {optimizationSuggestions && optimizationSuggestions.length > 0 && (
            <div className="mt-2 p-2 bg-success-50 dark:bg-success-900/20 rounded border border-success-200 dark:border-success-800">
              <span className="text-success-700 dark:text-success-400 text-xs font-semibold font-sans">
                Optimization Suggestions:
              </span>
              <ul className="mt-1 space-y-0.5">
                {optimizationSuggestions.map((suggestion, idx) => (
                  <li
                    key={idx}
                    className="text-success-600 dark:text-success-300 text-xs font-sans flex items-center gap-1"
                  >
                    <span className="text-success-500">💡</span>
                    {suggestion}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}
