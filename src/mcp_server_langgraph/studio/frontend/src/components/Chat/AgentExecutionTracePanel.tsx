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
        className={`mt-2 p-3 bg-neutral-1 rounded border border-neutral-5 text-xs ${className}`}
        data-testid="agent-trace-panel-empty"
      >
        <p className="text-neutral-9 italic font-sans">
          Processing... trace data will appear here.
        </p>
      </div>
    );
  }

  // Empty state when trace has no usable data
  if (!hasUsableData(trace)) {
    return (
      <div
        className={`mt-2 p-3 bg-neutral-1 rounded border border-neutral-5 text-xs ${className}`}
        data-testid="agent-trace-panel"
      >
        <p className="text-neutral-9 italic font-sans">
          Processing... trace data will appear here.
        </p>
      </div>
    );
  }

  const hasNodes = trace.nodes && trace.nodes.length > 0;
  const hasSteps = !hasNodes && trace.steps && trace.steps.length > 0;

  return (
    <div
      className={`mt-2 p-3 bg-neutral-1 rounded border border-neutral-5 text-xs font-mono ${className}`}
      data-testid="agent-trace-panel"
    >
      {/* LangGraph Node Visualization - when nodes are provided */}
      {hasNodes && (
        <div className="mb-3">
          <p className="text-neutral-10 mb-2 font-sans text-xs font-semibold">
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
          <p className="text-neutral-10 mb-1 font-sans text-xs font-semibold">
            Execution Steps:
          </p>
          <ul className="space-y-1">
            {trace.steps!.map((step, i) => (
              <li key={i} className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    step.status === "completed"
                      ? "bg-success-9"
                      : step.status === "running"
                        ? "bg-primary-9 animate-pulse"
                        : "bg-neutral-4"
                  }`}
                />
                <span className="text-neutral-11">{step.name}</span>
                {step.duration !== undefined && (
                  <span className="text-neutral-9">({step.duration}ms)</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Token usage */}
      {trace.tokens && (
        <div className="mb-2 flex gap-4 text-neutral-10">
          <span>Input: {trace.tokens.input} tokens</span>
          <span>Output: {trace.tokens.output} tokens</span>
        </div>
      )}

      {/* Raw output */}
      {trace.rawOutput && (
        <details className="mt-2">
          <summary className="cursor-pointer text-neutral-10 hover:text-neutral-11 font-sans">
            Raw Output
          </summary>
          <pre className="mt-1 p-2 bg-neutral-2 rounded overflow-x-auto max-h-48 overflow-y-auto text-neutral-11 whitespace-pre-wrap">
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
              className="mt-3 p-3 bg-primary-1 dark:bg-primary-a3 rounded border border-primary-4 dark:border-primary-11"
              data-testid="ai-trace-summary"
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-primary-10 dark:text-primary-11 font-semibold font-sans text-xs">
                  AI Summary
                </span>
                {aiLoading && (
                  <span className="w-3 h-3 border-2 border-primary-9 border-t-transparent rounded-full animate-spin" />
                )}
              </div>
              <p className="text-neutral-11 font-sans text-xs">{aiSummary}</p>

              {/* Key Actions */}
              {keyActions && keyActions.length > 0 && (
                <div className="mt-2">
                  <span className="text-neutral-10 text-xs font-sans">
                    Key actions:
                  </span>
                  <ul className="mt-1 space-y-0.5">
                    {keyActions.map((action, idx) => (
                      <li
                        key={idx}
                        className="text-neutral-11 text-xs font-sans flex items-center gap-1"
                      >
                        <span className="text-primary-9">•</span>
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
              <span className="text-neutral-10 text-xs font-sans">Health:</span>
              <div className="flex items-center gap-1">
                <div className="w-16 h-2 bg-neutral-3 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      healthScore >= 0.8
                        ? "bg-success-9"
                        : healthScore >= 0.6
                          ? "bg-warning-9"
                          : "bg-error-9"
                    }`}
                    style={
                      {
                        "--progress": `${healthScore * 100}%`,
                      } as React.CSSProperties
                    }
                  />
                </div>
                <span
                  className={`text-xs font-semibold ${
                    healthScore >= 0.8
                      ? "text-success-10 dark:text-success-11"
                      : healthScore >= 0.6
                        ? "text-warning-9 dark:text-warning-9"
                        : "text-error-10 dark:text-error-11"
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
              className="mt-2 p-2 bg-warning-3 bg-warning-3 rounded border border-warning-6 dark:border-warning-11"
              data-testid="ai-bottleneck-indicator"
            >
              <span className="text-warning-10 dark:text-warning-9 text-xs font-semibold font-sans">
                Bottlenecks Detected:
              </span>
              <ul className="mt-1 space-y-1">
                {bottlenecks.map((bottleneck, idx) => (
                  <li
                    key={idx}
                    className="text-warning-9 dark:text-warning-11 text-xs font-sans flex items-center justify-between"
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
                      ? "bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 text-error-11 dark:text-error-9"
                      : anomaly.severity === "warning"
                        ? "bg-warning-3 bg-warning-3 border border-warning-6 dark:border-warning-11 text-warning-10 dark:text-warning-11"
                        : "bg-primary-1 dark:bg-primary-a3 border border-primary-4 dark:border-primary-11 text-primary-11 dark:text-primary-11"
                  }`}
                  data-testid="ai-anomaly-badge"
                >
                  <span
                    className={`px-1.5 py-0.5 rounded text-xs font-semibold uppercase ${
                      anomaly.severity === "error"
                        ? "bg-error-4 dark:bg-error-11 text-error-11 dark:text-error-4"
                        : anomaly.severity === "warning"
                          ? "bg-warning-6 dark:bg-warning-11 text-warning-11 dark:text-warning-11"
                          : "bg-primary-4 dark:bg-primary-11 text-primary-11 dark:text-primary-4"
                    }`}
                  >
                    {anomaly.severity}
                  </span>
                  <div className="flex-1">
                    <span className="font-semibold">{anomaly.stepName}:</span>{" "}
                    {anomaly.message}
                    {anomaly.suggestedFix && (
                      <p className="mt-1 text-neutral-11 italic">
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
            <div className="mt-2 p-2 bg-success-1 dark:bg-success-a3 rounded border border-success-4 dark:border-success-11">
              <span className="text-success-11 dark:text-success-11 text-xs font-semibold font-sans">
                Optimization Suggestions:
              </span>
              <ul className="mt-1 space-y-0.5">
                {optimizationSuggestions.map((suggestion, idx) => (
                  <li
                    key={idx}
                    className="text-success-10 dark:text-success-11 text-xs font-sans flex items-center gap-1"
                  >
                    <span className="text-success-9">💡</span>
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
