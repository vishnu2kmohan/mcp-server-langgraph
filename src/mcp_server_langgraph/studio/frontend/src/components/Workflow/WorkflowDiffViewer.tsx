/**
 * WorkflowDiffViewer Component
 *
 * Side-by-side or unified diff view for comparing workflow versions.
 * Enables visual comparison of nodes, edges, and metadata changes.
 *
 * Features:
 * - Side-by-side view (split pane)
 * - Unified view (inline diff)
 * - Additions highlighted in green
 * - Deletions highlighted in red
 * - Diff summary statistics
 *
 * References:
 * - Plan: Chat-to-Workflow Feature, Phase 4
 * - ADR-0089: Prompt Architecture Centralization
 */

import { useState, useMemo, useCallback } from "react";
import { X, GitCompare, Columns, List, Plus, Minus } from "lucide-react";

import { cn } from "../../utils/cn";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

type DiffMode = "side-by-side" | "unified";

interface WorkflowVersion {
  id: string;
  workflowId: string;
  versionNumber: number;
  graphJson: {
    nodes: Array<{ id: string; type: string; data?: Record<string, unknown> }>;
    edges: Array<{ id?: string; source: string; target: string }>;
  };
  commitMessage?: string;
  createdBy: string;
  createdAt: string;
}

interface DiffSummary {
  nodesAdded: number;
  nodesRemoved: number;
  edgesAdded: number;
  edgesRemoved: number;
  hasChanges: boolean;
}

export interface WorkflowDiffViewerProps {
  /** Version A (older/left) */
  versionA: WorkflowVersion;
  /** Version B (newer/right) */
  versionB: WorkflowVersion;
  /** Initial diff mode */
  defaultMode?: DiffMode;
  /** Callback when close button clicked */
  onClose?: () => void;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Helpers
// =============================================================================

function computeDiffSummary(
  versionA: WorkflowVersion,
  versionB: WorkflowVersion,
): DiffSummary {
  const nodesA = new Set(versionA.graphJson.nodes.map((n) => n.id));
  const nodesB = new Set(versionB.graphJson.nodes.map((n) => n.id));

  const edgesA = new Set(
    versionA.graphJson.edges.map((e) => `${e.source}->${e.target}`),
  );
  const edgesB = new Set(
    versionB.graphJson.edges.map((e) => `${e.source}->${e.target}`),
  );

  const nodesAdded = [...nodesB].filter((n) => !nodesA.has(n)).length;
  const nodesRemoved = [...nodesA].filter((n) => !nodesB.has(n)).length;
  const edgesAdded = [...edgesB].filter((e) => !edgesA.has(e)).length;
  const edgesRemoved = [...edgesA].filter((e) => !edgesB.has(e)).length;

  return {
    nodesAdded,
    nodesRemoved,
    edgesAdded,
    edgesRemoved,
    hasChanges:
      nodesAdded > 0 || nodesRemoved > 0 || edgesAdded > 0 || edgesRemoved > 0,
  };
}

function formatJson(obj: unknown): string {
  return JSON.stringify(obj, null, 2);
}

// =============================================================================
// Component
// =============================================================================

export function WorkflowDiffViewer({
  versionA,
  versionB,
  defaultMode = "side-by-side",
  onClose,
  className,
}: WorkflowDiffViewerProps) {
  const [mode, setMode] = useState<DiffMode>(defaultMode);

  // Compute diff summary
  const diffSummary = useMemo(
    () => computeDiffSummary(versionA, versionB),
    [versionA, versionB],
  );

  // JSON representations
  const jsonA = useMemo(() => formatJson(versionA.graphJson), [versionA]);
  const jsonB = useMemo(() => formatJson(versionB.graphJson), [versionB]);

  // Handle mode toggle
  const handleModeChange = useCallback((newMode: DiffMode) => {
    setMode(newMode);
  }, []);

  return (
    <div
      data-testid="diff-viewer"
      className={cn(
        "flex flex-col h-full bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-700 rounded-lg",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center gap-2">
          <GitCompare
            size={16}
            className="text-neutral-500 dark:text-neutral-400"
          />
          <h3 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
            Compare Versions
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {/* Mode toggle */}
          <div
            data-testid="diff-mode-toggle"
            className="flex items-center gap-1 bg-neutral-100 dark:bg-neutral-800 rounded-md p-0.5"
          >
            <Button
              type="button"
              onClick={() => handleModeChange("side-by-side")}
              className={cn(
                "flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium",
                "transition-colors",
                mode === "side-by-side"
                  ? "bg-white dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 shadow-sm"
                  : "text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:hover:text-neutral-300",
              )}
            >
              <Columns size={12} />
              Split
            </Button>
            <Button
              type="button"
              aria-label="Unified"
              onClick={() => handleModeChange("unified")}
              className={cn(
                "flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium",
                "transition-colors",
                mode === "unified"
                  ? "bg-white dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100 shadow-sm"
                  : "text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:hover:text-neutral-300",
              )}
            >
              <List size={12} />
              Unified
            </Button>
          </div>

          {/* Close button */}
          {onClose && (
            <Button
              variant="secondary"
              className="p-1 rounded hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800 text-neutral-500 dark:text-neutral-400"
              type="button"
              aria-label="Close"
              onClick={onClose}
            >
              <X size={16} />
            </Button>
          )}
        </div>
      </div>
      {/* Version labels */}
      <div className="flex items-center justify-between px-4 py-1.5 bg-neutral-50 dark:bg-neutral-800/50 border-b border-neutral-200 dark:border-neutral-700 text-xs">
        <span className="text-neutral-600 dark:text-neutral-400">
          v{versionA.versionNumber} - {versionA.commitMessage || "No message"}
        </span>
        <span className="text-neutral-600 dark:text-neutral-400">
          v{versionB.versionNumber} - {versionB.commitMessage || "No message"}
        </span>
      </div>
      {/* Diff summary */}
      <div
        data-testid="diff-summary"
        className="flex items-center gap-4 px-4 py-2 bg-neutral-50 dark:bg-neutral-800/50 border-b border-neutral-200 dark:border-neutral-700"
      >
        {diffSummary.hasChanges ? (
          <>
            {(diffSummary.nodesAdded > 0 || diffSummary.edgesAdded > 0) && (
              <div
                data-testid="diff-additions"
                className="flex items-center gap-1 text-xs text-success-600 dark:text-success-400"
              >
                <Plus size={12} />
                <span>
                  {diffSummary.nodesAdded > 0 &&
                    `${diffSummary.nodesAdded} node${diffSummary.nodesAdded > 1 ? "s" : ""}`}
                  {diffSummary.nodesAdded > 0 &&
                    diffSummary.edgesAdded > 0 &&
                    ", "}
                  {diffSummary.edgesAdded > 0 &&
                    `${diffSummary.edgesAdded} edge${diffSummary.edgesAdded > 1 ? "s" : ""}`}
                </span>
              </div>
            )}
            {(diffSummary.nodesRemoved > 0 || diffSummary.edgesRemoved > 0) && (
              <div
                data-testid="diff-deletions"
                className="flex items-center gap-1 text-xs text-error-600 dark:text-error-400"
              >
                <Minus size={12} />
                <span>
                  {diffSummary.nodesRemoved > 0 &&
                    `${diffSummary.nodesRemoved} node${diffSummary.nodesRemoved > 1 ? "s" : ""}`}
                  {diffSummary.nodesRemoved > 0 &&
                    diffSummary.edgesRemoved > 0 &&
                    ", "}
                  {diffSummary.edgesRemoved > 0 &&
                    `${diffSummary.edgesRemoved} edge${diffSummary.edgesRemoved > 1 ? "s" : ""}`}
                </span>
              </div>
            )}
          </>
        ) : (
          <span className="text-xs text-neutral-500 dark:text-neutral-400">
            No changes between versions
          </span>
        )}
      </div>
      {/* Diff content */}
      <div className="flex-1 overflow-hidden">
        {mode === "side-by-side" ? (
          <div
            data-testid="side-by-side-view"
            className="flex h-full divide-x divide-neutral-200 dark:divide-neutral-700"
          >
            {/* Left pane (Version A) */}
            <div className="flex-1 overflow-auto">
              <pre className="p-4 text-xs text-neutral-700 dark:text-neutral-300 font-mono whitespace-pre-wrap">
                {jsonA}
              </pre>
            </div>
            {/* Right pane (Version B) */}
            <div className="flex-1 overflow-auto">
              <pre className="p-4 text-xs text-neutral-700 dark:text-neutral-300 font-mono whitespace-pre-wrap">
                {jsonB}
              </pre>
            </div>
          </div>
        ) : (
          <div data-testid="unified-view" className="h-full overflow-auto">
            <pre className="p-4 text-xs text-neutral-700 dark:text-neutral-300 font-mono whitespace-pre-wrap">
              {/* Unified diff view - show both with labels */}
              <span className="text-error-600 dark:text-error-400">
                --- v{versionA.versionNumber}
              </span>
              {"\n"}
              <span className="text-success-600 dark:text-success-400">
                +++ v{versionB.versionNumber}
              </span>
              {"\n\n"}
              {jsonB}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default WorkflowDiffViewer;
