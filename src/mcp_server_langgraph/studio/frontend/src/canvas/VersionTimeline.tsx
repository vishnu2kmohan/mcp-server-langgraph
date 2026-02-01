/**
 * VersionTimeline - Phase 1
 *
 * Artifact version history timeline component that displays
 * version history and allows rollback to previous versions.
 */
import { useState, useCallback, useMemo } from "react";
import {
  RotateCcw,
  User,
  Sparkles,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import type { ArtifactVersion } from "../types/artifacts";
import { cn } from "../utils/cn";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface VersionTimelineProps {
  /** List of versions (most recent first) */
  versions: ArtifactVersion[];
  /** Current version number */
  currentVersion: number;
  /** Callback when version is selected for preview */
  onVersionSelect: (version: ArtifactVersion) => void;
  /** Callback when restore is clicked */
  onRestore?: (version: ArtifactVersion) => void;
  /** Show diff preview on hover */
  showDiffPreview?: boolean;
  /** Maximum versions to show before collapse */
  maxVisibleVersions?: number;
  /** Additional class name */
  className?: string;
}

// =============================================================================
// Utility
// =============================================================================

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// =============================================================================
// Version Item Component
// =============================================================================

interface VersionItemProps {
  version: ArtifactVersion;
  isCurrent: boolean;
  isHovered: boolean;
  onSelect: () => void;
  onRestore?: () => void;
  onHover: (hovering: boolean) => void;
  showDiffPreview?: boolean;
}

function VersionItem({
  version,
  isCurrent,
  isHovered,
  onSelect,
  onRestore,
  onHover,
  showDiffPreview,
}: VersionItemProps) {
  // Check if this version was edited by AI
  const isAI = version.metadata.editedBy === "ai";

  return (
    <li
      data-testid={`version-item-${version.version}`}
      className={cn(
        "relative flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer",
        "transition-colors",
        isCurrent && "current bg-primary-1 dark:bg-primary-a3",
        !isCurrent && "hover:bg-neutral-1",
      )}
      onClick={() => !isCurrent && onSelect()}
      onMouseEnter={() => onHover(true)}
      onMouseLeave={() => onHover(false)}
    >
      {/* Timeline dot */}
      <div
        className={cn(
          "w-2 h-2 rounded-full flex-shrink-0",
          isCurrent ? "bg-primary-9" : "bg-neutral-3",
        )}
      />
      {/* Version info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "font-medium text-sm",
              isCurrent
                ? "text-primary-11 dark:text-primary-11"
                : "text-neutral-11",
            )}
          >
            v{version.version}
          </span>
          {isAI ? (
            <span data-testid="ai-indicator">
              <Sparkles
                size={12}
                className="text-insight-11 dark:text-insight-11"
              />
            </span>
          ) : (
            <span data-testid="user-indicator">
              <User size={12} className="text-neutral-11" />
            </span>
          )}
        </div>
        <div className="text-xs text-neutral-11">
          {formatDate(version.createdAt)}
        </div>
      </div>
      {/* Restore button (shown on hover) */}
      {!isCurrent && isHovered && onRestore && (
        <Button
          variant="primary"
          data-testid={`restore-button-${version.version}`}
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRestore();
          }}
          aria-label={`Restore version ${version.version}`}
          className={cn(
            "p-1.5 rounded transition-colors",
            "text-neutral-11 hover:text-primary-11",
            "hover:bg-primary-3 dark:hover:bg-primary-a4",
          )}
        >
          <RotateCcw size={14} />
        </Button>
      )}
      {/* Diff preview tooltip */}
      {showDiffPreview && isHovered && !isCurrent && (
        <div
          data-testid="diff-preview"
          className={cn(
            "absolute left-full ml-2 top-0 z-tooltip",
            "w-64 p-3 rounded-lg shadow-lg",
            "bg-neutral-1",
            "border border-neutral-5",
          )}
        >
          <div className="text-xs text-neutral-11 mb-2">Content preview:</div>
          <pre className="text-xs text-neutral-11 overflow-hidden truncate">
            {version.content.slice(0, 100)}...
          </pre>
        </div>
      )}
    </li>
  );
}

// =============================================================================
// Component
// =============================================================================

export function VersionTimeline({
  versions,
  currentVersion,
  onVersionSelect,
  onRestore,
  showDiffPreview = false,
  maxVisibleVersions = 5,
  className,
}: VersionTimelineProps) {
  const [hoveredVersion, setHoveredVersion] = useState<number | null>(null);
  const [isExpanded, setIsExpanded] = useState(false);

  const shouldCollapse = versions.length > maxVisibleVersions;
  const visibleVersions = useMemo(() => {
    if (!shouldCollapse || isExpanded) {
      return versions;
    }
    return versions.slice(0, maxVisibleVersions);
  }, [versions, shouldCollapse, isExpanded, maxVisibleVersions]);

  const hiddenCount = versions.length - maxVisibleVersions;

  const handleVersionSelect = useCallback(
    (version: ArtifactVersion) => {
      if (version.version !== currentVersion) {
        onVersionSelect(version);
      }
    },
    [currentVersion, onVersionSelect],
  );

  const handleRestore = useCallback(
    (version: ArtifactVersion) => {
      onRestore?.(version);
    },
    [onRestore],
  );

  const handleHover = useCallback((version: number, hovering: boolean) => {
    setHoveredVersion(hovering ? version : null);
  }, []);

  if (versions.length === 0) {
    return (
      <div
        data-testid="version-timeline"
        className={cn(
          "flex items-center justify-center p-4 text-neutral-11",
          className,
        )}
      >
        No version history
      </div>
    );
  }

  return (
    <div
      data-testid="version-timeline"
      className={cn("flex flex-col", className)}
    >
      <ul role="list" className="space-y-1">
        {visibleVersions.map((version) => (
          <VersionItem
            key={version.id}
            version={version}
            isCurrent={version.version === currentVersion}
            isHovered={hoveredVersion === version.version}
            onSelect={() => handleVersionSelect(version)}
            onRestore={onRestore ? () => handleRestore(version) : undefined}
            onHover={(hovering) => handleHover(version.version, hovering)}
            showDiffPreview={showDiffPreview}
          />
        ))}
      </ul>
      {/* Show more/less button */}
      {shouldCollapse && (
        <Button
          variant="primary"
          data-testid="show-more-button"
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className={cn(
            "flex items-center justify-center gap-1 mt-2 py-1.5 text-sm",
            "text-neutral-11 hover:text-neutral-11",
            "transition-colors",
          )}
        >
          {isExpanded ? (
            <>
              <ChevronUp size={14} />
              Show less
            </>
          ) : (
            <>
              <ChevronDown size={14} />
              Show {hiddenCount} more
            </>
          )}
        </Button>
      )}
    </div>
  );
}
