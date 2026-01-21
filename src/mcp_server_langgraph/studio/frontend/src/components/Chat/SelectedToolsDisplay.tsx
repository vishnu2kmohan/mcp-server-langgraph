/**
 * SelectedToolsDisplay Component
 *
 * Displays semantically selected tools as badges with optional selection scores.
 * Used to show which tools were selected for a chat message via semantic search.
 *
 * Features:
 * - Tool names as badges (v7: looks up display names from tool_ids)
 * - Selection scores as visual indicators
 * - Total available tools context
 * - Compact mode for space-constrained UIs
 * - Accessible list structure
 *
 * v7: Uses tool_id for unique identification, looks up display name from availableTools
 *
 * @see ADR-0099 Semantic Tool Selection
 */

import { useMemo } from "react";
import { Wrench } from "lucide-react";
import { Badge } from "../UI/Badge";
import type { ToolOption } from "./ToolSelector";

// =============================================================================
// Types
// =============================================================================

export interface SelectedToolsDisplayProps {
  /** List of selected tool IDs (v7: use tool_id for unique identification) */
  selectedTools: string[];
  /** Selection scores for each tool (keyed by tool_id) */
  selectionScores: Record<string, number>;
  /** Total number of tools available for selection */
  totalAvailableTools?: number | null;
  /** Available tools for display name lookup (v7) */
  availableTools?: ToolOption[];
  /** Compact mode for smaller display */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Utilities
// =============================================================================

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Format score as percentage (0.95 -> "95%")
 */
function formatScore(score: number): string {
  return `${Math.round(score * 100)}%`;
}

// =============================================================================
// Component
// =============================================================================

export function SelectedToolsDisplay({
  selectedTools,
  selectionScores,
  totalAvailableTools,
  availableTools = [],
  compact = false,
  className,
}: SelectedToolsDisplayProps) {
  // v7: Build lookup map from tool_id to tool details (must be before any early returns)
  const toolLookup = useMemo(() => {
    const map = new Map<string, ToolOption>();
    for (const tool of availableTools) {
      map.set(tool.toolId, tool);
    }
    return map;
  }, [availableTools]);

  // Don't render if no tools selected
  if (selectedTools.length === 0) {
    return null;
  }

  // v7: Get display name for a tool_id
  const getDisplayName = (toolId: string): string => {
    const tool = toolLookup.get(toolId);
    if (tool) {
      return tool.displayName;
    }
    // Fallback: extract name from tool_id (e.g., "builtin:web_search" → "web_search")
    const parts = toolId.split(":");
    return parts.length > 1 ? parts.slice(1).join(":") : toolId;
  };

  const textSize = compact ? "text-xs" : "text-sm";
  const iconSize = compact ? 12 : 14;

  return (
    <div className={cn("flex flex-col gap-1", textSize, className)}>
      {/* Header */}
      <div className="flex items-center gap-1.5 text-neutral-10">
        <Wrench size={iconSize} className="flex-shrink-0" />
        <span>Selected Tools</span>
        {totalAvailableTools != null && (
          <span className="text-neutral-9">
            ({selectedTools.length} of {totalAvailableTools})
          </span>
        )}
      </div>

      {/* Tool badges list (v7: uses tool_id, displays friendly name) */}
      <ul role="list" className="flex flex-wrap gap-1.5">
        {selectedTools.map((toolId) => {
          const score = selectionScores[toolId];
          const hasScore = score !== undefined;
          const displayName = getDisplayName(toolId);

          return (
            <li key={toolId} role="listitem">
              <Badge variant="outline" size={compact ? "sm" : "sm"} pill>
                <span>{displayName}</span>
                {hasScore && (
                  <span className="ml-1 text-neutral-9">
                    {formatScore(score)}
                  </span>
                )}
              </Badge>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default SelectedToolsDisplay;
