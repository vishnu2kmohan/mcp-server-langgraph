/**
 * ArtifactTabBar Component
 *
 * Tab bar with drag-to-reorder support for canvas artifacts.
 * Uses @dnd-kit for accessible drag and drop.
 *
 * Design System Compliance:
 * - Radix color scale (neutral-2 background)
 * - Horizontal scrolling for overflow
 * - Accessible tablist pattern
 */

import { useCallback } from "react";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  horizontalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import type { CanvasArtifact } from "../types/artifacts";
import { ArtifactTab } from "./ArtifactTab";
import { cn } from "../utils/cn";

interface ArtifactTabBarProps {
  /** List of artifacts */
  artifacts: CanvasArtifact[];
  /** Order of artifact IDs for display */
  tabOrder: string[];
  /** Currently selected artifact ID */
  selectedId: string | null;
  /** Callback when an artifact is selected */
  onSelect: (artifact: CanvasArtifact) => void;
  /** Callback when an artifact tab is closed */
  onClose: (artifactId: string) => void;
  /** Callback when an artifact is renamed */
  onRename: (artifactId: string, title: string) => void;
  /** Callback when duplicate is requested */
  onDuplicate: (artifactId: string) => void;
  /** Callback when export is requested */
  onExport: (artifactId: string) => void;
  /** Callback when tab order changes */
  onReorder: (newOrder: string[]) => void;
  /** Additional class names */
  className?: string;
}

export function ArtifactTabBar({
  artifacts,
  tabOrder,
  selectedId,
  onSelect,
  onClose,
  onRename,
  onDuplicate,
  onExport,
  onReorder,
  className = "",
}: ArtifactTabBarProps) {
  // Set up drag sensors with activation constraint
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8, // 8px drag distance before activating
      },
    })
  );

  // Sort artifacts by tabOrder
  const sortedArtifacts = tabOrder
    .map((id) => artifacts.find((a) => a.id === id))
    .filter((a): a is CanvasArtifact => a !== undefined);

  // Handle drag end
  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (over && active.id !== over.id) {
        const oldIndex = tabOrder.indexOf(active.id as string);
        const newIndex = tabOrder.indexOf(over.id as string);
        onReorder(arrayMove(tabOrder, oldIndex, newIndex));
      }
    },
    [tabOrder, onReorder]
  );

  // Empty state
  if (sortedArtifacts.length === 0) {
    return (
      <div
        role="tablist"
        aria-label="Artifact tabs"
        className={cn(
          "flex items-center justify-center",
          "px-2 pt-2 pb-0",
          "bg-neutral-2",
          "border-b border-neutral-6",
          "text-sm text-neutral-11",
          "h-10",
          className
        )}
      >
        <span>No artifacts</span>
      </div>
    );
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      <div
        role="tablist"
        aria-label="Artifact tabs"
        className={cn(
          "flex items-end gap-0.5",
          "px-2 pt-2",
          "bg-neutral-2",
          "border-b border-neutral-6",
          "overflow-x-auto",
          "scrollbar-thin scrollbar-thumb-neutral-6",
          className
        )}
      >
        <SortableContext
          items={tabOrder}
          strategy={horizontalListSortingStrategy}
        >
          {sortedArtifacts.map((artifact) => (
            <ArtifactTab
              key={artifact.id}
              artifact={artifact}
              isSelected={artifact.id === selectedId}
              onSelect={() => onSelect(artifact)}
              onClose={() => onClose(artifact.id)}
              onRename={(title) => onRename(artifact.id, title)}
              onDuplicate={() => onDuplicate(artifact.id)}
              onExport={() => onExport(artifact.id)}
            />
          ))}
        </SortableContext>
      </div>
    </DndContext>
  );
}

export default ArtifactTabBar;
