/**
 * VersionDiff - Phase 7 + Sprint 4 AI Enhancement
 *
 * Artifact version diff view component.
 * Shows text differences between two artifact versions.
 *
 * Features:
 * - Unified and split diff view modes
 * - Line-by-line diff visualization
 * - Added/removed/unchanged line highlighting
 * - Restore action for reverting to a version
 * - AI-powered diff explanation (Sprint 4)
 */
import { useMemo } from "react";
import { X, RotateCcw, Sparkles, Loader2 } from "lucide-react";
import type { ArtifactVersion } from "../types/artifacts";
import { cn } from "../utils/cn";
import { useDiffExplanation } from "../hooks";

// =============================================================================
// Types
// =============================================================================

export interface VersionDiffProps {
  /** Base version to compare from */
  baseVersion: ArtifactVersion;
  /** Version to compare against */
  comparedVersion: ArtifactVersion;
  /** View mode: unified (default) or split */
  mode?: "unified" | "split";
  /** Callback when close button clicked */
  onClose?: () => void;
  /** Callback when restore button clicked */
  onRestore?: (version: ArtifactVersion) => void;
  /** Additional class name */
  className?: string;
  /** User ID for AI features (Sprint 4) */
  userId?: string;
  /** Session ID for AI features (Sprint 4) */
  sessionId?: string;
  /** Enable AI-powered diff explanation (Sprint 4) */
  enableAI?: boolean;
}

interface DiffLine {
  type: "added" | "removed" | "unchanged";
  content: string;
  lineNumber?: number;
  baseLineNumber?: number;
}

// =============================================================================
// Diff Algorithm (Simple Line-by-Line)
// =============================================================================

/**
 * Simple line-by-line diff algorithm.
 * For production, consider using a proper diff library like 'diff' or 'diff-match-patch'.
 */
function computeDiff(baseContent: string, comparedContent: string): DiffLine[] {
  const baseLines = baseContent.split("\n");
  const comparedLines = comparedContent.split("\n");

  const result: DiffLine[] = [];
  let baseIndex = 0;
  let comparedIndex = 0;

  // Simple LCS-inspired approach
  while (baseIndex < baseLines.length || comparedIndex < comparedLines.length) {
    const baseLine = baseLines[baseIndex];
    const comparedLine = comparedLines[comparedIndex];

    if (baseIndex >= baseLines.length) {
      // All remaining lines are additions
      if (comparedLine !== undefined) {
        result.push({
          type: "added",
          content: comparedLine,
          lineNumber: comparedIndex + 1,
        });
      }
      comparedIndex++;
    } else if (comparedIndex >= comparedLines.length) {
      // All remaining lines are removals
      if (baseLine !== undefined) {
        result.push({
          type: "removed",
          content: baseLine,
          baseLineNumber: baseIndex + 1,
        });
      }
      baseIndex++;
    } else if (baseLine === comparedLine) {
      // Lines match - unchanged
      if (baseLine !== undefined) {
        result.push({
          type: "unchanged",
          content: baseLine,
          lineNumber: comparedIndex + 1,
          baseLineNumber: baseIndex + 1,
        });
      }
      baseIndex++;
      comparedIndex++;
    } else {
      // Lines differ - look ahead to find matches
      const lookAheadLimit = 3;
      let foundMatch = false;

      // Check if base line appears later in compared
      for (
        let i = 1;
        i <= lookAheadLimit && comparedIndex + i < comparedLines.length;
        i++
      ) {
        if (baseLine === comparedLines[comparedIndex + i]) {
          // Added lines before the match
          for (let j = 0; j < i; j++) {
            const addedLine = comparedLines[comparedIndex + j];
            if (addedLine !== undefined) {
              result.push({
                type: "added",
                content: addedLine,
                lineNumber: comparedIndex + j + 1,
              });
            }
          }
          comparedIndex += i;
          foundMatch = true;
          break;
        }
      }

      if (!foundMatch) {
        // Check if compared line appears later in base
        for (
          let i = 1;
          i <= lookAheadLimit && baseIndex + i < baseLines.length;
          i++
        ) {
          if (baseLines[baseIndex + i] === comparedLine) {
            // Removed lines before the match
            for (let j = 0; j < i; j++) {
              const removedLine = baseLines[baseIndex + j];
              if (removedLine !== undefined) {
                result.push({
                  type: "removed",
                  content: removedLine,
                  baseLineNumber: baseIndex + j + 1,
                });
              }
            }
            baseIndex += i;
            foundMatch = true;
            break;
          }
        }
      }

      if (!foundMatch) {
        // No match found - treat as removed then added
        if (baseLine !== undefined) {
          result.push({
            type: "removed",
            content: baseLine,
            baseLineNumber: baseIndex + 1,
          });
        }
        if (comparedLine !== undefined) {
          result.push({
            type: "added",
            content: comparedLine,
            lineNumber: comparedIndex + 1,
          });
        }
        baseIndex++;
        comparedIndex++;
      }
    }
  }

  return result;
}

// =============================================================================
// Component
// =============================================================================

export function VersionDiff({
  baseVersion,
  comparedVersion,
  mode = "unified",
  onClose,
  onRestore,
  className,
  userId,
  sessionId,
  enableAI = false,
}: VersionDiffProps) {
  // Compute diff between versions
  const diffLines = useMemo(
    () => computeDiff(baseVersion.content, comparedVersion.content),
    [baseVersion.content, comparedVersion.content],
  );

  const hasChanges = diffLines.some((line) => line.type !== "unchanged");

  // Sprint 4: AI-powered diff explanation
  const {
    summary: aiSummary,
    changes: aiChanges,
    breakingChanges,
    affectedAreas,
    isLoading: aiLoading,
    error: aiError,
    refetch: refetchAI,
  } = useDiffExplanation({
    userId: userId ?? "anonymous",
    sessionId: sessionId ?? "",
    oldContent: baseVersion.content,
    newContent: comparedVersion.content,
    enabled: enableAI && hasChanges && !!userId && !!sessionId,
  });

  return (
    <div
      data-testid="version-diff"
      className={cn(
        "flex flex-col h-full bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-4">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Comparing{" "}
            <span className="text-primary-600">v{baseVersion.version}</span>
            {" → "}
            <span className="text-primary-600">v{comparedVersion.version}</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          {onRestore && (
            <button
              type="button"
              onClick={() => onRestore(baseVersion)}
              className={cn(
                "flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg",
                "bg-primary-50 text-primary-700 hover:bg-primary-100",
                "dark:bg-primary-900/30 dark:text-primary-300 dark:hover:bg-primary-900/50",
                "transition-colors",
              )}
            >
              <RotateCcw size={14} />
              Restore v{baseVersion.version}
            </button>
          )}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              aria-label="Close diff view"
              className={cn(
                "p-1.5 rounded-lg transition-colors",
                "text-gray-500 hover:text-gray-700 hover:bg-gray-100",
                "dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-700",
              )}
            >
              <X size={18} />
            </button>
          )}
        </div>
      </div>

      {/* AI Explanation Panel (Sprint 4) */}
      {enableAI && userId && hasChanges && (
        <div
          data-testid="ai-diff-explanation"
          className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50"
        >
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={16} className="text-primary-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              AI Analysis
            </span>
            {aiLoading && (
              <Loader2 size={14} className="animate-spin text-primary-500" />
            )}
            {aiError && (
              <button
                type="button"
                onClick={() => refetchAI()}
                className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400"
              >
                Retry
              </button>
            )}
          </div>

          {aiLoading && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Analyzing changes...
            </p>
          )}

          {aiError && (
            <p className="text-sm text-red-600 dark:text-red-400">
              Failed to analyze diff. Click retry to try again.
            </p>
          )}

          {!aiLoading && !aiError && aiSummary && (
            <div className="space-y-2">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                {aiSummary}
              </p>

              {aiChanges && aiChanges.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {aiChanges.map((change, idx) => (
                    <span
                      key={idx}
                      className={cn(
                        "px-2 py-0.5 text-xs rounded-full",
                        change.impact === "high"
                          ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                          : change.impact === "medium"
                            ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300"
                            : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
                      )}
                    >
                      {change.type}: {change.description}
                    </span>
                  ))}
                </div>
              )}

              {breakingChanges && (
                <div className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400">
                  <span className="font-medium">
                    ⚠ Breaking changes detected
                  </span>
                </div>
              )}

              {affectedAreas && affectedAreas.length > 0 && (
                <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
                  <span>Affected areas:</span>
                  {affectedAreas.map((area, idx) => (
                    <span
                      key={idx}
                      className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded"
                    >
                      {area}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Diff Content */}
      <div
        data-testid="diff-content"
        data-mode={mode}
        className={cn(
          "flex-1 overflow-auto p-4 font-mono text-sm",
          mode === "split" && "grid grid-cols-2 gap-4",
        )}
      >
        {!hasChanges ? (
          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
            No changes between these versions
          </div>
        ) : mode === "unified" ? (
          <div className="space-y-0">
            {diffLines.map((line, index) => (
              <div
                key={index}
                className={cn(
                  "flex",
                  line.type === "added" && "bg-green-50 dark:bg-green-900/20",
                  line.type === "removed" && "bg-red-50 dark:bg-red-900/20",
                )}
              >
                <span
                  className={cn(
                    "w-12 text-right pr-3 text-gray-400 select-none border-r border-gray-200 dark:border-gray-700",
                    line.type === "added" &&
                      "text-green-600 dark:text-green-400",
                    line.type === "removed" && "text-red-600 dark:text-red-400",
                  )}
                >
                  {line.type === "added" && "+"}
                  {line.type === "removed" && "-"}
                  {line.type === "unchanged" && " "}
                </span>
                <span
                  className={cn(
                    "flex-1 pl-3 whitespace-pre",
                    line.type === "added" &&
                      "text-green-700 dark:text-green-300",
                    line.type === "removed" && "text-red-700 dark:text-red-300",
                    line.type === "unchanged" &&
                      "text-gray-700 dark:text-gray-300",
                  )}
                >
                  {line.content}
                </span>
              </div>
            ))}
          </div>
        ) : (
          // Split view
          <>
            <div className="border-r border-gray-200 dark:border-gray-700 pr-4">
              <div className="text-xs text-gray-500 mb-2">
                v{baseVersion.version}
              </div>
              {diffLines
                .filter((line) => line.type !== "added")
                .map((line, index) => (
                  <div
                    key={index}
                    className={cn(
                      "whitespace-pre",
                      line.type === "removed" &&
                        "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300",
                      line.type === "unchanged" &&
                        "text-gray-700 dark:text-gray-300",
                    )}
                  >
                    {line.content}
                  </div>
                ))}
            </div>
            <div className="pl-4">
              <div className="text-xs text-gray-500 mb-2">
                v{comparedVersion.version}
              </div>
              {diffLines
                .filter((line) => line.type !== "removed")
                .map((line, index) => (
                  <div
                    key={index}
                    className={cn(
                      "whitespace-pre",
                      line.type === "added" &&
                        "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300",
                      line.type === "unchanged" &&
                        "text-gray-700 dark:text-gray-300",
                    )}
                  >
                    {line.content}
                  </div>
                ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
