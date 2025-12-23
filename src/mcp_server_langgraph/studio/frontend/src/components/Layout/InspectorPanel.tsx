/**
 * InspectorPanel Component
 *
 * @deprecated This component functionality is available in DevTools StateTab.
 * The StateTab provides enhanced functionality including:
 * - Redux state tree inspection with search
 * - Context-aware state filtering (session, workflow, global)
 * - Expand/collapse tree navigation
 * - Path display for state properties
 *
 * Migration: Use DevTools panel (Cmd+Shift+I) State tab instead.
 * See: components/DevTools/CONSOLIDATION.md for migration guide.
 *
 * Displays MCP server details and tool information.
 * Used in the BottomPanel's Inspector tab.
 *
 * Features:
 * - Lists connected MCP servers
 * - Shows server status with visual indicators
 * - Displays available tools per server
 * - Supports server selection/highlighting
 */

import { useAppSelector } from "../../store/hooks";
import { selectServers } from "../../store/slices/mcpSlice";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface InspectorPanelProps {
  /** ID of selected server to highlight */
  selectedServerId?: string;
  /** Compact mode with reduced spacing */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Status Badge Component
// =============================================================================

interface StatusBadgeProps {
  status: "connected" | "connecting" | "disconnected" | "error";
}

function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "text-xs px-2 py-0.5 rounded-full",
        status === "connected" &&
          "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
        status === "connecting" &&
          "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400",
        status === "error" &&
          "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
        status === "disconnected" &&
          "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
      )}
    >
      {status}
    </span>
  );
}

// =============================================================================
// Server Card Component
// =============================================================================

interface ServerCardProps {
  id: string;
  status: "connected" | "connecting" | "disconnected" | "error";
  tools: Array<{ name: string; description?: string }>;
  isSelected?: boolean;
  compact?: boolean;
}

function ServerCard({
  id,
  status,
  tools,
  isSelected,
  compact,
}: ServerCardProps) {
  return (
    <div
      data-testid={`server-card-${id}`}
      className={cn(
        "border border-gray-200 dark:border-gray-700 rounded-md",
        compact ? "p-2" : "p-3",
        isSelected && "ring-2 ring-primary-500",
      )}
    >
      <div className="flex items-center justify-between mb-2">
        <span
          className={cn(
            "font-medium text-gray-700 dark:text-gray-200",
            compact ? "text-xs" : "text-sm",
          )}
        >
          {id}
        </span>
        <StatusBadge status={status} />
      </div>
      {tools.length > 0 && (
        <div className="mt-2">
          <p
            className={cn(
              "font-medium text-gray-500 dark:text-gray-400 mb-1",
              compact ? "text-[10px]" : "text-xs",
            )}
          >
            Tools
          </p>
          <div className="flex flex-wrap gap-1">
            {tools.map((tool) => (
              <span
                key={tool.name}
                title={tool.description}
                className={cn(
                  "px-2 py-0.5 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded",
                  compact ? "text-[10px]" : "text-xs",
                )}
              >
                {tool.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function InspectorPanel({
  selectedServerId,
  compact = false,
  className,
}: InspectorPanelProps) {
  const servers = useAppSelector(selectServers);
  const serverList = Object.values(servers);

  return (
    <div
      data-testid="inspector-panel"
      className={cn(
        "text-sm text-gray-500 dark:text-gray-400",
        compact ? "p-2" : "p-4",
        className,
      )}
    >
      {serverList.length === 0 ? (
        <p>Select an MCP tool or resource to inspect</p>
      ) : (
        <div className={cn("space-y-3", compact && "space-y-2")}>
          {serverList.map((server) => (
            <ServerCard
              key={server.id}
              id={server.id}
              status={server.status}
              tools={server.tools}
              isSelected={server.id === selectedServerId}
              compact={compact}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default InspectorPanel;
