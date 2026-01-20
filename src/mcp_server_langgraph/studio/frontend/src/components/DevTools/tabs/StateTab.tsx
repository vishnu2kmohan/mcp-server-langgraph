/**
 * StateTab Component
 *
 * Displays Redux/session/workflow state inspection in DevTools.
 * Provides a tree view of state with search and expand/collapse.
 * Includes time-travel debugging for history replay.
 *
 * Design System Compliance:
 * - Uses CVA for toolbar button variants
 * - Uses Motion.dev for button press feedback
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 */
import { useState, useMemo, useCallback, useEffect } from "react";
import {
  ChevronRight,
  ChevronDown,
  Search,
  RefreshCw,
  Database,
  Clock,
} from "lucide-react";

import { motion, useReducedMotion } from "motion/react";
import { cva } from "class-variance-authority";
import { buttonVariants as motionButtonVariants } from "@/design-system/micro-interactions";
import { cn } from "../../../utils/cn";
import { useAppSelector } from "../../../store/hooks";
import { useStateHistory } from "../hooks/useStateHistory";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import type { StateTabProps } from "../types";
import { STATUS_TEXT_COLORS } from "../utils/devToolsColors";

import { Button, Input } from "@/components/UI";

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Time-travel toggle button variants
 */
// eslint-disable-next-line react-refresh/only-export-components
export const timeTravelToggleVariants = cva(
  "flex items-center gap-1 px-2 py-0.5 rounded text-xs transition-colors",
  {
    variants: {
      active: {
        true: "bg-primary-3 dark:bg-primary-4 text-primary-10 dark:text-primary-7",
        false: "bg-neutral-2 text-neutral-10",
      },
    },
    defaultVariants: {
      active: false,
    },
  },
);

// =============================================================================
// Types
// =============================================================================

interface StateNode {
  key: string;
  value: unknown;
  path: string;
  type: "object" | "array" | "primitive";
  childCount?: number;
}

// =============================================================================
// Utility Functions
// =============================================================================

function getValueType(value: unknown): "object" | "array" | "primitive" {
  if (Array.isArray(value)) return "array";
  if (value !== null && typeof value === "object") return "object";
  return "primitive";
}

function formatValue(value: unknown): string {
  if (value === null) return "null";
  if (value === undefined) return "undefined";
  if (typeof value === "string") return `"${value}"`;
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return String(value);
  if (Array.isArray(value)) return `Array(${value.length})`;
  if (typeof value === "object") {
    const keys = Object.keys(value);
    return `{${keys.length} keys}`;
  }
  return String(value);
}

function getChildNodes(value: unknown, parentPath: string): StateNode[] {
  if (value === null || value === undefined) return [];

  if (Array.isArray(value)) {
    return value.map((item, index) => ({
      key: String(index),
      value: item,
      path: `${parentPath}[${index}]`,
      type: getValueType(item),
      childCount: getChildCount(item),
    }));
  }

  if (typeof value === "object") {
    return Object.entries(value).map(([key, val]) => ({
      key,
      value: val,
      path: parentPath ? `${parentPath}.${key}` : key,
      type: getValueType(val),
      childCount: getChildCount(val),
    }));
  }

  return [];
}

function getChildCount(value: unknown): number {
  if (Array.isArray(value)) return value.length;
  if (value !== null && typeof value === "object") {
    return Object.keys(value).length;
  }
  return 0;
}

function matchesSearch(node: StateNode, search: string): boolean {
  if (!search) return true;
  const lowerSearch = search.toLowerCase();

  // Check key
  if (node.key.toLowerCase().includes(lowerSearch)) return true;

  // Check path
  if (node.path.toLowerCase().includes(lowerSearch)) return true;

  // Check value for primitives
  if (node.type === "primitive") {
    const valueStr = formatValue(node.value).toLowerCase();
    if (valueStr.includes(lowerSearch)) return true;
  }

  return false;
}

// =============================================================================
// Subcomponents
// =============================================================================

interface StateNodeRowProps {
  node: StateNode;
  depth: number;
  isExpanded: boolean;
  onToggle: () => void;
  searchTerm: string;
}

function StateNodeRow({
  node,
  depth,
  isExpanded,
  onToggle,
  searchTerm,
}: StateNodeRowProps) {
  const hasChildren = node.type !== "primitive" && (node.childCount ?? 0) > 0;
  const isMatch = searchTerm && matchesSearch(node, searchTerm);

  const valueColor = useMemo(() => {
    if (node.value === null || node.value === undefined) {
      return STATUS_TEXT_COLORS.neutral;
    }
    if (typeof node.value === "string") {
      return STATUS_TEXT_COLORS.success;
    }
    if (typeof node.value === "number") {
      return STATUS_TEXT_COLORS.info;
    }
    if (typeof node.value === "boolean") {
      return "text-insight-10 dark:text-insight-9";
    }
    return "text-neutral-11";
  }, [node.value]);

  return (
    <div
      className={cn(
        "flex items-center py-0.5 hover:bg-neutral-a6 tree-indent",
        isMatch && "bg-warning-3",
      )}
      style={{ "--indent": `${depth * 16 + 8}px` } as React.CSSProperties}
    >
      {/* Expand/collapse button */}
      {hasChildren ? (
        <Button
          variant="secondary"
          className="p-0.5 hover:bg-neutral-3 rounded"
          data-testid={`expand-${node.path.replace(/\./g, "-")}`}
          type="button"
          onClick={onToggle}
          aria-expanded={isExpanded}
          aria-label={
            isExpanded ? `Collapse ${node.key}` : `Expand ${node.key}`
          }
        >
          {isExpanded ? (
            <ChevronDown
              size={12}
              className="text-neutral-10"
            />
          ) : (
            <ChevronRight
              size={12}
              className="text-neutral-10"
            />
          )}
        </Button>
      ) : (
        <span className="w-4" />
      )}
      {/* Key */}
      <span className="ml-1 text-sm text-neutral-11 font-medium">
        {node.key}
      </span>
      <span className="text-neutral-9 mx-1">:</span>
      {/* Value */}
      <span className={cn("text-sm", valueColor)}>
        {formatValue(node.value)}
      </span>
    </div>
  );
}

interface StateTreeProps {
  state: Record<string, unknown>;
  searchTerm: string;
}

function StateTree({ state, searchTerm }: StateTreeProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());

  const togglePath = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  // Build root nodes
  const rootNodes = useMemo((): StateNode[] => {
    return Object.entries(state).map(([key, value]) => ({
      key,
      value,
      path: key,
      type: getValueType(value),
      childCount: getChildCount(value),
    }));
  }, [state]);

  // Render nodes recursively
  const renderNode = (node: StateNode, depth: number): React.ReactNode => {
    const isExpanded = expandedPaths.has(node.path);
    const children = isExpanded ? getChildNodes(node.value, node.path) : [];

    // Filter by search if applicable
    if (searchTerm && !matchesSearch(node, searchTerm)) {
      // Check if any children match
      const allChildren = getChildNodes(node.value, node.path);
      const hasMatchingChildren = allChildren.some((child) =>
        matchesSearch(child, searchTerm),
      );
      if (!hasMatchingChildren) {
        return null;
      }
    }

    return (
      <div key={node.path}>
        <StateNodeRow
          node={node}
          depth={depth}
          isExpanded={isExpanded}
          onToggle={() => togglePath(node.path)}
          searchTerm={searchTerm}
        />
        {isExpanded && children.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  };

  return (
    <div data-testid="state-tree" className="font-mono text-xs">
      {rootNodes.map((node) => renderNode(node, 0))}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function StateTab({ context, contextEntityId }: StateTabProps) {
  const prefersReducedMotion = useReducedMotion();
  const [searchTerm, setSearchTerm] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [timeTravelEnabled, setTimeTravelEnabled] = useState(true);

  // Timeline integration for synchronized time-travel debugging
  const timeline = useTimelineContext();

  // Get state from Redux
  const reduxState = useAppSelector((state) => state);

  // Filter state based on context
  const displayState = useMemo(() => {
    // Cast through unknown to satisfy TypeScript
    const stateObj = reduxState as unknown as Record<string, unknown>;
    if (context === "session") {
      return {
        session: stateObj.session,
        canvas: stateObj.canvas,
      };
    }
    if (context === "workflow") {
      return {
        // workflow: stateObj.workflow, // if exists
      };
    }
    // Global - show all state
    return stateObj;
  }, [context, reduxState]);

  // State history for timeline integration
  // Note: Playback controls are provided by the unified TimelineBar
  const { snapshots, recordSnapshot } = useStateHistory({
    maxSnapshots: 50,
    playbackInterval: 300,
  });

  // Record state changes
  useEffect(() => {
    if (timeTravelEnabled && displayState) {
      recordSnapshot(displayState);
    }
  }, [displayState, timeTravelEnabled, recordSnapshot]);

  // Sync state display with unified timeline
  // The TimelineBar controls time-travel; StateTab shows the appropriate snapshot
  const stateToDisplay = useMemo(() => {
    // If timeline has a time window, find the snapshot closest to the current time
    if (timeline.timeWindow && snapshots.length > 0) {
      const targetTime = timeline.timeWindow.end;
      // Find the snapshot closest to but not after the target time
      let closestSnapshot = snapshots[0];
      for (const snapshot of snapshots) {
        if (snapshot.timestamp <= targetTime) {
          closestSnapshot = snapshot;
        } else {
          break;
        }
      }
      if (closestSnapshot) {
        return closestSnapshot.state;
      }
    }

    // Default: show current state
    return displayState;
  }, [displayState, timeline.timeWindow, snapshots]);

  const handleRefresh = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
  }, []);

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchTerm(e.target.value);
    },
    [],
  );

  const toggleTimeTravel = useCallback(() => {
    setTimeTravelEnabled((prev) => !prev);
  }, []);

  return (
    <div
      data-testid="state-tab"
      className="flex flex-col h-full bg-neutral-1"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-neutral-5 bg-neutral-1">
        {/* Context indicator */}
        <div className="flex items-center gap-1.5">
          <Database
            size={14}
            className="text-neutral-10"
            aria-hidden="true"
          />
          <span className="text-xs text-neutral-11 capitalize">
            {context}
          </span>
          {contextEntityId && (
            <span className="text-xs text-neutral-10 ml-1 px-1.5 py-0.5 bg-neutral-2 rounded">
              {contextEntityId}
            </span>
          )}
        </div>

        {/* Time-travel toggle */}
        <motion.button
          data-testid="time-travel-toggle"
          type="button"
          onClick={toggleTimeTravel}
          className={timeTravelToggleVariants({ active: timeTravelEnabled })}
          aria-pressed={timeTravelEnabled}
          aria-label="Toggle time-travel debugging"
          variants={prefersReducedMotion ? undefined : motionButtonVariants}
          initial="rest"
          whileHover="hover"
          whileTap="pressed"
        >
          <Clock size={10} />
          {timeTravelEnabled ? "Recording" : "Paused"}
        </motion.button>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Search */}
        <div className="relative">
          <Search
            className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-9"
            aria-hidden="true"
          />
          <Input
            data-testid="state-search"
            placeholder="Search state..."
            value={searchTerm}
            onChange={handleSearchChange}
            className={cn(
              "h-8 pl-8 pr-2 py-1.5 text-sm",
              "bg-neutral-1",
              "border border-neutral-5 rounded",
              "focus:outline-none focus:ring-1 focus:ring-primary-7",
              "w-40",
            )}
            aria-label="Search state"
          />
        </div>

        {/* Refresh button */}
        <Button size="icon"
          variant="secondary"
          className="p-1 hover:bg-neutral-3 rounded text-neutral-10"
          data-testid="refresh-button"
          type="button"
          onClick={handleRefresh}
          aria-label="Refresh state"
        >
          <RefreshCw size={14} />
        </Button>
      </div>
      {/* State tree - syncs with unified TimelineBar for time-travel */}
      <div className="flex-1 overflow-y-auto p-2" key={refreshKey}>
        <StateTree state={stateToDisplay} searchTerm={searchTerm} />
      </div>
    </div>
  );
}

export default StateTab;
