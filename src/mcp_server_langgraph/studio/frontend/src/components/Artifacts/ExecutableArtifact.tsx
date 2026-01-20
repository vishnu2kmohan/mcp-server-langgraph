/**
 * ExecutableArtifact Component
 *
 * Renders executable code with a run button for sandboxed execution.
 * Supports Docker, Kubernetes, WebAssembly, and Pyodide runtimes.
 */

import { useState } from "react";
import {
  Play,
  Loader2,
  Terminal,
  Clock,
  Box,
  AlertTriangle,
} from "lucide-react";
import type { ExecutableConfig, ExecutionResult } from "../../types/artifacts";

import { Button } from "@/components/UI";

export interface ExecutableArtifactProps {
  data: string;
  title?: string;
  config: ExecutableConfig;
  result?: ExecutionResult;
  onExecute?: (code: string, config: ExecutableConfig) => void;
  /** Whether to show confirmation dialog before execution (default: true) */
  requireConfirmation?: boolean;
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
  requireConfirmation = true,
}: ExecutableArtifactProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);

  if (!data || data.trim() === "") {
    return (
      <div
        className="p-4 bg-error-1 dark:bg-error-a3 border border-error-4 dark:border-error-11 rounded-lg"
        role="alert"
      >
        <p className="text-sm text-error-10 dark:text-error-7">
          No code provided
        </p>
      </div>
    );
  }

  const runtime = config.runtime || "docker";
  const runtimeLabel = runtimeLabels[runtime] || runtime;

  const executeCode = () => {
    setIsRunning(true);
    setShowConfirmation(false);
    if (onExecute) {
      onExecute(data, config);
    }
    // In a real implementation, this would wait for the result
    // For now, we just show the loading state briefly
    if (!onExecute) {
      setTimeout(() => setIsRunning(false), 2000);
    }
  };

  const handleRun = () => {
    if (requireConfirmation) {
      setShowConfirmation(true);
    } else {
      executeCode();
    }
  };

  const handleConfirm = () => {
    executeCode();
  };

  const handleCancel = () => {
    setShowConfirmation(false);
  };

  const runtimeIcon = runtimeIcons[runtime] || <Terminal size={14} />;

  return (
    <div className="relative bg-neutral-1 rounded-lg overflow-hidden border border-neutral-5">
      {/* Confirmation Dialog */}
      {showConfirmation && (
        <div
          data-testid="execution-confirmation"
          className="absolute inset-0 z-10 bg-neutral-a9 backdrop-blur-sm flex items-center justify-center p-4"
        >
          <div className="bg-neutral-1 rounded-lg shadow-xl max-w-md w-full p-6 border border-neutral-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-warning-3 dark:bg-warning-a4 rounded-full">
                <AlertTriangle
                  size={24}
                  className="text-warning-9 dark:text-warning-9"
                />
              </div>
              <h3 className="text-lg font-semibold text-neutral-12">
                Execute Code?
              </h3>
            </div>
            <p className="text-sm text-neutral-11 mb-4">
              This will execute code in a sandbox using{" "}
              <span className="font-medium text-neutral-12">
                {runtimeLabel}
              </span>
              . Make sure you trust the source before running.
            </p>
            <div className="flex items-center gap-3 justify-end">
              <Button
                variant="secondary"
                className="px-4 py-2 text-sm text-neutral-11 hover:bg-neutral-2 rounded-lg"
                onClick={handleCancel}
              >
                Cancel
              </Button>
              <Button
                variant="success"
                className="px-4 py-2 text-sm text-neutral-12 bg-success-10 hover:bg-success-11 rounded-lg flex"
                onClick={handleConfirm}
              >
                <Play size={14} />
                Confirm
              </Button>
            </div>
          </div>
        </div>
      )}
      {/* Header */}
      <div className="px-4 py-2 bg-neutral-2 border-b border-neutral-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {title && (
            <span className="text-sm font-medium text-neutral-11">
              {title}
            </span>
          )}
          <span className="text-xs font-mono bg-neutral-3 px-2 py-0.5 rounded text-neutral-11">
            {config.language}
          </span>
          <span className="flex items-center gap-1 text-xs text-neutral-10">
            {runtimeIcon}
            {runtimeLabel}
          </span>
        </div>
        <Button
          variant="success"
          size="sm"
          className="flex .5 px-3 py-1 text-sm bg-success-10 hover:bg-success-11 disabled:bg-success-7 text-neutral-12 rounded"
          onClick={handleRun}
          disabled={isRunning}
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
        </Button>
      </div>
      {/* Code */}
      <div className="p-4 bg-neutral-2 overflow-x-auto">
        <pre className="text-sm font-mono text-neutral-9 whitespace-pre-wrap">
          {data}
        </pre>
      </div>
      {/* Output */}
      {result && (
        <div className="border-t border-neutral-5">
          <div className="px-4 py-2 bg-neutral-2 flex items-center justify-between">
            <span className="text-xs font-medium text-neutral-11">
              Output
            </span>
            <div className="flex items-center gap-3 text-xs text-neutral-10">
              {result.executionTime !== undefined && (
                <span className="flex items-center gap-1">
                  <Clock size={12} />
                  {result.executionTime}ms
                </span>
              )}
              <span
                className={
                  result.exitCode === 0
                    ? "text-success-10 dark:text-success-7"
                    : "text-error-10 dark:text-error-7"
                }
              >
                Exit code: {result.exitCode}
              </span>
            </div>
          </div>
          <div className="p-4 bg-neutral-2 max-h-64 overflow-y-auto">
            {result.stdout && (
              <pre className="text-sm font-mono text-neutral-9 whitespace-pre-wrap">
                {result.stdout}
              </pre>
            )}
            {result.stderr && (
              <div className="text-error-10 dark:text-error-7">
                <pre className="text-sm font-mono whitespace-pre-wrap">
                  {result.stderr}
                </pre>
              </div>
            )}
            {result.error && (
              <div className="text-error-10 dark:text-error-7">
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
