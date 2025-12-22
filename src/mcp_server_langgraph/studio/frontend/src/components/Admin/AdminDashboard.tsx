/**
 * AdminDashboard Component
 *
 * Main dashboard for administrators with system health, HEART metrics, user management,
 * and infrastructure alerts.
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { useState, useMemo, useCallback } from "react";
import { RefreshCw, Loader2, AlertTriangle, UserCheck } from "lucide-react";
import { useKeyboardShortcuts } from "../../hooks/useKeyboardShortcuts";
import { UserManager, type User } from "./UserManager";
import { AlertsPanel } from "./AlertsPanel";
import { AlertDetailPanel } from "./AlertDetailPanel";
import { RemediationApprovalDialog } from "./RemediationApprovalDialog";
import { BatchApprovalPanel } from "./BatchApprovalPanel";
import { AgentApprovalAuditLog, type AuditEntry } from "./AgentApprovalAuditLog";
import type {
  RemediationRequest,
  ApproveRemediationRequest,
  RejectRemediationRequest,
} from "../../types/api";
import { useAppSelector, useAppDispatch } from "../../store/hooks";
import {
  selectSelectedAlert,
  selectCriticalAlertCount,
  selectWarningAlertCount,
  setSelectedAlertId,
  toggleSound,
} from "../../store/slices/alertSlice";
import { selectUsername } from "../../store/slices/personaSlice";
import {
  useGetAlertRecommendationQuery,
  useApproveRemediationMutation,
  useRejectRemediationMutation,
  useRegenerateAlertRecommendationMutation,
  useListPendingAgentRequestsQuery,
  useBatchApproveAgentRequestsMutation,
  useBatchRejectAgentRequestsMutation,
} from "../../api";
import type { ConnectionStatus } from "../../hooks/useRealtimeSync";

export interface SystemHealth {
  status: "healthy" | "degraded" | "unhealthy";
  uptime: number;
  activeUsers: number;
  activeSessions: number;
  errorRate: number;
}

export interface HEARTMetrics {
  happiness: number;
  engagement: number;
  adoption: number;
  retention: number;
  taskSuccess: number;
}

export interface AdminDashboardProps {
  systemHealth: SystemHealth;
  heartMetrics: HEARTMetrics;
  isLoading: boolean;
  onRefresh: () => void;
  // User management props (optional for backwards compatibility)
  users?: User[];
  usersLoading?: boolean;
  onUpdateRoles?: (userId: string, roles: string[]) => void;
  onDeactivate?: (userId: string) => void;
  onActivate?: (userId: string) => void;
  onInvite?: (email: string, roles: string[]) => void;
  // Alert props (optional for backwards compatibility)
  alertCount?: number;
  alertsLoading?: boolean;
  alertConnectionStatus?: ConnectionStatus;
}

type TabId = "overview" | "users" | "alerts" | "agent-requests";

export function AdminDashboard({
  systemHealth,
  heartMetrics,
  isLoading,
  onRefresh,
  users = [],
  usersLoading = false,
  onUpdateRoles = () => {},
  onDeactivate = () => {},
  onActivate = () => {},
  onInvite = () => {},
  alertCount = 0,
  alertsLoading = false,
  alertConnectionStatus = "connected",
}: AdminDashboardProps) {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [selectedRemediationForDialog, setSelectedRemediationForDialog] = useState<string | null>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const dispatch = useAppDispatch();

  // Alert selectors
  const selectedAlert = useAppSelector(selectSelectedAlert);
  const criticalCount = useAppSelector(selectCriticalAlertCount);
  const warningCount = useAppSelector(selectWarningAlertCount);

  // User selector for attribution
  const currentUsername = useAppSelector(selectUsername);

  // Keyboard shortcuts for tab navigation
  const goToOverview = useCallback(() => setActiveTab("overview"), []);
  const goToUsers = useCallback(() => setActiveTab("users"), []);
  const goToAlerts = useCallback(() => setActiveTab("alerts"), []);
  const goToAgentRequests = useCallback(() => setActiveTab("agent-requests"), []);

  useKeyboardShortcuts({
    "shift+o": goToOverview,
    "shift+u": goToUsers,
    "shift+a": goToAlerts,
    "shift+r": goToAgentRequests,
  });

  // Alert API hooks
  const { data: recommendation, isLoading: recommendationLoading } = useGetAlertRecommendationQuery(
    selectedAlert?.alert_id ?? "",
    { skip: !selectedAlert }
  );
  const [approveRemediation, { isLoading: isApproving }] = useApproveRemediationMutation();
  const [rejectRemediation, { isLoading: isRejecting }] = useRejectRemediationMutation();
  const [regenerateRecommendation, { isLoading: isRegenerating }] = useRegenerateAlertRecommendationMutation();

  // Agent HITL API hooks
  const { data: pendingAgentRequests, isLoading: agentRequestsLoading } = useListPendingAgentRequestsQuery();
  const [batchApproveRequests, { isLoading: isBatchApproving }] = useBatchApproveAgentRequestsMutation();
  const [batchRejectRequests, { isLoading: isBatchRejecting }] = useBatchRejectAgentRequestsMutation();

  // Build pending remediations from recommendation steps
  const pendingRemediations = useMemo((): RemediationRequest[] => {
    if (!recommendation || !selectedAlert) return [];
    // Only critical and warning alerts can have remediations
    const remediationSeverity = selectedAlert.severity === "info" ? "warning" : selectedAlert.severity;
    return recommendation.remediation_steps.map((step) => ({
      remediation_id: `${recommendation.recommendation_id}-step-${step.step_number}`,
      alert_id: selectedAlert.alert_id,
      alert_name: selectedAlert.name,
      severity: remediationSeverity as "warning" | "critical",
      step_number: step.step_number,
      action: step.action,
      description: step.description,
      command: step.command ?? null,
      risk_level: step.risk_level,
      status: "pending" as const,
      requested_at: recommendation.generated_at,
      approved_by: null,
      approved_at: null,
      reason: null,
      recommendation_id: recommendation.recommendation_id,
    }));
  }, [recommendation, selectedAlert]);

  // Find remediation for dialog
  const selectedRemediation = pendingRemediations.find(
    (r) => r.remediation_id === selectedRemediationForDialog
  );

  // Alert handlers
  const handleSelectAlert = (alertId: string) => {
    dispatch(setSelectedAlertId(alertId));
  };

  const handleSoundToggle = () => {
    dispatch(toggleSound());
  };

  // Open dialog instead of directly approving
  const handleApproveClick = (remediationId: string) => {
    setDialogError(null);
    setSelectedRemediationForDialog(remediationId);
  };

  // Open dialog instead of directly rejecting
  const handleRejectClick = (remediationId: string) => {
    setDialogError(null);
    setSelectedRemediationForDialog(remediationId);
  };

  // Close dialog
  const handleCloseDialog = () => {
    setSelectedRemediationForDialog(null);
    setDialogError(null);
  };

  // Handle actual approval from dialog
  const handleDialogApprove = async (data: ApproveRemediationRequest) => {
    try {
      await approveRemediation(data).unwrap();
      handleCloseDialog();
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : "Failed to approve remediation");
    }
  };

  // Handle actual rejection from dialog
  const handleDialogReject = async (data: RejectRemediationRequest) => {
    try {
      await rejectRemediation(data).unwrap();
      handleCloseDialog();
    } catch (err) {
      setDialogError(err instanceof Error ? err.message : "Failed to reject remediation");
    }
  };

  const handleRegenerate = () => {
    if (selectedAlert) {
      regenerateRecommendation(selectedAlert.alert_id);
    }
  };

  const handleCloseDetail = () => {
    dispatch(setSelectedAlertId(null));
  };

  // Agent HITL batch handlers
  const handleBatchApproveAgents = useCallback(
    async (requestIds: string[], reason?: string) => {
      await batchApproveRequests({
        request_ids: requestIds,
        approved_by: currentUsername ?? "admin",
        reason,
      }).unwrap();
    },
    [batchApproveRequests, currentUsername]
  );

  const handleBatchRejectAgents = useCallback(
    async (requestIds: string[], reason?: string) => {
      await batchRejectRequests({
        request_ids: requestIds,
        rejected_by: currentUsername ?? "admin",
        reason,
      }).unwrap();
    },
    [batchRejectRequests, currentUsername]
  );

  // Handle audit log export
  const handleExportAuditLog = useCallback((entries: AuditEntry[]) => {
    const csv = [
      ["ID", "Request ID", "Agent", "Decision", "Confidence", "Threshold", "Decided By", "Date", "Reason"].join(","),
      ...entries.map((e) =>
        [
          e.id,
          e.request_id,
          e.agent_name,
          e.decision,
          (e.confidence * 100).toFixed(0) + "%",
          (e.threshold * 100).toFixed(0) + "%",
          e.decided_by,
          e.decided_at,
          e.reason ?? "",
        ].join(",")
      ),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `agent-approval-audit-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  // Mock audit entries (until audit log API is implemented)
  const mockAuditEntries: AuditEntry[] = useMemo(() => [], []);

  // Use prop or Redux count
  const effectiveAlertCount = alertCount > 0 ? alertCount : criticalCount + warningCount;

  if (isLoading) {
    return (
      <div
        data-testid="dashboard-loading"
        className="flex items-center justify-center h-full"
      >
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const getHealthColor = (status: SystemHealth["status"]) => {
    switch (status) {
      case "healthy":
        return "bg-green-500";
      case "degraded":
        return "bg-yellow-500";
      case "unhealthy":
        return "bg-red-500";
    }
  };

  // Count pending agent requests
  const pendingAgentRequestCount = pendingAgentRequests?.total_count ?? 0;

  const tabs: { id: TabId; label: string; badge?: number; icon?: "alert" | "agent" }[] = [
    { id: "overview", label: "Overview" },
    { id: "users", label: "Users" },
    { id: "alerts", label: "Alerts", badge: effectiveAlertCount, icon: "alert" },
    { id: "agent-requests", label: "Agent Requests", badge: pendingAgentRequestCount, icon: "agent" },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Admin Dashboard
        </h1>
        <button
          onClick={onRefresh}
          className="flex items-center gap-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          aria-label="Refresh dashboard"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div
        role="tablist"
        className="flex border-b border-gray-200 dark:border-gray-700"
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? "border-blue-600 text-blue-600 dark:text-blue-400"
                : "border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
            }`}
          >
            {tab.icon === "alert" && <AlertTriangle className="w-4 h-4" />}
            {tab.icon === "agent" && <UserCheck className="w-4 h-4" />}
            {tab.label}
            {tab.badge !== undefined && tab.badge > 0 && (
              <span
                data-testid="alert-badge"
                className="flex items-center justify-center min-w-[20px] h-5 px-1.5 text-xs font-medium text-white bg-red-500 rounded-full"
              >
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "overview" && (
        <>
          {/* System Health Section */}
          <section className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              System Health
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* Status */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div
                    data-testid="health-status"
                    className={`w-3 h-3 rounded-full ${getHealthColor(systemHealth.status)}`}
                  />
                  <span className="text-sm text-gray-600 dark:text-gray-300">
                    Status
                  </span>
                </div>
                <span className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
                  {systemHealth.status}
                </span>
              </div>

              {/* Uptime */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <span className="text-sm text-gray-600 dark:text-gray-300 block mb-2">
                  Uptime
                </span>
                <span className="text-lg font-semibold text-gray-900 dark:text-white">
                  {systemHealth.uptime}%
                </span>
              </div>

              {/* Active Users */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <span className="text-sm text-gray-600 dark:text-gray-300 block mb-2">
                  Active Users
                </span>
                <span className="text-lg font-semibold text-gray-900 dark:text-white">
                  {systemHealth.activeUsers}
                </span>
              </div>

              {/* Error Rate */}
              <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                <span className="text-sm text-gray-600 dark:text-gray-300 block mb-2">
                  Error Rate
                </span>
                <span className="text-lg font-semibold text-gray-900 dark:text-white">
                  {systemHealth.errorRate}%
                </span>
              </div>
            </div>
          </section>

          {/* HEART Metrics Section */}
          <section className="bg-white dark:bg-gray-800 rounded-lg p-6 shadow">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              HEART Metrics
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <MetricCard label="Happiness" value={heartMetrics.happiness} />
              <MetricCard label="Engagement" value={heartMetrics.engagement} />
              <MetricCard label="Adoption" value={heartMetrics.adoption} />
              <MetricCard label="Retention" value={heartMetrics.retention} />
              <MetricCard
                label="Task Success"
                value={heartMetrics.taskSuccess}
              />
            </div>
          </section>
        </>
      )}

      {activeTab === "users" && (
        <UserManager
          users={users}
          isLoading={usersLoading}
          onUpdateRoles={onUpdateRoles}
          onDeactivate={onDeactivate}
          onActivate={onActivate}
          onInvite={onInvite}
        />
      )}

      {activeTab === "alerts" && (
        <div data-testid="alerts-container" className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Alerts Panel */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <AlertsPanel
              onSelectAlert={handleSelectAlert}
              onSoundToggle={handleSoundToggle}
              isLoading={alertsLoading}
              connectionStatus={alertConnectionStatus}
            />
          </div>

          {/* Alert Detail Panel */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <AlertDetailPanel
              alert={selectedAlert ?? null}
              recommendation={recommendation ?? null}
              pendingRemediations={pendingRemediations}
              onApprove={handleApproveClick}
              onReject={handleRejectClick}
              onRegenerate={handleRegenerate}
              onClose={handleCloseDetail}
              isLoadingRecommendation={recommendationLoading}
              isRegenerating={isRegenerating}
            />
          </div>
        </div>
      )}

      {activeTab === "agent-requests" && (
        <div data-testid="agent-requests-container" className="space-y-6">
          {/* Batch Approval Panel */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <BatchApprovalPanel
              approvals={pendingAgentRequests?.approvals ?? []}
              onBatchApprove={handleBatchApproveAgents}
              onBatchReject={handleBatchRejectAgents}
              currentUser={currentUsername ?? undefined}
              isApproving={isBatchApproving}
              isRejecting={isBatchRejecting}
            />
          </div>

          {/* Audit Log */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
            <AgentApprovalAuditLog
              entries={mockAuditEntries}
              isLoading={agentRequestsLoading}
              onExport={handleExportAuditLog}
            />
          </div>
        </div>
      )}

      {/* Remediation Approval Dialog */}
      {selectedRemediation && recommendation && (
        <RemediationApprovalDialog
          remediation={selectedRemediation}
          recommendation={recommendation}
          isOpen={!!selectedRemediationForDialog}
          onClose={handleCloseDialog}
          onApprove={handleDialogApprove}
          onReject={handleDialogReject}
          isApproving={isApproving}
          isRejecting={isRejecting}
          error={dialogError}
          currentUser={currentUsername ?? "unknown"}
        />
      )}
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: number;
}

function MetricCard({ label, value }: MetricCardProps) {
  const getColor = (value: number) => {
    if (value >= 80) return "text-green-600";
    if (value >= 60) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
      <span className="text-sm text-gray-600 dark:text-gray-300 block mb-2">
        {label}
      </span>
      <span className={`text-lg font-semibold ${getColor(value)}`}>
        {value}%
      </span>
    </div>
  );
}
