/**
 * Admin Components
 *
 * Components for the admin portal with user and organization management.
 */

export { AdminDashboard } from "./AdminDashboard";
export type {
  AdminDashboardProps,
  SystemHealth,
  HEARTMetrics,
} from "./AdminDashboard";

export { OrganizationManager } from "./OrganizationManager";
export type {
  OrganizationManagerProps,
  Organization,
  OrganizationFormData,
} from "./OrganizationManager";

export { UserManager } from "./UserManager";
export type { UserManagerProps, User } from "./UserManager";

export { AuditLogFilters } from "./AuditLogFilters";
export type {
  AuditLogFiltersProps,
  DateRange,
  ActionType,
} from "./AuditLogFilters";

export { MetricCard } from "./MetricCard";
export type { MetricCardProps } from "./MetricCard";

// Alert components (ADR-0026)
export { AlertsPanel } from "./AlertsPanel";
export type { AlertsPanelProps } from "./AlertsPanel";

export { AlertDetailPanel } from "./AlertDetailPanel";
export type { AlertDetailPanelProps } from "./AlertDetailPanel";

export { RemediationApprovalDialog } from "./RemediationApprovalDialog";
export type { RemediationApprovalDialogProps } from "./RemediationApprovalDialog";

export { AIRecommendationCard } from "./AIRecommendationCard";
export type { AIRecommendationCardProps } from "./AIRecommendationCard";

// Agent HITL approval components
export { AgentApprovalDialog } from "./AgentApprovalDialog";
export type {
  AgentApprovalDialogProps,
  AgentApprovalRequestCamelCase,
} from "./AgentApprovalDialog";

export { ClarificationDialog } from "./ClarificationDialog";
export type { ClarificationDialogProps } from "./ClarificationDialog";

export { BatchApprovalPanel } from "./BatchApprovalPanel";
export type {
  BatchApprovalPanelProps,
  ApprovalRequest,
} from "./BatchApprovalPanel";

export { AgentApprovalAuditLog } from "./AgentApprovalAuditLog";
export type {
  AgentApprovalAuditLogProps,
  AuditEntry,
} from "./AgentApprovalAuditLog";
