/**
 * ConnectionsPage
 *
 * MCP Connections management page with:
 * - List view with status indicators
 * - Filtering by status and auth type
 * - Sorting by name, created_at, updated_at, status
 * - Search functionality (FTS)
 * - Add/Edit/Delete operations
 * - Connection testing
 * - Real-time status polling (configurable interval)
 */

import { useState, useCallback, useMemo, useRef, Suspense } from "react";
import {
  Plus,
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  RefreshCw,
  Pencil,
  Trash2,
  Zap,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Server,
  Key,
  Shield,
  Link,
  Pause,
  Play,
  FileText,
  LayoutTemplate,
} from "lucide-react";
import {
  useListConnectionsQuery,
  useTestConnectionMutation,
  useDeleteConnectionMutation,
} from "../api";
import {
  ConnectionDialog,
  ConnectionBulkActions,
  ConnectionTemplateSelector,
  ConnectionAuditLog,
} from "../components/Connection";
import {
  LazyAggregatedCapabilitiesPanel,
  LazyToolInvocationDialog,
  LazyResourceViewer,
  LazyPromptTester,
} from "../components/MCP";
import { useAppSelector } from "../store/hooks";
import { selectPersona } from "../store/slices/personaSlice";
import type {
  MCPConnectionSummary,
  MCPConnection,
  ConnectionStatus,
  AuthType,
  ConnectionSortField,
} from "../types/connection";
import {
  useKeyboardShortcuts,
  useShortcutDisplay,
  COMMON_SHORTCUTS,
} from "../hooks/useKeyboardShortcuts";
import { useConnectionsRealtimeWebSocket } from "../hooks/useConnectionsRealtimeWebSocket";

// Status badge colors
const statusColors: Record<ConnectionStatus, string> = {
  connected:
    "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
  disconnected: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
  connecting: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
  error: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
  auth_required:
    "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
};

// Auth type icons
const authIcons: Record<AuthType, React.ReactNode> = {
  none: <Link className="w-4 h-4" />,
  api_key: <Key className="w-4 h-4" />,
  oauth2: <Shield className="w-4 h-4" />,
};

// Status icons
const statusIcons: Record<ConnectionStatus, React.ReactNode> = {
  connected: <CheckCircle className="w-4 h-4 text-green-500" />,
  disconnected: <XCircle className="w-4 h-4 text-gray-400" />,
  connecting: <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />,
  error: <AlertCircle className="w-4 h-4 text-red-500" />,
  auth_required: <AlertCircle className="w-4 h-4 text-yellow-500" />,
};

// Polling interval options (in milliseconds)
const POLLING_INTERVALS = {
  off: 0,
  slow: 30000, // 30 seconds
  normal: 10000, // 10 seconds
  fast: 5000, // 5 seconds
} as const;

type PollingSpeed = keyof typeof POLLING_INTERVALS;

export function ConnectionsPage() {
  // Persona for admin-only actions
  const persona = useAppSelector(selectPersona);
  const isAdmin = persona === "admin";

  // Filter/sort state
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<ConnectionStatus | "">("");
  const [authTypeFilter, setAuthTypeFilter] = useState<AuthType | "">("");
  const [sortBy, setSortBy] = useState<ConnectionSortField>("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  // Polling state - default to normal (10 second) polling
  const [pollingSpeed, setPollingSpeed] = useState<PollingSpeed>("normal");
  const pollingInterval = useMemo(
    () => POLLING_INTERVALS[pollingSpeed],
    [pollingSpeed],
  );

  // Dialog state
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingConnection, setEditingConnection] = useState<
    MCPConnection | undefined
  >();
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  // Template selector state
  const [templateSelectorOpen, setTemplateSelectorOpen] = useState(false);

  // Audit log state
  const [auditLogConnectionId, setAuditLogConnectionId] = useState<
    string | null
  >(null);

  // Selection state for bulk operations
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Capability dialog states (Tool/Resource/Prompt)
  const [toolDialogOpen, setToolDialogOpen] = useState(false);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [resourceViewerOpen, setResourceViewerOpen] = useState(false);
  const [selectedResource, setSelectedResource] = useState<string | null>(null);
  const [promptTesterOpen, setPromptTesterOpen] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);

  // Refs for keyboard shortcuts
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Keyboard shortcut display formatting
  const { formatShortcut } = useShortcutDisplay();

  // RTK Query hooks with polling
  const { data, isLoading, isFetching, error, refetch } =
    useListConnectionsQuery(
      {
        search: search || undefined,
        status: statusFilter || undefined,
        auth_type: authTypeFilter || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: 50,
      },
      {
        // Enable polling when interval is > 0
        pollingInterval: pollingInterval > 0 ? pollingInterval : undefined,
        // Skip polling when the page is not visible
        refetchOnFocus: true,
        refetchOnReconnect: true,
      },
    );

  const [testConnection, { isLoading: isTesting }] =
    useTestConnectionMutation();
  const [deleteConnection, { isLoading: isDeleting }] =
    useDeleteConnectionMutation();

  // Real-time WebSocket connection for instant status updates
  const {
    status: wsStatus,
    connections: wsConnections,
    subscribeAll,
    requestHealthCheck: _requestHealthCheck,
    error: wsError,
  } = useConnectionsRealtimeWebSocket({
    onConnectionUpdate: (connection) => {
      // Real-time updates automatically merged via connections state
      console.debug(
        "[ConnectionsPage] WebSocket connection update:",
        connection.id,
        connection.status,
      );
    },
  });

  // Subscribe to all connection updates when WebSocket connects
  useMemo(() => {
    if (wsStatus === "connected") {
      subscribeAll();
    }
  }, [wsStatus, subscribeAll]);

  // Merge polling data with WebSocket updates for real-time status
  // WebSocket provides faster status updates while polling ensures data freshness
  const connections = useMemo(() => {
    const pollingConnections = data?.items ?? [];
    if (wsConnections.length === 0) {
      return pollingConnections;
    }
    // Merge: prefer WebSocket status but keep polling data structure
    const wsStatusMap = new Map(wsConnections.map((c) => [c.id, c.status]));
    return pollingConnections.map((conn) => ({
      ...conn,
      status: wsStatusMap.get(conn.id) ?? conn.status,
    }));
  }, [data?.items, wsConnections]);

  // Handlers
  const handleAddClick = useCallback(() => {
    setEditingConnection(undefined);
    setDialogOpen(true);
  }, []);

  const handleEditClick = useCallback((connection: MCPConnectionSummary) => {
    // For editing, we need full connection data - for now use summary
    setEditingConnection(connection as unknown as MCPConnection);
    setDialogOpen(true);
  }, []);

  const handleDeleteClick = useCallback((id: string) => {
    setDeleteConfirmId(id);
  }, []);

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteConfirmId) return;

    try {
      await deleteConnection(deleteConfirmId).unwrap();
      setDeleteConfirmId(null);
      refetch();
    } catch (err) {
      console.error("Failed to delete connection:", err);
    }
  }, [deleteConfirmId, deleteConnection, refetch]);

  const handleTestClick = useCallback(
    async (id: string) => {
      try {
        await testConnection(id).unwrap();
        refetch();
      } catch (err) {
        console.error("Failed to test connection:", err);
      }
    },
    [testConnection, refetch],
  );

  const handleDialogSuccess = useCallback(() => {
    refetch();
  }, [refetch]);

  const toggleSortOrder = useCallback(() => {
    setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
  }, []);

  // Selection handlers for bulk operations
  const handleSelectConnection = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    if (selectedIds.size === connections.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(connections.map((c) => c.id)));
    }
  }, [connections, selectedIds.size]);

  const handleClearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const handleBulkActionComplete = useCallback(() => {
    setSelectedIds(new Set());
    refetch();
  }, [refetch]);

  // Template selector handlers
  const handleTemplateSelect = useCallback((template: unknown) => {
    setTemplateSelectorOpen(false);
    // Open connection dialog pre-filled with template data
    setEditingConnection(template as unknown as MCPConnection);
    setDialogOpen(true);
  }, []);

  // Audit log handlers
  const handleViewAuditLog = useCallback((connectionId: string) => {
    setAuditLogConnectionId(connectionId);
  }, []);

  // Close all modals
  const handleCloseModals = useCallback(() => {
    setDialogOpen(false);
    setDeleteConfirmId(null);
    setTemplateSelectorOpen(false);
    setAuditLogConnectionId(null);
    // Close capability dialogs
    setToolDialogOpen(false);
    setSelectedTool(null);
    setResourceViewerOpen(false);
    setSelectedResource(null);
    setPromptTesterOpen(false);
    setSelectedPrompt(null);
  }, []);

  // Focus search input
  const handleFocusSearch = useCallback(() => {
    searchInputRef.current?.focus();
  }, []);

  // Delete selected connections
  const handleDeleteSelected = useCallback(async () => {
    if (selectedIds.size === 1) {
      // Single selection - show confirmation
      const [id] = Array.from(selectedIds);
      if (id) setDeleteConfirmId(id);
    }
    // For multiple selections, bulk actions bar handles it
  }, [selectedIds]);

  // Keyboard shortcuts
  useKeyboardShortcuts(
    {
      [COMMON_SHORTCUTS.NEW]: handleAddClick,
      [COMMON_SHORTCUTS.SEARCH]: handleFocusSearch,
      [COMMON_SHORTCUTS.CLOSE]: handleCloseModals,
      [COMMON_SHORTCUTS.DELETE]: handleDeleteSelected,
      [COMMON_SHORTCUTS.SELECT_ALL]: handleSelectAll,
      [COMMON_SHORTCUTS.REFRESH]: () => refetch(),
    },
    {
      // Disable shortcuts when any modal is open (except Escape to close)
      enabled: true,
      preventDefault: true,
    },
  );

  // Render loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <span className="ml-2 text-gray-600 dark:text-gray-400">
          Loading connections...
        </span>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-red-600 dark:text-red-400">
          Failed to fetch connections
        </p>
        <button
          onClick={() => refetch()}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Server className="w-8 h-8 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            MCP Connections
          </h1>
          {/* WebSocket status indicator */}
          <span
            data-testid="ws-status-indicator"
            aria-label={`Live sync: ${wsStatus}`}
            title={wsError ? `WebSocket: ${wsError}` : `WebSocket: ${wsStatus}`}
            className={`w-2.5 h-2.5 rounded-full ${
              wsStatus === "connected"
                ? "bg-green-500"
                : wsStatus === "connecting" || wsStatus === "reconnecting"
                  ? "bg-yellow-500 animate-pulse"
                  : "bg-gray-400"
            }`}
          />
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setTemplateSelectorOpen(true)}
            className="flex items-center gap-2 px-4 py-2 border border-blue-600 text-blue-600 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/20"
            aria-label="From Template"
          >
            <LayoutTemplate className="w-4 h-4" />
            From Template
          </button>
          <button
            onClick={handleAddClick}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
            aria-label="Add Connection"
            title={`Add Connection (${formatShortcut(COMMON_SHORTCUTS.NEW)})`}
          >
            <Plus className="w-4 h-4" />
            Add Connection
            <kbd className="ml-1 px-1.5 py-0.5 text-xs bg-blue-700 rounded">
              {formatShortcut(COMMON_SHORTCUTS.NEW)}
            </kbd>
          </button>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-wrap gap-4 mb-6">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            ref={searchInputRef}
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search connections... (${formatShortcut(COMMON_SHORTCUTS.SEARCH)})`}
            className="w-full pl-10 pr-4 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          />
        </div>

        {/* Status Filter */}
        <div>
          <label htmlFor="status-filter" className="sr-only">
            Status
          </label>
          <select
            id="status-filter"
            aria-label="Status"
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as ConnectionStatus | "")
            }
            className="px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          >
            <option value="">All Statuses</option>
            <option value="connected">Connected</option>
            <option value="disconnected">Disconnected</option>
            <option value="connecting">Connecting</option>
            <option value="error">Error</option>
            <option value="auth_required">Auth Required</option>
          </select>
        </div>

        {/* Auth Type Filter */}
        <div>
          <label htmlFor="auth-type-filter" className="sr-only">
            Auth Type
          </label>
          <select
            id="auth-type-filter"
            aria-label="Auth Type"
            value={authTypeFilter}
            onChange={(e) => setAuthTypeFilter(e.target.value as AuthType | "")}
            className="px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          >
            <option value="">All Auth Types</option>
            <option value="none">No Auth</option>
            <option value="api_key">API Key</option>
            <option value="oauth2">OAuth2</option>
          </select>
        </div>

        {/* Sort By */}
        <div>
          <label htmlFor="sort-by" className="sr-only">
            Sort By
          </label>
          <select
            id="sort-by"
            aria-label="Sort By"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as ConnectionSortField)}
            className="px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
          >
            <option value="created_at">Created</option>
            <option value="updated_at">Updated</option>
            <option value="name">Name</option>
            <option value="status">Status</option>
          </select>
        </div>

        {/* Sort Order Toggle */}
        <button
          onClick={toggleSortOrder}
          className="flex items-center gap-1 px-3 py-2 border rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 dark:border-gray-600"
          aria-label="Sort Order"
        >
          {sortOrder === "asc" ? (
            <ArrowUp className="w-4 h-4" />
          ) : (
            <ArrowDown className="w-4 h-4" />
          )}
          <ArrowUpDown className="w-4 h-4 text-gray-400" />
        </button>

        {/* Polling Control */}
        <div className="flex items-center gap-1 border rounded-md dark:border-gray-600">
          <button
            onClick={() =>
              setPollingSpeed(pollingSpeed === "off" ? "normal" : "off")
            }
            className={`p-2 rounded-l-md transition-colors ${
              pollingSpeed !== "off"
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                : "hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
            aria-label={
              pollingSpeed !== "off"
                ? "Pause auto-refresh"
                : "Enable auto-refresh"
            }
            title={
              pollingSpeed !== "off"
                ? "Pause auto-refresh"
                : "Enable auto-refresh"
            }
          >
            {pollingSpeed !== "off" ? (
              <Pause className="w-4 h-4" />
            ) : (
              <Play className="w-4 h-4" />
            )}
          </button>
          <select
            value={pollingSpeed}
            onChange={(e) => setPollingSpeed(e.target.value as PollingSpeed)}
            className="px-2 py-2 bg-transparent text-sm focus:outline-none dark:text-white"
            aria-label="Polling interval"
          >
            <option value="off">Off</option>
            <option value="slow">30s</option>
            <option value="normal">10s</option>
            <option value="fast">5s</option>
          </select>
        </div>

        {/* Refresh Button */}
        <button
          onClick={() => refetch()}
          className={`p-2 border rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 dark:border-gray-600 ${
            isFetching ? "animate-spin" : ""
          }`}
          aria-label="Refresh"
          title={`Refresh (${formatShortcut(COMMON_SHORTCUTS.REFRESH)})`}
          disabled={isFetching}
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Empty State */}
      {connections.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Server className="w-16 h-16 text-gray-300 dark:text-gray-600 mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            No Connections
          </h2>
          <p className="text-gray-500 dark:text-gray-400 mb-6">
            Add your first MCP server connection to get started.
          </p>
          <button
            onClick={handleAddClick}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            <Plus className="w-4 h-4" />
            Add Connection
          </button>
        </div>
      )}

      {/* Bulk Actions Bar */}
      <ConnectionBulkActions
        selectedIds={Array.from(selectedIds)}
        connections={connections.map((c) => ({
          id: c.id,
          name: c.name,
          status: c.status,
        }))}
        onActionComplete={handleBulkActionComplete}
        onClearSelection={handleClearSelection}
      />

      {/* Connection List */}
      {connections.length > 0 && (
        <div className="grid gap-4">
          {/* Select All Header */}
          <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg border dark:border-gray-700">
            <input
              type="checkbox"
              checked={
                selectedIds.size > 0 && selectedIds.size === connections.length
              }
              onChange={handleSelectAll}
              className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              aria-label="Select all connections"
            />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {selectedIds.size > 0
                ? `${selectedIds.size} selected`
                : `${connections.length} connections`}
            </span>
          </div>

          {connections.map((connection) => (
            <div
              key={connection.id}
              className={`bg-white dark:bg-gray-800 rounded-lg border dark:border-gray-700 p-4 hover:shadow-md transition-shadow ${
                selectedIds.has(connection.id) ? "ring-2 ring-blue-500" : ""
              }`}
            >
              <div className="flex items-start justify-between">
                {/* Selection Checkbox */}
                <div className="flex items-center mr-4">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(connection.id)}
                    onChange={() => handleSelectConnection(connection.id)}
                    className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                    aria-label={`Select ${connection.name}`}
                  />
                </div>

                {/* Connection Info */}
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    {/* Status Icon */}
                    {statusIcons[connection.status]}

                    {/* Name */}
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {connection.name}
                    </h3>

                    {/* Status Badge */}
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded-full ${statusColors[connection.status]}`}
                    >
                      {connection.status}
                    </span>

                    {/* Auth Type Badge */}
                    <span className="flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300">
                      {authIcons[connection.auth_type]}
                      {connection.auth_type}
                    </span>
                  </div>

                  {/* URL */}
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                    {connection.url}
                  </p>

                  {/* Stats (for connected servers) */}
                  {connection.status === "connected" && (
                    <div className="flex gap-4 text-sm text-gray-600 dark:text-gray-400">
                      <span>{connection.tool_count} tools</span>
                      <span>{connection.resource_count} resources</span>
                      <span>{connection.prompt_count} prompts</span>
                    </div>
                  )}

                  {/* Server info */}
                  {connection.server_name && (
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                      Server: {connection.server_name}
                    </p>
                  )}
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleTestClick(connection.id)}
                    className="p-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/50 rounded-md"
                    aria-label="Test"
                    disabled={isTesting}
                  >
                    <Zap className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleViewAuditLog(connection.id)}
                    className="p-2 text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-900/50 rounded-md"
                    aria-label="Audit Log"
                  >
                    <FileText className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleEditClick(connection)}
                    className="p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 rounded-md"
                    aria-label="Edit"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteClick(connection.id)}
                    className="p-2 text-red-600 hover:bg-red-50 dark:hover:bg-red-900/50 rounded-md"
                    aria-label="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Aggregated Capabilities Panel - Shows tools/resources/prompts from all connected servers */}
      {connections.length > 0 && (
        <div className="mt-8">
          <Suspense
            fallback={
              <div className="p-8 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-center gap-3 text-gray-500 dark:text-gray-400">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Loading capabilities...</span>
                </div>
              </div>
            }
          >
            <LazyAggregatedCapabilitiesPanel
              showAdminActions={isAdmin}
              onToolInvoke={(qualifiedName) => {
                setSelectedTool(qualifiedName);
                setToolDialogOpen(true);
              }}
              onResourceView={(qualifiedName) => {
                setSelectedResource(qualifiedName);
                setResourceViewerOpen(true);
              }}
              onPromptTest={(qualifiedName) => {
                setSelectedPrompt(qualifiedName);
                setPromptTesterOpen(true);
              }}
            />
          </Suspense>
        </div>
      )}

      {/* Connection Dialog */}
      <ConnectionDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSuccess={handleDialogSuccess}
        connection={editingConnection}
      />

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setDeleteConfirmId(null)}
          />
          <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              Delete Connection
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Are you sure you want to delete this connection? This action
              cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirmId(null)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                className="px-4 py-2 bg-red-600 text-white hover:bg-red-700 rounded-md"
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Template Selector Modal */}
      {templateSelectorOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setTemplateSelectorOpen(false)}
          />
          <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-4xl mx-4 max-h-[80vh] overflow-y-auto">
            <ConnectionTemplateSelector
              onSelect={handleTemplateSelect}
              onCustom={() => {
                setTemplateSelectorOpen(false);
                setDialogOpen(true);
              }}
              showCustomOption
            />
            <button
              onClick={() => setTemplateSelectorOpen(false)}
              className="absolute top-4 right-4 p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              aria-label="Close"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Audit Log Modal */}
      {auditLogConnectionId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setAuditLogConnectionId(null)}
          />
          <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-3xl mx-4 max-h-[80vh] overflow-y-auto">
            <ConnectionAuditLog connectionId={auditLogConnectionId} />
            <button
              onClick={() => setAuditLogConnectionId(null)}
              className="absolute top-4 right-4 p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
              aria-label="Close"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Tool Invocation Dialog */}
      <LazyToolInvocationDialog
        open={toolDialogOpen}
        onClose={() => {
          setToolDialogOpen(false);
          setSelectedTool(null);
        }}
        preselectedToolName={selectedTool ?? undefined}
      />

      {/* Resource Viewer Dialog */}
      <LazyResourceViewer
        open={resourceViewerOpen}
        onClose={() => {
          setResourceViewerOpen(false);
          setSelectedResource(null);
        }}
        preselectedResourceUri={selectedResource ?? undefined}
      />

      {/* Prompt Tester Dialog */}
      <LazyPromptTester
        open={promptTesterOpen}
        onClose={() => {
          setPromptTesterOpen(false);
          setSelectedPrompt(null);
        }}
        preselectedPromptName={selectedPrompt ?? undefined}
      />
    </div>
  );
}
