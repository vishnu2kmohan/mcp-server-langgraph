/**
 * SelectedToolsDisplay Component
 *
 * Displays semantically selected tools as badges with optional selection scores.
 * Used to show which tools were selected for a chat message via semantic search.
 *
 * Features:
 * - Tool names as badges
 * - Selection scores as visual indicators
 * - Total available tools context
 * - Compact mode for space-constrained UIs
 * - Accessible list structure
 *
 * @see ADR-0099 Semantic Tool Selection
 */

import { Wrench } from "lucide-react";
import { Badge } from "../UI/Badge";

// =============================================================================
// Types
// =============================================================================

export interface SelectedToolsDisplayProps {
  /** List of selected tool names */
  selectedTools: string[];
  /** Selection scores for each tool (0-1 scale) */
  selectionScores: Record<string, number>;
  /** Total number of tools available for selection */
  totalAvailableTools?: number | null;
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
  compact = false,
  className,
}: SelectedToolsDisplayProps) {
  // Don't render if no tools selected
  if (selectedTools.length === 0) {
    return null;
  }

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

      {/* Tool badges list */}
      <ul role="list" className="flex flex-wrap gap-1.5">
        {selectedTools.map((toolName) => {
          const score = selectionScores[toolName];
          const hasScore = score !== undefined;

          return (
            <li key={toolName} role="listitem">
              <Badge variant="outline" size={compact ? "sm" : "sm"} pill>
                <span>{toolName}</span>
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
