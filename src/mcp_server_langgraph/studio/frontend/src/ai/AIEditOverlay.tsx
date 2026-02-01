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

import { Button, Input } from "@/components/UI";

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
        "absolute z-panel w-96 bg-neutral-1 rounded-lg shadow-xl border border-neutral-5",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2 border-b border-neutral-5 bg-neutral-1 rounded-t-lg">
        <Sparkles size={16} className="text-primary-9" />
        <span className="text-sm font-medium text-neutral-12">AI Edit</span>
      </div>
      {/* Selection Preview */}
      <div
        data-testid="selection-preview"
        className="px-4 py-2 border-b border-neutral-5"
      >
        <div className="text-xs text-neutral-10 mb-1">
          Selected code (lines {selection.start.line}-{selection.end.line})
        </div>
        <pre className="text-xs bg-neutral-2 p-2 rounded max-h-20 overflow-auto text-neutral-11 font-mono">
          {selection.content.slice(0, 200)}
          {selection.content.length > 200 && "..."}
        </pre>
      </div>
      {/* Instruction Input */}
      {!editResult && !error && (
        <div className="p-4">
          <Input
            className="px-3 py-2 text-sm bg-neutral-1 text-neutral-12 placeholder-neutral-9 focus:ring-primary-7"
            ref={inputRef}
            data-testid="instruction-input"
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="Describe the change you want..."
            disabled={isLoading}
          />
          <div className="flex justify-end gap-2 mt-3">
            <Button
              variant="secondary"
              className="px-3 py-1.5 text-sm text-neutral-11 hover:bg-neutral-2 rounded"
              data-testid="cancel-edit"
              type="button"
              onClick={onCancel}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              className="flex px-3 py-1.5 text-sm bg-primary-9 text-neutral-12 rounded hover:bg-primary-10"
              data-testid="submit-edit"
              type="button"
              onClick={handleSubmit}
              disabled={isLoading || !instruction.trim()}
            >
              {isLoading && (
                <Loader2
                  data-testid="loading-spinner"
                  size={14}
                  className="animate-spin"
                />
              )}
              Generate
            </Button>
          </div>
        </div>
      )}
      {/* Error State */}
      {error && (
        <div className="p-4">
          <div className="flex items-center gap-2 text-error-9 mb-3">
            <AlertCircle size={16} />
            <span className="text-sm">{error}</span>
          </div>
          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              className="px-3 py-1.5 text-sm text-neutral-11 hover:bg-neutral-2 rounded"
              data-testid="cancel-edit"
              type="button"
              onClick={onCancel}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              className="flex px-3 py-1.5 text-sm bg-error-9 text-neutral-12 rounded hover:bg-error-10"
              data-testid="retry-button"
              type="button"
              onClick={handleRetry}
            >
              <RefreshCw size={14} />
              Retry
            </Button>
          </div>
        </div>
      )}
      {/* Diff Preview */}
      {editResult && (
        <div className="p-4">
          <div
            data-testid="diff-preview"
            className="bg-neutral-2 rounded-lg overflow-hidden mb-3 max-h-48 overflow-y-auto"
          >
            <pre className="text-xs font-mono p-2">
              {editResult.diff.map((line, index) => (
                <div
                  key={index}
                  data-testid={`diff-${line.type}`}
                  className={cn(
                    "px-2 py-0.5",
                    line.type === "add" && "bg-success-a4 text-success-7",
                    line.type === "remove" &&
                      "bg-error-a4 text-error-7 line-through",
                    line.type === "same" && "text-neutral-9",
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
            <Button
              variant="secondary"
              className="flex px-3 py-1.5 text-sm text-neutral-11 hover:bg-neutral-2 rounded"
              data-testid="regenerate-button"
              type="button"
              onClick={handleRegenerate}
            >
              <RefreshCw size={14} />
              Regenerate
            </Button>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                className="flex px-3 py-1.5 text-sm text-neutral-11 hover:bg-neutral-2 rounded"
                data-testid="cancel-edit"
                type="button"
                onClick={onCancel}
              >
                <X size={14} />
                Cancel
              </Button>
              <Button
                variant="success"
                className="flex px-3 py-1.5 text-sm bg-success-9 text-neutral-12 rounded hover:bg-success-10"
                data-testid="apply-edit"
                type="button"
                onClick={() => onApply(editResult.newContent)}
              >
                <Check size={14} />
                Apply
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
