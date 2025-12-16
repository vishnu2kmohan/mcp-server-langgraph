/**
 * ExecutableArtifact Component
 *
 * Renders executable code with a run button for sandboxed execution.
 * Supports Docker, Kubernetes, WebAssembly, and Pyodide runtimes.
 */

import { useState } from "react";
import { Play, Loader2, Terminal, Clock, Box } from "lucide-react";
import type { ExecutableConfig, ExecutionResult } from "../../types/artifacts";

export interface ExecutableArtifactProps {
  data: string;
  title?: string;
  config: ExecutableConfig;
  result?: ExecutionResult;
  onExecute?: (code: string, config: ExecutableConfig) => void;
}

const runtimeLabels: Record<string, string> = {
  docker: "Docker",
  kubernetes: "Kubernetes",
  webassembly: "WebAssembly",
  pyodide: "Pyodide",
};

const runtimeIcons: Record<string, React.ReactNode> = {
  docker: <Box size={14} />,
  kubernetes: <Box size={14} />,
  webassembly: <Terminal size={14} />,
  pyodide: <Terminal size={14} />,
};

export function ExecutableArtifact({
  data,
  title,
  config,
  result,
  onExecute,
}: ExecutableArtifactProps) {
  const [isRunning, setIsRunning] = useState(false);

  if (!data || data.trim() === "") {
    return (
      <div
        className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
        role="alert"
      >
        <p className="text-sm text-red-600 dark:text-red-400">
          No code provided
        </p>
      </div>
    );
  }

  const handleRun = () => {
    setIsRunning(true);
    if (onExecute) {
      onExecute(data, config);
    }
    // In a real implementation, this would wait for the result
    // For now, we just show the loading state briefly
    if (!onExecute) {
      setTimeout(() => setIsRunning(false), 2000);
    }
  };

  const runtime = config.runtime || "docker";
  const runtimeLabel = runtimeLabels[runtime] || runtime;
  const runtimeIcon = runtimeIcons[runtime] || <Terminal size={14} />;

  return (
    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="px-4 py-2 bg-gray-100 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {title && (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {title}
            </span>
          )}
          <span className="text-xs font-mono bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded text-gray-600 dark:text-gray-400">
            {config.language}
          </span>
          <span className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-500">
            {runtimeIcon}
            {runtimeLabel}
          </span>
        </div>
        <button
          onClick={handleRun}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3 py-1 text-sm bg-green-600 hover:bg-green-700 disabled:bg-green-400 text-white rounded transition-colors"
        >
          {isRunning ? (
            <>
              <Loader2 size={14} className="animate-spin" />
              Running...
            </>
          ) : (
            <>
              <Play size={14} />
              Run
            </>
          )}
        </button>
      </div>

      {/* Code */}
      <div className="p-4 bg-gray-900 overflow-x-auto">
        <pre className="text-sm font-mono text-gray-100 whitespace-pre-wrap">
          {data}
        </pre>
      </div>

      {/* Output */}
      {result && (
        <div className="border-t border-gray-200 dark:border-gray-700">
          <div className="px-4 py-2 bg-gray-100 dark:bg-gray-900 flex items-center justify-between">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
              Output
            </span>
            <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-500">
              {result.executionTime !== undefined && (
                <span className="flex items-center gap-1">
                  <Clock size={12} />
                  {result.executionTime}ms
                </span>
              )}
              <span
                className={
                  result.exitCode === 0
                    ? "text-green-600 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                }
              >
                Exit code: {result.exitCode}
              </span>
            </div>
          </div>
          <div className="p-4 bg-gray-950 max-h-64 overflow-y-auto">
            {result.stdout && (
              <pre className="text-sm font-mono text-gray-100 whitespace-pre-wrap">
                {result.stdout}
              </pre>
            )}
            {result.stderr && (
              <div className="text-red-600 dark:text-red-400">
                <pre className="text-sm font-mono whitespace-pre-wrap">
                  {result.stderr}
                </pre>
              </div>
            )}
            {result.error && (
              <div className="text-red-600 dark:text-red-400">
                <pre className="text-sm font-mono whitespace-pre-wrap">
                  {result.error}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
