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
        "flex flex-col bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
        <div className="flex items-center gap-3">
          <h3 className="font-medium text-gray-900 dark:text-gray-100">
            {config.title}
          </h3>
          <span className="px-2 py-0.5 text-xs rounded bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
            {config.language}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {/* View mode toggles */}
          <div className="flex items-center border border-gray-200 dark:border-gray-700 rounded">
            <button
              data-testid="view-split"
              type="button"
              onClick={() => setViewMode("split")}
              className={cn(
                "p-1.5",
                viewMode === "split"
                  ? "bg-gray-200 dark:bg-gray-700"
                  : "hover:bg-gray-100 dark:hover:bg-gray-800",
              )}
              aria-label="Split view"
            >
              <Columns size={14} />
            </button>
            <button
              data-testid="view-code-only"
              type="button"
              onClick={() => setViewMode("code")}
              className={cn(
                "p-1.5",
                viewMode === "code"
                  ? "bg-gray-200 dark:bg-gray-700"
                  : "hover:bg-gray-100 dark:hover:bg-gray-800",
              )}
              aria-label="Code only"
            >
              <Code size={14} />
            </button>
            <button
              data-testid="view-preview-only"
              type="button"
              onClick={() => setViewMode("preview")}
              className={cn(
                "p-1.5",
                viewMode === "preview"
                  ? "bg-gray-200 dark:bg-gray-700"
                  : "hover:bg-gray-100 dark:hover:bg-gray-800",
              )}
              aria-label="Preview only"
            >
              <Eye size={14} />
            </button>
          </div>

          {/* Run/Stop button */}
          {isRunning ? (
            <button
              data-testid="stop-button"
              type="button"
              onClick={onStop}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
            >
              <Square size={14} />
              Stop
            </button>
          ) : (
            <button
              data-testid="run-button"
              type="button"
              onClick={handleRun}
              className="flex items-center gap-1 px-3 py-1.5 text-sm bg-green-500 text-white rounded hover:bg-green-600 transition-colors"
            >
              <Play size={14} />
              Run
            </button>
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
                ? "w-1/2 border-r border-gray-200 dark:border-gray-700"
                : "flex-1",
            )}
          >
            <textarea
              data-testid="code-input"
              value={code}
              onChange={handleCodeChange}
              spellCheck={false}
              aria-label={`${config.language} code editor for ${config.title}`}
              className="flex-1 p-4 font-mono text-sm bg-gray-900 text-gray-100 resize-none focus:outline-none"
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
                className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-900"
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
          className="error flex items-center gap-2 px-4 py-2 bg-red-50 dark:bg-red-900/20 border-t border-red-200 dark:border-red-800"
        >
          <AlertTriangle size={16} className="text-red-500" />
          <span className="text-sm text-red-600 dark:text-red-400">
            {error}
          </span>
        </div>
      )}

      {/* Console Panel */}
      {consoleOutput.length > 0 && (
        <div
          data-testid="console-panel"
          className="border-t border-gray-200 dark:border-gray-700"
        >
          <div className="flex items-center justify-between px-4 py-1 bg-gray-100 dark:bg-gray-900">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              Console
            </span>
            <button
              data-testid="clear-console"
              type="button"
              onClick={onClearConsole}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              aria-label="Clear console"
            >
              <Trash2 size={12} />
            </button>
          </div>
          <div className="max-h-32 overflow-y-auto p-2 font-mono text-xs bg-gray-900 text-gray-100">
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
