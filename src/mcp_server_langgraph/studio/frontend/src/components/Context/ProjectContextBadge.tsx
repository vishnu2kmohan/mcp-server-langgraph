/**
 * ProjectContextBadge Component
 *
 * Badge indicator showing when project context is active.
 * Features:
 * - Visible only when project has context file
 * - Shows context file path
 * - Click to open context panel
 * - Tooltip on hover
 * - Loading indicator
 *
 * Implements WCAG 2.1 AA accessibility requirements.
 * Based on GEMINI.md, AGENTS.md, CLAUDE.md patterns.
 */

import { useState } from "react";
import { FileText, Loader2 } from "lucide-react";

// ==============================================================================
// Types
// ==============================================================================

export type BadgeSize = "sm" | "md";

export interface ProjectContextBadgeProps {
  /** Whether project has context file */
  hasContext: boolean;
  /** Context file path */
  contextPath?: string;
  /** Whether loading */
  isLoading?: boolean;
  /** Size variant */
  size?: BadgeSize;
  /** Click handler */
  onClick?: () => void;
  /** Additional CSS classes */
  className?: string;
}

// ==============================================================================
// Constants
// ==============================================================================

const SIZE_CLASSES: Record<
  BadgeSize,
  { badge: string; icon: number; text: string }
> = {
  sm: { badge: "px-2 py-0.5", icon: 12, text: "text-xs" },
  md: { badge: "px-2.5 py-1", icon: 14, text: "text-sm" },
};

// ==============================================================================
// Component
// ==============================================================================

export function ProjectContextBadge({
  hasContext,
  contextPath,
  isLoading = false,
  size = "md",
  onClick,
  className = "",
}: ProjectContextBadgeProps) {
  const [showTooltip, setShowTooltip] = useState(false);

  // Don't render if no context
  if (!hasContext) {
    return null;
  }

  const sizeClasses = SIZE_CLASSES[size];

  return (
    <div className="relative inline-flex">
      <button
        type="button"
        data-testid="project-context-badge"
        data-size={size}
        onClick={onClick}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        aria-label={`Project context active${contextPath ? `: ${contextPath}` : ""}`}
        className={`inline-flex items-center gap-1.5 rounded-full bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300 hover:bg-primary-200 dark:hover:bg-primary-900/50 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors ${sizeClasses.badge} ${className}`}
      >
        {isLoading ? (
          <Loader2
            data-testid="loading-spinner"
            size={sizeClasses.icon}
            className="animate-spin"
          />
        ) : (
          <FileText data-testid="context-icon" size={sizeClasses.icon} />
        )}
        {contextPath && (
          <span className={`font-medium ${sizeClasses.text}`}>
            {contextPath}
          </span>
        )}
      </button>

      {/* Tooltip */}
      {showTooltip && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 dark:bg-gray-700 text-white text-xs rounded shadow-lg whitespace-nowrap z-50"
        >
          Project context active
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900 dark:border-t-gray-700" />
        </div>
      )}
    </div>
  );
}

export default ProjectContextBadge;
