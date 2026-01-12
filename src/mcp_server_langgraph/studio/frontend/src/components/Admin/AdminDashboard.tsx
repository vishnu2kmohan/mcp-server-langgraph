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
import { AIQualityMetricsCard } from "./AIQualityMetricsCard";
import {
  AgentApprovalAuditLog,
  type AuditEntry,
} from "./AgentApprovalAuditLog";
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
  useGetFeatureFlagsQuery,
} from "../../api";
import type { WebSocketConnectionStatus } from "../../hooks/useRealtimeSync";

import { Button } from "@/components/UI";

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
  alertConnectionStatus?: WebSocketConnectionStatus;
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
  const [selectedRemediationForDialog, setSelectedRemediationForDialog] =
    useState<string | null>(null);
  const [dialogError, setDialogError] = useState<string | null>(null);
  const dispatch = useAppDispatch();

  // Alert selectors
  const selectedAlert = useAppSelector(selectSelectedAlert);
  const criticalCount = useAppSelector(selectCriticalAlertCount);
  const warningCount = useAppSelector(selectWarningAlertCount);

  // User selector for attribution
  const currentUsername = useAppSelector(selectUsername);

  // Feature flags
  const { data: featureFlags } = useGetFeatureFlagsQuery();
  const showAiQualityMetrics = featureFlags?.ai_quality_metrics ?? true;

  // Keyboard shortcuts for tab navigation
  const goToOverview = useCallback(() => setActiveTab("overview"), []);
  const goToUsers = useCallback(() => setActiveTab("users"), []);
  const goToAlerts = useCallback(() => setActiveTab("alerts"), []);
  const goToAgentRequests = useCallback(
    () => setActiveTab("agent-requests"),
    [],
  );

  useKeyboardShortcuts({
    "shift+o": goToOverview,
    "shift+u": goToUsers,
    "shift+a": goToAlerts,
    "shift+r": goToAgentRequests,
  });

  // Alert API hooks
  const { data: recommendation, isLoading: recommendationLoading } =
    useGetAlertRecommendationQuery(selectedAlert?.alertId ?? "", {
      skip: !selectedAlert,
    });
  const [approveRemediation, { isLoading: isApproving }] =
    useApproveRemediationMutation();
  const [rejectRemediation, { isLoading: isRejecting }] =
    useRejectRemediationMutation();
  const [regenerateRecommendation, { isLoading: isRegenerating }] =
    useRegenerateAlertRecommendationMutation();

  // Agent HITL API hooks
  const { data: pendingAgentRequests, isLoading: agentRequestsLoading } =
    useListPendingAgentRequestsQuery();
  const [batchApproveRequests, { isLoading: isBatchApproving }] =
    useBatchApproveAgentRequestsMutation();
  const [batchRejectRequests, { isLoading: isBatchRejecting }] =
    useBatchRejectAgentRequestsMutation();

  // Build pending remediations from recommendation steps
  const pendingRemediations = useMemo((): RemediationRequest[] => {
    if (!recommendation || !selectedAlert) return [];
    // Only critical and warning alerts can have remediations
    const remediationSeverity =
      selectedAlert.severity === "info" ? "warning" : selectedAlert.severity;
    return recommendation.remediationSteps.map((step) => ({
      remediationId: `${recommendation.recommendationId}-step-${step.stepNumber}`,
      alertId: selectedAlert.alertId,
      alertName: selectedAlert.name,
      severity: remediationSeverity as "warning" | "critical",
      stepNumber: step.stepNumber,
      action: step.action,
      description: step.description,
      command: step.command ?? null,
      riskLevel: step.riskLevel,
      status: "pending" as const,
      requestedAt: recommendation.generatedAt,
      approvedBy: null,
      approvedAt: null,
      reason: null,
      recommendationId: recommendation.recommendationId,
    }));
  }, [recommendation, selectedAlert]);

  // Find remediation for dialog
  const selectedRemediation = pendingRemediations.find(
    (r) => r.remediationId === selectedRemediationForDialog,
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
      setDialogError(
        err instanceof Error ? err.message : "Failed to approve remediation",
      );
    }
  };

  // Handle actual rejection from dialog
  const handleDialogReject = async (data: RejectRemediationRequest) => {
    try {
      await rejectRemediation(data).unwrap();
      handleCloseDialog();
    } catch (err) {
      setDialogError(
        err instanceof Error ? err.message : "Failed to reject remediation",
      );
    }
  };

  const handleRegenerate = () => {
    if (selectedAlert) {
      regenerateRecommendation(selectedAlert.alertId);
    }
  };

  const handleCloseDetail = () => {
    dispatch(setSelectedAlertId(null));
  };

  // Agent HITL batch handlers
  // NOTE: approved_by/rejected_by are derived from auth on the backend
  const handleBatchApproveAgents = useCallback(
    async (requestIds: string[], reason?: string) => {
      await batchApproveRequests({
        request_ids: requestIds,
        reason,
      }).unwrap();
    },
    [batchApproveRequests],
  );

  const handleBatchRejectAgents = useCallback(
    async (requestIds: string[], reason?: string) => {
      await batchRejectRequests({
        request_ids: requestIds,
        reason,
      }).unwrap();
    },
    [batchRejectRequests],
  );

  // Handle audit log export
  const handleExportAuditLog = useCallback((entries: AuditEntry[]) => {
    const csv = [
      [
        "ID",
        "Request ID",
        "Agent",
        "Decision",
        "Confidence",
        "Threshold",
        "Decided By",
        "Date",
        "Reason",
      ].join(","),
      ...entries.map((e) =>
        [
          e.id,
          e.requestId,
          e.agentName,
          e.decision,
          (e.confidence * 100).toFixed(0) + "%",
          (e.threshold * 100).toFixed(0) + "%",
          e.decidedBy,
          e.decidedAt,
          e.reason ?? "",
        ].join(","),
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
  const effectiveAlertCount =
    alertCount > 0 ? alertCount : criticalCount + warningCount;

  if (isLoading) {
    return (
      <div
        data-testid="dashboard-loading"
        className="flex items-center justify-center h-full"
      >
        <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
      </div>
    );
  }

  const getHealthColor = (status: SystemHealth["status"]) => {
    switch (status) {
      case "healthy":
        return "bg-success-500";
      case "degraded":
        return "bg-warning-500";
      case "unhealthy":
        return "bg-error-500";
    }
  };

  // Count pending agent requests
  const pendingAgentRequestCount = pendingAgentRequests?.totalCount ?? 0;

  const tabs: {
    id: TabId;
    label: string;
    badge?: number;
    icon?: "alert" | "agent";
  }[] = [
    { id: "overview", label: "Overview" },
    { id: "users", label: "Users" },
    {
      id: "alerts",
      label: "Alerts",
      badge: effectiveAlertCount,
      icon: "alert",
    },
    {
      id: "agent-requests",
      label: "Agent Requests",
      badge: pendingAgentRequestCount,
      icon: "agent",
    },
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-neutral-900 dark:text-white">
          Admin Dashboard
        </h1>
        <Button
          variant="primary"
          className="flex px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700"
          onClick={onRefresh}
          aria-label="Refresh dashboard"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </Button>
      </div>
      {/* Tabs */}
      <div
        role="tablist"
        className="flex border-b border-neutral-200 dark:border-neutral-700"
      >
        {tabs.map((tab) => (
          <Button
            className="flex px-4 py-2 text-sm border-b-2"
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.icon === "alert" && <AlertTriangle className="w-4 h-4" />}
            {tab.icon === "agent" && <UserCheck className="w-4 h-4" />}
            {tab.label}
            {tab.badge !== undefined && tab.badge > 0 && (
              <span
                data-testid="alert-badge"
                className="flex items-center justify-center min-w-[20px] h-5 px-1.5 text-xs font-medium text-white bg-error-500 rounded-full"
              >
                {tab.badge}
              </span>
            )}
          </Button>
        ))}
      </div>
      {/* Tab Content */}
      {activeTab === "overview" && (
        <>
          {/* System Health Section */}
          <section className="bg-white dark:bg-neutral-800 rounded-lg p-6 shadow">
            <h2 className="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
              System Health
            </h2>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* Status */}
              <div className="bg-neutral-50 dark:bg-neutral-700 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div
                    data-testid="health-status"
                    className={`w-3 h-3 rounded-full ${getHealthColor(systemHealth.status)}`}
                  />
                  <span className="text-sm text-neutral-600 dark:text-neutral-300">
                    Status
                  </span>
                </div>
                <span className="text-lg font-semibold text-neutral-900 dark:text-white capitalize">
                  {systemHealth.status}
                </span>
              </div>

              {/* Uptime */}
              <div className="bg-neutral-50 dark:bg-neutral-700 rounded-lg p-4">
                <span className="text-sm text-neutral-600 dark:text-neutral-300 block mb-2">
                  Uptime
                </span>
                <span className="text-lg font-semibold text-neutral-900 dark:text-white">
                  {systemHealth.uptime}%
                </span>
              </div>

              {/* Active Users */}
              <div className="bg-neutral-50 dark:bg-neutral-700 rounded-lg p-4">
                <span className="text-sm text-neutral-600 dark:text-neutral-300 block mb-2">
                  Active Users
                </span>
                <span className="text-lg font-semibold text-neutral-900 dark:text-white">
                  {systemHealth.activeUsers}
                </span>
              </div>

              {/* Error Rate */}
              <div className="bg-neutral-50 dark:bg-neutral-700 rounded-lg p-4">
                <span className="text-sm text-neutral-600 dark:text-neutral-300 block mb-2">
                  Error Rate
                </span>
                <span className="text-lg font-semibold text-neutral-900 dark:text-white">
                  {systemHealth.errorRate}%
                </span>
              </div>
            </div>
          </section>

          {/* HEART Metrics Section */}
          <section className="bg-white dark:bg-neutral-800 rounded-lg p-6 shadow">
            <h2 className="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
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

          {/* AI Quality Metrics Section (feature-flagged) */}
          {showAiQualityMetrics && (
            <AIQualityMetricsCard timeframe="7d" showToggle />
          )}
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
        <div
          data-testid="alerts-container"
          className="grid grid-cols-1 lg:grid-cols-2 gap-6"
        >
          {/* Alerts Panel */}
          <div className="bg-white dark:bg-neutral-800 rounded-lg shadow overflow-hidden">
            <AlertsPanel
              onSelectAlert={handleSelectAlert}
              onSoundToggle={handleSoundToggle}
              isLoading={alertsLoading}
              connectionStatus={alertConnectionStatus}
            />
          </div>

          {/* Alert Detail Panel */}
          <div className="bg-white dark:bg-neutral-800 rounded-lg shadow overflow-hidden">
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
          <div className="bg-white dark:bg-neutral-800 rounded-lg shadow overflow-hidden">
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
          <div className="bg-white dark:bg-neutral-800 rounded-lg shadow overflow-hidden">
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
    if (value >= 80) return "text-success-600";
    if (value >= 60) return "text-warning-600";
    return "text-error-600";
  };

  return (
    <div className="bg-neutral-50 dark:bg-neutral-700 rounded-lg p-4">
      <span className="text-sm text-neutral-600 dark:text-neutral-300 block mb-2">
        {label}
      </span>
      <span className={`text-lg font-semibold ${getColor(value)}`}>
        {value}%
      </span>
    </div>
  );
}
