/**
 * AgentExecutionTracePanel Component
 *
 * Displays agent execution trace data including:
 * - LangGraph node visualization (when nodes provided)
 * - Execution steps fallback (when no nodes)
 * - Token usage statistics
 * - Raw output (collapsible)
 *
 * Extracted from ChatMessages.tsx for improved modularity.
 */

import { LangGraphNodeVisualization } from "./LangGraphNodeVisualization";
import type { AgentExecutionTrace } from "../../types/chat";

export interface AgentExecutionTracePanelProps {
  /** The agent execution trace data to display */
  trace: AgentExecutionTrace | undefined;
  /** Optional additional CSS classes */
  className?: string;
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
}: AgentExecutionTracePanelProps) {
  // Empty state when trace is undefined
  if (!trace) {
    return (
      <div
        className={`mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs ${className}`}
        data-testid="agent-trace-panel-empty"
      >
        <p className="text-gray-400 italic font-sans">
          Processing... trace data will appear here.
        </p>
      </div>
    );
  }

  // Empty state when trace has no usable data
  if (!hasUsableData(trace)) {
    return (
      <div
        className={`mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs ${className}`}
        data-testid="agent-trace-panel"
      >
        <p className="text-gray-400 italic font-sans">
          Processing... trace data will appear here.
        </p>
      </div>
    );
  }

  const hasNodes = trace.nodes && trace.nodes.length > 0;
  const hasSteps =
    !hasNodes && trace.steps && trace.steps.length > 0;

  return (
    <div
      className={`mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs font-mono ${className}`}
      data-testid="agent-trace-panel"
    >
      {/* LangGraph Node Visualization - when nodes are provided */}
      {hasNodes && (
        <div className="mb-3">
          <p className="text-gray-500 dark:text-gray-400 mb-2 font-sans text-xs font-semibold">
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
          <p className="text-gray-500 dark:text-gray-400 mb-1 font-sans text-xs font-semibold">
            Execution Steps:
          </p>
          <ul className="space-y-1">
            {trace.steps!.map((step, i) => (
              <li key={i} className="flex items-center gap-2">
                <span
                  className={`w-2 h-2 rounded-full ${
                    step.status === "completed"
                      ? "bg-green-500"
                      : step.status === "running"
                        ? "bg-blue-500 animate-pulse"
                        : "bg-gray-400"
                  }`}
                />
                <span className="text-gray-700 dark:text-gray-300">
                  {step.name}
                </span>
                {step.duration !== undefined && (
                  <span className="text-gray-400">({step.duration}ms)</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Token usage */}
      {trace.tokens && (
        <div className="mb-2 flex gap-4 text-gray-500 dark:text-gray-400">
          <span>Input: {trace.tokens.input} tokens</span>
          <span>Output: {trace.tokens.output} tokens</span>
        </div>
      )}

      {/* Raw output */}
      {trace.rawOutput && (
        <details className="mt-2">
          <summary className="cursor-pointer text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 font-sans">
            Raw Output
          </summary>
          <pre className="mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded overflow-x-auto max-h-48 overflow-y-auto text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
            {trace.rawOutput}
          </pre>
        </details>
      )}
    </div>
  );
}
