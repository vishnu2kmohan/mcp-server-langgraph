/**
 * AgentTraceTab Component
 *
 * Displays LangGraph agent execution traces in DevTools.
 * Provides node visualization, token usage, and timeline view.
 */
import { useState, useCallback, useMemo } from "react";
import {
  RefreshCw,
  List,
  Activity,
  ChevronRight,
  ChevronDown,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap,
} from "lucide-react";

import { cn } from "../../../utils/cn";
import { useAgentTrace } from "../hooks/useAgentTrace";
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import { STATUS_TEXT_COLORS } from "../utils/devToolsColors";
import type { AgentTraceTabProps } from "../types";
import type { TraceStepPayload } from "../../../types/websocket-protocols";

import { Button } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

interface TraceNode {
  id: string;
  name: string;
  status: "pending" | "running" | "completed" | "error" | "skipped";
  duration?: number;
  startTime?: number;
  endTime?: number;
}

type ViewMode = "list" | "timeline";

// =============================================================================
// Subcomponents
// =============================================================================

interface NodeStatusIconProps {
  status: TraceNode["status"];
  nodeId: string;
}

function NodeStatusIcon({ status, nodeId }: NodeStatusIconProps) {
  const iconProps = { size: 14, "aria-hidden": true };

  return (
    <span data-testid={`node-status-${nodeId}`}>
      {status === "completed" && (
        <CheckCircle {...iconProps} className="text-success-9" />
      )}
      {status === "running" && (
        <Loader2 {...iconProps} className="text-primary-9 animate-spin" />
      )}
      {status === "pending" && (
        <Clock {...iconProps} className="text-neutral-9" />
      )}
      {status === "error" && (
        <AlertCircle {...iconProps} className="text-error-9" />
      )}
      {status === "skipped" && (
        <Clock {...iconProps} className="text-neutral-9" />
      )}
    </span>
  );
}

interface TraceNodeRowProps {
  node: TraceNode;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggleExpand: () => void;
}

function TraceNodeRow({
  node,
  isSelected,
  isExpanded,
  onSelect,
  onToggleExpand,
}: TraceNodeRowProps) {
  return (
    <div
      data-testid={`trace-node-${node.id}`}
      className={cn(
        "flex items-center gap-2 px-2 py-1.5 cursor-pointer",
        "border-b border-neutral-5",
        "hover:bg-neutral-a6",
        isSelected && "bg-primary-1 dark:bg-primary-a3",
      )}
      onClick={onSelect}
    >
      {/* Expand button */}
      <Button
        variant="secondary"
        className="p-0.5 hover:bg-neutral-3 rounded"
        data-testid={`expand-node-${node.id}`}
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onToggleExpand();
        }}
        aria-expanded={isExpanded}
        aria-label={
          isExpanded ? `Collapse ${node.name}` : `Expand ${node.name}`
        }
      >
        {isExpanded ? (
          <ChevronDown size={12} className="text-neutral-10" />
        ) : (
          <ChevronRight size={12} className="text-neutral-10" />
        )}
      </Button>
      {/* Status icon */}
      <NodeStatusIcon status={node.status} nodeId={node.id} />
      {/* Node name */}
      <span className="flex-1 text-sm text-neutral-11">{node.name}</span>
      {/* Duration */}
      {node.duration !== undefined && node.duration > 0 && (
        <span className="text-xs text-neutral-10">{node.duration}ms</span>
      )}
    </div>
  );
}

interface NodeDetailsProps {
  node: TraceNode;
}

function NodeDetails({ node }: NodeDetailsProps) {
  return (
    <div
      data-testid={`node-details-${node.id}`}
      className="px-4 py-2 bg-neutral-1 text-xs"
    >
      <div className="grid grid-cols-2 gap-2">
        <div>
          <span className="text-neutral-10">ID:</span>
          <span className="ml-2 text-neutral-11">{node.id}</span>
        </div>
        <div>
          <span className="text-neutral-10">Status:</span>
          <span className="ml-2 text-neutral-11 capitalize">{node.status}</span>
        </div>
        {node.startTime && (
          <div>
            <span className="text-neutral-10">Start:</span>
            <span className="ml-2 text-neutral-11">
              {new Date(node.startTime).toISOString()}
            </span>
          </div>
        )}
        {node.endTime && (
          <div>
            <span className="text-neutral-10">End:</span>
            <span className="ml-2 text-neutral-11">
              {new Date(node.endTime).toISOString()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

interface TimelineNodeProps {
  node: TraceNode;
  totalDuration: number;
  startOffset: number;
}

function TimelineNode({ node, totalDuration, startOffset }: TimelineNodeProps) {
  const width =
    totalDuration > 0 ? ((node.duration ?? 0) / totalDuration) * 100 : 0;
  const left = totalDuration > 0 ? (startOffset / totalDuration) * 100 : 0;

  const statusColors: Record<TraceNode["status"], string> = {
    completed: "bg-success-9",
    running: "bg-primary-9",
    pending: "bg-neutral-3",
    error: "bg-error-9",
    skipped: "bg-neutral-3",
  };

  return (
    <div className="flex items-center gap-2 py-1">
      <span className="w-24 text-xs text-neutral-11 truncate">{node.name}</span>
      <div className="flex-1 h-4 bg-neutral-2 rounded relative">
        <div
          className={cn("h-full rounded", statusColors[node.status])}
          style={{
            width: `${Math.max(width, 1)}%`,
            marginLeft: `${left}%`,
          }}
          title={`${node.name}: ${node.duration ?? 0}ms`}
        />
      </div>
      <span className="w-12 text-xs text-right text-neutral-10">
        {node.duration ?? 0}ms
      </span>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AgentTraceTab({
  sessionId,
  onNodeHighlight,
  externalSteps = [],
}: AgentTraceTabProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  // Timeline integration for time-travel debugging
  const timeline = useTimelineContext();

  const { trace, isLoading, error, refetch } = useAgentTrace({
    sessionId,
    autoRefresh: Boolean(sessionId),
  });

  const mappedExternalNodes: TraceNode[] = useMemo(() => {
    return externalSteps.map((step: TraceStepPayload) => ({
      id: step.node_id || step.id || `${step.name}-${step.start_time}`,
      name: step.name,
      status: (step.status as TraceNode["status"]) ?? "pending",
      duration: step.duration_ms ?? undefined,
      startTime: step.start_time,
      endTime: step.end_time,
    }));
  }, [externalSteps]);

  const combinedNodes: TraceNode[] = useMemo(() => {
    const baseNodes = trace?.nodes ?? [];
    const existingIds = new Set(baseNodes.map((n) => n.id));
    const extra = mappedExternalNodes.filter((n) => !existingIds.has(n.id));
    return [...baseNodes, ...extra];
  }, [trace?.nodes, mappedExternalNodes]);

  // Handle node selection
  const handleNodeSelect = useCallback(
    (nodeId: string) => {
      if (selectedNodeId === nodeId) {
        setSelectedNodeId(null);
        onNodeHighlight?.(null);
      } else {
        setSelectedNodeId(nodeId);
        onNodeHighlight?.(nodeId);
      }
    },
    [selectedNodeId, onNodeHighlight],
  );

  // Handle node expand/collapse
  const toggleNodeExpand = useCallback((nodeId: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  }, []);

  // Filter nodes by timeline window for time-travel debugging
  // Uses startTime and endTime properties from LangGraphNode for filtering
  const filteredNodes = useMemo(() => {
    if (!combinedNodes.length) return [];

    // If no timeline window is set, show all nodes
    if (!timeline?.timeWindow) {
      return combinedNodes;
    }

    const { start: windowStart, end: windowEnd } = timeline.timeWindow;

    // Filter nodes that overlap with the timeline window
    // A node overlaps if: nodeStart < windowEnd AND nodeEnd > windowStart
    return combinedNodes.filter((node) => {
      // If node has no timing info, include it (backward compatibility)
      if (node.startTime === undefined) {
        return true;
      }

      const nodeStart = node.startTime;
      // For running nodes without endTime, use current time
      const nodeEnd = node.endTime ?? Date.now();

      // Check for overlap: node overlaps window if it doesn't end before window starts
      // AND doesn't start after window ends
      return nodeEnd > windowStart && nodeStart < windowEnd;
    });
  }, [combinedNodes, timeline?.timeWindow]);

  // Calculate total duration for timeline (using filtered nodes)
  const totalDuration = filteredNodes.reduce(
    (sum, node) => sum + (node.duration ?? 0),
    0,
  );

  // Calculate start offsets for timeline (using filtered nodes)
  const getStartOffset = (index: number): number => {
    return filteredNodes
      .slice(0, index)
      .reduce((sum, node) => sum + (node.duration ?? 0), 0);
  };

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="agent-trace-tab"
        className="flex flex-col h-full bg-neutral-1"
      >
        <div
          data-testid="agent-trace-loading"
          className="flex-1 flex items-center justify-center"
        >
          <Loader2 className="w-8 h-8 animate-spin text-primary-9" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        data-testid="agent-trace-tab"
        className="flex flex-col h-full bg-neutral-1"
      >
        <div
          data-testid="agent-trace-error"
          className={cn(
            "flex-1 flex flex-col items-center justify-center",
            STATUS_TEXT_COLORS.error,
          )}
        >
          <AlertCircle size={32} className="mb-2" />
          <p className="text-sm">{error.message}</p>
        </div>
      </div>
    );
  }

  // Empty state
  if (!trace && combinedNodes.length === 0) {
    return (
      <div
        data-testid="agent-trace-tab"
        className="flex flex-col h-full bg-neutral-1"
      >
        <div
          data-testid="agent-trace-empty"
          className="flex-1 flex flex-col items-center justify-center text-neutral-9"
        >
          <Activity size={32} className="mb-2 opacity-50" />
          <p className="text-sm">No trace data available</p>
          <p className="text-xs mt-1">Run an agent to see execution traces</p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="agent-trace-tab"
      className="flex flex-col h-full bg-neutral-1"
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-neutral-5 bg-neutral-1">
        {/* Session indicator */}
        <div className="flex items-center gap-1.5">
          <Activity size={14} className="text-neutral-10" aria-hidden="true" />
          <h3 className="text-xs text-neutral-11">Trace</h3>
          <span className="text-xs text-neutral-10 ml-1 px-1.5 py-0.5 bg-neutral-2 rounded">
            {sessionId}
          </span>
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Token counts */}
        {trace?.tokens && (
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1 text-neutral-10">
              <Zap size={12} className="text-primary-9" />
              <span data-testid="token-input">{trace.tokens.input}</span>
              <span className="text-neutral-9">in</span>
            </span>
            <span className="flex items-center gap-1 text-neutral-10">
              <span data-testid="token-output">{trace.tokens.output}</span>
              <span className="text-neutral-9">out</span>
            </span>
            <span className="flex items-center gap-1 text-neutral-10">
              <span data-testid="token-total">
                {trace.tokens.input + trace.tokens.output}
              </span>
              <span className="text-neutral-9">total</span>
            </span>
          </div>
        )}

        {/* View toggle */}
        <div data-testid="view-toggle" className="flex items-center gap-1">
          <Button
            variant="ghost"
            data-testid="view-list"
            type="button"
            onClick={() => setViewMode("list")}
            className={cn(
              "p-1 rounded",
              viewMode === "list"
                ? "bg-primary-3 bg-primary-4 text-primary-10"
                : "hover:bg-neutral-3 text-neutral-10",
            )}
            aria-label="List view"
            aria-pressed={viewMode === "list"}
          >
            <List size={14} />
          </Button>
          <Button
            variant="primary"
            data-testid="view-timeline"
            type="button"
            onClick={() => setViewMode("timeline")}
            className={cn(
              "p-1 rounded",
              viewMode === "timeline"
                ? "bg-primary-3 bg-primary-4 text-primary-10"
                : "hover:bg-neutral-3 text-neutral-10",
            )}
            aria-label="Timeline view"
            aria-pressed={viewMode === "timeline"}
          >
            <Activity size={14} />
          </Button>
        </div>

        {/* Refresh button */}
        <Button
          size="icon"
          variant="secondary"
          className="p-1 hover:bg-neutral-3 rounded text-neutral-10"
          data-testid="refresh-trace-button"
          type="button"
          onClick={refetch}
          aria-label="Refresh trace"
        >
          <RefreshCw size={14} />
        </Button>
      </div>
      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {viewMode === "list" ? (
          <div data-testid="trace-list-view">
            {filteredNodes.map((node) => (
              <div key={node.id}>
                <TraceNodeRow
                  node={node}
                  isSelected={selectedNodeId === node.id}
                  isExpanded={expandedNodes.has(node.id)}
                  onSelect={() => handleNodeSelect(node.id)}
                  onToggleExpand={() => toggleNodeExpand(node.id)}
                />
                {expandedNodes.has(node.id) && <NodeDetails node={node} />}
              </div>
            ))}
          </div>
        ) : (
          <div data-testid="trace-timeline-view" className="p-2">
            {filteredNodes.map((node, index) => (
              <TimelineNode
                key={node.id}
                node={node}
                totalDuration={totalDuration}
                startOffset={getStartOffset(index)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default AgentTraceTab;
