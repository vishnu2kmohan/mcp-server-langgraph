/**
 * AIEditOverlay - Phase 2
 *
 * Inline AI edit overlay for the canvas with diff preview.
 */
import { useState, useRef, useEffect, useCallback } from "react";
import {
  Loader2,
  Check,
  X,
  RefreshCw,
  AlertCircle,
  Sparkles,
} from "lucide-react";
import { cn } from "../utils/cn";

// =============================================================================
// Types
// =============================================================================

export interface Selection {
  start: { line: number; column: number };
  end: { line: number; column: number };
  content: string;
}

export interface DiffLine {
  type: "add" | "remove" | "same";
  content: string;
}

export interface EditResult {
  newContent: string;
  diff: DiffLine[];
}

export interface EditRequest {
  selection: Selection;
  instruction: string;
}

export interface AIEditOverlayProps {
  selection: Selection;
  isVisible: boolean;
  onApply: (newContent: string) => void;
  onCancel: () => void;
  onRequestEdit?: (request: EditRequest) => Promise<EditResult>;
  editResult?: EditResult;
  error?: string;
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function AIEditOverlay({
  selection,
  isVisible,
  onApply,
  onCancel,
  onRequestEdit,
  editResult: initialEditResult,
  error: initialError,
  className,
}: AIEditOverlayProps) {
  const [instruction, setInstruction] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [editResult, setEditResult] = useState<EditResult | undefined>(
    initialEditResult,
  );
  const [error, setError] = useState<string | undefined>(initialError);
  const inputRef = useRef<HTMLInputElement>(null);

  // Update from props
  useEffect(() => {
    setEditResult(initialEditResult);
  }, [initialEditResult]);

  useEffect(() => {
    setError(initialError);
  }, [initialError]);

  // Focus input when visible
  useEffect(() => {
    if (isVisible && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isVisible]);

  // Reset state when hidden
  useEffect(() => {
    if (!isVisible) {
      setInstruction("");
      setIsLoading(false);
      setEditResult(undefined);
      setError(undefined);
    }
  }, [isVisible]);

  const handleSubmit = useCallback(async () => {
    if (!instruction.trim() || !onRequestEdit) return;

    setIsLoading(true);
    setError(undefined);

    try {
      const result = await onRequestEdit({
        selection,
        instruction: instruction.trim(),
      });
      setEditResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate edit");
    } finally {
      setIsLoading(false);
    }
  }, [instruction, onRequestEdit, selection]);

  const handleRegenerate = useCallback(() => {
    setEditResult(undefined);
    handleSubmit();
  }, [handleSubmit]);

  const handleRetry = useCallback(() => {
    setError(undefined);
    handleSubmit();
  }, [handleSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onCancel();
      } else if (
        e.key === "Enter" &&
        !e.shiftKey &&
        !isLoading &&
        !editResult
      ) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [onCancel, handleSubmit, isLoading, editResult],
  );

  if (!isVisible) return null;

  return (
    <div
      data-testid="ai-edit-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="AI Edit"
      onKeyDown={handleKeyDown}
      className={cn(
        "absolute z-50 w-96 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50 rounded-t-lg">
        <Sparkles size={16} className="text-primary-500" />
        <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
          AI Edit
        </span>
      </div>

      {/* Selection Preview */}
      <div
        data-testid="selection-preview"
        className="px-4 py-2 border-b border-gray-200 dark:border-gray-700"
      >
        <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
          Selected code (lines {selection.start.line}-{selection.end.line})
        </div>
        <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded max-h-20 overflow-auto text-gray-700 dark:text-gray-300 font-mono">
          {selection.content.slice(0, 200)}
          {selection.content.length > 200 && "..."}
        </pre>
      </div>

      {/* Instruction Input */}
      {!editResult && !error && (
        <div className="p-4">
          <input
            ref={inputRef}
            data-testid="instruction-input"
            type="text"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="Describe the change you want..."
            disabled={isLoading}
            className="w-full px-3 py-2 text-sm rounded-lg bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <div className="flex justify-end gap-2 mt-3">
            <button
              data-testid="cancel-edit"
              type="button"
              onClick={onCancel}
              className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded transition-colors"
            >
              Cancel
            </button>
            <button
              data-testid="submit-edit"
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || !instruction.trim()}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary-500 text-white rounded hover:bg-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading && (
                <Loader2
                  data-testid="loading-spinner"
                  size={14}
                  className="animate-spin"
                />
              )}
              Generate
            </button>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="p-4">
          <div className="flex items-center gap-2 text-error-500 mb-3">
            <AlertCircle size={16} />
            <span className="text-sm">{error}</span>
          </div>
          <div className="flex justify-end gap-2">
            <button
              data-testid="cancel-edit"
              type="button"
              onClick={onCancel}
              className="px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded transition-colors"
            >
              Cancel
            </button>
            <button
              data-testid="retry-button"
              type="button"
              onClick={handleRetry}
              className="flex items-center gap-2 px-3 py-1.5 text-sm bg-error-500 text-white rounded hover:bg-error-600 transition-colors"
            >
              <RefreshCw size={14} />
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Diff Preview */}
      {editResult && (
        <div className="p-4">
          <div
            data-testid="diff-preview"
            className="bg-gray-900 rounded-lg overflow-hidden mb-3 max-h-48 overflow-y-auto"
          >
            <pre className="text-xs font-mono p-2">
              {editResult.diff.map((line, index) => (
                <div
                  key={index}
                  data-testid={`diff-${line.type}`}
                  className={cn(
                    "px-2 py-0.5",
                    line.type === "add" && "bg-success-900/30 text-success-400",
                    line.type === "remove" &&
                      "bg-error-900/30 text-error-400 line-through",
                    line.type === "same" && "text-gray-400 dark:text-gray-400",
                  )}
                >
                  {line.type === "add" && "+ "}
                  {line.type === "remove" && "- "}
                  {line.type === "same" && "  "}
                  {line.content}
                </div>
              ))}
            </pre>
          </div>

          <div className="flex justify-between">
            <button
              data-testid="regenerate-button"
              type="button"
              onClick={handleRegenerate}
              className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded transition-colors"
            >
              <RefreshCw size={14} />
              Regenerate
            </button>
            <div className="flex gap-2">
              <button
                data-testid="cancel-edit"
                type="button"
                onClick={onCancel}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-700 rounded transition-colors"
              >
                <X size={14} />
                Cancel
              </button>
              <button
                data-testid="apply-edit"
                type="button"
                onClick={() => onApply(editResult.newContent)}
                className="flex items-center gap-2 px-3 py-1.5 text-sm bg-success-500 text-white rounded hover:bg-success-600 transition-colors"
              >
                <Check size={14} />
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
