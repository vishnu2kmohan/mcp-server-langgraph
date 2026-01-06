/**
 * ProjectDetailPage
 *
 * Unified workspace view for a single project.
 * Shows sessions, workflows, connections, observability, and cost
 * all in one place - implementing the Unified Workspace Paradigm.
 */

import { useState, useMemo } from "react";
import { useParams, useNavigate } from "react-router";
import {
  useGetFeatureFlagsQuery,
  useGetProjectQuery,
  useGetProjectObservabilityQuery,
  useGetProjectLogsQuery,
  useGetProjectAlertsQuery,
  useGetProjectCostSummaryQuery,
  useGetProjectCostByModelQuery,
  useAddProjectMemberMutation,
  useRemoveProjectMemberMutation,
  useAddProjectConnectionMutation,
} from "../api";
import {
  ArrowLeft,
  RefreshCw,
  MessageSquare,
  GitBranch,
  Plug,
  Activity,
  DollarSign,
  Settings,
  Plus,
  Users,
  X,
  Trash2,
} from "lucide-react";
import { SessionsTab } from "../components/Project/SessionsTab";
import { WorkflowsTab } from "../components/Project/WorkflowsTab";

// ============================================================================
// Dialog Components
// ============================================================================

interface DialogProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

function Dialog({ isOpen, onClose, title, children }: DialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            {title}
          </h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

interface AddConnectionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (name: string, type: string) => Promise<void>;
}

function AddConnectionDialog({
  isOpen,
  onClose,
  onSubmit,
}: AddConnectionDialogProps) {
  const [name, setName] = useState("");
  const [type, setType] = useState("mcp_server");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    try {
      await onSubmit(name.trim(), type);
      setName("");
      setType("mcp_server");
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title="Add New Connection">
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label
            htmlFor="connection-name"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Connection Name
          </label>
          <input
            id="connection-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter connection name"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            autoFocus
          />
        </div>
        <div className="mb-4">
          <label
            htmlFor="connection-type"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Connection Type
          </label>
          <select
            id="connection-type"
            value={type}
            onChange={(e) => setType(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="mcp_server">MCP Server</option>
            <option value="vector_store">Vector Store</option>
            <option value="api_key">API Key</option>
          </select>
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!name.trim() || isSubmitting}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isSubmitting ? "Adding..." : "Add"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

interface AddMemberDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (userId: string, role: string) => Promise<void>;
}

function AddMemberDialog({ isOpen, onClose, onSubmit }: AddMemberDialogProps) {
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState("viewer");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userId.trim()) return;
    setIsSubmitting(true);
    try {
      await onSubmit(userId.trim(), role);
      setUserId("");
      setRole("viewer");
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title="Add Team Member">
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label
            htmlFor="user-id"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            User ID
          </label>
          <input
            id="user-id"
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Enter user ID"
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            autoFocus
          />
        </div>
        <div className="mb-4">
          <label
            htmlFor="member-role"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Role
          </label>
          <select
            id="member-role"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="editor">Editor</option>
            <option value="viewer">Viewer</option>
            <option value="executor">Executor</option>
          </select>
        </div>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!userId.trim() || isSubmitting}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {isSubmitting ? "Adding..." : "Add"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

interface ConnectionRef {
  id: string;
  type: string;
  name: string;
  status: string;
}

interface ProjectMember {
  userId: string;
  role: string;
  addedAt: string;
}

type TabType =
  | "sessions"
  | "workflows"
  | "connections"
  | "observability"
  | "cost"
  | "members";

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { data: featureFlags } = useGetFeatureFlagsQuery();

  // RTK Query for project loading
  const {
    data: project,
    isLoading,
    isFetching,
    error: queryError,
    refetch,
  } = useGetProjectQuery(projectId ?? "", {
    skip: !projectId,
    // Poll every 30 seconds for near-real-time updates
    // This keeps project members, connections, and sessions fresh
    pollingInterval: 30000,
  });

  // Convert RTK Query error to string for display
  const error = queryError
    ? "status" in queryError
      ? `Error: ${(queryError as { status: number; data?: unknown }).status}`
      : (queryError as { message?: string }).message || "Failed to load project"
    : null;

  const [activeTab, setActiveTab] = useState<TabType>("sessions");

  const handleBack = () => {
    navigate("/studio/projects");
  };

  // All possible tabs with feature flag requirements (using snake_case for RTK Query)
  const allTabs: {
    id: TabType;
    label: string;
    icon: React.ReactNode;
    count?: number;
    featureFlag?: keyof NonNullable<typeof featureFlags>;
  }[] = [
    {
      id: "sessions",
      label: "Sessions",
      icon: <MessageSquare className="w-4 h-4" />,
      count: project?.sessionCount,
    },
    {
      id: "workflows",
      label: "Workflows",
      icon: <GitBranch className="w-4 h-4" />,
      count: project?.workflowCount,
      featureFlag: "enable_workflows_feature",
    },
    {
      id: "connections",
      label: "Connections",
      icon: <Plug className="w-4 h-4" />,
      count: project?.connectionCount,
    },
    {
      id: "observability",
      label: "Observability",
      icon: <Activity className="w-4 h-4" />,
      featureFlag: "enable_observability_ui",
    },
    {
      id: "cost",
      label: "Cost",
      icon: <DollarSign className="w-4 h-4" />,
      featureFlag: "enable_cost_dashboard",
    },
    {
      id: "members",
      label: "Members",
      icon: <Users className="w-4 h-4" />,
      count: project?.members.length,
    },
  ];

  // Filter tabs based on feature flags
  const tabs = useMemo(() => {
    return allTabs.filter((tab) => {
      if (!tab.featureFlag) return true; // No feature flag required
      if (!featureFlags) return true; // Default to showing if flags not loaded
      return featureFlags[tab.featureFlag] !== false; // Default to showing if not explicitly false
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    featureFlags,
    project?.sessionCount,
    project?.workflowCount,
    project?.connectionCount,
    project?.members?.length,
  ]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <RefreshCw className="w-5 h-5 animate-spin" />
          <span>Loading project...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !project) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4">
        <div className="text-red-500 dark:text-red-400">
          Error: {error || "Project not found"}
        </div>
        <button
          onClick={handleBack}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Back to Projects
        </button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-4">
          <button
            onClick={handleBack}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex-1">
            <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
              {project.name}
            </h1>
            {project.description && (
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {project.description}
              </p>
            )}
          </div>
          <button
            onClick={() => refetch()}
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            title={isFetching ? "Syncing..." : "Refresh (auto-syncs every 30s)"}
            data-testid="project-refresh-button"
          >
            <RefreshCw
              className={`w-5 h-5 ${isFetching ? "animate-spin" : ""}`}
            />
          </button>
          <button
            className="p-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            title="Settings"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="px-6 border-b border-gray-200 dark:border-gray-700">
        <div className="flex gap-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? "border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400"
                  : "border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
              }`}
            >
              {tab.icon}
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className="px-1.5 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 rounded">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "sessions" && (
          <SessionsTab
            sessions={project.sessions}
            projectId={project.id}
            onRefresh={() => refetch()}
          />
        )}
        {activeTab === "workflows" && (
          <WorkflowsTab
            workflows={project.workflows}
            projectId={project.id}
            onRefresh={() => refetch()}
          />
        )}
        {activeTab === "connections" && (
          <ConnectionsTab
            connections={project.connections}
            projectId={project.id}
            onRefresh={() => refetch()}
          />
        )}
        {activeTab === "observability" && (
          <ObservabilityTab projectId={project.id} />
        )}
        {activeTab === "cost" && <CostTab projectId={project.id} />}
        {activeTab === "members" && (
          <MembersTab
            members={project.members}
            projectId={project.id}
            onRefresh={() => refetch()}
          />
        )}
      </div>
    </div>
  );
}

// Tab Components - SessionsTab and WorkflowsTab imported from ../components/Project/

function ConnectionsTab({
  connections,
  projectId,
  onRefresh,
}: {
  connections: ConnectionRef[];
  projectId: string;
  onRefresh: () => void;
}) {
  const [showDialog, setShowDialog] = useState(false);

  // RTK Query mutation for adding connections
  const [addConnection] = useAddProjectConnectionMutation();

  const handleAddConnection = async (name: string, type: string) => {
    const connectionId = crypto.randomUUID();
    try {
      await addConnection({
        project_id: projectId,
        connection_type: type,
        connection_id: connectionId,
        connection_name: name,
      }).unwrap();
      onRefresh();
    } catch {
      // Error handled by RTK Query
    }
  };

  return (
    <div>
      <AddConnectionDialog
        isOpen={showDialog}
        onClose={() => setShowDialog(false)}
        onSubmit={handleAddConnection}
      />
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">
          Connections
        </h2>
        <button
          onClick={() => setShowDialog(true)}
          className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          Add Connection
        </button>
      </div>
      {connections.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No connections yet. Add MCP servers, vector stores, or API
          integrations.
        </div>
      ) : (
        <div className="space-y-2">
          {connections.map((connection) => (
            <div
              key={connection.id}
              className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
            >
              <div>
                <div className="font-medium text-gray-900 dark:text-gray-100">
                  {connection.name}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {connection.type}
                </div>
              </div>
              <span
                className={`px-2 py-0.5 text-xs rounded-full ${
                  connection.status === "active"
                    ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                }`}
              >
                {connection.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ObservabilityTab({ projectId }: { projectId: string }) {
  // RTK Query hooks for project-scoped observability data
  const {
    data: observabilityData,
    isLoading: isLoadingObservability,
    error: observabilityError,
    refetch: refetchObservability,
  } = useGetProjectObservabilityQuery(projectId);

  const { data: logsData, isLoading: isLoadingLogs } =
    useGetProjectLogsQuery(projectId);

  const { data: alertsData, isLoading: isLoadingAlerts } =
    useGetProjectAlertsQuery(projectId);

  const isLoading = isLoadingObservability || isLoadingLogs || isLoadingAlerts;
  const logs = logsData?.logs || [];
  const alerts = alertsData?.alerts || [];
  const data = observabilityData;

  // Convert RTK Query error to string
  const error = observabilityError
    ? "status" in observabilityError
      ? `Error: ${(observabilityError as { status: number }).status}`
      : "Failed to load observability data"
    : null;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-500 dark:text-gray-400">
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <div className="text-red-500 dark:text-red-400">{error}</div>
        <button
          onClick={() => refetchObservability()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Total Traces
          </h3>
          <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            {data?.traceCount ?? 0}
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Total Requests
          </h3>
          <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            {data?.requestsTotal ?? 0}
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Total Errors
          </h3>
          <div className="text-2xl font-semibold text-red-600 dark:text-red-400">
            {data?.errorsTotal ?? 0}
          </div>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Avg Latency
          </h3>
          <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            {data?.avgLatencyMs ?? 0}ms
          </div>
        </div>
      </div>

      {/* Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
            Traces
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            View traces from sessions and workflows in this project.
          </p>
          <a
            href={`/studio/observability?project=${projectId}`}
            className="text-blue-600 dark:text-blue-400 text-sm hover:underline"
          >
            View traces →
          </a>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
            Metrics
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            View aggregated metrics for this project.
          </p>
          <a
            href={`/studio/observability?project=${projectId}&tab=metrics`}
            className="text-blue-600 dark:text-blue-400 text-sm hover:underline"
          >
            View metrics →
          </a>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
            Logs
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            View logs from sessions and workflows.
          </p>
          <a
            href={`/studio/observability?project=${projectId}&tab=logs`}
            className="text-blue-600 dark:text-blue-400 text-sm hover:underline"
          >
            View logs →
          </a>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="font-medium text-gray-900 dark:text-gray-100 mb-2">
            Alerts
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
            View active alerts for this project.
          </p>
          <a
            href={`/studio/observability?project=${projectId}&tab=alerts`}
            className="text-blue-600 dark:text-blue-400 text-sm hover:underline"
          >
            View alerts →
          </a>
        </div>
      </div>

      {/* Recent Logs */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h3 className="font-medium text-gray-900 dark:text-gray-100">
            Recent Logs
          </h3>
          <a
            href={`/studio/observability?project=${projectId}&tab=logs`}
            className="text-blue-600 dark:text-blue-400 text-sm hover:underline"
          >
            View all →
          </a>
        </div>
        <div className="p-4">
          {logs.length === 0 ? (
            <div className="text-center py-4 text-gray-500 dark:text-gray-400">
              No logs available
            </div>
          ) : (
            <div className="space-y-2">
              {logs.slice(0, 10).map((log) => (
                <div
                  key={log.id}
                  className="flex items-start gap-3 p-2 bg-gray-50 dark:bg-gray-900 rounded text-sm"
                >
                  <span
                    className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                      log.level === "error"
                        ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                        : log.level === "warn"
                          ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                          : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                    }`}
                  >
                    {log.level}
                  </span>
                  <span className="text-gray-500 dark:text-gray-400 whitespace-nowrap text-xs">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  <span className="text-gray-900 dark:text-gray-100 flex-1">
                    {log.message}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Active Alerts */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
          <h3 className="font-medium text-gray-900 dark:text-gray-100">
            Active Alerts
          </h3>
          <a
            href={`/studio/observability?project=${projectId}&tab=alerts`}
            className="text-blue-600 dark:text-blue-400 text-sm hover:underline"
          >
            View all →
          </a>
        </div>
        <div className="p-4">
          {alerts.length === 0 ? (
            <div className="text-center py-4 text-gray-500 dark:text-gray-400">
              No active alerts
            </div>
          ) : (
            <div className="space-y-2">
              {alerts.slice(0, 5).map((alert) => (
                <div
                  key={alert.id}
                  className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-900 rounded border-l-4 border-l-red-500"
                >
                  <span
                    className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                      alert.severity === "critical"
                        ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                        : alert.severity === "warning"
                          ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                          : "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                    }`}
                  >
                    {alert.severity}
                  </span>
                  <div className="flex-1">
                    <div className="text-gray-900 dark:text-gray-100 text-sm">
                      {alert.message}
                    </div>
                    <div className="text-gray-500 dark:text-gray-400 text-xs mt-1">
                      {new Date(alert.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CostTab({ projectId }: { projectId: string }) {
  // RTK Query hooks for project-scoped cost data
  const {
    data: costSummary,
    isLoading: isLoadingSummary,
    error: costError,
    refetch: refetchCost,
  } = useGetProjectCostSummaryQuery(projectId);

  const { data: modelCosts, isLoading: isLoadingModels } =
    useGetProjectCostByModelQuery(projectId);

  const isLoading = isLoadingSummary || isLoadingModels;
  const data = costSummary;

  // Convert RTK Query error to string
  const error = costError
    ? "status" in costError
      ? `Error: ${(costError as { status: number }).status}`
      : "Failed to load cost data"
    : null;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-500 dark:text-gray-400">
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-4">
        <div className="text-red-500 dark:text-red-400">{error}</div>
        <button
          onClick={() => refetchCost()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Retry
        </button>
      </div>
    );
  }

  const totalTokens =
    (data?.prompt_tokens || 0) + (data?.completion_tokens || 0);
  const formattedCost = `$${(data?.total_cost || 0).toFixed(2)}`;
  const formattedTokens = totalTokens.toLocaleString();

  const formatCurrency = (amount: number): string => `$${amount.toFixed(2)}`;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Total Cost
          </h3>
          <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            {formattedCost}
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            This month
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Total Tokens
          </h3>
          <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            {formattedTokens}
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            Prompt + Completion
          </p>
        </div>
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">
            Sessions
          </h3>
          <div className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
            {data?.session_count || 0}
          </div>
          <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
            Active this month
          </p>
        </div>
      </div>

      {/* Cost by Model */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
            Cost by Model
          </h3>
        </div>
        <div className="p-4">
          {(modelCosts || []).length === 0 ? (
            <div className="text-center py-4 text-gray-500 dark:text-gray-400">
              No model data available
            </div>
          ) : (
            <div className="space-y-2">
              {(modelCosts || []).map((model) => (
                <div
                  key={model.model}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded-lg"
                >
                  <div>
                    <div className="font-medium text-gray-900 dark:text-gray-100">
                      {model.model}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {model.tokens.toLocaleString()} tokens
                    </div>
                  </div>
                  <div className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                    {formatCurrency(model.cost)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Link to detailed breakdown */}
      <div>
        <a
          href={`/studio/cost?project=${projectId}`}
          className="text-blue-600 dark:text-blue-400 text-sm hover:underline"
        >
          View detailed cost breakdown →
        </a>
      </div>
    </div>
  );
}

function MembersTab({
  members,
  projectId,
  onRefresh,
}: {
  members: ProjectMember[];
  projectId: string;
  onRefresh: () => void;
}) {
  const [showDialog, setShowDialog] = useState(false);

  // RTK Query mutations for project members
  const [addMember] = useAddProjectMemberMutation();
  const [removeMember] = useRemoveProjectMemberMutation();

  const handleAddMember = async (userId: string, role: string) => {
    try {
      await addMember({
        project_id: projectId,
        user_id: userId,
        role,
      }).unwrap();
      onRefresh();
    } catch {
      // Error handled by RTK Query
    }
  };

  const handleRemoveMember = async (userId: string) => {
    try {
      await removeMember({
        project_id: projectId,
        user_id: userId,
      }).unwrap();
      onRefresh();
    } catch {
      // Error handled by RTK Query
    }
  };

  return (
    <div>
      <AddMemberDialog
        isOpen={showDialog}
        onClose={() => setShowDialog(false)}
        onSubmit={handleAddMember}
      />
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-gray-900 dark:text-gray-100">
          Members
        </h2>
        <button
          onClick={() => setShowDialog(true)}
          className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          <Plus className="w-4 h-4" />
          Add Member
        </button>
      </div>
      {members.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No members added yet. Invite team members to collaborate.
        </div>
      ) : (
        <div className="space-y-2">
          {members.map((member, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                  <Users className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                </div>
                <div>
                  <div className="font-medium text-gray-900 dark:text-gray-100">
                    {member.userId}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    Added {new Date(member.addedAt).toLocaleDateString()}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {member.role !== "owner" && (
                  <button
                    aria-label="Remove member"
                    onClick={() => handleRemoveMember(member.userId)}
                    className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
                <span
                  className={`px-2 py-0.5 text-xs rounded-full ${
                    member.role === "owner"
                      ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
                      : member.role === "editor"
                        ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                        : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                  }`}
                >
                  {member.role}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
