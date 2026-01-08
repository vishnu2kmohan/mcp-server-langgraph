/**
 * AggregatedCapabilitiesPanel Component
 *
 * Main panel for browsing all aggregated MCP capabilities.
 * Provides tabs for Tools, Resources, Prompts, and Servers.
 * Supports the MCP Protocol 2025-11-25 capability aggregation feature.
 */

import { useState, useCallback } from "react";
import {
  useListAggregatedServersQuery,
  useListAggregatedToolsQuery,
  useListAggregatedResourcesQuery,
  useListAggregatedPromptsQuery,
} from "../../api";
import { Card, CardHeader, CardTitle, CardContent } from "../UI/Card";
import { ToolExplorer } from "./ToolExplorer";
import { ResourceBrowser } from "./ResourceBrowser";
import { PromptLibrary } from "./PromptLibrary";
import { MCPServerCard } from "./MCPServerCard";
import { useMCPAggregatedUpdates } from "../../hooks";

export interface AggregatedCapabilitiesPanelProps {
  /** Whether to show admin-only actions (refresh all, etc.) */
  showAdminActions?: boolean;
  /** Callback when tool invoke is clicked */
  onToolInvoke?: (qualifiedName: string) => void;
  /** Callback when resource view is clicked */
  onResourceView?: (qualifiedName: string) => void;
  /** Callback when prompt test is clicked */
  onPromptTest?: (qualifiedName: string) => void;
  /** Callback when a server is selected */
  onServerSelect?: (serverName: string) => void;
}

type TabId = "tools" | "resources" | "prompts" | "servers";

/**
 * Utility to combine class names
 */
function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * Tab button component
 */
function TabButton({
  id,
  label,
  active,
  onClick,
}: {
  id: TabId;
  label: string;
  active: boolean;
  onClick: (id: TabId) => void;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={() => onClick(id)}
      className={cn(
        "px-4 py-2 text-sm font-medium rounded-t-lg transition-colors",
        "focus:outline-none focus:ring-2 focus:ring-brand-primary focus:ring-offset-2",
        active
          ? "bg-white dark:bg-gray-900 text-brand-primary border-b-2 border-brand-primary"
          : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200",
      )}
    >
      {label}
    </button>
  );
}

/**
 * Loading spinner component
 */
function LoadingSpinner() {
  return (
    <div
      className="flex items-center justify-center p-8"
      data-testid="loading-spinner"
    >
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary" />
    </div>
  );
}

/**
 * AggregatedCapabilitiesPanel - Main panel for browsing MCP capabilities
 */
export function AggregatedCapabilitiesPanel({
  showAdminActions = true,
  onToolInvoke,
  onResourceView,
  onPromptTest,
  onServerSelect,
}: AggregatedCapabilitiesPanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>("tools");
  const [serverFilter, setServerFilter] = useState<string | undefined>(
    undefined,
  );

  const {
    data: serversData,
    isLoading,
    error,
    refetch,
  } = useListAggregatedServersQuery();

  // Get refetch functions for each capability type
  const { refetch: refetchTools } = useListAggregatedToolsQuery(serverFilter);
  const { refetch: refetchResources } =
    useListAggregatedResourcesQuery(serverFilter);
  const { refetch: refetchPrompts } =
    useListAggregatedPromptsQuery(serverFilter);

  // WebSocket real-time updates - auto-refetch when capabilities change
  const handleToolsChanged = useCallback(() => {
    refetchTools();
    refetch(); // Also refresh server list to update counts
  }, [refetchTools, refetch]);

  const handleResourcesChanged = useCallback(() => {
    refetchResources();
    refetch();
  }, [refetchResources, refetch]);

  const handlePromptsChanged = useCallback(() => {
    refetchPrompts();
    refetch();
  }, [refetchPrompts, refetch]);

  // Connect to WebSocket for real-time capability updates
  const { status: wsStatus } = useMCPAggregatedUpdates({
    onToolsChanged: handleToolsChanged,
    onResourcesChanged: handleResourcesChanged,
    onPromptsChanged: handlePromptsChanged,
  });

  const handleTabChange = (tab: TabId) => {
    setActiveTab(tab);
  };

  const handleServerSelect = (serverName: string) => {
    setServerFilter(serverName);
    setActiveTab("tools"); // Switch to tools tab to show filtered tools
    onServerSelect?.(serverName);
  };

  const handleRefreshAll = () => {
    refetch();
  };

  const handleClearFilter = () => {
    setServerFilter(undefined);
  };

  if (isLoading) {
    return (
      <Card variant="elevated" padding="lg">
        <LoadingSpinner />
      </Card>
    );
  }

  if (error) {
    return (
      <Card variant="elevated" padding="lg">
        <div className="p-4 text-center">
          <p className="text-error-500 mb-4">
            Failed to load aggregated capabilities.
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className={cn(
              "px-4 py-2 text-sm font-medium rounded-md",
              "bg-brand-primary text-white",
              "hover:bg-brand-primary/90",
            )}
          >
            Retry
          </button>
        </div>
      </Card>
    );
  }

  const { totalServers, totalTools, totalResources, totalPrompts, servers } =
    serversData ?? {
      totalServers: 0,
      totalTools: 0,
      totalResources: 0,
      totalPrompts: 0,
      servers: [],
    };

  return (
    <Card variant="elevated" padding="none">
      {/* Header */}
      <CardHeader>
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-4">
            <CardTitle>Aggregated Capabilities</CardTitle>
            {/* Stats summary */}
            <div className="flex items-center gap-3 text-sm text-gray-600 dark:text-gray-400">
              <span>{totalServers} servers</span>
              <span className="text-gray-300 dark:text-gray-600 dark:text-gray-300">
                |
              </span>
              <span>{totalTools} tools</span>
              <span className="text-gray-300 dark:text-gray-600 dark:text-gray-300">
                |
              </span>
              <span>{totalResources} resources</span>
              <span className="text-gray-300 dark:text-gray-600 dark:text-gray-300">
                |
              </span>
              <span>{totalPrompts} prompts</span>
              <span className="text-gray-300 dark:text-gray-600 dark:text-gray-300">
                |
              </span>
              {/* Real-time sync indicator */}
              <span
                className="flex items-center gap-1"
                title={`Real-time updates: ${wsStatus}`}
              >
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    wsStatus === "connected" && "bg-success-500",
                    wsStatus === "connecting" && "bg-warning-500 animate-pulse",
                    wsStatus === "reconnecting" &&
                      "bg-warning-500 animate-pulse",
                    wsStatus === "disconnected" && "bg-gray-400",
                    wsStatus === "error" && "bg-error-500",
                  )}
                />
                <span className="text-xs">
                  {wsStatus === "connected" ? "Live" : wsStatus}
                </span>
              </span>
            </div>
          </div>
          {/* Admin actions */}
          {showAdminActions && (
            <button
              type="button"
              onClick={handleRefreshAll}
              className={cn(
                "px-3 py-1.5 text-sm font-medium rounded-md",
                "bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 dark:bg-gray-700 dark:text-gray-200",
                "hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600",
                "focus:outline-none focus:ring-2 focus:ring-brand-primary",
              )}
            >
              Refresh All
            </button>
          )}
        </div>
      </CardHeader>

      {/* Filter indicator */}
      {serverFilter && (
        <div className="px-4 py-2 bg-primary-50 dark:bg-primary-900/20 border-b border-primary-100 dark:border-primary-800 flex items-center justify-between">
          <span className="text-sm text-primary-700 dark:text-primary-300">
            Filtered by server: <strong>{serverFilter}</strong>
          </span>
          <button
            type="button"
            onClick={handleClearFilter}
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline"
          >
            Clear filter
          </button>
        </div>
      )}

      {/* Tabs */}
      <div
        className="border-b border-gray-200 dark:border-gray-700 px-4"
        role="tablist"
      >
        <div className="flex gap-2">
          <TabButton
            id="tools"
            label="Tools"
            active={activeTab === "tools"}
            onClick={handleTabChange}
          />
          <TabButton
            id="resources"
            label="Resources"
            active={activeTab === "resources"}
            onClick={handleTabChange}
          />
          <TabButton
            id="prompts"
            label="Prompts"
            active={activeTab === "prompts"}
            onClick={handleTabChange}
          />
          <TabButton
            id="servers"
            label="Servers"
            active={activeTab === "servers"}
            onClick={handleTabChange}
          />
        </div>
      </div>

      {/* Tab content */}
      <CardContent className="p-4">
        {activeTab === "tools" && (
          <ToolExplorer serverFilter={serverFilter} onInvoke={onToolInvoke} />
        )}
        {activeTab === "resources" && (
          <ResourceBrowser
            serverFilter={serverFilter}
            onView={onResourceView}
          />
        )}
        {activeTab === "prompts" && (
          <PromptLibrary serverFilter={serverFilter} onTest={onPromptTest} />
        )}
        {activeTab === "servers" && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {servers.map((server) => (
              <MCPServerCard
                key={server.serverName}
                serverName={server.serverName}
                toolCount={server.toolCount}
                resourceCount={server.resourceCount}
                promptCount={server.promptCount}
                onSelect={handleServerSelect}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
