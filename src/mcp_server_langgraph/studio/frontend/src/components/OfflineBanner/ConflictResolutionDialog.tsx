/**
 * ConflictResolutionDialog Component
 *
 * Sprint 3 - Phase 2.2: Offline Conflict Resolution UI
 *
 * Displays sync conflicts and allows users to choose how to resolve them.
 * Supports individual resolution and bulk "resolve all" with suggested resolutions.
 */

import { useState, useCallback } from "react";
import { Dialog, Button, Card } from "../UI";
import { ChevronLeft, ChevronRight, AlertTriangle, Check } from "lucide-react";
import type {
  SyncConflict,
  ConflictResolution,
} from "../../hooks/useOfflineQueue";

// =============================================================================
// Types
// =============================================================================

export interface ConflictResolutionDialogProps {
  /** List of conflicts to resolve */
  conflicts: SyncConflict[];
  /** Called when a single conflict is resolved */
  onResolve: (conflictId: string, resolution: ConflictResolution) => void;
  /** Called when "Resolve All" is clicked (uses suggested resolutions) */
  onResolveAll: () => void;
}

// =============================================================================
// Helper Components
// =============================================================================

interface VersionDisplayProps {
  label: string;
  version: unknown;
  variant: "local" | "server";
}

function VersionDisplay({ label, version, variant }: VersionDisplayProps) {
  const formatValue = (val: unknown): string => {
    if (val === null || val === undefined) return "(empty)";
    if (typeof val === "object") {
      // Try to extract common fields
      const obj = val as Record<string, unknown>;
      if ("title" in obj) return String(obj.title);
      if ("name" in obj) return String(obj.name);
      if ("content" in obj) return String(obj.content);
      return JSON.stringify(val, null, 2);
    }
    return String(val);
  };

  return (
    <div
      className={`flex-1 rounded-md border p-3 ${
        variant === "local"
          ? "border-warning-6 bg-warning-2"
          : "border-primary-6 bg-primary-2"
      }`}
    >
      <div
        className={`mb-1 text-xs font-medium uppercase tracking-wide ${
          variant === "local" ? "text-warning-11" : "text-primary-11"
        }`}
      >
        {label}
      </div>
      <div className="font-mono text-sm text-neutral-12">
        {formatValue(version)}
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function ConflictResolutionDialog({
  conflicts,
  onResolve,
  onResolveAll,
}: ConflictResolutionDialogProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Derived values - computed before hooks to avoid conditional hook calls
  const hasConflicts = conflicts.length > 0;
  const currentConflict = hasConflicts ? conflicts[currentIndex] : null;
  const hasMultiple = conflicts.length > 1;
  const isFirst = currentIndex === 0;
  const isLast = currentIndex === conflicts.length - 1;

  // All hooks must be called unconditionally (before any early returns)
  const handleResolve = useCallback(
    (resolution: ConflictResolution) => {
      if (currentConflict) {
        onResolve(currentConflict.actionId, resolution);
      }
    },
    [currentConflict, onResolve],
  );

  const handlePrevious = useCallback(() => {
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const handleNext = useCallback(() => {
    setCurrentIndex((prev) => Math.min(conflicts.length - 1, prev + 1));
  }, [conflicts.length]);

  // Early return after all hooks
  if (!hasConflicts || !currentConflict) {
    return null;
  }

  return (
    <Dialog
      open={true}
      onClose={() => {}}
      title={`Sync Conflict${hasMultiple ? "s" : ""}`}
      aria-label="Sync Conflict Resolution"
    >
      <div className="space-y-4">
        {/* Header with conflict count */}
        <div className="flex items-center gap-2 text-warning-11">
          <AlertTriangle className="h-5 w-5" />
          <span className="font-medium">
            {conflicts.length} conflict{conflicts.length !== 1 ? "s" : ""}{" "}
            detected
          </span>
        </div>

        {/* Conflict details */}
        <Card className="p-4">
          <div className="mb-3 text-sm text-neutral-11">
            Field: <span className="font-medium">{currentConflict.field}</span>
          </div>

          {/* Version comparison */}
          <div className="flex gap-4">
            <VersionDisplay
              label="Local Version"
              version={currentConflict.localVersion}
              variant="local"
            />
            <VersionDisplay
              label="Server Version"
              version={currentConflict.serverVersion}
              variant="server"
            />
          </div>
        </Card>

        {/* Resolution buttons */}
        <div className="flex flex-wrap gap-2">
          <Button
            variant={
              currentConflict.suggestedResolution === "keep-local"
                ? "primary"
                : "secondary"
            }
            onClick={() => handleResolve("keep-local")}
            data-suggested={
              currentConflict.suggestedResolution === "keep-local"
            }
            aria-label="Keep Local"
          >
            Keep Local
          </Button>
          <Button
            variant={
              currentConflict.suggestedResolution === "keep-server"
                ? "primary"
                : "secondary"
            }
            onClick={() => handleResolve("keep-server")}
            data-suggested={
              currentConflict.suggestedResolution === "keep-server"
            }
            aria-label="Keep Server"
          >
            Keep Server
          </Button>
          <Button
            variant={
              currentConflict.suggestedResolution === "merge"
                ? "primary"
                : "secondary"
            }
            onClick={() => handleResolve("merge")}
            data-suggested={currentConflict.suggestedResolution === "merge"}
            aria-label="Merge"
          >
            Merge
          </Button>
        </div>

        {/* Navigation and bulk actions */}
        <div className="flex items-center justify-between border-t border-neutral-6 pt-4">
          {/* Pagination */}
          {hasMultiple && (
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handlePrevious}
                disabled={isFirst}
                aria-label="Previous"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-neutral-11">
                {currentIndex + 1} of {conflicts.length}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleNext}
                disabled={isLast}
                aria-label="Next"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}

          {/* Resolve All button (only for multiple conflicts) */}
          {hasMultiple && (
            <Button
              variant="primary"
              onClick={onResolveAll}
              aria-label="Resolve All"
            >
              <Check className="mr-1 h-4 w-4" />
              Resolve All (Suggested)
            </Button>
          )}
        </div>
      </div>
    </Dialog>
  );
}
