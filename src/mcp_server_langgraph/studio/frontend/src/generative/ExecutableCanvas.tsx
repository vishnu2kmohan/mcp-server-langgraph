/**
 * ExecutableCanvas - Phase 2
 *
 * Sandboxed code execution canvas with code editor,
 * preview, and console output.
 */
import { useState, useCallback } from "react";
import {
  Play,
  Square,
  Trash2,
  Loader2,
  Columns,
  Code,
  Eye,
  AlertTriangle,
} from "lucide-react";
import { cn } from "../utils/cn";

import { Button, Textarea } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface ExecutableConfig {
  id: string;
  language: "jsx" | "html" | "javascript" | "css" | "typescript";
  code: string;
  title: string;
}

export interface ExecutableCanvasProps {
  config: ExecutableConfig;
  isRunning?: boolean;
  isPreviewLoading?: boolean;
  error?: string;
  consoleOutput?: string[];
  onChange?: (code: string) => void;
  onRun?: (code: string) => void;
  onStop?: () => void;
  onClearConsole?: () => void;
  className?: string;
}

type ViewMode = "split" | "code" | "preview";

// =============================================================================
// Component
// =============================================================================

export function ExecutableCanvas({
  config,
  isRunning = false,
  isPreviewLoading = false,
  error,
  consoleOutput = [],
  onChange,
  onRun,
  onStop,
  onClearConsole,
  className,
}: ExecutableCanvasProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("split");
  const [code, setCode] = useState(config.code);

  const handleCodeChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newCode = e.target.value;
      setCode(newCode);
      onChange?.(newCode);
    },
    [onChange],
  );

  const handleRun = useCallback(() => {
    onRun?.(code);
  }, [code, onRun]);

  const showCodeEditor = viewMode === "split" || viewMode === "code";
  const showPreview = viewMode === "split" || viewMode === "preview";

  return (
    <div
      data-testid="executable-canvas"
      role="region"
      aria-label={config.title}
      className={cn(
        "flex flex-col bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-900/50">
        <div className="flex items-center gap-3">
          <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
            {config.title}
          </h3>
          <span className="px-2 py-0.5 text-xs rounded bg-neutral-200 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400">
            {config.language}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* View mode toggles */}
          <div className="flex items-center border border-neutral-200 dark:border-neutral-700 rounded">
            <Button
              data-testid="view-split"
              type="button"
              onClick={() => setViewMode("split")}
              className={cn(
                "p-1.5",
                viewMode === "split"
                  ? "bg-neutral-200 dark:bg-neutral-700"
                  : "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800",
              )}
              aria-label="Split view"
            >
              <Columns size={14} />
            </Button>
            <Button
              data-testid="view-code-only"
              type="button"
              onClick={() => setViewMode("code")}
              className={cn(
                "p-1.5",
                viewMode === "code"
                  ? "bg-neutral-200 dark:bg-neutral-700"
                  : "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800",
              )}
              aria-label="Code only"
            >
              <Code size={14} />
            </Button>
            <Button
              data-testid="view-preview-only"
              type="button"
              onClick={() => setViewMode("preview")}
              className={cn(
                "p-1.5",
                viewMode === "preview"
                  ? "bg-neutral-200 dark:bg-neutral-700"
                  : "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800",
              )}
              aria-label="Preview only"
            >
              <Eye size={14} />
            </Button>
          </div>

          {/* Run/Stop button */}
          {isRunning ? (
            <Button
              variant="danger"
              className="flex px-3 py-1.5 text-sm bg-error-500 text-white rounded hover:bg-error-600"
              data-testid="stop-button"
              type="button"
              onClick={onStop}
            >
              <Square size={14} />
              Stop
            </Button>
          ) : (
            <Button
              variant="success"
              className="flex px-3 py-1.5 text-sm bg-success-500 text-white rounded hover:bg-success-600"
              data-testid="run-button"
              type="button"
              onClick={handleRun}
            >
              <Play size={14} />
              Run
            </Button>
          )}
        </div>
      </div>
      {/* Main content */}
      <div
        data-testid={
          viewMode === "split"
            ? "split-view"
            : viewMode === "code"
              ? "code-only-view"
              : "preview-only-view"
        }
        className="flex flex-1 min-h-[300px]"
      >
        {/* Code Editor */}
        {showCodeEditor && (
          <div
            data-testid="code-editor"
            className={cn(
              "flex flex-col",
              viewMode === "split"
                ? "w-1/2 border-r border-neutral-200 dark:border-neutral-700"
                : "flex-1",
            )}
          >
            <Textarea
              className="flex-1 p-4 font-mono text-sm bg-neutral-900 text-neutral-100 resize-none"
              data-testid="code-input"
              value={code}
              onChange={handleCodeChange}
              spellCheck={false}
              aria-label={`${config.language} code editor for ${config.title}`}
            />
          </div>
        )}

        {/* Preview */}
        {showPreview && (
          <div
            data-testid="preview-area"
            className={cn(
              "flex flex-col",
              viewMode === "split" ? "w-1/2" : "flex-1",
            )}
          >
            {isPreviewLoading ? (
              <div
                data-testid="preview-loading"
                className="flex-1 flex items-center justify-center bg-neutral-50 dark:bg-neutral-900"
              >
                <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
              </div>
            ) : (
              <iframe
                data-testid="sandbox-iframe"
                sandbox="allow-scripts"
                className="flex-1 bg-white"
                title="Preview"
              />
            )}
          </div>
        )}
      </div>
      {/* Error Panel */}
      {error && (
        <div
          data-testid="error-panel"
          className="error flex items-center gap-2 px-4 py-2 bg-error-50 dark:bg-error-900/20 border-t border-error-200 dark:border-error-800"
        >
          <AlertTriangle size={16} className="text-error-500" />
          <span className="text-sm text-error-600 dark:text-error-400">
            {error}
          </span>
        </div>
      )}
      {/* Console Panel */}
      {consoleOutput.length > 0 && (
        <div
          data-testid="console-panel"
          className="border-t border-neutral-200 dark:border-neutral-700"
        >
          <div className="flex items-center justify-between px-4 py-1 bg-neutral-100 dark:bg-neutral-800">
            <span className="text-xs font-medium text-neutral-500 dark:text-neutral-400">
              Console
            </span>
            <Button
              className="p-1 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-300"
              data-testid="clear-console"
              type="button"
              onClick={onClearConsole}
              aria-label="Clear console"
            >
              <Trash2 size={12} />
            </Button>
          </div>
          <div className="max-h-32 overflow-y-auto p-2 font-mono text-xs bg-neutral-900 text-neutral-100">
            {consoleOutput.map((line, index) => (
              <div key={index} className="py-0.5">
                {line}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
