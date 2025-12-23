/**
 * StateTab Component
 *
 * Displays Redux/session/workflow state inspection in DevTools.
 * Provides a tree view of state with search and expand/collapse.
 * Includes time-travel debugging for history replay.
 */
import { useState, useMemo, useCallback, useEffect } from "react";
import {
  ChevronRight,
  ChevronDown,
  Search,
  RefreshCw,
  Database,
  Play,
  Pause,
  SkipBack,
  SkipForward,
  Rewind,
  FastForward,
  Clock,
} from "lucide-react";

import { cn } from "../../../utils/cn";
import { useAppSelector } from "../../../store/hooks";
import { useStateHistory } from "../hooks/useStateHistory";
import type { StateTabProps } from "../types";

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
      return "text-gray-400 dark:text-gray-500";
    }
    if (typeof node.value === "string") {
      return "text-green-600 dark:text-green-400";
    }
    if (typeof node.value === "number") {
      return "text-blue-600 dark:text-blue-400";
    }
    if (typeof node.value === "boolean") {
      return "text-purple-600 dark:text-purple-400";
    }
    return "text-gray-600 dark:text-gray-400";
  }, [node.value]);

  return (
    <div
      className={cn(
        "flex items-center py-0.5 hover:bg-gray-50 dark:hover:bg-gray-800/50",
        isMatch && "bg-yellow-50 dark:bg-yellow-900/20",
      )}
      style={{ paddingLeft: `${depth * 16 + 8}px` }}
    >
      {/* Expand/collapse button */}
      {hasChildren ? (
        <button
          data-testid={`expand-${node.path.replace(/\./g, "-")}`}
          type="button"
          onClick={onToggle}
          className="p-0.5 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
          aria-expanded={isExpanded}
          aria-label={
            isExpanded ? `Collapse ${node.key}` : `Expand ${node.key}`
          }
        >
          {isExpanded ? (
            <ChevronDown size={12} className="text-gray-500" />
          ) : (
            <ChevronRight size={12} className="text-gray-500" />
          )}
        </button>
      ) : (
        <span className="w-4" />
      )}

      {/* Key */}
      <span className="ml-1 text-sm text-gray-700 dark:text-gray-300 font-medium">
        {node.key}
      </span>

      <span className="text-gray-400 dark:text-gray-500 mx-1">:</span>

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
  const [searchTerm, setSearchTerm] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

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

  const handleRefresh = useCallback(() => {
    setRefreshKey((prev) => prev + 1);
  }, []);

  const handleSearchChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setSearchTerm(e.target.value);
    },
    [],
  );

  return (
    <div
      data-testid="state-tab"
      className="flex flex-col h-full bg-white dark:bg-gray-900"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        {/* Context indicator */}
        <div className="flex items-center gap-1.5">
          <Database size={14} className="text-gray-500" aria-hidden="true" />
          <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">
            {context}
          </span>
          {contextEntityId && (
            <span className="text-xs text-gray-500 dark:text-gray-500 ml-1 px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded">
              {contextEntityId}
            </span>
          )}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Search */}
        <div className="relative">
          <Search
            size={12}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400"
            aria-hidden="true"
          />
          <input
            data-testid="state-search"
            type="text"
            placeholder="Search state..."
            value={searchTerm}
            onChange={handleSearchChange}
            className={cn(
              "pl-6 pr-2 py-1 text-xs",
              "bg-white dark:bg-gray-900",
              "border border-gray-200 dark:border-gray-700 rounded",
              "focus:outline-none focus:ring-1 focus:ring-primary-500",
              "w-40",
            )}
            aria-label="Search state"
          />
        </div>

        {/* Refresh button */}
        <button
          data-testid="refresh-button"
          type="button"
          onClick={handleRefresh}
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500"
          aria-label="Refresh state"
        >
          <RefreshCw size={14} />
        </button>
      </div>

      {/* State tree */}
      <div className="flex-1 overflow-y-auto p-2" key={refreshKey}>
        <StateTree state={displayState} searchTerm={searchTerm} />
      </div>
    </div>
  );
}

export default StateTab;
