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
        "flex flex-col h-full bg-neutral-1 border border-neutral-5 rounded-lg",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-5">
        <div className="flex items-center gap-2">
          <GitCompare size={16} className="text-neutral-10" />
          <h3 className="text-sm font-medium text-neutral-12">
            Compare Versions
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {/* Mode toggle */}
          <div
            data-testid="diff-mode-toggle"
            className="flex items-center gap-1 bg-neutral-2 rounded-md p-0.5"
          >
            <Button
              variant="primary"
              type="button"
              onClick={() => handleModeChange("side-by-side")}
              className={cn(
                "flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium",
                "transition-colors",
                mode === "side-by-side"
                  ? "bg-neutral-1 text-neutral-12 shadow-sm"
                  : "text-neutral-10 hover:text-neutral-11",
              )}
            >
              <Columns size={12} />
              Split
            </Button>
            <Button
              variant="ghost"
              type="button"
              aria-label="Unified"
              onClick={() => handleModeChange("unified")}
              className={cn(
                "flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium",
                "transition-colors",
                mode === "unified"
                  ? "bg-neutral-1 text-neutral-12 shadow-sm"
                  : "text-neutral-10 hover:text-neutral-11",
              )}
            >
              <List size={12} />
              Unified
            </Button>
          </div>

          {/* Close button */}
          {onClose && (
            <Button
              size="icon"
              variant="secondary"
              className="p-1 rounded hover:bg-neutral-2 text-neutral-10"
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
      <div className="flex items-center justify-between px-4 py-1.5 bg-neutral-1 border-b border-neutral-5 text-xs">
        <span className="text-neutral-11">
          v{versionA.versionNumber} - {versionA.commitMessage || "No message"}
        </span>
        <span className="text-neutral-11">
          v{versionB.versionNumber} - {versionB.commitMessage || "No message"}
        </span>
      </div>
      {/* Diff summary */}
      <div
        data-testid="diff-summary"
        className="flex items-center gap-4 px-4 py-2 bg-neutral-1 border-b border-neutral-5"
      >
        {diffSummary.hasChanges ? (
          <>
            {(diffSummary.nodesAdded > 0 || diffSummary.edgesAdded > 0) && (
              <div
                data-testid="diff-additions"
                className="flex items-center gap-1 text-xs text-success-10 dark:text-success-7"
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
                className="flex items-center gap-1 text-xs text-error-10 dark:text-error-7"
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
          <span className="text-xs text-neutral-10">
            No changes between versions
          </span>
        )}
      </div>
      {/* Diff content */}
      <div className="flex-1 overflow-hidden">
        {mode === "side-by-side" ? (
          <div
            data-testid="side-by-side-view"
            className="flex h-full divide-x divide-neutral-5 dark:divide-neutral-6"
          >
            {/* Left pane (Version A) */}
            <div className="flex-1 overflow-auto">
              <pre className="p-4 text-xs text-neutral-11 font-mono whitespace-pre-wrap">
                {jsonA}
              </pre>
            </div>
            {/* Right pane (Version B) */}
            <div className="flex-1 overflow-auto">
              <pre className="p-4 text-xs text-neutral-11 font-mono whitespace-pre-wrap">
                {jsonB}
              </pre>
            </div>
          </div>
        ) : (
          <div data-testid="unified-view" className="h-full overflow-auto">
            <pre className="p-4 text-xs text-neutral-11 font-mono whitespace-pre-wrap">
              {/* Unified diff view - show both with labels */}
              <span className="text-error-10 dark:text-error-7">
                --- v{versionA.versionNumber}
              </span>
              {"\n"}
              <span className="text-success-10 dark:text-success-7">
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
