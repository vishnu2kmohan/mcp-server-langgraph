/**
 * MCPPage
 *
 * MCP (Model Context Protocol) explorer page showing tools,
 * resources, prompts, and server connections.
 */

import { useState, useCallback, Suspense } from "react";
import { useNavigate } from "react-router";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";
import {
  removeServer,
  clearMCPError,
  selectServerList,
  selectPrimaryServerId,
  selectIsConnecting,
  selectMCPError,
  selectAllTools,
  selectAllResources,
  selectAllPrompts,
  selectIsConnected,
} from "../store/slices/mcpSlice";
import {
  Wrench,
  FileText,
  MessageSquare,
  Server,
  RefreshCw,
  Search,
  ChevronDown,
  ChevronRight,
  Check,
  X,
  Plus,
  AlertCircle,
  Play,
  Eye,
  TestTube,
  UserCheck,
  Loader2,
} from "lucide-react";
import type {
  MCPTool,
  MCPResource,
  MCPPrompt,
  ServerEntry,
} from "../types/mcp";
import type { MCPConnectionCreate } from "../types/connection";
import {
  LazyAddConnectionDialog,
  LazyToolInvocationDialog,
  LazyResourceViewer,
  LazyPromptTester,
  LazyElicitationDialog,
  LazyAggregatedCapabilitiesPanel,
} from "../components/MCP";
import { selectPersona } from "../store/slices/personaSlice";
import { useMCPKeyboardShortcuts } from "../hooks";
import { useMCPWebSocket } from "../hooks/useMCPWebSocket";
import { useMCPTaskWebSocket } from "../hooks/useMCPTaskWebSocket";
import { Layers } from "lucide-react";

import { Button, Input } from "@/components/UI";

type MCPTab = "tools" | "resources" | "prompts" | "servers" | "aggregated";

export function MCPPage() {
  const navigate = useNavigate();

  // Auth failure handler for authenticatedFetch
  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  // Persona for admin-only actions in aggregated panel
  const persona = useAppSelector(selectPersona);
  const isAdmin = persona === "admin";

  const [activeTab, setActiveTab] = useState<MCPTab>("tools");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // MCP Action Dialog States
  const [isToolInvocationOpen, setIsToolInvocationOpen] = useState(false);
  const [isResourceViewerOpen, setIsResourceViewerOpen] = useState(false);
  const [isPromptTesterOpen, setIsPromptTesterOpen] = useState(false);
  const [isElicitationOpen, setIsElicitationOpen] = useState(false);

  // Pre-selected items from aggregated capabilities panel
  const [preselectedToolName, setPreselectedToolName] = useState<
    string | undefined
  >(undefined);
  const [preselectedResourceUri, setPreselectedResourceUri] = useState<
    string | undefined
  >(undefined);
  const [preselectedPromptName, setPreselectedPromptName] = useState<
    string | undefined
  >(undefined);

  /**
   * Extract item name from qualified name.
   * Format: "server_name:item_name" -> "item_name"
   */
  const extractItemName = (qualifiedName: string): string => {
    const colonIndex = qualifiedName.indexOf(":");
    return colonIndex >= 0
      ? qualifiedName.slice(colonIndex + 1)
      : qualifiedName;
  };

  // Close whichever MCP dialog is currently open
  const handleCloseActiveDialog = useCallback(() => {
    if (isToolInvocationOpen) setIsToolInvocationOpen(false);
    else if (isResourceViewerOpen) setIsResourceViewerOpen(false);
    else if (isPromptTesterOpen) setIsPromptTesterOpen(false);
    else if (isElicitationOpen) setIsElicitationOpen(false);
    else if (isAddDialogOpen) setIsAddDialogOpen(false);
  }, [
    isToolInvocationOpen,
    isResourceViewerOpen,
    isPromptTesterOpen,
    isElicitationOpen,
    isAddDialogOpen,
  ]);

  // Wire up keyboard shortcuts for MCP dialogs
  useMCPKeyboardShortcuts({
    onOpenToolDialog: useCallback(() => setIsToolInvocationOpen(true), []),
    onOpenResourceViewer: useCallback(() => setIsResourceViewerOpen(true), []),
    onOpenPromptTester: useCallback(() => setIsPromptTesterOpen(true), []),
    onCloseActiveDialog: handleCloseActiveDialog,
  });

  const dispatch = useAppDispatch();
  const serverList = useAppSelector(selectServerList);
  const primaryServerId = useAppSelector(selectPrimaryServerId);
  const isConnecting = useAppSelector(selectIsConnecting);
  const error = useAppSelector(selectMCPError);
  const tools = useAppSelector(selectAllTools);
  const resources = useAppSelector(selectAllResources);
  const prompts = useAppSelector(selectAllPrompts);
  const isConnected = useAppSelector(selectIsConnected);

  // MCP WebSocket for real-time protocol communication
  const {
    status: mcpWsStatus,
    isInitialized: mcpWsInitialized,
    serverInfo: mcpServerInfo,
    error: mcpWsError,
  } = useMCPWebSocket();

  // MCP Task WebSocket for monitoring background tasks
  const { tasks: mcpTasks } = useMCPTaskWebSocket();

  // Calculate running tasks for indicator
  const hasRunningTasks = mcpTasks.some(
    (t) => t.status === "running" || t.status === "pending",
  );

  const toggleExpanded = (id: string) => {
    const next = new Set(expandedItems);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    setExpandedItems(next);
  };

  const handleOpenAddDialog = useCallback(() => {
    setIsAddDialogOpen(true);
  }, []);

  const handleCloseAddDialog = useCallback(() => {
    setIsAddDialogOpen(false);
  }, []);

  const handleCreateConnection = useCallback(
    async (data: MCPConnectionCreate) => {
      setIsCreating(true);
      try {
        // Call the backend API to create the connection
        const response = await authenticatedFetch("/api/v1/connections", {
          method: "POST",
          body: JSON.stringify(data),
          onAuthFailure: handleAuthFailure,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }

        const connection = await response.json();

        // Test the connection after creation
        await authenticatedFetch(`/api/v1/connections/${connection.id}/test`, {
          method: "POST",
          onAuthFailure: handleAuthFailure,
        });

        // Close dialog on success
        setIsAddDialogOpen(false);

        // Reload page to show new connection (temporary until we have proper state management)
        window.location.reload();
      } catch (err) {
        console.error("Failed to create connection:", err);
        // Error will be shown in dialog
        throw err;
      } finally {
        setIsCreating(false);
      }
    },
    [handleAuthFailure],
  );

  const tabs = [
    { id: "tools" as const, label: "Tools", icon: Wrench, count: tools.length },
    {
      id: "resources" as const,
      label: "Resources",
      icon: FileText,
      count: resources.length,
    },
    {
      id: "prompts" as const,
      label: "Prompts",
      icon: MessageSquare,
      count: prompts.length,
    },
    {
      id: "servers" as const,
      label: "Servers",
      icon: Server,
      count: serverList.length,
    },
    {
      id: "aggregated" as const,
      label: "Aggregated",
      icon: Layers,
      count: undefined, // Count shown in panel header
    },
  ];

  const filteredTools = tools.filter(
    (t: MCPTool) =>
      t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description?.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const filteredResources = resources.filter(
    (r: MCPResource) =>
      r.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.uri?.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const filteredPrompts = prompts.filter(
    (p: MCPPrompt) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description?.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="h-screen flex flex-col bg-neutral-50 dark:bg-neutral-900">
      {/* Header */}
      <header className="px-6 py-4 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
              MCP Explorer
            </h1>
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Browse and test Model Context Protocol capabilities
            </p>
          </div>
          <div className="flex items-center gap-4">
            {/* Add Server Button - always visible for discoverability */}
            <Button
              variant="primary"
              className="flex px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
              onClick={handleOpenAddDialog}
              disabled={isConnecting}
              aria-label="Add MCP Server"
            >
              <Plus size={16} />
              <span className="hidden sm:inline">Add Server</span>
            </Button>

            {/* MCP Action Buttons */}
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                className="flex px-3 py-1.5 text-sm text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 hover:bg-neutral-100 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-700 rounded-md"
                onClick={() => setIsToolInvocationOpen(true)}
                aria-label="Invoke Tool"
              >
                <Play size={16} />
                <span className="hidden sm:inline">Invoke Tool</span>
              </Button>
              <Button
                variant="secondary"
                className="flex px-3 py-1.5 text-sm text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 hover:bg-neutral-100 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-700 rounded-md"
                onClick={() => setIsResourceViewerOpen(true)}
                aria-label="View Resources"
              >
                <Eye size={16} />
                <span className="hidden sm:inline">View Resources</span>
              </Button>
              <Button
                variant="secondary"
                className="flex px-3 py-1.5 text-sm text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 hover:bg-neutral-100 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-700 rounded-md"
                onClick={() => setIsPromptTesterOpen(true)}
                aria-label="Test Prompt"
              >
                <TestTube size={16} />
                <span className="hidden sm:inline">Test Prompt</span>
              </Button>
              <Button
                variant="secondary"
                className="flex px-3 py-1.5 text-sm text-neutral-600 dark:text-neutral-300 hover:text-neutral-900 hover:bg-neutral-100 dark:bg-neutral-800 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-700 rounded-md"
                onClick={() => setIsElicitationOpen(true)}
                aria-label="Request Input"
              >
                <UserCheck size={16} />
                <span className="hidden sm:inline">Request Input</span>
              </Button>
            </div>

            {/* Connection Status */}
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full ${
                  isConnected ? "bg-success-500" : "bg-error-500"
                }`}
              />
              <span className="text-sm text-neutral-600 dark:text-neutral-300">
                {isConnected ? "Connected" : "Disconnected"}
              </span>
            </div>

            {/* MCP WebSocket Status Indicator */}
            <span
              data-testid="mcp-ws-status-indicator"
              aria-label={`MCP live sync: ${mcpWsStatus}`}
              title={
                mcpWsInitialized && mcpServerInfo
                  ? `MCP Server: ${mcpServerInfo.name} v${mcpServerInfo.version}`
                  : mcpWsError
                    ? `MCP WebSocket: ${mcpWsError}`
                    : `MCP WebSocket: ${mcpWsStatus}`
              }
              className={`w-2.5 h-2.5 rounded-full ${
                mcpWsStatus === "connected"
                  ? "bg-success-500"
                  : mcpWsStatus === "connecting" ||
                      mcpWsStatus === "reconnecting"
                    ? "bg-warning-500 animate-pulse"
                    : "bg-neutral-400"
              }`}
            />

            {/* MCP Task Indicator - shown when tasks exist */}
            {mcpTasks.length > 0 && (
              <span
                data-testid="mcp-task-indicator"
                aria-label={`${mcpTasks.length} MCP task${mcpTasks.length === 1 ? "" : "s"}`}
                title={`${mcpTasks.length} MCP task${mcpTasks.length === 1 ? "" : "s"}${hasRunningTasks ? " (running)" : ""}`}
                className={`flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full ${
                  hasRunningTasks
                    ? "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400 animate-pulse"
                    : "bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400"
                }`}
              >
                {mcpTasks.length}
              </span>
            )}
          </div>
        </div>
      </header>
      {/* Tabs */}
      <div className="px-6 py-2 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <Button
              className="flex px-4 py-2 rounded-lg"
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
            >
              <tab.icon size={16} />
              {tab.label}
              {tab.count !== undefined && (
                <span
                  className={`px-2 py-0.5 text-xs rounded-full ${
                    activeTab === tab.id
                      ? "bg-primary-200 dark:bg-primary-800"
                      : "bg-neutral-200 dark:bg-neutral-700 dark:bg-neutral-600"
                  }`}
                >
                  {tab.count}
                </span>
              )}
            </Button>
          ))}
        </div>
      </div>
      {/* Search - hide for servers and aggregated tabs */}
      {activeTab !== "servers" && activeTab !== "aggregated" && (
        <div className="px-6 py-4 bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
          <div className="relative">
            <Search
              size={20}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 dark:text-neutral-400"
            />
            <Input
              className="pl-10 pr-4 py-2 text-neutral-900 dark:text-neutral-100"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={`Search ${activeTab}...`}
            />
          </div>
        </div>
      )}
      {/* Error */}
      {error && (
        <div
          role="alert"
          className="px-6 py-3 bg-error-50 dark:bg-error-900/20 border-b border-error-200 dark:border-error-800"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="text-error-500" />
              <p className="text-error-700 dark:text-error-400 text-sm">
                {error}
              </p>
            </div>
            <Button
              className="p-1 text-error-500 hover:text-error-700 dark:hover:text-error-300"
              onClick={() => dispatch(clearMCPError())}
              aria-label="Dismiss"
            >
              <X size={16} />
            </Button>
          </div>
        </div>
      )}
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isConnecting ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw size={32} className="animate-spin text-primary-500" />
          </div>
        ) : (
          <div className="space-y-4">
            {/* Tools Tab */}
            {activeTab === "tools" && (
              <>
                {filteredTools.length === 0 ? (
                  <p className="text-neutral-500 dark:text-neutral-400">
                    No tools found
                  </p>
                ) : (
                  filteredTools.map((tool: MCPTool) => (
                    <div
                      key={tool.name}
                      className="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
                    >
                      <Button
                        className="w-full p-4 flex justify-between text-left"
                        onClick={() => toggleExpanded(tool.name)}
                      >
                        <div className="flex items-center gap-3">
                          <Wrench size={20} className="text-primary-500" />
                          <div>
                            <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
                              {tool.name}
                            </h3>
                            <p className="text-sm text-neutral-500 dark:text-neutral-400">
                              {tool.description}
                            </p>
                          </div>
                        </div>
                        {expandedItems.has(tool.name) ? (
                          <ChevronDown
                            size={20}
                            className="text-neutral-400 dark:text-neutral-400"
                          />
                        ) : (
                          <ChevronRight
                            size={20}
                            className="text-neutral-400 dark:text-neutral-400"
                          />
                        )}
                      </Button>
                      {expandedItems.has(tool.name) && (
                        <div className="px-4 pb-4 border-t border-neutral-100 dark:border-neutral-700 mt-2 pt-4">
                          <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                            Parameters
                          </h4>
                          <pre className="text-xs bg-neutral-50 dark:bg-neutral-900 p-3 rounded overflow-x-auto">
                            {JSON.stringify(tool.inputSchema, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </>
            )}

            {/* Resources Tab */}
            {activeTab === "resources" && (
              <>
                {filteredResources.length === 0 ? (
                  <p className="text-neutral-500 dark:text-neutral-400">
                    No resources found
                  </p>
                ) : (
                  filteredResources.map(
                    (resource: MCPResource, idx: number) => (
                      <div
                        key={resource.uri || idx}
                        className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
                      >
                        <div className="flex items-center gap-3">
                          <FileText size={20} className="text-success-500" />
                          <div>
                            <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
                              {resource.name}
                            </h3>
                            <p className="text-sm text-neutral-500 dark:text-neutral-400 font-mono">
                              {resource.uri}
                            </p>
                          </div>
                        </div>
                      </div>
                    ),
                  )
                )}
              </>
            )}

            {/* Prompts Tab */}
            {activeTab === "prompts" && (
              <>
                {filteredPrompts.length === 0 ? (
                  <p className="text-neutral-500 dark:text-neutral-400">
                    No prompts found
                  </p>
                ) : (
                  filteredPrompts.map((prompt: MCPPrompt) => (
                    <div
                      key={prompt.name}
                      className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
                    >
                      <div className="flex items-center gap-3">
                        <MessageSquare size={20} className="text-insight-500" />
                        <div>
                          <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
                            {prompt.name}
                          </h3>
                          <p className="text-sm text-neutral-500 dark:text-neutral-400">
                            {prompt.description}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </>
            )}

            {/* Servers Tab */}
            {activeTab === "servers" && (
              <>
                {/* Add Server Button */}
                <div className="mb-4">
                  <Button
                    variant="primary"
                    className="flex px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                    onClick={handleOpenAddDialog}
                    disabled={isConnecting}
                  >
                    <Plus size={16} />
                    Add MCP Connection
                  </Button>
                </div>

                {serverList.length === 0 ? (
                  <p className="text-neutral-500 dark:text-neutral-400">
                    No servers configured
                  </p>
                ) : (
                  serverList.map((server: ServerEntry) => (
                    <div
                      key={server.id}
                      className="p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Server
                            size={20}
                            className="text-neutral-500 dark:text-neutral-400"
                          />
                          <div>
                            <h3 className="font-medium text-neutral-900 dark:text-neutral-100">
                              {server.id}
                              {server.id === primaryServerId && (
                                <span className="ml-2 text-xs text-primary-600">
                                  (Primary)
                                </span>
                              )}
                            </h3>
                            <p className="text-sm text-neutral-500 dark:text-neutral-400 font-mono">
                              {server.url}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {server.status === "connected" ? (
                            <span className="flex items-center gap-1 text-success-600">
                              <Check size={16} />
                              Connected
                            </span>
                          ) : server.status === "error" ? (
                            <span className="flex items-center gap-1 text-error-600">
                              <X size={16} />
                              Error
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-warning-600">
                              <RefreshCw size={16} className="animate-spin" />
                              Connecting
                            </span>
                          )}
                          <Button
                            className="p-2 text-neutral-400 dark:text-neutral-400 hover:text-error-500"
                            onClick={() => dispatch(removeServer(server.id))}
                          >
                            <X size={16} />
                          </Button>
                        </div>
                      </div>
                      {server.error && (
                        <p className="mt-2 text-sm text-error-600">
                          {server.error}
                        </p>
                      )}
                    </div>
                  ))
                )}
              </>
            )}

            {/* Aggregated Tab - Shows capabilities from all external MCP connections */}
            {activeTab === "aggregated" && (
              <Suspense
                fallback={
                  <div className="p-8 flex items-center justify-center">
                    <Loader2 className="w-5 h-5 animate-spin text-primary-500 mr-2" />
                    <span className="text-neutral-500 dark:text-neutral-400">
                      Loading capabilities...
                    </span>
                  </div>
                }
              >
                <LazyAggregatedCapabilitiesPanel
                  showAdminActions={isAdmin}
                  onToolInvoke={(qualifiedName) => {
                    const toolName = extractItemName(qualifiedName);
                    setPreselectedToolName(toolName);
                    setIsToolInvocationOpen(true);
                  }}
                  onResourceView={(qualifiedName) => {
                    // For resources, use the URI which is the qualified_name
                    // but the dialogs use simple URIs, so extract the name part
                    const resourceName = extractItemName(qualifiedName);
                    setPreselectedResourceUri(resourceName);
                    setIsResourceViewerOpen(true);
                  }}
                  onPromptTest={(qualifiedName) => {
                    const promptName = extractItemName(qualifiedName);
                    setPreselectedPromptName(promptName);
                    setIsPromptTesterOpen(true);
                  }}
                />
              </Suspense>
            )}
          </div>
        )}
      </div>
      {/* Add Connection Dialog */}
      <Suspense
        fallback={
          <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-50">
            <div className="bg-white dark:bg-neutral-800 p-6 rounded-lg shadow-xl flex items-center gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
              <span className="text-neutral-700 dark:text-neutral-300">
                Loading...
              </span>
            </div>
          </div>
        }
      >
        <LazyAddConnectionDialog
          isOpen={isAddDialogOpen}
          onClose={handleCloseAddDialog}
          onSubmit={handleCreateConnection}
          isLoading={isCreating}
        />
      </Suspense>
      {/* MCP Action Dialogs - Lazy loaded for bundle optimization */}
      <Suspense
        fallback={
          <div className="fixed inset-0 flex items-center justify-center bg-black/50 z-50">
            <div className="bg-white dark:bg-neutral-800 p-6 rounded-lg shadow-xl flex items-center gap-3">
              <Loader2 className="w-5 h-5 animate-spin text-primary-500" />
              <span className="text-neutral-700 dark:text-neutral-300">
                Loading...
              </span>
            </div>
          </div>
        }
      >
        {isToolInvocationOpen && (
          <LazyToolInvocationDialog
            open={isToolInvocationOpen}
            onClose={() => {
              setIsToolInvocationOpen(false);
              setPreselectedToolName(undefined);
            }}
            preselectedToolName={preselectedToolName}
          />
        )}
        {isResourceViewerOpen && (
          <LazyResourceViewer
            open={isResourceViewerOpen}
            onClose={() => {
              setIsResourceViewerOpen(false);
              setPreselectedResourceUri(undefined);
            }}
            preselectedResourceUri={preselectedResourceUri}
          />
        )}
        {isPromptTesterOpen && (
          <LazyPromptTester
            open={isPromptTesterOpen}
            onClose={() => {
              setIsPromptTesterOpen(false);
              setPreselectedPromptName(undefined);
            }}
            preselectedPromptName={preselectedPromptName}
          />
        )}
        {isElicitationOpen && (
          <LazyElicitationDialog
            open={isElicitationOpen}
            onClose={() => setIsElicitationOpen(false)}
          />
        )}
      </Suspense>
    </div>
  );
}

export default MCPPage;
